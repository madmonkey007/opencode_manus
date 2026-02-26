/**
 * Enhanced Task Panel - Manus-style Progressive Disclosure
 * 实现类似 Manus 的逐级展开任务面板
 */

// 渲染增强的任务面板
function renderEnhancedTaskPanel(session) {
    const container = document.createElement('div');
    container.className = 'enhanced-task-panel space-y-6';

    const pSep = '\n\n---\n\n';
    const rSep = '\n\n---\n\n**新的回答：**\n\n';

    // 分割多轮对话
    const prompts = (session.prompt || '').split(pSep);
    const responses = (session.response || '').split(rSep);

    const turnsCount = Math.max(prompts.length, responses.length);

    for (let i = 0; i < turnsCount; i++) {
        const turnContainer = document.createElement('div');
        turnContainer.className = `conversation-turn space-y-4 ${i < turnsCount - 1 ? 'border-b border-gray-100 dark:border-zinc-800 pb-8' : ''}`;

        // 1. 该轮的用户输入
        if (prompts[i]) {
            const userCard = createUserPromptCard(prompts[i]);
            turnContainer.appendChild(userCard);
        }

        // 2. 任务阶段卡片 - 仅显示属于该对话轮次 (turn_index === i + 1) 的 phases
        // 注意：turnIndex 是从 1 开始计数的（在 patch.js 中初始化为 1）
        const turnPhases = session.phases ? session.phases.filter(p => (p.turn_index === i + 1)) : [];
        
        // 兜底：如果是最后一轮且没找到匹配的 turn_index，显示所有未关联的 phases
        if (i === turnsCount - 1 && turnPhases.length === 0 && session.phases && session.phases.length > 0) {
            const unassociatedPhases = session.phases.filter(p => !p.turn_index || p.turn_index >= i + 1);
            if (unassociatedPhases.length > 0) {
                const phasesCard = createPhasesCard(unassociatedPhases, session.currentPhase);
                turnContainer.appendChild(phasesCard);
            }
        } else if (turnPhases.length > 0) {
            const phasesCard = createPhasesCard(turnPhases, session.currentPhase);
            turnContainer.appendChild(phasesCard);
        }

        // 3. 该轮的回答

        if (responses[i] !== undefined && responses[i] !== null) {
            // 只有当有内容或者是最后一轮时才渲染回答卡片
            if (responses[i].trim() || i === turnsCount - 1) {
                const summaryCard = createDeliverableCard({
                    ...session,
                    response: responses[i],
                    // 交付物通常也只关联到最后一轮执行
                    deliverables: (i === turnsCount - 1) ? session.deliverables : null
                });
                turnContainer.appendChild(summaryCard);
            }
        }

        container.appendChild(turnContainer);
    }

    return container;
}

// 创建用户输入卡片
function createUserPromptCard(prompt) {
    const card = document.createElement('div');
    card.className = 'message-bubble user-bubble animate-fade-in text-sm';
    card.style.cssText = 'margin-left: auto; margin-right: 0; width: fit-content; max-width: 85%;';
    card.textContent = prompt;
    return card;
}

// 创建阶段卡片（逐级展开）
function createPhasesCard(phases, currentPhaseId) {
    const card = document.createElement('div');
    card.className = 'overflow-hidden'; // 去掉背景、边框和阴影

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
    body.className = 'phases-body py-2 space-y-3 relative'; // 移除 p-4 减少外部边距

    // 先创建所有 phase
    const phaseItems = [];
    phases.forEach((phase, idx) => {
        const isLast = idx === phases.length - 1;
        const phaseItem = createPhaseItem(phase, idx, currentPhaseId, isLast);
        phaseItems.push(phaseItem);
        body.appendChild(phaseItem);
    });

    // 添加贯穿所有 phase 的连续实线
    // 从第一个 phase 的状态图标中心开始，到最后一个 phase 的状态图标中心
    if (phases.length > 1) {
        const timelineLine = document.createElement('div');
        timelineLine.className = 'absolute bg-gray-300 dark:bg-gray-600 opacity-50';
        // 24px = 12px (header padding-left) + 12px (图标半径)
        // 32px = 8px (body padding-top) + 12px (header padding-top) + 12px (图标中心偏移)
        timelineLine.style.cssText = 'left: 24px; width: 2px; top: 32px; bottom: 32px; z-index: 0;';
        body.appendChild(timelineLine);
    }

    card.appendChild(body);

    return card;
}

