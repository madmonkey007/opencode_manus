# OpenCode Web Interface - 开发者指南

**版本**: 2.0.0
**最后更新**: 2026-02-10

---

## 📋 目录

1. [项目结构](#项目结构)
2. [技术栈](#技术栈)
3. [架构设计](#架构设计)
4. [开发环境设置](#开发环境设置)
5. [API 开发](#api-开发)
6. [前端开发](#前端开发)
7. [测试指南](#测试指南)
8. [部署指南](#部署指南)

---

## 🏗️ 项目结构

```
opencode/
├── app/                      # 后端应用
│   ├── __init__.py
│   ├── main.py               # FastAPI 主应用
│   ├── models.py             # Pydantic 数据模型
│   ├── managers.py           # Session/Message 管理
│   ├── api.py                # RESTful API 端点
│   ├── opencode_client.py    # CLI 客户端
│   └── history_service.py    # 历史服务
│
├── static/                   # 前端资源
│   ├── index.html            # 主页面
│   ├── opencode.js           # 核心逻辑
│   ├── api-client.js         # API 客户端
│   ├── event-adapter.js      # 事件适配器
│   ├── opencode-new-api-patch.js  # API 补丁
│   ├── code-preview-enhanced.js   # 增强版预览
│   ├── enhanced-task-panel.js     # 任务面板
│   └── ...
│
├── tests/                    # 测试
│   ├── test_api.py           # API 测试
│   ├── test_e2e.py           # 端到端测试
│   └── quick_test_e2e.py     # 快速验证
│
├── docs/                     # 文档
│   ├── api-migration-plan.md # 迁移计划
│   ├── phase*-summary.md     # 阶段总结
│   ├── USER_GUIDE.md         # 用户指南
│   └── DEVELOPER_GUIDE.md    # 开发者指南（本文件）
│
├── workspace/                # 工作区
│   └── {session_id}/         # 会话目录
│       ├── run.log           # 运行日志
│       └── status.txt        # 状态文件
│
└── CLAUDE.md                 # 项目文档
```

---

## 🛠️ 技术栈

### 后端

- **框架**: FastAPI 0.104+
- **Python**: 3.11+
- **数据验证**: Pydantic v2
- **异步**: asyncio
- **SSE**: Server-Sent Events

### 前端

- **框架**: Vanilla JavaScript
- **样式**: Tailwind CSS
- **图标**: Material Symbols
- **Markdown**: Marked.js
- **语法高亮**: Highlight.js

### 工具

- **CLI**: OpenCode CLI
- **进程**: asyncio subprocess
- **日志**: Python logging

---

## 🏛️ 架构设计

### 新架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ opencode.js  │  │ api-client.js│  │event-adapter │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           ↓ SSE
┌─────────────────────────────────────────────────────────────┐
│                        API 层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  REST API    │  │EventStreamMgr│  │OpenCodeClient│    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      管理层                                 │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │SessionManager│  │ MessageStore │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      数据层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ 内存存储     │  │ 文件系统     │  │ History DB  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      CLI 层                                │
│                   OpenCode CLI                              │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

```
用户输入
   ↓
opencode.js (submitTask)
   ↓
api-client.js (sendTextMessage)
   ↓
FastAPI (/opencode/session/{id}/message)
   ↓
SessionManager (创建 user/assistant message)
   ↓
BackgroundTasks (execute_opencode_message)
   ↓
OpenCodeClient (execute_message)
   ↓
CLI subprocess (opencode run --format json)
   ↓
_parse_line() (解析 JSON 输出)
   ↓
EventStreamManager (broadcast)
   ↓
EventSource (前端接收)
   ↓
event-adapter.js (adaptEvent)
   ↓
UI 更新 (renderResults)
```

---

## 🔧 开发环境设置

### 1. 克隆项目

```bash
git clone <repository-url>
cd opencode
```

### 2. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# 或手动安装主要依赖
pip install fastapi uvicorn pydantic python-multipart
```

### 3. 配置环境

```bash
# 复制配置文件
cp config/opencode.json.example config/opencode.json

# 编辑配置
vim config/opencode.json
```

### 4. 启动开发服务器

```bash
# 方式 1: 直接运行
python -m app.main

# 方式 2: 使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8088

# 方式 3: 使用 supervisord
supervisord -c supervisord.conf
```

### 5. 访问应用

打开浏览器访问 `http://localhost:8088`

---

## 🌐 API 开发

### 添加新端点

#### 1. 在 `app/api.py` 中添加路由

```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/opencode", tags=["opencode"])

@router.get("/custom_endpoint")
async def custom_endpoint(param: str):
    """自定义端点"""
    try:
        # 业务逻辑
        result = await some_function(param)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 2. 添加数据模型

在 `app/models.py` 中：

```python
from pydantic import BaseModel

class CustomRequest(BaseModel):
    field1: str
    field2: int = 0

class CustomResponse(BaseModel):
    status: str
    data: Optional[Dict] = None
```

### 添加新事件类型

#### 1. 定义事件

```python
event = {
    "type": "custom_event",
    "properties": {
        "key": "value"
    }
}
```

#### 2. 广播事件

```python
await event_stream_manager.broadcast(session_id, event)
```

#### 3. 前端适配

在 `event-adapter.js` 中：

```javascript
static adaptEvent(newEvent, session) {
    if (newEvent.type === 'custom_event') {
        return {
            type: 'custom',
            data: newEvent.properties
        };
    }
    return null;
}
```

---

## 🎨 前端开发

### 添加新组件

#### 1. 创建 JavaScript 文件

```javascript
// static/my-component.js

class MyComponent {
    constructor() {
        this.element = null;
        this.init();
    }

    init() {
        this.createDOM();
        this.bindEvents();
    }

    createDOM() {
        // 创建 DOM 元素
    }

    bindEvents() {
        // 绑定事件
    }

    render(data) {
        // 渲染数据
    }
}

// 初始化
window.myComponent = new MyComponent();
```

#### 2. 在 HTML 中引入

```html
<script src="/static/my-component.js"></script>
```

### 修改现有功能

#### 1. 修改任务面板

编辑 `static/enhanced-task-panel.js`

#### 2. 修改预览功能

编辑 `static/code-preview-enhanced.js`

#### 3. 修改事件处理

编辑 `static/opencode.js` 或 `static/event-adapter.js`

---

## 🧪 测试指南

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_api.py

# 运行端到端测试
python tests/test_e2e.py

# 快速验证
python tests/quick_test_e2e.py
```

### 编写测试

#### 1. API 测试

```python
# tests/test_my_feature.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_feature():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/opencode/my_endpoint")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
```

#### 2. 前端测试

使用浏览器控制台或自动化测试工具（Playwright, Selenium）

---

## 🚀 部署指南

### Docker 部署

#### 1. 构建 Docker 镜像

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "app.main"]
```

```bash
docker build -t opencode:latest .
```

#### 2. 运行容器

```bash
docker run -d -p 8088:8088 \
  -v $(pwd)/workspace:/app/workspace \
  opencode:latest
```

### 生产环境配置

#### 1. 使用 Gunicorn

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8088
```

#### 2. 使用 Nginx 反向代理

```nginx
location /opencode {
    proxy_pass http://localhost:8088;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;

    # SSE 支持
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
}
```

---

## 📊 性能优化

### 后端优化

1. **异步处理**: 使用 `asyncio` 和 `BackgroundTasks`
2. **缓存**: 添加 Redis 缓存层
3. **数据库**: 扩展到 PostgreSQL
4. **负载均衡**: 多实例部署

### 前端优化

1. **代码分割**: 按需加载组件
2. **CDN**: 静态资源 CDN
3. **压缩**: Gzip/Brotli 压缩
4. **缓存**: 浏览器缓存策略

---

## 🐛 调试技巧

### 后端调试

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)

# 在代码中添加日志
logger.debug("Debug info: %s", variable)
```

### 前端调试

```javascript
// 在浏览器控制台中
console.log('Debug info:', variable);

// 查看事件
console.table(sessions);

// 性能分析
console.time('operation');
// ... code ...
console.timeEnd('operation');
```

---

## 📝 贡献指南

### 代码规范

1. **Python**: 遵循 PEP 8
2. **JavaScript**: 使用 ESLint
3. **提交信息**: 使用 Conventional Commits

### 提交流程

1. Fork 项目
2. 创建特性分支
3. 提交代码
4. 创建 Pull Request

---

**最后更新**: 2026-02-10
**版本**: 2.0.0
