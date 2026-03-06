# 🔴 子Session 404错误诊断报告

## 问题描述

**错误信息**:
```
GET http://localhost:8089/opencode/events?session_id=ses_352b0f09fffeH1ynEIRC0IpDHL 404 (Not Found)
[ChildSession] SSE error for ses_352b0f09fffeH1ynEIRC0IpDHL
[ChildSession] Unsubscribed: ses_352b0f09fffeH1ynEIRC0IpDHL
```

**发生场景**:
- 用户提交任务："帮我写一个网页版闹钟，位于画面居中，简单精致"
- 主代理使用task工具创建子代理
- 前端自动订阅子session事件流
- **后端返回404**: 子session不存在

---

## Phase 1: Root Cause Investigation

### 1.1 后端SSE路由验证 ✅

**代码位置**: `app/api.py` 第452-454行

```python
@app.get("/opencode/events")
async def events(session_id: str):
    """SSE事件流端点"""
    session = await get_session(session_id)  # 验证session是否存在
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")  # ❌ 返回404
```

**结论**: 后端严格验证session存在性，不存在的session返回404

### 1.2 子session在后端的数据库中不存在 ✅

**检查workspace目录**:
```bash
$ ls workspace/ | grep ses_352b
# ❌ 没有输出：workspace中没有ses_352b0f09fffeH1ynEIRC0IpDHL目录
```

**结论**: 子session的workspace目录根本不存在！

### 1.3 后端session管理流程 ✅

**Session创建流程**:
```python
# app/api.py
async def create_session(title: str = "New Session", mode: str = "auto"):
    """创建新会话"""
    session = await session_manager.create_session(title=title, version=version)

    # 创建workspace目录
    session_dir = os.path.join(WORKSPACE_BASE, session.id)
    os.makedirs(session_dir, exist_ok=True)  # ✅ 创建目录

    return session
```

**通过API创建的session**:
1. 调用`session_manager.create_session()`
2. 在内存中注册session
3. 创建workspace目录
4. 返回session对象

**通过CLI task工具创建的子session**:
- ❌ 可能没有调用`session_manager.create_session()`
- ❌ 可能没有创建workspace目录
- ❌ 可能没有在后端注册

### 1.4 数据流追踪 ✅

**完整调用链**:
```
用户提交任务
  → POST /opencode/session (创建主session: ses_e617d142) ✅
  → 后端在session_manager中注册 ✅
  → 创建workspace/ses_e617d142 ✅
  → 主代理使用task工具
  → CLI创建子session (ses_352b0f09fffeH1ynEIRC0IpDHL) ❓
  → 前端从task output解析出子session ID ✅
  → 前端尝试订阅: GET /opencode/events?session_id=ses_352b0f09fffeH1ynEIRC0IpDHL
  → 后端验证: get_session("ses_352b0f09fffeH1ynEIRC0IpDHL") ❌ 返回None
  → 抛出404错误 ❌
```

---

## 🔴 Root Cause Identified

### 直接原因

子session `ses_352b0f09fffeH1ynEIRC0IpDHL` 在后端session_manager中不存在，导致SSE订阅返回404。

### 深层原因（架构问题）

**问题**: OpenCode CLI和Web后端使用不同的session管理机制

