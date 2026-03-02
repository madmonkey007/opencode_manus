# 子会话自动监听功能 - 使用指南

## 功能概述

OpenCode现在支持自动监听和显示子代理（通过task工具创建）的工具调用事件。当主会话使用task工具创建子代理时，前端会自动订阅子会话的事件流，并将所有工具调用（read、write、bash等）实时显示在右侧面板。

## 核心特性

### 1. 自动检测和订阅
- **零配置**: 前端自动检测task工具事件
- **智能解析**: 从task输出中解析子session ID
- **即时订阅**: 自动建立SSE连接到子会话

### 2. 事件路由和适配
- **透明路由**: 子会话事件自动路由到主会话处理
- **上下文保持**: 所有子会话事件标记来源，便于追踪
- **UI集成**: 子会话的工具调用显示在主界面右侧面板

### 3. 内存管理
- **自动清理**: 会话切换时取消旧会话的子会话订阅
- **防重复**: 智能检测，避免重复订阅同一子会话
- **生命周期追踪**: 维护主子会话映射关系

## 技术架构

### 核心组件

#### 1. ChildSessionManager (子会话管理器)
```javascript
// 位置: opencode-new-api-patch.js

// 主要方法:
ChildSessionManager.parseChildSessionId(output)        // 解析子session ID
ChildSessionManager.subscribeToChildSession(...)       // 订阅子会话
ChildSessionManager.unsubscribeFromChildSession(...)   // 取消订阅
ChildSessionManager.getChildSessions(mainId)          // 获取子会话列表
ChildSessionManager.isChildSession(sessionId)         // 检查是否为子会话
```

#### 2. 事件处理增强
```javascript
// 在 processEvent 函数中添加:
if (adapted.type === 'action' && adapted.data?.tool_name === 'task') {
    const childSessionId = ChildSessionManager.parseChildSessionId(output);
    if (childSessionId) {
        ChildSessionManager.subscribeToChildSession(
            s.id,          // 主会话ID
            childSessionId, // 子会话ID
            (mainSession, childEvent) => {
                // 事件回调: 处理子会话事件
                processEvent(mainSession, childEvent);
            }
        );
    }
}
```

#### 3. EventAdapter增强
```javascript
// 位置: event-adapter.js

// 支持子会话上下文:
const adapted = EventAdapter.adaptEvent(newEvent, session, {
    childSessionId: 'ses_xxx'  // 标记事件来源
});

// 适配后的事件包含:
adapted._childSessionId      // 子会话ID
adapted._isFromChildSession  // 来源标记
```

## 数据流图

```
┌─────────────────────────────────────────────────────────────┐
│                     主会话 (ses_main)                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  processEvent 处理                                    │  │
│  │                                                       │  │
│  │  检测到 task 工具事件                                  │  │
│  │  └─> 解析子session ID: ses_child                     │  │
│  │  └─> 调用 ChildSessionManager.subscribeToChildSession│  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ChildSessionManager                                 │  │
│  │                                                       │  │
│  │  apiClient.subscribeToEvents(ses_child)              │  │
│  │  └─> 建立 SSE 连接到子会话                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ SSE事件流
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   子会话 (ses_child)                         │
│                                                              │
│  事件流:                                                     │
│  - read工具: 读取文件                                        │
│  - write工具: 写入文件                                       │
│  - bash工具: 执行命令                                        │
│  - ... 其他工具                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ 事件路由
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              事件适配和显示 (主会话上下文)                    │
│                                                              │
│  1. EventAdapter.adaptEvent(childEvent, mainSession, {      │
│       childSessionId: 'ses_child'                           │
│     })                                                      │
│                                                              │
│  2. processEvent(mainSession, adaptedEvent)                 │
│     └─> 更新主会话的 phases 和 actions                      │
│                                                              │
│  3. 右侧面板显示                                             │
│     └─> showFileEditor() 显示工具操作                       │
│                                                              │
│  4. 实时渲染                                                 │
│     └─> renderResults() 更新UI                              │
└─────────────────────────────────────────────────────────────┘
```

## 使用示例

### 场景1: 基本使用

1. **用户提交任务**
```javascript
// 用户输入: "创建一个React组件"
// 主会话: ses_main_123
```

2. **主代理使用task工具**
```javascript
// 主会话事件流:
{
  type: "tool_use",
  sessionID: "ses_main_123",
  part: {
    tool: "task",
    state: {
      output: "task_id: ses_child_456\n\n<task_result>..."
    }
  }
}
```

3. **前端自动订阅子会话**
```javascript
// ChildSessionManager 自动:
// - 解析: ses_child_456
// - 订阅: subscribeToEvents("ses_child_456")
// - 路由: 子会话事件 -> 主会话processEvent
```

4. **子会话的工具调用显示在右侧面板**
```javascript
// 子会话事件:
{
  type: "tool_event",
  data: {
    type: "tool",
    tool: "read",
    output: "文件内容..."
  }
}

// 自动适配并显示在主会话的右侧面板
```

### 场景2: 多层嵌套

```
主会话 (ses_main)
  └─> 子会话1 (ses_sub1)
       └─> 子会话2 (ses_sub2)
```

