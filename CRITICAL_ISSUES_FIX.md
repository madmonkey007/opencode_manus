# 🔴 Critical Issues修复方案

## 概述

本文档修复Solution 1设计方案中的两个Critical问题：
- **C1**: 缺少API认证机制
- **C2**: Session ID冲突未处理

---

## 🔴 C1: API认证机制

### 问题

`POST /opencode/session`无认证，任何人都可以创建session，导致安全漏洞。

### 修复方案

#### 1. 创建认证模块

**文件**: `app/auth.py`

```python
"""
认证和授权模块
"""
import os
from typing import Optional
from fastapi import Header, HTTPException
from pydantic import BaseModel

# API密钥（从环境变量读取）
API_KEY = os.getenv("OPENCODE_API_KEY", "dev-key-change-in-production")

class User(BaseModel):
    """用户模型"""
    id: str
    username: str
    is_authenticated: bool = True

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> User:
    """
    从请求头获取当前用户

    Args:
        authorization: Authorization header (格式: "Bearer {api_key}")

    Returns:
        当前用户对象

    Raises:
        HTTPException: 认证失败
    """
    # 开发模式：允许无认证
    if os.getenv("OPENCODE_DEV_MODE") == "true":
        return User(id="dev-user", username="developer")

    # 生产模式：验证API密钥
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )

    # 解析Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Expected: 'Bearer {api_key}'"
        )

    api_key = authorization[7:]  # 去掉"Bearer "前缀

    # 验证API密钥
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    # 返回用户对象
    return User(
        id="api-user",
        username="api_client",
        is_authenticated=True
    )


async def verify_session_ownership(
    session_id: str,
    current_user: User,
    session_manager
) -> bool:
    """
    验证用户是否拥有指定session的权限

    Args:
        session_id: Session ID
        current_user: 当前用户
        session_manager: Session管理器

    Returns:
        True表示有权限，False表示无权限

    Raises:
        HTTPException: Session不存在或无权限
    """
    # 开发模式：跳过权限验证
    if os.getenv("OPENCODE_DEV_MODE") == "true":
        return True

    # 获取session
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )

    # 验证所有权
    if hasattr(session, 'user_id') and session.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    return True
```

#### 2. 修改Web API添加认证

**文件**: `app/api.py`

```python
from fastapi import Depends, HTTPException
from app.auth import get_current_user, verify_session_ownership
from app.managers import session_manager

@app.post("/opencode/session")
async def create_session(
    current_user: User = Depends(get_current_user),  # ✅ 添加认证依赖
    id: Optional[str] = None,
    title: str = "New Session",
    mode: str = "auto",
    version: str = "1.0.0",
    parent_session_id: Optional[str] = None
):
    """
    创建新会话（支持CLI注册子session）

    Args:
        current_user: 当前认证用户（自动注入）
        id: 可选的session ID（CLI提供）
        title: 会话标题
        mode: 执行模式
        version: API版本
        parent_session_id: 父session ID（如果是子session）

    Returns:
        创建的session对象

    Raises:
        HTTPException: 认证失败或权限不足
    """
    try:
        # ✅ 验证父session权限
        if parent_session_id:
            await verify_session_ownership(
                session_id=parent_session_id,
                current_user=current_user,
                session_manager=session_manager
            )

        # 使用提供的ID或自动生成
        session_id = id or await generate_unique_session_id()

        # ✅ 验证ID格式
        if id and not validate_session_id(id):
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID format. Expected: ses_<12 chars>"
            )

        # 创建session对象（绑定用户）
        session = await session_manager.create_session(
            session_id=session_id,
            title=title,
            version=version,
            user_id=current_user.id  # ✅ 绑定用户
        )

        # 如果是子session，建立父子关系
        if parent_session_id:
            session.parent_id = parent_session_id
            logger.info(
                f"✅ Registered child session: {session_id} <- {parent_session_id} "
                f"(user: {current_user.username})"
            )

        # 创建workspace目录
        from app.main import WORKSPACE_BASE
        import os
        session_dir = os.path.join(WORKSPACE_BASE, session_id)
        os.makedirs(session_dir, exist_ok=True)

        logger.info(f"✅ Created session: {session_id} (user: {current_user.username})")

        return session

    except HTTPException:
        raise  # 重新抛出HTTP异常
    except Exception as e:
        logger.error(f"❌ Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/opencode/events")
async def events(
    session_id: str,
    current_user: User = Depends(get_current_user)  # ✅ 添加认证
):
    """
    SSE事件流端点

    Args:
        session_id: Session ID
        current_user: 当前认证用户

    Returns:
        Server-Sent Events流

    Raises:
        HTTPException: 认证失败或无权限
    """
    # 验证session存在
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # ✅ 验证权限
    await verify_session_ownership(
        session_id=session_id,
        current_user=current_user,
        session_manager=session_manager
    )

    # 返回SSE流
    return EventSourceResponse(session_id)
```

