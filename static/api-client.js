/**
 * OpenCode API Client - 新架构 API 客户端
 *
 * 基于 Session + Message 架构的官方 Web API
 * 提供真正的多轮对话支持
 */

class OpenCodeAPIClient {
    constructor() {
        this.baseURL = '';
        this.eventSources = new Map(); // session_id -> EventSource
        this.eventHandlers = new Map(); // session_id -> Set<handler>
    }

    // ====================================================================
    // Session 管理
    // ====================================================================

    /**
     * 创建新会话
     * @param {string} title - 会话标题
     * @param {string} mode - 运行模式 (plan, build, auto)
     * @returns {Promise<Session>}
     */
    async createSession(title = 'New Session', mode = 'auto') {
        const url = `${this.baseURL}/opencode/session`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ title, mode })
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to create session: ${response.status} - ${errorText}`);
        }
        return await response.json();
    }


    /**
     * 获取会话信息
     * @param {string} sessionId - 会话ID
     * @returns {Promise<Session>}
     */
    async getSession(sessionId) {
        const url = `${this.baseURL}/opencode/session/${encodeURIComponent(sessionId)}`;
        const response = await fetch(url);
        if (!response.ok) {
            if (response.status === 404) {
                return null;
            }
            throw new Error(`Failed to get session: ${response.status}`);
        }
        return await response.json();
    }

    /**
     * 删除会话
     * @param {string} sessionId - 会话ID
     * @returns {Promise<boolean>}
     */
    async deleteSession(sessionId) {
        const url = `${this.baseURL}/opencode/session/${encodeURIComponent(sessionId)}`;
        const response = await fetch(url, { method: 'DELETE' });
        if (!response.ok) {
            if (response.status === 404) {
                return false;
            }
            throw new Error(`Failed to delete session: ${response.status}`);
        }
        return true;
    }

    /**
     * 列出所有会话
     * @param {string} status - 可选的状态过滤器 (active, idle, archived)
     * @returns {Promise<Session[]>}
     */
    async listSessions(status = null) {
        let url = `${this.baseURL}/opencode/sessions`;
        if (status) {
            url += `?status=${encodeURIComponent(status)}`;
        }
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to list sessions: ${response.status}`);
        }
        return await response.json();
    }

    // ====================================================================
    // Message 管理
    // ====================================================================

    /**
     * 获取会话的消息历史
     * @param {string} sessionId - 会话ID
     * @returns {Promise<Object>}
     */
    async getMessages(sessionId) {
        const url = `${this.baseURL}/opencode/session/${encodeURIComponent(sessionId)}/messages`;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to get messages: ${response.status}`);
        }
        return await response.json();
    }

    /**
     * ✅ v=38.1新增：获取会话的时间轴（工具调用历史）
     * @param {string} sessionId - 会话ID
     * @returns {Promise<Object>} 返回 {session_id, timeline, count}
     */
    async getTimeline(sessionId) {
        const url = `${this.baseURL}/opencode/session/${encodeURIComponent(sessionId)}/timeline`;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to get timeline: ${response.status}`);
        }
        return await response.json();
    }

    /**
     * 发送新消息到会话
     * @param {string} sessionId - 会话ID
     * @param {SendMessageRequest} request - 发送消息请求
     * @returns {Promise<SendMessageResponse>}
     */
    async sendMessage(sessionId, request) {
        const url = `${this.baseURL}/opencode/session/${encodeURIComponent(sessionId)}/message`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request)
        });
        if (!response.ok) {
            throw new Error(`Failed to send message: ${response.status}`);
        }
        return await response.json();
    }

    /**
     * 便捷方法：发送文本消息
     * @param {string} sessionId - 会话ID
     * @param {string} text - 消息文本
     * @param {Object} options - 可选参数
     * @returns {Promise<SendMessageResponse>}
     */
    async sendTextMessage(sessionId, text, options = {}) {
        const messageId = options.messageId || this.generateMessageId();
        const {
            providerId = 'anthropic',
            modelId = 'claude-3-5-sonnet-20241022',
            mode = 'auto'
        } = options;

        return await this.sendMessage(sessionId, {
            message_id: messageId,
            provider_id: providerId,
            model_id: modelId,
            mode: mode,
            parts: [{
                type: 'text',
                text: text
            }]
        });
    }

    // ====================================================================
    // SSE 事件流
    // ====================================================================

    /**
     * 订阅会话的 SSE 事件流
     * @param {string} sessionId - 会话ID
     * @param {Function} onEvent - 事件回调函数 (event) => void
     * @param {Function} onError - 错误回调函数 (error) => void
     * @returns {EventSource}
     */
    subscribeToEvents(sessionId, onEvent, onError = null) {
        // 如果已有该会话的 EventSource，先关闭
        this.unsubscribeFromEvents(sessionId);

        const url = `${this.baseURL}/opencode/events?session_id=${encodeURIComponent(sessionId)}`;
        const eventSource = new EventSource(url);

        // 连接建立
        eventSource.onopen = () => {
            console.log(`[SSE] Connected to session: ${sessionId}`);
        };

        // 接收消息
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onEvent(data);
            } catch (e) {
                console.error('[SSE] Failed to parse event:', event.data, e);
            }
        };

        // 错误处理
        eventSource.onerror = (error) => {
            console.error(`[SSE] Connection error for session ${sessionId}:`, error);
            if (onError) {
                onError(error);
            }
            // EventSource 会自动重连，但我们可以选择关闭它
            // eventSource.close();
        };

        // 保存 EventSource
        this.eventSources.set(sessionId, eventSource);

        // 保存事件处理器
        if (!this.eventHandlers.has(sessionId)) {
            this.eventHandlers.set(sessionId, new Set());
        }
        this.eventHandlers.get(sessionId).add(onEvent);

        return eventSource;
    }

    /**
     * 取消订阅会话的 SSE 事件流
     * @param {string} sessionId - 会话ID
     */
    unsubscribeFromEvents(sessionId) {
        const eventSource = this.eventSources.get(sessionId);
        if (eventSource) {
            eventSource.close();
            this.eventSources.delete(sessionId);
            this.eventHandlers.delete(sessionId);
            console.log(`[SSE] Unsubscribed from session: ${sessionId}`);
        }
    }

    /**
     * 取消所有订阅
     */
    unsubscribeAll() {
        for (const sessionId of this.eventSources.keys()) {
            this.unsubscribeFromEvents(sessionId);
        }
    }

    // ====================================================================
    // 工具端点
    // ====================================================================

    /**
     * 健康检查
     * @returns {Promise<Object>}
     */
    async healthCheck() {
        const url = `${this.baseURL}/opencode/health`;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Health check failed: ${response.status}`);
        }
        return await response.json();
    }

    /**
     * 获取 API 信息
     * @returns {Promise<Object>}
     */
    async getAPIInfo() {
        const url = `${this.baseURL}/opencode/info`;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to get API info: ${response.status}`);
        }
        return await response.json();
    }

    // ====================================================================
    // 辅助方法
    // ====================================================================

    /**
     * 生成消息 ID
     * @returns {string}
     */
    generateMessageId() {
        return 'msg_' + Math.random().toString(36).slice(2, 15);
    }

    /**
     * 生成会话 ID（用于前端临时会话）
     * @returns {string}
     */
    generateSessionId() {
        return 'ses_' + Math.random().toString(36).slice(2, 9);
    }

    /**
     * 检查会话是否存在
     * @param {string} sessionId - 会话ID
     * @returns {Promise<boolean>}
     */
    async sessionExists(sessionId) {
        const session = await this.getSession(sessionId);
        return session !== null;
    }

    // ====================================================================
    // 兼容旧 API（可选）
    // ====================================================================

    /**
     * 使用旧 API 运行任务（兼容模式）
     * @param {string} prompt - 提示词
     * @param {string} sessionId - 会话ID
     * @returns {EventSource}
     */
    runLegacyTask(prompt, sessionId) {
        const url = `${this.baseURL}/opencode/run_sse?prompt=${encodeURIComponent(prompt)}&sid=${encodeURIComponent(sessionId)}`;
        return new EventSource(url);
    }
}

// ====================================================================
// 单例模式
// ====================================================================

const apiClient = new OpenCodeAPIClient();

// 导出（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { OpenCodeAPIClient, apiClient };
}

// 全局访问（浏览器环境）
window.OpenCodeAPIClient = OpenCodeAPIClient;
window.apiClient = apiClient;
