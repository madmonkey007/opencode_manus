"""
EventBroadcaster IM集成演示

展示如何配置和使用EventBroadcaster的IM推送功能
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.gateway.event_broadcaster import (
    EventBroadcaster,
    Event
)


async def demo_basic_config():
    """演示1：基础配置"""
    print("\n=== 演示1：EventBroadcaster基础配置 ===\n")

    # 创建带IM webhook的广播器
    broadcaster = EventBroadcaster(
        max_history=1000,
        im_webhook_url="http://localhost:18080/opencode/events",
        im_enabled_events=["complete", "error", "phase"]
    )

    print("✓ EventBroadcaster已初始化")
    print(f"  - IM Webhook URL: {broadcaster.im_webhook_url}")
    print(f"  - IM启用事件: {broadcaster.im_enabled_events}")
    print(f"  - 统计指标: {list(broadcaster._stats.keys())}")


async def demo_event_creation():
    """演示2：创建不同类型的事件"""
    print("\n=== 演示2：创建不同类型的事件 ===\n")

    events = [
        Event(
            event_type="phase",
            session_id="task-001",
            data={"phase": "planning", "description": "任务规划中"}
        ),
        Event(
            event_type="action",
            session_id="task-001",
            data={"action": "create_file", "file": "main.py"}
        ),
        Event(
            event_type="progress",
            session_id="task-001",
            data={"progress": 50, "message": "执行中"}
        ),
        Event(
            event_type="complete",
            session_id="task-001",
            data={"result": "success", "files": ["main.py", "utils.py"]}
        ),
        Event(
            event_type="error",
            session_id="task-002",
            data={"error": "File not found: missing.py"}
        )
    ]

    print("创建了5个测试事件：")
    for i, event in enumerate(events, 1):
        print(f"{i}. {event.event_type:12} | session: {event.session_id}")

    return events


async def demo_filtering():
    """演示3：事件过滤"""
    print("\n=== 演示3：事件过滤机制 ===\n")

    # 配置只推送complete和error事件
    broadcaster = EventBroadcaster(
        im_webhook_url="http://localhost:18080/opencode/events",
        im_enabled_events=["complete", "error"]  # 只推送这两种
    )

    events = [
        Event(event_type="phase", session_id="s1", data={}),
        Event(event_type="action", session_id="s1", data={}),
        Event(event_type="complete", session_id="s1", data={}),  # ✓ 会推送
        Event(event_type="error", session_id="s1", data={}),    # ✓ 会推送
    ]

    print(f"配置的推送事件: {broadcaster.im_enabled_events}")
    print("\n事件过滤结果：")

    for event in events:
        should_push = event.event_type in broadcaster.im_enabled_events
        status = "✓ 会推送到IM" if should_push else "✗ 不推送"
        print(f"  {event.event_type:12} | {status}")


async def demo_statistics():
    """演示4：统计信息"""
    print("\n=== 演示4：IM推送统计 ===\n")

    broadcaster = EventBroadcaster(
        im_webhook_url="http://localhost:18080/opencode/events"
    )

    # 模拟一些统计
    broadcaster._stats["im_notifications_sent"] = 15
    broadcaster._stats["im_notifications_failed"] = 3

    stats = broadcaster.get_stats()

    print("IM推送统计：")
    print(f"  成功推送: {stats['im_notifications_sent']}")
    print(f"  推送失败: {stats['im_notifications_failed']}")
    print(f"  成功率: {stats['im_notifications_sent'] / (stats['im_notifications_sent'] + stats['im_notifications_failed']) * 100:.1f}%")
    print(f"  Webhook已配置: {stats['im_webhook_configured']}")


async def demo_task_execution_flow():
    """演示5：完整任务执行流程"""
    print("\n=== 演示5：完整任务执行流程 ===\n")

    broadcaster = EventBroadcaster(
        im_webhook_url="http://localhost:18080/opencode/events",
        im_enabled_events=["phase", "action", "complete", "error"]
    )

    session_id = "real-task-123"

    print(f"模拟任务执行流程 (session: {session_id})\n")

    # 任务生命周期事件
    task_events = [
        ("phase", {"phase": "planning", "description": "任务规划"}),
        ("action", {"action": "create_file", "file": "main.py"}),
        ("action", {"action": "write_code", "file": "main.py", "lines": 50}),
        ("progress", {"progress": 30, "message": "代码编写中"}),
        ("action", {"action": "test", "file": "main.py"}),
        ("progress", {"progress": 80, "message": "测试中"}),
        ("complete", {"result": "success", "files": ["main.py"], "tests_passed": 5})
    ]

    for i, (event_type, data) in enumerate(task_events, 1):
        event = Event(
            event_type=event_type,
            session_id=session_id,
            data=data
        )

        should_push = event_type in broadcaster.im_enabled_events
        status = "📤 推送IM" if should_push else "   本地"

        print(f"{i}. {event_type:12} | {status} | {str(data)[:50]}")

    print("\n说明：")
    print("  - ✓ 会推送到IM的事件：phase, action, complete, error")
    print("  - ✗ 不推送的事件：progress（不在im_enabled_events中）")


async def demo_configuration_comparison():
    """演示6：不同配置对比"""
    print("\n=== 演示6：配置方案对比 ===\n")

    configs = [
        {
            "name": "最小化配置",
            "im_enabled_events": ["complete", "error"],
            "description": "只推送任务完成和失败通知"
        },
        {
            "name": "标准配置",
            "im_enabled_events": ["complete", "error", "phase"],
            "description": "推送关键状态变更"
        },
        {
            "name": "详细配置",
            "im_enabled_events": ["complete", "error", "phase", "action", "progress"],
            "description": "推送所有事件，适合调试"
        },
        {
            "name": "自定义配置",
            "im_enabled_events": ["progress"],
            "description": "只推送进度更新"
        }
    ]

    print(f"{'配置方案':<12} | {'事件数量':<8} | {'事件列表'}")
    print("-" * 70)

    for config in configs:
        events = config["im_enabled_events"]
        print(f"{config['name']:<12} | {len(events):<8} | {', '.join(events)}")

    print("\n推荐配置：")
    print("  - 生产环境: 标准配置（减少噪音，关注关键状态）")
    print("  - 开发调试: 详细配置（全面监控任务执行）")
    print("  - 移动端: 最小化配置（减少通知频率）")


async def demo_message_format():
    """演示7：IM消息格式"""
    print("\n=== 演示7：IM消息格式建议 ===\n")

    event_examples = [
        ("complete", {"result": "success"}, "✅ 任务完成\n结果: success"),
        ("error", {"error": "File not found"}, "❌ 任务失败\n错误: File not found"),
        ("phase", {"phase": "planning", "description": "任务规划"}, "🔄 任务阶段\n阶段: planning\n任务规划"),
        ("action", {"action": "create_file", "file": "main.py"}, "⚙️ 执行操作\n创建文件 → main.py"),
        ("progress", {"progress": 50, "message": "执行中"}, "📊 任务进度\n50%\n执行中"),
    ]

    print("事件 → IM消息格式映射：\n")

    for event_type, data, suggested_message in event_examples:
        print(f"{event_type.upper():12}")
        print(f"  数据: {data}")
        print(f"  建议消息:")
        for line in suggested_message.split('\n'):
            print(f"    {line}")
        print()


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("EventBroadcaster IM集成演示")
    print("=" * 70)

    await demo_basic_config()
    await demo_event_creation()
    await demo_filtering()
    await demo_statistics()
    await demo_task_execution_flow()
    await demo_configuration_comparison()
    await demo_message_format()

    print("\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)

    print("\n后续步骤：")
    print("  1. 部署message-bridge接收端点（参考 docs/message-bridge-integration.js）")
    print("  2. 配置环境变量 OPENCODE_IM_WEBHOOK_URL")
    print("  3. 启动EventBroadcaster并测试推送")
    print("  4. 在IM平台（飞书/Telegram）接收任务通知")
    print("\n详细文档：docs/IM_INTEGRATION_GUIDE.md")


if __name__ == "__main__":
    asyncio.run(main())
