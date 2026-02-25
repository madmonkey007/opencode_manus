/**
 * OpenCode Event Adapter
 *
 * 将新架构的 SSE 事件适配为前端现有代码期望的格式
 * 实现向后兼容，最小化前端重构工作量
 */

class EventAdapter {
    /**
     * 将新 API 事件转换为前端格式
     * @param {Object} newEvent - 新 API 事件
     * @param {Object} session - 当前会话对象
     * @returns {Object|null} 转换后的事件，或 null（如果事件应被忽略）
     */
    static adaptEvent(newEvent, session) {
        const eventType = newEvent.type;

        // 跳过心跳事件
        if (eventType === 'ping') {
            return null;
        }

        // 连接建立事件
        if (eventType === 'connection.established') {
            return {
                type: 'system',
                content: 'Connected to session',
                timestamp: newEvent.timestamp
            };
        }

        // 会话状态事件
        if (eventType === 'session.state') {
            return {
                type: 'session_state',
                message_count: newEvent.message_count
            };
        }

        // 消息更新事件
        if (eventType === 'message.updated') {
            const messageInfo = newEvent.properties?.info;
            if (!messageInfo) return null;

            return {
                type: 'message_updated',
                message_id: messageInfo.id,
                role: messageInfo.role,
                time: messageInfo.time
            };
        }

        // 消息部分更新事件（核心事件）
        if (eventType === 'message.part.updated') {
            const part = newEvent.properties?.part;
            if (!part) return null;

            return this.adaptPartEvent(part, session);
        }

        // 文件预览事件
        if (eventType === 'preview_start') {
            return {
                type: 'file_preview_start',
                step_id: newEvent.step_id,
                file_path: newEvent.file_path,
                action: newEvent.action
            };
        }

        if (eventType === 'preview_delta') {
            return {
                type: 'file_preview_delta',
                step_id: newEvent.step_id,
                delta: newEvent.delta
            };
        }

        if (eventType === 'preview_end') {
            return {
                type: 'file_preview_end',
                step_id: newEvent.step_id,
                file_path: newEvent.file_path
            };
        }

        // 时间轴更新事件
        if (eventType === 'timeline_update') {
            const step = newEvent.step;
            return {
                type: 'timeline_event',
                step_id: step.step_id,
                action: step.action,
                path: step.path,
                timestamp: step.timestamp,
                status: step.status
            };
        }

        // 错误事件
        if (eventType === 'error') {
            return {
                type: 'error',
                message: newEvent.properties?.message || newEvent.message || 'Unknown error'
            };
        }

        // 未知事件类型
        console.warn('[EventAdapter] Unknown event type:', eventType, newEvent);
        return null;
    }

    /**
     * 适配 Part 事件
     * @param {Object} part - Part 对象
     * @param {Object} session - 当前会话
     * @returns {Object} 适配后的事件
     */
    static adaptPartEvent(part, session) {
        const partType = part.type;

        const isThought = partType === 'thought';

        // TEXT 类型
        if (partType === 'text') {
            return {
                type: 'answer_chunk',
                text: part.content?.text || '',
                message_id: part.message_id
            };
        }

        // THOUGHT 类型
        if (partType === 'thought') {
            return {
                type: 'thought',
                content: part.content?.text || '',
                message_id: part.message_id
            };
        }

        // TOOL 类型
        if (partType === 'tool') {
            const content = part.content || {};
            const toolName = content.tool || 'unknown';
            const state = content.state || {};
            const status = state.status || 'running';

            // 跳过 todowrite 工具（前端已处理）
            if (toolName === 'todowrite') {
                return null;
            }

            // 映射工具类型
            const toolType = this.mapToolType(toolName);

            // 提取元数据中的标题
            const metadata = part.metadata || {};
            const title = metadata.title || (isThought ? 'Thinking' : `Using ${toolName}`);

            return {
                type: 'action',
                data: {
                    tool: toolType,
                    tool_name: toolName,
                    title: title,
                    status: status,
                    input: metadata.input || content.input || {},
                    output: state.output || '',
                    timestamp: part.time?.start || Date.now()
                },
                message_id: part.message_id
            };
        }

        // STEP-START 类型
        if (partType === 'step-start') {
            const metadata = part.metadata || {};
            return {
                type: 'phase_start',
                phase_id: part.id,
                title: metadata.title || part.content?.text || 'Executing',
                description: metadata.description || '',
                message_id: part.message_id
            };
        }

        // STEP-FINISH 类型
        if (partType === 'step-finish') {
            return {
                type: 'phase_finish',
                phase_id: part.id,
                message_id: part.message_id
            };
        }

        // FILE 类型
        if (partType === 'file') {
            const content = part.content || {};
            return {
                type: 'file_operation',
                file_path: content.file_path || '',
                operation: content.operation || 'unknown',
                content: content.content || '',
                message_id: part.message_id
            };
        }

        // 未知 Part 类型
        console.warn('[EventAdapter] Unknown part type:', partType, part);
        return null;
    }