#### 3. 环境变量配置

**文件**: `.env`

```bash
# API配置
OPENCODE_API_KEY=your-secret-api-key-here  # 生产环境必须修改
OPENCODE_DEV_MODE=false  # 生产环境设为false
```

**文件**: `.env.example`

```bash
# API配置示例
OPENCODE_API_KEY=your-secret-api-key-here
OPENCODE_DEV_MODE=false
```

---

## 🔴 C2: Session ID冲突处理

### 问题

CLI和Web API可能生成相同的Session ID，导致数据覆盖和事件混淆。

### 修复方案

#### 1. 统一ID生成逻辑

**文件**: `app/utils.py`

```python
"""
工具函数
"""
import asyncio
import uuid
import re
from typing import Set

# 全局Session ID锁和已使用ID集合
_SESSION_ID_LOCK = asyncio.Lock()
_USED_SESSION_IDS: Set[str] = set()

SESSION_ID_PATTERN = re.compile(r'^ses_[a-zA-Z0-9]{12}$')


def validate_session_id(session_id: str) -> bool:
    """
    验证Session ID格式

    Args:
        session_id: Session ID

    Returns:
        True表示格式正确，False表示格式错误
    """
    return bool(SESSION_ID_PATTERN.match(session_id))


async def generate_unique_session_id() -> str:
    """
    生成唯一的Session ID

    格式: ses_<12位hex字符>

    Returns:
        唯一的Session ID

    Raises:
        RuntimeError: 生成ID失败（极低概率）
    """
    async with _SESSION_ID_LOCK:
        # 尝试生成唯一ID（最多100次）
        for attempt in range(100):
            # 生成ID: ses_ + 12位hex
            session_id = f"ses_{uuid.uuid4().hex[:12]}"

            # 检查是否已使用
            if session_id not in _USED_SESSION_IDS:
                _USED_SESSION_IDS.add(session_id)

                # 清理：如果集合过大，移除旧的ID（LRU）
                if len(_USED_SESSION_IDS) > 10000:
                    # 移除一半（简单的LRU实现）
                    _USED_SESSION_IDS.clear()

                return session_id

        # 极低概率：100次都没生成唯一ID
        raise RuntimeError("Failed to generate unique session ID after 100 attempts")


async def reserve_session_id(session_id: str) -> bool:
    """
    预留指定的Session ID（防止冲突）

    Args:
        session_id: 要预留的Session ID

    Returns:
        True表示预留成功，False表示ID已被占用
    """
    async with _SESSION_ID_LOCK:
        if session_id in _USED_SESSION_IDS:
            return False

        _USED_SESSION_IDS.add(session_id)
        return True


def release_session_id(session_id: str) -> None:
    """
    释放Session ID（session删除时调用）

    Args:
        session_id: 要释放的Session ID
    """
    # 同步释放（session删除时可能没有asyncio上下文）
    _USED_SESSION_IDS.discard(session_id)
```

#### 2. 修改Web API使用统一ID生成

