# 🐳 Docker部署完整指南（Solution 1）

## 当前状态

✅ Docker Desktop已运行
✅ opencode容器正在运行（container ID: 2a1f39bd4d87）
⚠️ 命令行工具连接Docker API失败（需要使用Docker Desktop UI）

---

## 🎯 部署步骤（通过Docker Desktop UI）

### 第1步：停止当前容器

**在Docker Desktop中**：
1. 打开Docker Desktop
2. 点击左侧"Containers"
3. 找到"opencode"容器
4. 点击"Stop"按钮

---

### 第2步：重新构建镜像

**方式A：使用PowerShell（推荐）**

```powershell
# 进入项目目录
cd D:\manus\opencode

# 重新构建镜像
docker-compose build --no-cache
```

**如果PowerShell也报错，使用方式B** ↓

**方式B：使用Docker Desktop UI**

1. 在Docker Desktop中，点击左侧"Images"
2. 找到"opencode:latest"镜像
3. 点击"..." → "Build Image"
4. 输入：
   - Image name: `opencode`
   - Tag: `latest`
   - Build context: `D:\manus\opencode`
   - Dockerfile path: `D:\manus\opencode\Dockerfile`

**构建时间**: 2-5分钟

---

### 第3步：启动容器

**使用PowerShell**：

```powershell
cd D:\manus\opencode
docker-compose up -d
```

**或使用Docker Desktop UI**：

1. 在Docker Desktop中，点击左侧"Containers"
2. 找到"opencode"容器
3. 点击"Run"按钮

---

### 第4步：验证部署

#### 4.1 检查日志

**在Docker Desktop中**：
1. 点击"opencode"容器
2. 点击"Logs"标签
3. 查找关键日志：
   ```
   ✅ Importing app.auth
   ✅ Importing app.utils
   ✅ Importing app.subspace_registration
   ✅ Starting OpenCode API server
   ```

#### 4.2 进入容器验证（可选）

**在PowerShell中**：

```powershell
# 进入容器
docker exec -it opencode-container bash

# 检查文件
ls -la /app/opencode/app/auth.py

# 检查依赖
python -c "import httpx, tenacity; print('✅ OK')"

# 退出容器
exit
```

---

## 🧪 功能测试

### 测试步骤

1. **打开浏览器访问**：
   ```
   http://localhost:8089
   ```

2. **提交一个使用task工具的任务**：
   ```
   帮我写一个网页版闹钟，位于画面居中，简单精致
   ```

3. **观察Docker Desktop日志**：
   - 点击"opencode"容器 → "Logs"标签
   - 查找：
     ```
     ✅ "🔧 Detected 'task' tool"
     ✅ "📡 Registering child session"
     ✅ "✅ Registered child session"
     ```

4. **预期结果**：
   - ✅ 不再出现404错误
   - ✅ 右侧面板显示子代理的工具调用（read, write等）
   - ✅ 实时显示子session的执行过程

---

## ⚠️ 常见问题

### 问题1：PowerShell连接Docker API失败

**现象**：
```
error during connect: open //./pipe/dockerDesktopLinuxEngine
```

**原因**：Docker Desktop API管道未正确连接

**解决**：
- 使用Docker Desktop UI操作
- 或重启Docker Desktop：
  1. 退出Docker Desktop
  2. 重新打开
  3. 等待"Docker Desktop is running"

---

### 问题2：构建时提示找不到requirements.txt

**解决**：
1. 确认在正确的目录：`D:\manus\opencode`
2. 确认requirements.txt文件存在：
   ```powershell
   ls D:\manus\opencode\requirements.txt
   ```

---

### 问题3：容器启动后立即退出

**排查**：
1. 查看容器日志（Docker Desktop → Logs）
2. 查找错误信息
3. 常见原因：
   - Python依赖安装失败
   - 端口冲突（8089已被占用）
   - 环境变量配置错误

---

## 📋 快速参考

### Docker Desktop常用操作

| 操作          | UI位置                          | PowerShell命令               |
| ------------- | ------------------------------- | ---------------------------- |
| 查看容器      | Containers → opencode           | `docker ps`                  |
| 查看日志      | Containers → opencode → Logs    | `docker logs opencode-container` |
| 重启容器      | Containers → opencode → Restart | `docker-compose restart`     |
| 停止容器      | Containers → opencode → Stop    | `docker-compose stop`        |
| 进入容器      | Containers → opencode → CLI     | `docker exec -it opencode-container bash` |

---

## 📊 部署状态总结

| 项目          | 状态              |
| ------------- | ----------------- |
| 新增文件      | ✅ 已创建（3个）  |
| 修改文件      | ✅ 已修改（1个）  |
| Python依赖    | ✅ 已更新         |
| Docker Desktop | ✅ 运行中         |
| 容器状态      | ⏳ 需要重启       |
| 构建状态      | ⏳ 需要重新构建   |

---

## ✅ 完整部署命令（如果PowerShell可用）

```powershell
# 完整的一键部署脚本
cd D:\manus\opencode
docker-compose down
docker-compose build --no-cache
docker-compose up -d
docker-compose logs -f opencode
```

**按Ctrl+C退出日志查看**

---

## 🎯 下一步

1. **停止当前容器**（Docker Desktop UI）
2. **重新构建镜像**（Docker Desktop UI或PowerShell）
3. **启动容器**（Docker Desktop UI）
4. **查看日志**（Docker Desktop → Logs）
5. **测试功能**（浏览器提交任务）

一切准备就绪，等待你操作Docker Desktop！🚀
