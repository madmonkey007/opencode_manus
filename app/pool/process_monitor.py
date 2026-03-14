"""
OpenCode 进程监控模块

功能：
1. 实时监控进程健康状态
2. 检测僵尸进程
3. 自动重启策略
4. 性能指标收集
"""
import psutil
import threading
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ProcessMetrics:
    """进程性能指标"""
    pid: int
    cpu_percent: float
    memory_mb: float
    uptime_seconds: float
    tasks_completed: int
    last_activity: datetime
    is_zombie: bool = False
    is_high_memory: bool = False
    is_high_cpu: bool = False


class ProcessMonitor:
    """
    进程监控器

    监控指标：
    - CPU使用率
    - 内存使用
    - 运行时长
    - 任务完成数
    - 僵尸进程检测
    """

    # 阈值配置
    ZOMBIE_THRESHOLD = 60  # 60秒无活动视为僵尸
    HIGH_MEMORY_THRESHOLD = 500  # 500MB视为高内存
    HIGH_CPU_THRESHOLD = 80  # 80% CPU视为高CPU

    def __init__(self, check_interval: int = 10):
        """
        初始化监控器

        Args:
            check_interval: 检查间隔（秒）
        """
        self.check_interval = check_interval
        self.metrics_history: Dict[int, list] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._should_stop = False

    def start(self) -> None:
        """启动监控"""
        logger.info("Starting process monitor...")
        self._should_stop = False

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ProcessMetricsMonitor"
        )
        self._monitor_thread.start()

    def stop(self) -> None:
        """停止监控"""
        logger.info("Stopping process monitor...")
        self._should_stop = True

        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)

    def _monitor_loop(self) -> None:
        """监控循环"""
        while not self._should_stop:
            try:
                time.sleep(self.check_interval)
                self._collect_metrics()
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

    def _collect_metrics(self) -> None:
        """收集所有进程的指标"""
        # 这个方法会从进程池获取当前进程列表并收集指标
        # 实际实现在集成时完成
        pass

    def collect_process_metrics(self, pid: int, tasks_completed: int, last_activity: datetime) -> ProcessMetrics:
        """
        收集单个进程的指标

        Args:
            pid: 进程ID
            tasks_completed: 已完成任务数
            last_activity: 最后活动时间

        Returns:
            ProcessMetrics: 进程指标
        """
        try:
            process = psutil.Process(pid)

            # CPU使用率
            cpu_percent = process.cpu_percent(interval=0.1)

            # 内存使用
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # 运行时长
            create_time = datetime.fromtimestamp(process.create_time())
            uptime = (datetime.now() - create_time).total_seconds()

            # 判断异常状态
            is_zombie = (datetime.now() - last_activity).total_seconds() > self.ZOMBIE_THRESHOLD
            is_high_memory = memory_mb > self.HIGH_MEMORY_THRESHOLD
            is_high_cpu = cpu_percent > self.HIGH_CPU_THRESHOLD

            metrics = ProcessMetrics(
                pid=pid,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                uptime_seconds=uptime,
                tasks_completed=tasks_completed,
                last_activity=last_activity,
                is_zombie=is_zombie,
                is_high_memory=is_high_memory,
                is_high_cpu=is_high_cpu
            )

            # 保存历史数据
            if pid not in self.metrics_history:
                self.metrics_history[pid] = []

            self.metrics_history[pid].append(metrics)

            # 只保留最近100条记录
            if len(self.metrics_history[pid]) > 100:
                self.metrics_history[pid] = self.metrics_history[pid][-100:]

            return metrics

        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} no longer exists")
            return None
        except Exception as e:
            logger.error(f"Error collecting metrics for process {pid}: {e}")
            return None

    def get_metrics_summary(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        获取进程指标摘要

        Args:
            pid: 进程ID

        Returns:
            指标摘要字典
        """
        if pid not in self.metrics_history or not self.metrics_history[pid]:
            return None

        history = self.metrics_history[pid]
        latest = history[-1]

        avg_cpu = sum(m.cpu_percent for m in history) / len(history)
        avg_memory = sum(m.memory_mb for m in history) / len(history)

        return {
            "pid": pid,
            "current": {
                "cpu_percent": latest.cpu_percent,
                "memory_mb": latest.memory_mb,
                "tasks_completed": latest.tasks_completed,
                "is_zombie": latest.is_zombie,
                "is_high_memory": latest.is_high_memory,
                "is_high_cpu": latest.is_high_cpu
            },
            "average": {
                "cpu_percent": avg_cpu,
                "memory_mb": avg_memory
            },
            "uptime_seconds": latest.uptime_seconds,
            "data_points": len(history)
        }

    def should_restart_process(self, pid: int) -> tuple[bool, str]:
        """
        判断是否需要重启进程

        Args:
            pid: 进程ID

        Returns:
            (should_restart, reason): 是否需要重启及原因
        """
        metrics = self.collect_process_metrics(
            pid=pid,
            tasks_completed=0,
            last_activity=datetime.now()
        )

        if metrics is None:
            return True, "Process not found"

        if metrics.is_zombie:
            return True, f"Zombie process (no activity for {self.ZOMBIE_THRESHOLD}s)"

        if metrics.is_high_memory:
            return True, f"High memory usage: {metrics.memory_mb:.1f}MB"

        if metrics.is_high_cpu:
            # 持续高CPU才重启
            history = self.metrics_history.get(pid, [])
            if len(history) >= 3:
                recent_high_cpu = all(m.is_high_cpu for m in history[-3:])
                if recent_high_cpu:
                    return True, f"Sustained high CPU: {metrics.cpu_percent:.1f}%"

        return False, ""

    def get_all_metrics(self) -> Dict[int, Dict[str, Any]]:
        """获取所有进程的指标摘要"""
        return {
            pid: self.get_metrics_summary(pid)
            for pid in self.metrics_history.keys()
        }

    def clear_history(self, pid: int) -> None:
        """清除指定进程的历史数据"""
        if pid in self.metrics_history:
            del self.metrics_history[pid]
