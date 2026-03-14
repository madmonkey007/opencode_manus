"""
网关集成示例

展示如何使用网关的完整功能：认证、限流、路由
"""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.gateway import (
    Gateway,
    GatewayConfig,
    SubmitTaskRequest,
    AuthManager,
    AuthContext,
    RateLimiter,
    RateLimitConfig,
    WebAdapter,
    CLIAdapter,
    HybridStrategy
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_basic_gateway():
    """示例：基础网关使用"""
    print("\n=== 示例1：基础网关使用 ===\n")

    # 创建适配器（使用 Mock 配置）
    web_config = {
        "server_url": "http://127.0.0.1:4096",
        "timeout": 300
    }

    cli_config = {
        "pool_size": 2,
        "server_url": "http://127.0.0.1:4096",
        "model": "new-api/glm-4.7"
    }

    # 创建网关（禁用认证和限流）
    config = GatewayConfig(
        enable_auth=False,
        enable_rate_limit=False
    )

    gateway = Gateway(
        cli_adapter=CLIAdapter(config=cli_config),
        web_adapter=WebAdapter(config=web_config),
        config=config
    )

    print("网关已创建")
    print(f"  - 认证: {'启用' if config.enable_auth else '禁用'}")
    print(f"  - 限流: {'启用' if config.enable_rate_limit else '禁用'}")

    # 创建任务请求
    request = SubmitTaskRequest(
        prompt="创建一个Hello World程序",
        mode="build",
        priority="normal"
    )

    print(f"\n提交任务: {request.prompt}")

    # 注意：这里会尝试执行真实任务，可能失败
    # 在实际使用中，您需要确保 OpenCode 服务正在运行
    try:
        response = await gateway.submit_task(request)

        print(f"\n任务响应:")
        print(f"  - 成功: {response.success}")
        print(f"  - 任务ID: {response.task_id}")
        print(f"  - 会话ID: {response.session_id}")
        print(f"  - 消息: {response.message}")

        if response.success:
            print(f"  - 执行时间: {response.execution_time:.2f}秒")
            print(f"  - 使用适配器: {response.adapter_used}")
            print(f"  - 路由原因: {response.route_reason}")

    except Exception as e:
        print(f"\n任务执行失败: {e}")

    # 查看网关指标
    metrics = gateway.get_metrics()
    print(f"\n网关指标:")
    print(f"  - 总请求数: {metrics['total_requests']}")
    print(f"  - 成功请求数: {metrics['successful_requests']}")
    print(f"  - 失败请求数: {metrics['failed_requests']}")
    print(f"  - 成功率: {metrics['success_rate']:.1%}")


async def example_with_auth():
    """示例：使用认证的网关"""
    print("\n=== 示例2：使用认证的网关 ===\n")

    # 创建认证管理器
    auth_manager = AuthManager()

    # 生成 API Key
    user_id = "user123"
    api_key = auth_manager.create_api_key(
        user_id=user_id,
        expires_in_days=365,
        permissions=["execute", "read"]
    )

    print(f"已为用户 {user_id} 生成 API Key")
    print(f"  API Key: {api_key[:20]}...")

    # 生成 JWT Token
    jwt_token = auth_manager.create_jwt_token(
        user_id=user_id,
        expires_in_hours=24,
        permissions=["execute", "read"]
    )

    print(f"\n已生成 JWT Token")
    print(f"  Token: {jwt_token[:20]}...")

    # 创建认证上下文
    auth_context = AuthContext(
        user_id=user_id,
        auth_type="api_key",
        credentials={"api_key": api_key},
        permissions=["execute", "read"]
    )

    # 验证认证
    is_valid, error = await auth_manager.verify(auth_context)

    print(f"\n认证验证:")
    print(f"  - 有效: {is_valid}")
    if error:
        print(f"  - 错误: {error}")


async def example_with_rate_limit():
    """示例：使用限流的网关"""
    print("\n=== 示例3：使用限流的网关 ===\n")

    # 创建限流器
    rate_limiter = RateLimiter(
        default_limit=5,  # 每分钟5个请求
        default_window=60
    )

    await rate_limiter.start()

    print("限流器已启动")
    print(f"  - 限制: 5 请求/分钟")

    # 创建网关（启用限流，禁用认证）
    config = GatewayConfig(
        enable_auth=False,
        enable_rate_limit=True,
        default_rate_limit=5,
        rate_limit_window=60
    )

    # 模拟限流测试
    user_id = "user123"

    print(f"\n测试用户 {user_id} 的限流:")

    for i in range(7):
        try:
            await rate_limiter.check_limit(
                key=f"user:{user_id}",
                limit=5,
                window=60
            )
            print(f"  请求 {i+1}: 成功")

        except Exception as e:
            print(f"  请求 {i+1}: 被限流 ({e})")

    # 查看限流器统计
    stats = rate_limiter.get_stats()
    print(f"\n限流器统计:")
    print(f"  - 令牌桶数量: {stats['total_buckets']}")
    print(f"  - 默认限制: {stats['default_limit']} 请求/{stats['default_window']}秒")

    await rate_limiter.stop()


async def example_complete_gateway():
    """示例：完整的网关功能"""
    print("\n=== 示例4：完整的网关功能 ===\n")

    # 创建所有组件
    auth_manager = AuthManager()
    rate_limiter = RateLimiter()
    await rate_limiter.start()

    # 创建配置
    config = GatewayConfig(
        enable_auth=True,
        enable_rate_limit=True,
        default_rate_limit=100,
        rate_limit_window=60
    )

    # 创建适配器
    web_adapter = WebAdapter(config={
        "server_url": "http://127.0.0.1:4096"
    })

    cli_adapter = CLIAdapter(config={
        "pool_size": 2,
        "server_url": "http://127.0.0.1:4096"
    })

    # 创建网关
    gateway = Gateway(
        cli_adapter=cli_adapter,
        web_adapter=web_adapter,
        auth_manager=auth_manager,
        rate_limiter=rate_limiter,
        config=config
    )

    print("网关已创建（完整功能）")
    print(f"  - 认证: 启用")
    print(f"  - 限流: 启用")
    print(f"  - 智能路由: 启用")

    # 创建用户和 API Key
    user_id = "user456"
    api_key = auth_manager.create_api_key(user_id)

    print(f"\n已创建用户 {user_id}")

    # 创建认证上下文
    auth_context = AuthContext(
        user_id=user_id,
        auth_type="api_key",
        credentials={"api_key": api_key}
    )

    # 创建任务请求
    request = SubmitTaskRequest(
        prompt="创建一个待办事项应用",
        mode="build",
        priority="high"
    )

    print(f"\n提交任务: {request.prompt}")
    print(f"  - 模式: {request.mode}")
    print(f"  - 优先级: {request.priority}")

    # 提交任务
    try:
        response = await gateway.submit_task(
            request=request,
            auth_context=auth_context
        )

        print(f"\n任务响应:")
        print(f"  - 成功: {response.success}")
        print(f"  - 消息: {response.message}")

    except Exception as e:
        print(f"\n任务执行失败: {e}")

    # 查看完整指标
    metrics = gateway.get_metrics()

    print(f"\n网关完整指标:")
    print(f"  - 运行时间: {metrics['uptime_seconds']:.1f}秒")
    print(f"  - 总请求数: {metrics['total_requests']}")
    print(f"  - 成功请求数: {metrics['successful_requests']}")
    print(f"  - 失败请求数: {metrics['failed_requests']}")
    print(f"  - 认证请求数: {metrics['authenticated_requests']}")
    print(f"  - 限流请求数: {metrics['rate_limited_requests']}")
    print(f"  - 成功率: {metrics['success_rate']:.1%}")
    print(f"  - QPS: {metrics['requests_per_second']:.2f}")

    # 路由器统计
    router_stats = metrics['router']
    print(f"\n路由器统计:")
    print(f"  - 总路由数: {router_stats['total_routes']}")
    print(f"  - CLI 路由数: {router_stats['cli_routes']}")
    print(f"  - Web 路由数: {router_stats['web_routes']}")
    print(f"  - CLI 使用率: {router_stats['cli_usage_rate']:.1%}")

    await rate_limiter.stop()


async def main():
    """主函数"""
    print("\nOpenCode 网关集成示例")
    print("=" * 60)

    # 示例1：基础网关使用
    await example_basic_gateway()

    # 示例2：使用认证
    await example_with_auth()

    # 示例3：使用限流
    await example_with_rate_limit()

    # 示例4：完整功能
    await example_complete_gateway()

    print("\n" + "=" * 60)
    print("所有示例执行完毕")


if __name__ == "__main__":
    asyncio.run(main())
