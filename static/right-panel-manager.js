// Right Panel Manager - Handles dynamic content display
class RightPanelManager {
    constructor() {
        this.panel = document.getElementById('vm-panel');
        this.previewTab = document.getElementById('tab-preview');
        this.filesTab = document.getElementById('tab-files');
        this.currentMode = null; // 'browser', 'file-editor', 'idle'
        this.fileEditorContainer = null;
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
        if (this.panel.classList.contains('hidden')) {
            this.panel.classList.remove('hidden');
        }
    }
    
    hide() {
        this.panel.classList.add('hidden');
    }
    
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active-tab');
                btn.classList.remove('text-gray-500', 'dark:text-gray-400');
            } else {
                btn.classList.remove('active-tab');
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
        iframe.style.display = 'none';
        
        if (this.fileEditorContainer) {
            this.fileEditorContainer.classList.remove('hidden');
            
            // Update file editor content with enhanced UI
            const contentDiv = document.getElementById('file-editor-content');
            contentDiv.innerHTML = `
                <div class="mb-3 flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-zinc-700 pb-2">
                    <span class="material-symbols-outlined text-base text-gray-600 dark:text-gray-400">edit_note</span>
                    <span class="font-medium">${this.escapeHtml(filename)}</span>
                    <span class="ml-auto text-xs text-gray-500 dark:text-gray-400">
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
        }
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
