"""
API端点常量定义

统一管理所有API端点URL，避免硬编码，便于维护和修改。
"""

class APIEndpoints:
    """RESTful API端点常量"""

    # Session相关
    SESSION_CREATE = "/session"
    SESSION_GET = "/session/{session_id}"
    SESSION_DELETE = "/session/{session_id}"
    SESSION_LIST = "/sessions"

    # Message相关
    SESSION_MESSAGES = "/session/{session_id}/messages"  # 复数，RESTful规范
    SESSION_SINGLE_MESSAGE = "/session/{session_id}/message"  # 单数，向后兼容
    SESSION_TIMELINE = "/session/{session_id}/timeline"

    # SSE相关
    SESSION_SSE = "/session/{session_id}/sse"

    # 健康检查
    HEALTH = "/health"

    @classmethod
    def format_session_messages(cls, session_id: str) -> str:
        """格式化session messages端点"""
        return cls.SESSION_MESSAGES.format(session_id=session_id)

    @classmethod
    def format_session_single_message(cls, session_id: str) -> str:
        """格式化session single message端点"""
        return cls.SESSION_SINGLE_MESSAGE.format(session_id=session_id)

    @classmethod
    def format_session_get(cls, session_id: str) -> str:
        """格式化session get端点"""
        return cls.SESSION_GET.format(session_id=session_id)

    @classmethod
    def format_session_sse(cls, session_id: str) -> str:
        """格式化session SSE端点"""
        return cls.SESSION_SSE.format(session_id=session_id)

    @classmethod
    def format_session_timeline(cls, session_id: str) -> str:
        """格式化session timeline端点"""
        return cls.SESSION_TIMELINE.format(session_id=session_id)
