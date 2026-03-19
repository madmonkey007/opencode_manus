import asyncio
import subprocess
import shlex
import json
import logging
import os
import re
import platform
import sys
import time
import httpx
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime

try:
    from .models import (
        Part,
        PartType,
        PartTime,
        PartContent,
        ToolStatus,
        generate_part_id,
        generate_step_id,
    )
    from .api import event_stream_manager
    from .history_service import get_history_service, HistoryService
except ImportError:
    from models import (
        Part,
        PartType,
        PartTime,
        PartContent,
        ToolStatus,
        generate_part_id,
        generate_step_id,
    )
    from history_service import get_history_service, HistoryService

logger = logging.getLogger("opencode.client")

# Server API session reuse: map app session_id -> server session_id
_SERVER_SESSION_ID_MAP: Dict[str, str] = {}

# Constants
CLI_EVENT_TYPE_TOOL_USE = 'tool_use'
CLI_EVENT_TYPE_TEXT = 'text'
PART_TYPE_TOOL = 'tool'
PART_TYPE_TEXT = 'text'
PART_TYPE_THOUGHT = 'thought'

# Known tools whitelist
KNOWN_TOOLS = [
    'read', 'write', 'edit', 'bash', 'grep', 'task', 'todowrite',
    'search', 'browse', 'run_server', 'file_editor', 'common_search__search'
]

# JSON size limit
MAX_JSON_SIZE = 10240

# Regex patterns
THOUGHT_PATTERN = re.compile(r"(?:🤔\s*Thought:|Thought:|Thought\s*>\s*|思考[:：])\s*(.*)", re.IGNORECASE)
PHASE_HEADER_PATTERN = re.compile(r"^(?:\[\d+/\d+\]|(?:\d+\.))\s*(.*)", re.IGNORECASE)

"""
Global Cursor Tracking for AI Reply Deduplication

Key Format: "{session_id}_{message_id}_{part_type}"
  - session_id:  前端会话ID
  - message_id:  助手消息ID
  - part_type:   "text" | "thought"
Value: int (已发送的字符长度)

Thread Safety: asyncio 单线程，但路径B/C并发时需用 _cursor_lock 保护。
Memory:        每小时由 _cleanup_cursors() 清理一次。
"""
_SENT_TEXT_LENGTHS_GLOBAL: Dict[str, int] = {}
_cursor_lock = asyncio.Lock()

# Preview deduplication: tracks which step_ids have already had preview events sent
# Key Format: "preview_{session_id}_{step_id}"
# Memory: 每小时由 _cleanup_cursors() 一并清理。
_SENT_PREVIEW_STEPS: set = set()


async def _cleanup_cursors():
    """每小时清理一次游标字典和 preview 集合，防止内存无限增长。"""
    while True:
        await asyncio.sleep(3600)
        _SENT_TEXT_LENGTHS_GLOBAL.clear()
        _SENT_PREVIEW_STEPS.clear()
        logger.info("[Cleanup] Cursor and preview dedup state cleared")

