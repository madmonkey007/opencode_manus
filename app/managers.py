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

    async def restore_session_from_db(self, session_id: str) -> bool:
        """
        从数据库恢复会话到内存

        Args:
            session_id: 会话ID

        Returns:
            是否成功恢复
        """
        try:
            import sqlite3
            from pathlib import Path

            # 查找数据库文件
            db_path = Path("history.db")
            if not db_path.exists():
                logger.warning(f"Database file not found: {db_path}")
                return False

            # 初始化内存结构
            if session_id not in self.messages:
                self.messages[session_id] = {}
            if session_id not in self.parts:
                self.parts[session_id] = {}
            if session_id not in self.message_order:
                self.message_order[session_id] = []
            if session_id not in self.file_snapshots:
                self.file_snapshots[session_id] = []
            if session_id not in self.timelines:
                self.timelines[session_id] = []

            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 检查会话是否存在
            cursor.execute("SELECT COUNT(*) as cnt FROM sessions WHERE session_id = ?", (session_id,))
            if cursor.fetchone()["cnt"] == 0:
                logger.warning(f"Session {session_id} not found in database")
                conn.close()
                return False

            # 读取messages表
            cursor.execute("""
                SELECT message_id, session_id, role, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))

            rows = cursor.fetchall()
            if not rows:
                logger.warning(f"No messages found for session {session_id}")
                conn.close()
                return False

            for row in rows:
                message_id = row["message_id"]
                role = row["role"]
                created_at = row["created_at"]

                # 创建Message对象
                from .models import MessageTime, MessageRole as MR
                message = Message(
                    id=message_id,
                    session_id=session_id,
                    role=MR(role),
                    time=MessageTime(
                        created=int(datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").timestamp())
                    )
                )

                # 存储到内存
                self.messages[session_id][message_id] = message
                if message_id not in self.message_order[session_id]:
                    self.message_order[session_id].append(message_id)

                # 初始化parts字典
                self.parts[session_id][message_id] = {}

            # 读取message_parts表（如果存在）
            try:
                cursor.execute("""
                    SELECT part_id, message_id, part_type, content_json, created_at
                    FROM message_parts
                    WHERE message_id IN (
                        SELECT message_id FROM messages WHERE session_id = ?
                    )
                    ORDER BY created_at ASC
                """, (session_id,))

                part_rows = cursor.fetchall()
                for part_row in part_rows:
                    from .models import Part, PartType, PartTime, PartContent
                    import json

                    # 解析content_json
                    content_data = json.loads(part_row["content_json"]) if part_row["content_json"] else {}

                    # 创建PartContent对象
                    part_content = PartContent(
                        text=content_data.get("text"),
                        tool=content_data.get("tool"),
                        call_id=content_data.get("call_id")
                    )

                    # 创建PartTime对象
                    created_at = part_row["created_at"]
                    if created_at:
                        part_time = PartTime(
                            start=int(datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").timestamp())
                        )
                    else:
                        import time as time_module
                        part_time = PartTime(
                            start=int(time_module.time())
                        )

                    # 创建Part对象
                    part = Part(
                        id=part_row["part_id"],
                        session_id=session_id,
                        message_id=part_row["message_id"],
                        type=PartType(part_row["part_type"]),
                        content=part_content,
                        time=part_time
                    )
                    message_id = part_row["message_id"]
                    if message_id not in self.parts[session_id]:
                        self.parts[session_id][message_id] = {}
                    self.parts[session_id][message_id][part.id] = part
            except sqlite3.OperationalError:
                # message_parts表可能不存在
                logger.debug("message_parts table does not exist, skipping")
            except Exception as e:
                logger.warning(f"Error restoring message_parts: {e}")

            # 读取steps表（工具调用事件）
            try:
                cursor.execute("""
                    SELECT step_id, session_id, action_type, file_path, timestamp
                    FROM steps
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """, (session_id,))

                step_rows = cursor.fetchall()
                for step_row in step_rows:
                    from .models import TimelineStep

                    step = TimelineStep(
                        step_id=step_row["step_id"],
                        action=step_row["action_type"],
                        path=step_row["file_path"] or "",
                        timestamp=int(datetime.strptime(
                            step_row["timestamp"], "%Y-%m-%d %H:%M:%S"
                        ).timestamp())
                    )
                    self.timelines[session_id].append(step)
            except sqlite3.OperationalError:
                logger.debug("steps table does not exist, skipping")
            except Exception as e:
                logger.warning(f"Error restoring steps: {e}")

            conn.close()
            logger.info(f"Restored {len(rows)} messages for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error restoring session from DB: {e}")
            return False

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
    5. 持久化会话到数据库
    """
    
    # 常量定义
    # 使用workspace/history.db（在Docker volume中，opencode CLI可以访问）
    DB_PATH = "/app/opencode/workspace/history.db"
    PROMPT_MAX_LENGTH = 500
    DEFAULT_MODE = "auto"
    DEFAULT_STATUS = "active"

    def __init__(self):
        # {session_id: Session}
        self.sessions: Dict[str, Session] = {}

        # 消息存储
        self.message_store = MessageStore()
        
        # 数据库路径
        self.db_path = self.DB_PATH

        logger.info("SessionManager initialized")

    # ====================================================================
    # Database Operations
    # ====================================================================
    
    def _write_session_to_db(self, sid: str, prompt: str):
        """
        将session写入SQLite数据库，让opencode CLI可以查询到。
        
        注意事项:
        - 使用workspace/history.db（在Docker volume中，opencode CLI可以访问）
        - Schema: id (主键), prompt, created_at, updated_at, status, workspace_path
        
        Args:
            sid: Session ID（格式: ses_XXXXXXXXX）
            prompt: 用户输入的prompt（限制PROMPT_MAX_LENGTH字符）
        """
        try:
            import sqlite3
            from datetime import datetime

            # workspace/history.db使用created_at (TIMESTAMP类型，自动设置)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 插入session记录到workspace/history.db（使用id列）
            cursor.execute("""
                INSERT INTO sessions (id, prompt, status, workspace_path)
                VALUES (?, ?, ?, ?)
            """, (sid, prompt[:self.PROMPT_MAX_LENGTH], "running", f"/app/opencode/workspace/{sid}"))

            conn.commit()
            conn.close()

            logger.info(f"[DB] Session {sid} written to workspace/history.db successfully")
        except Exception as e:
            logger.error(f"[DB] Failed to write session {sid} to database: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ====================================================================
    # Session CRUD
    # ====================================================================

    async def create_session(
        self,
        title: str = "New Session",
        version: str = "1.0.0",
        session_id: Optional[str] = None,
    ) -> Session:
        """
        创建新会话

        Args:
            title: 会话标题
            version: API 版本
            session_id: 指定 session id（透传 opencode server 返回的 id）

        Returns:
            创建的会话对象
        """
        session_id = session_id or generate_session_id()
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

        # 存储会话到内存
        self.sessions[session_id] = session

        # ✅ 添加：写入数据库（让opencode CLI可以查询）
        self._write_session_to_db(session_id, title)

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
        # 如果会话不在内存中，尝试从数据库恢复
        if session_id not in self.message_store.messages:
            logger.info(f"Session {session_id} not in memory, restoring from database...")
            restored = await self.message_store.restore_session_from_db(session_id)
            if restored:
                logger.info(f"Successfully restored session {session_id} from database")
            else:
                logger.warning(f"Failed to restore session {session_id} from database")
                return []

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