    /**
     * 映射工具名称到前端工具类型
     * @param {string} toolName - 工具名称
     * @returns {string} 工具类型
     */
    static mapToolType(toolName) {
        const tool = toolName.toLowerCase();

        if (tool.includes('read')) return 'read';
        if (tool.includes('write') || tool.includes('save') || tool.includes('create')) return 'write';
        if (tool.includes('bash') || tool === 'sh' || tool.includes('shell')) return 'bash';
        if (tool.includes('terminal') || tool.includes('command') || tool.includes('cmd') || tool.includes('run')) return 'terminal';
        if (tool.includes('grep') || tool.includes('search')) return 'grep';
        if (tool.includes('browser') || tool.includes('click') || tool.includes('visit') || tool.includes('scroll')) return 'browser';
        if (tool.includes('web') || tool.includes('google')) return 'web_search';
        if (tool.includes('edit') || tool.includes('replace')) return 'file_editor';

        return 'file_editor'; // Default fallback
    }

    /**
     * 批量适配事件
     * @param {Array<Object>} newEvents - 新 API 事件数组
     * @param {Object} session - 当前会话
     * @returns {Array<Object>} 适配后的事件数组
     */
    static adaptEvents(newEvents, session) {
        return newEvents
            .map(event => this.adaptEvent(event, session))
            .filter(event => event !== null);
    }

    /**
     * 将前端会话转换为创建会话请求
     * @param {Object} frontendSession - 前端会话对象
     * @returns {Object} 创建会话请求
     */
    static sessionToCreateRequest(frontendSession) {
        return {
            title: frontendSession.prompt?.substring(0, 100) || 'New Session',
            version: '1.0.0'
        };
    }

    /**
     * 将前端消息转换为发送消息请求
     * @param {string} text - 消息文本
     * @param {Object} options - 可选参数
     * @returns {Object} 发送消息请求
     */
    static messageToSendRequest(text, options = {}) {
        return {
            message_id: options.messageId || apiClient.generateMessageId(),
            provider_id: options.providerId || 'anthropic',
            model_id: options.modelId || 'claude-3-5-sonnet-20241022',
            mode: options.mode || 'auto',
            parts: [{
                type: 'text',
                text: text
            }]
        };
    }

    /**
     * 从新 API 响应构建前端会话对象
     * @param {Object} apiSession - API 返回的 Session 对象
     * @param {Object} apiMessages - API 返回的消息列表
     * @returns {Object} 前端会话对象
     */
    static apiSessionToFrontend(apiSession, apiMessages = null) {
        const session = {
            id: apiSession.id,
            title: apiSession.title,
            prompt: '', // 将从第一条 user message 提取
            response: '',
            phases: [],
            actions: [],
            orphanEvents: [],
            uploadedFiles: [],
            currentPhase: null,
            // 新增字段
            apiSession: apiSession,
            version: apiSession.version,
            status: apiSession.status,
            time: apiSession.time
        };

        // 如果有消息数据，提取内容
        if (apiMessages && apiMessages.messages) {
            const userMessages = apiMessages.messages.filter(m => m.info.role === 'user');
            const assistantMessages = apiMessages.messages.filter(m => m.info.role === 'assistant');

            // 提取第一条 user message 作为 prompt
            if (userMessages.length > 0) {
                const firstUser = userMessages[0];
                const textParts = (firstUser.parts || []).filter(p => p.type === 'text');
                session.prompt = textParts.map(p => p.content?.text || '').join('\n');
            }

            // 提取最后一条 assistant message 的内容作为 response
            if (assistantMessages.length > 0) {
                const lastAssistant = assistantMessages[assistantMessages.length - 1];
                const textParts = (lastAssistant.parts || []).filter(p => p.type === 'text');
                session.response = textParts.map(p => p.content?.text || '').join('');
            }

            // 处理所有 parts，转换为 events
            for (const message of apiMessages.messages) {
                for (const part of message.parts || []) {
                    const adaptedEvent = this.adaptPartEvent(part, session);
                    if (adaptedEvent) {
                        session.orphanEvents.push(adaptedEvent);
                    }
                }
            }
        }

        return session;
    }

    /**
     * 判断事件是否为文件预览事件
     * @param {Object} event - 事件对象
     * @returns {boolean}
     */
    static isFilePreviewEvent(event) {
        return event &&
            (event.type === 'preview_start' ||
                event.type === 'preview_delta' ||
                event.type === 'preview_end');
    }

    /**
     * 判断事件是否为时间轴事件
     * @param {Object} event - 事件对象
     * @returns {boolean}
     */
    static isTimelineEvent(event) {
        return event && event.type === 'timeline_update';
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EventAdapter };
}

// 全局访问
window.EventAdapter = EventAdapter;
