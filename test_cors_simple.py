import subprocess
import sys
import os
import time
import requests

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000,http://localhost:8999'

print("Starting OpenCode service for CORS test...")

# 启动服务
if sys.platform == "win32":
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env,
        startupinfo=startupinfo
    )
else:
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

# 等待服务启动
print("Waiting for service to start...")
time.sleep(8)

# 测试CORS
print("\n=== Testing CORS Security ===")

test_cases = [
    ("Allowed origin", "http://localhost:3000", True),
    ("Malicious origin", "http://evil.com", False),
]

for name, origin, should_allow in test_cases:
    print(f"\nTesting: {name}")
    print(f"  Origin: {origin}")
    
    try:
        headers = {"Origin": origin}
        if origin:
            headers["Access-Control-Request-Method"] = "POST"
        
        response = requests.options(
            "http://localhost:8999/health",
            headers=headers,
            timeout=5
        )
        
        allowed_origin = response.headers.get("Access-Control-Allow-Origin", "")
        
        if should_allow:
            if allowed_origin == origin:
                print(f"  Result: PASS - Origin correctly allowed")
            else:
                print(f"  Result: FAIL - Origin should be allowed but was denied")
        else:
            if allowed_origin == "*":
                print(f"  Result: FAIL - Wildcard detected (security issue)")
            elif allowed_origin:
                print(f"  Result: FAIL - Origin should be denied but was allowed")
            else:
                print(f"  Result: PASS - Origin correctly denied")
                
    except Exception as e:
        print(f"  Result: ERROR - {e}")

# 停止服务
print("\nStopping service...")
process.terminate()
process.wait()
print("Service stopped")