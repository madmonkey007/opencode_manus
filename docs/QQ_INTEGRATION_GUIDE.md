# OpenCode QQ Bot集成完整指南

## 📋 概述

本指南说明如何将OpenCode EventBroadcaster与QQ Bot集成，实现在QQ上接收任务执行通知。

## 🎯 功能特性

- ✅ 私聊通知：发送到指定QQ号
- ✅ 群消息通知：发送到指定QQ群
- ✅ 事件过滤：选择需要推送的事件类型
- ✅ 消息格式化：自动转换为QQ友好格式
- ✅ 多目标支持：同时推送到多个QQ号/群
- ✅ 健壮性：失败重试、错误隔离

## 🏗️ 系统架构

```
OpenCode EventBroadcaster
    ↓ (HTTP Webhook)
IM Bridge Server (Express.js)
    ↓ (go-cqhttp API)
go-cqhttp (QQ Bot框架)
    ↓ (QQ协议)
QQ服务器
    ↓
QQ客户端 (手机/QQ电脑版)
```

## 📦 前置要求

### 1. 安装go-cqhttp

参考文档：`GO_CQHTTP_SETUP.md`

**快速安装**：
```bash
# 下载
wget https://github.com/Mrs4s/go-cqhttp/releases/download/v1.2.0/go-cqhttp_linux_amd64.tar.gz

# 解压
tar -xzf go-cqhttp_linux_amd64.tar.gz
cd go-cqhttp

# 运行
./go-cqhttp
```

### 2. 扫码登录

1. 首次运行会显示二维码
2. 使用手机QQ扫码
3. 按提示完成验证

### 3. 验证安装

```bash
curl http://localhost:3000/get_login_info
```

**预期响应**：
```json
{
  "retcode": 0,
  "data": {
    "user_id": 123456789,
    "nickname": "你的昵称"
  }
}
```

## ⚙️ 配置步骤

### 步骤1：配置环境变量

**方式A：创建 .env.qq 文件**

```bash
# 复制示例配置
cp .env.qq.example .env.qq

# 编辑配置
nano .env.qq
```

**方式B：直接设置环境变量**

```bash
# Windows
set QQ_ENABLE=true
set QQ_TARGETS=user:123456,group:789
set QQ_ENABLED_EVENTS=complete,error,phase

# Linux/Mac
export QQ_ENABLE=true
export QQ_TARGETS="user:123456,group:789"
export QQ_ENABLED_EVENTS="complete,error,phase"
```

### 步骤2：配置参数说明

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `QQ_ENABLE` | 是否启用QQ Bot | false | true |
| `QQ_API_URL` | go-cqhttp API地址 | http://localhost:3000 | - |
| `QQ_ACCESS_TOKEN` | 访问令牌（可选） | - | your-secret-token |
| `QQ_PLATFORM` | QQ Bot平台 | go-cqhttp | shamrock |
| `QQ_TARGETS` | 推送目标列表 | - | user:123,group:456 |
| `QQ_ENABLED_EVENTS` | 启用的事件类型 | complete,error,phase | complete |

### 步骤3：启动IM Bridge服务器

```bash
# 加载QQ配置
source .env.qq  # Linux/Mac
# 或
set -a; source .env.qq; set +a  # Bash

# 启动服务器
node im-bridge-server.js
```

或使用启动脚本：
```bash
# Windows
QQ_ENABLE=true QQ_TARGETS=user:123456 start-im-bridge.bat

# Linux/Mac
QQ_ENABLE=true QQ_TARGETS=user:123456 ./start-im-bridge.sh
```

## 🧪 测试集成

### 测试1：检查QQ Bot状态

```bash
curl http://localhost:18080/health
```

**预期输出**：
```
============================================================
🚀 OpenCode IM Bridge Server Started
============================================================
📱 QQ Bot配置:
   状态: ✅ 已启用
   平台: go-cqhttp
   API: http://localhost:3000
   账号: 你的昵称 (123456789)
   推送目标: user:123456
```

### 测试2：发送测试事件

```bash
curl -X POST http://localhost:18080/test/event \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "complete",
    "data": {"result": "success"}
  }'
```

