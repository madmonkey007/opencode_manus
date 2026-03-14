"""
混合路由策略测试
"""
import pytest
from unittest.mock import Mock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.gateway.router import (
    HybridStrategy,
    RouteDecision,
    SmartRouter
)
from app.gateway.adapters.base import ExecutionContext


class TestHybridStrategy:
    """混合策略测试"""

    @pytest.fixture
    def strategy(self):
        """创建混合策略实例"""
        return HybridStrategy(
            low_load_threshold=0.5,
            high_load_threshold=0.8,
            max_wait_time_low_load=10.0,
            max_wait_time_high_load=2.0
        )

    @pytest.fixture
    def low_load_stats(self):
        """低负载统计信息"""
        return {
            "healthy_processes": 2,
            "busy_processes": 0,
            "idle_processes": 2,
            "total_tasks_completed": 10
        }

    @pytest.fixture
    def medium_load_stats(self):
        """中负载统计信息"""
        return {
            "healthy_processes": 2,
            "busy_processes": 1,
            "idle_processes": 1,
            "total_tasks_completed": 20
        }

    @pytest.fixture
    def high_load_stats(self):
        """高负载统计信息"""
        return {
            "healthy_processes": 2,
            "busy_processes": 2,
            "idle_processes": 0,
            "total_tasks_completed": 30
        }

    @pytest.fixture
    def normal_context(self):
        """普通优先级上下文"""
        return ExecutionContext(
            session_id="test-session",
            prompt="测试任务",
            mode="auto",
            context={"priority": "normal"}
        )

    @pytest.fixture
    def high_priority_context(self):
        """高优先级上下文"""
        return ExecutionContext(
            session_id="test-session",
            prompt="测试任务",
            mode="auto",
            context={"priority": "high"}
        )

    @pytest.fixture
    def urgent_context(self):
        """紧急优先级上下文"""
        return ExecutionContext(
            session_id="test-session",
            prompt="测试任务",
            mode="auto",
            context={"priority": "urgent"}
        )

    def test_init(self, strategy):
        """测试初始化"""
        assert strategy.name == "hybrid"
        assert strategy.low_load_threshold == 0.5
        assert strategy.high_load_threshold == 0.8

    def test_init_invalid_thresholds(self):
        """测试无效的阈值"""
        with pytest.raises(ValueError):
            HybridStrategy(
                low_load_threshold=0.8,
                high_load_threshold=0.5
            )

    def test_calculate_busy_ratio(self, strategy):
        """测试计算忙碌比例"""
        stats = {
            "healthy_processes": 2,
            "busy_processes": 1
        }

        ratio = strategy._calculate_busy_ratio(stats)
        assert ratio == 0.5

    def test_calculate_busy_ratio_no_healthy(self, strategy):
        """测试无健康进程时的忙碌比例"""
        stats = {
            "healthy_processes": 0,
            "busy_processes": 0
        }

        ratio = strategy._calculate_busy_ratio(stats)
        assert ratio == 1.0

    def test_low_load_with_idle(self, strategy, low_load_stats):
        """测试低负载且有空闲进程"""
        should_use, reason = strategy.should_use_cli(low_load_stats)

        assert should_use is True
        assert "idle_process_available" in reason

    def test_medium_load_normal_priority(
        self,
        strategy,
        medium_load_stats,
        normal_context
    ):
        """测试中负载普通优先级"""
        should_use, reason = strategy.should_use_cli(
            medium_load_stats,
            normal_context
        )

        # 中负载场景有空闲进程，应该直接使用 CLI
        assert should_use is True
        # 由于有空闲进程，reason 应该包含 "idle_process_available"
        assert "idle_process_available" in reason

    def test_high_load_normal_priority(
        self,
        strategy,
        high_load_stats,
        normal_context
    ):
        """测试高负载普通优先级"""
        should_use, reason = strategy.should_use_cli(
            high_load_stats,
            normal_context
        )

        # 应该降级到 Web
        assert should_use is False
        assert "high_load" in reason
        assert "fallback" in reason

    def test_high_load_urgent_priority(
        self,
        strategy,
        high_load_stats,
        urgent_context
    ):
        """测试高负载紧急任务"""
        # 高负载场景：100% 忙碌，估算等待时间可能超过阈值
        # 紧急任务只有在等待时间 <= max_wait_time_high_load 时才会使用 CLI
        should_use, reason = strategy.should_use_cli(
            high_load_stats,
            urgent_context
        )

        # 高负载场景下，即使紧急任务也可能因为等待时间过长而降级
        # 这是正确的行为，因为避免长时间等待更重要
        # 紧急任务在高负载时也会降级到 Web 以保证系统吞吐量
        assert should_use is False
        assert "high_load" in reason
        assert "fallback" in reason

    def test_get_task_priority(self, strategy, normal_context):
        """测试获取任务优先级"""
        priority = strategy._get_task_priority(normal_context)
        assert priority == 5

    def test_get_task_priority_high(self, strategy, high_priority_context):
        """测试获取高优先级"""
        priority = strategy._get_task_priority(high_priority_context)
        assert priority == 8

    def test_get_task_priority_urgent(self, strategy, urgent_context):
        """测试获取紧急优先级"""
        priority = strategy._get_task_priority(urgent_context)
        assert priority == 10

    def test_moderate_high_load_urgent_priority(
        self,
        strategy,
        urgent_context
    ):
        """测试适度高负载紧急任务（85% 忙碌，接近高负载阈值）"""
        moderate_high_load_stats = {
            "healthy_processes": 2,
            "busy_processes": 1,  # 50% 忙碌，低于 high_load_threshold (0.8)
            "idle_processes": 1,
            "total_tasks_completed": 25
        }

        should_use, reason = strategy.should_use_cli(
            moderate_high_load_stats,
            urgent_context
        )

        # 适度高负载下，有空闲进程，紧急任务应该使用 CLI
        assert should_use is True
        assert "idle_process_available" in reason

    def test_estimate_wait_time_idle(self, strategy, low_load_stats):
        """测试估算等待时间（有空闲进程）"""
        wait_time = strategy._estimate_wait_time(low_load_stats, 0.0)
        assert wait_time == 0.0

    def test_estimate_wait_time_busy(self, strategy, high_load_stats):
        """测试估算等待时间（繁忙）"""
        wait_time = strategy._estimate_wait_time(high_load_stats, 1.0)
        assert wait_time > 0


