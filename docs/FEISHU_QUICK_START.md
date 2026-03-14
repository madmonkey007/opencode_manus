# 飞书机器人快速集成指南

## 🎯 为什么选择飞书？

| 特性 | 飞书 | QQ官方机器人 | go-cqhttp |
|------|------|------------|-----------|
| **配置难度** | ⭐ 极简单 | ⭐⭐⭐⭐⭐ 极难 | ⭐⭐ 中等 |
| **配置时间** | 2分钟 | 数周申请 | 5-10分钟 |
| **是否需要审核** | ❌ 不需要 | ✅ 需要 | ❌ 不需要 |
| **是否需要程序** | ❌ 不需要 | ❌ 不需要 | ✅ 需要 |
| **稳定性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **消息格式** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

**结论**：飞书是最简单、最快的方案！

---

## 🚀 3分钟快速配置

### 第1步：获取飞书Webhook（1分钟）

1. **打开飞书群聊**
   - 在你想接收通知的群聊中

2. **添加自定义机器人**
   - 点击右上角 `...`（更多）
   - 选择 `群机器人` → `添加机器人`
   - 选择 `自定义机器人`

3. **复制Webhook URL**
   - 创建后会显示Webhook URL
   - 格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxx`
   - 点击"复制"

### 第2步：运行配置脚本（1分钟）

**Windows**:
```bash
# 双击运行
start-feishu.bat
```

**脚本会引导你**：
1. 粘贴Webhook URL
2. 自动创建配置文件
3. 启动IM Bridge服务器

### 第3步：测试（1分钟）

```bash
curl -X POST http://localhost:18080/test/event \
  -H "Content-Type: application/json" \
  -d '{"event_type":"complete","data":{"result":"success"}}'
```

**完成！** 飞书群会立即收到测试消息。

---

## 📝 手动配置（可选）

如果你想手动配置：

### 创建 `.env.feishu` 文件

```bash
# 启用飞书通知
FEISHU_ENABLE=true

# 使用飞书平台
IM_PLATFORM=feishu

# 飞书Webhook URL（从机器人设置中复制）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxxxxxxxx

# 启用的事件类型
FEISHU_ENABLED_EVENTS=complete,error,phase

# IM Bridge端口
IM_BRIDGE_PORT=18080
```

### 启动服务器

```bash
python start-im-bridge.py
```

或直接使用node：

```bash
IM_PLATFORM=feishu ^
FEISHU_ENABLE=true ^
FEISHU_WEBHOOK_URL=你的webhook_url ^
node im-bridge-server.js
```

---

## 🔧 配置参数说明

### 环境变量

| 变量名 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `IM_PLATFORM` | ✅ | IM平台类型 | `feishu` |
| `FEISHU_ENABLE` | ✅ | 启用飞书通知 | `true` |
| `FEISHU_WEBHOOK_URL` | ✅ | 飞书Webhook地址 | `https://open.feishu.cn/...` |
| `FEISHU_ENABLED_EVENTS` | ⚠️ | 事件过滤 | `complete,error,phase` |
| `IM_BRIDGE_PORT` | ⚠️ | 服务器端口 | `18080` |

### 事件类型

| 事件 | 说明 | 示例消息 |
|------|------|---------|
| `complete` | 任务完成 | ✅ **OpenCode任务通知**<br>**状态**: 任务完成<br>**结果**: success |
| `error` | 任务失败 | ❌ **OpenCode任务通知**<br>**状态**: 任务失败<br>**错误**: ValueError |
| `phase` | 阶段更新 | 🔄 **OpenCode任务通知**<br>**阶段**: planning<br>**描述**: 任务规划中 |
| `progress` | 进度更新 | 📊 **OpenCode任务通知**<br>**进度**: 50% |

---

## 🧪 测试验证

### 1. 健康检查

```bash
curl http://localhost:18080/health
```

**期望响应**：
```json
{
  "status": "healthy",
  "uptime": 123.45,
  "platform": "feishu",
  "stats": {
    "eventsReceived": 0,
    "messagesSent": 0,
    "messagesFailed": 0
  }
}
```

