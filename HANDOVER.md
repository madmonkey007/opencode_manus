# OpenCode 项目移交文档 (Handover)

**更新日期**：2026-03-16
**当前状态**：⚠️ 存在无限循环问题，已实施临时修复，待专家进一步指导

---

## 🏗️ 项目架构概览

### 1. 技术栈
- **后端**：Python 3.12 + FastAPI + Uvicorn
- **前端**：OpenCode Web (原生 JS + SSE 实时推送)
- **容器**：Docker (supervisord 管理进程)
- **数据库**：SQLite (`/app/opencode/workspace/history.db`)
- **AI 引擎**：OpenCode CLI + Server API (`new-api/glm-4.7`)

### 2. 核心执行流程
1. **Web UI** 提交任务 -> 调用 `POST /opencode/session/{id}/message`
2. **API 服务** 接收请求 -> 自动检查/启动 **OpenCode Server (4096端口)**
3. **OpenCode Client** 执行任务 -> 优先使用 HTTP API，失败则降级到 CLI 模式
4. **History Service** 实时持久化 -> 消息和工具调用记录存入 SQLite
5. **SSE** 实时推送 -> 进度、思考过程、结果回传前端

---

## ✅ 已修复的核心问题

### 1. 历史数据丢失 (Critical)
- **问题**：刷新页面后，历史任务只显示提示词，详细记录全部丢失。
- **原因**：SQL 查询列名不匹配 (`message_id` vs `id`) 且数据库路径不统一。
- **修复**：修正了 `history_service.py` 中的查询别名，并强制统一使用容器内绝对路径。

### 2. 任务执行无输出 (Critical)
- **问题**：点击发送后前端无响应，后端 `run_agent` 没被调用。
- **原因**：
    1. 前端只订阅了 SSE，忘记调用 `sendMessage` 触发执行。
    2. 后端 `ServerManager` 虽运行但未真正启动 `opencode serve` 子进程。
    3. `isFromChildSession` 变量未定义导致 JS 报错中断流程。
- **修复**：补全前端调用链路，添加后端显式启动逻辑，并修复了 JS 语法和引用错误。

### 3. 前后端 Session 不同步 (Major)
- **问题**：前端使用本地生成的 ID 发送消息，后端因 ID 不存在返回 404。
- **修复**：实现了前端自动同步机制。如果 session 不存在，前端会先调用 `createSession` 创建并进行 ID 映射。

---

## 🚨 当前紧急问题：AI 模型无限循环 (Critical)

### 问题描述
**症状**：AI 模型在执行简单查询时出现无限思考循环，无法给出最终答案
- **典型输入**："hello" 或 "1+1等于几" 等简单查询
- **实际表现**：
  - AI 不断生成 thought 事件
  - 每个 thought 创建一个新的 step 和 phase
  - 观察到单个查询创建 **36+ 个 phases**
  - 任务一直显示"执行中"，永不完成
  - 最终响应包含重复几十遍的相同回答

### 根本原因分析
1. **build agent 配置问题**：
   - doom_loop 权限检测已配置，但 action 是 `"ask"`（询问用户）而非 `"deny"`（自动拒绝）
   - `question.asked` 事件可能未被正确触发或处理

2. **模型问题**：
   - glm-4.7 模型可能有已知的思考循环倾向
   - 缺少收敛参数配置（如 maxTokens, temperature）

3. **架构层面**：
   - 缺少任务复杂度评估机制
   - 简单查询和复杂任务使用相同执行策略

### 已实施的修复 (Commit: f4f7ed5)

#### 1. Doom Loop 自动拒绝机制
**文件**：`app/opencode_client.py:144-226`

```python
if etype == "question.asked":
    question_text = q.get("question", "")
    # 检测循环相关的权限请求
    if "loop" in question_text.lower() or "repetition" in question_text.lower():
        # 自动发送拒绝响应
        await client.post(
            f"{base_url}/session/{session_id}/permissions/{call_id}",
            json={"response": "deny", "remember": False}
        )
        # 返回错误事件，停止执行
        return {"type": "error", "properties": {"error": "..."}}
```

