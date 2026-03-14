"""
混合路由策略使用示例

展示如何使用智能混合策略在不同负载下自动选择最优执行渠道
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


async def example_hybrid_strategy():
    """示例：混合策略的基本使用"""
    from app.gateway.router import HybridStrategy
    from app.gateway.adapters.base import ExecutionContext

    logger.info("=== 混合策略示例 ===")

    # 创建混合策略
    strategy = HybridStrategy(
        low_load_threshold=0.5,      # 50% 以下视为低负载
        high_load_threshold=0.8,     # 80% 以上视为高负载
        max_wait_time_low_load=10.0,  # 低负载时最多等待 10 秒
        max_wait_time_high_load=2.0   # 高负载时最多等待 2 秒
    )

    logger.info(f"策略名称: {strategy.name}")
    logger.info(f"低负载阈值: {strategy.low_load_threshold:.1%}")
    logger.info(f"高负载阈值: {strategy.high_load_threshold:.1%}")

    # 模拟不同的系统负载状态
    scenarios = [
        {
            "name": "低负载（有空闲进程）",
            "stats": {
                "healthy_processes": 2,
                "busy_processes": 0,
                "idle_processes": 2
            }
        },
        {
            "name": "中负载（50% 忙碌）",
            "stats": {
                "healthy_processes": 2,
                "busy_processes": 1,
                "idle_processes": 1
            }
        },
        {
            "name": "高负载（100% 忙碌）",
            "stats": {
                "healthy_processes": 2,
                "busy_processes": 2,
                "idle_processes": 0
            }
        },
        {
            "name": "无健康进程",
            "stats": {
                "healthy_processes": 0,
                "busy_processes": 0,
                "idle_processes": 0
            }
        }
    ]

    # 测试不同场景下的路由决策
    for scenario in scenarios:
        logger.info(f"\n场景: {scenario['name']}")
        logger.info(f"  统计: {scenario['stats']}")

        # 测试不同优先级的任务
        priorities = ["low", "normal", "high", "urgent"]

        for priority in priorities:
            context = ExecutionContext(
                session_id=f"test-{priority}",
                prompt="测试任务",
                mode="auto",
                context={"priority": priority}
            )

            should_use_cli, reason = strategy.should_use_cli(
                scenario['stats'],
                context
            )

            logger.info(
                f"  优先级={priority:8} -> "
                f"{'CLI' if should_use_cli else 'Web':4} "
                f"({reason})"
            )


async def example_smart_router():
    """示例：使用智能路由器执行任务"""
    from app.gateway.router import SmartRouter, HybridStrategy
    from app.gateway.adapters import WebAdapter, CLIAdapter
    from app.gateway.adapters.base import ExecutionContext

    logger.info("\n=== 智能路由器示例 ===")

    # 创建适配器（使用 Mock 进行演示）
    # 在实际使用中，您会使用真实的适配器

    # Web 适配器配置
    web_config = {
        "server_url": "http://127.0.0.1:4096",
        "timeout": 300
    }

    # CLI 适配器配置
    cli_config = {
        "pool_size": 2,
        "server_url": "http://127.0.0.1:4096",
        "model": "new-api/glm-4.7"
    }

    # 创建混合策略
    strategy = HybridStrategy(
        low_load_threshold=0.5,
        high_load_threshold=0.8
    )

    logger.info(f"创建智能路由器，使用 {strategy.name} 策略")

    # 注意：这里使用 Mock 适配器进行演示
    # 在实际使用中，您会创建真实的适配器实例
    # router = SmartRouter(
    #     cli_adapter=CLIAdapter(config=cli_config),
    #     web_adapter=WebAdapter(config=web_config),
    #     strategy=strategy
    # )

    logger.info("路由器配置:")
    logger.info(f"  - 策略: {strategy.name}")
    logger.info(f"  - 低负载阈值: {strategy.low_load_threshold:.1%}")
    logger.info(f"  - 高负载阈值: {strategy.high_load_threshold:.1%}")
    logger.info(f"  - 低负载最大等待: {strategy.max_wait_time_low_load}s")
    logger.info(f"  - 高负载最大等待: {strategy.max_wait_time_high_load}s")


async def example_routing_simulation():
    """示例：模拟路由决策过程"""
    from app.gateway.router import HybridStrategy
    from app.gateway.adapters.base import ExecutionContext

    logger.info("\n=== 路由决策模拟 ===")

    strategy = HybridStrategy()

    # 模拟任务队列
    tasks = [
        {"prompt": "简单任务", "priority": "normal"},
        {"prompt": "复杂任务", "priority": "high"},
        {"prompt": "紧急修复", "priority": "urgent"},
        {"prompt": "常规任务", "priority": "low"},
    ]

    # 模拟系统状态变化
    system_states = [
        {
            "name": "系统启动（空闲）",
            "stats": {
                "healthy_processes": 2,
                "busy_processes": 0,
                "idle_processes": 2
            }
        },
        {
            "name": "负载增加（50%）",
            "stats": {
                "healthy_processes": 2,
                "busy_processes": 1,
                "idle_processes": 1
            }
        },
        {
            "name": "高峰期（100%）",
            "stats": {
                "healthy_processes": 2,
                "busy_processes": 2,
                "idle_processes": 0
            }
        }
    ]

    for state in system_states:
        logger.info(f"\n【{state['name']}】")
        logger.info(f"系统状态: {state['stats']}")

        for task in tasks:
            context = ExecutionContext(
                session_id=f"task-{task['prompt'][:5]}",
                prompt=task['prompt'],
                mode="auto",
                context={"priority": task['priority']}
            )

            should_use_cli, reason = strategy.should_use_cli(
                state['stats'],
                context
            )

            adapter = "CLI (快速)" if should_use_cli else "Web (降级)"
            logger.info(
                f"  任务: {task['prompt']:12} | "
                f"优先级: {task['priority']:8} | "
                f"选择: {adapter:15} | "
                f"原因: {reason}"
            )


async def example_custom_strategy():
    """示例：创建自定义混合策略"""
    from app.gateway.router import HybridStrategy

    logger.info("\n=== 自定义混合策略示例 ===")

    # 创建一个更激进的策略：
    # - 更倾向于使用 CLI（更高的高负载阈值）
    # - 愿意等待更长时间（更高的等待时间限制）
    aggressive_strategy = HybridStrategy(
        low_load_threshold=0.6,      # 60% 以下才认为低负载
        high_load_threshold=0.9,     # 90% 以上才认为高负载
        max_wait_time_low_load=20.0,  # 低负载时最多等待 20 秒
        max_wait_time_high_load=5.0   # 高负载时最多等待 5 秒
    )

    logger.info("激进策略配置:")
    logger.info(f"  - 低负载阈值: {aggressive_strategy.low_load_threshold:.1%}")
    logger.info(f"  - 高负载阈值: {aggressive_strategy.high_load_threshold:.1%}")
    logger.info(f"  - 最大等待时间（低负载）: {aggressive_strategy.max_wait_time_low_load}s")
    logger.info(f"  - 最大等待时间（高负载）: {aggressive_strategy.max_wait_time_high_load}s")

    # 创建一个更保守的策略：
    # - 更倾向于降级到 Web（更低的阈值）
    # - 不愿意等待（更低的等待时间限制）
    conservative_strategy = HybridStrategy(
        low_load_threshold=0.3,      # 30% 以下才认为低负载
        high_load_threshold=0.6,     # 60% 以上就认为高负载
        max_wait_time_low_load=5.0,   # 低负载时最多等待 5 秒
        max_wait_time_high_load=1.0   # 高负载时最多等待 1 秒
    )

    logger.info("\n保守策略配置:")
    logger.info(f"  - 低负载阈值: {conservative_strategy.low_load_threshold:.1%}")
    logger.info(f"  - 高负载阈值: {conservative_strategy.high_load_threshold:.1%}")
    logger.info(f"  - 最大等待时间（低负载）: {conservative_strategy.max_wait_time_low_load}s")
    logger.info(f"  - 最大等待时间（高负载）: {conservative_strategy.max_wait_time_high_load}s")

    # 比较两种策略在同一场景下的决策
    test_stats = {
        "healthy_processes": 2,
        "busy_processes": 1,
        "idle_processes": 1
    }

    logger.info(f"\n测试场景: {test_stats}")

    from app.gateway.adapters.base import ExecutionContext

    context = ExecutionContext(
        session_id="test",
        prompt="测试",
        mode="auto",
        context={"priority": "normal"}
    )

    aggressive_decision = aggressive_strategy.should_use_cli(test_stats, context)
    conservative_decision = conservative_strategy.should_use_cli(test_stats, context)

    logger.info(
        f"激进策略: {'CLI' if aggressive_decision[0] else 'Web'} - {aggressive_decision[1]}"
    )
    logger.info(
        f"保守策略: {'CLI' if conservative_decision[0] else 'Web'} - {conservative_decision[1]}"
    )


async def example_priority_handling():
    """示例：任务优先级处理"""
    from app.gateway.router import HybridStrategy
    from app.gateway.adapters.base import ExecutionContext

    logger.info("\n=== 任务优先级处理示例 ===")

    strategy = HybridStrategy()

    # 高负载场景
    high_load_stats = {
        "healthy_processes": 2,
        "busy_processes": 2,
        "idle_processes": 0
    }

    logger.info(f"场景: 高负载 {high_load_stats}")

    # 测试不同优先级
    priorities = [
        ("low", "低优先级"),
        ("normal", "普通优先级"),
        ("high", "高优先级"),
        ("urgent", "紧急任务")
    ]

    logger.info("\n优先级处理结果:")
    for priority, description in priorities:
        context = ExecutionContext(
            session_id=f"task-{priority}",
            prompt="测试任务",
            mode="auto",
            context={"priority": priority}
        )

        should_use_cli, reason = strategy.should_use_cli(
            high_load_stats,
            context
        )

        adapter = "CLI (快速通道)" if should_use_cli else "Web (降级)"
        logger.info(
            f"  {description:12} -> {adapter:20} ({reason})"
        )


async def main():
    """主函数：运行所有示例"""
    logger.info("OpenCode 混合路由策略演示")
    logger.info("=" * 60)

    # 1. 混合策略基本使用
    await example_hybrid_strategy()

    # 2. 智能路由器
    await example_smart_router()

    # 3. 路由决策模拟
    await example_routing_simulation()

    # 4. 自定义策略
    await example_custom_strategy()

    # 5. 优先级处理
    await example_priority_handling()

    logger.info("\n" + "=" * 60)
    logger.info("演示完成！")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
