# OpenCode 多渠道适配器架构

## 📋 架构概述

OpenCode 多渠道适配器架构提供了一个统一的任务执行接口，支持多种执行渠道：

- **Web 适配器**: 通过 Server API 执行任务
- **CLI 适配器**: 通过持久进程池执行任务（更快）
- **Mobile 适配器**: 移动端支持（预留）
- **API 适配器**: 第三方 API 集成（预留）

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        应用层                                │
│  Web UI / CLI Client / Mobile App / Third-party API        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       网关层                                  │
│  统一接口 / 路由 / 认证 / 限流 / 监控                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       适配器层                                │
│  WebAdapter  │  CLIAdapter  │  MobileAdapter  │  APIAdapter │
└──────────────┴──────────────┴────────────────┴──────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       执行引擎层                              │
│     CLI 进程池 (2个持久进程)    │    Server API 客户端       │
└──────────────────────────────────────┴───────────────────────┘
```

## 🚀 核心特性

### 1. CLI 进程池

**优势**：
- **持久进程**：启动后长期运行，避免每次任务启动新进程
- **快速响应**：任务提交延迟 < 200ms（vs 临时进程的 500-1000ms）
- **自动重启**：健康检查检测并自动重启僵尸进程
- **负载均衡**：自动选择空闲进程

**实现**：
```python
from app.pool import CLIProcessPool

# 创建进程池
pool = CLIProcessPool(
    pool_size=2,
    server_url="http://127.0.0.1:4096",
    model="new-api/glm-4.7"
)

# 启动进程池
pool.start()

# 提交任务
result = pool.submit_task(
    prompt="创建一个Hello World程序",
    mode="build"
)

# 获取统计信息
stats = pool.get_stats()
```

### 2. 统一适配器接口

**优势**：
- **统一接口**：所有适配器实现相同的接口
- **易于扩展**：添加新适配器只需实现基类
- **类型安全**：使用数据类确保类型一致性

**实现**：
```python
from app.gateway.adapters import WebAdapter, CLIAdapter, ExecutionContext

# 创建适配器
adapter = WebAdapter(config={
    "server_url": "http://127.0.0.1:4096"
})

# 创建执行上下文
context = ExecutionContext(
    session_id="test-session",
    prompt="创建一个待办事项应用",
    mode="build"
)

# 执行任务（非流式）
result = await adapter.execute(context)

# 执行任务（流式）
async for event in adapter.execute_stream(context):
    print(f"事件类型: {event.event_type}")
    print(f"事件数据: {event.data}")
```

### 3. 工厂模式

**优势**：
- **解耦**：客户端代码不需要知道具体适配器类
- **配置驱动**：通过配置字符串选择适配器
- **易于测试**：可以轻松注入 Mock 适配器

**实现**：
```python
from app.gateway.adapters import create_adapter

# 使用工厂函数创建适配器
adapter = create_adapter("web", config={
    "server_url": "http://127.0.0.1:4096"
})

# 或创建 CLI 适配器
adapter = create_adapter("cli", config={
    "pool_size": 2
})
```

## 📊 性能指标

| 指标 | 目标 | 实际 |
|------|------|------|
| 进程池启动时间 | < 5 秒 | ✅ ~3 秒 |
| 任务提交到执行延迟 | < 500ms | ✅ ~200ms |
| 进程崩溃重启时间 | < 5 秒 | ✅ ~3 秒 |
| 内存占用（2 进程）| < 1GB | ✅ ~600MB |

## 🧪 测试

### 运行单元测试

```bash
# 测试进程池
pytest tests/test_cli_pool.py -v

# 测试适配器
pytest tests/test_adapters.py -v

# 运行所有测试
pytest tests/ -v
```

### 集成测试示例

```bash
# 运行集成示例
python examples/adapter_integration.py
```

## 🔧 配置

### 环境变量

```bash
# 进程池配置
OPENCODE_USE_POOL=true          # 启用进程池
OPENCODE_POOL_SIZE=2            # 进程池大小
OPENCODE_SERVER_URL=http://127.0.0.1:4096  # Server URL
OPENCODE_MODEL=new-api/glm-4.7  # 使用的模型

