# Preview事件问题诊断报告

## 问题描述
运行"帮我写一个网页版闹钟"任务时：
- 只显示thought事件
- 没有文件预览
- 没有交付面板

## 诊断结果

### ✅ 文件确实生成了
**位置**: `workspace/alarm-clock/index.html`
**大小**: 18,851 字节
**状态**: 完整可用的HTML文件

### ❌ 问题1：路径与会话不一致
```
会话ID: ses_dee5bb5d
会话路径: /app/opencode/workspace/ses_dee5bb5d
实际文件: /app/opencode/workspace/alarm-clock/index.html
```

**问题**: 文件生成在workspace根目录下的 `alarm-clock/`，而不是在会话隔离目录 `ses_dee5bb5d/` 下。

### ❌ 问题2：Preview事件丢失
从日志分析：
```
[PREVIEW] Generating preview for write: /app/opencode/workspace/alarm-clock/index.html (18641 chars)
```

但没有后续的：
```
[PREVIEW] Broadcasting to X listener(s)
[EventStreamManager] Broadcasting 'preview_start' to X listeners
```

**根本原因**: `event_stream_manager.broadcast(session_id, event)` 时，`session_id` 不在 `listeners` 中，事件被静默丢弃。

## 根本原因分析

### Session ID映射问题
1. 前端SSE连接订阅: `ses_dee5bb5d`
2. 后端创建服务器session: `ses_2e68fea1dffejwfPJPJK2b0phq`
3. 后端发送preview事件到: `ses_dee5bb5d`
4. 但此时 `ses_dee5bb5d` 可能已经不在 `listeners` 中了

### 可能原因
1. **时序问题**: `_maybe_broadcast_preview` 作为异步任务运行时，SSE连接可能已经断开
2. **Session清理**: 前端在任务"完成"后断开SSE，但后端的preview异步任务还在执行
3. **路径问题**: 文件写入路径与session路径不匹配，导致前端无法读取

## 修复方案

### 方案1：修复文件路径映射（推荐）
确保文件写入session隔离目录：
- 从: `/app/opencode/workspace/alarm-clock/index.html`
- 到: `/app/opencode/workspace/ses_dee5bb5d/alarm-clock/index.html`

### 方案2：改进Preview事件发送时机
- 在发送preview前检查SSE连接是否活跃
- 如果连接已断开，记录警告但不发送事件
- 或者在任务完成前等待所有preview任务完成

### 方案3：降级文件查找逻辑
- 前端查找文件时，如果session目录为空，则查找workspace根目录
- 这样即使文件路径不匹配，前端也能找到并显示文件

## 优先级

| 优先级 | 问题 | 影响 | 修复难度 |
|--------|------|------|----------|
| P0 | Preview事件丢失 | 高 | 中 |
| P1 | 文件路径不匹配 | 高 | 低 |
| P2 | 前端文件查找 | 中 | 已修复 |

## 下一步

1. ✅ 已添加调试日志
2. 🔧 需要修复文件路径映射
3. 🔧 需要改进preview事件发送时机
4. 🧪 需要测试验证修复效果
