/**
 * OpenCode.js 新 API 扩展 (V2.8)
 * 修复 404 错误：强制丢弃前端生成的旧版伪造 Session ID
 * 完整功能修复：找回丢失的 executeSubmission, prepareSession 等核心函数
 */

(function () {
    'use strict';

    const ENABLE_NEW_API = true;

    function init() {
        console.log('[NewAPI] Initializing V2.8 Patch (Advanced UI Mode)...');

        // 1. 全局点击捕获拦截
        window.addEventListener('click', handleGlobalClick, true);

        // 2. 劫持全局 connectSSE
        const originalConnectSSE = window.connectSSE;
        if (typeof window.connectSSE === 'function' && !window.connectSSE._isPatched) {
            const patchedConnectSSE = function (s) {
                if (!s) return;
                // 仅对真实受控的 Session 进行劫持
                if (s.id && s.id.startsWith('ses_') && s.id.length === 12) {
                    console.log('[NewAPI] Hijacking connectSSE for real session:', s.id);
                    return handleNewAPIConnection(s);
                }
                if (originalConnectSSE) return originalConnectSSE.apply(this, arguments);
            };
            patchedConnectSSE._isPatched = true;
            window.connectSSE = patchedConnectSSE;
        }

        // 3. 拦截回车键
        window.addEventListener('keydown', handleGlobalKeydown, true);

        // 4. 注入样式和 Mode Selector
        injectAdvancedUI();

        console.log('[NewAPI] V2.8 Advanced UI active');
    }

    /**
     * 注入高级 UI 元素 (Plan/Build Mode + CSS)
     */
    function injectAdvancedUI() {
        if (document.getElementById('opencode-patch-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'opencode-patch-styles';
        styles.textContent = `
            .mode-selector {
                display: flex;
                gap: 8px;
                margin-left: 8px;
                padding: 4px;
                background: rgba(0,0,0,0.03);
                border-radius: 20px;
                border: 1px solid rgba(0,0,0,0.05);
            }
            .dark .mode-selector {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
            }
            .mode-btn {
                padding: 4px 12px;
                border-radius: 16px;
                font-size: 11px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                color: #666;
            }
            .dark .mode-btn { color: #aaa; }
            .mode-btn.active {
                background: #000;
                color: #fff;
            }
            .dark .mode-btn.active {
                background: #fff;
                color: #000;
            }
            #stopStream {
                border: 2px solid #ff4d4f !important;
                background: transparent !important;
                color: #ff4d4f !important;
            }
            #stopStream:hover {
                background: #ff4d4f !important;
                color: #fff !important;
            }
        `;
        document.head.appendChild(styles);

        // 注入模式选择器到输入框下方按钮栏
        const target = document.querySelector('#bottom-input-container .flex.items-center.gap-1');
        if (target) {
            const selector = document.createElement('div');
            selector.className = 'mode-selector';
            selector.innerHTML = `
                <div class="mode-btn active" data-mode="plan">Plan</div>
                <div class="mode-btn" data-mode="build">Build</div>
            `;
            target.appendChild(selector);

            selector.addEventListener('click', (e) => {
                const btn = e.target.closest('.mode-btn');
                if (!btn) return;
                selector.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                window._currentMode = btn.dataset.mode;
            });
        }
        window._currentMode = 'plan';
    }

    /**
     * 全局点击处理器 (捕获阶段)
     */
    function handleGlobalClick(e) {
        // 增加对停止按钮的捕获
        const stopTarget = e.target.closest('#stopStream');
        if (stopTarget) {
            console.log('[NewAPI] Global Intercept: Stop clicked');
            e.stopPropagation();
            e.preventDefault();
            if (window.state.activeSSE) {
                window.state.activeSSE.close();
                window.state.activeSSE = null;
            }
            document.getElementById('stopStream')?.classList.add('hidden');
            document.getElementById('runStream')?.classList.remove('hidden');
            return;
        }

        const target = e.target.closest('#runStream, #runStream-welcome');
        if (!target) return;

        console.log(`[NewAPI] Global Intercept: ${target.id} clicked`);
        e.stopPropagation();
        e.preventDefault();

        executeSubmission(target);
    }

    /**
     * 全局按键处理器
     */
    function handleGlobalKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            const activeEl = document.activeElement;
            if (activeEl && (activeEl.id === 'prompt' || activeEl.id === 'prompt-welcome')) {
                console.log(`[NewAPI] Global Intercept: Enter on ${activeEl.id}`);
                e.stopPropagation();
                e.preventDefault();

                const btnId = activeEl.id === 'prompt-welcome' ? 'runStream-welcome' : 'runStream';
                const btn = document.getElementById(btnId);
                if (btn) executeSubmission(btn);
            }
        }
    }

    /**
     * 执行提交逻辑
     */
    async function executeSubmission(btn) {
        if (!ENABLE_NEW_API || !window.apiClient) {
            console.warn('[NewAPI] API Client not ready');
            return;
        }

        const isWelcome = btn.id === 'runStream-welcome';
        const primaryInput = document.getElementById(isWelcome ? 'prompt-welcome' : 'prompt');
        const secondaryInput = document.getElementById(isWelcome ? 'prompt' : 'prompt-welcome');

        const promptValue = (primaryInput?.value || secondaryInput?.value || '').trim();
        if (!promptValue) return;

        console.log('[NewAPI] Processing submission...', { isWelcome, promptLength: promptValue.length });

        try {
            // 设置按钮状态
            const runBtn = document.getElementById('runStream');
            if (runBtn) {
                runBtn.disabled = true;
                runBtn.innerHTML = '<span class="material-symbols-outlined animate-spin">refresh</span>';
            }

            // 1. 准备 Session
            let s = await prepareSession(promptValue, isWelcome);
            console.log('[NewAPI] Session focused:', s.id);

            // 2. 强力切换 UI 模式
            forceChatMode();

            // 3. 确保状态机指向当前 session
            window.state.activeId = s.id;
            if (typeof window.renderAll === 'function') window.renderAll();

            // 4. 连接并下发指令
            await handleNewAPIConnection(s, true);

            // 5. 清理
            if (primaryInput) primaryInput.value = '';
            if (secondaryInput) secondaryInput.value = '';

            // 恢复按钮状态
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.innerHTML = '<span class="material-symbols-outlined !text-white dark:!text-black">arrow_upward</span>';
            }

        } catch (err) {
            console.error('[NewAPI] Submission sequence failed:', err);
            alert('服务器响应异常: ' + (err.message || 'Error occurred'));
            const runBtn = document.getElementById('runStream');
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.innerHTML = '<span class="material-symbols-outlined !text-white dark:!text-black">arrow_upward</span>';
            }
        }
    }

    /**
     * 获取或创建 Session
     */
    async function prepareSession(prompt, forceNew = false) {
        const state = window.state;
        let s = state.sessions.find(x => x.id === state.activeId);

        // 识别逻辑：11位为伪造，12位为后端真实
        const isFakeId = s && s.id && s.id.startsWith('ses_') && s.id.length === 11;

        if (forceNew || !state.activeId || !s || !s.id.startsWith('ses_') || isFakeId) {
            console.log('[NewAPI] Target session is missing or invalid, creating fresh one...');

            const backendSession = await window.apiClient.createSession(prompt.substring(0, 30));
            console.log('[NewAPI] Backend created session:', backendSession.id);

            s = {
                id: backendSession.id,
                title: backendSession.title,
                prompt: prompt,
                response: '',
                phases: [],
                orphanEvents: [],
                actions: [],
                currentPhase: null
            };

            state.sessions.unshift(s);
            state.activeId = s.id;
        } else {
            console.log('[NewAPI] Reusing verified session:', s.id);
            s.prompt = (s.prompt ? s.prompt + '\n\n---\n\n' : '') + prompt;
            s.phases = [];
            s.currentPhase = null;
        }

        syncState(state);
        return s;
    }

    function syncState(state) {
        localStorage.setItem('opencode_state', JSON.stringify({
            activeId: state.activeId,
            sessions: state.sessions.map(s => ({
                id: s.id, title: s.title, prompt: s.prompt, response: s.response, phases: s.phases
            }))
        }));
        if (typeof window.renderSidebar === 'function') window.renderSidebar();
    }

    function forceChatMode() {
        const welcome = document.getElementById('welcome-interface');
        const chat = document.getElementById('chat-messages');
        if (welcome) welcome.classList.add('hidden');
        if (chat) chat.classList.remove('hidden');

        const bottomInputArea = document.getElementById('chat-bottom-input') || document.querySelector('.bottom-input-area');
        if (bottomInputArea) bottomInputArea.classList.remove('hidden');

        if (window.updateInterfaceMode) window.updateInterfaceMode();
    }

    async function handleNewAPIConnection(s, isNewSubmission = false) {
        console.log('[NewAPI] Establishing SSE for:', s.id);

        if (window.state.activeSSE) {
            console.log('[NewAPI] Closing existing SSE');
            window.state.activeSSE.close();
        }

        // 显示停止按钮，隐藏发送按钮
        const stopBtn = document.getElementById('stopStream');
        const runBtn = document.getElementById('runStream');
        if (stopBtn) stopBtn.classList.remove('hidden');
        if (runBtn) runBtn.classList.add('hidden');

        window.state.activeSSE = window.apiClient.subscribeToEvents(
            s.id,
            (newEvent) => {
                const adapted = window.EventAdapter?.adaptEvent(newEvent, s);
                if (!adapted) return;

                processEvent(s, adapted);

                // 实时渲染
                if (typeof window.renderResults === 'function' && window.state.activeId === s.id) {
                    window.renderResults();
                }

                // 检查是否完成
                if (adapted.type === 'status' && (adapted.value === 'done' || adapted.value === 'completed')) {
                    if (stopBtn) stopBtn.classList.add('hidden');
                    if (runBtn) runBtn.classList.remove('hidden');
                }
            },
            (err) => {
                console.error('[NewAPI] SSE Stream Error:', err);
                if (stopBtn) stopBtn.classList.add('hidden');
                if (runBtn) runBtn.classList.remove('hidden');
            }
        );

        if (isNewSubmission) {
            const currentPrompt = s.prompt.split('\n\n---\n\n').pop();
            console.log('[NewAPI] Sending user message to backend (Mode:', window._currentMode, ')');
            await window.apiClient.sendTextMessage(s.id, currentPrompt, { mode: window._currentMode });
        }

        // 重新同步 UI 状态
        if (window.state.activeId !== s.id) {
            window.state.activeId = s.id;
        }

        if (typeof window.renderAll === 'function') {
            window.renderAll();
        }
    }

    function processEvent(s, adapted) {
        if (adapted.type === 'answer_chunk') {
            s.response += adapted.text;
        } else if (adapted.type === 'status' || (adapted.type === 'message_updated' && adapted.time?.completed)) {
            // 标记所有 Phase 为完成
            if (s.phases) {
                s.phases.forEach(p => p.status = 'completed');
            }
            document.getElementById('stopStream')?.classList.add('hidden');
            document.getElementById('runStream')?.classList.remove('hidden');
        } else if (adapted.type === 'phase_start') {
            // 停用当前活跃 Phase
            if (s.currentPhase) {
                const prevPhase = s.phases.find(p => p.id === s.currentPhase);
                if (prevPhase) prevPhase.status = 'completed';
            }

            let phase = s.phases.find(p => p.id === adapted.phase_id);
            if (!phase) {
                phase = {
                    id: adapted.phase_id,
                    title: adapted.title || '正在执行',
                    description: adapted.description || '',
                    status: 'active',
                    events: []
                };
                s.phases.push(phase);
            } else {
                phase.status = 'active';
                // 如果后端提供了更具体的标题，更新它
                if (adapted.title && adapted.title !== 'Executing') {
                    phase.title = adapted.title;
                }
            }
            s.currentPhase = phase.id;
        } else if (adapted.type === 'phase_finish') {
            const phase = s.phases.find(p => p.id === adapted.phase_id);
            if (phase) phase.status = 'completed';
        } else if (adapted.type === 'action' || adapted.type === 'thought' || adapted.type === 'error') {
            // 处理 action/thought/error
            if (!s.phases || s.phases.length === 0) {
                s.phases = [{ id: 'phase_executing', title: '🚀 任务执行中', status: 'active', events: [] }];
                s.currentPhase = 'phase_executing';
            }

            const targetPhase = s.phases.find(p => p.id === s.currentPhase) || s.phases[s.phases.length - 1];
            if (targetPhase) {
                if (!targetPhase.events) targetPhase.events = [];

                // 幂等处理：防止重复添加相同 Part ID 的事件
                const eventId = adapted.id || (adapted.data && (adapted.data.id || adapted.data.call_id)) || adapted.message_id;

                let existingEventIndex = -1;
                if (eventId) {
                    existingEventIndex = targetPhase.events.findIndex(e => {
                        const eId = e.id || (e.data && (e.data.id || e.data.call_id)) || e.message_id;
                        return eId === eventId;
                    });
                }

                if (existingEventIndex > -1) {
                    // 更新现有事件
                    const existing = targetPhase.events[existingEventIndex];
                    if (adapted.type === 'action' && existing.type === 'action') {
                        existing.data = { ...existing.data, ...adapted.data };
                    } else {
                        targetPhase.events[existingEventIndex] = adapted;
                    }
                } else {
                    // 只有在新事件时才追加
                    targetPhase.events.push(adapted);
                }
            }
        }
    }

    init();

})();
