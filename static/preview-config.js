/**
 * Preview Config - 预览配置管理
 * 管理实时预览功能的用户配置
 */

class PreviewConfig {
    constructor() {
        this.config = this.loadConfig();
    }

    loadConfig() {
        // 从 localStorage 加载配置
        const saved = localStorage.getItem('preview_config');
        if (saved) {
            try {
                return { ...this.getDefaultConfig(), ...JSON.parse(saved) };
            } catch (e) {
                console.warn('Failed to load preview config:', e);
            }
        }
        return this.getDefaultConfig();
    }

    getDefaultConfig() {
        // 获取默认配置
        return {
            // 显示设置
            enabled_events: ['write', 'edit', 'bash'],
            show_thought_events: false,
            show_read_events: false,

            // 打字机效果
            typing_speed: 20,              // 字符/秒
            enable_typewriter: true,

            // UI 行为
            auto_scroll: true,
            auto_open_preview: true,
            preview_mode: 'overlay',       // 'overlay' | 'inline' | 'panel'

            // 历史设置
            max_history_days: 30,
            auto_cleanup: true
        };
    }

    saveConfig() {
        // 保存配置到 localStorage
        try {
            localStorage.setItem('preview_config', JSON.stringify(this.config));
        } catch (e) {
            console.warn('Failed to save preview config:', e);
        }
    }

    updateConfig(updates) {
        // 更新配置
        this.config = { ...this.config, ...updates };
        this.saveConfig();
    }

    isEventEnabled(eventType) {
        // 检查事件类型是否启用
        return this.config.enabled_events.includes(eventType);
    }

    get typingSpeed() {
        return this.config.typing_speed;
    }

    set typingSpeed(value) {
        this.config.typing_speed = value;
        this.saveConfig();
    }

    get enableTypewriter() {
        return this.config.enable_typewriter;
    }

    set enableTypewriter(value) {
        this.config.enable_typewriter = value;
        this.saveConfig();
    }

    get autoScroll() {
        return this.config.auto_scroll;
    }

    set autoScroll(value) {
        this.config.auto_scroll = value;
        this.saveConfig();
    }

    get autoOpenPreview() {
        return this.config.auto_open_preview;
    }

    set autoOpenPreview(value) {
        this.config.auto_open_preview = value;
        this.saveConfig();
    }

    get previewMode() {
        return this.config.preview_mode;
    }

    set previewMode(value) {
        this.config.preview_mode = value;
        this.saveConfig();
    }

    reset() {
        // 重置为默认配置
        this.config = this.getDefaultConfig();
        this.saveConfig();
    }

    exportConfig() {
        // 导出配置为 JSON 字符串
        return JSON.stringify(this.config, null, 2);
    }

    importConfig(configJson) {
        // 从 JSON 字符串导入配置
        try {
            const parsed = JSON.parse(configJson);
            this.config = { ...this.getDefaultConfig(), ...parsed };
            this.saveConfig();
            return true;
        } catch (e) {
            console.error('Failed to import config:', e);
            return false;
        }
    }
}

// 全局配置实例
let previewConfig;

function initPreviewConfig() {
    previewConfig = new PreviewConfig();
    window.previewConfig = previewConfig;
    return previewConfig;
}

// 在 DOMContentLoaded 时初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPreviewConfig);
} else {
    initPreviewConfig();
}

// 导出初始化函数
window.initPreviewConfig = initPreviewConfig;
