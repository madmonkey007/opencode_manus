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
    if os.getenv("OPENCODE_DEV_MODE", "true") == "true":
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
        True表示有权限

    Raises:
        HTTPException: Session不存在或无权限
    """
    # 开发模式：跳过权限验证
    if os.getenv("OPENCODE_DEV_MODE", "true") == "true":
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
