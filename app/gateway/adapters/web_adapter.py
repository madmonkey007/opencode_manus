"""
Web 适配器实现

通过 Server API 执行任务
"""
import asyncio
import httpx
from typing import AsyncIterator, Dict, Any
from datetime import datetime
import logging

from .base import BaseAdapter, ExecutionContext, ExecutionResult, ExecutionEvent
from .base import AdapterUnavailableError, AdapterExecutionError

logger = logging.getLogger(__name__)


class WebAdapter(BaseAdapter):
    """
    Web 适配器

    使用 Server API 执行任务
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 Web 适配器

        Args:
            config: 配置参数
                - server_url: Server API 地址
                - timeout: 请求超时时间（秒）
                - api_key: API 密钥（可选）
        """
        super().__init__("web", config)

        self.server_url = config.get("server_url", "http://127.0.0.1:4096")
        self.timeout = config.get("timeout", 300)
        self.api_key = config.get("api_key")

        # HTTP 客户端
        self._client: httpx.AsyncClient = None

        self.logger.info(f"WebAdapter initialized: server={self.server_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建HTTP客户端"""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.server_url,
                timeout=self.timeout,
                headers=headers
            )

        return self._client

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
            client = await self._get_client()

            # 构建请求数据
            request_data = {
                "title": context.prompt[:100],  # 标题限制
                "mode": context.mode,
                **context.context
            }

            # 发送请求
            self.logger.info(f"Executing task via Server API: session={context.session_id}")

            response = await client.post(
                f"/opencode/session/{context.session_id}/submit",
                json=request_data
            )

            response.raise_for_status()

            result_data = response.json()

            execution_time = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(
                success=True,
                session_id=context.session_id,
                response=result_data.get("response"),
                events=result_data.get("events", []),
                metadata=result_data.get("metadata", {}),
                execution_time=execution_time
            )

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error: {e}")
            raise AdapterExecutionError(
                self.name,
                f"HTTP error: {str(e)}",
                context
            )

        except Exception as e:
            self.logger.error(f"Execution error: {e}")
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

        try:
            client = await self._get_client()

            # 构建请求数据
            request_data = {
                "title": context.prompt[:100],
                "mode": context.mode,
                **context.context
            }

            self.logger.info(f"Executing stream task: session={context.session_id}")

            # 发送流式请求
            async with client.stream(
                "POST",
                f"/opencode/session/{context.session_id}/stream",
                json=request_data,
                timeout=self.timeout
            ) as response:
                response.raise_for_status()

                # 读取SSE事件
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]  # 移除 "data: " 前缀

                        try:
                            import json
                            event_data = json.loads(data_str)

                            yield ExecutionEvent(
                                event_type=event_data.get("type", "unknown"),
                                data=event_data
                            )

                        except json.JSONDecodeError:
                            self.logger.warning(f"Invalid JSON in event: {data_str}")

        except httpx.HTTPError as e:
            self.logger.error(f"Stream HTTP error: {e}")
            yield ExecutionEvent(
                event_type="error",
                data={"error": f"HTTP error: {str(e)}"}
            )

        except Exception as e:
            self.logger.error(f"Stream error: {e}")
            yield ExecutionEvent(
                event_type="error",
                data={"error": str(e)}
            )

    def is_available(self) -> bool:
        """
        检查适配器是否可用

        Returns:
            bool: 是否可用
        """
        # 简单检查：如果能ping通server就认为可用
        try:
            import socket
            host = self.server_url.split("://")[1].split(":")[0]
            port = int(self.server_url.split(":")[-1].split("/")[0])

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            return result == 0

        except Exception:
            return False

    def get_health(self) -> Dict[str, Any]:
        """
        获取适配器健康状态

        Returns:
            健康状态字典
        """
        return {
            "server_url": self.server_url,
            "timeout": self.timeout,
            "has_api_key": bool(self.api_key),
            "client_active": self._client is not None and not self._client.is_closed
        }

    async def close(self) -> None:
        """关闭适配器，释放资源"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self.logger.info("WebAdapter closed")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()
