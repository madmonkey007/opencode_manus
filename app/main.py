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
import sys
import sqlite3
import time

# Import from managers_internal module to avoid circular imports
from app.managers_internal import get_opencode_server_manager

# Fix Windows encoding issue
if sys.platform == "win32":
    import locale
    try:
        # Try to set UTF-8 encoding
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        # Fallback for older Python versions
        pass

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

# 数据库初始化函数
def init_database():
    """初始化数据库表结构"""
    db_path = os.path.join(WORKSPACE_BASE, "history.db")

    # ✅ 修复：使用 context manager 确保连接总是关闭
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # 创建sessions表（包含Python和Go CLI两套列）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    prompt TEXT,
                    status TEXT,
                    workspace_path TEXT,
                    -- Go CLI兼容列
                    title TEXT,
                    message_count INTEGER DEFAULT 0,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    -- 时间戳
                    created_at INTEGER,
                    updated_at INTEGER
                )
            """)

            # 创建messages表（与 history_service.py 保持一致，使用 message_id 列名）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)

            conn.commit()

        logger.info(f"[DB] Database initialized at {db_path}")

    except Exception as e:
        logger.error(f"[DB] Failed to initialize database: {e}")
        raise

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

# ====================================================================
# 应用启动事件：初始化数据库
# ====================================================================
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    logger.info("[Startup] Initializing database...")
    init_database()
    logger.info("[Startup] Database initialization complete")

# CORS配置：从环境变量读取允许的来源
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8999").split(",")
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin"
    ],
)

# 导入提示词增强模块
from .prompt_enhancer import enhance_prompt

# 导入 OpenCode 服务器管理器（懒加载）
# 不在模块导入时初始化，避免阻塞主线程
from .server_manager import OpenCodeServerManager

# 懒加载：只在首次使用时才创建实例
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
    DB_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "../workspace")), "history.db")
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
        now = int(time.time())
        # ✅ 修复：如果prompt是"New Session"（API创建时的默认值），使用空字符串作为title
        # 这样Go CLI查询时不会因为title为NULL而失败
        if prompt == "New Session":
            title = ""
        else:
            title = prompt[:100] if len(prompt) > 100 else prompt

        # ✅ 修复：使用 context manager 确保连接总是关闭
        try:
            with sqlite3.connect(self.db_path) as conn:
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
                """, (sid, prompt, "running", os.path.join(self.db_path.replace("history.db", ""), sid),
                       title, now, now))

                conn.commit()

            logger.info(f"[DB] Session {sid} written to database (dual-schema compatible)")
        except sqlite3.IntegrityError as e:
            # Session ID已存在，更新时间戳
            logger.warning(f"[DB] Session {sid} already exists, updating timestamp")
            try:
                now = int(time.time())
                # ✅ 修复：使用 context manager 确保连接总是关闭
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, sid))
                    conn.commit()
            except Exception as e2:
                logger.error(f"[DB] Failed to update session {sid}: {e2}")
        except Exception as e:
            logger.error(f"[DB] Failed to write session {sid} to database: {e}")
            # traceback已在顶部导入，无需重复导入

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
        # 路径A已废弃：任务执行由 api.py send_message() → opencode_client.py 负责。
        # _run_process 只初始化状态文件，不执行任务、不轮询、不广播事件。
        session_dir = os.path.join(WORKSPACE_BASE, sid)
        os.makedirs(session_dir, exist_ok=True)
        try:
            with open(os.path.join(session_dir, "run.log"), "w", encoding="utf-8") as f:
                f.write(f"Session started: {sid}\n")
            with open(os.path.join(session_dir, "status.txt"), "w", encoding="utf-8") as f:
                f.write("running")
            if sid in self.sessions:
                self.sessions[sid]["status"] = "running"
            logger.info(f"[_run_process] Session {sid} initialized (task handled by opencode_client)")
        except Exception as e:
            logger.error(f"[_run_process] Failed to initialize session {sid}: {e}")

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
                        if not line:
                            continue
                        
                        # ✅ 健壮过滤：只处理合法的JSON事件数据
                        # 问题：run.log混合了系统纯文本日志和JSON事件
                        # 影响：非JSON日志被前端强行解析，导致显示污染
                        # 修复：尝试解析JSON，只发送合法的事件
                        try:
                            parsed = json.loads(line)  # ✅ 使用顶部导入的json
                            # 只有包含必要事件字段的才发送
                            if any(field in parsed for field in ("type", "event", "message_type")):
                                async for event in process_log_line(line, sid):
                                    yield event
                            else:
                                logger.debug(f"[Catch-up] Filtered non-event JSON: {line}")
                        except json.JSONDecodeError:
                            # 忽略所有非JSON格式的纯文本日志
                            logger.debug(f"[Catch-up] Filtered non-JSON log: {line}")
                            continue
            except Exception as e:
                logger.error(f"Error reading history: {e}")

        # Stream new events
        last_activity = asyncio.get_running_loop().time()

        try:
            while True:
                try:
                    text = await asyncio.wait_for(queue.get(), timeout=5.0)
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
                            # ✅ 发送 session.idle 信号，让前端 patch.js 知道任务完成
                            yield format_sse({"type": "session.idle", "properties": {"sessionID": sid}})
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
                        # ⚠️ 路径A已废弃：preview 事件现在由 opencode_client.py _maybe_broadcast_preview() 负责。
                        # 此处代码仅保留注释，不再执行，防止重复 preview。
                        # file_path = str(input_data.get("file_path") or input_data.get("path") or ...)
                        # yield format_sse({"type": "preview_start", ...})
                        # yield format_sse({"type": "preview_delta", ...})
                        # yield format_sse({"type": "preview_end", ...})
                        pass

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

            # ✅ 修复：删除text事件处理，避免与opencode_client.py重复广播
            # 问题：opencode_client.py已经正确发送了text事件的增量
            # 影响：main.py再次发送完整文本，导致"52"+"52"="5252"
            # 修复：注释掉以下代码，只让opencode_client.py负责text事件
            # elif event_type == "text":
            #     chunk = event.get("part", {}).get("text", "")
            #     if chunk: yield format_sse({"type": "answer_chunk", "text": chunk})

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

    # ✅ 修复：删除普通文本处理，防止日志文件中的调试信息被误当作answer_chunk发送
    # 原因：日志文件包含 "Session started: ses_xxx" 和其他初始化信息
    # 问题：process_log_line 会读取日志文件的每一行，并将所有非JSON、非噪音的行作为 answer_chunk 发送
    # 影响：前端显示 "Session started" 和 HTML 代码，而不是 AI 的真实回答
    # 解决：普通文本已经在 Line 443-445 通过队列正确处理了，这里不应该重复发送
    # 
    # 注释掉以下代码：
    # if not text.startswith("{"):
    #     noise_keywords = ["opencode run", "options:", "positionals:", "message", "run opencode with"]
    #     if not any(x in text.lower() for x in noise_keywords):
    #         yield format_sse({"type": "answer_chunk", "text": text + " "})


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("[Shutdown] Cleaning up resources...")
    try:
        # Cleanup ServerManager
        from app.managers_internal import cleanup_opencode_server_manager
        await cleanup_opencode_server_manager()
        logger.info("[Shutdown] ServerManager cleanup complete")
    except Exception as e:
        logger.error(f"[Shutdown] Error during cleanup: {e}")
    logger.info("[Shutdown] Cleanup complete")

@app.get("/opencode/run_sse")
async def run_sse(prompt: str, sid: str | None = None, mode: str = "auto"):
    if not sid: sid = str(uuid.uuid4())
    generator_func = await run_agent(prompt, sid, mode)
    if not generator_func: raise HTTPException(status_code=500, detail="Failed to initialize session")
    return StreamingResponse(generator_func(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    # Configure graceful shutdown
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8089,
        reload=False,
        log_level="info",
        timeout_graceful_shutdown=30  # 30秒优雅关闭超时
    )
    server = uvicorn.Server(config)

    logger.info("[Main] Starting uvicorn server with graceful shutdown support...")
    server.run()
