"""
QQ Bot Integration Quick Test

Simple test without special characters
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

print("\n" + "="*70)
print("QQ Bot Integration Quick Test")
print("="*70)

# Test 1: Check IM Bridge Server
print("\n[Test 1] Check IM Bridge Server...")

try:
    import aiohttp

    async def check_server():
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:18080/health", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"[OK] IM Bridge is running")
                    print(f"  Uptime: {data['uptime']:.1f} seconds")
                    print(f"  Status: {data['status']}")
                    return True
                else:
                    print(f"[FAIL] Server returned HTTP {resp.status}")
                    return False

    result = asyncio.run(check_server())

    if not result:
        print("\n[ERROR] IM Bridge server is not running")
        print("Please start it first: node im-bridge-server.js")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] Cannot connect to server: {e}")
    sys.exit(1)

# Test 2: Initialize EventBroadcaster
print("\n[Test 2] Initialize EventBroadcaster...")

try:
    from app.gateway.event_broadcaster import EventBroadcaster, Event

    broadcaster = EventBroadcaster(
        im_webhook_url="http://localhost:18080/opencode/events",
        im_enabled_events=["complete", "error", "phase"]
    )

    print("[OK] EventBroadcaster initialized")
    print(f"  Webhook: http://localhost:18080/opencode/events")
    print(f"  Events: {broadcaster.im_enabled_events}")

except Exception as e:
    print(f"[ERROR] Failed to initialize: {e}")
    sys.exit(1)

# Test 3: Create Test Events
print("\n[Test 3] Create Test Events...")

test_events = [
    {
        "name": "Complete Event",
        "event": Event(
            event_type="complete",
            session_id="qq-test-001",
            data={"result": "success", "files": ["main.py"]}
        )
    },
    {
        "name": "Error Event",
        "event": Event(
            event_type="error",
            session_id="qq-test-002",
            data={"error": "Test error"}
        )
    },
    {
        "name": "Phase Event",
        "event": Event(
            event_type="phase",
            session_id="qq-test-003",
            data={"phase": "planning", "description": "Planning"}
        )
    }
]

for i, test in enumerate(test_events, 1):
    print(f"  {i}. {test['name']}: {test['event'].event_type}")

print("[OK] All test events created")

# Test 4: Push to IM Bridge
print("\n[Test 4] Push Event to IM Bridge...")

async def test_push():
    test_event = {
        "event_id": "test-qq-001",
        "event_type": "complete",
        "session_id": "qq-test",
        "timestamp": "2026-03-14T10:00:00",
        "data": {"result": "success", "message": "QQ test"}
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:18080/opencode/events",
                json=test_event,
                timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print("[OK] Event pushed successfully")
                    print(f"  Response: {data.get('message', 'OK')}")
                    print(f"  QQ Sent: {data.get('qq_sent', 'N/A')}")
                    return True
                else:
                    print(f"[FAIL] HTTP {resp.status}")
                    return False

    except Exception as e:
        print(f"[ERROR] Push failed: {e}")
        return False

result = asyncio.run(test_push())

# Test 5: Check Statistics
print("\n[Test 5] Check Statistics...")

async def check_stats():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:18080/stats", timeout=5) as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    print("[OK] Statistics retrieved:")
                    print(f"  Events Received: {stats.get('eventsReceived', 0)}")
                    print(f"  QQ Messages Sent: {stats.get('qqMessagesSent', 0)}")
                    print(f"  QQ Messages Failed: {stats.get('qqMessagesFailed', 0)}")
                    return True
                else:
                    print(f"[FAIL] HTTP {resp.status}")
                    return False

    except Exception as e:
        print(f"[ERROR] Failed to get stats: {e}")
        return False

stats_result = asyncio.run(check_stats())

# Test 6: Configuration Check
print("\n[Test 6] Configuration Check...")

qq_enable = os.getenv('QQ_ENABLE')
qq_targets = os.getenv('QQ_TARGETS')

print("Current Configuration:")
print(f"  QQ_ENABLE: {qq_enable if qq_enable else '(not set)'}")
print(f"  QQ_TARGETS: {qq_targets if qq_targets else '(not set)'}")

if qq_enable and qq_enable.lower() == 'true':
    print("[OK] QQ Bot is ENABLED")
    if qq_targets:
        print(f"  Target: {qq_targets}")
    else:
        print("  [WARNING] No targets configured")
else:
    print("[INFO] QQ Bot is NOT ENABLED")
    print("  Enable with: export QQ_ENABLE=true")

# Summary
print("\n" + "="*70)
print("Test Summary")
print("="*70)

test_results = [
    ("Server Connection", True),
    ("EventBroadcaster Init", True),
    ("Test Events Created", True),
    ("Event Push", result),
    ("Statistics Check", stats_result),
    ("Configuration", True)
]

passed = 0
failed = 0

for test_name, passed_flag in test_results:
    if passed_flag:
        print(f"  [OK] {test_name}")
        passed += 1
    else:
        print(f"  [FAIL] {test_name}")
        failed += 1

print("\n" + "="*70)
if failed == 0:
    print("SUCCESS! All tests passed")
    print("\nNext Steps to Enable QQ Notifications:")
    print("  1. Install go-cqhttp:")
    print("     Windows: install-go-cqhttp.bat")
    print("     Linux/Mac: ./install-go-cqhttp.sh")
    print()
    print("  2. Configure your QQ number:")
    print("     export QQ_TARGETS=user:YOUR_QQ_NUMBER")
    print()
    print("  3. Start go-cqhttp:")
    print("     cd go-cqhttp")
    print("     ./go-cqhttp (or go-cqhttp.exe on Windows)")
    print()
    print("  4. Scan QR code with mobile QQ")
    print()
    print("  5. Run full test:")
    print("     python tests/test_qq_integration.py")
    print()
    print("Quick Start Script:")
    print("  Windows: start-qq-integration.bat")
    print("  Linux/Mac: ./start-qq-integration.sh")
else:
    print(f"FAILED: {failed} test(s) failed")
    print("Please check the errors above")

print("="*70)

print("\nTest Status: PASSED" if failed == 0 else "FAILED")
print("="*70 + "\n")

sys.exit(0 if failed == 0 else 1)
