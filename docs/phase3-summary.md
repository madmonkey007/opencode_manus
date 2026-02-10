# 阶段 3 完成总结

**日期**: 2026-02-10
**状态**: ✅ 完成
**Git 标签**: `phase3-client-complete`
**前序**: `phase2-api-complete`

---

## ✅ 已完成的工作

### 1. OpenCode Client 实现

**文件**: `app/opencode_client.py` (606 行)

#### 1.1 核心类：OpenCodeClient

```python
class OpenCodeClient:
    """
    OpenCode CLI 客户端

    职责：
    1. 调用 opencode run CLI 命令
    2. 解析 JSON 输出
    3. 转换为 SSE 事件
    4. 广播到 EventStreamManager
    5. 生成文件预览事件
    """

    def __init__(self, workspace_base: str):
        """初始化客户端"""
        self.workspace_base = workspace_base
        self.history_service = get_history_service()

    async def execute_message(
        self,
        session_id: str,
        assistant_message_id: str,
        user_prompt: str,
        model_id: str = "new-api/gemini-3-flash-preview"
    ):
        """执行单条消息（调用 CLI 并广播事件）"""
```

**关键功能**:
- ✅ 创建会话目录
- ✅ 构建 CLI 命令（使用 `script` 伪造 TTY）
- ✅ 启动异步子进程
- ✅ 实时解析 stdout
- ✅ 写入日志文件
- ✅ 生成状态文件
- ✅ 发送完成事件

#### 1.2 事件处理方法

```python
async def _process_line(
    self, text: str, session_id: str, message_id: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """处理单行输出，生成 SSE 事件"""

async def _handle_text_event(...) -> AsyncGenerator[Dict[str, Any], None]:
    """处理 text 事件"""

async def _handle_tool_use_event(...) -> AsyncGenerator[Dict[str, Any], None]:
    """处理 tool_use 事件"""

async def _handle_step_start_event(...) -> AsyncGenerator[Dict[str, Any], None]:
    """处理 step_start 事件"""

async def _handle_step_finish_event(...) -> AsyncGenerator[Dict[str, Any], None]:
    """处理 step_finish 事件"""

def _handle_error_event(...) -> Dict[str, Any]:
    """处理 error 事件"""
```

**支持的事件类型**:
- ✅ `text` - 文本内容
- ✅ `tool_use` - 工具调用
- ✅ `step_start` - 步骤开始
- ✅ `step_finish` - 步骤完成
- ✅ `error` - 错误信息
- ✅ Thought（非 JSON 行）

#### 1.3 文件预览功能（打字机效果）

```python
async def _handle_file_operation(
    self,
    session_id: str,
    message_id: str,
    tool_name: str,
    input_data: Dict[str, Any],
    status: str
):
    """
    处理文件操作，生成预览事件

    流程：
    1. 发送 preview_start 事件
    2. 逐字符发送 preview_delta 事件（5ms 间隔）
    3. 发送 preview_end 事件
    4. 保存文件快照到 history_service
    5. 发送 timeline_update 事件
    """
```

**生成的预览事件**:
```python
# 1. 预览开始
{"type": "preview_start", "step_id": "step_xxx", "file_path": "/path/to/file", "action": "write"}

# 2. 预览增量（逐字符）
{"type": "preview_delta", "step_id": "step_xxx", "delta": {"type": "insert", "position": 0, "content": "H"}}
{"type": "preview_delta", "step_id": "step_xxx", "delta": {"type": "insert", "position": 1, "content": "e"}}
{"type": "preview_delta", "step_id": "step_xxx", "delta": {"type": "insert", "position": 2, "content": "l"}}
{"type": "preview_delta", "step_id": "step_xxx", "delta": {"type": "insert", "position": 3, "content": "l"}}
{"type": "preview_delta", "step_id": "step_xxx", "delta": {"type": "insert", "position": 4, "content": "o"}}
...

# 3. 预览结束
{"type": "preview_end", "step_id": "step_xxx", "file_path": "/path/to/file"}

# 4. 时间轴更新
{"type": "timeline_update", "step": {"step_id": "step_xxx", "action": "write", "path": "/path/to/file", ...}}
```

