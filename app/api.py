"""
OpenCode 新架构 API 端点

基于官方 Web API 的 Session + Message 架构
提供真正的多轮对话支持
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from typing import List, Optional, Dict, Any
import asyncio
import json
import logging
import os
import sqlite3  # ✅ P1-3修复：导入sqlite3用于细化异常处理
from .models import MessageTime
import time
from datetime import datetime
import sys

# 将当前目录添加到 sys.path 以确保导入正常
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入数据模型
try:
    from .models import (
        Session,
        SessionStatus,
        Message,
        MessageRole,
        MessageWithParts,
        SendMessageRequest,
        SendMessageResponse,
        SessionEvent,
        Part,
        PartType,
        PartTime,
        PartContent,
        generate_part_id,
        generate_message_id,
    )
    from .managers import SessionManager
except ImportError:
    from models import (
        Session,
        SessionStatus,
        Message,
        MessageRole,
        MessageWithParts,
        SendMessageRequest,
        SendMessageResponse,
        SessionEvent,
        Part,
        PartType,
        PartTime,
        PartContent,
        generate_part_id,
        generate_message_id,
    )
    from managers import SessionManager

logger = logging.getLogger("opencode.api")

# ====================================================================
# 全局管理器实例
# ====================================================================

session_manager = SessionManager()

# ====================================================================
# API Router
# ====================================================================

router = APIRouter(prefix="/opencode", tags=["opencode"])


# ====================================================================
# Session Management Endpoints
# ====================================================================


@router.post("/session", response_model=Session)
async def create_session(
    title: str = "New Session",
    mode: str = "auto",
    version: str = "1.0.0",
    project_id: Optional[str] = None
):
    """
    创建新会话

    Args:
        title: 会话标题
        mode: 初始模式 (plan/build/auto)
        version: API 版本
        project_id: 所属项目ID（可选，默认使用默认项目）

    Returns:
        创建的会话对象
    """
    from .history_service import get_history_service

    # 验证 project_id 是否存在（如果不是默认项目）
    if project_id and project_id != "proj_default":
        history = get_history_service()
        project = await history.get_project(project_id)
        if not project:
            raise HTTPException(status_code=400, detail=f"Project {project_id} not found")

    # 使用默认值
    project_id = project_id or "proj_default"
    try:
        # ✅ 先向 opencode server 创建 session，拿到真实 id
        # 这样前端 session id == server session id，无需两层映射
        server_session_id = None
        try:
            import httpx as _httpx
            import os as _os
            _server_url = _os.getenv("OPENCODE_SERVER_URL", "http://127.0.0.1:4096")
            _username = _os.getenv("OPENCODE_SERVER_USERNAME", "opencode")
            _password = _os.getenv("OPENCODE_SERVER_PASSWORD", "opencode-dev-2026")
            async with _httpx.AsyncClient(timeout=10) as _client:
                _resp = await _client.post(
                    f"{_server_url}/session",
                    json={"title": title},
                    auth=(_username, _password),
                )
                if _resp.status_code in (200, 201):
                    server_session_id = _resp.json().get("id")
                    logger.info(f"[create_session] Got server session id: {server_session_id}")
                else:
                    logger.warning(f"[create_session] Server returned {_resp.status_code}, will use local id")
        except Exception as _e:
            logger.warning(f"[create_session] Could not reach opencode server: {_e}, using local id")

        session = await session_manager.create_session(
            title=title, version=version, session_id=server_session_id
        )

        # 创建workspace目录
        from app.main import WORKSPACE_BASE
        import os
        session_dir = os.path.join(WORKSPACE_BASE, session.id)
        os.makedirs(session_dir, exist_ok=True)

        # 创建初始文件
        status_file = os.path.join(session_dir, "status.txt")
        with open(status_file, "w", encoding="utf-8") as f:
            f.write("created")

        log_file = os.path.join(session_dir, "run.log")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Session created: {session.id}\n")

        # 将模式存储在会话元数据中
        session.metadata["mode"] = mode
        # 存储 project_id 到会话元数据
        session.metadata["project_id"] = project_id
        session.project_id = project_id
        logger.info(f"Created session: {session.id} with mode: {mode}, project_id: {project_id}")
        logger.info(f"Workspace directory created: {session_dir}")

        return session

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """
    获取会话信息

    Args:
        session_id: 会话ID

    Returns:
        会话对象
    """
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return session


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话及其所有数据

    Args:
        session_id: 会话ID

    Returns:
        删除结果
    """
    success = await session_manager.delete_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    logger.info(f"Deleted session: {session_id}")
    return {"status": "deleted", "session_id": session_id}


