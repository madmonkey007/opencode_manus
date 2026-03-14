"""
OpenCode 事件分发器

支持多渠道实时事件推送：
- Web: Server-Sent Events (SSE)
- CLI: Stream 输出
- Mobile: WebSocket（预留）
- API: Webhook（预留）
"""
import asyncio
import json
import logging
import uuid
from typing import Dict, Set, Optional, Any, AsyncIterator, Callable
from datetime import datetime
from dataclasses import dataclass, field
from collections import deque, defaultdict
import weakref

logger = logging.getLogger(__name__)


# ============================================================================
# 事件模型
# ============================================================================

@dataclass
class Event:
    """事件对象"""
    event_type: str  # phase, action, progress, complete, error
    data: Dict[str, Any]
    session_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict())

    def to_sse(self) -> str:
        """转换为SSE格式"""
        return f"data: {self.to_json()}\n\n"


# ============================================================================
# 订阅者接口
# ============================================================================

class EventSubscriber:
    """事件订阅者基类"""

    def __init__(self, subscriber_id: str, channels: Set[str]):
        """
        初始化订阅者

        Args:
            subscriber_id: 订阅者ID
            channels: 订阅的渠道集合
        """
        self.subscriber_id = subscriber_id
        self.channels = channels
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.created_at = datetime.now()
        self.last_event_at: Optional[datetime] = None

    async def put_event(self, event: Event) -> bool:
        """
        放入事件到队列

        Args:
            event: 事件对象

        Returns:
            是否成功放入（队列未满）
        """
        try:
            self.queue.put_nowait(event)
            self.last_event_at = datetime.now()
            return True
        except asyncio.QueueFull:
            logger.warning(
                f"Subscriber {self.subscriber_id} queue full, "
                f"dropping event {event.event_id}"
            )
            return False

    async def get_event(self) -> Event:
        """从队列获取事件"""
        return await self.queue.get()

    def has_events(self) -> bool:
        """检查是否有待处理事件"""
        return not self.queue.empty()

    def queue_size(self) -> int:
        """获取队列大小"""
        return self.queue.qsize()


class SSESubscriber(EventSubscriber):
    """SSE订阅者（Web）"""

    def __init__(self, subscriber_id: str, session_id: str):
        super().__init__(subscriber_id, {"sse"})
        self.session_id = session_id


class StreamSubscriber(EventSubscriber):
    """流订阅者（CLI）"""

    def __init__(self, subscriber_id: str):
        super().__init__(subscriber_id, {"stream"})


# ============================================================================
# 事件会话（支持断线重连）
# ============================================================================

