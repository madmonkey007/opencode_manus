"""
SessionManager 和 MessageStore 单元测试

运行测试：
    cd D:\manus\opencode
    python -m pytest tests/test_managers.py -v
"""
import pytest
import asyncio
import sys
import os

# 添加 app 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from managers import SessionManager, MessageStore
from models import (
    Session, SessionStatus,
    Message, MessageRole,
    Part, PartType,
    FileSnapshot, TimelineStep,
    generate_session_id, generate_message_id, generate_part_id
)


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
async def session_manager():
    """创建 SessionManager 实例"""
    manager = SessionManager()
    yield manager
    # 清理
    for session_id in list(manager.sessions.keys()):
        await manager.delete_session(session_id)


@pytest.fixture
async def message_store():
    """创建 MessageStore 实例"""
    store = MessageStore()
    yield store
    # 清理
    for session_id in list(store.messages.keys()):
        await store.clear_session(session_id)


# ====================================================================
# SessionManager Tests
# ====================================================================

class TestSessionManager:
    """SessionManager 测试"""

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """测试创建会话"""
        session = await session_manager.create_session(
            title="Test Session",
            version="1.0.0"
        )

        assert session is not None
        assert session.id.startswith("ses_")
        assert session.title == "Test Session"
        assert session.version == "1.0.0"
        assert session.status == SessionStatus.ACTIVE
        assert session.time.created > 0
        assert session.time.updated > 0

    @pytest.mark.asyncio
    async def test_get_session(self, session_manager):
        """测试获取会话"""
        # 创建会话
        created = await session_manager.create_session(title="Test")

        # 获取会话
        retrieved = await session_manager.get_session(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, session_manager):
        """测试获取不存在的会话"""
        session = await session_manager.get_session("ses_nonexistent")
        assert session is None

    @pytest.mark.asyncio
    async def test_update_session_status(self, session_manager):
        """测试更新会话状态"""
        session = await session_manager.create_session()

        # 更新为 idle
        updated = await session_manager.update_session_status(
            session.id,
            SessionStatus.IDLE
        )

        assert updated is not None
        assert updated.status == SessionStatus.IDLE

    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager):
        """测试删除会话"""
        session = await session_manager.create_session()

        # 删除会话
        result = await session_manager.delete_session(session.id)

        assert result is True

        # 验证已删除
        retrieved = await session_manager.get_session(session.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_manager):
        """测试列出会话"""
        # 创建多个会话
        s1 = await session_manager.create_session(title="Session 1")
        s2 = await session_manager.create_session(title="Session 2")

        # 列出所有会话
        sessions = await session_manager.list_sessions()

        assert len(sessions) == 2
        assert any(s.id == s1.id for s in sessions)
        assert any(s.id == s2.id for s in sessions)

    @pytest.mark.asyncio
    async def test_list_sessions_by_status(self, session_manager):
        """测试按状态过滤会话"""
        s1 = await session_manager.create_session(title="Active")
        s2 = await session_manager.create_session(title="Idle")

        # 更新 s2 为 idle
        await session_manager.update_session_status(s2.id, SessionStatus.IDLE)

        # 只列出活跃会话
        active_sessions = await session_manager.list_sessions(status=SessionStatus.ACTIVE)

        assert len(active_sessions) == 1
        assert active_sessions[0].id == s1.id


# ====================================================================
# MessageStore Tests
# ====================================================================

