const el = (sel) => document.querySelector(sel);
const els = (sel) => Array.from(document.querySelectorAll(sel));

window.state = {
    sessions: [],
    activeId: null,
    projects: [],          // 项目列表
    activeProjectId: null, // 当前选中的项目ID
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
    'documents': { icon: 'article', color: 'text-gray-600', bg: 'bg-gray-50 dark:bg-zinc-800' },
    'images': { icon: 'image', color: 'text-gray-600', bg: 'bg-gray-50 dark:bg-zinc-800' },
    'code': { icon: 'code', color: 'text-gray-600', bg: 'bg-gray-50 dark:bg-zinc-800' },
    'links': { icon: 'language', color: 'text-gray-600', bg: 'bg-gray-50 dark:bg-zinc-800' },
    'default': { icon: 'description', color: 'text-gray-600', bg: 'bg-gray-50 dark:bg-zinc-800' }
};

// SVG 图标配置（从 manus.html 复制）
const TOOL_SVG_ICONS = {
    'thought': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M13 6.75C13 4.14831 10.7836 2 8 2C5.2164 2 3 4.14831 3 6.75C3 8.22062 3.78012 9.51358 4.98463 10.3028C5.06178 10.3533 5.12 10.4284 5.14844 10.5135L5.59619 11.8568C5.70422 12.181 6.02844 12.3846 6.36958 12.342L7.41652 12.2121C7.47921 12.2043 7.54269 12.2075 7.60428 12.2217L8.60547 12.4453C8.86719 12.5039 9.13477 12.4355 9.33691 12.2617L10.1123 11.5957C10.2842 11.4482 10.5156 11.3887 10.7393 11.4336L11.6904 11.625C12.165 11.7188 12.6191 11.3828 12.668 10.9023L12.751 10.0996C12.7637 9.9707 12.8203 9.84961 12.9121 9.75781L13.5166 9.15332C13.8281 8.8418 14 8.42773 14 8V6.75H13ZM6.5 6.75C6.5 6.33579 6.83579 6 7.25 6C7.66421 6 8 6.33579 8 6.75C8 7.16421 7.66421 7.5 7.25 7.5C6.83579 7.5 6.5 7.16421 6.5 6.75ZM9.5 6.75C9.5 6.33579 9.83579 6 10.25 6C10.6642 6 11 6.33579 11 6.75C11 7.16421 10.6642 7.5 10.25 7.5C9.83579 7.5 9.5 7.16421 9.5 6.75Z" fill="#666"></path>
    </svg>`,
    'default': `<svg style="width:14px;height:14px;color:#666" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
    </svg>`
};

const TOOL_LABELS = {
    'thought': '思考过程',
    'read': 'Read',
    'write': 'Write',
    'default': 'Tool'
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

// 安全解析 JSON，防止解析失败导致整个加载失败
function safeParseJSON(str, fallback = {}) {
    try {
        return str ? JSON.parse(str) : fallback;
    } catch (e) {
        console.warn('[safeParseJSON] JSON parse error:', e.message, '| input:', str);
        return fallback;
    }
}

function renderAll() {
    console.log('🔄 renderAll 被调用');
    console.log('  - sessions 数量:', state.sessions.length);
    console.log('  - activeId:', state.activeId);
    renderSidebar();
    renderResults();
    renderFiles();

    // 更新界面模式（欢迎界面 vs 聊天界面）
    if (window.updateInterfaceMode) {
        window.updateInterfaceMode();
    }
}

// ✅ 修复3：添加防抖和验证机制
let _saveStateDebounceTimer = null;
let _saveStateInProgress = false;

function saveState() {
    // 防抖：如果已经有待执行的保存，取消它
    if (_saveStateDebounceTimer) {
        clearTimeout(_saveStateDebounceTimer);
    }

    // 防抖：延迟100ms执行，避免频繁写入
    _saveStateDebounceTimer = setTimeout(() => {
        _executeSave();
    }, 100);
}

// ✅ 修复C1: 在页面刷新前立即执行待处理的保存
if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', () => {
        if (_saveStateDebounceTimer) {
            console.log('[beforeunload] Flushing pending save...');
            clearTimeout(_saveStateDebounceTimer);
            _saveStateDebounceTimer = null;
            _executeSave();
        }
    });
}

function _executeSave(retryCount = 0) {
    // ✅ 修复C3: 添加递归重试限制，防止栈溢出
    const MAX_RETRIES = 2;
    if (retryCount > MAX_RETRIES) {
        console.error('[saveState] Max retries exceeded, giving up');
        _saveStateInProgress = false;
        return;
    }

    if (_saveStateInProgress && retryCount === 0) {
        console.log('[saveState] Save already in progress, skipping...');
        return;
    }

    _saveStateInProgress = true;

    try {
        // ✅ 验证1：基本数据完整性
        if (!state || typeof state !== 'object') {
            throw new Error('Invalid state object');
        }

        if (!Array.isArray(state.sessions)) {
            console.error('[saveState] state.sessions is not an array:', state.sessions);
            throw new Error('state.sessions must be an array');
        }

        // ✅ 验证2：session数据完整性 + 清理空session
        const now = Date.now();
        const GRACE_PERIOD_MS = 5 * 60 * 1000;  // 5分钟宽限期

        const validSessions = state.sessions.filter(s => {
            if (!s || typeof s !== 'object') return false;
            if (!s.id) return false;

            // ✅ 修复C2竞态条件: 只清理真正旧的空session
            // 条件：是后端session AND 不是当前active AND 没有任何数据 AND 超过宽限期
            if (s.id.startsWith('ses_') &&
                s.id !== state.activeId &&  // ✅ 保护当前active session
                !s.prompt &&
                !s.response &&
                (!s.actions || s.actions.length === 0) &&
                (!s.phases || s.phases.length === 0)) {

                // 检查是否在宽限期内（最近创建或正在加载的session）
                const sessionAge = now - (s._createdTime || now);
                if (sessionAge < GRACE_PERIOD_MS) {
                    console.log(`[saveState] Grace period active for ${s.id} (${Math.round(sessionAge/1000)}s old), skipping cleanup`);
                    return true;  // 保留，在宽限期内
                }

                // 超过宽限期且确实为空，清理
                console.log('[saveState] Cleaning up truly empty session:', s.id, `(${Math.round(sessionAge/1000/60)}min old)`);
                return false;
            }
            return true;
        });

        if (validSessions.length !== state.sessions.length) {
            console.warn(`[saveState] Filtered ${state.sessions.length - validSessions.length} invalid sessions`);
            state.sessions = validSessions;
        }

        // ✅ 验证3：确保每个session都有必需字段
        const sanitizedSessions = validSessions.map(s => {
            return {
                id: s.id,
                prompt: s.prompt || '',
                phases: (s.phases || []).map(p => ({
                    id: p.id,
                    title: p.title,
                    status: p.status,
                    number: p.number
                })),
                response: s.response || '',
                deliverables: s.deliverables || [],
                actions: s.actions || [],
                orphanEvents: s.orphanEvents || [],
                mode: s.mode || null,
                _version: s._version || 1,
                _createdTime: s._createdTime || Date.now(),  // ✅ 修复I1: 添加创建时间，用于宽限期判断
                _hasCompletionSummary: s._hasCompletionSummary || false  // ✅ v=32: 持久化任务总结标志位
            };
        });

        const stateToSave = {
            activeId: state.activeId,
            sessions: sanitizedSessions,
            activeProjectId: state.activeProjectId
        };

        const jsonString = JSON.stringify(stateToSave);

        // ✅ 验证4：检查大小（localStorage通常限制5MB）
        const sizeInMB = jsonString.length / (1024 * 1024);
        if (sizeInMB > 4.5) {
            console.warn(`[saveState] State size large: ${sizeInMB.toFixed(2)}MB, approaching 5MB limit`);

            // ✅ 修复C2: 保护当前active session，正确过滤旧的已完成session
            const activeSession = state.sessions.find(s => s.id === state.activeId);

            // 找出所有已完成的session（排除当前active session）
            const oldCompletedSessions = sanitizedSessions.filter(s =>
                s.phases && s.phases.some(p => p.status === 'completed') &&
                s.id !== state.activeId
            );

            if (oldCompletedSessions.length > 10) {
                // 只保留最新的10个已完成session（删除最旧的）
                const toRemove = oldCompletedSessions.slice(0, oldCompletedSessions.length - 10);
                console.log('[saveState] Removing', toRemove.length, 'old completed sessions to free space');

                // 保留：不是被删除的session，或者是当前active session
                state.sessions = sanitizedSessions.filter(s =>
                    !toRemove.includes(s) || s.id === state.activeId
                );

                // 确保active session不会被删除
                if (activeSession && !state.sessions.find(s => s.id === activeSession.id)) {
                    console.warn('[saveState] Active session was incorrectly filtered, re-adding');
                    state.sessions.unshift(activeSession);
                }

                // ✅ 修复C2: 防止无限递归 - 检查清理后的大小
                const newSize = JSON.stringify({ activeId: state.activeId, sessions: state.sessions }).length / (1024 * 1024);
                if (newSize > 4.5) {
                    console.error('[saveState] Still over limit after cleanup, giving up. Size:', newSize.toFixed(2) + 'MB');
                    // 不要再递归，避免无限循环
                    return;
                }

                console.log('[saveState] Cleanup complete, new size:', newSize.toFixed(2) + 'MB');
                return _executeSave(retryCount + 1);
            }
        }

        localStorage.setItem('opencode_state', jsonString);

        // ✅ 验证5：保存后验证
        try {
            const saved = JSON.parse(localStorage.getItem('opencode_state'));
            if (!saved || saved.sessions.length !== sanitizedSessions.length) {
                throw new Error('Save verification failed');
            }
        } catch (verifyError) {
            console.error('[saveState] Verification failed:', verifyError);
            // 清理损坏的localStorage
            localStorage.removeItem('opencode_state');
            throw verifyError;
        }

        console.log(`[saveState] Saved ${sanitizedSessions.length} sessions (${sizeInMB.toFixed(2)}MB)`);

        // 单独保存 projects（避免被 sessions 的大数据影响）
        try {
            const projectData = (state.projects || []).map(p => ({
                id: p.id,
                name: p.name
            }));
            localStorage.setItem('opencode_projects', JSON.stringify(projectData));
            
            // 保存 activeProjectId
            if (state.activeProjectId) {
                localStorage.setItem('opencode_activeProjectId', state.activeProjectId);
            } else {
                localStorage.removeItem('opencode_activeProjectId');
            }
            console.log(`[saveState] Saved ${projectData.length} projects`);
        } catch (projectSaveError) {
            console.warn('[saveState] Failed to save projects:', projectSaveError);
        }

    } catch (e) {
        console.error('[saveState] Failed to save state:', e);

        // ✅ 用户友好提示
        if (e.name === 'QuotaExceededError') {
            console.warn('[saveState] localStorage quota exceeded, clearing old data...');
            // 清理旧的已完成session
            if (Array.isArray(state.sessions)) {
                state.sessions = state.sessions.filter(s => {
                    const isOld = s.phases && s.phases.some(p => p.status === 'completed');
                    return !isOld;
                });
            }
        } else {
            console.error('[saveState] Unknown error:', e.message, e.stack);
        }
    } finally {
        _saveStateInProgress = false;
    }
}


async function loadState() {
    console.log('[loadState] Loading state...');
    const saved = localStorage.getItem('opencode_state');
    if (saved) {
        try {
            const parsed = JSON.parse(saved);
            console.log('[loadState] Found', parsed.sessions?.length, 'sessions in localStorage');
            state.sessions = parsed.sessions || [];
            state.activeId = parsed.activeId || null;

            // ✅ 修复4：版本兼容 + 数据修复 + 清理空session
            let repairedCount = 0;
            let cleanedCount = 0;

            state.sessions = state.sessions.filter(s => {
                // 基本验证
                if (!s || typeof s !== 'object') {
                    console.warn('[loadState] Invalid session object, removing');
                    cleanedCount++;
                    return false;
                }
                if (!s.id) {
                    console.warn('[loadState] Session without ID, removing');
                    cleanedCount++;
                    return false;
                }

                // ✅ 修复：确保所有session都有project_id
                if (!s.project_id) {
                    s.project_id = 'proj_default';
                    repairedCount++;
                }

                // ✅ 修复C2竞态条件: 添加宽限期，清理真正的旧空session
                const now = Date.now();
                const GRACE_PERIOD_MS = 5 * 60 * 1000;  // 5分钟宽限期

                if (s.id.startsWith('ses_') &&
                    s.id !== state.activeId &&  // ✅ 保护当前active session
                    !s.prompt &&
                    !s.response &&
                    (!s.actions || s.actions.length === 0) &&
                    (!s.phases || s.phases.length === 0)) {

                    // 检查是否在宽限期内
                    const sessionAge = now - (s._createdTime || now);
                    if (sessionAge < GRACE_PERIOD_MS) {
                        // 在宽限期内，保留
                        return true;
                    }

                    // 超过宽限期且确实为空，清理
                    console.log('[loadState] Cleaning up truly empty session:', s.id, `(${Math.round(sessionAge/1000/60)}min old)`);
                    cleanedCount++;
                    return false;
                }

                return true;
            });

            if (cleanedCount > 0) {
                console.warn(`[loadState] Cleaned ${cleanedCount} invalid/empty sessions`);
            }

            // 数据修复和迁移
            for (const s of state.sessions) {
                const version = s._version || 0;

                // 版本0 → 1：添加缺失字段
                if (version < 1) {
                    if (!s.actions) {
                        console.log('[loadState] Migration: Adding actions array to', s.id);
                        s.actions = [];
                        repairedCount++;
                    }
                    if (!s.orphanEvents) {
                        s.orphanEvents = [];
                        repairedCount++;
                    }
                    if (!s.mode) {
                        s.mode = null;
                    }
                    if (!s._createdTime) {
                        // 对于旧数据，设置为当前时间（不会立即被清理）
                        s._createdTime = Date.now();
                        repairedCount++;
                    }
                    if (!s._hasCompletionSummary) {
                        // ✅ v=32: 初始化任务总结标志位 - 从response推断
                        s._hasCompletionSummary = !!(s.response && s.response.includes('**✅ 任务完成**'));
                        repairedCount++;
                    }
                    s._version = 1;
                }

                // ✅ 数据完整性修复：如果session已使用但actions为空，尝试深度加载
                if (s.id.startsWith('ses_') && s.phases && s.phases.length > 0) {
                    if (!s.actions || s.actions.length === 0) {
                        // ✅ 修复C4: 使用统一的_isLoading标志防止竞态条件
                        if (!s._isLoading && !s._deepLoaded) {
                            console.log('[loadState] Detected used session with empty actions, triggering deep load:', s.id);
                            s._isLoading = true;
                            // ✅ 修复C1: 不要过早设置_deepLoaded，在成功后才设置

                            // 异步深度加载（不阻塞UI）
                            if (typeof apiClient !== 'undefined') {
                                apiClient.getMessages(s.id).then(data => {
                                    if (data && data.messages && data.messages.length > 0) {
                                        console.log('[loadState] Deep load recovered messages for', s.id);
                                        s.response = '';
                                        s.actions = [];
                                        s.orphanEvents = [];

                                        data.messages.forEach(msg => {
                                            if (msg.role === 'user') {
                                                const userText = msg.parts?.[0]?.content?.text || msg.parts?.[0]?.text;
                                                if (userText) s.prompt = userText;
                                            } else {
                                                msg.parts?.forEach(part => {
                                                    if (part.type === 'text') {
                                                        s.response += (part.content?.text || part.text || '');
                                                    } else if (part.type === 'tool' || part.type === 'action') {
                                                        const toolContent = part.content || part;
                                                        const toolEv = {
                                                            type: 'action',
                                                            id: part.id,
                                                            data: {
                                                                tool_name: toolContent.tool || toolContent.tool_name,
                                                                input: toolContent.input || toolContent.state?.input,
                                                                output: toolContent.output || toolContent.state?.output,
                                                                status: toolContent.status || toolContent.state?.status
                                                            }
                                                        };
                                                        s.orphanEvents.push(toolEv);
                                                        s.actions.push(toolEv);
                                                    }
                                                });
                                            }
                                        });

                                        // ✅ 修复C4: 保存修复后的数据并刷新界面
                                        saveState();
                                        console.log('[loadState] Deep load complete and saved:', s.id);

                                        // 如果当前正在查看这个session，刷新界面
                                        if (state.activeId === s.id && typeof renderAll === 'function') {
                                            console.log('[loadState] Refreshing UI for current session');
                                            renderAll();
}


// 项目删除和重命名功能
async function confirmDeleteProject(projectId, projectName) {
    const confirmed = confirm(`确定要删除项目"${projectName}"吗？\n\n项目下的所有任务将被移到"默认项目"中。`);
    if (!confirmed) return;
    
    try {
        await window.apiClient.deleteProject(projectId);
        console.log('[Project] Deleted:', projectId);
        
        // 从本地 state 移除
        window.state.projects = window.state.projects.filter(p => p.id !== projectId);
        
        // 如果删除的是当前选中项目，切换到默认项目
        if (window.state.activeProjectId === projectId) {
            window.state.activeProjectId = null;
        }
        
        // 重新加载会话列表（更新 project_id）
        if (typeof apiClient !== 'undefined') {
            try {
                const sessions = await apiClient.listSessions();
                window.state.sessions = sessions;
            } catch (e) {
                console.warn('[Project] Failed to reload sessions:', e);
            }
        }
        
        saveState();
        renderSidebar();
    } catch (e) {
        console.error('[Project] Delete failed:', e);
        alert('删除项目失败: ' + e.message);
    }
}

async function renameProject(projectId, currentName) {
    const newName = prompt('请输入新的项目名称:', currentName);
    if (!newName || newName.trim() === '') return;
    if (newName === currentName) return;
    
    try {
        const updated = await window.apiClient.updateProject(projectId, newName.trim());
        console.log('[Project] Renamed:', updated);
        
        // 更新本地 state
        const project = window.state.projects.find(p => p.id === projectId);
        if (project) {
            project.name = updated.name;
        }
        
        saveState();
        renderSidebar();
    } catch (e) {
        console.error('[Project] Rename failed:', e);
        alert('重命名项目失败: ' + e.message);
    }
}


                                        // ✅ 修复C1: 成功后才设置_deepLoaded
                                        s._deepLoaded = true;
                                    }
                                }).catch(async (err) => {
                                    console.warn('[loadState] Deep load failed for', s.id, ':', err);

                                    // ✅ v=38.1修复：降级尝试timeline API（从steps表获取工具调用）
                                    if (typeof apiClient !== 'undefined' && apiClient.getTimeline) {
                                        try {
                                            console.log('[loadState] Attempting timeline API fallback for:', s.id);
                                            const timelineData = await apiClient.getTimeline(s.id);

                                            if (timelineData && timelineData.timeline && timelineData.timeline.length > 0) {
                                                // 转换timeline steps为actions格式
                                                s.actions = timelineData.timeline.map(step => ({
                                                    type: 'action',
                                                    id: step.step_id,
                                                    data: {
                                                        tool_name: step.tool_name,
                                                        input: safeParseJSON(step.tool_input, {}),
                                                        output: null, // steps表没有output字段
                                                        status: 'completed',
                                                        action_type: step.action_type,
                                                        file_path: step.file_path
                                                    }
                                                }));

                                                // 同时添加到orphanEvents以保持兼容
                                                s.orphanEvents = [...s.actions];

                                                console.log('[loadState] Timeline fallback successful for:', s.id, '(', s.actions.length, 'actions from timeline)');

                                                // 保存修复后的数据
                                                saveState();
                                                s._deepLoaded = true;
                                            } else {
                                                console.log('[loadState] Timeline API returned empty data for:', s.id);
                                            }
                                        } catch (timelineError) {
                                            console.warn('[loadState] Timeline API fallback also failed:', s.id, timelineError);
                                        }
                                    }
                                    // ✅ 修复C1: 失败时不设置_deepLoaded，允许下次重试
                                }).finally(() => {
                                    s._isLoading = false;
                                });
                            }
                        }
                    }
                }

                // 数据完整性验证
                if (s.actions && !Array.isArray(s.actions)) {
                    console.error('[loadState] Invalid actions array for', s.id, ', resetting');
                    s.actions = [];
                    repairedCount++;
                }
                if (s.orphanEvents && !Array.isArray(s.orphanEvents)) {
                    console.error('[loadState] Invalid orphanEvents array for', s.id, ', resetting');
                    s.orphanEvents = [];
                    repairedCount++;
                }
            }

            if (repairedCount > 0) {
                console.warn(`[loadState] Repaired ${repairedCount} data issues`);
                // 保存修复后的数据
                setTimeout(() => saveState(), 100);
            }

        } catch (e) {
            console.error('Failed to parse saved state:', e);
            // 清理损坏的数据
            localStorage.removeItem('opencode_state');
            state.sessions = [];
            state.activeId = null;
            state.projects = [];
            state.activeProjectId = null;
        }
    }

    // 加载本地保存的 projects（如果后端未返回）
    if (state.projects.length === 0) {
        const savedProjects = localStorage.getItem('opencode_projects');
        if (savedProjects) {
            try {
                state.projects = JSON.parse(savedProjects);
                console.log('[State] Loaded projects from localStorage:', state.projects.length);
            } catch (e) {
                console.warn('[State] Failed to parse saved projects:', e);
                state.projects = [];
            }
        }
    }

    // 加载 activeProjectId
    const savedActiveProjectId = localStorage.getItem('opencode_activeProjectId');
    if (savedActiveProjectId) {
        state.activeProjectId = savedActiveProjectId;
    } else {
        // ✅ 修复：默认选中proj_default项目，确保历史记录能显示
        state.activeProjectId = 'proj_default';
    }

    // 从后端同步 Session 列表
    if (typeof apiClient !== 'undefined') {
        try {
            const backendSessions = await apiClient.listSessions();
            if (backendSessions && backendSessions.length > 0) {
                console.log('[Sync] Found', backendSessions.length, 'sessions from backend');
                const merged = [...state.sessions];
                backendSessions.forEach(bs => {
                    const existingIdx = merged.findIndex(s => s.id === bs.id);
                    if (existingIdx >= 0) {
                        // ✅ 修复：保留本地完整数据，只更新后端字段
                        const local = merged[existingIdx];
                        console.log('[Sync] Merging session', bs.id, '- local has', local.actions?.length, 'actions');
                        merged[existingIdx] = {
                            ...local,  // 保留所有本地字段（response, actions, orphanEvents, phases等）
                            title: bs.title,
                            status: bs.status
                        };
                    } else {
                        // 新 session，添加到列表
                        console.log('[Sync] Adding new session', bs.id);
                        merged.push({
                            id: bs.id,
                            title: bs.title,
                            status: bs.status,
                            prompt: bs.title,
                            response: '',
                            phases: [],
                            actions: [],
                            orphanEvents: [],
                            mode: bs.mode || null,
                            project_id: bs.project_id || 'proj_default',  // ✅ 修复：确保project_id有默认值
                            _version: 1,
                            _createdTime: Date.now()  // ✅ 添加创建时间，用于宽限期判断
                        });
                    }
                });
                state.sessions = merged;
                console.log('[Sync] Total sessions after merge:', state.sessions.length);

                // ✅ v=37修复：对新发现的session，异步深度加载完整内容
                // 避免创建空session导致刷新后数据丢失
                const newSessions = backendSessions.filter(bs =>
                    !state.sessions.find(s => s.id === bs.id) ||
                    (state.sessions.find(s => s.id === bs.id)?.actions?.length === 0)
                );

                if (newSessions.length > 0) {
                    console.log('[Sync] Deep loading', newSessions.length, 'new sessions...');
                    newSessions.forEach(async bs => {
                        const session = state.sessions.find(s => s.id === bs.id);
                        if (!session || session._isLoading) return;

                        session._isLoading = true;
                        try {
                            const data = await apiClient.getMessages(bs.id);
                            if (data && data.messages) {
                                // 转换后端消息格式到前端 state 格式
                                session.response = '';
                                session.phases = [];
                                session.orphanEvents = [];
                                session.actions = [];

                                data.messages.forEach(msg => {
                                    if (msg.role === 'user') {
                                        const userText = msg.parts?.[0]?.content?.text || msg.parts?.[0]?.text;
                                        if (userText) session.prompt = userText;
                                    } else {
                                        msg.parts?.forEach(part => {
                                            if (part.type === 'text') {
                                                session.response += (part.content?.text || part.text || '');
                                            } else if (part.type === 'tool' || part.type === 'action') {
                                                const toolContent = part.content || part;
                                                const toolEv = {
                                                    type: 'action',
                                                    id: part.id,
                                                    data: {
                                                        tool_name: toolContent.tool || toolContent.tool_name,
                                                        input: toolContent.input || toolContent.state?.input,
                                                        output: toolContent.output || toolContent.state?.output,
                                                        status: toolContent.status || toolContent.state?.status
                                                    }
                                                };
                                                session.orphanEvents.push(toolEv);
                                                session.actions.push(toolEv);
                                            }
                                        });
                                    }
                                });

                                console.log('[Sync] Deep load complete for:', bs.id, '(', session.actions.length, 'actions)');
                            }
                        } catch (e) {
                            console.warn('[Sync] Failed to deep load', bs.id, ':', e);

                            // ✅ v=38.1修复：降级尝试timeline API（从steps表获取工具调用）
                            if (typeof apiClient !== 'undefined' && apiClient.getTimeline) {
                                try {
                                    console.log('[Sync] Attempting timeline API fallback for:', bs.id);
                                    const timelineData = await apiClient.getTimeline(bs.id);

                                    if (timelineData && timelineData.timeline && timelineData.timeline.length > 0) {
                                        // 转换timeline steps为actions格式
                                        session.actions = timelineData.timeline.map(step => ({
                                            type: 'action',
                                            id: step.step_id,
                                            data: {
                                                tool_name: step.tool_name,
                                                input: step.tool_input ? JSON.parse(step.tool_input) : {},
                                                output: null, // steps表没有output字段
                                                status: 'completed',
                                                action_type: step.action_type,
                                                file_path: step.file_path
                                            }
                                        }));

                                        // 同时添加到orphanEvents以保持兼容
                                        session.orphanEvents = [...session.actions];

                                        console.log('[Sync] Timeline fallback successful for:', bs.id, '(', session.actions.length, 'actions from timeline)');
                                    } else {
                                        console.log('[Sync] Timeline API returned empty data for:', bs.id);
                                    }
                                } catch (timelineError) {
                                    console.warn('[Sync] Timeline API fallback also failed:', bs.id, timelineError);
                                }
                            }
                        } finally {
                            session._isLoading = false;
                        }
                    });

                    // 等待所有深度加载完成后保存
                    setTimeout(() => {
                        console.log('[Sync] Saving state after deep loads');
                        saveState();
                    }, 1000);
                } else {
                    // 没有新session，直接保存
                    setTimeout(() => saveState(), 100);
                }
            }
        } catch (e) {
            console.warn('[Sync] Failed to sync sessions from backend:', e);
        }
    }

    // 加载 projects
    if (typeof apiClient !== 'undefined') {
        try {
            const projects = await apiClient.listProjects();
            if (projects && projects.length > 0) {
                state.projects = projects;
                console.log('[State] Loaded projects from API:', state.projects.length);
            } else {
                console.log('[State] API returned empty, using local cache');
            }
        } catch (e) {
            console.warn('[State] Failed to load projects from API, using local cache:', e);
            // 不清空 state.projects，保留 localStorage 的数据
        }
    }

    renderAll();
}


function renderSidebar() {
    const list = el('#session-list'); if (!list) return;
    list.innerHTML = '';
    
    const { sessions, projects, activeId, activeProjectId } = state;
    
    // 如果有项目，按项目分组显示
    if (projects && projects.length > 0) {
        projects.forEach(project => {
            // 获取该项目下的会话
            // ✅ 修复：兼容没有project_id的旧session，默认分配到proj_default
            const projectSessions = sessions.filter(s => (s.project_id || 'proj_default') === project.id);
            
            // 创建项目分组
            const projectItem = document.createElement('div');
            projectItem.className = 'project-group mb-2';
            
            // 项目标题
            const projectHeader = document.createElement('div');
            projectHeader.className = `project-header group flex items-center gap-2 px-3 py-2 
                rounded-lg cursor-pointer transition-colors
                ${activeProjectId === project.id ? 'bg-blue-100 dark:bg-blue-900' : 'hover:bg-gray-100 dark:hover:bg-gray-700'}`;
            projectHeader.innerHTML = `
                <span class="material-symbols-outlined text-[18px] text-gray-500">
                    ${project.id === 'proj_default' ? 'folder' : 'folder_open'}
                </span>
                <span class="flex-1 text-sm font-medium text-gray-700 dark:text-gray-200 truncate project-name"
                    ondblclick="event.stopPropagation(); renameProject('${project.id}', '${project.name.replace(/'/g, "\\'")}')"
                    title="双击重命名">
                    ${project.name}
                </span>
                <span class="text-xs text-gray-400">${projectSessions.length}</span>
                <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    ${project.id !== 'proj_default' ? `
                    <button class="p-1 hover:bg-blue-100 dark:hover:bg-blue-900 rounded" 
                        onclick="event.stopPropagation(); renameProject('${project.id}', '${project.name.replace(/'/g, "\\'")}')"
                        title="重命名项目">
                        <span class="material-symbols-outlined text-[16px] text-gray-400 hover:text-blue-600">edit</span>
                    </button>
                    <button class="p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded"
                        onclick="event.stopPropagation(); confirmDeleteProject('${project.id}', '${project.name.replace(/'/g, "\\'")}')"
                        title="删除项目">
                        <span class="material-symbols-outlined text-[16px] text-gray-400 hover:text-red-600">delete</span>
                    </button>
                    ` : ''}
                </div>
            `;
            
            // 点击项目展开/折叠
            projectHeader.onclick = () => {
                state.activeProjectId = state.activeProjectId === project.id ? null : project.id;
                saveState();
                renderSidebar();
            };
            
            projectItem.appendChild(projectHeader);
            
            // 如果项目展开，显示会话列表
            if (activeProjectId === project.id || project.id === 'proj_default') {
                const sessionList = document.createElement('div');
                sessionList.className = 'session-list ml-4 mt-1';
                
                if (projectSessions.length === 0) {
                    sessionList.innerHTML = '<div class="text-xs text-gray-400 px-3 py-2">暂无任务</div>';
                } else {
                    projectSessions.forEach(s => {
                        const isActive = s.id === activeId;
                        const item = document.createElement('div');
                        item.className = `session-item group cursor-pointer mb-1 px-3 py-2 rounded-lg transition-all 
                            ${isActive ? 'bg-blue-50 dark:bg-blue-900/50 border-l-4 border-blue-500' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`;
                        item.innerHTML = `
                            <div class="flex items-center justify-between gap-2">
                                <div class="flex items-center gap-2 flex-1 min-w-0">
                                    <span class="material-symbols-outlined text-[14px] text-gray-400">task</span>
                                    <span class="session-item-title text-sm text-gray-700 dark:text-gray-200 truncate">
                                        ${s.prompt ? (s.prompt.substring(0, 20) + '...') : 'New Task'}
                                    </span>
                                </div>
                                <button class="session-delete-btn opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded"
                                    onclick="event.stopPropagation(); deleteSession('${s.id}')" title="删除任务">
                                    <span class="material-symbols-outlined text-[16px] text-gray-400 hover:text-red-600">delete</span>
                                </button>
                            </div>
                        `;
                        item.onclick = async () => {
                            console.log('[点击历史记录] session:', s);
                            console.log('[点击历史记录] actions length:', s.actions?.length);
                            console.log('[点击历史记录] response length:', s.response?.length);
                            state.activeId = s.id;

                            // 避免重复加载
                            if (s._isLoading) {
                                console.log('[History] Already loading, skipping...');
                                return;
                            }

                            // 如果是新 API Session 且本地数据不完整（刷新后），从后端深度加载
                            if (s.id.startsWith('ses_') && (!s.actions || s.actions.length === 0)) {
                                s._isLoading = true;
                                console.log('[History] Deep loading session content for:', s.id, '(actions:', s.actions?.length, ')');
                                try {
                                    const data = await apiClient.getMessages(s.id);
                                    if (data && data.messages) {
                                        // 转换后端消息格式到前端 state 格式
                                        s.response = '';
                                        s.phases = [];
                                        s.orphanEvents = [];
                                        s.actions = [];

                                        data.messages.forEach(msg => {
                                            if (msg.role === 'user') {
                                                // 更新 Prompt（如果有的话）
                                                const userText = msg.parts?.[0]?.content?.text || msg.parts?.[0]?.text;
                                                if (userText) s.prompt = userText;
                                            } else {
                                                msg.parts?.forEach(part => {
                                                    if (part.type === 'text') {
                                                        s.response += (part.content?.text || part.text || '');
                                                    } else if (part.type === 'tool' || part.type === 'action') {
                                                        const toolContent = part.content || part;
                                                        const toolEv = {
                                                            type: 'action',
                                                            id: part.id,
                                                            data: {
                                                                tool_name: toolContent.tool || toolContent.tool_name,
                                                                input: toolContent.input || toolContent.state?.input,
                                                                output: toolContent.output || toolContent.state?.output,
                                                                status: toolContent.status || toolContent.state?.status
                                                            }
                                                        };
                                                        s.orphanEvents.push(toolEv);
                                                        s.actions.push(toolEv);
                                                    }
                                                });
                                            }
                                        });
                                        console.log('[History] Deep load complete for:', s.id);

                                        // 保存到localStorage，下次无需重新加载
                                        saveState();
                                    }
                                } catch (e) {
                                    console.warn('[History] Failed to fetch session messages:', e);
                                    console.error('无法加载历史任务，请检查网络连接或刷新页面重试');
                                } finally {
                                    s._isLoading = false;
                                }
                            }

                            // 清空右侧面板内容，避免显示旧会话的内容
                            if (window.rightPanelManager) {
                                // 重置预览状态
                                window.rightPanelManager.currentMode = null;
                                window.rightPanelManager.currentFilename = null;

                                // 清空文件编辑器内容
                                const contentDiv = document.getElementById('file-editor-content');
                                if (contentDiv) {
                                    contentDiv.innerHTML = `
                                        <div class="text-gray-400 dark:text-gray-500 text-center py-8 text-sm">
                                            等待文件操作...
                                        </div>
                                    `;
                                }

                                // 隐藏 web preview
                                if (window.rightPanelManager.webPreviewContainer) {
                                    window.rightPanelManager.webPreviewContainer.classList.add('hidden');
                                    const iframe = document.getElementById('web-preview-iframe');
                                    if (iframe) {
                                        iframe.src = 'about:blank';
                                    }
                                }

                                // 隐藏 file editor
                                if (window.rightPanelManager.fileEditorContainer) {
                                    window.rightPanelManager.fileEditorContainer.classList.add('hidden');
                                }

                                // 隐藏 VNC iframe（如果存在）
                                const vncIframe = document.getElementById('uvn-frame');
                                if (vncIframe) {
                                    vncIframe.style.display = 'none';
                                }

                                // 隐藏右侧面板
                                window.rightPanelManager.hide();
                            }

                            renderAll();
                            saveState();
                        };
                        sessionList.appendChild(item);
                    });
                }
                
                projectItem.appendChild(sessionList);
            }
            
            list.appendChild(projectItem);
        });
    } else {
        // 没有项目时，平铺显示所有会话（兼容旧数据）
        sessions.forEach(s => {
            const item = document.createElement('div');
            const isActive = s.id === activeId;
            item.className = `session-item cursor-pointer mb-1 transition-all ${isActive ? 'active' : ''}`;
            item.innerHTML = `
                <div class="session-item-icon">
                    <span class="material-symbols-outlined text-[14px]">task</span>
                </div>
                <span class="session-item-title">${s.prompt ? (s.prompt.substring(0, 24) + (s.prompt.length > 24 ? '...' : '')) : 'New Task'}</span>
                <button class="session-delete-btn" onclick="event.stopPropagation(); deleteSession('${s.id}')">
                    <span class="material-symbols-outlined text-[16px]">delete</span>
                </button>
            `;
            item.onclick = async () => {
                console.log('[点击历史记录] session:', s);
                console.log('[点击历史记录] actions length:', s.actions?.length);
                console.log('[点击历史记录] response length:', s.response?.length);
                state.activeId = s.id;

                // 避免重复加载
                if (s._isLoading) {
                    console.log('[History] Already loading, skipping...');
                    return;
                }

                // 如果是新 API Session 且本地数据不完整（刷新后），从后端深度加载
                if (s.id.startsWith('ses_') && (!s.actions || s.actions.length === 0)) {
                    s._isLoading = true;
                    console.log('[History] Deep loading session content for:', s.id, '(actions:', s.actions?.length, ')');
                    try {
                        const data = await apiClient.getMessages(s.id);
                        if (data && data.messages) {
                            // 转换后端消息格式到前端 state 格式
                            s.response = '';
                            s.phases = [];
                            s.orphanEvents = [];
                            s.actions = [];

                            data.messages.forEach(msg => {
                                if (msg.role === 'user') {
                                    // 更新 Prompt（如果有的话）
                                    const userText = msg.parts?.[0]?.content?.text || msg.parts?.[0]?.text;
                                    if (userText) s.prompt = userText;
                                } else {
                                    msg.parts?.forEach(part => {
                                        if (part.type === 'text') {
                                            s.response += (part.content?.text || part.text || '');
                                        } else if (part.type === 'tool' || part.type === 'action') {
                                            const toolContent = part.content || part;
                                            const toolEv = {
                                                type: 'action',
                                                id: part.id,
                                                data: {
                                                    tool_name: toolContent.tool || toolContent.tool_name,
                                                    input: toolContent.input || toolContent.state?.input,
                                                    output: toolContent.output || toolContent.state?.output,
                                                    status: toolContent.status || toolContent.state?.status
                                                }
                                            };
                                            s.orphanEvents.push(toolEv);
                                            s.actions.push(toolEv);
                                        }
                                    });
                                }
                            });
                            console.log('[History] Deep load complete for:', s.id);

                            // 保存到localStorage，下次无需重新加载
                            saveState();
                        }
                    } catch (e) {
                        console.warn('[History] Failed to fetch session messages:', e);
                        console.error('无法加载历史任务，请检查网络连接或刷新页面重试');
                    } finally {
                        s._isLoading = false;
                    }
                }

                // 清空右侧面板内容，避免显示旧会话的内容
                if (window.rightPanelManager) {
                    // 重置预览状态
                    window.rightPanelManager.currentMode = null;
                    window.rightPanelManager.currentFilename = null;

                    // 清空文件编辑器内容
                    const contentDiv = document.getElementById('file-editor-content');
                    if (contentDiv) {
                        contentDiv.innerHTML = `
                            <div class="text-gray-400 dark:text-gray-500 text-center py-8 text-sm">
                                等待文件操作...
                            </div>
                        `;
                    }

                    // 隐藏 web preview
                    if (window.rightPanelManager.webPreviewContainer) {
                        window.rightPanelManager.webPreviewContainer.classList.add('hidden');
                        const iframe = document.getElementById('web-preview-iframe');
                        if (iframe) {
                            iframe.src = 'about:blank';
                        }
                    }

                    // 隐藏 file editor
                    if (window.rightPanelManager.fileEditorContainer) {
                        window.rightPanelManager.fileEditorContainer.classList.add('hidden');
                    }

                    // 隐藏 VNC iframe（如果存在）
                    const vncIframe = document.getElementById('uvn-frame');
                    if (vncIframe) {
                        vncIframe.style.display = 'none';
                    }

                    // 隐藏右侧面板
                    window.rightPanelManager.hide();
                }

                renderAll();
                saveState();
            };
            list.appendChild(item);
        });
    }
}

function deleteSession(sessionId) {
    if (!confirm('确定要删除这条任务记录吗？')) return;

    const index = state.sessions.findIndex(s => s.id === sessionId);
    if (index !== -1) {
        state.sessions.splice(index, 1);

        // 如果删除的是当前活动会话
        if (state.activeId === sessionId) {
            if (state.sessions.length > 0) {
                // 切换到相邻的一个
                const nextIndex = Math.min(index, state.sessions.length - 1);
                state.activeId = state.sessions[nextIndex].id;
            } else {
                // 没有会话了，显示欢迎界面
                state.activeId = null;
                const welcome = el('#welcome-interface');
                const scrollArea = el('#chat-scroll-area');
                if (welcome && scrollArea) {
                    welcome.classList.remove('hidden');
                    // 清空显示区域
                    const container = scrollArea.querySelector('.max-w-4xl');
                    if (container) {
                        // 移除除 welcome 之外的所有内容（如果有的话）
                    }
                }
            }
        }

        renderSidebar();
        renderAll();
        saveState();
    }
}

async function openFile(filePath) {
    const ext = filePath.split('.').pop().toLowerCase();
    const renderable = ['html', 'htm', 'png', 'jpg', 'jpeg', 'gif', 'pdf', 'svg'];

    // Switch to preview tab if it's a renderable file
    if (renderable.includes(ext)) {
        // 首先确保右侧面板展开并切换到预览标签
        if (typeof togglePanel === 'function') {
            togglePanel('preview');
        }

        const frame = el('#uvn-frame');
        if (frame) {
            frame.src = `/opencode/get_file_content?path=${encodeURIComponent(filePath)}`;
        }
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
        const res = await fetch(`/opencode/list_session_files?sid=${s.id}`);
        const data = await res.json();
        let files = data.files || [];

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
                item.className = 'file-item group cursor-pointer';
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
    
    // 欢迎页面时清空右侧预览面板，避免显示旧会话的内容
    if (!s && window.rightPanelManager) {
        window.rightPanelManager.clearPreview && window.rightPanelManager.clearPreview();
    }
    
    if (!s) { return; }

    // Use enhanced task panel if available
    if (typeof renderEnhancedTaskPanel === 'function') {
        console.log('[OpenCode] Using enhanced task panel');
        const enhancedPanel = renderEnhancedTaskPanel(s);
        convo.appendChild(enhancedPanel);
        const area = el('#chat-scroll-area');
        area.scrollTop = area.scrollHeight;
        return;
    } else {
        console.warn('[OpenCode] Enhanced task panel not available, using fallback rendering');
    }

    if (s.prompt) {
        const pSep = '\n\n---\n\n';
        const prompts = s.prompt.split(pSep);
        prompts.forEach(p => {
            const m = document.createElement('div');
            m.className = 'message-bubble user-bubble animate-fade-in self-end mb-6 text-sm shadow-md';
            m.textContent = p;
            convo.appendChild(m);
        });
    }

    const renderEvent = (ev) => {
        const card = document.createElement('div');
        card.className = 'tool-card border border-border-light dark:border-border-dark rounded-[2rem] mb-3 bg-white dark:bg-surface-dark shadow-sm overflow-hidden transition-all duration-300';

        const isThought = ev.type === 'thought';
        const svgIcon = isThought ? TOOL_SVG_ICONS['thought'] : TOOL_SVG_ICONS['default'];
        const toolName = ev.tool || 'Kernel Process';
        const label = isThought ? TOOL_LABELS['thought'] : (TOOL_LABELS[toolName] || TOOL_LABELS['default']);
        const title = isThought ? TOOL_LABELS['thought'] : `Using ${toolName}`;

        card.innerHTML = `
            <div class="card-header p-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                <div class="flex items-center gap-2">
                    ${svgIcon}
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-200">${label}</span>
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
        const rSep = '\n\n---\n\n**新的回答：**\n\n';
        const responses = s.response.split(rSep);
        responses.forEach(resp => {
            const r = document.createElement('div');
            r.className = 'message-bubble assistant-bubble animate-fade-in max-w-[90%] text-sm leading-relaxed mt-6 prose dark:prose-invert';
            r.innerHTML = marked.parse(resp);
            convo.appendChild(r);
        });
    }

    const area = el('#chat-scroll-area');
    area.scrollTop = area.scrollHeight;

    // Save state on every render to ensure latest progress is saved
    saveState();

    // Update interface mode based on session content
    if (window.updateInterfaceMode) {
        window.updateInterfaceMode();
    }
}