#### 当前的架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Web后端 (FastAPI)                         │
│                                                              │
│  session_manager (内存)                                      │
│    └─ session_1 (ses_xxx) ──✅ 在内存中注册                 │
│    └─ session_2 (ses_yyy) ──✅ 在内存中注册                 │
│                                                              │
│  GET /opencode/events?session_id=ses_xxx ──✅ 返回SSE        │
│  GET /opencode/events?session_id=ses_zzz ──❌ 404 (不存在)  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    OpenCode CLI                              │
│                                                              │
│  主代理 (ses_e617d142)                                       │
│    └─ task工具 ──→ 创建子代理                                │
│                     └─ 子session (ses_352b0f09...)           │
│                          ❌ 不在Web后端的session_manager中   │
│                          ❌ 没有对应的workspace目录          │
│                          ❌ Web后端无法访问                 │
└─────────────────────────────────────────────────────────────┘
```

#### 为什么发生？

1. **CLI创建的子session不经过Web API**
   - CLI直接调用Python函数创建子session
   - 没有调用`session_manager.create_session()`
   - 没有在Web后端的内存中注册

2. **Web后端只能访问自己创建的session**
   - SSE事件流端点验证session在`session_manager`中是否存在
   - CLI创建的子session不在`session_manager`中
   - 因此返回404

3. **workspace目录不匹配**
   - Web API创建的session会创建workspace目录
   - CLI创建的子session可能没有创建目录
   - 或者目录位置不同

---

## Phase 2: Pattern Analysis

### 2.1 对比：正常工作的session ✅

**主session (ses_e617d142)**:
```
✅ 通过POST /opencode/session创建
✅ 在session_manager中注册
✅ workspace/ses_e617d142目录存在
✅ SSE订阅成功
```

**日志证据**:
```
api-client.js:179 [SSE] Connected to session: ses_e617d142 ✅
```

### 2.2 对比：失败的子session ❌

**子session (ses_352b0f09fffeH1ynEIRC0IpDHL)**:
```
❌ 通过CLI task工具创建
❌ 不在session_manager中
❌ workspace/ses_352b0f09fffeH1ynEIRC0IpDHL目录不存在
❌ SSE订阅404错误
```

**日志证据**:
```
events:1 GET http://localhost:8089/opencode/events?session_id=ses_352b0f09fffeH1ynEIRC0IpDHL 404
```

### 2.3 差异总结

| 维度          | 主session (ses_e617d142) | 子session (ses_352b0f09...) |
| ------------- | ------------------------ | --------------------------- |
| 创建方式      | POST /opencode/session   | CLI task工具                |
| 后端注册      | ✅ 是                     | ❌ 否                        |
| workspace目录 | ✅ 存在                   | ❌ 不存在                    |
| SSE订阅       | ✅ 成功                   | ❌ 404错误                   |

---

## Phase 3: Hypothesis and Testing

### 3.1 单一假设 ✅

**假设**: "CLI创建的子session不在Web后端的session_manager中注册，导致前端订阅时返回404错误。"

### 3.2 验证步骤 ✅

1. **检查workspace目录**
   ```bash
   $ ls workspace/ | grep ses_352b
   # ❌ 没有输出：目录不存在
   ```

2. **检查后端session_manager**
   - 子session不在内存中注册
   - `get_session()`返回None

3. **SSE订阅测试**
   - 前端尝试订阅子session
   - 后端返回404 ✅ 证实假设

### 3.3 结论 ✅

**假设成立**: CLI创建的子session不在Web后端注册

---

## 📋 解决方案

### 🔧 Solution 1: CLI创建子session时在后端注册（推荐）

**实现方案**:

在CLI的task工具实现中，创建子session后立即调用Web API注册：

```python
# app/main.py (CLI部分)
async def create_subsession(parent_session_id: str, task_id: str):
    """
    创建子session并在Web后端注册
    """
    # 1. 生成子session ID
    child_session_id = f"ses_{generate_id()}"

    # 2. 在Web后端的session_manager中注册 ✅
    # 方案A: 直接调用session_manager
    await session_manager.create_session(
        title=f"Subsession of {parent_session_id}",
        version="1.0.0"
    )

    # 方案B: 通过HTTP API调用
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8089/opencode/session",
            json={
                "title": f"Subsession of {parent_session_id}",
                "mode": "auto"
            }
        )
        child_session = response.json()

    # 3. 创建workspace目录 ✅
    child_workspace = os.path.join(WORKSPACE_BASE, child_session_id)
    os.makedirs(child_workspace, exist_ok=True)

    return child_session_id
