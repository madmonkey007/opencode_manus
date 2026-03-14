# 🤖 QQ机器人快速配置指南

## 🎯 3种配置方式

### 方式1：一键启动（最简单）⭐推荐

**Windows**:
```bash
# 1. 双击运行
start-qq-integration.bat

# 2. 输入你的QQ号
# 3. 用手机QQ扫码登录go-cqhttp
# 4. 完成！
```

**Linux/Mac**:
```bash
# 1. 赋予执行权限
chmod +x start-qq-integration.sh

# 2. 运行脚本
./start-qq-integration.sh

# 3. 输入QQ号并扫码登录
# 4. 完成！
```

---

### 方式2：手动配置（更灵活）

#### 第1步：安装go-cqhttp

**Windows**:
```bash
# 双击运行
install-go-cqhttp.bat
```

**Linux/Mac**:
```bash
chmod +x install-go-cqhttp.sh
./install-go-cqhttp.sh
```

#### 第2步：启动go-cqhttp

```bash
# 进入目录
cd go-cqhttp

# Windows
go-cqhttp.exe

# Linux/Mac
./go-cqhttp
```

**首次运行**：
1. 会生成配置文件
2. 显示二维码（或保存为qrcode.png）
3. 用手机QQ扫码
4. 完成设备验证（短信/密保）
5. 登录成功！

#### 第3步：配置IM Bridge

**方式A：环境变量**
```bash
export QQ_ENABLE=true
export QQ_TARGETS=user:123456
export QQ_ENABLED_EVENTS=complete,error

node im-bridge-server.js
```

**方式B：.env文件**
```bash
# 创建 .env.qq 文件
cat > .env.qq << EOF
QQ_ENABLE=true
QQ_TARGETS=user:123456
QQ_ENABLED_EVENTS=complete,error,phase
EOF

# 启动时加载
source .env.qq && node im-bridge-server.js
```

---

### 方式3：使用Docker（推荐生产环境）

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app
COPY im-bridge-server.js .
COPY qq-adapter.js .
COPY package.json .
RUN npm install --production

# 安装go-cqhttp（或使用官方镜像）
RUN wget https://github.com/Mrs4s/go-cqhttp/releases/download/v1.2.0/go-cqhttp_linux_amd64.tar.gz
RUN tar -xzf go-cqhttp_linux_amd64.tar.gz
RUN mv go-cqhttp /usr/local/bin/

ENV QQ_ENABLE=true
ENV QQ_TARGETS=user:123456

EXPOSE 18080 3000
CMD node im-bridge-server.js
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
    depends_on:
      - go-cqhttp

  go-cqhttp:
    image: mrs4s/go-cqhttp:latest
    ports:
      - "3000:3000"
    volumes:
      - ./go-cqhttp-data:/data
```

---

## 📝 配置参数说明

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `QQ_ENABLE` | 启用QQ Bot | `true` |
| `QQ_TARGETS` | 推送目标 | `user:123456` |
| `QQ_API_URL` | go-cqhttp地址 | `http://localhost:3000` |

### 可选参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `QQ_ACCESS_TOKEN` | 访问令牌 | 无 | `your-secret-token` |
| `QQ_PLATFORM` | Bot平台 | `go-cqhttp` | `shamrock` |
| `QQ_ENABLED_EVENTS` | 事件类型 | `complete,error,phase` | `complete` |

### 推送目标格式

```
QQ_TARGETS=user:123456              # 发送到QQ号123456
QQ_TARGETS=group:789                 # 发送到群号789
QQ_TARGETS=user:123,group:456       # 发送到私聊和群
QQ_TARGETS=user:123,user:456        # 发送到多个QQ号
```

---

## 🧪 验证配置

### 1. 检查go-cqhttp

```bash
curl http://localhost:3000/get_login_info
```

**成功响应**:
```json
{
  "retcode": 0,
  "data": {
    "user_id": 123456789,
    "nickname": "你的昵称"
  }
}
```

### 2. 测试QQ消息

```bash
curl -X POST http://localhost:3000/send_private_msg \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123456789,
    "message": "测试消息"
  }'
```

### 3. 运行完整测试

