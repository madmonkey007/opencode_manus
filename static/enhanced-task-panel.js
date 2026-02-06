/**
 * Enhanced Task Panel - Manus-style Progressive Disclosure
 * 实现类似 Manus 的逐级展开任务面板
 */

// 渲染增强的任务面板
function renderEnhancedTaskPanel(session) {
    const container = document.createElement('div');
    container.className = 'enhanced-task-panel space-y-4';
    
    // 1. 用户输入卡片
    if (session.prompt) {
        const userCard = createUserPromptCard(session.prompt);
        container.appendChild(userCard);
    }
    
    // 2. 任务阶段卡片（逐级展开）
    if (session.phases && session.phases.length > 0) {
        const phasesCard = createPhasesCard(session.phases, session.currentPhase);
        container.appendChild(phasesCard);
    }
    
    // 3. 执行动作列表（默认收起，可展开）
    if (session.actions && session.actions.length > 0) {
        const actionsCard = createActionsCard(session.actions);
        container.appendChild(actionsCard);
    }
    
    // 4. 任务交付总结（底部）
    if (session.response || session.deliverables) {
        const summaryCard = createDeliverableCard(session);
        container.appendChild(summaryCard);
    }
    
    return container;
}

// 创建用户输入卡片
function createUserPromptCard(prompt) {
    const card = document.createElement('div');
    card.className = 'bg-gray-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-700 rounded-lg p-4';
    card.innerHTML = `
        <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-full bg-gray-700 dark:bg-gray-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                U
            </div>
            <div class="flex-1 min-w-0">
                <div class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">您的任务</div>
                <div class="text-sm text-gray-800 dark:text-gray-200">${escapeHtml(prompt)}</div>
            </div>
        </div>
    `;
    return card;
}

// 创建阶段卡片（逐级展开）
function createPhasesCard(phases, currentPhaseId) {
    const card = document.createElement('div');
    card.className = 'bg-white dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm overflow-hidden';
    
    const header = document.createElement('div');
    header.className = 'px-4 py-3 border-b border-border-light dark:border-border-dark bg-gray-50 dark:bg-zinc-800/50 flex items-center justify-between cursor-pointer hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors';
    header.innerHTML = `
        <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-purple-500 text-[20px]">account_tree</span>
            <span class="text-sm font-semibold text-gray-900 dark:text-white">任务阶段</span>
            <span class="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded-full font-medium">${phases.length} 个阶段</span>
        </div>
        <span class="material-symbols-outlined text-gray-400 expand-icon transition-transform duration-200">expand_more</span>
    `;
    
    const body = document.createElement('div');
    body.className = 'phases-body p-4 space-y-3';
    
    phases.forEach((phase, idx) => {
        const phaseItem = createPhaseItem(phase, idx, currentPhaseId);
        body.appendChild(phaseItem);
    });
    
    // 默认展开
    header.onclick = () => {
        const isHidden = body.classList.contains('hidden');
        body.classList.toggle('hidden');
        header.querySelector('.expand-icon').style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
    };
    
    card.appendChild(header);
    card.appendChild(body);
    
    return card;
}

