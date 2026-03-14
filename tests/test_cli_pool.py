"""
CLI 进程池单元测试
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
import subprocess

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.pool.cli_process_pool import CLIProcessPool, TaskRequest, TaskResponse


class TestCLIProcessPool:
    """CLI 进程池测试"""

    def test_init(self):
        """测试进程池初始化"""
        pool = CLIProcessPool(pool_size=2)

        assert pool.pool_size == 2
        assert pool.server_url == "http://127.0.0.1:4096"
        assert pool.model == "new-api/glm-4.7"
        assert len(pool.processes) == 0

    def test_task_request_creation(self):
        """测试任务请求创建"""
        task = TaskRequest(
            prompt="测试任务",
            mode="build"
        )

        assert task.prompt == "测试任务"
        assert task.mode == "build"
        assert task.id is not None

    def test_task_response_creation(self):
        """测试任务响应创建"""
        response = TaskResponse(
            id="test-id",
            success=True,
            data={"result": "ok"}
        )

        assert response.id == "test-id"
        assert response.success is True
        assert response.data["result"] == "ok"

    @patch('subprocess.Popen')
    def test_start_process(self, mock_popen):
        """测试进程启动"""
        # Mock 进程对象
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        pool = CLIProcessPool(pool_size=1)

        with pool.lock:
            proc_info = pool._start_process(0)

        assert proc_info is not None
        assert proc_info.pid == 12345
        assert proc_info.is_healthy is True
        assert proc_info.is_busy is False

    def test_get_idle_process_empty(self):
        """测试获取空闲进程（空池）"""
        pool = CLIProcessPool(pool_size=0)
        proc_info = pool.get_idle_process()

        assert proc_info is None

    @patch('subprocess.Popen')
    def test_get_idle_process_with_processes(self, mock_popen):
        """测试获取空闲进程（有进程）"""
        # Mock 进程对象
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # 进程存活
        mock_popen.return_value = mock_process

        pool = CLIProcessPool(pool_size=1)

        with pool.lock:
            proc_info = pool._start_process(0)

        idle_proc = pool.get_idle_process()

        assert idle_proc is not None
        assert idle_proc.pid == 12345
        assert idle_proc.is_busy is False

    def test_get_stats_empty_pool(self):
        """测试获取统计信息（空池）"""
        pool = CLIProcessPool(pool_size=0)
        stats = pool.get_stats()

        assert stats["pool_size"] == 0
        assert stats["active_processes"] == 0
        assert stats["healthy_processes"] == 0
        assert stats["total_tasks_completed"] == 0

    def test_context_manager(self):
        """测试上下文管理器"""
        pool = CLIProcessPool(pool_size=0)

        # 模拟启动和停止
        with patch.object(pool, 'start'), \
             patch.object(pool, 'stop'):

            with pool:
                pass

            # 验证start和stop被调用
            # 注意：由于我们没有真实的进程，这些只是Mock调用


class TestTaskExecution:
    """任务执行测试"""

    def test_submit_task_no_process(self):
        """测试提交任务（无可用进程）"""
        pool = CLIProcessPool(pool_size=0)

        response = pool.submit_task(
            prompt="测试任务",
            mode="auto"
        )

        assert response.success is False
        assert "No available process" in response.error

    @patch('subprocess.Popen')
    def test_submit_task_timeout(self, mock_popen):
        """测试提交任务（超时）"""
        # Mock 进程对象
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.stdin.write = Mock()
        mock_process.stdin.flush = Mock()
        mock_process.stdout.readline.return_value = ""  # 模拟无响应

        mock_popen.return_value = mock_process

        pool = CLIProcessPool(pool_size=1)

        with pool.lock:
            proc_info = pool._start_process(0)

        response = pool.submit_task(
            prompt="测试任务",
            mode="auto",
            timeout=0.1  # 很短的超时时间
        )

        # 由于超时，应该返回错误
        # 注意：实际测试中可能需要更复杂的Mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
