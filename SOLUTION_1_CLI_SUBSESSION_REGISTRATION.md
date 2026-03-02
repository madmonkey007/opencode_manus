# Solution 1: CLI在后端注册子session - 实现方案

## 📋 方案概述

**目标**: CLI创建子session时，自动在Web后端的session_manager中注册，使前端可以正常订阅SSE事件流。

**核心思想**: 统一session管理机制，让CLI和Web API共享同一个session_manager。

---

## 🏗️ 架构设计

### 当前架构（问题）

```
┌─────────────────────────────────────────────────────────────┐
│                    Web后端 (FastAPI)                         │
│                                                              │
│  session_manager (内存)                                      │
│    └─ ses_main (通过API创建) ✅                             │
│                                                              │
│  GET /opencode/events?session_id=ses_child ❌ 404 (不在内存) │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    CLI (Python)                              │
│                                                              │
│  主代理使用task工具                                          │
│    └─ 创建子session (ses_child)                              │
│         └─ ❌ 不在Web后端的session_manager中                  │
└─────────────────────────────────────────────────────────────┘
```

### 目标架构（解决方案）

```
┌─────────────────────────────────────────────────────────────┐
│                    Web后端 (FastAPI)                         │
│                                                              │
│  session_manager (内存)                                      │
│    └─ ses_main (通过API创建) ✅                             │
│    └─ ses_child (CLI注册) ✅ ← 新增                         │
│                                                              │
│  GET /opencode/events?session_id=ses_child ✅ 返回SSE        │
└─────────────────────────────────────────────────────────────┘
          ↑                                               ↓
          │ CLI调用API注册                            前端订阅成功
          │
┌─────────────────────────────────────────────────────────────┐
│                    CLI (Python)                              │
│                                                              │
│  主代理使用task工具                                          │
│    └─ 创建子session (ses_child)                              │
│         └─ ✅ 调用POST /opencode/session注册                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 实现方案

### 方案A: HTTP API调用（推荐）⭐

**实现方式**: CLI通过HTTP调用Web API注册子session

#### 代码实现

```python
# app/main.py

import httpx
import asyncio
from typing import Optional
import os

# Web API基础URL（从环境变量读取）
WEB_API_URL = os.getenv("WEB_API_URL", "http://localhost:8089")

