/**
 * 调试脚本：检查preview事件流
 *
 * 使用方法：
 * 1. 在浏览器控制台运行此脚本
 * 2. 运行一个新任务（如"写一个网页版闹钟"）
 * 3. 观察控制台输出
 */

(function() {
    console.log('🔍 [Preview Debug] 开始监听preview事件...');

    // 1. 检查EventSource连接
    const checkEventSource = () => {
        if (typeof EventSource === 'undefined') {
            console.error('❌ EventSource不可用');
            return false;
        }

        const activeSSE = window.state?.activeSSE;
        if (!activeSSE) {
            console.warn('⚠️ 没有活跃的SSE连接');
            return false;
        }

        console.log('✅ SSE连接状态:', activeSSE.readyState);
        console.log('   0=CONNECTING, 1=OPEN, 2=CLOSED');
        return true;
    };

    // 2. 拦截EventSource.onmessage
    const originalOnMessage = EventSource.prototype.onmessage;
    let previewEventCount = 0;
    let previewEventTypes = new Set();

    EventSource.prototype.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            const eventType = data.type;

            // 统计所有事件类型
            if (!previewEventTypes.has(eventType)) {
                previewEventTypes.add(eventType);
                console.log(`📨 [Event] 新的事件类型: ${eventType}`);
            }

            // 专门监听preview事件
            if (eventType && eventType.includes('preview')) {
                previewEventCount++;
                console.log(`🎯 [Preview Event #${previewEventCount}]`, {
                    type: eventType,
                    hasData: !!data.data,
                    hasDelta: !!data.delta,
                    hasFilePath: !!data.file_path,
                    stepId: data.step_id,
                    filePath: data.file_path
                });

                // 详细显示delta内容
                if (data.delta) {
                    const delta = data.delta;
                    console.log(`   Delta: type=${delta.type}, content_length=${delta.content?.length || 0}, position=${delta.position}`);
                }
            }
        } catch (e) {
            // 忽略解析错误
        }

        // 调用原始处理器
        return originalOnMessage.call(this, event);
    };

    // 3. 拦截EventAdapter.adaptEvent
    if (window.EventAdapter) {
        const originalAdaptEvent = EventAdapter.adaptEvent;
        EventAdapter.adaptEvent = function(newEvent, session, options) {
            const eventType = newEvent.type;

            if (eventType && eventType.includes('preview')) {
                console.log(`🔄 [EventAdapter] 适配preview事件:`, {
                    inputType: eventType,
                    inputEvent: newEvent
                });

                const adapted = originalAdaptEvent.call(this, newEvent, session, options);

                console.log(`   → 适配结果:`, adapted ? {
                    type: adapted.type,
                    hasFilePath: !!adapted.file_path,
                    hasDelta: !!adapted.delta
                } : 'null');

                return adapted;
            }

            return originalAdaptEvent.call(this, newEvent, session, options);
        };
    }

    // 4. 检查TypingEffectManager
    const checkTypingEffectManager = () => {
        if (typeof TypingEffectManager !== 'undefined') {
            console.log('✅ TypingEffectManager可用');
            console.log('   方法:', Object.getOwnPropertyNames(TypingEffectManager));
        } else {
            console.warn('⚠️ TypingEffectManager不可用');
        }
    };

    // 5. 检查rightPanelManager
    const checkRightPanelManager = () => {
        if (window.rightPanelManager) {
            console.log('✅ rightPanelManager可用');
            console.log('   方法:', Object.getOwnPropertyNames(window.rightPanelManager));
        } else {
            console.warn('⚠️ rightPanelManager不可用');
        }
    };

    // 6. 汇总报告
    const showSummary = () => {
        setTimeout(() => {
            console.log('\n📊 [Preview Debug] 事件统计报告:');
            console.log('   收到的事件类型:', Array.from(previewEventTypes));
            console.log('   Preview事件数量:', previewEventCount);
            console.log('   SSE连接状态:', checkEventSource() ? '✅ 正常' : '❌ 异常');
            checkTypingEffectManager();
            checkRightPanelManager();
        }, 5000); // 5秒后显示报告
    };

    // 启动检查
    checkEventSource();
    showSummary();

    // 返回清理函数
    return {
        cleanup: () => {
            EventSource.prototype.onmessage = originalOnMessage;
            console.log('🧹 [Preview Debug] 已清理监听器');
        }
    };
})();
