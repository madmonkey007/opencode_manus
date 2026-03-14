"""
OpenCode 网关核心

提供统一的任务执行入口，支持认证、限流、路由等功能
"""
import logging
import uuid
from typing import Optional, Dict, Any, AsyncIterator
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from .adapters.base import BaseAdapter, ExecutionContext, ExecutionEvent, ExecutionResult, AdapterError
from .router import SmartRouter, HybridStrategy
from .auth import AuthManager, AuthContext, AuthError
from .rate_limiter import RateLimiter, RateLimitError

logger = logging.getLogger(__name__)


# ============================================================================
# 请求和响应模型
# ============================================================================

class SubmitTaskRequest(BaseModel):
    """提交任务请求"""
    prompt: str = Field(..., description="任务提示词", min_length=1, max_length=10000)
    mode: str = Field(default="auto", description="执行模式", pattern="^(auto|build|plan)$")
    context: Dict[str, Any] = Field(default_factory=dict, description="任务上下文")
    priority: str = Field(default="normal", description="任务优先级", pattern="^(low|normal|high|urgent)$")
    stream: bool = Field(default=False, description="是否使用流式响应")


class SubmitTaskResponse(BaseModel):
    """提交任务响应"""
    success: bool
    task_id: str
    session_id: str
    message: Optional[str] = None
    execution_time: Optional[float] = None
    adapter_used: Optional[str] = None
    route_reason: Optional[str] = None


