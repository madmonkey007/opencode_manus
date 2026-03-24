# Preview事件修复 - 手动测试指南

## 测试目的
验证preview事件修复是否生效，确认：
1. ✅ 文件预览正常显示
2. ✅ 打字机效果正常
3. ✅ 交付面板显示文件
4. ✅ 工具调用正确显示

---

## 📋 测试步骤

### 步骤1：确认服务已重启

**检查服务是否运行最新代码**：

```bash
# 查看服务启动时间
tasklist | findstr python

# 查看日志时间戳
tail -1 D:\manus\opencode\logs\app.err.log
```

**预期**：日志应该是最近的（今天），而不是3月23日的旧日志。

**如果是旧服务**，请重启：
```bash
# 使用修复脚本
D:\manus\opencode\fix_service.bat
```

---

### 步骤2：打开浏览器开发者工具

1. 打开Chrome/Edge浏览器
2. 访问：`http://localhost:8089`
3. 按 `F12` 打开开发者工具
4. 切换到 **Console（控制台）** 标签

---

### 步骤3：运行测试任务

在欢迎页输入框中输入：
```
帮我写一个简单的HTML页面，标题是Test Preview
```

点击"发送"按钮。

---

### 步骤4：观察控制台日志

**预期应该看到的日志**：

```
[NewAPI] Connecting to events... (Mode: build)
[NewAPI] Established SSE connection
[Event-Adapter] message.part.updated received: Object
[Event-Adapter] adaptPartEvent returned: action
[NewAPI] 显示写入文件: xxx (Tool: write)
[PREVIEW] Current listener count for session ses_xxx: 1
[PREVIEW] Broadcasting to 1 listener(s)
[PREVIEW] Sent preview_start event
```

**关键日志检查点**：
- ✅ `[NewAPI] 显示写入文件: xxx (Tool: write)` - 看到write工具
- ✅ 没有看到"命令输出为空，跳过保存"的bash消息
- ✅ 右侧面板应该显示文件预览

---

### 步骤5：验证功能

#### 5.1 检查工具调用显示

**应该看到**：
```
📝 正在写入文件...
文件：index.html
工具：write
```

**不应该看到**：
```
❌ Tool: bash（所有工具都显示为bash）
❌ 命令输出为空，跳过保存
```

#### 5.2 检查右侧文件面板

**应该看到**：
- 文件列表中出现 `index.html`
- 点击文件可以看到预览内容
- 有打字机效果（文字逐个显示）

#### 5.3 检查交付面板

**应该看到**：
- 任务完成后出现交付面板
- 显示生成的文件
- 文件可以点击查看

---

## 🔍 诊断检查清单

### 如果Preview事件正常

**控制台应该有**：
```
✅ [NewAPI] 显示写入文件: index.html (Tool: write)
✅ [PREVIEW] Generating preview for write: ...
✅ [PREVIEW] Broadcasting to 1 listener(s)
✅ [PREVIEW] Sent preview_start event
✅ [PREVIEW] Starting typewriter effect: xx chunks
✅ [PREVIEW] Completed typewriter effect
✅ [PREVIEW] Sent preview_end event
```

**前端应该显示**：
- ✅ 右侧面板显示文件预览
- ✅ 有打字机效果
- ✅ 交付面板显示文件

---

### 如果Preview事件仍然不工作

**请收集以下信息**：

1. **后端日志**：
```bash
tail -100 D:\manus\opencode\logs\app.err.log | findstr PREVIEW
```

2. **前端控制台日志**：
   - 按F12打开开发者工具
   - 切换到Console标签
   - 截图所有日志

3. **网络请求**：
   - 开发者工具 → Network标签
   - 筛选`/events`
   - 查看SSE连接状态

4. **工具调用详情**：
   - 是否看到write工具？
   - 还是只看到bash工具？

---

## 🎯 成功标准

测试**成功**的标准：

1. ✅ 看到write工具调用（不只是bash）
2. ✅ 右侧面板显示文件预览
3. ✅ 有打字机效果（逐字显示）
4. ✅ 交付面板显示生成的文件
5. ✅ 后端日志有完整的preview事件记录

如果**全部通过**，恭喜！Preview事件修复成功！🎉

如果**有任何失败**，请告诉我具体是哪一步，我会进一步诊断。

---

## 📸 如何收集证据

**如果需要反馈问题**，请提供：

1. **浏览器控制台截图**（F12 → Console）
2. **右侧面板截图**
3. **后端日志**：
```bash
tail -50 D:\manus\opencode\logs\app.err.log > preview_debug.log
```
4. **网络请求截图**（F12 → Network → 筛选events）

---

**准备好了吗？请开始测试并告诉我结果！** 🚀

---

**相关文档**：
- `PREVIEW_FIX_SUMMARY.md` - 修复摘要
- `PREVIEW_DIAGNOSIS.md` - 问题诊断
- `CODE_REVIEW_FIX_SUMMARY.md` - 代码审查修复