// 创建单个阶段项（包含嵌套的执行动作）
function createPhaseItem(phase, index, currentPhaseId, isLast) {
    const item = document.createElement('div');
    item.className = 'phase-item';
    const isActive = phase.id === currentPhaseId;
    const isDone = phase.status === 'done' || phase.status === 'completed';
    const isPending = !isActive && !isDone;

    // 计算该阶段的事件数量
    const eventCount = phase.events ? phase.events.length : 0;

    // 状态图标 HTML
    let statusIconHtml, statusClass, statusBg;
    if (isDone) {
        // 完成状态：黑色圆形 + 白色勾选 SVG
        statusIconHtml = `<svg width="12" height="12" color="white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        statusClass = 'bg-gray-800 dark:bg-gray-700';
        statusBg = 'bg-gray-50 dark:bg-gray-900/20';
    } else {
        // 执行中或未开始：灰色 loading 圆圈
        statusIconHtml = `<svg class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-dasharray="32" stroke-dashoffset="32" class="text-gray-300 opacity-25"></circle>
            <path d="M12 2C17.5228 2 22 6.47715 22 12" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="text-gray-500"></path>
        </svg>`;
        statusClass = 'bg-white dark:bg-zinc-800';
        statusBg = isActive ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-gray-50 dark:bg-zinc-800/50';
    }

    // 阶段头部
    const header = document.createElement('div');
    header.className = `phase-header ${statusBg} rounded-xl p-3 transition-all duration-200 cursor-pointer hover:shadow-sm relative`;

    header.innerHTML = `
        <div class="flex items-center gap-3">
            <!-- 状态图标容器 -->
            <div class="flex items-center justify-center w-6 h-6 rounded-full ${statusClass} flex-shrink-0 relative" style="z-index: 10;">
                ${statusIconHtml}
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-900 dark:text-white">${index + 1}. ${escapeHtml(phase.title)}</span>
                    ${eventCount > 0 ? `<span class="text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full font-medium">${eventCount} 个动作</span>` : ''}
                </div>
                ${phase.description ? `<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${escapeHtml(phase.description)}</div>` : ''}
            </div>
            ${isActive && !isDone ? '<span class="text-xs px-2 py-0.5 bg-blue-500 text-white rounded-full font-medium">进行中</span>' : ''}
            ${isDone ? '<span class="text-xs px-2 py-0.5 bg-green-500 text-white rounded-full font-medium">已完成</span>' : ''}
            ${eventCount > 0 ? '<span class="material-symbols-outlined text-gray-400 expand-icon transition-transform duration-200 text-[18px]">expand_more</span>' : ''}
        </div>
    `;

    // 阶段内容（执行动作列表）
    const body = document.createElement('div');
    body.className = 'phase-body hidden pl-9 pr-3 pt-2 pb-2 space-y-2';

    // 渲染该阶段的所有事件（执行动作）
    if (phase.events && phase.events.length > 0) {
        phase.events.forEach((event, eventIdx) => {
            const eventItem = createEventItem(event, eventIdx);
            body.appendChild(eventItem);
        });
    } else {
        body.innerHTML = '<div class="text-xs text-gray-400 dark:text-gray-600 italic">暂无执行动作</div>';
    }

    // 点击展开/收起动作列表
    if (eventCount > 0) {
        header.onclick = () => {
            const isHidden = body.classList.contains('hidden');
            body.classList.toggle('hidden');
            const expandIcon = header.querySelector('.expand-icon');
            if (expandIcon) {
                expandIcon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
            }
        };

        // 如果是当前活动阶段或已完成阶段，默认展开
        if (isActive || isDone) {
            body.classList.remove('hidden');
            const expandIcon = header.querySelector('.expand-icon');
            if (expandIcon) {
                expandIcon.style.transform = 'rotate(180deg)';
            }
        }
    }

    item.appendChild(header);
    item.appendChild(body);

    return item;
}

// 辅助函数：从工具输入中提取有意义的摘要
function getToolSummary(toolType, input, output) {
    const tool = toolType.toLowerCase();

    // 提取最有意义的字段作为摘要
    if (tool === 'read') {
        const path = input.path || input.file_path || input.file;
        return path ? `读取文件: ${path}` : '读取文件';
    }

    if (tool === 'bash' || tool === 'terminal' || tool === 'execute') {
        const cmd = input.command || input.cmd;
        return cmd ? `执行命令: ${cmd}` : '执行命令';
    }

    if (tool === 'write') {
        const path = input.path || input.file_path || input.file;
        const contentLen = input.content ? input.content.length : 0;
        return path ? `写入文件: ${path} (${contentLen} 字符)` : '写入文件';
    }

    if (tool === 'edit' || tool === 'file_editor') {
        const path = input.path || input.file_path || input.file;
        return path ? `编辑文件: ${path}` : '编辑文件';
    }

    if (tool === 'grep') {
        const pattern = input.pattern || input.regex || input.search;
        const path = input.path || input.file_path || input.file;
        if (pattern && path) {
            return `搜索: ${pattern} 在 ${path}`;
        }
        return pattern ? `搜索: ${pattern}` : '搜索';
    }

    // 默认返回工具名称
    return toolType;
}

// 创建事件项（执行动作）
function createEventItem(event, index) {
    const item = document.createElement('div');

    // 判断事件类型
    const isThought = event.type === 'thought';
    const isTool = event.type === 'tool' || event.type === 'action';
    const isError = event.type === 'error';

    let iconHtml, title, content, detailsHtml = '';
    let statusClass = 'text-gray-400';
    let statusIcon = 'schedule';
    let isExpandable = false;

    if (isThought) {
        iconHtml = TOOL_ICONS['thought'];
        title = 'thought';
        // 显示完整的思考内容，而不是token数
        content = event.content || event.data?.text || (typeof event.data === 'string' ? event.data : '') || '思考中...';
        isExpandable = true;
    } else if (isError) {
        iconHtml = '<span class="material-symbols-outlined text-[14px]">error</span>';
        title = '执行错误';
        content = event.content || event.message || '发生了未知错误';
        statusIcon = 'error';
        statusClass = 'text-red-500';
    } else if (isTool) {
        const data = event.data || {};
        const toolName = data.tool_name || event.tool || 'file_editor';
        const toolType = data.tool || toolName;

        if (typeof getToolIcon === 'function') {
            iconHtml = getToolIcon(toolType).icon;
        } else {
            iconHtml = TOOL_ICONS['file_editor'];
        }

        // 使用辅助函数生成友好的摘要
        const rawInput = data.input || {};
        const output = data.output || '';

        title = data.title || getToolSummary(toolName, rawInput, output);

        // 提取输入输出详情
        const inputIsNotEmpty = Object.keys(rawInput).length > 0;
        const input = inputIsNotEmpty ? JSON.stringify(rawInput, null, 2) : '';

        content = input ? `Input: ${input.substring(0, 100)}${input.length > 100 ? '...' : ''}` : (output || `${toolName} 操作`);

        if (input || output) {
            isExpandable = true;
            detailsHtml = `
                <div class="mt-2 p-2 bg-gray-50 dark:bg-black/20 rounded border border-gray-100 dark:border-white/5 font-mono text-[10px] overflow-auto max-h-60">
                    ${inputIsNotEmpty ? `<div class="text-blue-500 mb-1">Incoming Input:</div><pre class="whitespace-pre-wrap mb-2">${escapeHtml(input)}</pre>` : ''}
                    ${output ? `<div class="text-green-500 mb-1">Command Output:</div><pre class="whitespace-pre-wrap">${escapeHtml(output)}</pre>` : ''}
                </div>
            `;
        }
    }

    // 基础样式
    item.className = 'event-item bg-white dark:bg-zinc-900/30 rounded-lg p-2.5 transition-colors border border-gray-200 dark:border-gray-700';

    item.innerHTML = `
        <div class="flex items-start gap-2">
            <div class="flex-shrink-0 w-4 h-4 flex items-center justify-center">
                ${iconHtml}
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-xs font-bold text-gray-700 dark:text-gray-200">${title}</span>
                </div>
                <div class="event-content text-xs text-gray-500 dark:text-gray-400 ${isExpandable ? 'line-clamp-2' : ''}">${escapeHtml(content || '')}</div>
                <div class="event-details hidden">${detailsHtml || escapeHtml(content || '')}</div>
            </div>
            ${isExpandable ? `
                <div class="flex-shrink-0 expand-icon-wrapper cursor-pointer p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                    <span class="material-symbols-outlined text-gray-400 expand-icon transition-transform duration-200 text-[16px]">expand_more</span>
                </div>
            ` : ''}
        </div>
    `;

    if (isExpandable) {
        const expandWrapper = item.querySelector('.expand-icon-wrapper');
        const expandIcon = item.querySelector('.expand-icon');
        const eventContent = item.querySelector('.event-content');
        const eventDetails = item.querySelector('.event-details');

        expandWrapper.onclick = (e) => {
            e.stopPropagation();
            const isHidden = eventDetails.classList.contains('hidden');
            if (isHidden) {
                eventDetails.classList.remove('hidden');
                eventContent.classList.add('hidden');
                expandIcon.style.transform = 'rotate(180deg)';
            } else {
                eventDetails.classList.add('hidden');
                eventContent.classList.remove('hidden');
                expandIcon.style.transform = 'rotate(0deg)';
            }
        };
    }

    // 添加工具事件点击响应
    if (isTool && !isThought) {
        item.style.cursor = 'pointer';
        item.onclick = () => {
            // 调用右侧面板显示完整内容
            if (typeof window.rightPanelManager === 'object' && window.rightPanelManager) {
                const data = event.data || {};
                const toolName = data.tool_name || event.tool || '';
                const output = data.output || '';

                // 根据工具类型决定显示方式
                if (toolName.toLowerCase() === 'read' || toolName.toLowerCase().includes('read')) {
                    // read 工具 - 显示文件内容
                    const input = data.input || {};
                    const filePath = input.path || input.file_path || 'unknown';
                    window.rightPanelManager.showFileEditor(filePath, output);
                } else if (output && typeof output === 'string' && output.length > 0) {
                    // bash/grep 等工具 - 显示输出
                    window.rightPanelManager.showFileEditor(`${toolName} 输出`, output);
                }
            }
        };
    }

    return item;
}

// 创建单个动作项
function createActionItem(action, index) {
    const item = document.createElement('div');

    // 判断动作类型
    const isThought = action.type === 'thought';
    const isError = action.type === 'error';

    // 根据类型设置图标和标题
    let iconName, title, content;
    let statusClass = 'text-gray-400';
    let statusIcon = 'schedule';

    if (isThought) {
        // 思考类型
        iconName = 'psychology';
        title = 'thought';
        content = action.content || '';
    } else if (isError) {
        // 错误类型
        iconName = 'error';
        title = '执行错误';
        content = action.content || '发生了未知错误';
        statusIcon = 'error';
        statusClass = 'text-red-500';
    } else {
        // 工具类型动作（read, write, execute, bash, grep, test 等）
        const toolType = action.tool || action.type || 'default';

        // 使用 getToolIcon 获取图标配置
        if (typeof getToolIcon === 'function') {
            const toolConfig = getToolIcon(toolType);
            iconName = toolConfig.icon;
        } else {
            iconName = 'extension';
        }

        title = toolType;
        content = action.description || action.brief || `${toolType} 操作`;
    }

    // 获取工具图标配置（使用灰色系）
    const toolIconHtml = `
        <div class="flex items-center justify-center bg-gray-100 dark:bg-zinc-800 rounded-lg p-1.5 flex-shrink-0">
            <span class="material-symbols-outlined text-gray-600 dark:text-gray-400 text-[16px]">
                ${iconName}
            </span>
        </div>
    `;

    item.className = 'action-item bg-gray-50 dark:bg-zinc-800/50 rounded-lg p-3 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer border border-transparent hover:border-primary/20 mb-2';
    item.innerHTML = `
        <div class="flex items-start gap-3">
            ${toolIconHtml}
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-xs font-bold text-gray-700 dark:text-gray-200">${title}</span>
                    <span class="text-[10px] text-gray-400 font-mono">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 font-mono bg-black/5 dark:bg-white/5 p-2 rounded-lg border border-border-light dark:border-border-dark break-all line-clamp-3">${escapeHtml(content || '')}</div>
            </div>
            <div class="flex-shrink-0">
                <span class="material-symbols-outlined ${statusClass} text-[14px]">${statusIcon}</span>
            </div>
        </div>
    `;

    // 点击展开详情
    item.onclick = () => {
        if (window.showActionDetail) window.showActionDetail(action);
    };

    return item;
}

// 创建任务交付卡片
function createDeliverableCard(session) {
    const card = document.createElement('div');
    card.className = 'space-y-6';

    const hasDeliverables = session.deliverables && session.deliverables.length > 0;
    const showMoreFiles = hasDeliverables && session.deliverables.length > 4;
    const displayFiles = hasDeliverables ? session.deliverables.slice(0, 4) : [];

    card.innerHTML = `
        <div class="space-y-4">
            ${session.response ? `
                <div>
                    ${marked.parse(session.response)}
                </div>
            ` : '<p class="text-slate-600 dark:text-slate-400">任务正在执行中...</p>'}
        </div>
        ${hasDeliverables ? `
            <div class="space-y-4">
                <h2 class="text-xl font-semibold text-slate-900 dark:text-white">
                    生成文件 ${showMoreFiles ? `(${session.deliverables.length} 个文件)` : `(${session.deliverables.length})`}
                </h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3" id="file-cards-${session.id}">
                    ${displayFiles.map((file, idx) => {
        const fileName = typeof file === 'string' ? file : (file.name || file.path || 'unknown');
        const fileExt = fileName.split('.').pop()?.toLowerCase() || '';
        const iconAndColor = getFileIconAndColor(fileExt);

        return `
                            <div class="file-card flex items-center gap-3 p-3 bg-card-light dark:bg-card-dark border border-transparent hover:border-slate-200 dark:hover:border-slate-700 transition-all rounded-xl group relative"
                                 data-file-name="${escapeHtml(fileName)}" data-file-ext="${fileExt}">
                                <div class="w-10 h-10 flex-shrink-0 bg-white dark:bg-slate-800 rounded-lg flex items-center justify-center shadow-sm">
                                    <span class="material-symbols-outlined ${iconAndColor.color} text-xl">${iconAndColor.icon}</span>
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-[13px] leading-snug text-slate-700 dark:text-slate-300 font-medium overflow-hidden text-ellipsis whitespace-nowrap">
                                        ${escapeHtml(fileName)}
                                    </div>
                                </div>
                                <!-- 操作按钮菜单 -->
                                <div class="file-actions relative">
                                    <button class="action-menu-btn p-1 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded transition-colors opacity-0 group-hover:opacity-100">
                                        <span class="material-symbols-outlined text-gray-500 dark:text-gray-400 text-[18px]">more_horiz</span>
                                    </button>
                                    <div class="action-menu hidden absolute right-0 top-8 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg shadow-lg py-1 z-50 min-w-[140px]">
                                        ${fileExt === 'html' ? `
                                            <button class="view-source-btn w-full px-3 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-700 flex items-center gap-2">
                                                <span class="material-symbols-outlined text-[16px]">code</span>
                                                查看源码
                                            </button>
                                        ` : ''}
                                        <button class="delete-file-btn w-full px-3 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2">
                                            <span class="material-symbols-outlined text-[16px]">delete</span>
                                            删除
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `;
    }).join('')}
                    ${showMoreFiles ? `
                        <div class="view-all-files flex items-center gap-3 p-3 bg-card-light dark:bg-card-dark border border-transparent hover:border-slate-200 dark:hover:border-slate-700 transition-all cursor-pointer rounded-xl group md:col-span-2 md:max-w-sm">
                            <div class="w-10 h-10 flex-shrink-0 bg-white dark:bg-slate-800 rounded-lg flex items-center justify-center shadow-sm">
                                <span class="material-symbols-outlined text-blue-500 text-xl">folder_open</span>
                            </div>
                            <div class="text-[13px] leading-snug text-slate-700 dark:text-slate-300 font-medium">
                                查看所有文件
                            </div>
                            <div class="text-xs text-slate-400 dark:text-slate-500 ml-auto">
                                ${session.deliverables.length} 个文件
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        ` : ''}
    `;

    // 绑定文件卡片点击事件
    if (hasDeliverables) {
        const fileCards = card.querySelectorAll('.file-card');
        fileCards.forEach(fileCard => {
            const fileName = fileCard.getAttribute('data-file-name');
            const fileExt = fileCard.getAttribute('data-file-ext');

            // 点击卡片主体（不包括操作按钮）
            fileCard.addEventListener('click', (e) => {
                // 如果点击的是操作按钮或菜单，不触发卡片点击
                if (e.target.closest('.file-actions')) return;

                console.log('点击文件卡片:', fileName, '扩展名:', fileExt);

                // HTML文件默认预览网页
                if (fileExt === 'html') {
                    // 使用正确的文件预览URL
                    const previewUrl = `/opencode/preview_file?session_id=${session.id}&file_path=${encodeURIComponent(fileName)}`;
                    console.log('[FileCard] Loading HTML preview:', previewUrl);

                    if (window.rightPanelManager && typeof window.rightPanelManager.showWebPreview === 'function') {
                        window.rightPanelManager.showWebPreview(previewUrl);
                    }
                } else {
                    // 其他文件显示源码
                    if (window.rightPanelManager && typeof window.rightPanelManager.showFileEditor === 'function') {
                        window.rightPanelManager.showFileEditor(fileName, '加载中...');
                        // 实际加载文件内容
                        fetch(`/opencode/read_file?session_id=${session.id}&file_path=${encodeURIComponent(fileName)}`)
                            .then(res => res.json())
                            .then(data => {
                                if (data.status === 'success' && data.content) {
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, data.content);
                                    }
                                } else {
                                    console.error('读取文件失败:', data);
                                    // 显示错误信息
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, `无法读取文件: ${data.message || '未知错误'}`);
                                    }
                                }
                            })
                            .catch(err => {
                                console.error('读取文件出错:', err);
                                if (window.rightPanelManager) {
                                    window.rightPanelManager.showFileEditor(fileName, `读取文件时出错: ${err.message}`);
                                }
                            });
                    }
                }
            });

            // 操作菜单按钮点击
            const menuBtn = fileCard.querySelector('.action-menu-btn');
            const menu = fileCard.querySelector('.action-menu');
            if (menuBtn && menu) {
                menuBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    // 关闭其他打开的菜单
                    card.querySelectorAll('.action-menu').forEach(m => {
                        if (m !== menu) m.classList.add('hidden');
                    });
                    menu.classList.toggle('hidden');
                });

                // 查看源码按钮（仅HTML文件）
                const viewSourceBtn = fileCard.querySelector('.view-source-btn');
                if (viewSourceBtn) {
                    viewSourceBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        menu.classList.add('hidden');
                        console.log('查看源码:', fileName);
                        // 读取文件内容并显示
                        fetch(`/opencode/read_file?session_id=${session.id}&file_path=${encodeURIComponent(fileName)}`)
                            .then(res => res.json())
                            .then(data => {
                                if (data.status === 'success' && data.content) {
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, data.content);
                                    }
                                } else {
                                    console.error('读取文件失败:', data);
                                }
                            })
                            .catch(err => console.error('读取文件出错:', err));
                    });
                }

                // 删除按钮
                const deleteBtn = fileCard.querySelector('.delete-file-btn');
                if (deleteBtn) {
                    deleteBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        menu.classList.add('hidden');
                        if (confirm(`确定要删除文件 "${fileName}" 吗？`)) {
                            console.log('删除文件:', fileName);
                            // 从deliverables中移除
                            const index = session.deliverables.findIndex(f => {
                                const fName = typeof f === 'string' ? f : (f.name || f.path);
                                return fName === fileName;
                            });
                            if (index > -1) {
                                session.deliverables.splice(index, 1);
                                // 重新渲染
                                if (typeof window.renderResults === 'function') {
                                    window.renderResults();
                                }
                            }
                        }
                    });
                }
            }
        });

        // 点击其他地方关闭所有菜单
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.file-actions')) {
                card.querySelectorAll('.action-menu').forEach(m => m.classList.add('hidden'));
            }
        });

        // 绑定"查看所有文件"按钮
        const viewAllBtn = card.querySelector('.view-all-files');
        if (viewAllBtn) {
            viewAllBtn.onclick = () => {
                // 唤起右侧文件面板
                if (typeof togglePanel === 'function') {
                    togglePanel('files');
                } else {
                    console.warn('togglePanel 函数未定义');
                }
            };
        }
    }

    return card;
}

