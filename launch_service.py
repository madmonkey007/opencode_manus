#!/usr/bin/env python3
"""
OpenCode Service Launcher
修复启动问题的专用脚本
"""
import os
import sys
import subprocess
import signal

def main():
    # 设置环境变量
    os.environ['CORS_ORIGINS'] = 'http://localhost:3000,http://localhost:8089'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    print("=== OpenCode Service Launcher ===")
    print(f"CORS Origins: {os.environ['CORS_ORIGINS']}")
    print(f"Working Dir: {os.getcwd()}")
    print(f"Python: {sys.version}")
    
    # 添加当前目录到Python路径
    sys.path.insert(0, os.getcwd())
    
    try:
        # 直接运行main文件
        cmd = [sys.executable, 'app/main.py']
        print(f"\nStarting: {' '.join(cmd)}")
        
        # 启动服务
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print(f"Service PID: {process.pid}")
        print("\nService output:")
        print("-" * 50)
        
        # 实时输出日志
        for line in iter(process.stdout.readline, ''):
            print(line.strip())
            
            # 检查是否启动成功
            if "Uvicorn running on" in line:
                print("\n✅ Service started successfully!")
                print("URL: http://localhost:8089")
                print("Health: http://localhost:8089/health")
            
            # 检查是否有错误
            if "ERROR" in line and "Traceback" in line:
                print("\n❌ Service failed to start!")
                return False
        
        # 等待进程结束
        return_code = process.wait()
        print(f"\nService exited with code: {return_code}")
        return return_code == 0
        
    except KeyboardInterrupt:
        print("\n\nStopping service...")
        if 'process' in locals():
            process.terminate()
            process.wait()
        print("Service stopped")
        return 0
    except Exception as e:
        print(f"\n❌ Failed to start service: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())