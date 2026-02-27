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
            .mode-selector-container {
                position: relative;
                margin-left: 8px;
                user-select: none;
            }
            .mode-active-display {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                background: rgba(0,0,0,0.04);
                border-radius: 12px;
                border: 1px solid rgba(0,0,0,0.08);
                cursor: pointer;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .dark .mode-active-display {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
            }
            .mode-active-display:hover {
                background: rgba(0,0,0,0.08);
                transform: translateY(-1px);
            }
            .dark .mode-active-display:hover {
                background: rgba(255,255,255,0.1);
            }
            .mode-active-display .mode-label {
                font-size: 12px;
                font-weight: 600;
                color: #444;
                letter-spacing: 0.01em;
            }
            .dark .mode-active-display .mode-label { color: #ccc; }
            .mode-active-display .arrow {
                font-size: 16px;
                color: #888;
                transition: transform 0.2s ease;
            }
            .mode-active-display.open .arrow {
                transform: rotate(180deg);
            }
            .mode-dropdown {
                position: absolute;
                bottom: calc(100% + 12px);
                left: 0;
                min-width: 180px;
                background: #fff;
                border-radius: 16px;
                box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1);
                border: 1px solid rgba(0,0,0,0.08);
                overflow: hidden;
                opacity: 0;
                transform: scale(0.95);
                pointer-events: none;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                z-index: 100;
            }
            .dark .mode-dropdown {
                background: #1f2937;
                border: 1px solid rgba(255,255,255,0.1);
                box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3);
            }
            .mode-dropdown.show {
                opacity: 1;
                transform: scale(1);
                pointer-events: auto;
            }
            .mode-option {
                padding: 10px 16px;
                display: flex;
                flex-direction: column;
                gap: 2px;
                cursor: pointer;
                transition: background 0.2s;
            }
            .mode-option:hover {
                background: rgba(0,0,0,0.04);
            }
            .dark .mode-option:hover {
                background: rgba(255,255,255,0.05);
            }
            .mode-option.active {
                background: rgba(59, 130, 246, 0.08);
            }
            .dark .mode-option.active {
                background: rgba(59, 130, 246, 0.15);
            }
            .mode-option-title {
                font-size: 13px;
                font-weight: 600;
                color: #111;
            }
            .dark .mode-option-title { color: #eee; }
            .mode-option-desc {
                font-size: 11px;
                color: #777;
            }
            .dark .mode-option-desc { color: #999; }

            #stopStream {
                border: 2px solid #000 !important;
                background: #000 !important;
                color: #fff !important;
            }
            .dark #stopStream {
                border: 2px solid #fff !important;
                background: #fff !important;
                color: #000 !important;
            }
            #stopStream:hover {
                background: #000 !important;
                color: #fff !important;
                opacity: 0.8;
            }
            .dark #stopStream:hover {
                background: #fff !important;
                color: #000 !important;
                opacity: 0.8;
            }
        `;
        document.head.appendChild(styles);

        // 注入模式选择器到输入框下方按钮栏
        const target = document.querySelector('#bottom-input-container .flex.items-center.gap-1');
        if (target) {
            const container = document.createElement('div');
            container.className = 'mode-selector-container';
            container.innerHTML = `
                <div class="mode-active-display" id="mode-trigger">
                    <span class="material-symbols-outlined !text-[16px]">psychology</span>
                    <span class="mode-label" id="active-mode-name">Plan (分析)</span>
                    <span class="material-symbols-outlined arrow">expand_more</span>
                </div>
                <div class="mode-dropdown" id="mode-dropdown">
                    <div class="mode-option active" data-mode="plan">
                        <span class="mode-option-title">Plan (分析模式)</span>
                        <span class="mode-option-desc">仅制定计划和分析，不修改文件</span>
                    </div>
                    <div class="mode-option" data-mode="build">
                        <span class="mode-option-title">Build (开发模式)</span>
                        <span class="mode-option-desc">全自动执行，支持读写文件及运行代码</span>
                    </div>
                    <div class="mode-option" data-mode="auto">
                        <span class="mode-option-title">Auto (智能模式)</span>
                        <span class="mode-option-desc">由 OpenCode 根据任务自动选择</span>
                    </div>
                </div>
            `;
            target.appendChild(container);

            const trigger = container.querySelector('#mode-trigger');
            const dropdown = container.querySelector('#mode-dropdown');
            const activeLabel = container.querySelector('#active-mode-name');

            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                const isOpen = dropdown.classList.contains('show');
                if (isOpen) {
                    dropdown.classList.remove('show');
                    trigger.classList.remove('open');
                } else {
                    dropdown.classList.add('show');
                    trigger.classList.add('open');
                }
            });

            document.addEventListener('click', () => {
                dropdown.classList.remove('show');
                trigger.classList.remove('open');
            });

            dropdown.addEventListener('click', (e) => {
                const option = e.target.closest('.mode-option');
                if (!option) return;
                
                const mode = option.dataset.mode;
                dropdown.querySelectorAll('.mode-option').forEach(o => o.classList.remove('active'));
                option.classList.add('active');
                
                const labels = {
                    'plan': 'Plan (分析)',
                    'build': 'Build (开发)',
                    'auto': 'Auto (智能)'
                };
                activeLabel.textContent = labels[mode];
                window._currentMode = mode;
                
                dropdown.classList.remove('show');
                trigger.classList.remove('open');
                console.log('[NewAPI] Agent mode switched to:', mode);
            });
        }
        window._currentMode = 'plan';
        window._turnIndex = 0; // 追踪对话轮次

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
     * 准备并切换 Session
     */
    async function prepareSession(prompt, isWelcome) {
        // 尝试从本地状态查找（如果已经点击过侧边栏切换）
        let existing = window.state.sessions.find(s => s.id === window.state.activeId);
        
        // 如果是新任务，或者当前没有活跃 ID，则创建
        if (!existing || isWelcome) {
            const mode = window._currentMode || 'plan';
            console.log('[NewAPI] Creating new session with mode:', mode);
            const session = await window.apiClient.createSession(prompt, mode);
            
            existing = {
                id: session.id,
                title: session.title,
                prompt: prompt,
                response: '',
                phases: [],
                deliverables: [],
                status: 'active',
                mode: mode // 保存模式
            };
            window.state.sessions.unshift(existing);
        }
        return existing;
    }


        const isWelcome = btn.id === 'runStream-welcome';
        const primaryInput = document.getElementById(isWelcome ? 'prompt-welcome' : 'prompt');
        const secondaryInput = document.getElementById(isWelcome ? 'prompt' : 'prompt-welcome');

        const promptValue = (primaryInput?.value || secondaryInput?.value || '').trim();
        if (!promptValue) return;

        console.log('[NewAPI] Processing submission...', { isWelcome, promptLength: promptValue.length });

        try {
            const mode = s.mode || window._currentMode || 'plan';
            console.log(`[NewAPI] Connecting to events... (Mode: ${mode})`);
            
            // 1. 订阅事件
            window.apiClient.subscribeToEvents(s.id, (data) => {
                handleNewAPIEvent(data, s);
            });

            // 2. 发送消息
            if (isNewTask) {
                console.log('[NewAPI] Sending initial message...');
                await window.apiClient.sendTextMessage(s.id, s.prompt, { mode: mode });
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

            // 如果当前是伪造session，先移除它
            if (isFakeId && s) {
                const fakeIndex = state.sessions.findIndex(x => x.id === s.id);
                if (fakeIndex !== -1) {
                    console.log('[NewAPI] Removing fake session:', s.id);
                    state.sessions.splice(fakeIndex, 1);
                }
            }

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
        // 调用 opencode.js 中的完整保存函数，而不是自定义逻辑
        if (typeof window.saveState === 'function') {
            window.saveState();
        } else {
            // 降级方案：手动保存（包含 deliverables）
            localStorage.setItem('opencode_state', JSON.stringify({
                activeId: state.activeId,
                sessions: state.sessions.map(s => ({
                    id: s.id,
                    title: s.title,
                    prompt: s.prompt,
                    response: s.response,
                    phases: s.phases || [],
                    deliverables: s.deliverables || [],
                    currentPhase: s.currentPhase
                }))
            }));
        }
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
        console.log('[NewAPI] Establishing SSE for:', s.id, 'isNewSubmission:', isNewSubmission);

        if (window.state.activeSSE) {
            console.log('[NewAPI] Closing existing SSE');
            window.state.activeSSE.close();
        }

        // 显示停止按钮，隐藏发送按钮
        const stopBtn = document.getElementById('stopStream');
        const runBtn = document.getElementById('runStream');
        if (stopBtn) stopBtn.classList.remove('hidden');
        if (runBtn) runBtn.classList.add('hidden');

        // 检查会话是否有活跃的 phase 或正在进行中
        const hasActivePhase = s.phases && s.phases.some(p => p.status === 'active');
        const isRunning = hasActivePhase || (s.phases && s.phases.length > 0 && s.phases[s.phases.length - 1].status !== 'completed');

        // 如果是新提交或正在运行的会话，自动展开右侧面板
        if (isNewSubmission || isRunning) {
            if (window.rightPanelManager && typeof window.rightPanelManager.show === 'function') {
                window.rightPanelManager.show();
                // 切换到预览标签页
                if (typeof window.rightPanelManager.switchTab === 'function') {
                    window.rightPanelManager.switchTab('preview');
                }
                console.log('[NewAPI] Right panel auto-expanded (isNewSubmission:', isNewSubmission, ', isRunning:', isRunning, ')');
            }
        }

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
            window._turnIndex = (window._turnIndex || 0) + 1; // 每一轮新对话增加索引
            const currentPrompt = s.prompt.split('

---

').pop();
            console.log('[NewAPI] Sending user message to backend (Mode:', window._currentMode, ', Turn:', window._turnIndex, ')');
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
        // 处理文件预览事件 - 更新右侧文件面板（带打字机效果）
        if (adapted.type === 'file_preview_start') {
            console.log('[NewAPI] File preview start:', adapted.file_path);

            // 显示文件编辑器
            if (window.rightPanelManager && typeof window.rightPanelManager.showFileEditor === 'function') {
                window.rightPanelManager.showFileEditor(adapted.file_path, '');
            }
            return;
        }

        if (adapted.type === 'file_preview_delta') {
            console.log('[NewAPI] File preview delta:', adapted.delta?.substring(0, 50) + '...');

            // 使用打字机效果追加内容
            if (window.rightPanelManager && typeof window.rightPanelManager.typeAppendContent === 'function') {
                window.rightPanelManager.typeAppendContent(adapted.delta);
            } else if (window.rightPanelManager && typeof window.rightPanelManager.appendFileContent === 'function') {
                // 降级：直接追加（无打字机效果）
                window.rightPanelManager.appendFileContent(adapted.delta);
            }
            return;
        }

        if (adapted.type === 'file_preview_end') {
            console.log('[NewAPI] File preview end:', adapted.file_path);

            // 更新状态为完成
            if (window.rightPanelManager && typeof window.rightPanelManager.setFileStatus === 'function') {
                window.rightPanelManager.setFileStatus('完成');
            }
            return;
        }

        // 处理时间轴事件 - 更新右侧文件面板
        if (adapted.type === 'timeline_event') {
            console.log('[NewAPI] Timeline event:', adapted);
            // 可以在这里触发右侧面板更新
            return;
        }

        if (adapted.type === 'answer_chunk') {
            // 支持多轮对话分隔符
            const pSep = '\n\n---\n\n';
            const rSep = '\n\n---\n\n**新的回答：**\n\n';
            const pCount = (s.prompt || '').split(pSep).length - 1;
            const rCount = (s.response || '').split(rSep).length - 1;
            if (pCount > rCount) {
                s.response += rSep;
            }
            s.response += adapted.text;
        } else if (adapted.type === 'phases_init') {
            // 处理阶段初始化
            const currentTurnIndex = window._turnIndex || 0;
            const newPhases = (adapted.phases || []).map(p => {
                const existingPhase = s.phases?.find(sp => sp.id === p.id);
                return { 
                    ...p, 
                    events: existingPhase?.events || [],
                    turn_index: existingPhase?.turn_index ?? currentTurnIndex // 关联到当前对话轮次
                };
            });

            
            const phaseMap = new Map();
            s.phases?.forEach(p => phaseMap.set(p.id, p));
            
            newPhases.forEach(p => {
                const existing = phaseMap.get(p.id);
                if (existing) {
                    // 只有在现有状态是 pending 或者新状态不是 pending 时才更新状态
                    if (p.status !== 'pending' || existing.status === 'pending') {
                        existing.status = p.status;
                    }
                    if (p.title) existing.title = p.title;
                    if (p.number !== undefined) existing.number = p.number;
                } else {
                    phaseMap.set(p.id, p);
                }
            });
            
            s.phases = Array.from(phaseMap.values()).sort((a, b) => (a.number || 0) - (b.number || 0));

            // 自动清理临时的 Planning Phase
            const hasDynamicPhases = s.phases.some(p => p.id?.startsWith('phase_') && p.id !== 'phase_planning');
            if (hasDynamicPhases) {
                s.phases = s.phases.filter(p => p.id !== 'phase_planning');
            }
            
            s.currentPhase = adapted.phases.find(p => p.status === 'active')?.id || s.currentPhase;
        } else if (adapted.type === 'deliverables') {
            s.deliverables = adapted.items || [];
        } else if (adapted.type === 'status' || (adapted.type === 'message_updated' && adapted.time?.completed)) {
            // 标记当前活跃阶段为完成，不应盲目标记所有阶段
            const isError = adapted.value === 'error' || adapted.status === 'error';
            if (s.phases) {
                s.phases.forEach(p => {
                    if (p.status === 'active') {
                        p.status = isError ? 'error' : 'completed';
                    }
                });
            }
            document.getElementById('stopStream')?.classList.add('hidden');
            document.getElementById('runStream')?.classList.remove('hidden');
            console.log(`[NewAPI] Task session ${isError ? 'failed' : 'completed'}`);

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
            // 实时显示到右侧面板
            if (window.rightPanelManager) {
                const data = adapted.data || {};
                const toolName = data.tool_name || adapted.tool || '';

                // 确保右侧面板展开并切换到预览标签页
                if (typeof window.rightPanelManager.show === 'function') {
                    window.rightPanelManager.show();
                }
                if (typeof window.rightPanelManager.switchTab === 'function') {
                    window.rightPanelManager.switchTab('preview');
                }

                // 判断事件类型并显示
                if (adapted.type === 'thought') {
                    // 显示思考内容
                    const content = adapted.content || adapted.data?.text || '';
                    console.log('[NewAPI] 显示思考内容到右侧面板');
                    window.rightPanelManager.showFileEditor('💭 思考过程', content);
                } else if (adapted.type === 'action') {
                    // 显示工具操作
                    const output = data.output || '';
                    const toolLower = toolName.toLowerCase();

                    if (toolLower === 'read') {
                        // read 工具 - 显示文件内容
                        const input = data.input || {};
                        const filePath = input.path || input.file_path || 'unknown';
                        console.log('[NewAPI] 显示read文件内容:', filePath);
                        window.rightPanelManager.showFileEditor(filePath, output);
                    } else if (toolLower === 'bash' || toolLower === 'grep') {
                        // bash/grep - 显示命令输出
                        const input = data.input || {};
                        const command = input.command || input.pattern || '';
                        const title = command ? `${toolName}: ${command}` : `${toolName} 输出`;
                        console.log('[NewAPI] 显示终端输出:', title);
                        window.rightPanelManager.showFileEditor(title, output);
                    } else if (toolLower === 'write' || toolLower === 'edit' || toolLower === 'file_editor') {
                        // write/edit - 显示正在写入
                        const input = data.input || {};
                        const filePath = input.path || input.file_path || 'unknown';
                        const content = input.content || '';

                        console.log('[NewAPI] 显示写入文件:', filePath);
                        window.rightPanelManager.showFileEditor(filePath, '正在写入...');

                        // 如果有内容，使用打字机效果
                        if (content && typeof content === 'string') {
                            setTimeout(() => {
                                if (window.rightPanelManager.fileEditorContainer) {
                                    window.rightPanelManager.fileEditorContainer.classList.remove('hidden');
                                    const pre = document.getElementById('file-code-content');
                                    if (pre) {
                                        pre.textContent = '';
                                        // 打字机效果
                                        let i = 0;
                                        const typeWriter = () => {
                                            if (i < content.length) {
                                                pre.textContent += content.charAt(i);
                                                i++;
                                                setTimeout(typeWriter, 5); // 5ms 打字速度
                                            }
                                        };
                                        typeWriter();
                                    }
                                }
                            }, 100);
                        }
                    } else if (toolLower === 'browser' || toolLower.includes('web')) {
                        // browser 工具 - 显示浏览器操作
                        const input = data.input || {};
                        const action = data.action || toolName;
                        const details = Object.entries(input).map(([k, v]) => `${k}: ${v}`).join('\n');
                        console.log('[NewAPI] 显示浏览器操作:', action);
                        window.rightPanelManager.showFileEditor(`🌐 ${action}`, details || '浏览器操作中...');
                    } else {
                        // 其他工具 - 显示通用信息
                        const input = data.input || {};
                        const title = `🔧 ${toolName}`;
                        const details = Object.entries(input).map(([k, v]) => `${k}: ${v}`).join('\n');
                        console.log('[NewAPI] 显示工具操作:', toolName);
                        window.rightPanelManager.showFileEditor(title, details || '工具执行中...');
                    }
                } else if (adapted.type === 'error') {
                    // 显示错误信息
                    const errorMsg = adapted.message || adapted.content || '未知错误';
                    console.log('[NewAPI] 显示错误信息:', errorMsg);
                    window.rightPanelManager.showFileEditor('❌ 错误', errorMsg);
                }
            }

            // 处理 action/thought/error
            if (!s.phases || s.phases.length === 0) {
                s.phases = [{ id: 'phase_executing', title: '🚀 任务执行中', status: 'active', events: [] }];
                s.currentPhase = 'phase_executing';
            }

            const targetPhase = s.phases.find(p => p.id === s.currentPhase) || s.phases[s.phases.length - 1];
            if (targetPhase) {
                if (!targetPhase.events) targetPhase.events = [];

                const eventId = adapted.id || (adapted.data && (adapted.data.id || adapted.data.call_id)) || adapted.message_id;

                if (!targetPhase.events) targetPhase.events = [];
                
                // 增加 event_id 去重检查，防止重复添加相同动作
                const isDuplicate = eventId && targetPhase.events.some(e => {
                    const eId = e.id || (e.data && (e.data.id || e.data.call_id)) || e.message_id;
                    return eId === eventId;
                });

                if (isDuplicate) {
                    console.log('[NewAPI] Skipping duplicate event:', eventId);
                    return;
                }

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

                    // 文件收集：如果是write/edit/file_editor工具，将文件添加到deliverables
                    if (adapted.type === 'action' && adapted.data) {
                        const toolName = adapted.data.tool_name || adapted.data.tool || '';
                        const toolLower = toolName.toLowerCase();

                        // 判断是否为文件写入类工具
                        if (toolLower === 'write' || toolLower === 'edit' || toolLower === 'file_editor') {
                            const input = adapted.data.input || {};
                            const filePath = input.path || input.file_path || input.file;

                            if (filePath) {
                                // 初始化deliverables数组
                                if (!s.deliverables) s.deliverables = [];

                                // 检查文件是否已存在（避免重复）
                                const exists = s.deliverables.some(d => {
                                    const dPath = typeof d === 'string' ? d : (d.name || d.path);
                                    return dPath === filePath;
                                });

                                if (!exists) {
                                    s.deliverables.push(filePath);
                                    console.log('[NewAPI] 文件已添加到deliverables:', filePath);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    init();

})();
