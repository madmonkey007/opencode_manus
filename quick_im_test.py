"""
快速IM集成测试
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

try:
    from app.gateway.event_broadcaster import EventBroadcaster, Event
    print("[OK] EventBroadcaster imported")
except Exception as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

async def main():
    print("\n" + "="*60)
    print("IM集成快速测试")
    print("="*60 + "\n")

    # Step 1: Create broadcaster
    print("[Step 1] 创建EventBroadcaster...")
    broadcaster = EventBroadcaster(
        im_webhook_url="http://localhost:18080/opencode/events",
        im_enabled_events=["complete", "error"]
    )
    print(f"  ✓ Webhook: {broadcaster.im_webhook_url}")

    # Step 2: Create event
    print("\n[Step 2] 创建测试事件...")
    event = Event(
        event_type="complete",
        session_id="quick-test-123",
        data={"result": "success", "test": True}
    )
    print(f"  ✓ 事件: {event.event_type}")

    # Step 3: Push to IM
    print("\n[Step 3] 推送到IM...")
    try:
        success = await broadcaster._push_to_im(event)
        if success:
            print("  ✓ 推送成功!")
        else:
            print("  ✗ 推送失败")
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False

    # Step 4: Check stats
    print("\n[Step 4] 验证结果...")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:18080/stats", timeout=5) as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    print(f"  ✓ 服务器接收事件数: {stats['eventsReceived']}")
                    if stats['eventsReceived'] > 0:
                        print("\n" + "="*60)
                        print("✅ 集成测试成功!")
                        print("="*60)
                        return True
                else:
                    print(f"  ✗ 服务器返回错误: {resp.status}")
    except Exception as e:
        print(f"  ✗ 无法连接到服务器: {e}")

    print("\n" + "="*60)
    print("⚠️ 测试未通过")
    print("="*60)
    return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n测试已中断")
        sys.exit(1)
