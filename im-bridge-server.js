/**
 * OpenCode IM Bridge Server
 *
 * 接收来自EventBroadcaster的事件并转发到IM平台
 *
 * 运行: node im-bridge-server.js
 * 依赖: npm install express body-parser cors
 */

const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const QQAdapter = require('./qq-adapter');
const QQOfficialBotAdapter = require('./qq-official-adapter');
const FeishuWebhookAdapter = require('./feishu-webhook-adapter');

const app = express();
const PORT = process.env.IM_BRIDGE_PORT || 18080;

// 中间件
app.use(cors());
app.use(bodyParser.json());

// IM平台选择：feishu, qq, qq-official
const imPlatform = process.env.IM_PLATFORM || 'feishu';

// 根据平台选择适配器
let imAdapter;
let imConfig;

if (imPlatform === 'feishu') {
  // 使用飞书webhook
  imConfig = {
    enable: process.env.FEISHU_ENABLE === 'true',
    webhookUrl: process.env.FEISHU_WEBHOOK_URL || ''
  };
  imAdapter = new FeishuWebhookAdapter(imConfig);
  console.log('📱 使用飞书机器人 (Webhook)');
} else if (imPlatform === 'qq-official') {
  // 使用QQ官方机器人
  imConfig = {
    enable: process.env.QQ_ENABLE === 'true',
    appId: process.env.QQ_APP_ID || '',
    token: process.env.QQ_TOKEN || '',
    sandbox: process.env.QQ_SANDBOX === 'true'
  };
  imAdapter = new QQOfficialBotAdapter(imConfig);
  console.log('📱 使用QQ官方机器人API');
} else {
  // 使用go-cqhttp
  imConfig = {
    enable: process.env.QQ_ENABLE === 'true',
    apiUrl: process.env.QQ_API_URL || 'http://localhost:3000',
    accessToken: process.env.QQ_ACCESS_TOKEN || '',
    platform: process.env.QQ_PLATFORM || 'go-cqhttp'
  };
  imAdapter = new QQAdapter(imConfig);
  console.log('📱 使用go-cqhttp框架');
}

// 统计信息
const stats = {
  eventsReceived: 0,
  eventsByType: {},
  lastEventTime: null,
  messagesSent: 0,
  messagesFailed: 0
};

/**
 * 主端点：接收EventBroadcaster事件
 */
app.post('/opencode/events', async (req, res) => {
  try {
    const { event_id, event_type, session_id, timestamp, data } = req.body;

    // 更新统计
    stats.eventsReceived++;
    stats.eventsByType[event_type] = (stats.eventsByType[event_type] || 0) + 1;
    stats.lastEventTime = new Date().toISOString();

    // 格式化IM消息
    const message = formatEventToIMMessage(event_type, data);

    // 打印到控制台（模拟发送到IM）
    console.log('\n' + '='.repeat(60));
    console.log(`📥 收到事件: ${event_type}`);
    console.log('='.repeat(60));
    console.log(`事件ID: ${event_id}`);
    console.log(`会话ID: ${session_id}`);
    console.log(`时间戳: ${timestamp}`);
    console.log(`数据: ${JSON.stringify(data, null, 2)}`);
    console.log('\n📤 推送到IM的消息:');
    console.log('-'.repeat(60));
    console.log(message);
    console.log('='.repeat(60));

    // 推送到IM平台（如果启用）
    let imSent = false;
    if (imConfig.enable) {
      try {
        // 格式化为平台消息
        const platformMessage = imAdapter.formatOpenCodeEvent(event_type, data);

        // 发送消息
        const result = await imAdapter.sendMessage(platformMessage);
        const success = typeof result === 'boolean' ? result : (result && result.success);

        if (success) {
          stats.messagesSent++;
          imSent = true;
          console.log(`✅ 消息已发送到${imPlatform}`);
        } else {
          stats.messagesFailed++;
          const errorMsg = typeof result === 'object' ? result.error : 'Unknown error';
          console.error(`❌ 消息发送失败: ${errorMsg}`);
        }

      } catch (error) {
        console.error(`[IM Adapter] Error:`, error.message);
        stats.messagesFailed++;
      }
    }

    // 返回成功响应
    res.json({
      success: true,
      event_id: event_id,
      message: 'Event received',
      im_sent: imSent,
      platform: imPlatform
    });

  } catch (error) {
    console.error('❌ 处理事件时出错:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * 健康检查端点
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    uptime: process.uptime(),
    stats: stats
  });
});

/**
 * 统计信息端点
 */
app.get('/stats', (req, res) => {
  res.json(stats);
});

/**
 * 重置统计
 */
app.post('/stats/reset', (req, res) => {
  stats.eventsReceived = 0;
  stats.eventsByType = {};
  stats.lastEventTime = null;
  res.json({ success: true, message: 'Stats reset' });
});

/**
 * 手动测试端点
 */
