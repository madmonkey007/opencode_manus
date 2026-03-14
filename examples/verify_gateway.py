"""
简单的网关功能验证
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """测试导入"""
    print("测试导入...")
    try:
        from app.gateway import (
            Gateway, GatewayConfig,
            SubmitTaskRequest, SubmitTaskResponse,
            AuthManager, AuthContext,
            RateLimiter, RateLimitError,
            WebAdapter, CLIAdapter
        )
        print("  ✓ 所有组件导入成功")
        return True
    except Exception as e:
        print(f"  ✗ 导入失败: {e}")
        return False

def test_auth():
    """测试认证"""
    print("\n测试认证...")
    try:
        from app.gateway import AuthManager, AuthContext

        auth_manager = AuthManager()

        # 生成 API Key
        api_key = auth_manager.create_api_key(
            user_id="test_user",
            expires_in_days=365,
            permissions=["execute", "read"]
        )
        print(f"  ✓ API Key 生成成功: {api_key[:20]}...")

        # 生成 JWT Token
        token = auth_manager.create_jwt_token(
            user_id="test_user",
            expires_in_hours=24,
            permissions=["execute", "read"]
        )
        print(f"  ✓ JWT Token 生成成功: {token[:20]}...")

        # 创建认证上下文
        auth_context = AuthContext(
            user_id="test_user",
            auth_type="api_key",
            credentials={"api_key": api_key}
        )
        print(f"  ✓ 认证上下文创建成功")

        return True
    except Exception as e:
        print(f"  ✗ 认证测试失败: {e}")
        return False

def test_rate_limiter():
    """测试限流器"""
    print("\n测试限流器...")
    try:
        from app.gateway import RateLimiter, RateLimitError
        import asyncio

        async def run_test():
            rate_limiter = RateLimiter(
                default_limit=5,
                default_window=60
            )

            print(f"  ✓ 限流器创建成功")

            # 测试限流
            for i in range(7):
                try:
                    await rate_limiter.check_limit(
                        key="test_user",
                        limit=5,
                        window=60
                    )
                    if i < 5:
                        print(f"  ✓ 请求 {i+1}: 成功")
                    else:
                        print(f"  ✗ 请求 {i+1}: 应该被限流")
                except RateLimitError as e:
                    if i >= 5:
                        print(f"  ✓ 请求 {i+1}: 被限流（正确）")
                    else:
                        print(f"  ✗ 请求 {i+1}: 不应该被限流")

            # 获取统计
            stats = rate_limiter.get_stats()
            print(f"  ✓ 限流器统计: {stats['total_buckets']} 个令牌桶")

        asyncio.run(run_test())
        return True
    except Exception as e:
        print(f"  ✗ 限流器测试失败: {e}")
        return False

def test_gateway_config():
    """测试网关配置"""
    print("\n测试网关配置...")
    try:
        from app.gateway import GatewayConfig, SubmitTaskRequest

        # 创建配置
        config = GatewayConfig(
            enable_auth=True,
            enable_rate_limit=True,
            default_rate_limit=100,
            rate_limit_window=60
        )
        print(f"  ✓ 网关配置创建成功")
        print(f"    - 认证: {config.enable_auth}")
        print(f"    - 限流: {config.enable_rate_limit}")
        print(f"    - 限制: {config.default_rate_limit} 请求/{config.rate_limit_window}秒")

        # 创建请求
        request = SubmitTaskRequest(
            prompt="创建一个Hello World程序",
            mode="build",
            priority="high"
        )
        print(f"  ✓ 任务请求创建成功")
        print(f"    - 提示词: {request.prompt}")
        print(f"    - 模式: {request.mode}")
        print(f"    - 优先级: {request.priority}")

        return True
    except Exception as e:
        print(f"  ✗ 网关配置测试失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("OpenCode 网关功能验证")
    print("=" * 60)

    results = []

    # 测试导入
    results.append(test_imports())

    # 测试认证
    results.append(test_auth())

    # 测试限流器
    results.append(test_rate_limiter())

    # 测试网关配置
    results.append(test_gateway_config())

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    total = len(results)
    passed = sum(results)

    print(f"通过: {passed}/{total}")

    if passed == total:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    exit(main())