class StreamEvent(BaseModel):
    """流式事件"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# 网关配置
# ============================================================================

class GatewayConfig:
    """网关配置"""

    def __init__(
        self,
        enable_auth: bool = True,
        enable_rate_limit: bool = True,
        default_rate_limit: int = 100,
        rate_limit_window: int = 60,
        max_request_size: int = 1024 * 1024,  # 1MB
        request_timeout: int = 300,
        enable_metrics: bool = True
    ):
        """
        初始化网关配置

        Args:
            enable_auth: 是否启用认证
            enable_rate_limit: 是否启用限流
            default_rate_limit: 默认限流值（请求/分钟）
            rate_limit_window: 限流时间窗口（秒）
            max_request_size: 最大请求大小（字节）
            request_timeout: 请求超时时间（秒）
            enable_metrics: 是否启用指标收集
        """
        self.enable_auth = enable_auth
        self.enable_rate_limit = enable_rate_limit
        self.default_rate_limit = default_rate_limit
        self.rate_limit_window = rate_limit_window
        self.max_request_size = max_request_size
        self.request_timeout = request_timeout
        self.enable_metrics = enable_metrics


# ============================================================================
# 网关核心
# ============================================================================

class Gateway:
    """
    OpenCode 网关核心

    功能：
    1. 统一的任务执行入口
    2. 认证鉴权
    3. 限流控制
    4. 智能路由
    5. 指标收集
    """

    def __init__(
        self,
        cli_adapter: BaseAdapter,
        web_adapter: BaseAdapter,
        auth_manager: AuthManager = None,
        rate_limiter: RateLimiter = None,
        router: SmartRouter = None,
        config: GatewayConfig = None
    ):
        """
        初始化网关

        Args:
            cli_adapter: CLI 适配器
            web_adapter: Web 适配器
            auth_manager: 认证管理器（可选）
            rate_limiter: 限流器（可选）
            router: 智能路由器（可选）
            config: 网关配置（可选）
        """
        self.cli_adapter = cli_adapter
        self.web_adapter = web_adapter

        # 路由器
        if router is None:
            router = SmartRouter(
                cli_adapter=cli_adapter,
                web_adapter=web_adapter,
                strategy=HybridStrategy()
            )
        self.router = router

        # 认证管理器
        self.auth_manager = auth_manager or AuthManager()

        # 限流器
        self.rate_limiter = rate_limiter or RateLimiter()

        # 配置
        self.config = config or GatewayConfig()

        # 指标
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "authenticated_requests": 0,
            "rate_limited_requests": 0,
            "start_time": datetime.now()
        }

        # 修复：添加启动状态标志
        self._started = False

        self.logger = logging.getLogger(__name__)
        self.logger.info("Gateway initialized")

    async def start(self) -> None:
        """启动网关服务"""
        if self._started:
            self.logger.warning("Gateway already started")
            return

        # 启动限流器清理任务
        if self.config.enable_rate_limit:
            await self.rate_limiter.start()
            self.logger.info("Gateway rate limiter started")

        self._started = True
        self.logger.info("Gateway started")

    async def stop(self) -> None:
        """停止网关服务"""
        if not self._started:
            self.logger.warning("Gateway not started")
            return

        # 停止限流器清理任务
        if self.config.enable_rate_limit:
            await self.rate_limiter.stop()
            self.logger.info("Gateway rate limiter stopped")

        self._started = False
        self.logger.info("Gateway stopped")

    async def submit_task(
        self,
        request: SubmitTaskRequest,
        auth_context: AuthContext = None
    ) -> SubmitTaskResponse:
        """
        提交任务

        Args:
            request: 任务请求
            auth_context: 认证上下文（可选）

        Returns:
            SubmitTaskResponse: 任务响应
        """
        task_id = str(uuid.uuid4())
        session_id = f"ses_{task_id[:8]}"

        start_time = datetime.now()

        try:
            # 更新指标
            self.metrics["total_requests"] += 1

            # 修复：验证请求大小
            request_size = len(request.prompt.encode('utf-8'))
            context_size = len(str(request.context).encode('utf-8'))
            total_size = request_size + context_size

            if total_size > self.config.max_request_size:
                self.metrics["failed_requests"] += 1
                return SubmitTaskResponse(
                    success=False,
                    task_id=task_id,
                    session_id=session_id,
                    message=f"Request too large: {total_size} bytes (max {self.config.max_request_size})"
                )

            # 1. 认证鉴权
            if self.config.enable_auth:
                if auth_context is None:
                    return SubmitTaskResponse(
                        success=False,
                        task_id=task_id,
                        session_id=session_id,
                        message="Authentication required"
                    )

                is_valid, error = await self.auth_manager.verify(auth_context)
                if not is_valid:
                    return SubmitTaskResponse(
                        success=False,
                        task_id=task_id,
                        session_id=session_id,
                        message=f"Authentication failed: {error}"
                    )

                self.metrics["authenticated_requests"] += 1

            # 2. 限流检查
            if self.config.enable_rate_limit:
                try:
                    # 获取用户ID（用于限流）
                    user_id = auth_context.user_id if auth_context else "anonymous"

                    # 检查用户级限流
                    await self.rate_limiter.check_limit(
                        key=f"user:{user_id}",
                        limit=self.config.default_rate_limit,
                        window=self.config.rate_limit_window
                    )

                    # 检查全局限流
                    await self.rate_limiter.check_limit(
                        key="global",
                        limit=self.config.default_rate_limit * 10,
                        window=self.config.rate_limit_window
                    )

                except RateLimitError as e:
                    self.metrics["rate_limited_requests"] += 1
                    self.logger.warning(f"Rate limit exceeded: {e}")
                    return SubmitTaskResponse(
                        success=False,
                        task_id=task_id,
                        session_id=session_id,
                        message=f"Rate limit exceeded: {str(e)}"
                    )

            # 3. 创建执行上下文
            context = ExecutionContext(
                session_id=session_id,
                prompt=request.prompt,
                mode=request.mode,
                context={
                    **request.context,
                    "priority": request.priority,
                    "task_id": task_id
                }
            )

            # 修复：流式执行应该使用 submit_task_stream
            if request.stream:
                return SubmitTaskResponse(
                    success=False,
                    task_id=task_id,
                    session_id=session_id,
                    message="Use submit_task_stream() for streaming requests"
                )

            # 4. 执行任务（带超时控制）
            import asyncio
            result = await asyncio.wait_for(
                self.router.execute_with_routing(context),
                timeout=self.config.request_timeout
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            if result.success:
                self.metrics["successful_requests"] += 1
                return SubmitTaskResponse(
                    success=True,
                    task_id=task_id,
                    session_id=session_id,
                    message="Task completed successfully",
                    execution_time=execution_time,
                    adapter_used=result.metadata.get("adapter_used"),
                    route_reason=result.metadata.get("route_reason")
                )
            else:
                self.metrics["failed_requests"] += 1
                return SubmitTaskResponse(
                    success=False,
                    task_id=task_id,
                    session_id=session_id,
                    message=result.error or "Task execution failed"
                )

        # 修复：细化的异常处理
        except (RateLimitError, AuthError) as e:
            # 预期的业务异常
            self.logger.warning(f"Expected error: {e}")
            self.metrics["failed_requests"] += 1
            return SubmitTaskResponse(
                success=False,
                task_id=task_id,
                session_id=session_id,
                message=str(e)
            )
        except asyncio.TimeoutError:
            # 超时异常
            self.logger.warning(f"Task timeout after {self.config.request_timeout}s")
            self.metrics["failed_requests"] += 1
            return SubmitTaskResponse(
                success=False,
                task_id=task_id,
                session_id=session_id,
                message=f"Task timeout after {self.config.request_timeout}s"
            )
        except Exception as e:
            # 未预期的异常
            self.logger.exception(f"Unexpected error submitting task")
            self.metrics["failed_requests"] += 1
            return SubmitTaskResponse(
                success=False,
                task_id=task_id,
                session_id=session_id,
                message="Internal server error"
            )

    async def submit_task_stream(
        self,
        request: SubmitTaskRequest,
        auth_context: AuthContext = None
    ) -> AsyncIterator[StreamEvent]:
        """
        提交任务（流式）

        Args:
            request: 任务请求
            auth_context: 认证上下文（可选）

        Yields:
            StreamEvent: 流式事件
        """
        task_id = str(uuid.uuid4())
        session_id = f"ses_{task_id[:8]}"

        try:
            # 1. 认证鉴权
            if self.config.enable_auth:
                if auth_context is None:
                    yield StreamEvent(
                        event_type="error",
                        data={"error": "Authentication required"}
                    )
                    return

                is_valid, error = await self.auth_manager.verify(auth_context)
                if not is_valid:
                    yield StreamEvent(
                        event_type="error",
                        data={"error": f"Authentication failed: {error}"}
                    )
                    return

            # 2. 限流检查
            if self.config.enable_rate_limit:
                try:
                    user_id = auth_context.user_id if auth_context else "anonymous"
                    await self.rate_limiter.check_limit(
                        key=f"user:{user_id}",
                        limit=self.config.default_rate_limit,
                        window=self.config.rate_limit_window
                    )
                except RateLimitError as e:
                    yield StreamEvent(
                        event_type="error",
                        data={"error": f"Rate limit exceeded: {str(e)}"}
                    )
                    return

            # 3. 创建执行上下文
            context = ExecutionContext(
                session_id=session_id,
                prompt=request.prompt,
                mode=request.mode,
                context={
                    **request.context,
                    "priority": request.priority,
                    "task_id": task_id
                }
            )

            # 4. 路由决策
            decision = await self.router.route(context)

            # 发送路由信息事件
            yield StreamEvent(
                event_type="route",
                data={
                    "adapter": decision.adapter.name,
                    "reason": decision.reason
                }
            )

            # 5. 执行任务（流式）
            async for event in decision.adapter.execute_stream(context):
                yield StreamEvent(
                    event_type=event.event_type,
                    data=event.data,
                    timestamp=event.timestamp
                )

                # 如果是完成或错误事件，结束流
                if event.event_type in ["complete", "error"]:
                    break

        except Exception as e:
            self.logger.error(f"Error in stream task: {e}")
            yield StreamEvent(
                event_type="error",
                data={"error": str(e)}
            )

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取网关指标

        Returns:
            指标字典
        """
        uptime = (datetime.now() - self.metrics["start_time"]).total_seconds()

        return {
            "uptime_seconds": uptime,
            "total_requests": self.metrics["total_requests"],
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "authenticated_requests": self.metrics["authenticated_requests"],
            "rate_limited_requests": self.metrics["rate_limited_requests"],
            "success_rate": (
                self.metrics["successful_requests"] / self.metrics["total_requests"]
                if self.metrics["total_requests"] > 0 else 0
            ),
            "requests_per_second": (
                self.metrics["total_requests"] / uptime
                if uptime > 0 else 0
            ),
            "router": self.router.get_stats()
        }

    def reset_metrics(self) -> None:
        """重置指标"""
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "authenticated_requests": 0,
            "rate_limited_requests": 0,
            "start_time": datetime.now()
        }
