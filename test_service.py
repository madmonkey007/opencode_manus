import requests
import time

print("Testing OpenCode service...")

# 等待服务启动
for i in range(10):
    try:
        response = requests.get("http://localhost:8999/health", timeout=5)
        if response.status_code == 200:
            print("✅ Service is healthy!")
            print(f"Response: {response.text}")
            break
    except requests.exceptions.ConnectionError:
        print(f"Waiting for service to start... ({i+1}/10)")
        time.sleep(2)
else:
    print("❌ Service failed to start")
    exit(1)

# 测试安全修复
print("\n=== Testing Security Fixes ===")

# 1. 测试路径遍历防护
print("\n1. Testing Path Traversal Protection...")
try:
    response = requests.get("http://localhost:8999/files?path=../../../etc/passwd", timeout=5)
    if response.status_code == 400:
        print("✅ Path traversal attack blocked!")
    else:
        print(f"⚠️ Unexpected response code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# 2. 测试CORS
print("\n2. Testing CORS...")
try:
    response = requests.options(
        "http://localhost:8999/health",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST"
        },
        timeout=5
    )
    if "Access-Control-Allow-Origin" in response.headers:
        origin = response.headers["Access-Control-Allow-Origin"]
        if origin == "*":
            print("⚠️ CORS allows all origins (should be restricted)")
        else:
            print(f"✅ CORS allows origin: {origin}")
    else:
        print("ℹ️ No CORS headers present")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Test Complete ===")