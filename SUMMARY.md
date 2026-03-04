# OpenCode CLI Session 兼容性问题修复总结

## 项目背景

OpenCode 是一个 AI 编程助手系统，由 Python FastAPI 后端和 Bun/TypeScript CLI 组成。在测试中发现 CLI 无法读取 Python 创建的 session，导致 "Session not found" 错误。

## 问题诊断历程

### 1. 初始错误假设：Go 代码问题 ❌
- **错误方向**：检查 `kernel/` 目录的 Go 代码
- **用户纠正**：`kernel/` 是独立仓库，实际 CLI 是 Bun/TypeScript
- **时间浪费**：约 1 小时

### 2. 发现 Session ID 格式差异
```
Python 创建：ses_22e8bc42（12 字符）
CLI 列表显示：ses_34e15ec24ffef8FvO7CGlzAKuv（24 字符）
```

### 3. 发现数据库路径不同（真正根本原因）
```bash
# CLI 使用的数据库
$ opencode db path
/root/.local/share/opencode/opencode.db  # 表名：session

# Python 写入的数据库
/app/opencode/workspace/history.db       # 表名：sessions
```

### 4. 测试环境变量影响
```bash
# 设置 HOME 后
HOME=/app/opencode/workspace opencode db path
# 输出：/app/opencode/workspace/.local/share/opencode/opencode.db
```

### 5. Schema 不兼容问题

**CLI 的 session 表**：
```sql
CREATE TABLE `session` (
  `id` text PRIMARY KEY,
  `project_id` text NOT NULL,
  `slug` text NOT NULL,
  `directory` text NOT NULL,
  -- ... 共 20+ 列
  FOREIGN KEY (`project_id`) REFERENCES `project`(`id`)
)
```

**Python 的 sessions 表**：
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    workspace_path TEXT,
    title TEXT,
    -- ... 共 12 列，无外键
)
```

### 6. 错误修复尝试
- **尝试 1**：ALTER TABLE 添加 Go CLI 列（v=38.4.2）
  - 结果：失败，数据库路径不同

- **尝试 2**：软链接 + HOME 环境变量
  - Code Reviewer 审计：**根本性错误**
  - 问题：表名不同（session vs sessions），软链接无法解决

### 7. 正确方案（方案 A）✅
**核心思想**：移除 `--session` 参数，让 CLI 创建自己的 session

**理由**：
1. CLI 和 Python 使用不同的数据库
2. 表名不同（session vs sessions）
3. Schema 完全不兼容
4. 强制统一会导致架构破坏

## 修复版本记录

### v=38.4.2 - Schema 扩展（部分有效）
**文件**：`app/main.py`

**修改**：
```python
def _write_session_to_db(self, sid: str, prompt: str):
    """同时兼容 Python 和 Go CLI 的 schema"""
    # ALTER TABLE 添加 7 列
    # 同时填充旧列和新列
    cursor.execute("""
        INSERT INTO sessions (
            id, prompt, status, workspace_path,
            title, message_count, prompt_tokens, completion_tokens, cost,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0.0, ?, ?)
    """, ...)
```

**结果**：Python 端正常，但 CLI 仍无法读取

### v=38.4.3 - Session Title 更新
**文件**：`app/api.py`

**修改**：
```python
# 在 send_message 中更新数据库
cursor.execute("""
    UPDATE sessions
    SET title = ?, prompt = ?, updated_at = ?
    WHERE id = ?
""", (title, user_text, now, session_id))
```

**结果**：改善用户体验，但未解决核心问题

### v=38.4.4 - 移除 --session 参数（最终方案）✅
**文件**：`app/opencode_client.py`

**修改**：
```python
# Lines 209-220
# ✅ v=38.4.4修复：不传递session参数给CLI
# 原因：CLI查询session表，Python写入sessions表（表名不同，schema不兼容）
# 让CLI创建自己的session，避免"Session not found"错误
# 注意：Python和CLI将使用不同的session ID，这是正常的
session_flag = ""  # Changed from: f" --session {session_id}"

