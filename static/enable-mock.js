// Mock 数据启用脚本
// 在 index.html 中，将此脚本放在 opencode.js 之前加载

// 保存原始的 fetch
const originalFetch = window.fetch;

// Mock 文件列表数据
const mockFileList = {
    'demo-task-001': [
        { name: 'my_clock.html', path: '/opencode/sessions/demo-task-001/my_clock.html', type: 'html' },
        { name: 'clock_styles.css', path: '/opencode/sessions/demo-task-001/clock_styles.css', type: 'css' },
        { name: 'clock_script.js', path: '/opencode/sessions/demo-task-001/clock_script.js', type: 'js' },
        { name: 'README.md', path: '/opencode/sessions/demo-task-001/README.md', type: 'md' },
        { name: 'screenshot.png', path: '/opencode/sessions/demo-task-001/screenshot.png', type: 'png' },
        { name: 'clock_icon.svg', path: '/opencode/sessions/demo-task-001/clock_icon.svg', type: 'svg' }
    ],
    'demo-task-004': [
        { name: 'elite_clock.html', path: '/opencode/sessions/demo-task-004/elite_clock.html', type: 'html' }
    ]
};

// 拦截 fetch 请求
window.fetch = async function(url, options) {
    console.log('[Mock] Intercepting fetch:', url);

    // 拦截文件列表请求
    if (url.includes('/opencode/list_session_files')) {
        const sid = new URL(url, window.location.origin).searchParams.get('sid');
        const files = mockFileList[sid] || [];

        return new Promise(resolve => {
            setTimeout(() => {
                resolve({
                    ok: true,
                    json: async () => ({ files })
                });
            }, 300);
        });
    }

    // 拦截文件内容请求
    if (url.includes('/opencode/get_file_content')) {
        return new Promise(resolve => {
            setTimeout(() => {
                resolve({
                    ok: true,
                    json: async () => ({
                        type: 'text',
                        filename: 'mock-file.html',
                        content: '<!DOCTYPE html>\n<html>\n<head>\n    <title>Mock File</title>\n</head>\n<body>\n    <h1>这是 Mock 文件内容</h1>\n    <p>用于样式调试</p>\n</body>\n</html>'
                    })
                });
            }, 300);
        });
    }

    // 其他请求使用原始 fetch
    return originalFetch(url, options);
};

console.log('[Mock] Mock data enabled');
