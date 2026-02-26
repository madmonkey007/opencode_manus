from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import asyncio
import json
import uuid
import os
import re
import logging
import subprocess
import shlex

# Configure logging FIRST before using logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("opencode")

# 导入历史追踪服务
try:
    from .history_service import get_history_service

    history_service = get_history_service()
    logger.info("History service initialized")
except ImportError as e:
    logger.warning(f"Failed to import history service: {e}")
    history_service = None

# 导入新架构 API（阶段 2）
try:
    from .api import router as api_router

    logger.info("New API router imported successfully")
except ImportError as e:
    logger.warning(f"Failed to import new API router: {e}")
    import traceback

    logger.error(traceback.format_exc())
    api_router = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入提示词增强模块
from .prompt_enhancer import enhance_prompt

# Workspace setup
WORKSPACE_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../workspace")
)
os.makedirs(WORKSPACE_BASE, exist_ok=True)

# ====================================================================
# 注册新架构 API Router（阶段 2）
# ====================================================================
if api_router:
    logger.info(f"Including api_router with {len(api_router.routes)} routes")
    app.include_router(api_router)
    logger.info(f"After include_router, total routes: {len(app.routes)}")
    logger.info("New API router registered at /opencode")
else:
    logger.warning("New API router not available, using legacy API only")

# Mount static files
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../static"))
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def read_index():
    path = os.path.join(static_dir, "index.html")
    return FileResponse(path)


@app.get("/frontend")
async def read_index_frontend():
    """Frontend 分支的前端页面"""
    path = os.path.join(static_dir, "index.html")
    return FileResponse(path)


def format_sse(data: dict) -> str:
    """Safely format SSE data using chr codes for newlines to avoid physical line break issues"""
    json_data = json.dumps(data)
    n = chr(10)
    return "data: " + json_data + n + n


@app.get("/opencode/list_session_files")
async def list_session_files(sid: str):
    # 如果前端 sid 有映射到实际的 opencode sid，使用实际的
    actual_sid = _session_id_map.get(sid, sid)
    session_dir = os.path.join(WORKSPACE_BASE, actual_sid)
    if not os.path.exists(session_dir):
        return {"files": []}

    files = []
    for root, dirs, filenames in os.walk(session_dir):
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), session_dir)
            url_path = (sid + "/" + rel_path).replace(os.sep, "/")
            files.append({"name": rel_path, "path": url_path})
    return {"files": files}


@app.get("/opencode/get_file_content")
async def get_file_content(path: str):
    full_path = os.path.abspath(os.path.join(WORKSPACE_BASE, path))
    if not full_path.startswith(WORKSPACE_BASE):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(full_path)[1].lower()
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".pdf", ".html", ".htm", ".svg"]:
        return FileResponse(full_path)

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "content": content,
            "filename": os.path.basename(full_path),
            "type": "text",
        }
    except Exception as e:
        return {"content": f"Error reading file: {str(e)}", "type": "error"}


@app.get("/opencode/read_file")
async def read_file(session_id: str, file_path: str):
    """
    读取会话工作区中的文件内容

    Args:
        session_id: 会话ID
        file_path: 文件路径（相对于会话工作区）
    """
    try:
        # 构建完整路径
        session_dir = os.path.join(WORKSPACE_BASE, session_id)
        full_path = os.path.abspath(os.path.join(session_dir, file_path))

        # 安全检查：确保文件在会话目录内
        if not full_path.startswith(session_dir):
            return {"status": "error", "message": "Access denied"}

        if not os.path.exists(full_path):
            return {"status": "error", "message": "File not found"}

        # 读取文件内容
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "status": "success",
            "content": content,
            "file_path": file_path,
            "size": len(content)
        }
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/opencode/get_log")
async def get_log(sid: str, offset: int = 0):
    """
    Get execution log for a specific session.
    offset: The byte offset to start reading from.
    Returns: {"content": "...", "next_offset": 123, "status": "running/completed"}
    """
    session_dir = os.path.join(WORKSPACE_BASE, sid)
    log_file = os.path.join(session_dir, "run.log")

    if not os.path.exists(log_file):
        return {"content": "", "next_offset": 0, "status": "unknown"}

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            f.seek(offset)
            content = f.read()
            next_offset = f.tell()

        # Check if process is still running (simple check via status file if exists)
        status = "running"
        status_file = os.path.join(session_dir, "status.txt")
        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as f:
                status = f.read().strip()

        return {"content": content, "next_offset": next_offset, "status": status}
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return {"content": "", "next_offset": offset, "status": "error"}