async def register_subsession_with_web_backend(
    parent_session_id: str,
    child_session_id: str,
    mode: str = "auto"
) -> Optional[dict]:
    """
    将CLI创建的子session注册到Web后端

    Args:
        parent_session_id: 主session ID
        child_session_id: 子session ID
        mode: 执行模式

    Returns:
        注册后的session对象，失败返回None
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{WEB_API_URL}/opencode/session",
                json={
                    "id": child_session_id,  # 使用CLI生成的ID
                    "title": f"Subsession of {parent_session_id}",
                    "mode": mode,
                    "version": "1.0.0",
                    "parent_session_id": parent_session_id  # 标记父session
                }
            )

            if response.status_code == 200:
                session = response.json()
                logger.info(f"✅ Registered child session with Web backend: {child_session_id}")
                return session
            else:
                logger.error(f"❌ Failed to register child session: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"❌ Error registering child session: {e}")
        return None


# 修改原有的task工具实现
async def execute_task_tool(
    session_id: str,
    agent_type: str,
    prompt: str
) -> str:
    """
    执行task工具，创建子代理

    Returns:
        子session的ID
    """
    # 1. 生成子session ID
    child_session_id = f"ses_{generate_unique_id()}"

    # 2. 创建子workspace目录 ✅
    child_workspace = os.path.join(WORKSPACE_BASE, child_session_id)
    os.makedirs(child_workspace, exist_ok=True)

    # 3. ✅ NEW: 注册到Web后端
    registered_session = await register_subsession_with_web_backend(
        parent_session_id=session_id,
        child_session_id=child_session_id,
        mode="auto"
    )

    if not registered_session:
        logger.warning(f"⚠️ Failed to register child session, continuing anyway...")

    # 4. 创建子代理并执行任务
    # ... 原有的子代理创建逻辑 ...

    return f"task_id: {child_session_id}\n\nSubagent created successfully."
```

#### Web API修改

```python
# app/api.py

@app.post("/opencode/session")
async def create_session(
    id: Optional[str] = None,  # ✅ 新增：允许指定session ID
    title: str = "New Session",
    mode: str = "auto",
    version: str = "1.0.0",
    parent_session_id: Optional[str] = None  # ✅ 新增：父session ID
):
    """
    创建新会话（支持CLI注册子session）

    Args:
        id: 可选的session ID（CLI提供）
        title: 会话标题
        mode: 执行模式
        version: API版本
        parent_session_id: 父session ID（如果是子session）
    """
    try:
        # 使用提供的ID或自动生成
        session_id = id or f"ses_{generate_id()}"

        # 创建session对象
        session = await session_manager.create_session(
            session_id=session_id,  # ✅ 使用指定的ID
            title=title,
            version=version
        )

        # 如果是子session，建立父子关系
        if parent_session_id:
            session.parent_id = parent_session_id
            logger.info(f"Registered child session: {session_id} <- {parent_session_id}")

        # 创建workspace目录
        from app.main import WORKSPACE_BASE
        session_dir = os.path.join(WORKSPACE_BASE, session_id)
        os.makedirs(session_dir, exist_ok=True)

        return session

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 优点

✅ **解耦**: CLI和Web后端通过HTTP通信，不共享内存
✅ **灵活性**: CLI和Web后端可以在不同进程/机器上运行
✅ **标准**: 使用标准的RESTful API
✅ **易测试**: 可以mock HTTP客户端进行单元测试

#### 缺点

⚠️ **网络依赖**: 依赖HTTP通信，可能有网络延迟
⚠️ **错误处理**: 需要处理网络错误、超时等

---

### 方案B: 直接调用session_manager（替代方案）

**实现方式**: CLI直接调用session_manager的内存方法

#### 代码实现

```python
# app/main.py

from app.managers import session_manager  # 导入共享的session_manager

async def execute_task_tool(
    session_id: str,
    agent_type: str,
    prompt: str
) -> str:
    """
    执行task工具，创建子代理
    """
    # 1. 生成子session ID
    child_session_id = f"ses_{generate_unique_id()}"

    # 2. ✅ NEW: 直接在session_manager中注册
    session = await session_manager.create_session(
        session_id=child_session_id,
        title=f"Subsession of {session_id}",
        version="1.0.0"
    )

    # 3. 建立父子关系
    session.parent_id = session_id

    # 4. 创建workspace目录
    child_workspace = os.path.join(WORKSPACE_BASE, child_session_id)
    os.makedirs(child_workspace, exist_ok=True)

    # 5. 创建子代理并执行任务
    # ... 原有的子代理创建逻辑 ...

    return f"task_id: {child_session_id}\n\nSubagent created successfully."
```

#### 优点

✅ **简单**: 直接调用，无需HTTP通信
✅ **快速**: 无网络延迟
✅ **可靠**: 无网络错误风险

#### 缺点

❌ **耦合**: CLI和Web后端必须在同一进程
❌ **限制**: 无法分布式部署
❌ **架构**: 违反了微服务解耦原则

---

## 🎯 推荐方案：方案A（HTTP API）⭐

### 选择理由

1. ✅ **解耦**: CLI和Web后端独立运行
2. ✅ **可扩展**: 未来可以分布式部署
3. ✅ **标准化**: 使用RESTful API
4. ✅ **容错**: Web后端重启不影响CLI

---

## 📝 实施步骤

### 第1步：修改Web API（30分钟）

**文件**: `app/api.py`

**修改内容**:
1. `create_session`函数添加`id`和`parent_session_id`参数
2. 支持使用CLI提供的session ID
3. 记录父子关系

### 第2步：CLI实现注册函数（1小时）

**文件**: `app/main.py`

**新增内容**:
1. `register_subsession_with_web_backend`函数
2. 修改`execute_task_tool`函数
3. 调用注册API

### 第3步：错误处理和日志（30分钟）

**新增内容**:
1. HTTP请求失败时的降级处理
2. 详细的日志记录
3. 重试机制（可选）

### 第4步：测试验证（1小时）

**测试场景**:
1. ✅ CLI创建子session
2. ✅ 后端session_manager中有记录
3. ✅ workspace目录存在
4. ✅ 前端SSE订阅成功
5. ✅ 子session事件正常显示

---

## 🧪 测试方案

### 单元测试

```python
# tests/test_cli_subsession.py

import pytest
from app.main import register_subsession_with_web_backend

@pytest.mark.asyncio
async def test_register_subsession_success(mocker):
    """测试成功注册子session"""
    # Mock HTTP客户端
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "ses_test123",
        "title": "Subsession of ses_main"
    }

    mocker.patch("httpx.AsyncClient", return_value=mocker.AsyncClient())

    # 测试注册
    result = await register_subsession_with_web_backend(
        parent_session_id="ses_main",
        child_session_id="ses_test123"
    )

    assert result is not None
    assert result["id"] == "ses_test123"

@pytest.mark.asyncio
async def test_register_subsession_failure(mocker):
    """测试注册失败时的处理"""
    # Mock HTTP错误
    mocker.patch("httpx.AsyncClient", side_effect=Exception("Network error"))

    # 测试注册失败
    result = await register_subsession_with_web_backend(
        parent_session_id="ses_main",
        child_session_id="ses_test123"
    )

    assert result is None
```

### 集成测试

```python
# tests/test_subsession_integration.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_cli_creates_subsession_and_frontend_subscribes():
    """测试完整流程：CLI创建子session → 前端订阅"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 创建主session
        main_session = await client.post("/opencode/session", json={
            "title": "Main session"
        })
        main_session_id = main_session.json()["id"]

        # 2. 模拟CLI创建子session（通过API）
        child_session = await client.post("/opencode/session", json={
            "id": "ses_child123",
            "title": "Subsession of ses_main",
            "parent_session_id": main_session_id
        })
        assert child_session.status_code == 200

        # 3. 验证前端可以订阅子session
        events_response = await client.get(
            f"/opencode/events?session_id=ses_child123"
        )
        assert events_response.status_code == 200  # ✅ 不再是404
