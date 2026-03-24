/**
 * OpenCode 配置管理模块
 *
 * 提供配置的读取、修改和持久化功能
 */

(function(window) {
    'use strict';

    /**
     * 配置管理器
     */
    const ConfigManager = {
        /**
         * 获取所有配置
         * @returns {Object} 配置对象
         */
        getAll() {
            return window.state.config || {};
        },

        /**
         * 获取单个配置项
         * @param {string} key - 配置键名
         * @returns {*} 配置值
         */
        get(key) {
            const config = this.getAll();
            return config[key];
        },

        /**
         * 设置单个配置项
         * @param {string} key - 配置键名
         * @param {*} value - 配置值
         * @param {boolean} saveToLocalStorage - 是否保存到localStorage
         */
        set(key, value, saveToLocalStorage = true) {
            if (!window.state.config) {
                window.state.config = {};
            }

            const oldValue = window.state.config[key];
            window.state.config[key] = value;

            // 保存到localStorage
            if (saveToLocalStorage) {
                this.saveToLocalStorage();
            }

            // 触发配置变更事件
            this._notifyChange(key, oldValue, value);

            if (window.state.config.verboseLogging) {
                console.log(`[Config] 配置已更新: ${key} =`, value, `(旧值: ${oldValue})`);
            }
        },

        /**
         * 批量设置配置
         * @param {Object} configs - 配置对象
         * @param {boolean} saveToLocalStorage - 是否保存到localStorage
         */
        setMultiple(configs, saveToLocalStorage = true) {
            Object.keys(configs).forEach(key => {
                this.set(key, configs[key], false); // 暂时不保存
            });

            if (saveToLocalStorage) {
                this.saveToLocalStorage();
            }

            if (window.state.config.verboseLogging) {
                console.log('[Config] 批量更新配置:', configs);
            }
        },

        /**
         * 保存配置到localStorage
         */
        saveToLocalStorage() {
            try {
                const state = {
                    config: window.state.config
                };
                localStorage.setItem('opencode_config', JSON.stringify(state));

                if (window.state.config.verboseLogging) {
                    console.log('[Config] 配置已保存到localStorage');
                }
            } catch (e) {
                console.error('[Config] 保存配置失败:', e);
            }
        },

        /**
         * 从localStorage加载配置
         */
        loadFromLocalStorage() {
            try {
                const saved = localStorage.getItem('opencode_config');
                if (saved) {
                    const parsed = JSON.parse(saved);
                    if (parsed.config) {
                        window.state.config = { ...window.state.config, ...parsed.config };
                        console.log('[Config] 已从localStorage加载配置');
                    }
                }
            } catch (e) {
                console.error('[Config] 加载配置失败:', e);
            }
        },

        /**
         * 重置为默认配置
         */
        resetToDefaults() {
            const defaults = {
                enableDeepLoad: false,
                deepLoadReason: 'Docker重启导致后端内存数据丢失，禁用深度加载以保护localStorage数据',
                verboseLogging: false
            };

            this.setMultiple(defaults);
            console.log('[Config] 已重置为默认配置');
        },

        /**
         * 打开配置面板UI
         */
        openConfigPanel() {
            const config = this.getAll();

            // 创建配置面板HTML
            const panel = document.createElement('div');
            panel.id = 'config-panel';
            panel.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                dark-mode: #1f2937;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                z-index: 9999;
                min-width: 500px;
                max-width: 90vw;
            `;

            panel.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; font-size: 20px; font-weight: 600;">⚙️ OpenCode 配置</h2>
                    <button id="close-config" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                </div>

                <div style="margin-bottom: 20px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="cfg-deepload" ${config.enableDeepLoad ? 'checked' : ''}
                            style="margin-right: 8px; cursor: pointer;">
                        <div>
                            <div style="font-weight: 500;">启用深度加载</div>
                            <div style="font-size: 12px; color: #6b7280;">
                                从后端API恢复历史数据（后端支持持久化存储时启用）
                            </div>
                        </div>
                    </label>
                    ${config.enableDeepLoad ? `
                        <div style="margin-top: 8px; margin-left: 24px; padding: 8px; background: #fef3c7; border-left: 3px solid #f59e0b; font-size: 12px;">
                            ⚠️ 注意：启用深度加载前，请确保后端已配置持久化存储（数据库/Redis）
                        </div>
                    ` : `
                        <div style="margin-top: 8px; margin-left: 24px; padding: 8px; background: #e5e7eb; font-size: 12px;">
                            ℹ️ 当前禁用原因：${config.deepLoadReason}
                        </div>
                    `}
                </div>

                <div style="margin-bottom: 20px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="cfg-verbose" ${config.verboseLogging ? 'checked' : ''}
                            style="margin-right: 8px; cursor: pointer;">
                        <div>
                            <div style="font-weight: 500;">启用详细日志</div>
                            <div style="font-size: 12px; color: #6b7280;">
                                在控制台显示详细的配置变更和调试信息
                            </div>
                        </div>
                    </label>
                </div>

                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button id="reset-config" style="padding: 8px 16px; background: white; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer;">
                        重置默认
                    </button>
                    <button id="save-config" style="padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer;">
                        保存配置
                    </button>
                </div>
            `;

            document.body.appendChild(panel);

            // 事件绑定
            document.getElementById('close-config').onclick = () => {
                document.body.removeChild(panel);
            };

            document.getElementById('cfg-deepload').onchange = (e) => {
                this.set('enableDeepLoad', e.target.checked, false); // 暂不保存
            };

            document.getElementById('cfg-verbose').onchange = (e) => {
                this.set('verboseLogging', e.target.checked, false);
            };

            document.getElementById('reset-config').onclick = () => {
                if (confirm('确定要重置为默认配置吗？')) {
                    this.resetToDefaults();
                    this.openConfigPanel(); // 刷新面板
                }
            };

            document.getElementById('save-config').onclick = () => {
                this.saveToLocalStorage();
                alert('✅ 配置已保存！');
                document.body.removeChild(panel);
            };
        },

        /**
         * 配置变更通知（内部使用）
         * @private
         */
        _notifyChange(key, oldValue, newValue) {
            // 可以在这里添加配置变更的回调
            // 例如：触发自定义事件
            if (typeof window.CustomEvent === 'function') {
                const event = new CustomEvent('opencode-config-change', {
                    detail: { key, oldValue, newValue }
                });
                window.dispatchEvent(event);
            }
        }
    };

    // 页面加载时从localStorage恢复配置
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            ConfigManager.loadFromLocalStorage();
        });
    } else {
        ConfigManager.loadFromLocalStorage();
    }

    // 导出到全局
    window.ConfigManager = ConfigManager;

    // 添加快捷命令
    window.openConfig = () => ConfigManager.openConfigPanel();

    console.log('[Config] 配置管理器已加载');
    console.log('        使用 window.ConfigManager 管理配置');
    console.log('        使用 window.openConfig() 打开配置面板');

})(window);
