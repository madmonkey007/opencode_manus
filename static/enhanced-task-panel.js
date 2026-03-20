/**
 * Enhanced Task Panel - Manus-style Progressive Disclosure
 * 实现类似 Manus 的逐级展开任务面板
 */

/**
 * ✅ 辅助函数 - 按时间戳排序事件
 */
window.sortEventsByTimestamp = function (events) {
    if (!Array.isArray(events)) return [];
    return [...events].sort((a, b) => {
        const timeA = a.timestamp || (a.data && a.data.timestamp) || a.time || 0;
        const timeB = b.timestamp || (b.data && b.data.timestamp) || b.time || 0;
        return timeA - timeB;
    });
};

/**
 * ✅ 代码审查修复：辅助函数 - 从文件对象中提取文件名和扩展名
 */
function extractFileInfo(file) {
    const fileName = typeof file === 'string' ? file : (file.name || file.path || '');
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    return { fileName, ext };
}

/**
 * ✅ 代码审查修复：文件路径验证函数
 * 防止路径遍历攻击（../../etc/passwd）
 * 修复问题：Important #1 - 缺少文件路径验证
 */
function isValidFilePath(filePath) {
    // ✅ 方案1修复：允许Linux/Mac绝对路径（后端标准路径格式）
    // 例如：/app/opencode/workspace/ses_xxx/file.html

    // 阻止路径遍历攻击（关键安全验证）
    if (filePath.includes('..')) {
        console.warn('[Security] Path traversal attack detected:', filePath);
        return false;
    }

    // 阻止Windows绝对路径（\\开头）
    if (filePath.startsWith('\\\\')) {
        console.warn('[Security] Windows absolute path not allowed:', filePath);
        return false;
    }

    // ✅ 允许Linux/Mac绝对路径（/开头）- 后端标准路径格式

    // 验证路径格式（允许绝对路径和相对路径）
    // 规则：字母、数字、下划线、点、短横线、斜杠
    const validPattern = /^[a-zA-Z0-9_\-.\/]+\.[a-zA-Z0-9]+$/;
    const isValid = validPattern.test(filePath);

    if (!isValid) {
        console.warn('[Security] Invalid file path format:', filePath);
    }

    return isValid;
}

/**
 * ✅ 代码审查修复：安全地渲染Markdown内容
 * 使用textContent防止XSS攻击
 * 修复问题：Critical #1 - marked.parse()未消毒
 */
function safeRenderMarkdown(markdownContent) {
    // ⚠️ 安全警告：marked.parse() 输出包含用户内容，必须消毒！
    // 推荐方案：安装并使用DOMPurify
    //   npm install dompurify
    //   import DOMPurify from 'dompurify';
    //   return DOMPurify.sanitize(marked.parse(markdownContent));
    //
    // ✅ v=38.4.11 改进：使用简化的markdown渲染器
    // 支持常见格式：**粗体**、*斜体*、- 列表、`代码`、换行等
    // 安全性：只处理特定的markdown语法，不渲染HTML标签
    try {
        if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
            // 生产环境：使用DOMPurify消毒
            return DOMPurify.sanitize(marked.parse(markdownContent));
        } else {
            // ✅ v=38.4.11: 简化的markdown渲染器（安全且支持基本格式）
            return renderSimpleMarkdown(markdownContent);
        }
    } catch (e) {
        console.error('[safeRenderMarkdown] Failed to render markdown:', e);
        const div = document.createElement('div');
        div.textContent = markdownContent;
        return div.innerHTML;
    }
}

/**
 * ✅ v=38.4.11: 简化的markdown渲染器
 * 支持基本markdown语法，同时保证XSS安全
 * 不使用eval/innerHTML，手动构建DOM
 */
