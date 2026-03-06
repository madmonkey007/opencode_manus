# 🔄 本地与Docker环境差异分析

## 📋 架构对比

### 本地环境（Windows）

```
Windows
├─ Python 3.12 (直接安装)
├─ 运行命令: python -m app.main
├─ 文件路径: D:\manus\opencode\
└─ 修改热重载: ✅ 支持（部分）
```

### Docker环境

```
Docker Container (opencode-container)
├─ Python 3.12-slim-bookworm (Linux)
├─ 运行命令: /app/opencode/app/start.sh
├─ 文件路径: /app/opencode/
└─ 修改热重载: ❌ 需要重启容器
```

---

## 🔍 关键差异点

### 1. 文件同步机制

**好消息**: ✅ **大部分修改会自动同步**

**docker-compose.yml配置**:
```yaml
volumes:
  - ./app:/app/opencode/app        # ✅ 自动同步
  - ./static:/app/opencode/static  # ✅ 自动同步
  - ./workspace:/app/opencode/workspace  # ✅ 自动同步
  - ./logs:/app/opencode/logs      # ✅ 自动同步
  - .env:/app/opencode/.env        # ✅ 自动同步
```

**这意味着**:
- ✅ 修改`app/*.py` → Docker容器立即看到
- ✅ 修改`static/*.js` → Docker容器立即看到
- ✅ 修改`.env` → Docker容器立即看到

**但是**:
- ❌ 新增Python文件 → **需要重启容器**
- ❌ 修改`requirements.txt` → **需要重新构建镜像**
- ❌ 修改`Dockerfile` → **需要重新构建镜像**

---

### 2. Python依赖差异

**本地环境**:
```bash
# 你可以直接pip install
pip install httpx tenacity
```

**Docker环境**:
```bash
# 需要修改requirements.txt，然后重新构建
# 修改requirements.txt
# 重新构建镜像
docker-compose build
```

---

### 3. 环境变量差异

**本地环境**:
```bash
# 在Windows PowerShell
$env:OPENCODE_DEV_MODE="true"
$env:WEB_API_URL="http://localhost:8089"
```

**Docker环境**:
```bash
# 需要修改.env文件或docker-compose.yml
# docker-compose.yml
environment:
  - OPENCODE_DEV_MODE=true
  - WEB_API_URL=http://localhost:8089
```

---

## 🔧 Solution 1的Docker部署指南

### 新增文件（3个）

```bash
app/
├─ auth.py                      # ✅ 新增（会自动同步）
├─ utils.py                     # ✅ 新增（会自动同步）
└─ subsession_registration.py   # ✅ 新增（会自动同步）
```

**同步状态**: ✅ 自动同步（通过volume挂载）

**但是**: ⚠️ **需要重启容器**，因为Python需要重新导入这些模块

---

### 修改文件（1个）

```bash
app/
└─ opencode_client.py  # ✅ 修改（会自动同步）
```

**同步状态**: ✅ 自动同步

**但是**: ⚠️ **需要重启容器**，因为代码已加载到内存

---

### 新增Python依赖

**requirements.txt需要添加**:
```txt
# 新增依赖
httpx>=0.24.0
tenacity>=8.2.0
```

**操作**: 重新构建Docker镜像

---

## 🚀 完整部署步骤

### 方式1: 快速重启（推荐用于开发）⚡

```bash
# 1. 确保所有文件已保存
# app/auth.py, app/utils.py, app/subsession_registration.py
# app/opencode_client.py (已修改)

# 2. 重启容器（保留volume）
docker-compose restart

# 3. 查看日志
docker-compose logs -f opencode

# 预期输出:
# ✅ 容器重启成功
# ✅ app/auth.py 被导入
# ✅ app/utils.py 被导入
# ✅ app/subsession_registration.py 被导入
```

**优点**: 快速（10秒）
**缺点**: 新增的Python依赖不会安装

---

### 方式2: 重新构建（完整部署）🔧

```bash
# 1. 更新requirements.txt
cat >> requirements.txt << EOF
httpx>=0.24.0
tenacity>=8.2.0
EOF

# 2. 重新构建镜像
docker-compose build --no-cache

# 3. 重启容器
docker-compose up -d

# 4. 查看日志
docker-compose logs -f opencode
```

**优点**: 完整（包含新依赖）
**缺点**: 慢（2-5分钟）

---

### 方式3: 进入容器手动安装（临时方案）🛠️

```bash
# 1. 进入容器
docker exec -it opencode-container bash

# 2. 安装新依赖
pip install httpx tenacity

# 3. 重启应用（取决于启动方式）
# 如果使用supervisor:
supervisorctl restart opencode

# 或者直接重启容器
docker-compose restart
```

**优点**: 快速测试
**缺点**: 临时方案，重启后失效

---

## 🧪 验证部署

### 1. 检查文件是否同步

