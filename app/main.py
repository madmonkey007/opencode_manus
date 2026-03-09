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

# 导入 OpenCode 服务器管理器（懒加载）
# 不在模块导入时初始化，避免阻塞主线程
from .server_manager import OpenCodeServerManager

# 懒加载：只在首次使用时才创建实例
_opencode_server_manager: Optional[OpenCodeServerManager] = None
_manager_lock = asyncio.Lock()

async def get_opencode_server_manager() -> OpenCodeServerManager:
    """
    懒加载 OpenCodeServerManager

    使用 Lock 确保线程安全，避免竞态条件
    """
    global _opencode_server_manager

    if _opencode_server_manager is None:
        async with _manager_lock:
            if _opencode_server_manager is None:
                try:
                    logger.info("Initializing OpenCodeServerManager (lazy load)...")
                    _opencode_server_manager = OpenCodeServerManager()
                    logger.info("OpenCodeServerManager initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize OpenCodeServerManager: {e}", exc_info=True)
                    raise RuntimeError("Failed to initialize OpenCode server manager") from e

    return _opencode_server_manager

# Workspace setup
WORKSPACE_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../workspace")
)
os.makedirs(WORKSPACE_BASE, exist_ok=True)

# Project root for package.json
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

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


@app.get("/package.json")
async def get_package_json():
    """提供根目录下的 package.json 以解决前端 404 问题"""
    path = os.path.join(PROJECT_ROOT, "package.json")
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(content={"version": "1.0.0", "name": "opencode"}, status_code=200)


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

        # Check if process is still running
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
    """会话管理器，负责管理OpenCode会话的生命周期和持久化"""

    # 常量定义
    DB_PATH = "/app/opencode/workspace/history.db"  # ✅ 与Go CLI保持一致
    SESSION_ID_PREFIX = "ses_"
    SESSION_ID_LENGTH = 9

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.db_path = self.DB_PATH

    def _write_session_to_db(self, sid: str, prompt: str):
        """
        ✅ v=38.4.2修复：将session写入数据库，同时兼容Python和Go CLI的schema

        修复说明：
        1. 数据库路径统一为 /app/opencode/workspace/history.db
        2. 同时填充旧列（prompt, status, workspace_path）和新列（title, message_count等）
        3. 使用Unix时间戳与Go CLI保持一致

        Schema兼容性：
        - Python使用: prompt, status, workspace_path
        - Go CLI使用: title, message_count, prompt_tokens, completion_tokens, cost
        - 修复方案：同时写入两组列，确保兼容性
        """
        try:
            import sqlite3
            import time

            now = int(time.time())
            # ✅ 修复：如果prompt是"New Session"（API创建时的默认值），使用空字符串作为title
            # 这样Go CLI查询时不会因为title为NULL而失败
            if prompt == "New Session":
                title = ""
            else:
                title = prompt[:100] if len(prompt) > 100 else prompt

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # ✅ 同时填充旧列和新列，确保兼容性
            cursor.execute("""
                INSERT INTO sessions (
                    -- 旧列（Python使用）
                    id, prompt, status, workspace_path,
                    -- 新列（Go CLI使用）
                    title, message_count, prompt_tokens, completion_tokens, cost,
                    -- 时间戳
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0.0, ?, ?)
            """, (sid, prompt, "running", f"/app/opencode/workspace/{sid}",
                   title, now, now))

            conn.commit()
            conn.close()

            logger.info(f"[DB] Session {sid} written to database (dual-schema compatible)")
        except sqlite3.IntegrityError as e:
            # Session ID已存在，更新时间戳
            logger.warning(f"[DB] Session {sid} already exists, updating timestamp")
            try:
                import time
                now = int(time.time())
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, sid))
                conn.commit()
                conn.close()
            except Exception as e2:
                logger.error(f"[DB] Failed to update session {sid}: {e2}")
        except Exception as e:
            logger.error(f"[DB] Failed to write session {sid} to database: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def create_session(self, sid: str, prompt: str, mode: str = "auto"):
        if sid in self.sessions:
            return self.sessions[sid]

        # 1. 写入数据库（让Go CLI可以查询）
        self._write_session_to_db(sid, prompt)

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
            logger.info(f"Enhancing prompt with mode: {mode}")
            enhanced_prompt = enhance_prompt(prompt, mode)

            # ✅ 新方案：使用 OpenCodeServerManager 的 HTTP API（懒加载）
            logger.info(f"Using OpenCodeServerManager (lazy load) for session {sid}")

            # 获取管理器实例（首次请求时才会启动服务器）
            manager = await get_opencode_server_manager()

            # 更新会话状态
            if sid in self.sessions:
                self.sessions[sid]["status"] = "running"

            # 发送 HTTP 请求执行任务
            logger.info(f"Executing task via HTTP API: {mode}")
            result = await manager.execute(
                session_id=sid,
                prompt=enhanced_prompt,
                mode=mode
            )

            # 写入结果到日志
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(result + "\n")

            # 广播结果到队列（保持与原代码一致的接口）
            if sid in self.sessions:
                for q in self.sessions[sid]["queues"]:
                    await q.put(result)

            with open(status_file, "w", encoding="utf-8") as f:
                f.write("completed")

            if sid in self.sessions:
                self.sessions[sid]["status"] = "completed"

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

# SSE tracking flags
_phases_initialized = {}
_phase_counts = {}
_session_id_map = {}
_reverse_session_id_map = {}


async def run_agent(prompt: str, sid: str, mode: str = "auto"):
    """
    Bridge to the official opencode CLI with SSE extensions
    """
    session_dir = os.path.join(WORKSPACE_BASE, sid)

    # Ensure session exists - 传递mode参数
    await session_manager.create_session(sid, prompt, mode)

    # Attach listener
    queue = await session_manager.attach(sid)
    if not queue:
        return None

    # 保存mode到session数据中
    if sid in session_manager.sessions:
        session_manager.sessions[sid]["mode"] = mode

    async def event_generator():
        logger.info(f"Agent session attached: {sid}")

        _phases_initialized[sid] = False
        if sid in _phase_counts:
            del _phase_counts[sid]

        yield format_sse(
            {
                "type": "status",
                "value": "thinking",
                "message": "正在分析任务并制定计划..."
            }
        )

        # Catch-up from log file
        log_file = os.path.join(session_dir, "run.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            async for event in process_log_line(line, sid):
                                yield event
            except Exception as e:
                logger.error(f"Error reading history: {e}")

        # Stream new events
        last_activity = asyncio.get_running_loop().time()

        try:
            while True:
                try:
                    text = await asyncio.wait_for(queue.get(), timeout=1.0)
                    last_activity = asyncio.get_running_loop().time()

                    async for event in process_log_line(text, sid):
                        yield event

                except asyncio.TimeoutError:
                    session = session_manager.sessions.get(sid)
                    if (
                        session
                        and session["status"] in ["completed", "error"]
                        and queue.empty()
                    ):
                        if session["status"] == "completed":
                            phase_count = _phase_counts.get(sid, 0)
                            for idx in range(1, phase_count + 1):
                                yield format_sse({"type": "phase_update", "phase_id": f"phase_{idx}", "status": "completed"})
                            yield format_sse({"type": "phase_update", "phase_id": "phase_summary", "status": "completed"})
                            yield format_sse({"type": "file_update", "sid": sid})
                        break

                    if asyncio.get_running_loop().time() - last_activity > 15:
                        yield format_sse({"type": "ping", "timestamp": str(asyncio.get_running_loop().time())})
                        last_activity = asyncio.get_running_loop().time()
                    continue

        finally:
            session_manager.detach(sid, queue)
            yield format_sse({"type": "status", "value": "done"})

    return event_generator


def map_tool_to_type(tool_name: str) -> str:
    """Map tool names to frontend icons"""
    tool = tool_name.lower()
    if "read" in tool: return "read"
    if any(x in tool for x in ["write", "create", "save"]): return "write"
    if any(x in tool for x in ["bash", "sh", "terminal", "run"]): return "bash"
    if any(x in tool for x in ["grep", "search"]): return "grep"
    if any(x in tool for x in ["browser", "web"]): return "browser"
    if any(x in tool for x in ["edit", "patch", "file_editor"]): return "file_editor"
    return "file_editor"


async def process_log_line(text: str, sid: str = None):
    """
    解析日志行并生成 SSE 事件
    """
    # Session ID mapping
    session_match = re.search(r"Session started:\s+(\S+)", text, re.IGNORECASE)
    if session_match:
        actual_sid = session_match.group(1)
        if sid and actual_sid != sid:
            _session_id_map[sid] = actual_sid
            _reverse_session_id_map[actual_sid] = sid

    if text.startswith("{") and text.endswith("}"):
        try:
            event = json.loads(text)
            event_type = event.get("type")

            # Handle todowrite (Planning)
            if event_type == "tool_use" and event.get("part", {}).get("tool") == "todowrite":
                part = event.get("part", {})
                state = part.get("state", {})
                input_data = state.get("input", {}) or part.get("input", {})
                todos = input_data.get("todos", [])

                if todos:
                    if not _phases_initialized.get(sid, False):
                        phases = []
                        for idx, todo in enumerate(todos, 1):
                            phases.append({
                                "id": f"phase_{idx}",
                                "number": idx,
                                "title": todo.get("content", f"Step {idx}"),
                                "status": todo.get("status", "pending"),
                            })
                        phases.append({"id": "phase_summary", "number": len(todos) + 1, "title": "📝 总结生成内容", "status": "pending"})
                        yield format_sse({"type": "phases_init", "phases": phases})
                        _phases_initialized[sid] = True
                        _phase_counts[sid] = len(todos)
                    else:
                        for idx, todo in enumerate(todos, 1):
                            yield format_sse({"type": "phase_update", "phase_id": f"phase_{idx}", "status": todo.get("status", "pending")})
                        prev_count = _phase_counts.get(sid, len(todos))
                        if len(todos) < prev_count:
                            for idx in range(len(todos) + 1, prev_count + 1):
                                yield format_sse({"type": "phase_update", "phase_id": f"phase_{idx}", "status": "completed"})
                        _phase_counts[sid] = len(todos)

            # Handle file operation previews
            elif event_type == "tool_use":
                part = event.get("part", {})
                tool_name = part.get("tool", "unknown")
                state = part.get("state", {})
                status = state.get("status")
                output = state.get("output", "")
                input_data = part.get("input", {})

                if tool_name != "todowrite":
                    step_id = str(uuid.uuid4())
                    capture_result = None

                    # 获取当前会话的mode
                    current_mode = "auto"
                    if sid in session_manager.sessions:
                        current_mode = session_manager.sessions[sid].get("mode", "auto")
                    elif sid in _session_id_map:
                        mapped_sid = _session_id_map[sid]
                        if mapped_sid in session_manager.sessions:
                            current_mode = session_manager.sessions[mapped_sid].get("mode", "auto")

                    if history_service and sid:
                        capture_result = await history_service.capture_tool_use(sid, tool_name, input_data, step_id, current_mode)

                    if tool_name in ["write", "edit", "file_editor", "patch"]:
                        # 改进：识别多种路径和内容键名
                        file_path = str(input_data.get("file_path") or input_data.get("path") or input_data.get("filePath") or "")
                        content = input_data.get("content") or input_data.get("newString") or ""
                        action_type = "write" if tool_name == "write" else "edit"
                        
                        yield format_sse({"type": "preview_start", "step_id": step_id, "file_path": file_path, "action": action_type})
                        
                        if content:
                            # 批量推送以防止 SSE 拥塞
                            chunk_size = 100
                            for i in range(0, len(content), chunk_size):
                                chunk = content[i:i+chunk_size]
                                yield format_sse({"type": "preview_delta", "step_id": step_id, "delta": {"type": "insert", "position": i, "content": chunk}})
                                await asyncio.sleep(0.03)  # ✅ 修复：从5ms增加到30ms，让用户能看到逐步显示效果
                        
                        yield format_sse({"type": "preview_end", "step_id": step_id, "file_path": file_path})

                    if capture_result:
                        yield format_sse({"type": "timeline_update", "step": {"step_id": step_id, "action": capture_result.get("action_type"), "path": capture_result.get("file_path"), "timestamp": capture_result.get("timestamp")}})

                    display_type = map_tool_to_type(tool_name)
                    yield format_sse({"type": "tool_event", "data": {"type": "tool", "tool": display_type, "status": status, "output": output}})
                    if output:
                        yield format_sse({"type": "answer_chunk", "text": f"\n`{tool_name}` output:\n{output}\n"})

                    # ✅ v=38.2长期方案：直接保存tool part到message_parts表
                    if history_service and sid:
                        try:
                            # 使用session_id作为message_id（简化方案）
                            assistant_message_id = f"msg_{sid}"

                            # 先保存message（如果不存在）
                            await history_service.save_message(sid, assistant_message_id, "assistant")

                            # 保存tool part
                            part_dict = {
                                "id": f"part_{step_id}",
                                "type": "tool",
                                "content": {
                                    "tool": tool_name,
                                    "tool_name": display_type,
                                    "call_id": step_id,
                                    "state": {
                                        "status": status,
                                        "output": output
                                    },
                                    "input": input_data,
                                    "output": output,
                                    "text": output
                                }
                            }
                            success = await history_service.save_part(sid, assistant_message_id, part_dict)
                            if success:
                                # ✅ P1-2修复：数据库保存是重要业务操作，使用info级别
                                logger.info(f"Saved tool part to DB: {tool_name} for session {sid}")
                        except Exception as save_err:
                            logger.warning(f"Failed to save tool part for {sid}: {save_err}")

            elif event_type == "text":
                chunk = event.get("part", {}).get("text", "")
                if chunk: yield format_sse({"type": "answer_chunk", "text": chunk})

            elif event_type == "error":
                yield format_sse({"type": "tool_event", "data": {"type": "error", "content": event.get("message", "Unknown error")}})

            return
        except Exception: pass

    # Fallback Thought parsing
    thought_match = re.search(r"(?:🤔\s*Thought:|Thought:|思考[:：])\s*(.*)", text, re.IGNORECASE)
    if thought_match:
        content = thought_match.group(1).strip()
        if content: yield format_sse({"type": "tool_event", "data": {"type": "thought", "content": content}})
        return

    if not text.startswith("{"):
        noise_keywords = ["opencode run", "options:", "positionals:", "message", "run opencode with"]
        if not any(x in text.lower() for x in noise_keywords):
            yield format_sse({"type": "answer_chunk", "text": text + " "})


@app.get("/opencode/run_sse")
async def run_sse(prompt: str, sid: str | None = None, mode: str = "auto"):
    if not sid: sid = str(uuid.uuid4())
    generator_func = await run_agent(prompt, sid, mode)
    if not generator_func: raise HTTPException(status_code=500, detail="Failed to initialize session")
    return StreamingResponse(generator_func(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8089,
        reload=False,
        log_level="info"
    )