// 创建单个阶段项
function createPhaseItem(phase, index, currentPhaseId) {
    const item = document.createElement('div');
    const isActive = phase.id === currentPhaseId;
    const isDone = phase.status === 'done' || phase.status === 'completed';
    const isPending = !isActive && !isDone;
    
    let statusIcon, statusClass, statusBg;
    if (isDone) {
        statusIcon = 'check_circle';
        statusClass = 'text-green-500';
        statusBg = 'bg-green-50 dark:bg-green-900/20';
    } else if (isActive) {
        statusIcon = 'radio_button_checked';
        statusClass = 'text-blue-500 animate-pulse';
        statusBg = 'bg-blue-50 dark:bg-blue-900/20';
    } else {
        statusIcon = 'radio_button_unchecked';
        statusClass = 'text-gray-400';
        statusBg = 'bg-gray-50 dark:bg-zinc-800/50';
    }
    
    item.className = `phase-item ${statusBg} border border-border-light dark:border-border-dark rounded-xl p-3 transition-all duration-200`;
    item.innerHTML = `
        <div class="flex items-center gap-3">
            <div class="flex items-center justify-center w-6 h-6 rounded-full ${statusBg}">
                <span class="material-symbols-outlined ${statusClass} text-[18px]">${statusIcon}</span>
            </div>
            <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-900 dark:text-white">${index + 1}. ${escapeHtml(phase.title)}</div>
                ${phase.description ? `<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${escapeHtml(phase.description)}</div>` : ''}
            </div>
            ${isActive ? '<span class="text-xs px-2 py-0.5 bg-blue-500 text-white rounded-full font-medium">进行中</span>' : ''}
            ${isDone ? '<span class="text-xs px-2 py-0.5 bg-green-500 text-white rounded-full font-medium">已完成</span>' : ''}
        </div>
    `;
    
    return item;
}

// 创建执行动作卡片（默认收起）
function createActionsCard(actions) {
    const card = document.createElement('div');
    card.className = 'bg-white dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm overflow-hidden';
    
    const header = document.createElement('div');
    header.className = 'px-4 py-3 border-b border-border-light dark:border-border-dark bg-gray-50 dark:bg-zinc-800/50 flex items-center justify-between cursor-pointer hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors';
    header.innerHTML = `
        <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-amber-500 text-[20px]">bolt</span>
            <span class="text-sm font-semibold text-gray-900 dark:text-white">执行动作</span>
            <span class="text-xs px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-full font-medium">${actions.length} 个动作</span>
        </div>
        <span class="material-symbols-outlined text-gray-400 expand-icon transition-transform duration-200">expand_more</span>
    `;
    
    const body = document.createElement('div');
    body.className = 'actions-body hidden p-4 space-y-2 max-h-[400px] overflow-y-auto custom-scrollbar';
    
    actions.forEach((action, idx) => {
        const actionItem = createActionItem(action, idx);
        body.appendChild(actionItem);
    });
    
    // 默认收起，点击展开
    header.onclick = () => {
        const isHidden = body.classList.contains('hidden');
        body.classList.toggle('hidden');
        header.querySelector('.expand-icon').style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
    };
    
    card.appendChild(header);
    card.appendChild(body);
    
    return card;
}

// 创建单个动作项
function createActionItem(action, index) {
    const item = document.createElement('div');
    const isRunning = action.status === 'running';
    const isSuccess = action.status === 'success';
    const isFailed = action.status === 'failed';

    let statusIcon, statusClass;
    if (isSuccess) {
        statusIcon = 'check_circle';
        statusClass = 'text-green-500';
    } else if (isFailed) {
        statusIcon = 'error';
        statusClass = 'text-red-500';
    } else if (isRunning) {
        statusIcon = 'sync';
        statusClass = 'text-blue-500 animate-spin';
    } else {
        statusIcon = 'schedule';
        statusClass = 'text-gray-400';
    }

    // 获取工具图标配置
    const toolIconConfig = getToolIcon(action.tool);
    const toolIconHtml = `
        <div class="flex items-center justify-center ${toolIconConfig.bg} rounded-lg p-1.5 flex-shrink-0">
            <span class="material-symbols-outlined ${toolIconConfig.text} text-[16px]">
                ${toolIconConfig.icon}
            </span>
        </div>
    `;

    item.className = 'action-item bg-gray-50 dark:bg-zinc-800/50 rounded-lg p-3 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer';
    item.innerHTML = `
        <div class="flex items-start gap-3">
            ${toolIconHtml}
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-xs font-mono px-1.5 py-0.5 bg-white dark:bg-zinc-900 border border-border-light dark:border-border-dark rounded ${toolIconConfig.text}">${action.tool || 'unknown'}</span>
                    <span class="text-xs text-gray-500 dark:text-gray-400">${action.timestamp || ''}</span>
                </div>
                <div class="text-sm text-gray-700 dark:text-gray-300">${escapeHtml(action.description || action.brief || '执行中...')}</div>
                ${action.result ? `<div class="text-xs text-gray-500 dark:text-gray-400 mt-1 font-mono truncate">${escapeHtml(JSON.stringify(action.result).substring(0, 100))}...</div>` : ''}
            </div>
        </div>
    `;
    
    // 点击展开详情
    item.onclick = () => {
        showActionDetail(action);
    };
    
    return item;
}

