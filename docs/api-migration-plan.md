# OpenCode 架构迁移计划

**日期**: 2026-02-10
**目标**: 从 CLI 单任务模式迁移到官方 Web API 架构（Session + Message 模式）

---

## 📊 现状分析

### 当前架构（CLI 模式）

```
用户提问 → GET /opencode/run_sse?prompt=xxx
           ↓
         后端调用 opencode run "prompt"
           ↓
         返回 SSE 事件流（单次执行）
           ↓
         前端拼接 prompt 模拟多轮对话
```

**问题**：
1. ❌ 每次执行都是独立的任务，无法追踪历史
2. ❌ 阶段信息（phases）会重置
3. ❌ 无法实现真正的历史回溯
4. ❌ 前端需要拼接 prompt/response
5. ❌ 文件快照存储困难

### 目标架构（官方 Web API 模式）

```
1. POST /session → 创建 session
2. GET /session/{id}/messages → 获取历史消息
3. POST /session/{id}/message → 发送新消息
4. GET /events → SSE 实时事件流
```

**优势**：
1. ✅ 真正的多轮对话支持
2. ✅ 完整的 Message/Part 结构
3. ✅ 支持历史回溯（时间轴）
4. ✅ 文件快照自动管理
5. ✅ 更好的断线重连支持

---

## 🏗️ 新架构设计

### 1. 数据模型

#### Session 表
```python
class Session(BaseModel):
    id: str                    # "ses_abc123"
    title: str                 # 会话标题（自动生成或用户指定）
    version: str               # API 版本
    time: SessionTime
    status: str               # "active" | "idle" | "archived"

class SessionTime(BaseModel):
    created: int              # Unix timestamp
    updated: int              # Unix timestamp
```

#### Message 表
```python
class Message(BaseModel):
    id: str                   # "msg_abc123"
    session_id: str           # Foreign Key to Session
    role: str                 # "user" | "assistant"
    time: MessageTime
    metadata: MessageMetadata # Optional

class MessageTime(BaseModel):
    created: int
    completed: Optional[int]

class MessageMetadata(BaseModel):
    system: Optional[List[str]]
    model_id: Optional[str]
    provider_id: Optional[str]
    path: Optional[WorkspacePath]
    cost: Optional[float]
    tokens: Optional[TokenCount]
```

#### Part 表
```python
class Part(BaseModel):
    id: str                   # "part_xyz789"
    session_id: str           # Foreign Key
    message_id: str           # Foreign Key
    type: PartType            # "text" | "tool" | "file" | "step-start" | "step-finish"
    content: PartContent      # Union type
    time: PartTime

class PartTime(BaseModel):
    start: int
    end: Optional[int]

class PartContent(BaseModel):
    # Text part
    text: Optional[str]

    # Tool part
    tool: Optional[str]
    call_id: Optional[str]
    state: Optional[ToolState]

    # File part
    mime: Optional[str]
    filename: Optional[str]
    url: Optional[str]
```

#### ToolState
```python
class ToolState(BaseModel):
    status: str               # "pending" | "running" | "completed" | "error"
    input: Optional[Dict[str, Any]]
    output: Optional[str]
    error: Optional[str]

class ToolMetadata(BaseModel):
    preview: Optional[str]    # 文件内容预览
    diff: Optional[str]       # Edit 操作的 diff
    title: Optional[str]      # 操作标题
```

#### FileSnapshot（用于历史回溯）
```python
class FileSnapshot(BaseModel):
    id: str
    session_id: str
    file_path: str
    content: str
    operation: str            # "created" | "modified" | "deleted"
    step_id: str              # 关联到对应的 part
    timestamp: int
    checksum: str             # MD5/SHA256
```

### 2. API 端点设计

#### Session 管理
```python
# 创建新 Session
POST /opencode/session
Response: {
    "id": "ses_abc123",
    "title": "New Session",
    "version": "1.0.0",
    "time": {"created": 1640995200, "updated": 1640995200},
    "status": "active"
}

# 获取 Session 信息
GET /opencode/session/{id}
Response: <Session 对象>

# 删除 Session
DELETE /opencode/session/{id}
Response: {"status": "deleted"}
```