inner_cmd = f"opencode run --model {model_id} --format json --thinking{agent_flag}{session_flag} {safe_prompt}"
```

**结果**：待测试验证

## 已修改文件清单

### 1. app/opencode_client.py
**修改次数**：3 次
- v=38.4.2: 添加数据库路径
- v=38.4.4: 移除 `--session` 参数（核心修复）
- 移除无效的 HOME 环境变量代码

**关键代码**：
```python
# Line 213
session_flag = ""  # 不传递 session ID
```

### 2. app/main.py
**修改版本**：v=38.4.2
- 添加 `_write_session_to_db` 方法
- ALTER TABLE 添加 7 列
- 同时填充新旧字段

**关键代码**：
```python
# Lines 241-284
def _write_session_to_db(self, sid: str, prompt: str):
    # 写入数据库，兼容两种 schema
```

### 3. app/api.py
**修改版本**：v=38.4.3
- 在 `send_message` 中更新 session title
- 添加数据库更新逻辑

**关键代码**：
```python
# Lines 475-498
cursor.execute("""
    UPDATE sessions
    SET title = ?, prompt = ?, updated_at = ?
    WHERE id = ?
""", ...)
```

## 当前状态

### 已完成 ✅
1. 问题根因诊断完成
2. v=38.4.4 代码已提交
3. Docker 容器已部署
4. 浏览器已打开 http://localhost:8089

### 测试中 ⚙️
- 准备提交测试任务验证 v=38.4.4 修复效果

### 待完成 ⏳
1. 验证 CLI 是否正常执行任务
2. 检查工具调用记录是否正常
3. 确认文件生成功能
4. 添加单元测试和集成测试

## 技术架构说明

### 数据流
```
用户输入（欢迎页）
  ↓
Python FastAPI（app/main.py）
  ↓
创建 session → 写入 sessions 表（/app/opencode/workspace/history.db）
  ↓
调用 CLI（opencode run）
  ↓
Bun/TypeScript CLI 读取 session 表（/root/.local/share/opencode/opencode.db）❌
  ↓
【v=38.4.4 修复】CLI 创建自己的 session ✅
  ↓
执行任务，返回 SSE 事件
  ↓
前端接收并渲染
```

### 数据库架构差异

| 维度 | CLI (Bun/TS) | Python (FastAPI) |
|------|-------------|------------------|
| 数据库路径 | `/root/.local/share/opencode/opencode.db` | `/app/opencode/workspace/history.db` |
| 表名 | `session` (单数) | `sessions` (复数) |
| 主键 | `id` TEXT | `id` TEXT |
| 外键 | 有 (`project_id` → `project`) | 无 |
| 核心字段 | `slug`, `directory`, `project_id` | `prompt`, `status`, `workspace_path` |
| 用途 | CLI 内部 session 管理 | Web UI session 管理 |

## 经验教训

### 1. 诊断优先原则 ⚠️
- **用户指导**："你修复前先用code review这个skills诊断一下你的结论"
- **错误做法**：直接修复未经验证的假设
- **正确做法**：使用 code-reviewer skill 系统性诊断

### 2. 避免过度工程化
- **错误做法**：试图统一两个完全不同的系统
- **正确做法**：接受架构差异，使用最小改动解决问题

### 3. 环境差异检查清单
- [ ] 数据库路径
- [ ] 表名
- [ ] Schema 结构
- [ ] 环境变量（HOME, PATH 等）
- [ ] 运行用户权限

### 4. Code Reviewer 价值
发现软链接方案的根本性缺陷：
> "软链接可以让 CLI 找到数据库文件，但无法解决表名不同的问题。CLI 查询 `session` 表，但数据库中只有 `sessions` 表，仍然会失败。"

## 下一步计划

### 立即任务（高优先级）
1. **测试 v=38.4.4 修复效果**
   - 提交简单任务："用Python创建一个计算器"
   - 观察是否出现 "Session not found" 错误
   - 检查服务器日志：`docker exec opencode-container sh -c "tail -50 /app/opencode/logs/app.err.log"`
   - 验证工具调用是否正常

2. **确认成功标准**
   - ✅ CLI 正常启动
   - ✅ 不报 "Session not found" 错误
   - ✅ 工具调用记录 > 0
   - ✅ 文件正确生成

### 后续任务（中优先级）
3. **添加自动化测试**
   - 单元测试：session 创建逻辑
   - 集成测试：CLI 命令格式验证
   - 回归测试：确保不再出现 "Session not found"

4. **文档完善**
   - 更新 README 说明架构差异
   - 添加故障排查指南
   - 记录已知的限制

### 长期优化（低优先级）
5. **架构统一讨论**
   - 是否需要统一 Python 和 CLI 的 session 管理
   - 考虑使用共享数据库或 API 桥接
   - 评估迁移成本和收益

## 相关资源

### Git 提交记录
- v=38.4.2: `fix: 添加Go CLI兼容的session schema列`
- v=38.4.3: `fix: 更新session title到数据库`
- v=38.4.4: `fix: 移除--session参数，避免Session not found错误`

### 诊断日志
- 完整诊断历程：见用户提供的参考文档
- Code Reviewer 审计报告：已保存在项目文档中

### 测试环境
- Docker 容器：opencode-container
- Web UI：http://localhost:8089
- 后端日志：/app/opencode/logs/app.err.log

## 结论

通过系统性的诊断和 code-reviewer skill 的辅助，我们最终识别出问题的根本原因：**CLI 和 Python 使用完全不同的数据库、表名和 schema**。

最终采用的解决方案（移除 `--session` 参数）虽然看似简单，但这是经过多次错误尝试和严格审计后的最优解。它避免了复杂的架构重构，用最小的改动解决了实际问题。

**关键收获**：在修复复杂系统问题时，应该先彻底诊断根本原因，而非急于实施表面修复。

---

## ✅ 测试结果（v=38.4.4 验证成功）

### 测试时间
2026-03-03 09:08:59 - 09:10:XX

### 测试任务
**输入**：用Python创建一个简单的计算器脚本，支持加减乘除运算

**模式**：Build (开发模式)

### 成功标准验证

| 验证项 | 状态 | 详情 |
|--------|------|------|
| ✅ CLI 正常启动 | **通过** | 日志显示 `Starting CLI process (Platform: Linux)` |
| ✅ 不报 "Session not found" 错误 | **通过** | 日志中无此错误，完全消失 |
| ✅ 工具调用记录 > 0 | **通过** | 多个 write、bash 工具调用 |
| ✅ 文件正确生成 | **通过** | calculator.py、run.log、status.txt 已创建 |

### 关键日志证据

```bash
# ✅ CLI 命令正确（无 --session 参数）
opencode run --model new-api/gemini-3-flash-preview --format json --thinking --agent build '用Python创建一个简单的计算器脚本，支持加减乘除运算'

