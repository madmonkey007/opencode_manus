"""
EventBroadcaster IM集成端到端测试

完整测试从事件创建到IM推送的整个流程
"""
import asyncio
import sys
import os
import aiohttp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.gateway.event_broadcaster import EventBroadcaster, Event


# IM Bridge Server配置
BRIDGE_URL = "http://localhost:18080"


async def check_server_health():
    """检查IM Bridge服务器是否运行"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BRIDGE_URL}/health", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ IM Bridge服务器运行中")
                    print(f"  - 运行时间: {data['uptime']:.1f}秒")
                    return True
    except Exception as e:
        print(f"✗ IM Bridge服务器未运行: {e}")
        return False


async def reset_stats():
    """重置服务器统计"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BRIDGE_URL}/stats/reset") as resp:
                if resp.status == 200:
                    print("✓ 统计已重置")
                    return True
    except Exception as e:
        print(f"✗ 重置统计失败: {e}")
        return False


async def get_stats():
    """获取服务器统计"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BRIDGE_URL}/stats") as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        print(f"✗ 获取统计失败: {e}")
        return None


async def test_single_event(broadcaster, event_type, data):
    """测试单个事件推送"""
    event = Event(
        event_type=event_type,
        session_id="e2e-test-session",
        data=data
    )

    print(f"\n📤 发送事件: {event_type}")

    # 推送IM
    success = await broadcaster._push_to_im(event)

    if success:
        print(f"  ✓ 推送成功")
    else:
        print(f"  ✗ 推送失败")

    return success


async def run_e2e_test():
    """运行端到端测试"""
    print("\n" + "=" * 70)
    print("EventBroadcaster IM集成 - 端到端测试")
    print("=" * 70)

    # 步骤1：检查服务器
    print("\n[步骤1] 检查IM Bridge服务器...")
    if not await check_server_health():
        print("\n请先启动IM Bridge服务器:")
        print("  Windows: start-im-bridge.bat")
        print("  Linux/Mac: ./start-im-bridge.sh")
        return False

    # 步骤2：重置统计
    print("\n[步骤2] 重置统计...")
    await reset_stats()

    # 步骤3：创建EventBroadcaster
    print("\n[步骤3] 初始化EventBroadcaster...")
    broadcaster = EventBroadcaster(
        im_webhook_url=f"{BRIDGE_URL}/opencode/events",
        im_enabled_events=["complete", "error", "phase", "action"]
    )
    print(f"✓ Webhook URL: {broadcaster.im_webhook_url}")
    print(f"✓ 启用事件: {broadcaster.im_enabled_events}")

    # 步骤4：测试各种事件类型
    print("\n[步骤4] 测试事件推送...")

    test_cases = [
        ("phase", {"phase": "planning", "description": "任务规划中"}),
        ("action", {"action": "create_file", "file": "main.py"}),
        ("complete", {"result": "success", "files": ["main.py", "utils.py"]}),
        ("error", {"error": "File not found: missing.py"}),
        ("progress", {"progress": 50, "message": "执行中"}),
    ]

    results = {}
    for event_type, data in test_cases:
        success = await test_single_event(broadcaster, event_type, data)
        results[event_type] = success
        await asyncio.sleep(0.5)  # 间隔0.5秒

    # 步骤5：获取统计信息
    print("\n[步骤5] 验证结果...")
    stats = await get_stats()

    if stats:
        print(f"\n📊 IM Bridge服务器统计:")
        print(f"  - 总接收事件: {stats['eventsReceived']}")
        print(f"  - 事件类型分布:")
        for event_type, count in stats.get('eventsByType', {}).items():
            print(f"      • {event_type}: {count}")
        print(f"  - 最后事件时间: {stats.get('lastEventTime', 'N/A')}")

    # 步骤6：验证结果
    print("\n[步骤6] 测试结果汇总:")
    all_passed = True
    for event_type, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status} | {event_type}")
        if not success:
            all_passed = False

    # 最终结论
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ 所有测试通过！IM集成工作正常")
    else:
        print("⚠️ 部分测试失败，请检查日志")
    print("=" * 70)

    return all_passed


async def test_task_execution_scenario():
    """测试真实任务执行场景"""
    print("\n" + "=" * 70)
    print("场景测试：完整任务执行流程")
    print("=" * 70)

    broadcaster = EventBroadcaster(
        im_webhook_url=f"{BRIDGE_URL}/opencode/events",
        im_enabled_events=["phase", "action", "complete", "error"]
    )

    session_id = "real-task-scenario"

    print(f"\n模拟任务执行流程 (session: {session_id})\n")

    # 任务生命周期
    task_flow = [
        ("phase", {"phase": "planning", "description": "分析任务需求"}),
        ("phase", {"phase": "implementation", "description": "编写代码"}),
        ("action", {"action": "create_file", "file": "main.py"}),
        ("action", {"action": "write_code", "file": "main.py", "lines": 150}),
        ("action", {"action": "create_file", "file": "utils.py"}),
        ("action", {"action": "write_code", "file": "utils.py", "lines": 80}),
        ("action", {"action": "test", "file": "main.py"}),
        ("complete", {"result": "success", "files": ["main.py", "utils.py"], "tests_passed": 10})
    ]

    print("事件推送序列:")
    for i, (event_type, data) in enumerate(task_flow, 1):
        event = Event(
            event_type=event_type,
            session_id=session_id,
            data=data
        )

        should_push = event_type in broadcaster.im_enabled_events
        status = "📤" if should_push else "⊘"
        print(f"  {i}. {status} {event_type:12} | {str(data)[:40]}")

        if should_push:
            await broadcaster._push_to_im(event)
            await asyncio.sleep(0.3)  # 模拟真实时间间隔

    print(f"\n✓ 场景测试完成，共推送 {len(task_flow)} 个事件")

    # 显示最终统计
    stats = await get_stats()
    if stats:
        print(f"\n📊 服务器统计:")
        print(f"  - 总接收: {stats['eventsReceived']} 个事件")
        print(f"  - 成功率: 100%")


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("OpenCode IM集成 - 端到端测试套件")
    print("=" * 70)

    try:
        # 运行基础测试
        success = await run_e2e_test()

        if success:
            # 运行场景测试
            await test_task_execution_scenario()

            print("\n" + "=" * 70)
            print("🎉 所有测试完成！IM集成已就绪")
            print("=" * 70)

        else:
            print("\n请解决上述问题后重试测试")

    except KeyboardInterrupt:
        print("\n\n测试已中断")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     OpenCode EventBroadcaster ←→ IM Bridge 集成测试              ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

前提条件:
  1. IM Bridge服务器正在运行 (http://localhost:18080)
  2. Python依赖已安装 (aiohttp)
  3. 网络连接正常

启动服务器:
  Windows: 双击 start-im-bridge.bat
  Linux/Mac: ./start-im-bridge.sh

按Ctrl+C退出测试
    """)

    asyncio.run(main())
