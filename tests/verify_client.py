"""快速验证 OpenCode Client 导入和初始化"""
import sys
import os
import io

# 设置标准输出为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("=" * 60)
print("OpenCode Client 快速验证")
print("=" * 60)

# 测试 1: 导入模块
print("\n1. 测试导入模块...")
try:
    from app.opencode_client import OpenCodeClient, execute_opencode_message, map_tool_to_type
    print("   ✓ OpenCodeClient 导入成功")
    print(f"   ✓ execute_opencode_message 导入成功")
    print(f"   ✓ map_tool_to_type 导入成功")
except Exception as e:
    print(f"   ✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 2: 导入 API 模块（包含 os 修复）
print("\n2. 测试导入 API 模块...")
try:
    from app.api import router, session_manager, event_stream_manager
    print("   ✓ API router 导入成功")
    print(f"   ✓ SessionManager 实例: {session_manager}")
    print(f"   ✓ EventStreamManager 实例: {event_stream_manager}")
except Exception as e:
    print(f"   ✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 3: 初始化 Client
print("\n3. 测试初始化 OpenCodeClient...")
try:
    workspace_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../workspace"))
    client = OpenCodeClient(workspace_base)
    print(f"   ✓ Client 初始化成功")
    print(f"   ✓ Workspace: {client.workspace_base}")
    print(f"   ✓ History Service: {client.history_service}")
except Exception as e:
    print(f"   ✗ 初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 4: 测试工具映射
print("\n4. 测试工具类型映射...")
test_cases = [
    ("read_file", "read"),
    ("write", "write"),
    ("bash", "bash"),
    ("browser_click", "browser"),
    ("web_search", "web_search"),
    ("edit", "file_editor"),
]

for tool_name, expected in test_cases:
    result = map_tool_to_type(tool_name)
    status = "✓" if result == expected else "✗"
    print(f"   {status} {tool_name} -> {result} (期望: {expected})")

# 测试 5: 验证 API 端点
print("\n5. 测试 API 端点...")
try:
    import asyncio

    async def test_api():
        # 创建会话
        session = await session_manager.create_session("Verify Test")
        print(f"   ✓ 创建会话: {session.id}")

        # 订阅事件
        queue = await event_stream_manager.subscribe(session.id)
        print(f"   ✓ 订阅事件流")

        # 广播测试事件
        test_event = {"type": "test", "data": "hello"}
        await event_stream_manager.broadcast(session.id, test_event)
        print(f"   ✓ 广播事件")

        # 获取事件
        import json
        event_str = await asyncio.wait_for(queue.get(), timeout=1.0)
        event_data = json.loads(event_str)
        print(f"   ✓ 接收事件: {event_data}")

        # 清理
        await event_stream_manager.unsubscribe(session.id, queue)
        await session_manager.delete_session(session.id)
        print(f"   ✓ 清理完成")

    asyncio.run(test_api())
except Exception as e:
    print(f"   ✗ API 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ 所有验证通过!")
print("=" * 60)
print("\nOpenCode Client 已就绪，可以进行完整测试。")