@dataclass
class EventSession:
    """事件会话（用于断线恢复）"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_event_id: Optional[str] = None
    event_history: deque = field(default_factory=lambda: deque(maxlen=1000))

    def add_event(self, event: Event) -> None:
        """添加事件到历史"""
        self.event_history.append(event)
        self.last_event_id = event.event_id

    def get_events_since(self, last_event_id: str) -> list:
        """获取指定事件ID之后的所有事件"""
        events = []
        found = False

        for event in self.event_history:
            if found:
                events.append(event)
            elif event.event_id == last_event_id:
                found = True

        return events

    def get_recent_events(self, count: int = 100) -> list:
        """获取最近的事件"""
        return list(self.event_history)[-count:]


# ============================================================================
# 事件分发器
# ============================================================================

class EventBroadcaster:
    """
    事件分发器

    功能：
    1. 多渠道事件广播
    2. 订阅管理
    3. 事件持久化（支持断线恢复）
    4. 背压处理
    """

    def __init__(
        self,
        max_history: int = 1000,
        cleanup_interval: int = 300,
        im_webhook_url: str = None,
        im_enabled_events: list = None
    ):
        """
        初始化事件分发器

        Args:
            max_history: 最大事件历史数量
            cleanup_interval: 清理间隔（秒）
            im_webhook_url: IM桥接服务webhook地址（用于message-bridge集成）
            im_enabled_events: 需要推送到IM的事件类型列表
        """
        # 订阅者管理
        # 格式: {subscriber_id: EventSubscriber}
        self._subscribers: Dict[str, EventSubscriber] = {}

        # 会话管理
        # 格式: {session_id: EventSession}
        self._sessions: Dict[str, EventSession] = {}

        # 订阅索引（按channel）
        # 格式: {channel: set(subscriber_ids)}
        self._channel_index: Dict[str, Set[str]] = defaultdict(set)

        # 配置
        self.max_history = max_history
        self.cleanup_interval = cleanup_interval

        # IM集成配置
        self.im_webhook_url = im_webhook_url
        self.im_enabled_events = im_enabled_events or ["complete", "error", "phase"]

        # 统计
        self._stats = {
            "events_broadcast": 0,
            "events_dropped": 0,
            "subscribers_added": 0,
            "subscribers_removed": 0,
            "im_notifications_sent": 0,
            "im_notifications_failed": 0
        }

        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None

        self.logger = logging.getLogger(__name__)
        self.logger.info("EventBroadcaster initialized")

    async def start(self) -> None:
        """启动事件分发器"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info("EventBroadcaster started")

    async def stop(self) -> None:
        """停止事件分发器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            self.logger.info("EventBroadcaster stopped")

    def subscribe(
        self,
        subscriber: EventSubscriber,
        session_id: str = None
    ) -> str:
        """
        订阅事件

        Args:
            subscriber: 订阅者对象
            session_id: 会话ID（用于断线恢复）

        Returns:
            订阅者ID
        """
        # 添加订阅者
        self._subscribers[subscriber.subscriber_id] = subscriber

        # 更新渠道索引
        for channel in subscriber.channels:
            self._channel_index[channel].add(subscriber.subscriber_id)

        # 创建或恢复会话
        if session_id:
            if session_id not in self._sessions:
                self._sessions[session_id] = EventSession(session_id=session_id)

        self._stats["subscribers_added"] += 1

        self.logger.info(
            f"Subscriber {subscriber.subscriber_id} added, "
            f"channels: {subscriber.channels}"
        )

        return subscriber.subscriber_id

    def unsubscribe(self, subscriber_id: str) -> bool:
        """
        取消订阅

        Args:
            subscriber_id: 订阅者ID

        Returns:
            是否成功
        """
        if subscriber_id not in self._subscribers:
            return False

        subscriber = self._subscribers[subscriber_id]

        # 从渠道索引中移除
        for channel in subscriber.channels:
            self._channel_index[channel].discard(subscriber_id)

        # 移除订阅者
        del self._subscribers[subscriber_id]

        self._stats["subscribers_removed"] += 1

        self.logger.info(f"Subscriber {subscriber_id} removed")
        return True

    async def broadcast(
        self,
        event: Event,
        channels: Set[str] = None
    ) -> int:
        """
        广播事件到订阅者

        Args:
            event: 事件对象
            channels: 目标渠道（None表示所有渠道）

        Returns:
            成功接收的订阅者数量
        """
        # 添加到会话历史
        if event.session_id in self._sessions:
            self._sessions[event.session_id].add_event(event)

        # 获取目标订阅者
        target_subscribers = self._get_target_subscribers(channels)

        # 并发发送事件
        tasks = [
            subscriber.put_event(event)
            for subscriber in target_subscribers.values()
        ]

        # 等待所有发送完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计成功数量
        success_count = sum(1 for r in results if r is True)

        self._stats["events_broadcast"] += 1

        if success_count < len(target_subscribers):
            dropped = len(target_subscribers) - success_count
            self._stats["events_dropped"] += dropped
            self.logger.warning(
                f"Event {event.event_id}: {success_count} delivered, "
                f"{dropped} dropped"
            )

        # 🆕 推送到IM桥接服务（如果配置且事件类型匹配）
        if self.im_webhook_url and event.event_type in self.im_enabled_events:
            await self._push_to_im(event)

        return success_count

    def _get_target_subscribers(
        self,
        channels: Set[str] = None
    ) -> Dict[str, EventSubscriber]:
        """
        获取目标订阅者

        Args:
            channels: 渠道过滤（None表示所有）

        Returns:
            订阅者字典
        """
        if channels is None:
            return self._subscribers.copy()

        # 根据渠道过滤
        subscriber_ids = set()
        for channel in channels:
            subscriber_ids.update(self._channel_index.get(channel, set()))

        return {
            sub_id: self._subscribers[sub_id]
            for sub_id in subscriber_ids
            if sub_id in self._subscribers
        }

    async def replay_events(
        self,
        session_id: str,
        last_event_id: Optional[str] = None
    ) -> AsyncIterator[Event]:
        """
        重放事件（用于断线恢复）

        Args:
            session_id: 会话ID
            last_event_id: 最后接收到的事件ID

        Yields:
            历史事件
        """
        if session_id not in self._sessions:
            self.logger.warning(f"Session {session_id} not found")
            return

        session = self._sessions[session_id]

        # 获取需要重放的事件
        if last_event_id:
            events = session.get_events_since(last_event_id)
        else:
            events = session.get_recent_events()

        # 逐个yield事件
        for event in events:
            yield event

    async def create_sse_stream(
        self,
        session_id: str
    ) -> AsyncIterator[str]:
        """
        创建SSE流（用于Web）

        Args:
            session_id: 会话ID

        Yields:
            SSE格式的字符串
        """
        # 创建SSE订阅者
        subscriber_id = f"sse-{session_id}-{uuid.uuid4().hex[:8]}"
        subscriber = SSESubscriber(subscriber_id, session_id)

        # 订阅
        self.subscribe(subscriber, session_id)

        self.logger.info(f"SSE stream created for {session_id}")

        try:
            # 发送SSE头部
            yield "event: connected\n"
            yield f"data: {{\"stream_id\": \"{subscriber_id}\"}}\n\n"

            # 持续发送事件
            while True:
                try:
                    # 等待事件（带超时，用于心跳）
                    event = await asyncio.wait_for(
                        subscriber.get_event(),
                        timeout=30.0  # 30秒心跳
                    )

                    # 发送事件
                    yield event.to_sse()

                except asyncio.TimeoutError:
                    # 发送心跳
                    yield ": heartbeat\n\n"

                except asyncio.CancelledError:
                    # 客户端断开连接
                    break

        finally:
            # 取消订阅
            self.unsubscribe(subscriber_id)
            self.logger.info(f"SSE stream closed for {session_id}")

    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话统计信息

        Args:
            session_id: 会话ID

        Returns:
            统计信息字典
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        return {
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "last_event_id": session.last_event_id,
            "event_count": len(session.event_history)
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        获取分发器统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_subscribers": len(self._subscribers),
            "total_sessions": len(self._sessions),
            "events_broadcast": self._stats["events_broadcast"],
            "events_dropped": self._stats["events_dropped"],
            "subscribers_added": self._stats["subscribers_added"],
            "subscribers_removed": self._stats["subscribers_removed"],
            "im_notifications_sent": self._stats["im_notifications_sent"],
            "im_notifications_failed": self._stats["im_notifications_failed"],
            "im_webhook_configured": self.im_webhook_url is not None,
            "channels": {
                channel: len(subscribers)
                for channel, subscribers in self._channel_index.items()
            }
        }

    async def _cleanup_loop(self) -> None:
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup(self) -> None:
        """清理过期资源"""
        now = datetime.now()

        # 清理不活跃的订阅者（超过1小时无活动）
        inactive_subscribers = []

        for sub_id, subscriber in self._subscribers.items():
            if subscriber.last_event_at:
                idle_time = (now - subscriber.last_event_at).total_seconds()
                if idle_time > 3600:  # 1小时
                    inactive_subscribers.append(sub_id)

        for sub_id in inactive_subscribers:
            self.unsubscribe(sub_id)

        if inactive_subscribers:
            self.logger.info(f"Cleaned up {len(inactive_subscribers)} inactive subscribers")

    async def _push_to_im(self, event: Event) -> bool:
        """
        推送事件到IM桥接服务

        Args:
            event: 事件对象

        Returns:
            是否成功推送
        """
        try:
            import aiohttp

            # 构建webhook payload
            payload = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "session_id": event.session_id,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            }

            # 发送webhook请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.im_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        self._stats["im_notifications_sent"] += 1
                        self.logger.info(
                            f"IM notification sent: {event.event_type} "
                            f"(session: {event.session_id})"
                        )
                        return True
                    else:
                        self._stats["im_notifications_failed"] += 1
                        self.logger.warning(
                            f"IM notification failed: HTTP {response.status} "
                            f"(event: {event.event_id})"
                        )
                        return False

        except asyncio.TimeoutError:
            self._stats["im_notifications_failed"] += 1
            self.logger.warning(f"IM notification timeout (event: {event.event_id})")
            return False

        except Exception as e:
            self._stats["im_notifications_failed"] += 1
            self.logger.error(f"IM notification error: {e} (event: {event.event_id})")
            return False


# ============================================================================
# 全局事件分发器
# ============================================================================

_global_broadcaster: Optional[EventBroadcaster] = None


def get_global_broadcaster() -> EventBroadcaster:
    """获取全局事件分发器实例"""
    global _global_broadcaster

    if _global_broadcaster is None:
        _global_broadcaster = EventBroadcaster()
        # 注意：需要手动调用 start()

    return _global_broadcaster


async def start_global_broadcaster() -> EventBroadcaster:
    """启动全局事件分发器"""
    global _global_broadcaster

    if _global_broadcaster is None:
        _global_broadcaster = EventBroadcaster()

    await _global_broadcaster.start()
    return _global_broadcaster


async def stop_global_broadcaster() -> None:
    """停止全局事件分发器"""
    global _global_broadcaster

    if _global_broadcaster is not None:
        await _global_broadcaster.stop()
        _global_broadcaster = None
