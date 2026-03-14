"""
事件分发器使用示例

展示如何使用事件分发器实现实时事件推送
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.gateway.event_broadcaster import (
    EventBroadcaster,
    Event,
    SSESubscriber,
    StreamSubscriber
)


async def example_basic_broadcast():
    """示例：基础事件广播"""
    print("\n=== 示例1：基础事件广播 ===\n")

    # 创建事件分发器
    broadcaster = EventBroadcaster()
    await broadcaster.start()

    # 创建订阅者
    sse_sub = SSESubscriber("sse-sub-1", "session-123")
    stream_sub = StreamSubscriber("stream-sub-1")

    # 订阅
    broadcaster.subscribe(sse_sub, "session-123")
    broadcaster.subscribe(stream_sub)

    print("已创建2个订阅者")

    # 创建事件
    events = [
        Event(
            event_type="phase",
            session_id="session-123",
            data={"phase": "planning", "description": "任务规划中"}
        ),
        Event(
            event_type="action",
            session_id="session-123",
            data={"action": "create_file", "file": "main.py"}
        ),
        Event(
            event_type="complete",
            session_id="session-123",
            data={"result": "success"}
        )
    ]

    # 广播事件
    for event in events:
        count = await broadcaster.broadcast(event)
        print(f"事件 {event.event_type}: 已发送给 {count} 个订阅者")

    # 查看订阅者队列
    print(f"\nSSE订阅者队列大小: {sse_sub.queue_size()}")
    print(f"Stream订阅者队列大小: {stream_sub.queue_size()}")

    # 获取事件
    event = await sse_sub.get_event()
    print(f"\nSSE订阅者接收到事件: {event.event_type}")

    # 查看统计
    stats = broadcaster.get_stats()
    print(f"\n分发器统计:")
    print(f"  总订阅者: {stats['total_subscribers']}")
    print(f"  总会话: {stats['total_sessions']}")
    print(f"  已广播事件: {stats['events_broadcast']}")

    await broadcaster.stop()


async def example_sse_stream():
    """示例：SSE流"""
    print("\n=== 示例2：SSE流 ===\n")

    broadcaster = EventBroadcaster()
    await broadcaster.start()

    session_id = "test-session"

    # 模拟客户端订阅SSE流
    print("创建SSE流...")

    # 在实际使用中，这会是FastAPI的StreamingResponse
    # 这里模拟发送事件
    async def simulate_client():
        # 创建SSE流
        async for sse_data in broadcaster.create_sse_stream(session_id):
            print(f"SSE数据: {sse_data.strip()}")

            # 模拟客户端接收几个事件后断开
            if "phase" in sse_data:
                break
            if "action" in sse_data:
                break

    # 模拟发送事件
    async def send_events():
        await asyncio.sleep(0.5)

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

    # 并发运行
    await asyncio.gather(
        simulate_client(),
        send_events()
    )

    await broadcaster.stop()


async def example_replay_events():
    """示例：事件重放（断线恢复）"""
    print("\n=== 示例3：事件重放 ===\n")

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
        ),
        Event(
            event_type="progress",
            session_id=session_id,
            data={"progress": 50}
        )
    ]

    # 广播事件
    for event in events:
        await broadcaster.broadcast(event)

    print(f"已广播 {len(events)} 个事件")

    # 模拟客户端断线重连
    print("\n客户端断线...")
    await asyncio.sleep(0.5)

    print("客户端重连，请求重放...")
    last_event_id = events[1].event_id  # 只收到了前2个事件

    # 重放事件
    replay_count = 0
    async for event in broadcaster.replay_events(session_id, last_event_id):
        replay_count += 1
        print(f"重放事件 {replay_count}: {event.event_type}")

    await broadcaster.stop()


async def example_channel_filtering():
    """示例：渠道过滤"""
    print("\n=== 示例4：渠道过滤 ===\n")

    broadcaster = EventBroadcaster()
    await broadcaster.start()

    # 创建不同渠道的订阅者
    sse_sub = SSESubscriber("sse-1", "session-1")
    stream_sub = StreamSubscriber("stream-1")

    broadcaster.subscribe(sse_sub, "session-1")
    broadcaster.subscribe(stream_sub)

    print("已创建SSE和Stream订阅者")

    # 创建事件
    event = Event(
        event_type="test",
        session_id="session-1",
        data={"message": "test"}
    )

    # 只广播到SSE渠道
    count = await broadcaster.broadcast(event, channels={"sse"})
    print(f"\n广播到SSE渠道: {count} 个订阅者")

    # 广播到所有渠道
    count = await broadcaster.broadcast(event)
    print(f"广播到所有渠道: {count} 个订阅者")

    await broadcaster.stop()


async def example_statistics():
    """示例：统计信息"""
    print("\n=== 示例5：统计信息 ===\n")

    broadcaster = EventBroadcaster()
    await broadcaster.start()

    # 创建多个订阅者
    for i in range(5):
        subscriber = SSESubscriber(f"sse-{i}", f"session-{i}")
        broadcaster.subscribe(subscriber, f"session-{i}")

    # 广播一些事件
    for i in range(10):
        event = Event(
            event_type="test",
            session_id="session-1",
            data={"index": i}
        )
        await broadcaster.broadcast(event)

    # 获取统计
    stats = broadcaster.get_stats()
    print(f"分发器统计:")
    print(f"  总订阅者: {stats['total_subscribers']}")
    print(f"  总会话: {stats['total_sessions']}")
    print(f"  已广播事件: {stats['events_broadcast']}")
    print(f"  丢弃事件: {stats['events_dropped']}")
    print(f"  渠道分布: {stats['channels']}")

    # 获取会话统计
    session_stats = broadcaster.get_session_stats("session-1")
    if session_stats:
        print(f"\n会话 session-1 统计:")
        print(f"  创建时间: {session_stats['created_at']}")
        print(f"  事件数量: {session_stats['event_count']}")
        print(f"  最后事件ID: {session_stats['last_event_id']}")

    await broadcaster.stop()


async def example_heartbeat():
    """示例：心跳机制"""
    print("\n=== 示例6：心跳机制 ===\n")

    broadcaster = EventBroadcaster()
    await broadcaster.start()

    session_id = "test-session"

    # 创建SSE流
    print("创建SSE流（30秒心跳）...")

    event_count = 0
    timeout_task = asyncio.create_task(asyncio.sleep(5))  # 5秒后停止

    async def receive_events():
        nonlocal event_count
        async for sse_data in broadcaster.create_sse_stream(session_id):
            if "heartbeat" in sse_data:
                print(f"💓 心跳")
            else:
                event_count += 1
                print(f"📨 事件 {event_count}: {sse_data.strip()[:50]}...")

    # 发送一个事件
    async def send_single_event():
        await asyncio.sleep(1)
        event = Event(
            event_type="test",
            session_id=session_id,
            data={"message": "test"}
        )
        await broadcaster.broadcast(event)

    # 并发运行
    await asyncio.gather(
        receive_events(),
        send_single_event(),
        timeout_task
    )

    print(f"\n共接收到 {event_count} 个事件和若干心跳")

    await broadcaster.stop()


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("OpenCode 事件分发器演示")
    print("=" * 60)

    # 示例1：基础事件广播
    await example_basic_broadcast()

    # 示例2：SSE流
    await example_sse_stream()

    # 示例3：事件重放
    await example_replay_events()

    # 示例4：渠道过滤
    await example_channel_filtering()

    # 示例5：统计信息
    await example_statistics()

    # 示例6：心跳机制
    await example_heartbeat()

    print("\n" + "=" * 60)
    print("所有示例执行完毕")


if __name__ == "__main__":
    asyncio.run(main())
