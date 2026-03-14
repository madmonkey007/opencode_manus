/**
 * Feishu Webhook Adapter
 *
 * 使用飞书自定义机器人webhook发送消息
 * 文档：https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNkE
 */
class FeishuWebhookAdapter {
    constructor(config = {}) {
        this.webhookUrl = config.webhookUrl || process.env.FEISHU_WEBHOOK_URL;
        this.enable = config.enable !== false;
    }

    /**
     * 发送消息到飞书
     * @param {string} message - 消息内容
     */
    async sendMessage(message) {
        if (!this.webhookUrl) {
            return {
                success: false,
                error: 'Webhook URL not configured'
            };
        }

        try {
            // Ensure UTF-8 encoding
            const payload = JSON.stringify({
                msg_type: 'text',
                content: {
                    text: message
                }
            });

            const response = await fetch(this.webhookUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json; charset=utf-8'
                },
                body: payload
            });

            const data = await response.json();

            if (data.code === 0) {
                return {
                    success: true,
                    messageId: data.data ? data.data.message_id : null,
                    data: data
                };
            } else {
                return {
                    success: false,
                    error: data.msg || 'Unknown error',
                    errorCode: data.code
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * 格式化OpenCode事件为飞书消息
     * @param {string} eventType - 事件类型
     * @param {object} eventData - 事件数据
     */
    formatOpenCodeEvent(eventType, eventData) {
        const emoji = {
            'complete': '✅',
            'error': '❌',
            'phase': '🔄',
            'action': '⚡',
            'progress': '📊'
        };

        const icon = emoji[eventType] || '📌';

        let message = `${icon} **OpenCode任务通知**\n\n`;

        // 添加关键词（如果启用了关键词验证）
        const keyword = process.env.FEISHU_KEYWORD || '';
        if (keyword) {
            message = `${keyword} ${message}`;
        }

        switch (eventType) {
            case 'complete':
                const result = eventData.result || 'unknown';
                const files = eventData.files ? eventData.files.join(', ') : 'none';
                message += `**状态**: 任务完成\n`;
                message += `**结果**: ${result}\n`;
                if (files !== 'none') {
                    message += `**文件**: ${files}\n`;
                }
                break;

            case 'error':
                const error = eventData.error || 'Unknown error';
                message += `**状态**: 任务失败\n`;
                message += `**错误**: ${error}\n`;
                if (eventData.session) {
                    message += `**会话**: ${eventData.session}\n`;
                }
                break;

            case 'phase':
                const phase = eventData.phase || 'unknown';
                const description = eventData.description || '';
                message += `**阶段**: ${phase}\n`;
                if (description) {
                    message += `**描述**: ${description}\n`;
                }
                break;

            case 'progress':
                const progress = eventData.progress || 0;
                message += `**进度**: ${progress}%\n`;
                if (eventData.message) {
                    message += `**消息**: ${eventData.message}\n`;
                }
                break;

            default:
                message += `**类型**: ${eventType}\n`;
                message += `**数据**: ${JSON.stringify(eventData, null, 2)}\n`;
        }

        // 添加时间戳
        message += `\n⏰ ${new Date().toLocaleString('zh-CN')}`;

        return message;
    }

    /**
     * 健康检查
     */
    async healthCheck() {
        return {
            healthy: true,
            message: 'Feishu webhook adapter initialized',
            type: 'feishu-webhook',
            webhookUrl: this.webhookUrl ? '***configured***' : '(not set)'
        };
    }
}

module.exports = FeishuWebhookAdapter;