# Global Session Manager
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    async def create_session(self, sid: str, prompt: str, mode: str = "auto"):
        if sid in self.sessions:
            return self.sessions[sid]

        self.sessions[sid] = {
            "queues": [],  # List of queues for connected clients
            "status": "starting",
            "process": None,
        }

        # Start background task
        asyncio.create_task(self._run_process(sid, prompt, mode))
        return self.sessions[sid]

    async def _run_process(self, sid: str, prompt: str, mode: str = "auto"):
        session_dir = os.path.join(WORKSPACE_BASE, sid)
        os.makedirs(session_dir, exist_ok=True)
        log_file = os.path.join(session_dir, "run.log")
        status_file = os.path.join(session_dir, "status.txt")

        # Init logs
        with open(status_file, "w", encoding="utf-8") as f:
            f.write("running")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Session started: {sid}\n")

        try:
            # ====================================================================
            # 智能提示词增强：在执行前根据用户意图添加技术指导
            # ====================================================================
            logger.info(f"[DEBUG] Received prompt: '{prompt}'")
            logger.info(f"[DEBUG] Prompt length: {len(prompt)}")

            enhanced_prompt = enhance_prompt(prompt, mode)
            logger.info(f"Original prompt: {prompt[:100]}...")
            logger.info(f"Enhanced prompt length: {len(enhanced_prompt)} chars")
            logger.info(f"[DEBUG] Enhanced prompt: '{enhanced_prompt[:200]}'")

            # 不使用 script 命令，直接构建命令数组
            # 这样可以避免 shell 引号解析问题
            # Ensure PATH includes bun location
            path_env = "/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"

            # 构建命令数组，最后一个参数是 prompt
            # 不使用 --session 参数，每次调用都是独立的
            # 会话上下文管理由前端通过传递完整 prompt 来实现
            cmd = [
                "opencode",
                "run",
                "--model",
                "new-api/gemini-3-flash-preview",
                "--format",
                "json",
            ]
            
            # 添加 agent 模式
            if mode in ["plan", "build"]:
                cmd.extend(["--agent", mode])
            
            cmd.append(enhanced_prompt)

            logger.info(
                f"[DEBUG] Final command: {' '.join(cmd[:10])}... [prompt length: {len(enhanced_prompt)}]"
            )

            env = {**os.environ}
            env["PATH"] = path_env
            env["FORCE_COLOR"] = "1"

            # Use config_host directly as it's verified to work
            patched_config = "/app/opencode/config_host/opencode.json"
            if os.path.exists(patched_config):
                env["OPENCODE_CONFIG_FILE"] = patched_config

            logger.info(f"Starting process for {sid} with command: {cmd}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=session_dir,
                env=env,
            )

            if sid in self.sessions:
                self.sessions[sid]["process"] = process
                self.sessions[sid]["status"] = "running"

            async for line in process.stdout:
                decoded = line.decode(errors="ignore").strip()
                if decoded:
                    # Write to file
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(decoded + "\n")

                    # Broadcast to queues
                    if sid in self.sessions:
                        for q in self.sessions[sid]["queues"]:
                            await q.put(decoded)

            await process.wait()

            with open(status_file, "w", encoding="utf-8") as f:
                f.write("completed")

            # Notify completion
            if sid in self.sessions:
                self.sessions[sid]["status"] = "completed"
                # Keep session in memory for a while? Or just let it be.
                # Remove queues but keep status?

        except Exception as e:
            logger.error(f"Process error for {sid}: {e}")
            with open(status_file, "w", encoding="utf-8") as f:
                f.write("error")
            if sid in self.sessions:
                self.sessions[sid]["status"] = "error"

    async def attach(self, sid: str):
        if sid not in self.sessions:
            return None

        q = asyncio.Queue()
        self.sessions[sid]["queues"].append(q)
        return q

    def detach(self, sid: str, q: asyncio.Queue):
        if sid in self.sessions and q in self.sessions[sid]["queues"]:
            self.sessions[sid]["queues"].remove(q)


session_manager = SessionManager()

