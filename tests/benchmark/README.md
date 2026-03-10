# OpenCode 性能优化调研

## 📋 调研概述

本调研旨在验证**迁移到官方 `opencode web` 持久化服务器**的可行性和收益。

### 调研目标

1. ✅ **性能验证**: opencode web能否真正消除CLI冷启动？
2. ✅ **API兼容性**: 官方API是否支持当前所有功能？
3. ✅ **数据模型**: 数据库schema是否兼容？
4. ✅ **成本效益**: 迁移的成本和收益对比

### 预期时间线

- **Day 0**: 环境准备（2小时）
- **Day 1**: 性能测试（8-10小时）
- **Day 2**: API兼容性检查（8-10小时）
- **Day 3**: 数据分析和决策（6-8小时）

---

## 🚀 快速开始

### 前置要求

1. **当前FastAPI服务器**（8000端口）正在运行
2. **opencode web服务器**（8888端口）正在运行
3. Python 3.8+ 和必要的依赖

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务器

#### 终端1: 当前实现
```bash
cd D:\manus\opencode
python -m uvicorn app.main:app --port 8000 --reload
```

#### 终端2: opencode web
```bash
opencode web --port 8888
```

### 运行测试

#### Day 1: 性能测试
```bash
cd D:\manus\opencode\tests
python benchmark/benchmark.py
```

#### Day 2: API兼容性
```bash
cd D:\manus\opencode\tests
python api_compatibility/api_check.py
```

#### Day 3: 最终分析
```bash
cd D:\manus\opencode\tests
python analysis/final_analysis.py
```

---

## 📁 目录结构

```
D:\manus\opencode\tests\
├── benchmark/              # Day 1: 性能测试
│   ├── config.py          # 配置文件
│   ├── benchmark.py       # 基准测试脚本
│   └── README.md          # 本文档
├── api_compatibility/     # Day 2: API兼容性检查
│   ├── api_check.py       # API对比脚本
│   └── verify_features.py # 功能验证
├── analysis/              # Day 3: 数据分析
│   ├── final_analysis.py  # 最终分析脚本
│   └── generate_report.py # 报告生成器
├── logs/                  # 测试日志
├── results/               # 测试结果（JSON格式）
└── reports/               # 生成的报告（Markdown格式）
    ├── day1_performance.md
    ├── day2_api_compatibility.md
    └── FINAL_DECISION.md
```

---

## 🔬 测试方法

### Day 1: 性能测试

**方法**:
1. 对当前实现进行10次创建session测试
2. 对opencode web进行10次创建session测试
3. 对比两者的平均响应时间、中位数、成功率

**关键指标**:
- 平均响应时间
- 首个token到达时间
- 第一个session vs 后续session的性能差异

**成功标准**:
- 性能提升 >= 50%
- opencode web后续session < 10秒

### Day 2: API兼容性

**方法**:
1. 获取两个实现的OpenAPI规范
2. 对比端点路径、请求参数、响应格式
3. 验证关键功能（项目分组、文件上传等）

**关键指标**:
- API兼容性比例
- 缺失的端点数量
- 不兼容的功能

**成功标准**:
- API兼容性 >= 60%
- 关键功能（projects、message_parts）可迁移

### Day 3: 成本效益分析

**方法**:
1. 统计需要重写的代码量
2. 估算开发工作量（人天）
3. 计算ROI和投资回报期

**关键指标**:
- 需要重写的代码行数
- 预计工作量
- 性能提升百分比
- 年化ROI

**决策标准**:
- ✅ **批准**: 性能提升>=50% + API兼容性>=60% + 回报期<=90天
- ⚠️ **谨慎**: 性能提升30-50% 或 API兼容性50-60%
- ❌ **拒绝**: 性能提升<30% 或 API兼容性<50%

---

## 🛡️ 风险控制

### 测试数据隔离

**虚拟项目机制**:
- 所有测试使用虚拟项目 `proj_benchmark_test`
- 测试完成后自动删除该项目
- 不污染生产数据

**实施**:
```python
# 测试前
await create_project("proj_benchmark_test", "性能测试项目")

# 执行测试（所有session创建在测试项目中）
await run_tests()

# 测试后
await delete_project("proj_benchmark_test")  # 级联删除所有测试数据
```

### 错误处理

**自动重试机制**:
- API调用失败自动重试3次
- 指数退避策略（1s, 2s, 4s）
- 超时设置：30秒

**日志记录**:
- 所有操作记录到 `tests/logs/benchmark.log`
- 详细记录失败原因和堆栈跟踪

---

## 📊 报告格式

### Day 1 报告

```markdown
# Day 1: 性能测试报告

## 执行摘要
- 当前实现平均: 17.5s
- opencode web平均: 5.8s
- 性能提升: 66.7%

## 详细数据
[统计数据、图表、分析...]

## 结论
✅ 性能显著提升
```

### 最终决策报告

```markdown
# 迁移可行性调研 - 最终决策

## 决策
**APPROVE** / **REJECT** / **CAUTIOUS**

## 理由
[基于数据的决策依据...]

## 下一步行动
[具体的实施计划...]
```

---

## 🤝 贡献指南

### 代码规范

- 使用Python 3.8+类型提示
- 所有异步函数使用 `async/await`
- 完整的文档字符串
- 详细的错误日志

### 测试规范

- 每个测试脚本可独立运行
- 测试失败时提供详细的错误信息
- 结果保存为JSON格式（便于后续分析）

---

## 📞 支持

如有问题，请查看：
1. 测试日志: `tests/logs/benchmark.log`
2. 测试结果: `tests/results/`
3. 生成的报告: `reports/`

---

**调研开始时间**: 2026-03-08
**预计完成时间**: 2026-03-11
**调研负责人**: ___________
