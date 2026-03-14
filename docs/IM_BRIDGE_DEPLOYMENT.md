# IM Bridge服务器部署指南

## 📋 概述

本指南说明如何部署和运行IM Bridge服务器，用于接收EventBroadcaster的事件并转发到IM平台。

## 🚀 快速开始

### Windows用户

#### 方法1：一键启动（推荐）

1. **双击运行启动脚本**
   ```
   start-im-bridge.bat
   ```

2. **看到以下输出表示成功**
   ```
   ========================================
   🚀 OpenCode IM Bridge Server Started
   ========================================
   📡 监听端口: 18080
   🔗 事件端点: http://localhost:18080/opencode/events
   ✅ 服务器已就绪，等待EventBroadcaster推送事件...
   ```

#### 方法2：命令行启动

```bash
# 1. 安装依赖
npm install

# 2. 启动服务器
node im-bridge-server.js
```

### Linux/Mac用户

#### 方法1：使用启动脚本

```bash
# 1. 赋予执行权限
chmod +x start-im-bridge.sh

# 2. 启动服务器
./start-im-bridge.sh
```

#### 方法2：直接运行

```bash
# 1. 安装依赖
npm install

# 2. 启动服务器
node im-bridge-server.js
```

## ✅ 验证部署

### 1. 检查服务器状态

在浏览器访问：http://localhost:18080/health

**预期响应**：
```json
{
  "status": "healthy",
  "uptime": 123.456,
  "stats": {
    "eventsReceived": 0,
    "eventsByType": {},
    "lastEventTime": null
  }
}
```

### 2. 运行端到端测试

```bash
# 确保IM Bridge服务器正在运行
# 然后在新终端运行测试

python tests/test_im_integration_e2e.py
```

**预期输出**：
```
======================================================================
EventBroadcaster IM集成 - 端到端测试
======================================================================

[步骤1] 检查IM Bridge服务器...
✓ IM Bridge服务器运行中
  - 运行时间: 12.3秒

[步骤2] 重置统计...
✓ 统计已重置

[步骤3] 初始化EventBroadcaster...
✓ Webhook URL: http://localhost:18080/opencode/events
✓ 启用事件: ["complete", "error", "phase", "action"]

[步骤4] 测试事件推送...

📤 发送事件: phase
  ✓ 推送成功
📤 发送事件: action
  ✓ 推送成功
📤 发送事件: complete
  ✓ 推送成功
...

[步骤6] 测试结果汇总:
  ✓ PASS | phase
  ✓ PASS | action
  ✓ PASS | complete
  ✓ PASS | error
  ✓ PASS | progress

======================================================================
✅ 所有测试通过！IM集成工作正常
======================================================================
```

## 🔧 配置EventBroadcaster

### 方法1：环境变量（推荐）

```bash
# Windows
set OPENCODE_IM_WEBHOOK_URL=http://localhost:18080/opencode/events
set OPENCODE_IM_ENABLED_EVENTS=complete,error,phase

# Linux/Mac
export OPENCODE_IM_WEBHOOK_URL="http://localhost:18080/opencode/events"
export OPENCODE_IM_ENABLED_EVENTS="complete,error,phase"
```

### 方法2：Python代码

```python
from app.gateway.event_broadcaster import EventBroadcaster

broadcaster = EventBroadcaster(
    im_webhook_url="http://localhost:18080/opencode/events",
    im_enabled_events=["complete", "error", "phase"]
)
await broadcaster.start()
```

### 方法3：.env文件

```bash
# 添加到项目根目录的.env文件
OPENCODE_IM_WEBHOOK_URL=http://localhost:18080/opencode/events
OPENCODE_IM_ENABLED_EVENTS=complete,error,phase
```

## 🧪 手动测试

### 使用curl测试

```bash
# 测试事件端点
curl -X POST http://localhost:18080/opencode/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test-123",
    "event_type": "complete",
    "session_id": "test-session",
    "timestamp": "2026-03-14T10:00:00",
    "data": {"result": "success", "message": "Test event"}
  }'
```

**预期响应**：
```json
{
  "success": true,
  "event_id": "test-123",
  "message": "Event received and forwarded to IM"
}
```

### 使用Python测试

```python
import asyncio
from app.gateway.event_broadcaster import EventBroadcaster, Event

async def test():
    broadcaster = EventBroadcaster(
        im_webhook_url="http://localhost:18080/opencode/events"
    )

    event = Event(
        event_type="complete",
        session_id="test-session",
        data={"result": "success"}
    )

    await broadcaster._push_to_im(event)
    print("✓ 事件已推送")

asyncio.run(test())
```

## 📊 监控和日志

### 查看统计信息

```bash
# 方式1：浏览器
http://localhost:18080/stats

# 方式2：curl
curl http://localhost:18080/stats

# 方式3：Python
import aiohttp
async with aiohttp.ClientSession() as session:
    async with session.get("http://localhost:18080/stats") as resp:
        stats = await resp.json()
        print(stats)
```

### 日志输出示例

