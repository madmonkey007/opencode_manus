/**
 * Enhanced Code Preview Overlay - 增强版代码预览覆盖层
 *
 * 新增功能：
 * - 打字机效果优化（缓冲机制）
 * - 语法高亮支持
 * - Diff 视图（修改对比）
 * - 历史回溯功能
 */

// ✅ 修复4：UI字符串常量定义，避免魔法字符串
const UI_STRINGS = {
    STATUS_GENERATING: '正在生成...',
    STATUS_WRITING: '正在写入...',
    STATUS_COMPLETE: '完成',
    STATUS_ERROR: '错误',
    MODE_PLAN: 'Plan (分析)',
    MODE_BUILD: 'Build (开发)',
    MODE_RUN: 'Run (运行)',
    MODE_TASK: 'Task (任务)'
};

class EnhancedCodePreviewOverlay {
    constructor() {
        this.overlay = null;
        this.editorContainer = null;
        this.lineNumbersContainer = null;
        this.currentContent = '';
        this.previousContent = '';  // 用于 diff 视图
        this.currentStepId = null;
        this.currentFilePath = null;

        // 打字机缓冲
        this.deltaBuffer = [];
        this.bufferTimer = null;
        this.bufferFlushInterval = 100; // 每 100ms 刷新一次

        // 语法高亮
        this.highlightjs = null;
        this.language = 'plaintext';

        this.settings = {
            typingSpeed: 20,           // 打字速度 (字符/秒)
            autoScroll: true,          // 自动滚动
            showLineNumbers: true,     // 显示行号
            enableHighlight: true,     // 启用语法高亮
            enableDiff: false,         // 启用 diff 视图
            enableBuffer: true         // 启用缓冲机制
        };

        this.init();
    }

    async init() {
        await this.loadHighlightJS();
        this.createOverlay();
        this.bindEvents();
        this.startBufferFlush();
    }

    async loadHighlightJS() {
        // 加载 highlight.js
        if (typeof hljs !== 'undefined') {
            this.highlightjs = hljs;
            return;
        }

        return new Promise((resolve) => {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css';
            document.head.appendChild(link);

            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js';
            script.onload = () => {
                this.highlightjs = window.hljs;
                resolve();
            };
            script.onerror = () => {
                console.warn('[CodePreview] Failed to load highlight.js');
                resolve();
            };
            document.head.appendChild(script);
        });
    }

