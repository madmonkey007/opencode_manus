// Files Manager - Handles file list display and modal preview
class FilesManager {
    constructor() {
        this.files = [];
        this.modal = null;
        this.init();
    }
    
    init() {
        this.createModal();
    }
    
    createModal() {
        // Create modal for file preview (Manus-style)
        const modal = document.createElement('div');
        modal.id = 'file-preview-modal';
        modal.className = 'fixed inset-0 bg-black/50 backdrop-blur-sm z-[100] hidden flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                <!-- Modal Header -->
                <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                    <div class="flex items-center gap-3">
                        <span id="modal-file-icon" class="material-symbols-outlined text-2xl text-blue-500"></span>
                        <div>
                            <h3 id="modal-file-name" class="text-lg font-semibold text-gray-900 dark:text-white"></h3>
                            <p id="modal-file-path" class="text-xs text-gray-500 dark:text-gray-400"></p>
                        </div>
                    </div>
                    <button id="close-modal" class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                        <span class="material-symbols-outlined text-gray-600 dark:text-gray-400">close</span>
                    </button>
                </div>
                
                <!-- Modal Content -->
                <div id="modal-content" class="flex-1 overflow-auto p-6 bg-gray-50 dark:bg-gray-900">
                    <div class="text-center text-gray-500">Loading...</div>
                </div>
                
                <!-- Modal Footer -->
                <div class="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                    <div id="modal-file-size" class="text-sm text-gray-600 dark:text-gray-400"></div>
                    <a id="modal-download-btn" href="#" download class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2">
                        <span class="material-symbols-outlined text-sm">download</span>
                        <span>Download</span>
                    </a>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        this.modal = modal;
        
        // Close modal on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal();
            }
        });
        
        // Close button
        modal.querySelector('#close-modal').addEventListener('click', () => {
            this.closeModal();
        });
    }
    
    addFile(file) {
        // file: { name, path, type, size, timestamp }
        if (!this.files.find(f => f.path === file.path)) {
            this.files.push({
                ...file,
                timestamp: file.timestamp || new Date().toISOString()
            });
            this.renderFileList();
        }
    }
    
    renderFileList() {
        const container = document.getElementById('file-list-view');
        if (!container) return;
        
        if (this.files.length === 0) {
            container.innerHTML = '<div class="text-sm text-gray-500 italic text-center py-8">No files generated yet.</div>';
            return;
        }
        
        container.innerHTML = '';
        
        this.files.forEach((file, index) => {
            const fileItem = this.createFileItem(file, index);
            container.appendChild(fileItem);
        });
    }
    
    createFileItem(file, index) {
        const item = document.createElement('div');
        item.className = 'flex items-center gap-3 p-3 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg cursor-pointer transition-colors group';
        
        const ext = file.name.split('.').pop().toLowerCase();
        const iconInfo = this.getFileIconInfo(ext);
        
        item.innerHTML = `
            <div class="${iconInfo.bg} p-2 rounded-lg">
                <span class="material-symbols-outlined ${iconInfo.color} text-xl">${iconInfo.icon}</span>
            </div>
            <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-900 dark:text-white truncate">${this.escapeHtml(file.name)}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400">${this.formatTimestamp(file.timestamp)}</div>
            </div>
            <div class="text-xs text-gray-400 dark:text-gray-500">${this.formatFileSize(file.size || 0)}</div>
            <span class="material-symbols-outlined text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">chevron_right</span>
        `;
        
        item.addEventListener('click', () => {
            this.openFileModal(file);
        });
        
        return item;
    }
    
    async openFileModal(file) {
        const modal = this.modal;
        modal.classList.remove('hidden');
        
        // Update modal header
        const ext = file.name.split('.').pop().toLowerCase();
        const iconInfo = this.getFileIconInfo(ext);
        
        modal.querySelector('#modal-file-icon').textContent = iconInfo.icon;
        modal.querySelector('#modal-file-name').textContent = file.name;
        modal.querySelector('#modal-file-path').textContent = file.path;
        modal.querySelector('#modal-file-size').textContent = this.formatFileSize(file.size || 0);
        
        // Set download link
        const downloadBtn = modal.querySelector('#modal-download-btn');
        downloadBtn.href = `/opencode/get_file_content?path=${encodeURIComponent(file.path)}`;
        downloadBtn.download = file.name;
        
        // Load file content
        const contentDiv = modal.querySelector('#modal-content');
        contentDiv.innerHTML = '<div class="text-center text-gray-500"><span class="material-symbols-outlined animate-spin">sync</span><br/>Loading...</div>';
        
        try {
            const response = await fetch(`/opencode/get_file_content?path=${encodeURIComponent(file.path)}`);
            
            if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'gif' || ext === 'webp' || ext === 'svg') {
                // Image preview
                contentDiv.innerHTML = `<img src="/opencode/get_file_content?path=${encodeURIComponent(file.path)}" class="max-w-full h-auto rounded-lg shadow-lg mx-auto" alt="${file.name}">`;
            } else if (ext === 'pdf') {
                // PDF preview
                contentDiv.innerHTML = `<iframe src="/opencode/get_file_content?path=${encodeURIComponent(file.path)}" class="w-full h-full min-h-[600px] rounded-lg"></iframe>`;
            } else {
                // Text content
                const text = await response.text();
                contentDiv.innerHTML = `<pre class="bg-white dark:bg-gray-800 p-4 rounded-lg text-sm text-gray-800 dark:text-gray-200 overflow-auto font-mono whitespace-pre-wrap">${this.escapeHtml(text)}</pre>`;
            }
        } catch (err) {
            contentDiv.innerHTML = `<div class="text-center text-red-500">Failed to load file: ${err.message}</div>`;
        }
    }
    
    closeModal() {
        this.modal.classList.add('hidden');
    }
    
    getFileIconInfo(ext) {
        const iconMap = {
            'pdf': { icon: 'picture_as_pdf', color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20' },
            'doc': { icon: 'description', color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
            'docx': { icon: 'description', color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
            'txt': { icon: 'article', color: 'text-gray-500', bg: 'bg-gray-100 dark:bg-gray-800' },
            'md': { icon: 'article', color: 'text-purple-500', bg: 'bg-purple-50 dark:bg-purple-900/20' },
            'png': { icon: 'image', color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
            'jpg': { icon: 'image', color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
            'jpeg': { icon: 'image', color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
            'gif': { icon: 'image', color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
            'svg': { icon: 'image', color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
            'webp': { icon: 'image', color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
            'js': { icon: 'code', color: 'text-yellow-500', bg: 'bg-yellow-50 dark:bg-yellow-900/20' },
            'py': { icon: 'code', color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
            'html': { icon: 'code', color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-900/20' },
            'css': { icon: 'code', color: 'text-pink-500', bg: 'bg-pink-50 dark:bg-pink-900/20' },
            'json': { icon: 'code', color: 'text-gray-600', bg: 'bg-gray-100 dark:bg-gray-800' }
        };
        return iconMap[ext] || { icon: 'insert_drive_file', color: 'text-gray-400', bg: 'bg-gray-100 dark:bg-gray-800' };
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
        if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
        
        return date.toLocaleString('zh-CN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize files manager
let filesManager;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        filesManager = new FilesManager();
        window.filesManager = filesManager;
    });
} else {
    filesManager = new FilesManager();
    window.filesManager = filesManager;
}
