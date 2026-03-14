# EventBroadcaster IM集成指南

本文档说明如何将OpenCode EventBroadcaster与message-bridge集成，实现任务执行状态的IM通知。

## 📋 概述

EventBroadcaster支持将事件推送到IM桥接服务（如message-bridge-opencode-plugin），从而在飞书、Telegram等IM平台接收任务执行通知。

### 支持的IM平台

通过message-bridge支持：
- ✅ 飞书 / Lark (Webhook + WebSocket)
- ✅ Telegram (Bot API)
- 🚧 iMessage（开发中）
- 🚧 QQ（开发中）
- 🚧 Slack、Discord（计划中）

## 🚀 快速开始

### 步骤1：配置EventBroadcaster

**方式A：环境变量（推荐）**

```bash
# 在 .env 文件中添加
OPENCODE_IM_WEBHOOK_URL=http://localhost:18080/opencode/events
OPENCODE_IM_ENABLED_EVENTS=complete,error,phase
```

**方式B：Python代码配置**

```python
from app.gateway.event_broadcaster import EventBroadcaster

broadcaster = EventBroadcaster(
    max_history=1000,
    im_webhook_url="http://localhost:18080/opencode/events",
    im_enabled_events=["complete", "error", "phase"]
)
await broadcaster.start()
```

**方式C：Gateway配置**

```python
from app.gateway.gateway import Gateway, GatewayConfig

config = GatewayConfig(
    # ... 其他配置
    im_webhook_url="http://localhost:18080/opencode/events",
    im_enabled_events=["complete", "error", "phase", "action"]
)

gateway = Gateway(config)
```

### 步骤2：部署message-bridge接收端点

参考 `docs/message-bridge-integration.js` 创建HTTP端点接收事件。

**最简单的Express.js示例**：

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/opencode/events', async (req, res) => {
  const { event_type, data } = req.body;

  let message = '';
  switch(event_type) {
    case 'complete':
      message = `✅ 任务完成: ${data.result}`;
      break;
    case 'error':
      message = `❌ 任务失败: ${data.error}`;
      break;
    case 'phase':
      message = `🔄 阶段: ${data.phase}`;
      break;
  }

  // 发送到IM平台（需要根据实际平台API调用）
  await sendToIMPlatform(message);

  res.json({ success: true });
});

app.listen(18080, () => {
  console.log('IM bridge listening on port 18080');
});
```

### 步骤3：测试集成

```bash
# 1. 启动message-bridge接收端点
node im-bridge-server.js &

# 2. 发送测试事件
curl -X POST http://localhost:18080/test/event

# 3. 或通过Python测试
python -c "
import asyncio
from app.gateway.event_broadcaster import EventBroadcaster, Event

async def test():
    broadcaster = EventBroadcaster(
        im_webhook_url='http://localhost:18080/opencode/events'
    )

    event = Event(
        event_type='complete',
        session_id='test-session',
        data={'result': 'success'}
    )

    await broadcaster._push_to_im(event)
    print('Event pushed to IM')

asyncio.run(test())
"
```

## 📊 事件类型

EventBroadcaster支持以下事件类型：

| 事件类型 | 说明 | 默认推送 | 推荐IM格式 |
|---------|------|---------|-----------|
| `complete` | 任务完成 | ✅ | ✅ 任务完成: {result} |
| `error` | 任务失败 | ✅ | ❌ 任务失败: {error} |
| `phase` | 阶段变更 | ✅ | 🔄 阶段: {phase} |
| `action` | 执行操作 | ❌ | ⚙️ 操作: {action} |
| `progress` | 进度更新 | ❌ | 📊 进度: {progress}% |

### 配置推送事件类型

```python
# 只推送关键事件
broadcaster = EventBroadcaster(
    im_webhook_url="http://localhost:18080/opencode/events",
    im_enabled_events=["complete", "error"]  # 仅完成和失败
)

# 推送所有事件
broadcaster = EventBroadcaster(
    im_webhook_url="http://localhost:18080/opencode/events",
    im_enabled_events=["complete", "error", "phase", "action", "progress"]
)

# 只推送进度
broadcaster = EventBroadcaster(
    im_webhook_url="http://localhost:18080/opencode/events",
    im_enabled_events=["progress"]
)
```

## 🔧 高级配置

### 超时控制

```python
# 在event_broadcaster.py中修改默认超时（5秒）
async with session.post(
    self.im_webhook_url,
    json=payload,
    timeout=aiohttp.ClientTimeout(total=10)  # 改为10秒
) as response:
    ...