// 根据文件扩展名获取图标和颜色
function getFileIconAndColor(ext) {
    const iconMap = {
        // 图片
        'png': { icon: 'image', color: 'text-purple-500' },
        'jpg': { icon: 'image', color: 'text-purple-500' },
        'jpeg': { icon: 'image', color: 'text-purple-500' },
        'gif': { icon: 'image', color: 'text-purple-500' },
        'svg': { icon: 'image', color: 'text-purple-500' },
        'webp': { icon: 'image', color: 'text-purple-500' },

        // 文档
        'pdf': { icon: 'picture_as_pdf', color: 'text-red-500' },
        'doc': { icon: 'description', color: 'text-blue-500' },
        'docx': { icon: 'description', color: 'text-blue-500' },
        'txt': { icon: 'text_snippet', color: 'text-gray-500' },
        'md': { icon: 'markdown', color: 'text-gray-600' },

        // 代码
        'js': { icon: 'javascript', color: 'text-yellow-500' },
        'ts': { icon: 'data_object', color: 'text-blue-600' },
        'py': { icon: 'code', color: 'text-blue-400' },
        'java': { icon: 'code', color: 'text-red-500' },
        'cpp': { icon: 'code', color: 'text-blue-500' },
        'c': { icon: 'code', color: 'text-blue-500' },
        'html': { icon: 'html', color: 'text-orange-500' },
        'css': { icon: 'css', color: 'text-blue-500' },
        'json': { icon: 'data_object', color: 'text-yellow-600' },

        // 其他
        'zip': { icon: 'folder_zip', color: 'text-amber-500' },
        'rar': { icon: 'folder_zip', color: 'text-amber-500' },
    };

    return iconMap[ext] || { icon: 'insert_drive_file', color: 'text-gray-500' };
}

