"""
OpenCode 适配器层

支持多种执行渠道：
- Web: 通过 Server API
- CLI: 通过进程池
- Mobile: 移动端（预留）
- API: 第三方 API（预留）
"""
from .base import (
    BaseAdapter,
    ExecutionContext,
    ExecutionEvent,
    ExecutionResult,
    AdapterError,
    AdapterUnavailableError,
    AdapterExecutionError
)
from .web_adapter import WebAdapter
from .cli_adapter import CLIAdapter

__all__ = [
    # 基础类
    "BaseAdapter",
    "ExecutionContext",
    "ExecutionEvent",
    "ExecutionResult",
    "AdapterError",
    "AdapterUnavailableError",
    "AdapterExecutionError",
    # 适配器实现
    "WebAdapter",
    "CLIAdapter",
]


def create_adapter(adapter_type: str, config: dict = None) -> BaseAdapter:
    """
    工厂函数：创建适配器实例

    Args:
        adapter_type: 适配器类型 (web, cli, mobile, api)
        config: 配置参数

    Returns:
        适配器实例

    Raises:
        ValueError: 不支持的适配器类型
    """
    config = config or {}

    adapters = {
        "web": WebAdapter,
        "cli": CLIAdapter,
    }

    adapter_class = adapters.get(adapter_type.lower())

    if adapter_class is None:
        raise ValueError(
            f"Unsupported adapter type: {adapter_type}. "
            f"Supported types: {', '.join(adapters.keys())}"
        )

    return adapter_class(config=config)