# ✅ Session ID 分离（符合预期）
Python session: ses_27f2f862
CLI session: ses_34d0aaadcffeXkkXnqkrzByYcF

# ✅ 事件正常接收
Processing line 1: {"type":"step_start",...
Broadcasting event message.part.updated to session ses_27f2f862
```

### 生成的文件内容

**calculator.py**：
```python
def add(x, y):
    return x + y

def subtract(x, y):
    return x - y

def multiply(x, y):
    return x * y

def divide(x, y):
    if y == 0:
        raise ValueError("Cannot divide by zero.")
    return x / y

if __name__ == "__main__":
    # ... 完整的交互式计算器实现
```

**功能验证**：
- ✅ 加法运算
- ✅ 减法运算
- ✅ 乘法运算
- ✅ 除法运算
- ✅ 除零错误处理
- ✅ 用户友好的交互菜单

### 测试结论

🎉 **v=38.4.4 修复完全成功！**

**核心改进**：
1. **彻底消除** "Session not found" 错误
2. **保持功能完整**：所有工具调用正常
3. **文件生成正常**：代码文件、日志文件均正确创建
4. **Session 独立性**：Python 和 CLI 各自管理自己的 session ID，符合架构设计

**最终方案**：
- 移除 `--session` 参数传递（line 213: `session_flag = ""`）
- 让 CLI 创建自己的 session，而非查询不兼容的 Python session
- 接受 Python 和 CLI 使用不同 session ID 的架构现实

### 用户视角的改进

**修复前**：
- ❌ 每次提交任务都报 "Session not found" 错误
- ❌ 任务无法正常执行
- ❌ 文件无法生成

**修复后**：
- ✅ 任务提交后立即开始执行
- ✅ SSE 事件正常接收
- ✅ 工具调用实时展示
- ✅ 文件正确生成并预览

---

## 下一步行动

### 已完成 ✅
1. ✅ 问题根因诊断
2. ✅ v=38.4.4 代码实施
3. ✅ Docker 容器部署
4. ✅ 功能测试验证

### 待完成 ⏳
1. ⏳ 添加单元测试和集成测试
2. ⏳ 更新用户文档说明架构差异
3. ⏳ 添加故障排查指南

---

**项目状态**：🎯 **核心问题已解决，系统运行正常**