#### Message 管理
```python
# 获取消息历史
GET /opencode/session/{id}/messages
Response: {
    "messages": [
        {
            "id": "msg_001",
            "session_id": "ses_abc123",
            "role": "user",
            "time": {"created": 1640995200},
            "parts": [
                {
                    "id": "part_001",
                    "type": "text",
                    "content": {"text": "帮我创建一个Python文件"},
                    "time": {"start": 1640995200}
                }
            ]
        }
    ]
}

# 发送新消息
POST /opencode/session/{id}/message
Request: {
    "message_id": "msg_002",
    "provider_id": "anthropic",
    "model_id": "claude-3-5-sonnet-20241022",
    "mode": "auto",
    "parts": [
        {"type": "text", "text": "再添加一个函数"}
    ]
}
Response: {
    "id": "msg_002",
    "role": "assistant",
    "parts": [...]  # 初始的空消息
}

# 通过 SSE 接收实时更新
GET /opencode/events
Response: SSE 流
```

#### SSE 事件格式
```python
# Message 更新
{
    "type": "message.updated",
    "properties": {
        "info": {
            "id": "msg_002",
            "role": "assistant",
            "time": {"created": 1640995260}
        }
    }
}

# Part 更新（工具状态）
{
    "type": "message.part.updated",
    "properties": {
        "part": {
            "id": "part_tool_001",
            "type": "tool",
            "tool": "write",
            "state": {
                "status": "running",
                "input": {"file_path": "/src/app.py", "content": "..."}
            }
        },
        "session_id": "ses_abc123",
        "message_id": "msg_002"
    }
}

# Part 更新（文本内容）
{
    "type": "message.part.updated",
    "properties": {
        "part": {
            "id": "part_text_001",
            "type": "text",
            "text": "好的，我来添加函数..."
        }
    }
}

# 文件预览（打字机效果）
{
    "type": "preview_delta",
    "properties": {
        "step_id": "step_001",
        "delta": {
            "type": "insert",
            "position": 10,
            "content": "d"
        }
    }
}
```

### 3. 后端架构设计

