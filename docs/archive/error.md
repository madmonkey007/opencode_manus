# OpenCode 指令调用错误记录 (Error Log)

为了避免后续操作中重复出现工具调用错误，特此记录以下典型错误及其规避方案：

## 1. 工具缺失/不可用错误
- **错误现象**：`Model tried to call unavailable tool 'task'` 或 `Model tried to call unavailable tool 'bash'`。
- **原因**：在特定环境（如 OpenCode 系统内部）中，部分工具（如 `task`、`bash`）可能被禁用或未配置。
- **规避方案**：
    - 始终使用 `delegate_task` 代替 `task`。
    - 在需要执行命令时，先确认 `bash` 或 `interactive_bash` 是否可用。如果不可用，优先使用 `delegate_task(subagent_type='explore', ...)` 进行只读操作。
    - 不要调用 `context_info` 等系统保留工具。

## 2. 代理/委托调用错误 (Delegation Errors)
- **错误现象**：`Agent 'explore' is read-only and should use the delegate tool` 或 `Agent 'plan' is write-capable and requires the native 'task' tool`。
- **原因**：误用了 `delegate`（用于只读代理）和 `delegate_task`（用于功能性代理）的场景，或者对代理的读写权限理解有误。
- **规避方案**：
    - **只读探索**：使用 `delegate(agent='explore', ...)` 或 `delegate_task(subagent_type='explore', ...)`。
    - **规划/写入任务**：使用 `delegate_task(subagent_type='plan', ...)` 或 `delegate_task(category='...', ...)`。
    - **注意**：如果 `delegate_task` 失败提示 `Unexpected EOF`，通常是由于 Prompt 过长或代理连接中断，应简化 Prompt 后重试。

## 3. 参数校验错误 (Invalid Arguments)
- **错误现象**：`Error: The invalid tool was called with invalid arguments: [...] expected string, received undefined`。
- **原因**：调用 `invalid` 工具时漏掉了 `tool` 或 `error` 参数，或者参数类型不匹配。
- **规避方案**：
    - 调用工具前严格核对 schema。
    - 确保 `invalid` 工具的所有必需字段（如 `tool`, `error`）均已提供字符串类型的值。

## 4. 路径与权限错误
- **错误现象**：`rg: .\Application Data: 拒绝访问 (os error 5)`。
- **原因**：使用 `glob` 或 `grep` 在 Windows 环境下搜索根目录时，触碰到了系统受保护的链接文件夹。
- **规避方案**：
    - 搜索时精确指定目标子目录（如 `app/`, `static/`），避免直接搜索全盘或根目录。
    - 路径使用 `/` 风格以保证跨平台兼容性。

## 5. 执行中断错误
- **错误现象**：`Tool execution aborted` 或 `Delegation timed out`。
- **原因**：代理执行耗时过长（超过 900s）或由于网络/模型原因被强制终止。
- **规避方案**：
    - 将大任务拆分为多个小任务。
    - 使用 `run_in_background=true` 异步执行耗时操作。

## 6. 工具使用流程错误 (Tool Flow Errors)
- **错误现象**：`Error: You must read file [path] before overwriting it. Use the Read tool first`。
- **原因**：违反了“写前必读”原则。在调用 `edit` 或 `write` 之前，没有先使用 `read` 工具读取文件内容，导致系统无法验证上下文。
- **规避方案**：**在对任何现有文件进行 `edit` 或 `write` 操作之前，必须先调用 `read` 工具并确保内容已加载到上下文。** 严禁跳过此步骤。
