import sys
import os
import socket

# 设置路径
os.chdir('D:/Manus/opencode')
sys.path.insert(0, 'D:/Manus/opencode')

# 获取本机IP
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

local_ip = get_local_ip()

print("=" * 70)
print("  OpenCode Server - All Interfaces Mode")
print("=" * 70)
print()
print(f"  Your Local IP: {local_ip}")
print(f"  Access URLs:")
print(f"    - http://localhost:8088")
print(f"    - http://127.0.0.1:8088")
print(f"    - http://{local_ip}:8088")
print()
print("  Press Ctrl+C to stop")
print("=" * 70)
print()

try:
    from app.main import app
    import uvicorn
    
    # 使用 0.0.0.0 监听所有网络接口
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8088,
        log_level="info"
    )
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