class TestMessageStore:
    """MessageStore 测试"""

    @pytest.mark.asyncio
    async def test_initialize_session(self, message_store):
        """测试初始化会话存储"""
        session_id = "ses_test123"
        await message_store.initialize_session(session_id)

        assert message_store.session_exists(session_id)
        assert session_id in message_store.messages
        assert session_id in message_store.parts
        assert session_id in message_store.message_order

    @pytest.mark.asyncio
    async def test_add_message(self, message_store):
        """测试添加消息"""
        session_id = "ses_test123"
        await message_store.initialize_session(session_id)

        # 创建消息
        message = Message(
            id=generate_message_id(),
            session_id=session_id,
            role=MessageRole.USER
        )

        # 添加消息
        added = await message_store.add_message(message)

        assert added.id == message.id
        assert message.id in message_store.messages[session_id]
        assert message.id in message_store.message_order[session_id]

    @pytest.mark.asyncio
    async def test_get_messages(self, message_store):
        """测试获取消息列表"""
        session_id = "ses_test123"
        await message_store.initialize_session(session_id)

        # 添加多条消息
        m1 = Message(id=generate_message_id(), session_id=session_id, role=MessageRole.USER)
        m2 = Message(id=generate_message_id(), session_id=session_id, role=MessageRole.ASSISTANT)

        await message_store.add_message(m1)
        await message_store.add_message(m2)

        # 获取消息
        messages = await message_store.get_messages(session_id)

        assert len(messages) == 2
        assert messages[0].info.id == m1.id  # 按顺序
        assert messages[1].info.id == m2.id

    @pytest.mark.asyncio
    async def test_add_part(self, message_store):
        """测试添加部分"""
        session_id = "ses_test123"
        message_id = generate_message_id()
        await message_store.initialize_session(session_id)

        # 先添加消息
        message = Message(id=message_id, session_id=session_id, role=MessageRole.ASSISTANT)
        await message_store.add_message(message)

        # 添加部分
        part = Part(
            id=generate_part_id(),
            session_id=session_id,
            message_id=message_id,
            type=PartType.TEXT
        )
        await message_store.add_part(session_id, message_id, part)

        # 验证
        parts = await message_store.get_parts(session_id, message_id)
        assert len(parts) == 1
        assert parts[0].id == part.id

    @pytest.mark.asyncio
    async def test_add_file_snapshot(self, message_store):
        """测试添加文件快照"""
        session_id = "ses_test123"
        await message_store.initialize_session(session_id)

        snapshot = FileSnapshot(
            id="snap_001",
            session_id=session_id,
            file_path="/test/file.txt",
            content="Hello, World!",
            operation="created",
            step_id="step_001",
            timestamp=1234567890,
            checksum="abc123"
        )

        await message_store.add_file_snapshot(snapshot)

        snapshots = message_store.file_snapshots[session_id]
        assert len(snapshots) == 1
        assert snapshots[0].id == "snap_001"

    @pytest.mark.asyncio
    async def test_get_file_at_step(self, message_store):
        """测试获取文件在指定步骤的内容"""
        session_id = "ses_test123"
        await message_store.initialize_session(session_id)

        # 添加多个快照
        s1 = FileSnapshot(
            id="snap_001",
            session_id=session_id,
            file_path="/test/file.txt",
            content="Version 1",
            operation="created",
            step_id="step_001",
            timestamp=1000,
            checksum="abc1"
        )

        s2 = FileSnapshot(
            id="snap_002",
            session_id=session_id,
            file_path="/test/file.txt",
            content="Version 2",
            operation="modified",
            step_id="step_002",
            timestamp=2000,
            checksum="abc2"
        )

        await message_store.add_file_snapshot(s1)
        await message_store.add_file_snapshot(s2)

        # 获取 step_001 时刻的内容
        content = await message_store.get_file_at_step(
            session_id, "/test/file.txt", "step_001"
        )

        assert content == "Version 1"

    @pytest.mark.asyncio
    async def test_timeline(self, message_store):
        """测试时间轴"""
        session_id = "ses_test123"
        await message_store.initialize_session(session_id)

        step = TimelineStep(
            step_id="step_001",
            action="write",
            path="/test/file.txt",
            timestamp=1234567890
        )

        await message_store.add_timeline_step(session_id, step)

        timeline = await message_store.get_timeline(session_id)
        assert len(timeline) == 1
        assert timeline[0].step_id == "step_001"


# ====================================================================
# Integration Tests
# ====================================================================

class TestIntegration:
    """集成测试：SessionManager + MessageStore"""

    @pytest.mark.asyncio
    async def test_multi_round_conversation(self, session_manager):
        """测试多轮对话场景"""
        # 创建会话
        session = await session_manager.create_session(title="Multi-round Test")

        # 第一轮：用户消息
        user_msg1 = Message(
            id=generate_message_id(),
            session_id=session.id,
            role=MessageRole.USER
        )
        await session_manager.add_message(user_msg1)

        # 第一轮：助手响应
        assistant_msg1 = Message(
            id=generate_message_id(),
            session_id=session.id,
            role=MessageRole.ASSISTANT
        )
        await session_manager.add_message(assistant_msg1)

        # 添加响应的部分
        text_part = Part(
            id=generate_part_id(),
            session_id=session.id,
            message_id=assistant_msg1.id,
            type=PartType.TEXT
        )
        await session_manager.add_part(session.id, assistant_msg1.id, text_part)

        # 第二轮：用户追问
        user_msg2 = Message(
            id=generate_message_id(),
            session_id=session.id,
            role=MessageRole.USER
        )
        await session_manager.add_message(user_msg2)

        # 验证消息数量
        count = await session_manager.get_message_count(session.id)
        assert count == 3  # user1, assistant1, user2

        # 获取所有消息
        messages = await session_manager.get_messages(session.id)
        assert len(messages) == 3
        assert messages[0].info.role == MessageRole.USER
        assert messages[1].info.role == MessageRole.ASSISTANT
        assert messages[2].info.role == MessageRole.USER
        assert len(messages[1].parts) == 1  # assistant_msg1 有 1 个部分


# ====================================================================
# Run Tests
# ====================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
