# OpenCode 架构迁移 - 备份与回滚计划

**日期**: 2026-02-10
**目的**: 确保在迁移到新架构时可以安全回滚到旧方案

---

## 📦 备份策略

### 1. 自动备份脚本

创建自动备份脚本 `scripts/backup.sh`：

```bash
#!/bin/bash
# OpenCode 备份脚本
# 用法: ./scripts/backup.sh

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
PROJECT_DIR="/d/manus/opencode"

echo "📦 开始备份 OpenCode 项目..."
echo "备份位置: $BACKUP_DIR"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份关键文件和目录
echo "备份 app/ 目录..."
cp -r "$PROJECT_DIR/app" "$BACKUP_DIR/"

echo "备份 static/ 目录..."
cp -r "$PROJECT_DIR/static" "$BACKUP_DIR/"

echo "备份 docs/ 目录..."
cp -r "$PROJECT_DIR/docs" "$BACKUP_DIR/" 2>/dev/null || true

echo "备份配置文件..."
cp "$PROJECT_DIR/*.json" "$BACKUP_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/*.md" "$BACKUP_DIR/" 2>/dev/null || true

# 创建备份信息文件
cat > "$BACKUP_DIR/backup_info.txt" << EOF
备份时间: $(date)
Git commit: $(cd "$PROJECT_DIR" && git rev-parse HEAD 2>/dev/null || echo "N/A")
Git branch: $(cd "$PROJECT_DIR" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "N/A")
备份文件列表:
$(cd "$BACKUP_DIR" && find . -type f | sort)
EOF

echo "✅ 备份完成!"
echo "备份位置: $BACKUP_DIR"
echo "恢复命令: ./scripts/restore.sh $BACKUP_DIR"
```

### 2. 手动备份清单

在每次重大修改前，确认备份以下内容：

- [ ] `app/main.py` - 当前工作的后端代码
- [ ] `app/history_service.py` - 历史追踪服务
- [ ] `static/opencode.js` - 当前前端代码
- [ ] `static/enhanced-task-panel.js` - 任务面板代码
- [ ] `static/index.html` - 主页面
- [ ] `workspace/` - 工作区数据（可选）
- [ ] 整个项目的 Git 仓库

### 3. 备份验证

```bash
# 验证备份完整性
./scripts/verify_backup.sh backups/20260210_120000

# 应该输出：
# ✅ app/main.py exists
# ✅ static/opencode.js exists
# ✅ All critical files backed up
```

---

## 🔄 回滚方案

### 方案 A: 快速回滚（文件级）

**适用场景**: 发现新架构有重大问题，需要立即切换回旧版本

```bash
# 1. 停止服务
# uvicorn 停止（如果正在运行）

# 2. 备份当前状态（保留新代码以防万一）
./scripts/backup.sh

# 3. 恢复旧版本
cp backups/20260210_120000/app/main.py app/
cp backups/20260210_120000/static/opencode.js static/
cp backups/20260210_120000/static/enhanced-task-panel.js static/

# 4. 重启服务
uvicorn app.main:app --host 0.0.0.0 --port 8088

# 5. 验证
curl http://localhost:8088/
```

### 方案 B: Git 回滚（版本级）

**适用场景**: 已经提交到 Git，可以通过 Git 历史回滚

```bash
# 1. 查看提交历史
git log --oneline -10

# 2. 回滚到指定提交（保留新代码在 backup 分支）
git branch backup-architecture-migration
git checkout <last-working-commit>

# 3. 重新部署
# ... 重启服务

# 4. 如果需要恢复到新架构
git checkout backup-architecture-migration
```

### 方案 C: 渐进式回滚（模块级）

**适用场景**: 部分功能有问题，只回滚特定模块

```bash
# 例如：只回滚前端，保留后端新架构
cp backups/20260210_120000/static/opencode.js static/
cp backups/20260210_120000/static/enhanced-task-panel.js static/

# 或者：只回滚后端，保留前端新代码
cp backups/20260210_120000/app/main.py app/
```

---

## 🛡️ 安全措施

### 1. 版本标记

在每个阶段开始前，打上 Git 标签：

```bash
# 阶段0: 开始迁移前
git tag -a phase0-start -m "架构迁移开始前"

# 阶段1: 数据模型完成
git tag -a phase1-models-complete -m "数据模型和存储完成"

# 阶段2: API端点完成
git tag -a phase2-api-complete -m "新API端点实现完成"
```

### 2. 并行运行

新、旧 API 可以同时运行，互不影响：

```python
# app/main.py

# 旧版 API（保留）
@app.get("/opencode/run_sse")
async def run_sse_legacy(prompt: str, sid: str = None):
    """旧版 CLI API - 保留用于回滚"""
    # ... 现有实现

# 新版 API（新增）
@app.post("/opencode/session")
async def create_session():
    """新版 API"""
    # ... 新实现
```

### 3. 功能开关

通过环境变量控制使用哪个版本：

```python
# app/main.py
import os

USE_NEW_ARCHITECTURE = os.getenv("USE_NEW_ARCHITECTURE", "false").lower() == "true"

@app.get("/opencode/run_sse")
async def run_sse(prompt: str, sid: str = None):
    if USE_NEW_ARCHITECTURE:
        # 调用新架构
        return await run_sse_new(prompt, sid)
    else:
        # 使用旧实现
        return await run_sse_legacy(prompt, sid)
```

