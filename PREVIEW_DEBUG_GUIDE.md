# Preview事件调试指南

## 问题描述
运行任务时只显示thought事件，不显示文件预览和交付面板。

## 调试步骤

### 1. 后端日志检查

运行任务后，查看后端日志：

```bash
# 查看完整的preview事件流程
tail -f logs/app.err.log | grep -E "PREVIEW|preview|listener"
```

**期望看到的日志**：
```
[PREVIEW] Generating preview for write: /path/to/file (1234 chars)
[PREVIEW] Session ID: ses_xxx, Step ID: step_xxx
[PREVIEW] Current listener count for session ses_xxx: 1
[PREVIEW] Broadcasting to 1 listener(s)
[PREVIEW] Sent preview_start event
[PREVIEW] Starting typewriter effect: 20 chunks, 1234 chars
[EventStreamManager] Broadcasting 'preview_delta' to 1 listeners for session ses_xxx
[PREVIEW] Completed typewriter effect: 20 chunks sent
[EventStreamManager] Broadcasting 'preview_end' to 1 listeners for session ses_xxx
[PREVIEW] Sent preview_end event
```

**问题日志（如果出现）**：
```
[PREVIEW] Current listener count for session ses_xxx: 0
[PREVIEW] ⚠️ No listeners for session ses_xxx!
[EventStreamManager] ⚠️ Session ses_xxx not in listeners
```

### 2. 前端控制台检查

在浏览器中打开开发者工具（F12），然后在控制台运行调试脚本：

```javascript
// 方法1：加载调试脚本
// 将项目根目录的debug_preview_events.js内容粘贴到控制台

// 方法2：手动检查EventSource
console.log('Active SSE:', window.state?.activeSSE);
console.log('SSE ReadyState:', window.state?.activeSSE?.readyState);

// 方法3：检查事件监听
if (window.apiClient) {
    console.log('API Client EventSources:', window.apiClient.eventSources);
}
```

### 3. 常见问题诊断

#### 问题A：Session ID不匹配

**症状**：
```
[PREVIEW] Session ID: ses_dee5bb5d
[EventStreamManager] ⚠️ Session ses_dee5bb5d not in listeners
Current sessions: ['ses_2e68fea1dffejwfPJPJK2b0phq']
```

**原因**：前端订阅的session ID与后端发送的session ID不一致

**修复**：检查session ID映射逻辑

#### 问题B：SSE连接过早断开

**症状**：
```
[PREVIEW] Current listener count for session ses_xxx: 0
```

**原因**：SSE连接在任务完成前断开

**修复**：检查网络连接和超时设置

#### 问题C：事件未被正确适配

**症状**：后端发送了事件，但前端没显示

**原因**：事件适配器没有正确转换事件格式

**修复**：检查浏览器控制台的事件日志

## 下一步行动

1. 运行一个新任务（如"写一个简单的HTML页面"）
2. 收集后端日志和前端控制台输出
3. 将日志内容保存到文件
4. 提供日志内容以便进一步分析

## 收集完整日志

```bash
# 后端日志
grep "ses_<session_id>" logs/app.err.log > debug_backend.log

# 前端日志
# 在浏览器控制台执行：
console.log(JSON.stringify(localStorage));
```
