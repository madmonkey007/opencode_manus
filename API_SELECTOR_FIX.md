# API端点选择器单选功能修复

## 问题描述
用户反馈：选择了Web按钮后，还可以点击CLI按钮，没有单选互斥效果

## 根本原因
1. **HTML硬编码样式**：Web按钮和CLI按钮在HTML中预设了固定的样式类
2. **CSS类不匹配**：JavaScript使用`active`类，但实际需要的是具体的Tailwind样式类

## 修复方案

### 1. 修改HTML (`static/index.html`)

**修复前**：
```html
<button id="api-web-btn"
    class="api-endpoint-btn px-3 py-1.5 rounded-full text-xs font-medium transition-all bg-white dark:bg-gray-700 shadow"
    data-endpoint="web">
```

**修复后**：
```html
<button id="api-web-btn"
    class="api-endpoint-btn px-3 py-1.5 rounded-full text-xs font-medium transition-all"
    data-endpoint="web">
```

**变更**：移除了硬编码的 `bg-white dark:bg-gray-700 shadow` 类

### 2. 修改JavaScript (`static/ui-layout-refactor.js`)

**修复后的updateEndpointButtons函数**：
```javascript
function updateEndpointButtons(endpoint) {
    // 先移除两个按钮的所有状态类
    webBtn.classList.remove('bg-white', 'dark:bg-gray-700', 'shadow', 'text-gray-900', 'dark:text-white');
    cliBtn.classList.remove('bg-white', 'dark:bg-gray-700', 'shadow', 'text-gray-900', 'dark:text-white');

    // 添加基础未选中状态
    webBtn.classList.add('text-gray-600', 'dark:text-gray-400');
    cliBtn.classList.add('text-gray-600', 'dark:text-gray-400');

    // 为选中按钮添加选中样式
    if (endpoint === 'web') {
        webBtn.classList.remove('text-gray-600', 'dark:text-gray-400');
        webBtn.classList.add('bg-white', 'dark:bg-gray-700', 'shadow', 'text-gray-900', 'dark:text-white');
    } else {
        cliBtn.classList.remove('text-gray-600', 'dark:text-gray-400');
        cliBtn.classList.add('bg-white', 'dark:bg-gray-700', 'shadow', 'text-gray-900', 'dark:text-white');
    }
}
```

**关键改进**：
1. ✅ 先清除所有状态类（确保干净的状态）
2. ✅ 统一添加未选中样式（灰色文本）
3. ✅ 为选中按钮添加选中样式（白色背景+阴影）
4. ✅ 使用实际Tailwind CSS类，而不是抽象的`active`类

## 单选逻辑原理

```
初始化：
  updateEndpointButtons('web')
  → Web按钮：白色背景+阴影（选中）
  → CLI按钮：灰色文本（未选中）

点击CLI按钮：
  1. 清除两个按钮所有样式类
  2. 两个按钮都设为灰色文本
  3. CLI按钮添加白色背景+阴影
  → Web：灰色（未选中）
  → CLI：白色背景（选中）✓

点击Web按钮：
  1. 清除两个按钮所有样式类
  2. 两个按钮都设为灰色文本
  3. Web按钮添加白色背景+阴影
  → Web：白色背景（选中）✓
  → CLI：灰色（未选中）
```

## 验证步骤

### 1. 清除浏览器缓存
```
Ctrl + Shift + R (硬刷新)
或
Ctrl + F5 (强制刷新)
```

### 2. 访问应用
```
http://127.0.0.1:8089
```

### 3. 观察默认状态
- ✅ Web按钮：白色背景，有阴影（选中状态）
- ✅ CLI按钮：灰色文本（未选中状态）

### 4. 点击CLI按钮
- ✅ CLI按钮变为白色背景+阴影
- ✅ Web按钮变为灰色文本
- ✅ 控制台输出：`[UI] 切换到 CLI API (4096)`

### 5. 点击Web按钮
- ✅ Web按钮恢复白色背景+阴影
- ✅ CLI按钮恢复灰色文本
- ✅ 控制台输出：`[UI] 切换到 Web API (8089)`

### 6. 打开浏览器开发者工具（F12）
- 切换到Console标签
- 应该看到初始化日志：
  ```
  [UI] 初始化新的UI布局...
  [UI] 输入框模式选择器初始化完成，默认模式: build
  [UI] API端点切换器初始化完成，默认端点: FastAPI Web应用
  [UI] 新的UI布局初始化完成
  ```

## 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `static/index.html` | 编辑 | 移除硬编码样式类（第977、985行） |
| `static/ui-layout-refactor.js` | 编辑 | 改进updateEndpointButtons函数（第89-106行） |

## 技术要点

1. **避免HTML硬编码状态**：让JavaScript完全控制UI状态
2. **互斥性原则**：先清除所有状态，再设置目标状态
3. **CSS类命名**：使用实际的Tailwind类，而不是自定义抽象类
4. **初始化一致性**：确保DOM加载完成后正确初始化

## 故障排查

如果单选功能仍不正常：

1. **清除浏览器缓存**：硬刷新（Ctrl+Shift+R）
2. **检查JavaScript加载**：F12 → Network → 刷新页面，检查ui-layout-refactor.js是否加载成功
3. **检查控制台错误**：F12 → Console，查看是否有JavaScript错误
4. **验证Docker容器**：
   ```bash
   docker ps  # 确认容器正在运行
   docker restart opencode-container  # 重启容器
   ```

---

**状态**：✅ 修复已完成，等待用户验证
**修改时间**：2026-03-23
