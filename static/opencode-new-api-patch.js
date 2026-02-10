/**
 * OpenCode.js 新 API 扩展
 *
 * 通过 Monkey Patching 的方式修改 submitTask 函数
 * 支持新的 Session + Message API，同时保持向后兼容
 */

(function() {
    'use strict';

    // 配置：是否启用新 API
    const ENABLE_NEW_API = true;
    const USE_NEW_API_FOR_NEW_SESSIONS = true;

    // 保存原始函数
    let originalSubmitTask = null;
    let newAPISessions = new Set(); // 使用新 API 的 session IDs

    /**
     * 检查新 API 是否可用
     */
    function isNewAPIAvailable() {
        return typeof window.apiClient !== 'undefined' &&
               typeof window.EventAdapter !== 'undefined';
    }

    /**
     * 检查 session 是否在后端存在
     */
    async function sessionExistsOnBackend(sessionId) {
        if (!isNewAPIAvailable()) return false;

        try {
            return await window.apiClient.sessionExists(sessionId);
        } catch (e) {
            console.warn('[NewAPI] Failed to check session existence:', e);
            return false;
        }
    }

    /**
     * 新 API: 创建会话并发送第一条消息
     */
    async function submitWithNewAPI(prompt, sessionId) {
        console.log('[NewAPI] Creating session and sending message...');

        try {
            // 1. 创建会话
            const apiSession = await window.apiClient.createSession(
                prompt.substring(0, 100) || 'New Session'
            );
            console.log('[NewAPI] Session created:', apiSession);

            // 2. 更新前端 session 对象
            const s = window.state.sessions.find(x => x.id === sessionId);
            if (s) {
                s.id = apiSession.id; // 更新为后端返回的 ID
                s.apiSession = apiSession;
                s.version = apiSession.version;
                s.status = apiSession.status;
                window.state.activeId = apiSession.id;
            }

            // 3. 订阅 SSE 事件流
            subscribeToNewAPIEvents(apiSession.id, sessionId);

            // 4. 发送消息
            const response = await window.apiClient.sendTextMessage(
                apiSession.id,
                prompt
            );
            console.log('[NewAPI] Message sent:', response);

            // 标记此 session 使用新 API
            newAPISessions.add(apiSession.id);

            return response;
        } catch (e) {
            console.error('[NewAPI] Failed to submit task:', e);
            throw e;
        }
    }

    /**
     * 新 API: 向现有会话发送消息
     */
    async function continueWithNewAPI(prompt, sessionId) {
        console.log('[NewAPI] Sending message to existing session...');

        try {
            // 1. 订阅 SSE 事件流（如果未订阅）
            if (!window.state.activeSSE) {
                subscribeToNewAPIEvents(sessionId, sessionId);
            }

            // 2. 发送消息
            const response = await window.apiClient.sendTextMessage(
                sessionId,
                prompt
            );
            console.log('[NewAPI] Message sent:', response);

            return response;
        } catch (e) {
            console.error('[NewAPI] Failed to continue task:', e);
            throw e;
        }
    }

    /**
     * 订阅新 API 的 SSE 事件流
     */
    function subscribeToNewAPIEvents(apiSessionId, frontendSessionId) {
        console.log('[NewAPI] Subscribing to events for session:', apiSessionId);

        const eventSource = window.apiClient.subscribeToEvents(
            apiSessionId,
            (newEvent) => {
                handleNewAPIEvent(newEvent, frontendSessionId);
            },
            (error) => {
                console.warn('[NewAPI] SSE error:', error);
                // SSE 错误处理由 EventSource 自动重连
            }
        );

        // 保存到 state
        window.state.activeSSE = eventSource;
    }

    /**
     * 处理新 API 的事件
     */
    function handleNewAPIEvent(newEvent, frontendSessionId) {
        console.log('[NewAPI] Event received:', newEvent.type);

        const s = window.state.sessions.find(x => x.id === frontendSessionId);
        if (!s) {
            console.warn('[NewAPI] Session not found:', frontendSessionId);
            return;
        }

        // 使用 EventAdapter 转换事件
        const adaptedEvent = window.EventAdapter.adaptEvent(newEvent, s);

        if (!adaptedEvent) {
            // 事件被过滤（如 ping）
            return;
        }

        // 处理特殊事件类型
        if (adaptedEvent.type === 'preview_start') {
            // 文件预览开始
            if (window.codePreviewOverlay && window.previewConfig?.isEventEnabled(adaptedEvent.action)) {
                window.codePreviewOverlay.setStepId(adaptedEvent.step_id);
                window.codePreviewOverlay.show(
                    adaptedEvent.file_path.split('/').pop(),
                    adaptedEvent.action
                );
            }
        } else if (adaptedEvent.type === 'preview_delta') {
            // 文件预览增量（打字机效果）
            if (window.codePreviewOverlay && window.previewConfig?.enableTypewriter) {
                window.codePreviewOverlay.appendDelta(adaptedEvent.delta);
            }
        } else if (adaptedEvent.type === 'preview_end') {
            // 文件预览结束
            if (window.codePreviewOverlay) {
                window.codePreviewOverlay.setStatus('完成');
            }
        } else if (adaptedEvent.type === 'timeline_update') {
            // 时间轴更新
            if (window.timelineProgress && adaptedEvent.step) {
                window.timelineProgress.addStep(adaptedEvent.step);
                window.timelineProgress.setActiveStep(adaptedEvent.step.step_id);

                const timelineContainer = document.getElementById('timeline-progress-container');
                if (timelineContainer) {
                    timelineContainer.classList.remove('hidden');
                }
            }
        } else if (adaptedEvent.type === 'message_updated') {
            // 消息更新（可忽略，主要用于状态跟踪）
            console.log('[NewAPI] Message updated:', adaptedEvent.message_id);
        } else if (adaptedEvent.type === 'action') {
            // 工具事件
            if (!s.actions) s.actions = [];
            s.actions.push(adaptedEvent.data);

            // 添加到 orphanEvents
            if (!s.orphanEvents) s.orphanEvents = [];
            s.orphanEvents.push(adaptedEvent);
        } else if (adaptedEvent.type === 'answer_chunk') {
            // 文本内容
            s.response += adaptedEvent.text;
        } else if (adaptedEvent.type === 'thought') {
            // 思考内容
            if (!s.orphanEvents) s.orphanEvents = [];
            s.orphanEvents.push(adaptedEvent);
        } else if (adaptedEvent.type === 'error') {
            // 错误
            console.error('[NewAPI] Error event:', adaptedEvent.message);
            if (!s.orphanEvents) s.orphanEvents = [];
            s.orphanEvents.push({
                type: 'error',
                content: adaptedEvent.message
            });
        }

        // 重新渲染
        if (typeof window.renderResults === 'function') {
            window.renderResults();
        }
        if (typeof window.renderAll === 'function') {
            window.renderAll();
        }
    }

    /**
     * 修改后的 submitTask 函数
     */
    async function newSubmitTask() {
        // UI 元素
        const stopBtn = el('#stop-btn');
        const rs = el('#right-send-btn');
        const input = el('#prompt');
        if (!input.value.trim()) return;

        const p = input.value.trim();
        let s = window.state.sessions.find(x => x.id === window.state.activeId);

        // 清空输入框
        input.value = '';

        // 决定使用哪个 API
        let useNewAPI = false;

        if (ENABLE_NEW_API && isNewAPIAvailable()) {
            if (!s) {
                // 新会话：检查配置
                useNewAPI = USE_NEW_API_FOR_NEW_SESSIONS;
            } else if (newAPISessions.has(s.id)) {
                // 已知使用新 API 的会话
                useNewAPI = true;
            } else if (s.id.startsWith('ses_')) {
                // ses_ 开头的 ID：检查后端是否存在
                const exists = await sessionExistsOnBackend(s.id);
                useNewAPI = exists;
            }
        }

        if (useNewAPI) {
            console.log('[NewAPI] Using new Session + Message API');

            // UI 更新
            if (stopBtn) stopBtn.classList.remove('hidden');
            if (rs) rs.classList.add('hidden');

            // 创建或获取 session
            const emptyPhases = [];
            let sessionId = window.state.activeId;

            if (!s) {
                sessionId = window.apiClient.generateSessionId();
                s = {
                    id: sessionId,
                    prompt: p,
                    response: '',
                    phases: emptyPhases,
                    orphanEvents: [],
                    actions: [],
                    currentPhase: null
                };
                window.state.sessions.unshift(s);
                window.state.activeId = sessionId;
            } else {
                // 追问模式
                const previousPrompt = s.prompt ? s.prompt + '\n\n---\n\n' : '';
                s.prompt = previousPrompt + p;
                s.phases = emptyPhases;
                s.orphanEvents = [];
                s.actions = [];
                s.currentPhase = null;
            }

            // 初始化提示
            s.orphanEvents.push({
                type: "thought",
                content: "正在初始化引擎，请稍候..."
            });

            if (typeof window.renderAll === 'function') {
                window.renderAll();
            }
            if (typeof window.saveState === 'function') {
                window.saveState();
            }

            try {
                // 使用新 API 提交
                if (newAPISessions.has(s.id) || await sessionExistsOnBackend(s.id)) {
                    await continueWithNewAPI(p, s.id);
                } else {
                    await submitWithNewAPI(p, sessionId);
                }

                // 更新 UI
                if (typeof window.renderAll === 'function') {
                    window.renderAll();
                }
            } catch (e) {
                console.error('[NewAPI] Failed, falling back to legacy API:', e);

                // 回退到旧 API
                if (stopBtn) stopBtn.classList.add('hidden');
                if (rs) rs.classList.remove('hidden');

                // 调用原始函数
                if (originalSubmitTask) {
                    originalSubmitTask.call(window);
                }
            }
        } else {
            // 使用旧 API
            console.log('[LegacyAPI] Using legacy CLI API');
            if (originalSubmitTask) {
                originalSubmitTask.call(window);
            }
        }
    }

    /**
     * 初始化：Monkey patch submitTask
     */
    function init() {
        if (typeof window.submitTask !== 'function') {
            console.warn('[NewAPI] submitTask not found, waiting for DOM loaded...');
            setTimeout(init, 100);
            return;
        }

        // 保存原始函数
        originalSubmitTask = window.submitTask;

        // 替换为新函数
        window.submitTask = newSubmitTask;

        console.log('[NewAPI] submitTask has been patched to support new API');
        console.log('[NewAPI] ENABLE_NEW_API:', ENABLE_NEW_API);
        console.log('[NewAPI] USE_NEW_API_FOR_NEW_SESSIONS:', USE_NEW_API_FOR_NEW_SESSIONS);
    }

    // DOM 加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