#### 1.4 工具类型映射

```python
def map_tool_to_type(tool_name: str) -> str:
    """映射内部工具名称到前端显示类型"""
```

**支持的映射**:
- `read_file` → `read`
- `write` / `save` / `create` → `write`
- `bash` / `sh` / `shell` → `bash`
- `terminal` / `command` / `cmd` / `run` → `terminal`
- `grep` / `search` → `grep`
- `browser` / `click` / `visit` / `scroll` → `browser`
- `web` / `google` → `web_search`
- `edit` / `replace` → `file_editor`

---

### 2. API 集成

**文件**: `app/api.py` (修改)

#### 2.1 修改内容

```python
# 添加 os 模块导入
import os

# 在 send_message 端点中集成 OpenCode Client
@router.post("/session/{session_id}/message", response_model=SendMessageResponse)
async def send_message(...):
    # ... 前面的代码 ...

    # 3. 发送消息更新事件（通过 SSE 广播）
    await broadcast_message_update(session_id, assistant_message)

    # 4. 后台执行 OpenCode CLI 任务
    workspace_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../workspace"))
    background_tasks.add_task(
        execute_opencode_message,
        session_id,
        assistant_message_id,
        user_text,
        workspace_base
    )

    return SendMessageResponse(...)
```

**关键变更**:
- ✅ 添加 `os` 模块导入
- ✅ 在创建 assistant message 后广播更新事件
- ✅ 使用 `BackgroundTasks` 异步执行 OpenCode CLI
- ✅ 计算正确的 workspace_base 路径

#### 2.2 辅助函数

```python
async def execute_opencode_message(
    session_id: str,
    message_id: str,
    user_prompt: str,
    workspace_base: str
):
    """
    后台执行 OpenCode 消息的入口函数

    创建 OpenCodeClient 实例并调用 execute_message()
    """
```

---

### 3. 测试脚本

**文件**: `tests/test_opencode_client.py` (250+ 行)

#### 3.1 测试覆盖

```python
async def test_client_basic():
    """测试 OpenCodeClient 基本功能"""
    # - 创建会话
    # - 初始化客户端
    # - 订阅事件流
    # - 执行消息
    # - 验证事件广播

async def test_api_send_message():
    """测试 API send_message 端点集成"""
    # - 创建会话
    # - 订阅事件流
    # - 构建 SendMessageRequest
    # - 调用 execute_opencode_message
    # - 验证事件接收

async def test_event_stream_manager():
    """测试 EventStreamManager 功能"""
    # - 创建多个订阅者
    # - 广播测试事件
    # - 验证所有订阅者都收到事件
    # - 验证取消订阅
```

#### 3.2 验证脚本

**文件**: `tests/verify_client.py` (完整验证)
**文件**: `tests/quick_verify_client.py` (快速验证)

**验证内容**:
- ✅ OpenCodeClient 导入
- ✅ API 模块导入
- ✅ Client 初始化
- ✅ 工具类型映射
- ✅ EventStreamManager 基本功能

---

## 📊 代码统计

| 文件 | 行数 | 说明 |
|------|------|------|
| `app/opencode_client.py` | 606 | OpenCode Client 实现 |
| `app/api.py` (修改) | ~10 | 添加 os 导入，集成 Client |
| `tests/test_opencode_client.py` | 250 | 集成测试 |
| `tests/verify_client.py` | 100 | 完整验证脚本 |
| `tests/quick_verify_client.py` | 50 | 快速验证脚本 |
| **阶段 3 新增** | **~1,016** | |

---

## 🎯 关键成就

### 1. 完整的 CLI 桥接

✅ 封装 OpenCode CLI 调用
✅ 解析 JSON 输出
✅ 转换为 SSE 事件
✅ 广播到 EventStreamManager
✅ 错误处理和日志记录