#### 2. 智能循环检测算法
**文件**：`app/opencode_client.py:1520-1620`

- **完全重复检测**：连续 10 个相同的 step 标题 → 立即停止
- **相似度检测**：使用 Jaccard 相似度算法（70% 阈值）→ 警告但继续
- **绝对上限**：200 步硬性限制 → 极端情况保护

**相似度算法**：
```python
def similarity_score(s1: str, s2: str) -> float:
    words1 = set(s1.split())
    words2 = set(s2.split())
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)  # 0-1 范围
```

#### 3. 前端 Phase 保护
**文件**：`static/opencode-new-api-patch.js:2167-2242`

- 从硬性 50 个 phase 限制改为智能检测
- 检测连续 15 个 phase 的重复模式
- 200 个 phase 硬性上限
- 100 个 phase 时显示进度提示

### 待解决的专家咨询问题

#### P0 - 核心配置问题
1. **Doom Loop 权限机制**
   - `question.asked` 事件的触发条件是什么？
   - 为什么 action 是 `"ask"` 而非 `"deny"`？这是设计意图还是配置错误？
   - 如何验证权限机制是否正常工作？

2. **模型配置**
   - glm-4.7 是否有官方已知的循环问题？
   - API 调用时应该配置哪些参数来避免循环？
   - 是否有推荐的替代模型？

3. **Agent 选择策略**
   - 对于简单查询，应该使用哪个 agent？（build, plan, auto?）
   - 是否有根据任务复杂度自动选择 agent 的机制？
   - build agent 的 doom_loop 权限如何配置为 `"deny"`？

#### P1 - 优化方向
4. **OpenCode 官方最佳实践**
   - 官方如何处理无限循环？
   - 是否有示例配置或文档？
   - 推荐的权限配置策略是什么？

5. **任务复杂度评估**
   - 如何在执行前评估任务复杂度？
   - 是否有任务类型分类机制？
   - 如何为不同复杂度配置不同的执行策略？

### 测试与验证
**测试脚本位置**：
- `D:\manus\opencode\direct_test.py` - 直接 API 测试
- `D:\manus\opencode\test_doom_loop_fix.js` - 浏览器测试

**复现步骤**：
```bash
# 方法1：使用浏览器
1. 打开 http://localhost:8089/
2. 点击"新任务"
3. 输入 "hello"
4. 观察是否在 20 步内完成

# 方法2：使用测试脚本
cd D:\manus\opencode
python direct_test.py
```

### 当前修复效果
✅ **已改进**：
- 不会误杀真正复杂的任务（可正常执行 100-150 步）
- 快速检测真正的循环（10-20 步内）
- 提供有意义的错误提示

⚠️ **仍需验证**：
- Doom Loop 自动拒绝机制是否被触发
- 简单查询是否能正常完成
- 权限响应 API 是否正确调用

### 相关代码位置
```
D:\manus\opencode\
├── app/
│   └── opencode_client.py       # 核心修复：第144-226行（权限拒绝）、第1520-1620行（循环检测）
├── static/
│   └── opencode-new-api-patch.js # 前端保护：第2167-2242行
└── API文档.md                    # OpenCode API 文档
```

---

## 🛠️ 关键技术实现

### 1. 并发启动锁
在 `opencode_client.py` 中引入 `asyncio.Lock`：
```python
if not hasattr(execute_opencode_message_with_manager, '_startup_lock'):
    execute_opencode_message_with_manager._startup_lock = asyncio.Lock()
# 确保多用户并发提交时，Server 只会被启动一次
```

### 2. 自动降级机制 (CLI Fallback)
系统优先使用高性能的 Server API 模式。若 4096 端口连接失败，将自动切换至 `opencode run` 命令行模式执行，确保存效性。

### 3. 增强日志系统
所有关键节点（执行前、成功、报错、降级）均添加了详细的日志记录，包含 `SessionID`、`MessageID` 和完整堆栈信息。

---

## ⚠️ 开发与运行注意事项

### 1. 模型配置 (最高优先级)
- **禁止私自修改模型配置**！
- 当前模型：`new-api/glm-4.7`
- 涉及文件：`app/main.py`、`app/opencode_client.py`、`.env`
- 修改前必须取得用户明确授权。

