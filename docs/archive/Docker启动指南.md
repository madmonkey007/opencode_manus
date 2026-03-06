# 使用 Docker 启动 OpenCode 服务器

## 前置准备

### 1. 启动 Docker Desktop

请手动启动 Docker Desktop：
- 在开始菜单中找到 "Docker Desktop"
- 或在桌面双击 "Docker Desktop" 图标
- 等待Docker图标变为绿色（表示运行中）

### 2. 检查 Docker 状态

打开新的命令提示符或PowerShell，执行：

```bash
docker ps
```

如果显示容器列表，说明Docker已正常运行。

## 启动 OpenCode 容器

### 方法1：查找并启动现有容器

```bash
# 查看所有容器（包括停止的）
docker ps -a

# 查找opencode相关容器
docker ps -a | grep opencode

# 如果找到容器，启动它
docker start <容器名或容器ID>

# 查看容器日志
docker logs -f <容器名或容器ID>
```

### 方法2：使用docker-compose（如果有）

```bash
cd D:\Manus\opencode
docker-compose up -d
```

### 方法3：运行新的容器（如果没有）

```bash
cd D:\Manus\opencode
docker build -t opencode .
docker run -d -p 8088:8088 --name opencode-server opencode
```

## 验证服务

### 1. 检查容器状态

```bash
docker ps
```

应该看到opencode容器在运行，端口映射显示 `0.0.0.0:8088->8088/tcp`

### 2. 访问服务

打开浏览器访问：http://localhost:8088

### 3. 清除浏览器缓存

- 按 `Ctrl+Shift+Delete`
- 选择"缓存的图片和文件"
- 点击"清除数据"
- 然后按 `Ctrl+F5` 强制刷新

### 4. 测试功能

1. ✓ 检查页面正常加载（无JavaScript错误）
2. 创建一个新任务
3. 等待任务完成
4. 点击左侧历史记录中的该任务
5. 再次点击同一个任务
6. ✓ 检查控制台是否显示"已经是当前激活session，跳过"
7. ✓ 确认没有触发重复的查询请求

## 容器管理命令

```bash
# 查看日志
docker logs -f opencode-server

# 停止容器
docker stop opencode-server

# 重启容器
docker restart opencode-server

# 进入容器Shell（用于调试）
docker exec -it opencode-server sh
```

## 故障排除

### 端口8088被占用

如果端口8088已被占用：
```bash
# Windows查找占用进程
netstat -ano | findstr :8088

# 或使用其他端口
docker run -d -p 8089:8088 --name opencode-server opencode
```

### Docker Desktop无法启动

1. 检查Docker Desktop是否正确安装
2. 检查Windows虚拟化是否启用
3. 检查WSL2是否安装
4. 重启Docker Desktop

---

**修复完成时间**: 2026-02-12 00:05
**方案**: Docker容器部署
**优势**:
- ✓ 环境隔离，避免本地配置问题
- ✓ 已包含所有依赖
- ✓ 一键启动，停止方便
- ✓ 代码修复已完成，Docker环境可直接使用
