#!/usr/bin/env python
"""OpenCode Server Startup Script"""
import subprocess
import sys
import time
import psutil

def stop_old_servers():
    """Stop existing Python processes"""
    print("[1/2] Stopping old services...")
    count = 0
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                proc.kill()
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if count > 0:
        print(f"  Stopped {count} Python process(es)")
    time.sleep(1)
    print("  Done.")

def start_server():
    """Start uvicorn server"""
    print("[2/2] Starting server...")
    print("\n" + "=" * 60)
    print("  Server is starting...")
    print("  URL: http://localhost:8088")
    print("  New API: http://localhost:8088?use_new_api=true")
    print("=" * 60 + "\n")
    print("Press Ctrl+C to stop server\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "app.main:app", 
             "--host", "0.0.0.0", "--port", "8088", "--log-level", "info"],
            cwd="/d/Manus/opencode"
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    stop_old_servers()
    start_server()
