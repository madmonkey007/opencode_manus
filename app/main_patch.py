import re
import json
import logging
import uuid
import asyncio
from typing import Optional
from fastapi.responses import StreamingResponse

# ... (imports stay same)

async def process_log_line(text: str, sid: str = None):
    """
    解析日志行并生成 SSE 事件 - 增强版
    """
    # 1. 尝试匹配 Think (Thought) 内容
    # 匹配模式：🤔 Thought: 或 Thought: 或 思考: 或 > Thought
    thought_match = re.search(r"(?:🤔\s*Thought:|Thought:|思考[:：]|>\s*Thought)\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    if thought_match:
        content = thought_match.group(1).strip()
        if content:
            yield format_sse({
                "type": "tool_event", 
                "data": {
                    "type": "thought", 
                    "content": content
                }
            })
            # 如果是文本中的思绪，我们不希望它出现在回答区，所以直接 return
            return

    # 2. 处理 JSON 格式的工具调用 (tool_use)
    if text.startswith("{") and text.endswith("}"):
        try:
            event = json.loads(text)
            event_type = event.get("type")

            # 处理任务规划 (todowrite)
            if event_type == "tool_use" and event.get("part", {}).get("tool") == "todowrite":
                # ... (todowrite logic remains same)
                pass

            # 处理具体工具执行
            elif event_type == "tool_use":
                part = event.get("part", {})
                tool_name = part.get("tool", "unknown")
                input_data = part.get("input", {})
                
                # 如果工具是 task (子智能体)，它通常包含描述性文字
                if tool_name == "task":
                    task_reason = input_data.get("reason", "") or input_data.get("task", "")
                    if task_reason:
                        yield format_sse({
                            "type": "answer_chunk", 
                            "text": f"\n> **任务调度**: {task_reason}\n"
                        })

                # 预览面板增强：确保能抓取到 code/content
                if tool_name in ["write", "edit", "file_editor", "patch", "coder"]:
                    file_path = str(input_data.get("file_path") or input_data.get("path") or input_data.get("filePath") or "unknown_file")
                    # 关键：OpenCode 的 coder 工具可能把内容放在 code 字段
                    content = input_data.get("content") or input_data.get("newString") or input_data.get("code") or ""
                    
                    step_id = str(uuid.uuid4())
                    yield format_sse({"type": "preview_start", "step_id": step_id, "file_path": file_path, "action": "write"})
                    
                    if content:
                        # 快速推送内容到预览面板
                        yield format_sse({"type": "preview_delta", "step_id": step_id, "delta": {"type": "insert", "position": 0, "content": content}})
                    
                    yield format_sse({"type": "preview_end", "step_id": step_id, "file_path": file_path})

            # ... (rest of parsing)
        except Exception:
            pass

    # 3. 过滤噪音，将普通回复显示在回答区
    noise_keywords = ["opencode run", "options:", "positionals:", "run opencode with"]
    if not any(x in text.lower() for x in noise_keywords):
        # 如果不是 JSON 且不是被处理过的思绪，作为回答块发送
        yield format_sse({"type": "answer_chunk", "text": text + "\n"})
