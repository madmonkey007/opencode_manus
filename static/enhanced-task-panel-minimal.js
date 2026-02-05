/**
 * Enhanced Task Panel - Minimal Design
 * 简洁配色版本
 */

// 渲染增强的任务面板
function renderEnhancedTaskPanel(session) {
    const container = document.createElement('div');
    container.className = 'enhanced-task-panel space-y-3';
    
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

// 创建用户输入卡片 - 简洁灰色调
function createUserPromptCard(prompt) {
    const card = document.createElement('div');
    card.className = 'bg-gray-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-700 rounded-lg p-4';
    card.innerHTML = `
        <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-full bg-gray-700 dark:bg-gray-600 flex items-center justify-center text-white font-medium text-sm flex-shrink-0">
                U
            </div>
            <div class="flex-1 min-w-0">
                <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">您的任务</div>
                <div class="text-sm text-gray-900 dark:text-gray-100">${escapeHtml(prompt)}</div>
            </div>
        </div>
    `;
    return card;
}

// 创建阶段卡片（逐级展开）- 简洁样式
function createPhasesCard(phases, currentPhaseId) {
    const card = document.createElement('div');
    card.className = 'bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-lg overflow-hidden';
    
    const header = document.createElement('div');
    header.className = 'px-4 py-3 border-b border-gray-200 dark:border-zinc-700 flex items-center justify-between cursor-pointer hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors';
    header.innerHTML = `
        <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-gray-600 dark:text-gray-400 text-[18px]">account_tree</span>
            <span class="text-sm font-semibold text-gray-900 dark:text-white">任务阶段</span>
            <span class="text-xs px-2 py-0.5 bg-gray-100 dark:bg-zinc-700 text-gray-600 dark:text-gray-400 rounded font-medium">${phases.length}</span>
        </div>
        <span class="material-symbols-outlined text-gray-400 expand-icon transition-transform duration-200">expand_more</span>
    `;
    
    const body = document.createElement('div');
    body.className = 'phases-body p-4 space-y-2';
    
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

// 创建单个阶段项 - 简洁样式
function createPhaseItem(phase, index, currentPhaseId) {
    const item = document.createElement('div');
    const isActive = phase.id === currentPhaseId;
    const isDone = phase.status === 'done' || phase.status === 'completed';
    const isPending = !isActive && !isDone;
    
    let statusIcon, statusClass;
    if (isDone) {
        statusIcon = 'check_circle';
        statusClass = 'text-green-600 dark:text-green-500';
    } else if (isActive) {
        statusIcon = 'radio_button_checked';
        statusClass = 'text-gray-600 dark:text-gray-400';
    } else {
        statusIcon = 'radio_button_unchecked';
        statusClass = 'text-gray-300 dark:text-gray-600';
    }
    
    item.className = `phase-item bg-gray-50 dark:bg-zinc-800/30 border border-gray-200 dark:border-zinc-700 rounded-lg p-3 transition-all duration-200`;
    item.innerHTML = `
        <div class="flex items-center gap-3">
            <span class="material-symbols-outlined ${statusClass} text-[18px]">${statusIcon}</span>
            <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-900 dark:text-white">${index + 1}. ${escapeHtml(phase.title)}</div>
                ${phase.description ? `<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${escapeHtml(phase.description)}</div>` : ''}
            </div>
            ${isDone ? '<span class="text-xs text-gray-500 dark:text-gray-400">✓</span>' : ''}
        </div>
    `;
    
    return item;
}

// 创建执行动作卡片（默认收起）- 简洁样式
function createActionsCard(actions) {
    const card = document.createElement('div');
    card.className = 'bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-lg overflow-hidden';
    
    const header = document.createElement('div');
    header.className = 'px-4 py-3 border-b border-gray-200 dark:border-zinc-700 flex items-center justify-between cursor-pointer hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors';
    header.innerHTML = `
        <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-gray-600 dark:text-gray-400 text-[18px]">bolt</span>
            <span class="text-sm font-semibold text-gray-900 dark:text-white">执行动作</span>
            <span class="text-xs px-2 py-0.5 bg-gray-100 dark:bg-zinc-700 text-gray-600 dark:text-gray-400 rounded font-medium">${actions.length}</span>
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

// 创建单个动作项 - 简洁样式
function createActionItem(action, index) {
    const item = document.createElement('div');
    const isRunning = action.status === 'running';
    const isSuccess = action.status === 'success';
    const isFailed = action.status === 'failed';
    
    let statusIcon, statusClass;
    if (isSuccess) {
        statusIcon = 'check_circle';
        statusClass = 'text-green-600 dark:text-green-500';
    } else if (isFailed) {
        statusIcon = 'error';
        statusClass = 'text-red-600 dark:text-red-500';
    } else if (isRunning) {
        statusIcon = 'sync';
        statusClass = 'text-gray-600 dark:text-gray-400 animate-spin';
    } else {
        statusIcon = 'schedule';
        statusClass = 'text-gray-400';
    }
    
    item.className = 'action-item bg-gray-50 dark:bg-zinc-800/30 rounded-lg p-3 hover:bg-gray-100 dark:hover:bg-zinc-800/50 transition-colors';
    item.innerHTML = `
        <div class="flex items-start gap-3">
            <span class="material-symbols-outlined ${statusClass} text-[16px] mt-0.5">${statusIcon}</span>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-xs font-mono px-1.5 py-0.5 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded text-gray-600 dark:text-gray-400">${action.tool || 'unknown'}</span>
                    <span class="text-xs text-gray-400">${action.timestamp || ''}</span>
                </div>
                <div class="text-sm text-gray-700 dark:text-gray-300">${escapeHtml(action.description || action.brief || '执行中...')}</div>
            </div>
        </div>
    `;
    
    return item;
}

// 创建任务交付卡片 - 简洁样式
function createDeliverableCard(session) {
    const card = document.createElement('div');
    card.className = 'bg-gray-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-700 rounded-lg p-4';
    
    card.innerHTML = `
        <div class="flex items-start gap-3">
            <div class="w-8 h-8 rounded-full bg-green-600 dark:bg-green-700 flex items-center justify-center text-white flex-shrink-0">
                <span class="material-symbols-outlined text-[20px]">task_alt</span>
            </div>
            <div class="flex-1 min-w-0">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-2">任务完成</h3>
                <div class="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-300">
                    ${session.response ? marked.parse(session.response) : '<p class="text-gray-500 dark:text-gray-400">任务正在执行中...</p>'}
                </div>
                ${session.deliverables && session.deliverables.length > 0 ? `
                    <div class="mt-3 pt-3 border-t border-gray-200 dark:border-zinc-700">
                        <div class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">交付物</div>
                        <div class="space-y-1.5">
                            ${session.deliverables.map(d => `
                                <div class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                                    <span class="material-symbols-outlined text-gray-500 text-[16px]">insert_drive_file</span>
                                    <span>${escapeHtml(d.name || d)}</span>
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

// HTML 转义函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
