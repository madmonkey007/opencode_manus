# OpenCode 项目 Handover（更新于 2026-03-12）

## 目标与背景
- 目标：修复任务执行时前端事件/交付面板不同步、停止按钮过早结束、工具显示 unknown、thought 事件重复或不展示，以及 SSE 长时间无输出后一次性展示的问题。
- 背景：已切换为 Server API 直连，前端通过 SSE 渲染事件流。

## 当前架构
技术栈：
- 后端：Python 3.11 + FastAPI + Uvicorn
- 前端：OpenCode Web（Server API / SSE）
- 容器：Docker Desktop + supervisord
- 数据库：SQLite（workspace/history.db）
- OpenCode CLI：opencode-ai@1.2.24

端口：
- 8089：主应用（Nginx 代理）
- 8000：FastAPI（容器内）
- 4096：opencode serve
- 6901：VNC

目录（核心）：
```
D:\manus\opencode\
  app/
    api.py
    main.py
    server_manager.py
    opencode_client.py
  static/
  workspace/
  docker-compose.yml
```

## 本次关键变更（已落地）
1) 前端增量渲染（解决“等很久才一下全展示”）
- 文件：static/event-adapter.js
- 新增处理 message.part.delta，把 text delta 转为 answer_chunk；thought delta 单独事件。
- 记录 partTypeById，保证 delta 能正确判断类型。

2) 前端 UI 事件处理稳定性
- 文件：static/opencode-new-api-patch.js
- stop 按钮：仅在“当前 assistant message 完成”时才结束，避免其他消息触发提前结束。
- thought 事件：忽略空内容，避免重复/空白 thought 展示。
- 工具名 fallback：tool/name/action 多字段兜底，减少 unknown。
- thought_delta 仅用于调试，不展示（避免泄露思考过程）。

3) 后端 SSE 结束条件修正
- 文件：app/opencode_client.py
- SSE bridge 收到 assistant message.updated completed 时设置 completed 并 stop_event。
- _execute_via_server_api：等待 SSE 完成或超时后再停止 bridge，避免“POST 后立刻结束”。

## 现存问题（需继续验证/修复）
P0：
1. stop 按钮仍可能过早结束（需确认是否还有非当前 message 的 completed 触发）。
2. SSE 事件仍可能批量出现（需确认 opencode serve 是否在服务端缓冲）。

P1：
3. 工具事件部分显示为 unknown（需核对 Server API part/tool 字段来源）。
4. thought 事件出现两个：一个无内容、一个有内容（已忽略空 thought，但需验证来源）。
5. 右侧预览面板内容与事件不同步（疑似事件完成顺序和 deliverables 更新时机问题）。
6. 交付面板偶发不展示（需看 deliverables 事件是否缺失）。

## 关键日志与证据
- 前端控制台长日志：D:\manus\opencode\logs\console-log.txt
- 典型现象：
  - SSE 连接建立后，长时间无渲染，任务完成后统一输出
  - thought 事件重复或空内容
  - stop 按钮提前消失
  - unknown tool

## 容量告警（需要处理）
- workspace/ 与 logs/ 下文件数量巨大（大量 ses_* 与前端日志），已明显影响 Git 状态与性能。
- 建议：
  - logs/console-log.txt 已保留；其余历史日志可归档/清理。
  - workspace/ 中旧 ses_* 目录可按日期清理或迁移备份。

## 下一步建议（按优先级）
1. 继续复测 SSE 逐步输出与 stop 按钮时机（建议执行“计算器/闹钟”类任务）。
2. 若仍批量输出，抓取 /global/event 流量，确认服务端是否缓冲或是否只发 thought。
3. 核对 tool 事件字段映射（opencode serve 原始 event payload）。
4. 检查 deliverables 事件来源与 UI 渲染时机。

## 快速诊断命令
```
docker ps | findstr opencode-container
docker exec opencode-container sh -c "netstat -tlnp 2>&1 | grep 4096"
docker exec opencode-container sh -c "tail -80 /app/opencode/logs/app.err.log"
docker exec opencode-container sh -c "tail -120 /root/.local/share/opencode/log/$(ls -1 /root/.local/share/opencode/log | tail -1)"
```

## 关键文件
- app/opencode_client.py（Server API 直连 + SSE bridge）
- static/event-adapter.js（前端事件适配与 delta 处理）
- static/opencode-new-api-patch.js（UI 事件展示逻辑）
- logs/console-log.txt（最新控制台日志）