**预期结果**：QQ收到测试消息

### 测试3：端到端测试

```python
import asyncio
from app.gateway.event_broadcaster import EventBroadcaster, Event

async def test():
    broadcaster = EventBroadcaster(
        im_webhook_url="http://localhost:18080/opencode/events",
        im_enabled_events=["complete", "error"]
    )

    event = Event(
        event_type="complete",
        session_id="test-session",
        data={"result": "success", "message": "测试消息"}
    )

    await broadcaster._push_to_im(event)
    print("✓ 测试事件已发送")

asyncio.run(test())
```

## 📊 推送的消息格式

### complete事件
```
✅ OpenCode任务完成

结果: success
📁 文件: main.py, utils.py
```

### error事件
```
❌ OpenCode任务失败

错误: File not found: missing.py
```

### phase事件
```
🔄 OpenCode任务阶段

阶段: planning
描述: 任务规划中
```

### action事件
```
⚙️ OpenCode执行操作

create_file → main.py
```

## 🔧 高级配置

### 1. 自定义消息格式

修改 `qq-adapter.js` 中的 `formatOpenCodeEvent` 方法：

```javascript
formatOpenCodeEvent(eventType, eventData) {
  const prefix = process.env.QQ_MESSAGE_PREFIX || '[OpenCode] ';

  switch (eventType) {
    case 'complete':
      return `${prefix}任务完成！\n结果: ${eventData.result}`;
    // ...
  }
}
```

### 2. 条件推送

只在特定条件下推送：

```javascript
// 在 qq-adapter.js 中添加
shouldSend(eventType, eventData) {
  // 只在工作时间推送
  const hour = new Date().getHours();
  if (hour < 9 || hour > 18) {
    return false;
  }

  // 只推送特定会话
  if (eventData.session_id.startsWith('test-')) {
    return false;
  }

  return true;
}
```

### 3. 富文本消息

使用CQ码发送富文本：

```javascript
// 发送图片
this.sendPrivateMessage(userId, `[CQ:image,file=http://example.com/image.jpg]`);

// @某人
this.sendGroupMessage(groupId, `[CQ:at,qq=123456] 请查收任务结果`);

// 发送卡片
const cardData = {
  title: "任务完成",
  desc: "OpenCode任务已成功执行",
  url: "https://opencode.example.com"
};
this.sendPrivateMessage(userId, this.buildMessage('card', cardData));
```

## 🐛 故障排查

### 问题1：QQ未收到消息

**检查清单**：

```bash
# 1. 检查go-cqhttp运行状态
curl http://localhost:3000/get_status

# 2. 检查IM Bridge服务器日志
# 应该看到 "QQ Adapter" 相关输出

# 3. 检查环境变量
echo $QQ_ENABLE
echo $QQ_TARGETS

# 4. 检查统计信息
curl http://localhost:18080/stats
```

### 问题2：go-cqhttp连接失败

**可能原因**：
- go-cqhttp未启动
- 端口配置错误
- 防火墙阻止

**解决方案**：
```bash
# 1. 重启go-cqhttp
cd /path/to/go-cqhttp
./go-cqhttp

# 2. 检查端口
netstat -an | grep 3000

# 3. 检查防火墙
# Windows: 控制面板 → Windows防火墙
# Linux: sudo ufw allow 3000
```

### 问题3：登录失败

**滑块验证**：
```bash
# 安装依赖
pip install Pillow numpy

# 使用验证工具
python slider-captcha.py
```

**设备锁**：
- 按提示短信验证
- 或使用手机密保

### 问题4：消息发送失败

**可能原因**：
- 目标QQ号/群不存在
- 没有发送权限
- 触发风控

**解决方案**：
```bash
# 1. 先给自己发消息测试
QQ_TARGETS=user:你的QQ号

# 2. 检查返回码
# retcode: 0 = 成功
# retcode: 100 = 好友不存在
# retcode: 120 = 消息过长

# 3. 降低频率
# 在go-cqhttp配置中设置限流
```

## 📈 监控和统计

### 查看统计

```bash
curl http://localhost:18080/stats
```

**响应**：
```json
{
  "eventsReceived": 100,
  "qqMessagesSent": 95,
  "qqMessagesFailed": 5,
  "eventsByType": {
    "complete": 50,
    "error": 30,
    "phase": 20
  }
}
```

### 计算成功率

```bash
# 计算
success_rate = qqMessagesSent / (qqMessagesSent + qqMessagesFailed) * 100
```

### 日志分析

```bash
# IM Bridge服务器日志显示
# [QQ Adapter] ✓ Private message sent to 123456789
# [QQ Adapter] ✗ Failed: 消息发送失败
```

## 🔐 安全建议

### 1. 使用访问令牌

**go-cqhttp配置**：
```yaml
servers:
  - http:
      token: "your-secret-token"
```

**环境变量**：
```bash
QQ_ACCESS_TOKEN=your-secret-token
```

### 2. 限制访问IP

**go-cqhttp配置**：
```yaml
servers:
  - http:
      host: 127.0.0.1  # 只允许本地访问
```

### 3. 隐藏QQ号

使用环境变量而非硬编码：
```bash
# 好的做法
QQ_TARGETS=user:$MY_QQ_ID

# 不好的做法
QQ_TARGETS=user:123456789  # 硬编码在代码中
```

## 🚀 生产环境部署

### 1. 使用PM2自动重启

```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'im-bridge',
    script: './im-bridge-server.js',
    env: {
      QQ_ENABLE: 'true',
      QQ_TARGETS: 'user:123456'
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    autorestart: true,
    max_restarts: 10
  }]
};
```

### 2. 使用systemd

```ini
# /etc/systemd/system/opencode-im-bridge.service
[Unit]
Description=OpenCode IM Bridge with QQ Bot
After=network.target go-cqhttp.service

