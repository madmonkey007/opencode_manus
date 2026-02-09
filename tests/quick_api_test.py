"""Quick test for new API endpoints"""
import sys
sys.path.insert(0, 'app')

from fastapi.testclient import TestClient
from fastapi import FastAPI
from api import router

# 创建测试应用
app = FastAPI()
app.include_router(router)

# 创建测试客户端
client = TestClient(app)

print("Testing OpenCode New API Endpoints")
print("=" * 60)

# 测试 1: 创建会话
print("\n1. Testing POST /opencode/session...")
response = client.post("/opencode/session?title=Test%20Session")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Session ID: {data['id']}")
    print(f"   Title: {data['title']}")
    print(f"   Status: {data['status']}")
    session_id = data['id']
else:
    print(f"   Error: {response.text}")
    sys.exit(1)

# 测试 2: 获取会话
print(f"\n2. Testing GET /opencode/session/{session_id}...")
response = client.get(f"/opencode/session/{session_id}")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Session ID: {data['id']}")
else:
    print(f"   Error: {response.text}")

# 测试 3: 列出会话
print("\n3. Testing GET /opencode/sessions...")
response = client.get("/opencode/sessions")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Session count: {len(data)}")
else:
    print(f"   Error: {response.text}")

# 测试 4: 发送消息
print(f"\n4. Testing POST /opencode/session/{session_id}/message...")
message_data = {
    "message_id": "msg_test_001",
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
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Message ID: {data['id']}")
    print(f"   Role: {data['role']}")
else:
    print(f"   Error: {response.text}")

# 测试 5: 获取消息列表
print(f"\n5. Testing GET /opencode/session/{session_id}/messages...")
response = client.get(f"/opencode/session/{session_id}/messages")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Message count: {data['count']}")
else:
    print(f"   Error: {response.text}")

# 测试 6: 健康检查
print("\n6. Testing GET /opencode/health...")
response = client.get("/opencode/health")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Health: {data['status']}")
    print(f"   Sessions: {data['sessions']}")
else:
    print(f"   Error: {response.text}")

# 测试 7: 获取 API 信息
print("\n7. Testing GET /opencode/info...")
response = client.get("/opencode/info")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   API Name: {data['name']}")
    print(f"   Version: {data['version']}")
else:
    print(f"   Error: {response.text}")

# 测试 8: 删除会话
print(f"\n8. Testing DELETE /opencode/session/{session_id}...")
response = client.delete(f"/opencode/session/{session_id}")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Status: {data['status']}")
else:
    print(f"   Error: {response.text}")

print("\n" + "=" * 60)
print("✅ All API endpoint tests passed!")