function parseLogLine(line, s) {
    if (!line || !line.trim()) return;

    // Try to parse as JSON first
    if (line.trim().startsWith('{') && line.trim().endsWith('}')) {
        try {
            const event = JSON.parse(line);
            const eventType = event.type;

            if (eventType === 'step_start') {
                // 激活第一个 pending 状态的阶段
                if (s.phases && s.phases.length > 0) {
                    const firstPending = s.phases.find(p => p.status === 'pending');
                    if (firstPending) {
                        firstPending.status = 'active';
                        s.currentPhase = firstPending.id;
                    }
                }
            } else if (eventType === 'tool_use') {
                const part = event.part || {};
                const toolName = part.tool;
                const state = part.state || {};
                const status = state.status;
                const output = state.output || "";

                const toolEvent = {
                    type: "activate",
                    tool: toolName,
                    status: status,
                    output: output
                };

                // Add to actions
                if (!s.actions) s.actions = [];
                s.actions.push(toolEvent);

                // Add to events
                if (s.currentPhase) {
                    const phase = s.phases.find(p => p.id === s.currentPhase);
                    if (phase) {
                        if (!phase.events) phase.events = [];
                        phase.events.push(toolEvent);
                    }
                } else {
                    if (!s.orphanEvents) s.orphanEvents = [];
                    s.orphanEvents.push(toolEvent);
                }

                // If output exists, also show as text
                if (output) {
                    s.response += `\n\`${toolName}\` output:\n${output}\n`;
                }
            } else if (eventType === 'text') {
                const chunk = (event.part || {}).text || "";
                if (chunk) s.response += chunk;
            } else if (eventType === 'error') {
                const errMsg = event.message || "Unknown error";
                const errEvent = { type: "error", content: errMsg };
                if (s.currentPhase) {
                    const phase = s.phases.find(p => p.id === s.currentPhase);
                    if (phase) {
                        if (!phase.events) phase.events = [];
                        phase.events.push(errEvent);
                    }
                } else {
                    if (!s.orphanEvents) s.orphanEvents = [];
                    s.orphanEvents.push(errEvent);
                }
            }
            return;
        } catch (e) {
            // Not valid JSON, fall through to text parsing
        }
    }

    // Text parsing (Thought regex)
    const thoughtMatch = line.match(/(?:🤔\s*Thought:|Thought:|Thought\s*>\s*|思考[:：])\s*(.*)/i);
    if (thoughtMatch) {
        const content = thoughtMatch[1].trim();
        if (content) {
            const thoughtEvent = { type: "thought", content: content };
            if (s.currentPhase) {
                const phase = s.phases.find(p => p.id === s.currentPhase);
                if (phase) {
                    if (!phase.events) phase.events = [];
                    phase.events.push(thoughtEvent);
                }
            } else {
                if (!s.orphanEvents) s.orphanEvents = [];
                s.orphanEvents.push(thoughtEvent);
            }

            // 激活第一个 pending 状态的阶段（如果有）
            if (s.phases && s.phases.length > 0) {
                const firstPending = s.phases.find(p => p.status === 'pending');
                if (firstPending) {
                    firstPending.status = 'active';
                    s.currentPhase = firstPending.id;
                }
            }
        }
        return;
    }

    // Regular text (skip noise)
    const noiseKeywords = ["opencode run", "options:", "positionals:", "message  message to send", "run opencode with"];
    if (!noiseKeywords.some(k => line.toLowerCase().includes(k))) {
        s.response += line + "\n";
    }
}