[Service]
Type=simple
User=opencode
WorkingDirectory=/opt/opencode
Environment="QQ_ENABLE=true"
Environment="QQ_TARGETS=user:123456"
ExecStart=/usr/bin/node /opt/opencode/im-bridge-server.js
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### 3. Docker部署

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app
COPY im-bridge-server.js .
COPY qq-adapter.js .
COPY package.json .
RUN npm install --production

ENV QQ_ENABLE=true
ENV QQ_TARGETS=user:123456
ENV QQ_API_URL=http://go-cqhttp:3000

EXPOSE 18080
CMD ["node", "im-bridge-server.js"]
```

```yaml
# docker-compose.yml
version: '3'
services:
  im-bridge:
    build: .
    ports:
      - "18080:18080"
    environment:
      - QQ_ENABLE=true
      - QQ_TARGETS=user:123456
      - QQ_API_URL=http://go-cqhttp:3000
    depends_on:
      - go-cqhttp

  go-cqhttp:
    image: mrs4s/go-cqhttp:latest
    ports:
      - "3000:3000"
    volumes:
      - ./go-cqhttp-data:/data
```

## 📚 相关文档

- [go-cqhttp安装指南](./GO_CQHTTP_SETUP.md)
- [IM Bridge部署指南](./IM_BRIDGE_DEPLOYMENT.md)
- [EventBroadcaster API](./event_broadcaster_api.md)

## 🆘 获取帮助

- **QQ Bot框架**: https://github.com/Mrs4s/go-cqhttp
- **go-cqhttp文档**: https://docs.go-cqhttp.org/
- **社区支持**: https://jq.qq.com/

## 🎉 下一步

配置完成后，你可以：
1. 在QQ上实时接收任务通知
2. 设置多个推送目标（群+私聊）
3. 自定义消息格式和内容
4. 实现从QQ触发任务执行（Slash Command）

## 💡 最佳实践

1. **测试优先**：先给自己发消息测试
2. **渐进式启用**：只启用complete事件，逐步增加
3. **设置限流**：避免频繁触发QQ风控
4. **监控日志**：定期检查发送成功率
5. **备用方案**：配置多个推送目标以防失败

---

**配置完成标志**：
- ✅ go-cqhttp运行正常
- ✅ IM Bridge服务器启动
- ✅ QQ配置加载成功
- ✅ 测试消息已接收
- ✅ 端到端流程验证通过
