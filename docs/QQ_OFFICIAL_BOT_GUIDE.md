# QQ官方机器人集成指南

## 📋 概述

本指南介绍如何使用QQ官方机器人API为OpenCode添加QQ通知功能。

---

## ✅ 优势

与go-cqhttp相比，QQ官方机器人的优势：

| 特性 | QQ官方机器人 | go-cqhttp |
|------|-------------|-----------|
| **稳定性** | ⭐⭐⭐⭐⭐ 官方保证 | ⭐⭐⭐⭐ 依赖协议 |
| **封号风险** | ✅ 无（官方授权） | ⚠️ 理论上有 |
| **维护成本** | ⭐⭐⭐⭐⭐ 几乎为零 | ⭐⭐⭐ 需要更新 |
| **部署** | ✅ 无需本地程序 | ❌ 需要运行本地程序 |
| **合规性** | ✅ 完全合规 | ⚠️ 灰色地带 |
| **申请难度** | ⭐⭐⭐⭐⭐ 极难 | ⭐ 非常容易 |

---

## 🔑 前置条件

### 必需信息

在使用QQ官方机器人之前，你需要准备：

1. **QQ机器人AppID**
   - 从QQ开放平台获取
   - 网址：https://bot.q.qq.com
   - 需要企业认证或特殊资质

2. **QQ机器人Token**
   - 在QQ开放平台创建机器人后获得
   - 用于API调用鉴权

3. **你的OpenID**
   - 机器人的用户标识
   - 不是QQ号，是机器人的用户ID
   - 可以通过API获取

---

## 🚀 快速开始

### 方式1：使用配置脚本（推荐）

**Windows**:
```bash
# 双击运行脚本
start-qq-official.bat
```

**脚本会自动**:
1. 引导输入AppID和Token
2. 创建.env配置文件
3. 启动IM Bridge服务器
4. 验证配置是否正确

### 方式2：手动配置

**第1步：创建配置文件**

创建 `.env` 文件：

```bash
# 启用QQ通知
QQ_ENABLE=true

# 使用官方机器人
QQ_BOT_TYPE=official

# 你的机器人信息
QQ_APP_ID=your_app_id
QQ_TOKEN=your_token

# 环境（false=生产，true=沙箱）
QQ_SANDBOX=false

# 推送目标（你的OpenID）
QQ_TARGETS=user:your_openid

# 启用的事件类型
QQ_ENABLED_EVENTS=complete,error,phase

# IM Bridge端口
IM_BRIDGE_PORT=18080
```

**第2步：启动服务器**

```bash
node im-bridge-server.js
```

**第3步：测试**

```bash
curl -X POST http://localhost:18080/test/event \
  -H "Content-Type: application/json" \
  -d '{"event_type":"complete","data":{"result":"success"}}'
```

---

## 📝 获取OpenID的方法

OpenID是机器人的用户标识，不是QQ号。获取方法：

### 方法1：通过机器人事件

当用户首次与机器人交互时，你会收到事件：

```json
{
  "openid": "xxxxxxxxxx",
  "unionid": "xxxxxxxxxx"
}
```

### 方法2：通过API查询

如果你有用户的QQ号，可以通过API查询OpenID：

```javascript
// 伪代码，实际API请参考官方文档
const response = await fetch(
    `https://api.q.qq.com/some/api?qq=${user_qq}`,
    {
        headers: { 'Authorization': `Bearer ${token}` }
    }
);
const data = await response.json();
const openid = data.openid;
```

### 方法3：测试号使用

如果是测试环境，可以使用机器人管理后台提供的测试用户OpenID。

---

## 🔧 配置参数说明

### 环境变量

| 变量名 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `QQ_ENABLE` | ✅ | 启用QQ通知 | `true` |
| `QQ_BOT_TYPE` | ✅ | 机器人类型 | `official` |
| `QQ_APP_ID` | ✅ | 机器人AppID | `123456789` |
| `QQ_TOKEN` | ✅ | 机器人Token | `abcdefg...` |
| `QQ_SANDBOX` | ⚠️ | 沙箱环境 | `false` |
| `QQ_TARGETS` | ✅ | 推送目标 | `user:openid` |
| `QQ_ENABLED_EVENTS` | ⚠️ | 事件过滤 | `complete,error` |

### 推送目标格式

```
QQ_TARGETS=user:OPENID1,user:OPENID2
QQ_TARGETS=group:GROUP_ID1,group:GROUP_ID2
QQ_TARGETS=user:OPENID,group:GROUP_ID
```

### 事件类型

| 事件 | 说明 | 示例 |
|------|------|------|
| `complete` | 任务完成 | ✅ 任务完成\n结果: success |
| `error` | 任务失败 | ❌ 任务失败\n错误: xxx |
| `phase` | 阶段更新 | 🔄 任务阶段\n阶段: coding |
| `progress` | 进度更新 | 📊 任务进度\n50% |
| `action` | 执行操作 | ⚡ 执行操作\n创建文件 |

---

## 🧪 测试验证

### 1. 健康检查

```bash
curl http://localhost:18080/health
```

**期望响应**:
```json
{
  "status": "healthy",
  "uptime": 123.45,
  "stats": {
    "eventsReceived": 0,
    "eventsByType": {},
    "qqMessagesSent": 0,
    "qqMessagesFailed": 0
  }
}
```

### 2. 统计信息

```bash
curl http://localhost:18080/stats
```

### 3. 发送测试事件

```bash
curl -X POST http://localhost:18080/test/event \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "complete",
    "data": {
      "result": "success",
      "message": "测试消息"
    }
  }'
