"""
事件分发器单元测试
"""
import pytest
import asyncio
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.gateway.event_broadcaster import (
    EventBroadcaster,
    Event,
    SSESubscriber,
    StreamSubscriber
)


class TestEvent:
    """事件测试"""

    def test_create_event(self):
        """测试创建事件"""
        event = Event(
            event_type="phase",
            session_id="test-session",
            data={"phase": "planning"}
        )

        assert event.event_type == "phase"
        assert event.session_id == "test-session"
        assert event.data["phase"] == "planning"
        assert isinstance(event.timestamp, datetime)
        assert event.event_id is not None

    def test_event_to_dict(self):
        """测试事件转换为字典"""
        event = Event(
            event_type="test",
            session_id="test-session",
            data={"test": "data"}
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "test"
        assert event_dict["session_id"] == "test-session"
        assert event_dict["data"]["test"] == "data"
        assert "timestamp" in event_dict
        assert "event_id" in event_dict

    def test_event_to_json(self):
        """测试事件转换为JSON"""
        event = Event(
            event_type="test",
            session_id="test-session",
            data={"test": "data"}
        )

        json_str = event.to_json()

        assert isinstance(json_str, str)
        assert "test" in json_str

    def test_event_to_sse(self):
        """测试事件转换为SSE格式"""
        event = Event(
            event_type="test",
            session_id="test-session",
            data={"test": "data"}
        )

        sse_str = event.to_sse()

        assert sse_str.startswith("data: ")
        assert sse_str.endswith("\n\n")


class TestEventSubscriber:
    """事件订阅者测试"""

    @pytest.mark.asyncio
    async def test_put_and_get_event(self):
        """测试放入和获取事件"""
        subscriber = SSESubscriber("test-sub", "test-session")

        event = Event(
            event_type="test",
            session_id="test-session",
            data={"test": "data"}
        )

        # 放入事件
        success = await subscriber.put_event(event)
        assert success is True

        # 获取事件
        retrieved_event = await subscriber.get_event()
        assert retrieved_event.event_id == event.event_id
        assert retrieved_event.event_type == "test"

    def test_has_events(self):
        """测试检查是否有事件"""
        subscriber = SSESubscriber("test-sub", "test-session")

        assert subscriber.has_events() is False

        # 使用同步方式放入（测试用）
        event = Event(
            event_type="test",
            session_id="test-session",
            data={"test": "data"}
        )
        subscriber.queue.put_nowait(event)

        assert subscriber.has_events() is True

    def test_queue_size(self):
        """测试获取队列大小"""
        subscriber = SSESubscriber("test-sub", "test-session")

        assert subscriber.queue_size() == 0

        # 添加几个事件
        for i in range(3):
            event = Event(
                event_type="test",
                session_id="test-session",
                data={"index": i}
            )
            subscriber.queue.put_nowait(event)

        assert subscriber.queue_size() == 3


class TestEventBroadcaster:
    """事件分发器测试"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        broadcaster = EventBroadcaster()

        assert broadcaster._subscribers == {}
        assert broadcaster._sessions == {}
        assert broadcaster._channel_index == {}

    @pytest.mark.asyncio
    async def test_subscribe(self):
        """测试订阅"""
        broadcaster = EventBroadcaster()
        await broadcaster.start()

        subscriber = SSESubscriber("test-sub", "test-session")

        sub_id = broadcaster.subscribe(subscriber, "test-session")

        assert sub_id == "test-sub"
        assert "test-sub" in broadcaster._subscribers
        assert "test-session" in broadcaster._sessions

        await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """测试取消订阅"""
        broadcaster = EventBroadcaster()
        await broadcaster.start()

        subscriber = SSESubscriber("test-sub", "test-session")
        broadcaster.subscribe(subscriber)

        # 取消订阅
        success = broadcaster.unsubscribe("test-sub")

        assert success is True
        assert "test-sub" not in broadcaster._subscribers

        # 再次取消订阅
        success = broadcaster.unsubscribe("test-sub")
        assert success is False

        await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """测试广播事件"""
        broadcaster = EventBroadcaster()
        await broadcaster.start()

        # 创建订阅者
        sub1 = SSESubscriber("sub-1", "session-1")
        sub2 = SSESubscriber("sub-2", "session-2")

        broadcaster.subscribe(sub1, "session-1")
        broadcaster.subscribe(sub2, "session-2")

        # 创建事件
        event = Event(
            event_type="test",
            session_id="session-1",
            data={"test": "data"}
        )

        # 广播到所有渠道
        count = await broadcaster.broadcast(event)

        assert count == 2

        await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_broadcast_channel_filtering(self):
        """测试渠道过滤"""
        broadcaster = EventBroadcaster()
        await broadcaster.start()

        # 创建不同渠道的订阅者
        sse_sub = SSESubscriber("sse-sub", "session-1")
        stream_sub = StreamSubscriber("stream-sub")

        broadcaster.subscribe(sse_sub, "session-1")
        broadcaster.subscribe(stream_sub)

        # 创建事件
        event = Event(
            event_type="test",
            session_id="session-1",
            data={"test": "data"}
        )

        # 只广播到SSE渠道
        count = await broadcaster.broadcast(event, channels={"sse"})

        assert count == 1  # 只有SSE订阅者收到

        await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取统计信息"""
        broadcaster = EventBroadcaster()
        await broadcaster.start()

        # 创建订阅者
        subscriber = SSESubscriber("test-sub", "test-session")
        broadcaster.subscribe(subscriber, "test-session")

        # 广播事件
        event = Event(
            event_type="test",
            session_id="test-session",
            data={"test": "data"}
        )
        await broadcaster.broadcast(event)

        # 获取统计
        stats = broadcaster.get_stats()

        assert stats["total_subscribers"] == 1
        assert stats["total_sessions"] == 1
        assert stats["events_broadcast"] == 1

        await broadcaster.stop()


class TestEventSession:
    """事件会话测试"""

    def test_add_event(self):
        """测试添加事件到会话"""
        from app.gateway.event_broadcaster import EventSession

        session = EventSession(session_id="test-session")

        event1 = Event(
            event_type="test1",
            session_id="test-session",
            data={"index": 1}
        )

        event2 = Event(
            event_type="test2",
            session_id="test-session",
            data={"index": 2}
        )

        session.add_event(event1)
        session.add_event(event2)

        assert len(session.event_history) == 2
        assert session.last_event_id == event2.event_id

    def test_get_events_since(self):
        """测试获取指定事件之后的事件"""
        from app.gateway.event_broadcaster import EventSession

        session = EventSession(session_id="test-session")

        # 添加事件
        for i in range(5):
            event = Event(
                event_type=f"test{i}",
                session_id="test-session",
                data={"index": i}
            )
            session.add_event(event)

        events = session.get_events_since(session.event_history[1].event_id)

        # 应该返回第3、4、5个事件
        assert len(events) == 3

    def test_get_recent_events(self):
        """测试获取最近的事件"""
        from app.gateway.event_broadcaster import EventSession

        session = EventSession(session_id="test-session")

        # 添加10个事件
        for i in range(10):
            event = Event(
                event_type="test",
                session_id="test-session",
                data={"index": i}
            )
            session.add_event(event)

        # 获取最近5个事件
        recent = session.get_recent_events(5)

        assert len(recent) == 5
        # 应该是最后5个事件
        assert recent[0].data["index"] == 5
        assert recent[4].data["index"] == 9


class TestReplayEvents:
    """事件重放测试"""

    @pytest.mark.asyncio
    async def test_replay_all_events(self):
        """测试重放所有事件"""
        broadcaster = EventBroadcaster()
        await broadcaster.start()

        session_id = "test-session"

        # 创建初始事件
        events = [
            Event(
                event_type="phase",
                session_id=session_id,
                data={"phase": "planning"}
            ),
            Event(
                event_type="action",
                session_id=session_id,
                data={"action": "create_file"}
            )
        ]

        for event in events:
            await broadcaster.broadcast(event)

        # 重放所有事件（last_event_id=None）
        replayed = []
        async for event in broadcaster.replay_events(session_id):
            replayed.append(event)

        assert len(replayed) == 2
        assert replayed[0].event_type == "phase"
        assert replayed[1].event_type == "action"

        await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_replay_since_last_event(self):
        """测试从指定事件开始重放"""
        broadcaster = EventBroadcaster()
        await broadcaster.start()

        session_id = "test-session"

        # 创建事件
        events = []
        for i in range(5):
            event = Event(
                event_type=f"test{i}",
                session_id=session_id,
                data={"index": i}
            )
            events.append(event)
            await broadcaster.broadcast(event)

        # 从第2个事件开始重放
        last_event_id = events[1].event_id

        replayed = []
        async for event in broadcaster.replay_events(session_id, last_event_id):
            replayed.append(event)

        # 应该返回第3、4、5个事件
        assert len(replayed) == 3

        await broadcaster.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