启动时切换：

```bash
# 使用旧架构（默认）
uvicorn app.main:app --host 0.0.0.0 --port 8088

# 使用新架构
USE_NEW_ARCHITECTURE=true uvicorn app.main:app --host 0.0.0.0 --port 8088
```

---

## 📋 迁移检查清单

### 阶段 1: 数据模型（当前阶段）

- [x] 创建 `app/models.py`
- [x] 创建 `app/managers.py`
- [x] 创建单元测试
- [ ] **运行测试验证** ⚠️ 进行中
- [ ] Git commit: `feat: add session and message models`

### 阶段 2: API 端点

- [ ] 创建 `app/api.py`
- [ ] 保留旧 `app/main.py`
- [ ] 集成 SessionManager
- [ ] 测试新端点
- [ ] Git commit: `feat: add new API endpoints`

### 阶段 3: OpenCode Client

- [ ] 创建 `app/opencode_client.py`
- [ ] 实现 CLI 事件转换
- [ ] 集成 history_service
- [ ] 测试执行
- [ ] Git commit: `feat: add OpenCode CLI client`

### 阶段 4: 前端重构

- [ ] 创建 `static/api-client.js`
- [ ] 修改 `static/opencode.js`
- [ ] 修改 `static/enhanced-task-panel.js`
- [ ] 测试新前端
- [ ] Git commit: `feat: refactor frontend for new API`

### 阶段 5: 预览功能

- [ ] 实现打字机效果
- [ ] 创建预览面板
- [ ] 测试 write/edit 操作
- [ ] Git commit: `feat: add write preview feature`

### 阶段 6: 历史回溯

- [ ] 实现文件快照存储
- [ ] 实现 timeline 组件
- [ ] 测试回溯功能
- [ ] Git commit: `feat: add history rollback feature`

---

## 🚨 应急预案

### 问题 1: 测试失败

**症状**: 单元测试不通过

**解决方案**:
1. 检查导入路径（可能是相对导入问题）
2. 检查 Pydantic 版本兼容性
3. 查看详细错误日志
4. 如果无法快速修复，标记为 TODO，继续下一步

### 问题 2: 导入错误

**症状**: `ImportError: attempted relative import with no known parent package`

**解决方案**:
1. 确保 `app/__init__.py` 存在
2. 使用 try-except 处理相对/绝对导入
3. 或使用绝对导入：`from app.models import ...`

### 问题 3: 服务无法启动

**症状**: uvicorn 启动失败

**解决方案**:
1. 检查端口占用：`lsof -i :8088`
2. 检查依赖：`pip install -r requirements.txt`
3. 查看详细错误：`uvicorn app.main:app --log-level debug`
4. 如果无法修复，立即回滚到旧版本

### 问题 4: 前端无法连接

**症状**: 浏览器控制台显示 404 或连接错误

**解决方案**:
1. 检查 API 端点路径
2. 检查 CORS 配置
3. 查看浏览器 Network 标签
4. 临时切换回旧 API

---

## 📞 回滚决策树

```
发现问题
  │
  ├─ 是否影响核心功能？
  │   ├─ 是 → 立即回滚（方案 A）
  │   └─ 否 → 继续评估
  │
  ├─ 是否能在 30 分钟内修复？
  │   ├─ 是 → 尝试修复
  │   └─ 否 → 回滚（方案 A）
  │
  ├─ 是否是新功能的 Bug？
  │   ├─ 是 → 标记为 TODO，禁用该功能
  │   └─ 否 → 回滚（方案 A）
  │
  └─ 是否有可用的旧版本？
      ├─ 是 → 回滚（方案 A/B/C）
      └─ 否 → 紧急修复（联系技术支持）
```

---

## 📝 回滚后操作

回滚完成后，记录以下信息：

1. **回滚原因**: 为什么需要回滚？
2. **回滚时间**: 何时回滚？
3. **回滚方案**: 使用了哪个方案（A/B/C）？
4. **问题记录**: 什么导致了问题？
5. **后续计划**: 如何解决该问题？

**模板**：

```markdown
## 回滚记录 - YYYY-MM-DD

**回滚原因**:
**回滚时间**:
**回滚方案**: 方案 A（文件级）
**问题详情**:
**后续行动**:
- [ ] 修复问题
- [ ] 重新测试
- [ ] 再次尝试迁移
```

---

## ✅ 验证清单

回滚后，验证以下内容：

- [ ] 服务正常启动
- [ ] 旧 API 端点可以访问
- [ ] 前端可以正常连接
- [ ] 可以创建任务
- [ ] 可以查看结果
- [ ] 没有错误日志
- [ ] 性能正常

---

## 📚 参考资料

- **架构设计**: `docs/api-migration-plan.md`
- **实施计划**: `docs/api-migration-plan.md#实施步骤`
- **测试文件**: `tests/test_managers.py`
- **备份目录**: `backups/`

---

**最后更新**: 2026-02-10
**状态**: 阶段 1 进行中
**风险等级**: 中等（有完整备份和回滚方案）
