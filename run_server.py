#!/usr/bin/env python
"""
OpenCode 服务器启动脚本
"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    print("=" * 60)
    print("  OpenCode Web Server")
    print("=" * 60)
    print(f"  地址: http://localhost:8088")
    print(f"  新 API: http://localhost:8088?use_new_api=true")
    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8088,
        log_level="info",
        access_log=True
    )
