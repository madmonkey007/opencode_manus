# Preview任务超时配置说明

## 配置项

**环境变量**: `PREVIEW_TASK_TIMEOUT`
**默认值**: `300`（5分钟）
**单位**: 秒
**特殊值**: `0` 表示不限制等待时间

## 配置方式

### 方法1：通过 `.env` 文件配置（推荐）

在项目根目录的 `.env` 文件中添加：

```bash
# Preview任务超时时间（秒）
# 0 = 不限制，建议用于复杂任务
# 60 = 1分钟，适合简单任务
# 300 = 5分钟（默认），适合大多数任务
# 600 = 10分钟，适合大型项目
# 0 = 不限制，适合可能很长的复杂任务
PREVIEW_TASK_TIMEOUT=300
```

### 方法2：通过系统环境变量配置

**Linux/Mac**:
```bash
export PREVIEW_TASK_TIMEOUT=600
python -m app.main
```

**Windows (PowerShell)**:
```powershell
$env:PREVIEW_TASK_TIMEOUT="600"
python -m app.main
```

**Windows (CMD)**:
```cmd
set PREVIEW_TASK_TIMEOUT=600
python -m app.main
```

### 方法3：在代码中配置（不推荐）

修改 `app/opencode_client.py` 第147行：
```python
self._preview_task_timeout = 600  # 10分钟
```

## 配置建议

### 场景1：简单任务（快速原型）
```bash
PREVIEW_TASK_TIMEOUT=60  # 1分钟
```
适合：单文件HTML、简单脚本、小工具

### 场景2：常规任务（默认配置）
```bash
PREVIEW_TASK_TIMEOUT=300  # 5分钟
```
适合：React/Vue项目、中型应用、多文件项目

### 场景3：复杂任务（大型项目）
```bash
PREVIEW_TASK_TIMEOUT=600  # 10分钟
```
适合：完整的应用系统、包含多个模块的项目

### 场景4：不确定任务大小（最灵活）
```bash
PREVIEW_TASK_TIMEOUT=0  # 不限制
```
适合：
- 任务复杂度不确定
- 网络速度可能较慢
- 文件可能非常大
- 不希望任务因为超时而中断

**注意**: 设置为0时，任务会一直等待，直到所有preview完成。如果某个任务真的卡住了，可能需要手动重启服务。

## 行为说明

### 有超时限制（PREVIEW_TASK_TIMEOUT > 0）

```
Session idle → 等待preview任务 → 超时后强制继续
                   ↓
            最多等待N秒
                   ↓
            超时则：
            - 记录警告日志
            - 取消未完成的任务
            - 继续关闭SSE连接
```

**优点**:
- 防止任务永久卡住
- 用户体验可控
- 资源及时释放

**缺点**:
- 复杂任务可能被中断
- 需要根据实际情况调整超时时间

### 无超时限制（PREVIEW_TASK_TIMEOUT = 0）

```
Session idle → 等待preview任务 → 全部完成后继续
                   ↓
            无限等待（直到完成）
                   ↓
            所有任务完成后：
            - 记录完成时间
            - 关闭SSE连接
```

**优点**:
- 所有preview事件都能正常发送
- 不会因为超时而中断
- 最灵活

**缺点**:
- 如果任务真的卡住，会永久等待
- 需要手动重启服务才能恢复

## 日志示例

### 有超时限制的情况

**正常完成**:
```
[BRIDGE] Session idle detected, waiting for 3 preview task(s) to complete (timeout: 300s)...
[BRIDGE] All 3 preview tasks completed for session ses_abc123 in 2.3s
```

**超时情况**:
```
[BRIDGE] Session idle detected, waiting for 5 preview task(s) to complete (timeout: 60s)...
[BRIDGE] ⚠️ Preview tasks timed out after 60.0s (limit: 60s) for session ses_abc123.
Consider increasing PREVIEW_TASK_TIMEOUT if this happens frequently.
Continuing with 5 pending task(s).
[BRIDGE] Cancelled 5/5 incomplete preview tasks
```

### 无超时限制的情况

```
[BRIDGE] Session idle detected, waiting for 2 preview task(s) to complete (timeout: unlimited)...
[BRIDGE] All 2 preview tasks completed for session ses_xyz789 in 15.7s
```

## 故障排查

### 问题1: 经常出现超时警告

**症状**:
```
[BRIDGE] ⚠️ Preview tasks timed out after 60.0s
```

**解决方案**:
1. 增加超时时间：`PREVIEW_TASK_TIMEOUT=600`
2. 或设置为无限制：`PREVIEW_TASK_TIMEOUT=0`

### 问题2: 任务等待时间过长

**症状**: 任务完成后很久才显示完成

**原因**: Preview任务可能在处理大文件

**解决方案**:
- 检查日志确认是否有preview任务
- 如果是正常的大文件处理，增加超时时间
- 如果任务卡住，重启服务

### 问题3: 某个任务永久卡住

**症状**:
```
[BRIDGE] Session idle detected, waiting for 1 preview task(s)...
（一直等待，没有任何输出）
```

**解决方案**:
1. 设置合理的超时时间（不要用0）
2. 重启服务
3. 检查preview任务代码是否有死循环

## 性能影响

### 预览任务耗时估算

根据文件大小和打字机效果：

| 文件字符数 | 预计耗时 | 说明 |
|----------|---------|------|
| 1,000 | ~1秒 | 20块 × 50ms |
| 5,000 | ~5秒 | 100块 × 50ms |
| 10,000 | ~10秒 | 200块 × 50ms |
| 50,000 | ~50秒 | 1000块 × 50ms |
| 100,000 | ~100秒 | 2000块 × 50ms |

**注意**: 实际耗时还受网络延迟、服务器性能影响

### 配置建议

- **小项目（<10个文件）**: 60秒足够
- **中项目（10-50个文件）**: 300秒（默认）合适
- **大项目（>50个文件）**: 600秒或更久
- **不确定**: 使用0（无限制）

## 相关文件

- `app/opencode_client.py` - 实现代码
- `.env` - 配置文件
- `PREVIEW_FIX_SUMMARY.md` - 修复摘要
- `PREVIEW_DIAGNOSIS.md` - 诊断报告

## 更新日志

**2026-03-24**:
- 从硬编码30秒改为可配置的超时时间
- 默认超时从30秒增加到300秒（5分钟）
- 支持设置为0表示无超时限制
- 添加详细的进度和统计日志
- 改进错误处理和任务取消逻辑
