"""
OpenCode 新架构管理器

包含 SessionManager 和 MessageStore，用于管理会话和消息存储
"""
import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

try:
    # 相对导入（作为包使用）
    from .models import (
        Session, SessionTime, SessionStatus,
        Message, MessageWithParts, MessageTime, MessageRole,
        Part, PartTime,
        FileSnapshot, TimelineStep,
        generate_session_id, generate_message_id, generate_part_id
    )
except ImportError:
    # 绝对导入（测试环境）
    from models import (
        Session, SessionTime, SessionStatus,
        Message, MessageWithParts, MessageTime, MessageRole,
        Part, PartTime,
        FileSnapshot, TimelineStep,
        generate_session_id, generate_message_id, generate_part_id
    )

logger = logging.getLogger("opencode.managers")


# ====================================================================
# Message Store
# ====================================================================

class MessageStore:
    """
    消息存储管理器

    职责：
    1. 存储和检索消息历史
    2. 管理消息部分（Parts）
    3. 维护消息顺序
    4. 支持会话清理
    """

    def __init__(self):
        # {session_id: {message_id: Message}}
        self.messages: Dict[str, Dict[str, Message]] = {}

        # {session_id: {message_id: {part_id: Part}}}
        self.parts: Dict[str, Dict[str, Dict[str, Part]]] = {}

        # {session_id: [message_id]}  按创建时间排序
        self.message_order: Dict[str, List[str]] = {}

        # {session_id: FileSnapshot[]}  文件快照
        self.file_snapshots: Dict[str, List[FileSnapshot]] = {}

        # {session_id: TimelineStep[]}  时间轴
        self.timelines: Dict[str, List[TimelineStep]] = {}

        logger.info("MessageStore initialized")

    # ====================================================================
    # Session Management
    # ====================================================================

    async def initialize_session(self, session_id: str) -> None:
        """初始化会话存储"""
        self.messages[session_id] = {}
        self.parts[session_id] = {}
        self.message_order[session_id] = []
        self.file_snapshots[session_id] = []
        self.timelines[session_id] = []
        logger.info(f"Initialized storage for session: {session_id}")

    async def clear_session(self, session_id: str) -> None:
        """清除会话的所有数据"""
        if session_id in self.messages:
            del self.messages[session_id]
        if session_id in self.parts:
            del self.parts[session_id]
        if session_id in self.message_order:
            del self.message_order[session_id]
        if session_id in self.file_snapshots:
            del self.file_snapshots[session_id]
        if session_id in self.timelines:
            del self.timelines[session_id]
        logger.info(f"Cleared storage for session: {session_id}")

    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        return session_id in self.messages

    # ====================================================================
    # Message Operations
    # ====================================================================

    async def add_message(self, message: Message) -> Message:
        """
        添加新消息

        Args:
            message: 消息对象

        Returns:
            添加的消息对象
        """
        session_id = message.session_id

        # 初始化会话（如果不存在）
        if not self.session_exists(session_id):
            await self.initialize_session(session_id)

        # 存储消息
        self.messages[session_id][message.id] = message

        # 添加到顺序列表
        self.message_order[session_id].append(message.id)

        # 初始化消息的 parts 字典
        self.parts[session_id][message.id] = {}

        logger.info(f"Added message: {message.id} to session: {session_id}")
        return message

    async def update_message(self, message: Message) -> Optional[Message]:
        """
        更新消息元信息

        Args:
            message: 更新后的消息对象

        Returns:
            更新后的消息对象，如果消息不存在则返回 None
        """
        session_id = message.session_id

        if session_id not in self.messages:
            logger.warning(f"Session not found: {session_id}")
            return None

        if message.id not in self.messages[session_id]:
            logger.warning(f"Message not found: {message.id} in session: {session_id}")
            return None

        # 更新消息
        self.messages[session_id][message.id] = message

        logger.info(f"Updated message: {message.id}")
        return message

    async def get_message(self, session_id: str, message_id: str) -> Optional[Message]:
        """
        获取单个消息

        Args:
            session_id: 会话ID
            message_id: 消息ID

        Returns:
            消息对象，如果不存在则返回 None
        """
        if session_id not in self.messages:
            return None

        return self.messages[session_id].get(message_id)

    async def get_messages(self, session_id: str) -> List[MessageWithParts]:
        """
        获取会话的所有消息（按时间顺序）

        Args:
            session_id: 会话ID

        Returns:
            消息列表（包含部分）
        """
        if session_id not in self.messages:
            logger.warning(f"Session not found: {session_id}")
            return []

        messages = []
        for msg_id in self.message_order.get(session_id, []):
            msg = self.messages[session_id][msg_id]
            parts = list(self.parts[session_id][msg_id].values())

            # 按 time.start 排序部分
            parts.sort(key=lambda p: p.time.start if p.time else 0)

            messages.append(MessageWithParts(info=msg, parts=parts))

        logger.info(f"Retrieved {len(messages)} messages for session: {session_id}")
        return messages

    async def get_message_count(self, session_id: str) -> int:
        """
        获取会话的消息数量

        Args:
            session_id: 会话ID

        Returns:
            消息数量
        """
        return len(self.message_order.get(session_id, []))

    # ====================================================================
    # Part Operations
    # ====================================================================

    async def add_part(self, session_id: str, message_id: str, part: Part) -> Part:
        """
        添加消息部分

        Args:
            session_id: 会话ID
            message_id: 消息ID
            part: 部分对象

        Returns:
            添加的部分对象
        """
        if session_id not in self.parts:
            logger.warning(f"Session not found: {session_id}")
            await self.initialize_session(session_id)

        if message_id not in self.parts[session_id]:
            logger.warning(f"Message not found: {message_id} in session: {session_id}")
            self.parts[session_id][message_id] = {}

        # 存储部分
        self.parts[session_id][message_id][part.id] = part

        logger.info(f"Added part: {part.id} to message: {message_id}")
        return part

    async def update_part(self, session_id: str, part: Part) -> Optional[Part]:
        """
        更新消息部分

        Args:
            session_id: 会话ID
            part: 更新后的部分对象

        Returns:
            更新后的部分对象，如果不存在则返回 None
        """
        if session_id not in self.parts:
            logger.warning(f"Session not found: {session_id}")
            return None

        # 在所有消息中查找该部分
        for msg_id, parts in self.parts[session_id].items():
            if part.id in parts:
                parts[part.id] = part
                logger.info(f"Updated part: {part.id}")
                return part

        logger.warning(f"Part not found: {part.id} in session: {session_id}")
        return None

    async def get_parts(self, session_id: str, message_id: str) -> List[Part]:
        """
        获取消息的所有部分

        Args:
            session_id: 会话ID
            message_id: 消息ID

        Returns:
            部分列表（按时间排序）
        """
        if session_id not in self.parts:
            return []

        if message_id not in self.parts[session_id]:
            return []

        parts = list(self.parts[session_id][message_id].values())
        parts.sort(key=lambda p: p.time.start if p.time else 0)

        return parts

    # ====================================================================
    # File Snapshot Operations（用于历史回溯）
    # ====================================================================

    async def add_file_snapshot(self, snapshot: FileSnapshot) -> FileSnapshot:
        """
        添加文件快照

        Args:
            snapshot: 文件快照对象

        Returns:
            添加的快照对象
        """
        session_id = snapshot.session_id

        if session_id not in self.file_snapshots:
            self.file_snapshots[session_id] = []

        self.file_snapshots[session_id].append(snapshot)

        logger.info(f"Added file snapshot: {snapshot.id} for {snapshot.file_path}")
        return snapshot

    async def get_file_snapshots(self, session_id: str, file_path: str) -> List[FileSnapshot]:
        """
        获取文件的所有快照（按时间排序）

        Args:
            session_id: 会话ID
            file_path: 文件路径

        Returns:
            快照列表
        """
        if session_id not in self.file_snapshots:
            return []

        snapshots = [
            s for s in self.file_snapshots[session_id]
            if s.file_path == file_path
        ]
        snapshots.sort(key=lambda s: s.timestamp)

        return snapshots

    async def get_file_at_step(
        self,
        session_id: str,
        file_path: str,
        target_step_id: str
    ) -> Optional[str]:
        """
        获取文件在指定步骤时刻的内容

        Args:
            session_id: 会话ID
            file_path: 文件路径
            target_step_id: 目标步骤ID

        Returns:
            文件内容，如果不存在则返回 None
        """
        snapshots = await self.get_file_snapshots(session_id, file_path)

        # 找到目标步骤之前的最后一个快照
        target_content = None
        for snapshot in snapshots:
            if snapshot.step_id == target_step_id:
                target_content = snapshot.content
                break
            # 继续查找，直到找到目标步骤或更晚的快照

        return target_content

    async def add_timeline_step(self, session_id: str, step: TimelineStep) -> TimelineStep:
        """
        添加时间轴步骤

        Args:
            session_id: 会话ID
            step: 时间轴步骤对象

        Returns:
            添加的步骤对象
        """
        if session_id not in self.timelines:
            self.timelines[session_id] = []

        self.timelines[session_id].append(step)

        logger.info(f"Added timeline step: {step.step_id} for {step.action}")
        return step

    async def get_timeline(self, session_id: str) -> List[TimelineStep]:
        """
        获取会话的完整时间轴

        Args:
            session_id: 会话ID

        Returns:
            时间轴步骤列表
        """
        return self.timelines.get(session_id, [])


