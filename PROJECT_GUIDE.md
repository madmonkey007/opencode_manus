# OpenCode 项目快速上手指南

## 🎯 5分钟快速了解项目

### 项目核心功能
- **AI辅助编程助手**: 支持Build和Plan两种模式
- **多任务管理**: 支持创建、切换、追问多个任务
- **实时交互**: SSE流式响应，实时显示进度
- **Docker部署**: 一键启动，包含VNC可视化界面

### 技术栈
- **后端**: FastAPI + Python 3.12
- **前端**: React + Vanilla JS
- **AI模型**: OpenAI API (glm-4.7)
- **容器**: Docker + Docker Compose

---

## 🚀 快速启动（3分钟）

### 1. 克隆并启动
```bash
cd /d/manus/opencode
docker-compose up -d
```

### 2. 访问应用
- **主界面**: http://localhost:8089
- **VNC可视化**: http://localhost:6901 (密码: vnc)

### 3. 验证运行
```bash
# 健康检查
curl http://localhost:8089/health

# 查看日志
docker-compose logs opencode
```

---

## 📊 项目架构（2分钟）

### 核心文件
```
关键文件说明：
app/main.py                 # FastAPI主应用（健康检查、路由注册）
app/api.py                  # OpenCode专用API端点
app/opencode_client.py      # OpenCode CLI客户端
app/server_manager.py       # OpenCodeServerManager类（性能优化核心）
app/managers_internal/       # Manager集中管理（新增，解决循环导入）
static/opencode.js          # 前端JavaScript核心
```

### 数据流
```
用户请求 → FastAPI → OpenCodeServerManager → OpenCode CLI → SSE流 → 前端显示
                              ↓
                         持久服务器（首次15秒启动，后续复用）
```

---

## 🔧 最近优化工作（了解即可）

### 1. 安全加固（已完成）
- CORS配置: 从通配符改为限制特定来源
- 路径遍历: 添加路径规范化验证
- SSL验证: HTTP请求添加证书验证
- 资源限制: 子进程CPU/内存限制

### 2. 性能优化（部分完成）
- **目标**: 新建任务从70秒降到2秒
- **原理**: OpenCodeServerManager懒加载 + 持久服务器
- **状态**: 
  - ✅ 循环导入问题已解决
  - ✅ 代码架构已优化
  - ⚠️ 待验证: 新建任务速度优化效果

### 3. 架构重构（已完成）
- 创建 `app/managers_internal/` 模块
- 避免循环导入: `app/main → app/api → app.managers_internal`
- 单一职责: 集中管理所有Manager实例

---

## ⚠️ 当前已知问题

### P0级（影响功能）
1. **API端点404错误**
   - 端点: `/opencode/session/{id}/messages`
   - 原因: 空消息列表返回404而不是200
   - 影响: 新建任务功能部分受阻
   - 解决方案: 修改messages端点逻辑

### P1级（影响开发体验）
1. **Docker部署流程**
   - 问题: 容器代码版本可能不是最新
   - 原因: Docker构建失败后的手动修复流程
   - 解决方案: 添加版本验证脚本

---

## 📝 下个会话快速优化指南

### 步骤1: 修复P0问题（5分钟）
```bash
# 1. 定位问题
cd /d/manus/opencode
grep -n "Session not found" app/api.py

# 2. 修复逻辑（返回200而非404）
# 文件: app/api.py 第345-387行
# 修复: 空消息列表返回200 + 空数组

# 3. 测试修复
curl http://localhost:8089/opencode/session/{session_id}/messages
```

### 步骤2: 验证性能优化（10分钟）
```bash
# 1. 重启容器
docker-compose restart

# 2. 测试新建任务速度
# - 访问 http://localhost:8089
# - 点击"新任务"
# - 输入简单任务
# - 点击"添加"
# - 记录时间: 应该约2秒（不是70秒）

# 3. 多次测试验证
# - 重复创建3-5个任务
# - 每次都应该很快（2秒左右）
```

### 步骤3: 验证持续优化效果（15分钟）
```bash
# 1. 创建第一个任务（应该15秒启动opencode serve）
# 2. 创建第二个任务（应该2秒复用服务器）
# 3. 在第一个任务中追问（应该2秒）
# 4. 在第二个任务中追问（应该2秒）

# 预期结果:
# - 首次操作: 15秒
# - 后续所有操作: 2秒
# - 性能提升: 87%
```

---

## 🧪 常用测试命令

### API测试
```bash
# 健康检查
curl http://localhost:8089/health

# 获取session列表
curl http://localhost:8089/opencode/sessions | python -m json.tool

# 获取session消息（修复后）
curl http://localhost:8089/opencode/session/{session_id}/messages | python -m json.tool

# 创建新session
curl -X POST http://localhost:8089/opencode/session | python -m json.tool
```

