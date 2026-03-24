# 修复Phase重复问题

## 问题现象

用户看到两个重复的Phase：
- "1. Executing"
- "1. 思考过程"

## 根本原因

1. **SSE实时处理**：`phase_start`事件创建phase（标题为"正在执行"）
2. **后端数据**：`phases_init`事件或深度加载获取后端phases（标题为"思考过程"）
3. **ID不匹配**：两个phase有不同的ID，但有相同的number，导致同时存在

## 修复方案

### 双层去重逻辑

**第一层：ID+Number去重**
```javascript
const key = `${p.id}_n${p.number || 0}`;
if (!phaseMap.has(key)) {
    phaseMap.set(key, p);
}
```

**第二层：Number去重**
```javascript
const seenNumbers = new Set();
const dedupedPhases = [];
Array.from(phaseMap.values()).forEach(p => {
    const num = p.number || 0;
    if (!seenNumbers.has(num)) {
        seenNumbers.add(num);
        dedupedPhases.push(p);
    }
});
```

### 处理流程

```
loadState深度加载：
  1. 从后端获取phases
  2. 第一层去重：按ID+number，确保唯一
  3. 第二层去重：按number，如果有相同的number只保留第一个
  4. 保存到localStorage
  5. 渲染UI
```

## 验证步骤

### 1. 硬刷新浏览器
```
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)
```

### 2. 执行新任务
- 输入：`66 + 55等于多少？`
- 等待完成

### 3. 切换测试
- 切换到其他历史记录
- 再切换回来
- 观察右侧panel的phase列表

### 4. 控制台验证

```javascript
// 诊断phase重复
const s = window.state.sessions.find(x => x.id === window.state.activeId);
console.log('Phases数量:', s.phases?.length);

s.phases?.forEach((p, i) => {
    console.log(`Phase ${i+1}:`, p.id, 'number:', p.number, 'title:', p.title);
});

// 检查是否有重复的number
const numbers = s.phases?.map(p => p.number || 0) || [];
const uniqueNumbers = new Set(numbers);
console.log('Numbers总数:', numbers.length, '唯一:', uniqueNumbers.size);

if (numbers.length !== uniqueNumbers.size) {
    console.log('⚠️ 仍有重复number');
} else {
    console.log('✓ 无重复');
}
```

## 预期效果

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| Phase数量 | 2个（重复） ❌ | 1个 ✓ |
| 标题 | "1. Executing" + "1. 思考过程" | "1. 思考过程"（或后端返回的标题） |
| 切换历史 | 重复增多 | 无重复 ✓ |

## 如果仍有问题

### 临时清理方案

如果刷新后仍有重复，在控制台运行：

```javascript
// 清理重复的phase
const s = window.state.sessions.find(x => x.id === window.state.activeId);
if (s && s.phases && s.phases.length > 1) {
    console.log('清理前phases:', s.phases.length);

    // 按number去重，保留第一个
    const seenNumbers = new Set();
    const cleanedPhases = [];
    s.phases.forEach(p => {
        const num = p.number || 0;
        if (!seenNumbers.has(num)) {
            seenNumbers.add(num);
            cleanedPhases.push(p);
        } else {
            console.log('删除重复phase:', p.id, 'number:', num, 'title:', p.title);
        }
    });

    s.phases = cleanedPhases;
    saveState();
    renderAll();

    console.log('清理后phases:', s.phases.length);
}
```

### 深度诊断

```javascript
// 详细phase诊断
// 复制文件内容：phase_duplicate_diagnose.js
```

---

**修改时间**：2026-03-23
**修改文件**：`static/opencode.js` 第450-490行
**修复内容**：
- 第一层：ID+Number复合键去重
- 第二层：Number字段去重（避免相同编号的phase）
**Docker容器**：已重启