async function startPolling(sid) {
    console.log(`[Polling] Starting polling for session ${sid}`);
    const s = state.sessions.find(x => x.id === sid);
    if (!s) return;

    // Initialize polling state if not exists
    if (typeof s.logOffset === 'undefined') s.logOffset = 0;

    const poll = async () => {
        // If session changed active, we might still want to poll in background, 
        // but for now let's only poll if it's the active one or just poll regardless?
        // Better to poll regardless to keep data up to date.

        try {
            const res = await fetch(`/opencode/get_log?sid=${sid}&offset=${s.logOffset}`);
            const data = await res.json();

            if (data.content) {
                // Parse new content
                const lines = data.content.split('\n');
                lines.forEach(line => parseLogLine(line, s));

                s.logOffset = data.next_offset;
                renderResults();
                renderFiles(); // Update files if any
            }

            if (data.status === 'completed' || data.status === 'done') {
                console.log(`[Polling] Task completed`);
                // 标记所有未完成的阶段为 completed
                if (s.phases && s.phases.length > 0) {
                    s.phases.forEach(p => {
                        if (p.status !== 'completed') {
                            p.status = 'completed';
                        }
                    });
                }
                renderResults();
                return; // Stop polling
            } else if (data.status === 'error') {
                console.error(`[Polling] Task error`);
                return;
            }

            // Schedule next poll
            setTimeout(poll, 2000); // Poll every 2 seconds

        } catch (e) {
            console.error("[Polling] Error fetching log:", e);
            setTimeout(poll, 5000); // Retry later
        }
    };

    poll();
}

