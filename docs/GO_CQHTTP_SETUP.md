# go-cqhttp 快速安装指南

## 📋 概述

go-cqhttp是一个基于MiraiGo的QQ Bot框架，支持Android手机协议登录，无需加密卡即可使用。

## 🚀 快速安装

### Windows

#### 方法1：下载预编译版本（推荐）

1. **下载最新版本**
   - 访问：https://github.com/Mrs4s/go-cqhttp/releases
   - 下载：`go-cqhttp_windows_amd64.zip`

2. **解压**
   ```bash
   # 解压到任意目录，如：C:\go-cqhttp
   unzip go-cqhttp_windows_amd64.zip -d C:\go-cqhttp
   cd C:\go-cqhttp
   ```

3. **运行程序**
   ```bash
   # 双击运行
   go-cqhttp.exe

   # 或命令行
   ./go-cqhttp.exe
   ```

4. **扫码登录**
   - 首次运行会生成配置文件
   - 再次运行会显示二维码
   - 使用手机QQ扫描登录

#### 方法2：使用Docker（推荐）

```bash
# 拉取镜像
docker pull mrs4s/go-cqhttp:latest

# 运行容器
docker run -d \
  --name go-cqhttp \
  -p 3000:3000 \
  -v /path/to/config:/data \
  mrs4s/go-cqhttp:latest
```

### Linux/Mac

```bash
# 下载
wget https://github.com/Mrs4s/go-cqhttp/releases/download/v1.2.0/go-cqhttp_linux_amd64.tar.gz

# 解压
tar -xzf go-cqhttp_linux_amd64.tar.gz
cd go-cqhttp

# 运行
./go-cqhttp
```

## ⚙️ 配置文件

首次运行后会生成 `config.yml`，关键配置：

```yaml
# QQ账号
account: # 账号相关
  uin: 123456789 # QQ账号（无需密码，扫码登录）
  password: '' # 密码留空，扫码登录
  encrypt: false  # 是否加密密码
  status: 0      # 在线状态

# 心跳间隔
heartbeat:
  interval: 5

# API设置
servers:
  - http:
      host: 0.0.0.0
      port: 3000          # API端口（默认）
      token: ''           # 访问令牌（可选）
      post: []            # 上报地址

# 消息设置
message:
  post-format: string    # 消息格式
  ignore-invalid-cqcode: false
  force-fragment: false

# 输出设置
output:
  log-level: warn         # 日志级别
  debug: false
```

## 🔑 首次登录

1. **启动程序**
   ```bash
   ./go-cqhttp
   ```

2. **扫描二维码**
   - 终端会显示ASCII二维码
   - 或在 `data/qrcode.png` 查看图片

3. **手机扫码**
   - 打开手机QQ → 扫一扫
   - 确认登录

4. **设备锁验证**
   - 如有设备锁，按提示短信验证

5. **登录成功**
   - 看到日志：`Bot 登录成功`
   - API服务器启动在 http://0.0.0.0:3000

## 🧪 测试API

### 1. 获取登录信息

```bash
curl http://localhost:3000/get_login_info
```

**响应**：
```json
{
  "retcode": 0,
  "status": "ok",
  "data": {
    "user_id": 123456789,
    "nickname": "你的昵称"
  }
}
```

### 2. 发送私聊消息

```bash
curl -X POST http://localhost:3000/send_private_msg \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123456789,
    "message": "测试消息"
  }'
```

### 3. 发送群消息

```bash
curl -X POST http://localhost:3000/send_group_msg \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 987654321,
    "message": "测试群消息"
  }'
```

## 🔧 常见问题

### 问题1：登录失败 - 需要滑块验证

**解决方案**：
```bash
# 1. 安装依赖
pip install Pillow numpy

# 2. 使用滑块验证工具
# https://github.com/TkMurakami/go-cqhttp-slider-captcha
```

### 问题2：登录失败 - 需要设备锁

**解决方案**：
- 按提示发送短信验证
- 或使用手机密保验证

### 问题3：API无法访问

**检查清单**：
```bash
# 1. 确认进程运行
ps aux | grep go-cqhttp

# 2. 确认端口监听
netstat -an | grep 3000

# 3. 检查防火墙
# Windows: 控制面板 → 系统和安全 → Windows防火墙
# Linux: sudo ufw allow 3000
```

### 问题4：消息发送失败

**可能原因**：
- 好友/群不存在
- 没有权限发消息
- 触发风控

**解决方案**：
- 先给自己发消息测试
- 避免频繁发送（限流）
- 避免敏感词

## 📊 性能优化

### 1. 减少日志输出

```yaml
output:
  log-level: warn  # 只显示警告和错误
```

### 2. 调整心跳间隔

```yaml
heartbeat:
  interval: 5  # 5秒心跳（默认）
```

### 3. 限制并发数

```yaml
account:
  relogin:
    max-retry-times: 3
    relogin-delay: 3000
```

## 🔐 安全建议

### 1. 设置访问令牌

```yaml
servers:
  - http:
      token: "your-secret-token-here"
```

### 2. 绑定本地地址

```yaml
servers:
  - http:
      host: 127.0.0.1  # 只允许本地访问
```

### 3. 使用HTTPS反向代理

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /cqhttp {
        proxy_pass http://localhost:3000;
    }
}
```

## 📚 进阶配置

### 消息上报

```yaml
servers:
  - http:
      post:
        - url: http://your-server.com/callback
          secret: "your-secret"
```

### 自动回复

```javascript
// 使用Node.js监听消息
app.post('/callback', (req, res) => {
  const message = req.body.message;

  if (message === 'hello') {
    // 调用API回复
    sendReply(req.body.user_id, '你好！');
  }
});
```

### CQ码使用

```
[CQ:at,qq=123456]              @某人
[CQ:image,file=/path/to.jpg]   发送图片
[CQ:music,type=qq,id=123456]   发送音乐
[CQ:json,data=...]             发送JSON卡片
```

## 🆘 获取帮助

- **官方文档**: https://docs.go-cqhttp.org/
- **GitHub**: https://github.com/Mrs4s/go-cqhttp
- **社区**: https://jq.qq.com/

## 📝 下一步

安装完成后，继续配置OpenCode集成：

1. 设置环境变量
2. 配置推送目标
3. 测试消息推送
4. 监控运行状态

详细配置见：`QQ_INTEGRATION_GUIDE.md`