app.post('/test/event', async (req, res) => {
  const testEvent = {
    event_id: 'test-' + Date.now(),
    event_type: req.body.event_type || 'complete',
    session_id: req.body.session_id || 'test-session',
    timestamp: new Date().toISOString(),
    data: req.body.data || { result: 'success', message: 'This is a test event from EventBroadcaster' }
  };

  console.log('\n🧪 发送测试事件到 /opencode/events');

  try {
    // 内部转发到实际端点
    const response = await fetch(`http://localhost:${PORT}/opencode/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(testEvent)
    });

    const result = await response.json();

    res.json({
      test: true,
      event: testEvent,
      result: result
    });

  } catch (error) {
    res.status(500).json({
      test: true,
      error: error.message
    });
  }
});

/**
 * 格式化事件为IM消息
 */
function formatEventToIMMessage(eventType, data) {
  switch (eventType) {
    case 'complete':
      const result = data.result || 'success';
      const files = data.files ? `\n📁 文件: ${data.files.join(', ')}` : '';
      return `✅ 任务完成\n\n结果: ${result}${files}`;

    case 'error':
      const error = data.error || '未知错误';
      return `❌ 任务失败\n\n错误: ${error}`;

    case 'phase':
      const phase = data.phase || 'unknown';
      const description = data.description ? `\n描述: ${data.description}` : '';
      return `🔄 任务阶段\n\n阶段: ${phase}${description}`;

    case 'action':
      const action = data.action || 'unknown';
      const file = data.file ? ` → ${data.file}` : '';
      return `⚙️ 执行操作\n\n${action}${file}`;

    case 'progress':
      const progress = data.progress || 0;
      const message = data.message ? `\n${data.message}` : '';
      return `📊 任务进度\n\n${progress}%${message}`;

    default:
      return `📡 事件: ${eventType}\n\n${JSON.stringify(data, null, 2)}`;
  }
}

/**
 * 启动服务器
 */
app.listen(PORT, async () => {
  console.log('\n' + '='.repeat(60));
  console.log('🚀 OpenCode IM Bridge Server Started');
  console.log('='.repeat(60));
  console.log(`📡 监听端口: ${PORT}`);
  console.log(`🔗 事件端点: http://localhost:${PORT}/opencode/events`);
  console.log(`💚 健康检查: http://localhost:${PORT}/health`);
  console.log(`📊 统计信息: http://localhost:${PORT}/stats`);
  console.log(`🧪 测试端点: http://localhost:${PORT}/test/event`);
  console.log('='.repeat(60));

  // 显示IM配置状态
  if (imConfig.enable) {
    console.log(`\n📱 IM Bot配置:`);
    console.log(`   状态: ✅ 已启用`);
    console.log(`   平台: ${imPlatform}`);

    if (imPlatform === 'feishu') {
      console.log(`   Webhook: ${imConfig.webhookUrl ? '✅ 已配置' : '❌ 未配置'}`);

      // 飞书健康检查
      const health = await imAdapter.healthCheck();
      if (health.healthy) {
        console.log(`   ✅ 适配器已就绪`);
      } else {
        console.log(`   ⚠️ 适配器检查失败: ${health.error || 'Unknown'}`);
      }
    } else if (imPlatform === 'qq-official') {
      console.log(`   AppID: ${imConfig.appId ? '✅ 已配置' : '❌ 未配置'}`);
      console.log(`   Token: ${imConfig.token ? '✅ 已配置' : '❌ 未配置'}`);
      console.log(`   环境: ${imConfig.sandbox ? '沙箱' : '生产'}`);

      // QQ官方机器人健康检查
      const health = await imAdapter.healthCheck();
      if (health.healthy) {
        console.log(`   ✅ 适配器已就绪`);
      } else {
        console.log(`   ⚠️ 适配器检查失败: ${health.error || 'Unknown'}`);
      }
    } else {
      console.log(`   API: ${imConfig.apiUrl}`);

      // 检查QQ连接
      const connected = await imAdapter.checkConnection();

      if (connected) {
        const loginInfo = await imAdapter.getLoginInfo();
        if (loginInfo) {
          console.log(`   账号: ${loginInfo.nickname} (${loginInfo.userId})`);
        }
      } else {
        console.log(`   ⚠️ 无法连接到go-cqhttp`);
        console.log(`   请确保go-cqhttp正在运行`);
      }

      const targets = process.env.QQ_TARGETS ? process.env.QQ_TARGETS.split(',') : [];
      if (targets.length > 0) {
        console.log(`   推送目标: ${targets.join(', ')}`);
      } else {
        console.log(`   ⚠️ 未配置推送目标`);
        console.log(`   请设置环境变量: QQ_TARGETS=user:123456,group:789`);
      }
    }
  } else {
    console.log(`\n📱 IM Bot配置:`);
    console.log(`   状态: ❌ 未启用`);
    console.log(`   启用方法: IM_PLATFORM=feishu FEISHU_ENABLE=true`);
  }

  console.log('\n✅ 服务器已就绪，等待EventBroadcaster推送事件...\n');

  // 显示配置示例
  console.log('📝 配置EventBroadcaster:');
  console.log(`   export OPENCODE_IM_WEBHOOK_URL="http://localhost:${PORT}/opencode/events"\n`);
});

// 优雅关闭
process.on('SIGINT', () => {
  console.log('\n\n👋 正在关闭服务器...');
  console.log(`📊 最终统计: ${stats.eventsReceived} 个事件已处理`);
  process.exit(0);
});

module.exports = app;