```python
# ==================== Session Manager ====================
class SessionManager:
    """管理活跃的 OpenCode 会话"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.message_store: MessageStore = MessageStore()

    async def create_session(self) -> Session:
        """创建新会话"""
        session_id = f"ses_{uuid.uuid4().hex[:8]}"
        session = Session(
            id=session_id,
            title="New Session",
            version="1.0.0",
            time=SessionTime(
                created=int(time.time()),
                updated=int(time.time())
            ),
            status="active"
        )
        self.sessions[session_id] = session
        await self.message_store.initialize_session(session_id)
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.sessions.get(session_id)

    async def delete_session(self, session_id: str):
        """删除会话及其所有数据"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            await self.message_store.clear_session(session_id)


# ==================== Message Store ====================
class MessageStore:
    """存储和检索消息历史"""

    def __init__(self):
        # {session_id: {message_id: Message}}
        self.messages: Dict[str, Dict[str, Message]] = {}
        # {session_id: {message_id: {part_id: Part}}}
        self.parts: Dict[str, Dict[str, Dict[str, Part]]] = {}
        # {session_id: [message_id]}  按时间排序
        self.message_order: Dict[str, List[str]] = {}

    async def initialize_session(self, session_id: str):
        """初始化会话存储"""
        self.messages[session_id] = {}
        self.parts[session_id] = {}
        self.message_order[session_id] = []

    async def add_message(self, message: Message) -> Message:
        """添加新消息"""
        session_id = message.session_id
        self.messages[session_id][message.id] = message
        self.message_order[session_id].append(message.id)
        self.parts[session_id][message.id] = {}
        return message

    async def update_message(self, message: Message):
        """更新消息元信息"""
        session_id = message.session_id
        if message.id in self.messages[session_id]:
            self.messages[session_id][message.id] = message

    async def add_part(self, session_id: str, message_id: str, part: Part):
        """添加消息部分"""
        if session_id in self.parts and message_id in self.parts[session_id]:
            self.parts[session_id][message_id][part.id] = part

    async def update_part(self, session_id: str, part: Part):
        """更新消息部分"""
        session_parts = self.parts.get(session_id, {})
        for msg_id, parts in session_parts.items():
            if part.id in parts:
                parts[part.id] = part
                break

    async def get_messages(self, session_id: str) -> List[MessageWithParts]:
        """获取会话的所有消息"""
        messages = []
        for msg_id in self.message_order.get(session_id, []):
            msg = self.messages[session_id][msg_id]
            parts = list(self.parts[session_id][msg_id].values())
            # 按 time.start 排序
            parts.sort(key=lambda p: p.time.start if p.time else 0)
            messages.append(MessageWithParts(info=msg, parts=parts))
        return messages

    async def clear_session(self, session_id: str):
        """清除会话数据"""
        if session_id in self.messages:
            del self.messages[session_id]
        if session_id in self.parts:
            del self.parts[session_id]
        if session_id in self.message_order:
            del self.message_order[session_id]


# ==================== OpenCode Client ====================
class OpenCodeClient:
    """调用 OpenCode CLI 并解析输出"""

    def __init__(self, workspace_base: str):
        self.workspace_base = workspace_base
        self.history_service = get_history_service()

    async def execute_message(
        self,
        session_id: str,
        message: str,
        event_queue: asyncio.Queue
    ):
        """
        执行单条消息（对应 CLI 的一次 run）

        这是关键：我们需要将多次 opencode run 的输出
        组装成一个完整的 Session 对象
        """
        session_dir = os.path.join(self.workspace_base, session_id)
        os.makedirs(session_dir, exist_ok=True)

        # 构建命令
        cmd = [
            "script", "-q", "-c",
            f"opencode run --model new-api/gemini-3-flash-preview --format json --thinking {shlex.quote(message)}",
            "/dev/null"
        ]

        env = {**os.environ}
        env["PATH"] = "/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
        env["FORCE_COLOR"] = "1"
        env["OPENCODE_CONFIG_FILE"] = "/app/opencode/config_host/opencode.json"

        # 启动进程
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=session_dir,
            env=env
        )

        # 解析输出并转换为事件
        current_message_id = None
        current_parts = {}

        async for line in process.stdout:
            decoded = line.decode(errors='ignore').strip()
            if not decoded:
                continue

            # 解析 JSON 事件
            try:
                event = json.loads(decoded) if decoded.startswith("{") else None
                if event:
                    # 转换为 SSE 事件
                    sse_events = await self._convert_to_sse(
                        event, session_id, current_message_id
                    )
                    for sse_event in sse_events:
                        await event_queue.put(sse_event)
            except Exception as e:
                logger.error(f"Error parsing output: {e}")

        await process.wait()

    async def _convert_to_sse(
        self,
        cli_event: dict,
        session_id: str,
        message_id: Optional[str]
    ) -> List[dict]:
        """将 CLI 事件转换为 SSE 事件"""
        events = []
        event_type = cli_event.get("type")

        if event_type == "text":
            # 文本内容 → Part 更新
            part_id = f"part_{uuid.uuid4().hex[:8]}"
            events.append({
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "id": part_id,
                        "type": "text",
                        "text": cli_event.get("part", {}).get("text", ""),
                        "time": {"start": int(time.time())}
                    },
                    "session_id": session_id,
                    "message_id": message_id
                }
            })

        elif event_type == "tool_use":
            # 工具使用 → Part 更新
            part = cli_event.get("part", {})
            tool_name = part.get("tool")
            state = part.get("state", {})

            part_id = f"part_tool_{uuid.uuid4().hex[:8]}"
            events.append({
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "id": part_id,
                        "type": "tool",
                        "tool": tool_name,
                        "call_id": part_id,
                        "state": state,
                        "time": {
                            "start": int(time.time()),
                            "end": int(time.time()) if state.get("status") in ["completed", "error"] else None
                        }
                    },
                    "session_id": session_id,
                    "message_id": message_id
                }
            })

            # 文件操作：生成预览事件
            if tool_name in ["write", "edit", "file_editor"]:
                step_id = f"step_{uuid.uuid4().hex[:8]}"
                file_path = state.get("input", {}).get("file_path", "")
                content = state.get("input", {}).get("content", "")

                # 预览开始
                events.append({
                    "type": "preview_start",
                    "step_id": step_id,
                    "file_path": file_path,
                    "action": "write" if tool_name == "write" else "edit"
                })

                # 打字机效果
                for i, char in enumerate(content):
                    events.append({
                        "type": "preview_delta",
                        "step_id": step_id,
                        "delta": {
                            "type": "insert",
                            "position": i,
                            "content": char
                        }
                    })

                # 预览结束
                events.append({
                    "type": "preview_end",
                    "step_id": step_id,
                    "file_path": file_path
                })

                # 保存快照
                if self.history_service:
                    await self.history_service.capture_file_change(
                        step_id=step_id,
                        file_path=file_path,
                        content=content,
                        operation_type="created" if tool_name == "write" else "modified"
                    )

        return events


# ==================== Event Stream Manager ====================
class EventStreamManager:
    """管理 SSE 事件流广播"""

    def __init__(self):
        # {session_id: Set[asyncio.Queue]}
        self.listeners: Dict[str, Set[asyncio.Queue]] = {}

    async def subscribe(self, session_id: str) -> asyncio.Queue:
        """订阅会话事件"""
        if session_id not in self.listeners:
            self.listeners[session_id] = set()

        queue = asyncio.Queue()
        self.listeners[session_id].add(queue)
        return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        """取消订阅"""
        if session_id in self.listeners:
            self.listeners[session_id].discard(queue)

    async def broadcast(self, session_id: str, event: dict):
        """向会话的所有监听者广播事件"""
        if session_id not in self.listeners:
            return

        event_json = json.dumps(event)
        sse_data = f"data: {event_json}\n\n"

        for queue in list(self.listeners[session_id]):
            try:
                await queue.put(sse_data)
            except Exception as e:
                logger.error(f"Failed to send event: {e}")
                self.listeners[session_id].discard(queue)
```

