#!/usr/bin/env python3
"""
OpenCode 快速验证脚本

快速验证服务是否正常运行，不需要等待长时间任务。
"""

import requests
import sys

BASE_URL = "http://localhost:8088"

def print_header(msg):
    print(f"\n{'=' * 50}")
    print(f"  {msg}")
    print(f"{'=' * 50}\n")

def print_success(msg):
    print(f"[PASS] {msg}")

def print_error(msg):
    print(f"[FAIL] {msg}")

def print_info(msg):
    print(f"[INFO] {msg}")

def test_service_available():
    """测试服务是否可用"""
    print_header("1. 测试服务可用性")

    try:
        response = requests.get(f"{BASE_URL}/opencode/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("服务正常运行")
            print_info(f"版本: {data.get('version', 'unknown')}")
            print_info(f"状态: {data.get('status', 'unknown')}")
            return True
        else:
            print_error(f"服务返回错误: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to service")
        print_info("请确保服务已启动: python -m app.main")
        return False
    except Exception as e:
        print_error(f"错误: {e}")
        return False

def test_create_session():
    """测试创建会话"""
    print_header("2. 测试创建会话")

    try:
        url = f"{BASE_URL}/opencode/session?title=快速测试"
        response = requests.post(url, timeout=5)

        if response.status_code == 200:
            session = response.json()
            session_id = session.get("id")
            print_success("会话创建成功")
            print_info(f"会话 ID: {session_id}")
            print_info(f"标题: {session.get('title', 'unknown')}")
            print_info(f"状态: {session.get('status', 'unknown')}")
            return session_id
        else:
            print_error(f"创建会话失败: HTTP {response.status_code}")
            return None
    except Exception as e:
        print_error(f"错误: {e}")
        return None

def test_send_message(session_id):
    """测试发送消息"""
    print_header("3. 测试发送消息")

    if not session_id:
        print_error("没有可用的会话 ID")
        return False

    try:
        import uuid
        message_id = f"msg_{uuid.uuid4().hex[:16]}"

        url = f"{BASE_URL}/opencode/session/{session_id}/message"
        payload = {
            "message_id": message_id,
            "provider_id": "anthropic",
            "model_id": "claude-3-5-sonnet-20241022",
            "mode": "auto",
            "parts": [{"type": "text", "text": "说你好"}]
        }

        response = requests.post(url, json=payload, timeout=5)

        if response.status_code == 200:
            result = response.json()
            print_success("消息发送成功")
            print_info(f"消息 ID: {message_id}")
            print_info(f"角色: {result.get('role', 'unknown')}")
            return True
        else:
            print_error(f"发送消息失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print_error(f"错误: {e}")
        return False

def test_get_messages(session_id):
    """测试获取消息历史"""
    print_header("4. 测试获取消息历史")

    if not session_id:
        print_error("没有可用的会话 ID")
        return False

    try:
        url = f"{BASE_URL}/opencode/session/{session_id}/messages"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            print_success("获取消息历史成功")
            print_info(f"消息数量: {len(messages)}")

            for msg in messages:
                role = msg.get("role", "unknown")
                parts = len(msg.get("parts", []))
                print(f"  - {role}: {parts} 个部分")

            return True
        else:
            print_error(f"获取消息失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print_error(f"错误: {e}")
        return False

def test_list_sessions():
    """测试列出会话"""
    print_header("5. 测试列出会话")

    try:
        url = f"{BASE_URL}/opencode/sessions"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            sessions = data.get("sessions", [])
            print_success("列出会话成功")
            print_info(f"会话总数: {len(sessions)}")
            return True
        else:
            print_error(f"列出会话失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print_error(f"错误: {e}")
        return False

def main():
    print_header("OpenCode Web Interface 快速验证")
    print_info(f"服务地址: {BASE_URL}")

    results = []

    # 运行测试
    results.append(test_service_available())
    session_id = test_create_session()
    results.append(session_id is not None)
    results.append(test_send_message(session_id))
    results.append(test_get_messages(session_id))
    results.append(test_list_sessions())

    # 汇总结果
    print_header("测试结果")
    total = len(results)
    passed = sum(results)

    print(f"总计: {total}")
    print_success(f"通过: {passed}")
    print_error(f"失败: {total - passed}")
    print(f"\n通过率: {passed / total * 100:.0f}%")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print("\n[WARNING] Some tests failed, please check service status")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
        sys.exit(1)
