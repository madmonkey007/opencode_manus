"""
基准测试基类和实现
基于Code Review改进版本：
- 统一的基类设计
- 完整的错误处理
- 虚拟项目隔离测试数据
- 自动重试机制
"""
import asyncio
import time
import aiohttp
import logging
from typing import List, Dict, Optional
from .config import (
    logger,
    CURRENT_IMPLEMENTATION_URL,
    OPENCODE_WEB_URL,
    TEST_PROJECT_ID,
    TEST_TIMEOUT
)


class BenchmarkError(Exception):
    """基准测试异常"""
    pass


class BenchmarkBase:
    """
    统一的基准测试基类
    提供通用的测试逻辑，子类实现具体的API调用
    """

    def __init__(self, base_url: str, project_id: Optional[str] = TEST_PROJECT_ID):
        self.base_url = base_url
        self.project_id = project_id
        self.results: List[Dict] = []
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()

    async def setup_test_environment(self):
        """
        设置测试环境
        创建虚拟项目用于隔离测试数据
        """
        logger.info(f"设置测试环境: 创建项目 {self.project_id}")

        try:
            # 尝试创建测试项目
            if self.project_id:
                await self.create_project(self.project_id, "性能测试项目")

            logger.info("✅ 测试环境设置完成")
        except Exception as e:
            logger.warning(f"⚠️ 创建测试项目失败（可能已存在）: {e}")
            # 不影响测试继续

    async def cleanup_test_environment(self):
        """
        清理测试环境
        删除虚拟项目及其所有测试数据
        """
        logger.info(f"清理测试环境: 删除项目 {self.project_id}")

        try:
            if self.project_id:
                await self.delete_project(self.project_id)

            logger.info("✅ 测试环境清理完成")
        except Exception as e:
            logger.error(f"❌ 清理测试环境失败: {e}")

    async def create_project(self, project_id: str, name: str) -> bool:
        """创建项目（子类可选实现）"""
        # 默认实现：尝试创建项目
        try:
            async with self.session.post(
                f"{self.base_url}/opencode/project",
                json={"id": project_id, "name": name},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in [200, 201]:
                    logger.info(f"  项目创建成功: {project_id}")
                    return True
                elif resp.status == 409:  # 已存在
                    logger.info(f"  项目已存在: {project_id}")
                    return True
                else:
                    logger.warning(f"  创建项目返回状态码: {resp.status}")
                    return False
        except Exception as e:
            logger.warning(f"  创建项目异常: {e}")
            return False

    async def delete_project(self, project_id: str) -> bool:
        """删除项目（子类可选实现）"""
        try:
            async with self.session.delete(
                f"{self.base_url}/opencode/project/{project_id}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in [200, 204]:
                    logger.info(f"  项目删除成功: {project_id}")
                    return True
                else:
                    logger.warning(f"  删除项目返回状态码: {resp.status}")
                    return False
        except Exception as e:
            logger.warning(f"  删除项目异常: {e}")
            return False

    async def create_session(self, prompt: str, mode: str = "build", max_retries: int = 3) -> str:
        """
        创建session（子类必须实现）
        返回session_id
        """
        raise NotImplementedError("子类必须实现create_session方法")

    async def wait_for_first_event(self, session_id: str, timeout: int = TEST_TIMEOUT) -> float:
        """
        等待首个SSE事件
        返回耗时（秒）
        """
        raise NotImplementedError("子类必须实现wait_for_first_event方法")

    async def run_single_test(self, run_number: int, prompt: str, mode: str = "build") -> Dict:
        """
        运行单次测试
        """
        logger.info(f"[运行 {run_number}] 开始测试")

        start_time = time.time()
        result = {
            "run": run_number,
            "start_time": start_time,
            "success": False,
            "error": None
        }

        try:
            # 创建session
            session_id = await self.create_session(prompt, mode)
            create_time = time.time()
            result["session_id"] = session_id
            result["create_time"] = create_time - start_time

            # 等待首个事件
            first_event_time = await self.wait_for_first_event(session_id)
            total_time = time.time() - start_time

            result["total_time"] = total_time
            result["first_event_time"] = first_event_time
            result["success"] = True

            logger.info(f"[运行 {run_number}] ✅ 完成: {total_time:.2f}s")

        except asyncio.TimeoutError as e:
            total_time = time.time() - start_time
            result["total_time"] = total_time
            result["error"] = f"超时: {str(e)}"
            logger.error(f"[运行 {run_number}] ❌ 超时: {total_time:.2f}s")

        except Exception as e:
            total_time = time.time() - start_time
            result["total_time"] = total_time
            result["error"] = str(e)
            logger.error(f"[运行 {run_number}] ❌ 失败: {e}")

        return result

    async def run_benchmark(self, num_runs: int = 10) -> List[Dict]:
        """
        执行完整的基准测试
        """
        logger.info("=" * 70)
        logger.info(f"开始基准测试: {num_runs}次运行")
        logger.info(f"目标服务器: {self.base_url}")
        logger.info("=" * 70)

        # 设置测试环境
        await self.setup_test_environment()

        try:
            # 执行多次测试
            for i in range(1, num_runs + 1):
                result = await self.run_single_test(i, f"性能测试_{i}", mode="build")
                self.results.append(result)

                # 间隔时间（避免连续请求干扰）
                if i < num_runs:
                    await asyncio.sleep(1)

        finally:
            # 清理测试环境
            await self.cleanup_test_environment()

        # 输出统计信息
        self._log_statistics()

        return self.results

    def _log_statistics(self):
        """输出统计信息"""
        successful_results = [r for r in self.results if r.get("success")]
        failed_results = [r for r in self.results if not r.get("success")]

        logger.info("=" * 70)
        logger.info("测试统计:")
        logger.info(f"  总运行次数: {len(self.results)}")
        logger.info(f"  成功: {len(successful_results)}")
        logger.info(f"  失败: {len(failed_results)}")

        if successful_results:
            times = [r["total_time"] for r in successful_results]
            logger.info(f"  平均时间: {sum(times)/len(times):.2f}s")
            logger.info(f"  最小时间: {min(times):.2f}s")
            logger.info(f"  最大时间: {max(times):.2f}s")
            logger.info(f"  中位数: {sorted(times)[len(times)//2]:.2f}s")

        if failed_results:
            logger.info("  失败原因:")
            for r in failed_results[:5]:  # 只显示前5个
                logger.info(f"    - 运行{r['run']}: {r.get('error', 'Unknown')}")

        logger.info("=" * 70)

    def get_statistics(self) -> Dict:
        """计算统计数据"""
        successful_results = [r for r in self.results if r.get("success")]

        if not successful_results:
            return {
                "count": 0,
                "success_rate": 0
            }

        times = [r["total_time"] for r in successful_results]
        sorted_times = sorted(times)

        return {
            "count": len(times),
            "success_rate": len(successful_results) / len(self.results) * 100,
            "mean": sum(times) / len(times),
            "median": sorted_times[len(times) // 2],
            "min": min(times),
            "max": max(times),
            "p95": sorted_times[int(len(times) * 0.95)] if len(times) >= 20 else sorted_times[-1],
            "p99": sorted_times[int(len(times) * 0.99)] if len(times) >= 100 else sorted_times[-1],
            "std": (sum((t - sum(times)/len(times))**2 for t in times) / len(times))**0.5
        }


class CurrentImplementationBenchmark(BenchmarkBase):
    """
    当前实现的基准测试
    使用现有的FastAPI + CLI包装
    """

    def __init__(self):
        super().__init__(
            base_url=CURRENT_IMPLEMENTATION_URL,
            project_id=TEST_PROJECT_ID
        )

    async def create_session(self, prompt: str, mode: str = "build") -> str:
        """创建session"""
        url = f"{self.base_url}/opencode/session"
        payload = {
            "title": prompt,
            "mode": mode,
            "project_id": self.project_id
        }

        for attempt in range(3):
            try:
                async with self.session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        session_id = result.get("id")
                        if not session_id:
                            raise BenchmarkError("响应中没有session_id")
                        return session_id
                    else:
                        error_text = await resp.text()
                        raise BenchmarkError(f"API error: {resp.status} - {error_text}")

            except asyncio.TimeoutError:
                if attempt < 2:
                    logger.warning(f"  创建session超时，重试 {attempt + 1}/3")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                else:
                    raise
            except BenchmarkError:
                raise
            except Exception as e:
                if attempt < 2:
                    logger.warning(f"  创建session异常，重试 {attempt + 1}/3: {e}")
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

    async def wait_for_first_event(self, session_id: str, timeout: int = TEST_TIMEOUT) -> float:
        """等待首个SSE事件"""
        url = f"{self.base_url}/opencode/session/{session_id}/events"
        start = time.time()

        try:
            async with self.session.get(
                url,
                headers={"Accept": "text/event-stream"},
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status != 200:
                    raise BenchmarkError(f"SSE连接失败: {resp.status}")

                async for line in resp.content:
                    if line:
                        elapsed = time.time() - start
                        return elapsed

        except asyncio.TimeoutError:
            raise BenchmarkError(f"等待SSE事件超时({timeout}s)")

        raise BenchmarkError("未收到任何SSE事件")


class OpenCodeWebBenchmark(BenchmarkBase):
    """
    opencode web的基准测试
    使用官方持久的web服务器
    """

    def __init__(self):
        # opencode web可能不支持project_id
        super().__init__(
            base_url=OPENCODE_WEB_URL,
            project_id=None  # 官方可能不支持
        )

    async def create_session(self, prompt: str, mode: str = "build") -> str:
        """创建session"""
        # 注意: 官方API路径可能不同，需要根据实际情况调整
        url = f"{self.base_url}/session"  # 或 /api/session
        payload = {
            "prompt": prompt,  # 官方可能使用prompt而不是title
            "mode": mode
        }

        # 如果需要认证
        headers = {}
        if hasattr(self, 'password'):
            headers["Authorization"] = f"Bearer {self.password}"

        for attempt in range(3):
            try:
                async with self.session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        session_id = result.get("id")
                        if not session_id:
                            raise BenchmarkError("响应中没有session_id")
                        return session_id
                    elif resp.status == 401:
                        raise BenchmarkError("认证失败，请检查密码配置")
                    else:
                        error_text = await resp.text()
                        raise BenchmarkError(f"API error: {resp.status} - {error_text}")

            except asyncio.TimeoutError:
                if attempt < 2:
                    logger.warning(f"  创建session超时，重试 {attempt + 1}/3")
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
            except BenchmarkError:
                raise
            except Exception as e:
                if attempt < 2:
                    logger.warning(f"  创建session异常，重试 {attempt + 1}/3: {e}")
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

    async def wait_for_first_event(self, session_id: str, timeout: int = TEST_TIMEOUT) -> float:
        """等待首个SSE事件"""
        url = f"{self.base_url}/session/{session_id}/events"
        start = time.time()

        # 如果需要认证
        headers = {}
        if hasattr(self, 'password'):
            headers["Authorization"] = f"Bearer {self.password}"

        try:
            async with self.session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status != 200:
                    raise BenchmarkError(f"SSE连接失败: {resp.status}")

                async for line in resp.content:
                    if line:
                        elapsed = time.time() - start
                        return elapsed

        except asyncio.TimeoutError:
            raise BenchmarkError(f"等待SSE事件超时({timeout}s)")

        raise BenchmarkError("未收到任何SSE事件")


async def main():
    """主函数 - 执行完整的基准测试"""
    from config import logger

    # 测试当前实现
    logger.info("\n" + "=" * 70)
    logger.info("阶段1: 测试当前实现")
    logger.info("=" * 70 + "\n")

    async with CurrentImplementationBenchmark() as current_bench:
        current_results = await current_bench.run_benchmark(num_runs=10)
        current_stats = current_bench.get_statistics()

    # 测试opencode web
    logger.info("\n" + "=" * 70)
    logger.info("阶段2: 测试opencode web")
    logger.info("=" * 70 + "\n")

    try:
        async with OpenCodeWebBenchmark() as web_bench:
            web_results = await web_bench.run_benchmark(num_runs=10)
            web_stats = web_bench.get_statistics()
    except Exception as e:
        logger.error(f"❌ opencode web测试失败: {e}")
        logger.error("这可能是因为:")
        logger.error("  1. opencode web服务器未启动（请运行: opencode web --port 8888）")
        logger.error("  2. 端口8888被占用")
        logger.error("  3. API路径不兼容")
        web_stats = None
        web_results = []

    # 生成对比报告
    if current_stats and web_stats:
        logger.info("\n" + "=" * 70)
        logger.info("性能对比结果")
        logger.info("=" * 70)
        logger.info(f"当前实现:")
        logger.info(f"  平均时间: {current_stats['mean']:.2f}s")
        logger.info(f"  中位数: {current_stats['median']:.2f}s")
        logger.info(f"  成功率: {current_stats['success_rate']:.1f}%")

        logger.info(f"\nopencode web:")
        logger.info(f"  平均时间: {web_stats['mean']:.2f}s")
        logger.info(f"  中位数: {web_stats['median']:.2f}s")
        logger.info(f"  成功率: {web_stats['success_rate']:.1f}%")

        improvement = (1 - web_stats['mean'] / current_stats['mean']) * 100
        logger.info(f"\n性能提升: {improvement:.1f}%")
        logger.info("=" * 70)

    # 保存结果
    import json
    from pathlib import Path

    results_file = Path(__file__).parent.parent / "results" / "day1_performance.json"

    with open(results_file, "w") as f:
        json.dump({
            "current": {
                "results": current_results,
                "stats": current_stats
            },
            "web": {
                "results": web_results,
                "stats": web_stats
            },
            "timestamp": time.time()
        }, f, indent=2)

    logger.info(f"\n✅ 结果已保存到: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