class OpenCodeClient:
    def __init__(self, workspace_base: str):
        self.workspace_base = workspace_base
        os.makedirs(workspace_base, exist_ok=True)
        self.server_api_base_url = os.getenv("OPENCODE_SERVER_URL", "http://127.0.0.1:4096")

        # 初始化history_service（使用正确的数据库路径）
        history_db_path = os.path.join(workspace_base, 'history.db')
        try:
            self.history_service: Optional[HistoryService] = HistoryService(history_db_path)
            logger.info(f"History service initialized: {history_db_path}")
        except FileNotFoundError:
            logger.error(f"History database directory not found: {os.path.dirname(history_db_path)}")
            self.history_service = None
        except PermissionError:
            logger.error(f"Permission denied accessing history database: {history_db_path}")
            self.history_service = None
        except Exception as e:
            logger.error(f"Failed to initialize history service: {type(e).__name__}: {e}")
            self.history_service = None

        self._skip_preview_sessions = set()
        # Track active preview tasks so errors surface and cleanup is possible
        self._active_preview_tasks: set = set()

    def _extract_session_id_from_payload(self, payload: Dict[str, Any]) -> Optional[str]:
        props = payload.get("properties") or {}
        if isinstance(props, dict) and props.get("sessionID"):
            return props.get("sessionID")
        info = props.get("info") or {}
        if isinstance(info, dict) and info.get("sessionID"):
            return info.get("sessionID")
        part = props.get("part") or {}
        if isinstance(part, dict) and part.get("sessionID"):
            return part.get("sessionID")
        return None

    def _normalize_server_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        etype = payload.get("type")
        props = payload.get("properties") or {}
        if etype == "message.part.updated":
            part = props.get("part") or {}
            if not isinstance(part, dict): return payload
            if part.get("type") == "reasoning": part["type"] = "thought"
            if "content" not in part: part["content"] = {"text": part.get("text", "")}
            if part.get("type") == "tool":
                state = part.get("state") or {}
                content = {"tool": part.get("tool", "unknown"), "call_id": part.get("id"), "state": state, "text": state.get("output", "")}
                metadata = part.get("metadata") or {}
                if "input" not in metadata: metadata["input"] = state.get("input", {})
                if "status" not in metadata: metadata["status"] = state.get("status")
                part["content"] = content
                part["metadata"] = metadata
            payload["properties"]["part"] = part
        return payload

    async def _broadcast_event(self, session_id: str, event: Dict[str, Any]):
        try:
            # ✅ Final deduplication check at broadcast point
            etype = event.get("type")
            if etype in ["message.part.updated", "message.part.delta"]:
                props = event.get("properties") or {}
                part = props.get("part") or {}
                ptype = part.get("type")
                if ptype in [PART_TYPE_TEXT, PART_TYPE_THOUGHT, "reasoning"]:
                    mapped_type = PART_TYPE_THOUGHT if ptype == "reasoning" else ptype
                    msg_id = part.get("message_id")
                    if msg_id:
                        text = part.get("text") or ""
                        if not text and isinstance(part.get("content"), dict):
                            text = part["content"].get("text") or ""
                        
                        global_key = f"{session_id}_{msg_id}_{mapped_type}"
                        # If the text being broadcast is already known, we might need to skip or adjust
                        # However, by this point the delta should have been applied by the caller.
            
            logger.info(f"[BROADCAST] session={session_id} type={event.get('type')}")
            await event_stream_manager.broadcast(session_id, event)
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")

    async def _maybe_broadcast_preview(self, session_id: str, part: Dict[str, Any]):
        """
        ✅ 方案2：从 tool part 生成右侧面板 preview 事件。
        替代 main.py _run_process 路径A中的 preview_start/delta/end 逻辑。
        只处理 write/edit 类工具，且只在 SSE 路径B中触发（不在 poll 路径C中重复）。
        """
        try:
            content = part.get("content") or {}
            metadata = part.get("metadata") or {}
            state_data = content.get("state") or part.get("state") or {}

            tool_name = content.get("tool") or metadata.get("tool") or part.get("tool") or ""
            tool_name_lower = tool_name.lower()

            WRITE_TOOLS = {"write", "edit", "file_editor", "patch", "str_replace_editor"}
            if not any(t in tool_name_lower for t in WRITE_TOOLS):
                return

            # 提取文件路径
            input_data = metadata.get("input") or state_data.get("input") or content.get("input") or {}
            file_path = str(
                input_data.get("file_path") or
                input_data.get("path") or
                input_data.get("filePath") or
                part.get("file_path") or
                ""
            )
            if not file_path:
                return

            # 提取文件内容
            file_content = (
                input_data.get("content") or
                input_data.get("new_string") or
                input_data.get("newString") or
                ""
            )

            action_type = "edit" if any(t in tool_name_lower for t in {"edit", "patch", "str_replace"}) else "write"
            step_id = part.get("id") or part.get("call_id") or f"preview_{int(time.time())}"

            # 去重：同一 step_id 只发一次 preview
            preview_key = f"preview_{session_id}_{step_id}"
            if preview_key in _SENT_PREVIEW_STEPS:
                logger.debug(f"[PREVIEW] Skipping duplicate preview for step: {step_id}")
                return
            _SENT_PREVIEW_STEPS.add(preview_key)

            logger.info(f"[PREVIEW] Generating preview for {tool_name}: {file_path} ({len(file_content)} chars)")

            await event_stream_manager.broadcast(session_id, {
                "type": "preview_start",
                "step_id": step_id,
                "file_path": file_path,
                "action": action_type,
            })

            if file_content:
                chunk_size = 100
                for i in range(0, len(file_content), chunk_size):
                    chunk = file_content[i:i + chunk_size]
                    await event_stream_manager.broadcast(session_id, {
                        "type": "preview_delta",
                        "step_id": step_id,
                        "delta": {"type": "insert", "position": i, "content": chunk},
                    })
                    await asyncio.sleep(0.03)

            await event_stream_manager.broadcast(session_id, {
                "type": "preview_end",
                "step_id": step_id,
                "file_path": file_path,
            })

        except Exception as e:
            logger.error(f"[PREVIEW] Failed to broadcast preview for session {session_id}: {e}")

    async def _bridge_global_events(self, base_url, request_params, server_session_id, session_id, assistant_message_id, stop_event, state):
        async def _stream_events(url):
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url, params=request_params) as resp:
                    resp.raise_for_status()
                    data_buf = []
                    async for line in resp.aiter_lines():
                        if stop_event.is_set(): break
                        if not line:
                            if not data_buf: continue
                            data_str = "\n".join(data_buf).strip()
                            data_buf = []
                            if not data_str or data_str == "[DONE]": continue
                            try: event = json.loads(data_str)
                            except: continue
                            payload = event.get("payload") or event
                            if self._extract_session_id_from_payload(payload) != server_session_id: continue
                            normalized = self._normalize_server_event(payload)
                            if not normalized: continue
                            
                            etype = normalized.get("type")
                            props = normalized.get("properties") or {}
                            part = props.get("part") or {}
                            
                            if etype in ["message.part.updated", "message.part.delta"]:
                                ptype = part.get("type")
                                # For message.part.delta, type might be missing in some server versions, so we infer it from partId if possible
                                if not ptype and etype == "message.part.delta":
                                    ptype = "text" # Default to text for deltas if unknown

                                if ptype in [PART_TYPE_TEXT, PART_TYPE_THOUGHT, "reasoning"]:
                                    mapped_type = PART_TYPE_THOUGHT if ptype == "reasoning" else ptype
                                    
                                    # ✅ Robust text extraction
                                    text = part.get("text")
                                    if not text and isinstance(part.get("content"), dict):
                                        text = part["content"].get("text", "")
                                    
                                    if text:
                                        global_key = f"{session_id}_{assistant_message_id}_{mapped_type}"
                                        async with _cursor_lock:
                                            sent_len = _SENT_TEXT_LENGTHS_GLOBAL.get(global_key, 0)
                                            if len(text) > sent_len:
                                                delta = text[sent_len:]
                                                _SENT_TEXT_LENGTHS_GLOBAL[global_key] = len(text)
                                            else:
                                                delta = None
                                        
                                        if delta:
                                            if "content" in part and isinstance(part["content"], dict):
                                                part["content"]["text"] = delta
                                            else:
                                                part["content"] = {"text": delta}
                                            part["text"] = delta
                                            logger.info(f"[BRIDGE] Delta Applied to {etype}: {global_key} +{len(delta)}")
                                        else:
                                            logger.debug(f"[BRIDGE] Skipping duplicate content for {etype}: {global_key}")
                                            continue
                            
                            if etype == "message.part.updated" and part.get("type") == "tool":
                                state["saw_tool"] = True
                                # ✅ 非阻塞触发 preview，跟踪 task 以便错误可见和优雅关闭
                                task = asyncio.create_task(self._maybe_broadcast_preview(session_id, part))
                                self._active_preview_tasks.add(task)
                                task.add_done_callback(self._active_preview_tasks.discard)

                            if etype == "session.idle" or (etype == "message.updated" and (props.get("info") or {}).get("time", {}).get("completed")):
                                state["completed"] = True
                                stop_event.set()
                            
                            await self._broadcast_event(session_id, normalized)
                            state["events"] += 1
                        elif line.startswith("data:"): data_buf.append(line[5:].lstrip())

        # ✅ CRITICAL: Only use /event (the session-specific stream)
        # Using /global/event is redundant and often causes duplicates when sequential connection is used
        for p in ["/event"]:
            if stop_event.is_set(): break
            try: await _stream_events(f"{base_url}{p}")
            except Exception as e: logger.warning(f"Bridge failed at {p}: {e}")

    async def _execute_via_server_api(self, session_id, assistant_message_id, user_prompt, mode, model_id):
        base_url = self.server_api_base_url
        server_session_id = _SERVER_SESSION_ID_MAP.get(session_id)
        if not server_session_id:
            try:
                resp = await httpx.AsyncClient().post(f"{base_url}/session")
                server_session_id = resp.json().get("id")
                _SERVER_SESSION_ID_MAP[session_id] = server_session_id
            except: return False
        
        request_params = {"sessionID": server_session_id}
        stop_event = asyncio.Event()
        sse_state = {"events": 0, "completed": False, "saw_tool": False}
        
        bridge_task = asyncio.create_task(self._bridge_global_events(base_url, request_params, server_session_id, session_id, assistant_message_id, stop_event, sse_state))
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                # Parse model_id from environment variable or default to "new-api/glm-4.7"
                model_id = os.getenv("OPENCODE_MODEL_ID", os.getenv("OPENAI_MODEL", "new-api/glm-4.7"))

                # Extract provider and model from model_id (format: "provider/model" or just "model")
                if "/" in model_id:
                    provider_id, model_name = model_id.split("/", 1)
                else:
                    provider_id = os.getenv("OPENCODE_PROVIDER_ID", "openai")
                    model_name = model_id

                payload = {"model": {"providerID": provider_id, "modelID": model_name}, "parts": [{"type": "text", "text": user_prompt}]}
                resp = await client.post(f"{base_url}/session/{server_session_id}/message", json=payload, params=request_params)
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"Post message failed: {e}")
            return False

        try: 
            # Wait for SSE to finish or timeout
            await asyncio.wait_for(stop_event.wait(), timeout=60)
        except: 
            logger.warning(f"SSE stream for {session_id} timed out or interrupted")
            pass
        
        stop_event.set()
        
        # ✅ Polling for final state - ensures everything is captured
        # We still use _SENT_TEXT_LENGTHS_GLOBAL here to ensure no duplication with SSE content
        async def _poll_parts():
            try:
                # Limit 1 ensures we only get the latest message (assistant response)
                async with httpx.AsyncClient() as client:
                    r = await client.get(f"{base_url}/session/{server_session_id}/message", params={**request_params, "limit": 1})
                    if r.status_code == 200:
                        msgs = r.json()
                        for m in msgs:
                            if (m.get("info") or {}).get("role") == "assistant":
                                return m.get("parts") or []
            except Exception as e: 
                logger.error(f"Failed to poll final parts: {e}")
            return []

        final_parts = await _poll_parts()
        now_ts = int(time.time())
        for part in final_parts:
            ptype = part.get("type") or "text"
            if ptype in [PART_TYPE_TEXT, PART_TYPE_THOUGHT, "reasoning"]:
                mapped_type = PART_TYPE_THOUGHT if ptype == "reasoning" else ptype
                
                # Robust text extraction for final parts
                text = part.get("text")
                if not text and isinstance(part.get("content"), dict):
                    text = part["content"].get("text", "")
                
                if not text: continue
                
                global_key = f"{session_id}_{assistant_message_id}_{mapped_type}"
                async with _cursor_lock:
                    sent_len = _SENT_TEXT_LENGTHS_GLOBAL.get(global_key, 0)
                    if len(text) > sent_len:
                        delta = text[sent_len:]
                        _SENT_TEXT_LENGTHS_GLOBAL[global_key] = len(text)
                    else:
                        delta = None
                
                if delta:
                    logger.info(f"[POLL] Final Delta Applied: {global_key} +{len(delta)}")
                    await self._broadcast_event(session_id, {
                        "type": "message.part.updated",
                        "properties": {
                            "part": {
                                "id": f"final_{global_key}", "session_id": session_id, "message_id": assistant_message_id,
                                "type": mapped_type, "content": {"text": delta}, "time": {"start": now_ts}
                            }
                        }
                    })
                else:
                    logger.debug(f"[POLL] Content already fully sent for {global_key}")

                # ✅ 持久化：在 poll 阶段用完整 text 写入数据库（INSERT OR REPLACE 幂等）
                # 选择 poll 而非 SSE delta 阶段，是因为 poll 拿到的是最终完整文本，一条记录即可。
                # 注意：持久化条件独立于 delta，即使 SSE 已发完全部内容，数据库里也必须有记录。
                if self.history_service:
                    raw_id = part.get("id")
                    # 有原始 id 直接用；fallback 时加 mapped_type 后缀保证 text/thought 不互相覆盖
                    part_id = raw_id if raw_id else f"final_{global_key}_{mapped_type}"
                    try:
                        await self.history_service.save_part(session_id, assistant_message_id, {
                            "id": part_id,
                            "type": mapped_type,
                            "content": {"text": text},  # 完整文本，非 delta
                        })
                        logger.info(f"[POLL] Persisted {mapped_type} part to DB: {part_id} ({len(text)} chars)")
                    except Exception as e:
                        logger.error(f"[POLL] Failed to persist part {part_id}: {e}")
                        # 不抛出，持久化失败不影响主流程
        
        return True

    async def execute_message(self, session_id, assistant_message_id, user_prompt, mode="auto"):
        # Minimal implementation for now to restore functionality
        logger.info(f"Executing {assistant_message_id} for {session_id}")
        await self._broadcast_event(session_id, {"type": "message.updated", "properties": {"info": {"id": assistant_message_id, "session_id": session_id, "role": "assistant", "time": {"created": int(time.time())}}}})
        
        server_ok = await self._execute_via_server_api(session_id, assistant_message_id, user_prompt, mode, os.getenv("OPENAI_MODEL", "deepseek-chat"))
        
        if server_ok:
            # Wait for any in-flight preview tasks before signalling completion
            if self._active_preview_tasks:
                await asyncio.gather(*self._active_preview_tasks, return_exceptions=True)
            await self._broadcast_event(session_id, {"type": "message.updated", "properties": {"info": {"id": assistant_message_id, "time": {"completed": int(time.time())}}}})
            return
        
        # Fallback to simple stub if server fails
        await self._broadcast_event(session_id, {"type": "error", "properties": {"session_id": session_id, "message": "Server API failed"}})

_cleanup_task_started = False

async def execute_opencode_message_with_manager(session_id, message_id, user_prompt, workspace_base, mode="auto"):
    global _cleanup_task_started
    if not _cleanup_task_started:
        asyncio.create_task(_cleanup_cursors())
        _cleanup_task_started = True
    client = OpenCodeClient(workspace_base)
    await client.execute_message(session_id, message_id, user_prompt, mode=mode)
