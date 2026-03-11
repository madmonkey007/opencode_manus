/**
 * OpenCode.js 新 API 扩展 (V2.8)
 * 修复 404 错误：强制丢弃前端生成的旧版伪造 Session ID
 * 完整功能修复：找回丢失的 executeSubmission, prepareSession 等核心函数
 */

// ✅ 全局DEBUG常量 - 从window.DEBUG_MODE读取
const DEBUG = window.DEBUG_MODE || false;

// ✅ 统一日志管理器 - 提供更精细的控制
window.Logger = {
    // 记录日志（受DEBUG开关控制）
    log: function(category, ...args) {
        // error和warn始终记录，其他受DEBUG控制
        if (DEBUG || category === 'error' || category === 'warn') {
            console.log(`[${category}]`, ...args);
        }
    },
    
    // 快捷方法
    info: function(...args) { this.log('INFO', ...args); },
    warn: function(...args) { this.log('WARN', ...args); },
    error: function(...args) { this.log('ERROR', ...args); },
    debug: function(...args) { if (DEBUG) this.log('DEBUG', ...args); }
};

// 📝 使用说明：
// 1. window.DEBUG_MODE = false  → 只记录ERROR和WARN（生产环境）
// 2. window.DEBUG_MODE = true   → 记录所有日志（开发环境）
// 3. console.error 始终会显示
// 4. 使用示例：Logger.info('[NewAPI]', 'Processing...');

