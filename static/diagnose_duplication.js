/**
 * OpenCode 重复内容诊断脚本
 * 用于分析session中的重复内容模式
 */

// 在浏览器控制台中运行此脚本
function diagnoseDuplication() {
    const state = window.state;
    if (!state || !state.sessions) {
        console.error('❌ 无法访问window.state');
        return;
    }

    const activeSession = state.sessions.find(s => s.id === state.activeId);
    if (!activeSession) {
        console.error('❌ 没有活动的session');
        return;
    }

    console.log('📊 诊断报告：', activeSession.id);
    console.log('═'.repeat(60));

    // 1. 检查去重集合状态
    console.log('\n1️⃣ 去重集合状态：');
    console.log('   - hasChunkFingerprints:', !!activeSession._appendedChunkFingerprints);
    console.log('   - fingerprintCount:', activeSession._appendedChunkFingerprints?.size || 0);
    console.log('   - hasSystemMessageSet:', !!activeSession._displayedSystemMessages);
    console.log('   - systemMessageCount:', activeSession._displayedSystemMessages?.size || 0);

    // 2. 分析响应内容
    const response = activeSession.response || '';
    const lines = response.split('\n');

    console.log('\n2️⃣ 响应内容分析：');
    console.log('   - 总长度:', response.length, '字符');
    console.log('   - 总行数:', lines.length, '行');

    // 3. 检测重复行
    const lineMap = new Map();
    lines.forEach((line, idx) => {
        if (line.trim().length > 5) { // 忽略短行
            const key = line.trim();
            if (!lineMap.has(key)) {
                lineMap.set(key, []);
            }
            lineMap.get(key).push(idx);
        }
    });

    const duplicates = Array.from(lineMap.entries())
        .filter(([_, indices]) => indices.length > 1)
        .sort((a, b) => b[1].length - a[1].length);

    console.log('\n3️⃣ 重复内容检测：');
    if (duplicates.length === 0) {
        console.log('   ✅ 未发现重复内容');
    } else {
        console.log('   ⚠️ 发现', duplicates.length, '处重复内容：\n');
        duplicates.slice(0, 10).forEach(([content, indices], i) => {
            console.log(`   [${i + 1}] 重复 ${indices.length} 次：`);
            console.log('       内容:', content.substring(0, 60) + (content.length > 60 ? '...' : ''));
            console.log('       位置: 行', indices.join(', '));
        });

        if (duplicates.length > 10) {
            console.log(`   ... 还有 ${duplicates.length - 10} 处重复未显示`);
        }
    }

    // 4. 显示最近收到的chunk指纹
    if (activeSession._appendedChunkFingerprints) {
        console.log('\n4️⃣ 最近的chunk指纹样本（最多10个）：');
        const fingerprints = Array.from(activeSession._appendedChunkFingerprints).slice(-10);
        fingerprints.forEach((fp, i) => {
            console.log(`   [${i + 1}] ${fp.substring(0, 40)}...`);
        });
    }

    // 5. 检查事件历史
    console.log('\n5️⃣ 事件历史统计：');
    console.log('   - orphanEvents数量:', activeSession.orphanEvents?.length || 0);
    console.log('   - actions数量:', activeSession.actions?.length || 0);
    console.log('   - phases数量:', activeSession.phases?.length || 0);

    // 6. 检查调试信息
    if (window._debugFilteredTimeline) {
        console.log('\n6️⃣ 过滤的timeline事件：');
        console.log('   - 总数:', window._debugFilteredTimeline.length);
        if (window._debugFilteredTimeline.length > 0) {
            console.log('   - 最近事件:');
            window._debugFilteredTimeline.slice(-3).forEach((evt, i) => {
                console.log(`     [${i + 1}]`, evt.preview);
            });
        }
    }

    console.log('\n' + '═'.repeat(60));
    console.log('✅ 诊断完成\n');

    // 返回诊断结果对象
    return {
        sessionId: activeSession.id,
        responseLength: response.length,
        fingerprintCount: activeSession._appendedChunkFingerprints?.size || 0,
        duplicateCount: duplicates.length,
        topDuplicates: duplicates.slice(0, 5).map(([content, indices]) => ({
            content: content.substring(0, 100),
            count: indices.length,
            positions: indices
        }))
    };
}

// 自动运行诊断（如果在浏览器中）
if (typeof window !== 'undefined') {
    window.diagnoseDuplication = diagnoseDuplication;
    console.log('✅ 诊断脚本已加载');
    console.log('   使用方法：在控制台输入 diagnoseDuplication()');
}

// Node.js导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { diagnoseDuplication };
}
