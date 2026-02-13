import sys
import os

# 设置路径
os.chdir('D:/Manus/opencode')
sys.path.insert(0, 'D:/Manus/opencode')

print("=" * 60)
print("OpenCode Server Diagnostic Tool")
print("=" * 60)
print()

try:
    print("[1/5] Testing Python...")
    print(f"  Python version: {sys.version}")
    print(f"  Current directory: {os.getcwd()}")
    print("  OK")
    print()
    
    print("[2/5] Testing sys.path...")
    if 'D:\Manus\opencode' in sys.path or 'D:/Manus/opencode' in sys.path:
        print("  OK - Project path in sys.path")
    else:
        print("  WARNING - Project path not in sys.path")
        sys.path.insert(0, 'D:/Manus/opencode')
    print()
    
    print("[3/5] Importing app.main...")
    from app.main import app
    print("  OK - App imported")
    print(f"  App type: {type(app)}")
    print()
    
    print("[4/5] Importing uvicorn...")
    import uvicorn
    print(f"  Uvicorn version: {uvicorn.__version__}")
    print("  OK")
    print()
    
    print("[5/5] Starting server...")
    print("  Host: 127.0.0.1")
    print("  Port: 8088")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # 使用更简单的配置
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8088,
        log_level="info",
        access_log=False  # 禁用访问日志减少输出
    )
    
except KeyboardInterrupt:
    print("\nServer stopped by user.")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