```
==============================================================
📥 收到事件: complete
==============================================================
事件ID: evt_abc123
会话ID: ses_task456
时间戳: 2026-03-14T10:30:45.123456
数据: {
  "result": "success",
  "files": ["main.py", "utils.py"]
}

📤 推送到IM的消息:
--------------------------------------------------------------
✅ 任务完成

结果: success
📁 文件: main.py, utils.py
==============================================================
```

## 🐛 故障排查

### 问题1：端口已被占用

**错误信息**：
```
Error: listen EADDRINUSE: address already in use :::18080
```

**解决方案**：
```bash
# Windows: 查找占用进程
netstat -ano | findstr :18080
taskkill /PID <进程ID> /F

# Linux/Mac: 查找占用进程
lsof -ti:18080 | xargs kill -9

# 或修改端口
export IM_BRIDGE_PORT=18081
node im-bridge-server.js
```

### 问题2：依赖未安装

**错误信息**：
```
Error: Cannot find module 'express'
```

**解决方案**：
```bash
npm install express body-parser cors
```

### 问题3：防火墙阻止连接

**症状**：EventBroadcaster无法连接到服务器

**解决方案**：
```bash
# Windows: 添加防火墙规则
netsh advfirewall firewall add rule name="IM Bridge" dir=in action=allow protocol=TCP localport=18080

# Linux: 开放端口
sudo ufw allow 18080/tcp
```

### 问题4：EventBroadcaster推送失败

**检查清单**：

```python
# 1. 确认服务器运行
import aiohttp
async with aiohttp.ClientSession() as session:
    async with session.get("http://localhost:18080/health") as resp:
        print(await resp.json())

# 2. 确认URL配置
print(broadcaster.im_webhook_url)

# 3. 确认事件类型匹配
print(event.event_type in broadcaster.im_enabled_events)

# 4. 查看详细错误
import logging
logging.getLogger('app.gateway.event_broadcaster').setLevel(logging.DEBUG)
```

## 🚀 生产环境部署

### 使用PM2（推荐）

```bash
# 1. 安装PM2
npm install -g pm2

# 2. 启动服务
pm2 start im-bridge-server.js --name opencode-im-bridge

# 3. 设置开机自启
pm2 startup
pm2 save

# 4. 查看日志
pm2 logs opencode-im-bridge

# 5. 监控
pm2 monit
```

### 使用Docker

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app
COPY im-bridge-server.js .
COPY package.json .
RUN npm install --production

EXPOSE 18080

CMD ["node", "im-bridge-server.js"]
```

```bash
# 构建镜像
docker build -t opencode-im-bridge .

# 运行容器
docker run -d \
  --name opencode-im-bridge \
  -p 18080:18080 \
  opencode-im-bridge
```

### 使用systemd（Linux）

```ini
# /etc/systemd/system/opencode-im-bridge.service
[Unit]
Description=OpenCode IM Bridge Server
After=network.target

[Service]
Type=simple
User=opencode
WorkingDirectory=/opt/opencode
ExecStart=/usr/bin/node /opt/opencode/im-bridge-server.js
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl enable opencode-im-bridge
sudo systemctl start opencode-im-bridge

# 查看状态
sudo systemctl status opencode-im-bridge
```

## 🔐 安全建议

### 1. 使用反向代理（Nginx）

```nginx
# /etc/nginx/sites-available/opencode-im-bridge
server {
    listen 80;
    server_name im-bridge.yourdomain.com;

    location /opencode/events {
        proxy_pass http://localhost:18080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # 限制请求大小
        client_max_body_size 1M;

        # 访问控制
        allow 192.168.1.0/24;  # 允许内网
        deny all;               # 拒绝其他
    }
}
```

### 2. 添加API密钥认证

```javascript
// 在im-bridge-server.js中添加
const API_KEY = process.env.IM_BRIDGE_API_KEY;

app.use((req, res, next) => {
  const apiKey = req.headers['x-api-key'];
  if (apiKey !== API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
});
```

```python
# 在EventBroadcaster中添加密钥
async def _push_to_im(self, event: Event):
    headers = {
        'X-API-Key': os.getenv('IM_BRIDGE_API_KEY')
    }

    async with session.post(
        self.im_webhook_url,
        json=payload,
        headers=headers
    ) as response:
        # ...
```

### 3. 使用HTTPS

```bash
# 使用Let's Encrypt获取免费SSL证书
sudo certbot --nginx -d im-bridge.yourdomain.com
```

## 📚 下一步

1. **集成真实IM平台**
   - 飞书：参考[飞书开放平台文档](https://open.feishu.cn/)
   - Telegram：参考[Telegram Bot API](https://core.telegram.org/bots/api)

2. **实现Slash Command**
   - 从IM触发任务执行
   - 查询任务状态

3. **添加持久化**
   - 保存事件到数据库
   - 支持历史查询

4. **监控告警**
   - Prometheus指标导出
   - 失败告警通知

## 🆘 获取帮助

- GitHub Issues: https://github.com/your-org/opencode/issues
- 文档: https://docs.opencode.example.com
- 社区: https://discord.gg/opencode