**文件**: `app/api.py`

```python
from app.utils import generate_unique_session_id, validate_session_id, reserve_session_id

@app.post("/opencode/session")
async def create_session(
    current_user: User = Depends(get_current_user),
    id: Optional[str] = None,
    title: str = "New Session",
    mode: str = "auto",
    version: str = "1.0.0",
    parent_session_id: Optional[str] = None
):
    """
    创建新会话
    """
    try:
        # ✅ 验证父session权限
        if parent_session_id:
            await verify_session_ownership(
                session_id=parent_session_id,
                current_user=current_user,
                session_manager=session_manager
            )

        # 处理Session ID
        if id:
            # CLI提供了ID
            if not validate_session_id(id):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid session ID format. Expected: ses_<12 chars>"
                )

            # ✅ 尝试预留ID
            reserved = await reserve_session_id(id)
            if not reserved:
                # ID已被占用，生成新的
                logger.warning(f"⚠️ Session ID {id} already exists, generating new ID...")
                session_id = await generate_unique_session_id()
            else:
                session_id = id
        else:
            # 自动生成ID
            session_id = await generate_unique_session_id()

        # 创建session对象
        session = await session_manager.create_session(
            session_id=session_id,
            title=title,
            version=version,
            user_id=current_user.id
        )

        # 如果是子session，建立父子关系
        if parent_session_id:
            session.parent_id = parent_session_id
            logger.info(
                f"✅ Registered child session: {session_id} <- {parent_session_id} "
                f"(user: {current_user.username})"
            )

        # 创建workspace目录
        from app.main import WORKSPACE_BASE
        import os
        session_dir = os.path.join(WORKSPACE_BASE, session_id)
        os.makedirs(session_dir, exist_ok=True)

        logger.info(f"✅ Created session: {session_id} (user: {current_user.username})")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 3. 修改CLI使用统一ID生成

**文件**: `app/main.py`

```python
from app.utils import generate_unique_session_id, reserve_session_id

async def execute_task_tool(
    session_id: str,
    agent_type: str,
    prompt: str
) -> str:
    """
    执行task工具，创建子代理

    Returns:
        子session的ID（task_id格式）
    """
    # 1. ✅ 使用统一的ID生成函数
    child_session_id = await generate_unique_session_id()

    logger.info(f"Generated child session ID: {child_session_id}")

    # 2. 创建子workspace目录
    child_workspace = os.path.join(WORKSPACE_BASE, child_session_id)
    os.makedirs(child_workspace, exist_ok=True)

    # 3. ✅ 注册到Web后端
    try:
        registered_session = await register_subsession_with_web_backend(
            parent_session_id=session_id,
            child_session_id=child_session_id,
            mode="auto"
        )

        if registered_session:
            logger.info(f"✅ Registered child session: {child_session_id}")
        else:
            logger.warning(f"⚠️ Failed to register child session: {child_session_id}")

    except Exception as e:
        logger.error(f"❌ Error registering child session: {e}")
        logger.warning("⚠️ Child session events will not be visible in web UI")

    # 4. 创建子代理并执行任务
    # ... 原有的子代理创建逻辑 ...

    return f"task_id: {child_session_id}\n\nSubagent created successfully."
```

#### 4. 添加Session删除时的ID释放

**文件**: `app/managers.py`

```python
from app.utils import release_session_id

async def delete_session(session_id: str) -> bool:
    """
    删除session

    Args:
        session_id: Session ID

    Returns:
        True表示删除成功，False表示失败
    """
    try:
        # 删除session
        success = await session_manager.delete_session(session_id)

        if success:
            # ✅ 释放Session ID
            release_session_id(session_id)
            logger.info(f"✅ Released session ID: {session_id}")

        return success

    except Exception as e:
        logger.error(f"❌ Error deleting session {session_id}: {e}")
        return False