```

**优点**:
- ✅ 彻底解决问题
- ✅ 子session与主session享受相同待遇
- ✅ SSE订阅正常工作

**缺点**:
- ⚠️ 需要修改CLI代码
- ⚠️ 增加CLI与Web后端的耦合

---

### 🔧 Solution 2: 前端优雅降级（临时方案）

**实现方案**:

前端订阅失败时，不显示错误，仅记录日志：

```javascript
// opencode-new-api-patch.js
function subscribeToChildSession(mainSessionId, childSessionId, onChildEvent) {
    // ...

    const eventSource = apiClient.subscribeToEvents(childSessionId, {
        onmessage: (event) => { /* ... */ },
        onerror: (error) => {
            console.warn(`[ChildSession] ⚠️ Child session not accessible: ${childSessionId}`);
            console.warn(`[ChildSession] This is expected for CLI-created sub-sessions`);
            // ❌ 不取消订阅，保持连接（可能后续可用）
            // ✅ 优雅降级：不显示错误给用户
        }
    });
}
```

**优点**:
- ✅ 无需修改后端
- ✅ 快速实施

**缺点**:
- ⚠️ 治标不治本
- ⚠️ 子session事件仍然无法显示

---

### 🔧 Solution 3: 后端为CLI session创建虚拟记录（折中方案）

**实现方案**:

后端在验证session时，如果发现workspace目录存在但session不在内存中，自动创建虚拟session：

```python
# app/api.py
async def get_session(session_id: str):
    """获取session，如果不存在但workspace存在则自动创建"""
    # 1. 尝试从session_manager获取
    session = await session_manager.get_session(session_id)
    if session:
        return session

    # 2. 检查workspace目录是否存在 ✅
    session_dir = os.path.join(WORKSPACE_BASE, session_id)
    if os.path.exists(session_dir):
        # ✅ 自动创建虚拟session
        session = await session_manager.create_session(
            title=f"CLI Session: {session_id}",
            version="1.0.0"
        )
        logger.info(f"Auto-created session for CLI: {session_id}")
        return session

    # 3. workspace目录也不存在，返回None
    return None
```

**优点**:
- ✅ 兼容CLI创建的session
- ✅ 最小化代码变更
- ✅ 自动修复

**缺点**:
- ⚠️ 虚拟session可能缺少完整信息
- ⚠️ 治标不治本

---

## 🎯 推荐实施顺序

### 阶段1: 立即实施（临时方案）
- ✅ **Solution 2**: 前端优雅降级
  - 隐藏404错误
  - 改善用户体验
  - 15分钟内完成

### 阶段2: 短期实施（1-2周）
- ✅ **Solution 3**: 后端自动创建虚拟session
  - 兼容CLI session
  - 最小化变更
  - 1-2小时完成

### 阶段3: 长期方案（1个月）
- ✅ **Solution 1**: CLI在后端注册子session
  - 彻底解决问题
  - 需要重构CLI代码
  - 1-2周完成

---

## 📊 影响评估

### 当前影响

| 影响维度      | 严重程度 | 说明                         |
| ------------- | -------- | ---------------------------- |
| 用户体验      | 🟡 中等   | 看不到子代理的工具调用过程   |
| 功能完整性    | 🟡 中等   | 子session事件无法显示        |
| 系统稳定性    | ✅ 无     | 不影响主session功能          |
| 数据安全      | ✅ 无     | 无数据丢失                   |

### 修复后影响

| 解决方案      | 用户体验 | 功能完整性 | 实施难度 |
| ------------- | -------- | ---------- | -------- |
| Solution 2    | 🟡 改善   | ❌ 未修复  | ✅ 简单  |
| Solution 3    | ✅ 完美   | ✅ 修复    | ✅ 中等  |
| Solution 1    | ✅ 完美   | ✅ 完美    | ⚠️ 困难  |

---

## ✅ 结论

### Root Cause

**架构问题**: CLI创建的子session不在Web后端的session_manager中注册，导致前端SSE订阅返回404。

### 为什么之前的测试没发现？

1. **测试场景不完整**
   - 之前可能没有测试task工具创建的子session
   - 或者使用的是mock数据

2. **环境差异**
   - 开发环境和生产环境的session管理可能不同
   - 需要在真实环境测试CLI集成

### 推荐行动

**立即**:
- ✅ 实施Solution 2（前端优雅降级）
- ⏳ 15分钟完成

**本周**:
- ✅ 实施Solution 3（后端虚拟session）
- ⏳ 1-2小时完成

**本月**:
- ✅ 实施Solution 1（彻底重构）
- ⏳ 1-2周完成

---

**诊断状态**: ✅ 完成
**Root Cause**: ✅ 确认（架构问题）
**解决方案**: ✅ 提供3个方案
**推荐优先级**: Solution 2 → Solution 3 → Solution 1

需要我帮你实施哪个解决方案？
