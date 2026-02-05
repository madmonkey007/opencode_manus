#!/bin/bash

echo "🚀 [OpenCode] Initializing Sandbox Core..."

# 1. 确保必要目录存在
mkdir -p /app/opencode/logs
mkdir -p /app/opencode/workspace
mkdir -p /app/opencode/config

# 2. 强效路径转换补丁 (Windows -> Linux)
# 我们将宿主机的配置文件复制并转换路径，以确保内核能找到模块
RAW_CONFIG="/app/opencode/config_host/opencode.json"
PATCHED_CONFIG="/app/opencode/config/opencode.json"

if [ -f "$RAW_CONFIG" ]; then
    echo "🛠️ Patching opencode.json for container environment..."
    # 替换 Windows 绝对路径为容器内挂载路径
    # 处理 C:/Users/EDY/.config/opencode 为 /app/opencode/config_host
    # 同时处理反斜杠转义
    sed -e 's|C:/Users/EDY/.config/opencode|/app/opencode/config_host|g' \
        -e 's|C:\Users\EDY\.config\opencode|/app/opencode/config_host|g' \
        -e 's|file:///C:/Users/EDY/.config/opencode|/app/opencode/config_host|g' \
        "$RAW_CONFIG" > "$PATCHED_CONFIG"
    
    # 设置环境变量让内核加载此配置文件
    export OPENCODE_CONFIG_FILE="$PATCHED_CONFIG"
    echo "✅ Config patched and exported: $PATCHED_CONFIG"
else
    echo "⚠️ Raw config not found at $RAW_CONFIG"
fi

# 3. 确保 oh-my-opencode 插件就绪
echo "✨ Syncing oh-my-opencode..."
# 使用 bun 全局安装最新的 dev 分支
bun install -g git+https://github.com/code-yeongyu/oh-my-opencode.git#dev

# 4. 补全 Skills 依赖
if [ -d "/app/opencode/config_host/skills" ]; then
    echo "📦 Syncing local skills dependencies..."
    if [ -f "/app/opencode/config_host/skills/package.json" ]; then
        cd /app/opencode/config_host/skills && bun install --no-save && cd /app/opencode
    fi
fi

# 5. 启动可视化控制台 (Xvfb + VNC + FastAPI)
echo "📺 Launching Visual Console via UVN..."
exec /usr/bin/supervisord -c /app/opencode/supervisord.conf