    createOverlay() {
        // 创建覆盖层容器
        const container = document.createElement('div');
        container.id = 'enhanced-code-preview-overlay';
        container.className = 'hidden fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-8';
        container.innerHTML = `
            <div class="bg-white dark:bg-zinc-900 w-full max-w-6xl h-full max-h-[90vh] flex flex-col rounded-2xl overflow-hidden shadow-2xl">
                <!-- 头部 -->
                <div class="px-6 py-4 border-b border-gray-200 dark:border-zinc-700 flex items-center justify-between bg-gray-50 dark:bg-zinc-800/50">
                    <div class="flex items-center gap-3">
                        <div class="w-3 h-3 rounded-full bg-red-500"></div>
                        <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
                        <div class="w-3 h-3 rounded-full bg-green-500"></div>
                        <span class="ml-4 text-sm font-medium text-gray-700 dark:text-gray-300" id="preview-filename">file.py</span>
                        <span class="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full" id="preview-action">WRITE</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="text-xs text-gray-500 dark:text-gray-400" id="preview-status">正在生成...</span>
                        <button class="close-preview p-2 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded-lg transition-colors">
                            <span class="material-symbols-outlined text-gray-600 dark:text-gray-400">close</span>
                        </button>
                    </div>
                </div>

                <!-- 工具栏 -->
                <div class="px-4 py-2 border-b border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-800/30 flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <button class="view-mode-btn active px-3 py-1.5 text-xs rounded-lg transition-colors" data-mode="normal">
                            <span class="material-symbols-outlined text-[14px] align-middle mr-1">code</span>
                            正常视图
                        </button>
                        <button class="view-mode-btn px-3 py-1.5 text-xs rounded-lg transition-colors" data-mode="diff">
                            <span class="material-symbols-outlined text-[14px] align-middle mr-1">compare</span>
                            Diff 视图
                        </button>
                    </div>
                    <div class="flex items-center gap-2">
                        <label class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                            <input type="checkbox" id="enable-highlight" ${this.settings.enableHighlight ? 'checked' : ''}>
                            语法高亮
                        </label>
                        <label class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                            <input type="checkbox" id="enable-buffer" ${this.settings.enableBuffer ? 'checked' : ''}>
                            缓冲优化
                        </label>
                    </div>
                </div>

                <!-- 编辑器区域 -->
                <div class="flex-1 overflow-hidden flex">
                    <!-- 行号 -->
                    <div class="w-12 bg-gray-100 dark:bg-zinc-800 border-r border-gray-200 dark:border-zinc-700 py-4 overflow-hidden" id="preview-line-numbers">
                    </div>

                    <!-- 代码内容 -->
                    <div class="flex-1 overflow-auto bg-white dark:bg-zinc-900 p-4 relative" id="preview-code-container">
                        <!-- 正常视图 -->
                        <pre id="preview-code-content" class="text-sm font-mono whitespace-pre-wrap break-words"></pre>
                        <!-- Diff 视图 -->
                        <div id="preview-diff-content" class="hidden text-sm font-mono whitespace-pre-wrap break-words"></div>
                    </div>
                </div>

                <!-- 底部状态栏 -->
                <div class="px-6 py-3 border-t border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-800/50 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <div class="flex items-center gap-4">
                        <span id="preview-position">第 1 行, 第 1 列</span>
                        <span id="preview-size">0 字符</span>
                        <span id="preview-buffer-status" class="hidden">缓冲: 0 字符</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <button class="preview-action-btn px-3 py-1.5 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-300 dark:hover:bg-zinc-600 rounded-lg transition-colors flex items-center gap-1.5" id="preview-history-btn">
                            <span class="material-symbols-outlined text-[14px]">history</span>
                            <span>查看历史</span>
                        </button>
                        <button class="preview-action-btn px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors flex items-center gap-1.5" id="preview-open-btn">
                            <span class="material-symbols-outlined text-[14px]">open_in_new</span>
                            <span>在新窗口打开</span>
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(container);
        this.overlay = container;
        this.editorContainer = container.querySelector('#preview-code-content');
        this.diffContainer = container.querySelector('#preview-diff-content');
        this.lineNumbersContainer = container.querySelector('#preview-line-numbers');
    }

    bindEvents() {
        // 关闭按钮
        this.overlay.querySelector('.close-preview').onclick = () => {
            this.hide();
        };

        // 点击背景关闭
        this.overlay.onclick = (e) => {
            if (e.target === this.overlay) {
                this.hide();
            }
        };

        // ESC 键关闭
        this.handleEscKey = (e) => {
            if (e.key === 'Escape' && !this.overlay.classList.contains('hidden')) {
                this.hide();
            }
        };
        document.addEventListener('keydown', this.handleEscKey);

        // 视图切换按钮
        this.overlay.querySelectorAll('.view-mode-btn').forEach(btn => {
            btn.onclick = () => {
                this.switchViewMode(btn.dataset.mode);
            };
        });

        // 设置切换
        this.overlay.querySelector('#enable-highlight').onchange = (e) => {
            this.settings.enableHighlight = e.target.checked;
            this.render();
        };

        this.overlay.querySelector('#enable-buffer').onchange = (e) => {
            this.settings.enableBuffer = e.target.checked;
        };

        // 查看历史按钮
        this.overlay.querySelector('#preview-history-btn').onclick = () => {
            this.showHistory();
        };

        // 在新窗口打开
        this.overlay.querySelector('#preview-open-btn').onclick = () => {
            this.openInNewWindow();
        };
    }

    show(filename, action) {
        this.overlay.classList.remove('hidden');

        // 更新头部信息
        this.overlay.querySelector('#preview-filename').textContent = filename || 'unknown';
        this.overlay.querySelector('#preview-action').textContent = (action || 'write').toUpperCase();
        this.overlay.querySelector('#preview-status').textContent = '正在生成...';

        // 检测语言
        this.language = this.detectLanguage(filename);

        // 重置内容
        this.currentContent = '';
        this.previousContent = '';
        this.editorContainer.textContent = '';
        this.diffContainer.innerHTML = '';
        this.editorContainer.classList.remove('hidden');
        this.diffContainer.classList.add('hidden');

        this.updateLineNumbers();
        this.updateStats();
    }

    hide() {
        this.overlay.classList.add('hidden');
        // 清空缓冲
        this.deltaBuffer = [];
    }

    detectLanguage(filename) {
        if (!filename) return 'plaintext';

        const ext = filename.split('.').pop().toLowerCase();
        const langMap = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'md': 'markdown',
            'sql': 'sql',
            'sh': 'bash',
            'yaml': 'yaml',
            'yml': 'yaml',
            'xml': 'xml',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'go': 'go',
            'rs': 'rust',
            'php': 'php',
            'rb': 'ruby'
        };

        return langMap[ext] || 'plaintext';
    }

    appendDelta(delta) {
        if (!this.settings.enableBuffer) {
            // 直接应用 delta
            this.applyDelta(delta);
        } else {
            // 添加到缓冲
            this.deltaBuffer.push(delta);
            this.updateBufferStatus();
        }
    }

    applyDelta(delta) {
        // 处理增量更新
        if (delta.type === 'insert') {
            this.currentContent += delta.content;
        } else if (delta.type === 'delete') {
            const length = delta.length || 1;
            this.currentContent = this.currentContent.slice(0, delta.position) +
                                  this.currentContent.slice(delta.position + length);
        } else if (delta.type === 'replace') {
            const oldLength = delta.old_content ? delta.old_content.length : 0;
            this.currentContent = this.currentContent.slice(0, delta.position) +
                                  delta.new_content +
                                  this.currentContent.slice(delta.position + oldLength);
        }

        this.render();
    }

    render() {
        // 应用语法高亮
        let content = this.currentContent;

        if (this.settings.enableHighlight && this.highlightjs) {
            try {
                const result = this.highlightjs.highlight(content, { language: this.language });
                this.editorContainer.innerHTML = result.value;
            } catch (e) {
                // 高亮失败，显示纯文本
                this.editorContainer.textContent = content;
            }
        } else {
            this.editorContainer.textContent = content;
        }

        this.updateLineNumbers();
        this.updateStats();

        // 自动滚动到底部
        if (this.settings.autoScroll) {
            this.editorContainer.parentElement.scrollTop = this.editorContainer.parentElement.scrollHeight;
        }
    }

    switchViewMode(mode) {
        const normalBtn = this.overlay.querySelector('.view-mode-btn[data-mode="normal"]');
        const diffBtn = this.overlay.querySelector('.view-mode-btn[data-mode="diff"]');

        if (mode === 'normal') {
            normalBtn.classList.add('active', 'bg-blue-500', 'text-white');
            diffBtn.classList.remove('active', 'bg-blue-500', 'text-white');
            this.editorContainer.classList.remove('hidden');
            this.diffContainer.classList.add('hidden');
        } else if (mode === 'diff') {
            diffBtn.classList.add('active', 'bg-blue-500', 'text-white');
            normalBtn.classList.remove('active', 'bg-blue-500', 'text-white');
            this.editorContainer.classList.add('hidden');
            this.diffContainer.classList.remove('hidden');
            this.renderDiff();
        }
    }

    renderDiff() {
        // 生成 diff HTML
        const oldLines = this.previousContent.split('\n');
        const newLines = this.currentContent.split('\n');

        let diffHtml = '';
        let maxLen = Math.max(oldLines.length, newLines.length);

        for (let i = 0; i < maxLen; i++) {
            const oldLine = oldLines[i] || '';
            const newLine = newLines[i] || '';

            if (oldLine === newLine) {
                // 未修改
                diffHtml += `<div class="flex"><div class="w-12 text-right pr-2 text-gray-500 bg-gray-50 dark:bg-zinc-800">${i + 1}</div><pre class="flex-1 px-2 text-gray-700 dark:text-gray-300">${this.escapeHtml(newLine) || ' '}</pre></div>`;
            } else {
                // 有修改
                if (!oldLine) {
                    // 新增行
                    diffHtml += `<div class="flex bg-green-50 dark:bg-green-900/20"><div class="w-12 text-right pr-2 text-green-600">+${i + 1}</div><pre class="flex-1 px-2 text-green-700 dark:text-green-400">+${this.escapeHtml(newLine)}</pre></div>`;
                } else if (!newLine) {
                    // 删除行
                    diffHtml += `<div class="flex bg-red-50 dark:bg-red-900/20"><div class="w-12 text-right pr-2 text-red-600">-${i + 1}</div><pre class="flex-1 px-2 text-red-700 dark:text-red-400">-${this.escapeHtml(oldLine)}</pre></div>`;
                } else {
                    // 修改行
                    diffHtml += `<div class="flex bg-yellow-50 dark:bg-yellow-900/20"><div class="w-12 text-right pr-2 text-yellow-600">~${i + 1}</div><pre class="flex-1 px-2 text-yellow-700 dark:text-yellow-400">`;
                    diffHtml += `<span class="line-through text-red-600">${this.escapeHtml(oldLine)}</span><br>`;
                    diffHtml += `<span class="text-green-600">+${this.escapeHtml(newLine)}</span>`;
                    diffHtml += `</pre></div>`;
                }
            }
        }

        this.diffContainer.innerHTML = diffHtml;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    startBufferFlush() {
        this.bufferTimer = setInterval(() => {
            if (this.deltaBuffer.length > 0) {
                // 批量处理缓冲的 deltas
                const deltas = [...this.deltaBuffer];
                this.deltaBuffer = [];

                for (const delta of deltas) {
                    this.applyDelta(delta);
                }

                this.updateBufferStatus();
            }
        }, this.bufferFlushInterval);
    }

    updateBufferStatus() {
        const statusEl = this.overlay.querySelector('#preview-buffer-status');
        if (this.deltaBuffer.length > 0) {
            statusEl.textContent = `缓冲: ${this.deltaBuffer.length} 个更新`;
            statusEl.classList.remove('hidden');
        } else {
            statusEl.classList.add('hidden');
        }
    }

    setContent(content, previousContent = null) {
        this.previousContent = previousContent || '';
        this.currentContent = content;
        this.render();
        this.updateLineNumbers();
        this.updateStats();
    }

    setStepId(stepId) {
        this.currentStepId = stepId;
    }

    setFilePath(filePath) {
        this.currentFilePath = filePath;
    }

    updateLineNumbers() {
        const lines = this.currentContent.split('\n').length;
        let lineNumbersHtml = '';

        for (let i = 1; i <= lines; i++) {
            lineNumbersHtml += `<div class="text-right pr-3 text-xs text-gray-400 dark:text-gray-600 font-mono">${i}</div>`;
        }

        this.lineNumbersContainer.innerHTML = lineNumbersHtml;
    }

    updateStats() {
        const charCount = this.currentContent.length;
        const lineCount = this.currentContent.split('\n').length;

        this.overlay.querySelector('#preview-size').textContent = `${charCount} 字符`;
        this.overlay.querySelector('#preview-position').textContent = `第 ${lineCount} 行`;
    }

    setStatus(status) {
        this.overlay.querySelector('#preview-status').textContent = status;
    }

    async showHistory() {
        if (!this.currentStepId || !this.currentFilePath) {
            alert('无法获取历史信息');
            return;
        }

        // 获取会话 ID
        const sessionId = window.state?.activeId;
        if (!sessionId) {
            alert('无法获取当前会话');
            return;
        }

        try {
            // 调用后端 API 获取文件历史
            const response = await fetch(`/opencode/get_file_history?session_id=${sessionId}&file_path=${encodeURIComponent(this.currentFilePath)}`);
            const data = await response.json();

            if (data.history && data.history.length > 0) {
                // 显示历史版本列表
                this.showHistoryDialog(data.history);
            } else {
                alert('该文件没有历史记录');
            }
        } catch (e) {
            console.error('[CodePreview] Failed to fetch file history:', e);
            alert('获取历史失败');
        }
    }

    showHistoryDialog(history) {
        // 创建历史对话框
        const dialog = document.createElement('div');
        dialog.className = 'fixed inset-0 z-[60] bg-black/50 flex items-center justify-center p-8';
        dialog.innerHTML = `
            <div class="bg-white dark:bg-zinc-900 w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl overflow-hidden shadow-2xl">
                <div class="px-6 py-4 border-b border-gray-200 dark:border-zinc-700 flex items-center justify-between bg-gray-50 dark:bg-zinc-800/50">
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">文件历史</span>
                    <button class="close-history p-2 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded-lg transition-colors">
                        <span class="material-symbols-outlined text-gray-600 dark:text-gray-400">close</span>
                    </button>
                </div>
                <div class="flex-1 overflow-auto p-4">
                    <div class="space-y-2">
                        ${history.map((item, index) => `
                            <div class="history-item p-3 rounded-lg border border-gray-200 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800 cursor-pointer transition-colors" data-index="${index}">
                                <div class="flex items-center justify-between">
                                    <div class="flex items-center gap-2">
                                        <span class="material-symbols-outlined text-[18px] ${item.operation === 'created' ? 'text-green-500' : 'text-blue-500'}">
                                            ${item.operation === 'created' ? 'add_circle' : 'edit'}
                                        </span>
                                        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">${item.operation === 'created' ? '创建' : '修改'}</span>
                                    </div>
                                    <span class="text-xs text-gray-500 dark:text-gray-400">${new Date(item.timestamp * 1000).toLocaleString()}</span>
                                </div>
                                <div class="mt-2 text-xs text-gray-600 dark:text-gray-400">
                                    步骤 ID: ${item.step_id}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        // 绑定事件
        dialog.querySelector('.close-history').onclick = () => dialog.remove();
        dialog.onclick = (e) => {
            if (e.target === dialog) dialog.remove();
        };

        // 点击历史项
        dialog.querySelectorAll('.history-item').forEach(item => {
            item.onclick = () => {
                const index = parseInt(item.dataset.index);
                const historyItem = history[index];
                this.loadHistoryVersion(historyItem);
                dialog.remove();
            };
        });

        document.body.appendChild(dialog);
    }

    async loadHistoryVersion(historyItem) {
        if (!this.currentStepId || !this.currentFilePath) {
            return;
        }

        const sessionId = window.state?.activeId;
        if (!sessionId) {
            return;
        }

        try {
            // 获取文件在该步骤的内容
            const response = await fetch(`/opencode/get_file_at_step?session_id=${sessionId}&file_path=${encodeURIComponent(this.currentFilePath)}&step_id=${historyItem.step_id}`);
            const data = await response.json();

            if (data.content !== undefined) {
                // 显示历史版本
                this.previousContent = this.currentContent; // 保存当前内容作为对比
                this.setContent(data.content);

                // 切换到 diff 视图
                this.switchViewMode('diff');

                // 更新状态
                this.setStatus(`查看历史版本: ${new Date(historyItem.timestamp * 1000).toLocaleString()}`);
            } else {
                alert('无法加载该版本');
            }
        } catch (e) {
            console.error('[CodePreview] Failed to load history version:', e);
            alert('加载失败');
        }
    }

    openInNewWindow() {
        const newWindow = window.open('', '_blank');
        newWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${this.currentFilePath || 'code preview'}</title>
                <style>
                    body {
                        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                        padding: 20px;
                        background: #1e1e1e;
                        color: #d4d4d4;
                    }
                    pre {
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }
                </style>
            </head>
            <body>
                <pre>${this.escapeHtml(this.currentContent)}</pre>
            </body>
            </html>
        `);
        newWindow.document.close();
    }

    destroy() {
        // 清理定时器
        if (this.bufferTimer) {
            clearInterval(this.bufferTimer);
        }

        // 清理事件监听
        document.removeEventListener('keydown', this.handleEscKey);
        if (this.overlay && this.overlay.parentNode) {
            this.overlay.parentNode.removeChild(this.overlay);
        }
    }
}

// 初始化并导出全局实例
let enhancedCodePreview;

function initEnhancedCodePreview() {
    enhancedCodePreview = new EnhancedCodePreviewOverlay();
    window.enhancedCodePreview = enhancedCodePreview;

    // 兼容旧的 API
    window.codePreviewOverlay = enhancedCodePreview;
}

// 在 DOMContentLoaded 时初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initEnhancedCodePreview);
} else {
    initEnhancedCodePreview();
}

// 导出初始化函数供外部调用
window.initEnhancedCodePreview = initEnhancedCodePreview;
