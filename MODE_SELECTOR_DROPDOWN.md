# 模式选择器改为下拉菜单

## 修改内容

将输入框底部的模式选择器从按钮组改为下拉菜单形式，并移除所有图标。

## 修改详情

### 1. HTML结构修改 (`static/index.html`)

**修改前**（按钮组形式）：
```html
<div id="input-mode-selector"
    class="inline-flex bg-gray-100 dark:bg-gray-700 rounded-full p-0.5">
    <button class="mode-btn-input ..." data-mode="plan">
        <span class="material-symbols-outlined !text-[14px]">psychology</span>
        <span class="hidden sm:inline">Plan</span>
    </button>
    <button class="mode-btn-input ..." data-mode="build">
        <span class="material-symbols-outlined !text-[14px]">build</span>
        <span class="hidden sm:inline">Build</span>
    </button>
    <button class="mode-btn-input ..." data-mode="auto">
        <span class="material-symbols-outlined !text-[14px]">auto_awesome</span>
        <span class="hidden sm:inline">Auto</span>
    </button>
</div>
```

**修改后**（下拉菜单形式）：
```html
<select id="input-mode-selector"
    class="mode-selector-select px-3 py-1.5 rounded-full text-xs font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-sm">
    <option value="plan">Plan 分析</option>
    <option value="build" selected>Build 开发</option>
    <option value="auto">Auto 智能模式</option>
</select>
```

**关键变化**：
- ✅ 从`<button>`改为原生`<select>`元素
- ✅ 移除所有`material-symbols-outlined`图标
- ✅ 添加`selected`属性到Build选项（默认值）
- ✅ 保留圆角设计（`rounded-full`）以匹配整体UI风格
- ✅ 添加聚焦样式（`focus:ring-2`）

### 2. JavaScript逻辑修改 (`static/ui-layout-refactor.js`)

**修改前**（按钮点击事件）：
```javascript
function initInputModeSelector() {
    const selector = document.getElementById('input-mode-selector');
    const buttons = selector.querySelectorAll('.mode-btn-input');

    // 设置默认模式
    window._currentMode = 'build';
    updateButtonSelection('build');

    // 绑定点击事件
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const mode = btn.dataset.mode;
            window._currentMode = mode;
            updateButtonSelection(mode);
        });
    });

    function updateButtonSelection(mode) {
        // 样式切换逻辑...
    }
}
```

**修改后**（下拉菜单变化事件）：
```javascript
function initInputModeSelector() {
    const selector = document.getElementById('input-mode-selector');

    const DEFAULT_MODE = 'build';  // 默认Build模式

    // 设置默认模式
    selector.value = DEFAULT_MODE;
    window._currentMode = DEFAULT_MODE;

    // 绑定变化事件
    selector.addEventListener('change', (e) => {
        const mode = e.target.value;
        window._currentMode = mode;
        console.log('[UI] 模式切换到:', mode, '(', selector.options[selector.selectedIndex].text, ')');
    });

    console.log('[UI] 输入框模式选择器初始化完成，默认模式:', DEFAULT_MODE);
}
```

**关键变化**：
- ✅ 移除`updateButtonSelection`函数（不再需要）
- ✅ 将点击事件改为`change`事件
- ✅ 直接通过`selector.value`获取选中的模式
- ✅ 简化代码逻辑（从~40行减少到~20行）

## 用户体验改进

### 修改前
- **空间占用**：按钮组需要显示3个按钮，占用较宽空间
- **移动端**：小屏幕可能隐藏按钮文字（`hidden sm:inline`）
- **交互**：需要点击3个按钮中的一个

### 修改后
- **空间效率**：下拉菜单只占用一个选项的空间
- **移动端**：原生select在所有设备上都能良好工作
- **交互**：点击一次展开所有选项，点击选择
- **键盘导航**：原生支持上下键选择
- **无障碍性**：屏幕阅读器天然支持

## 样式设计

### Tailwind CSS类说明
```html
class="
    px-3 py-1.5              # 内边距，控制下拉框大小
    rounded-full             # 完全圆角，匹配整体UI风格
    text-xs                  # 小字体（12px）
    font-medium              # 中等字重
    bg-white                 # 白色背景（浅色模式）
    dark:bg-gray-700         # 深色背景（深色模式）
    border                   # 显示边框
    border-gray-200          # 浅色边框颜色
    dark:border-gray-600     # 深色模式边框颜色
    text-gray-700            # 浅色模式文字颜色
    dark:text-gray-200       # 深色模式文字颜色
    focus:outline-none       # 移除默认聚焦轮廓
    focus:ring-2             # 聚焦时添加2px光环
    focus:ring-blue-500      # 聚焦光环颜色（蓝色）
    cursor-pointer           # 鼠标悬停显示指针
    shadow-sm                # 小阴影效果
"
```

## 验证清单

- ✅ 下拉菜单显示在输入框左侧底部
- ✅ 默认选中"Build 开发"
- ✅ 三个选项：Plan 分析、Build 开发、Auto 智能模式
- ✅ 无图标显示
- ✅ 点击可展开选项列表
- ✅ 选择不同选项后更新全局模式变量
- ✅ 控制台输出切换日志
- ✅ 圆角设计匹配整体UI
- ✅ 深色模式支持

## 浏览器兼容性

原生`<select>`元素在所有现代浏览器中都得到完美支持：
- ✅ Chrome/Edge (最新版本)
- ✅ Firefox (最新版本)
- ✅ Safari (最新版本)
- ✅ 移动浏览器（iOS Safari, Chrome Mobile）

## 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `static/index.html` | 编辑 | 将按钮组改为select下拉菜单（第1028-1054行） |
| `static/ui-layout-refactor.js` | 编辑 | 简化事件处理逻辑（第14-33行） |

---

**状态**：✅ 修改已完成并验证通过
**修改时间**：2026-03-23
**测试结果**：所有检查通过 ✓
