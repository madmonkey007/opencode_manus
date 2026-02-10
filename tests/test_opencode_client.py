"""
OpenCode Client 集成测试

测试 OpenCode Client 与 API 端点的完整集成流程
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import json
import time
from app.api import session_manager, event_stream_manager
from app.managers import SessionManager
from app.opencode_client import OpenCodeClient, execute_opencode_message


async def test_client_basic():
    """测试 OpenCodeClient 基本功能"""
    print("=" * 60)
    print("测试 1: OpenCodeClient 基本功能")
    print("=" * 60)

    # 创建测试会话
    session = await session_manager.create_session(title="Test Client Session")
    print(f"✓ 创建会话: {session.id}")

    # 创建客户端
    workspace_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../workspace"))
    client = OpenCodeClient(workspace_base)
    print(f"✓ 初始化 OpenCodeClient (workspace: {workspace_base})")

    # 订阅事件流
    queue = await event_stream_manager.subscribe(session.id)
    print(f"✓ 订阅事件流 (session: {session.id})")

    # 执行简单消息
    print("\n开始执行测试消息...")
    assistant_message_id = f"msg_test_{int(time.time())}"

    # 创建异步任务来收集事件
    events_received = []

    async def collect_events():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=10.0)
                event_data = json.loads(event)
                events_received.append(event_data)
                print(f"  收到事件: {event_data.get('type')}")
        except asyncio.TimeoutError:
            print("  事件收集超时，结束收集")

    # 启动事件收集和消息执行
    collect_task = asyncio.create_task(collect_events())

    # 执行消息（使用简单的提示）
    try:
        await client.execute_message(
            session_id=session.id,
            assistant_message_id=assistant_message_id,
            user_prompt="Say hello"
        )
        print("✓ 消息执行完成")
    except Exception as e:
        print(f"✗ 消息执行失败: {e}")

    # 等待事件收集完成
    await asyncio.sleep(2)
    collect_task.cancel()

    # 取消订阅
    await event_stream_manager.unsubscribe(session.id, queue)

    # 分析收到的事件
    print(f"\n✓ 总共收到 {len(events_received)} 个事件")
    event_types = [e.get('type') for e in events_received]
    print(f"  事件类型: {set(event_types)}")

    # 清理
    await session_manager.delete_session(session.id)
    print(f"✓ 清理会话: {session.id}")

    return len(events_received) > 0


async def test_api_send_message():
    """测试 API send_message 端点集成"""
    print("\n" + "=" * 60)
    print("测试 2: API send_message 端点集成")
    print("=" * 60)

    # 创建会话
    session = await session_manager.create_session(title="Test API Session")
    print(f"✓ 创建会话: {session.id}")

    # 订阅事件流
    queue = await event_stream_manager.subscribe(session.id)
    print(f"✓ 订阅事件流")

    # 模拟 API 请求
    from app.models import SendMessageRequest, MessagePart, PartType, PartContent
    from fastapi import BackgroundTasks
    from app.api import send_message

    # 构建请求
    request = SendMessageRequest(
        message_id=f"msg_user_{int(time.time())}",
        provider_id="anthropic",
        model_id="claude-3-5-sonnet-20241022",
        mode="auto",
        parts=[
            MessagePart(
                type=PartType.TEXT,
                content=PartContent(text="Hello, test message")
            )
        ]
    )

    print(f"✓ 构建请求: {request.message_id}")

    # 收集事件
    events_received = []

    async def collect_events():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                event_data = json.loads(event)
                events_received.append(event_data)
                print(f"  收到事件: {event_data.get('type')}")
        except asyncio.TimeoutError:
            print("  事件收集超时")

    # 这里不实际调用 send_message（因为它需要 FastAPI 上下文）
    # 而是直接调用后台任务函数
    collect_task = asyncio.create_task(collect_events())

    print("\n直接调用 execute_opencode_message...")

    try:
        assistant_id = f"msg_assistant_{int(time.time())}"
        await execute_opencode_message(
            session_id=session.id,
            message_id=assistant_id,
            user_prompt="Hello",
            workspace_base=os.path.abspath(os.path.join(os.path.dirname(__file__), "../workspace"))
        )
        print("✓ execute_opencode_message 完成")
    except Exception as e:
        print(f"✗ execute_opencode_message 失败: {e}")
        import traceback
        traceback.print_exc()

    # 等待事件
    await asyncio.sleep(3)
    collect_task.cancel()

    await event_stream_manager.unsubscribe(session.id, queue)

    print(f"\n✓ 收到 {len(events_received)} 个事件")

    # 清理
    await session_manager.delete_session(session.id)

    return len(events_received) > 0


async def test_event_stream_manager():
    """测试 EventStreamManager 功能"""
    print("\n" + "=" * 60)
    print("测试 3: EventStreamManager 功能")
    print("=" * 60)

    session = await session_manager.create_session(title="Test Event Stream")
    print(f"✓ 创建会话: {session.id}")

    # 创建多个订阅者
    queue1 = await event_stream_manager.subscribe(session.id)
    queue2 = await event_stream_manager.subscribe(session.id)
    print(f"✓ 创建 2 个订阅者")

    # 广播测试事件
    test_event = {
        "type": "test_event",
        "data": "Hello from test",
        "timestamp": int(time.time())
    }

    await event_stream_manager.broadcast(session.id, test_event)
    print(f"✓ 广播测试事件")

    # 验证两个队列都收到事件
    event1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
    event2 = await asyncio.wait_for(queue2.get(), timeout=1.0)

    event1_data = json.loads(event1)
    event2_data = json.loads(event2)

    assert event1_data == test_event, "queue1 收到的事件不匹配"
    assert event2_data == test_event, "queue2 收到的事件不匹配"

    print(f"✓ 两个订阅者都收到事件")

    # 取消订阅
    await event_stream_manager.unsubscribe(session.id, queue1)
    await event_stream_manager.unsubscribe(session.id, queue2)

    listener_count = event_stream_manager.get_listener_count(session.id)
    assert listener_count == 0, f"订阅者数量应为 0，实际为 {listener_count}"
    print(f"✓ 取消订阅成功，监听者数量: {listener_count}")

    # 清理
    await session_manager.delete_session(session.id)

    return True


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("OpenCode Client 集成测试套件")
    print("=" * 60)

    results = {}

    try:
        # 测试 1: EventStreamManager
        results['event_stream_manager'] = await test_event_stream_manager()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['event_stream_manager'] = False

    try:
        # 测试 2: OpenCodeClient 基本
        results['client_basic'] = await test_client_basic()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['client_basic'] = False

    try:
        # 测试 3: API 端点集成
        results['api_integration'] = await test_api_send_message()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['api_integration'] = False

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    print(f"\n总计: {passed_tests}/{total_tests} 测试通过")

    if passed_tests == total_tests:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print("\n⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
