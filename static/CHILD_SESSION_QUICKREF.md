# 子会话自动监听功能 - 快速参考

## 🚀 快速开始

### 自动启用
无需任何配置！功能已自动集成到OpenCode中。

当主代理使用`task`工具创建子代理时，前端会自动：
1. ✅ 检测子会话ID
2. ✅ 订阅子会话事件流
3. ✅ 将工具调用显示在右侧面板
4. ✅ 会话切换时自动清理

---

## 📊 核心API

### ChildSessionManager

```javascript
// 解析子session ID (自动调用)
const childId = ChildSessionManager.parseChildSessionId(output);

// 检查是否为子会话
const isChild = ChildSessionManager.isChildSession(sessionId);

// 获取主会话的所有子会话
const children = ChildSessionManager.getChildSessions(mainSessionId);

// 获取子会话的主会话ID
const mainId = ChildSessionManager.getMainSessionId(childSessionId);

// 手动取消订阅 (通常不需要)
ChildSessionManager.unsubscribeFromChildSession(childSessionId);

// 取消主会话的所有子会话订阅
ChildSessionManager.unsubscribeAllFromMain(mainSessionId);
```

---

## 🔍 调试命令

```javascript
// 查看子会话状态
testChildSessionStatus();

// 模拟task事件
testManualTaskEvent();

// 检查订阅状态
const children = ChildSessionManager.getChildSessions(window.state.activeId);
console.log('子会话数量:', children.length);
```

---

## 🎯 工作流程

```
用户提交任务
    ↓
主代理使用task工具
    ↓
前端检测: "task_id: ses_xxx"
    ↓
自动订阅子会话SSE
    ↓
子会话工具调用事件
    ↓
适配并路由到主会话
    ↓
右侧面板实时显示
```

---

## 🛡️ 安全特性

### Parse, Don't Validate
- 在边界处解析子session ID
- 内部使用可信状态
- 避免重复验证

### Early Exit
- 所有边界检查在函数顶部
- 无效输入立即返回
- 清晰的错误消息

### Memory Safety
- 自动清理旧订阅
- 防止内存泄漏
- 限制连接数量

---

## 📝 事件标记

子会话事件包含额外标记：

```javascript
{
  type: 'action',
  data: { /* 工具数据 */ },
  _childSessionId: 'ses_child_123',    // 子会话ID
  _isFromChildSession: true             // 来源标记
}
```

---

## ⚠️ 注意事项

1. **不要手动订阅子会话**
   - ChildSessionManager会自动处理
   - 手动订阅可能导致重复

2. **会话切换时自动清理**
   - 不需要手动取消订阅
   - updateInterfaceMode劫持会处理

3. **子会话ID格式**
   - 必须以 `ses_` 开头
   - 格式: `task_id: ses_xxx`

4. **性能影响**
   - 每个子会话一个SSE连接
   - 实际使用中数量有限
   - 自动错误恢复

---

## 🔧 故障排除

### 问题: 子会话事件未显示

```javascript
// 检查解析
const childId = ChildSessionManager.parseChildSessionId(output);
console.log('解析结果:', childId);

// 检查订阅
const isSubscribed = ChildSessionManager.isChildSession(childId);
console.log('已订阅:', isSubscribed);

// 查看日志
// 搜索: [ChildSession]
```

### 问题: 内存泄漏

```javascript
// 手动清理
const activeId = window.state.activeId;
ChildSessionManager.unsubscribeAllFromMain(activeId);
```

---

## 📚 相关文件

| 文件 | 说明 |
|------|------|
| `opencode-new-api-patch.js` | 核心实现 |
| `event-adapter.js` | 事件适配 |
| `api-client.js` | SSE订阅 |
| `test-child-session.js` | 测试脚本 |
| `CHILD_SESSION_GUIDE.md` | 完整文档 |

---

## ✨ 示例场景

### 场景1: 单层子会话

```
主会话 (ses_main)
  └─> 子会话 (ses_child)
       ├─> read: src/App.tsx
       ├─> write: src/Button.tsx
       └─> bash: npm test
```

### 场景2: 多层嵌套

```
主会话 (ses_main)
  └─> 子会话1 (ses_sub1)
       ├─> read: package.json
       └─> 子会话2 (ses_sub2)
            ├─> write: src/index.js
            └─> bash: node src/index.js
```

---

## 🎨 UI显示

### 右侧面板
- 子会话的工具调用与主会话混合显示
- 通过 `_childSessionId` 标记区分
- 实时更新，打字机效果

### 状态栏
```javascript
[ChildSession] Subscribing to: ses_child_123
[ChildSession] Routing event from ses_child to ses_main
[ChildSession] Child session completed: ses_child_123
```

---

## 📖 完整文档

详细使用指南请参考:
**CHILD_SESSION_GUIDE.md**

---

**版本**: V1.0
**状态**: 生产就绪 ✅