### 4. FastAPI 端点实现

```python
# 全局管理器
session_manager = SessionManager()
event_stream_manager = EventStreamManager()
opencode_client = OpenCodeClient(workspace_base=WORKSPACE_BASE)


@app.post("/opencode/session")
async def create_session():
    """创建新会话"""
    session = await session_manager.create_session()
    return session


@app.get("/opencode/session/{session_id}")
async def get_session(session_id: str):
    """获取会话信息"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/opencode/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await session_manager.delete_session(session_id)
    return {"status": "deleted"}


@app.get("/opencode/session/{session_id}/messages")
async def get_messages(session_id: str):
    """获取会话的所有消息"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await session_manager.message_store.get_messages(session_id)
    return {"messages": [m.dict() for m in messages]}


@app.post("/opencode/session/{session_id}/message")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks
):
    """
    发送新消息

    流程：
    1. 创建 user message（立即返回）
    2. 创建 assistant message（初始为空）
    3. 后台执行 opencode run
    4. 通过 SSE 推送更新
    """
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. 创建 user message
    user_message_id = f"msg_{uuid.uuid4().hex[:8]}"
    user_message = Message(
        id=user_message_id,
        session_id=session_id,
        role="user",
        time=MessageTime(created=int(time.time()))
    )
    await session_manager.message_store.add_message(user_message)

    # 添加 user text part
    user_part_id = f"part_{uuid.uuid4().hex[:8]}"
    user_text = request.parts[0].text if request.parts else ""
    user_part = Part(
        id=user_part_id,
        session_id=session_id,
        message_id=user_message_id,
        type="text",
        content=PartContent(text=user_text),
        time=PartTime(start=int(time.time()))
    )
    await session_manager.message_store.add_part(session_id, user_message_id, user_part)

    # 2. 创建 assistant message（初始为空）
    assistant_message_id = f"msg_{uuid.uuid4().hex[:8]}"
    assistant_message = Message(
        id=assistant_message_id,
        session_id=session_id,
        role="assistant",
        time=MessageTime(created=int(time.time())),
        metadata=MessageMetadata(
            model_id=request.model_id,
            provider_id=request.provider_id
        )
    )
    await session_manager.message_store.add_message(assistant_message)

    # 3. 发送消息更新事件
    await event_stream_manager.broadcast(session_id, {
        "type": "message.updated",
        "properties": {"info": assistant_message.dict()}
    })

    # 4. 后台执行 opencode run
    background_tasks.add_task(
        execute_opencode_message,
        session_id,
        assistant_message_id,
        user_text
    )

    return assistant_message


async def execute_opencode_message(
    session_id: str,
    message_id: str,
    user_message: str
):
    """
    后台执行 OpenCode 消息

    这是连接 CLI 和新架构的关键
    """
    # 创建事件队列
    event_queue = await event_stream_manager.subscribe(session_id)

    try:
        # 调用 OpenCode CLI
        await opencode_client.execute_message(
            session_id=session_id,
            message=user_message,
            event_queue=event_queue
        )

        # 标记消息完成
        await event_stream_manager.broadcast(session_id, {
            "type": "message.updated",
            "properties": {
                "info": {
                    "id": message_id,
                    "time": {"completed": int(time.time())}
                }
            }
        })
    finally:
        await event_stream_manager.unsubscribe(session_id, event_queue)


@app.get("/opencode/events")
async def events(request: Request):
    """
    SSE 事件流端点

    客户端通过这个端点接收实时更新
    """
    session_id = request.query_params.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    async def event_stream():
        # 订阅会话事件
        queue = await event_stream_manager.subscribe(session_id)

        try:
            # 发送连接成功消息
            yield format_sse({"type": "connection.established", "session_id": session_id})

            # 持续发送事件
            while True:
                try:
                    sse_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield sse_data
                except asyncio.TimeoutError:
                    # 心跳
                    yield format_sse({"type": "ping", "timestamp": int(time.time())})
        except GeneratorExit:
            # 客户端断开
            pass
        finally:
            await event_stream_manager.unsubscribe(session_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## 📝 实施步骤

### 阶段 1：数据模型和管理器（2-3 天）

**文件**: `app/models.py`

**任务**：
1. ✅ 定义所有 Pydantic 模型
2. ✅ 实现 SessionManager
3. ✅ 实现 MessageStore
4. ✅ 编写单元测试

**验证**：
```python
# 测试创建 session
session = await session_manager.create_session()
assert session.id.startswith("ses_")