# ====================================================================
# Session Manager
# ====================================================================

class SessionManager:
    """
    会话管理器

    职责：
    1. 创建和管理会话
    2. 维护会话状态
    3. 提供会话查询接口
    4. 集成 MessageStore
    """

    def __init__(self):
        # {session_id: Session}
        self.sessions: Dict[str, Session] = {}

        # 消息存储
        self.message_store = MessageStore()

        logger.info("SessionManager initialized")

    # ====================================================================
    # Session CRUD
    # ====================================================================

    async def create_session(
        self,
        title: str = "New Session",
        version: str = "1.0.0"
    ) -> Session:
        """
        创建新会话

        Args:
            title: 会话标题
            version: API 版本

        Returns:
            创建的会话对象
        """
        session_id = generate_session_id()
        session = Session(
            id=session_id,
            title=title,
            version=version,
            time=SessionTime(
                created=int(datetime.now().timestamp()),
                updated=int(datetime.now().timestamp())
            ),
            status=SessionStatus.ACTIVE
        )

        # 存储会话
        self.sessions[session_id] = session

        # 初始化消息存储
        await self.message_store.initialize_session(session_id)

        logger.info(f"Created session: {session_id} with title: {title}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话

        Args:
            session_id: 会话ID

        Returns:
            会话对象，如果不存在则返回 None
        """
        return self.sessions.get(session_id)

    async def update_session_status(
        self,
        session_id: str,
        status: SessionStatus
    ) -> Optional[Session]:
        """
        更新会话状态

        Args:
            session_id: 会话ID
            status: 新状态

        Returns:
            更新后的会话对象，如果不存在则返回 None
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None

        session.status = status
        session.time.updated = int(datetime.now().timestamp())

        logger.info(f"Updated session status: {session_id} -> {status}")
        return session

    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话及其所有数据

        Args:
            session_id: 会话ID

        Returns:
            是否成功删除
        """
        if session_id not in self.sessions:
            logger.warning(f"Session not found: {session_id}")
            return False

        # 删除会话
        del self.sessions[session_id]

        # 清除消息存储
        await self.message_store.clear_session(session_id)

        logger.info(f"Deleted session: {session_id}")
        return True

    async def list_sessions(
        self,
        status: Optional[SessionStatus] = None
    ) -> List[Session]:
        """
        列出所有会话

        Args:
            status: 可选的状态过滤器

        Returns:
            会话列表
        """
        sessions = list(self.sessions.values())

        if status:
            sessions = [s for s in sessions if s.status == status]

        # 按更新时间倒序排序
        sessions.sort(key=lambda s: s.time.updated, reverse=True)

        return sessions

    # ====================================================================
    # Message Operations（代理到 MessageStore）
    # ====================================================================

    async def add_message(self, message: Message) -> Message:
        """添加消息（代理到 MessageStore）"""
        # 更新会话的 updated 时间
        if message.session_id in self.sessions:
            self.sessions[message.session_id].time.updated = int(datetime.now().timestamp())

        return await self.message_store.add_message(message)

    async def update_message(self, message: Message) -> Optional[Message]:
        """更新消息（代理到 MessageStore）"""
        return await self.message_store.update_message(message)

    async def get_message(self, session_id: str, message_id: str) -> Optional[Message]:
        """获取消息（代理到 MessageStore）"""
        return await self.message_store.get_message(session_id, message_id)

    async def get_messages(self, session_id: str) -> List[MessageWithParts]:
        """获取会话的所有消息（代理到 MessageStore）"""
        return await self.message_store.get_messages(session_id)

    async def get_message_count(self, session_id: str) -> int:
        """获取消息数量（代理到 MessageStore）"""
        return await self.message_store.get_message_count(session_id)

    # ====================================================================
    # Part Operations（代理到 MessageStore）
    # ====================================================================

    async def add_part(self, session_id: str, message_id: str, part: Part) -> Part:
        """添加部分（代理到 MessageStore）"""
        return await self.message_store.add_part(session_id, message_id, part)

    async def update_part(self, session_id: str, part: Part) -> Optional[Part]:
        """更新部分（代理到 MessageStore）"""
        return await self.message_store.update_part(session_id, part)

    async def get_parts(self, session_id: str, message_id: str) -> List[Part]:
        """获取部分（代理到 MessageStore）"""
        return await self.message_store.get_parts(session_id, message_id)

    # ====================================================================
    # File Snapshot Operations（代理到 MessageStore）
    # ====================================================================

    async def add_file_snapshot(self, snapshot: FileSnapshot) -> FileSnapshot:
        """添加文件快照（代理到 MessageStore）"""
        return await self.message_store.add_file_snapshot(snapshot)

    async def get_file_snapshots(self, session_id: str, file_path: str) -> List[FileSnapshot]:
        """获取文件快照（代理到 MessageStore）"""
        return await self.message_store.get_file_snapshots(session_id, file_path)

    async def get_file_at_step(
        self,
        session_id: str,
        file_path: str,
        target_step_id: str
    ) -> Optional[str]:
        """获取文件在指定步骤的内容（代理到 MessageStore）"""
        return await self.message_store.get_file_at_step(
            session_id, file_path, target_step_id
        )

    async def add_timeline_step(self, session_id: str, step: TimelineStep) -> TimelineStep:
        """添加时间轴步骤（代理到 MessageStore）"""
        return await self.message_store.add_timeline_step(session_id, step)

    async def get_timeline(self, session_id: str) -> List[TimelineStep]:
        """获取时间轴（代理到 MessageStore）"""
        return await self.message_store.get_timeline(session_id)

    # ====================================================================
    # Utility Methods
    # ====================================================================

    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        return session_id in self.sessions

    def get_message_store(self) -> MessageStore:
        """获取消息存储对象"""
        return self.message_store
