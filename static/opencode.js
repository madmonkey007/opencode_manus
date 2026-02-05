const el = (sel) => document.querySelector(sel);
const els = (sel) => Array.from(document.querySelectorAll(sel));

window.state = {
    sessions: [],
    activeId: null,
    renderThrottle: null,
    fileFilter: 'all',
    fileSearch: '',
    theme: localStorage.getItem('theme') || 'dark'
};

const FILE_TYPE_MAP = {
    'documents': ['md', 'txt', 'pdf', 'doc', 'docx'],
    'images': ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'],
    'code': ['js', 'py', 'html', 'css', 'ts', 'json', 'c', 'cpp', 'rs', 'go', 'php', 'sh'],
    'links': ['url', 'link']
};

const FILE_TYPE_CONFIG = {
    'documents': { icon: 'article', color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    'images': { icon: 'image', color: 'text-purple-500', bg: 'bg-purple-50 dark:bg-purple-900/20' },
    'code': { icon: 'code', color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
    'links': { icon: 'language', color: 'text-gray-500', bg: 'bg-gray-100 dark:bg-zinc-700' },
    'default': { icon: 'description', color: 'text-gray-400', bg: 'bg-gray-100 dark:bg-zinc-700' }
};


const TOOL_ICON_CONFIG = {
    'read': { 
        icon: 'description', 
        color: 'text-blue-500', 
        bg: 'bg-blue-50 dark:bg-blue-900/20',
        label: 'Read'
    },
    'write': { 
        icon: 'edit', 
        color: 'text-green-500', 
        bg: 'bg-green-50 dark:bg-green-900/20',
        label: 'Write'
    },
    'edit': { 
        icon: 'edit_document', 
        color: 'text-amber-500', 
        bg: 'bg-amber-50 dark:bg-amber-900/20',
        label: 'Edit'
    },
    'browser_search': { 
        icon: 'travel_explore', 
        color: 'text-purple-500', 
        bg: 'bg-purple-50 dark:bg-purple-900/20',
        label: 'Browser Search'
    },
    'grep': { 
        icon: 'manage_search', 
        color: 'text-indigo-500', 
        bg: 'bg-indigo-50 dark:bg-indigo-900/20',
        label: 'Grep'
    },
    'bash': { 
        icon: 'terminal', 
        color: 'text-gray-700 dark:text-gray-300', 
        bg: 'bg-gray-100 dark:bg-zinc-800',
        label: 'Bash'
    },
    'thought': { 
        icon: 'lightbulb', 
        color: 'text-amber-500', 
        bg: 'bg-amber-50 dark:bg-amber-900/20',
        label: 'Thought'
    },
    'run_code': { 
        icon: 'play_circle', 
        color: 'text-green-500', 
        bg: 'bg-green-50 dark:bg-green-900/20',
        label: 'Run Code'
    },
    'file_editor': { 
        icon: 'code', 
        color: 'text-cyan-500', 
        bg: 'bg-cyan-50 dark:bg-cyan-900/20',
        label: 'File Editor'
    },
    'code_editor': { 
        icon: 'edit_note', 
        color: 'text-cyan-500', 
        bg: 'bg-cyan-50 dark:bg-cyan-900/20',
        label: 'Code Editor'
    },
    'browser_preview': { 
        icon: 'desktop_windows', 
        color: 'text-pink-500', 
        bg: 'bg-pink-50 dark:bg-pink-900/20',
        label: 'Browser Preview'
    },
    'file_search': { 
        icon: 'search', 
        color: 'text-teal-500', 
        bg: 'bg-teal-50 dark:bg-teal-900/20',
        label: 'File Search'
    },
    'default': { 
        icon: 'settings', 
        color: 'text-gray-500', 
        bg: 'bg-gray-50 dark:bg-zinc-800',
        label: 'Tool'
    }
};

function applyTheme() {
    if (state.theme === 'dark') {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', state.theme);
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme();
}

function getFileTypeCategory(ext) {
    for (const [cat, exts] of Object.entries(FILE_TYPE_MAP)) {
        if (exts.includes(ext)) return cat;
    }
    return 'default';
}

function renderAll() {
    renderSidebar();
    renderResults();
    renderFiles();
}

function renderSidebar() {
    const list = el('#session-list'); if (!list) return;
    list.innerHTML = '';
    state.sessions.forEach(s => {
        const item = document.createElement('div');
        const isActive = s.id === state.activeId;
        item.className = `p-3 rounded-xl cursor-pointer mb-1 text-sm transition-colors ${isActive ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 font-medium' : 'hover:bg-gray-100 dark:hover:bg-zinc-800 text-gray-700 dark:text-gray-300'}`;
        item.textContent = s.prompt ? (s.prompt.substring(0, 24) + (s.prompt.length > 24 ? '...' : '')) : 'New Task';
        item.onclick = () => { state.activeId = s.id; renderAll(); };
        list.appendChild(item);
    });
}

async function openFile(filePath) {
    const ext = filePath.split('.').pop().toLowerCase();
    const renderable = ['html', 'htm', 'png', 'jpg', 'jpeg', 'gif', 'pdf', 'svg'];
    
    // Switch to preview tab if it's a renderable file
    if (renderable.includes(ext)) {
        els('.tab-btn').find(b => b.dataset.tab === 'preview').click();
        const frame = el('#uvn-frame');
        frame.src = `/opencode/get_file_content?path=${encodeURIComponent(filePath)}`;
    } else {
        // Fetch text content
        try {
            const res = await fetch(`/opencode/get_file_content?path=${encodeURIComponent(filePath)}`);
            const data = await res.json();
            if (data.type === 'text') {
                // For now, we'll alert or show in a simple way, 
                // but ideally we should have a 'Code Viewer' tab.
                // Let's create a temporary overlay
                const viewer = document.createElement('div');
                viewer.className = 'fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-8';
                viewer.innerHTML = `
                    <div class="bg-white dark:bg-zinc-900 w-full max-w-4xl h-full flex flex-col rounded-2xl overflow-hidden shadow-2xl">
                        <div class="p-4 border-b border-gray-200 dark:border-zinc-800 flex justify-between items-center bg-gray-50 dark:bg-zinc-800/50">
                            <span class="font-bold text-sm">${data.filename}</span>
                            <button class="close-viewer p-1 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded"><span class="material-symbols-outlined">close</span></button>
                        </div>
                        <pre class="flex-1 p-6 overflow-auto text-sm font-mono whitespace-pre-wrap">${data.content}</pre>
                    </div>
                `;
                document.body.appendChild(viewer);
                viewer.querySelector('.close-viewer').onclick = () => viewer.remove();
            }
        } catch (e) {
            console.error("Failed to load file content", e);
        }
    }
}

async function renderFiles() {
    const fileList = el('#file-list-view'); if (!fileList) return;
    const s = state.sessions.find(x => x.id === state.activeId);
    if (!s || !s.id) {
        fileList.innerHTML = '<div class="text-sm text-gray-500 italic px-5 py-4">No files generated yet.</div>';
        return;
    }

    try {
        // 优先使用本地 deliverables 数据（mock 模式）
        let files = [];
        if (s.deliverables && s.deliverables.length > 0) {
            files = s.deliverables.map(f => ({
                name: f.name,
                path: f.path,
                type: f.name.split('.').pop().toLowerCase()
            }));
        } else {
            const res = await fetch(`/opencode/list_session_files?sid=${s.id}`);
            const data = await res.json();
            files = data.files || [];
        }

        // Apply Search
        if (state.fileSearch) {
            const query = state.fileSearch.toLowerCase();
            files = files.filter(f => f.name.toLowerCase().includes(query));
        }

        // Apply Filter
        if (state.fileFilter !== 'all') {
            files = files.filter(f => {
                const ext = f.name.split('.').pop().toLowerCase();
                return getFileTypeCategory(ext) === state.fileFilter;
            });
        }

        if (files.length > 0) {
            fileList.innerHTML = '';
            files.forEach(f => {
                const ext = f.name.split('.').pop().toLowerCase();
                const cat = getFileTypeCategory(ext);
                const config = FILE_TYPE_CONFIG[cat] || FILE_TYPE_CONFIG['default'];
                
                const item = document.createElement('div');
                item.className = 'flex items-center gap-3 px-3 py-2 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-lg group cursor-pointer transition-colors';
                item.innerHTML = `
                    <div class="${config.bg} p-2 rounded-lg ${config.color}">
                        <span class="material-symbols-outlined text-[20px]">${config.icon}</span>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">${f.name}</div>
                        <div class="flex items-center gap-2 mt-0.5">
                            <span class="text-[9px] font-bold px-1.5 py-0.5 rounded bg-gray-100 dark:bg-zinc-700 text-gray-500 uppercase tracking-tight">${ext.toUpperCase()}</span>
                            <span class="text-[10px] text-gray-400">Mock Date</span>
                        </div>
                    </div>
                    <button class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 p-1 transition-opacity">
                        <span class="material-symbols-outlined text-[18px]">more_horiz</span>
                    </button>
                `;
                item.onclick = (e) => {
                    if (e.target.closest('button')) return;
                    openFile(f.path);
                };
                fileList.appendChild(item);
            });
        } else {
            fileList.innerHTML = `<div class="text-sm text-gray-500 italic px-5 py-4">${state.fileSearch ? 'No files found matching your search.' : 'No files in this category.'}</div>`;
        }
    } catch (e) {
        console.error("Failed to load files", e);
        fileList.innerHTML = '<div class="text-sm text-red-500 px-5 py-4">Error loading files.</div>';
    }
}

function renderResults() {
    const convo = el('#chat-messages'); if (!convo) return;
    const s = state.sessions.find(x => x.id === state.activeId);
    convo.innerHTML = '';
    if (!s) { el('#welcome-message')?.classList.remove('hidden'); return; }
    el('#welcome-message')?.classList.add('hidden');
    
    // Use enhanced task panel if available
    if (typeof renderEnhancedTaskPanel === 'function') {
        const enhancedPanel = renderEnhancedTaskPanel(s);
        convo.appendChild(enhancedPanel);
        const area = el('#chat-scroll-area');
        area.scrollTop = area.scrollHeight;
        return;
    }

    if (s.prompt) {
        const m = document.createElement('div');
        m.className = 'message-bubble user-bubble animate-fade-in ml-auto mb-6 text-sm shadow-md';
        m.textContent = s.prompt;
        convo.appendChild(m);
    }

    const renderEvent = (ev) => {
        const card = document.createElement('div');
        card.className = 'tool-card border border-border-light dark:border-border-dark rounded-xl mb-3 bg-white dark:bg-surface-dark shadow-sm overflow-hidden transition-all duration-200';
        
        // 获取工具图标配置
        const toolName = ev.tool || 'default';
        const iconConfig = TOOL_ICON_CONFIG[toolName] || TOOL_ICON_CONFIG['default'];
        const isThought = ev.type === 'thought';
        
        // 根据运行状态添加动画效果
        const isRunning = ev.status === 'running';
        const iconClass = isRunning 
            ? iconConfig.color + ' animate-spin' 
            : iconConfig.color;
        
        const title = isThought ? 'Thought' : (iconConfig.label || toolName);
        
        card.innerHTML = `
            <div class="card-header p-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                <div class="flex items-center gap-3">
                    <div class="${iconConfig.bg} p-1.5 rounded-lg">
                        <span class="material-symbols-outlined ${iconClass} text-[20px]">${iconConfig.icon}</span>
                    </div>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-200">${title}</span>
                </div>
                <span class="material-symbols-outlined text-gray-400 expand-icon transition-transform duration-200">expand_more</span>
            </div>
            <div class="card-body hidden border-t border-border-light dark:border-border-dark p-3 text-sm text-gray-600 dark:text-gray-400 bg-gray-50/50 dark:bg-black/20">
                ${isThought ? (ev.content || '') : `<pre class="font-mono text-xs whitespace-pre-wrap">${JSON.stringify(ev.args || {}, null, 2)}</pre>`}
            </div>
        `;

        card.querySelector('.card-header').onclick = () => {
            const body = card.querySelector('.card-body');
            const icon = card.querySelector('.expand-icon');
            const isHidden = body.classList.contains('hidden');
            body.classList.toggle('hidden');
            icon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
        };

        return card;
    };

    const timelineContainer = document.createElement('div');
    timelineContainer.className = 'flex flex-col space-y-0';
    
    // Render orphan events first
    if (s.orphanEvents && s.orphanEvents.length > 0) {
        s.orphanEvents.forEach(ev => {
            timelineContainer.appendChild(renderEvent(ev));
        });
    }

    // Render phases
    if (s.phases && s.phases.length > 0) {
        s.phases.forEach((p, idx) => {
            const phaseNode = document.createElement('div');
            phaseNode.className = 'relative pl-8 pb-8 last:pb-0';
            
            // Timeline line
            if (idx < s.phases.length - 1 || (p.events && p.events.length > 0)) {
                const line = document.createElement('div');
                line.className = 'timeline-line';
                phaseNode.appendChild(line);
            }

            const isDone = p.status === 'done' || p.status === 'completed';
            const phaseIcon = isDone ? 'check' : 'pending';
            const phaseIconClass = isDone ? 'bg-green-500 text-white' : 'bg-white dark:bg-zinc-900 border-2 border-blue-500 text-blue-500';

            phaseNode.innerHTML += `
                <div class="timeline-dot top-2"></div>
                <div class="mb-4">
                    <h3 class="text-base font-semibold text-gray-900 dark:text-white pt-1">${p.title}</h3>
                </div>
                <div class="phase-events space-y-3"></div>
            `;

            const eventsContainer = phaseNode.querySelector('.phase-events');
            if (p.events && p.events.length > 0) {
                p.events.forEach(ev => {
                    eventsContainer.appendChild(renderEvent(ev));
                });
            }
            timelineContainer.appendChild(phaseNode);
        });
    }
    convo.appendChild(timelineContainer);

    if (s.response) {
        const r = document.createElement('div');
        r.className = 'message-bubble assistant-bubble animate-fade-in max-w-[90%] text-sm leading-relaxed mt-6 prose dark:prose-invert';
        r.innerHTML = marked.parse(s.response);
        convo.appendChild(r);
    }
    
    const area = el('#chat-scroll-area');
    area.scrollTop = area.scrollHeight;
}

function bindUI() {
    el('#theme-toggle').onclick = toggleTheme;

    // Sidebar toggle
    const sidebar = el('#sidebar');
    const openSidebarBtn = el('#open-sidebar');
    const toggleSidebarBtn = el('#toggle-sidebar');
    
    if (toggleSidebarBtn) {
        toggleSidebarBtn.onclick = () => {
            sidebar.classList.add('hidden');
            openSidebarBtn.classList.remove('hidden');
        };
    }
    
    if (openSidebarBtn) {
        openSidebarBtn.onclick = () => {
            sidebar.classList.remove('hidden');
            openSidebarBtn.classList.add('hidden');
        };
    }

    // VM Panel toggle
    const vmPanel = el('#vm-panel');
    const mainContent = el('#main-content');
    const closeVmPanelBtn = el('#close-vm-panel');
    const openVmPanelBtn = el('#open-vm-panel');
    
    if (closeVmPanelBtn) {
        closeVmPanelBtn.onclick = () => {
            // 关闭右侧面板
            vmPanel.classList.remove('w-[45%]');
            vmPanel.classList.add('vm-panel-closed');
            
            // 隐藏关闭按钮，显示打开按钮
            closeVmPanelBtn.classList.add('hidden');
            if (openVmPanelBtn) {
                openVmPanelBtn.classList.remove('hidden');
            }
            
            // 中间面板居中（可选）
            if (mainContent) {
                mainContent.classList.add('main-content-centered');
            }
        };
    }
    
    if (openVmPanelBtn) {
        openVmPanelBtn.onclick = () => {
            // 打开右侧面板
            vmPanel.classList.remove('vm-panel-closed');
            vmPanel.classList.add('w-[45%]');
            
            // 隐藏打开按钮，显示关闭按钮
            openVmPanelBtn.classList.add('hidden');
            if (closeVmPanelBtn) {
                closeVmPanelBtn.classList.remove('hidden');
            }
            
            // 移除中间面板居中
            if (mainContent) {
                mainContent.classList.remove('main-content-centered');
            }
        };
    }

    el('#new-task').onclick = () => {
        const id = Math.random().toString(36).slice(2, 9);
        state.sessions.unshift({ id, prompt: '', response: '', phases: [], actions: [], currentPhase: null, deliverables: [], uploadedFiles: [] });
        state.activeId = id;
        renderAll();
    };

    // File Upload
    const fileUploadBtn = el('#file-upload-btn');
    const fileInput = el('#file-input');
    const uploadedFilesDiv = el('#uploaded-files');
    
    if (fileUploadBtn && fileInput) {
        fileUploadBtn.onclick = () => fileInput.click();
        
        fileInput.onchange = async (e) => {
            const files = Array.from(e.target.files);
            if (files.length === 0) return;
            
            const s = state.sessions.find(x => x.id === state.activeId);
            if (!s) return;
            
            if (!s.uploadedFiles) s.uploadedFiles = [];
            
            for (const file of files) {
                // Upload file to server
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const resp = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await resp.json();
                    
                    s.uploadedFiles.push({
                        name: file.name,
                        size: file.size,
                        path: data.path,
                        type: file.type
                    });
                } catch (err) {
                    console.error('File upload failed:', err);
                    alert(`文件上传失败: ${file.name}`);
                }
            }
            
            // Display uploaded files
            renderUploadedFiles(s);
            fileInput.value = ''; // Reset input
        };
    }

    // File Filtering and Search
    const searchInput = el('#file-search');
    if (searchInput) {
        searchInput.oninput = (e) => {
            state.fileSearch = e.target.value;
            renderFiles();
        };
    }

    const filterButtons = {
        '#filter-all': 'all',
        '#filter-docs': 'documents',
        '#filter-images': 'images',
        '#filter-code': 'code',
        '#filter-links': 'links'
    };

    Object.entries(filterButtons).forEach(([id, cat]) => {
        const btn = el(id);
        if (btn) {
            btn.onclick = () => {
                state.fileFilter = cat;
                // Update active style
                Object.keys(filterButtons).forEach(bId => {
                    const b = el(bId);
                    if (!b) return;
                    if (bId === id) {
                        b.className = 'px-4 py-1.5 bg-gray-900 dark:bg-white text-white dark:text-black rounded-full text-xs font-medium whitespace-nowrap';
                    } else {
                        b.className = 'px-4 py-1.5 bg-white border border-gray-200 dark:bg-zinc-800 dark:border-zinc-700 text-gray-600 dark:text-gray-300 rounded-full text-xs font-medium hover:bg-gray-50 dark:hover:bg-zinc-700 whitespace-nowrap transition-colors';
                    }
                });
                renderFiles();
            };
        }
    });

    const rs = el('#runStream');
    if (rs) rs.onclick = async () => {
        // Show VM panel when task starts and load iframe if not loaded
        const vmPanel = el('#vm-panel');
        const uvnFrame = el('#uvn-frame');
        
        if (vmPanel) {
            vmPanel.classList.remove('hidden');
            
            // Lazy load iframe on first use
            if (uvnFrame && uvnFrame.hasAttribute('data-src')) {
                const src = uvnFrame.getAttribute('data-src');
                uvnFrame.setAttribute('src', src);
                uvnFrame.removeAttribute('data-src');
                console.log('VNC iframe loaded on demand');
            }
        }
        const input = el('#prompt'); if (!input.value.trim()) return;
        const p = input.value.trim();
        let s = state.sessions.find(x => x.id === state.activeId);
        if (!s) {
            const id = Math.random().toString(36).slice(2, 9);
            s = { id, prompt: p, response: '', phases: [], orphanEvents: [], actions: [], currentPhase: null };
            state.sessions.unshift(s);
            state.activeId = id;
        } else {
            s.prompt = p;
            s.response = '';
            s.phases = [];
            s.orphanEvents = [];
            s.actions = [];
            s.currentPhase = null;
        }
        input.value = '';
        renderAll();

        const es = new EventSource(`/opencode/run_sse?prompt=${encodeURIComponent(p)}&sid=${state.activeId}`);
        es.onmessage = (e) => {
            console.log("SSE Message:", e.data);
            const data = JSON.parse(e.data);
            if (data.type === 'phases_init') {
                s.phases = (data.phases || []).map(p => ({ ...p, events: [] }));
                s.currentPhase = data.phases.find(p => p.status === 'active')?.id || null;
            } else if (data.type === 'actions_init') {
                s.actions = data.actions || [];
            } else if (data.type === 'action') {
                // Add or update action
                const actionData = data.data;
                const existingIdx = s.actions.findIndex(a => a.tool === actionData.tool && a.timestamp === actionData.timestamp);
                if (existingIdx >= 0) {
                    s.actions[existingIdx] = actionData;
                } else {
                    s.actions.push(actionData);
                }
            } else if (data.type === 'panel_mode') {
                // Handle panel mode changes
                if (window.rightPanelManager) {
                    if (data.mode === 'browser') {
                        window.rightPanelManager.showBrowser();
                    } else if (data.mode === 'file-editor') {
                        window.rightPanelManager.showFileEditor(data.filename || 'output.txt', data.content || '');
                    }
                }
            } else if (data.type === 'file_content_update') {
                // Handle file content updates
                if (window.rightPanelManager) {
                    window.rightPanelManager.updateFileContent(data.content);
                }
            } else if (data.type === 'file_content_append') {
                // Handle file content streaming
                if (window.rightPanelManager) {
                    window.rightPanelManager.appendFileContent(data.chunk);
                }
            } else if (data.type === 'file_generated') {
                // Handle file generation
                if (window.filesManager && data.file) {
                    window.filesManager.addFile(data.file);
                }
            } else if (data.type === 'preview_url') {
                // Handle web preview
                console.log('Received preview_url event:', data.data);
                if (window.rightPanelManager && data.data && data.data.url) {
                    window.rightPanelManager.showWebPreview(data.data.url);
                }
            } else if (data.type === 'phase_update') {
                // Update phase status
                const phase = s.phases.find(p => p.id === data.phase_id);
                if (phase) {
                    phase.status = data.status;
                    if (data.status === 'active') {
                        s.currentPhase = data.phase_id;
                    }
                }
            } else if (data.type === 'tool_event') {
                const event = data.data;
                // Map to phase if specified, otherwise to the current active phase
                let targetPhase = null;
                if (event.phase !== undefined) {
                    targetPhase = s.phases.find(p => p.number === event.phase);
                }
                
                if (!targetPhase) {
                    // Find the last phase that is not 'pending'
                    targetPhase = [...s.phases].reverse().find(p => p.status !== 'pending') || s.phases[s.phases.length - 1];
                }

                if (targetPhase) {
                    if (!targetPhase.events) targetPhase.events = [];
                    targetPhase.events.push(event);
                } else {
                    // Fallback for events before any phase is initialized
                    if (!s.orphanEvents) s.orphanEvents = [];
                    s.orphanEvents.push(event);
                }
            } else if (data.type === 'answer_chunk') {
                s.response += data.text;
            } else if (data.type === 'file_update') {
                if (data.sid === state.activeId) renderFiles();
            } else if (data.type === 'deliverables') {
                s.deliverables = data.items || [];
            } else if (data.type === 'status' && data.value === 'done') {
                es.close();
                renderFiles();
            }
            renderResults();
        };
    };

    el('#prompt').onkeydown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); rs.click(); } };
    
    els('.tab-btn').forEach(btn => {
        btn.onclick = () => {
            els('.tab-btn').forEach(b => b.classList.remove('active-tab'));
            btn.classList.add('active-tab');
            const target = btn.dataset.tab;
            els('.tab-pane').forEach(p => p.classList.add('hidden'));
            el(`#tab-${target}`).classList.remove('hidden');
            if (target === 'files') renderFiles();
        };
    });
}

function init() {
    // 加载 mock 数据（如果可用）
    if (typeof MOCK_DATA !== 'undefined' && MOCK_DATA && MOCK_DATA.sessions && MOCK_DATA.sessions.length > 0) {
        console.log('[Mock] Loading mock data...');
        window.state = {
            ...window.state,
            ...MOCK_DATA
        };
        console.log('[Mock] Mock data loaded:', window.state.sessions.length, 'sessions');
    }
    // Theme initialization
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    state.theme = savedTheme;
    applyTheme();

    bindUI();
    renderAll();
}

function applyTheme() {
    const isDark = state.theme === 'dark';
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('theme', state.theme);
    
    // Update Icons
    const lightIcon = el('.light-icon');
    const darkIcon = el('.dark-icon');
    if (lightIcon && darkIcon) {
        if (isDark) {
            lightIcon.classList.add('hidden');
            darkIcon.classList.remove('hidden');
        } else {
            lightIcon.classList.remove('hidden');
            darkIcon.classList.add('hidden');
        }
    }
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme();
}

// Wait for DOM to be fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
