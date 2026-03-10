import subprocess
import sys
import os
import time
import signal

# 设置环境变量
os.environ['CORS_ORIGINS'] = 'http://localhost:3000,http://localhost:8089'
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("Starting OpenCode service...")
print(f"CORS Origins: {os.environ['CORS_ORIGINS']}")
print(f"Working Directory: {os.getcwd()}")

# 启动服务
process = subprocess.Popen(
    [sys.executable, "-m", "app.main"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding='utf-8',
    errors='replace'
)

print("Service PID:", process.pid)
print("Waiting for service to start...")

# 等待启动
time.sleep(10)

# 检查是否仍在运行
if process.poll() is None:
    print("✅ Service is running!")
    print("Service URL: http://localhost:8089")
    print("Health Check: http://localhost:8089/health")
    
    # 保持服务运行
    try:
        while True:
            # 读取输出
            line = process.stdout.readline()
            if line:
                print(line.strip())
            
            # 检查进程状态
            if process.poll() is not None:
                print("Service stopped")
                break
                
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping service...")
        process.terminate()
        process.wait()
        print("Service stopped")
else:
    print("❌ Service failed to start")
    print("Output:")
    print(process.stdout.read())