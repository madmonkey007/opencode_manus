"""
OpenCode 智能路由器

负责根据系统状态选择最优的执行渠道（Web / CLI）
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

from .adapters.base import BaseAdapter, ExecutionContext, ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class RouteDecision:
    """路由决策"""
    adapter: BaseAdapter
    reason: str
    fallback_available: bool = False
    estimated_wait_time: float = 0.0


class RouterStrategy:
    """
    路由策略基类

    定义当进程池满载时的处理策略
    """

    def __init__(self, name: str):
        self.name = name

    def should_use_cli(self, pool_stats: Dict[str, Any]) -> tuple[bool, str]:
        """
        判断是否应该使用 CLI 适配器

        Args:
            pool_stats: 进程池统计信息

        Returns:
            (should_use, reason): 是否使用及原因
        """
        raise NotImplementedError("Subclasses must implement this method")


class WaitStrategy(RouterStrategy):
    """
    等待策略：如果进程池满载，等待空闲进程

    优点：
    - 保证所有任务都使用快速的 CLI 进程池
    - 用户体验一致（都是快速响应）

    缺点：
    - 可能导致任务排队等待
    - 在高负载时可能延迟较高
    """

    def __init__(self, max_wait_time: float = 30.0):
        """
        初始化等待策略

        Args:
            max_wait_time: 最大等待时间（秒）
        """
        super().__init__("wait")
        self.max_wait_time = max_wait_time

    def should_use_cli(self, pool_stats: Dict[str, Any]) -> tuple[bool, str]:
        """
        判断是否使用 CLI（始终等待）

        Returns:
            (True, "wait_for_idle_process")
        """
        idle_processes = pool_stats.get("idle_processes", 0)

        if idle_processes > 0:
            return True, "idle_process_available"

        # 有繁忙进程但可以等待
        if pool_stats.get("healthy_processes", 0) > 0:
            return True, f"wait_for_idle_process(max_wait={self.max_wait_time}s)"

        # 没有健康进程
        return False, "no_healthy_processes"


class FallbackStrategy(RouterStrategy):
    """
    降级策略：如果进程池满载，降级到 Web 适配器

    优点：
    - 不会排队等待，任务立即执行
    - 系统吞吐量更高

    缺点：
    - 用户体验不一致（有时快有时慢）
    - Web 适配器响应较慢（500-1000ms vs 200ms）
    """

    def __init__(self, busy_threshold: float = 0.8):
        """
        初始化降级策略

        Args:
            busy_threshold: 忙碌阈值（0-1），超过此比例则降级
        """
        super().__init__("fallback")
        self.busy_threshold = busy_threshold

    def should_use_cli(self, pool_stats: Dict[str, Any]) -> tuple[bool, str]:
        """
        判断是否使用 CLI（可能降级）

        Returns:
            (should_use, reason): 是否使用及原因
        """
        healthy = pool_stats.get("healthy_processes", 0)
        busy = pool_stats.get("busy_processes", 0)

        if healthy == 0:
            return False, "no_healthy_processes"

        # 计算忙碌比例
        if healthy > 0:
            busy_ratio = busy / healthy

            if busy_ratio >= self.busy_threshold:
                return False, f"pool_too_busy({busy_ratio:.1%} >= {self.busy_threshold:.1%})"

        # 有空闲进程
        idle = pool_stats.get("idle_processes", 0)
        if idle > 0:
            return True, "idle_process_available"

        # 有进程但都繁忙，根据阈值决定
        busy_ratio = busy / healthy if healthy > 0 else 0
        return busy_ratio < self.busy_threshold, f"busy_ratio={busy_ratio:.1%}"


class HybridStrategy(RouterStrategy):
    """
    混合策略：智能地在等待和降级之间选择

    策略逻辑：
    1. 优先使用 CLI 进程池
    2. 根据系统负载动态决策：
       - 轻负载（< 50%）：等待空闲进程
       - 中负载（50-80%）：根据任务优先级决定
       - 高负载（> 80%）：降级到 Web 适配器
    3. 支持任务优先级（高优先级优先使用 CLI）
    4. 考虑预估等待时间

    优点：
    - 自动适应系统负载
    - 平衡响应时间和吞吐量
    - 支持任务优先级
    - 用户体验可预测

    可配置参数：
    - low_load_threshold: 低负载阈值（默认 0.5）
    - high_load_threshold: 高负载阈值（默认 0.8）
    - max_wait_time_low_load: 低负载时最大等待时间（默认 10s）
    - max_wait_time_high_load: 高负载时最大等待时间（默认 2s）
    """

    def __init__(
        self,
        low_load_threshold: float = 0.5,
        high_load_threshold: float = 0.8,
        max_wait_time_low_load: float = 10.0,
        max_wait_time_high_load: float = 2.0
    ):
        """
        初始化混合策略

        Args:
            low_load_threshold: 低负载阈值（0-1）
            high_load_threshold: 高负载阈值（0-1）
            max_wait_time_low_load: 低负载时最大等待时间（秒）
            max_wait_time_high_load: 高负载时最大等待时间（秒）
        """
        super().__init__("hybrid")
        self.low_load_threshold = low_load_threshold
        self.high_load_threshold = high_load_threshold
        self.max_wait_time_low_load = max_wait_time_low_load
        self.max_wait_time_high_load = max_wait_time_high_load

        if low_load_threshold >= high_load_threshold:
            raise ValueError(
                f"low_load_threshold ({low_load_threshold}) must be "
                f"less than high_load_threshold ({high_load_threshold})"
            )

    def _calculate_busy_ratio(self, pool_stats: Dict[str, Any]) -> float:
        """计算进程池忙碌比例"""
        healthy = pool_stats.get("healthy_processes", 0)
        busy = pool_stats.get("busy_processes", 0)

        if healthy == 0:
            return 1.0  # 没有健康进程，视为满载

        return busy / healthy

    def _estimate_wait_time(
        self,
        pool_stats: Dict[str, Any],
        busy_ratio: float
    ) -> float:
        """
        估算等待时间

        基于以下因素：
        - 当前忙碌比例
        - 平均任务执行时间（假设 30 秒）
        - 空闲进程数量
        """
        # 假设平均任务执行时间为 30 秒
        avg_task_time = 30.0

        # 空闲进程数
        idle = pool_stats.get("idle_processes", 0)

        if idle > 0:
            return 0.0  # 有空闲进程，无需等待

        # 没有空闲进程，根据忙碌比例估算
        # 繁忙进程数
        busy = pool_stats.get("busy_processes", 0)

        if busy > 0:
            # 估算等待时间 = (任务数 / 进程数) * 平均任务时间
            # 简化为基于忙碌比例的估算
            return busy_ratio * avg_task_time / 2

        return 5.0  # 默认等待时间

    def _get_task_priority(self, context: ExecutionContext) -> int:
        """
        获取任务优先级

        Returns:
            优先级值（0-10，10 为最高）
        """
        priority = context.context.get("priority", "normal")

        priority_map = {
            "low": 3,
            "normal": 5,
            "high": 8,
            "urgent": 10
        }

        return priority_map.get(priority, 5)

    def should_use_cli(
        self,
        pool_stats: Dict[str, Any],
        context: ExecutionContext = None
    ) -> tuple[bool, str]:
        """
        判断是否使用 CLI（混合策略）

        Args:
            pool_stats: 进程池统计信息
            context: 执行上下文（可选，用于获取任务优先级）

        Returns:
            (should_use, reason): 是否使用及原因
        """
        # 检查是否有健康进程
        healthy = pool_stats.get("healthy_processes", 0)
        if healthy == 0:
            return False, "no_healthy_processes"

        # 计算忙碌比例
        busy_ratio = self._calculate_busy_ratio(pool_stats)

        # 有空闲进程，直接使用
        idle = pool_stats.get("idle_processes", 0)
        if idle > 0:
            return True, "idle_process_available"

        # 估算等待时间
        estimated_wait = self._estimate_wait_time(pool_stats, busy_ratio)

        # 根据负载级别决策
        if busy_ratio < self.low_load_threshold:
            # 低负载：等待空闲进程
            if estimated_wait <= self.max_wait_time_low_load:
                return True, (
                    f"low_load({busy_ratio:.1%}), "
                    f"wait_estimated_{estimated_wait:.1f}s"
                )
            else:
                return False, (
                    f"low_load_but_long_wait({estimated_wait:.1f}s > "
                    f"{self.max_wait_time_low_load}s)"
                )

        elif busy_ratio < self.high_load_threshold:
            # 中负载：根据任务优先级决定
            if context:
                priority = self._get_task_priority(context)

                # 高优先级任务（>=7）使用 CLI
                if priority >= 7:
                    if estimated_wait <= self.max_wait_time_low_load:
                        return True, (
                            f"medium_load({busy_ratio:.1%}), "
                            f"high_priority({priority}), "
                            f"wait_estimated_{estimated_wait:.1f}s"
                        )

                # 低优先级任务（<5）降级到 Web
                if priority < 5:
                    return False, (
                        f"medium_load({busy_ratio:.1%}), "
                        f"low_priority({priority}), "
                        f"fallback_to_web"
                    )

            # 中等优先级，根据等待时间决定
            max_wait = (
                self.max_wait_time_low_load +
                self.max_wait_time_high_load
            ) / 2

            if estimated_wait <= max_wait:
                return True, (
                    f"medium_load({busy_ratio:.1%}), "
                    f"wait_estimated_{estimated_wait:.1f}s"
                )
            else:
                return False, (
                    f"medium_load({busy_ratio:.1%}), "
                    f"wait_too_long({estimated_wait:.1f}s > {max_wait}s)"
                )

        else:
            # 高负载：降级到 Web（除非是紧急任务）
            if context:
                priority = self._get_task_priority(context)

                # 只有紧急任务（优先级=10）才使用 CLI
                if priority == 10 and estimated_wait <= self.max_wait_time_high_load:
                    return True, (
                        f"high_load({busy_ratio:.1%}), "
                        f"urgent_priority({priority}), "
                        f"wait_estimated_{estimated_wait:.1f}s"
                    )

            return False, (
                f"high_load({busy_ratio:.1%}), "
                f"fallback_to_web_for_throughput"
            )


class SmartRouter:
    """
    智能路由器

    根据配置的策略和系统状态，自动选择最优的执行渠道
    """

    def __init__(
        self,
        cli_adapter: BaseAdapter,
        web_adapter: BaseAdapter,
        strategy: RouterStrategy = None
    ):
        """
        初始化路由器

        Args:
            cli_adapter: CLI 适配器
            web_adapter: Web 适配器
            strategy: 路由策略（默认为混合策略）
        """
        self.cli_adapter = cli_adapter
        self.web_adapter = web_adapter
        self.strategy = strategy or HybridStrategy()

        self.logger = logging.getLogger(__name__)

        # 统计信息
        self._total_routes = 0
        self._cli_routes = 0
        self._web_routes = 0
        self._fallback_count = 0

    async def route(
        self,
        context: ExecutionContext
    ) -> RouteDecision:
        """
        路由任务到最优的适配器

        Args:
            context: 执行上下文

        Returns:
            RouteDecision: 路由决策
        """
        self._total_routes += 1

        # 检查 CLI 适配器可用性
        if not self.cli_adapter.is_available():
            self.logger.warning("CLI adapter unavailable, using Web adapter")
            self._web_routes += 1
            return RouteDecision(
                adapter=self.web_adapter,
                reason="cli_adapter_unavailable",
                fallback_available=False
            )

        # 获取进程池状态
        pool_health = self.cli_adapter.get_health()

        # 使用策略决策
        if isinstance(self.strategy, HybridStrategy):
            # 混合策略需要上下文信息
            should_use_cli, reason = self.strategy.should_use_cli(
                pool_health,
                context
            )
        else:
            # 其他策略只需要统计信息
            should_use_cli, reason = self.strategy.should_use_cli(pool_health)

        # 记录决策
        self.logger.info(
            f"Route decision: {'CLI' if should_use_cli else 'Web'} - {reason}"
        )

        if should_use_cli:
            self._cli_routes += 1
            return RouteDecision(
                adapter=self.cli_adapter,
                reason=reason,
                fallback_available=self.web_adapter.is_available()
            )
        else:
            self._web_routes += 1
            return RouteDecision(
                adapter=self.web_adapter,
                reason=reason,
                fallback_available=False
            )

    async def execute_with_routing(
        self,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        使用智能路由执行任务

        Args:
            context: 执行上下文

        Returns:
            ExecutionResult: 执行结果
        """
        # 获取路由决策
        decision = await self.route(context)

        self.logger.info(
            f"Routing decision: {decision.adapter.name} adapter, "
            f"reason: {decision.reason}"
        )

        # 执行任务
        start_time = datetime.now()

        try:
            result = await decision.adapter.execute(context)

            # 添加路由信息到结果
            if result.metadata is None:
                result.metadata = {}

            result.metadata.update({
                "router": self.strategy.name,
                "adapter_used": decision.adapter.name,
                "route_reason": decision.reason,
                "execution_time": result.execution_time
            })

            return result

        except Exception as e:
            self.logger.error(f"Execution error with {decision.adapter.name}: {e}")

            # 如果失败且有备用适配器，尝试降级
            if decision.fallback_available:
                self._fallback_count += 1
                self.logger.warning("Primary adapter failed, trying fallback")

                fallback_adapter = (
                    self.web_adapter if decision.adapter == self.cli_adapter
                    else self.cli_adapter
                )

                if fallback_adapter.is_available():
                    try:
                        result = await fallback_adapter.execute(context)

                        if result.metadata is None:
                            result.metadata = {}

                        result.metadata.update({
                            "router": f"{self.strategy.name}_fallback",
                            "adapter_used": fallback_adapter.name,
                            "route_reason": "primary_adapter_failed",
                            "execution_time": result.execution_time
                        })

                        return result

                    except Exception as fallback_error:
                        self.logger.error(f"Fallback also failed: {fallback_error}")

            # 返回错误结果
            return ExecutionResult(
                success=False,
                session_id=context.session_id,
                error=str(e)
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        获取路由器统计信息

        Returns:
            统计信息字典
        """
        return {
            "strategy": self.strategy.name,
            "total_routes": self._total_routes,
            "cli_routes": self._cli_routes,
            "web_routes": self._web_routes,
            "fallback_count": self._fallback_count,
            "cli_usage_rate": (
                self._cli_routes / self._total_routes
                if self._total_routes > 0 else 0
            ),
            "web_usage_rate": (
                self._web_routes / self._total_routes
                if self._total_routes > 0 else 0
            ),
            "fallback_rate": (
                self._fallback_count / self._total_routes
                if self._total_routes > 0 else 0
            ),
            "cli_adapter": self.cli_adapter.get_stats(),
            "web_adapter": self.web_adapter.get_stats(),
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._total_routes = 0
        self._cli_routes = 0
        self._web_routes = 0
        self._fallback_count = 0
