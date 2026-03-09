"""
OpenCodeServerManager - 管理持久的 opencode serve 服务器

功能：
1. 启动和管理 opencode serve 持久化服务器
2. 提供 HTTP API 调用接口
3. 懒加载初始化，避免阻塞主线程
4. 自动服务器健康检查和重启
"""

import asyncio
import subprocess
import logging
import httpx
import os
import uuid
import json
from typing import Optional, Dict, Any, List

logger = logging.getLogger("opencode")


class OpenCodeServerManager:
    """
    管理持久的 opencode serve 服务器

    实现懒加载：首次请求时才启动服务器，不阻塞主线程
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4096,
        model: str = "new-api/glm-4.7",
        workspace: str = "/app/opencode/workspace",
    ):
        # 参数验证
        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {port}")

        if not host:
            raise ValueError("Host cannot be empty")

        if not model:
            raise ValueError("Model cannot be empty")

        self.host = host
        self.port = port
        self.model = model
        self.workspace = workspace

        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{host}:{port}"
        self.is_running = False
        self.startup_lock = asyncio.Lock()

    async def start(self, max_retries: int = 3) -> bool:
        """
        启动 opencode serve 服务器（懒加载）

        使用 Lock 确保线程安全
        """
        async with self.startup_lock:
            # 检查是否已经运行
            if self.is_running and await self._check_health():
                logger.info(f"OpenCode server already running at {self.base_url}")
                return True

            # 尝试启动服务器（带重试机制）
            logger.info(f"Starting OpenCode server at {self.base_url}...")

            for attempt in range(max_retries):
                if attempt > 0:
                    logger.info(f"Retry {attempt + 1}/{max_retries} starting server...")
                    await asyncio.sleep(2 ** attempt)  # 指数退避

                if await self._start_server():
                    # ✅ 在锁内设置状态，避免竞态条件
                    self.is_running = True
                    logger.info(f"✅ OpenCode server started successfully at {self.base_url}")
                    return True

            logger.error(f"Failed to start server after {max_retries} attempts")
            return False

    async def _start_server(self) -> bool:
        """启动 opencode serve 进程"""
        try:
            # 构建命令
            cmd = [
                "opencode",
                "serve",
                "--port", str(self.port),
                "--hostname", self.host,
                "--log-level", "INFO",
            ]

            # 设置环境变量
            env = os.environ.copy()

            # 使用 config_host
            patched_config = "/app/opencode/config_host/opencode.json"
            if not os.path.exists(patched_config):
                patched_config = "config_host/opencode.json"

            if os.path.exists(patched_config):
                patched_config = os.path.abspath(patched_config)
                env["OPENCODE_CONFIG_FILE"] = patched_config
                logger.info(f"Using config: {patched_config}")

            # 启动进程（后台，不阻塞）
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                bufsize=1,
                universal_newlines=True,
            )

            # 等待服务器启动（最多30秒）
            for i in range(30):
                await asyncio.sleep(1)
                if await self._check_health():
                    self.is_running = True
                    logger.info(f"✅ OpenCode server started successfully at {self.base_url}")
                    return True

                # 检查进程是否崩溃
                if self.process.poll() is not None:
                    logger.error(f"OpenCode server process exited unexpectedly")
                    return False

            # 超时
            logger.error(f"Timeout waiting for OpenCode server to start")
            self._stop_process()
            return False

        except FileNotFoundError as e:
            logger.error(f"opencode executable not found: {e}")
            return False
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return False
        except OSError as e:
            if "Address already in use" in str(e) or "port" in str(e).lower():
                logger.error(f"Port {self.port} is already in use or unavailable")
            else:
                logger.error(f"OS error starting server: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error starting server: {e}", exc_info=True)
            return False

    async def _check_health(self) -> bool:
        """检查服务器健康状态"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/opencode/health")
                return response.status_code == 200
        except httpx.ConnectTimeout:
            logger.debug(f"Health check timeout")
            return False
        except httpx.ConnectError as e:
            logger.debug(f"Health check connection error: {e}")
            return False
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def _stop_process(self):
        """停止服务器进程"""
        if not self.process:
            return

        try:
            # 1. 先尝试优雅终止
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
                logger.info(f"Process terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(f"Process did not terminate gracefully, forcing kill")
                # 2. 强制终止（kill() 后备方案）
                self.process.kill()
                self.process.wait(timeout=3)
                logger.info(f"Process killed forcefully")
        except Exception as e:
            logger.error(f"Error stopping process: {e}")
        finally:
            self.process = None

    async def execute(self, session_id: str, prompt: str, mode: str = "auto") -> str:
        """
        通过 HTTP API 执行任务（替代 opencode run）

        Args:
            session_id: 会话ID（必需）
            prompt: 用户提示词
            mode: 运行模式 (auto, plan, build)

        Returns:
            执行结果（JSON字符串）
        """
        # 确保服务器已启动
        if not await self.start():
            raise RuntimeError("Failed to start OpenCode server")

        # 使用正确的 API 端点：/opencode/session/{session_id}/message
        url = f"{self.base_url}/opencode/session/{session_id}/message"

        # 生成消息ID
        import uuid
        message_id = f"msg_{uuid.uuid4().hex[:12]}"

        # 构建请求
        payload = {
            "message_id": message_id,
            "mode": mode,
            "provider_id": "anthropic",  # 默认使用 Anthropic
            "model_id": self.model,
            "parts": [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }

        # 发送请求
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as e:
            logger.error(f"HTTP request failed: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        if not await self.start():
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 使用正确的 API 端点：/opencode/session/{session_id}
                response = await client.get(f"{self.base_url}/opencode/session/{session_id}")
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None

    async def stop(self):
        """停止服务器"""
        logger.info("Stopping OpenCode server...")
        self._stop_process()
        self.is_running = False