```

### 重试策略

```python
# 在event_broadcaster.py的_push_to_im中添加重试
async def _push_to_im(self, event: Event, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            # ... 发送逻辑
            if response.status == 200:
                return True
        except Exception as e:
            if attempt == max_retries - 1:
                self.logger.error(f"IM push failed after {max_retries} retries")
                return False
            await asyncio.sleep(2 ** attempt)  # 指数退避
```

### 消息格式化

在message-bridge端添加富文本支持：

```javascript
function formatEventToIMMessage(eventType, data) {
  switch (eventType) {
    case 'complete':
      // 飞书卡片格式
      return {
        msg_type: "interactive",
        card: {
          header: {
            title: {
              tag: "plain_text",
              content: "✅ 任务完成"
            }
          },
          elements: [
            {
              tag: "div",
              text: {
                tag: "plain_text",
                content: `结果: ${data.result}`
              }
            }
          ]
        }
      };

    default:
      return {
        msg_type: "text",
        content: {
          text: `📡 ${eventType}: ${JSON.stringify(data)}`
        }
      };
  }
}
```

## 📈 监控和统计

### 查看统计信息

```python
stats = broadcaster.get_stats()

print(f"IM通知发送成功: {stats['im_notifications_sent']}")
print(f"IM通知发送失败: {stats['im_notifications_failed']}")
print(f"IM webhook已配置: {stats['im_webhook_configured']}")
```

### Prometheus指标

```python
# 在event_broadcaster.py中添加Prometheus支持
from prometheus_client import Counter, Gauge

im_notifications_sent = Counter(
    'opencode_im_notifications_sent_total',
    'Total IM notifications sent'
)

im_notifications_failed = Counter(
    'opencode_im_notifications_failed_total',
    'Total IM notifications failed'
)

# 在_push_to_im中更新指标
if success:
    im_notifications_sent.inc()
else:
    im_notifications_failed.inc()
```

## 🧪 测试

### 单元测试

```bash
# 运行IM集成测试
pytest tests/test_event_broadcaster_im_integration.py -v
```

### 手动测试

```python
import asyncio
from app.gateway.event_broadcaster import EventBroadcaster, Event

async def test_im_integration():
    broadcaster = EventBroadcaster(
        im_webhook_url="http://localhost:18080/opencode/events",
        im_enabled_events=["complete", "error", "phase"]
    )

    # 测试各种事件
    events = [
        Event(event_type="phase", session_id="test", data={"phase": "planning"}),
        Event(event_type="action", session_id="test", data={"action": "create_file"}),
        Event(event_type="complete", session_id="test", data={"result": "success"}),
        Event(event_type="error", session_id="test", data={"error": "test error"}),
    ]

    for event in events:
        await broadcaster.broadcast(event)
        print(f"Event {event.event_type} broadcasted")

    stats = broadcaster.get_stats()
    print(f"\nStats:")
    print(f"  Sent: {stats['im_notifications_sent']}")
    print(f"  Failed: {stats['im_notifications_failed']}")

asyncio.run(test_im_integration())
```

## 🐛 故障排查

### 问题1：IM通知未收到

**检查清单**：

```python
# 1. 确认webhook URL配置正确
print(broadcaster.im_webhook_url)

# 2. 确认事件类型在允许列表中
print(broadcaster.im_enabled_events)

# 3. 查看统计信息
stats = broadcaster.get_stats()
print(f"Sent: {stats['im_notifications_sent']}")
print(f"Failed: {stats['im_notifications_failed']}")

# 4. 启用调试日志
import logging
logging.getLogger('app.gateway.event_broadcaster').setLevel(logging.DEBUG)
```

### 问题2：推送超时

**解决方案**：

```python
# 增加超时时间（在_push_to_im中）
async with session.post(
    self.im_webhook_url,
    json=payload,
    timeout=aiohttp.ClientTimeout(total=10)  # 从5秒增加到10秒
)
```

### 问题3：消息格式不兼容

**解决方案**：在message-bridge端添加消息格式转换

```javascript
// 处理特殊字符
function sanitizeMessage(message) {
  return message
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
```

## 📚 相关文档

- [EventBroadcaster API文档](./event_broadcaster_api.md)
- [message-bridge集成示例](./message-bridge-integration.js)
- [IM平台配置指南](./im-platforms-config.md)

## 🆘 获取帮助

- GitHub Issues: https://github.com/your-org/opencode/issues
- 文档: https://docs.opencode.example.com
- 社区: https://discord.gg/opencode
