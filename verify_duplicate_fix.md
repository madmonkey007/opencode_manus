# 修复历史记录重复事件问题

## 问题原因

切换历史记录时，`loadState()`函数的深度加载逻辑导致数据重复：

1. **第450-452行**：如果后端返回`data.phases`，直接替换`s.phases`
2. **第454-485行**：又遍历`data.messages`重新构建`thoughtEvents`、`orphanEvents`、`actions`
3. **结果**：phase.events（来自后端phases）+ thoughtEvents/orphanEvents（从messages重建）同时存在，渲染时重复显示

## 修复方案

### 逻辑分支

**情况A：后端返回完整的phases（包含events）**
- ✅ 直接使用后端的phases数据
- ✅ 从messages重建prompt和response
- ✅ 清空独立的thoughtEvents/orphanEvents/actions数组
- ✅ 统一使用phase.events，避免重复

**情况B：后端没有返回完整phases**
- ✅ 保留现有phases结构，但清空events
- ✅ 从messages重建所有数据
- ✅ 添加到thoughtEvents/orphanEvents/actions

### 代码修改

```javascript
// 修改前：总是从messages重建events，导致重复
if (data.phases && data.phases.length > 0) {
    s.phases = data.phases;  // 使用后端phases（可能包含events）
}
data.messages.forEach(msg => {
    // 又重建events，添加到thoughtEvents/orphanEvents/actions
    // 导致：phase.events + thoughtEvents 都有数据
});

// 修改后：判断phases是否完整，避免重复
const hasCompletePhases = data.phases && data.phases.length > 0 &&
    data.phases.some(p => p.events && p.events.length > 0);

if (hasCompletePhases) {
    // 使用完整phases，清空独立数组
    s.phases = data.phases;
    s.actions = [];
    s.orphanEvents = [];
    s.thoughtEvents = [];
} else {
    // 从messages重建
    // ...
}
```

## 验证步骤

### 1. 硬刷新浏览器
```
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)
```

### 2. 执行新任务
- 输入问题：`66 + 55等于多少？`
- 等待任务完成

### 3. 切换历史记录测试
- 切换到其他历史记录
- 再切换回来
- 观察右侧面板的phase和thought事件

### 4. 在控制台验证
```javascript
const s = window.state.sessions.find(x => x.id === window.state.activeId);
console.log('Phase事件数:', s.phases?.[0]?.events?.length || 0);
console.log('thoughtEvents数:', s.thoughtEvents?.length || 0);
console.log('orphanEvents数:', s.orphanEvents?.length || 0);

// 检查phase.events中是否有重复thought
const phase = s.phases?.[0];
if (phase && phase.events) {
    const thoughts = phase.events.filter(e => e.type === 'thought');
    const contents = thoughts.map(t => t.content?.substring(0, 50));
    const unique = new Set(contents);
    console.log('Phase中thought:', contents.length, '唯一:', unique.size);
    if (contents.length !== unique.size) {
        console.log('⚠️ 仍有重复');
    } else {
        console.log('✓ 无重复');
    }
}
```

## 预期结果

- ✅ 执行任务时，phase和thought正常显示（无重复）
- ✅ 切换历史记录后，仍然无重复
- ✅ phase.events有数据，thoughtEvents/orphanEvents为空（使用完整phases情况）

## 如果仍有问题

如果刷新后仍有重复，请运行以下诊断：

```javascript
// 详细诊断
const s = window.state.sessions.find(x => x.id === window.state.activeId);
console.log('=== Session数据诊断 ===');
console.log('Phases:', s.phases?.length);
s.phases?.forEach((p, i) => {
    console.log(`Phase ${i}:`, p.id, 'events:', p.events?.length);
    p.events?.forEach((e, j) => {
        console.log(`  Event ${j}:`, e.type, e.content?.substring(0, 50) || e.id);
    });
});
console.log('thoughtEvents:', s.thoughtEvents?.length);
console.log('orphanEvents:', s.orphanEvents?.length);
console.log('actions:', s.actions?.length);
```

将输出发给我进一步分析。

---

**修改时间**：2026-03-23
**修改文件**：`static/opencode.js` 第442-495行
**Docker容器**：已重启