// 显示事件详情弹窗
function showEventDetail(event) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4 animate-fade-in';

    const isThought = event.type === 'thought';
    const isTool = event.type === 'tool';
    const isError = event.type === 'error';

    let eventTitle = '事件详情';
    if (isThought) eventTitle = '思考过程';
    else if (isTool) eventTitle = `工具操作: ${event.tool || 'unknown'}`;
    else if (isError) eventTitle = '执行错误';

    modal.innerHTML = `
        <div class="bg-white dark:bg-surface-dark rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div class="px-6 py-4 border-b border-border-light dark:border-border-dark flex items-center justify-between">
                <h3 class="text-lg font-bold text-gray-900 dark:text-white">${eventTitle}</h3>
                <button class="close-modal p-1 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded transition-colors">
                    <span class="material-symbols-outlined text-gray-500">close</span>
                </button>
            </div>
            <div class="flex-1 overflow-y-auto p-6 space-y-4">
                ${event.type ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">类型</div>
                        <div class="text-sm px-3 py-2 bg-gray-100 dark:bg-zinc-800 rounded">${escapeHtml(event.type)}</div>
                    </div>
                ` : ''}
                ${event.tool ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">工具</div>
                        <div class="text-sm px-3 py-2 bg-gray-100 dark:bg-zinc-800 rounded font-mono">${escapeHtml(event.tool)}</div>
                    </div>
                ` : ''}
                ${event.content ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">内容</div>
                        <div class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">${escapeHtml(event.content)}</div>
                    </div>
                ` : ''}
                ${event.args ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">参数</div>
                        <pre class="text-xs font-mono p-3 bg-gray-100 dark:bg-zinc-800 rounded overflow-x-auto">${JSON.stringify(event.args, null, 2)}</pre>
                    </div>
                ` : ''}
                ${event.result ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">结果</div>
                        <pre class="text-xs font-mono p-3 bg-gray-100 dark:bg-zinc-800 rounded overflow-x-auto max-h-[300px]">${JSON.stringify(event.result, null, 2)}</pre>
                    </div>
                ` : ''}
                ${event.timestamp ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">时间戳</div>
                        <div class="text-sm text-gray-700 dark:text-gray-300">${escapeHtml(event.timestamp)}</div>
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
