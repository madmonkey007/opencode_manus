/**
 * Tool Icons - Material Symbols Outlined 风格的 SVG 图标定义
 * 为增强任务面板提供工具图标，参考 Manus.html 的设计风格
 * 统一使用 outlined 风格，gray-600 颜色，1.5px 描边宽度
 */

const TOOL_ICONS = {
    // 思考 - 信息图标（outlined 风格）
    'thought': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M11 7H13V9H11V7Z" fill="#475569"/>
        <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20ZM11 11H13V17H11V11Z" fill="#475569"/>
    </svg>`,

    // 文件编辑器 - 文档图标（outlined 风格）
    'file_editor': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="#475569" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M14 2V8H20" stroke="#475569" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M16 13H8" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M16 17H8" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    // 读取 - 打开的书本图标（outlined 风格）
    'read': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2.5C12 2.5 10 4.5 6.5 4.5C3 4.5 1 3 1 3V19C1 19 3 20.5 6.5 20.5C10 20.5 12 18.5 12 18.5C12 18.5 14 20.5 17.5 20.5C21 20.5 23 19 23 19V3C23 3 21 4.5 17.5 4.5C14 4.5 12 2.5 12 2.5Z" stroke="#475569" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M12 18.5V4" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M6.5 7.5C8 7.5 9.5 8 12 9C14.5 8 16 7.5 17.5 7.5" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M6.5 11.5C8 11.5 9.5 12 12 13C14.5 12 16 11.5 17.5 11.5" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    // 写入 - 编辑笔图标（outlined 风格）
    'write': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 17.25V21H6.75L17.81 9.94L14.06 6.19L3 17.25Z" stroke="#475569" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M15.13 5.12L16.96 3.29C17.35 2.9 17.98 2.9 18.37 3.29L20.71 5.63C21.1 6.02 21.1 6.65 20.71 7.04L18.88 8.87L15.13 5.12Z" stroke="#475569" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    // bash/execute - 终端命令图标（outlined 风格）
    'bash': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="#475569" stroke-width="1.5"/>
        <path d="M7 12L10 15L7 18" stroke="#475569" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M13 17H17" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    // terminal - 终端图标（outlined 风格，带 >_ 符号）
    'terminal': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="4" width="20" height="16" rx="2" stroke="#475569" stroke-width="1.5"/>
        <path d="M6 9L9 12L6 15" stroke="#475569" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M11 15H16" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    // grep - 搜索网格图标（outlined 风格）
    'grep': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="11" cy="11" r="6" stroke="#475569" stroke-width="1.5"/>
        <path d="M20 20L15.5 15.5" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M8 11H14" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,

    // browser - 浏览器图标（outlined 风格）
    'browser': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="#475569" stroke-width="1.5"/>
        <path d="M3 9H21" stroke="#475569" stroke-width="1.5"/>
        <circle cx="7.5" cy="6" r="1" fill="#475569"/>
        <circle cx="11.5" cy="6" r="1" fill="#475569"/>
    </svg>`,

    // web_search - 放大镜搜索图标（outlined 风格）
    'web_search': `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="11" cy="11" r="7" stroke="#475569" stroke-width="1.5"/>
        <path d="M21 21L15.5 15.5" stroke="#475569" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`
};

// getToolIcon 函数 - 根据工具类型返回图标配置
function getToolIcon(toolType) {
    // 直接返回 TOOL_ICONS 中的 SVG
    if (TOOL_ICONS[toolType]) {
        return { icon: TOOL_ICONS[toolType] };
    }

    // 如果没有找到，尝试匹配相似的工具类型
    const typeMapping = {
        'execute': 'bash',
        'command': 'bash',
        'file': 'file_editor',
        'edit': 'file_editor',
        'create': 'file_editor',
        'search': 'grep',
        'find': 'grep',
        'web': 'web_search',
        'http': 'browser'
    };

    const mappedType = typeMapping[toolType] || 'file_editor';
    return { icon: TOOL_ICONS[mappedType] || TOOL_ICONS['file_editor'] };
}

// Make TOOL_ICONS and getToolIcon available globally
if (typeof window !== 'undefined') {
    window.TOOL_ICONS = TOOL_ICONS;
    window.getToolIcon = getToolIcon;
}