(function () {
    'use strict';

    const ENABLE_NEW_API = true;

    // ✅ 调试配置（暴露到全局，便于调试和跨文件访问）
    window.DEBUG_CONFIG = {
        ENABLE_THOUGHT_DIAGNOSTIC: false,
        ENABLE_DELIVERABLE_DIAGNOSTIC: false,
        ENABLE_MARKDOWN_DIAGNOSTIC: false
    };

    // ✅ 保留局部引用，兼容现有代码
    const DEBUG_CONFIG = window.DEBUG_CONFIG;

    // 🔍 Thought 事件追踪开关（在浏览器控制台设置：window._DEBUG_THOUGHT_EVENTS = true）
    window._DEBUG_THOUGHT_EVENTS = false;

    // 显示当前调试状态
    if (window._DEBUG_THOUGHT_EVENTS) {
        console.log('🔍 [DEBUG] Thought event tracking ENABLED');
        console.log('🔍 [DEBUG] To disable: window._DEBUG_THOUGHT_EVENTS = false');
    }

    // ✅ 修复1：提取重复的icons和labels定义为常量，消除重复代码
    const MODE_CONFIG = {
        plan: {
            icon: 'psychology',
            label: 'Plan (分析)',
            title: 'Plan (分析模式)',
            desc: '仅制定计划和分析，不修改文件'
        },
        build: {
            icon: 'build',
            label: 'Build (开发)',
            title: 'Build (开发模式)',
            desc: '全自动执行，支持读写文件及运行代码'
        },
        auto: {
            icon: 'auto_awesome',
            label: 'Auto (智能)',
            title: 'Auto (智能模式)',
            desc: '由 OpenCode 根据任务自动选择'
        }
    };

    // ✅ 修复可维护性：提取默认模式为常量（统一管理，易于修改）
    const DEFAULT_MODE = 'build';
    const VALID_MODES = ['plan', 'build', 'auto'];

    // ✅ 代码质量改进：提取魔法数字为常量
    // 子会话配置常量
    const CHILD_SESSION_CLEANUP_DELAY_MS = 5000; // 子会话完成后的清理延迟（毫秒）
    const RENDER_THROTTLE_MS = 500; // ✅ Round 4: 节流间隔提高到500ms，平衡响应性与性能
    const TYPING_EFFECT_TIMEOUT_MS = 30000; // ✅ P0-1: 打字机效果超时时间（30秒）

    // ✅ 安全错误消息常量（不暴露后端错误详情）
    const ERROR_MESSAGES = {
        SESSION_CREATE_FAILED: '创建会话失败，请稍后重试',
        NETWORK_ERROR: '网络连接失败，请检查网络设置',
        SUBMISSION_FAILED: '提交任务失败，请稍后重试',
        SERVER_ERROR: '服务器错误，请稍后重试'
    };

    // ✅ 根据错误对象返回安全的用户提示消息
    function getUserSafeErrorMessage(error, defaultMessage = ERROR_MESSAGES.SERVER_ERROR) {
        console.error('[NewAPI] Error details:', error);

        // 根据错误类型返回安全的用户提示
        if (error.message && (
            error.message.includes('network') ||
            error.message.includes('fetch') ||
            error.message.includes('ECONNREFUSED') ||
            error.message.includes('ERR_CONNECTION')
        )) {
            return ERROR_MESSAGES.NETWORK_ERROR;
        }

        return defaultMessage;
    }

    // ✅ v=29: 防止重复显示同一个文件的预览
    // ✅ v=30: 修复内存泄漏 - 使用LRU策略限制Map大小
    const _recentlyPreviewedFiles = new Map(); // path -> timestamp
    const PREVIEW_DEBOUNCE_MS = 2000; // 2秒内不重复预览同一文件
    const MAX_PREVIEW_CACHE_SIZE = 100; // 最多缓存100个文件路径

    const TypingEffectManager = (function () {
        let count = 0; // 并发计数器（支持多文件同时写入）
        let timeout = null; // 超时定时器

        return {
            /**
             * 开始打字机效果
             * @param {string} reason - 开始原因（用于日志）
             */
            start(reason = 'unknown') {
                count++;
                console.log(`[TypingEffectManager] Start (count: ${count}, reason: ${reason})`);

                // ✅ v=29: 每次start都重置超时定时器（防止Query气泡抖动）
                // ✅ v=30: 修复并发bug - 防止"永远不超时"的问题
                if (timeout) {
                    clearTimeout(timeout);
                }
                timeout = setTimeout(() => {
                    console.warn(`[TypingEffectManager] ⚠️ Timeout after ${TYPING_EFFECT_TIMEOUT_MS}ms, auto-resetting`);
                    this.reset('timeout');
                }, TYPING_EFFECT_TIMEOUT_MS);
                console.log(`[TypingEffectManager] Timeout timer reset for ${TYPING_EFFECT_TIMEOUT_MS}ms`);
            },

            /**
             * 结束打字机效果
             * @param {string} reason - 结束原因（用于日志）
             */
            end(reason = 'unknown') {
                count = Math.max(0, count - 1);
                console.log(`[TypingEffectManager] End (count: ${count}, reason: ${reason})`);

                if (count === 0 && timeout) {
                    clearTimeout(timeout);
                    timeout = null;
                }
            },

            /**
             * 重置打字机效果（异常恢复）
             * @param {string} reason - 重置原因（用于日志）
             */
            reset(reason = 'manual') {
                const wasActive = count > 0;
                count = 0;
                if (timeout) {
                    clearTimeout(timeout);
                    timeout = null;
                }
                if (wasActive) {
                    console.warn(`[TypingEffectManager] Reset (reason: ${reason})`);
                }
            },

            /**
             * 检查是否有打字机效果正在进行
             * @returns {boolean}
             */
            isActive() {
                return count > 0;
            },

            /**
             * 获取当前活跃的打字机效果数量
             * @returns {number}
             */
            getActiveCount() {
                return count;
            }
        };
    })();

    // 子会话ID解析模式
    const TASK_ID_PATTERN = /task_id:\s*(ses_[a-zA-Z0-9]+)/;

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
                if (s.id && s.id.startsWith('ses_') && s.id.length >= 11) {
                    console.log('[NewAPI] Hijacking connectSSE for real session:', s.id);
                    return handleNewAPIConnection(s);
                }
                if (originalConnectSSE) return originalConnectSSE.apply(this, arguments);
            };
            patchedConnectSSE._isPatched = true;
            window.connectSSE = patchedConnectSSE;
        }

        // 3. 拦截回车键
        // ❌ v=38.3.1修复：注释掉全局Enter键拦截，避免与opencode.js的元素级处理器冲突
        // 问题：全局捕获 phase 阻止了 opencode.js 中 #prompt 元素的事件处理器执行
        // window.addEventListener('keydown', handleGlobalKeydown, true);

        // 4. 注入样式和 Mode Selector
        injectAdvancedUI();

        // 5. 劫持 updateInterfaceMode 以在切换模式时清空面板
        // 使用定时器延迟劫持，因为 opencode.js 在此脚本之后加载
        let hijackAttempts = 0;
        let lastActiveId = null; // 跟踪上一次的会话ID
        const hijackInterval = setInterval(() => {
            hijackAttempts++;
            if (typeof window.updateInterfaceMode === 'function' && !window.updateInterfaceMode._isPanelHijacked) {
                clearInterval(hijackInterval);
                const originalUpdateInterfaceMode = window.updateInterfaceMode;
                window.updateInterfaceMode = function () {
                    // 调用原函数
                    const result = originalUpdateInterfaceMode.apply(this, arguments);

                    // 只在会话真正切换时才清空面板
                    const state = window.state;
                    if (state && state.activeId) {
                        // 检查会话是否切换
                        if (lastActiveId && lastActiveId !== state.activeId) {
                            // 清理旧会话的子会话订阅
                            if (window.ChildSessionManager) {
                                window.ChildSessionManager.unsubscribeAllFromMain(lastActiveId);
                            }

                            const activeSession = state.sessions.find(x => x.id === state.activeId);
                            // 只有切换到空白会话（没有prompt和response）时才清空
                            if (activeSession && !activeSession.prompt && !activeSession.response) {
                                if (window.rightPanelManager) {
                                    window.rightPanelManager.clear();
                                    console.log('[NewAPI] Cleared panel for new empty session (switched from', lastActiveId, 'to', state.activeId + ')');
                                }
                            }
                        }
                        // 更新跟踪的会话ID
                        lastActiveId = state.activeId;

                        // 更新模式选择器显示
                        updateModeSelectorDisplay(state);
                    }

                    return result;
                };
                window.updateInterfaceMode._isPanelHijacked = true;
                console.log('[NewAPI] Successfully hijacked updateInterfaceMode for panel clearing');
            } else if (hijackAttempts > 50) {
                // 10秒后停止尝试（50 * 200ms）
                clearInterval(hijackInterval);
                console.warn('[NewAPI] Failed to hijack updateInterfaceMode after 50 attempts');
            }
        }, 200);

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
            // ✅ 修复：从当前session获取mode，如果没有则使用window._currentMode，最后默认为build
            const activeId = window.state?.activeId;
            const activeSession = window.state?.sessions?.find(s => s.id === activeId);
            // ✅ 修复可维护性：使用DEFAULT_MODE常量替代硬编码
            const currentMode = activeSession?.mode || window._currentMode || DEFAULT_MODE;

            const container = document.createElement('div');
            container.className = 'mode-selector-container';
            container.innerHTML = `
                 <div class="mode-active-display" id="mode-trigger">
                     <span class="material-symbols-outlined !text-[16px]">${MODE_CONFIG[currentMode].icon}</span>
                     <span class="mode-label" id="active-mode-name">${MODE_CONFIG[currentMode].label}</span>
                     <span class="material-symbols-outlined arrow">expand_more</span>
                 </div>
                 <div class="mode-dropdown" id="mode-dropdown">
                     <div class="mode-option ${currentMode === 'plan' ? 'active' : ''}" data-mode="plan">
                         <span class="mode-option-title">${MODE_CONFIG.plan.title}</span>
                         <span class="mode-option-desc">${MODE_CONFIG.plan.desc}</span>
                     </div>
                     <div class="mode-option ${currentMode === 'build' ? 'active' : ''}" data-mode="build">
                         <span class="mode-option-title">${MODE_CONFIG.build.title}</span>
                         <span class="mode-option-desc">${MODE_CONFIG.build.desc}</span>
                     </div>
                     <div class="mode-option ${currentMode === 'auto' ? 'active' : ''}" data-mode="auto">
                         <span class="mode-option-title">${MODE_CONFIG.auto.title}</span>
                         <span class="mode-option-desc">${MODE_CONFIG.auto.desc}</span>
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
        window._turnIndex = 0; // 追踪对话轮次

        // 初始化欢迎页模式选择器（会在内部设置默认模式为 build）
        initWelcomeModeSelector();
    }

    /**
     * 初始化欢迎页模式选择器
     */
    function initWelcomeModeSelector() {
        const container = document.getElementById('welcome-mode-selector');
        if (!container) return;

        const buttons = container.querySelectorAll('.mode-btn-welcome');
        const styles = {
            active: 'bg-white dark:bg-gray-700 shadow',
            inactive: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
        };

        function updateButtonSelection(selectedMode) {
            buttons.forEach(btn => {
                const mode = btn.dataset.mode;
                if (mode === selectedMode) {
                    btn.classList.add(...styles.active.split(' '));
                    btn.classList.remove(...styles.inactive.split(' '));
                } else {
                    btn.classList.remove(...styles.active.split(' '));
                    btn.classList.add(...styles.inactive.split(' '));
                }
            });
        }

        // 初始化：设置 Build 为默认选中
        updateButtonSelection('build');
        window._currentMode = 'build';

        // 添加点击事件监听
        buttons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const mode = btn.dataset.mode;
                window._currentMode = mode;
                updateButtonSelection(mode);
                console.log('[NewAPI] Welcome page mode switched to:', mode);
            });
        });

        console.log('[NewAPI] Welcome mode selector initialized with default mode: build');
    }

    /**
     * DOM元素缓存（优化性能，带生命周期验证）
     */
    const modeSelectorCache = {
        modeLabel: null,
        modeTrigger: null,
        dropdown: null,
        initialized: false,

        init() {
            // ✅ 修复：验证缓存的元素是否仍在DOM中
            if (this.initialized) {
                const stillInDOM = (this.modeLabel?.isConnected || document.contains(this.modeLabel)) &&
                    (this.modeTrigger?.isConnected || document.contains(this.modeTrigger));
                if (stillInDOM) {
                    return; // 缓存仍然有效
                }
                // DOM已重建，重新初始化
                console.log('[NewAPI] DOM cache invalidated, re-initializing');
            }

            // 重新初始化
            this.modeLabel = document.getElementById('active-mode-name');
            this.modeTrigger = document.getElementById('mode-trigger');
            this.dropdown = document.getElementById('mode-dropdown');

            // 只有在元素存在时才标记为已初始化
            this.initialized = !!(this.modeLabel && this.modeTrigger);

            if (!this.initialized) {
                console.warn('[NewAPI] Failed to initialize DOM cache - elements not found');
            }
        },

        reset() {
            this.initialized = false;
            this.modeLabel = null;
            this.modeTrigger = null;
            this.dropdown = null;
        }
    };

    /**
     * 防抖工具函数
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * ✅ 修复3：节流工具函数 - 限制函数执行频率
     * @param {Function} func - 要节流的函数
     * @param {number} limit - 时间限制（毫秒）
     * @returns {Function} 节流后的函数
     */
    function throttle(func, limit) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * 更新模式选择器显示以匹配当前session的mode（性能优化版）
     */
    function updateModeSelectorDisplay(state) {
        if (!state || !state.activeId) return;

        // ✅ 修复：使用最新的state避免快速切换时的竞态条件
        const activeSession = state.sessions.find(s => s.id === state.activeId);
        if (!activeSession || !activeSession.mode) return;

        const mode = activeSession.mode;

        // 使用缓存的DOM元素
        modeSelectorCache.init();
        const { modeLabel, modeTrigger, dropdown } = modeSelectorCache;

        // ✅ 修复：添加警告日志便于调试
        if (!modeLabel || !modeTrigger) {
            console.warn('[NewAPI] Mode selector DOM elements not found, skipping update for session:', state.activeId);
            return;
        }

        // ✅ 修复1：使用MODE_CONFIG常量，消除重复代码
        // 更新显示文本和图标
        modeLabel.textContent = MODE_CONFIG[mode].label;
        const iconSpan = modeTrigger.querySelector('.material-symbols-outlined');
        if (iconSpan && !iconSpan.classList.contains('arrow')) {
            iconSpan.textContent = MODE_CONFIG[mode].icon;
        }

        // 更新下拉菜单的选中状态
        if (dropdown) {
            dropdown.querySelectorAll('.mode-option').forEach(opt => {
                opt.classList.remove('active');
                if (opt.dataset.mode === mode) {
                    opt.classList.add('active');
                }
            });
        }

        console.log('[NewAPI] Mode selector updated to:', mode, 'for session:', state.activeId);
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

        executeSubmission(target, true);
    }

    /**
     * ❌ v=38.3.1修复：已禁用全局按键处理器
     *
     * 原因：全局捕获 phase 阻止了 opencode.js 中 #prompt 元素的事件处理器执行
     * 导致 Enter 键失效，无法提交任务
     */
    /*
    function handleGlobalKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            const activeEl = document.activeElement;
            if (activeEl && (activeEl.id === 'prompt' || activeEl.id === 'prompt-welcome')) {
                console.log(`[NewAPI] Global Intercept: Enter on ${activeEl.id}`);
                e.stopPropagation();
                e.preventDefault();

                const btnId = activeEl.id === 'prompt-welcome' ? 'runStream-welcome' : 'runStream';
                const btn = document.getElementById(btnId);
                if (btn) executeSubmission(btn, true);
            }
        }
    }
    */

    /**
     * ✅ v=35: 系统消息显示函数 - 用于显示thought、任务完成等消息（XSS安全）
     * 在主聊天区域创建临时的系统消息卡片
     *
     * 安全特性：
     * - 使用textContent而不是innerHTML插入用户内容
     * - 防止XSS攻击
     *
     * @param {string} content - 消息内容
     * @param {string} type - 消息类型 (thought|success|error|info)
     * @param {string|null} messageId - 消息ID（用于后续移除，P0修复）
     * @returns {HTMLElement|null} 返回消息卡片元素引用，失败时返回null
     */
    function addSystemMessage(content, type = 'info', messageId = null) {
        try {
            const s = state.sessions.find(x => x.id === state.activeId);
            if (!s) {
                console.warn('[addSystemMessage] No active session found');
                return null;
            }

            // 找到聊天消息容器
            const chatMessages = document.querySelector('#chat-messages');
            if (!chatMessages) {
                console.warn('[addSystemMessage] Chat messages container not found');
                return null;
            }

            // ✅ v=35: 消息配置对象 - 消除重复，易于扩展
            const MESSAGE_CONFIG = {
                thought: {
                    color: 'purple',
                    icon: 'psychology',
                    bgClass: 'bg-purple-50 dark:bg-purple-900/20',
                    borderClass: 'border-purple-200 dark:border-purple-700',
                    textClass: 'text-purple-800 dark:text-purple-200',
                    iconClass: 'text-purple-600 dark:text-purple-300'
                },
                success: {
                    color: 'green',
                    icon: 'check_circle',
                    bgClass: 'bg-green-50 dark:bg-green-900/20',
                    borderClass: 'border-green-200 dark:border-green-700',
                    textClass: 'text-green-800 dark:text-green-200',
                    iconClass: 'text-green-600 dark:text-green-300'
                },
                error: {
                    color: 'red',
                    icon: 'error',
                    bgClass: 'bg-red-50 dark:bg-red-900/20',
                    borderClass: 'border-red-200 dark:border-red-700',
                    textClass: 'text-red-800 dark:text-red-200',
                    iconClass: 'text-red-600 dark:text-red-300'
                },
                info: {
                    color: 'blue',
                    icon: 'info',
                    bgClass: 'bg-blue-50 dark:bg-blue-900/20',
                    borderClass: 'border-blue-200 dark:border-blue-700',
                    textClass: 'text-blue-800 dark:text-blue-200',
                    iconClass: 'text-blue-600 dark:text-blue-300'
                }
            };

            const config = MESSAGE_CONFIG[type] || MESSAGE_CONFIG.info;

            // 创建系统消息卡片
            const messageCard = document.createElement('div');
            messageCard.className = `system-message message-bubble mb-3 p-3 rounded-lg text-sm animate-fade-in ${config.bgClass} border ${config.borderClass} ${config.textClass}`;

            // ✅ P0修复：添加data属性用于后续移除
            if (messageId) {
                messageCard.setAttribute('data-message-id', messageId);
                messageCard.setAttribute('data-message-type', type);
            }

            // ✅ v=35: 安全地创建DOM结构（使用createElement而不是innerHTML）
            const container = document.createElement('div');
            container.className = 'flex items-start gap-2';

            // 创建图标
            const iconSpan = document.createElement('span');
            iconSpan.className = `material-symbols-outlined !text-[18px] ${config.iconClass}`;
            iconSpan.textContent = config.icon;

            // 创建内容容器
            const contentDiv = document.createElement('div');
            contentDiv.className = 'flex-1';
            // ✅ v=35: 关键安全改进 - 使用textContent防止XSS
            contentDiv.textContent = content;

            // 组装DOM树
            container.appendChild(iconSpan);
            container.appendChild(contentDiv);
            messageCard.appendChild(container);

            // 添加到聊天区域（append到最后）
            chatMessages.appendChild(messageCard);

            // 滚动到底部
            const scrollArea = document.querySelector('#chat-scroll-area');
            if (scrollArea) {
                scrollArea.scrollTop = scrollArea.scrollHeight;
            }

            // ✅ v=35: 改进日志 - 显示完整长度信息
            const preview = content.length > 50
                ? content.substring(0, 50) + `... (${content.length} chars)`
                : content;
            console.log(`[addSystemMessage] Displayed ${type} message:`, preview);

            // ✅ P0修复：返回消息卡片元素引用
            return messageCard;
        } catch (error) {
            console.error('[addSystemMessage] Failed to display message:', error);
            return null;
        }
    }

    // === Question Modal (blocking) ===
    const questionQueue = [];
    let activeQuestion = null;
    let questionModal = null;

    function setInputBlocked(blocked) {
        const runBtn = document.getElementById('runStream');
        const runBtnWelcome = document.getElementById('runStream-welcome');
        const prompt = document.getElementById('prompt');
        const promptWelcome = document.getElementById('prompt-welcome');
        const promptBottom = document.getElementById('prompt-bottom');
        const inputs = [prompt, promptWelcome, promptBottom];

        if (runBtn) runBtn.disabled = blocked;
        if (runBtnWelcome) runBtnWelcome.disabled = blocked;
        inputs.forEach((el) => {
            if (!el) return;
            el.disabled = blocked;
            if (blocked) {
                el.classList.add('opacity-50', 'cursor-not-allowed');
            } else {
                el.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        });
    }

    function normalizeQuestionPayload(data = {}) {
        const input = data.input || {};
        const question = data.question || input.question || input.prompt || data.title || '请回答以下问题';
        const rawChoices = data.choices || input.choices || input.options || [];
        const choices = Array.isArray(rawChoices)
            ? rawChoices.map((c) => {
                if (typeof c === 'string') return { label: c, value: c };
                return { label: c.label || c.text || String(c.value || c.id || ''), value: c.value || c.id || c.label || c.text || '' };
            }).filter(c => c.value !== '')
            : [];
        return { question, choices };
    }

    function enqueueQuestion(session, data) {
        const payload = normalizeQuestionPayload(data);
        questionQueue.push({ session, payload });
        if (!activeQuestion) {
            // Avoid UI re-render race; render in next tick
            setTimeout(showNextQuestion, 0);
        }
    }

    function showNextQuestion() {
        if (activeQuestion || questionQueue.length === 0) return;
        activeQuestion = questionQueue.shift();
        renderQuestionModal(activeQuestion.session, activeQuestion.payload);
    }

    function closeQuestionModal() {
        if (questionModal && questionModal.parentNode) {
            questionModal.parentNode.removeChild(questionModal);
        }
        questionModal = null;
        activeQuestion = null;
        setInputBlocked(false);
        showNextQuestion();
    }

    async function submitQuestionAnswer(sessionId, answer) {
        if (!answer || !answer.trim()) return;
        setInputBlocked(true);
        try {
            await window.apiClient.sendTextMessage(sessionId, answer.trim(), {
                mode: window._currentMode || 'build'
            });
            closeQuestionModal();
        } catch (err) {
            console.error('[QuestionModal] Failed to send answer:', err);
            alert('发送回答失败，请重试');
            setInputBlocked(false);
        }
    }

    function renderQuestionModal(session, payload) {
        const { question, choices } = payload;
        setInputBlocked(true);

        questionModal = document.createElement('div');
        // Use inline styles for critical layering/positioning to avoid missing Tailwind classes
        questionModal.className = 'fixed inset-0 bg-black/50 flex items-center justify-center p-4';
        questionModal.style.position = 'fixed';
        questionModal.style.top = '0';
        questionModal.style.right = '0';
        questionModal.style.bottom = '0';
        questionModal.style.left = '0';
        questionModal.style.zIndex = '9999';

        const card = document.createElement('div');
        card.className = 'bg-white dark:bg-zinc-900 rounded-lg w-full max-w-xl p-5 shadow-lg border border-gray-200 dark:border-gray-700';

        const title = document.createElement('div');
        title.className = 'text-base font-semibold text-gray-900 dark:text-gray-100 mb-2';
        title.textContent = '需要你的选择';

        const questionText = document.createElement('div');
        questionText.className = 'text-sm text-gray-700 dark:text-gray-300 mb-4 whitespace-pre-wrap';
        questionText.textContent = question;

        const choicesContainer = document.createElement('div');
        choicesContainer.className = 'flex flex-col gap-2 mb-4';

        const input = document.createElement('textarea');
        input.className = 'w-full min-h-[90px] p-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-zinc-800 text-sm text-gray-900 dark:text-gray-100';
        input.placeholder = '请在此输入你的回答';

        if (choices.length > 0) {
            choices.forEach((c) => {
                const btn = document.createElement('button');
                btn.className = 'w-full text-left px-3 py-2 rounded border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-zinc-800 text-sm text-gray-800 dark:text-gray-200';
                btn.textContent = c.label || c.value;
                btn.onclick = () => {
                    input.value = c.value || c.label || '';
                };
                choicesContainer.appendChild(btn);
            });
        } else {
            const hint = document.createElement('div');
            hint.className = 'text-xs text-gray-500 dark:text-gray-400';
            hint.textContent = '未提供选项，请直接输入回答。';
            choicesContainer.appendChild(hint);
        }

        const submitBtn = document.createElement('button');
        submitBtn.className = 'w-full mt-2 px-4 py-2 rounded bg-black text-white dark:bg-white dark:text-black text-sm';
        submitBtn.textContent = '提交回答';
        submitBtn.onclick = () => submitQuestionAnswer(session.id, input.value);

        card.appendChild(title);
        card.appendChild(questionText);
        card.appendChild(choicesContainer);
        card.appendChild(input);
        card.appendChild(submitBtn);
        questionModal.appendChild(card);
        document.body.appendChild(questionModal);
    }

    /**
     * ✅ P1修复：清理thinking消息的辅助函数
     *
     * 功能：
     * - 清除超时定时器
     * - 移除DOM元素（优先使用缓存的引用）
     * - 清理所有状态标志
     *
     * @param {Object} s - Session对象
     */
    function cleanupThinkingMessage(s) {
        if (!s) return;

        try {
            // 清除超时定时器
            if (s._thinkingTimeout) {
                clearTimeout(s._thinkingTimeout);
                s._thinkingTimeout = null;
                console.log('[Status] Cleared thinking timeout timer');
            }

            // 移除DOM元素（优先使用缓存的引用）
            if (s._thinkingMessageElement) {
                s._thinkingMessageElement.remove();
                s._thinkingMessageElement = null;
                console.log('[Status] Removed thinking message via cached element reference');
            } else if (s._thinkingMessageId) {
                // 如果缓存引用失效，通过ID查找并移除
                const chatMessages = document.querySelector('#chat-messages');
                if (chatMessages) {
                    const oldMessage = chatMessages.querySelector(`[data-message-id="${s._thinkingMessageId}"]`);
                    if (oldMessage) {
                        oldMessage.remove();
                        console.log('[Status] Removed thinking message via data attribute selector');
                    }
                }
            }

            // 清理所有状态标志
            s._isLoadingThinking = false;
            s._thinkingMessageId = null;
            s._thinkingMessageElement = null;

            console.log('[Status] All thinking state cleared');
        } catch (error) {
            console.error('[Status] Error cleaning up thinking message:', error);
            // 确保状态标志被清理，即使移除失败
            s._isLoadingThinking = false;
            s._thinkingMessageId = null;
            s._thinkingMessageElement = null;
            s._thinkingTimeout = null;
        }
    }

    // 暴露到全局作用域，供事件处理函数调用
    window.addSystemMessage = addSystemMessage;
    window.cleanupThinkingMessage = cleanupThinkingMessage;

    /**
     * Append answer chunk text to session response with timeline filtering.
     * Returns true if appended.
     */
    function appendAnswerChunk(s, text) {
        if (!s || typeof text !== 'string' || text.length === 0) return false;

        // ✅ v=33: 精确过滤timeline事件 - 避免误报AI的正常回复
        // 问题：后端可能错误地把timeline信息包装成answer_chunk
        const TIMELINE_PATTERNS = [
            // 模式1: 完整的timeline事件格式
            /^\s*Step ID:\s*[a-f0-9\-]+.*Action:\s*\w+.*$/mi,
            // 模式2: Timeline event开头
            /^\s*Timeline event:\s*\w+.*$/mi,
            // 模式3: 多个timeline字段组合（至少2个）
            /(?:Step ID:|Action:|tool_input:|file_path:|step_id:).*(?:Step ID:|Action:|tool_input:|file_path:)/mis
        ];

        // ✅ 重要：如果文本在markdown代码块中，不应该被过滤
        // AI的正常代码会包含"write"、"read"等，但会在```中
        const isInCodeBlock = /```\s*(?:javascript|python|json|bash|shell)?[\s\S]*?```/.test(text) ||
            text.trim().startsWith('```') ||
            text.includes('```代码');

        let isTimelineEvent = false;
        if (!isInCodeBlock && text.length > 0) {
            // 只有不在代码块中，才检查是否是timeline事件
            isTimelineEvent = TIMELINE_PATTERNS.some(pattern => pattern.test(text));
        }

        if (isTimelineEvent) {
            // ✅ 保存完整内容到debug变量，便于调试
            if (!window._debugFilteredTimeline) {
                window._debugFilteredTimeline = [];
            }
            window._debugFilteredTimeline.push({
                timestamp: Date.now(),
                content: text,
                preview: text.substring(0, 200)
            });

            console.warn('[NewAPI] ⚠️ Filtered structured timeline event from answer_chunk');
            console.log('[NewAPI] Debug: Filtered content preview:', text.substring(0, 150));
            console.log('[NewAPI] Debug: Total filtered events:', window._debugFilteredTimeline.length);

            // 不添加到response中，跳过这段文本
            return false;
        }

        // 支持多轮对话分隔符
        const pSep = '\n\n---\n\n';
        const rSep = '\n\n---\n\n**新的回答：**\n\n';
        const pCount = (s.prompt || '').split(pSep).length - 1;
        const rCount = (s.response || '').split(rSep).length - 1;
        if (pCount > rCount) {
            s.response += rSep;
        }
        s.response += text;
        return true;
    }

    /**
     * ✅ 修复3：节流版本的状态更新函数 - 限制DOM更新频率（每500ms最多更新一次）
     * 防止每个字符delta都触发DOM更新
     */
    const throttledSetFileStatus = throttle((status) => {
        if (window.rightPanelManager && typeof window.rightPanelManager.setFileStatus === 'function') {
            window.rightPanelManager.setFileStatus(status);
        }
    }, 500);

    /**
     * ✅ 代码质量改进：节流版本的渲染函数 - 限制UI更新频率（每250ms最多一次）
     * 防止每次事件都触发完整的DOM重渲染，提升性能
     */
    const throttledRenderResults = throttle(() => {
        // 允许在打字机效果（如右侧写代码）期间，左侧任务面板也能实时更新进度
        // 这解决了用户看到的“右侧写完很久左侧才出事件”的延迟感

        try {
            if (typeof window.renderResults === 'function') {
                window.renderResults();
            }
        } catch (error) {
            console.error('[NewAPI] Failed to render results:', error);
            // 不中断事件流，继续处理
        }
    }, RENDER_THROTTLE_MS);

    /**
     * 防抖版本的saveState（优化性能，避免频繁写入localStorage）
     * ✅ 修复：缩短防抖时间至100ms，减少数据丢失窗口
     */
    const debouncedSaveState = debounce(() => {
        if (typeof window.saveState === 'function') {
            window.saveState();
        }
    }, 100);

    /**
     * ✅ 修复：页面卸载前立即保存状态，防止数据丢失
     */
    window.addEventListener('beforeunload', () => {
        if (typeof window.saveState === 'function') {
            console.log('[NewAPI] Page unloading, saving state immediately');
            window.saveState();
        }
    });

    /**
     * 准备并切换 Session
     */
    /**
     * 准备或创建 session
     * @param {string} prompt - 用户输入的提示词
     * @param {boolean} isWelcome - 是否来自欢迎页
     * @returns {Promise<Object|null>} session 对象，如果创建失败则返回 null
     */
    async function prepareSession(prompt, isWelcome) {
        // 尝试从本地状态查找（如果已经点击过侧边栏切换）
        let existing = window.state.sessions.find(s => s.id === window.state.activeId);

        // ✅ 从已存在的 session 恢复 turnIndex
        if (existing && existing.turnIndex !== undefined) {
            window._turnIndex = existing.turnIndex;
            console.log('[NewAPI] Restored turnIndex from session:', window._turnIndex);
        }

        // 如果是新任务，或者当前没有活跃 ID，则创建
        if (!existing || isWelcome) {
            // ✅ 修复可维护性：使用DEFAULT_MODE常量替代硬编码
            const mode = window._currentMode || DEFAULT_MODE;
            const projectId = window.state.activeProjectId || null;  // 获取当前选中项目
            console.log('[NewAPI] Creating new session with mode:', mode, 'project:', projectId);

            let session;
            try {
                session = await window.apiClient.createSession(prompt, mode, '1.0.0', projectId);
                console.log('[NewAPI] Session created successfully:', session);

                if (!session || !session.id) {
                    throw new Error('Invalid session response from server');
                }
            } catch (err) {
                const safeMessage = getUserSafeErrorMessage(err, ERROR_MESSAGES.SESSION_CREATE_FAILED);
                console.error('[NewAPI] Failed to create session:', err);

                // 使用非阻塞的 UI 提示（如果存在 showNotification 函数）
                if (typeof window.showNotification === 'function') {
                    window.showNotification(safeMessage, 'error');
                } else {
                    alert(safeMessage);
                }
                return null;
            }

            existing = {
                id: session.id,
                title: session.title,
                prompt: prompt,
                response: '',
                phases: [],
                actions: [],          // ✅ 必须初始化，否则刷新后数据丢失
                orphanEvents: [],      // ✅ 必须初始化
                deliverables: [],
                status: 'active',
                mode: mode,
                turnIndex: 0,        // ✅ 修复：初始化为0，handleNewAPIConnection中会递增到1
                _version: 1,          // ✅ 添加版本号用于数据迁移
                _createdTime: Date.now()  // ✅ 添加创建时间，用于宽限期判断
            };
            // ✅ 从 session 恢复 turnIndex
            window._turnIndex = existing.turnIndex || 0;
            window.state.sessions.unshift(existing);
            window.state.activeId = existing.id;  // ✅ 立即更新activeId，防止临时session被误删

            // ✅ 立即保存新创建的session，确保不会丢失
            if (typeof window.saveState === 'function') {
                console.log('[prepareSession] Saving new session to localStorage');
                window.saveState();
            }
        } else {
            // ✅ P0修复：追问场景 - 追加新的prompt到现有session
            //
            // 说明：
            // - 使用分隔符 '\n\n---\n\n' 追加prompt
            // - renderResults会根据分隔符split渲染多个query气泡
            // - turnIndex由handleNewAPIConnection负责递增，不要在这里修改！
            //
            const pSep = '\n\n---\n\n';

            // 验证prompt参数
            if (typeof prompt !== 'string' || prompt.trim().length === 0) {
                console.error('[NewAPI] Invalid prompt for follow-up:', typeof prompt);
                return existing;
            }

            // 追加prompt
            existing.prompt = existing.prompt ?
                existing.prompt + pSep + prompt :
                prompt;

            console.log('[NewAPI] Follow-up: appended prompt to session');
            console.log('[NewAPI] Updated prompt length:', existing.prompt.length);
            console.log('[NewAPI] Total prompts:', existing.prompt.split(pSep).length);

            // ✅ 保存更新后的session到localStorage
            if (typeof window.saveState === 'function') {
                window.saveState();
            }
        }
        return existing;
    }

    /**
     * 执行提交逻辑
     */
    async function executeSubmission(btn, isNewTask) {
        const isWelcome = btn.id === 'runStream-welcome';
        const primaryInput = document.getElementById(isWelcome ? 'prompt-welcome' : 'prompt');
        const secondaryInput = document.getElementById(isWelcome ? 'prompt' : 'prompt-welcome');

        const promptValue = (primaryInput?.value || secondaryInput?.value || '').trim();
        if (!promptValue) return;

        console.log('[NewAPI] Processing submission...', { isWelcome, promptLength: promptValue.length });

        try {
            // 准备 Session
            const s = await prepareSession(promptValue, isWelcome);

            // ✅ 立即切换到聊天界面，消除欢迎页 15s 延迟感
            forceChatMode();

            // ✅ 修复：检查 prepareSession 返回值
            if (!s) {
                console.error('[NewAPI] prepareSession returned null, aborting submission');
                btn.disabled = false;
                btn.innerHTML = '<span class="material-symbols-outlined !text-white dark:!text-black">arrow_upward</span>';
                return;
            }

            // ✅ 修复可维护性：使用DEFAULT_MODE常量替代硬编码
            const mode = s.mode || window._currentMode || DEFAULT_MODE;
            console.log(`[NewAPI] Connecting to events... (Mode: ${mode})`);

            // 使用 handleNewAPIConnection 处理完整的连接和事件流
            await handleNewAPIConnection(s, isNewTask);

            // 清空输入框
            if (primaryInput) primaryInput.value = '';
            if (secondaryInput) secondaryInput.value = '';
        } catch (err) {
            console.error('[NewAPI] Submission sequence failed:', err);
            const safeMessage = getUserSafeErrorMessage(err, ERROR_MESSAGES.SUBMISSION_FAILED);

            // 使用非阻塞的 UI 提示
            if (typeof window.showNotification === 'function') {
                window.showNotification(safeMessage, 'error');
            } else {
                alert(safeMessage);
            }

            const runBtn = document.getElementById('runStream');
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.innerHTML = '<span class="material-symbols-outlined !text-white dark:!text-black">arrow_upward</span>';
            }
        }
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

        // ✅ P1修复：网络重连时清理thinking消息
        // 防止旧的thinking消息残留
        if (s._isLoadingThinking) {
            console.log('[Status] Network reconnection, cleaning up thinking message');
            cleanupThinkingMessage(s);
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

                // ✅ 优化：使用防抖机制在关键事件后保存状态（避免频繁写入localStorage）
                const shouldSave = adapted.type === 'answer_chunk' ||
                    adapted.type === 'action' ||
                    adapted.type === 'phases_init' ||
                    adapted.type === 'phase_update' ||
                    (adapted.type === 'status' && (adapted.value === 'done' || adapted.value === 'completed'));

                if (shouldSave) {
                    debouncedSaveState();
                }

                // ✅ 代码质量改进：使用节流版本减少DOM更新频率
                throttledRenderResults();

                // 检查是否完成
                if (adapted.type === 'status' && (adapted.value === 'done' || adapted.value === 'completed')) {
                    if (stopBtn) stopBtn.classList.add('hidden');
                    if (runBtn) runBtn.classList.remove('hidden');

                    // ✅ 修复C7: 子会话完成清理 - 防止内存泄漏
                    // 当子会话完成时，延迟清理资源（给用户查看历史事件的时间）
                    if (adapted._isFromChildSession) {
                        const childSessionId = adapted._childSessionId;
                        console.log(`[ChildSession] ✅ Child session completed: ${childSessionId}`);

                        // 延迟清理：给用户时间查看子会话的历史事件
                        // 防止频繁创建子会话导致内存泄漏
                        setTimeout(() => {
                            console.log(`[ChildSession] 🧹 Cleaning up completed child session: ${childSessionId}`);

                            // 取消子会话的SSE订阅
                            if (window.ChildSessionManager) {
                                window.ChildSessionManager.unsubscribeFromChildSession(childSessionId);
                            }

                            // 清理深度追踪
                            eventDepthMap.delete(childSessionId);

                            console.log(`[ChildSession] ✅ Cleanup complete for: ${childSessionId}`);
                        }, CHILD_SESSION_CLEANUP_DELAY_MS);
                    }
                    
                    // ✅ P0修复：在任务完成时同步turnIndex状态到session对象
                    // 这确保了window._turnIndex的值被正确保存到session中
                    // 然后通过saveState()持久化到localStorage
                    if (s && window._turnIndex) {
                        s.turnIndex = window._turnIndex;
                        s._lastPromptCount = s._lastPromptCount || 0;
                        console.log('[NewAPI] 💾 Saving turnIndex state on completion:', {
                            turnIndex: s.turnIndex,
                            _lastPromptCount: s._lastPromptCount
                        });
                    }
                }
            },
            (err) => {
                console.error('[NewAPI] SSE Stream Error:', err);
                if (stopBtn) stopBtn.classList.add('hidden');
                if (runBtn) runBtn.classList.remove('hidden');
            }
        );

        // ✅ v=38.4.23修复：正确处理多轮对话的turnIndex递增
        // 问题描述：追问时turnIndex不递增，导致所有文件的turn_index都是1
        // 根本原因：isNewSubmission只表示"是否新任务"，不表示"是否新轮次"
        // 解决方案：使用prompt数量检测新轮次，不依赖isNewSubmission

        const pSep = '\n\n---\n\n';
        const promptCount = (s.prompt || '').split(pSep).length;

        // ✅ 从session恢复turnIndex（处理页面刷新场景）
        if (s && s.turnIndex && (!window._turnIndex || window._turnIndex < s.turnIndex)) {
            window._turnIndex = s.turnIndex;
            console.log('[NewAPI] Restored turnIndex from session:', window._turnIndex);
        }

        // 初始化计数器（持久化到session）
        s._lastPromptCount = s._lastPromptCount || 0;

        // ✅ 检测新轮次：prompt数量增加
        if (promptCount > s._lastPromptCount) {
            window._turnIndex = (window._turnIndex || 0) + 1;
            s.turnIndex = window._turnIndex;
            s._lastPromptCount = promptCount;

            console.log('[NewAPI] 🔄 New turn detected:', {
                turnIndex: window._turnIndex,
                promptCount: promptCount,
                lastPromptCount: s._lastPromptCount - 1,
                isNewSubmission: isNewSubmission
            });
        } else {
            console.log('[NewAPI] 📝 Existing turn:', {
                turnIndex: window._turnIndex,
                promptCount: promptCount,
                isNewSubmission: isNewSubmission
            });
        }

        // ✅ 总是发送消息到后端（无论是新任务还是追问）
        const currentPrompt = s.prompt.split(pSep).pop();
        console.log('[NewAPI] 📤 Sending message (Mode:', window._currentMode, ', Turn:', window._turnIndex, ', Prompt length:', currentPrompt.length, ')');
        await window.apiClient.sendTextMessage(s.id, currentPrompt, { mode: window._currentMode });


        // 重新同步 UI 状态
        if (window.state.activeId !== s.id) {
            window.state.activeId = s.id;
        }

        if (typeof window.renderAll === 'function') {
            window.renderAll();
        }
    }

    // ========================================================================
    // 子会话自动监听管理器 (V1.0)
    // ========================================================================

    /**
     * 子会话管理器 - 负责跟踪和管理子代理session的生命周期
     *
     * 设计原则：
     * 1. Parse, Don't Validate: 在边界处解析子session ID，内部使用可信状态
     * 2. Early Exit: 所有边界检查在函数顶部处理
     * 3. Atomic Predictability: 每个函数职责单一，行为可预测
     */
    const ChildSessionManager = (function () {
        // 核心数据结构
        const childSessions = new Map(); // mainSessionId -> Set<childSessionId>
        const eventSources = new Map();  // childSessionId -> EventSource
        const mainSessions = new Map();  // childSessionId -> mainSessionId (反向查找)

        /**
         * 解析task工具输出中的子session ID
         * @param {string} output - task工具的output字符串，格式: "task_id: ses_xxx\n\n..."
         * @returns {string|null} 子session ID（格式: ses_xxx）或null（如果解析失败）
         * @example
         *   parseChildSessionId("task_id: ses_abc123\n\n...") // "ses_abc123"
         *   parseChildSessionId("invalid output") // null
         */
        function parseChildSessionId(output) {
            // Early Exit: 无效输入
            if (!output || typeof output !== 'string') {
                return null;
            }

            // Parse, Don't Validate: 使用常量解析子session ID
            const match = output.match(TASK_ID_PATTERN);
            return match ? match[1] : null;
        }

        /**
         * 检查是否已订阅子会话
         * @param {string} mainSessionId - 主session ID
         * @param {string} childSessionId - 子session ID
         * @returns {boolean}
         */
        function isSubscribed(mainSessionId, childSessionId) {
            const children = childSessions.get(mainSessionId);
            return children ? children.has(childSessionId) : false;
        }

        /**
         * 添加子会话订阅
         * @param {string} mainSessionId - 主session ID
         * @param {string} childSessionId - 子session ID
         */
        function addChildSession(mainSessionId, childSessionId) {
            // Parse, Don't Validate: 创建双向映射，确保数据一致性
            if (!childSessions.has(mainSessionId)) {
                childSessions.set(mainSessionId, new Set());
            }
            childSessions.get(mainSessionId).add(childSessionId);
            mainSessions.set(childSessionId, mainSessionId);

            console.log(`[ChildSession] Registered: ${childSessionId} <- ${mainSessionId}`);
        }

        /**
         * 移除子会话订阅
         * @param {string} childSessionId - 子session ID
         */
        function removeChildSession(childSessionId) {
            const mainSessionId = mainSessions.get(childSessionId);
            if (mainSessionId) {
                const children = childSessions.get(mainSessionId);
                if (children) {
                    children.delete(childSessionId);
                }
                mainSessions.delete(childSessionId);
                console.log(`[ChildSession] Unregistered: ${childSessionId} from ${mainSessionId}`);
            }
        }

        /**
         * 订阅子会话的SSE事件流
         * @param {string} mainSessionId - 主会话ID
         * @param {string} childSessionId - 子会话ID
         * @param {Function} onChildEvent - 子会话事件回调函数 (mainSession, childEvent) => void
         * @returns {void}
         * @description
         *   自动订阅子会话的事件流，并将事件适配到主会话上下文。
         *   如果已经订阅过，则跳过重复订阅。
         *   事件会标记为来自子会话（_isFromChildSession: true）。
         */
        function subscribeToChildSession(mainSessionId, childSessionId, onChildEvent) {
            // Early Exit: 防止重复订阅
            if (isSubscribed(mainSessionId, childSessionId)) {
                console.log(`[ChildSession] Already subscribed: ${childSessionId}`);
                return;
            }

            console.log(`[ChildSession] Subscribing to: ${childSessionId}`);

            // 创建子会话的事件处理器
            const eventSource = window.apiClient.subscribeToEvents(
                childSessionId,
                (newEvent) => {
                    // Parse, Don't Validate: 适配时保持主session上下文
                    const mainSession = window.state.sessions.find(s => s.id === mainSessionId);
                    if (!mainSession) {
                        console.warn(`[ChildSession] Main session not found: ${mainSessionId}`);
                        return;
                    }

                    // 标记事件来源为子会话
                    const adapted = window.EventAdapter?.adaptEvent(newEvent, mainSession);
                    if (!adapted) return;

                    // 添加子会话上下文信息
                    adapted._childSessionId = childSessionId;
                    adapted._isFromChildSession = true;

                    // 调用回调处理事件
                    onChildEvent(mainSession, adapted);
                },
                (error) => {
                    console.error(`[ChildSession] SSE error for ${childSessionId}:`, error);
                    // 发生错误时清理订阅
                    unsubscribeFromChildSession(childSessionId);
                }
            );

            // 保存EventSource以便后续清理
            eventSources.set(childSessionId, eventSource);
            addChildSession(mainSessionId, childSessionId);
        }

        /**
         * 取消订阅子会话
         * @param {string} childSessionId - 子会话ID
         * @returns {void}
         * @description
         *   关闭子会话的SSE连接，并清理相关订阅记录。
         *   如果子会话不存在订阅，则静默忽略。
         */
        function unsubscribeFromChildSession(childSessionId) {
            const eventSource = eventSources.get(childSessionId);
            if (eventSource) {
                eventSource.close();
                eventSources.delete(childSessionId);
                console.log(`[ChildSession] Unsubscribed: ${childSessionId}`);
            }
            removeChildSession(childSessionId);
        }

        /**
         * 取消主会话的所有子会话订阅
         * @param {string} mainSessionId - 主session ID
         */
        function unsubscribeAllFromMain(mainSessionId) {
            const children = childSessions.get(mainSessionId);
            if (children) {
                children.forEach(childId => {
                    unsubscribeFromChildSession(childId);
                });
                childSessions.delete(mainSessionId);
                console.log(`[ChildSession] Unsubscribed all children of: ${mainSessionId}`);
            }
        }

        /**
         * 获取主会话的所有子会话ID
         * @param {string} mainSessionId - 主session ID
         * @returns {string[]}
         */
        function getChildSessions(mainSessionId) {
            const children = childSessions.get(mainSessionId);
            return children ? Array.from(children) : [];
        }

        /**
         * 检查会话是否为子会话
         * @param {string} sessionId - 会话ID
         * @returns {boolean}
         */
        function isChildSession(sessionId) {
            return mainSessions.has(sessionId);
        }

        /**
         * 获取子会话的主会话ID
         * @param {string} childSessionId - 子会话ID
         * @returns {string|null}
         */
        function getMainSessionId(childSessionId) {
            return mainSessions.get(childSessionId) || null;
        }

        // 公共API
        return {
            subscribeToChildSession,
            unsubscribeFromChildSession,
            unsubscribeAllFromMain,
            parseChildSessionId,
            getChildSessions,
            isChildSession,
            getMainSessionId
        };
    })();

    // ✅ 修复C6: 防止processEvent递归调用导致栈溢出
    // 添加最大递归深度限制，防止多层嵌套子会话导致栈溢出
    const MAX_EVENT_DEPTH = 10; // 最大允许10层嵌套
    const eventDepthMap = new Map(); // 追踪每个会话的事件深度

    function processEvent(s, adapted, depth = 0) {
        // ✅ 添加错误边界：确保任何事件处理异常都不会中断整个数据流
        try {
            // ====================================================================
            // 🔴 CRITICAL FIX: 递归深度检查
            // Early Exit: 防止过深的递归导致栈溢出
            // ====================================================================
            if (depth > MAX_EVENT_DEPTH) {
                console.error(`[processEvent] ❌ CRITICAL: Max recursion depth (${MAX_EVENT_DEPTH}) reached!`);
                console.error(`[processEvent] Potential infinite loop in session: ${s.id}`);
                console.error(`[processEvent] Current event type: ${adapted.type}`);
                return; // 立即返回，防止栈溢出
            }

            // 记录当前深度
            eventDepthMap.set(s.id, depth);

            // ====================================================================
            // 子会话事件处理 - 检测并自动订阅子session
            // ====================================================================
            if (adapted.data && adapted.data.tool_name === 'task') {
                console.log('[ChildSession] Detected task tool event');

                // Parse, Don't Validate: 在边界处解析子session ID
                const output = adapted.data.output || '';
                const childSessionId = ChildSessionManager.parseChildSessionId(output);

                if (childSessionId) {
                    console.log(`[ChildSession] Found child session: ${childSessionId}`);

                    // Early Exit: 避免重复订阅
                    if (!ChildSessionManager.isSubscribed(s.id, childSessionId)) {
                        // ✅ 修复C6: 传递depth + 1，追踪递归深度
                        console.log(`[ChildSession] Current depth: ${depth}, subscribing to child at depth: ${depth + 1}`);

                        // 订阅子会话事件流
                        ChildSessionManager.subscribeToChildSession(
                            s.id,
                            childSessionId,
                            (mainSession, childEvent) => {
                                // 子会话事件回调 - 路由到主会话的processEvent
                                console.log(`[ChildSession] Routing event from ${childSessionId} to ${mainSession.id} (depth: ${depth + 1})`);
                                processEvent(mainSession, childEvent, depth + 1); // ✅ 传递递增的深度

                                // 保存状态
                                debouncedSaveState();

                                // ✅ 代码质量改进：使用节流版本减少DOM更新频率
                                throttledRenderResults();
                            }
                        );
                    }
                } else {
                    console.warn('[ChildSession] Failed to parse child session ID from task output:', output);
                }
            }

            // ====================================================================
            // 原有事件处理逻辑
            // ====================================================================
            // 处理文件预览事件 - 更新右侧文件面板（带打字机效果）
            if (adapted.type === 'file_preview_start') {
                console.log('[NewAPI] File preview start:', adapted.file_path);

                if (!adapted.file_path) {
                    console.error('[NewAPI] preview_start missing file_path:', adapted);
                    return;
                }

                TypingEffectManager.start(`file_preview_start: ${adapted.file_path}`);

                // 显示文件编辑器
                if (window.rightPanelManager && typeof window.rightPanelManager.showFileEditor === 'function') {
                    window.rightPanelManager.showFileEditor(adapted.file_path, '');
                }
                return;
            }

            if (adapted.type === 'file_preview_delta') {
                // ✅ 修复3：添加delta数据验证
                if (!adapted.delta) {
                    console.error('[NewAPI] file_preview_delta missing delta:', adapted);
                    return;
                }

                // delta 是对象格式: {type: "insert", position: i, content: char}
                const deltaContent = adapted.delta?.content !== undefined ? String(adapted.delta.content) : '';

                // ✅ 修复3：使用节流版本更新UI状态，限制DOM更新频率（每500ms最多一次）
                throttledSetFileStatus('正在写入...');

                // 使用打字机效果追加内容
                if (window.rightPanelManager && typeof window.rightPanelManager.typeAppendContent === 'function') {
                    window.rightPanelManager.typeAppendContent(deltaContent);
                } else if (window.rightPanelManager && typeof window.rightPanelManager.appendFileContent === 'function') {
                    // 降级：直接追加（无打字机效果）
                    window.rightPanelManager.appendFileContent(deltaContent);
                }
                return;
            }

            if (adapted.type === 'file_preview_end') {
                console.log('[NewAPI] File preview end:', adapted.file_path);

                TypingEffectManager.end(`file_preview_end: ${adapted.file_path}`);

                // 更新状态为完成
                if (window.rightPanelManager && typeof window.rightPanelManager.setFileStatus === 'function') {
                    window.rightPanelManager.setFileStatus('完成');
                }

                // ✅ v=35修复：移除renderResults()调用，避免无限循环
                // 问题：file_preview_end → renderResults() → 重新渲染面板 → 触发预览 → file_preview_end → 循环
                // 解决：文件预览结束不需要重新渲染整个面板，右侧面板已独立更新
                console.log('[NewAPI] File preview end - skipping renderResults to prevent infinite loop');

                return;
            }

            // ✅ 修复：处理文件生成事件 - 更新文件列表
            if (adapted.type === 'file_generated') {
                console.log('[NewAPI] File generated:', adapted.file.path);

                // 更新文件列表管理器
                if (window.filesManager && typeof window.filesManager.addFile === 'function') {
                    window.filesManager.addFile(adapted.file);
                }

                // 可选：也在右侧面板显示文件生成信息
                const fileInfo = `文件: ${adapted.file.name}\n路径: ${adapted.file.path}\n类型: ${adapted.file.type}`;
                if (window.rightPanelManager && typeof window.rightPanelManager.showFileEditor === 'function') {
                    // 如果文件编辑器已打开，更新内容
                    // 否则不强制显示，避免打扰用户
                    console.log('[NewAPI] File info:', fileInfo);
                }

                // ✅ 修复：收集文件到deliverables
                if (adapted.file && adapted.file.path) {
                    addFileToDeliverables(s, adapted.file.path, 'file_generated');
                    console.log('[Deliverables] Added file from file_generated event:', adapted.file.path);
                }

                return;
            }

            // 处理时间轴事件 - 更新右侧文件面板
            if (adapted.type === 'timeline_event') {
                console.log('[NewAPI] Timeline event:', adapted);

                // 渲染timeline事件到右侧面板
                if (adapted.step) {
                    const step = adapted.step;
                    const action = step.action || step.action_type || 'unknown';
                    const path = step.path || step.file_path || '';

                    // ✅ 修复：收集文件到deliverables（在防抖检查之前）
                    if (path) {
                        addFileToDeliverables(s, path, 'timeline');
                        console.log('[Deliverables] Added file from timeline event:', path);
                    }

                    // ✅ v=29: 防止重复预览同一文件（2秒内只预览一次）
                    // ✅ v=30: 修复内存泄漏 - 添加LRU清理机制
                    if (path) {
                        const lastPreviewTime = _recentlyPreviewedFiles.get(path);
                        const now = Date.now();

                        // 检查是否在防抖窗口内
                        if (lastPreviewTime && now - lastPreviewTime < PREVIEW_DEBOUNCE_MS) {
                            console.log(`[NewAPI] Skipping duplicate preview for: ${path} (${now - lastPreviewTime}ms ago)`);
                            return;
                        }

                        // LRU清理：如果缓存已满，删除最旧的条目
                        if (_recentlyPreviewedFiles.size >= MAX_PREVIEW_CACHE_SIZE) {
                            const firstKey = _recentlyPreviewedFiles.keys().next().value;
                            if (firstKey) {
                                _recentlyPreviewedFiles.delete(firstKey);
                                console.log(`[NewAPI] LRU cleanup: removed ${firstKey} from preview cache`);
                            }
                        }

                        // 添加当前文件到缓存
                        _recentlyPreviewedFiles.set(path, now);
                    }

                    // 构建事件标题和内容
                    let title = `[${action}]`;
                    if (path) {
                        title += ` ${path}`;
                    } else if (step.tool_name) {
                        title += ` ${step.tool_name}`;
                    } else {
                        title += ' 事件';
                    }

                    let content = `Step ID: ${step.step_id}\n`;
                    content += `Action: ${action}\n`;
                    if (path) content += `Path: ${path}\n`;
                    if (step.timestamp) content += `Timestamp: ${step.timestamp}\n`;
                    if (step.tool_input) {
                        content += `Input: ${JSON.stringify(step.tool_input, null, 2)}\n`;
                    }

                    // 显示到右侧面板
                    if (window.rightPanelManager) {
                        if (typeof window.rightPanelManager.show === 'function') {
                            window.rightPanelManager.show();
                        }
                        if (typeof window.rightPanelManager.switchTab === 'function') {
                            window.rightPanelManager.switchTab('preview');
                        }
                        if (typeof window.rightPanelManager.showFileEditor === 'function') {
                            window.rightPanelManager.showFileEditor(title, content);
                        }
                    }

                    // 同时显示在console区域
                    if (typeof window.addSystemMessage === 'function') {
                        window.addSystemMessage(`[Timeline] ${title}`, 'info');
                    }

                    // 这样增强任务面板也能显示 timeline 事件
                    if (s.currentPhase && s.phases) {
                        const currentPhase = s.phases.find(p => p.id === s.currentPhase);
                        if (currentPhase) {
                            if (!currentPhase.events) currentPhase.events = [];
                            currentPhase.events.push({
                                type: 'timeline_event',
                                title: title,
                                content: content,
                                step: step,
                                timestamp: Date.now()
                            });
                            console.log('[NewAPI] Associated timeline_event to phase:', currentPhase.id);
                        }
                    }
                }

                return;
            }

            if (adapted.type === 'answer_chunk') {
                const text = adapted.text || '';
                const appended = appendAnswerChunk(s, text);
                if (appended) {
                    s._hasAnswerChunk = true;
                    s._usingThoughtAsAnswer = false;
                }
            } else if (adapted.type === 'phases_init') {
                // 处理阶段初始化
                const currentTurnIndex = window._turnIndex || 0;

                // ✅ P0修复：追问时强制创建新phase对象，不复用旧phase
                // 判断是否是新对话轮次（通过比较prompt数量和现有phases的最大turn_index）
                const pSep = '\n\n---\n\n';
                const promptCount = (s.prompt || '').split(pSep).length;
                const maxExistingTurnIndex = s.phases && s.phases.length > 0
                    ? Math.max(...s.phases.map(p => parseInt(p.turn_index, 10) || 0))
                    : 0;

                const isNewTurn = promptCount > maxExistingTurnIndex;

                console.log('[phases_init] Debug:', {
                    promptCount,
                    maxExistingTurnIndex,
                    currentTurnIndex,
                    isNewTurn,
                    phasesCount: adapted.phases?.length
                });

                const newPhases = (adapted.phases || []).map(p => {
                    // ✅ P0修复v3：新轮次时创建独立的phase对象，不复用旧phase
                    if (isNewTurn) {
                        // ✅ 新轮次：创建完全独立的phase对象
                        // 使用后端返回的数据，但确保是新的对象引用
                        return {
                            ...p,
                            events: [],
                            turn_index: currentTurnIndex,
                            // ✅ 添加唯一标识符，确保不同轮次的phase不会互相覆盖
                            _uniqueId: `${p.id}_turn${currentTurnIndex}`
                        };
                    }

                    // 复用旧phase（保持兼容性）
                    const existingPhase = s.phases?.find(sp => sp.id === p.id);
                    return {
                        ...p,
                        events: existingPhase?.events || [],
                        turn_index: existingPhase?.turn_index ?? currentTurnIndex // 关联到当前对话轮次
                    };
                });


                // ✅ P0修复v3：使用复合键（id + turn_index）来区分不同轮次的phase
                // 防止相同ID的phase在不同轮次互相覆盖
                const phaseMap = new Map();

                // 先将现有phases放入Map，使用复合键
                s.phases?.forEach(p => {
                    const phaseTurn = parseInt(p.turn_index, 10);
                    const key = p._uniqueId || `${p.id}_turn${phaseTurn}`;
                    phaseMap.set(key, p);
                });

                // 将新phases放入Map
                newPhases.forEach(p => {
                    const phaseTurn = parseInt(p.turn_index, 10);
                    const key = p._uniqueId || `${p.id}_turn${phaseTurn}`;
                    const existing = phaseMap.get(key);

                    if (existing) {
                        // 只有在现有状态是 pending 或者新状态不是 pending 时才更新状态
                        if (p.status !== 'pending' || existing.status === 'pending') {
                            existing.status = p.status;
                        }
                        if (p.title) existing.title = p.title;
                        if (p.number !== undefined) existing.number = p.number;
                        if (p._uniqueId) existing._uniqueId = p._uniqueId;
                    } else {
                        phaseMap.set(key, p);
                    }
                });

                s.phases = Array.from(phaseMap.values()).sort((a, b) => {
                    // 先按turn_index排序，再按number排序
                    const turnA = parseInt(a.turn_index, 10) || 0;
                    const turnB = parseInt(b.turn_index, 10) || 0;
                    if (turnA !== turnB) return turnA - turnB;
                    return (a.number || 0) - (b.number || 0);
                });

                // ✅ P1修复：phases_init时清理thinking消息
                // 当真正的phase开始时，临时thinking消息应该被移除
                if (s._isLoadingThinking) {
                    console.log('[Status] phases_init received, cleaning up thinking message');
                    cleanupThinkingMessage(s);
                }

                // 自动清理临时的 Planning Phase
                const hasDynamicPhases = s.phases.some(p => p.id?.startsWith('phase_') && p.id !== 'phase_planning');
                if (hasDynamicPhases) {
                    s.phases = s.phases.filter(p => p.id !== 'phase_planning');
                }

                s.currentPhase = adapted.phases.find(p => p.status === 'active')?.id || s.currentPhase;

                // ✅ v=33: 强制更新phase UI - 即使在打字机效果期间也要显示loading状态和完成标签
                // 注意：直接调用renderResults而不是不存在的renderPhases函数
                try {
                    // 强制调用renderResults确保UI更新（不受打字机效果限制）
                    if (typeof window.renderResults === 'function') {
                        window.renderResults();
                    } else if (typeof window.renderEnhancedTaskPanel === 'function') {
                        // ✅ v=33: 修复DOM累积 - 清空旧内容后再追加新面板
                        try {
                            const s = state.sessions.find(x => x.id === state.activeId);
                            if (s) {
                                const convo = document.querySelector('#chat-messages');
                                if (convo) {
                                    // 清空旧内容，防止DOM节点累积
                                    convo.innerHTML = '';
                                    const panel = window.renderEnhancedTaskPanel(s);
                                    convo.appendChild(panel);
                                    console.log('[NewAPI] Fallback: Used renderEnhancedTaskPanel');
                                }
                            }
                        } catch (fallbackError) {
                            console.error('[NewAPI] Fallback renderEnhancedTaskPanel failed:', fallbackError);
                            // 降级方案失败，至少不会中断事件流
                        }
                    }

                    console.log('[NewAPI] Phase UI updated for phases:', adapted.phases.map(p => `${p.id}:${p.status}`).join(', '));
                } catch (error) {
                    console.error('[NewAPI] Failed to render phases:', error);
                    // 不中断事件流，继续处理
                }
            } else if (adapted.type === 'deliverables') {
                s.deliverables = adapted.items || [];
            } else if (adapted.type === 'status' || (adapted.type === 'message_updated' && adapted.time?.completed)) {
                // ✅ P0修复：处理status thinking事件（显示开场白/思考中消息）
                const isThinking = adapted.status === 'thinking' || adapted.value === 'thinking';

                if (isThinking) {
                    console.log('[Status] Received thinking event for session:', s.id);

                    // ✅ P1修复：检测并忽略重复的thinking事件
                    if (s._isLoadingThinking) {
                        console.log('[Status] Duplicate thinking event detected, skipping display');
                        return;
                    }

                    // ✅ P1修复：清理旧的thinking消息（如果存在）
                    if (s._thinkingMessageId) {
                        cleanupThinkingMessage(s);
                    }

                    // ✅ P0修复：显示thinking消息（开场白/思考中）
                    // 使用后端传入的message，或使用默认值作为fallback
                    const thinkingContent = adapted.message || '正在分析任务并制定计划...';
                    const messageId = `thinking_${Date.now()}`;

                    const messageElement = window.addSystemMessage(thinkingContent, 'info', messageId);

                    // ✅ P1修复：设置状态标志和缓存引用
                    if (messageElement) {
                        s._isLoadingThinking = true;
                        s._thinkingMessageId = messageId;
                        s._thinkingMessageElement = messageElement;
                        s._thinkingTimeout = null;

                        // ✅ P1修复：15秒超时自动移除
                        s._thinkingTimeout = setTimeout(() => {
                            console.log('[Status] Thinking message timeout (15s), auto-removing');
                            cleanupThinkingMessage(s);
                        }, 15000);
                    } else {
                        console.error('[Status] Failed to create thinking message element');
                    }

                    // ✅ P1修复：不调用throttledRenderResults，避免触发节流
                    // thinking消息已经通过addSystemMessage显示，无需额外渲染
                    return;
                }

                const isError = adapted.value === 'error' || adapted.status === 'error';
                const isDone = adapted.value === 'done' || adapted.value === 'completed' || (adapted.type === 'message_updated' && adapted.time?.completed);

                if (isDone || isError) {
                    if (s.phases) {
                        s.phases.forEach(p => {
                            if (p.status === 'active' || p.status === 'pending') {
                                p.status = isError ? 'error' : 'completed';
                            }
                        });
                    }
                    s.status = isError ? 'error' : 'completed';
                    s.currentPhase = null;

                    const stopBtn = document.getElementById('stopStream');
                    const runBtn = document.getElementById('runStream');
                    if (stopBtn) stopBtn.classList.add('hidden');
                    if (runBtn) runBtn.classList.remove('hidden');

                    console.log(`[NewAPI] Task session ${isError ? 'failed' : 'completed'}, all phases cleaned up.`);
                }

                // ✅ v=33: 修复总结不显示 - 强制刷新UI确保总结可见（绕过节流）
                if (!isError) {
                    // 双重检查：防止标志位丢失或response已包含总结
                    const SUMMARY_MARKER = '**✅ 任务完成**';
                    const hasSummaryInResponse = s.response && s.response.includes(SUMMARY_MARKER);
                    const hasSummaryFlag = s._hasCompletionSummary;

                    // 只在两种情况都不存在时才添加总结
                    if (!hasSummaryInResponse && !hasSummaryFlag) {
                        // 计算任务统计信息
                        const totalActions = s.actions ? s.actions.length : 0;
                        const completedPhases = s.phases ? s.phases.filter(p => p.status === 'completed').length : 0;

                        // 添加总结到response末尾
                        const summary = `\n\n---\n\n${SUMMARY_MARKER}\n\n- 完成阶段：${completedPhases}个\n- 工具调用：${totalActions}次\n`;
                        s.response += summary;
                        s._hasCompletionSummary = true; // 设置标志位

                        console.log('[NewAPI] Task summary added:', summary.trim());

                        // 显示系统消息
                        if (typeof window.addSystemMessage === 'function') {
                            window.addSystemMessage(`✅ 任务完成 - 完成${completedPhases}个阶段，执行${totalActions}次工具调用`, 'success');
                        }

                        // Fallback: only if no answer chunks, use last thought at completion
                        if (!s._hasAnswerChunk && s._lastThoughtContent) {
                            console.warn('[NewAPI] Fallback: using last thought as answer on completion');
                            if (appendAnswerChunk(s, s._lastThoughtContent)) {
                                s._hasAnswerChunk = true;
                            }
                        }

                        // ✅ v=33: 强制刷新UI，绕过节流确保总结立即显示
                        try {
                            // 检查是否有原始的renderResults（非节流版本）
                            if (typeof window._originalRenderResults === 'function') {
                                window._originalRenderResults();
                                console.log('[NewAPI] UI refreshed with _originalRenderResults (no throttle)');
                            } else if (typeof window.renderResults === 'function') {
                                window.renderResults();
                                console.log('[NewAPI] UI refreshed with renderResults');
                            }
                            console.log('[NewAPI] UI refreshed to show summary');
                        } catch (error) {
                            console.error('[NewAPI] Failed to refresh UI after summary:', error);
                        }
                    } else {
                        if (hasSummaryInResponse && hasSummaryFlag) {
                            console.log('[NewAPI] Task summary already exists (both flag and response)');
                        } else if (hasSummaryInResponse) {
                            console.log('[NewAPI] Task summary exists in response but flag is missing, fixing flag');
                            s._hasCompletionSummary = true;
                            if (typeof window.saveState === 'function') {
                                window.saveState();
                            }
                        } else {
                            console.log('[NewAPI] Task summary flag exists but response missing summary, recreating...');
                            const totalActions = s.actions ? s.actions.length : 0;
                            const completedPhases = s.phases ? s.phases.filter(p => p.status === 'completed').length : 0;
                            const summary = `\n\n---\n\n${SUMMARY_MARKER}\n\n- 完成阶段：${completedPhases}个\n- 工具调用：${totalActions}次\n`;
                            s.response = (s.response || '') + summary;

                            // ✅ v=33: 重建总结后也要刷新UI（绕过节流）
                            try {
                                if (typeof window._originalRenderResults === 'function') {
                                    window._originalRenderResults();
                                } else if (typeof window.renderResults === 'function') {
                                    window.renderResults();
                                }
                            } catch (error) {
                                console.error('[NewAPI] Failed to refresh UI after recreating summary:', error);
                            }

                            if (typeof window.saveState === 'function') {
                                window.saveState();
                            }
                        }
                    }
                } else {
                    // 错误总结
                    if (typeof window.addSystemMessage === 'function') {
                        window.addSystemMessage('❌ 任务执行失败', 'error');
                    }
                }

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
                        events: [],
                        turn_index: window._turnIndex || 0 // ✅ v=38.4.12.1: 关联到当前轮次
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
                // ✅ 修复：更新 session 的 actions 和 orphanEvents 数组
                if (adapted.type === 'action') {
                    const actionEvent = {
                        type: 'action',
                        id: adapted.id || adapted.call_id,
                        data: adapted.data || {}
                    };

                    // 确保 actions 和 orphanEvents 数组存在
                    if (!s.actions) s.actions = [];
                    if (!s.orphanEvents) s.orphanEvents = [];

                    // 添加到数组
                    s.actions.push(actionEvent);
                    s.orphanEvents.push(actionEvent);

                    // 避免同一个事件被添加两次到 phase.events
                    // 通用处理器已经有完整的去重和更新逻辑（第1942-1961行）

                    console.log('[NewAPI] Added action to session:', actionEvent.data.tool_name, 'total actions:', s.actions.length);
                }

                        // 实时显示到右侧面板
                        if (window.rightPanelManager) {
                            const data = adapted.data || {};
                            const toolName = data.tool_name || adapted.tool || '';

                            // ✅ 诊断：追踪思考内容是否误入回复
                            if (DEBUG_CONFIG.ENABLE_THOUGHT_DIAGNOSTIC && adapted.type === 'thought') {
                                console.group('🔍 [THOUGHT DIAGNOSTIC]');
                                console.log('Thought type:', adapted.type);
                                console.log('Thought content:', adapted.content || adapted.message);
                                console.log('Current response length:', s.response?.length || 0);
                                console.log('Response preview:', s.response?.slice(-100));  // ✅ 修复：使用 slice
                                console.log('Will be added to response?', !!(s.response && (s.response.includes(adapted.content) || s.response.includes(adapted.message))));
                                console.groupEnd();
                            }

                            // 确保右侧面板展开并切换到预览标签页
                    if (typeof window.rightPanelManager.show === 'function') {
                        window.rightPanelManager.show();
                    }
                    if (typeof window.rightPanelManager.switchTab === 'function') {
                        window.rightPanelManager.switchTab('preview');
                    }

                    // 判断事件类型并显示
                    if (adapted.type === 'thought') {
                        // 🔍 调试日志：追踪 thought 事件接收
                        if (window._DEBUG_THOUGHT_EVENTS) {
                            console.log('🔍 [SSE_HANDLER] Thought event received:', {
                                adapted: adapted,
                                session: s.id,
                                hasResponse: !!s.response,
                                responseLength: s.response?.length || 0
                            });
                        }
                        
                        // ✅ v=35: 思考内容立即显示在主聊天区域（XSS安全）
                        const content = adapted.content || adapted.data?.text || '';

                        // ✅ v=35: 改进日志 - 显示完整长度信息
                        const preview = content.length > 100
                            ? content.substring(0, 100) + `... (${content.length} chars)`
                            : content;
                        console.log('[NewAPI] Thought event received:', preview);

                        // ✅ Option C: 判断当前是否有active phase
                        if (s.currentPhase && s.phases) {
                            const currentPhase = s.phases.find(p => p.id === s.currentPhase);
                            if (currentPhase) {
                                // 添加到当前phase的events
                                if (!currentPhase.events) currentPhase.events = [];
                                currentPhase.events.push({
                                    type: 'thought',
                                    content: content,
                                    timestamp: Date.now()
                                });
                                console.log('[NewAPI] Thought added to phase.events, phase:', currentPhase.id);
                            } else {
                                // phase未找到，添加到orphanEvents（兜底）
                                if (!s.orphanEvents) s.orphanEvents = [];
                                s.orphanEvents.push({
                                    type: 'thought',
                                    content: content,
                                    timestamp: Date.now()
                                });
                                console.log('[NewAPI] Thought added to orphanEvents (phase not found)');
                            }
                        } else {
                            // 没有active phase，添加到thoughtEvents
                            if (!s.thoughtEvents) s.thoughtEvents = [];
                            s.thoughtEvents.push({
                                type: 'thought',
                                content: content,
                                timestamp: Date.now()
                            });
                            console.log('[NewAPI] Thought added to thoughtEvents (no active phase), total:', s.thoughtEvents.length);
                        }

                        // Store last thought for fallback use only if final answer is missing
                        if (content) {
                            s._lastThoughtContent = content;
                        }

                        // ✅ 触发渲染，确保thought实时显示
                        throttledRenderResults();

                        // 不在右侧面板显示，避免覆盖文件预览
                        return;
                    } else if (adapted.type === 'action') {
                        // 显示工具操作
                        const output = data.output || '';
                        const toolLower = toolName.toLowerCase();

                        if (toolLower === 'question') {
                            try {
                                enqueueQuestion(s, adapted.data || data);
                                console.log('[NewAPI] Queued question tool for session:', s.id);
                            } catch (err) {
                                console.error('[NewAPI] Failed to enqueue question:', err);
                            }
                            return;
                        }

                        if (toolLower === 'read') {
                            // read 工具 - 显示文件内容
                            const input = data.input || {};
                            const filePath = input.path || input.file_path || 'unknown';
                            console.log('[NewAPI] 显示read文件内容:', filePath);
                            window.rightPanelManager.showFileEditor(filePath, output);
                        } else if (toolLower === 'bash' || toolLower === 'grep') {
                            // bash/grep - 显示命令输出并保存到 deliverables
                            const input = data.input || {};
                            const command = input.command || input.pattern || '';
                            const title = command ? `${toolName}: ${command}` : `${toolName} 输出`;
                            const output = adapted.content || adapted.output || '';

                            // ✅ 验证输出内容，避免保存空命令
                            if (!output || output.trim() === '') {
                                console.log('[NewAPI] 命令输出为空，跳过保存:', title);
                                window.rightPanelManager.showFileEditor(title, output || '(无输出)');
                                return;
                            }

                            console.log('[NewAPI] 显示终端输出:', title);
                            window.rightPanelManager.showFileEditor(title, output);

                            // ✅ 将命令输出保存到 deliverables，刷新后可查看
                            if (!s.deliverables) s.deliverables = [];
                            
                            // 检查是否已存在（避免重复保存）
                            const exists = s.deliverables.some(d => {
                                if (typeof d === 'string') return d === title;
                                return d.name === title || d.path === title;
                            });

                            if (!exists) {
                                s.deliverables.push({
                                    name: title,
                                    content: output,
                                    type: 'command'
                                });
                                console.log('[NewAPI] 命令输出已保存到 deliverables:', title);
                                saveState();
                            }
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
                    s.phases = [{
                        id: 'phase_executing',
                        title: '🚀 任务执行中',
                        status: 'active',
                        events: [],
                        turn_index: window._turnIndex || 0 // ✅ v=38.4.12.1: 关联到当前轮次
                    }];
                    s.currentPhase = 'phase_executing';
                }

                const targetPhase = s.phases.find(p => p.id === s.currentPhase) || s.phases[s.phases.length - 1];
                if (targetPhase) {
                    if (!targetPhase.events) targetPhase.events = [];

                    const eventId = adapted.id || (adapted.data && (adapted.data.id || adapted.data.call_id)) || adapted.message_id;

                    // ✅ 修复：统一的事件更新逻辑（删除了冗余的去重检查）
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

                            // ✅ 修复：更新action事件时也收集文件
                            collectFileToDeliverables(s, adapted.data);
                        } else {
                            targetPhase.events[existingEventIndex] = adapted;

                            // ✅ 修复：更新其他类型事件时也尝试收集文件
                            if (adapted.type === 'action' && adapted.data) {
                                collectFileToDeliverables(s, adapted.data);
                            }
                        }
                    } else {
                        // 只有在新事件时才追加
                        // ✅ 方案A修复：添加timestamp确保排序正确
                        if (!adapted.timestamp) {
                            adapted.timestamp = adapted.time || Date.now();
                        }
                        targetPhase.events.push(adapted);

                        // 文件收集：如果是write/edit/file_editor工具，将文件添加到deliverables
                        if (adapted.type === 'action' && adapted.data) {
                            collectFileToDeliverables(s, adapted.data);
                        }
                    }
                }
            }
        } catch (error) {
            // ✅ 修复C5: 错误处理 - 标记session可能处于不一致状态
            console.error('[processEvent] Error processing event:', adapted.type, error);
            console.error('[processEvent] Event data:', adapted);
            console.error('[processEvent] Stack trace:', error.stack);

            // 标记session有处理错误
            s._hasProcessingError = true;
            s._lastError = {
                type: adapted.type,
                message: error.message,
                timestamp: Date.now()
            };

            // 确保至少保存当前状态
            if (typeof window.saveState === 'function') {
                try {
                    window.saveState();
                    console.log('[processEvent] Emergency save completed (session may be inconsistent)');
                } catch (saveError) {
                    console.error('[processEvent] Emergency save failed:', saveError);
                }
            }

            // 显示用户警告
            console.warn('[processEvent] Some data may be inconsistent for session:', s.id);
        }
    }

    // === P1修复3：通用文件收集函数（支持多种事件格式） ===
    function addFileToDeliverables(session, filePath, source = 'unknown') {
        if (!filePath) {
            return;
        }

        if (!session.deliverables) session.deliverables = [];

        // ✅ v=38.4.22优化：检查文件是否已存在（兼容新旧格式）
        const exists = session.deliverables.some(d => {
            const dPath = typeof d === 'string' ? d : (d.name || d.path);
            return dPath === filePath;
        });

        if (!exists) {
            // ✅ v=38.4.22优化：存储为对象格式，包含turn_index信息
            // 这样可以按轮次过滤交付物，解决追问时交付物位置混乱的问题
            session.deliverables.push({
                path: filePath,
                turn_index: window._turnIndex || 1,
                timestamp: Date.now()
            });
            console.log('[Deliverables] Added file:', filePath, 'turn:', window._turnIndex || 1);
        }
    }

    // === P0-2修复：文件收集辅助函数（消除重复代码） ===
    function collectFileToDeliverables(session, actionData) {
        const toolName = actionData.tool_name || actionData.tool || '';
        const toolLower = toolName.toLowerCase();

        if (toolLower === 'write' || toolLower === 'edit' || toolLower === 'file_editor') {
            const input = actionData.input || {};
            const filePath = input.path || input.file_path || input.file;

            if (filePath) {
                addFileToDeliverables(session, filePath, 'action');
            }
        }
    }

    // 加载会话的完整timeline
    async function loadSessionTimeline(sessionId) {
        try {
            console.log(`[History] Loading timeline for session: ${sessionId}`);

            const response = await fetch(`/opencode/session/${sessionId}/timeline`);
            if (!response.ok) {
                console.error(`[History] Failed to load timeline: ${response.status}`);
                return;
            }

            const data = await response.json();
            const timeline = data.timeline || [];

            console.log(`[History] Loaded ${timeline.length} timeline events`);

            // 渲染每个timeline事件
            timeline.forEach(step => {
                const adapted = {
                    type: 'timeline_event',
                    step: step,
                    id: step.step_id
                };

                // ✅ 修复：sessions是数组，使用find查找
                const session = window.state.sessions ?
                    window.state.sessions.find(s => s.id === sessionId) : null;
                if (session) {
                    processEvent(session, adapted);
                }
            });

            console.log(`[History] Timeline rendering complete for session: ${sessionId}`);

        } catch (error) {
            console.error(`[History] Error loading timeline:`, error);
        }
    }

    // 增强历史记录点击处理
    async function handleHistorySessionClick(sessionId) {
        console.log(`[History] Loading session: ${sessionId}`);

        try {
            const response = await fetch(`/opencode/session/${sessionId}/messages`);
            if (!response.ok) {
                throw new Error(`Failed to load session: ${response.status}`);
            }

            const data = await response.json();

            // ✅ 修复：sessions是数组，不是对象
            if (!window.state.sessions) {
                window.state.sessions = [];
            }

            // 查找或创建session
            let s = window.state.sessions.find(sess => sess.id === sessionId);
            if (!s) {
                s = {
                    id: sessionId,
                    phases: [],
                    actions: [],
                    orphanEvents: [],
                    deliverables: [],
                    currentPhase: null,
                    prompt: '',
                    response: ''
                };
                window.state.sessions.push(s);
            }

            if (data.messages && Array.isArray(data.messages)) {
                data.messages.forEach(msg => {
                    const info = msg.info || {};
                    const parts = msg.parts || [];

                    parts.forEach(part => {
                        let adapted;
                        if (part.type === 'text') {
                            adapted = {
                                type: info.role === 'user' ? 'user_message' : 'text',
                                content: part.content.text || '',
                                id: info.id
                            };
                            processEvent(s, adapted);
                        } else if (part.type === 'tool') {
                            const content = part.content;
                            adapted = {
                                type: 'action',
                                data: {
                                    tool_name: content.tool,
                                    id: content.call_id,
                                    input: content.tool_input
                                },
                                id: content.call_id
                            };
                            processEvent(s, adapted);
                        }
                    });
                });
            }

            await loadSessionTimeline(sessionId);

            console.log(`[History] Session loaded complete: ${sessionId}`);

        } catch (error) {
            console.error(`[History] Error loading session:`, error);
        }
    }

    init();

    // 暴露函数到全局作用域
    window.loadSessionTimeline = loadSessionTimeline;
    window.handleHistorySessionClick = handleHistorySessionClick;
    window.ChildSessionManager = ChildSessionManager;

    // ✅ 修复 UI 提交流程：暴露关键函数到全局作用域
    // handleGlobalClick 需要调用这些函数，必须在全局作用域可访问
    window.prepareSession = prepareSession;
    window.executeSubmission = executeSubmission;
    window.handleNewAPIConnection = handleNewAPIConnection;

    console.log('[NewAPI] Core functions exposed to global scope:', {
        prepareSession: typeof window.prepareSession,
        executeSubmission: typeof window.executeSubmission,
        handleNewAPIConnection: typeof window.handleNewAPIConnection
    });
    console.log('[NewAPI] ChildSessionManager exposed to global scope');
})();
