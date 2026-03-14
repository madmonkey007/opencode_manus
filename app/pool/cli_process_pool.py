"""
OpenCode CLI 进程池实现

核心功能：
1. 管理多个持久CLI进程
2. 使用JSON-RPC协议与进程通信
3. 自动健康检查和进程重启
4. 负载均衡和任务分发
"""
import asyncio
import json
import subprocess
import threading
import time
import uuid
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """进程信息"""
    process_id: str
    process: subprocess.Popen
    pid: int
    start_time: datetime
    last_used: datetime
    tasks_completed: int = 0
    is_busy: bool = False
    is_healthy: bool = True


@dataclass
class TaskRequest:
    """任务请求"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = ""
    mode: str = "auto"
    context: Dict[str, Any] = field(default_factory=dict)
    submit_time: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResponse:
    """任务响应"""
    id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    complete_time: datetime = field(default_factory=datetime.now)


class CLIProcessPool:
    """
    CLI 进程池管理器

    特性：
    - 持久进程：启动后长期运行，避免每次任务启动新进程
    - JSON-RPC通信：标准化的请求/响应协议
    - 健康检查：自动检测并重启僵尸进程
    - 负载均衡：自动选择空闲进程
    """

    def __init__(
        self,
        pool_size: int = 2,
        server_url: str = "http://127.0.0.1:4096",
        model: str = "new-api/glm-4.7",
        health_check_interval: int = 5,
        command: str = "opencode",
        command_args: list = None
    ):
        """
        初始化进程池

        Args:
            pool_size: 进程池大小（默认2个）
            server_url: OpenCode服务器地址
            model: 使用的模型
            health_check_interval: 健康检查间隔（秒）
            command: CLI命令
            command_args: 额外的命令参数
        """
        self.pool_size = pool_size
        self.server_url = server_url
        self.model = model
        self.health_check_interval = health_check_interval
        self.command = command

        # 默认命令参数
        if command_args is None:
            self.command_args = [
                "run",
                "--attach", server_url,
                "--model", model,
                "--format", "json",
                "--thinking",
                "--agent", "auto"
            ]
        else:
            self.command_args = command_args

        # 进程池
        self.processes: Dict[str, ProcessInfo] = {}
        self.lock = threading.Lock()

        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None
        self._should_stop = False

        logger.info(f"CLIProcessPool initialized: pool_size={pool_size}, model={model}")

    def start(self) -> None:
        """启动进程池"""
        logger.info("Starting CLI process pool...")

        with self.lock:
            for i in range(self.pool_size):
                self._start_process(i)

        # 启动健康检查线程
        self._monitor_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="ProcessMonitor"
        )
        self._monitor_thread.start()

        logger.info(f"Process pool started with {len(self.processes)} processes")

    def stop(self) -> None:
        """停止进程池"""
        logger.info("Stopping CLI process pool...")
        self._should_stop = True

        with self.lock:
            for proc_info in list(self.processes.values()):
                try:
                    proc_info.process.terminate()
                    proc_info.process.wait(timeout=5)

                    # 修复：关闭文件描述符防止资源泄漏
                    if proc_info.process.stdin:
                        proc_info.process.stdin.close()
                    if proc_info.process.stdout:
                        proc_info.process.stdout.close()
                    if proc_info.process.stderr:
                        proc_info.process.stderr.close()
                except Exception as e:
                    logger.error(f"Error stopping process {proc_info.process_id}: {e}")
                    try:
                        proc_info.process.kill()
                        # 确保kill后也关闭文件描述符
                        if proc_info.process.stdin:
                            proc_info.process.stdin.close()
                        if proc_info.process.stdout:
                            proc_info.process.stdout.close()
                        if proc_info.process.stderr:
                            proc_info.process.stderr.close()
                    except:
                        pass

            self.processes.clear()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)

        logger.info("Process pool stopped")

    def _start_process(self, index: int) -> Optional[ProcessInfo]:
        """启动单个CLI进程"""
        process_id = f"cli-pool-{index}-{uuid.uuid4().hex[:8]}"

        try:
            # 启动进程
            process = subprocess.Popen(
                [self.command] + self.command_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲
                encoding='utf-8',
                errors='replace'
            )

            proc_info = ProcessInfo(
                process_id=process_id,
                process=process,
                pid=process.pid,
                start_time=datetime.now(),
                last_used=datetime.now()
            )

            self.processes[process_id] = proc_info

            logger.info(f"Started CLI process: {process_id} (PID: {process.pid})")
            return proc_info

        except Exception as e:
            logger.error(f"Failed to start CLI process: {e}")
            return None

    def _health_check_loop(self) -> None:
        """健康检查循环"""
        while not self._should_stop:
            try:
                time.sleep(self.health_check_interval)
                self._health_check()
            except Exception as e:
                logger.error(f"Health check error: {e}")

    def _health_check(self) -> None:
        """检查所有进程的健康状态"""
        with self.lock:
            dead_processes = []

            for proc_id, proc_info in self.processes.items():
                # 检查进程是否存活
                if proc_info.process.poll() is not None:
                    logger.warning(f"Process {proc_id} (PID: {proc_info.pid}) is dead")
                    proc_info.is_healthy = False
                    dead_processes.append(proc_id)
                else:
                    proc_info.is_healthy = True

            # 重启死掉的进程
            for proc_id in dead_processes:
                logger.info(f"Restarting dead process: {proc_id}")
                del self.processes[proc_id]

                # 找到原来的索引并重启
                index = len(self.processes)
                self._start_process(index)

    def get_idle_process(self) -> Optional[ProcessInfo]:
        """获取一个空闲进程"""
        with self.lock:
            # 优先选择空闲且健康的进程
            for proc_info in self.processes.values():
                if not proc_info.is_busy and proc_info.is_healthy:
                    return proc_info

            # 如果没有空闲进程，选择最久未使用的健康进程
            healthy_processes = [
                p for p in self.processes.values()
                if p.is_healthy
            ]

            if healthy_processes:
                return min(healthy_processes, key=lambda p: p.last_used)

            return None

    def submit_task(
        self,
        prompt: str,
        mode: str = "auto",
        context: Dict[str, Any] = None,
        timeout: float = 300.0
    ) -> TaskResponse:
        """
        提交任务到进程池

        Args:
            prompt: 任务提示词
            mode: 执行模式 (auto/build/plan)
            context: 上下文信息
            timeout: 超时时间（秒）

        Returns:
            TaskResponse: 任务执行结果
        """
        task = TaskRequest(prompt=prompt, mode=mode, context=context or {})

        # 获取空闲进程
        proc_info = self.get_idle_process()

        if proc_info is None:
            return TaskResponse(
                id=task.id,
                success=False,
                error="No available process in pool"
            )

        # 执行任务
        try:
            # 修复：在锁内获取进程，锁外执行，最后在锁内释放
            with self.lock:
                if proc_info.is_busy:
                    # 进程状态异常，重新获取
                    proc_info = self.get_idle_process()
                    if proc_info is None:
                        return TaskResponse(
                            id=task.id,
                            success=False,
                            error="No available process in pool"
                        )

                proc_info.is_busy = True
                proc_info.last_used = datetime.now()

            result = self._execute_on_process(proc_info, task, timeout)

            if result.success:
                proc_info.tasks_completed += 1

            return result

        except Exception as e:
            logger.error(f"Task execution error: {e}")
            return TaskResponse(
                id=task.id,
                success=False,
                error=str(e)
            )
        finally:
            # 修复：确保释放进程锁
            with self.lock:
                proc_info.is_busy = False

    def _execute_on_process(
        self,
        proc_info: ProcessInfo,
        task: TaskRequest,
        timeout: float
    ) -> TaskResponse:
        """在指定进程上执行任务"""
        try:
            # 构建JSON-RPC请求
            request = {
                "jsonrpc": "2.0",
                "id": task.id,
                "method": "execute",
                "params": {
                    "prompt": task.prompt,
                    "mode": task.mode,
                    **task.context
                }
            }

            # 发送请求
            proc_info.process.stdin.write(json.dumps(request) + "\n")
            proc_info.process.stdin.flush()

            # 读取响应
            start_time = time.time()
            response_lines = []

            while time.time() - start_time < timeout:
                try:
                    line = proc_info.process.stdout.readline()
                    if not line:
                        break

                    # 解析JSON响应
                    try:
                        response = json.loads(line.strip())

                        if response.get("id") == task.id:
                            return TaskResponse(
                                id=task.id,
                                success=True,
                                data=response.get("result")
                            )

                    except json.JSONDecodeError:
                        # 可能是事件流，继续读取
                        response_lines.append(line)

                except Exception as e:
                    logger.error(f"Error reading process output: {e}")
                    break

            # 修复：超时后标记进程为不健康，触发重启
            logger.warning(
                f"Task {task.id} timeout after {timeout}s, "
                f"marking process {proc_info.process_id} as unhealthy"
            )
            proc_info.is_healthy = False

            return TaskResponse(
                id=task.id,
                success=False,
                error=f"Timeout after {timeout}s"
            )

        except Exception as e:
            logger.error(f"Process execution error: {e}")
            return TaskResponse(
                id=task.id,
                success=False,
                error=str(e)
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取进程池统计信息"""
        with self.lock:
            healthy = sum(1 for p in self.processes.values() if p.is_healthy)
            busy = sum(1 for p in self.processes.values() if p.is_busy)
            total_tasks = sum(p.tasks_completed for p in self.processes.values())

            return {
                "pool_size": self.pool_size,
                "active_processes": len(self.processes),
                "healthy_processes": healthy,
                "busy_processes": busy,
                "idle_processes": healthy - busy,
                "total_tasks_completed": total_tasks,
                "processes": [
                    {
                        "id": p.process_id,
                        "pid": p.pid,
                        "is_busy": p.is_busy,
                        "is_healthy": p.is_healthy,
                        "tasks_completed": p.tasks_completed,
                        "uptime_seconds": (datetime.now() - p.start_time).total_seconds()
                    }
                    for p in self.processes.values()
                ]
            }

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()


# 全局进程池实例
_global_pool: Optional[CLIProcessPool] = None


def get_global_pool() -> CLIProcessPool:
    """获取全局进程池实例"""
    global _global_pool

    if _global_pool is None:
        _global_pool = CLIProcessPool()
        _global_pool.start()

    return _global_pool


def shutdown_global_pool() -> None:
    """关闭全局进程池"""
    global _global_pool

    if _global_pool is not None:
        _global_pool.stop()
        _global_pool = None
