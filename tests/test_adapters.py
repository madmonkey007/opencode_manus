"""
适配器层单元测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.gateway.adapters.base import (
    BaseAdapter,
    ExecutionContext,
    ExecutionEvent,
    ExecutionResult,
    AdapterError,
    AdapterUnavailableError
)
from app.gateway.adapters.web_adapter import WebAdapter
from app.gateway.adapters.cli_adapter import CLIAdapter


class TestExecutionContext:
    """执行上下文测试"""

    def test_create_context(self):
        """测试创建上下文"""
        context = ExecutionContext(
            session_id="test-session",
            prompt="测试任务",
            mode="build"
        )

        assert context.session_id == "test-session"
        assert context.prompt == "测试任务"
        assert context.mode == "build"

    def test_context_with_defaults(self):
        """测试上下文默认值"""
        context = ExecutionContext(
            session_id="test-session",
            prompt="测试任务"
        )

        assert context.mode == "auto"
        assert context.context == {}
        assert context.metadata == {}


class TestExecutionEvent:
    """执行事件测试"""

    def test_create_event(self):
        """测试创建事件"""
        event = ExecutionEvent(
            event_type="phase",
            data={"phase": "planning"}
        )

        assert event.event_type == "phase"
        assert event.data["phase"] == "planning"
        assert isinstance(event.timestamp, datetime.datetime)


class TestExecutionResult:
    """执行结果测试"""

    def test_create_success_result(self):
        """测试创建成功结果"""
        result = ExecutionResult(
            success=True,
            session_id="test-session",
            response="任务完成"
        )

        assert result.success is True
        assert result.response == "任务完成"
        assert result.error is None

    def test_create_error_result(self):
        """测试创建错误结果"""
        result = ExecutionResult(
            success=False,
            session_id="test-session",
            error="执行失败"
        )

        assert result.success is False
        assert result.error == "执行失败"
        assert result.response is None


class TestWebAdapter:
    """Web 适配器测试"""

    @pytest.fixture
    def web_adapter(self):
        """创建 Web 适配器实例"""
        config = {
            "server_url": "http://test.example.com",
            "timeout": 100,
            "api_key": "test-key"
        }
        return WebAdapter(config=config)

    def test_init(self, web_adapter):
        """测试初始化"""
        assert web_adapter.name == "web"
        assert web_adapter.server_url == "http://test.example.com"
        assert web_adapter.timeout == 100
        assert web_adapter.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_validate_context_valid(self, web_adapter):
        """测试验证上下文（有效）"""
        context = ExecutionContext(
            session_id="test-session",
            prompt="测试任务",
            mode="build"
        )

        is_valid, error = await web_adapter.validate_context(context)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_context_invalid_no_session(self, web_adapter):
        """测试验证上下文（无会话ID）"""
        context = ExecutionContext(
            session_id="",
            prompt="测试任务"
        )

        is_valid, error = await web_adapter.validate_context(context)

        assert is_valid is False
        assert "Session ID is required" in error

    @pytest.mark.asyncio
    async def test_validate_context_invalid_no_prompt(self, web_adapter):
        """测试验证上下文（无提示词）"""
        context = ExecutionContext(
            session_id="test-session",
            prompt=""
        )

        is_valid, error = await web_adapter.validate_context(context)

        assert is_valid is False
        assert "Prompt is required" in error

    @pytest.mark.asyncio
    async def test_validate_context_invalid_mode(self, web_adapter):
        """测试验证上下文（无效模式）"""
        context = ExecutionContext(
            session_id="test-session",
            prompt="测试任务",
            mode="invalid"
        )

        is_valid, error = await web_adapter.validate_context(context)

        assert is_valid is False
        assert "Invalid mode" in error

    def test_get_stats(self, web_adapter):
        """测试获取统计信息"""
        stats = web_adapter.get_stats()

        assert stats["name"] == "web"
        assert stats["type"] == "WebAdapter"


class TestCLIAdapter:
    """CLI 适配器测试"""

    @pytest.fixture
    def cli_adapter(self):
        """创建 CLI 适配器实例"""
        config = {
            "pool_size": 2,
            "server_url": "http://test.example.com",
            "model": "test-model"
        }
        return CLIAdapter(config=config)

    def test_init(self, cli_adapter):
        """测试初始化"""
        assert cli_adapter.name == "cli"
        assert cli_adapter.pool_size == 2
        assert cli_adapter.model == "test-model"

    @pytest.mark.asyncio
    async def test_validate_context_valid(self, cli_adapter):
        """测试验证上下文（有效）"""
        context = ExecutionContext(
            session_id="test-session",
            prompt="测试任务",
            mode="plan"
        )

        is_valid, error = await cli_adapter.validate_context(context)

        assert is_valid is True
        assert error is None

    def test_get_stats_not_initialized(self, cli_adapter):
        """测试获取统计信息（未初始化）"""
        stats = cli_adapter.get_stats()

        assert stats["status"] == "not_initialized"
        assert stats["pool_size"] == 2


class TestAdapterFactory:
    """适配器工厂测试"""

    def test_create_web_adapter(self):
        """测试创建 Web 适配器"""
        from app.gateway.adapters import create_adapter

        adapter = create_adapter("web", config={"server_url": "http://test.com"})

        assert isinstance(adapter, WebAdapter)
        assert adapter.name == "web"

    def test_create_cli_adapter(self):
        """测试创建 CLI 适配器"""
        from app.gateway.adapters import create_adapter

        adapter = create_adapter("cli", config={"pool_size": 2})

        assert isinstance(adapter, CLIAdapter)
        assert adapter.name == "cli"

    def test_create_unsupported_adapter(self):
        """测试创建不支持的适配器"""
        from app.gateway.adapters import create_adapter

        with pytest.raises(ValueError) as exc_info:
            create_adapter("unsupported")

        assert "Unsupported adapter type" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