```

---

## 📊 与EventBroadcaster集成

EventBroadcaster会自动推送事件到IM Bridge。

### 配置EventBroadcaster

```python
from app.gateway.event_broadcaster import EventBroadcaster

broadcaster = EventBroadcaster(
    im_webhook_url="http://localhost:18080/opencode/events",
    im_enabled_events=["complete", "error", "phase"]
)
```

### 推送的事件格式

```json
{
  "event_id": "ses_abc123_complete",
  "event_type": "complete",
  "session_id": "ses_abc123",
  "timestamp": "2026-03-14T10:00:00Z",
  "data": {
    "result": "success",
    "files": ["main.py", "utils.py"]
  }
}
```

---

## 🛠️ 故障排查

### 问题1：消息发送失败

**症状**:
```
❌ QQ消息发送失败: Unauthorized
```

**解决方案**:
1. 检查Token是否正确
2. 检查Token是否过期
3. 确认AppID和Token匹配

### 问题2：无法连接API

**症状**:
```
❌ QQ消息发送失败: Network error
```

**解决方案**:
1. 检查网络连接
2. 如果使用沙箱，检查沙箱URL是否正确
3. 检查防火墙设置

### 问题3：OpenID错误

**症状**:
```
❌ QQ消息发送失败: Invalid openid
```

**解决方案**:
1. 确认OpenID格式正确
2. 通过机器人管理后台查询正确的OpenID
3. 确保用户已关注/添加机器人

### 问题4：消息格式问题

**症状**:
```
✅ 消息已发送，但QQ收到乱码或格式错误
```

**解决方案**:
1. 检查消息编码
2. 避免使用特殊字符
3. 控制消息长度（QQ有长度限制）

---

## 📚 参考资源

### 官方文档

- **QQ开放平台**: https://bot.q.qq.com
- **API文档**: https://bot.q.qq.com/wiki/develop/api/
- **开发指南**: https://bot.q.qq.com/wiki/

### OpenCode文档

- **EventBroadcaster**: `app/gateway/event_broadcaster.py`
- **IM Bridge**: `im-bridge-server.js`
- **QQ适配器**: `qq-official-adapter.js`

---

## 🔄 从go-cqhttp迁移

如果你之前使用go-cqhttp，迁移到官方机器人很简单：

**第1步：修改.env**

```bash
# 修改这一行
QQ_BOT_TYPE=official  # 从 'go-cqhttp' 改为 'official'

# 添加官方机器人配置
QQ_APP_ID=your_app_id
QQ_TOKEN=your_token

# 移除go-cqhttp配置（不需要了）
# QQ_API_URL=...
```

**第2步：修改推送目标**

```bash
# 从QQ号改为OpenID
QQ_TARGETS=user:YOUR_OPENID  # 之前是 user:QQ_NUMBER
```

**第3步：重启服务器**

```bash
# 停止go-cqhttp（不需要了）
# 重启IM Bridge
node im-bridge-server.js
```

---

## ✅ 验收清单

完成配置后，请验证：

- [ ] IM Bridge服务器正常启动
- [ ] 健康检查返回200
- [ ] 测试消息成功发送到QQ
- [ ] EventBroadcaster事件正常推送
- [ ] 统计信息正确记录

---

## 💡 最佳实践

1. **使用生产环境**
   - 沙箱环境仅供测试
   - 生产环境稳定性更高

2. **Token管理**
   - 定期更换Token
   - 不要提交到代码仓库
   - 使用环境变量

3. **错误处理**
   - 监控发送失败率
   - 设置重试机制
   - 记录错误日志

4. **消息格式**
   - 保持简洁明了
   - 使用emoji增加可读性
   - 控制在合理长度内

5. **监控告警**
   - 定期检查统计信息
   - 设置失败阈值告警
   - 定期测试发送功能

---

## 🎉 完成

现在你的OpenCode已经集成了QQ官方机器人！

当任务完成、失败或更新时，你会立即收到QQ通知。

**享受实时通知带来的便利吧！** 🚀
