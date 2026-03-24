// 在浏览器控制台运行此脚本来诊断重复事件
// 复制整个脚本到控制台执行

(function() {
    console.log('=' .repeat(80));
    console.log('前端重复事件诊断');
    console.log('=' .repeat(80));

    const sessions = window.state.sessions || [];
    console.log(`\n找到 ${sessions.length} 个session\n`);

    let total_duplicates = 0;
    let total_issues = 0;

    sessions.forEach((session, idx) => {
        const session_id = session.id || `unknown_${idx}`;
        const title = (session.prompt || 'No title').substring(0, 50);

        console.log(`\n${'='.repeat(80)}`);
        console.log(`Session ${idx + 1}/${sessions.length}: ${session_id}`);
        console.log(`Title: ${title}`);
        console.log(`${'='.repeat(80)}`);

        // 检查phases中的events
        const phases = session.phases || [];
        if (phases.length > 0) {
            phases.forEach((phase, pidx) => {
                const phase_id = phase.id || `phase_${pidx}`;
                const events = phase.events || [];

                if (events.length > 0) {
                    console.log(`\n  Phase ${pidx + 1}/${phases.length} (${phase_id}):`);
                    console.log(`    - 总事件数: ${events.length}`);

                    // 按类型统计
                    const by_type = {};
                    events.forEach(e => {
                        const type = e.type || 'unknown';
                        by_type[type] = (by_type[type] || 0) + 1;
                    });

                    Object.entries(by_type).forEach(([type, count]) => {
                        console.log(`    - ${type}: ${count} 个`);
                    });

                    // 检查thought事件重复
                    const thoughts = events.filter(e => e.type === 'thought');
                    if (thoughts.length > 0) {
                        const seen = new Map();
                        const duplicates = [];

                        thoughts.forEach((t, i) => {
                            const content = (t.content || '').substring(0, 100);
                            if (seen.has(content)) {
                                duplicates.push({
                                    index: i,
                                    content: content,
                                    first_at: seen.get(content)
                                });
                            } else {
                                seen.set(content, i);
                            }
                        });

                        if (duplicates.length > 0) {
                            total_issues++;
                            total_duplicates += duplicates.length;
                            console.log(`    ⚠️  发现 ${duplicates.length} 个重复的thought事件:`);
                            duplicates.slice(0, 3).forEach(d => {
                                console.log(`       - 位置${d.index} (首次在位置${d.first_at}): "${d.content}..."`);
                            });
                        }
                    }

                    // 检查action事件重复
                    const actions = events.filter(e => e.type === 'action');
                    if (actions.length > 0) {
                        const seen = new Map();
                        const duplicates = [];

                        actions.forEach((a, i) => {
                            const id = a.id || `action_${i}`;
                            if (seen.has(id)) {
                                duplicates.push({
                                    index: i,
                                    id: id,
                                    first_at: seen.get(id)
                                });
                            } else {
                                seen.set(id, i);
                            }
                        });

                        if (duplicates.length > 0) {
                            total_issues++;
                            total_duplicates += duplicates.length;
                            console.log(`    ⚠️  发现 ${duplicates.length} 个重复的action事件:`);
                            duplicates.slice(0, 3).forEach(d => {
                                console.log(`       - 位置${d.index} (ID: ${d.id}, 首次在位置${d.first_at})`);
                            });
                        }
                    }
                }
            });
        }

        // 检查orphanEvents
        const orphanEvents = session.orphanEvents || [];
        if (orphanEvents.length > 0) {
            console.log(`\n  orphanEvents: ${orphanEvents.length} 个事件`);

            const by_type = {};
            orphanEvents.forEach(e => {
                const type = e.type || 'unknown';
                by_type[type] = (by_type[type] || 0) + 1;
            });

            Object.entries(by_type).forEach(([type, count]) => {
                console.log(`    - ${type}: ${count}`);
            });
        }

        // 检查actions数组
        const actions = session.actions || [];
        if (actions.length > 0) {
            console.log(`\n  actions: ${actions.length} 个事件`);

            const by_type = {};
            actions.forEach(e => {
                const type = e.type || 'unknown';
                by_type[type] = (by_type[type] || 0) + 1;
            });

            Object.entries(by_type).forEach(([type, count]) => {
                console.log(`    - ${type}: ${count}`);
            });
        }

        // 检查thoughtEvents
        const thoughtEvents = session.thoughtEvents || [];
        if (thoughtEvents.length > 0) {
            console.log(`\n  thoughtEvents: ${thoughtEvents.length} 个事件`);
        }

        // 检查跨数组重复
        console.log(`\n  跨数组重复检查:`);

        // 检查actions和orphanEvents是否有重复
        if (actions.length > 0 && orphanEvents.length > 0) {
            const action_ids = new Set(actions.map(a => a.id));
            const orphan_ids = new Set(orphanEvents.map(e => e.id));

            const intersection = [...action_ids].filter(id => orphan_ids.has(id));
            if (intersection.length > 0) {
                total_issues++;
                console.log(`    ⚠️  actions和orphanEvents有 ${intersection.length} 个共同ID`);
                console.log(`       示例ID: ${intersection.slice(0, 3).join(', ')}`);
            }
        }
    });

    console.log(`\n${'='.repeat(80)}`);
    console.log(`诊断总结`);
    console.log(`${'='.repeat(80)}`);
    console.log(`  - 总session数: ${sessions.length}`);
    console.log(`  - 发现问题的session数: ${total_issues}`);
    console.log(`  - 重复事件总数: ${total_duplicates}`);

    if (total_duplicates > 0) {
        console.log(`\n⚠️  发现重复事件！`);
        console.log(`\n建议：`);
        console.log(`  1. 清空localStorage后重新加载: localStorage.clear(); location.reload();`);
        console.log(`  2. 检查SSE事件处理逻辑（opencode-new-api-patch.js）`);
        console.log(`  3. 检查深度加载逻辑（opencode.js loadState函数）`);
    } else {
        console.log(`\n✓ 未发现明显的重复事件`);
        console.log(`\n如果UI上仍然显示重复，可能是渲染逻辑问题。`);
    }

    console.log(`\n${'='.repeat(80)}`);

    // 导出详细数据供分析
    console.log(`\n💾 提示：可以运行以下命令导出数据:`);
    console.log(`   copy(JSON.stringify(window.state.sessions, null, 2))`);
    console.log(`   然后粘贴到文本文件中分析`);
})();
