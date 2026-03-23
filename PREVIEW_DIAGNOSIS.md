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

| 优先级 | 问题 | 影响 | 修复难度 | 状态 |
|--------|------|------|----------|------|
| P0 | Preview事件丢失 | 高 | 中 | ✅ 已修复 |
| P1 | 文件路径不匹配 | 高 | 低 | ⚠️ 待修复 |
| P2 | 前端文件查找 | 中 | 低 | ✅ 已修复 |

## 修复记录

### ✅ P0: Preview事件丢失问题（已修复）

**修复日期**: 2026-03-24

**修复方案**: 在`app/opencode_client.py`的`_bridge_global_events`方法中：
1. 在`session.idle`事件处理时，等待所有active preview任务完成
2. 添加30秒超时保护，防止任务卡住
3. 在finally块中取消未完成的任务并清理

**核心代码**:
```python
if self._active_preview_tasks:
    logger.info(f"Session idle detected, waiting for {len(self._active_preview_tasks)} preview task(s)...")
    try:
        await asyncio.wait_for(
            asyncio.gather(*self._active_preview_tasks, return_exceptions=True),
            timeout=30.0
        )
        logger.info(f"All preview tasks completed for session {session_id}")
    except asyncio.TimeoutError:
        logger.warning(f"Preview tasks timed out after 30s")
    finally:
        for task in list(self._active_preview_tasks):
            if not task.done():
                task.cancel()
        self._active_preview_tasks.clear()
stop_event.set()
```

**Commit**: `4c0872b` - fix(opencode_client): 修复preview事件在session idle时丢失问题

**代码审查结果**:
- ✅ 修复策略正确
- ✅ 添加超时保护
- ✅ 添加任务取消机制
- ✅ 错误处理完整

### ⚠️ P1: 文件路径不匹配问题（待修复）

**现象**: 文件生成在`/workspace/alarm-clock/index.html`而不是`/workspace/ses_dee5bb5d/alarm-clock/index.html`

**影响**: 前端无法在正确的session目录下找到文件

**待修复**: 需要确保文件写入时使用session隔离路径

## 下一步

1. ✅ 已添加调试日志
2. ✅ 已改进preview事件发送时机（P0修复）
3. 🔧 需要修复文件路径映射（P1待修复）
4. 🧪 需要测试验证修复效果