// 创建任务交付卡片
function createDeliverableCard(session) {
    const card = document.createElement('div');
    card.className = 'bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border border-green-200 dark:border-green-800 rounded-2xl p-5 shadow-md';
    
    card.innerHTML = `
        <div class="flex items-start gap-4">
            <div class="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center text-white flex-shrink-0">
                <span class="material-symbols-outlined text-[24px]">task_alt</span>
            </div>
            <div class="flex-1 min-w-0">
                <h3 class="text-base font-bold text-gray-900 dark:text-white mb-2">任务完成</h3>
                <div class="prose prose-sm dark:prose-invert max-w-none">
                    ${session.response ? marked.parse(session.response) : '<p class="text-gray-600 dark:text-gray-400">任务正在执行中...</p>'}
                </div>
                ${session.deliverables && session.deliverables.length > 0 ? `
                    <div class="mt-4 pt-4 border-t border-green-200 dark:border-green-800">
                        <div class="text-xs font-medium text-green-700 dark:text-green-400 mb-2">交付物</div>
                        <div class="space-y-2">
                            ${session.deliverables.map(d => `
                                <div class="flex items-center gap-2 text-sm">
                                    <span class="material-symbols-outlined text-green-600 dark:text-green-400 text-[16px]">insert_drive_file</span>
                                    <span class="text-gray-700 dark:text-gray-300">${escapeHtml(d.name || d)}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
    
    return card;
}

// 显示动作详情弹窗
function showActionDetail(action) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4 animate-fade-in';
    modal.innerHTML = `
        <div class="bg-white dark:bg-surface-dark rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div class="px-6 py-4 border-b border-border-light dark:border-border-dark flex items-center justify-between">
                <h3 class="text-lg font-bold text-gray-900 dark:text-white">动作详情</h3>
                <button class="close-modal p-1 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded transition-colors">
                    <span class="material-symbols-outlined text-gray-500">close</span>
                </button>
            </div>
            <div class="flex-1 overflow-y-auto p-6 space-y-4">
                <div>
                    <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">工具</div>
                    <div class="text-sm font-mono px-3 py-2 bg-gray-100 dark:bg-zinc-800 rounded">${action.tool || 'unknown'}</div>
                </div>
                ${action.brief ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">描述</div>
                        <div class="text-sm text-gray-700 dark:text-gray-300">${escapeHtml(action.brief)}</div>
                    </div>
                ` : ''}
                ${action.args ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">参数</div>
                        <pre class="text-xs font-mono p-3 bg-gray-100 dark:bg-zinc-800 rounded overflow-x-auto">${JSON.stringify(action.args, null, 2)}</pre>
                    </div>
                ` : ''}
                ${action.result ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">结果</div>
                        <pre class="text-xs font-mono p-3 bg-gray-100 dark:bg-zinc-800 rounded overflow-x-auto max-h-[300px]">${JSON.stringify(action.result, null, 2)}</pre>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
    
    modal.onclick = (e) => {
        if (e.target === modal || e.target.closest('.close-modal')) {
            modal.remove();
        }
    };
    
    document.body.appendChild(modal);
}

// HTML 转义工具函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 导出函数
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { renderEnhancedTaskPanel };
}
