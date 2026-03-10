# -*- coding: utf-8 -*-
"""
启动OpenCode服务用于测试
"""
import os
import sys
import subprocess
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000,http://localhost:8999'

print("=== OpenCode Service Test ===")
print(f"Python: {sys.version}")
print(f"Working Dir: {os.getcwd()}")
print(f"CORS Origins: {os.environ['CORS_ORIGINS']}")

# 启动OpenCode服务
try:
    print("\n启动OpenCode服务...")
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # 等待服务启动
    print("等待服务启动...")
    for i in range(30):
        if process.poll() is not None:
            # 进程已退出
            stdout, stderr = process.communicate()
            print("服务启动失败！")
            print(f"标准输出: {stdout}")
            print(f"错误输出: {stderr}")
            sys.exit(1)
        time.sleep(1)
        print(f"等待中... {i+1}/30")
    
    print("服务应该已启动在 http://localhost:8999")
    print("请使用浏览器测试以下URL:")
    print("  - http://localhost:8999/health")
    print("  - http://localhost:8999/")
    print("\n按 Ctrl+C 停止服务...")
    
    # 保持进程运行
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n停止服务...")
        process.terminate()
        process.wait()
        print("服务已停止")

except Exception as e:
    print(f"启动失败: {e}")
    import traceback
    traceback.print_exc()