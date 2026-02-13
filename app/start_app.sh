#!/bin/bash
cd /app/opencode
export PYTHONUNBUFFERED="1"
export PATH="/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