### 2. 数据库调试
- 数据库位置：`D:\manus\opencode\workspace\history.db` (挂载在容器 `/app/opencode/workspace/history.db`)
- 验证脚本：`D:\manus\opencode	ests	est_history_service.py`

### 3. 前端更新
- 若修改了 `static/*.js` 文件，必须**强制刷新浏览器 (Ctrl+Shift+R)**，否则旧缓存会导致执行失败。

---

## 📊 当前进程状态 (supervisorctl status)
| 进程名 | 状态 | 职责 |
| :--- | :--- | :--- |
| `app` | RUNNING | 主 API 服务 (8089 端口) |
| `python -m app.server_manager` | RUNNING | 管理 opencode serve 子进程 |
| `opencode serve` | RUNNING | 执行引擎 API (4096 端口) |

---

## 🚀 后续计划与优先级

### 🔴 紧急 - 专家咨询与指导
**目标**：彻底解决无限循环问题

1. **咨询 OpenCode 专家**
   - 确认 doom_loop 权限的正确配置方式
   - 获取官方推荐的模型和 agent 配置
   - 了解是否有官方的循环检测机制

2. **验证当前修复效果**
   - 运行 `direct_test.py` 测试简单查询
   - 监控 doom_loop 权限事件是否触发
   - 收集完整的 SSE 事件日志

3. **根据专家建议调整**
   - 可能需要修改 agent 配置
   - 可能需要更换模型或调整参数
   - 可能需要重构任务执行流程

### 🟡 重要 - 系统优化
1. **长连接优化**：观察 SSE 在长时间执行下的稳定性
2. **多并发测试**：验证 `asyncio.Lock` 在高负载下的表现
3. **状态同步改进**：增加任务完成后的状态反写逻辑

### 🟢 常规 - 功能增强
1. **任务复杂度评估**：实现自动任务分类和执行策略选择
2. **用户体验改进**：更清晰的进度提示和错误信息
3. **性能监控**：添加执行时间、资源使用监控

---

## 📞 专家快速参考

### 关键配置文件
```bash
# Agent 配置
opencode agent list
opencode agent show build

# 当前使用的 agent
# - 简单查询: build (可能不合适)
# - 复杂任务: build
# - 模式: auto (默认选择 build)
```

### 核心代码位置
```
opencode_client.py:144-226    # Doom Loop 自动拒绝
opencode_client.py:1520-1620   # 智能循环检测
opencode-new-api-patch.js:2167-2242  # 前端 Phase 保护
```

### 需要专家解答的核心问题
1. **为什么 `question.asked` 事件没有触发？**
2. **build agent 的 doom_loop 权限应该如何配置？**
3. **glm-4.7 是否适合作为默认模型？有无替代方案？**
4. **OpenCode 官方如何处理无限循环？**

### 测试复现
```bash
# 最简单的复现方式
curl -X POST http://localhost:8089/opencode/session \
  -H "Content-Type: application/json" \
  -d '{"title": "Test"}'

# 获取 session_id 后
curl -X POST http://localhost:8089/opencode/session/{id}/message \
  -H "Content-Type: application/json" \
  -d '{
    "messageID": "msg_test",
    "mode": "auto",
    "provider_id": "anthropic",
    "model_id": "new-api/glm-4.7",
    "parts": [{"type": "text", "text": "hello"}]
  }'
```

---

## 📋 专家咨询清单

请专家协助确认以下问题（按优先级排序）：

- [ ] **P0**: Doom Loop 权限机制的完整工作流程
- [ ] **P0**: `question.asked` 事件的触发条件和处理方式
- [ ] **P0**: build agent 的正确权限配置方法
- [ ] **P1**: glm-4.7 模型的已知问题和替代方案
- [ ] **P1**: API 调用时推荐配置的参数列表
- [ ] **P1**: 不同任务类型的 agent 选择策略
- [ ] **P2**: OpenCode 官方的无限循环解决方案
- [ ] **P2**: 推荐的最佳实践和配置示例

---

**最后更新**：2026-03-16
**维护者**：等待专家咨询后更新文档
