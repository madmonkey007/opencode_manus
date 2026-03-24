# OpenCode 配置管理指南

## 📋 概述

OpenCode 现在支持可配置的功能开关，允许用户根据部署环境和需求自定义行为。

## ⚙️ 可用配置项

### 1. 深度加载开关 (`enableDeepLoad`)

**默认值**: `false`

**说明**：控制是否从后端API恢复历史数据。

- **`false` (推荐)**: 仅使用localStorage
  - 适用场景：后端使用内存存储（Docker重启数据丢失）
  - 优点：保护localStorage数据不被空数据覆盖
  - 缺点：无法从后端恢复数据

- **`true`**: 同时使用localStorage和后端API
  - 适用场景：后端支持持久化存储（数据库/Redis）
  - 优点：可以从后端恢复完整历史数据
  - 缺点：需要后端配置持久化存储

**何时启用**：
- ✅ 后端已配置SQLite/PostgreSQL等数据库
- ✅ 后端已配置Redis等缓存
- ✅ 确认后端数据不会因重启丢失
- ❌ 后端使用内存存储（如当前默认配置）

### 2. 详细日志开关 (`verboseLogging`)

**默认值**: `false`

**说明**：在控制台输出详细的配置变更和调试信息。

- **`false`**: 正常日志级别
- **`true`**: 详细日志（显示所有配置变更、数据加载等）

## 🔧 使用方法

### 方法1：配置面板（推荐）

**快捷方式**：
1. 在浏览器控制台（F12）运行：
   ```javascript
   window.openConfig()
   ```
2. 或者在页面中添加配置按钮：
   ```html
   <button onclick="window.openConfig()">⚙️ 配置</button>
   ```

**面板操作**：
- 勾选复选框启用/禁用功能
- 点击"保存配置"持久化到localStorage
- 点击"重置默认"恢复默认值

### 方法2：编程方式

**读取配置**：
```javascript
const config = window.ConfigManager.getAll();
console.log(config.enableDeepLoad);  // false
```

**修改单个配置**：
```javascript
window.ConfigManager.set('enableDeepLoad', true);
// 自动保存到localStorage
```

**批量修改配置**：
```javascript
window.ConfigManager.setMultiple({
    enableDeepLoad: true,
    verboseLogging: true
});
```

**重置为默认**：
```javascript
window.ConfigManager.resetToDefaults();
```

### 方法3：直接修改localStorage

```javascript
// 读取配置
const saved = localStorage.getItem('opencode_config');
const config = JSON.parse(saved).config;

// 修改配置
config.enableDeepLoad = true;

// 保存回localStorage
localStorage.setItem('opencode_config', JSON.stringify({config}));

// 刷新页面生效
location.reload();
```

## 📊 配置持久化

配置保存在浏览器的 `localStorage` 中，键名为 `opencode_config`。

**配置格式**：
```json
{
    "config": {
        "enableDeepLoad": false,
        "deepLoadReason": "Docker重启导致后端内存数据丢失，禁用深度加载以保护localStorage数据",
        "verboseLogging": false
    }
}
```

**注意**：
- 每个浏览器/配置文件独立
- 清除浏览器缓存会丢失配置
- 隐身模式/无痕模式配置不会持久化

## 🚀 部署场景配置建议

### 场景1：开发环境（默认配置）

```javascript
{
    "enableDeepLoad": false,
    "verboseLogging": false
}
```

**特点**：
- Docker容器频繁重启
- 后端使用内存存储
- 不需要详细日志

### 场景2：生产环境（后端有持久化）

**前提条件**：
- 后端已配置PostgreSQL/MySQL数据库
- 或已配置Redis缓存
- 数据不会因重启丢失

**配置**：
```javascript
{
    "enableDeepLoad": true,
    "verboseLogging": false
}
```

**启用步骤**：
1. 在浏览器控制台运行：`window.openConfig()`
2. 勾选"启用深度加载"
3. 点击"保存配置"
4. 刷新页面

### 场景3：调试/开发（详细日志）

```javascript
{
    "enableDeepLoad": false,
    "verboseLogging": true
}
```

**启用详细日志**：
1. 打开配置面板：`window.openConfig()`
2. 勾选"启用详细日志"
3. 点击"保存配置"

## ⚠️ 注意事项

### 1. 深度加载启用前的检查清单

在启用 `enableDeepLoad = true` 之前，请确认：

- [ ] 后端已配置持久化存储（数据库/Redis）
- [ ] 后端数据不会因Docker重启丢失
- [ ] 后端API `/opencode/session/{id}/messages` 可用
- [ ] 测试过启用后不会导致数据丢失

### 2. 禁用深度加载的影响

当 `enableDeepLoad = false` 时（默认）：
- ✅ 防止后端空数据覆盖localStorage
- ✅ 提升加载速度（无需等待API响应）
- ❌ 新设备/浏览器无法同步历史数据
- ❌ 无法从后端恢复误删的localStorage数据

### 3. 配置变更时机

配置变更后：
- **立即生效**：当前页面内的后续操作
- **持久化**：保存到localStorage
- **刷新页面**：完全加载新配置

## 🐛 故障排查

### 问题1：配置修改后未生效

**症状**：修改配置后，行为没有变化

**解决方案**：
1. 检查浏览器控制台是否有错误
2. 刷新页面（`Ctrl + R`）
3. 清除缓存后重试（`Ctrl + Shift + R`）

### 问题2：配置丢失

**症状**：刷新页面后配置回到默认值

**可能原因**：
- 使用了隐身模式/无痕模式
- 清除了浏览器缓存
- 使用了不同的浏览器/配置文件

**解决方案**：
- 重新配置并保存
- 正常模式使用（非隐身）

### 问题3：启用深度加载后数据为空

**症状**：启用深度加载后，历史记录消失

**原因**：后端使用内存存储，重启后数据丢失

**解决方案**：
1. 立即禁用深度加载：`window.ConfigManager.set('enableDeepLoad', false)`
2. 如果数据已丢失，从 `DATA_EMERGENCY_RESTORE.html` 恢复

## 📝 配置示例

### 示例1：检查当前配置

```javascript
const config = window.ConfigManager.getAll();
console.table({
    '深度加载': config.enableDeepLoad ? '✅ 启用' : '❌ 禁用',
    '详细日志': config.verboseLogging ? '✅ 启用' : '❌ �禁用',
    '禁用原因': config.deepLoadReason
});
```

### 示例2：监听配置变更

```javascript
window.addEventListener('opencode-config-change', (event) => {
    const { key, oldValue, newValue } = event.detail;
    console.log(`配置已变更: ${key}`);
    console.log(`  旧值: ${oldValue}`);
    console.log(`  新值: ${newValue}`);
});
```

### 示例3：条件性执行代码

```javascript
if (window.ConfigManager.get('enableDeepLoad')) {
    // 执行深度加载
    console.log('正在从后端恢复数据...');
} else {
    // 仅使用localStorage
    console.log('跳过深度加载，使用localStorage数据');
}
```

## 🔗 相关文档

- [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) - 安全配置指南
- [API_SELECTOR_FIX.md](./API_SELECTOR_FIX.md) - API切换器修复
- [PHASE_DUPLICATE_FIX.md](./PHASE_DUPLICATE_FIX.md) - Phase重复修复

---

**版本**: 1.0.0
**更新时间**: 2026-03-23
**维护者**: OpenCode Team
