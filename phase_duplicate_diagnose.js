// 在浏览器控制台运行，诊断phase重复问题

(function() {
    const s = window.state.sessions.find(x => x.id === window.state.activeId);
    if (!s) {
        console.log('未找到active session');
        return;
    }

    console.log('='.repeat(80));
    console.log('Phase重复诊断');
    console.log('='.repeat(80));
    console.log('\nSession ID:', s.id);
    console.log('Phases总数:', s.phases?.length || 0);

    if (s.phases && s.phases.length > 0) {
        console.log('\n详细信息:');
        s.phases.forEach((p, i) => {
            console.log(`\nPhase ${i + 1}:`);
            console.log('  ID:', p.id);
            console.log('  标题:', p.title || 'No title');
            console.log('  描述:', p.description || 'No description');
            console.log('  状态:', p.status || 'unknown');
            console.log('  Number:', p.number || 'N/A');
            console.log('  Turn Index:', p.turn_index || 'N/A');
            console.log('  Events数量:', p.events?.length || 0);
            console.log('  _uniqueId:', p._uniqueId || 'N/A');

            // 显示前3个event
            if (p.events && p.events.length > 0) {
                console.log('  前几个events:');
                p.events.slice(0, 3).forEach((e, j) => {
                    const preview = (e.content || e.id || e.type || '').toString().substring(0, 60);
                    console.log(`    ${j + 1}. [${e.type}] ${preview}...`);
                });
            }
        });

        // 检查是否有重复的phase
        console.log('\n' + '='.repeat(80));
        console.log('重复检测:');

        const phaseIds = s.phases.map(p => p.id);
        const uniqueIds = new Set(phaseIds);
        if (phaseIds.length !== uniqueIds.size) {
            console.log('⚠️  发现重复的phase ID!');
            const duplicates = phaseIds.filter((id, index) => phaseIds.indexOf(id) !== index);
            console.log('重复的IDs:', [...new Set(duplicates)]);
        } else {
            console.log('✓ 无重复ID');
        }

        // 检查是否有相似标题的phase
        console.log('\n相似标题检测:');
        for (let i = 0; i < s.phases.length; i++) {
            for (let j = i + 1; j < s.phases.length; j++) {
                const title1 = (s.phases[i].title || '').toLowerCase();
                const title2 = (s.phases[j].title || '').toLowerCase();

                if (title1 && title2 && (title1.includes(title2.substring(0, 10)) || title2.includes(title1.substring(0, 10)))) {
                    console.log(`⚠️  相似Phase: ${i + 1} "${s.phases[i].title}" 和 ${j + 1} "${s.phases[j].title}"`);
                    console.log(`   ID1: ${s.phases[i].id}, ID2: ${s.phases[j].id}`);
                    console.log(`   Number1: ${s.phases[i].number}, Number2: ${s.phases[j].number}`);
                }
            }
        }
    }

    console.log('\n' + '='.repeat(80));
    console.log('建议修复方案:');
    console.log('如果发现重复，可以运行以下命令手动合并:');
    console.log('// 保留第一个phase，删除其他重复的phase');
    console.log('const s = window.state.sessions.find(x => x.id === window.state.activeId);');
    console.log('if (s.phases.length > 1) {');
    console.log('  // 保留第一个，删除其他的');
    console.log('  s.phases = [s.phases[0]];');
    console.log('  saveState();');
    console.log('  renderAll();');
    console.log('}');
    console.log('='.repeat(80));
})();
