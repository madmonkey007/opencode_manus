"""
CLI 适配器实现

通过进程池执行任务
"""
import asyncio
import json
from typing import AsyncIterator, Dict, Any
from datetime import datetime
import logging

from .base import BaseAdapter, ExecutionContext, ExecutionResult, ExecutionEvent
from .base import AdapterUnavailableError, AdapterExecutionError

logger = logging.getLogger(__name__)


class CLIAdapter(BaseAdapter):
    """
    CLI 适配器

    使用进程池执行任务，提供更快的响应速度
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 CLI 适配器

        Args:
            config: 配置参数
                - pool_size: 进程池大小
                - server_url: Server API 地址
                - model: 使用的模型
                - health_check_interval: 健康检查间隔
        """
        super().__init__("cli", config)

        self.pool_size = config.get("pool_size", 2)
        self.server_url = config.get("server_url", "http://127.0.0.1:4096")
        self.model = config.get("model", "new-api/glm-4.7")

        # 进程池（延迟初始化）
        self._pool = None

        self.logger.info(f"CLIAdapter initialized: pool_size={self.pool_size}, model={self.model}")

    def _get_pool(self):
        """获取进程池实例"""
        if self._pool is None:
            from app.pool import CLIProcessPool

            self._pool = CLIProcessPool(
                pool_size=self.pool_size,
                server_url=self.server_url,
                model=self.model
            )
            self._pool.start()

        return self._pool

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        执行任务（非流式）

        Args:
            context: 执行上下文

        Returns:
            ExecutionResult: 执行结果
        """
        start_time = datetime.now()

        # 验证上下文
        is_valid, error = await self.validate_context(context)
        if not is_valid:
            return ExecutionResult(
                success=False,
                session_id=context.session_id,
                error=error
            )

        try:
            pool = self._get_pool()

            self.logger.info(f"Executing task via CLI pool: session={context.session_id}")

            # 提交任务到进程池
            result = pool.submit_task(
                prompt=context.prompt,
                mode=context.mode,
                context=context.context,
                timeout=300.0
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            if result.success:
                return ExecutionResult(
                    success=True,
                    session_id=context.session_id,
                    response=result.data.get("response") if result.data else None,
                    events=result.data.get("events", []) if result.data else [],
                    metadata={
                        "execution_engine": "cli_pool",
                        "process_id": result.data.get("process_id") if result.data else None
                    },
                    execution_time=execution_time
                )
            else:
                return ExecutionResult(
                    success=False,
                    session_id=context.session_id,
                    error=result.error,
                    execution_time=execution_time
                )

        except Exception as e:
            self.logger.error(f"CLI execution error: {e}")
            return ExecutionResult(
                success=False,
                session_id=context.session_id,
                error=str(e)
            )

    async def execute_stream(
        self,
        context: ExecutionContext
    ) -> AsyncIterator[ExecutionEvent]:
        """
        执行任务（流式）

        CLI 进程池的流式实现

        Args:
            context: 执行上下文

        Yields:
            ExecutionEvent: 执行事件
        """
        # 验证上下文
        is_valid, error = await self.validate_context(context)
        if not is_valid:
            yield ExecutionEvent(
                event_type="error",
                data={"error": error}
            )
            return

        proc_info = None
        try:
            pool = self._get_pool()

            self.logger.info(f"Executing stream task via CLI pool: session={context.session_id}")

            # 获取空闲进程
            proc_info = pool.get_idle_process()

            if proc_info is None:
                yield ExecutionEvent(
                    event_type="error",
                    data={"error": "No available process in pool"}
                )
                return

            # 标记进程为繁忙
            proc_info.is_busy = True

            # 构建JSON-RPC请求
            request = {
                "jsonrpc": "2.0",
                "id": context.session_id,
                "method": "execute_stream",
                "params": {
                    "prompt": context.prompt,
                    "mode": context.mode,
                    **context.context
                }
            }

            # 发送请求
            proc_info.process.stdin.write(json.dumps(request) + "\n")
            proc_info.process.stdin.flush()

            # 读取流式响应
            import time
            start_time = time.time()
            timeout = 300.0

            while time.time() - start_time < timeout:
                try:
                    line = proc_info.process.stdout.readline()
                    if not line:
                        break

                    # 解析JSON事件
                    try:
                        event_data = json.loads(line.strip())

                        # 转换为ExecutionEvent
                        yield ExecutionEvent(
                            event_type=event_data.get("type", "unknown"),
                            data=event_data
                        )

                        # 如果是完成事件，结束流
                        if event_data.get("type") == "complete":
                            break

                    except json.JSONDecodeError:
                        # 可能是日志或其他输出
                        continue

                except Exception as e:
                    self.logger.error(f"Error reading stream: {e}")
                    break

        except Exception as e:
            self.logger.error(f"CLI stream error: {e}")
            yield ExecutionEvent(
                event_type="error",
                data={"error": str(e)}
            )
        finally:
            # 修复：确保释放进程
            if proc_info:
                proc_info.is_busy = False

    def is_available(self) -> bool:
        """
        检查适配器是否可用

        Returns:
            bool: 是否可用
        """
        try:
            if self._pool is None:
                return True  # 延迟初始化，返回True

            stats = self._pool.get_stats()
            return stats["healthy_processes"] > 0

        except Exception:
            return False

    def get_health(self) -> Dict[str, Any]:
        """
        获取适配器健康状态

        Returns:
            健康状态字典
        """
        if self._pool is None:
            return {
                "status": "not_initialized",
                "pool_size": self.pool_size,
                "model": self.model
            }

        stats = self._pool.get_stats()

        return {
            "status": "running",
            "pool_size": self.pool_size,
            "model": self.model,
            "active_processes": stats["active_processes"],
            "healthy_processes": stats["healthy_processes"],
            "idle_processes": stats["idle_processes"],
            "total_tasks": stats["total_tasks_completed"]
        }

    async def close(self) -> None:
        """关闭适配器，释放资源"""
        if self._pool is not None:
            self._pool.stop()
            self._pool = None
            self.logger.info("CLIAdapter closed")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()
