/**
 * 历史刷新修复验证脚本
 *
 * 使用方法：
 * 1. 打开OpenCode应用
 * 2. 按F12打开开发者工具
 * 3. 切换到Console标签
 * 4. 复制并粘贴此脚本，按回车执行
 */

console.log('=== 历史刷新修复验证 ===\n');

// 验证1：检查localStorage是否保存actions
console.log('【验证1】localStorage数据完整性检查');
try {
    const saved = JSON.parse(localStorage.getItem('opencode_state') || '{}');
    if (saved.sessions && saved.sessions.length > 0) {
        const firstSession = saved.sessions[0];
        console.log('✅ 找到', saved.sessions.length, '个session');

        const hasActions = firstSession.actions && firstSession.actions.length >= 0;
        const hasOrphanEvents = firstSession.orphanEvents && firstSession.orphanEvents.length >= 0;

        console.log('  - actions字段:', hasActions ? '✅ 存在' : '❌ 缺失');
        console.log('  - orphanEvents字段:', hasOrphanEvents ? '✅ 存在' : '❌ 缺失');

        if (hasActions) {
            console.log('  - actions数量:', firstSession.actions.length);
        }
        if (hasOrphanEvents) {
            console.log('  - orphanEvents数量:', firstSession.orphanEvents.length);
        }
    } else {
        console.warn('⚠️ localStorage中没有session数据，请先创建一个任务');
    }
} catch (e) {
    console.error('❌ 验证1失败:', e.message);
}

console.log('\n');

// 验证2：检查opencode.js中的修复是否加载
console.log('【验证2】opencode.js代码检查');
try {
    // 检查saveState函数是否保存actions
    const saveStateCode = window.saveState.toString();
    const savesActions = saveStateCode.includes('actions: s.actions');
    const savesOrphanEvents = saveStateCode.includes('orphanEvents: s.orphanEvents');

    console.log('  - saveState保存actions:', savesActions ? '✅ 是' : '❌ 否');
    console.log('  - saveState保存orphanEvents:', savesOrphanEvents ? '✅ 是' : '❌ 否');

    // 检查点击历史记录的条件判断
    // 由于这是在onclick函数内部，无法直接检查，我们通过检查其他特征来推断
    const hasIsLoadingCheck = saveStateCode.includes('_isLoading');
    console.log('  - 有_isLoading防重复加载:', hasIsLoadingCheck ? '✅ 是' : '❌ 否');
} catch (e) {
    console.error('❌ 验证2失败:', e.message);
}

console.log('\n');

// 验证3：检查当前session状态
console.log('【验证3】当前session状态检查');
try {
    if (typeof window.state !== 'undefined') {
        const currentSession = window.state.sessions.find(s => s.id === window.state.activeId);
        if (currentSession) {
            console.log('✅ 当前session ID:', currentSession.id);
            console.log('  - actions数量:', currentSession.actions?.length || 0);
            console.log('  - orphanEvents数量:', currentSession.orphanEvents?.length || 0);
            console.log('  - phases数量:', currentSession.phases?.length || 0);

            // 检查是否有_isLoading标志
            const hasLoadingFlag = currentSession._isLoading !== undefined;
            console.log('  - 有_isLoading标志:', hasLoadingFlag ? '✅ 是' : '❌ 否');
        } else {
            console.warn('⚠️ 没有活动的session');
        }
    } else {
        console.error('❌ window.state未定义');
    }
} catch (e) {
    console.error('❌ 验证3失败:', e.message);
}

console.log('\n');

// 验证4：检查UI修复（v=28）
console.log('【验证4】UI修复版本检查');
try {
    // 检查脚本版本
    const scripts = document.querySelectorAll('script[src]');
    let patchVersion = null;
    scripts.forEach(script => {
        const match = script.src.match(/opencode-new-api-patch\.js\?v=(\d+)/);
        if (match) {
            patchVersion = match[1];
        }
    });

    if (patchVersion) {
        console.log('✅ 当前UI版本: v=' + patchVersion);

        // 检查TypingEffectManager是否存在
        if (typeof window.TypingEffectManager !== 'undefined') {
            console.log('  - TypingEffectManager: ✅ 已加载');
            console.log('  - 当前打字机效果状态:', window.TypingEffectManager.isActive() ? '活跃' : '空闲');
        } else {
            console.log('  - TypingEffectManager: ❌ 未找到');
        }
    } else {
        console.warn('⚠️ 无法确定UI版本');
    }
} catch (e) {
    console.error('❌ 验证4失败:', e.message);
}

console.log('\n');

// 验证5：API客户端检查
console.log('【验证5】API客户端功能检查');
try {
    if (typeof window.apiClient !== 'undefined') {
        console.log('✅ apiClient已加载');

        // 检查关键方法是否存在
        const methods = ['getMessages', 'createSession'];
        methods.forEach(method => {
            const exists = typeof window.apiClient[method] === 'function';
            console.log('  - apiClient.' + method + ':', exists ? '✅ 存在' : '❌ 缺失');
        });
    } else {
        console.error('❌ apiClient未加载');
    }
} catch (e) {
    console.error('❌ 验证5失败:', e.message);
}

console.log('\n=== 验证完成 ===');
console.log('\n提示：');
console.log('1. 如果验证1和验证2都通过，说明历史刷新修复已生效');
console.log('2. 如果验证4显示v=28，说明UI抖动修复已生效');
console.log('3. 如需手动测试历史刷新，请按以下步骤：');
console.log('   a) 创建一个新任务（包含文件操作）');
console.log('   b) 等待任务完成');
console.log('   c) 按F5刷新页面');
console.log('   d) 点击刚才的历史任务');
console.log('   e) 检查是否能看到工具调用记录和文件预览');
