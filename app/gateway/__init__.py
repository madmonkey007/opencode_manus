"""
OpenCode 网关层

提供统一的任务执行接口，支持多种执行渠道
"""
from .adapters import (
    BaseAdapter,
    ExecutionContext,
    ExecutionEvent,
    ExecutionResult,
    WebAdapter,
    CLIAdapter,
    create_adapter
)
from .gateway import Gateway, GatewayConfig, SubmitTaskRequest, SubmitTaskResponse
from .router import SmartRouter, HybridStrategy
from .auth import AuthManager, AuthContext, AuthError, APIKeyManager, JWTManager
from .rate_limiter import RateLimiter, RateLimitError, RateLimitConfig
from .event_broadcaster import (
    EventBroadcaster,
    Event,
    EventSubscriber,
    SSESubscriber,
    StreamSubscriber,
    get_global_broadcaster
)

__all__ = [
    # 适配器
    "BaseAdapter",
    "ExecutionContext",
    "ExecutionEvent",
    "ExecutionResult",
    "WebAdapter",
    "CLIAdapter",
    "create_adapter",
    # 网关
    "Gateway",
    "GatewayConfig",
    "SubmitTaskRequest",
    "SubmitTaskResponse",
    # 路由
    "SmartRouter",
    "HybridStrategy",
    # 认证
    "AuthManager",
    "AuthContext",
    "AuthError",
    "APIKeyManager",
    "JWTManager",
    # 限流
    "RateLimiter",
    "RateLimitError",
    "RateLimitConfig",
    # 事件分发
    "EventBroadcaster",
    "Event",
    "EventSubscriber",
    "SSESubscriber",
    "StreamSubscriber",
    "get_global_broadcaster",
]