### 2. 发送测试事件

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

### 3. 检查统计信息

```bash
curl http://localhost:18080/stats
```

---

## 🔄 从其他平台切换

### 从QQ切换到飞书

只需修改环境变量：

```bash
# 修改平台类型
IM_PLATFORM=feishu  # 从 'qq' 或 'qq-official' 改为 'feishu'

# 添加飞书配置
FEISHU_ENABLE=true
FEISHU_WEBHOOK_URL=你的webhook_url
```

### 支持多平台同时使用

如果你想同时使用多个平台：

```bash
# 主要平台
IM_PLATFORM=feishu
FEISHU_ENABLE=true
FEISHU_WEBHOOK_URL=webhook1

# 备用平台（需要修改服务器代码支持）
# QQ_ENABLE=true
# QQ_TARGETS=user:123456
```

---

## 🛠️ 故障排查

### 问题1：消息发送失败

**症状**：
```
❌ 消息发送失败: Webhook URL not configured
```

**解决方案**：
1. 检查 `.env.feishu` 文件是否存在
2. 确认 `FEISHU_WEBHOOK_URL` 已设置
3. 验证URL格式是否正确

### 问题2：Webhook URL无效

**症状**：
```
❌ 消息发送失败: Invalid webhook
```

**解决方案**：
1. 重新从飞书机器人设置中复制Webhook URL
2. 确认机器人没有被删除
3. 检查URL是否完整（没有被截断）

### 问题3：飞书群收不到消息

**可能原因**：
- 机器人被禁用了
- Webhook URL过期了
- 网络连接问题

**解决方案**：
1. 检查飞书群中的机器人状态
2. 重新获取Webhook URL
3. 检查服务器能否访问外网

### 问题4：消息格式显示异常

**症状**：消息中的emoji或格式显示不正确

**解决方案**：
- 飞书支持大部分emoji
- 某些特殊字符可能需要转义
- 可以修改 `feishu-webhook-adapter.js` 调整消息格式

---

## 📚 进阶功能

### 1. 发送到多个群

如果你想同时发送到多个飞书群：

**修改服务器代码**支持多个Webhook：

```javascript
// 在im-bridge-server.js中
const webhookUrls = process.env.FEISHU_WEBHOOK_URL
  ? process.env.FEISHU_WEBHOOK_URL.split(',')
  : [];

for (const webhookUrl of webhookUrls) {
  const adapter = new FeishuWebhookAdapter({ webhookUrl });
  await adapter.sendMessage(message);
}
```

**配置多个Webhook**：
```bash
FEISHU_WEBHOOK_URL=url1,url2,url3
```

### 2. 添加@提醒

在消息中添加@特定成员：

```javascript
// 修改formatOpenCodeEvent方法
message += `\n<at user_id=\"all\">所有成员</at>`;
```

### 3. 发送卡片消息

飞书支持更丰富的卡片格式：

```javascript
{
  "msg_type": "interactive",
  "card": {
    "header": {
      "title": {
        "tag": "plain_text",
        "content": "OpenCode任务完成"
      }
    },
    "elements": [
      {
        "tag": "div",
        "text": {
          "tag": "plain_text",
          "content": "结果: success"
        }
      }
    ]
  }
}
```

---

## ✅ 验收清单

完成配置后，请验证：

- [ ] 飞书群已添加自定义机器人
- [ ] Webhook URL已复制
- [ ] `.env.feishu` 文件已创建
- [ ] IM Bridge服务器正常启动
- [ ] 健康检查返回200
- [ ] 测试消息成功发送到飞书
- [ ] 飞书群能正确显示消息格式

---

## 🎉 完成

现在你的OpenCode已经集成了飞书机器人！

**享受实时通知带来的便利吧！** 🚀

---

## 📞 需要帮助？

- **飞书官方文档**：https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNkE
- **自定义机器人指南**：https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNkE
- **OpenCode配置文件**：`im-bridge-server.js`
- **飞书适配器**：`feishu-webhook-adapter.js`