function bindUI() {
    // Welcome Interface Logic
    const welcomeInterface = el('#welcome-interface');
    const chatMessages = el('#chat-messages');
    const bottomInputContainer = el('#bottom-input-container');
    const promptWelcome = el('#prompt-welcome');
    const promptBottom = el('#prompt');
    const runStreamWelcome = el('#runStream-welcome');
    const taskTags = els('.task-tag');

    // Function to switch to chat mode (bottom input)
    function switchToChatMode() {
        if (welcomeInterface) welcomeInterface.classList.add('hidden');
        if (chatMessages) {
            chatMessages.classList.remove('hidden');
        }
        if (bottomInputContainer) {
            bottomInputContainer.classList.remove('hidden');
        }
        // 显示文件和预览按钮
        const filesPreviewButtons = el('#files-preview-buttons');
        if (filesPreviewButtons) {
            filesPreviewButtons.classList.remove('hidden');
        }
    }

    // Function to switch back to welcome mode
    function switchToWelcomeMode() {
        if (welcomeInterface) welcomeInterface.classList.remove('hidden');
        if (chatMessages) chatMessages.classList.add('hidden');
        if (bottomInputContainer) bottomInputContainer.classList.add('hidden');
        // 隐藏文件和预览按钮
        const filesPreviewButtons = el('#files-preview-buttons');
        if (filesPreviewButtons) {
            filesPreviewButtons.classList.add('hidden');
        }
    }

    // Task Tag Selection Logic
    const tagSuggestions = {
        '生成幻灯片': [
            '帮我创建一个关于人工智能的产品介绍PPT',
            '生成一个技术分享的演示文稿'
        ],
        '撰写文档': [
            '帮我为智能家居行业起草一个竞品对比框架',
            '写一篇纽约时报风格的文章，报道最新热点新闻'
        ],
        '生成设计': [
            '设计一个现代化的移动应用界面',
            '创建一个简洁的品牌Logo'
        ],
        '创建故事绘本': [
            '创作一个关于友谊的儿童绘本故事',
            '编写一个科幻短篇故事'
        ],
        '批量调研': [
            '帮我搜集10家同行业公司的最新动态',
            '调研2024年AI行业的发展趋势'
        ],
        '分析数据': [
            '给我一个家庭健身市场的快速概览，并提取主要结论',
            '分析这组销售数据，找出增长机会'
        ],
        '创建网页': [
            '帮我创建一个响应式的个人博客网站',
            '开发一个产品落地页'
        ],
        '翻译PDF': [
            '帮我翻译这份PDF文档',
            '将PDF内容翻译成中文'
        ],
        '总结视频': [
            '总结这个YouTube视频的主要内容',
            '提取视频中的关键信息点'
        ],
        '转写音频': [
            '将这段音频转写成文字',
            '把会议录音转写为文档'
        ]
    };

    taskTags.forEach(tagBtn => {
        tagBtn.onclick = () => {
            const tagName = tagBtn.getAttribute('data-tag');
            const suggestions = tagSuggestions[tagName] || [];

            // Clear all active states
            taskTags.forEach(t => {
                t.classList.remove('bg-blue-50', 'border-blue-500', 'text-blue-600', 'dark:bg-blue-900/20', 'dark:border-blue-500', 'dark:text-blue-400');
                t.classList.add('bg-gray-50', 'border-gray-200', 'dark:bg-gray-800', 'dark:border-gray-700');
            });

            // Set active state for clicked tag
            tagBtn.classList.remove('bg-gray-50', 'border-gray-200', 'dark:bg-gray-800', 'dark:border-gray-700');
            tagBtn.classList.add('bg-blue-50', 'border-blue-500', 'text-blue-600', 'dark:bg-blue-900/20', 'dark:border-blue-500', 'dark:text-blue-400');

            // Show selected tag in input area
            const selectedTagsContainer = el('#selected-tags-container');
            if (selectedTagsContainer) {
                selectedTagsContainer.classList.remove('hidden');
                selectedTagsContainer.innerHTML = `
                    <div class="inline-flex items-center gap-1.5 px-3 py-1 bg-[#f1f5ff] text-[#4d7fff] rounded-full text-sm font-light dark:bg-blue-900/30 dark:text-blue-300">
                        <span class="material-symbols-outlined text-base font-light">description</span>
                        <span class="tracking-wide">${tagName}</span>
                        <button class="ml-0.5 hover:opacity-70 flex items-center close-selected-tag">
                            <span class="material-symbols-outlined text-[14px] font-light">close</span>
                        </button>
                    </div>
                `;

                // Add close button functionality
                const closeBtn = selectedTagsContainer.querySelector('.close-selected-tag');
                if (closeBtn) {
                    closeBtn.onclick = () => {
                        selectedTagsContainer.classList.add('hidden');
                        selectedTagsContainer.innerHTML = '';
                        taskTags.forEach(t => {
                            t.classList.remove('bg-blue-50', 'border-blue-500', 'text-blue-600', 'dark:bg-blue-900/20', 'dark:border-blue-500', 'dark:text-blue-400');
                            t.classList.add('bg-gray-50', 'border-gray-200', 'dark:bg-gray-800', 'dark:border-gray-700');
                        });
                        el('#tag-suggestions')?.classList.add('hidden');
                    };
                }
            }

            // Update placeholder
            if (promptWelcome) {
                promptWelcome.placeholder = `请输入${tagName}的具体要求...`;

                // Show suggestions below the input
                let suggestionsDiv = el('#tag-suggestions');
                if (suggestionsDiv) {
                    suggestionsDiv.innerHTML = suggestions.map(text => `
                        <button class="suggestion-item w-full text-left py-2.5 px-4 rounded-xl text-gray-500 hover:text-gray-900 transition-all text-[15px] font-light tracking-wide" onclick="document.querySelector('#prompt-welcome').value = '${text.replace(/'/g, "\\'")}';document.querySelector('#tag-suggestions').classList.add('hidden');">
                            ${text}
                        </button>
                    `).join('');
                    suggestionsDiv.classList.remove('hidden');
                }
            }
        };
    });

    // Sync both inputs
    if (promptWelcome && promptBottom) {
        promptWelcome.addEventListener('input', (e) => {
            promptBottom.value = e.target.value;
        });
        promptBottom.addEventListener('input', (e) => {
            promptWelcome.value = e.target.value;
        });
    }

    // Handle welcome input submit
    if (runStreamWelcome) {
        runStreamWelcome.onclick = () => {
            if (promptWelcome && promptBottom) {
                promptBottom.value = promptWelcome.value;
                const runBtn = el('#runStream');
                if (runBtn) runBtn.click();
                switchToChatMode();
            }
        };
    }

    // Check if should show welcome or chat mode
    function updateInterfaceMode() {
        const activeSession = state.sessions.find(s => s.id === state.activeId);

        console.log('[updateInterfaceMode] 调试信息:');
        console.log('  - activeId:', state.activeId);
        console.log('  - sessions 数量:', state.sessions.length);
        console.log('  - activeSession:', activeSession);

        const hasMessages = activeSession && (
            activeSession.prompt ||
            activeSession.response ||
            (activeSession.phases && activeSession.phases.length > 0) ||
            (activeSession.actions && activeSession.actions.length > 0)
        );

        console.log('  - hasMessages:', hasMessages);
        console.log('  - prompt:', activeSession?.prompt);
        console.log('  - response:', activeSession?.response);

        if (hasMessages) {
            console.log('✓ 切换到聊天模式');
            switchToChatMode();
        } else {
            console.log('✓ 切换到欢迎模式');
            switchToWelcomeMode();
        }
    }

    // Store function in global scope for access in renderResults
    window.updateInterfaceMode = updateInterfaceMode;
    window.openFile = openFile;
    window.togglePanel = togglePanel;

    el('#theme-toggle').onclick = toggleTheme;

    // Sidebar toggle
    const sidebar = el('#sidebar');
    const expandSidebarBtn = el('#expand-sidebar');
    const toggleSidebarBtn = el('#toggle-sidebar');
    const openSidebarBtn = el('#open-sidebar');
    const sidebarContent = el('#sidebar-content');
    const sidebarLogo = el('#sidebar-logo');
    const newTaskBtn = el('#new-task');
    const historyBtn = el('#history-btn');
    const sessionList = el('#session-list');
    const sectionTitle = el('.sidebar-section-title');
    const themeToggle = el('#theme-toggle');
    const profileBtn = el('#my-profile-btn');
    const profileAvatar = el('#profile-avatar');
    const bottomSettings = el('#bottom-settings');

    if (toggleSidebarBtn) {
        toggleSidebarBtn.onclick = () => {
            sidebar.classList.add('collapsed');
            sidebar.style.width = '64px';
            sidebar.style.minWidth = '64px';
            sidebar.style.maxWidth = '64px';

            if (sidebarLogo) sidebarLogo.style.display = 'none';
            toggleSidebarBtn.style.display = 'none';
            expandSidebarBtn.classList.remove('hidden');

            if (sessionList) sessionList.style.display = 'none';
            if (sectionTitle) sectionTitle.style.display = 'none';
            if (historyBtn) historyBtn.classList.remove('hidden');

            if (newTaskBtn) {
                newTaskBtn.style.padding = '12px';
                newTaskBtn.style.margin = '8px';
                newTaskBtn.style.minWidth = '48px';
                newTaskBtn.style.justifyContent = 'center';
                const newTaskParent = newTaskBtn.parentElement;
                if (newTaskParent) {
                    newTaskParent.style.display = 'flex';
                    newTaskParent.style.justifyContent = 'center';
                }
                const textSpan = newTaskBtn.querySelector('span:not(.material-symbols-outlined)');
                if (textSpan) textSpan.style.display = 'none';
            }

            // Handle bottom settings area - collapse to icon only
            if (bottomSettings) {
                bottomSettings.style.padding = '8px';
                bottomSettings.style.flexDirection = 'column';
                bottomSettings.style.gap = '8px';
            }

            // Collapse profile button to icon only
            if (profileBtn) {
                profileBtn.style.padding = '12px';
                profileBtn.style.margin = '0';
                profileBtn.style.minWidth = '48px';
                profileBtn.style.justifyContent = 'center';
                // Hide avatar and text
                if (profileAvatar) profileAvatar.style.display = 'none';
                const flex1Div = profileBtn.querySelector('.flex-1');
                if (flex1Div) flex1Div.style.display = 'none';
            }

            // Theme button stays as is (already an icon button)
            if (themeToggle) {
                themeToggle.style.width = '48px';
                themeToggle.style.height = '48px';
            }
        };
    }

    if (expandSidebarBtn) {
        expandSidebarBtn.onclick = () => {
            sidebar.classList.remove('collapsed');
            sidebar.style.width = '260px';
            sidebar.style.minWidth = '260px';
            sidebar.style.maxWidth = '260px';

            if (sidebarLogo) sidebarLogo.style.display = 'flex';
            toggleSidebarBtn.style.display = 'flex';
            expandSidebarBtn.classList.add('hidden');

            if (sessionList) sessionList.style.display = '';
            if (sectionTitle) sectionTitle.style.display = '';
            if (historyBtn) historyBtn.classList.add('hidden');

            if (newTaskBtn) {
                newTaskBtn.style.padding = '';
                newTaskBtn.style.margin = '';
                newTaskBtn.style.minWidth = '';
                newTaskBtn.style.justifyContent = '';
                const newTaskParent = newTaskBtn.parentElement;
                if (newTaskParent) {
                    newTaskParent.style.display = '';
                    newTaskParent.style.justifyContent = '';
                }
                const textSpan = newTaskBtn.querySelector('span:not(.material-symbols-outlined)');
                if (textSpan) textSpan.style.display = '';
            }

            // Restore bottom settings area
            if (bottomSettings) {
                bottomSettings.style.padding = '';
                bottomSettings.style.flexDirection = '';
                bottomSettings.style.gap = '';
            }

            // Restore profile button
            if (profileBtn) {
                profileBtn.style.padding = '';
                profileBtn.style.margin = '';
                profileBtn.style.minWidth = '';
                profileBtn.style.justifyContent = '';
                // Show avatar and text
                if (profileAvatar) profileAvatar.style.display = 'flex';
                const flex1Div = profileBtn.querySelector('.flex-1');
                if (flex1Div) flex1Div.style.display = '';
            }

            // Restore theme button size
            if (themeToggle) {
                themeToggle.style.width = '';
                themeToggle.style.height = '';
            }
        };
    }

    if (openSidebarBtn) {
        openSidebarBtn.onclick = () => {
            sidebar.classList.remove('collapsed');
            sidebar.style.width = '260px';
            sidebar.style.minWidth = '260px';
            sidebar.style.maxWidth = '260px';

            if (sidebarLogo) sidebarLogo.style.display = 'flex';
            toggleSidebarBtn.style.display = 'flex';
            expandSidebarBtn.classList.add('hidden');
            openSidebarBtn.classList.add('hidden');

            if (sessionList) sessionList.style.display = '';
            if (sectionTitle) sectionTitle.style.display = '';
            if (historyBtn) historyBtn.classList.add('hidden');

            if (newTaskBtn) {
                newTaskBtn.style.padding = '';
                newTaskBtn.style.margin = '';
                newTaskBtn.style.minWidth = '';
                newTaskBtn.style.justifyContent = '';
                const newTaskParent = newTaskBtn.parentElement;
                if (newTaskParent) {
                    newTaskParent.style.display = '';
                    newTaskParent.style.justifyContent = '';
                }
                const textSpan = newTaskBtn.querySelector('span:not(.material-symbols-outlined)');
                if (textSpan) textSpan.style.display = '';
            }

            // Restore bottom settings area
            if (bottomSettings) {
                bottomSettings.style.padding = '';
                bottomSettings.style.flexDirection = '';
                bottomSettings.style.gap = '';
            }

            // Restore profile button
            if (profileBtn) {
                profileBtn.style.padding = '';
                profileBtn.style.margin = '';
                profileBtn.style.minWidth = '';
                profileBtn.style.justifyContent = '';
                // Show avatar and text
                if (profileAvatar) profileAvatar.style.display = 'flex';
                const flex1Div = profileBtn.querySelector('.flex-1');
                if (flex1Div) flex1Div.style.display = '';
            }

            // Restore theme button size
            if (themeToggle) {
                themeToggle.style.width = '';
                themeToggle.style.height = '';
            }
        };
    }

    // VM Panel toggle
    const vmPanel = el('#vm-panel');
    const closeVmPanelBtn = el('#close-vm-panel');

    if (closeVmPanelBtn) {
        closeVmPanelBtn.onclick = () => {
            vmPanel.classList.remove('w-[45%]');
            vmPanel.classList.add('w-0');

            // Remove active state from top action buttons
            els('.top-action-btn').forEach(b => b.classList.remove('active'));
        };
    }

    // Top action buttons - Files/Preview toggle
    const filesBtn = el('#toggle-files-panel');
    const previewBtn = el('#toggle-preview-panel');

    function togglePanel(panelType) {
        if (!vmPanel) return;

        const isCollapsed = vmPanel.classList.contains('w-0');

        if (isCollapsed) {
            // Expand panel
            vmPanel.classList.remove('w-0');
            vmPanel.classList.add('w-[45%]');

            // Switch to correct tab
            if (panelType === 'files') {
                const filesTabBtn = el('[data-tab="files"]');
                if (filesTabBtn) {
                    els('.tab-btn').forEach(b => b.classList.remove('active-tab'));
                    filesTabBtn.classList.add('active-tab');
                }
                const filesTabPane = el('#tab-files');
                if (filesTabPane) {
                    els('.tab-pane').forEach(p => p.classList.add('hidden'));
                    filesTabPane.classList.remove('hidden');
                }
                if (typeof renderFiles === 'function') renderFiles();
            } else if (panelType === 'preview') {
                const previewTabBtn = el('[data-tab="preview"]');
                if (previewTabBtn) {
                    els('.tab-btn').forEach(b => b.classList.remove('active-tab'));
                    previewTabBtn.classList.add('active-tab');
                }
                const previewTabPane = el('#tab-preview');
                if (previewTabPane) {
                    els('.tab-pane').forEach(p => p.classList.add('hidden'));
                    previewTabPane.classList.remove('hidden');
                }
            }

            // Update top button active states
            els('.top-action-btn').forEach(b => b.classList.remove('active'));
            if (panelType === 'files' && filesBtn) {
                filesBtn.classList.add('active');
            } else if (panelType === 'preview' && previewBtn) {
                previewBtn.classList.add('active');
            }
        } else {
            // Already expanded - just switch tabs
            if (panelType === 'files') {
                const filesTabBtn = el('[data-tab="files"]');
                if (filesTabBtn) {
                    els('.tab-btn').forEach(b => b.classList.remove('active-tab'));
                    filesTabBtn.classList.add('active-tab');
                }
                const filesTabPane = el('#tab-files');
                if (filesTabPane) {
                    els('.tab-pane').forEach(p => p.classList.add('hidden'));
                    filesTabPane.classList.remove('hidden');
                }
                if (typeof renderFiles === 'function') renderFiles();
            } else if (panelType === 'preview') {
                const previewTabBtn = el('[data-tab="preview"]');
                if (previewTabBtn) {
                    els('.tab-btn').forEach(b => b.classList.remove('active-tab'));
                    previewTabBtn.classList.add('active-tab');
                }
                const previewTabPane = el('#tab-preview');
                if (previewTabPane) {
                    els('.tab-pane').forEach(p => p.classList.add('hidden'));
                    previewTabPane.classList.remove('hidden');
                }
            }

            // Update top button active states
            els('.top-action-btn').forEach(b => b.classList.remove('active'));
            if (panelType === 'files' && filesBtn) {
                filesBtn.classList.add('active');
            } else if (panelType === 'preview' && previewBtn) {
                previewBtn.classList.add('active');
            }
        }
    }

    if (filesBtn) {
        filesBtn.onclick = () => togglePanel('files');
    }

    if (previewBtn) {
        previewBtn.onclick = () => togglePanel('preview');
    }

    el('#new-task').onclick = () => {
        // 清空当前激活 ID，这样 renderAll 会显示欢迎页
        // 且不会在 sessions 列表中产生空 session，直到用户真正提交任务
        state.activeId = null;
        renderAll();
        
        // 切换到侧边栏显示状态（如果之前是折叠的）
        if (sidebar && sidebar.classList.contains('collapsed') && expandSidebarBtn) {
            expandSidebarBtn.click();
        }
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

    // SSE Connector
    const connectSSE = (s) => {
        if (!s) return;

        if (state.activeSSE) {
            state.activeSSE.close();
            state.activeSSE = null;
        }

        const es = new EventSource(`/opencode/run_sse?prompt=${encodeURIComponent(s.prompt)}&sid=${s.id}`);
        state.activeSSE = es;
        const rs = el('#runStream');
        const stopBtn = el('#stopStream');

        es.onerror = (err) => {
            console.warn("SSE connection error.", err);
            es.close();
            state.activeSSE = null;
            if (rs) rs.classList.remove('hidden');
            if (stopBtn) stopBtn.classList.add('hidden');
        };

        es.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'ping') return;
            console.log("SSE Message:", e.data);

            if (data.type === 'phases_init') {
                const newPhases = (data.phases || []).map(p => {
                    const existingPhase = s.phases?.find(sp => sp.id === p.id);
                    return { ...p, events: existingPhase?.events || [] };
                });
                const phaseMap = new Map();
                s.phases?.forEach(p => phaseMap.set(p.id, p));
                newPhases.forEach(p => {
                    const existing = phaseMap.get(p.id);
                    if (existing) {
                        if (p.status !== 'pending' || existing.status === 'pending') existing.status = p.status;
                        if (p.title) existing.title = p.title;
                        if (p.number !== undefined) existing.number = p.number;
                    } else {
                        phaseMap.set(p.id, p);
                    }
                });
                s.phases = Array.from(phaseMap.values()).sort((a, b) => (a.number || 0) - (b.number || 0));

                const hasDynamicPhases = s.phases.some(p => p.id?.startsWith('phase_') && p.id !== 'phase_planning' && p.id !== 'phase_summary');
                const planningPhase = s.phases.find(p => p.id === 'phase_planning');
                if (hasDynamicPhases && planningPhase) {
                    s.phases = s.phases.filter(p => p.id !== 'phase_planning');
                } else if (planningPhase && planningPhase.status === 'active') {
                    planningPhase.status = 'completed';
                }
                s.currentPhase = data.phases.find(p => p.status === 'active')?.id || null;
            } else if (data.type === 'answer_chunk') {
                const pSep = '\n\n---\n\n';
                const rSep = '\n\n---\n\n**新的回答：**\n\n';
                const pCount = s.prompt.split(pSep).length - 1;
                const rCount = s.response.split(rSep).length - 1;
                if (pCount > rCount) s.response += rSep;
                s.response += data.text;
            } else if (data.type === 'status' && data.value === 'done') {
                es.close();
                state.activeSSE = null;
                if (rs) rs.classList.remove('hidden');
                if (stopBtn) stopBtn.classList.add('hidden');
                renderFiles();
            } else if (data.type === 'action') {
                const actionData = data.data;
                const existingIdx = s.actions.findIndex(a => a.tool === actionData.tool && a.timestamp === actionData.timestamp);
                if (existingIdx >= 0) s.actions[existingIdx] = actionData;
                else s.actions.push(actionData);
            } else if (data.type === 'tool_event') {
                const event = data.data;
                if (!s.actions) s.actions = [];
                s.actions.push(event);
                let targetPhase = null;
                if (event.phase !== undefined) targetPhase = s.phases.find(p => p.number === event.phase);
                if (!targetPhase) targetPhase = [...s.phases].reverse().find(p => p.status !== 'pending') || s.phases[s.phases.length - 1];
                if (targetPhase) {
                    if (!targetPhase.events) targetPhase.events = [];
                    targetPhase.events.push(event);
                } else {
                    if (!s.orphanEvents) s.orphanEvents = [];
                    s.orphanEvents.push(event);
                }
            } else if (data.type === 'file_generated') {
                if (window.filesManager && data.file) window.filesManager.addFile(data.file);
            } else if (data.type === 'preview_url') {
                if (window.rightPanelManager && data.data?.url) window.rightPanelManager.showWebPreview(data.data.url);
            } else if (data.type === 'timeline_update') {
                if (window.timelineProgress && data.step) {
                    window.timelineProgress.addStep(data.step);
                    window.timelineProgress.setActiveStep(data.step.step_id);
                    const container = el('#timeline-progress-container');
                    if (container) container.classList.remove('hidden');
                }
            } else if (data.type === 'preview_start') {
                if (window.codePreviewOverlay && window.previewConfig?.isEventEnabled(data.action)) {
                    window.codePreviewOverlay.setStepId(data.step_id);
                    window.codePreviewOverlay.show(data.file_path.split('/').pop(), data.action);
                }
            } else if (data.type === 'preview_delta') {
                if (window.codePreviewOverlay && window.previewConfig?.enableTypewriter) {
                    window.codePreviewOverlay.appendDelta(data.delta);
                }
            } else if (data.type === 'preview_end') {
                if (window.codePreviewOverlay) window.codePreviewOverlay.setStatus('完成');
            } else if (data.type === 'deliverables') {
                s.deliverables = data.items || [];
            }
            renderResults();
        };
    };

    window.connectSSE = connectSSE;

    const rs = el('#runStream');
    const stopBtn = el('#stopStream');

    if (rs) rs.onclick = async () => {
        const input = el('#prompt');
        const p = input.value.trim();
        if (!p) return;

        let s = state.sessions.find(x => x.id === state.activeId);
        if (!s) {
            const id = 'ses_' + Math.random().toString(36).slice(2, 9);
            s = { id, prompt: p, response: '', phases: [], orphanEvents: [], actions: [], currentPhase: null };
            state.sessions.unshift(s);
            state.activeId = id;
        } else {
            const previousPrompt = s.prompt ? s.prompt + '\n\n---\n\n' : '';
            s.prompt = previousPrompt + p;
            s.phases = [];
            s.orphanEvents = [];
            s.actions = [];
            s.currentPhase = null;
        }

        const vmPanel = el('#vm-panel');
        const uvnFrame = el('#uvn-frame');
        if (vmPanel) {
            vmPanel.classList.remove('hidden');
            if (uvnFrame && uvnFrame.hasAttribute('data-src')) {
                uvnFrame.setAttribute('src', uvnFrame.getAttribute('data-src'));
                uvnFrame.removeAttribute('data-src');
            }
        }

        if (stopBtn) stopBtn.classList.remove('hidden');
        if (rs) rs.classList.add('hidden');

        input.value = '';
        renderAll();
        saveState();
        connectSSE(s);
    };

    if (stopBtn) {
        stopBtn.onclick = () => {
            if (state.activeSSE) {
                state.activeSSE.close();
                state.activeSSE = null;
            }
            if (rs) rs.classList.remove('hidden');
            if (stopBtn) stopBtn.classList.add('hidden');
            const s = state.sessions.find(x => x.id === state.activeId);
            if (s) {
                s.orphanEvents.push({ type: "thought", content: "任务已被用户停止" });
                if (s.phases && s.phases.length > 0) {
                    const activePhase = s.phases.find(p => p.status === 'active');
                    if (activePhase) activePhase.status = 'done';
                }
            }
            renderAll();
            saveState();
        };
    }

    el('#prompt').onkeydown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (rs) rs.click();
        }
    };

    // ✅ v=38.3.3修复：为欢迎页输入框添加Enter键支持
    // 使用已声明的promptWelcome变量（在函数开头声明）
    if (promptWelcome) {
        promptWelcome.onkeydown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const rsWelcome = el('#runStream-welcome');
                if (rsWelcome) rsWelcome.click();
            }
        };
    }

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