@router.get("/sessions", response_model=List[Session])
async def list_sessions(status: Optional[SessionStatus] = None):
    """
    列出所有会话

    Args:
        status: 可选的状态过滤器

    Returns:
        会话列表
    """
    sessions = await session_manager.list_sessions(status=status)
    return sessions


# ====================================================================
# Project Management Endpoints
# ====================================================================

def _generate_project_id() -> str:
    """生成项目ID"""
    import uuid
    return f"proj_{uuid.uuid4().hex[:8]}"


@router.post("/project", response_model=dict)
async def create_project(name: str = "新建项目"):
    """创建项目"""
    from .history_service import get_history_service
    history = get_history_service()
    project_id = _generate_project_id()
    project = await history.create_project(project_id, name)
    logger.info(f"Created project: {project_id} - {name}")
    return project


@router.get("/projects", response_model=list)
async def list_projects():
    """获取所有项目列表"""
    from .history_service import get_history_service
    history = get_history_service()
    return await history.list_projects()


@router.get("/project/{project_id}", response_model=dict)
async def get_project(project_id: str):
    """获取项目详情"""
    from .history_service import get_history_service
    history = get_history_service()
    project = await history.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/project/{project_id}", response_model=dict)
async def update_project(project_id: str, name: str):
    """更新项目名称"""
    from .history_service import get_history_service
    history = get_history_service()
    project = await history.update_project(project_id, name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/project/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    from .history_service import get_history_service
    history = get_history_service()
    await history.delete_project(project_id)
    logger.info(f"Deleted project: {project_id}")
    return {"status": "deleted"}


@router.get("/project/{project_id}/sessions", response_model=list)
async def get_project_sessions(project_id: str):
    """获取项目下的会话列表"""
    from .history_service import get_history_service
    history = get_history_service()
    return await history.get_project_sessions(project_id)


# ====================================================================
# Session Recovery Mechanisms
# ====================================================================

# ✅ EC1: 并发恢复锁和缓存
_recovery_locks: Dict[str, bool] = {}
_recovery_cache: Dict[str, bool] = {}


async def _acquire_recovery_lock(session_id: str) -> bool:
    """获取恢复锁，防止并发恢复同一session"""
    if session_id in _recovery_locks:
        return False
    _recovery_locks[session_id] = True
    return True


def _release_recovery_lock(session_id: str):
    """释放恢复锁"""
    _recovery_locks.pop(session_id, None)


async def recover_session_from_disk(session_id: str) -> bool:
    """
    ✅ I1: 提取恢复逻辑 - 尝试从磁盘恢复session
    """
    from app.main import WORKSPACE_BASE
    session_dir = os.path.join(WORKSPACE_BASE, session_id)

    if not os.path.exists(session_dir):
        return False

    # 尝试获取锁
    if not await _acquire_recovery_lock(session_id):
        # 其他请求正在恢复，等待
        await asyncio.sleep(0.5)
        return True

    try:
        logger.info(f"[Session Recovery] Attempting to recover session {session_id} from disk")
        # ✅ 修复：使用message_store.initialize_session
        await session_manager.message_store.initialize_session(session_id)

        # 创建session对象并添加到sessions字典
        from .models import Session, SessionTime, SessionStatus
        import time as time_module  # ✅ 避免命名冲突
        recovered_session = Session(
            id=session_id,
            title=f"Recovered: {session_id}",
            version="1.0.0",
            time=SessionTime(
                created=int(time_module.time()),
                updated=int(time_module.time())
            ),
            status=SessionStatus.ACTIVE
        )
        session_manager.sessions[session_id] = recovered_session

        logger.info(f"[Session Recovery] Successfully recovered session {session_id}")
        return True
    except Exception as e:
        logger.error(f"[Session Recovery] Failed to recover {session_id}: {e}")
        return False
    finally:
        _release_recovery_lock(session_id)


# ====================================================================
# Message Management Endpoints
# ====================================================================


@router.get("/session/{session_id}/messages")
async def get_messages(session_id: str):
    """
    获取会话的所有消息历史
    """
    # ✅ S1: 路径验证 - 防止路径遍历攻击
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', session_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID format. Only alphanumeric and underscore allowed."
        )

    # 尝试从内存/数据库获取
    messages = await session_manager.get_messages(session_id)

    # 获取 history_svc 单例（后续复用，避免重复调用）
    from .history_service import get_history_service
    history_svc = get_history_service()

    # 如果内存中没有，尝试从数据库加载
    if not messages:
        # ✅ v=38.2增强：从数据库加载消息
        try:
            db_messages = await history_svc.get_session_messages(session_id)

            if db_messages:
                # ✅ 先初始化session存储
                await session_manager.message_store.initialize_session(session_id)

                # 从数据库恢复消息到内存
                from .models import Message, MessageTime, MessageRole

                for msg_data in db_messages:
                    # ✅ P0-1修复：正确解析SQLite时间戳格式
                    created_ts = msg_data['created_at']
                    if isinstance(created_ts, str):
                        # 解析SQLite时间戳格式 "YYYY-MM-DD HH:MM:SS"
                        try:
                            from datetime import datetime
                            dt = datetime.strptime(created_ts, '%Y-%m-%d %H:%M:%S')
                            created_ts = int(dt.timestamp())
                        except ValueError:
                            # 如果解析失败，使用当前时间
                            logger.warning(f"[v38.2] Failed to parse timestamp: {created_ts}, using current time")
                            created_ts = int(time.time())
                    elif created_ts is None:
                        created_ts = int(time.time())

                    msg = Message(
                        id=msg_data['id'],
                        session_id=msg_data['session_id'],
                        role=MessageRole.USER if msg_data['role'] == 'user' else MessageRole.ASSISTANT,
                        time=MessageTime(created=created_ts)
                    )
                    # ✅ 使用setdefault安全添加到SessionManager
                    session_manager.message_store.messages.setdefault(session_id, {})[msg.id] = msg
                    session_manager.message_store.message_order.setdefault(session_id, []).append(msg.id)
                    # ✅ 同时初始化parts字典（避免get_messages时的KeyError）
                    session_manager.message_store.parts.setdefault(session_id, {}).setdefault(msg.id, {})

                # 重新从内存获取
                messages = await session_manager.get_messages(session_id)
                # ✅ P1-2修复：数据库加载详情用debug级别
                logger.debug(f"[v38.2] Loaded {len(messages)} messages from database for session: {session_id}")
        # ✅ P1-3修复：细化异常处理
        except ValueError as ve:
            # 参数验证错误，不可恢复
            logger.error(f"[v38.2] Validation error loading messages: {ve}")
            raise HTTPException(status_code=400, detail=str(ve))
        except sqlite3.Error as sqlite_err:
            # 数据库错误，可恢复（返回空或尝试其他方式）
            logger.warning(f"[v38.2] Database error loading messages for {session_id}: {sqlite_err}")
        except Exception as e:
            # 未预期的错误，记录并向上抛出
            logger.error(f"[v38.2] Unexpected error loading messages: {e}", exc_info=True)
            raise  # 重新抛出让上层处理

    # 如果仍然没有，尝试从磁盘恢复
    if not messages:
        # ✅ E1: 缓存磁盘检查结果
        cache_key = f"checked:{session_id}"
        if not _recovery_cache.get(cache_key, False):
            _recovery_cache[cache_key] = True

            if await recover_session_from_disk(session_id):
                # 重新获取messages
                messages = await session_manager.get_messages(session_id)

    # 如果仍然找不到，返回404
    if not messages:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    # ✅ v=38.2增强：从数据库加载tool parts（补充内存中可能缺失的parts）
    try:
        # ✅ P1-1优化：一次性获取session的所有parts（1次查询代替N次）
        all_parts_by_message = await history_svc.get_all_parts_for_session(session_id)

        if all_parts_by_message:
            # ✅ P1-2修复：批量加载是重要优化，使用info级别
            logger.info(f"[v38.2] Batch loaded {len(all_parts_by_message)} messages with parts in 1 query")

            # 收集需要更新的消息索引
            updated_messages = []

            for idx, msg in enumerate(messages):
                message_id = msg.info.id
                db_parts = all_parts_by_message.get(message_id, [])

                if db_parts:
                    logger.debug(f"[v38.2] Message {message_id} has {len(db_parts)} parts in DB")

                    # 创建新的parts列表（复制现有parts）
                    new_parts = list(msg.parts)
                    existing_part_ids = {p.id for p in new_parts}

                    # 添加数据库中的新parts
                    for part_data in db_parts:
                        part_id = part_data.get('id')
                        if part_id and part_id not in existing_part_ids:
                            from .models import Part, PartTime, PartType, PartContent

                            # 创建Part对象
                            _ptype_str = part_data.get('type', 'text')
                            if _ptype_str == 'tool':
                                _ptype = PartType.TOOL
                            elif _ptype_str == 'thought':
                                _ptype = PartType.THOUGHT
                            else:
                                _ptype = PartType.TEXT
                            part = Part(
                                id=part_id,
                                session_id=session_id,
                                message_id=message_id,
                                type=_ptype,
                                content=PartContent(
                                    tool=part_data.get('content', {}).get('tool'),
                                    call_id=part_data.get('content', {}).get('call_id'),
                                    state=part_data.get('content', {}).get('state'),
                                    text=part_data.get('content', {}).get('text'),
                                ),
                                time=PartTime(start=int(time.time())),  # ✅ 使用顶部导入的time模块
                            )
                            new_parts.append(part)
                            existing_part_ids.add(part_id)
                            logger.debug(f"[v38.2] Loaded part from DB: {part.id} for message: {message_id}")

                    # 创建新的MessageWithParts对象
                    from .models import MessageWithParts
                    updated_msg = MessageWithParts(info=msg.info, parts=new_parts)
                    updated_messages.append((idx, updated_msg))
                    logger.info(f"[v38.2] Updated message {message_id} with {len(new_parts)} total parts")

            # 应用更新
            for idx, updated_msg in updated_messages:
                messages[idx] = updated_msg

    except Exception as db_err:
        logger.error(f"[v38.2] Failed to load parts from database for {session_id}: {db_err}", exc_info=True)

    # 同时加载 phases
    phases = []
    try:
        phases = await history_svc.get_session_phases(session_id)
    except Exception as e:
        logger.warning(f"Failed to load phases for {session_id}: {e}")

    return {
        "session_id": session_id,
        "messages": [msg.dict() for msg in messages],
        "count": len(messages),
        "phases": phases,
    }