### 2. 文件预览功能

✅ 打字机效果（5ms/字符）
✅ 逐字符推送
✅ 文件快照保存
✅ 时间轴更新

### 3. 事件转换

✅ text 事件
✅ tool_use 事件
✅ step_start/step_finish 事件
✅ Thought 识别
✅ error 事件

### 4. 集成测试

✅ 基本导入测试
✅ Client 初始化测试
✅ 工具映射测试
✅ EventStreamManager 测试

---

## 🔄 与阶段 2 的集成

| 阶段 2 (API) | 阶段 3 (Client) | 集成点 |
|--------------|----------------|--------|
| `POST /session/{id}/message` | `execute_opencode_message()` | BackgroundTasks |
| `EventStreamManager` | `_broadcast_event()` | 事件广播 |
| `SendMessageRequest` | `user_prompt` | 请求参数 |
| `SessionManager` | `session_id` | 会话管理 |

**集成流程**:
```
1. 前端发送 POST /session/{id}/message
   ↓
2. API 创建 user message 和 assistant message
   ↓
3. API 广播 message.updated 事件
   ↓
4. API 启动后台任务 execute_opencode_message()
   ↓
5. OpenCodeClient.execute_message() 调用 CLI
   ↓
6. CLI 输出通过 _process_line() 转换为事件
   ↓
7. 事件通过 EventStreamManager.broadcast() 广播
   ↓
8. SSE 客户端接收实时事件流
```

---

## ⚠️ 限制和注意事项

### 1. CLI 依赖

**要求**: 系统必须安装 `opencode` CLI 工具

**验证**:
```bash
which opencode  # Unix
where opencode  # Windows
```

### 2. 环境变量

**关键环境变量**:
```python
env = {
    "PATH": "/root/.bun/bin:/usr/local/bin:/...",
    "FORCE_COLOR": "1",
    "OPENCODE_CONFIG_FILE": "/app/opencode/config_host/opencode.json"
}
```

**注意**: Windows 环境需要调整 PATH

### 3. script 命令

**用途**: 伪造 TTY 以禁用缓冲

**限制**: Windows 不支持 `script` 命令

**替代方案**:
- Windows: 使用 `winpty` 或 Python `pty` (需要额外安装)
- Docker: Linux 环境原生支持

### 4. History Service

**当前状态**: 可选依赖

**行为**:
- 如果 `get_history_service()` 成功：保存文件快照
- 如果失败：仅记录警告，不影响主流程

### 5. 并发控制

**当前状态**: 未实现 Session 锁

**风险**: 同一 session 可能并发执行多条消息

**临时方案**: 前端避免并发发送

**计划**: 阶段 4/5 实现 Session 锁

---

## 🚀 使用示例

### 基本使用

```python
from app.opencode_client import OpenCodeClient

# 创建客户端
client = OpenCodeClient(workspace_base="/path/to/workspace")

# 执行消息
await client.execute_message(
    session_id="ses_abc123",
    assistant_message_id="msg_xyz789",
    user_prompt="Create a Python file",
    model_id="new-api/gemini-3-flash-preview"
)
```

### 订阅事件

```python
from app.api import event_stream_manager
import json

# 订阅会话事件
queue = await event_stream_manager.subscribe("ses_abc123")

# 接收事件
while True:
    event_str = await queue.get()
    event = json.loads(event_str)
    print(f"Event: {event['type']}")

# 取消订阅
await event_stream_manager.unsubscribe("ses_abc123", queue)
```

### 完整流程

