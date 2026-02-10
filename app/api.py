"""
OpenCode 新架构 API 端点

基于官方 Web API 的 Session + Message 架构
提供真正的多轮对话支持
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
import asyncio
import json
import logging
import os
import time
from datetime import datetime

# 导入数据模型
try:
    from .models import (
        Session, SessionStatus,
        Message, MessageRole, MessageWithParts,
        SendMessageRequest, SendMessageResponse,
        SessionEvent
    )
    from .managers import SessionManager
except ImportError:
    from models import (
        Session, SessionStatus,
        Message, MessageRole, MessageWithParts,
        SendMessageRequest, SendMessageResponse,
        SessionEvent
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
    version: str = "1.0.0"
):
    """
    创建新会话

    Args:
        title: 会话标题
        version: API 版本

    Returns:
        创建的会话对象
    """
    try:
        session = await session_manager.create_session(title=title, version=version)
        logger.info(f"Created session: {session.id}")
        return session
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


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
async def list_sessions(
    status: Optional[SessionStatus] = None
):
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
# Message Management Endpoints
# ====================================================================

@router.get("/session/{session_id}/messages")
async def get_messages(session_id: str):
    """
    获取会话的所有消息历史

    Args:
        session_id: 会话ID

    Returns:
        消息列表（包含部分）
    """
    # 验证会话存在
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    # 获取消息
    messages = await session_manager.get_messages(session_id)

    return {
        "session_id": session_id,
        "messages": [msg.dict() for msg in messages],
        "count": len(messages)
    }


@router.post("/session/{session_id}/message", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks
):
    """
    发送新消息到会话

    Args:
        session_id: 会话ID
        request: 发送消息请求
        background_tasks: FastAPI 后台任务

    Returns:
        创建的助手消息（初始为空）

    流程：
        1. 创建 user message
        2. 创建 assistant message（初始为空）
        3. 后台执行 OpenCode CLI
        4. 通过 SSE 推送更新
    """
    # 验证会话存在
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    # 1. 创建 user message
    user_message_id = request.message_id
    user_text = request.parts[0].text if request.parts else ""

    user_message = Message(
        id=user_message_id,
        session_id=session_id,
        role=MessageRole.USER,
        time={
            "created": int(time.time())
        }
    )
    await session_manager.add_message(user_message)

    # 添加 user text part
    from .models import generate_part_id, Part, PartType, PartTime, PartContent
    user_part_id = generate_part_id()
    user_part = Part(
        id=user_part_id,
        session_id=session_id,
        message_id=user_message_id,
        type=PartType.TEXT,
        content=PartContent(text=user_text),
        time=PartTime(start=int(time.time()))
    )
    await session_manager.add_part(session_id, user_message_id, user_part)

    logger.info(f"Added user message: {user_message_id} to session: {session_id}")

    # 2. 创建 assistant message（初始为空）
    from .models import generate_message_id
    assistant_message_id = generate_message_id()
    assistant_message = Message(
        id=assistant_message_id,
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        time={
            "created": int(time.time())
        }
    )
    await session_manager.add_message(assistant_message)

    logger.info(f"Created assistant message: {assistant_message_id} for session: {session_id}")

    # 3. 发送消息更新事件（通过 SSE 广播）
    await broadcast_message_update(session_id, assistant_message)

    # 4. 后台执行 OpenCode CLI 任务
    workspace_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../workspace"))
    background_tasks.add_task(
        execute_opencode_message,
        session_id,
        assistant_message_id,
        user_text,
        workspace_base
    )

    return SendMessageResponse(
        id=assistant_message_id,
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        time={"created": int(time.time())}
    )


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
        logger.info(f"New listener for session: {session_id} (total: {len(self.listeners[session_id])})")
        return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        """取消订阅"""
        if session_id in self.listeners:
            self.listeners[session_id].discard(queue)
            logger.info(f"Listener left session: {session_id} (remaining: {len(self.listeners[session_id])})")

    async def broadcast(self, session_id: str, event: dict):
        """向会话的所有监听者广播事件"""
        if session_id not in self.listeners:
            return

        event_json = json.dumps(event, ensure_ascii=False)
        sse_data = f"data: {event_json}\n\n"

        logger.debug(f"Broadcasting to {len(self.listeners[session_id])} listeners: {event.get('type')}")

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

        logger.info(f"SSE connection established for session: {session_id} (listeners: {listener_count})")

        try:
            # 发送连接成功消息
            yield format_sse({
                "type": "connection.established",
                "session_id": session_id,
                "timestamp": int(time.time())
            })

            # 发送初始状态（当前会话的消息）
            messages = await session_manager.get_messages(session_id)
            yield format_sse({
                "type": "session.state",
                "session_id": session_id,
                "message_count": len(messages)
            })

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
                    yield format_sse({
                        "type": "ping",
                        "timestamp": int(time.time()),
                        "session_id": session_id
                    })

                    # 检查会话是否还存在
                    session = await session_manager.get_session(session_id)
                    if not session or session.status == SessionStatus.ARCHIVED:
                        logger.info(f"Session {session_id} no longer active, closing SSE")
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
            "X-Accel-Buffering": "no"
        }
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
        "sessions": len(session_manager.sessions)
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
                "list": "GET /opencode/sessions"
            },
            "message": {
                "get_messages": "GET /opencode/session/{id}/messages",
                "send": "POST /opencode/session/{id}/message"
            },
            "events": {
                "stream": "GET /opencode/events?session_id={id}"
            }
        },
        "documentation": "/docs"
    }


# ====================================================================
# Helper Functions
# ====================================================================

async def broadcast_message_update(session_id: str, message: Message):
    """广播消息更新事件"""
    await event_stream_manager.broadcast(session_id, {
        "type": "message.updated",
        "properties": {
            "info": message.dict()
        }
    })


async def broadcast_part_update(session_id: str, part):
    """广播部分更新事件"""
    await event_stream_manager.broadcast(session_id, {
        "type": "message.part.updated",
        "properties": {
            "part": part.dict(),
            "session_id": session_id
        }
    })