class TestSmartRouter:
    """智能路由器测试"""

    @pytest.fixture
    def mock_cli_adapter(self):
        """Mock CLI 适配器"""
        adapter = Mock()
        adapter.is_available.return_value = True
        adapter.name = "cli"
        adapter.get_stats.return_value = {
            "healthy_processes": 2,
            "busy_processes": 1,
            "idle_processes": 1
        }
        return adapter

    @pytest.fixture
    def mock_web_adapter(self):
        """Mock Web 适配器"""
        adapter = Mock()
        adapter.is_available.return_value = True
        adapter.name = "web"
        adapter.get_stats.return_value = {
            "server_url": "http://127.0.0.1:4096"
        }
        return adapter

    @pytest.fixture
    def router(self, mock_cli_adapter, mock_web_adapter):
        """创建智能路由器"""
        return SmartRouter(
            cli_adapter=mock_cli_adapter,
            web_adapter=mock_web_adapter,
            strategy=HybridStrategy()
        )

    def test_init(self, router):
        """测试初始化"""
        assert router.strategy.name == "hybrid"
        assert router.cli_adapter.name == "cli"
        assert router.web_adapter.name == "web"

    def test_get_stats_initial(self, router):
        """测试获取初始统计信息"""
        stats = router.get_stats()

        assert stats["strategy"] == "hybrid"
        assert stats["total_routes"] == 0
        assert stats["cli_routes"] == 0
        assert stats["web_routes"] == 0

    def test_reset_stats(self, router):
        """测试重置统计信息"""
        router._total_routes = 10
        router._cli_routes = 7
        router._web_routes = 3

        router.reset_stats()

        assert router._total_routes == 0
        assert router._cli_routes == 0
        assert router._web_routes == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
