# OpenCode 项目文档

**项目名称**: OpenCode Web Interface
**版本**: v1.0.0 (Migration in Progress)
**最后更新**: 2026-02-10
**当前阶段**: 阶段 2 准备中（阶段 1 已完成）

---

## 📋 目录

- [项目概述](#项目概述)
- [当前产品架构](#当前产品架构)
- [实现方案](#实现方案)
- [已实现的功能](#已实现的功能)
- [遇到过的问题](#遇到过的问题)
- [待解决的问题](#待解决的问题)
- [开发指南](#开发指南)
- [架构迁移进度](#架构迁移进度)

---

## 项目概述

### 项目目标

为 OpenCode CLI 构建一个 Web 界面，支持：
- ✅ 多轮对话（真正的 Session + Message 架构）
- ✅ 实时任务进度显示
- ✅ 文件预览（打字机效果）
- ✅ 历史回溯（时间轴）
- ✅ 断线重连

### 核心技术栈

**后端**:
- FastAPI (Python 3.11+)
- OpenCode CLI (官方命令行工具)
- Pydantic v2 (数据验证)
- SSE (Server-Sent Events)

**前端**:
- Vanilla JavaScript
- Tailwind CSS
- EventSource API (SSE 客户端)

**架构模式**:
- RESTful API + SSE 事件流
- Session + Message + Part 数据模型
- 内存存储（未来可扩展到数据库）

---

## 当前产品架构

### 架构图（迁移中）

```
┌─────────────────────────────────────────────────────────────┐
│                         用户界面                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  输入面板     │  │  任务面板     │  │  预览面板     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      前端 (JavaScript)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ opencode.js  │  │  api-client  │  │  preview.js  │      │
│  │ (旧架构)     │  │  (新架构)    │  │  (待实现)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                       API 层 (FastAPI)                        │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │   旧 API (CLI)    │  │   新 API (Web)   │                 │
│  │  /run_sse        │  │  /session/*      │                 │
│  │  (保留用于回滚)   │  │  (迁移中)        │                 │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      业务逻辑层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │SessionManager│  │ MessageStore │  │OpenCodeClient│      │
│  │ (会话管理)    │  │ (消息存储)   │  │ (CLI 调用)   │      │
│  │  ✅ 已实现    │  │  ✅ 已实现   │  │  ⏳ 待实现   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      数据持久化层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 内存存储      │  │ 文件系统      │  │HistoryService│      │
│  │ (Session/Msg) │  │ (workspace/)  │  │ (文件快照)   │      │
│  │  ✅ 已实现    │  │  ✅ 已实现   │  │  ✅ 已实现   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   OpenCode CLI (外部)                        │
│  $ opencode run --model xxx --format json --thinking "prompt"│
└─────────────────────────────────────────────────────────────┘
```

### 架构说明

#### 旧架构（当前生产环境）

```
用户输入 → GET /opencode/run_sse?prompt=xxx
         → 调用 opencode run "prompt"
         → 返回 SSE 事件流
         → 前端拼接 prompt/response 模拟多轮对话
```

**问题**:
- ❌ 每次执行都是独立任务
- ❌ 无法追踪历史
- ❌ 阶段信息会重置
- ❌ 无法实现真正的历史回溯

#### 新架构（迁移中）

```
1. POST /opencode/session → 创建 Session
2. POST /opencode/session/{id}/message → 发送消息
3. GET /opencode/events → 接收实时更新（SSE）
```

**优势**:
- ✅ 真正的多轮对话
- ✅ 完整的消息历史
- ✅ 文件快照支持
- ✅ 更好的断线重连

---

## 实现方案

### 1. 数据模型设计

#### Session（会话）

```python
class Session(BaseModel):
    id: str                    # "ses_abc123"
    title: str                 # 会话标题
    version: str               # API 版本
    time: SessionTime
    status: SessionStatus      # "active" | "idle" | "archived"
```

#### Message（消息）

```python
class Message(BaseModel):
    id: str                   # "msg_abc123"
    session_id: str           # 所属会话
    role: MessageRole         # "user" | "assistant"
    time: MessageTime
    metadata: Optional[MessageMetadata]
```

#### Part（消息部分）

```python
class Part(BaseModel):
    id: str                   # "part_xyz789"
    session_id: str
    message_id: str
    type: PartType            # "text" | "tool" | "file" | "step-start" | "step-finish"
    content: Optional[PartContent]
    time: PartTime
```

#### FileSnapshot（文件快照）

```python
class FileSnapshot(BaseModel):
    id: str
    session_id: str
    file_path: str
    content: str
    operation: str            # "created" | "modified" | "deleted"
    step_id: str              # 关联的 Part ID
    timestamp: int
    checksum: str
```

**实现文件**: `app/models.py` (732 行)

### 2. 管理器设计

#### SessionManager

**职责**:
- 创建和管理会话
- 维护会话状态
- 提供会话查询接口

**关键方法**:
```python
async def create_session(title: str) -> Session
async def get_session(session_id: str) -> Optional[Session]
async def delete_session(session_id: str) -> bool
async def list_sessions(status: Optional[SessionStatus]) -> List[Session]
```

#### MessageStore

**职责**:
- 存储和检索消息历史
- 管理消息部分（Parts）
- 维护文件快照
- 管理时间轴

**关键方法**:
```python
async def add_message(message: Message) -> Message
async def get_messages(session_id: str) -> List[MessageWithParts]
async def add_part(session_id: str, message_id: str, part: Part) -> Part
async def add_file_snapshot(snapshot: FileSnapshot) -> FileSnapshot
async def get_file_at_step(session_id: str, file_path: str, step_id: str) -> Optional[str]
```

**实现文件**: `app/managers.py` (620 行)

### 3. API 端点设计

#### 新 API 端点（阶段 2 待实现）

```python
# Session 管理
POST   /opencode/session              # 创建会话
GET    /opencode/session/{id}         # 获取会话信息
DELETE /opencode/session/{id}         # 删除会话

# Message 管理
GET    /opencode/session/{id}/messages  # 获取消息历史
POST   /opencode/session/{id}/message   # 发送新消息

# 事件流
GET    /opencode/events              # SSE 事件流
```

#### 旧 API 端点（保留用于回滚）

```python
# CLI 执行端点（保留）
GET    /opencode/run_sse             # 执行 CLI 命令
GET    /opencode/get_log             # 获取日志
GET    /opencode/get_file_content    # 获取文件内容
```

**实现计划**:
- 新旧 API 并行运行
- 通过环境变量控制使用哪个版本
- 旧 API 作为回滚方案保留

### 4. 前端架构

#### 当前前端（旧架构）

**文件结构**:
```
static/
├── index.html                # 主页面
├── opencode.js               # 主逻辑 (SSE 处理, Session 管理)
├── enhanced-task-panel.js    # 任务面板 (阶段显示, 工具事件)
├── tool-icons.js             # 工具图标映射
└── ... (其他辅助文件)
```

**数据流**:
```javascript
// 用户提交任务
function submitTask() {
    const prompt = el('#prompt-input').value;
    sid = sid || uuid();

    // 创建 SSE 连接
    const source = new EventSource(`/opencode/run_sse?prompt=${prompt}&sid=${sid}`);

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleEvent(data);  // 处理各种事件类型
    };
}
```

**问题**:
- Session 管理混乱（sid 为全局变量）
- 消息历史通过拼接 prompt/response 模拟
- 无法支持真正的历史回溯

#### 新前端（阶段 4 待实现）

**文件结构**:
```
static/
├── index.html
├── opencode.js               # 重构为使用新 API
├── api-client.js             # [NEW] API 客户端封装
├── enhanced-task-panel.js    # 重构为适配新数据模型
├── preview-panel.js          # [NEW] 文件预览面板
├── timeline-panel.js         # [NEW] 时间轴面板
└── ...
```

**新的数据流**:
```javascript
// 1. 创建/获取 Session
async function ensureSession() {
    if (!currentSessionId) {
        const session = await apiClient.createSession();
        currentSessionId = session.id;
    }
    return currentSessionId;
}

// 2. 发送消息
async function submitTask() {
    const sessionId = await ensureSession();
    const message = await apiClient.sendMessage(sessionId, {
        message_id: uuid(),
        parts: [{text: el('#prompt-input').value}]
    });

    // 3. 订阅事件流
    const eventSource = new EventSource(`/opencode/events?session_id=${sessionId}`);
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleEvent(data);  // 处理 message.updated, message.part.updated 等
    };
}
```

### 5. 文件快照机制

#### 目标

支持"点击时间轴查看文件在某个时刻的内容"

#### 实现

**后端** (`app/managers.py`):
```python
async def add_file_snapshot(snapshot: FileSnapshot) -> FileSnapshot:
    """每次 write/edit 操作时保存快照"""
    self.file_snapshots[session_id].append(snapshot)

async def get_file_at_step(session_id: str, file_path: str, target_step_id: str) -> Optional[str]:
    """获取文件在指定步骤时刻的内容"""
    snapshots = await self.get_file_snapshots(session_id, file_path)
    for snapshot in snapshots:
        if snapshot.step_id == target_step_id:
            return snapshot.content
    return None
```

**前端**（待实现）:
```javascript
// 点击时间轴步骤
async function onTimelineStepClick(stepId) {
    const filePath = currentPreviewFile;

    // 获取该步骤时刻的文件内容
    const content = await apiClient.getFileAtStep(currentSessionId, filePath, stepId);

    // 显示在预览面板
    renderPreview(content);
}
```

### 6. SSE 事件流设计

#### 事件类型

```javascript
// 1. 连接建立
{"type": "connection.established", "session_id": "ses_abc123"}

// 2. 消息更新
{"type": "message.updated", "properties": {"info": {...}}}

// 3. 部分更新（工具状态）
{"type": "message.part.updated", "properties": {
    "part": {
        "type": "tool",
        "tool": "write",
        "state": {"status": "running", ...}
    }
}}

// 4. 部分更新（文本内容）
{"type": "message.part.updated", "properties": {
    "part": {
        "type": "text",
        "text": "好的，我来创建..."
    }
}}

// 5. 文件预览（打字机效果）
{"type": "preview_start", "step_id": "step_001", "file_path": "/test/file.txt"}
{"type": "preview_delta", "step_id": "step_001", "delta": {"content": "H", "position": 0}}
{"type": "preview_delta", "step_id": "step_001", "delta": {"content": "e", "position": 1}}
{"type": "preview_end", "step_id": "step_001", "file_path": "/test/file.txt"}

// 6. 心跳
{"type": "ping", "timestamp": 1234567890}
```

---

## 已实现的功能

### ✅ 阶段 0: 现有功能（生产环境）

#### 1. 基础任务执行
- [x] 提交任务到 OpenCode CLI
- [x] 实时显示任务进度
- [x] 显示工具调用事件（read, write, bash, grep 等）
- [x] 显示 AI 思考过程（reasoning tokens）
- [x] 显示最终回复

#### 2. 任务面板
- [x] 阶段进度显示（Planning → Phase 1 → Phase 2 → ... → Summary）
- [x] 工具图标映射（tool-icons.js）
- [x] 工具状态追踪（pending → running → completed/error）
- [x] 文件列表展示

#### 3. 多轮对话（前端模拟）
- [x] 支持追问
- [x] 问答对显示（Q1 → A1, Q2 → A2）
- [x] 阶段信息显示

**文件**:
- `app/main.py` - 旧 API 实现
- `static/opencode.js` - 前端主逻辑
- `static/enhanced-task-panel.js` - 任务面板

#### 4. 历史追踪
- [x] HistoryService 实现（文件快照存储）
- [x] 捕获 write/edit/bash 操作
- [x] 文件变更记录

**文件**:
- `app/history_service.py`

#### 5. SSE 缓冲问题解决
- [x] 使用 `script` 命令伪造 TTY
- [x] 强制无缓冲输出
- [x] Silent ping 机制（15秒心跳）

**解决方案**:
```python
cmd = ["script", "-q", "-c",
    f"opencode run --model xxx --format json --thinking {prompt}",
    "/dev/null"]
```

### ✅ 阶段 1: 新架构基础（已完成）

#### 1. 数据模型
- [x] Pydantic 模型定义
- [x] Session, Message, Part, FileSnapshot, TimelineStep
- [x] 枚举类型和辅助函数

**文件**: `app/models.py` (732 行)

#### 2. 管理器
- [x] SessionManager 实现
- [x] MessageStore 实现
- [x] 文件快照存储
- [x] 时间轴管理

**文件**: `app/managers.py` (620 行)

#### 3. 测试框架
- [x] 单元测试框架
- [x] SessionManager 测试（8 个）
- [x] MessageStore 测试（7 个）
- [x] 集成测试（1 个）

**文件**: `tests/test_managers.py` (350 行)

#### 4. 文档和备份
- [x] 架构迁移计划 (`docs/api-migration-plan.md`)
- [x] 备份回滚方案 (`docs/backup-rollback-plan.md`)
- [x] 阶段总结 (`docs/phase1-summary.md`)
- [x] 自动备份脚本 (`scripts/backup.sh`)
- [x] 备份执行 (`backups/20260210_005707/`)
- [x] Git 提交和标签 (`2fbccdf`, `phase1-models-complete`)

---

## 遇到过的问题

### 问题 1: SSE 缓冲导致输出不实时

**症状**:
- OpenCode CLI 的输出被缓冲
- 前端无法实时看到进度
- 所有输出在任务结束后一次性显示

**根本原因**:
- Python 的 subprocess 默认使用缓冲
- OpenCode CLI 检测到非 TTY 环境，启用块缓冲

**解决方案**:
```python
# 使用 script 命令伪造 TTY
cmd = ["script", "-q", "-c",
    f"opencode run --format json --thinking {shlex.quote(prompt)}",
    "/dev/null"]
```

**效果**:
- ✅ 输出实时显示
- ✅ 打字机效果流畅

**文件**: `app/main.py` (line 270-282)

---

### 问题 2: 多轮对话显示混乱

**症状**:
- 追问后，问题显示顺序错误（Q1, Q2, phases, A1, A2）
- 回复重复显示
- 阶段信息位置不对

**根本原因**:
- 前端通过 `---` 分隔符拼接 prompt/response
- 解析逻辑有缺陷
- 没有考虑问题和回复数量不匹配的情况

**解决方案**:
```javascript
// enhanced-task-panel.js (v16)
const questionCount = conversation.questions.length;
const responseCount = conversation.responses.length;
const hasNewQuestionWithoutAnswer = questionCount > responseCount;

if (hasNewQuestionWithoutAnswer) {
    // Q1 → A1, ..., Qn → 阶段（新问题还没有回答）
    // ...
} else {
    // Q1 → A1, ..., Qn → 阶段 → An（多轮完成）
    // ...
}
```

**效果**:
- ✅ 正确显示 Q1 → A1, Q2 → phases → A2
- ✅ 支持有新问题但还没有回答的情况

**文件**: `static/enhanced-task-panel.js` (v16, line 20-131)

---

### 问题 3: phase_planning 状态卡住

**症状**:
- `phase_planning` 一直显示为 `active`
- 即使动态阶段（phase_1, phase_2）已开始执行

**根本原因**:
- 后端发送两次 `phases_init`
- 第一次：`phase_planning` (active)
- 第二次：`phase_1`, `phase_2`, `phase_3`, `phase_summary`
- 但后端从未发送 `phase_update` 将 `phase_planning` 标记为 completed

**解决方案**:
```javascript
// opencode.js (v21, line 1278-1285)
const hasDynamicPhases = s.phases.some(p =>
    p.id?.startsWith('phase_1') ||
    p.id?.startsWith('phase_2') ||
    p.id?.startsWith('phase_3')
);
const planningPhase = s.phases.find(p => p.id === 'phase_planning');

if (hasDynamicPhases && planningPhase && planningPhase.status === 'active') {
    planningPhase.status = 'completed';
}
```

**效果**:
- ✅ `phase_planning` 自动标记为 completed
- ✅ 动态阶段正确显示为 active

---

### 问题 4: 追问时重复添加分隔符

**症状**:
- 每次追问都自动添加 `\n\n---\n\n**新的回答：**\n\n`
- 即使还没有新的回答内容
- 导致显示空白的回答卡片

**根本原因**:
- 在 `submitTask` 时立即添加分隔符
- 但实际新回答还未开始生成

**解决方案**:
```javascript
// opencode.js (v20, line 1163-1179)
// 移除立即添加分隔符的逻辑

// opencode.js (v20, line 1355-1367)
// 在 answer_chunk 事件中智能检测
const promptSeparatorCount = (s.prompt.match(/\n\n---\n\n/g) || []).length;
const responseSeparatorCount = (s.response.match(/\n\n---\n\n\*\*新的回答：\*\*\n\n/g) || []).length;

if (promptSeparatorCount > responseSeparatorCount) {
    s.response += '\n\n---\n\n**新的回答：**\n\n';
}
```

**效果**:
- ✅ 只有在有新回答时才添加分隔符
- ✅ 避免空白回答卡片

---

### 问题 5: 单元测试导入错误

**症状**:
```
ImportError: attempted relative import with no known parent package
```

**根本原因**:
- `app/managers.py` 使用相对导入 `from .models import ...`
- 测试环境直接运行时，Python 不认识包结构

**解决方案**:
```python
# app/managers.py (line 11-28)
try:
    # 相对导入（作为包使用）
    from .models import ...
except ImportError:
    # 绝对导入（测试环境）
    from models import ...
```

**效果**:
- ✅ 既支持包导入，也支持直接运行
- ✅ 测试和生产环境都能正常工作

---

## 待解决的问题

### ⏳ 问题 1: 单元测试运行超时

**症状**:
- `pytest tests/test_managers.py` 运行超时
- 可能是 logging 或导入导致死锁

**优先级**: 中
**下一步**:
- [ ] 调试超时原因
- [ ] 简化测试代码
- [ ] 确保测试可以快速运行

---

### ⏳ 问题 2: CLI 架固有限制

**症状**:
- OpenCode CLI 本身是单任务执行
- 每次调用都是独立的
- 无法在 CLI 层面支持真正的多轮对话

**影响**:
- 需要在 CLI 外层自己实现 Session/Message 管理
- 每次 `opencode run` 作为一条消息执行

**解决方案**:
- 通过 OpenCodeClient 封装 CLI 调用
- 维护 context 在应用层（而非 CLI 层）
- 多次 `opencode run` 的输出组装成完整 Session

**优先级**: 高
**阶段**: 阶段 3（OpenCode Client）

---

### ⏳ 问题 3: 内存管理

**症状**:
- 长时间会话会积累大量消息和快照
- 可能导致内存溢出

**临时方案**:
- 限制单个 session 的快照数量
- 定期归档旧消息

**长期方案**:
- 使用数据库存储（PostgreSQL/MongoDB）
- 实现消息分页加载
- 实现快照压缩

**优先级**: 中
**阶段**: 阶段 7（优化）

---

### ⏳ 问题 4: 并发控制

**症状**:
- 同一 session 的多个消息可能并发执行
- OpenCode CLI 不支持并发执行同一 session

**临时方案**:
- 实现 session 级别的锁
- 消息队列化执行

**实现**:
```python
class SessionLock:
    def __init__(self):
        self.locks: Dict[str, asyncio.Lock] = {}

    async def acquire(self, session_id: str):
        if session_id not in self.locks:
            self.locks[session_id] = asyncio.Lock()
        await self.locks[session_id].acquire()

    async def release(self, session_id: str):
        self.locks[session_id].release()
```

**优先级**: 高
**阶段**: 阶段 2（API 端点）

---

### ⏳ 问题 5: 前端大规模重构

**症状**:
- 需要重构现有前端代码以适配新 API
- 涉及多个文件
- 可能引入新的 Bug

**风险控制**:
- 新旧 API 并行运行
- 通过功能开关切换
- 完整的测试覆盖

**优先级**: 高
**阶段**: 阶段 4（前端重构）

---

## 开发指南

### 环境设置

```bash
# 1. 克隆仓库
git clone <repository-url>
cd opencode

# 2. 安装依赖
pip install fastapi uvicorn pydantic pytest pytest-asyncio

# 3. 启动服务（旧 API）
uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload

# 4. 访问
open http://localhost:8088
```

### 运行测试

```bash
# 单元测试
pytest tests/test_managers.py -v

# 快速测试
python tests/quick_test.py
```

### 备份和恢复

```bash
# 创建备份
bash scripts/backup.sh

# 恢复备份
cp -r backups/20260210_005707/app/* app/
cp -r backups/20260210_005707/static/* static/
```

### Git 工作流

```bash
# 查看当前分支和标签
git branch
git tag -l "phase*"

# 切换到阶段 1 的代码
git checkout phase1-models-complete

# 回滚到迁移前
git checkout phase1-models-complete~1

# 查看提交历史
git log --oneline -10
```

### 开发新功能

1. **创建新分支**（可选）
   ```bash
   git checkout -b feature/new-api
   ```

2. **编写代码**
   - 遵循现有代码风格
   - 添加类型注解
   - 编写测试

3. **本地测试**
   ```bash
   pytest tests/ -v
   ```

4. **提交代码**
   ```bash
   git add .
   git commit -m "feat: description"
   ```

5. **创建标签**（阶段完成时）
   ```bash
   git tag -a phase2-api-complete -m "Phase 2: API endpoints complete"
   ```

### 代码规范

#### Python
- 使用 Pydantic v2 语法
- 添加类型注解
- 编写 Docstring
- 遵循 PEP 8

```python
async def create_session(
    self,
    title: str = "New Session",
    version: str = "1.0.0"
) -> Session:
    """
    创建新会话

    Args:
        title: 会话标题
        version: API 版本

    Returns:
        创建的会话对象
    """
    ...
```

#### JavaScript
- 使用 Vanilla JS（不使用框架）
- 使用模板字符串
- 添加 JSDoc 注释

```javascript
/**
 * 创建新会话
 * @returns {Promise<Session>} 会话对象
 */
async function createSession() {
    const response = await fetch('/opencode/session', {
        method: 'POST'
    });
    return await response.json();
}
```

---

## 架构迁移进度

### 阶段概览

| 阶段 | 内容 | 状态 | 时间 | Git Tag |
|------|------|------|------|---------|
| 0 | 现有功能（生产环境） | ✅ 完成 | - | - |
| 1 | 数据模型和管理器 | ✅ 完成 | 2-3 天 | `phase1-models-complete` |
| 2 | API 端点实现 | ⏳ 待开始 | 2-3 天 | - |
| 3 | OpenCode Client | ⏳ 待开始 | 2-3 天 | - |
| 4 | 前端重构 | ⏳ 待开始 | 3-5 天 | - |
| 5 | 写入预览 | ⏳ 待开始 | 2-3 天 | - |
| 6 | 历史回溯 | ⏳ 待开始 | 2-3 天 | - |
| 7 | 完整测试 | ⏳ 待开始 | 2-3 天 | - |
| **总计** | | | **15-23 天** | |

### 详细进度

#### ✅ 阶段 0: 现有功能（生产环境）

**完成内容**:
- [x] 基础任务执行
- [x] SSE 实时事件流
- [x] 任务面板和阶段显示
- [x] 多轮对话（前端模拟）
- [x] 工具图标映射
- [x] HistoryService 实现
- [x] SSE 缓冲问题解决

**文件**:
- `app/main.py`
- `app/history_service.py`
- `static/opencode.js`
- `static/enhanced-task-panel.js`
- `static/tool-icons.js`

---

#### ✅ 阶段 1: 数据模型和管理器（已完成）

**完成内容**:
- [x] Pydantic 模型定义 (`app/models.py`)
- [x] SessionManager 实现 (`app/managers.py`)
- [x] MessageStore 实现 (`app/managers.py`)
- [x] 单元测试框架 (`tests/test_managers.py`)
- [x] 架构设计文档 (`docs/api-migration-plan.md`)
- [x] 备份回滚方案 (`docs/backup-rollback-plan.md`)
- [x] 自动备份脚本 (`scripts/backup.sh`)
- [x] 备份执行 (`backups/20260210_005707/`)
- [x] Git 提交和标签

**代码量**: ~2,900 行（模型 + 管理器 + 测试 + 文档）

**Git Tag**: `phase1-models-complete`

**下一步**: 阶段 2 - API 端点实现

---

#### ⏳ 阶段 2: API 端点实现（待开始）

**计划内容**:
- [ ] 创建 `app/api.py`
- [ ] 实现 Session 管理端点
  - [ ] POST /opencode/session
  - [ ] GET /opencode/session/{id}
  - [ ] DELETE /opencode/session/{id}
- [ ] 实现 Message 管理端点
  - [ ] GET /opencode/session/{id}/messages
  - [ ] POST /opencode/session/{id}/message
- [ ] 实现 SSE 事件流
  - [ ] GET /opencode/events
- [ ] 集成 SessionManager
- [ ] 添加错误处理
- [ ] 编写 API 测试
- [ ] Git commit

**预计时间**: 2-3 天

**依赖**: 阶段 1 完成 ✅

---

#### ⏳ 阶段 3: OpenCode Client（待开始）

**计划内容**:
- [ ] 创建 `app/opencode_client.py`
- [ ] 实现 CLI 调用封装
  - [ ] execute_message()
  - [ ] 进程管理
  - [ ] 输出解析
- [ ] 实现事件转换
  - [ ] CLI 事件 → SSE 事件
  - [ ] 文件预览事件生成
  - [ ] 打字机效果
- [ ] 集成 HistoryService
- [ ] 编写 Client 测试
- [ ] Git commit

**预计时间**: 2-3 天

**依赖**: 阶段 1 完成 ✅

---

#### ⏳ 阶段 4: 前端重构（待开始）

**计划内容**:
- [ ] 创建 `static/api-client.js`
- [ ] 重构 `static/opencode.js`
  - [ ] Session 管理
  - [ ] 消息发送
  - [ ] 事件处理
- [ ] 重构 `static/enhanced-task-panel.js`
  - [ ] 适配新数据模型
  - [ ] MessageWithParts 渲染
  - [ ] 阶段显示优化
- [ ] 测试新前端
- [ ] Git commit

**预计时间**: 3-5 天

**依赖**: 阶段 2, 3 完成 ✅

---

#### ⏳ 阶段 5: 写入预览功能（待开始）

**计划内容**:
- [ ] 后端：打字机事件生成
  - [ ] preview_start 事件
  - [ ] preview_delta 事件
  - [ ] preview_end 事件
- [ ] 前端：预览面板实现
  - [ ] 创建 `static/preview-panel.js`
  - [ ] 文件内容渲染
  - [ ] 打字机动画
  - [ ] 语法高亮
- [ ] 测试 write/edit/bash/grep
- [ ] Git commit

**预计时间**: 2-3 天

**依赖**: 阶段 4 完成 ✅

---

#### ⏳ 阶段 6: 历史回溯功能（待开始）

**计划内容**:
- [ ] 后端：时间轴 API
  - [ ] GET /opencode/session/{id}/timeline
  - [ ] GET /opencode/file_at_step
- [ ] 前端：时间轴组件
  - [ ] 创建 `static/timeline-panel.js`
  - [ ] 步骤列表显示
  - [ ] 点击事件处理
- [ ] 文件内容回溯
  - [ ] 获取历史快照
  - [ ] 显示在预览面板
- [ ] 测试多步骤操作
- [ ] Git commit

**预计时间**: 2-3 天

**依赖**: 阶段 5 完成 ✅

---

#### ⏳ 阶段 7: 完整测试（待开始）

**计划内容**:
- [ ] 多轮对话测试
  - [ ] 3-5 轮连续对话
  - [ ] 消息顺序验证
  - [ ] 阶段显示验证
- [ ] 断线重连测试
  - [ ] SSE 断开
  - [ ] 自动重连
  - [ ] 状态恢复
- [ ] 并发请求测试
  - [ ] 多个用户同时操作
  - [ ] 同一 session 并发消息
- [ ] 性能优化
  - [ ] 内存使用
  - [ ] 响应时间
  - [ ] 数据库迁移（可选）
- [ ] 错误处理完善
- [ ] 文档更新
- [ ] Git commit

**预计时间**: 2-3 天

**依赖**: 阶段 6 完成 ✅

---

## 附录

### A. 文件结构

```
D:\manus\opencode\
├── app/                          # 后端应用
│   ├── __init__.py              # 包初始化
│   ├── main.py                  # FastAPI 主入口（旧 API）
│   ├── models.py                # [NEW] Pydantic 数据模型
│   ├── managers.py              # [NEW] SessionManager + MessageStore
│   ├── history_service.py       # 历史追踪服务
│   └── opencode_client.py       # [TODO] OpenCode CLI 客户端
│
├── static/                       # 前端静态文件
│   ├── index.html               # 主页面
│   ├── opencode.js              # 主逻辑（待重构）
│   ├── enhanced-task-panel.js   # 任务面板（待重构）
│   ├── tool-icons.js            # 工具图标映射
│   ├── api-client.js            # [TODO] API 客户端
│   ├── preview-panel.js         # [TODO] 预览面板
│   └── timeline-panel.js        # [TODO] 时间轴面板
│
├── tests/                        # 测试文件
│   ├── test_managers.py         # 管理器测试
│   └── quick_test.py            # 快速测试脚本
│
├── docs/                         # 文档
│   ├── api-migration-plan.md    # 架构迁移计划
│   ├── backup-rollback-plan.md  # 备份回滚方案
│   ├── phase1-summary.md        # 阶段 1 总结
│   └── CLAUDE.md                # 本文档
│
├── scripts/                      # 脚本
│   └── backup.sh                # 自动备份脚本
│
├── backups/                      # 备份目录
│   └── 20260210_005707/         # 阶段 1 备份
│
├── workspace/                    # OpenCode 工作区
│
├── CLAUDE.md                     # 本文档
├── HANDOVER.md                   # 项目交接文档
└── README.md                     # 项目说明
```

### B. 关键配置

#### OpenCode CLI 配置

**文件**: `/app/opencode/config_host/opencode.json`

```json
{
  "models": [
    {
      "id": "new-api/gemini-3-flash-preview",
      "provider_id": "new-api",
      "name": "Gemini 3 Flash"
    }
  ],
  "default_model": "new-api/gemini-3-flash-preview"
}
```

#### FastAPI 配置

**启动命令**:
```bash
# 开发环境
uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload

# 生产环境
uvicorn app.main:app --host 0.0.0.0 --port 8088 --workers 4
```

### C. 常用命令

```bash
# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8088

# 运行测试
pytest tests/ -v

# 创建备份
bash scripts/backup.sh

# 查看 Git 日志
git log --oneline -10

# 查看标签
git tag -l "phase*"

# 切换到指定标签
git checkout phase1-models-complete

# 查看文件修改
git diff app/main.py
```

### D. 联系方式

- **项目仓库**: [GitHub URL]
- **问题追踪**: [Issues URL]
- **文档**: `docs/` 目录

---

**最后更新**: 2026-02-10
**维护者**: OpenCode Team
**状态**: 架构迁移进行中（阶段 1 已完成，阶段 2 准备中）