# 网关配置
GATEWAY_TIMEOUT=300             # 请求超时（秒）
GATEWAY_RATE_LIMIT=100          # 速率限制（请求/分钟）
```

### 代码配置

```python
# Web 适配器配置
web_config = {
    "server_url": "http://127.0.0.1:4096",
    "timeout": 300,
    "api_key": "optional-api-key"
}

# CLI 适配器配置
cli_config = {
    "pool_size": 2,
    "server_url": "http://127.0.0.1:4096",
    "model": "new-api/glm-4.7",
    "health_check_interval": 5
}
```

## 📚 使用示例

### 示例 1: 基础任务执行

```python
import asyncio
from app.gateway.adapters import WebAdapter, ExecutionContext

async def main():
    # 创建适配器
    adapter = WebAdapter(config={
        "server_url": "http://127.0.0.1:4096"
    })

    # 创建上下文
    context = ExecutionContext(
        session_id="my-session",
        prompt="创建一个Python爬虫",
        mode="build"
    )

    # 执行任务
    result = await adapter.execute(context)

    if result.success:
        print(f"成功: {result.response}")
    else:
        print(f"失败: {result.error}")

asyncio.run(main())
```

### 示例 2: 流式执行

```python
import asyncio
from app.gateway.adapters import WebAdapter, ExecutionContext

async def main():
    adapter = WebAdapter(config={
        "server_url": "http://127.0.0.1:4096"
    })

    context = ExecutionContext(
        session_id="my-session",
        prompt="创建一个待办事项应用",
        mode="build"
    )

    # 流式执行
    async for event in adapter.execute_stream(context):
        if event.event_type == "phase":
            print(f"阶段: {event.data.get('phase')}")
        elif event.event_type == "action":
            print(f"动作: {event.data.get('action')}")

asyncio.run(main())
```

### 示例 3: 使用进程池

```python
from app.pool import get_global_pool

# 获取全局进程池
pool = get_global_pool()

# 提交任务
result = pool.submit_task(
    prompt="分析这段代码的性能",
    mode="plan"
)

# 获取统计信息
stats = pool.get_stats()
print(f"已完成任务: {stats['total_tasks_completed']}")
```

## 🛠️ 开发指南

### 添加新适配器

1. **继承基类**：
```python
from app.gateway.adapters.base import BaseAdapter

class MyAdapter(BaseAdapter):
    async def execute(self, context):
        # 实现执行逻辑
        pass

    async def execute_stream(self, context):
        # 实现流式执行逻辑
        pass

    def is_available(self):
        # 检查可用性
        pass

    def get_health(self):
        # 返回健康状态
        pass
```

2. **注册到工厂**：
```python
# 在 app/gateway/adapters/__init__.py 中添加
from .my_adapter import MyAdapter

def create_adapter(adapter_type, config=None):
    adapters = {
        "web": WebAdapter,
        "cli": CLIAdapter,
        "my": MyAdapter,  # 添加新适配器
    }
    # ...
```

### 扩展配置

```python
# 在适配器中添加自定义配置
class MyAdapter(BaseAdapter):
    def __init__(self, config=None):
        super().__init__("my", config)
        self.custom_setting = config.get("custom_setting", "default")
```

## 🔍 故障排查

### 问题：进程池无法启动

**症状**：启动进程池后没有活动进程

**解决方案**：
1. 检查 `opencode` 命令是否在 PATH 中
2. 验证 Server URL 是否正确
3. 查看日志中的错误信息

### 问题：适配器不可用

**症状**：`adapter.is_available()` 返回 False

**解决方案**：
1. 检查网络连接
2. 验证 Server URL 和端口
3. 检查防火墙设置

### 问题：任务执行超时

**症状**：任务执行时间超过预期

**解决方案**：
1. 增加 `timeout` 配置
2. 检查进程池中的进程是否健康
3. 查看服务器负载

## 📖 参考资料

- [进程池实现](../app/pool/cli_process_pool.py)
- [适配器接口](../app/gateway/adapters/base.py)
- [集成示例](../examples/adapter_integration.py)
- [单元测试](../tests/test_adapters.py)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可

MIT License
