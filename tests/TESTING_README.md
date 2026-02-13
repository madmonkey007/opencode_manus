# OpenCode 自动化测试说明

## 测试脚本

本目录包含 OpenCode Web Interface v2.0 的自动化测试脚本。

### 文件列表

| 文件 | 说明 | 运行时间 |
|------|------|----------|
| `run_tests.bat` | Windows 测试启动器 | - |
| `quick_verify.py` | 快速验证脚本 | ~10 秒 |
| `automated_test.py` | 完整自动化测试 | ~1 分钟 |

---

## 快速开始

### Windows 用户（推荐）

**一键运行测试**:
```bash
双击 run_tests.bat
```

然后按照菜单提示选择测试类型。

### 手动运行

#### 1. 快速验证（推荐）

```bash
python tests/quick_verify.py
```

**测试内容**:
- ✅ 服务可用性
- ✅ 创建会话
- ✅ 发送消息
- ✅ 获取消息历史
- ✅ 列出会话

**预期输出**:
```
========================================
  OpenCode Web Interface 快速验证
========================================

========================================
  1. 测试服务可用性
========================================

✓ 服务正常运行
ℹ 版本: 2.0.0
ℹ 状态: healthy

...

🎉 所有测试通过！
```

#### 2. 完整测试

```bash
# 基础测试（跳过耗时测试）
python tests/automated_test.py --skip-slow

# 完整测试（包含所有测试）
python tests/automated_test.py

# 详细测试（包含日志输出）
python tests/automated_test.py --verbose
```

**测试内容**:
- 健康检查
- API 信息
- 会话管理（创建、获取、列表、删除）
- 消息功能（发送、获取历史）
- SSE 事件流
- 多轮对话
- 文件预览
- 历史回溯

---

## 命令行选项

### automated_test.py

```
用法: python tests/automated_test.py [选项]

选项:
  --base-url URL   服务地址（默认: http://localhost:8088）
  --verbose, -v    显示详细日志
  --skip-slow      跳过耗时测试
  --help, -h       显示帮助信息
```

**示例**:

```bash
# 测试本地服务
python tests/automated_test.py

# 测试远程服务
python tests/automated_test.py --base-url http://192.168.1.100:8088

# 显示详细日志
python tests/automated_test.py --verbose

# 跳过耗时测试
python tests/automated_test.py --skip-slow
```

---

## 测试前提

### 1. 服务必须运行

```bash
# 启动服务
python -m app.main

# 或使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8088
```

### 2. 依赖已安装

```bash
pip install requests sseclient-py
```

或使用 `run_tests.bat` 自动安装。

---

## 测试结果示例

### 成功示例

```
============================================================
  OpenCode Web Interface v2.0 - 自动化测试
============================================================

ℹ 服务地址: http://localhost:8088
ℹ 开始时间: 2026-02-10 14:30:00

============================================================
  基础功能
============================================================

✓ 健康检查
ℹ 版本: 2.0.0
✓ API 信息
ℹ API 版本: 2.0.0

...

============================================================
  测试结果汇总
============================================================

总计: 10
✓ 通过: 10
通过率: 100.0%

🎉 所有测试通过！
```

### 失败示例

```

============================================================
  测试结果汇总
============================================================

总计: 10
✓ 通过: 8
✗ 失败: 2
通过率: 80.0%

✗ 失败详情:
  • 创建会话
    HTTP 500: Internal Server Error
  • SSE 事件流
    连接超时
```

---

## 故障排除

### 问题 1: 无法连接到服务

**错误**:
```
✗ 服务可用性
✗ 无法连接到服务
ℹ 请确保服务已启动: python -m app.main
```

**解决方法**:
1. 确认服务已启动
2. 检查端口 8088 是否被占用
3. 尝试访问 `http://localhost:8088/opencode/health`

### 问题 2: 缺少依赖

**错误**:
```
❌ 缺少依赖: requests
请安装: pip install requests
```

**解决方法**:
```bash
pip install requests sseclient-py
```

### 问题 3: 测试超时

**错误**:
```
✗ SSE 事件流
✗ 连接超时
```

**解决方法**:
1. 检查服务是否正常运行
2. 使用 `--skip-slow` 跳过耗时测试
3. 增加超时时间（修改脚本中的 `SSE_TIMEOUT`）

### 问题 4: 会话创建失败

**错误**:
```
✗ 创建会话
✗ HTTP 500: Internal Server Error
```

**解决方法**:
1. 查看服务端日志
2. 检查 API 端点是否正确实现
3. 确认数据库/内存存储正常工作

---

## 测试覆盖范围

### 功能测试

| 功能 | 测试 | 脚本 |
|------|------|------|
| 健康检查 | ✅ | quick_verify.py |
| 创建会话 | ✅ | quick_verify.py |
| 发送消息 | ✅ | quick_verify.py |
| 获取消息 | ✅ | quick_verify.py |
| 列出会话 | ✅ | quick_verify.py |
| SSE 事件流 | ✅ | automated_test.py |
| 多轮对话 | ✅ | automated_test.py |
| 删除会话 | ✅ | automated_test.py |

### 未覆盖功能

- [ ] 文件预览（需要浏览器环境）
- [ ] 历史回溯（需要文件操作）
- [ ] UI 交互（需要浏览器自动化）
- [ ] 错误边界测试

---

## 集成到 CI/CD

### GitHub Actions 示例

```yaml
name: Test OpenCode API

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install requests sseclient-py

    - name: Start server
      run: |
        python -m app.main &
        sleep 10

    - name: Run tests
      run: python tests/automated_test.py --skip-slow
```

---

## 开发指南

### 添加新测试

1. 在 `automated_test.py` 中添加测试方法：

```python
def test_your_feature(self) -> bool:
    """测试你的功能"""
    test_name = "你的功能名称"

    try:
        # 测试逻辑
        response = requests.get(...)

        if response.status_code == 200:
            self.result.add_pass(test_name)
            return True
        else:
            self.result.add_fail(test_name, f"HTTP {response.status_code}")
            return False
    except Exception as e:
        self.result.add_fail(test_name, str(e))
        return False
```

2. 在 `run_all_tests()` 方法中添加测试调用：

```python
def run_all_tests(self) -> bool:
    # ... 现有测试

    # 添加你的测试
    print_header("你的功能分类")
    self.test_your_feature()

    # ...
```

3. 运行测试验证：

```bash
python tests/automated_test.py --verbose
```

---

## 许可证

MIT License
