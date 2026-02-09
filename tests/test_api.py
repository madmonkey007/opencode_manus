"""
OpenCode 新架构 API 端点测试

运行测试：
    cd D:\manus\opencode
    pytest tests/test_api.py -v

或使用 FastAPI 测试客户端：
    python tests/test_api.py
"""
import pytest
import asyncio
import sys
import os

# 添加 app 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from fastapi.testclient import TestClient
from api import router, session_manager, event_stream_manager
from models import SessionStatus, MessageRole, generate_message_id


# ====================================================================
# Fixture
# ====================================================================

@pytest.fixture
def client():
    """创建测试客户端"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    return TestClient(app)


# ====================================================================
# Session Endpoints Tests
# ====================================================================

class TestSessionEndpoints:
    """Session 管理端点测试"""

    def test_create_session(self, client):
        """测试创建会话"""
        response = client.post("/opencode/session?title=Test%20Session")

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["id"].startswith("ses_")
        assert data["title"] == "Test Session"
        assert data["status"] == "active"
        assert "time" in data

    def test_get_session(self, client):
        """测试获取会话"""
        # 1. 创建会话
        create_response = client.post("/opencode/session")
        session_id = create_response.json()["id"]

        # 2. 获取会话
        response = client.get(f"/opencode/session/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id

    def test_get_nonexistent_session(self, client):
        """测试获取不存在的会话"""
        response = client.get("/opencode/session/ses_nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_session(self, client):
        """测试删除会话"""
        # 1. 创建会话
        create_response = client.post("/opencode/session")
        session_id = create_response.json()["id"]

        # 2. 删除会话
        response = client.delete(f"/opencode/session/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["session_id"] == session_id

        # 3. 验证已删除
        get_response = client.get(f"/opencode/session/{session_id}")
        assert get_response.status_code == 404

    def test_list_sessions(self, client):
        """测试列出会话"""
        # 创建多个会话
        client.post("/opencode/session?title=Session1")
        client.post("/opencode/session?title=Session2")

        # 列出所有会话
        response = client.get("/opencode/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_sessions_by_status(self, client):
        """测试按状态过滤会话"""
        # 创建会话
        create_response = client.post("/opencode/session")
        session_id = create_response.json()["id"]

        # 只列出活跃会话
        response = client.get("/opencode/sessions?status=active")

        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "active" for s in data)


# ====================================================================
# Message Endpoints Tests
# ====================================================================

class TestMessageEndpoints:
    """Message 管理端点测试"""

    def test_send_message(self, client):
        """测试发送消息"""
        # 1. 创建会话
        session_response = client.post("/opencode/session")
        session_id = session_response.json()["id"]

        # 2. 发送消息
        message_data = {
            "message_id": generate_message_id(),
            "provider_id": "anthropic",
            "model_id": "claude-3-5-sonnet-20241022",
            "mode": "auto",
            "parts": [
                {"type": "text", "text": "Hello, OpenCode!"}
            ]
        }

        response = client.post(
            f"/opencode/session/{session_id}/message",
            json=message_data
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["session_id"] == session_id
        assert data["role"] == "assistant"

    def test_send_message_to_nonexistent_session(self, client):
        """测试向不存在的会话发送消息"""
        message_data = {
            "message_id": generate_message_id(),
            "parts": [{"type": "text", "text": "Test"}]
        }

        response = client.post(
            "/opencode/session/ses_nonexistent/message",
            json=message_data
        )

        assert response.status_code == 404

    def test_get_messages(self, client):
        """测试获取消息列表"""
        # 1. 创建会话
        session_response = client.post("/opencode/session")
        session_id = session_response.json()["id"]

        # 2. 发送消息
        message_data = {
            "message_id": generate_message_id(),
            "parts": [{"type": "text", "text": "Test message"}]
        }
        client.post(f"/opencode/session/{session_id}/message", json=message_data)

        # 3. 获取消息
        response = client.get(f"/opencode/session/{session_id}/messages")

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == session_id
        assert "messages" in data
        assert data["count"] >= 2  # user + assistant message


# ====================================================================
# Utility Endpoints Tests
# ====================================================================

class TestUtilityEndpoints:
    """工具端点测试"""

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/opencode/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "sessions" in data

    def test_get_info(self, client):
        """测试获取 API 信息"""
        response = client.get("/opencode/info")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "endpoints" in data


# ====================================================================
# Integration Tests
# ====================================================================

class TestIntegration:
    """集成测试：多轮对话场景"""

    def test_multi_round_conversation(self, client):
        """测试多轮对话"""
        # 1. 创建会话
        session_response = client.post("/opencode/session?title=Multi-round")
        session_id = session_response.json()["id"]

        # 2. 第一轮：发送消息
        msg1_data = {
            "message_id": generate_message_id(),
            "parts": [{"type": "text", "text": "创建一个 Python 文件"}]
        }
        response1 = client.post(
            f"/opencode/session/{session_id}/message",
            json=msg1_data
        )
        assert response1.status_code == 200

        # 3. 第二轮：发送追问
        msg2_data = {
            "message_id": generate_message_id(),
            "parts": [{"type": "text", "text": "再添加一个函数"}]
        }
        response2 = client.post(
            f"/opencode/session/{session_id}/message",
            json=msg2_data
        )
        assert response2.status_code == 200

        # 4. 获取所有消息
        messages_response = client.get(f"/opencode/session/{session_id}/messages")
        assert messages_response.status_code == 200

        data = messages_response.json()
        # 应该有 4 条消息：user1, assistant1, user2, assistant2
        assert data["count"] >= 4


# ====================================================================
# Run Tests
# ====================================================================

if __name__ == "__main__":
    print("Running OpenCode API tests...")
    pytest.main([__file__, "-v", "-s"])