@router.get("/session/{session_id}/timeline")
async def get_session_timeline(session_id: str):
    """
    获取会话的时间轴（工具调用事件）

    Args:
        session_id: 会话ID

    Returns:
        时间轴事件列表
    """
    try:
        timeline = await session_manager.get_timeline(session_id)

        return {
            "session_id": session_id,
            "timeline": [step.dict() for step in timeline],
            "count": len(timeline),
        }
    except Exception as e:
        logger.error(f"Error getting timeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get timeline: {str(e)}")


@router.post("/session/{session_id}/message", response_model=SendMessageResponse)
async def send_message(
    session_id: str, request: SendMessageRequest, background_tasks: BackgroundTasks
):
    """
    发送新消息到会话
    """
    try:
        # 验证会话存在
        session = await session_manager.get_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(
                status_code=404, detail=f"Session not found: {session_id}"
            )

        # 1. 创建 user message
        user_message_id = request.message_id
        user_text = ""
        if request.parts:
            first_part = request.parts[0]
            user_text = (first_part.text if hasattr(first_part, "text") else "") or ""
        user_text = user_text.strip()


        # 请求验证
        if not user_text:
            logger.warning(f"Empty message text in request for session: {session_id}")
            raise HTTPException(status_code=400, detail="Message text cannot be empty")

        # ✅ v=38.4.3修复：更新数据库中的session title和prompt
        # 这样Go CLI查询时能获取正确的title（非NULL）
        try:
            import sqlite3
            import time
            from app.main import WORKSPACE_BASE

            db_path = os.path.join(WORKSPACE_BASE, "history.db")
            title = user_text[:100] if len(user_text) > 100 else user_text
            now = int(time.time())

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET title = ?, prompt = ?, updated_at = ?
                WHERE id = ?
            """, (title, user_text, now, session_id))
            conn.commit()
            conn.close()

            logger.info(f"[DB] Updated session {session_id} with title: {title[:50]}...")
        except Exception as db_err:
            logger.warning(f"[DB] Failed to update session title (non-critical): {db_err}")

        user_message = Message(
            id=user_message_id,
            session_id=session_id,
            role=MessageRole.USER,
            time=MessageTime(created=int(time.time())),
        )

        await session_manager.add_message(user_message)

        # 添加 user text part
        user_part_id = generate_part_id()
        logger.info(f"Adding user message part: {user_part_id}")
        user_part = Part(
            id=user_part_id,
            session_id=session_id,
            message_id=user_message_id,
            type=PartType.TEXT,
            content=PartContent(text=user_text),
            time=PartTime(start=int(time.time())),
        )
        await session_manager.add_part(session_id, user_message_id, user_part)

        logger.info(f"Added user message: {user_message_id} to session: {session_id}")

        # 2. 创建 assistant message（初始为空）
        assistant_message_id = generate_message_id()
        assistant_message = Message(
            id=assistant_message_id,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            time=MessageTime(created=int(time.time())),
        )

        await session_manager.add_message(assistant_message)

        logger.info(
            f"Created assistant message: {assistant_message_id} for session: {session_id}"
        )

        # 3. 发送消息更新事件（通过 SSE 广播）
        await broadcast_message_update(session_id, assistant_message)

        # 4. 后台执行 OpenCode CLI 任务 - 使用全局OpenCodeServerManager实现性能优化
        # Import from managers_internal module to avoid circular imports
        from app.managers_internal import get_opencode_server_manager
        from .opencode_client import execute_opencode_message_with_manager

        workspace_base = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../workspace")
        )
        # 验证并创建工作区
        if not os.path.exists(workspace_base):
            logger.info(f"Creating workspace directory: {workspace_base}")
            os.makedirs(workspace_base, exist_ok=True)

        # 增强提示词
        from .prompt_enhancer import enhance_prompt

        try:
            enhanced_user_text = enhance_prompt(user_text)
        except Exception as pe:
            logger.error(f"Prompt enhancement failed, falling back to original: {pe}")
            enhanced_user_text = user_text

        # 确定运行模式：请求指定优先（非 auto），其次是 Session 预设（非auto/非空），最后默认为 build
        session_mode = getattr(session, "metadata", {}).get("mode", "auto")
        # 修复：当mode为auto时，默认使用build而不是plan，确保有足够的工具调用
        run_mode = request.mode if request.mode != "auto" else (session_mode if session_mode not in ["auto", None] else "build")

        # 验证mode值合法性
        VALID_MODES = {"auto", "plan", "build"}
        if run_mode not in VALID_MODES:
            logger.warning(f"Invalid mode '{run_mode}', falling back to 'build'")
            run_mode = "build"

        logger.info(f"Sending message to {session_id} in mode: {run_mode}")

        # ✅ 性能优化：使用全局OpenCodeServerManager而不是每次启动新进程
        background_tasks.add_task(
            execute_opencode_message_with_manager,
            session_id,
            assistant_message_id,
            enhanced_user_text,
            workspace_base,
            run_mode,
        )


        return SendMessageResponse(
            id=assistant_message_id,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            time=MessageTime(created=int(time.time())),
        )

    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


# ====================================================================
# SSE Event Stream Endpoints
# ====================================================================


class EventStreamManager:
    """管理 SSE 事件流广播"""

    def __init__(self):
        # {session_id: Set[asyncio.Queue]}
        self.listeners: dict = {}

    async def subscribe(self, session_id: str) -> asyncio.Queue:
        """订阅会话事件"""
        if session_id not in self.listeners:
            self.listeners[session_id] = set()

        queue = asyncio.Queue()
        self.listeners[session_id].add(queue)
        logger.info(
            f"New listener for session: {session_id} (total: {len(self.listeners[session_id])})"
        )
        return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        """取消订阅"""
        if session_id in self.listeners:
            self.listeners[session_id].discard(queue)
            logger.info(
                f"Listener left session: {session_id} (remaining: {len(self.listeners[session_id])})"
            )

    async def broadcast(self, session_id: str, event: dict):
        """向会话的所有监听者广播事件"""
        if session_id not in self.listeners:
            # ✅ 改进：记录警告而不是静默失败
            logger.warning(
                f"[EventStreamManager] ⚠️ Session {session_id} not in listeners. "
                f"Event '{event.get('type')}' will be discarded. "
                f"Current sessions: {list(self.listeners.keys())}"
            )
            return

        # 使用 jsonable_encoder 处理 Enum 和 Pydantic 模型
        encoded_event = jsonable_encoder(event)
        event_json = json.dumps(encoded_event, ensure_ascii=False)
        sse_data = f"data: {event_json}\n\n"

        logger.info(
            f"[EventStreamManager] Broadcasting '{event.get('type')}' to {len(self.listeners[session_id])} listeners for session {session_id}"
        )

        for queue in list(self.listeners[session_id]):
            try:
                await queue.put(sse_data)
            except Exception as e:
                logger.error(f"Failed to send event: {e}")
                self.listeners[session_id].discard(queue)

    def get_listener_count(self, session_id: str) -> int:
        """获取会话的监听者数量"""
        return len(self.listeners.get(session_id, set()))


# 全局事件流管理器
event_stream_manager = EventStreamManager()


def format_sse(data: dict) -> str:
    """格式化 SSE 数据"""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"data: {json_data}\n\n"


@router.get("/events")
async def events(session_id: str):
    """
    SSE 事件流端点

    Args:
        session_id: 会话ID（查询参数）

    Returns:
        SSE 事件流

    事件类型：
        - connection.established: 连接建立
        - message.updated: 消息更新
        - message.part.updated: 部分更新
        - ping: 心跳
    """
    # 验证会话存在
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    async def event_stream():
        # 订阅会话事件
        queue = await event_stream_manager.subscribe(session_id)
        listener_count = event_stream_manager.get_listener_count(session_id)

        logger.info(
            f"SSE connection established for session: {session_id} (listeners: {listener_count})"
        )

        try:
            # 发送连接成功消息
            yield format_sse(
                {
                    "type": "connection.established",
                    "session_id": session_id,
                    "timestamp": int(time.time()),
                }
            )

            # 发送初始状态（当前会话的消息）
            messages = await session_manager.get_messages(session_id)
            yield format_sse(
                {
                    "type": "session.state",
                    "session_id": session_id,
                    "message_count": len(messages),
                }
            )

            # 持续发送事件
            last_activity = time.time()

            while True:
                try:
                    # 等待事件（带超时）
                    sse_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    last_activity = time.time()
                    yield sse_data

                except asyncio.TimeoutError:
                    # 发送心跳
                    yield format_sse(
                        {
                            "type": "ping",
                            "timestamp": int(time.time()),
                            "session_id": session_id,
                        }
                    )

                    # 检查会话是否还存在
                    session = await session_manager.get_session(session_id)
                    if not session or session.status == SessionStatus.ARCHIVED:
                        logger.info(
                            f"Session {session_id} no longer active, closing SSE"
                        )
                        break

        except GeneratorExit:
            logger.info(f"SSE client disconnected from session: {session_id}")
        except Exception as e:
            logger.error(f"SSE error for session {session_id}: {e}")
        finally:
            await event_stream_manager.unsubscribe(session_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ====================================================================
# Utility Endpoints
# ====================================================================


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "sessions": len(session_manager.sessions),
    }


@router.get("/info")
async def get_info():
    """获取 API 信息"""
    return {
        "name": "OpenCode API",
        "version": "2.0.0",
        "description": "OpenCode Web API with Session + Message architecture",
        "endpoints": {
            "session": {
                "create": "POST /opencode/session",
                "get": "GET /opencode/session/{id}",
                "delete": "DELETE /opencode/session/{id}",
                "list": "GET /opencode/sessions",
            },
            "message": {
                "get_messages": "GET /opencode/session/{id}/messages",
                "send": "POST /opencode/session/{id}/message",
            },
            "events": {"stream": "GET /opencode/events?session_id={id}"},
            "history": {
                "get_file_history": "GET /opencode/get_file_history",
                "get_file_at_step": "GET /opencode/get_file_at_step",
            },
        },
        "documentation": "/docs",
    }


@router.get("/get_file_history")
async def get_file_history(session_id: str, file_path: str):
    """
    获取文件的历史记录

    Args:
        session_id: 会话ID
        file_path: 文件路径

    Returns:
        历史记录列表
    """
    try:
        timeline = await session_manager.get_timeline(session_id)

        # 过滤特定文件的历史记录
        file_history = [
            {
                "step_id": step.step_id,
                "action": step.action,
                "path": step.path,
                "timestamp": step.timestamp,
            }
            for step in timeline
            if step.path == file_path
        ]

        return {
            "file_path": file_path,
            "history": file_history,
            "count": len(file_history),
        }
    except Exception as e:
        logger.error(f"Error getting file history: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get file history: {str(e)}"
        )


@router.get("/get_file_at_step")
async def get_file_at_step(session_id: str, file_path: str, step_id: str):
    """
    获取文件在特定步骤时的内容

    Args:
        session_id: 会话ID
        file_path: 文件路径
        step_id: 步骤ID

    Returns:
        文件内容
    """
    try:
        content = await session_manager.get_file_at_step(session_id, file_path, step_id)

        if content is None:
            raise HTTPException(
                status_code=404,
                detail=f"File not found at step: {file_path} @ {step_id}",
            )

        return {"file_path": file_path, "step_id": step_id, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file at step: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get file at step: {str(e)}"
        )


# ====================================================================
# Helper Functions
# ====================================================================


async def broadcast_message_update(session_id: str, message: Message):
    """广播消息更新事件"""
    await event_stream_manager.broadcast(
        session_id, {"type": "message.updated", "properties": {"info": message.dict()}}
    )


async def broadcast_part_update(session_id: str, part):
    """广播部分更新事件"""
    await event_stream_manager.broadcast(
        session_id,
        {
            "type": "message.part.updated",
            "properties": {"part": part.dict(), "session_id": session_id},
        },
    )
