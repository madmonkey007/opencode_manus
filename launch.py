import sys
import os
import traceback

os.chdir('D:/Manus/opencode')
sys.path.insert(0, 'D:/Manus/opencode')

print("=" * 60)
print("OpenCode Server Launcher")
print("=" * 60)
print()

try:
    print("[1/3] Importing app.main...")
    from app.main import app
    print("  OK - App imported successfully")
    
    print("[2/3] Importing uvicorn...")
    import uvicorn
    print("  OK - Uvicorn imported")
    
    print("[3/3] Starting server...")
    print("  URL: http://localhost:8088")
    print("  New API: http://localhost:8088?use_new_api=true")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8088,
        log_level="info"
    )
    
except Exception as e:
    print()
    print("=" * 60)
    print("ERROR: Failed to start server")
    print("=" * 60)
    print(f"Error: {e}")
    print()
    print("Traceback:")
    traceback.print_exc()
    sys.exit(1)

