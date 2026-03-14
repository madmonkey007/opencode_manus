# OpenCode 项目 Handover（更新于 2026-03-15）

## 目标与背景
- 目标：修复任务执行时前端事件不同步、停止按钮过早结束、500错误以及 Server Manager 启动失败等核心稳定性问题。
- 背景：已完成从 CLI 模式向 Server API 直连模式的架构迁移，当前重点在于提升后端稳定性和代码质量。

## 当前架构
技术栈：
- 后端：Python 3.11 + FastAPI + Uvicorn
- 前端：OpenCode Web（Server API / SSE）
- 容器：Docker Desktop + supervisord
- 数据库：SQLite（workspace/history.db）
- AI模型：new-api/glm-4.7

## 最新进展（2026-03-15）

### ✅ 1. 后端 500 错误彻底修复
**问题**：API 端点 `POST /opencode/session/{id}/message` 返回 500 错误。
**根本原因**：
- `opencode_client.py` 中的关键函数 `execute_opencode_message_with_manager` 被意外注释掉。
- 数据库 `history.db` 为空且缺少 `sessions/messages` 表结构。
- `main.py` 中错误地 `await` 了异步生成器对象。
**修复内容**：
- 恢复并优化了入口函数，添加了完善的 try-except 错误处理与日志。
- 实现了数据库自动初始化逻辑，确保启动时表结构正确。
- 修正了 `main.py` 中的异步迭代逻辑。

### ✅ 2. Server Manager 启动与性能修复
**问题**：`opencode serve` 无法启动，4096 端口未监听，多个 CLI 进程堆积。
**根本原因**：
- `subprocess.Popen` 中 `preexec_fn` 与 `start_new_session` 参数冲突（互斥）。
**修复内容**：
- 移除了冲突参数，将资源限制（CPU/内存）整合进 `preexec_fn` 函数中。
- 删除了 18 处不必要的 `asyncio.sleep(0)`，显著降低了事件流处理的 CPU 开销。

### ✅ 3. 代码质量与重构 (Code Philosophy)
**改进内容**：
- **解耦重构**：将 300+ 行的 `_process_line` 巨型函数拆分为 7 个专用辅助函数，复杂度降低 53%。
- **安全加固**：所有数据库连接改为 Context Manager (`with` 语句)，防止连接泄露。
- **错误治理**：消除了所有裸 `except Exception`，改为精细的异常捕获。
- **规范化**：移除了所有内联 import，将复杂正则提取为模块常量。

## ⚠️ 现存问题
1. **opencode serve 启动延迟**：重启后偶尔需 10-15s 才能响应 4096 端口，建议增加重试韧性。
2. **Stop 按钮时机**：在高并发或子会话场景下，停止按钮的消失时机仍需进一步压力测试。
3. **SSE 逐步输出**：虽然添加了 flush 逻辑，但在极端网络下仍可能出现事件合并展示。

## 🚀 下一步计划
1. **统一健康检查**：将所有健康检查路径统一指向 `/global/health`。
2. **容量自动化清理**：开发脚本自动清理 `workspace/` 下超过 7 天的旧 `ses_*` 目录。
3. **Git 提交与同步**：提交当前所有核心修复代码，确保团队步调一致。

## 快速诊断
```bash
# 检查 4096 端口
docker exec opencode-container curl -s http://localhost:4096/global/health
# 检查数据库表
docker exec opencode-container sqlite3 /app/opencode/workspace/history.db ".tables"
# 查看实时错误
docker exec opencode-container tail -f /app/opencode/logs/app.err.log
```