```

### 手动测试

```bash
# 1. 启动Web后端
uvicorn app.main:app --reload

# 2. 提交一个使用task工具的任务
# 3. 观察控制台日志：
#    ✅ "Registered child session with Web backend: ses_xxx"
# 4. 观察前端：
#    ✅ SSE订阅成功
#    ✅ 子session事件正常显示
```

---

## 📊 风险评估

### 技术风险

| 风险                | 可能性 | 影响  | 缓解措施                     |
| ------------------- | ------ | ----- | ---------------------------- |
| HTTP请求失败        | 中     | 中     | 重试机制 + 降级处理          |
| Web后端不可用       | 低     | 高     | 优雅降级：继续执行，记录日志 |
| Session ID冲突      | 低     | 低     | API返回409，CLI生成新ID      |
| 性能影响（延迟）    | 低     | 低     | 异步调用，不阻塞主流程       |

### 业务风险

| 风险                | 可能性 | 影响  | 缓解措施                     |
| ------------------- | ------ | ----- | ---------------------------- |
| 现有功能破坏        | 低     | 高     | 完整的回归测试              |
| 用户体验受影响      | 低     | 中     | 灰度发布 + 监控             |

---

## ✅ 成功标准

### 功能标准

- [ ] CLI创建子session时自动在Web后端注册
- [ ] 前端SSE订阅子session不再返回404
- [ ] 子session事件正常显示在右侧面板
- [ ] workspace目录正确创建

### 性能标准

- [ ] 注册请求延迟 < 100ms
- [ ] 不影响主session的性能
- [ ] 内存增长 < 5MB per子session

### 稳定性标准

- [ ] HTTP请求失败时不影响CLI正常执行
- [ ] Web后端重启不影响已注册的session
- [ ] 错误日志完整且有用

---

## 📝 回滚计划

如果实施后出现问题：

1. **立即回滚**:
   ```bash
   git revert <commit_hash>
   ```

2. **临时方案**:
   - 启用Solution 3（后端虚拟session）
   - 前端优雅降级（隐藏404错误）

3. **数据恢复**:
   - session在内存中，重启后自动清空
   - 无需特殊恢复操作

---

## 📅 时间估算

| 阶段           | 时间   | 负责人    |
| -------------- | ------ | --------- |
| Web API修改    | 30分钟 | 后端开发  |
| CLI实现        | 1小时  | 后端开发  |
| 测试           | 1小时  | QA        |
| Code Review    | 30分钟 | 团队      |
| 部署上线       | 30分钟 | DevOps    |
| **总计**       | **3.5小时** |    |

---

## 🎯 后续优化

### Phase 2（可选）

1. **性能优化**
   - 批量注册多个子session
   - 缓存session_manager状态

2. **监控**
   - 添加metrics（注册成功率、延迟等）
   - 告警（注册失败率 > 5%）

3. **高可用**
   - Web后端多实例部署
   - 负载均衡

---

**方案状态**: ✅ 设计完成
**待Code Review**: 是
**批准后实施**: 是

---

**作者**: AI Solution Designer
**日期**: 2026-03-02
**版本**: 1.0