```bash
python tests/test_qq_integration.py
```

---

## 🎯 常见配置场景

### 场景1：推送到自己（最简单）

```bash
QQ_ENABLE=true
QQ_TARGETS=user:你的QQ号
QQ_ENABLED_EVENTS=complete,error
```

### 场景2：推送到群组

```bash
QQ_ENABLE=true
QQ_TARGETS=group:群号
QQ_ENABLED_EVENTS=complete,error,phase
```

### 场景3：推送到多个目标

```bash
QQ_ENABLE=true
QQ_TARGETS=user:你的QQ号,group:群号,group:另一个群号
QQ_ENABLED_EVENTS=complete,error
```

### 场景4：只推送关键事件

```bash
QQ_ENABLE=true
QQ_TARGETS=user:你的QQ号
QQ_ENABLED_EVENTS=complete  # 只推送完成事件
```

---

## 🐛 常见问题

### 问题1：go-cqhttp启动失败

**检查清单**:
```bash
# 1. 端口是否被占用
netstat -an | grep 3000

# 2. 文件权限
ls -la go-cqhttp/go-cqhttp

# 3. 依赖是否完整
ldd go-cqhttp/go-cqhttp  # Linux
```

**解决方案**:
```bash
# 修改端口（在config.yml中）
servers:
  - http:
      port: 3001  # 改用其他端口

# 或关闭占用进程
pkill go-cqhttp
```

### 问题2：扫码登录失败

**滑块验证**:
```bash
# 安装依赖
pip install Pillow numpy

# 使用验证工具
# 参考：https://github.com/TkMurakami/go-cqhttp-slider-captcha
```

**设备锁验证**:
- 发送短信验证
- 使用密保问题验证

**账号被冻结**:
- 等待24小时后重试
- 使用新QQ号

### 问题3：消息发送失败

**可能原因**:
- 目标QQ号/群不存在
- 没有发送权限
- 触发风控

**解决方案**:
```bash
# 1. 先测试给自己发消息
QQ_TARGETS=user:自己的QQ号

# 2. 降低发送频率
# 在go-cqhttp配置中设置限流

# 3. 查看go-cqhttp日志
tail -f go-cqhttp.log
```

---

## 📊 配置完成后

### 系统状态

```bash
# 检查go-cqhttp
curl http://localhost:3000/get_status

# 检查IM Bridge
curl http://localhost:18080/health

# 查看统计
curl http://localhost:18080/stats
```

### 预期输出

```json
{
  "status": "healthy",
  "uptime": 123.45,
  "stats": {
    "eventsReceived": 5,
    "qqMessagesSent": 5,
    "qqMessagesFailed": 0
  }
}
```

---

## 🚀 开始使用

配置完成后，EventBroadcaster会自动推送任务通知到QQ：

```python
from app.gateway.event_broadcaster import EventBroadcaster, Event

# 初始化（会自动读取环境变量）
broadcaster = EventBroadcaster(
    im_webhook_url="http://localhost:18080/opencode/events"
)

# 创建事件
event = Event(
    event_type="complete",
    session_id="task-123",
    data={"result": "success"}
)

# 广播事件（自动推送到QQ）
await broadcaster.broadcast(event)
```

**QQ收到消息**:
```
✅ OpenCode任务完成

结果: success
```

---

## 💡 最佳实践

1. **测试优先**: 先给自己发消息测试
2. **渐进式**: 只启用complete事件，逐步增加
3. **监控日志**: 定期检查发送成功率
4. **备用方案**: 配置多个推送目标
5. **定期维护**: 更新go-cqhttp到最新版本

---

## 📚 相关文档

- **go-cqhttp安装**: `GO_CQHTTP_SETUP.md`
- **QQ集成指南**: `QQ_INTEGRATION_GUIDE.md`
- **完整文档**: `QQ_INTEGRATION_COMPLETE.md`

---

## 🆘 获取帮助

- **go-cqhttp文档**: https://docs.go-cqhttp.org/
- **GitHub**: https://github.com/Mrs4s/go-cqhttp
- **社区**: 搜索"go-cqhttp QQ群"

---

**准备好开始配置了吗？选择上面任一方式即可！** 🎉