### Docker测试
```bash
# 查看容器状态
docker-compose ps

# 查看日志（实时）
docker-compose logs -f opencode

# 查看最近100行日志
docker-compose logs --tail=100 opencode

# 重启容器
docker-compose restart

# 进入容器调试
docker exec -it opencode-container /bin/bash

# 检查容器中的Git版本
docker exec opencode-container git log --oneline -1
```

### 性能测试
```bash
# 测试容器启动时间
time docker-compose up -d

# 测试API响应时间
time curl http://localhost:8089/health

# 测试session创建时间
time curl -X POST http://localhost:8089/opencode/session
```

---

## 🔍 问题诊断流程

### 问题1: API返回404
```bash
# 1. 检查路由是否注册
docker exec opencode-container python -c "
from app.api import router
print([r.path for r in router.routes])
"

# 2. 检查前端请求的路径
# 打开浏览器DevTools -> Network -> 查看请求URL

# 3. 检查数据库中是否有对应数据
docker exec opencode-container python -c "
import sqlite3
conn = sqlite3.connect('/app/opencode/workspace/history.db')
c = conn.cursor()
c.execute('SELECT * FROM sessions LIMIT 5')
print(c.fetchall())
"
```

### 问题2: 性能没有提升
```bash
# 1. 检查OpenCodeServerManager是否被使用
docker logs opencode-container | grep "Using global OpenCodeServerManager"

# 2. 检查opencode serve进程是否运行
docker exec opencode-container ps aux | grep opencode

# 3. 检查是否有多个opencode进程（可能导致冲突）
docker exec opencode-container ps aux | grep -c opencode
```

### 问题3: 容器代码不是最新
```bash
# 1. 对比本地和容器的Git版本
LOCAL_VERSION=$(cd /d/manus/opencode && git log --oneline -1)
CONTAINER_VERSION=$(docker exec opencode-container git log --oneline -1)

echo "Local: $LOCAL_VERSION"
echo "Container: $CONTAINER_VERSION"

if [ "$LOCAL_VERSION" != "$CONTAINER_VERSION" ]; then
    echo "❌ Version mismatch!"
    # 2. 复制最新代码到容器
    docker cp app/main.py opencode-container:/app/opencode/app/main.py
    docker cp app/api.py opencode-container:/app/opencode/app/api.py
    docker cp app/opencode_client.py opencode-container:/app/opencode/app/opencode_client.py
    docker cp app/managers_internal opencode-container:/app/opencode/app/
    
    # 3. 重启app进程
    docker exec opencode-container supervisorctl restart app
fi
```

---

## 📊 性能基准

### 当前性能（未优化）
- 容器启动: 3.7秒
- 新建任务: 70秒（每次启动新opencode进程）
- 追问: 70秒（每次启动新opencode进程）

### 预期性能（优化后）
- 容器启动: 3.7秒
- 首次opencode请求: 15秒（启动持久服务器）
- 新建任务: 2秒（复用服务器）
- 追问: 2秒（复用服务器）

### 性能提升
- 新建任务: 70秒 → 2秒 = **97%提升**
- 追问速度: 70秒 → 2秒 = **97%提升**

---

## 🎯 优化检查清单

在开始任何优化工作前，确认：

### 基础检查
- [ ] Docker容器运行正常
- [ ] 前端可以访问（http://localhost:8089）
- [ ] 数据库连接正常
- [ ] API端点响应正常

### 性能检查
- [ ] 首次opencode请求约15秒
- [ ] 新建任务约2秒
- [ ] 追问约2秒
- [ ] 多个任务之间无性能差异

### 代码检查
- [ ] 容器中的Git版本与本地一致
- [ ] 循环导入已解决（无模块导入错误）
- [ ] OpenCodeServerManager被正确使用
- [ ] 日志中无重大错误

---

## 📚 参考资源

### 关键文档
- 详细项目文档: `HANDOVER.md`
- Git提交历史: `git log --oneline -20`
- Docker配置: `docker-compose.yml`, `Dockerfile`

### 常用链接
- 前端: http://localhost:8089
- VNC: http://localhost:6901 (密码: vnc)
- API健康检查: http://localhost:8089/health

---

## 🆘 获取帮助

### 常见问题
**Q: Docker容器无法启动？**
A: 检查端口8089是否被占用，运行 `docker-compose ps` 查看状态

**Q: API返回404？**
A: 检查前端请求的路径是否正确，参考API端点列表

**Q: 性能没有提升？**
A: 检查OpenCodeServerManager是否被使用，查看日志中的"Using global OpenCodeServerManager"

### 联系方式
- 项目位置: `/d/manus/opencode`
- 日志位置: `docker logs opencode-container`
- 数据库位置: `/d/manus/opencode/workspace/history.db`

---

**最后更新**: 2026-03-09
**版本**: 1.0
**适用于**: OpenCode项目，基于commit 7e140fc（managers_internal模块创建）

祝下个会话优化顺利！🚀