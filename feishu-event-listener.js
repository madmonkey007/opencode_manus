/**
 * Feishu Event Listener for OpenCode
 *
 * 接收飞书群@机器人消息，提交OpenCode任务
 * 任务完成后通过IM Bridge发送结果到飞书群
 */

const express = require('express');
const bodyParser = require('body-parser');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;

// 中间件
app.use(bodyParser.json());

// 加载配置
function loadConfig() {
    const configPath = path.join(__dirname, 'configs', 'feishu-config.json');
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    return config;
}

// 验证飞书请求
function verifyFeishuRequest(req, config) {
    // 验证AppID
    if (req.body.app_id !== config.app_id) {
        console.error('[Auth] Invalid AppID:', req.body.app_id);
        return false;
    }

    // TODO: 添加加密验证（如启用）
    // const timestamp = req.headers['x-x-timestamp'];
    // const nonce = req.headers['x-x-nonce'];
    // const signature = req.headers['x-x-signature'];
    // const body = JSON.stringify(req.body);
    // const signStr = `${timestamp}\n${nonce}\n${body}`;
    // const expectedSignature = crypto
    //     .createHmac('sha256', config.encrypt_key)
    //     .update(signStr)
    //     .digest('base64');

    return true;
}

// 提取@消息内容
function extractAtMessage(message) {
    const botName = '@opencode';

    if (!message.includes(botName)) {
        return null;
    }

    // 提取@后面的内容
    const parts = message.split(botName);
    if (parts.length < 2) {
        return null;
    }

    const taskDescription = parts[1].trim();

    // 移除其他@提及
    const cleanMessage = taskDescription.replace(/@[\w]+/g, '').trim();

    return cleanMessage;
}

// 调用OpenCode API提交任务
async function submitOpenCodeTask(taskDescription, config) {
    try {
        const response = await fetch(`${config.opencode_api}/opencode/session`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: taskDescription,
                mode: 'auto'
            })
        });

        if (!response.ok) {
            throw new Error(`OpenCode API error: ${response.status}`);
        }

        const data = await response.json();

        console.log('[OpenCode] Task submitted:');
        console.log(`  Session ID: ${data.id}`);
        console.log(`  Prompt: ${taskDescription}`);

        return data;
    } catch (error) {
        console.error('[OpenCode] Failed to submit task:', error.message);
        throw error;
    }
}

// 主端点：接收飞书事件
app.post('/feishu/events', async (req, res) => {
    try {
        const config = loadConfig();

        // 打印请求信息（调试用）
        console.log('\n' + '='.repeat(60));
        console.log('[Feishu] Event received');
        console.log('='.repeat(60));
        console.log('Type:', req.body.type);
        console.log('App ID:', req.body.app_id);

        // 事件类型：im.message.receive_v1
        if (req.body.type === 'im.message.receive_v1') {
            const event = req.body.event;

            // 获取消息内容
            const message = event.message.content;

            console.log('Message:', message);

            // 提取@消息
            const taskDescription = extractAtMessage(message);

            if (taskDescription) {
                console.log('[Feishu] @opencode detected');
                console.log('[Feishu] Task description:', taskDescription);

                // 验证请求
                if (!verifyFeishuRequest(req, config)) {
                    return res.status(401).json({ code: 401, msg: 'Unauthorized' });
                }

                // 提交OpenCode任务
                const result = await submitOpenCodeTask(taskDescription, config);

                // 立即返回响应（飞书要求）
                res.json({
                    code: 0,
                    msg: 'Task submitted successfully'
                });

                console.log('[Feishu] Response sent');

            } else {
                // 非@消息，忽略
                console.log('[Feishu] Not an @mention, ignoring');
                res.json({ code: 0 });
            }

        } else {
            console.log('[Feishu] Other event type, ignoring');
            res.json({ code: 0 });
        }

    } catch (error) {
        console.error('[Feishu] Error:', error);
        res.status(500).json({
            code: 500,
            msg: error.message
        });
    }
});

// 健康检查
app.get('/health', (req, res) => {
    const config = loadConfig();
    res.json({
        status: 'ok',
        service: 'feishu-event-listener',
        port: PORT,
        app_id: config.app_id
    });
});

// 启动服务器
app.listen(PORT, () => {
    const config = loadConfig();
    console.log('\n' + '='.repeat(60));
    console.log('🚀 Feishu Event Listener for OpenCode');
    console.log('='.repeat(60));
    console.log(`📡 Listening on port: ${PORT}`);
    console.log(`🔗 Event endpoint: http://localhost:${PORT}/feishu/events`);
    console.log(`💚 Health check: http://localhost:${PORT}/health`);
    console.log('='.repeat(60));
    console.log('⚙️  Configuration:');
    console.log(`   App ID: ${config.app_id}`);
    console.log(`   Bot Name: ${config.bot_name}`);
    console.log(`   OpenCode API: ${config.opencode_api}`);
    console.log('='.repeat(60));
    console.log('✅ Server ready, waiting for Feishu events...');
    console.log();
    console.log('📝 Setup your Feishu app:');
    console.log('   1. Login to https://open.feishu.cn/');
    console.log('   2. Create enterprise app: "OpenCode Bot"');
    console.log('   3. Get AppID and AppSecret');
    console.log('   4. Update configs/feishu-config.json');
    console.log('   5. Subscribe to event: im.message.receive_v1');
    console.log('   6. Set callback URL to your public IP');
    console.log('   7. Add bot to your Feishu group');
    console.log();
    console.log('💡 Usage:');
    console.log('   In Feishu group: @opencode 创建一个Python脚本计算1+1');
    console.log('   Result will be sent back when task completes');
    console.log();
});

// 优雅关闭
process.on('SIGINT', () => {
    console.log('\n\n👋 Shutting down Feishu Event Listener...');
    process.exit(0);
});
