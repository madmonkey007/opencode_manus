# OpenCode Web Interface — 项目交接文档

**更新日期**：2026-03-20  
**项目健康度**：85/100 ✅  
**当前分支**：master  
**最新 commit**：`4b516a2` fix: phases/thought history restore

---

## 🏗️ 架构概览

```
前端 (端口 8089)          后端 FastAPI (端口 8089)       OpenCode Server (端口 4096)
─────────────────         ──────────────────────────     ──────────────────────────
opencode.js               app/main.py                    执行 AI 任务
opencode-new-api-patch.js app/api.py                     返回 SSE 事件流
event-adapter.js          app/opencode_client.py
enhanced-task-panel.js    app/history_service.py
                          app/server_manager.py
```

**两个服务都必须运行**：
- FastAPI：`uvicorn app.main:app --host 0.0.0.0 --port 8089`
- OpenCode Server：端口 4096（由 server_manager 管理）

---

## ✅ 已解决的问题

### 1. AI 回复重复（"343434"）
**根因**：`opencode_client.py` 使用全局字典 `_SENT_TEXT_LENGTHS_GLOBAL` 做增量去重，确保每段文本只发送 delta。  
**状态**：✅ 已解决，正常运行。

### 2. 历史记录恢复 — thought/phase 丢失（最近修复）

**现象**：刷新页面后点击历史记录，thought 和 phase 不显示。

**根因分析**：
- `session_phases` 表可能为空（`phases_init` 事件字段路径不确定）
- 深度加载时 `data.phases` 为空会覆盖 localStorage 里已有的 phases
- thought 没有 phase 容器包裹，裸露显示在 response 前

**已做的修复**（commit `4b516a2`）：

| 文件 | 修改内容 |
|------|---------|
| `app/opencode_client.py` | 扩大 `phases_init` 事件类型匹配（加 `session.phases`/`phases`）；加 warning log 打印完整 payload |
| `static/opencode.js` | 深度加载时 `data.phases` 为空不覆盖 localStorage 已有 phases（两处：`item.onclick` 和 `loadState`） |
| `static/enhanced-task-panel.js` | thought 包进"思考过程"伪 phase 卡片（兜底，phases 为空时也能正常显示） |

**当前状态**：✅ 刷新后 thought 和 phase 正常显示。

---

## ⚠️ 待确认的问题

### phases_init 事件字段路径

**背景**：`opencode_client.py` 里持久化 phases 的代码依赖 `phases_init` 事件，但 opencode server 发的事件类型名和字段路径未经验证。

**当前代码**（`opencode_client.py` ~340行）：
```python
if etype in ("phases_init", "session.phases", "phases") and self.history_service:
    phases = (
        props.get("phases") or
        payload.get("phases") or
        props.get("data", {}).get("phases") or
        []
    )
    logger.info(f"[PHASES] etype={etype} phases_count={len(phases)} ...")
    if not phases:
        logger.warning(f"[PHASES] phases_init received but phases is empty. Full payload: {payload}")
```

**下一步**：发一个有工具调用的任务（如"写一个 hello world python 文件"），在后端日志里找 `[PHASES]` 那行，确认：
1. `etype` 是什么（`phases_init`？`session.phases`？）
2. phases 字段在 `props` 还是 `payload` 里
3. `session_phases` 表是否有数据写入

如果 `[PHASES] phases_init received but phases is empty` 出现，说明字段路径还需要修。

---

## 📁 关键文件说明

### 后端

| 文件 | 职责 |
|------|------|
| `app/opencode_client.py` | 连接 OpenCode Server，桥接 SSE 事件流，持久化 phases/parts |
| `app/api.py` | REST API，`GET /session/{id}/messages` 返回 messages + phases |
| `app/history_service.py` | SQLite 持久化：`message_parts`、`session_phases`、`steps` 表 |
| `app/main.py` | FastAPI 入口，SSE 端点，catch-up 逻辑 |

### 前端

| 文件 | 职责 |
|------|------|
| `static/opencode.js` | 主控制器，`loadState`/`saveState`，历史记录深度加载 |
| `static/opencode-new-api-patch.js` | API 补丁，`processEvent`，`handleHistorySessionClick`，SSE 连接 |
| `static/enhanced-task-panel.js` | 渲染 phases/thought/response 的 UI 组件 |
| `static/event-adapter.js` | 事件格式转换 |
| `static/api-client.js` | HTTP 请求封装 |

---

## 🔄 数据流（历史恢复）

```
刷新页面
  → loadState() 从 localStorage 读取 sessions
  → 如果 session 有 phases 但 actions 为空 → 触发深度加载
      → apiClient.getMessages(sessionId)
          → GET /session/{id}/messages
          → 后端返回 { messages, phases }  ← phases 来自 session_phases 表
      → data.phases 有值 → 更新 s.phases
      → data.phases 为空 → 保留 localStorage 里的 phases（不覆盖）✅
  → renderAll() → renderEnhancedTaskPanel(session)
      → 渲染 phases 卡片（含 phase.events）
      → 渲染 thoughtEvents 伪 phase 卡片（兜底）✅
      → 渲染 response
```

---

## 🗄️ 数据库表结构

SQLite 文件：`app/opencode_history.db`（或类似路径）

| 表 | 内容 |
|----|------|
| `sessions` | 会话基本信息 |
| `messages` | 消息（user/assistant） |
| `message_parts` | 消息的 parts（text/thought/tool） |
| `session_phases` | phases（可能为空，待验证） |
| `steps` | 工具调用步骤（timeline） |

**验证命令**：
```powershell
# 检查 session_phases 是否有数据
Invoke-WebRequest -Uri "http://localhost:8089/opencode/session/{SESSION_ID}/messages" -UseBasicParsing | Select-Object -ExpandProperty Content
# 看返回的 "phases" 字段是否为空数组
```

---

## 🚀 快速启动

```bash
# 启动 FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8089 --reload

# 访问
http://localhost:8089
```

---

## 📝 Git 历史（近期）

```
4b516a2  fix: phases/thought history restore - debug log + preserve phases on deep load + thought pseudo-phase card
30a0770  chore: update gitignore + remove temp files
21887e5  fix: history restore thought/text separation, phase persistence, get_messages 404
```