# 测试添加 message
message = Message(id="msg_001", session_id=session.id, role="user", ...)
await message_store.add_message(message)
messages = await message_store.get_messages(session.id)
assert len(messages) == 1
```

---

### 阶段 2：API 端点实现（2-3 天）

**文件**: `app/api.py`（新建）

**任务**：
1. ✅ 实现 POST /opencode/session
2. ✅ 实现 GET /opencode/session/{id}
3. ✅ 实现 GET /opencode/session/{id}/messages
4. ✅ 实现 POST /opencode/session/{id}/message
5. ✅ 实现 GET /opencode/events（SSE）

**验证**：
```bash
# 创建 session
curl -X POST http://localhost:8088/opencode/session
# Response: {"id": "ses_abc123", ...}

# 发送消息
curl -X POST http://localhost:8088/opencode/session/ses_abc123/message \
  -H "Content-Type: application/json" \
  -d '{"message_id": "msg_001", "model_id": "claude-3-5-sonnet-20241022", "parts": [{"text": "帮我创建一个文件"}]}'
```

---

### 阶段 3：OpenCode Client 实现（2-3 天）

**文件**: `app/opencode_client.py`（新建）

**任务**：
1. ✅ 实现 OpenCodeClient.execute_message()
2. ✅ 实现 CLI 事件到 SSE 事件的转换
3. ✅ 集成 history_service（文件快照）
4. ✅ 处理错误和重试

**验证**：
```python
# 测试执行
events = []
queue = asyncio.Queue()

await opencode_client.execute_message(
    session_id="ses_test",
    message="创建一个test.txt文件",
    event_queue=queue
)

# 验证事件
while not queue.empty():
    event = await queue.get()
    events.append(event)
    assert event["type"] in ["message.part.updated", "preview_delta", "preview_end"]
```

---

### 阶段 4：前端重构（3-5 天）

**文件**:
- `static/opencode.js`
- `static/enhanced-task-panel.js`
- `static/api-client.js`（新建）

**任务**：
1. ✅ 创建新的 API 客户端
2. ✅ 重构 Session 管理
3. ✅ 重构消息存储
4. ✅ 重构事件处理
5. ✅ 更新 UI 渲染逻辑

**关键改动**：
```javascript
// 旧方式
function submitTask() {
    const prompt = el('#prompt-input').value;
    sid = sid || uuid();
    const source = new EventSource(`/opencode/run_sse?prompt=${prompt}&sid=${sid}`);
    // ...
}

// 新方式
async function submitTask() {
    // 1. 创建 session（如果还没有）
    if (!currentSessionId) {
        const session = await apiClient.createSession();
        currentSessionId = session.id;
    }

    // 2. 发送消息
    const message = await apiClient.sendMessage(currentSessionId, {
        message_id: uuid(),
        model_id: "claude-3-5-sonnet-20241022",
        parts: [{text: el('#prompt-input').value}]
    });

    // 3. 订阅事件流
    const eventSource = new EventSource(`/opencode/events?session_id=${currentSessionId}`);
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleEvent(data);
    };
}
```

---

### 阶段 5：写入预览功能（2-3 天）

**任务**：
1. ✅ 后端：打字机效果事件生成
2. ✅ 前端：预览面板渲染
3. ✅ 前端：实时打字机动画
4. ✅ 测试：write/edit/bash/grep

**验证**：
```bash
# 提交任务
echo "创建一个包含100行代码的Python文件"

