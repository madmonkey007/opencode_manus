"""
OpenCode 新架构端到端测试

测试 Session + Message 架构的完整功能流程
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import json
import time
import requests
from typing import Dict, Any

# 配置
BASE_URL = "http://localhost:8088"
SESSION_TITLE = "E2E Test Session"


class OpenCodeE2ETester:
    """端到端测试类"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session_id = None
        self.message_id = None
        self.assistant_message_id = None
        self.events_received = []

    def _url(self, path: str) -> str:
        """构建完整 URL"""
        return f"{self.base_url}{path}"

    async def test_1_health_check(self) -> bool:
        """测试 1: 健康检查"""
        print("\n" + "=" * 60)
        print("测试 1: 健康检查")
        print("=" * 60)

        try:
            response = requests.get(self._url("/opencode/health"))
            data = response.json()

            print(f"✓ 状态: {data['status']}")
            print(f"✓ 时间戳: {data['timestamp']}")
            print(f"✓ 会话数: {data['sessions']}")

            return data["status"] == "healthy"
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False

    async def test_2_create_session(self) -> bool:
        """测试 2: 创建会话"""
        print("\n" + "=" * 60)
        print("测试 2: 创建会话")
        print("=" * 60)

        try:
            url = self._url(f"/opencode/session?title={SESSION_TITLE}")
            response = requests.post(url)
            session = response.json()

            self.session_id = session["id"]

            print(f"✓ 会话 ID: {session['id']}")
            print(f"✓ 标题: {session['title']}")
            print(f"✓ 版本: {session['version']}")
            print(f"✓ 状态: {session['status']}")
            print(f"✓ 创建时间: {session['time']['created']}")

            # 验证 ID 格式
            assert session["id"].startswith("ses_"), "Session ID should start with 'ses_'"

            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False

    async def test_3_get_session(self) -> bool:
        """测试 3: 获取会话"""
        print("\n" + "=" * 60)
        print("测试 3: 获取会话")
        print("=" * 60)

        try:
            url = self._url(f"/opencode/session/{self.session_id}")
            response = requests.get(url)
            session = response.json()

            print(f"✓ 会话 ID: {session['id']}")
            print(f"✓ 状态: {session['status']}")

            assert session["id"] == self.session_id, "Session ID mismatch"

            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False

    async def test_4_list_sessions(self) -> bool:
        """测试 4: 列出会话"""
        print("\n" + "=" * 60)
        print("测试 4: 列出会话")
        print("=" * 60)

        try:
            url = self._url("/opencode/sessions")
            response = requests.get(url)
            sessions = response.json()

            print(f"✓ 会话总数: {len(sessions)}")

            # 查找我们创建的会话
            found = False
            for session in sessions:
                if session["id"] == self.session_id:
                    print(f"✓ 找到测试会话: {session['title']}")
                    found = True
                    break

            assert found, "Test session not found in list"

            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False

    async def test_5_send_message(self) -> bool:
        """测试 5: 发送消息"""
        print("\n" + "=" * 60)
        print("测试 5: 发送消息")
        print("=" * 60)

        try:
            import uuid
            self.message_id = f"msg_{uuid.uuid4().hex[:12]}"

            request_data = {
                "message_id": self.message_id,
                "provider_id": "anthropic",
                "model_id": "claude-3-5-sonnet-20241022",
                "mode": "auto",
                "parts": [
                    {
                        "type": "text",
                        "text": "Say hello"
                    }
                ]
            }

            url = self._url(f"/opencode/session/{self.session_id}/message")
            response = requests.post(url, json=request_data)
            result = response.json()

            self.assistant_message_id = result["id"]

            print(f"✓ 用户消息 ID: {self.message_id}")
            print(f"✓ 助手消息 ID: {result['id']}")
            print(f"✓ 角色: {result['role']}")

            assert result["role"] == "assistant", "Response should be from assistant"

            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_6_get_messages(self) -> bool:
        """测试 6: 获取消息历史"""
        print("\n" + "=" * 60)
        print("测试 6: 获取消息历史")
        print("=" * 60)

        try:
            url = self._url(f"/opencode/session/{self.session_id}/messages")
            response = requests.get(url)
            data = response.json()

            print(f"✓ 会话 ID: {data['session_id']}")
            print(f"✓ 消息数: {data['count']}")

            for msg in data["messages"]:
                info = msg["info"]
                print(f"  - {info['role']}: {info['id']}")

            assert data["count"] >= 2, "Should have at least 2 messages (user + assistant)"

            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False

    async def test_7_sse_events(self) -> bool:
        """测试 7: SSE 事件流"""
        print("\n" + "=" * 60)
        print("测试 7: SSE 事件流")
        print("=" * 60)

        try:
            import sseclient

            url = self._url(f"/opencode/events?session_id={self.session_id}")
            events_client = sseclient.SSEClient(url)

            print("✓ 连接到 SSE 事件流")

            # 接收事件（10秒超时）
            start_time = time.time()
            event_count = 0
            event_types = set()

            while time.time() - start_time < 10:
                try:
                    event = events_client.next(timeout=2)
                    if event:
                        event_data = json.loads(event.data)
                        event_count += 1
                        event_types.add(event_data.get("type"))

                        print(f"  事件 {event_count}: {event_data.get('type')}")

                        # 收集事件
                        self.events_received.append(event_data)

                except StopIteration:
                    break

            events_client.close()

            print(f"✓ 接收到 {event_count} 个事件")
            print(f"✓ 事件类型: {event_types}")

            # 验证至少收到了连接事件
            assert "connection.established" in event_types, "Should receive connection event"

            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_8_delete_session(self) -> bool:
        """测试 8: 删除会话"""
        print("\n" + "=" * 60)
        print("测试 8: 删除会话")
        print("=" * 60)

        try:
            url = self._url(f"/opencode/session/{self.session_id}")
            response = requests.delete(url)
            data = response.json()

            print(f"✓ 状态: {data['status']}")
            print(f"✓ 会话 ID: {data['session_id']}")

            # 验证删除
            get_response = requests.get(self._url(f"/opencode/session/{self.session_id}"))
            assert get_response.status_code == 404, "Session should be deleted"

            print("✓ 会话已删除")

            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False

    async def test_9_api_info(self) -> bool:
        """测试 9: API 信息"""
        print("\n" + "=" * 60)
        print("测试 9: API 信息")
        print("=" * 60)

        try:
            url = self._url("/opencode/info")
            response = requests.get(url)
            data = response.json()

            print(f"✓ 名称: {data['name']}")
            print(f"✓ 版本: {data['version']}")
            print(f"✓ 描述: {data['description']}")
            print(f"✓ 端点:")

            for category, endpoints in data["endpoints"].items():
                print(f"  {category}:")
                for name, endpoint in endpoints.items():
                    print(f"    - {name}: {endpoint}")

            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("OpenCode 新架构端到端测试套件")
        print("=" * 70)

        results = {}

        tests = [
            ("健康检查", self.test_1_health_check),
            ("创建会话", self.test_2_create_session),
            ("获取会话", self.test_3_get_session),
            ("列出会话", self.test_4_list_sessions),
            ("发送消息", self.test_5_send_message),
            ("获取消息", self.test_6_get_messages),
            ("SSE 事件流", self.test_7_sse_events),
            ("删除会话", self.test_8_delete_session),
            ("API 信息", self.test_9_api_info),
        ]

        for name, test_func in tests:
            try:
                result = await test_func()
                results[name] = result
            except Exception as e:
                print(f"\n✗ 测试异常: {name} - {e}")
                import traceback
                traceback.print_exc()
                results[name] = False

        # 总结
        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)

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
            print(f"\n⚠️  {total_tests - passed_tests} 个测试失败")
            return 1


async def main():
    """主函数"""
    tester = OpenCodeE2ETester()
    exit_code = await tester.run_all_tests()
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