```bash
# 进入容器
docker exec -it opencode-container bash

# 检查文件存在
ls -la /app/opencode/app/auth.py
ls -la /app/opencode/app/utils.py
ls -la /app/opencode/app/subsession_registration.py

# 预期: 文件都存在
```

### 2. 检查Python依赖

```bash
# 在容器内
python -c "import httpx, tenacity; print('✅ Dependencies OK')"

# 预期: ✅ Dependencies OK
```

### 3. 测试注册功能

```bash
# 在浏览器访问Docker环境
http://localhost:8089

# 提交一个使用task工具的任务
# 观察控制台日志:
docker-compose logs -f opencode | grep -E "register|child|subsession"

# 预期输出:
# ✅ "🔧 Detected 'task' tool"
# ✅ "📡 Registering child session"
# ✅ "✅ Registered child session"
```

---

## ⚠️ 常见问题

### 问题1: ModuleNotFoundError: No module named 'httpx'

**原因**: Docker容器中没有安装httpx

**解决**:
```bash
# 方案A: 重新构建镜像（推荐）
docker-compose build --no-cache
docker-compose up -d

# 方案B: 进入容器手动安装（临时）
docker exec -it opencode-container pip install httpx tenacity
docker-compose restart
```

---

### 问题2: 修改代码后没有生效

**原因**: Python已经加载了旧代码到内存

**解决**:
```bash
# 重启容器
docker-compose restart

# 或者，如果支持热重载（取决于启动方式）
# 触发文件保存（touch某个文件）
docker exec opencode-container touch /app/opencode/app/main.py
```

---

### 问题3: 环境变量没有生效

**原因**: Docker容器使用容器内的.env文件

**解决**:
```bash
# 检查.env文件是否挂载
docker exec opencode-container cat /app/opencode/.env

# 如果没有，确保.dockerignore不包含.env
# 确保.dockerignore文件内容正确
```

---

### 问题4: 404错误仍然存在

**原因**: Web后端可能没有重启，或者注册失败

**排查**:
```bash
# 1. 检查容器日志
docker-compose logs -f opencode | grep -E "error|Error|ERROR"

# 2. 检查新文件是否被导入
docker exec opencode-container python -c "from app.subsession_registration import safe_register_subsession; print('✅ OK')"

# 3. 手动测试HTTP调用
docker exec opencode-container curl -X POST http://localhost:8000/opencode/session \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Session"}'
```

---

## 📋 部署检查清单

### 部署前

- [ ] 本地测试通过（无痕浏览器）
- [ ] 新增文件已保存（auth.py, utils.py, subsession_registration.py）
- [ ] 修改文件已保存（opencode_client.py）
- [ ] requirements.txt已更新（添加httpx, tenacity）

### 部署中

- [ ] 停止容器: `docker-compose down`
- [ ] 重新构建: `docker-compose build --no-cache`
- [ ] 启动容器: `docker-compose up -d`
- [ ] 检查日志: `docker-compose logs -f opencode`

### 部署后验证

- [ ] 检查文件同步: `ls -la /app/opencode/app/auth.py`
- [ ] 检查依赖: `python -c "import httpx, tenacity"`
- [ ] 测试task工具: 提交任务，观察日志
- [ ] 验证404消失: 前端不再报404

---

## 🎯 推荐流程

### 开发阶段（本地）

```bash
# 1. 本地开发和测试
python -m app.main

# 2. 本地验证通过后
# 确保所有文件已保存
```

### 部署到Docker（生产）

```bash
# 1. 更新requirements.txt
echo "httpx>=0.24.0" >> requirements.txt
echo "tenacity>=8.2.0" >> requirements.txt

# 2. 重新构建镜像
docker-compose build --no-cache

# 3. 重启容器
docker-compose up -d

# 4. 验证部署
docker-compose logs -f opencode
```

---

## 📊 总结

| 方面            | 本地环境                     | Docker环境                   |
| --------------- | --------------------------- | --------------------------- |
| 文件同步        | N/A（直接在文件系统）        | ✅ 自动同步（volume挂载）    |
| 新增Python文件  | ✅ 立即生效                 | ⚠️ 需要重启容器             |
| Python依赖      | ✅ pip install立即生效       | ⚠️ 需要重新构建镜像         |
| 环境变量        | ✅ $env立即生效              | ⚠️ 需要.env文件或compose    |
| 代码修改        | ✅ 部分支持热重载            | ⚠️ 需要重启容器             |

---

## ✅ 快速命令

```bash
# 完整部署（推荐）
docker-compose down && \
docker-compose build --no-cache && \
docker-compose up -d && \
docker-compose logs -f opencode

# 快速重启（开发中）
docker-compose restart

# 查看日志
docker-compose logs -f opencode | grep -E "register|child"
```

---

**结论**: 本地修改**大部分会自动同步**，但需要**重启容器**才能生效。新增依赖需要**重新构建镜像**。
