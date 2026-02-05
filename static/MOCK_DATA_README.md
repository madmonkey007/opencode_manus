# Mock 数据使用说明

## 概述
已在前端添加完整的 mock 数据系统,方便样式调试。

## 修改的文件

1. **static/index.html**
   - 添加了 mock-data.js 和 enable-mock.js 脚本引用

2. **static/opencode.js**
   - 修改了 `init()` 函数,自动加载 mock 数据
   - 修改了 `renderFiles()` 函数,优先使用本地 deliverables 数据

3. **static/mock-data.js** (新文件)
   - 包含完整的 mock 数据

4. **static/enable-mock.js** (新文件)
   - 拦截 fetch 请求,返回 mock 文件列表

## Mock 数据内容

### 1. 任务历史记录 (4 个任务)
- `demo-task-001`: 创建网页时钟 (完整数据,包含所有字段)
- `demo-task-002`: 电子闹钟 (进行中)
- `demo-task-003`: 像素风格时钟 (未开始)
- `demo-task-004`: 精英动态时钟 (已完成)

### 2. 子任务执行阶段 (demo-task-001)
1. 需求分析与设计 (完成)
2. 编写 HTML 结构 (完成)
3. 实现 CSS 样式和动画 (完成)
4. 编写 JavaScript 逻辑 (完成)
5. 测试与优化 (进行中)

### 3. 子任务动作列表
包含 7 个动作:
- thought: 分析需求
- code_editor: 创建文件、编写代码
- browser_preview: 浏览器预览

### 4. 最终回复
完整的 Markdown 格式回复

### 5. 生成的文件 (demo-task-001)
- my_clock.html (可预览)
- clock_styles.css
- clock_script.js
- README.md
- screenshot.png (可预览)
- clock_icon.svg (可预览)

## 如何使用

### 方式一:启用 Mock 数据 (默认)
直接刷新页面,会自动加载 mock 数据。

### 方式二:禁用 Mock 数据
在 `index.html` 中注释掉以下两行:
```html
<!-- <script src="/static/mock-data.js"></script> -->
<!-- <script src="/static/enable-mock.js"></script> -->
```

### 方式三:切换任务
点击左侧任务列表切换不同的任务,查看不同状态:
- 完整任务的各个阶段
- 进行中的任务
- 空任务

## 调试功能

### 浏览器控制台
打开浏览器控制台,可以看到:
```
[Mock] Loading mock data...
[Mock] Mock data loaded: 4 sessions
[Mock] Intercepting fetch: /opencode/list_session_files?sid=...
[Mock] Mock data enabled
```

### 文件预览
- HTML 文件:点击可在 Preview 标签页预览
- 图片文件:点击可预览
- 其他文件:点击查看文本内容

## 备份文件

- `static/opencode.js.backup`
- `static/index.html.backup`

如需恢复原始版本,使用备份文件。

## 自定义 Mock 数据

编辑 `static/mock-data.js` 文件中的 `MOCK_DATA` 对象:

```javascript
const MOCK_DATA = {
    activeId: 'your-task-id',
    sessions: [
        {
            id: 'your-task-id',
            prompt: '你的任务描述',
            response: '回复内容',
            phases: [...],  // 子任务阶段
            actions: [...], // 动作列表
            deliverables: [...] // 生成的文件
        }
    ]
};
```

## 样式调试建议

1. **测试不同状态**
   - 完整任务: demo-task-001
   - 进行中任务: demo-task-002
   - 空任务: 点击"新建任务"

2. **测试文件过滤**
   - All / Docs / Images / Code 标签
   - 搜索框功能

3. **测试响应式布局**
   - 调整浏览器窗口大小
   - 测试不同屏幕尺寸

4. **测试深色/浅色模式**
   - 点击右上角主题切换按钮
