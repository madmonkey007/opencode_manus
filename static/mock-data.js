// Mock 数据配置 - 用于样式调试
const MOCK_DATA = {
    // 当前激活的任务 ID
    activeId: 'demo-task-001',

    // 任务历史记录
    sessions: [
        {
            id: 'demo-task-001',
            prompt: '创建一个精美的网页时钟，保存为 my_clock.html 并展示',
            response: `我已经成功创建了一个精美的动态网页时钟！

## 功能特点

1. **动态时间显示** - 实时显示当前时间，包含时、分、秒
2. **日期显示** - 显示完整的日期信息
3. **优雅的动画** - 平滑的指针动画和数字变化
4. **响应式设计** - 适配不同屏幕尺寸
5. **深色模式支持** - 自动适应系统主题

## 技术实现

- 使用 HTML5 Canvas 绘制表盘
- CSS3 实现流畅的动画效果
- JavaScript 实时更新时间数据

文件已保存为 \`my_clock.html\`，你可以在文件标签页中查看和预览。`,

            // 阶段（子任务）
            phases: [
                {
                    id: 'phase-1',
                    number: 1,
                    title: '需求分析与设计',
                    status: 'done',
                    events: [
                        {
                            type: 'thought',
                            content: '用户需要一个精美的网页时钟，我应该考虑以下方面：视觉设计、动画效果、响应式布局、代码结构。',
                            timestamp: '2026-02-05T13:11:23.123Z'
                        },
                        {
                            type: 'tool',
                            tool: 'code_editor',
                            status: 'completed',
                            args: {
                                action: 'create_file',
                                filename: 'my_clock.html',
                                language: 'html'
                            },
                            timestamp: '2026-02-05T13:11:25.456Z'
                        }
                    ]
                },
                {
                    id: 'phase-2',
                    number: 2,
                    title: '编写 HTML 结构',
                    status: 'done',
                    events: [
                        {
                            type: 'tool',
                            tool: 'code_editor',
                            status: 'completed',
                            args: {
                                action: 'write',
                                content: '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>...',
                                lines: 45
                            },
                            timestamp: '2026-02-05T13:11:28.789Z'
                        }
                    ]
                },
                {
                    id: 'phase-3',
                    number: 3,
                    title: '实现 CSS 样式和动画',
                    status: 'done',
                    events: [
                        {
                            type: 'thought',
                            content: '使用渐变背景和阴影效果，让时钟看起来更加立体和精美。添加平滑的过渡动画。',
                            timestamp: '2026-02-05T13:11:30.234Z'
                        },
                        {
                            type: 'tool',
                            tool: 'code_editor',
                            status: 'completed',
                            args: {
                                action: 'append_css',
                                properties: ['animation', 'gradient', 'box-shadow']
                            },
                            timestamp: '2026-02-05T13:11:32.567Z'
                        }
                    ]
                },
                {
                    id: 'phase-4',
                    number: 4,
                    title: '编写 JavaScript 逻辑',
                    status: 'done',
                    events: [
                        {
                            type: 'tool',
                            tool: 'code_editor',
                            status: 'completed',
                            args: {
                                action: 'write_js',
                                functions: ['updateTime', 'initClock', 'animateHands']
                            },
                            timestamp: '2026-02-05T13:11:35.890Z'
                        }
                    ]
                },
                {
                    id: 'phase-5',
                    number: 5,
                    title: '测试与优化',
                    status: 'completed',
                    events: [
                        {
                            type: 'tool',
                            tool: 'browser_preview',
                            status: 'running',
                            args: {
                                url: 'http://localhost:8000/my_clock.html',
                                viewport: 'responsive'
                            },
                            timestamp: '2026-02-05T13:11:40.123Z'
                        }
                    ]
                }
            ],

            // 孤立事件（不属于任何阶段的事件）
            orphanEvents: [
                {
                    type: 'thought',
                    content: '开始分析用户需求...',
                    timestamp: '2026-02-05T13:11:22.000Z'
                }
            ],

            // 子任务动作列表
            actions: [
                {
                    tool: 'thought',
                    timestamp: '2026-02-05T13:11:23.123Z',
                    status: 'completed',
                    detail: '分析需求和设计方案'
                },
                {
                    tool: 'code_editor',
                    timestamp: '2026-02-05T13:11:25.456Z',
                    status: 'completed',
                    detail: '创建 HTML 文件'
                },
                {
                    tool: 'code_editor',
                    timestamp: '2026-02-05T13:11:28.789Z',
                    status: 'completed',
                    detail: '编写 HTML 结构'
                },
                {
                    tool: 'thought',
                    timestamp: '2026-02-05T13:11:30.234Z',
                    status: 'completed',
                    detail: '设计样式和动画'
                },
                {
                    tool: 'code_editor',
                    timestamp: '2026-02-05T13:11:32.567Z',
                    status: 'completed',
                    detail: '实现 CSS 样式'
                },
                {
                    tool: 'code_editor',
                    timestamp: '2026-02-05T13:11:35.890Z',
                    status: 'completed',
                    detail: '编写 JavaScript 逻辑'
                },
                {
                    tool: 'browser_preview',
                    timestamp: '2026-02-05T13:11:40.123Z',
                    status: 'running',
                    detail: '浏览器预览测试'
                }
            ],

            // 生成的文件列表
            deliverables: [
                {
                    name: 'my_clock.html',
                    path: '/opencode/sessions/demo-task-001/my_clock.html',
                    type: 'html',
                    size: 4582,
                    previewable: true
                },
                {
                    name: 'clock_styles.css',
                    path: '/opencode/sessions/demo-task-001/clock_styles.css',
                    type: 'css',
                    size: 1234,
                    previewable: false
                },
                {
                    name: 'clock_script.js',
                    path: '/opencode/sessions/demo-task-001/clock_script.js',
                    type: 'js',
                    size: 856,
                    previewable: false
                },
                {
                    name: 'README.md',
                    path: '/opencode/sessions/demo-task-001/README.md',
                    type: 'md',
                    size: 456,
                    previewable: false
                },
                {
                    name: 'screenshot.png',
                    path: '/opencode/sessions/demo-task-001/screenshot.png',
                    type: 'png',
                    size: 25600,
                    previewable: true
                },
                {
                    name: 'clock_icon.svg',
                    path: '/opencode/sessions/demo-task-001/clock_icon.svg',
                    type: 'svg',
                    size: 1024,
                    previewable: true
                }
            ],

            // 上传的文件
            uploadedFiles: [],

            currentPhase: 'phase-5'
        },
        {
            id: 'demo-task-002',
            prompt: '帮我做一个简单的网页版电子闹钟页面',
            response: '正在处理您的请求...',
            phases: [
                {
                    id: 'phase-2-1',
                    number: 1,
                    title: '理解需求',
                    status: 'active',
                    events: []
                }
            ],
            orphanEvents: [],
            actions: [],
            deliverables: [],
            uploadedFiles: []
        },
        {
            id: 'demo-task-003',
            prompt: '设计一个精美的动态网页时钟，像素风格，时钟数字要大，灰色背景',
            response: '',
            phases: [],
            orphanEvents: [],
            actions: [],
            deliverables: [],
            uploadedFiles: []
        },
        {
            id: 'demo-task-004',
            prompt: '帮我设计一个精英的动态网页时钟',
            response: '已完成！查看右侧预览面板。',
            phases: [
                {
                    id: 'phase-4-1',
                    number: 1,
                    title: '设计规划',
                    status: 'done',
                    events: []
                },
                {
                    id: 'phase-4-2',
                    number: 2,
                    title: '实现代码',
                    status: 'done',
                    events: []
                }
            ],
            orphanEvents: [],
            actions: [],
            deliverables: [
                {
                    name: 'elite_clock.html',
                    path: '/opencode/sessions/demo-task-004/elite_clock.html',
                    type: 'html',
                    size: 6789,
                    previewable: true
                }
            ],
            uploadedFiles: []
        }
    ],

    // 文件过滤器状态
    fileFilter: 'all',
    fileSearch: '',

    // 主题设置
    theme: 'dark'
};

// 导出 mock 数据
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MOCK_DATA;
}
