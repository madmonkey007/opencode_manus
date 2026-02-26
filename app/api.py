"""
OpenCode 新架构 API 端点

基于官方 Web API 的 Session + Message 架构
提供真正的多轮对话支持
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from typing import List, Optional, Dict, Any
import asyncio
import json
import logging
import os
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
async def create_session(title: str = "New Session", mode: str = "auto", version: str = "1.0.0"):
    """
    创建新会话

    Args:
        title: 会话标题
        mode: 初始模式 (plan/build/auto)
        version: API 版本

    Returns:
        创建的会话对象
    """
    try:
        session = await session_manager.create_session(title=title, version=version)
        # 将模式存储在会话元数据中
        session.metadata["mode"] = mode
        logger.info(f"Created session: {session.id} with mode: {mode}")
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
        "count": len(messages),
    }


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

        # 4. 后台执行 OpenCode CLI 任务
        from .opencode_client import execute_opencode_message

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

        # 确定运行模式：请求指定优先（非 auto），其次是 Session 预设，最后默认为 auto
        session_mode = session.metadata.get("mode") if hasattr(session, "metadata") and session.metadata else "auto"
        run_mode = request.mode if request.mode != "auto" else (session_mode or "auto")
        logger.info(f"Sending message to {session_id} in mode: {run_mode}")

        background_tasks.add_task(
            execute_opencode_message,
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
            return

        # 使用 jsonable_encoder 处理 Enum 和 Pydantic 模型
        encoded_event = jsonable_encoder(event)
        event_json = json.dumps(encoded_event, ensure_ascii=False)
        sse_data = f"data: {event_json}\n\n"

        logger.debug(
            f"Broadcasting to {len(self.listeners[session_id])} listeners: {event.get('type')}"
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
                "operation": step.operation,
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
