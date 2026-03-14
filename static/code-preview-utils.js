/**
 * Code Preview 通用工具函数
 * 提取公共逻辑，遵循DRY原则
 */

/**
 * P1修复: SVG净化 - 防止XSS攻击
 * 验证SVG格式并确保安全性
 *
 * @param {string} svgContent - SVG字符串
 * @returns {boolean} - SVG是否有效且安全
 */
function isValidSVG(svgContent) {
    // Early Exit: 处理非字符串输入
    if (typeof svgContent !== 'string') {
        console.error('[PreviewIcon] SVG content must be a string');
        return false;
    }

    // 简单验证：确保只包含SVG标签和安全属性
    // 这个正则表达式匹配: 可选的空白 + <svg标签 + 内容 + </svg> + 可选的空白
    const svgPattern = /^[^<>]*<svg[^>]*>[^<]*<\/svg>[^<>]*$/i;

    if (!svgPattern.test(svgContent)) {
        console.error('[PreviewIcon] Invalid SVG format');
        return false;
    }

    // 额外的安全检查：确保没有危险的事件处理器
    const dangerousAttributes = ['onclick', 'onload', 'onerror', 'onmouseover', 'javascript:', 'data:text/html'];
    const hasDangerousContent = dangerousAttributes.some(attr =>
        svgContent.toLowerCase().includes(attr)
    );

    if (hasDangerousContent) {
        console.error('[PreviewIcon] SVG contains dangerous attributes');
        return false;
    }

    return true;
}

/**
 * P0修复: 公共函数 - 更新工具图标
 * 统一处理工具图标的显示逻辑，消除代码重复
 *
 * @param {HTMLElement} iconEl - 图标元素
 * @param {string} action - 动作类型（write/read/bash/edit/grep等）
 * @returns {void}
 */
function updateToolIcon(iconEl, action) {
    // Early Exit: 验证输入参数
    if (!iconEl || !iconEl.nodeType) {
        console.error('[PreviewIcon] Invalid icon element provided');
        return;
    }

    if (!action || typeof action !== 'string') {
        console.warn('[PreviewIcon] Invalid action, defaulting to "write"');
        action = 'write';
    }

    // 尝试使用全局的getToolIcon函数（如果存在）
    if (typeof window.getToolIcon === 'function') {
        try {
            const toolConfig = window.getToolIcon(action.toLowerCase() || 'write');

            if (toolConfig && toolConfig.icon) {
                // 处理SVG字符串
                if (toolConfig.icon.includes('<svg')) {
                    // P1修复: 添加SVG净化
                    if (isValidSVG(toolConfig.icon)) {
                        iconEl.innerHTML = toolConfig.icon;
                        // ✅ 修复：使用className完全替换，而不是classList.add
                        iconEl.className = 'tool-icon-svg';
                    } else {
                        // SVG无效，使用fallback
                        console.warn('[PreviewIcon] Invalid SVG for action:', action);
                        iconEl.textContent = 'edit';
                        iconEl.className = 'material-symbols-outlined text-[14px] text-blue-600 dark:text-blue-400';
                    }
                } else {
                    // 是图标名称字符串（如 'edit', 'search'等）
                    iconEl.textContent = toolConfig.icon;
                    iconEl.className = 'material-symbols-outlined text-[14px] text-blue-600 dark:text-blue-400';
                }

                return; // 成功处理，提前退出
            }
        } catch (e) {
            console.error('[PreviewIcon] Error using getToolIcon:', e);
            // 继续使用fallback逻辑
        }
    }

    // Fallback: 简单的图标映射（当getToolIcon不可用时）
    console.warn('[PreviewIcon] getToolIcon not available, using fallback');
    const iconMap = {
        'write': 'edit',
        'read': 'menu_book',
        'bash': 'terminal',
        'edit': 'edit_file',
        'grep': 'search',
        'browser': 'language',
        'web_search': 'search'
    };

    const iconName = iconMap[action.toLowerCase()] || 'edit';
    iconEl.textContent = iconName;
    iconEl.className = 'material-symbols-outlined text-[14px] text-blue-600 dark:text-blue-400';
}

/**
 * P0修复: 公共函数 - 更新动作文本和图标
 * 统一处理预览面板的动作显示
 *
 * @param {HTMLElement} actionTextEl - 动作文本元素
 * @param {HTMLElement} actionIconEl - 动作图标元素
 * @param {string} action - 动作类型
 * @returns {void}
 */
function updatePreviewAction(actionTextEl, actionIconEl, action) {
    // Early Exit: 验证输入参数
    if (!actionTextEl || !actionIconEl) {
        console.error('[PreviewIcon] Missing required elements');
        return;
    }

    // ✅ P1修复：添加action标准化和推断
    let normalizedAction = 'write';

    if (action && typeof action === 'string') {
        const trimmed = action.trim().toLowerCase();
        // 拒绝无效值
        if (trimmed && trimmed !== 'unknown') {
            normalizedAction = trimmed;
        }
    }

    // 更新动作文本
    actionTextEl.textContent = normalizedAction.toUpperCase();

    // 更新图标
    updateToolIcon(actionIconEl, normalizedAction);
}

// 导出到全局作用域
window.updateToolIcon = updateToolIcon;
window.updatePreviewAction = updatePreviewAction;
window.isValidSVG = isValidSVG;
