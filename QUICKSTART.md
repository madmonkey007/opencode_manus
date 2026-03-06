# OpenCode 快速上手指南

> 📅 最后更新：2026-03-06  
> 🎯 目标：5分钟快速了解项目状态

---

## 🚀 5分钟快速上手

### 第一步：了解项目目标（1分钟）

**项目**：OpenCode Thought事件显示时序修复

**核心问题**：
- 历史刷新后数据丢失
- 开场白和thought显示顺序混乱
- 任务面板时机不对

**当前状态**：
- ✅ P0+P1修复完成（评分97%）
- 🔴 3个待解决问题（影响较小）

---

### 第二步：查看最近修改（2分钟）

**快速查看**：
```bash
cd D:\manus\opencode
git log --oneline -5
git diff HEAD~1 --stat
```

**本次会话关键修复**：
- ✅ 历史刷新修复（SSE事件+localStorage）
- ✅ status thinking事件（视觉反馈）
- ✅ action timestamp修复（排序正确）
- ✅ cleanupThinkingMessage（统一清理）
- ✅ 15秒超时保护
- ✅ 去重逻辑
- ✅ 网络重连清理
- ✅ 用户取消清理
- ✅ phases_init清理

**修改统计**：
- `main.py`：净增7行
- `opencode-new-api-patch.js`：净增135行
- `opencode.js`：净增14行

---

### 第三步：了解待解决问题（1分钟）

**🔴 中等优先级**：
1. **开场白显示** - 需要enhanced-task-panel.js提取并独立显示
2. **thought在write之后** - AI执行顺序问题（已接受）

**🟢 低优先级**：
3. **Separator错误** - 影响小，可前端过滤

---

### 第四步：关键代码位置（1分钟）

**核心文件**：
- `app/main.py` (447-452行) - 后端status thinking事件
- `static/opencode-new-api-patch.js` (691-858行) - P0+P1完整修复
- `static/opencode.js` (2496-2503行) - 取消任务清理
- `static/enhanced-task-panel.js` (183-194行) - 开场白显示（待修复）

**关键函数**：
- `cleanupThinkingMessage(s)` - 统一清理thinking消息
- `sortEventsByTimestamp(events)` - 按时间排序事件
- `addSystemMessage(content, type, messageId)` - 显示系统消息

---

## 📚 深入了解

### 10分钟了解修复细节

**阅读顺序**：
1. `summary.md` - 完整修复历史
2. `CLAUDE.md` - 已知问题和注意事项
3. 本次会话关键修复（见下方）

### 30分钟完整回顾

**核心修复代码**：
- `opencode-new-api-patch.js` (691-858行) - 168行完整逻辑
  - addSystemMessage：支持messageId参数
  - cleanupThinkingMessage：统一清理
  - status thinking处理：去重+超时
  - phases_init清理：任务面板显示时清理

---

## 🧪 测试验证

### 正常流程测试
```bash
# 1. 启动后端
cd D:\manus\opencode
python -m app.main

# 2. 刷新浏览器（强制刷新）
Ctrl + Shift + R

# 3. 创建新任务
输入：帮我写一个网页版闹钟

# 4. 观察Console日志
应该看到：
[Status] Thinking started: 正在分析任务并制定计划...
[NewAPI] Thought added to phase.events
[Status] Thinking removed on phases_init

# 5. 验证显示顺序
开场白 → thinking提示消失 → 任务面板显示 → AI回复
```

### 异常流程测试
- 用户取消任务 → thinking应该立即消失
- 网络中断重连 → 旧thinking应该被清理
- AI不调用todowrite → 15秒后thinking自动消失

---

## 🔍 调试技巧

### Console日志过滤
```javascript
// 只看关键日志
[Status]      // thinking消息相关
[NewAPI]      // SSE事件处理
[TypingEffect] // 文件预览
```

### 调试开关
```javascript
// 启用thought事件调试
window._DEBUG_THOUGHT_EVENTS = true;

// 启用配置诊断
window.DEBUG_CONFIG.ENABLE_THOUGHT_DIAGNOSTIC = true;

// 查看session状态
const s = state.sessions.find(x => x.id === state.activeId);
console.log('Session:', s);
```

---

## ⚠️ 常见问题

### Q1: 开场白为什么还在response中？
**A**: 开场白独立显示功能待实施（需要修改enhanced-task-panel.js）

### Q2: thought为什么在write之后？
**A**: 这是AI的实际执行顺序（先调用write工具，再产生thought）。方案A已修复timestamp，按实际时间排序。

### Q3: 看到"Separator is not found"错误？
**A**: 这是后端error事件，影响较小，后续会修复。

---

## 📞 联系与反馈

**问题反馈**：
- 查看：`CLAUDE.md`的"已知问题"部分
- 添加：遇到新问题时更新文档

**Git提交**：
```bash
git add .
git commit -m "修复：问题描述"
git push
```

---

## 🎯 下一步

1. ✅ 阅读本文件（QUICKSTART.md）
2. ✅ 阅读summary.md（完整修复历史）
3. ✅ 测试验证修复效果
4. ✅ 处理待解决问题

**预计时间**：5分钟了解，30分钟深入

---

*最后更新：2026-03-06 - Thought事件显示时序修复完成*