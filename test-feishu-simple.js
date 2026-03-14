/**
 * Feishu Webhook Adapter - English Version
 * Using English text to avoid encoding issues
 */
class FeishuWebhookAdapterSimple {
    constructor(config = {}) {
        this.webhookUrl = config.webhookUrl || process.env.FEISHU_WEBHOOK_URL;
        this.enable = config.enable !== false;
    }

    async sendMessage(message) {
        if (!this.webhookUrl) {
            return {
                success: false,
                error: 'Webhook URL not configured'
            };
        }

        try {
            const response = await fetch(this.webhookUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json; charset=utf-8'
                },
                body: JSON.stringify({
                    msg_type: 'text',
                    content: {
                        text: message
                    }
                })
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
     * Format OpenCode event as Feishu message (English)
     */
    formatOpenCodeEvent(eventType, eventData) {
        const emoji = {
            'complete': '[OK]',
            'error': '[ERROR]',
            'phase': '[PHASE]',
            'action': '[ACTION]',
            'progress': '[PROGRESS]'
        };

        const icon = emoji[eventType] || '[INFO]';

        let message = `${icon} OpenCode Task Notification\n\n`;

        switch (eventType) {
            case 'complete':
                const result = eventData.result || 'unknown';
                const files = eventData.files ? eventData.files.join(', ') : 'none';
                message += `Status: Completed\n`;
                message += `Result: ${result}\n`;
                if (files !== 'none') {
                    message += `Files: ${files}\n`;
                }
                break;

            case 'error':
                const error = eventData.error || 'Unknown error';
                message += `Status: Failed\n`;
                message += `Error: ${error}\n`;
                if (eventData.session) {
                    message += `Session: ${eventData.session}\n`;
                }
                break;

            case 'phase':
                const phase = eventData.phase || 'unknown';
                const description = eventData.description || '';
                message += `Phase: ${phase}\n`;
                if (description) {
                    message += `Description: ${description}\n`;
                }
                break;

            case 'progress':
                const progress = eventData.progress || 0;
                message += `Progress: ${progress}%\n`;
                if (eventData.message) {
                    message += `Message: ${eventData.message}\n`;
                }
                break;

            default:
                message += `Type: ${eventType}\n`;
                message += `Data: ${JSON.stringify(eventData, null, 2)}\n`;
        }

        // Add timestamp
        message += `\nTime: ${new Date().toISOString()}`;

        // Add keyword
        const keyword = process.env.FEISHU_KEYWORD || '';
        if (keyword) {
            message = `${keyword} ${message}`;
        }

        return message;
    }

    async healthCheck() {
        return {
            healthy: true,
            message: 'Feishu webhook adapter initialized (Simple English version)',
            type: 'feishu-webhook-simple',
            webhookUrl: this.webhookUrl ? '***configured***' : '(not set)'
        };
    }
}

module.exports = FeishuWebhookAdapterSimple;