// 新建项目相关函数
function showNewProjectModal() {
    const modal = el('#new-project-modal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        const input = el('#project-name-input');
        if (input) {
            input.value = '';
            input.focus();
        }
    }
}

function hideNewProjectModal() {
    const modal = el('#new-project-modal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

async function createNewProject() {
    const input = el('#project-name-input');
    const name = input ? input.value.trim() : '';
    
    if (!name) {
        alert('请输入项目名称');
        return;
    }
    
    try {
        const project = await window.apiClient.createProject(name);
        console.log('[Project] Created:', project);
        
        // 添加到本地 state
        window.state.projects.unshift(project);
        window.state.activeProjectId = project.id;
        
        // 保存状态
        saveState();
        
        // 关闭弹窗
        hideNewProjectModal();
        
        // 重新渲染侧边栏
        renderSidebar();
    } catch (e) {
        console.error('[Project] Create failed:', e);
        alert('创建项目失败: ' + e.message);
    }
}

// 绑定事件
function initProjectModal() {
    // 新建项目按钮
    const newProjectBtn = el('#new-project');
    if (newProjectBtn) {
        newProjectBtn.onclick = showNewProjectModal;
    }
    
    // 取消按钮
    const cancelBtn = el('#cancel-project-btn');
    if (cancelBtn) {
        cancelBtn.onclick = hideNewProjectModal;
    }
    
    // 确认按钮
    const confirmBtn = el('#confirm-project-btn');
    if (confirmBtn) {
        confirmBtn.onclick = createNewProject;
    }
    
    // 点击遮罩关闭
    const modal = el('#new-project-modal');
    if (modal) {
        modal.onclick = (e) => {
            if (e.target === modal) {
                hideNewProjectModal();
            }
        };
    }
    
    // 回车创建
    const input = el('#project-name-input');
    if (input) {
        input.onkeydown = (e) => {
            if (e.key === 'Enter') {
                createNewProject();
            } else if (e.key === 'Escape') {
                hideNewProjectModal();
            }
        };
    }
}


function init() {
    // Theme initialization
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    state.theme = savedTheme;
    applyTheme();

    loadState();
    bindUI();
    initProjectModal();
    renderAll();

    // Auto-resume if active session exists
    if (state.activeId) {
        const s = state.sessions.find(x => x.id === state.activeId);
        // Only resume if it's not completed and has a prompt
        const isNotCompleted = !s.phases || s.phases.length === 0 ||
            (s.phases.length > 0 && s.phases[s.phases.length - 1].status !== 'completed');

        if (s && s.prompt && isNotCompleted) {
            console.log('Resuming session:', state.activeId);
            // 刷新页面时，只需重新建立 SSE 连接以监听进度，而不应模拟点击触发新运行
            if (typeof connectSSE === 'function') {
                // 等待 UI 绑定完成后连接
                setTimeout(() => connectSSE(s), 500);
            }
        }
    }
}

// Wait for DOM to be fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
// Version 38.3.4 - Fixed promptWelcome duplicate declaration issue
// Build timestamp: 1770561617
console.log('[OpenCode] Loaded opencode.js v38.3.4');
