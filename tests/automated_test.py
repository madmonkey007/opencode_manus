#!/usr/bin/env python3
"""
OpenCode Web Interface v2.0 - 自动化测试脚本

测试新 API 的所有核心功能：
1. 健康检查
2. 会话管理
3. 消息发送
4. SSE 事件流
5. 多轮对话
6. 文件预览
7. 历史回溯

使用方法:
    python tests/automated_test.py

选项:
    --base-url: 指定服务地址（默认: http://localhost:8088）
    --verbose: 显示详细日志
    --skip-slow: 跳过耗时测试
"""

import asyncio
import json
import time
import sys
import argparse
from typing import Optional, Dict, List, Any
from datetime import datetime

try:
    import requests
except ImportError:
    print("❌ 缺少依赖: requests")
    print("请安装: pip install requests")
    sys.exit(1)

try:
    from sseclient import SSEClient
except ImportError:
    print("❌ 缺少依赖: sseclient-py")
    print("请安装: pip install sseclient-py")
    sys.exit(1)


# ==================== 配置 ====================

class Config:
    BASE_URL = "http://localhost:8088"
    TIMEOUT = 10
    SSE_TIMEOUT = 30
    VERBOSE = False
    SKIP_SLOW = False


# ==================== 颜色输出 ====================

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_success(msg: str):
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")


def print_error(msg: str):
    print(f"{Colors.FAIL}✗{Colors.ENDC} {msg}")


def print_info(msg: str):
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {msg}")


def print_warning(msg: str):
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {msg}")


def print_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{msg}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.ENDC}\n")


def log(msg: str):
    """详细日志（仅在 verbose 模式下显示）"""
    if Config.VERBOSE:
        print(f"  [DEBUG] {msg}")


# ==================== 测试结果 ====================

class TestResult:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []

    def add_pass(self, test_name: str):
        self.total += 1
        self.passed += 1
        print_success(f"{test_name}")

    def add_fail(self, test_name: str, error: str):
        self.total += 1
        self.failed += 1
        print_error(f"{test_name}")
        self.errors.append((test_name, error))
        log(f"错误: {error}")

    def add_skip(self, test_name: str, reason: str):
        self.total += 1
        self.skipped += 1
        print_warning(f"{test_name} (跳过: {reason})")

    def print_summary(self):
        print_header("测试结果汇总")
        print(f"总计: {self.total}")
        print_success(f"通过: {self.passed}")
        if self.failed > 0:
            print_error(f"失败: {self.failed}")
        if self.skipped > 0:
            print_warning(f"跳过: {self.skipped}")

        if self.errors:
            print(f"\n{Colors.FAIL}失败详情:{Colors.ENDC}")
            for test_name, error in self.errors:
                print(f"  • {test_name}")
                log(f"    {error}")

        print(f"\n通过率: {self.passed / self.total * 100:.1f}%")

        return self.failed == 0


# ==================== 测试类 ====================

