# OpenCode 全功能运行实施计划

## TL;DR

> **Quick Summary**: 该计划旨在修复 OpenCode 的核心执行流（后端解析与内核调用），并深度集成 UVN 实时预览与 Playwright 自动化验证，同时将 UI 风格对齐至 OpenManus 级别。
> 
> **Deliverables**:
> - 修复后的 `app/main.py`（正则解析与 SSE 稳定性）
> - 完善的 `.env` 配置文件（API Keys）
> - 对齐 OpenManus 风格的 `index.html` 与 `opencode.js`
> - 集成的 UVN (noVNC) 实时预览面板
> - Playwright 自动化验证脚本与截图反馈流
> 
> **Estimated Effort**: Medium (3-5 Waves)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (Core Fix) → Task 2 (SSE) → Task 4 (UVN) → Task 5 (Verification)

---

## Context

### Original Request
用户希望在 `D:/manus/opencode` 下实现 OpenCode 的全功能运行，包括 UI 对齐 OpenManus、内核调用、UVN 实时预览以及 Playwright 截图验证。当前存在输入无响应及工具显示为 "undefined" 的问题。

### Interview Summary
**Key Discussions**:
- 确定了 "Using undefined" 是由于 `main.py` 中的正则表达式无法匹配 `opencode` 内核输出的新模式导致的。
- 确定了输入无响应可能是因为 Docker 容器内缺少 LLM API 密钥。
- 确定了 UVN 预览将通过 noVNC 嵌入 `iframe` 实现。

**Research Findings**:
- `opencode` CLI 版本为 1.1.50。
- Docker 容器 `opencode-container` 正在运行，且已挂载 `.env` 文件。
- noVNC 端口映射为 6081 (host) -> 6080 (container)。

---

## Work Objectives

### Core Objective
构建一个端到端的 AI 编程助手环境，用户输入指令后，内核能自动操作浏览器/编写代码，并让用户实时看到操作画面及验证结果。

### Concrete Deliverables
- 修复后的后端解析引擎（支持最新内核输出）。
- 实时 UVN 投影界面。
- Playwright 自动化测试报告（截图形式）。

### Definition of Done
- [ ] 输入 "生成一个简单的计时器网页" 能成功执行并显示过程。
- [ ] 工具调用（如 `bash`）在 UI 上正确显示名称。
- [ ] 右侧面板实时显示浏览器操作画面。
- [ ] 任务完成后自动显示 Playwright 验证截图。

### Must Have
- 正确的 LLM API 配置。
- 鲁棒的流式解析正则表达式。
- 响应式的双栏 UI 布局。

### Must NOT Have (Guardrails)
- 不得在非加密环境下暴露敏感 API Key。
- 不得在没有验证的情况下删除用户 workspace 里的文件。

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO (Current project lacks automated tests)
- **User wants tests**: YES (Playwright integration requested)
- **QA approach**: Manual verification for UI + Automated Playwright screenshots for kernel tasks.

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: 修复内核解析与环境 (High Priority)
└── Task 3: UI 风格深度适配 (Medium Priority)

Wave 2 (After Wave 1):
├── Task 2: 增强 SSE 流式传输稳定性
└── Task 4: UVN 实时预览集成 (Depends on Task 1)

Wave 3 (After Wave 2):
└── Task 5: Playwright 自动化验证流 (Final)
```

---

## TODOs

- [ ] 1. 修复内核解析与环境配置

  **What to do**:
  - 更新 `app/main.py` 中的正则表达式以支持 `Running tool:` 和 `Tool Activate >` 等模式。
  - 检查并更新 `.env` 文件，确保包含 `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY` 等内核所需的密钥。
  - 重启 Docker 容器以应用配置。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要同时处理 Python 代码逻辑和 Docker 环境配置。
  - **Skills**: [`python-programmer`, `git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2, Task 4

  **Acceptance Criteria**:
  - `docker exec opencode-container opencode run --prompt "hello"` 在终端有输出。
  - 网页端发送消息后，后端日志显示成功启动 `opencode run`。

- [ ] 2. 增强 SSE 流式传输稳定性

  **What to do**:
  - 在 `app/main.py` 的事件生成器中增加心跳机制（空注释或特定 ping 事件）。
  - 优化错误处理，确保子进程崩溃时前端能收到明确的错误通知。

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: 涉及异步并发流处理。
  - **Skills**: [`python-programmer`]

  **Parallelization**:
  - **Can Run In Parallel**: NO (Depends on Task 1)
  - **Parallel Group**: Wave 2

- [ ] 3. UI 风格深度适配 OpenManus

  **What to do**:
  - 调整 `static/index.html` 中的配色方案，确保与 OpenManus 的品牌色一致。
  - 实现侧边栏的折叠/展开动画。
  - 优化移动端适配。

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1

- [ ] 4. UVN 实时预览集成

  **What to do**:
  - 在前端 `index.html` 中配置 noVNC iframe 的连接参数。
  - 在 `opencode.js` 中增加逻辑：当内核启动带有浏览器的任务时，自动切换到预览标签。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`dev-browser`, `typescript-programmer`]

  **Parallelization**:
  - **Can Run In Parallel**: NO (Depends on Task 1)
  - **Parallel Group**: Wave 2

- [ ] 5. Playwright 自动化验证流

  **What to do**:
  - 在 `opencode` 工作区内编写或生成 Python 验证脚本，使用 Playwright 访问并截图。
  - 后端增加接口以读取并返回最新的验证截图。
  - 前端在任务结束时自动显示该截图。

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: [`agent-browser`, `python-programmer`]

  **Parallelization**:
  - **Can Run In Parallel**: NO (Final integration)
  - **Parallel Group**: Wave 3

---

## Success Criteria

### Final Checklist
- [ ] 输入 Query 正常响应且 UI 流式显示。
- [ ] 工具名称显示正确（非 "undefined"）。
- [ ] UVN 面板能看到浏览器实时画面。
- [ ] 任务结束后有 Playwright 截图反馈。
