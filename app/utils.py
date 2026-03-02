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
