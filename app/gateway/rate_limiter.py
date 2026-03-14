"""
OpenCode 限流控制模块

使用令牌桶算法实现多层限流：
- 用户级限流
- 渠道级限流
- 全局限流
"""
import asyncio
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================================
# 限流异常
# ============================================================================

class RateLimitError(Exception):
    """限流错误"""

    def __init__(self, key: str, limit: int, window: int, retry_after: float):
        """
        初始化限流错误

        Args:
            key: 限流键
            limit: 限制数量
            window: 时间窗口（秒）
            retry_after: 重试时间（秒）
        """
        self.key = key
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for {key}: "
            f"{limit} requests per {window}s. "
            f"Retry after {retry_after:.1f}s"
        )


# ============================================================================
# 令牌桶
# ============================================================================

@dataclass
class TokenBucket:
    """令牌桶（线程安全版本）"""
    capacity: int  # 桶容量
    tokens: float  # 当前令牌数
    rate: float  # 令牌补充速率（令牌/秒）
    last_update: float  # 最后更新时间（时间戳）
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __init__(self, capacity: int, rate: float):
        """
        初始化令牌桶

        Args:
            capacity: 桶容量（最大令牌数）
            rate: 令牌补充速率（令牌/秒）
        """
        self.capacity = capacity
        self.tokens = float(capacity)
        self.rate = rate
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        """
        消费令牌（线程安全）

        Args:
            tokens: 需要消费的令牌数

        Returns:
            是否成功消费
        """
        async with self._lock:  # 保护临界区
            # 补充令牌
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            # 检查是否有足够的令牌
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def get_retry_after(self, tokens: int = 1) -> float:
        """
        获取重试时间（线程安全）

        Args:
            tokens: 需要的令牌数

        Returns:
            重试时间（秒）
        """
        async with self._lock:
            # 补充令牌
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            # 计算需要等待的时间
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.rate if tokens_needed > 0 else 0

    async def peek(self) -> int:
        """查看当前令牌数（线程安全）"""
        async with self._lock:
            # 补充令牌
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            return int(self.tokens)


# ============================================================================
# 限流器
# ============================================================================

class RateLimiter:
    """
    限流器

    使用令牌桶算法实现多层限流
    """

    def __init__(
        self,
        default_limit: int = 100,
        default_window: int = 60,
        cleanup_interval: int = 300
    ):
        """
        初始化限流器

        Args:
            default_limit: 默认限流值
            default_window: 默认时间窗口（秒）
            cleanup_interval: 清理间隔（秒）
        """
        self.default_limit = default_limit
        self.default_window = default_window

        # 存储令牌桶
        # 格式: {key: TokenBucket}
        self._buckets: Dict[str, TokenBucket] = {}

        # 清理任务
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None

        self.logger = logging.getLogger(__name__)
        self.logger.info("RateLimiter initialized")

    async def start(self) -> None:
        """启动限流器"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info("RateLimiter started")

    async def stop(self) -> None:
        """停止限流器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            self.logger.info("RateLimiter stopped")

    async def check_limit(
        self,
        key: str,
        limit: int = None,
        window: int = None
    ) -> None:
        """
        检查限流（线程安全）

        Args:
            key: 限流键（如 user:123, global, etc）
            limit: 限制数量（默认使用 default_limit）
            window: 时间窗口（秒，默认使用 default_window）

        Raises:
            RateLimitError: 超过限流
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        # 获取或创建令牌桶
        bucket = self._get_or_create_bucket(key, limit, window)

        # 尝试消费令牌
        if not await bucket.consume(1):
            retry_after = await bucket.get_retry_after(1)
            raise RateLimitError(key, limit, window, retry_after)

    async def check_multi_limit(
        self,
        limits: Dict[str, int]
    ) -> None:
        """
        检查多层限流

        Args:
            limits: 限流字典 {key: limit}

        Raises:
            RateLimitError: 超过任意限流
        """
        for key, limit in limits.items():
            await self.check_limit(key, limit)

    def _get_or_create_bucket(
        self,
        key: str,
        limit: int,
        window: int
    ) -> TokenBucket:
        """
        获取或创建令牌桶

        Args:
            key: 限流键
            limit: 限制数量
            window: 时间窗口

        Returns:
            TokenBucket
        """
        if key not in self._buckets:
            # 计算令牌补充速率
            rate = limit / window

            self._buckets[key] = TokenBucket(
                capacity=limit,
                rate=rate
            )

        return self._buckets[key]

    async def _cleanup_loop(self) -> None:
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                self._cleanup()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")

    def _cleanup(self) -> None:
        """清理过期的令牌桶"""
        # 清理超过1小时未使用的令牌桶
        now = time.time()
        expired_keys = []

        for key, bucket in self._buckets.items():
            # 如果桶是满的且超过1小时未使用，删除
            if bucket.tokens >= bucket.capacity:
                idle_time = now - bucket.last_update
                if idle_time > 3600:  # 1小时
                    expired_keys.append(key)

        for key in expired_keys:
            del self._buckets[key]
            self.logger.debug(f"Cleaned up expired bucket: {key}")

        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired buckets")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取限流器统计信息

        Returns:
            统计信息字典
        """
        total_buckets = len(self._buckets)

        # 统计每个桶的状态
        bucket_stats = []
        for key, bucket in list(self._buckets.items())[:10]:  # 只显示前10个
            bucket_stats.append({
                "key": key,
                "tokens": bucket.peek(),
                "capacity": bucket.capacity
            })

        return {
            "total_buckets": total_buckets,
            "sample_buckets": bucket_stats,
            "default_limit": self.default_limit,
            "default_window": self.default_window
        }

    def reset(self) -> None:
        """重置所有令牌桶"""
        self._buckets.clear()
        self.logger.info("All buckets reset")


# ============================================================================
# 限流配置
# ============================================================================

@dataclass
class RateLimitConfig:
    """限流配置"""
    user_limit: int = 100  # 用户级限流（请求/分钟）
    user_window: int = 60  # 用户级时间窗口
    channel_limit: int = 1000  # 渠道级限流（请求/分钟）
    channel_window: int = 60  # 渠道级时间窗口
    global_limit: int = 10000  # 全局限流（请求/分钟）
    global_window: int = 60  # 全局时间窗口

    def get_user_limits(self, user_id: str, channel: str = "web") -> Dict[str, int]:
        """
        获取用户级限流

        Args:
            user_id: 用户ID
            channel: 渠道（web, cli, mobile, api）

        Returns:
            限流字典
        """
        limits = {
            f"user:{user_id}": self.user_limit,
            f"channel:{channel}": self.channel_limit,
            "global": self.global_limit
        }

        # CLI 渠道有更高的限流
        if channel == "cli":
            limits[f"user:{user_id}"] = self.user_limit * 10

        return limits


# ============================================================================
# 辅助函数
# ============================================================================

async def check_rate_limit(
    rate_limiter: RateLimiter,
    user_id: str,
    channel: str = "web",
    config: RateLimitConfig = None
) -> None:
    """
    检查多层限流

    Args:
        rate_limiter: 限流器
        user_id: 用户ID
        channel: 渠道
        config: 限流配置

    Raises:
        RateLimitError: 超过限流
    """
    config = config or RateLimitConfig()

    limits = config.get_user_limits(user_id, channel)

    await rate_limiter.check_multi_limit(limits)
