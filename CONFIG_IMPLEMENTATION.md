# 配置功能实现总结

## ✅ 已完成的改动

### 1. 添加配置对象 (`opencode.js`)

**位置**: `window.state.config`

```javascript
window.state = {
    // ... 其他字段
    config: {
        enableDeepLoad: false,      // 深度加载开关
        deepLoadReason: '...',      // 禁用原因说明
        verboseLogging: false       // 详细日志开关
    }
};
```

### 2. 修改硬编码为可配置

**修改前**：
```javascript
if (false && s.id.startsWith('ses_') && ...)
```

**修改后**：
```javascript
if (window.state.config.enableDeepLoad && s.id.startsWith('ses_') && ...)
```

### 3. 创建配置管理器 (`config-manager.js`)

**功能**：
- ✅ 读取/修改配置
- ✅ 持久化到localStorage
- ✅ 可视化配置面板
- ✅ 重置默认值
- ✅ 配置变更事件通知

### 4. 集成到页面 (`index.html`)

```html
<script src="/static/config-manager.js?v=1.0"></script>
```

## 🎯 使用方法

### 快速测试

1. **硬刷新浏览器**：`Ctrl + Shift + R`

2. **打开配置面板**：
   ```javascript
   window.openConfig()
   ```

3. **查看当前配置**：
   ```javascript
   console.log(window.state.config)
   ```

4. **修改配置**：
   ```javascript
   // 启用深度加载
   window.ConfigManager.set('enableDeepLoad', true)

   // 启用详细日志
   window.ConfigManager.set('verboseLogging', true)
   ```

## 📋 配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `enableDeepLoad` | `false` | 深度加载开关（从后端恢复历史数据） |
| `deepLoadReason` | 只读 | 禁用原因说明（自动生成） |
| `verboseLogging` | `false` | 详细日志开关 |

## ⚠️ 重要提示

### 默认配置（推荐）

```javascript
{
    enableDeepLoad: false,  // 保持禁用
    verboseLogging: false   // 保持简洁日志
}
```

**原因**：
- 后端使用内存存储，Docker重启后数据丢失
- 禁用深度加载可保护localStorage数据不被空数据覆盖

### 何时启用深度加载

只有在满足以下**所有条件**时才启用：
- ✅ 后端已配置数据库（PostgreSQL/MySQL）
- ✅ 或已配置Redis缓存
- ✅ 确认数据不会因重启丢失
- ✅ 测试过不会导致数据丢失

## 🔍 验证配置生效

### 方法1：控制台检查

```javascript
// 检查当前配置
console.log('深度加载:', window.state.config.enableDeepLoad);
console.log('详细日志:', window.state.config.verboseLogging);
```

### 方法2：执行测试

1. 禁用深度加载时（默认）：
   - 刷新页面 → 只显示localStorage中的session

2. 启用深度加载时：
   - 刷新页面 → 从后端+localStorage合并session

## 📚 相关文档

- [CONFIG_GUIDE.md](./CONFIG_GUIDE.md) - 详细配置指南
- [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) - 安全配置

---

**修改时间**: 2026-03-23
**修改文件**:
- `static/opencode.js` - 添加config对象
- `static/config-manager.js` - 配置管理器（新文件）
- `static/index.html` - 引入配置管理器
- `CONFIG_GUIDE.md` - 配置使用指南（新文件）

**Docker状态**: ✅ 已重启