# Track whether we've already sent phases_init for this session
_phases_initialized = {}
# Track the number of phases for each session (to detect when Agent merges tasks)
_phase_counts = {}
# Track frontend_sid -> actual_opencode_sid mapping
# OpenCode generates its own session IDs, so we need to map them
_session_id_map = {}
_reverse_session_id_map = {}  # actual_opencode_sid -> frontend_sid (for reverse lookup)


async def run_agent(prompt: str, sid: str, mode: str = "auto"):
    """
    Bridge to the official opencode CLI with Manus-level SSE extensions
    """
    session_dir = os.path.join(WORKSPACE_BASE, sid)

    # Ensure session exists or create new
    is_new = sid not in session_manager.sessions
    await session_manager.create_session(sid, prompt, mode)

    # Attach listener
    queue = await session_manager.attach(sid)

    async def event_generator():
        logger.info(f"Manus-Integrated Agent session attached: {sid}")

        # Always reset phases_initialized flag for new/resumed sessions
        # This ensures we always generate phases from the first todowrite
        _phases_initialized[sid] = False
        # Also reset phase count tracking
        if sid in _phase_counts:
            del _phase_counts[sid]

        # 1. Initialize with a temporary "Planning" phase
        # 这个阶段会被后续的 todowrite 动态生成的阶段替换
        yield format_sse(
            {
                "type": "phases_init",
                "phases": [
                    {
                        "id": "phase_planning",
                        "number": 0,
                        "title": "📋 正在制定执行计划...",
                        "status": "active",
                    }
                ],
            }
        )

        # 2. Catch-up from log file
        log_file = os.path.join(session_dir, "run.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            # Process historical line same as new line
                            async for event in process_log_line(line, sid):
                                yield event
            except Exception as e:
                logger.error(f"Error reading history: {e}")

        # 3. Stream new events
        last_activity = asyncio.get_running_loop().time()

        try:
            while True:
                try:
                    # Wait for output
                    text = await asyncio.wait_for(queue.get(), timeout=1.0)
                    last_activity = asyncio.get_running_loop().time()

                    async for event in process_log_line(text, sid):
                        yield event

                except asyncio.TimeoutError:
                    # Check status
                    session = session_manager.sessions.get(sid)
                    if (
                        session
                        and session["status"] in ["completed", "error"]
                        and queue.empty()
                    ):
                        if session["status"] == "completed":
                            # 完成时，将所有剩余阶段标记为完成
                            phase_count = _phase_counts.get(sid, 0)
                            logger.info(
                                f"[DEBUG] Task completed, marking all remaining phases as completed (count: {phase_count})"
                            )

                            # 标记所有阶段为完成
                            for idx in range(1, phase_count + 1):
                                phase_id = f"phase_{idx}"
                                yield format_sse(
                                    {
                                        "type": "phase_update",
                                        "phase_id": phase_id,
                                        "status": "completed",
                                    }
                                )
                                logger.info(f"[DEBUG] Marked {phase_id} as completed")

                            # 也标记 summary 阶段为完成
                            yield format_sse(
                                {
                                    "type": "phase_update",
                                    "phase_id": "phase_summary",
                                    "status": "completed",
                                }
                            )
                            logger.info(f"[DEBUG] Marked phase_summary as completed")

                            yield format_sse({"type": "file_update", "sid": sid})
                        break

                    # Heartbeat
                    if asyncio.get_running_loop().time() - last_activity > 15:
                        yield format_sse(
                            {
                                "type": "ping",
                                "timestamp": str(asyncio.get_running_loop().time()),
                            }
                        )
                        last_activity = asyncio.get_running_loop().time()
                    continue

        finally:
            session_manager.detach(sid, queue)
            yield format_sse({"type": "status", "value": "done"})

    return event_generator


def map_tool_to_type(tool_name: str) -> str:
    """Map internal tool names to frontend display types"""
    tool = tool_name.lower()

    if "read" in tool:
        return "read"
    if "write" in tool or "save" in tool or "create" in tool:
        return "write"
    if "bash" in tool or "sh" == tool or "shell" in tool:
        return "bash"
    if "terminal" in tool or "command" in tool or "cmd" in tool or "run" in tool:
        return "terminal"
    if (
        "grep" in tool
        or "search" in tool
        and "web" not in tool
        and "google" not in tool
    ):
        return "grep"
    if "browser" in tool or "click" in tool or "visit" in tool or "scroll" in tool:
        return "browser"
    if "web" in tool or "google" in tool:
        return "web_search"
    if "edit" in tool or "replace" in tool:
        return "file_editor"

    return "file_editor"  # Default fallback


async def process_log_line(text: str, sid: str = None):
    # MARKER: 追踪函数调用
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    logger.info(
        f"[MARKER] process_log_line called - text_length={len(text)}, sid={sid}"
    )
    sys.stdout.flush()
    sys.stderr.flush()

    # ========================================================================
    # 检测 "Session started: {actual_sid}" 并建立映射关系
    # ========================================================================
    session_match = re.search(r"Session started:\s+(\S+)", text, re.IGNORECASE)
    if session_match:
        actual_sid = session_match.group(1)
        if actual_sid != sid:
            # OpenCode 生成了自己的 session ID，建立映射
            _session_id_map[sid] = actual_sid
            _reverse_session_id_map[actual_sid] = sid
            logger.info(
                f"[SESSION MAP] Mapped frontend_sid={sid} -> actual_sid={actual_sid}"
            )
    # ========================================================================

    # Try to parse as JSON if it looks like one
    if text.startswith("{") and text.endswith("}"):
        try:
            event = json.loads(text)
            event_type = event.get("type")

            # ====================================================================
            # 检测 todowrite 事件，动态生成执行阶段
            # ====================================================================
            if (
                event_type == "tool_use"
                and event.get("part", {}).get("tool") == "todowrite"
            ):
                logger.info(f"[DEBUG] Processing todowrite event for sid: {sid}")
                logger.info(
                    f"[DEBUG] _phases_initialized.get(sid): {_phases_initialized.get(sid, False)}"
                )

                part = event.get("part", {})
                state = part.get("state", {})
                input_data = state.get("input", {})
                todos = input_data.get("todos", [])

                logger.info(f"[DEBUG] Found {len(todos)} todos in todowrite")

                if todos:
                    # 第一次 todowrite：发送完整的 phases_init（包含总结阶段）
                    if not _phases_initialized.get(sid, False):
                        # 将 todowrite 的 todos 转换为 phases
                        phases = []
                        for idx, todo in enumerate(todos, 1):
                            phases.append(
                                {
                                    "id": f"phase_{idx}",
                                    "number": idx,
                                    "title": todo.get("content", f"Step {idx}"),
                                    "status": todo.get("status", "pending"),
                                }
                            )

                        # 添加固定的"总结"阶段作为最后一个阶段
                        phases.append(
                            {
                                "id": "phase_summary",
                                "number": len(todos) + 1,
                                "title": "📝 总结生成内容",
                                "status": "pending",
                            }
                        )

                        logger.info(
                            f"[DEBUG] Generated {len(phases)} phases from todowrite (including summary)"
                        )
                        logger.info(f"[DEBUG] Phase IDs: {[p['id'] for p in phases]}")

                        event_data = {"type": "phases_init", "phases": phases}
                        logger.info(f"[DEBUG] Sending phases_init event: {event_data}")
                        yield format_sse(event_data)

                        _phases_initialized[sid] = True
                        # 记录初始阶段数量（不包括 summary 阶段）
                        _phase_counts[sid] = len(todos)
                        logger.info(
                            f"[DEBUG] Set _phases_initialized[{sid}] = True, _phase_counts[{sid}] = {len(todos)}"
                        )
                    else:
                        # 后续 todowrite：只更新对应 phase 的状态
                        logger.info(
                            f"[DEBUG] Updating existing phases (already initialized)"
                        )

                        # 获取之前记录的阶段数量（如果有的话）
                        previous_phase_count = _phase_counts.get(sid, len(todos))

                        # 更新当前批次的阶段状态
                        for idx, todo in enumerate(todos, 1):
                            phase_id = f"phase_{idx}"
                            status = todo.get("status", "pending")
                            event_data = {
                                "type": "phase_update",
                                "phase_id": phase_id,
                                "status": status,
                            }
                            logger.info(f"[DEBUG] Sending phase_update: {event_data}")
                            yield format_sse(event_data)

                        # 如果新的 todos 数量比之前的少，说明 Agent 合并了任务
                        # 需要把"消失"的那些旧阶段标记为 completed
                        if len(todos) < previous_phase_count:
                            logger.info(
                                f"[DEBUG] Agent merged tasks: {previous_phase_count} -> {len(todos)}"
                            )
                            logger.info(
                                f"[DEBUG] Marking phases {len(todos)+1} to {previous_phase_count} as completed"
                            )
                            for idx in range(len(todos) + 1, previous_phase_count + 1):
                                phase_id = f"phase_{idx}"
                                event_data = {
                                    "type": "phase_update",
                                    "phase_id": phase_id,
                                    "status": "completed",
                                }
                                logger.info(
                                    f"[DEBUG] Auto-completed merged phase: {event_data}"
                                )
                                yield format_sse(event_data)

                        # 更新记录的阶段数量
                        _phase_counts[sid] = len(todos)
                        logger.info(
                            f"[DEBUG] Updated {len(todos)} phase statuses from todowrite"
                        )
                else:
                    logger.warning(f"[DEBUG] No todos found in todowrite event!")

            if event_type == "step_start" or event_type == "step-start":
                # 激活第一个 pending 状态的 phase（如果有动态阶段）
                # 这里不需要额外发送，前端会自动管理
                pass

            elif event_type == "step_finish" or event_type == "step-finish":
                # 检查是否有 reasoning tokens，如果有则生成思考事件
                part = event.get("part", {})

                # tokens 可能在多个位置：
                # 1. event.tokens (直接在事件中)
                # 2. event.part.tokens (在 part 中)
                tokens = event.get("tokens", {}) or part.get("tokens", {})

                reasoning_tokens = tokens.get("reasoning", 0)

                # 禁用简单的token计数思考事件，用户需要更有意义的思考内容
                # 如果有 reasoning tokens，生成一个思考事件
                # if reasoning_tokens > 0:
                #     thought_content = f"AI 进行了 {reasoning_tokens} 个 tokens 的推理思考"
                #     yield format_sse({
                #         "type": "tool_event",
                #         "data": {
                #             "type": "thought",
                #             "content": thought_content,
                #             "reasoning_tokens": reasoning_tokens
                #         }
                #     })
                #     logger.info(f"Generated synthetic thought event: {reasoning_tokens} reasoning tokens")

            elif event_type == "tool_use":
                part = event.get("part", {})
                tool_name = part.get("tool", "unknown")
                state = part.get("state", {})
                status = state.get("status")
                output = state.get("output", "")
                input_data = part.get("input", {})

                # 跳过 todowrite，因为已经在上面处理过了
                if tool_name != "todowrite":
                    # ================================================================
                    # 历史追踪：捕获工具使用
                    # ================================================================
                    step_id = str(uuid.uuid4())
                    capture_result = None

                    if history_service and sid:
                        try:
                            capture_result = await history_service.capture_tool_use(
                                session_id=sid,
                                tool_name=tool_name,
                                tool_input=input_data,
                                step_id=step_id,
                            )
                        except Exception as e:
                            logger.error(f"Failed to capture tool use: {e}")

                    # 文件操作：发送预览事件（不依赖 history_service）
                    if tool_name in ["write", "edit", "file_editor"]:
                        file_path = input_data.get(
                            "file_path"
                        ) or input_data.get("path", "")
                        content = input_data.get("content", "")

                        # 确定 action_type（优先使用 capture_result，否则回退到默认值）
                        action_type = "write" if tool_name == "write" else "edit"
                        if capture_result:
                            action_type = capture_result.get("action_type", action_type)

                        logger.info(
                            f"[PREVIEW] Sending preview_start for {tool_name}: {file_path}"
                        )
                        logger.info(
                            f"[PREVIEW] Content length: {len(content)} chars"
                        )
                        logger.info(
                            f"[PREVIEW] Action type: {action_type}"
                        )

                        # 预览开始
                        yield format_sse(
                            {
                                "type": "preview_start",
                                "step_id": step_id,
                                "file_path": file_path,
                                "action": action_type,
                            }
                        )

                        # 流式推送内容（打字机效果）
                        if content:
                            logger.info(
                                f"[PREVIEW] Starting typewriter effect with {len(content)} chars"
                            )
                            for i, char in enumerate(content):
                                yield format_sse(
                                    {
                                        "type": "preview_delta",
                                        "step_id": step_id,
                                        "delta": {
                                            "type": "insert",
                                            "position": i,
                                            "content": char,
                                        },
                                    }
                                )
                                await asyncio.sleep(0.005)  # 打字机速度
                            logger.info(
                                f"[PREVIEW] Typewriter effect completed"
                            )

                        # 预览结束
                        yield format_sse(
                            {
                                "type": "preview_end",
                                "step_id": step_id,
                                "file_path": file_path,
                            }
                        )

                        # 保存快照（如果 history_service 可用）
                        if history_service:
                            try:
                                await history_service.capture_file_change(
                                    step_id=step_id,
                                    file_path=file_path,
                                    content=content,
                                    operation_type=(
                                        "created"
                                        if tool_name == "write"
                                        else "modified"
                                    ),
                                )
                            except Exception as e:
                                logger.error(f"Failed to capture file change: {e}")

                    # 时间轴更新
                    if capture_result:
                        yield format_sse(
                            {
                                "type": "timeline_update",
                                "step": {
                                    "step_id": capture_result["step_id"],
                                    "action": capture_result["action_type"],
                                    "path": capture_result["file_path"],
                                    "timestamp": capture_result["timestamp"],
                                },
                            }
                        )

                    # Map to standard type
                    display_type = map_tool_to_type(tool_name)

                    # Send as tool_event for the enhanced panel
                    yield format_sse(
                        {
                            "type": "tool_event",
                            "data": {
                                "type": "tool",  # Keep generic 'tool' type for frontend logic
                                "tool": display_type,  # Use mapped type as tool name for icon lookup
                                "status": status,
                                "output": output,
                            },
                        }
                    )

                    # If there's output, also send it as a chunk for visibility
                    if output:
                        display_text = f"
`{tool_name}` output:
{output}
"
                        yield format_sse({"type": "answer_chunk", "text": display_text})

            elif event_type == "text":
                chunk = event.get("part", {}).get("text", "")
                if chunk:
                    yield format_sse({"type": "answer_chunk", "text": chunk})

            elif event_type == "error":
                err_msg = event.get("message", "Unknown error")
                yield format_sse(
                    {
                        "type": "tool_event",
                        "data": {"type": "error", "content": err_msg},
                    }
                )

            return
        except Exception as json_err:
            pass

    # Fallback text parsing for Thought and other non-JSON markers
    thought_match = re.search(
        r"(?:🤔\s*Thought:|Thought:|Thought\s*>\s*|思考[:：])\s*(.*)",
        text,
        re.IGNORECASE,
    )
    if thought_match:
        content = thought_match.group(1).strip()
        if content:
            yield format_sse(
                {"type": "tool_event", "data": {"type": "thought", "content": content}}
            )
            # 使用 phase_id 而不是 number
            yield format_sse(
                {"type": "phase_update", "phase_id": "phase_2", "status": "active"}
            )
        return

    if not text.startswith("{"):
        # Skip help messages, options, or other noise
        noise_keywords = [
            "opencode run",
            "options:",
            "positionals:",
            "message  message to send",
            "run opencode with",
        ]
        if not any(x in text.lower() for x in noise_keywords):
            yield format_sse({"type": "answer_chunk", "text": text + " "})


@app.get("/opencode/run_sse")
async def run_sse(prompt: str, sid: str | None = None, mode: str = "auto"):
    if not sid:
        sid = str(uuid.uuid4())
    generator_func = await run_agent(prompt, sid, mode)
    return StreamingResponse(generator_func(), media_type="text/event-stream")


# ================================================================
# 历史查询 API 端点
# ================================================================


@app.get("/opencode/get_file_at_step")
async def get_file_at_step(session_id: str, file_path: str, step_id: str):
    """获取指定步骤时刻的文件内容"""
    if not history_service:
        raise HTTPException(status_code=503, detail="History service not available")

    content = await history_service.get_file_at_step(
        session_id=session_id, file_path=file_path, target_step_id=step_id
    )

    if content is None:
        raise HTTPException(status_code=404, detail="File not found at this step")

    return {"content": content, "file_path": file_path, "step_id": step_id}


@app.get("/opencode/get_timeline")
async def get_timeline(session_id: str):
    """获取会话的完整时间轴"""
    if not history_service:
        raise HTTPException(status_code=503, detail="History service not available")

    timeline = await history_service.get_timeline(session_id)
    return {"timeline": timeline}


@app.get("/opencode/get_step_info")
async def get_step_info(step_id: str):
    """获取单个步骤的详细信息"""
    if not history_service:
        raise HTTPException(status_code=503, detail="History service not available")

    # 这里需要在 history_service 中添加相应方法
    # 暂时返回基本信息
    return {"step_id": step_id, "message": "Step info retrieval not fully implemented"}
