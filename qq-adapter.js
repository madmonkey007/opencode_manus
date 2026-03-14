/**
 * QQ Bot适配器
 *
 * 支持多种QQ Bot框架:
 * - go-cqhttp (推荐)
 * - Shamrock
 * - NapCat
 */

class QQAdapter {
    constructor(config = {}) {
        this.apiUrl = config.apiUrl || 'http://localhost:3000'; // go-cqhttp默认地址
        this.accessToken = config.accessToken || '';
        this.enable = config.enable !== false;
        this.platform = config.platform || 'go-cqhttp'; // go-cqhttp, shamrock, napcat

        console.log(`[QQ Adapter] Initialized (${this.platform})`);
        console.log(`  API URL: ${this.apiUrl}`);
        console.log(`  Status: ${this.enable ? 'Enabled' : 'Disabled'}`);
    }

    /**
     * 发送私聊消息
     * @param {number|string} userId - QQ号
     * @param {string} message - 消息内容
     */
    async sendPrivateMessage(userId, message) {
        if (!this.enable) {
            console.log('[QQ Adapter] Disabled, skipping message');
            return false;
        }

        try {
            const url = `${this.apiUrl}/send_private_msg`;
            const payload = {
                user_id: Number(userId),
                message: message
            };

            if (this.accessToken) {
                payload.access_token = this.accessToken;
            }

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.retcode === 0) {
                console.log(`[QQ Adapter] ✓ Private message sent to ${userId}`);
                return true;
            } else {
                console.error(`[QQ Adapter] ✗ Failed: ${data.msg}`);
                return false;
            }

        } catch (error) {
            console.error(`[QQ Adapter] Error sending private message:`, error.message);
            return false;
        }
    }

    /**
     * 发送群消息
     * @param {number|string} groupId - 群号
     * @param {string} message - 消息内容
     */
    async sendGroupMessage(groupId, message) {
        if (!this.enable) {
            console.log('[QQ Adapter] Disabled, skipping message');
            return false;
        }

        try {
            const url = `${this.apiUrl}/send_group_msg`;
            const payload = {
                group_id: Number(groupId),
                message: message
            };

            if (this.accessToken) {
                payload.access_token = this.accessToken;
            }

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.retcode === 0) {
                console.log(`[QQ Adapter] ✓ Group message sent to ${groupId}`);
                return true;
            } else {
                console.error(`[QQ Adapter] ✗ Failed: ${data.msg}`);
                return false;
            }

        } catch (error) {
            console.error(`[QQ Adapter] Error sending group message:`, error.message);
            return false;
        }
    }

    /**
     * 构建消息格式
     * @param {string} type - 消息类型: text, image, at, card
     * @param {object} data - 消息数据
     */
    buildMessage(type, data) {
        switch (type) {
            case 'text':
                return data.text;

            case 'image':
                return `[CQ:image,file=${data.file},url=${data.url}]`;

            case 'at':
                return `[CQ:at,qq=${data.qq}]`;

            case 'card':
                // QQ的卡片消息（需要机器人框架支持）
                return this.buildJsonMessage(data);

            default:
                return data.text || '';
        }
    }

    /**
     * 构建JSON消息（卡片等富文本）
     */
    buildJsonMessage(data) {
        const jsonMsg = {
            app: "com.tencent.structmsg",
            config: {
                round: 1,
                forward: 1
            },
            meta: {
                detail_1: {
                    desc: data.desc || "",
                    meta: data.meta || "",
                    preview: data.preview || "",
                    title: data.title || "",
                    qrcode_url: data.url || ""
                }
            }
        };

        return `[CQ:json,data=${JSON.stringify(jsonMsg)}]`;
    }

    /**
     * 格式化OpenCode事件为QQ消息
     * @param {string} eventType - 事件类型
     * @param {object} eventData - 事件数据
     */
    formatOpenCodeEvent(eventType, eventData) {
        switch (eventType) {
            case 'complete':
                const result = eventData.result || 'success';
                const files = eventData.files ? `\n📁 文件: ${eventData.files.join(', ')}` : '';
                return `✅ OpenCode任务完成\n\n结果: ${result}${files}`;

            case 'error':
                const error = eventData.error || '未知错误';
                return `❌ OpenCode任务失败\n\n错误: ${error}`;

            case 'phase':
                const phase = eventData.phase || 'unknown';
                const description = eventData.description ? `\n描述: ${eventData.description}` : '';
                return `🔄 OpenCode任务阶段\n\n阶段: ${phase}${description}`;

            case 'action':
                const action = eventData.action || 'unknown';
                const file = eventData.file ? ` → ${eventData.file}` : '';
                return `⚙️ OpenCode执行操作\n\n${action}${file}`;

            case 'progress':
                const progress = eventData.progress || 0;
                const message = eventData.message ? `\n${eventData.message}` : '';
                return `📊 OpenCode任务进度\n\n${progress}%${message}`;

            default:
                return `📡 OpenCode事件: ${eventType}\n\n${JSON.stringify(eventData, null, 2)}`;
        }
    }

    /**
     * 检查连接状态
     */
    async checkConnection() {
        try {
            const url = `${this.apiUrl}/get_status`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.retcode === 0) {
                console.log(`[QQ Adapter] ✓ Connection OK`);
                console.log(`  Online: ${data.data.online}`);
                console.log(`  Nickname: ${data.data.nickname}`);
                return true;
            } else {
                console.error(`[QQ Adapter] ✗ Connection failed: ${data.msg}`);
                return false;
            }

        } catch (error) {
            console.error(`[QQ Adapter] ✗ Connection error:`, error.message);
            return false;
        }
    }

    /**
     * 获取登录账号信息
     */
    async getLoginInfo() {
        try {
            const url = `${this.apiUrl}/get_login_info`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.retcode === 0) {
                return {
                    userId: data.data.user_id,
                    nickname: data.data.nickname
                };
            } else {
                return null;
            }

        } catch (error) {
            console.error('[QQ Adapter] Error getting login info:', error.message);
            return null;
        }
    }

    /**
     * 获取好友列表
     */
    async getFriendList() {
        try {
            const url = `${this.apiUrl}/get_friend_list`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.retcode === 0) {
                return data.data;
            } else {
                return [];
            }

        } catch (error) {
            console.error('[QQ Adapter] Error getting friend list:', error.message);
            return [];
        }
    }

    /**
     * 获取群列表
     */
    async getGroupList() {
        try {
            const url = `${this.apiUrl}/get_group_list`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.retcode === 0) {
                return data.data;
            } else {
                return [];
            }

        } catch (error) {
            console.error('[QQ Adapter] Error getting group list:', error.message);
            return [];
        }
    }
}

module.exports = QQAdapter;
