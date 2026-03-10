# -*- coding: utf-8 -*-
"""
诊断OpenCode服务启动问题
"""
import os
import sys
import socket
import requests

print("=== OpenCode Service Diagnostics ===\n")

# 1. 检查端口占用
print("1. 检查端口占用:")
port = 8999
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(('localhost', port))
        if result == 0:
            print(f"   端口 {port} 已被占用")
            # 查找占用进程
            import subprocess
            try:
                output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True)
                print(f"   占用进程信息:\n{output.decode('gbk')}")
            except:
                pass
        else:
            print(f"   端口 {port} 可用")
except Exception as e:
    print(f"   检查端口时出错: {e}")

# 2. 检查环境变量
print("\n2. 环境变量:")
print(f"   CORS_ORIGINS: {os.getenv('CORS_ORIGINS', 'Not set')}")
print(f"   PYTHONIOENCODING: {os.getenv('PYTHONIOENCODING', 'Not set')}")

# 3. 尝试连接
print("\n3. 尝试连接服务:")
try:
    response = requests.get("http://localhost:8999/health", timeout=2)
    print(f"   ✅ 服务响应正常: {response.status_code}")
    print(f"   响应内容: {response.text}")
except requests.exceptions.ConnectionError:
    print("   ❌ 连接被拒绝 - 服务可能未启动")
except requests.exceptions.Timeout:
    print("   ⏰ 连接超时")
except Exception as e:
    print(f"   ❌ 其他错误: {e}")

# 4. 检查Python模块
print("\n4. 检查Python模块:")
try:
    import app.main
    print("   ✅ app.main 模块可导入")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")

print("\n=== Diagnostics Complete ===")