function renderSimpleMarkdown(text) {
    if (!text) return '';

    // 安全处理：先转义HTML特殊字符
    let safeText = escapeHtml(text);

    // ✅ 优化1：移除统计信息行（完成阶段、工具调用、任务完成等）
    // 匹配各种格式的统计信息行（包括带emoji的）
    safeText = safeText.replace(/^[\s]*[✅❌⚠️🔧📝💡🎯📊⭐]*[\s]*任务完成.*$/gm, '');
    safeText = safeText.replace(/^[\s]*任务完成.*$/gm, '');
    safeText = safeText.replace(/^[\s]*(完成阶段|阶段|阶段完成|完成).*[:：].*$/gm, '');
    safeText = safeText.replace(/^[\s]*工具调用.*[:：].*$/gm, '');
    safeText = safeText.replace(/^[\s]*\*.*完成阶段.*$/gm, '');
    safeText = safeText.replace(/^[\s]*\*.*工具调用.*$/gm, '');
    // ✅ 移除列表项格式的统计信息
    safeText = safeText.replace(/^[\s]*-\s*[✅❌⚠️🔧📝💡🎯📊⭐]*[\s]*(完成阶段|阶段|任务完成).*[:：]?.*$/gm, '');
    safeText = safeText.replace(/^[\s]*-\s*(完成阶段|阶段).*[:：].*$/gm, '');
    safeText = safeText.replace(/^[\s]*-\s*工具调用.*[:：].*$/gm, '');
    safeText = safeText.replace(/^[\s]*•\s*[✅❌⚠️🔧📝💡🎯📊⭐]*[\s]*(完成阶段|阶段|任务完成).*[:：]?.*$/gm, '');
    safeText = safeText.replace(/^[\s]*•\s*(完成阶段|阶段).*[:：].*$/gm, '');
    safeText = safeText.replace(/^[\s]*•\s*工具调用.*[:：].*$/gm, '');

    // ✅ 优化2：移除emoji（包括带 ✅ 等标记的行）
    // 移除行首的emoji和标记（如 ✅、❌、⚠️ 等）
    safeText = safeText.replace(/^[\s]*[✅❌⚠️🔧📝💡🎯📊⭐]+[\s]*/gm, '');
    // 移除行中的emoji
    safeText = safeText.replace(/[✅❌⚠️🔧📝💡🎯📊⭐]/g, '');

    // 然后处理markdown语法（从特殊到一般，避免重复处理）
    // 1. 代码块 ```code```
    safeText = safeText.replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-100 dark:bg-zinc-800 p-2 rounded my-2 overflow-x-auto text-xs"><code>$1</code></pre>');

    // 2. 行内代码 `code`
    safeText = safeText.replace(/`([^`]+)`/g, '<code class="bg-gray-100 dark:bg-zinc-800 px-1 rounded text-xs">$1</code>');

    // 3. 粗体 **text**
    safeText = safeText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 4. 斜体 *text*
    safeText = safeText.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 5. 链接 [text](url)
    safeText = safeText.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-500 underline" target="_blank" rel="noopener">$1</a>');

    // ✅ 优化3：处理分隔符 --- 作为段落分隔（换行显示）
    safeText = safeText.replace(/^---+$/gm, '<hr class="my-2 border-gray-300 dark:border-zinc-700">');

    // ✅ 优化4：改进无序列表处理 - 每个列表项单独成行
    // 匹配连续的列表项，并为每个创建独立的段落
    const listPattern = /(^|\n)- (.+?)(?=\n- |\n\n|\n\d+\. |\n*$)/g;
    safeText = safeText.replace(listPattern, (match, prefix, itemContent) => {
        // 移除列表项中的emoji
        const cleanContent = itemContent.replace(/^[✅❌⚠️🔧📝💡🎯📊⭐]+[\s]*/, '');
        return `<div class="flex items-start gap-2 my-2"><span class="text-gray-400 dark:text-gray-600 mt-0.5">•</span><span>${cleanContent}</span></div>`;
    });

    // ✅ 优化5：改进有序列表处理 - 每个列表项单独成行
    const orderedListPattern = /(^|\n)(\d+)\. (.+?)(?=\n\d+\. |\n\n|\n- |\n*$)/g;
    safeText = safeText.replace(orderedListPattern, (match, prefix, num, itemContent) => {
        const cleanContent = itemContent.replace(/^[✅❌⚠️🔧📝💡🎯📊⭐]+[\s]*/, '');
        return `<div class="flex items-start gap-2 my-2"><span class="text-gray-400 dark:text-gray-600 mt-0.5 font-semibold">${num}.</span><span>${cleanContent}</span></div>`;
    });

    // 6. 标题 # Heading
    safeText = safeText.replace(/^### (.+)$/gm, '<h3 class="text-sm font-bold my-2">$1</h3>');
    safeText = safeText.replace(/^## (.+)$/gm, '<h2 class="text-base font-bold my-2">$1</h2>');
    safeText = safeText.replace(/^# (.+)$/gm, '<h1 class="text-lg font-bold my-2">$1</h1>');

    // 7. 换行（不在列表中的换行）
    // 使用 /\n{2,}/g 匹配2个或更多连续换行符
    safeText = safeText.replace(/\n{2,}/g, '<br class="mb-3">');

    // 8. 单个换行转换为<br>
    safeText = safeText.replace(/\n/g, '<br>');

    return safeText;
}

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

    // ✅ v=36优化：预计算deliverables按turn_index分组（只执行一次）
    // 性能：O(n)总复杂度，vs 原方案的O(n * turnsCount)
    // 避免：每一轮都filter所有deliverables
    const deliverablesByTurn = {};
    if (session.deliverables && session.deliverables.length > 0) {
        session.deliverables.forEach(d => {
            // 兼容新旧格式：
            // - 新格式：{ path: '/app/file.html', turn_index: 1, timestamp: ... }
            // - 旧格式：'/app/file.html'
            const path = typeof d === 'string' ? d : (d.path || d);
            const turn = typeof d === 'object' && d.turn_index ? d.turn_index : 1;

            if (!deliverablesByTurn[turn]) {
                deliverablesByTurn[turn] = [];
            }
            deliverablesByTurn[turn].push(path);
        });
    }

    for (let i = 0; i < turnsCount; i++) {
        const turnContainer = document.createElement('div');
        turnContainer.className = `conversation-turn space-y-4 ${i < turnsCount - 1 ? 'border-b border-gray-100 dark:border-zinc-800 pb-8' : ''}`;

        // 1. 该轮的用户输入
        if (prompts[i]) {
            const userCard = createUserPromptCard(prompts[i]);
            turnContainer.appendChild(userCard);
        }

        // 2. 任务阶段卡片
        const turnPhases = session.phases ? session.phases.filter(p => {
            const phaseTurn = parseInt(p.turn_index, 10);
            return phaseTurn === i + 1;
        }) : [];

        // 兜底：最后一轮且没有匹配 turn_index 时，显示所有 phases（含历史恢复的无 turn_index phases）
        if (i === turnsCount - 1 && turnPhases.length === 0 && session.phases && session.phases.length > 0) {
            const unassociatedPhases = session.phases.filter(p => {
                const phaseTurn = parseInt(p.turn_index, 10);
                return !p.turn_index || isNaN(phaseTurn);
            });
            // ✅ 历史恢复兜底：如果所有 phases 都没有 turn_index，全部显示
            const phasesToShow = unassociatedPhases.length > 0 ? unassociatedPhases : session.phases;
            if (phasesToShow.length > 0) {
                const phasesCard = createPhasesCard(phasesToShow, session.currentPhase);
                turnContainer.appendChild(phasesCard);
            }
        } else if (turnPhases.length > 0) {
            const phasesCard = createPhasesCard(turnPhases, session.currentPhase);
            turnContainer.appendChild(phasesCard);
        }

        // 2b. thoughtEvents（历史恢复时 thought 不在 phase.events 里）
        // 只在最后一轮插入，避免多轮对话重复显示
        // 包进伪 phase 卡片，样式与真实 phase 一致（兜底：phases 为空时也能显示）
        if (i === turnsCount - 1 && session.thoughtEvents && session.thoughtEvents.length > 0) {
            const thoughtEvents = session.thoughtEvents.map(ev => ({
                type: 'thought',
                content: ev.content || ev.data?.text || '',
                id: ev.id
            })).filter(ev => ev.content);
            if (thoughtEvents.length > 0) {
                const thoughtPhaseCard = createPhasesCard([{
                    id: '_thought_pseudo_phase',
                    title: '思考过程',
                    status: 'done',
                    events: thoughtEvents
                }], null);
                turnContainer.appendChild(thoughtPhaseCard);
            }
        }

        // 3. 该轮的回答和交付物

        // ✅ v=37优化：从预计算的Map中获取当前轮次的deliverables（O(1)）
        const turnDeliverables = deliverablesByTurn[i + 1] || [];

        // ✅ v=37修复：更健壮的渲染条件
        // 问题：追问时response可能为空，导致交付面板不显示
        // 解决：满足以下任一条件就渲染：
        //   1. 有response内容，或
        //   2. 是最后一轮，或
        //   3. 有该轮的deliverables（即使response为空）
        const hasResponse = responses[i] && responses[i].trim();
        const isLastTurn = i === turnsCount - 1;
        const hasDeliverables = turnDeliverables && turnDeliverables.length > 0;

        // 调试日志
        console.log('[Render] Turn', i + 1, 'conditions:', {
            hasResponse,
            isLastTurn,
            hasDeliverables,
            deliverablesCount: turnDeliverables.length,
            willRender: hasResponse || isLastTurn || hasDeliverables
        });

        if (responses[i] !== undefined && responses[i] !== null) {
            if (hasResponse || isLastTurn || hasDeliverables) {
                const summaryCard = createDeliverableCard({
                    ...session,
                    response: responses[i] || '',  // ✅ 确保response不为undefined
                    // ✅ v=37修复：每轮只显示该轮生成的交付物，不显示其他轮的
                    // 使用预计算Map，性能优化：O(1)查询 vs O(n) filter
                    deliverables: turnDeliverables
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
    card.className = 'message-bubble user-bubble text-sm';
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
    // ✅ v=38.4.11 修复：使用工具函数按时间戳排序，确保事件显示顺序正确
    // 问题：SSE事件到达顺序可能乱序，导致thought事件显示在工具调用之后
    // 解决：使用全局工具函数window.sortEventsByTimestamp排序（升序，早的在前）
    if (phase.events) {
        const sortedEvents = window.sortEventsByTimestamp(phase.events);

        if (sortedEvents.length > 0) {
            sortedEvents.forEach((event, eventIdx) => {
                const eventItem = createEventItem(event, eventIdx);
                body.appendChild(eventItem);
            });
        } else if (isActive) { // 如果是当前活动阶段但没有事件
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'text-xs text-gray-400 italic py-1 px-4 ml-6';
            loadingMsg.textContent = '准备执行中...';
            body.appendChild(loadingMsg);
        } else { // 已完成或未开始但没有事件的阶段
            const emptyMsg = document.createElement('div');
            emptyMsg.className = 'text-xs text-gray-400 italic py-1 px-4 ml-6';
            emptyMsg.textContent = '无关联事件';
            body.appendChild(emptyMsg);
        }
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

    // === 基础文件操作 ===
    if (tool === 'read') {
        const path = input.path || input.file_path || input.file;
        return path ? `读取文件: ${path}` : '读取文件';
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

    // === 命令行工具 ===
    if (tool === 'bash' || tool === 'terminal' || tool === 'execute') {
        const cmd = input.command || input.cmd;
        return cmd ? `执行命令: ${cmd}` : '执行命令';
    }

    if (tool === 'grep') {
        const pattern = input.pattern || input.regex || input.search;
        const path = input.path || input.file_path || input.file;
        if (pattern && path) {
            return `搜索: ${pattern} 在 ${path}`;
        }
        return pattern ? `搜索: ${pattern}` : '搜索';
    }

    // === 子agent工具 ===
    if (tool === 'subagent_explore' || tool === 'explore') {
        const query = input.query || input.description || input.task;
        return query ? `探索: ${query}` : '探索任务';
    }

    if (tool === 'subagent_coder' || tool === 'coder') {
        const task = input.task || input.description || input.instruction;
        return task ? `代码生成: ${task}` : '代码生成';
    }

    if (tool === 'subagent_delegate' || tool === 'delegate_task') {
        const category = input.category || input.subagent_type;
        const task = input.task || input.description;
        if (category && task) {
            return `委托${category}: ${task}`;
        }
        return task ? `委托任务: ${task}` : '委托任务';
    }

    if (tool === 'todos' || tool === 'todowrite') {
        const todoCount = input.todos ? input.todos.length : 0;
        return todoCount > 0 ? `更新任务列表 (${todoCount}项)` : '更新任务列表';
    }

    if (tool === 'skill') {
        const skillName = input.name || input.skill;
        return skillName ? `加载技能: ${skillName}` : '加载技能';
    }

    // === 网络工具 ===
    if (tool === 'browser') {
        const action = input.action || input.url;
        return action ? `浏览器操作: ${action}` : '浏览器操作';
    }

    if (tool === 'web_search' || tool === 'search') {
        const query = input.query || input.q;
        return query ? `搜索: ${query}` : '搜索';
    }

    // === 其他工具 ===
    if (tool === 'system') {
        return '系统操作';
    }

    if (tool === 'database') {
        const action = input.mode || input.action;
        return action ? `数据库操作: ${action}` : '数据库操作';
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
        // ✅ v=38.4.11 修复：thought内容使用markdown渲染
        // 原因：GLM-4.7的reasoning内容包含markdown格式（列表、粗体等）
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
            // ✅ v=38.4.11 优化：减小bash/terminal字体大小，特别针对中文字符
            detailsHtml = `
                <div class="mt-2 p-2 bg-gray-50 dark:bg-black/20 rounded border border-gray-100 dark:border-white/5 font-mono text-[9px] leading-tight overflow-auto max-h-60">
                    ${inputIsNotEmpty ? `<div class="text-blue-500 mb-0.5">Incoming Input:</div><pre class="whitespace-pre-wrap mb-1">${escapeHtml(input)}</pre>` : ''}
                    ${output ? `<div class="text-green-500 mb-0.5">Command Output:</div><pre class="whitespace-pre-wrap">${escapeHtml(output)}</pre>` : ''}
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
                <div class="event-content text-xs text-gray-500 dark:text-gray-400 ${isExpandable ? 'line-clamp-1' : ''}">${isThought ? safeRenderMarkdown(content || '') : escapeHtml(content || '')}</div>
                <div class="event-details text-xs text-gray-500 dark:text-gray-400 hidden">${detailsHtml || (isThought ? safeRenderMarkdown(content || '') : escapeHtml(content || ''))}</div>
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

    // 早出口：如果没有交付物，只显示响应内容
    const hasDeliverables = session.deliverables && session.deliverables.length > 0;
    if (!hasDeliverables) {
        // ✅ 代码审查修复 #1: 使用safeRenderMarkdown防止XSS，而不是marked.parse
        card.innerHTML = `
            <div class="space-y-4">
                ${session.response ? `
                    <div>
                        ${safeRenderMarkdown(session.response)}
                    </div>
                ` : '<p class="text-slate-600 dark:text-slate-400">任务正在执行中...</p>'}
            </div>
        `;
        return card;
    }

    // ✅ 代码审查修复 #2: 使用辅助函数消除重复代码
    // 分类文件：网页文件 vs 非网页文件
    const webExtensions = ['html', 'htm'];
    const allFiles = session.deliverables;

    const webFiles = allFiles.filter(f => {
        const { ext } = extractFileInfo(f);
        return webExtensions.includes(ext);
    });

    const docFiles = allFiles.filter(f => {
        const { ext } = extractFileInfo(f);
        return !webExtensions.includes(ext);
    });

    const hasWebFiles = webFiles.length > 0;
    const hasDocFiles = docFiles.length > 0;
    const showMoreDocFiles = docFiles.length > 4;
    const displayDocFiles = docFiles.slice(0, 4);

    // ✅ 代码审查修复 #1: 响应内容也使用safeRenderMarkdown防止XSS
    card.innerHTML = `
        <div class="space-y-4">
            ${session.response ? `
                <div>
                    ${safeRenderMarkdown(session.response)}
                </div>
            ` : '<p class="text-slate-600 dark:text-slate-400">任务正在执行中...</p>'}
        </div>

        <div class="space-y-4">
            <h2 class="text-xl font-semibold text-slate-900 dark:text-white">
                交付文件
            </h2>

            ${hasWebFiles ? `
                <div class="space-y-3">
                    <div class="grid grid-cols-1 gap-3" id="web-file-cards-${session.id}">
                        ${webFiles.map((file, idx) => {
        // ✅ 代码审查修复 #2: 使用辅助函数提取文件信息
        const { fileName, ext } = extractFileInfo(file);
        // ✅ 代码审查修复 #1: 添加文件路径验证
        if (!isValidFilePath(fileName)) {
            console.warn('[Security] Skipping invalid file path:', fileName);
            return '';
        }
        const previewUrl = `/opencode/preview_file?session_id=${session.id}&file_path=${encodeURIComponent(fileName)}`;
        const iconAndColor = getFileIconAndColor(ext);

        return `
                                <div class="web-file-card flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800 hover:border-blue-300 dark:hover:border-blue-700 transition-all rounded-xl group cursor-pointer"
                                     data-file-name="${escapeHtml(fileName)}" data-preview-url="${previewUrl}">
                                    <div class="flex items-center gap-3 min-w-0">
                                        <div class="w-10 h-10 flex-shrink-0 bg-white dark:bg-slate-800 rounded-lg flex items-center justify-center shadow-sm">
                                            <span class="material-symbols-outlined ${iconAndColor.color} text-xl">${iconAndColor.icon}</span>
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <div class="text-[14px] leading-snug text-slate-700 dark:text-slate-300 font-medium overflow-hidden text-ellipsis whitespace-nowrap">
                                                ${escapeHtml(fileName)}
                                            </div>
                                            <div class="text-xs text-slate-500 dark:text-slate-400">
                                                HTML 文件
                                            </div>
                                        </div>
                                    </div>
                                    <button class="preview-btn flex-shrink-0 p-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors opacity-0 group-hover:opacity-100 flex items-center gap-2">
                                        <span class="material-symbols-outlined text-[18px]">visibility</span>
                                        <span class="text-sm font-medium">预览</span>
                                    </button>
                                </div>
                            `;
    }).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${hasDocFiles ? `
                <div class="space-y-3">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3" id="doc-file-cards-${session.id}">
                        ${displayDocFiles.map((file, idx) => {
        // ✅ 代码审查修复 #2: 使用辅助函数提取文件信息
        const { fileName, ext } = extractFileInfo(file);
        // ✅ 代码审查修复 #1: 添加文件路径验证
        if (!isValidFilePath(fileName)) {
            console.warn('[Security] Skipping invalid file path:', fileName);
            return '';
        }
        const iconAndColor = getFileIconAndColor(ext);

        return `
                                <div class="file-card flex items-center gap-3 p-3 bg-card-light dark:bg-card-dark border border-transparent hover:border-slate-200 dark:hover:border-slate-700 transition-all rounded-xl group relative"
                                     data-file-name="${escapeHtml(fileName)}" data-file-ext="${ext}">
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
                                            ${ext === 'html' ? `
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
                        ${showMoreDocFiles ? `
                            <div class="view-all-files flex items-center gap-3 p-3 bg-card-light dark:bg-card-dark border border-transparent hover:border-slate-200 dark:hover:border-slate-700 transition-all cursor-pointer rounded-xl group md:col-span-2 md:max-w-sm">
                                <div class="w-10 h-10 flex-shrink-0 bg-white dark:bg-slate-800 rounded-lg flex items-center justify-center shadow-sm">
                                    <span class="material-symbols-outlined text-blue-500 text-xl">folder_open</span>
                                </div>
                                <div class="text-[13px] leading-snug text-slate-700 dark:text-slate-300 font-medium">
                                    查看所有文件
                                </div>
                                <div class="text-xs text-slate-400 dark:text-slate-500 ml-auto">
                                    ${docFiles.length} 个文件
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            ` : ''}
        </div>
    `;

    // 绑定网页文件卡片点击事件
    if (hasWebFiles) {
        const webFileCards = card.querySelectorAll('.web-file-card');
        webFileCards.forEach(fileCard => {
            const previewUrl = fileCard.getAttribute('data-preview-url');
            const fileName = fileCard.getAttribute('data-file-name');

            // 点击预览按钮
            const previewBtn = fileCard.querySelector('.preview-btn');
            if (previewBtn) {
                previewBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    console.log('[Deliverable] Preview web file:', fileName);
                    if (window.rightPanelManager && typeof window.rightPanelManager.showWebPreview === 'function') {
                        window.rightPanelManager.showWebPreview(session.id, fileName);
                    }
                });
            }

            // 点击整个卡片也触发预览
            fileCard.addEventListener('click', (e) => {
                if (e.target.closest('.preview-btn')) return;
                console.log('[Deliverable] Click web file card:', fileName);
                if (window.rightPanelManager && typeof window.rightPanelManager.showWebPreview === 'function') {
                    window.rightPanelManager.showWebPreview(session.id, fileName);
                }
            });
        });
    }

    // 绑定文档文件卡片点击事件
    if (hasDocFiles) {
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
                    console.log('[FileCard] Loading HTML preview:', fileName);

                    if (window.rightPanelManager && typeof window.rightPanelManager.showWebPreview === 'function') {
                        window.rightPanelManager.showWebPreview(session.id, fileName);
                    }
                } else {
                    // 其他文件显示源码
                    if (window.rightPanelManager && typeof window.rightPanelManager.showFileEditor === 'function') {
                        window.rightPanelManager.showFileEditor(fileName, '加载中...');
                        // 实际加载文件内容
                        fetch(`/opencode/read_file?session_id=${session.id}&file_path=${encodeURIComponent(fileName)}`)
                            .then(res => {
                                // ✅ 代码审查修复 #2: 改进错误处理 - 提供更详细的HTTP错误信息
                                if (!res.ok) {
                                    // 根据HTTP状态码提供更具体的错误信息
                                    if (res.status === 404) {
                                        throw new Error('文件不存在或已被删除');
                                    } else if (res.status === 403) {
                                        throw new Error('没有访问权限');
                                    } else if (res.status >= 500) {
                                        throw new Error('服务器错误，请稍后重试');
                                    } else {
                                        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                                    }
                                }
                                return res.json();
                            })
                            .then(data => {
                                if (data.status === 'success' && data.content) {
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, data.content);
                                    }
                                } else {
                                    console.error('读取文件失败:', data);
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, `无法读取文件: ${data.message || '未知错误'}`);
                                    }
                                }
                            })
                            .catch(err => {
                                console.error('读取文件出错:', err);
                                if (window.rightPanelManager) {
                                    window.rightPanelManager.showFileEditor(fileName, `无法读取文件: ${err.message}`);
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
                            .then(res => {
                                // ✅ 代码审查修复 #2: 改进错误处理 - 提供更详细的HTTP错误信息
                                if (!res.ok) {
                                    if (res.status === 404) {
                                        throw new Error('文件不存在或已被删除');
                                    } else if (res.status === 403) {
                                        throw new Error('没有访问权限');
                                    } else if (res.status >= 500) {
                                        throw new Error('服务器错误，请稍后重试');
                                    } else {
                                        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                                    }
                                }
                                return res.json();
                            })
                            .then(data => {
                                if (data.status === 'success' && data.content) {
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, data.content);
                                    }
                                } else {
                                    console.error('读取文件失败:', data);
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, `无法读取文件: ${data.message || '未知错误'}`);
                                    }
                                }
                            })
                            .catch(err => {
                                console.error('读取文件出错:', err);
                                if (window.rightPanelManager) {
                                    window.rightPanelManager.showFileEditor(fileName, `无法读取文件: ${err.message}`);
                                }
                            });
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
                // 切换到右侧面板的Files标签
                if (window.rightPanelManager && typeof window.rightPanelManager.switchTab === 'function') {
                    window.rightPanelManager.switchTab('files');
                } else if (typeof togglePanel === 'function') {
                    togglePanel('files');
                } else {
                    console.warn('无法打开文件面板');
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
        'xls': { icon: 'table_chart', color: 'text-green-500' },
        'xlsx': { icon: 'table_chart', color: 'text-green-500' },
        'ppt': { icon: 'slideshow', color: 'text-orange-500' },
        'pptx': { icon: 'slideshow', color: 'text-orange-500' },
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

// ✅ 代码审查修复 #3: 优化全局菜单监听器性能 - 只在菜单显示时才查询DOM
// 修复问题：Important #3 - 每次点击都querySelectorAll影响性能
document.addEventListener('click', (e) => {
    // 只在菜单显示时才查询（性能优化）
    const visibleMenus = document.querySelectorAll('.action-menu:not(.hidden)');
    if (visibleMenus.length > 0 && !e.target.closest('.file-actions')) {
        visibleMenus.forEach(m => m.classList.add('hidden'));
    }
});

// 导出函数
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { renderEnhancedTaskPanel };
}

// 挂载到全局作用域，确保其他脚本可以访问（浏览器环境）
window.renderEnhancedTaskPanel = renderEnhancedTaskPanel;

