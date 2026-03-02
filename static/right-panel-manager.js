// Right Panel Manager - Handles dynamic content display
class RightPanelManager {
    constructor() {
        this.panel = document.getElementById('vm-panel');
        this.previewTab = document.getElementById('tab-preview');
        this.filesTab = document.getElementById('tab-files');
        this.currentMode = null; // 'browser', 'file-editor', 'idle'
        this.fileEditorContainer = null;
        this._scrollRAFPending = false; // ✅ v=28: 显式初始化RAF标志位
        this.init();
    }

    init() {
        // Create file editor container
        this.createFileEditorContainer();

        // Listen for tab switches
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                this.switchTab(tab);
            });
        });
    }

    createFileEditorContainer() {
        // Create a container for file editing visualization
        const container = document.createElement('div');
        container.id = 'file-editor-container';
        container.className = 'hidden h-full flex flex-col bg-white dark:bg-zinc-900';
        container.innerHTML = `
            <div class="flex-1 overflow-auto p-4">
                <div id="file-editor-content" class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 font-mono text-sm">
                    <div class="text-gray-400 dark:text-gray-500 text-center py-8 text-sm">
                        等待文件操作...
                    </div>
                </div>
            </div>
        `;
        this.previewTab.appendChild(container);
        this.fileEditorContainer = container;

        // Create web preview iframe container
        this.createWebPreviewContainer();
    }

    createWebPreviewContainer() {
        // Create a container for web preview
        const container = document.createElement('div');
        container.id = 'web-preview-container';
        container.className = 'hidden h-full w-full';
        container.innerHTML = `
            <iframe id="web-preview-iframe" class="w-full h-full border-0 bg-white"></iframe>
        `;
        this.previewTab.appendChild(container);
        this.webPreviewContainer = container;
    }

    show() {
        // 展开面板：移除宽度限制
        this.panel.classList.remove('w-0');
        this.panel.classList.add('w-[45%]');

        // 确保面板可见
        if (this.panel.classList.contains('hidden')) {
            this.panel.classList.remove('hidden');
        }
    }

    hide() {
        this.panel.classList.add('hidden');
    }

    // 清空面板内容（用于切换会话时）
    clear() {
        this.currentMode = null;
        this.currentFilename = null;

        // 隐藏所有内容容器
        if (this.fileEditorContainer) {
            this.fileEditorContainer.classList.add('hidden');
        }
        if (this.webPreviewContainer) {
            this.webPreviewContainer.classList.add('hidden');
        }

        const iframe = document.getElementById('uvn-frame');
        if (iframe) iframe.style.display = 'none';

        // 清空文件编辑器内容
        const contentDiv = document.getElementById('file-editor-content');
        if (contentDiv) {
            contentDiv.innerHTML = `
                <div class="text-gray-400 dark:text-gray-500 text-center py-8 text-sm">
                    等待文件操作...
                </div>
            `;
        }

        console.log('[RightPanel] Panel cleared');
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
                btn.classList.remove('text-gray-500', 'dark:text-gray-400');
            } else {
                btn.classList.remove('active');
                btn.classList.add('text-gray-500', 'dark:text-gray-400');
            }
        });

        // Switch tab content
        if (tabName === 'preview') {
            document.getElementById('tab-preview').classList.remove('hidden');
            document.getElementById('tab-files').classList.add('hidden');
        } else if (tabName === 'files') {
            document.getElementById('tab-preview').classList.add('hidden');
            document.getElementById('tab-files').classList.remove('hidden');
        }
    }

    // Show browser mode (noVNC)
    showBrowser() {
        this.show();
        this.switchTab('preview');
        this.currentMode = 'browser';

        // Hide file editor, show iframe
        if (this.fileEditorContainer) {
            this.fileEditorContainer.classList.add('hidden');
        }

        const iframe = document.getElementById('uvn-frame');
        iframe.style.display = 'block';

        // Load iframe if not loaded
        if (!iframe.src && iframe.dataset.src) {
            iframe.src = iframe.dataset.src;
            console.log('VNC iframe loaded on demand');
        }
    }

    // Show web preview mode
    showWebPreview(url) {
        console.log('Showing web preview:', url);
        this.show();
        this.switchTab('preview');
        this.currentMode = 'web-preview';

        // Hide file editor and VNC iframe
        if (this.fileEditorContainer) {
            this.fileEditorContainer.classList.add('hidden');
        }
        const vncIframe = document.getElementById('uvn-frame');
        if (vncIframe) {
            vncIframe.style.display = 'none';
        }

        // Show web preview container
        if (this.webPreviewContainer) {
            this.webPreviewContainer.classList.remove('hidden');
            const iframe = document.getElementById('web-preview-iframe');
            if (iframe) {
                iframe.src = url;
                console.log('Web preview iframe loaded:', url);
            }
        }
    }

    // Show file editor mode
    showFileEditor(filename, content = '') {
        this.show();
        this.switchTab('preview');
        this.currentMode = 'file-editor';
        this.currentFilename = filename;

        // Hide iframe, show file editor
        const iframe = document.getElementById('uvn-frame');
        if (iframe) iframe.style.display = 'none';

        if (this.fileEditorContainer) {
            this.fileEditorContainer.classList.remove('hidden');

            // Update file editor content with enhanced UI
            const contentDiv = document.getElementById('file-editor-content');
            contentDiv.innerHTML = `
                <div class="mb-3 flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-zinc-700 pb-2">
                    <span class="material-symbols-outlined text-base text-gray-600 dark:text-gray-400">edit_note</span>
                    <span class="font-bold">${this.escapeHtml(filename)}</span>
                    <span class="ml-auto text-xs text-gray-500 dark:text-gray-400 status-label">
                        正在写入...
                    </span>
                </div>
                <div class="relative">
                    <pre id="file-code-content" class="text-xs leading-relaxed text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words font-mono bg-gray-50 dark:bg-zinc-800/50 p-4 rounded border border-gray-200 dark:border-zinc-700">${this.escapeHtml(content)}</pre>
                    <div id="typing-cursor" class="absolute w-0.5 h-4 bg-blue-500 animate-pulse" style="display: none;"></div>
                </div>
                <div class="mt-2 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
                    <span class="material-symbols-outlined text-sm">info</span>
                    <span id="file-line-count">0 行</span>
                    <span class="mx-1">•</span>
                    <span id="file-char-count">0 字符</span>
                </div>
            `;
            this.updateFileStats(content);
        }
    }

    async showHistoryFile(sessionId, filePath, stepId) {
        this.show();
        this.switchTab('preview');
        this.currentMode = 'file-editor';
        this.currentFilename = filePath;

        const iframe = document.getElementById('uvn-frame');
        if (iframe) iframe.style.display = 'none';

        if (this.fileEditorContainer) {
            this.fileEditorContainer.classList.remove('hidden');
            const contentDiv = document.getElementById('file-editor-content');
            contentDiv.innerHTML = `
                <div class="p-8 text-center">
                    <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent mb-4"></div>
                    <div class="text-gray-500 dark:text-gray-400">正在加载历史版本 [${stepId}]...</div>
                </div>
            `;

            try {
                // 后端实际接口可能是 /opencode/get_file_at_step
                const res = await fetch(`/opencode/get_file_at_step?session_id=${sessionId}&file_path=${encodeURIComponent(filePath)}&step_id=${stepId}`);
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const data = await res.json();

                if (data.status === 'success' || data.content !== undefined) {
                    const content = data.content || '';
                    this.showFileEditor(filePath, content);
                    const statusLabel = contentDiv.querySelector('.status-label');
                    if (statusLabel) {
                        statusLabel.textContent = `历史版本 @ ${stepId}`;
                        statusLabel.classList.add('bg-amber-100', 'dark:bg-amber-900/30', 'text-amber-700', 'dark:text-amber-400', 'px-2', 'py-0.5', 'rounded');
                    }
                } else {
                    throw new Error(data.message || '获取失败');
                }
            } catch (e) {
                console.error('Failed to fetch history file:', e);
                contentDiv.innerHTML = `
                    <div class="p-8 text-center text-red-500">
                        <span class="material-symbols-outlined text-4xl mb-2">error</span>
                        <p>无法加载历史版本: ${e.message}</p>
                    </div>
                `;
            }
        }
    }

    updateFileStats(content) {
        const lineCount = content ? content.split('\n').length : 0;
        const charCount = content ? content.length : 0;
        const lineEl = document.getElementById('file-line-count');
        const charEl = document.getElementById('file-char-count');
        if (lineEl) lineEl.textContent = `${lineCount} 行`;
        if (charEl) charEl.textContent = `${charCount} 字符`;
    }

    // Update file editor content (for real-time updates)
    updateFileContent(content) {
        if (this.currentMode !== 'file-editor') return;

        const contentDiv = document.getElementById('file-editor-content');
        const pre = contentDiv.querySelector('pre');
        if (pre) {
            pre.textContent = content;
            // Auto scroll to bottom
            contentDiv.scrollTop = contentDiv.scrollHeight;
        }
    }

    // Append content to file editor (streaming)
    appendFileContent(chunk) {
        if (this.currentMode !== 'file-editor') return;

        const pre = document.getElementById('file-code-content');
        if (pre) {
            pre.textContent += chunk;

            // Update statistics
            const content = pre.textContent;
            const lineCount = content.split('\n').length;
            const charCount = content.length;

            const lineCountEl = document.getElementById('file-line-count');
            const charCountEl = document.getElementById('file-char-count');

            if (lineCountEl) lineCountEl.textContent = `${lineCount} 行`;
            if (charCountEl) charCountEl.textContent = `${charCount} 字符`;

            // Auto scroll to bottom
            const container = document.getElementById('file-editor-content');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }

            // Scroll pre element to bottom as well
            pre.scrollTop = pre.scrollHeight;
        }
    }

    // 打字机效果追加内容
    /**
     * 追加文件预览内容（支持SSE流式显示）
     *
     * 策略：累积小块内容后批量显示，避免逐字符太慢
     * - 如果SSE发送的是小块内容（<50字符），立即显示
     * - 如果SSE发送的是大块内容（≥50字符），也立即显示
     * - 不创建内部队列，信任SSE的时序控制
     */
    typeAppendContent(content) {
        if (this.currentMode !== 'file-editor') return;
        if (!content || content.length === 0) return;

        const pre = document.getElementById('file-code-content');
        const cursor = document.getElementById('typing-cursor');
        if (!pre) return;

        // 显示光标
        if (cursor) cursor.style.display = 'block';

        // ✅ 策略：直接追加内容，按SSE发送的块显示
        // 后端已经控制了发送节奏，前端立即显示即可
        pre.textContent += content;

        // 更新统计
        const fullContent = pre.textContent;
        const lineCount = fullContent.split('\n').length;
        const charCount = fullContent.length;

        const lineCountEl = document.getElementById('file-line-count');
        const charCountEl = document.getElementById('file-char-count');

        if (lineCountEl) lineCountEl.textContent = `${lineCount} 行`;
        if (charCountEl) charCountEl.textContent = `${charCount} 字符`;

        // ✅ v=33: 修复自动滚动 - 使用双重RAF + setTimeout降级确保内容完全渲染
        // 问题：单个RAF可能在DOM完全更新前执行，导致scrollHeight计算不准确
        if (!this._scrollRAFPending) {
            this._scrollRAFPending = true;

            // 第一帧RAF：等待浏览器开始布局
            requestAnimationFrame(() => {
                // 第二帧RAF：等待布局完成并获取准确的scrollHeight
                requestAnimationFrame(() => {
                    try {
                        this._performScroll();
                        console.log('[RightPanel] Auto-scrolled to bottom (double RAF)');
                    } catch (error) {
                        console.error('[RightPanel] Failed to auto-scroll:', error);
                    } finally {
                        this._scrollRAFPending = false;
                    }
                });

                // ✅ v=33: 添加setTimeout降级方案，确保双重RAF失败时仍能滚动
                setTimeout(() => {
                    if (this._scrollRAFPending) {
                        console.warn('[RightPanel] ⚠️ Double RAF timeout, using setTimeout fallback');
                        try {
                            this._performScroll();
                            console.log('[RightPanel] Auto-scrolled to bottom (setTimeout fallback)');
                        } catch (error) {
                            console.error('[RightPanel] Failed to auto-scroll with setTimeout:', error);
                        } finally {
                            this._scrollRAFPending = false;
                        }
                    }
                }, 150); // 150ms后降级（3-4帧的时间）
            });
        }
    }

    // ✅ v=33: 提取滚动逻辑为独立方法，便于RAF和setTimeout复用
    _performScroll() {
        // 1. 滚动pre元素（文件内容容器）
        const preEl = document.getElementById('file-code-content');
        if (preEl) {
            preEl.scrollTop = preEl.scrollHeight;
        }

        // 2. 滚动主容器（file-editor-content）
        const containerEl = document.getElementById('file-editor-content');
        if (containerEl) {
            containerEl.scrollTop = containerEl.scrollHeight;
        }

        // 3. 滚动外层容器（tab-preview）
        const tabPreviewEl = document.getElementById('tab-preview');
        if (tabPreviewEl) {
            tabPreviewEl.scrollTop = tabPreviewEl.scrollHeight;
        }

        // 4. 滚动主面板内容
        const panelContentEl = document.querySelector('.right-panel .panel-content');
        if (panelContentEl) {
            panelContentEl.scrollTop = panelContentEl.scrollHeight;
        }
    }

    // 设置文件状态
    setFileStatus(status) {
        const statusLabel = document.querySelector('.status-label');
        if (statusLabel) {
            statusLabel.textContent = status;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize panel manager
let rightPanelManager;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        rightPanelManager = new RightPanelManager();
        window.rightPanelManager = rightPanelManager;
    });
} else {
    rightPanelManager = new RightPanelManager();
    window.rightPanelManager = rightPanelManager;
}
