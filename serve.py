#!/usr/bin/env python
"""启动OpenCode服务器"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    print("=" * 50)
    print("正在启动 OpenCode 服务器...")
    print("=" * 50)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8088,
        log_level="info"
    )
