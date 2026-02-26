#!/bin/bash
cd /app/opencode
export PYTHONUNBUFFERED="1"
export PATH="/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"

# 启动 uvicorn（在前台）
exec /usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8089 --log-level info
