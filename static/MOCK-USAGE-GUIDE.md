# Mock 数据展示使用指南

## 快速查看新功能

### 方法 1：直接打开 Mock 文件（推荐）

1. **在浏览器中打开以下文件：**
   ```
   file:///D:/Manus/opencode/static/index-mock.html
   ```

2. **或者双击文件：**
   - 找到 `D:\Manus\opencode\static\index-mock.html`
   - 双击打开即可

### 方法 2：通过本地服务器

1. **启动本地服务器：**
   ```bash
   cd D:\Manus\opencode\static
   python -m http.server 8080
   ```

2. **在浏览器中访问：**
   ```
   http://localhost:8080/index-mock.html
   ```

---

## 🎨 新功能展示

打开后，您将看到以下改进效果：

### 1️⃣ 标签系统（任务4）
- **bash** - 命令行操作
- **browser** - 浏览器预览
- **file_editor** - 文件编辑
- **web_search** - 网络搜索
- **read** - 读取文件
- **write** - 写入文件
- **grep** - 搜索内容

### 2️⃣ 缩略图预览（任务7）
- 在 `Phase 3` 和 `Phase 5` 中，您会看到 browser 类型事件带有缩略图
- 缩略图显示在事件卡片的右侧

### 3️⃣ 优化状态图标（任务5）
- ✅ **已完成**: 黑色圆形 + 白色勾选
- 🔄 **执行中**: Loading 动画
- ⚪ **未开始**: 灰色圆圈

### 4️⃣ 卡片样式优化（任务3）
- 明显的边框
- 柔和的阴影
- 悬停效果
- 更清晰的层次

### 5️⃣ 间距优化（任务6）
- Phase 间距：16px
- Event 间距：12px
- 更好的视觉呼吸感

---

## 📋 测试数据说明

### 当前展示的任务
- **任务名称**: "创建一个精美的网页时钟"
- **阶段数量**: 5 个阶段
- **事件总数**: 14 个事件
- **包含工具类型**: 7 种

### 各阶段内容
1. **Phase 1 - 需求分析与设计**
   - 思考（可展开）
   - file_editor 操作
   - bash 操作

2. **Phase 2 - 编写 HTML 结构**
   - write 操作
   - read 操作

3. **Phase 3 - 实现 CSS 样式和动画**
   - 思考
   - file_editor 操作
   - **browser 操作（带缩略图）**

4. **Phase 4 - 编写 JavaScript 逻辑**
   - file_editor 操作
   - grep 操作

5. **Phase 5 - 测试与优化**
   - bash 操作
   - **browser 操作（带缩略图）**
   - web_search 操作

---

## 🔧 控制台日志

打开浏览器控制台（F12），您会看到：

```
[Mock] 初始化 Mock 数据展示
[Mock] 加载任务: 创建一个精美的网页时钟，保存为 my_clock.html 并展示
[Mock] ✓ 渲染完成 - 展示新功能:
  - 标签系统: bash, browser, file_editor, web_search 等
  - 缩略图预览: browser 类型事件
  - 优化状态图标: 黑色圆形 + 白色勾选
  - 卡片样式: 边框 + 阴影
  - 间距优化: Phase 16px, Event 12px
```

---

## 🎯 交互说明

### 点击 Phase
- 点击 Phase 标题可展开/收起子任务列表
- 当前阶段默认展开

### 点击事件
- **思考类型**：如果内容较长，可点击展开/收起
- **其他类型**：无点击效果

### 悬停效果
- 事件卡片悬停时会显示阴影
- 按钮、标签等都有悬停反馈

---

## 📝 自定义数据

如需修改测试数据，编辑以下文件：

```
D:\Manus\opencode\static\mock-data.js
```

### 添加新事件示例
```javascript
{
    type: 'tool',
    tool: 'your_tool_name',  // 会显示对应标签
    content: '操作描述',
    thumbnail: 'data:image/svg+xml,...',  // 可选：缩略图
    timestamp: '2026-02-08T12:00:00.000Z'
}
```

---

## ⚙️ 技术细节

### 加载顺序
1. ✅ tool-icons.js
2. ✅ enhanced-task-panel.js
3. ✅ mock-data.js
4. ✅ enable-mock.js
5. ✅ 初始化脚本
6. ✅ opencode.js

### CSS 变量
- `--card-light`: #f7f7f8
- `--card-dark`: #2d2d2d
- `--border-light`: #E5E7EB
- `--border-dark`: #334155

---

## 🐛 问题排查

### 样式不显示
1. 清除浏览器缓存（Ctrl+Shift+Delete）
2. 硬刷新（Ctrl+F5）
3. 检查控制台是否有错误

### Mock 数据未加载
1. 打开控制台（F12）
2. 查看 `Network` 标签
3. 确认所有 JS 文件都已加载（状态 200）

### 缩略图不显示
- 确保浏览器支持 data URI（所有现代浏览器都支持）

---

**生成时间**: 2026-02-08
**版本**: v6.0
**改进任务**: 3, 4, 5, 6, 7
