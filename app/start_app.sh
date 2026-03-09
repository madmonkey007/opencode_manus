#!/bin/bash
cd /app/opencode
export PYTHONUNBUFFERED="1"
export PATH="/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"

# 使用server_manager实现懒加载和持久化服务器
# 这样可以避免每次启动时的15秒冷启动时间
exec python -m app.server_manager
