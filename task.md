# OpenCode 执行规约与错误规避 (Critical Guidelines)

**⚠️ 强制性要求：在执行任何写入、修改或代理任务前，必须阅读此文件以避免已知错误。**

## 1. 核心错误：`AI_InvalidResponseDataError`
- **规避方案**：**严禁调用 `invalid` 工具。** 遇到逻辑错误或参数缺失时，应在回复文本中明确指出。

## 2. 工具调用中断与 Python 语法
- **错误原因**：在 Python `f-string` 中直接使用换行符而未开启三引号，或路径包含非法转义符。
- **规避方案**：
    - 路径统一使用正斜杠 `/`。
    - 字符串拼接 `
` 时确保格式正确。

## 3. 写前必读原则 (Read-Before-Write)
- **规避方案**：在调用任何 `edit` 或 `write` 之前，必须先调用 `read` 工具。

## 4. `delegate_task` 参数要求
- **错误原因**：`run_in_background` 参数是必须的。
- **规避方案**：必须显式提供 `run_in_background=false` (同步任务) 或 `true` (并行探索)。

## 5. 计划执行中断与 SSE 挂起
- **原因**：后端 `process_log_line` 的正则解析逻辑不够健壮，无法正确处理混合日志中的多个 JSON。
- **修复**：已改为 `re.findall(r'(\{.*?\})(?=\s|$|
)')` 非贪婪提取所有 JSON 块，并确保 `answer_chunk` 正确闭合。

## 6. 前端自动触发逻辑 (已修复)
- **状态**：已通过 `sessionStorage` 锁和 `running` 状态双重校验修复。
