// 在浏览器控制台运行此脚本诊断"Server API failed"错误

(function() {
    console.log('=== Server API Failed 诊断 ===\n');

    // 1. 检查window.state
    console.log('1. 检查window.state:');
    console.log('   - sessions:', window.state?.sessions?.length || 0);
    console.log('   - activeId:', window.state?.activeId);

    // 2. 检查apiClient
    console.log('\n2. 检查apiClient:');
    console.log('   - 存在:', typeof window.apiClient !== 'undefined');
    if (window.apiClient) {
        console.log('   - baseURL:', window.apiClient.baseURL);
    }

    // 3. 测试API端点
    console.log('\n3. 测试API端点:');
    const testEndpoints = [
        'GET /opencode/sessions',
        'POST /opencode/session',
        'GET /'
    ];

    Promise.all([
        fetch('/opencode/sessions').then(r => ({status: r.status, ok: r.ok})),
        fetch('/opencode/session', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{"prompt":"测试"}'}).then(r => ({status: r.status, ok: r.ok})),
        fetch('/').then(r => ({status: r.status, ok: r.ok}))
    ]).then(results => {
        console.log('   GET /opencode/sessions:', results[0]);
        console.log('   POST /opencode/session:', results[1]);
        console.log('   GET /:', results[2]);
    }).catch(e => {
        console.error('   ❌ API测试失败:', e);
    });

    // 4. 检查最近的控制台错误
    console.log('\n4. 请检查上方是否有红色错误信息');
    console.log('   常见错误:');
    console.log('   - TypeError: ...');
    console.log('   - ReferenceError: ...');
    console.log('   - 404/500等HTTP错误');

    // 5. 检查Network标签
    console.log('\n5. 请查看开发者工具的Network标签:');
    console.log('   - 打开F12 → Network');
    console.log('   - 执行任务');
    console.log('   - 查看失败的请求（红色）');
    console.log('   - 点击查看详细错误');

    // 6. 手动测试提交
    console.log('\n6. 手动测试任务提交:');
    console.log('   在输入框输入问题并提交');
    console.log('   然后查看控制台输出');

    console.log('\n=== 诊断完成 ===');
    console.log('请将以上信息和Network标签中的错误截图发给我');
})();
