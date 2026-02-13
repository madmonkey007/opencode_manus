/**
 * Code Preview Overlay - 代码编辑器实时预览覆盖层
 * 显示打字机效果的代码生成预览
 */

class CodePreviewOverlay {
    constructor() {
        this.overlay = null;
        this.editorContainer = null;
        this.lineNumbersContainer = null;
        this.currentContent = '';
        this.currentStepId = null;
        this.settings = {
            typingSpeed: 20,           // 打字速度 (字符/秒)
            autoScroll: true,          // 自动滚动
            showLineNumbers: true      // 显示行号
        };

        this.init();
    }

    init() {
        this.createOverlay();
        this.bindEvents();
    }

    createOverlay() {
        // 创建覆盖层容器
        const container = document.createElement('div');
        container.id = 'code-preview-overlay';
        container.className = 'hidden fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-8';
        container.innerHTML = `
            <div class="bg-white dark:bg-zinc-900 w-full max-w-5xl h-full max-h-[85vh] flex flex-col rounded-2xl overflow-hidden shadow-2xl animate-fade-in">
                <!-- 头部 -->
                <div class="px-6 py-4 border-b border-gray-200 dark:border-zinc-700 flex items-center justify-between bg-gray-50 dark:bg-zinc-800/50">
                    <div class="flex items-center gap-3">
                        <div class="w-3 h-3 rounded-full bg-red-500"></div>
                        <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
                        <div class="w-3 h-3 rounded-full bg-green-500"></div>
                        <span class="ml-4 text-sm font-medium text-gray-700 dark:text-gray-300" id="preview-filename">file.py</span>
                        <span class="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full" id="preview-action">WRITE</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs text-gray-500 dark:text-gray-400" id="preview-status">正在生成...</span>
                        <button class="close-preview p-2 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded-lg transition-colors">
                            <span class="material-symbols-outlined text-gray-600 dark:text-gray-400">close</span>
                        </button>
                    </div>
                </div>

                <!-- 编辑器区域 -->
                <div class="flex-1 overflow-hidden flex">
                    <!-- 行号 -->
                    <div class="w-12 bg-gray-100 dark:bg-zinc-800 border-r border-gray-200 dark:border-zinc-700 py-4 overflow-hidden" id="preview-line-numbers">
                    </div>

                    <!-- 代码内容 -->
                    <div class="flex-1 overflow-auto bg-white dark:bg-zinc-900 p-4" id="preview-code-container">
                        <pre id="preview-code-content" class="text-sm font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words"></pre>
                    </div>
                </div>

                <!-- 底部状态栏 -->
                <div class="px-6 py-3 border-t border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-800/50 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <div class="flex items-center gap-4">
                        <span id="preview-position">第 1 行, 第 1 列</span>
                        <span id="preview-size">0 字符</span>
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

        // 查看历史按钮
        this.overlay.querySelector('#preview-history-btn').onclick = () => {
            // TODO: 打开历史视图
            console.log('Show history for:', this.currentStepId);
        };
    }

    show(filename, action) {
        this.overlay.classList.remove('hidden');

        // 更新头部信息
        this.overlay.querySelector('#preview-filename').textContent = filename || 'unknown';
        this.overlay.querySelector('#preview-action').textContent = (action || 'write').toUpperCase();
        this.overlay.querySelector('#preview-status').textContent = '正在生成...';

        // 重置内容
        this.currentContent = '';
        this.editorContainer.textContent = '';
        this.updateLineNumbers();
        this.updateStats();
    }

    hide() {
        this.overlay.classList.add('hidden');
    }

    appendDelta(delta) {
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

        // 更新显示
        this.editorContainer.textContent = this.currentContent;
        this.updateLineNumbers();
        this.updateStats();

        // 自动滚动到底部
        if (this.settings.autoScroll) {
            this.editorContainer.parentElement.scrollTop = this.editorContainer.parentElement.scrollHeight;
        }
    }

    setContent(content) {
        """直接设置完整内容"""
        this.currentContent = content;
        this.editorContainer.textContent = content;
        this.updateLineNumbers();
        this.updateStats();
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

    setStepId(stepId) {
        this.currentStepId = stepId;
    }

    destroy() {
        // 清理事件监听
        document.removeEventListener('keydown', this.handleEscKey);
        if (this.overlay && this.overlay.parentNode) {
            this.overlay.parentNode.removeChild(this.overlay);
        }
    }
}

// 初始化并导出全局实例
let codePreviewOverlay;

function initCodePreviewOverlay() {
    codePreviewOverlay = new CodePreviewOverlay();
    window.codePreviewOverlay = codePreviewOverlay;
}

// 在 DOMContentLoaded 时初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCodePreviewOverlay);
} else {
    initCodePreviewOverlay();
}

// 导出初始化函数供外部调用
window.initCodePreviewOverlay = initCodePreviewOverlay;