```python
import asyncio
from app.api import session_manager, event_stream_manager
from app.opencode_client import execute_opencode_message

async def main():
    # 1. 创建会话
    session = await session_manager.create_session("Test Session")

    # 2. 订阅事件
    queue = await event_stream_manager.subscribe(session.id)

    # 3. 后台执行消息
    asyncio.create_task(
        execute_opencode_message(
            session_id=session.id,
            message_id="msg_test",
            user_prompt="Say hello",
            workspace_base="/path/to/workspace"
        )
    )

    # 4. 接收事件
    for _ in range(10):
        event_str = await queue.get()
        event = json.loads(event_str)
        print(f"Received: {event['type']}")

    # 5. 清理
    await event_stream_manager.unsubscribe(session.id, queue)
    await session_manager.delete_session(session.id)

asyncio.run(main())
```

---

## 📝 待办事项（进入阶段 4）

### 立即任务

1. **前端 API 客户端** (`static/api-client.js`)
   - 封装新 API 调用
   - SSE 事件处理
   - 自动重连机制

2. **前端重构** (`static/opencode.js`)
   - 适配 Session + Message 架构
   - 移除旧的 CLI 模拟逻辑
   - 实现真正的多轮对话

3. **任务面板更新** (`static/enhanced-task-panel.js`)
   - 适配新的事件格式
   - 文件预览渲染
   - 时间轴交互

### 下一步计划

**阶段 4**: 前端重构
- 时间: 3-5 天
- 任务:
  - 创建 `static/api-client.js`
  - 重构 `static/opencode.js`
  - 重构 `static/enhanced-task-panel.js`
  - 实现文件预览 UI
  - 实现时间轴 UI

**阶段 5**: 文件预览优化
- 时间: 1-2 天
- 任务:
  - 优化打字机效果性能
  - 添加语法高亮
  - 添加 diff 视图

**阶段 6**: 历史回溯
- 时间: 2-3 天
- 任务:
  - 实现时间轴点击事件
  - 获取文件快照
  - 显示历史版本

**阶段 7**: 完整测试
- 时间: 2-3 天
- 任务:
  - 端到端测试
  - 性能优化
  - 文档完善

---

## 🎓 经验总结

### 成功经验

1. **模块化设计**
   - Client 独立于 API
   - 事件处理器独立
   - 易于测试和维护

2. **异步编程**
   - 使用 asyncio.create_subprocess_exec
   - 异步生成器模式
   - 非阻塞事件处理

3. **错误处理**
   - 优雅降级（history_service）
   - 详细的日志记录
   - 异常传播

4. **测试策略**
   - 快速验证脚本
   - 集成测试
   - 分层测试

### 遇到的挑战

1. **CLI 输出解析**
   - 问题: 混合 JSON 和非 JSON 行
   - 解决: 智能检测，分别处理

2. **TTY 伪造**
   - 问题: Python subprocess 缓冲输出
   - 解决: 使用 `script -q -c` 命令

3. **Windows 兼容性**
   - 问题: Windows 不支持 `script` 命令
   - 解决: 记录在文档中，计划后续支持

4. **事件广播**
   - 问题: 如何将 CLI 事件转换为 SSE
   - 解决: 统一的事件格式和 _process_line() 方法

---

## 📚 相关文档

- **架构设计**: `docs/api-migration-plan.md`
- **阶段 1 总结**: `docs/phase1-summary.md`
- **阶段 2 总结**: `docs/phase2-summary.md`
- **备份方案**: `docs/backup-rollback-plan.md`
- **项目文档**: `CLAUDE.md`

---

## ✅ 验收清单

- [x] OpenCodeClient 类实现
- [x] execute_message() 方法
- [x] 事件处理方法（text, tool_use, step_start, step_finish, error）
- [x] 文件预览功能（打字机效果）
- [x] 工具类型映射
- [x] API 集成（send_message 端点）
- [x] execute_opencode_message() 辅助函数
- [x] 测试脚本编写
- [x] 快速验证通过
- [x] 代码提交
- [x] Git 标签创建
- [x] 文档更新

---

**阶段 3 状态**: ✅ 完成
**下一阶段**: 阶段 4 - 前端重构
**总进度**: 3/7 阶段完成（~43%）

---

**最后更新**: 2026-02-10
**维护者**: OpenCode Team
