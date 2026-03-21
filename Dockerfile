FROM python:3.12-slim-bookworm

WORKDIR /app/opencode

# 1. 安装基础系统依赖 (包括 Bun 所需的 unzip)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl wget unzip ca-certificates x11vnc xvfb fluxbox novnc websockify supervisor net-tools procps \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 \
    libpango-1.0-0 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 3. 安装 Bun
RUN curl -fsSL https://bun.sh/install | bash \
    && ln -s /root/.bun/bin/bun /usr/local/bin/bun \
    && ln -s /root/.bun/bin/bunx /usr/local/bin/bunx

# 4. 全局安装 OpenCode-AI 官方内核及平台二进制包
RUN npm install -g opencode-ai opencode-linux-x64 && \
    cd /usr/lib/node_modules/opencode-ai && node postinstall.mjs

# 5. 配置 noVNC 环境 (确保 vnc.html 存在，兼容不同发行版的 noVNC)
RUN if [ ! -f /usr/share/novnc/vnc.html ] && [ -f /usr/share/novnc/vnc_lite.html ]; then \
    ln -s /usr/share/novnc/vnc_lite.html /usr/share/novnc/vnc.html; \
    fi && \
    ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html && \
    echo '{}' > /usr/share/novnc/package.json

# 6. 安装 Python 环境 (使用镜像源以加速)
RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 7. 预安装 Playwright 浏览器及其内核
RUN playwright install chromium

# 8. 复制项目代码
COPY . .

# 确保启动脚本有执行权限
RUN chmod +x /app/opencode/app/start.sh

ENV DISPLAY=:0
ENV SCREEN_WIDTH=1280
ENV SCREEN_HEIGHT=720
ENV OPENCODE_CONFIG_DIR=/app/opencode/config_host

# Security fixes for CORS and encoding
ENV CORS_ORIGINS=http://localhost:3000,http://localhost:8089
ENV PYTHONIOENCODING=utf-8

# 暴露端口：8000 (UI), 6080 (UVN)
EXPOSE 8000 6080

# 使用自定义脚本启动
CMD ["/app/opencode/app/start.sh"]
