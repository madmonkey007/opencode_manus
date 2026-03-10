# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import time
import requests

# 设置Windows环境变量以支持UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("启动OpenCode服务...")

# 在Windows中使用正确的编码启动服务
if sys.platform == "win32":
    # 使用code page 65001 (UTF-8)
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    
    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONLEGACYWINDOWSSTDIO'] = '0'
    
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

print("等待服务启动...")
time.sleep(5)

# 检查服务是否启动
for i in range(10):
    try:
        response = requests.get("http://localhost:8999/health", timeout=2)
        if response.status_code == 200:
            print(f"✅ 服务启动成功！")
            print(f"健康检查响应: {response.text}")
            break
    except requests.exceptions.ConnectionError:
        print(f"等待服务启动... ({i+1}/10)")
        time.sleep(2)
else:
    print("❌ 服务启动失败")
    
    # 读取错误信息
    stdout, stderr = process.communicate(timeout=5)
    if stderr:
        print(f"错误信息:\n{stderr}")
    if stdout:
        print(f"输出信息:\n{stdout}")
    
    # 强制终止进程
    process.terminate()
    sys.exit(1)

print("\n=== 测试安全修复 ===")

# 1. 测试路径遍历防护
print("\n1. 测试路径遍历防护...")
try:
    response = requests.get("http://localhost:8999/files?path=../../../etc/passwd", timeout=5)
    if response.status_code == 400:
        print("✅ 路径遍历攻击被阻止!")
    elif response.status_code == 404:
        print("✅ 路径遍历攻击被阻止(404)!")
    else:
        print(f"⚠️ 意外的响应代码: {response.status_code}")
except Exception as e:
    print(f"错误: {e}")

# 2. 测试CORS
print("\n2. 测试CORS配置...")
try:
    response = requests.options(
        "http://localhost:8999/health",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST"
        },
        timeout=5
    )
    origin = response.headers.get("Access-Control-Allow-Origin", "")
    if origin == "*":
        print("⚠️ CORS允许所有来源(应限制)")
    elif origin:
        print(f"✅ CORS允许来源: {origin}")
    else:
        print("ℹ️ 没有CORS头部")
except Exception as e:
    print(f"错误: {e}")

print("\n=== 测试完成 ===")
print("服务正在运行中...")
print("按 Ctrl+C 停止服务")

try:
    # 保持服务运行
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n停止服务...")
    process.terminate()
    process.wait()
    print("服务已停止")