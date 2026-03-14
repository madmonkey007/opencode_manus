# OpenCode Stop Button Fix - 修复总结

## 问题描述
stop按钮可能在非当前message的completed事件触发时提前结束，导致任务实际上还在运行但UI已经显示完成。

## 根本原因分析
1. **子会话事件干扰**：当使用子会话（child session）时，子会话的message_updated事件会更新主会话的`_activeAssistantMessageId`
2. **消息ID混淆**：子会话和主会话的message_id是不同的，但代码没有区分来源，导致子会话的completed事件错误地触发了主会话的完成逻辑

## 修复内容

### 修复1：过滤子会话的消息跟踪（第2148-2154行）
```javascript
// 原代码：任何assistant message都会更新_activeAssistantMessageId
if (adapted.type === 'message_updated' && adapted.role === 'assistant' && ...) {
    s._activeAssistantMessageId = adapted.message_id;
    s._sessionIdleSeen = false;
}

// 修复后：只有非子会话的消息才会更新
const isFromChildSession = adapted._isFromChildSession === true;
if (... && !isFromChildSession) {
    s._activeAssistantMessageId = adapted.message_id;
    s._sessionIdleSeen = false;
}
```

### 修复2：过滤子会话的完成检测（第2200-2228行）
```javascript
// 新增：在计算completion时忽略子会话事件
const isFromChildSession = adapted._isFromChildSession === true;
const effectiveActiveAssistantMessageId = isFromChildSession ? null : s._activeAssistantMessageId;

// 在判断isAssistantCompletion时添加!isFromChildSession条件
const isAssistantCompletion = (
    !isFromChildSession &&  // 新增条件
    adapted.type === 'message_updated' &&
    adapted.time?.completed &&
    adapted.role === 'assistant' &&
    (...)
);
```

## 验证方法
1. 创建包含子会话的任务（如使用task工具的复杂任务）
2. 观察子会话的事件不会错误地触发主会话的完成状态
3. 确认stop按钮只在当前活跃的assistant message完成时才隐藏

## 代码质量保证
- 遵循**Early Exit**原则：边界检查在函数顶部处理
- 遵循**Parse, Don't Validate**：子会话状态通过`_isFromChildSession`标志明确标识
- 遵循**Fail Fast**：无效状态立即返回，不继续处理
- 遵循**Intentional Naming**：`isFromChildSession`和`effectiveActiveAssistantMessageId`命名清晰表达意图