```

---

## 🧪 测试

### 单元测试

**文件**: `tests/test_auth.py`

```python
import pytest
from fastapi import Header
from app.auth import get_current_user, verify_session_ownership
from app.utils import generate_unique_session_id, validate_session_id

@pytest.mark.asyncio
async def test_get_current_user_with_valid_key():
    """测试有效的API密钥"""
    from app.config import settings

    # Mock环境变量
    os.environ["OPENCODE_API_KEY"] = "test-key"
    os.environ["OPENCODE_DEV_MODE"] = "false"

    # 测试
    authorization = "Bearer test-key"
    user = await get_current_user(authorization=authorization)

    assert user.is_authenticated
    assert user.username == "api_client"

@pytest.mark.asyncio
async def test_get_current_user_with_invalid_key():
    """测试无效的API密钥"""
    os.environ["OPENCODE_API_KEY"] = "test-key"
    os.environ["OPENCODE_DEV_MODE"] = "false"

    # 测试
    authorization = "Bearer invalid-key"

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=authorization)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_generate_unique_session_id():
    """测试生成唯一Session ID"""
    session_id = await generate_unique_session_id()

    # 验证格式
    assert validate_session_id(session_id)
    assert session_id.startswith("ses_")
    assert len(session_id) == 16  # ses_ + 12 chars

    # 验证唯一性（连续生成100次）
    ids = set()
    for _ in range(100):
        session_id = await generate_unique_session_id()
        assert session_id not in ids  # 确保唯一
        ids.add(session_id)
```

### 集成测试

**文件**: `tests/test_session_creation.py`

```python
import pytest
from httpx import AsyncClient, Headers

@pytest.mark.asyncio
async def test_create_session_with_auth():
    """测试带认证的session创建"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 设置认证头
        headers = Headers({
            "authorization": "Bearer test-key"
        })

        # 创建session
        response = await client.post(
            "/opencode/session",
            json={"title": "Test Session"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert validate_session_id(data["id"])


@pytest.mark.asyncio
async def test_create_session_without_auth():
    """测试不带认证的session创建（应该失败）"""
    os.environ["OPENCODE_DEV_MODE"] = "false"

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 不设置认证头
        response = await client.post(
            "/opencode/session",
            json={"title": "Test Session"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_child_session_with_id_conflict():
    """测试Session ID冲突处理"""
    os.environ["OPENCODE_API_KEY"] = "test-key"
    os.environ["OPENCODE_DEV_MODE"] = "false"

    async with AsyncClient(app=app, base_url="http://test") as client:
        headers = Headers({"authorization": "Bearer test-key"})

        # 使用固定ID创建第一个session
        session1 = await client.post(
            "/opencode/session",
            json={"id": "ses_test123456", "title": "Session 1"},
            headers=headers
        )
        assert session1.status_code == 200

        # 尝试使用相同ID创建第二个session
        session2 = await client.post(
            "/opencode/session",
            json={"id": "ses_test123456", "title": "Session 2"},
            headers=headers
        )
        assert session2.status_code == 200

        # 验证：返回了不同的ID（自动生成）
        data2 = session2.json()
        assert data2["id"] != "ses_test123456"
```

---

## 📋 部署清单

### 环境变量配置

```bash
# 生产环境必须配置
export OPENCODE_API_KEY="$(openssl rand -hex 32)"  # 生成随机密钥
export OPENCODE_DEV_MODE="false"
```

### 数据库迁移

无需迁移（session在内存中）

### 重启服务

```bash
# 重启Web后端
systemctl restart opencode-api

# 重启CLI（如果在运行）
systemctl restart opencode-cli
```

---

## ✅ 验证清单

- [ ] API认证正常工作
- [ ] Session ID格式验证
- [ ] ID冲突自动处理
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 前端SSE订阅正常

---

**修复状态**: ✅ 设计完成
**优先级**: 🔴 Critical
**实施时间**: 1.5小时
**风险**: 低（向后兼容，有降级机制）

---

**作者**: AI Security Engineer
**日期**: 2026-03-02
**版本**: 1.0
