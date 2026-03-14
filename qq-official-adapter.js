/**
 * QQ Official Bot Adapter
 *
 * 使用QQ官方机器人API发送消息
 * 文档：https://bot.q.qq.com/wiki/develop/api/
 */
class QQOfficialBotAdapter {
    constructor(config = {}) {
        this.appId = config.appId || process.env.QQ_APP_ID;
        this.token = config.token || process.env.QQ_TOKEN;
        this.enable = config.enable !== false;
        this.sandbox = config.sandbox === true; // 沙箱环境
    }

    /**
     * API基础URL
     */
    get baseUrl() {
        return this.sandbox
            ? 'https://sandbox.api.q.qq.com/sandbox'
            : 'https://api.q.qq.com';
    }

    /**
     * 发送私聊消息
     * @param {string} openId - 用户的OpenID
     * @param {string} message - 消息内容
     */
    async sendPrivateMessage(openId, message) {
        const url = `${this.baseUrl}/json/send_message`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({
                    openid: openId,
                    msg_type: 0, // 文本消息
                    content: message
                })
            });

            const data = await response.json();

            if (data.retcode === 0) {
                return {
                    success: true,
                    messageId: data.msg_id,
                    data: data
                };
            } else {
                return {
                    success: false,
                    error: data.msg || 'Unknown error',
                    errorCode: data.retcode,
                    data: data
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
     * 发送群消息（如果机器人支持）
     * @param {string} groupId - 群ID
     * @param {string} message - 消息内容
     */
    async sendGroupMessage(groupId, message) {
        // QQ官方机器人可能不支持群消息，或需要特殊权限
        const url = `${this.baseUrl}/json/send_group_message`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({
                    group_id: groupId,
                    msg_type: 0,
                    content: message
                })
            });

            const data = await response.json();

            if (data.retcode === 0) {
                return {
                    success: true,
                    messageId: data.msg_id,
                    data: data
                };
            } else {
                return {
                    success: false,
                    error: data.msg || 'Unknown error',
                    errorCode: data.retcode
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
     * 格式化OpenCode事件为QQ消息
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

        let message = `${icon} OpenCode任务通知\n\n`;

        switch (eventType) {
            case 'complete':
                const result = eventData.result || 'unknown';
                const files = eventData.files ? eventData.files.join(', ') : 'none';
                message += `状态: 任务完成\n`;
                message += `结果: ${result}\n`;
                if (files !== 'none') {
                    message += `文件: ${files}\n`;
                }
                break;

            case 'error':
                const error = eventData.error || 'Unknown error';
                message += `状态: 任务失败\n`;
                message += `错误: ${error}\n`;
                if (eventData.session) {
                    message += `会话: ${eventData.session}\n`;
                }
                break;

            case 'phase':
                const phase = eventData.phase || 'unknown';
                const description = eventData.description || '';
                message += `阶段: ${phase}\n`;
                if (description) {
                    message += `描述: ${description}\n`;
                }
                break;

            case 'progress':
                const progress = eventData.progress || 0;
                message += `进度: ${progress}%\n`;
                if (eventData.message) {
                    message += `消息: ${eventData.message}\n`;
                }
                break;

            default:
                message += `类型: ${eventType}\n`;
                message += `数据: ${JSON.stringify(eventData, null, 2)}\n`;
        }

        // 添加时间戳
        message += `\n时间: ${new Date().toLocaleString('zh-CN')}`;

        return message;
    }

    /**
     * 健康检查
     */
    async healthCheck() {
        try {
            // QQ官方机器人API可能没有专门的health check端点
            // 这里发送一个测试消息来验证连接
            // 实际使用时应该调用更轻量的接口
            return {
                healthy: true,
                message: 'QQ Official Bot adapter initialized',
                type: 'official',
                appId: this.appId
            };
        } catch (error) {
            return {
                healthy: false,
                error: error.message
            };
        }
    }
}

module.exports = QQOfficialBotAdapter;