class OpenCodeTester:
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or Config.BASE_URL).rstrip('/')
        self.result = TestResult()
        self.session_id = None
        self.message_id = None
        self.events_received = []

    def _url(self, path: str) -> str:
        """构建完整 URL"""
        return f"{self.base_url}{path}"

    # ==================== 测试 1: 健康检查 ====================

    def test_health_check(self) -> bool:
        """测试健康检查端点"""
        test_name = "健康检查"

        try:
            response = requests.get(self._url("/opencode/health"), timeout=Config.TIMEOUT)
            log(f"状态码: {response.status_code}")
            log(f"响应: {response.text}")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.result.add_pass(test_name)
                    print_info(f"版本: {data.get('version', 'unknown')}")
                    return True
                else:
                    self.result.add_fail(test_name, f"状态不健康: {data}")
                    return False
            else:
                self.result.add_fail(test_name, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 测试 2: API 信息 ====================

    def test_api_info(self) -> bool:
        """测试 API 信息端点"""
        test_name = "API 信息"

        try:
            response = requests.get(self._url("/opencode/info"), timeout=Config.TIMEOUT)
            log(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.result.add_pass(test_name)
                log(f"API 版本: {data.get('api_version', 'unknown')}")
                return True
            else:
                self.result.add_fail(test_name, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 测试 3: 创建会话 ====================

    def test_create_session(self) -> bool:
        """测试创建会话"""
        test_name = "创建会话"

        try:
            url = self._url("/opencode/session?title=自动化测试会话")
            response = requests.post(url, timeout=Config.TIMEOUT)
            log(f"POST {url}")
            log(f"状态码: {response.status_code}")

            if response.status_code == 200:
                session = response.json()
                self.session_id = session.get("id")

                if self.session_id and self.session_id.startswith("ses_"):
                    self.result.add_pass(test_name)
                    print_info(f"会话 ID: {self.session_id}")
                    log(f"会话详情: {json.dumps(session, indent=2, ensure_ascii=False)}")
                    return True
                else:
                    self.result.add_fail(test_name, f"无效的会话 ID: {self.session_id}")
                    return False
            else:
                self.result.add_fail(test_name, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 测试 4: 获取会话 ====================

    def test_get_session(self) -> bool:
        """测试获取会话信息"""
        test_name = "获取会话"

        if not self.session_id:
            self.result.add_skip(test_name, "没有可用的会话 ID")
            return False

        try:
            url = self._url(f"/opencode/session/{self.session_id}")
            response = requests.get(url, timeout=Config.TIMEOUT)
            log(f"GET {url}")
            log(f"状态码: {response.status_code}")

            if response.status_code == 200:
                session = response.json()
                if session.get("id") == self.session_id:
                    self.result.add_pass(test_name)
                    log(f"会话状态: {session.get('status', 'unknown')}")
                    return True
                else:
                    self.result.add_fail(test_name, "会话 ID 不匹配")
                    return False
            else:
                self.result.add_fail(test_name, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 测试 5: 列出会话 ====================

    def test_list_sessions(self) -> bool:
        """测试列出所有会话"""
        test_name = "列出会话"

        try:
            url = self._url("/opencode/sessions")
            response = requests.get(url, timeout=Config.TIMEOUT)
            log(f"GET {url}")
            log(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                sessions = data.get("sessions", [])
                self.result.add_pass(test_name)
                print_info(f"会话数量: {len(sessions)}")
                log(f"会话列表: {[s.get('id') for s in sessions]}")
                return True
            else:
                self.result.add_fail(test_name, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 测试 6: 发送消息 ====================

    def test_send_message(self) -> bool:
        """测试发送消息"""
        test_name = "发送消息"

        if not self.session_id:
            self.result.add_skip(test_name, "没有可用的会话 ID")
            return False

        try:
            import uuid
            self.message_id = f"msg_{uuid.uuid4().hex[:16]}"

            url = self._url(f"/opencode/session/{self.session_id}/message")
            payload = {
                "message_id": self.message_id,
                "provider_id": "anthropic",
                "model_id": "claude-3-5-sonnet-20241022",
                "mode": "auto",
                "parts": [
                    {
                        "type": "text",
                        "text": "说你好"
                    }
                ]
            }

            log(f"POST {url}")
            log(f"载荷: {json.dumps(payload, indent=2, ensure_ascii=False)}")

            response = requests.post(url, json=payload, timeout=Config.TIMEOUT)
            log(f"状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                role = result.get("role")

                if role == "assistant":
                    self.result.add_pass(test_name)
                    print_info(f"消息角色: {role}")
                    log(f"消息详情: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    return True
                else:
                    self.result.add_fail(test_name, f"意外的角色: {role}")
                    return False
            else:
                self.result.add_fail(test_name, f"HTTP {response.status_code}: {response.text}")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 测试 7: SSE 事件流 ====================

    def test_sse_events(self) -> bool:
        """测试 SSE 事件流"""
        test_name = "SSE 事件流"

        if not self.session_id:
            self.result.add_skip(test_name, "没有可用的会话 ID")
            return False

        if Config.SKIP_SLOW:
            self.result.add_skip(test_name, "跳过耗时测试")
            return False

        try:
            url = self._url(f"/opencode/events?session_id={self.session_id}")
            log(f"SSE 连接: {url}")

            print_info("等待 SSE 事件（最多 30 秒）...")

            start_time = time.time()
            event_count = 0
            event_types = set()

            events_client = SSEClient(url)

            for event in events_client.events():
                if time.time() - start_time > Config.SSE_TIMEOUT:
                    log("达到超时时间")
                    break

                if event:
                    event_count += 1
                    try:
                        data = json.loads(event.data)
                        event_type = data.get("type", "unknown")
                        event_types.add(event_type)
                        self.events_received.append(data)

                        log(f"事件 #{event_count}: {event_type}")

                        # 收集到足够事件后停止
                        if event_count >= 5:
                            log("已收集足够事件")
                            break
                    except json.JSONDecodeError:
                        log(f"无法解析事件: {event.data}")

            if event_count > 0:
                self.result.add_pass(test_name)
                print_info(f"接收事件数: {event_count}")
                print_info(f"事件类型: {', '.join(event_types)}")
                return True
            else:
                self.result.add_fail(test_name, "未接收到任何事件")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 测试 8: 获取消息历史 ====================

    def test_get_messages(self) -> bool:
        """测试获取消息历史"""
        test_name = "获取消息历史"

        if not self.session_id:
            self.result.add_skip(test_name, "没有可用的会话 ID")
            return False

        try:
            url = self._url(f"/opencode/session/{self.session_id}/messages")
            response = requests.get(url, timeout=Config.TIMEOUT)
            log(f"GET {url}")
            log(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                self.result.add_pass(test_name)
                print_info(f"消息数量: {len(messages)}")

                for msg in messages:
                    role = msg.get("role", "unknown")
                    parts_count = len(msg.get("parts", []))
                    log(f"  - {role}: {parts_count} 个部分")

                return True
            else:
                self.result.add_fail(test_name, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 测试 9: 多轮对话 ====================

    def test_multi_turn_conversation(self) -> bool:
        """测试多轮对话"""
        test_name = "多轮对话"

        if Config.SKIP_SLOW:
            self.result.add_skip(test_name, "跳过耗时测试")
            return False

        if not self.session_id:
            self.result.add_skip(test_name, "没有可用的会话 ID")
            return False

        try:
            import uuid

            # 第一轮：创建文件
            message_id_1 = f"msg_{uuid.uuid4().hex[:16]}"
            url = self._url(f"/opencode/session/{self.session_id}/message")
            payload = {
                "message_id": message_id_1,
                "provider_id": "anthropic",
                "model_id": "claude-3-5-sonnet-20241022",
                "mode": "auto",
                "parts": [{"type": "text", "text": "创建一个名为 test.txt 的文件，内容是 'Hello World'"}]
            }

            log(f"第一轮: POST {url}")
            response = requests.post(url, json=payload, timeout=Config.TIMEOUT)

            if response.status_code != 200:
                self.result.add_fail(test_name, f"第一轮失败: HTTP {response.status_code}")
                return False

            log("第一轮消息发送成功，等待 2 秒...")
            time.sleep(2)

            # 第二轮：修改文件
            message_id_2 = f"msg_{uuid.uuid4().hex[:16]}"
            payload = {
                "message_id": message_id_2,
                "provider_id": "anthropic",
                "model_id": "claude-3-5-sonnet-20241022",
                "mode": "auto",
                "parts": [{"type": "text", "text": "修改 test.txt，内容改为 'Hello OpenCode'"}]
            }

            log(f"第二轮: POST {url}")
            response = requests.post(url, json=payload, timeout=Config.TIMEOUT)

            if response.status_code != 200:
                self.result.add_fail(test_name, f"第二轮失败: HTTP {response.status_code}")
                return False

            # 获取消息历史验证
            time.sleep(1)
            messages_url = self._url(f"/opencode/session/{self.session_id}/messages")
            messages_response = requests.get(messages_url, timeout=Config.TIMEOUT)

            if messages_response.status_code == 200:
                data = messages_response.json()
                messages = data.get("messages", [])

                # 统计消息数量
                user_messages = [m for m in messages if m.get("role") == "user"]
                assistant_messages = [m for m in messages if m.get("role") == "assistant"]

                if len(user_messages) >= 2:
                    self.result.add_pass(test_name)
                    print_info(f"用户消息: {len(user_messages)}")
                    print_info(f"助手消息: {len(assistant_messages)}")
                    return True
                else:
                    self.result.add_fail(test_name, f"消息数量不足: {len(user_messages)} < 2")
                    return False
            else:
                self.result.add_fail(test_name, "获取消息历史失败")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 测试 10: 删除会话 ====================

    def test_delete_session(self) -> bool:
        """测试删除会话"""
        test_name = "删除会话"

        if not self.session_id:
            self.result.add_skip(test_name, "没有可用的会话 ID")
            return False

        try:
            url = self._url(f"/opencode/session/{self.session_id}")
            response = requests.delete(url, timeout=Config.TIMEOUT)
            log(f"DELETE {url}")
            log(f"状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                if result.get("success") or result.get("deleted"):
                    self.result.add_pass(test_name)
                    return True
                else:
                    self.result.add_fail(test_name, f"删除失败: {result}")
                    return False
            else:
                self.result.add_fail(test_name, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.result.add_fail(test_name, str(e))
            return False

    # ==================== 运行所有测试 ====================

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print_header("OpenCode Web Interface v2.0 - 自动化测试")
        print_info(f"服务地址: {self.base_url}")
        print_info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 测试序列
        tests = [
            ("基础功能", [
                self.test_health_check,
                self.test_api_info,
            ]),
            ("会话管理", [
                self.test_create_session,
                self.test_get_session,
                self.test_list_sessions,
            ]),
            ("消息功能", [
                self.test_send_message,
                self.test_get_messages,
            ]),
            ("事件流", [
                self.test_sse_events,
            ]),
            ("高级功能", [
                self.test_multi_turn_conversation,
            ]),
            ("清理", [
                self.test_delete_session,
            ]),
        ]

        for category, category_tests in tests:
            print_header(f"{category}")
            for test_func in category_tests:
                try:
                    test_func()
                except Exception as e:
                    print_error(f"测试异常: {test_func.__name__}: {e}")

        print_info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return self.result.print_summary()


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(description="OpenCode Web Interface 自动化测试")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8088",
        help="服务地址（默认: http://localhost:8088）"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志"
    )
    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="跳过耗时测试"
    )

    args = parser.parse_args()

    # 更新配置
    Config.BASE_URL = args.base_url
    Config.VERBOSE = args.verbose
    Config.SKIP_SLOW = args.skip_slow

    # 运行测试
    tester = OpenCodeTester(base_url=args.base_url)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
