# OpenCode 项目移交文档 (Handover)

**更新日期**：2026-03-17
**项目健康度**：85/100 (⚠️ 存在严重重启与数据混入问题)

---

## 🏗️ 完整架构概览

### 1. 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户浏览器 (Web UI)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  输入面板     │  │  任务面板     │  │  文件预览面板          │  │
│  │ opencode.js  │  │enhanced-task │  │ code-preview-overlay │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         ↓ SSE (EventSource)                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              前端事件处理层                                │   │
│  │  opencode-new-api-patch.js  ←→  event-adapter.js         │   │
│  │  api-client.js              ←→  right-panel-manager.js   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                    ↕ HTTP REST + SSE
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI 后端 (端口 8089)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    app/api.py (路由层)                    │   │
│  │  POST /opencode/session                 创建会话          │   │
│  │  POST /opencode/session/{id}/message    发送消息          │   │
│  │  GET  /opencode/session/{id}/events     SSE 事件流        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   业务逻辑层                               │   │
│  │  OpenCodeClient (app/opencode_client.py)                 │   │
│  │    └─ _execute_via_server_api() → 优先 Server API        │   │
│  │    └─ _bridge_global_events() → SSE 事件桥接              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                    ↕ HTTP API (端口 4096)
┌─────────────────────────────────────────────────────────────────┐
│              OpenCode Server (opencode serve)                    │
│  由 OpenCodeServerManager (app/server_manager.py) 管理           │
│  由 supervisord 管理 app 进程生命周期                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚨 当前项目进展与核心问题

### 🔴 问题 1：任务回复中混入 "Session started" 与 HTML 代码
**现象描述**：
用户输入查询（如 "45+11"）后，AI 的正式回复正文前会重复一遍问题，且正文中可能显示大量的 HTML 源码，导致页面渲染异常。任务状态常卡在 "Executing"。

**诊断证据**：
- **Console 日志**：`msgid=295 {"type": "answer_chunk", "text": "Session started: ses_xxxx <!doctype html>..."}`
- **后端源码分析**：`main.py` 中的 `process_log_line` 函数会将日志文件中的任何非 JSON、非噪音文本行作为 `answer_chunk` 发送。
- **数据流追踪**：
    1. `main.py:407` 写入 "Session started" 到日志。
    2. `main.py:439` 写入 opencode 执行结果（含 HTML 内容）到日志。
    3. `process_log_line` 读取日志并错误地通过 SSE 发送到前端。

**可能原因**：
- 后端错误地将本应作为内部日志或队列处理的普通文本（非 JSON 格式）二次封装为 SSE `answer_chunk` 事件发送。

**修复进展**：
- ✅ **已实施**：修改 `app/main.py` 中的 `process_log_line`，注释掉普通文本的处理逻辑，仅转发 JSON 格式的事件。
- ✅ **待验证**：需要在清理缓存后观察新任务是否彻底移除混入内容。

---

### 🔴 问题 2：App 进程频繁被 SIGKILL 导致 FATAL 状态
**现象描述**：
后端 `app` 进程频繁重启。Supervisor 日志显示 `waiting for app to stop` 持续 10 秒后强杀进程。

**诊断证据**：
- **日志记录**：`WARN killing 'app' (PID) with SIGKILL`, `app entered FATAL state, too many start retries too quickly`。
- **Supervisor 配置**：缺少 `stopwaitsecs` 参数，默认 10 秒。

**可能原因分析**：
1. **超时设置过短**：默认 10 秒不足以让 uvicorn 处理完现有的 SSE 连接或 AI 任务。
2. **信号响应缺失**：`main.py` 缺乏显式的信号处理器来接收并触发 uvicorn 的优雅关闭。
3. **阻塞操作**：`asyncio.wait_for(queue.get(), timeout=1.0)` 等密集型操作可能在某些极端下干扰了事件循环的关闭信号处理。

---

## 🛠️ 修复方案与下一步计划

### 1. 紧急修复计划 (Next Actions)

- **[P0] 调整进程管理配置**：
    - **修改文件**：`D:\manus\opencode\supervisord.conf`
    - **内容**：在 `[program:app]` 节添加 `stopwaitsecs=30`，给 uvicorn 足够的退出缓冲期。
    - **预期**：消除 SIGKILL 导致的 FATAL 重启循环。

- **[P1] 增强 Uvicorn 优雅关闭**：
    - **修改文件**：`app/main.py`
    - **内容**：在 `uvicorn.Config` 中显式设置 `timeout_graceful_shutdown=30`，并注册 `shutdown` 事件处理器来清理 `ServerManager`。

- **[P1] 优化异步等待超时**：
    - **修改文件**：`app/main.py`
    - **内容**：将 `asyncio.wait_for` 的 1.0 秒超时放宽至 5.0 秒，减少频繁的超时异常对事件循环的压力。

### 2. 待核实的方向 (Future Investigations)

- **AI 模型倾向**：核实 `glm-4.7` 是否在特定 prompt 下倾向于返回包含环境上下文（如 HTML）的异常内容。
- **日志竞争**：排查是否存在多个进程同时写入同一个 `run.log` 导致的内容混乱。

---

## 📂 关键文件索引
- `app/main.py`: 核心流程控制、日志解析、SSE 事件分发。
- `app/opencode_client.py`: Server API 交互逻辑。
- `static/opencode-new-api-patch.js`: 前端补丁、循环检测逻辑。
- `supervisord.conf`: 宿主机进程生命周期配置。

---
**维护者注**：本次更新重点解决了“内容混入”的根源定位，并锁定了“进程强制杀掉”为重启问题的直接诱因。下一步应优先通过修改配置来稳固服务环境。
