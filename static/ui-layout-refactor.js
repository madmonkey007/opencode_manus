/**
 * UI布局重构 - 新的交互逻辑
 * 1. 模式选择器在输入框左侧底部
 * 2. API端点切换器（Web/CLI）
 */

(function() {
    'use strict';

    // ============================================================
    // 1. 模式选择器逻辑（移到输入框底部）
    // ============================================================

    function initInputModeSelector() {
        const selector = document.getElementById('input-mode-selector');
        if (!selector) {
            console.warn('[UI] 输入框模式选择器未找到');
            return;
        }

        const DEFAULT_MODE = 'build';  // 默认Build模式

        // 设置默认模式
        selector.value = DEFAULT_MODE;
        window._currentMode = DEFAULT_MODE;

        // 绑定变化事件
        selector.addEventListener('change', (e) => {
            const mode = e.target.value;
            window._currentMode = mode;
            console.log('[UI] 模式切换到:', mode, '(', selector.options[selector.selectedIndex].text, ')');
        });

        console.log('[UI] 输入框模式选择器初始化完成，默认模式:', DEFAULT_MODE);
    }

    // ============================================================
    // 2. API端点切换器逻辑（Web/CLI）
    // ============================================================

    function initApiEndpointSelector() {
        const webBtn = document.getElementById('api-web-btn');
        const cliBtn = document.getElementById('api-cli-btn');

        if (!webBtn || !cliBtn) {
            console.warn('[UI] API端点切换器未找到');
            return;
        }

        // API端点配置
        const API_ENDPOINTS = {
            web: {
                url: 'http://127.0.0.1:8089',
                name: 'FastAPI Web应用',
                port: 8089,
                auth: false
            },
            cli: {
                url: 'http://127.0.0.1:4096',
                name: 'OpenCode Server CLI',
                port: 4096,
                auth: true,
                username: 'opencode',
                password: 'opencode-dev-2026'
            }
        };

        // 当前端点（默认Web）
        let currentEndpoint = 'web';
        window._currentApiEndpoint = API_ENDPOINTS.web;

        // 更新按钮状态
        function updateEndpointButtons(endpoint) {
            // 先移除两个按钮的所有状态类
            webBtn.classList.remove('bg-white', 'dark:bg-gray-700', 'shadow', 'text-gray-900', 'dark:text-white');
            cliBtn.classList.remove('bg-white', 'dark:bg-gray-700', 'shadow', 'text-gray-900', 'dark:text-white');

            // 添加基础未选中状态
            webBtn.classList.add('text-gray-600', 'dark:text-gray-400');
            cliBtn.classList.add('text-gray-600', 'dark:text-gray-400');

            // 为选中按钮添加选中样式
            if (endpoint === 'web') {
                webBtn.classList.remove('text-gray-600', 'dark:text-gray-400');
                webBtn.classList.add('bg-white', 'dark:bg-gray-700', 'shadow', 'text-gray-900', 'dark:text-white');
            } else {
                cliBtn.classList.remove('text-gray-600', 'dark:text-gray-400');
                cliBtn.classList.add('bg-white', 'dark:bg-gray-700', 'shadow', 'text-gray-900', 'dark:text-white');
            }
        }

        // 切换到Web端点
        webBtn.addEventListener('click', () => {
            currentEndpoint = 'web';
            window._currentApiEndpoint = API_ENDPOINTS.web;
            updateEndpointButtons('web');
            console.log('[UI] 切换到 Web API (8089):', API_ENDPOINTS.web.url);
            // 可以在这里添加通知或其他逻辑
        });

        // 切换到CLI端点
        cliBtn.addEventListener('click', () => {
            currentEndpoint = 'cli';
            window._currentApiEndpoint = API_ENDPOINTS.cli;
            updateEndpointButtons('cli');
            console.log('[UI] 切换到 CLI API (4096):', API_ENDPOINTS.cli.url);
            // 可以在这里添加通知或其他逻辑
        });

        // 初始化状态
        updateEndpointButtons('web');
        console.log('[UI] API端点切换器初始化完成，默认端点:', window._currentApiEndpoint.name);
    }

    // ============================================================
    // 3. 初始化
    // ============================================================

    function init() {
        console.log('[UI] 初始化新的UI布局...');

        // 等待DOM加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        // 初始化各个组件
        initInputModeSelector();
        initApiEndpointSelector();

        console.log('[UI] 新的UI布局初始化完成');
    }

    // 启动
    init();

})();
