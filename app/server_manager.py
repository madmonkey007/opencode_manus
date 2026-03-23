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
import time
import signal
import platform
from typing import Optional, Dict, Any, List, AsyncGenerator

# Windows does not support the resource module
if platform.system() != "Windows":
    import resource

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
        
        # 配置文件搜索列表（按优先级排序）
        self.config_search_paths = [
            "/app/opencode/config_host/opencode.json",
            "config_host/opencode.json",
            os.path.expanduser("~/.opencode/config.json"),
            "./config/opencode.json"
        ]

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

    def _find_config_file(self) -> Optional[str]:
        """查找配置文件"""
        for config_path in self.config_search_paths:
            if os.path.exists(config_path):
                abs_path = os.path.abspath(config_path)
                logger.info(f"Found config file: {abs_path}")
                return abs_path
        logger.warning("No config file found, using defaults")
        return None

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

            # ✅ 降级逻辑：检查 opencode 是否可用
            import shutil
            if not shutil.which("opencode"):
                logger.warning("opencode command not found, using mock_kernel fallback")
                # 使用当前 Python 解释器运行 mock_kernel
                import sys
                cmd = [
                    sys.executable,
                    "-m", "app.mock_kernel"
                ]
                # mock_kernel 默认监听 4096，固不需要额外参数，或者可以根据需要添加
            
            # 设置环境变量
            env = os.environ.copy()
            # 确保 PYTHONPATH 包含当前目录
            original_pythonpath = env.get("PYTHONPATH", "")
            current_dir = os.getcwd()
            if current_dir not in original_pythonpath:
                env["PYTHONPATH"] = f"{current_dir}{os.pathsep}{original_pythonpath}" if original_pythonpath else current_dir

            # 查找并使用配置文件
            config_file = self._find_config_file()
            if config_file:
                env["OPENCODE_CONFIG_FILE"] = config_file
                logger.info(f"Using config: {config_file}")

            # 创建进程组，便于信号控制
            # ✅ 修复：将资源限制整合到preexec_fn中
            def set_limits_and_session():
                """设置进程组和资源限制"""
                # 1. 创建新会话（进程组）
                os.setsid()
                
                # 2. 只设置 CPU 时间限制，不限制内存（Bun/JavaScriptCore 需要较多内存）
                try:
                    # 限制CPU时间为10分钟
                    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
                except (OSError, ValueError):
                    pass
            
            preexec_fn = None
            if os.name != 'nt':  # Unix-like systems
                preexec_fn = set_limits_and_session
            
            # 启动进程（后台，不阻塞）
            # 把输出写到日志文件，方便诊断崩溃原因
            serve_log = open("/app/opencode/logs/serve_startup.log", "a")
            self.process = subprocess.Popen(
                cmd,
                stdout=serve_log,
                stderr=serve_log,
                env=env,
                preexec_fn=preexec_fn,
            )
            
            # ❌ 删除：资源限制已在preexec_fn中设置，不需要在这里重复设置
            # （之前的代码在Popen之后设置，实际上限制的是当前进程，不是子进程）

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
        except ValueError as e:
            # ✅ 改进：区分不同类型的ValueError
            if "preexec_fn" in str(e) and "start_new_session" in str(e):
                logger.error(f"subprocess.Popen parameter conflict: {e}")
                logger.error(f"Bug: preexec_fn and start_new_session cannot be used together")
            else:
                logger.error(f"ValueError starting server: {e}")
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
        # Early exit: validate base_url format
        if not self.base_url or not self.base_url.startswith(('http://', 'https://')):
            logger.error(f"Invalid base_url format: {self.base_url}")
            return False

        try:
            timeout = httpx.Timeout(5.0, connect=3.0)

            async with httpx.AsyncClient(timeout=timeout) as client:
                # opencode serve 的 /session 端点返回 200 表示服务器就绪
                # 注意：如果启用了认证插件（如 opencode-antigravity-auth），会返回 401
                # 这种情况下，401 也表示服务器正常运行，只是需要认证
                response = await client.get(f"{self.base_url}/session")
                if response.status_code == 200:
                    logger.debug(f"Health check successful: {self.base_url}")
                    return True
                elif response.status_code == 401:
                    # 401 表示服务器运行中但需要认证（antigravity-auth 插件）
                    logger.info(f"Server running with authentication enabled: {self.base_url}")
                    return True
                else:
                    logger.warning(f"Health check failed with status {response.status_code}")
                    return False
        except httpx.ConnectTimeout:
            logger.debug(f"Health check timeout for {self.base_url}")
            return False
        except httpx.ConnectError as e:
            logger.debug(f"Health check connection error: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.warning(f"Health check HTTP error: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Health check failed unexpectedly: {e}")
            return False

    def _stop_process(self):
        """停止服务器进程"""
        if not self.process:
            return

        try:
            # 1. 先尝试优雅终止（发送SIGTERM）
            logger.info(f"Attempting to terminate process {self.process.pid}")
            self.process.terminate()
            
            try:
                self.process.wait(timeout=5)
                logger.info(f"Process {self.process.pid} terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(f"Process {self.process.pid} did not terminate gracefully, forcing kill")
                # 2. 强制终止（发送SIGKILL）
                if os.name != 'nt':  # Unix-like systems
                    # 终止整个进程组
                    try:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    except (OSError, ProcessLookupError):
                        # Fallback to kill
                        self.process.kill()
                else:
                    # Windows
                    self.process.kill()
                    
                try:
                    self.process.wait(timeout=3)
                    logger.info(f"Process {self.process.pid} killed forcefully")
                except subprocess.TimeoutExpired:
                    logger.error(f"Process {self.process.pid} could not be killed after SIGKILL")
                    
        except ProcessLookupError:
            logger.info(f"Process {self.process.pid} already terminated")
        except PermissionError as e:
            logger.error(f"Permission denied when stopping process: {e}")
        except Exception as e:
            logger.error(f"Error stopping process: {e}", exc_info=True)
        finally:
            self.process = None
            self.is_running = False

    async def _ensure_server_ready(self, max_retries: int = 3) -> bool:
        """确保服务器准备就绪，带有崩溃恢复机制"""
        for attempt in range(max_retries):
            # 检查服务器状态
            if not self.is_running or not await self._check_health():
                logger.warning(f"Server not ready (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    # 重置状态并尝试重启
                    self.is_running = False
                    await asyncio.sleep(1)
                    continue
                # 尝试启动服务器
                if not await self.start():
                    return False
            return True
        return False

    async def execute(self, session_id: str, prompt: str, mode: str = "auto") -> AsyncGenerator[str, None]:
        """
        通过 HTTP API 执行任务（替代 opencode run）

        Args:
            session_id: 会话ID（必需）
            prompt: 用户提示词
            mode: 运行模式 (auto, plan, build)

        Returns:
            SSE 事件流生成器
        """
        # 参数验证（早期退出）
        if not session_id:
            raise ValueError("session_id cannot be empty")
        
        if not prompt:
            raise ValueError("prompt cannot be empty")
        
        if mode not in ["auto", "plan", "build"]:
            raise ValueError(f"mode must be one of 'auto', 'plan', 'build', got {mode}")

        # 确保服务器准备就绪（带有崩溃恢复）
        if not await self._ensure_server_ready():
            raise RuntimeError("Failed to start OpenCode server")

        # 使用正确的 API 端点：/opencode/session/{session_id}/message
        url = f"{self.base_url}/opencode/session/{session_id}/message"

        # 生成消息ID
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

        # 发送请求并处理SSE流
        try:
            # Configure SSL verification for production
            verify_ssl = os.getenv('OPENCODE_SSL_VERIFY', 'true').lower() == 'true'
            timeout = httpx.Timeout(300.0, connect=10.0, read=300.0)
            
            async with httpx.AsyncClient(timeout=timeout, verify=verify_ssl) as client:
                # 设置SSE请求头
                headers = {
                    "Accept": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "User-Agent": "OpenCodeServerManager/1.0"
                }
                
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    # Validate response before streaming
                    if response.status_code != 200:
                        error_msg = f"HTTP {response.status_code}: {response.reason_phrase}"
                        logger.error(f"SSE stream error: {error_msg}")
                        raise httpx.HTTPStatusError(error_msg, request=response.request, response=response)
                    
                    # 逐行读取SSE流
                    async for line in response.aiter_lines():
                        if line:
                            yield line
                            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP status error in execute: {e.response.status_code} - {e.response.text}")
            # 检查是否是服务器崩溃
            if e.response.status_code >= 500:
                logger.warning("Server error detected - possible server crash")
                self.is_running = False
            raise
        except httpx.ConnectError as e:
            logger.error(f"Connection error in execute: {e}")
            logger.warning("Connection error - possible server crash")
            self.is_running = False
            raise
        except httpx.TimeoutException as e:
            logger.error(f"Timeout error in execute: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in execute: {e}", exc_info=True)
            raise

    async def execute_sync(self, session_id: str, prompt: str, mode: str = "auto") -> str:
        """
        同步执行任务，返回完整响应文本（向后兼容）
        
        Args:
            session_id: 会话ID（必需）
            prompt: 用户提示词
            mode: 运行模式 (auto, plan, build)
            
        Returns:
            完整的SSE响应文本
        """
        events = []
        async for event in self.execute(session_id, prompt, mode):
            events.append(event)
        return "\n".join(events)

    async def get_session(self, session_id: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """获取会话信息，带有崩溃恢复机制"""
        if not session_id:
            raise ValueError("session_id cannot be empty")
            
        # 确保服务器准备就绪（带有崩溃恢复）
        if not await self._ensure_server_ready():
            return None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 使用正确的 API 端点：/opencode/session/{session_id}
                    response = await client.get(f"{self.base_url}/opencode/session/{session_id}")
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 404:
                        logger.info(f"Session {session_id} not found")
                        return None
                    else:
                        logger.warning(f"Unexpected status code {response.status_code}")
                        
            except httpx.ConnectError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 标记服务器未运行并重试
                    self.is_running = False
                    await asyncio.sleep(1)
                    continue
                return None
            except Exception as e:
                logger.error(f"Failed to get session (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return None
                
        return None

    async def stop(self):
        """停止服务器"""
        logger.info("Stopping OpenCode server...")
        self._stop_process()
        self.is_running = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口，确保资源清理"""
        await self.stop()


def main():
    """主入口点：使用app.main的懒加载机制"""
    import uvicorn
    
    # 导入app.main模块（包含懒加载的OpenCodeServerManager）
    try:
        from app import main as app_main
        logger.info("Using app.main with lazy loading OpenCodeServerManager")
        
        # 使用app.main的FastAPI app
        # 这个app内部已经实现了OpenCodeServerManager的懒加载
        uvicorn.run(
            app_main.app,  # 使用app.main中定义的FastAPI应用
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=False
        )
        
    except ImportError as e:
        logger.error(f"Failed to import app.main: {e}")
        logger.info("Falling back to direct uvicorn startup")
        
        # 如果app.main导入失败，使用直接启动（原始方式）
        import uvicorn as uv
        uv.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=False
        )


if __name__ == "__main__":
    main()
