# -*- coding: utf-8 -*-
"""快速验证脚本 - 测试新 API 基本功能"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import requests

BASE_URL = "http://localhost:8088"


def test_health():
    """测试健康检查"""
    print("1. 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/opencode/health", timeout=5)
        data = response.json()
        print(f"   [OK] 状态: {data['status']}")
        return True
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False


def test_api_info():
    """测试 API 信息"""
    print("2. 测试 API 信息...")
    try:
        response = requests.get(f"{BASE_URL}/opencode/info", timeout=5)
        data = response.json()
        print(f"   [OK] 版本: {data['version']}")
        return True
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False


def test_create_session():
    """测试创建会话"""
    print("3. 测试创建会话...")
    try:
        response = requests.post(
            f"{BASE_URL}/opencode/session?title=Test%20Session",
            timeout=5
        )
        session = response.json()
        print(f"   [OK] 会话 ID: {session['id']}")
        return session['id']
    except Exception as e:
        print(f"   [FAIL] {e}")
        return None


def test_get_session(session_id):
    """测试获取会话"""
    print("4. 测试获取会话...")
    try:
        response = requests.get(
            f"{BASE_URL}/opencode/session/{session_id}",
            timeout=5
        )
        session = response.json()
        print(f"   [OK] 状态: {session['status']}")
        return True
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False


def test_list_sessions():
    """测试列出会话"""
    print("5. 测试列出会话...")
    try:
        response = requests.get(f"{BASE_URL}/opencode/sessions", timeout=5)
        sessions = response.json()
        print(f"   [OK] 会话数: {len(sessions)}")
        return True
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False


def test_send_message(session_id):
    """测试发送消息"""
    print("6. 测试发送消息...")
    try:
        import uuid
        message_id = f"msg_{uuid.uuid4().hex[:12]}"

        request_data = {
            "message_id": message_id,
            "provider_id": "anthropic",
            "model_id": "claude-3-5-sonnet-20241022",
            "mode": "auto",
            "parts": [{"type": "text", "text": "Hello"}]
        }

        response = requests.post(
            f"{BASE_URL}/opencode/session/{session_id}/message",
            json=request_data,
            timeout=10
        )
        result = response.json()
        print(f"   [OK] 助手消息 ID: {result['id']}")
        return True
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False


def test_delete_session(session_id):
    """测试删除会话"""
    print("7. 测试删除会话...")
    try:
        response = requests.delete(
            f"{BASE_URL}/opencode/session/{session_id}",
            timeout=5
        )
        data = response.json()
        print(f"   [OK] 状态: {data['status']}")
        return True
    except Exception as e:
        print(f"   [FAIL] {e}")
        return False


def main():
    """运行所有快速验证测试"""
    print("=" * 60)
    print("OpenCode 新 API 快速验证")
    print("=" * 60)
    print()

    results = []
    session_id = None

    # 测试 1-2（不需要 session_id）
    results.append(test_health())
    results.append(test_api_info())

    # 测试 3-4（需要 session_id）
    session_id = test_create_session()
    if session_id:
        results.append(True)
        results.append(test_get_session(session_id))
        results.append(test_list_sessions())
        results.append(test_send_message(session_id))
        results.append(test_delete_session(session_id))
    else:
        results.append(False)
        results.append(False)
        results.append(False)
        results.append(False)
        results.append(False)

    # 总结
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"结果: {passed}/{total} 测试通过")

    if passed == total:
        print("[SUCCESS] 所有测试通过!")
        return 0
    else:
        print(f"[FAILED] {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