- ✅ **支持**: 每层子会话都会被自动订阅
- ✅ **独立管理**: 每个子会话有独立的SSE连接
- ✅ **清晰路由**: 事件标记来源，便于追踪

## 调试和监控

### 1. 使用测试脚本

```javascript
// 在浏览器控制台中运行:

// 运行完整测试套件
// (自动运行，或手动执行 test-child-session.js)

// 查看子会话状态
testChildSessionStatus();

// 模拟task事件
testManualTaskEvent();
```

### 2. 控制台日志

```javascript
// 关键日志标识符:

[ChildSession] Subscribing to: ses_xxx
[ChildSession] Found child session: ses_xxx
[ChildSession] Routing event from ses_child to ses_main
[ChildSession] Child session completed: ses_child
[ChildSession] Unsubscribed: ses_child from ses_main
```

### 3. 状态检查

```javascript
// 获取主会话的所有子会话
const children = ChildSessionManager.getChildSessions('ses_main_123');
console.log('子会话列表:', children);

// 检查是否为子会话
const isChild = ChildSessionManager.isChildSession('ses_child_456');
console.log('是子会话:', isChild);

// 获取子会话的主会话ID
const mainId = ChildSessionManager.getMainSessionId('ses_child_456');
console.log('主会话ID:', mainId);
```

## 性能考虑

### 内存管理
- **自动清理**: 切换会话时取消旧订阅
- **防重复**: 同一子会话只订阅一次
- **限制数量**: 实际使用中子会话数量有限

### 网络连接
- **SSE复用**: 使用同一个apiClient实例
- **错误处理**: 连接失败时自动清理
- **心跳检测**: EventSource内置重连机制

## 最佳实践

### 1. 不要手动管理子会话订阅
```javascript
// ❌ 错误: 手动订阅
apiClient.subscribeToEvents(childId, handler);

// ✅ 正确: 让ChildSessionManager管理
// processEvent会自动检测并订阅
```

### 2. 利用事件上下文标记
```javascript
// 检查事件来源
if (adapted._isFromChildSession) {
    console.log('来自子会话:', adapted._childSessionId);
}
```

### 3. 测试时使用模拟数据
```javascript
// 使用 test-child-session.js 中的工具
testManualTaskEvent(); // 不需要真实后端
```

## 故障排除

### 问题1: 子会话事件未显示

**可能原因**:
- 子session ID解析失败
- SSE连接失败
- 事件适配错误

**解决方案**:
```javascript
// 1. 检查解析
const childId = ChildSessionManager.parseChildSessionId(output);
console.log('解析结果:', childId);

// 2. 检查订阅状态
const isSubscribed = ChildSessionManager.isChildSession(childId);
console.log('已订阅:', isSubscribed);

// 3. 查看完整日志
localStorage.setItem('debug_child_session', 'true');
```

### 问题2: 内存泄漏

**可能原因**:
- 会话切换时未取消订阅
- EventSource未正确关闭

**解决方案**:
```javascript
// 手动清理所有子会话
const activeId = window.state.activeId;
ChildSessionManager.unsubscribeAllFromMain(activeId);
```

### 问题3: 事件显示混乱

**可能原因**:
- 子会话事件路由到错误的主会话
- 事件适配器丢失上下文

**解决方案**:
```javascript
// 检查事件来源
console.log('事件来源:', adapted._childSessionId);
console.log('主会话:', s.id);

// 验证适配
const adapted = EventAdapter.adaptEvent(event, session, {
    childSessionId: 'ses_xxx'
});
```

## 扩展和定制

### 添加自定义事件过滤

```javascript
// 在 processEvent 中添加过滤
if (adapted._isFromChildSession) {
    // 只显示特定类型的事件
    const allowedTools = ['read', 'write', 'bash'];
    const toolName = adapted.data?.tool_name;

    if (!allowedTools.includes(toolName)) {
        return; // 跳过此事件
    }
}
```

### 自定义子会话UI显示

```javascript
// 在事件处理中添加特殊标记
if (adapted._isFromChildSession) {
    adapted.title = `[子代理] ${adapted.data.title}`;
    adapted.color = '#FFA500'; // 橙色标记
}
```

## 版本历史

### V1.0 (当前版本)
- ✅ 自动检测和订阅子会话
- ✅ 事件路由和适配
- ✅ 内存管理和自动清理
- ✅ 上下文标记和追踪
- ✅ 完整测试套件

### 未来计划
- [ ] 子会话独立UI标签页
- [ ] 子会话性能监控
- [ ] 嵌套层级可视化
- [ ] 子会话结果汇总

## 相关文件

```
D:\manus\opencode\static\
├── opencode-new-api-patch.js   (主要实现)
├── event-adapter.js             (事件适配)
├── api-client.js                (SSE订阅)
├── test-child-session.js        (测试脚本)
└── CHILD_SESSION_GUIDE.md       (本文档)
```

## 支持

如有问题或建议，请查看:
- 控制台日志: 搜索 `[ChildSession]` 标记
- 测试脚本: 运行 `test-child-session.js`
- 代码注释: 查看 `opencode-new-api-patch.js`

---

**最后更新**: 2025-01-XX
**版本**: V1.0
**作者**: OpenCode开发团队
