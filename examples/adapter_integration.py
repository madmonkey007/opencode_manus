"""
OpenCode 适配器集成示例

展示如何使用进程池和适配器层执行任务
"""
import asyncio
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_web_adapter():
    """示例：使用 Web 适配器执行任务"""
    from app.gateway.adapters import WebAdapter, ExecutionContext

    logger.info("=== Web 适配器示例 ===")

    # 创建 Web 适配器
    config = {
        "server_url": "http://127.0.0.1:4096",
        "timeout": 300
    }

    async with WebAdapter(config=config) as adapter:
        # 检查适配器可用性
        if not adapter.is_available():
            logger.error("Web 适配器不可用")
            return

        logger.info(f"Web 适配器健康状态: {adapter.get_health()}")

        # 创建执行上下文
        context = ExecutionContext(
            session_id=f"web-test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            prompt="创建一个简单的Python Hello World程序",
            mode="build"
        )

        # 执行任务（非流式）
        logger.info(f"执行任务: {context.prompt}")

        result = await adapter.execute(context)

        if result.success:
            logger.info(f"任务执行成功!")
            logger.info(f"响应: {result.response[:100]}...")
            logger.info(f"执行时间: {result.execution_time:.2f}秒")
        else:
            logger.error(f"任务执行失败: {result.error}")


async def example_cli_adapter():
    """示例：使用 CLI 适配器执行任务"""
    from app.gateway.adapters import CLIAdapter, ExecutionContext

    logger.info("=== CLI 适配器示例 ===")

    # 创建 CLI 适配器
    config = {
        "pool_size": 2,
        "server_url": "http://127.0.0.1:4096",
        "model": "new-api/glm-4.7"
    }

    async with CLIAdapter(config=config) as adapter:
        # 检查适配器可用性
        if not adapter.is_available():
            logger.error("CLI 适配器不可用")
            return

        logger.info(f"CLI 适配器健康状态: {adapter.get_health()}")

        # 创建执行上下文
        context = ExecutionContext(
            session_id=f"cli-test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            prompt="分析这个Python函数的性能瓶颈",
            mode="plan"
        )

        # 执行任务（非流式）
        logger.info(f"执行任务: {context.prompt}")

        result = await adapter.execute(context)

        if result.success:
            logger.info(f"任务执行成功!")
            logger.info(f"响应: {result.response[:100] if result.response else 'N/A'}...")
            logger.info(f"执行时间: {result.execution_time:.2f}秒")
        else:
            logger.error(f"任务执行失败: {result.error}")


async def example_stream_execution():
    """示例：流式执行任务"""
    from app.gateway.adapters import WebAdapter, ExecutionContext

    logger.info("=== 流式执行示例 ===")

    # 创建 Web 适配器
    config = {
        "server_url": "http://127.0.0.1:4096",
        "timeout": 300
    }

    async with WebAdapter(config=config) as adapter:
        # 创建执行上下文
        context = ExecutionContext(
            session_id=f"stream-test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            prompt="创建一个待办事项管理应用",
            mode="build"
        )

        # 流式执行任务
        logger.info(f"开始流式执行: {context.prompt}")

        event_count = 0
        start_time = datetime.now()

        async for event in adapter.execute_stream(context):
            event_count += 1

            if event.event_type == "phase":
                logger.info(f"[阶段] {event.data.get('phase', 'unknown')}")
            elif event.event_type == "action":
                logger.info(f"[动作] {event.data.get('action', 'unknown')}")
            elif event.event_type == "progress":
                logger.info(f"[进度] {event.data.get('progress', 0)}%")
            elif event.event_type == "complete":
                logger.info(f"[完成] 任务完成")
                break
            elif event.event_type == "error":
                logger.error(f"[错误] {event.data.get('error', 'unknown')}")

        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"流式执行完成，共收到 {event_count} 个事件，耗时 {execution_time:.2f}秒")


async def example_adapter_factory():
    """示例：使用工厂函数创建适配器"""
    from app.gateway.adapters import create_adapter

    logger.info("=== 适配器工厂示例 ===")

    # 使用工厂函数创建适配器
    web_adapter = create_adapter("web", config={
        "server_url": "http://127.0.0.1:4096"
    })

    logger.info(f"创建的适配器: {web_adapter.name}")
    logger.info(f"适配器类型: {type(web_adapter).__name__}")

    # 创建 CLI 适配器
    cli_adapter = create_adapter("cli", config={
        "pool_size": 2
    })

    logger.info(f"创建的适配器: {cli_adapter.name}")
    logger.info(f"适配器类型: {type(cli_adapter).__name__}")


async def example_pool_stats():
    """示例：获取进程池统计信息"""
    from app.pool import get_global_pool

    logger.info("=== 进程池统计示例 ===")

    # 获取全局进程池
    pool = get_global_pool()

    # 获取统计信息
    stats = pool.get_stats()

    logger.info(f"进程池配置大小: {stats['pool_size']}")
    logger.info(f"活动进程数: {stats['active_processes']}")
    logger.info(f"健康进程数: {stats['healthy_processes']}")
    logger.info(f"繁忙进程数: {stats['busy_processes']}")
    logger.info(f"空闲进程数: {stats['idle_processes']}")
    logger.info(f"已完成任务总数: {stats['total_tasks_completed']}")

    # 显示每个进程的详细信息
    for proc in stats.get('processes', []):
        logger.info(
            f"  进程 {proc['id']}: "
            f"PID={proc['pid']}, "
            f"健康={proc['is_healthy']}, "
            f"繁忙={proc['is_busy']}, "
            f"任务数={proc['tasks_completed']}, "
            f"运行时间={proc['uptime_seconds']:.1f}秒"
        )


async def main():
    """主函数：运行所有示例"""
    logger.info("OpenCode 适配器集成示例")
    logger.info("=" * 50)

    # 1. Web 适配器示例
    try:
        await example_web_adapter()
    except Exception as e:
        logger.error(f"Web 适配器示例失败: {e}")

    print()

    # 2. CLI 适配器示例
    try:
        await example_cli_adapter()
    except Exception as e:
        logger.error(f"CLI 适配器示例失败: {e}")

    print()

    # 3. 流式执行示例
    try:
        await example_stream_execution()
    except Exception as e:
        logger.error(f"流式执行示例失败: {e}")

    print()

    # 4. 适配器工厂示例
    try:
        await example_adapter_factory()
    except Exception as e:
        logger.error(f"适配器工厂示例失败: {e}")

    print()

    # 5. 进程池统计示例
    try:
        await example_pool_stats()
    except Exception as e:
        logger.error(f"进程池统计示例失败: {e}")

    logger.info("=" * 50)
    logger.info("所有示例执行完毕")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
