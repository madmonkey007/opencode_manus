"""
混合路由策略简化演示

只展示路由决策逻辑，不涉及实际的适配器初始化
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.gateway.router import HybridStrategy
from app.gateway.adapters.base import ExecutionContext


def print_section(title):
    """打印分节标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def main():
    """主函数"""
    print("\nOpenCode 混合路由策略演示")
    print_section("策略配置")

    # 创建混合策略
    strategy = HybridStrategy(
        low_load_threshold=0.5,      # 50% 以下视为低负载
        high_load_threshold=0.8,     # 80% 以上视为高负载
        max_wait_time_low_load=10.0,  # 低负载时最多等待 10 秒
        max_wait_time_high_load=2.0   # 高负载时最多等待 2 秒
    )

    print(f"策略名称: {strategy.name}")
    print(f"低负载阈值: {strategy.low_load_threshold:.1%}")
    print(f"高负载阈值: {strategy.high_load_threshold:.1%}")
    print(f"低负载最大等待: {strategy.max_wait_time_low_load}s")
    print(f"高负载最大等待: {strategy.max_wait_time_high_load}s")

    # 场景1：不同负载下的路由决策
    print_section("场景1：不同负载下的路由决策")

    scenarios = [
        {
            "name": "🟢 低负载（有空闲进程）",
            "stats": {
                "healthy_processes": 2,
                "busy_processes": 0,
                "idle_processes": 2
            }
        },
        {
            "name": "🟡 中负载（50% 忙碌）",
            "stats": {
                "healthy_processes": 2,
                "busy_processes": 1,
                "idle_processes": 1
            }
        },
        {
            "name": "🔴 高负载（100% 忙碌）",
            "stats": {
                "healthy_processes": 2,
                "busy_processes": 2,
                "idle_processes": 0
            }
        }
    ]

    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print(f"  状态: {scenario['stats']}")

        # 普通优先级任务
        context = ExecutionContext(
            session_id="test",
            prompt="测试任务",
            mode="auto",
            context={"priority": "normal"}
        )

        should_use_cli, reason = strategy.should_use_cli(
            scenario['stats'],
            context
        )

        adapter = "⚡ CLI (快速)" if should_use_cli else "🌐 Web (降级)"
        print(f"  普通任务 -> {adapter}")
        print(f"  原因: {reason}")

    # 场景2：任务优先级处理
    print_section("场景2：高负载下的优先级处理")

    high_load_stats = {
        "healthy_processes": 2,
        "busy_processes": 2,
        "idle_processes": 0
    }

    print(f"\n场景: 高负载 {high_load_stats}")
    print("\n不同优先级的处理:")

    priorities = [
        ("low", "低优先级", "📦 常规任务"),
        ("normal", "普通优先级", "📋 标准任务"),
        ("high", "高优先级", "🔥 重要任务"),
        ("urgent", "紧急优先级", "🚨 紧急修复")
    ]

    for priority, description, emoji in priorities:
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

        adapter = "⚡ CLI (快速)" if should_use_cli else "🌐 Web (降级)"
        print(f"  {emoji} {description:12} -> {adapter:20} ({reason})")

    # 场景3：自定义策略对比
    print_section("场景3：激进 vs 保守策略")

    # 激进策略：更倾向于使用 CLI
    aggressive = HybridStrategy(
        low_load_threshold=0.6,
        high_load_threshold=0.9,
        max_wait_time_low_load=20.0,
        max_wait_time_high_load=5.0
    )

    # 保守策略：更倾向于降级到 Web
    conservative = HybridStrategy(
        low_load_threshold=0.3,
        high_load_threshold=0.6,
        max_wait_time_low_load=5.0,
        max_wait_time_high_load=1.0
    )

    test_stats = {
        "healthy_processes": 2,
        "busy_processes": 1,
        "idle_processes": 1
    }

    print(f"\n测试场景: 50% 忙碌 {test_stats}")

    context = ExecutionContext(
        session_id="test",
        prompt="测试任务",
        mode="auto",
        context={"priority": "normal"}
    )

    aggressive_decision = aggressive.should_use_cli(test_stats, context)
    conservative_decision = conservative.should_use_cli(test_stats, context)

    print(f"\n🎲 激进策略:")
    print(f"  - 低负载阈值: {aggressive.low_load_threshold:.1%}")
    print(f"  - 高负载阈值: {aggressive.high_load_threshold:.1%}")
    print(f"  - 决策: {'⚡ CLI' if aggressive_decision[0] else '🌐 Web'}")
    print(f"  - 原因: {aggressive_decision[1]}")

    print(f"\n🛡️ 保守策略:")
    print(f"  - 低负载阈值: {conservative.low_load_threshold:.1%}")
    print(f"  - 高负载阈值: {conservative.high_load_threshold:.1%}")
    print(f"  - 决策: {'⚡ CLI' if conservative_decision[0] else '🌐 Web'}")
    print(f"  - 原因: {conservative_decision[1]}")

    # 总结
    print_section("总结")

    print("""
✅ 混合策略的优势：

1. 📊 自适应负载
   - 低负载：优先使用 CLI，保证最快响应
   - 中负载：根据任务优先级智能决策
   - 高负载：降级到 Web，保证系统吞吐量

2. 🎯 优先级感知
   - 高优先级任务优先使用快速通道
   - 低优先级任务愿意降级以避免排队

3. ⚖️ 可配置性
   - 可根据实际需求调整阈值
   - 可选择激进或保守策略

4. 🚀 性能优化
   - 平衡响应时间和吞吐量
   - 用户体验可预测
    """)

    print_section("演示完成")


if __name__ == "__main__":
    main()
