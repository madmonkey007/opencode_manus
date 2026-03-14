"""
OpenCode 适配器层 - 基础接口

定义统一的适配器接口，支持多种执行渠道：
- Web: 通过Server API执行
- CLI: 通过进程池执行
- Mobile: 通过移动端API执行
- API: 通过第三方API执行
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """执行上下文"""
    session_id: str
    prompt: str
    mode: str = "auto"  # auto, build, plan
    context: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExecutionEvent:
    """执行事件"""
    event_type: str  # phase, action, progress, complete, error
    data: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    session_id: str
    response: Optional[str] = None
    error: Optional[str] = None
    events: list = None
    metadata: Dict[str, Any] = None
    execution_time: float = 0.0

    def __post_init__(self):
        if self.events is None:
            self.events = []
        if self.metadata is None:
            self.metadata = {}


class BaseAdapter(ABC):
    """
    基础适配器抽象类

    所有适配器必须实现此接口
    """

    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        初始化适配器

        Args:
            name: 适配器名称
            config: 配置参数
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        执行任务（非流式）

        Args:
            context: 执行上下文

        Returns:
            ExecutionResult: 执行结果
        """
        pass

    @abstractmethod
    async def execute_stream(
        self,
        context: ExecutionContext
    ) -> AsyncIterator[ExecutionEvent]:
        """
        执行任务（流式）

        Args:
            context: 执行上下文

        Yields:
            ExecutionEvent: 执行事件
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查适配器是否可用

        Returns:
            bool: 是否可用
        """
        pass

    @abstractmethod
    def get_health(self) -> Dict[str, Any]:
        """
        获取适配器健康状态

        Returns:
            健康状态字典
        """
        pass

    async def validate_context(self, context: ExecutionContext) -> tuple[bool, Optional[str]]:
        """
        验证执行上下文

        Args:
            context: 执行上下文

        Returns:
            (is_valid, error_message): 是否有效及错误信息
        """
        if not context.session_id:
            return False, "Session ID is required"

        if not context.prompt:
            return False, "Prompt is required"

        if context.mode not in ["auto", "build", "plan"]:
            return False, f"Invalid mode: {context.mode}"

        return True, None

    def get_stats(self) -> Dict[str, Any]:
        """
        获取适配器统计信息

        Returns:
            统计信息字典
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "available": self.is_available(),
            "health": self.get_health()
        }


class AdapterError(Exception):
    """适配器错误基类"""

    def __init__(self, message: str, adapter_name: str, details: Dict[str, Any] = None):
        self.message = message
        self.adapter_name = adapter_name
        self.details = details or {}
        super().__init__(f"[{adapter_name}] {message}")


class AdapterUnavailableError(AdapterError):
    """适配器不可用错误"""

    def __init__(self, adapter_name: str, reason: str = ""):
        message = f"Adapter unavailable: {reason}" if reason else "Adapter unavailable"
        super().__init__(message, adapter_name, {"reason": reason})


class AdapterExecutionError(AdapterError):
    """适配器执行错误"""

    def __init__(self, adapter_name: str, error: str, context: Any = None):
        super().__init__(
            f"Execution failed: {error}",
            adapter_name,
            {"error": error, "context": str(context) if context else None}
        )
