"""
CLI子session注册模块 - 方案A（最小化修改）

在CLI创建子session时，通过现有API在Web后端注册
"""
import httpx
import os
import logging
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger("opencode.subsession")

# Web API基础URL（从环境变量读取）
WEB_API_URL = os.getenv("WEB_API_URL", "http://localhost:8089")
API_KEY = os.getenv("OPENCODE_API_KEY", "dev-key-change-in-production")
DEV_MODE = os.getenv("OPENCODE_DEV_MODE", "true") == "true"


class RegistrationFailedError(Exception):
    """子session注册失败"""
    pass


@retry(
    stop=stop_after_attempt(3),  # 最多重试3次
    wait=wait_exponential(multiplier=1, min=1, max=10),  # 指数退避
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
)
async def register_subsession_with_web_backend(
    parent_session_id: str,
    child_session_id: str,
    mode: str = "auto"
) -> Optional[dict]:
    """
    将CLI创建的子session注册到Web后端（方案A：使用现有API）

    Args:
        parent_session_id: 主session ID
        child_session_id: 子session ID（将作为title传递）
        mode: 执行模式

    Returns:
        注册后的session对象，失败返回None

    Raises:
        RegistrationFailedError: 注册失败
    """
    # 开发模式：跳过注册
    if DEV_MODE:
        logger.info(f"[DEV MODE] Skipping child session registration: {child_session_id}")
        return {
            "id": child_session_id,
            "title": f"Subsession: {child_session_id}",
            "mode": mode
        }

    try:
        # 准备请求头（开发模式不需要Authorization）
        headers = {
            "Content-Type": "application/json"
        }

        # ✅ 方案A：使用现有API，将child_session_id放在title中
        # 后端会生成自己的session ID，我们在response中获取它
        payload = {
            "title": f"[Child] {child_session_id}",  # 标记为子session
            "mode": mode,
            "version": "1.0.0"
        }

        logger.info(f"📡 Registering child session to Web backend: {child_session_id}")

        # 发送HTTP POST请求
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{WEB_API_URL}/opencode/session",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                session = response.json()
                actual_session_id = session.get("id")
                logger.info(f"✅ Registered child session: {child_session_id} -> {actual_session_id}")
                # 返回实际的session ID
                return session

            elif response.status_code == 401:  # 认证失败（如果添加了认证）
                logger.error(f"❌ Authentication failed for child session registration")
                raise RegistrationFailedError("Authentication failed")

            else:
                logger.error(f"❌ Failed to register child session: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise RegistrationFailedError(f"HTTP {response.status_code}: {response.text}")

    except httpx.TimeoutException:
        logger.error(f"⏱️ Timeout registering child session: {child_session_id}")
        raise RegistrationFailedError("Timeout")
    except httpx.ConnectError:
        logger.error(f"🔌 Connection error registering child session: {child_session_id}")
        raise RegistrationFailedError("Connection error")
    except RegistrationFailedError:
        raise  # 重新抛出
    except Exception as e:
        logger.error(f"❌ Unexpected error registering child session: {e}")
        raise RegistrationFailedError(str(e))


async def safe_register_subsession(
    parent_session_id: str,
    child_session_id: str,
    mode: str = "auto"
) -> bool:
    """
    安全注册子session（失败时不抛出异常）

    Args:
        parent_session_id: 主session ID
        child_session_id: 子session ID
        mode: 执行模式

    Returns:
        True表示注册成功或跳过，False表示注册失败
    """
    try:
        result = await register_subsession_with_web_backend(
            parent_session_id=parent_session_id,
            child_session_id=child_session_id,
            mode=mode
        )
        return result is not None

    except RegistrationFailedError as e:
        logger.warning(f"⚠️ Child session registration failed: {e}")
        logger.warning(f"⚠️ Child session events will not be visible in web UI")
        # ✅ 继续执行，不影响CLI功能
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False
