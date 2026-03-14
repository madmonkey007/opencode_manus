"""
EventBroadcaster IM集成测试

测试 EventBroadcaster 与 message-bridge 的webhook集成
"""
import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.gateway.event_broadcaster import (
    EventBroadcaster,
    Event,
    SSESubscriber
)


class TestIMIntegration:
    """IM集成测试"""

    @pytest.mark.asyncio
    async def test_broadcaster_with_im_webhook(self):
        """测试带IM webhook的广播器初始化"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events",
            im_enabled_events=["complete", "error"]
        )

        assert broadcaster.im_webhook_url == "http://localhost:18080/opencode/events"
        assert broadcaster.im_enabled_events == ["complete", "error"]
        assert "im_notifications_sent" in broadcaster._stats
        assert "im_notifications_failed" in broadcaster._stats

    @pytest.mark.asyncio
    async def test_push_to_im_success(self):
        """测试成功推送IM通知"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events"
        )

        event = Event(
            event_type="complete",
            session_id="test-session",
            data={"result": "success"}
        )

        # Mock aiohttp.ClientSession
        mock_response = AsyncMock()
        mock_response.status = 200

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            success = await broadcaster._push_to_im(event)

        assert success is True
        assert broadcaster._stats["im_notifications_sent"] == 1
        assert broadcaster._stats["im_notifications_failed"] == 0

    @pytest.mark.asyncio
    async def test_push_to_im_http_error(self):
        """测试HTTP错误响应"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events"
        )

        event = Event(
            event_type="error",
            session_id="test-session",
            data={"error": "test error"}
        )

        # Mock 错误响应
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            success = await broadcaster._push_to_im(event)

        assert success is False
        assert broadcaster._stats["im_notifications_sent"] == 0
        assert broadcaster._stats["im_notifications_failed"] == 1

    @pytest.mark.asyncio
    async def test_push_to_im_timeout(self):
        """测试推送超时"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events"
        )

        event = Event(
            event_type="phase",
            session_id="test-session",
            data={"phase": "planning"}
        )

        # Mock 超时
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__.side_effect = asyncio.TimeoutError()
            mock_session_class.return_value = mock_session

            success = await broadcaster._push_to_im(event)

        assert success is False
        assert broadcaster._stats["im_notifications_failed"] == 1

    @pytest.mark.asyncio
    async def test_broadcast_with_im_enabled(self):
        """测试广播时自动推送IM（事件类型匹配）"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events",
            im_enabled_events=["complete", "error"]
        )
        await broadcaster.start()

        # Mock IM推送
        mock_push = AsyncMock(return_value=True)
        broadcaster._push_to_im = mock_push

        # 创建complete事件（在im_enabled_events中）
        event = Event(
            event_type="complete",
            session_id="test-session",
            data={"result": "success"}
        )

        await broadcaster.broadcast(event)

        # 验证IM推送被调用
        mock_push.assert_called_once_with(event)

        await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_broadcast_with_im_disabled_event_type(self):
        """测试事件类型不匹配时不推送IM"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events",
            im_enabled_events=["complete", "error"]
        )
        await broadcaster.start()

        # Mock IM推送
        mock_push = AsyncMock(return_value=True)
        broadcaster._push_to_im = mock_push

        # 创建action事件（不在im_enabled_events中）
        event = Event(
            event_type="action",
            session_id="test-session",
            data={"action": "create_file"}
        )

        await broadcaster.broadcast(event)

        # 验证IM推送未被调用
        mock_push.assert_not_called()

        await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_broadcast_without_im_webhook(self):
        """测试没有配置webhook时不推送IM"""
        broadcaster = EventBroadcaster(
            # im_webhook_url=None (默认)
        )
        await broadcaster.start()

        # Mock IM推送
        mock_push = AsyncMock(return_value=True)
        broadcaster._push_to_im = mock_push

        event = Event(
            event_type="complete",
            session_id="test-session",
            data={"result": "success"}
        )

        await broadcaster.broadcast(event)

        # 验证IM推送未被调用（因为没有配置webhook）
        mock_push.assert_not_called()

        await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_get_stats_includes_im_metrics(self):
        """测试统计信息包含IM指标"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events"
        )

        # 模拟一些统计
        broadcaster._stats["im_notifications_sent"] = 5
        broadcaster._stats["im_notifications_failed"] = 2

        stats = broadcaster.get_stats()

        assert stats["im_notifications_sent"] == 5
        assert stats["im_notifications_failed"] == 2
        assert stats["im_webhook_configured"] is True

    @pytest.mark.asyncio
    async def test_push_to_im_payload_format(self):
        """测试推送payload格式正确"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events"
        )

        event = Event(
            event_type="complete",
            session_id="test-session",
            data={"result": "success", "files": ["main.py"]}
        )

        # Mock 并捕获payload
        captured_payload = {}

        async def mock_post(url, json=None, timeout=None):
            captured_payload.update(json)
            mock_resp = AsyncMock()
            mock_resp.status = 200
            return mock_resp

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.post = mock_post

        with patch('aiohttp.ClientSession', return_value=mock_session):
            await broadcaster._push_to_im(event)

        # 验证payload格式
        assert captured_payload["event_type"] == "complete"
        assert captured_payload["session_id"] == "test-session"
        assert captured_payload["data"]["result"] == "success"
        assert "event_id" in captured_payload
        assert "timestamp" in captured_payload

    @pytest.mark.asyncio
    async def test_multiple_event_types_filtering(self):
        """测试多种事件类型的过滤"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events",
            im_enabled_events=["complete", "error", "phase"]
        )
        await broadcaster.start()

        mock_push = AsyncMock(return_value=True)
        broadcaster._push_to_im = mock_push

        events = [
            Event(event_type="complete", session_id="s1", data={}),
            Event(event_type="error", session_id="s1", data={}),
            Event(event_type="phase", session_id="s1", data={}),
            Event(event_type="action", session_id="s1", data={}),  # 不在列表中
            Event(event_type="progress", session_id="s1", data={}),  # 不在列表中
        ]

        for event in events:
            await broadcaster.broadcast(event)

        # 验证只有前3个事件被推送
        assert mock_push.call_count == 3

        await broadcaster.stop()


class TestIMIntegrationScenarios:
    """IM集成场景测试"""

    @pytest.mark.asyncio
    async def test_task_execution_flow_with_im(self):
        """测试完整任务执行流程的IM通知"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events",
            im_enabled_events=["phase", "action", "complete", "error"]
        )
        await broadcaster.start()

        mock_push = AsyncMock(return_value=True)
        broadcaster._push_to_im = mock_push

        session_id = "task-123"

        # 模拟任务执行流程
        events = [
            Event(event_type="phase", session_id=session_id,
                  data={"phase": "planning", "description": "任务规划中"}),
            Event(event_type="action", session_id=session_id,
                  data={"action": "create_file", "file": "main.py"}),
            Event(event_type="progress", session_id=session_id,
                  data={"progress": 50, "message": "执行中"}),
            Event(event_type="complete", session_id=session_id,
                  data={"result": "success", "files": ["main.py", "utils.py"]}),
        ]

        for event in events:
            await broadcaster.broadcast(event)

        # 验证所有事件都被推送（除了progress不在enabled列表）
        assert mock_push.call_count == 4

        # 验证事件顺序
        calls = mock_push.call_args_list
        assert calls[0][0][0].event_type == "phase"
        assert calls[1][0][0].event_type == "action"
        assert calls[2][0][0].event_type == "complete"  # progress被跳过
        assert calls[3][0][0].event_type == "complete"

        await broadcaster.stop()

    @pytest.mark.asyncio
    async def test_error_handling_doesnt_block_broadcast(self):
        """测试IM推送失败不影响正常的SSE/Stream分发"""
        broadcaster = EventBroadcaster(
            im_webhook_url="http://localhost:18080/opencode/events"
        )
        await broadcaster.start()

        # 创建SSE订阅者
        subscriber = SSESubscriber("test-sub", "test-session")
        broadcaster.subscribe(subscriber, "test-session")

        # Mock IM推送失败
        mock_push = AsyncMock(return_value=False)
        broadcaster._push_to_im = mock_push

        event = Event(
            event_type="complete",
            session_id="test-session",
            data={"result": "success"}
        )

        # 广播应该成功（SSE订阅者收到）
        count = await broadcaster.broadcast(event)

        # IM推送失败，但SSE订阅者应该收到
        assert count == 1
        assert subscriber.queue_size() == 1

        await broadcaster.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
