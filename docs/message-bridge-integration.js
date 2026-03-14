/**
 * message-bridge 集成示例
 *
 * 这个文件展示如何在 message-bridge-opencode-plugin 中
 * 添加HTTP端点来接收来自 OpenCode EventBroadcaster 的事件
 *
 * 使用方法：
 * 1. 在 message-bridge 的主文件中添加此端点
 * 2. 配置 OPENCODE_IM_WEBHOOK_URL 指向此端点
 * 3. EventBroadcaster 会自动推送事件到这个端点
 */

// ============================================================================
// 方案1: Express.js 端点（推荐用于生产环境）
// ============================================================================

const express = require('express');
const app = express();

app.use(express.json());

/**
 * 接收 OpenCode EventBroadcaster 的事件
 * 路径: /opencode/events
 */
app.post('/opencode/events', async (req, res) => {
  try {
    const { event_type, session_id, data, timestamp } = req.body;

    console.log(`[EventBroadcaster] Received event: ${event_type}`);

    // 根据事件类型转换为IM消息
    const message = formatEventToIMMessage(event_type, data);

    // 发送到配置的IM平台（飞书/Telegram等）
    // 这里假设你已经初始化了 platformAdapter
    await platformAdapter.sendMessage(message);

    // 返回成功响应
    res.json({
      success: true,
      event_id: req.body.event_id,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('[EventBroadcaster] Error processing event:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * 将 OpenCode 事件格式化为IM消息
 */
function formatEventToIMMessage(eventType, data) {
  switch (eventType) {
    case 'complete':
      const result = data.result || 'success';
      return `✅ 任务完成\n结果: ${result}`;

    case 'error':
      const errorMsg = data.error || '未知错误';
      return `❌ 任务失败\n错误: ${errorMsg}`;

    case 'phase':
      const phase = data.phase || 'unknown';
      const description = data.description || '';
      return `🔄 任务阶段\n阶段: ${phase}\n${description}`;

    case 'action':
      const action = data.action || 'unknown';
      const file = data.file || '';
      return `⚙️ 执行操作\n${action} ${file ? `→ ${file}` : ''}`;

    case 'progress':
      const progress = data.progress || 0;
      const message = data.message || '';
      return `📊 任务进度\n${progress}%\n${message}`;

    default:
      return `📡 事件: ${eventType}\n${JSON.stringify(data, null, 2)}`;
  }
}

// 启动服务器
const PORT = process.env.IM_BRIDGE_PORT || 18080;
app.listen(PORT, () => {
  console.log(`IM Bridge server listening on port ${PORT}`);
  console.log(`Event endpoint: http://localhost:${PORT}/opencode/events`);
});


// ============================================================================
// 方案2: FastAPI 端点（推荐用于Python环境）
// ============================================================================

/*
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

app = FastAPI()

class EventPayload(BaseModel):
    event_id: str
    event_type: str
    session_id: str
    timestamp: str
    data: Dict[str, Any]

@app.post("/opencode/events")
async def receive_opencode_event(event: EventPayload):
    '''接收来自 EventBroadcaster 的事件'''

    try:
        print(f"[EventBroadcaster] Received event: {event.event_type}")

        # 格式化为IM消息
        message = format_event_to_im_message(event.event_type, event.data)

        # 发送到IM平台
        # 这里需要根据你使用的IM平台API调用
        await send_to_im_platform(message)

        return {
            "success": True,
            "event_id": event.event_id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"[EventBroadcaster] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def format_event_to_im_message(event_type: str, data: Dict[str, Any]) -> str:
    '''格式化事件为IM消息'''

    if event_type == "complete":
        result = data.get("result", "success")
        return f"✅ 任务完成\n结果: {result}"

    elif event_type == "error":
        error = data.get("error", "未知错误")
        return f"❌ 任务失败\n错误: {error}"

    elif event_type == "phase":
        phase = data.get("phase", "unknown")
        description = data.get("description", "")
        return f"🔄 任务阶段\n阶段: {phase}\n{description}"

    # ... 其他事件类型

    return f"📡 {event_type}: {data}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18080)
*/


// ============================================================================
// 方案3: 无服务器函数（AWS Lambda / 阿里云函数计算）
// ============================================================================

/*
exports.handler = async (event, context) => {
  try {
    // 解析请求体
    const body = JSON.parse(event.body);

    console.log('[EventBroadcaster] Received event:', body.event_type);

    // 格式化消息
    const message = formatEventToIMMessage(body.event_type, body.data);

    // 发送到IM平台
    await sendToIMPlatform(message);

    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        event_id: body.event_id
      })
    };

  } catch (error) {
    console.error('[EventBroadcaster] Error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({
        success: false,
        error: error.message
      })
    };
  }
};
*/


// ============================================================================
// 配置示例
// ============================================================================

/**
 * 在 OpenCode 的环境变量中配置：
 *
 * export OPENCODE_IM_WEBHOOK_URL="http://localhost:18080/opencode/events"
 *
 * 或在 Python 代码中配置：
 *
 * broadcaster = EventBroadcaster(
 *     max_history=1000,
 *     im_webhook_url="http://localhost:18080/opencode/events",
 *     im_enabled_events=["complete", "error", "phase"]
 * )
 *
 */

// ============================================================================
// 测试端点
// ============================================================================

/**
 * 手动测试端点
 * curl -X POST http://localhost:18080/opencode/events \
 *   -H "Content-Type: application/json" \
 *   -d '{
 *     "event_id": "test-123",
 *     "event_type": "complete",
 *     "session_id": "ses-test",
 *     "timestamp": "2026-03-14T10:00:00",
 *     "data": {"result": "success"}
 *   }'
 */

app.post('/test/event', (req, res) => {
  const testEvent = {
    event_id: 'test-' + Date.now(),
    event_type: 'complete',
    session_id: 'ses-test',
    timestamp: new Date().toISOString(),
    data: {
      result: 'success',
      message: 'This is a test event from EventBroadcaster'
    }
  };

  console.log('[Test] Sending test event to /opencode/events');

  // 内部转发到实际端点
  fetch('http://localhost:' + PORT + '/opencode/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(testEvent)
  })
  .then(response => response.json())
  .then(data => {
    res.json({
      test: true,
      event: testEvent,
      result: data
    });
  })
  .catch(error => {
    res.status(500).json({
      test: true,
      error: error.message
    });
  });
});

module.exports = app;
