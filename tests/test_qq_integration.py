"""
QQ Bot集成快速测试

验证QQ Bot配置和消息推送功能
"""
import asyncio
import sys
import os

# 测试go-cqhttp连接
async def test_go_cqhttp_connection():
    """测试go-cqhttp API连接"""
    print("\n" + "="*60)
    print("步骤1: 测试go-cqhttp连接")
    print("="*60)

    import aiohttp

    api_url = os.getenv('QQ_API_URL', 'http://localhost:3000')

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/get_login_info", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('retcode') == 0:
                        user_info = data.get('data', {})
                        print(f"✓ go-cqhttp连接成功")
                        print(f"  用户ID: {user_info.get('user_id')}")
                        print(f"  昵称: {user_info.get('nickname')}")
                        return True
                    else:
                        print(f"✗ go-cqhttp返回错误: {data.get('msg')}")
                        return False
                else:
                    print(f"✗ HTTP错误: {resp.status}")
                    return False

    except Exception as e:
        print(f"✗ 连接失败: {e}")
        print("\n请确保:")
        print("  1. go-cqhttp正在运行 (http://localhost:3000)")
        print("  2. 已完成QQ扫码登录")
        return False


async def test_send_qq_message():
    """测试发送QQ消息"""
    print("\n" + "="*60)
    print("步骤2: 测试发送QQ消息")
    print("="*60)

    import aiohttp

    api_url = os.getenv('QQ_API_URL', 'http://localhost:3000')
    targets = os.getenv('QQ_TARGETS', '')

    if not targets:
        print("✗ 未配置QQ_TARGETS")
        print("\n请设置环境变量:")
        print("  export QQ_TARGETS=user:123456")
        return False

    print(f"推送目标: {targets}")

    # 解析第一个目标
    first_target = targets.split(',')[0]
    target_type, target_id = first_target.split(':')

    test_message = "[OpenCode] 这是一条测试消息"

    try:
        async with aiohttp.ClientSession() as session:
            # 选择API端点
            if target_type == 'user':
                url = f"{api_url}/send_private_msg"
                payload = {
                    "user_id": int(target_id),
                    "message": test_message
                }
            elif target_type == 'group':
                url = f"{api_url}/send_group_msg"
                payload = {
                    "group_id": int(target_id),
                    "message": test_message
                }
            else:
                print(f"✗ 未知目标类型: {target_type}")
                return False

            # 发送消息
            async with session.post(url, json=payload, timeout=10) as resp:
                data = await resp.json()

                if data.get('retcode') == 0:
                    print(f"✓ 消息发送成功")
                    print(f"  目标: {target_type}:{target_id}")
                    print(f"  消息: {test_message}")
                    return True
                else:
                    print(f"✗ 消息发送失败: {data.get('msg')}")
                    print(f"  错误码: {data.get('retcode')}")
                    return False

    except Exception as e:
        print(f"✗ 发送失败: {e}")
        return False


async def test_im_bridge_integration():
    """测试IM Bridge服务器集成"""
    print("\n" + "="*60)
    print("步骤3: 测试IM Bridge服务器集成")
    print("="*60)

    import aiohttp

    bridge_url = 'http://localhost:18080'

    try:
        # 检查服务器状态
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{bridge_url}/health", timeout=5) as resp:
                if resp.status != 200:
                    print(f"✗ IM Bridge服务器未运行")
                    return False

        print("✓ IM Bridge服务器运行正常")

        # 发送测试事件
        test_event = {
            "event_id": "qq-test-001",
            "event_type": "complete",
            "session_id": "test-session",
            "timestamp": "2026-03-14T10:00:00",
            "data": {
                "result": "success",
                "message": "QQ集成测试",
                "test": True
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{bridge_url}/opencode/events",
                json=test_event,
                timeout=10
            ) as resp:
                data = await resp.json()

                if data.get('success'):
                    print(f"✓ 事件已推送到IM Bridge")
                    print(f"  QQ推送状态: {'已发送' if data.get('qq_sent') else '未启用'}")
                    return True
                else:
                    print(f"✗ 事件推送失败")
                    return False

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


async def check_statistics():
    """检查统计信息"""
    print("\n" + "="*60)
    print("步骤4: 检查统计信息")
    print("="*60)

    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:18080/stats", timeout=5) as resp:
                if resp.status == 200:
                    stats = await resp.json()

                    print(f"服务器统计:")
                    print(f"  接收事件: {stats.get('eventsReceived', 0)}")
                    print(f"  QQ消息发送: {stats.get('qqMessagesSent', 0)}")
                    print(f"  QQ消息失败: {stats.get('qqMessagesFailed', 0)}")

                    if stats.get('eventsReceived', 0) > 0:
                        print(f"\n✓ 集成工作正常")
                        return True
                    else:
                        print(f"\n⚠️ 尚未接收到事件")
                        return False

    except Exception as e:
        print(f"✗ 获取统计失败: {e}")
        return False


async def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("OpenCode QQ Bot集成测试")
    print("="*60)

    print("\n前提条件:")
    print("  1. go-cqhttp正在运行 (http://localhost:3000)")
    print("  2. 已完成QQ扫码登录")
    print("  3. IM Bridge服务器正在运行 (http://localhost:18080)")
    print("  4. 环境变量已配置 (QQ_ENABLE, QQ_TARGETS)")

    # 检查环境变量
    qq_enable = os.getenv('QQ_ENABLE')
    qq_targets = os.getenv('QQ_TARGETS')

    if not qq_enable or qq_enable != 'true':
        print("\n⚠️ QQ Bot未启用")
        print("请设置: export QQ_ENABLE=true")
        return

    if not qq_targets:
        print("\n⚠️ 未配置推送目标")
        print("请设置: export QQ_TARGETS=user:123456")
        return

    print(f"\n当前配置:")
    print(f"  QQ_ENABLE: {qq_enable}")
    print(f"  QQ_TARGETS: {qq_targets}")

    # 运行测试
    results = []

    # 测试1: go-cqhttp连接
    result1 = await test_go_cqhttp_connection()
    results.append(("go-cqhttp连接", result1))

    if not result1:
        print("\n⚠️ go-cqhttp连接失败，请先解决此问题")
        return

    # 测试2: 发送QQ消息
    result2 = await test_send_qq_message()
    results.append(("发送QQ消息", result2))

    # 测试3: IM Bridge集成
    result3 = await test_im_bridge_integration()
    results.append(("IM Bridge集成", result3))

    # 测试4: 统计信息
    result4 = await check_statistics()
    results.append(("统计检查", result4))

    # 总结
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} | {test_name}")

    all_passed = all(r for _, r in results)

    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过！QQ集成已就绪")
    else:
        print("⚠️ 部分测试失败，请检查上述问题")
    print("="*60)

    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试已中断")
        sys.exit(1)