# 预期行为：
# 1. 右侧预览面板显示文件名
# 2. 内容逐字显示（打字机效果）
# 3. 完成后显示完整文件
```

---

### 阶段 6：历史回溯功能（2-3 天）

**任务**：
1. ✅ 后端：文件快照存储
2. ✅ 后端：timeline API
3. ✅ 前端：timeline 组件
4. ✅ 前端：点击回溯文件内容
5. ✅ 测试：多步骤操作

**验证**：
```bash
# 执行多个操作
1. 创建 file1.txt
2. 编辑 file1.txt
3. 创建 file2.txt
4. 编辑 file1.txt

# 点击 timeline 的第2步
# 预期：显示第2步完成后的 file1.txt 内容
```

---

### 阶段 7：完整测试和优化（2-3 天）

**任务**：
1. ✅ 多轮对话测试
2. ✅ 断线重连测试
3. ✅ 并发请求测试
4. ✅ 性能优化
5. ✅ 错误处理完善
6. ✅ 文档更新

---

## ⚠️ 关键风险和注意事项

### 1. CLI 架构限制

**问题**：OpenCode CLI 本身是单任务执行，不是真正的多轮对话

**解决方案**：
- ✅ 在 CLI 外层自己实现 Session/Message 管理
- ✅ 每次 `opencode run` 作为一条消息执行
- ✅ 通过 history_service 维护上下文

### 2. 内存管理

**问题**：长时间会话会积累大量消息和快照

**解决方案**：
- ✅ 实现消息归档机制
- ✅ 限制单个 session 的快照数量
- ✅ 可选：使用数据库而非内存存储

### 3. 并发控制

**问题**：同一 session 的多个消息可能并发执行

**解决方案**：
- ✅ 实现 session 级别的锁
- ✅ 消息队列化执行
- ✅ 取消正在执行的消息

### 4. 向后兼容

**问题**：现有的 `/opencode/run_sse` 端点可能还在使用

**解决方案**：
- ✅ 保留旧端点一段时间
- ✅ 添加废弃警告
- ✅ 提供迁移指南

---

## 📂 文件结构

```
D:\manus\opencode\
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 主入口（保留旧端点）
│   ├── models.py               # [NEW] Pydantic 模型
│   ├── api.py                  # [NEW] 新 API 端点
│   ├── managers.py             # [NEW] Session/Message 管理器
│   ├── opencode_client.py      # [NEW] OpenCode CLI 客户端
│   ├── events.py               # [NEW] SSE 事件管理
│   └── history_service.py      # [EXIST] 历史追踪服务
├── static/
│   ├── index.html
│   ├── opencode.js             # [MOD] 重构
│   ├── enhanced-task-panel.js  # [MOD] 重构
│   ├── api-client.js           # [NEW] API 客户端
│   └── preview-panel.js        # [NEW] 预览面板
├── docs/
│   └── api-migration-plan.md   # [NEW] 本文档
└── tests/
    ├── test_managers.py        # [NEW]
    ├── test_api.py             # [NEW]
    └── test_client.py          # [NEW]
```

---

## 🚀 预计时间线

| 阶段 | 任务 | 时间 | 依赖 |
|------|------|------|------|
| 1 | 数据模型和管理器 | 2-3 天 | 无 |
| 2 | API 端点实现 | 2-3 天 | 阶段 1 |
| 3 | OpenCode Client | 2-3 天 | 阶段 1 |
| 4 | 前端重构 | 3-5 天 | 阶段 2, 3 |
| 5 | 写入预览 | 2-3 天 | 阶段 4 |
| 6 | 历史回溯 | 2-3 天 | 阶段 5 |
| 7 | 测试和优化 | 2-3 天 | 阶段 6 |
| **总计** | | **15-23 天** | |

---

## ✅ 下一步行动

1. **确认方案**：你是否同意这个架构设计？
2. **开始实施**：我可以立即开始编写代码
3. **分阶段验证**：每完成一个阶段进行测试

**你想现在开始吗？我们从哪个阶段开始？**
