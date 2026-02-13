# OpenCode 测试指南

## 🚀 快速开始

### Windows 用户（最简单）

**双击运行**:
```
D:\manus\opencode\tests\quick_test.bat
```

这个脚本会：
1. 自动停止旧服务
2. 启动新服务
3. 运行快速验证测试

---

## 📁 测试文件

| 文件 | 说明 | 运行时间 |
|------|------|----------|
| `quick_test.bat` | 一键测试（推荐） | ~20 秒 |
| `start_and_test.bat` | 完整测试流程 | ~1 分钟 |
| `server_manager.py` | Python 服务器管理器 | 可配置 |
| `quick_verify.py` | 快速验证脚本 | ~10 秒 |
| `automated_test.py` | 完整自动化测试 | ~1 分钟 |

---

## 🛠️ 使用方法

### 方法 1: 批处理脚本（推荐）

#### 快速测试
```bash
双击: quick_test.bat
```

#### 完整测试
```bash
双击: start_and_test.bat
```

### 方法 2: Python 服务器管理器

```bash
# 快速测试
python tests\server_manager.py

# 完整测试
python tests\server_manager.py --test full

# 测试后打开浏览器
python tests\server_manager.py --test quick --browser
```

### 方法 3: 手动测试

```bash
# 1. 启动服务
python -m app.main

# 2. 运行测试（新终端）
python tests\quick_verify.py
```

---

## 📋 测试内容

### 快速验证（5 项）

1. ✅ 服务可用性检查
2. ✅ 创建会话
3. ✅ 发送消息
4. ✅ 获取消息历史
5. ✅ 列出会话

### 完整测试（10 项）

- 基础功能（健康检查、API 信息）
- 会话管理（创建、获取、列表、删除）
- 消息功能（发送、获取历史）
- 事件流（SSE）
- 高级功能（多轮对话）

---

## ✅ 成功示例

```
============================================================
  OpenCode Web Interface 快速验证
============================================================

[INFO] 服务地址: http://localhost:8088

============================================================
  1. 测试服务可用性
============================================================

[OK] 服务正常运行
[INFO] 状态: healthy

...

============================================================
  测试结果
============================================================

总计: 5
[OK] 通过: 5
通过率: 100%

[SUCCESS] All tests passed!
```

---

## ❌ 失败处理

### 错误 1: 服务启动失败

```
[ERROR] 服务启动失败
```

**解决方法**:
1. 手动停止所有 Python 进程: `taskkill /F /IM python.exe`
2. 重新运行测试脚本
3. 如果仍然失败，检查端口 8088 是否被占用

### 错误 2: 测试连接失败

```
[FAIL] 无法连接到服务
```

**解决方法**:
1. 确认服务正在运行
2. 检查防火墙设置
3. 尝试访问: http://localhost:8088

### 错误 3: 测试失败

```
[FAIL] 创建会话
HTTP 500: Internal Server Error
```

**解决方法**:
1. 查看服务器日志
2. 检查数据库/存储是否正常
3. 重启服务后重试

---

## 🔍 手动测试

### 浏览器测试

**访问地址**:
```
主页面: http://localhost:8088
新 API:  http://localhost:8088?use_new_api=true
旧 API:  http://localhost:8088?use_new_api=false
```

**浏览器控制台测试**:
```javascript
// 1. 检查配置
window.opencodeConfig.getCurrentConfig()

// 2. 测试创建会话
fetch('/opencode/session?title=测试', {method: 'POST'})
  .then(r => r.json())
  .then(d => console.log('成功:', d))
  .catch(e => console.error('失败:', e))

// 3. 动态切换 API
window.opencodeConfig.setUseNewAPI(true)
```

---

## 📊 测试报告

测试完成后，你可以查看：

1. **控制台输出** - 测试结果摘要
2. **浏览器日志** - F12 → Console
3. **网络请求** - F12 → Network
4. **服务器日志** - server.log（如使用 server_manager.py）

---

## 🛑 停止服务

测试完成后，手动停止服务：

```bash
taskkill /F /IM python.exe
```

或使用 Ctrl+C 停止服务器进程。

---

## 📝 常见问题

### Q: 测试显示端口被占用

**A**: 运行 `netstat -ano | findstr :8088` 查看占用进程，然后手动终止。

### Q: 测试超时

**A**: 可能是服务启动慢，增加等待时间（修改脚本中的 timeout）。

### Q: 测试通过但浏览器打不开

**A**: 手动访问 http://localhost:8088

### Q: 测试通过但功能不正常

**A**: 清除浏览器缓存后重试。

---

## 🎯 下一步

测试通过后：

1. **前端测试**: 访问 http://localhost:8088?use_new_api=true
2. **功能验证**: 测试多轮对话、文件预览、历史回溯
3. **性能测试**: 使用完整测试脚本
4. **集成测试**: 测试与 OpenCode CLI 的集成

---

**最后更新**: 2026-02-10
**版本**: 1.0
