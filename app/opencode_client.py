"""
OpenCode Client - CLI 调用和事件转换

负责调用 OpenCode CLI 命令，解析输出，并转换为 SSE 事件流
"""

import asyncio
import subprocess
import shlex
import json
import logging
import os
import re
import platform
import sys
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
    from .history_service import get_history_service
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
    from history_service import get_history_service

logger = logging.getLogger("opencode.client")


# ====================================================================
# OpenCode Client
# ====================================================================


class OpenCodeClient:
    """
    OpenCode CLI 客户端

    职责：
    1. 调用 opencode run CLI 命令
    2. 解析 JSON 输出
    3. 转换为 SSE 事件
    4. 广播到 EventStreamManager
    5. 生成文件预览事件
    """

    def __init__(self, workspace_base: str):
        """
        初始化客户端

        Args:
            workspace_base: 工作区基础路径
        """
        self.workspace_base = workspace_base
        os.makedirs(workspace_base, exist_ok=True)

        # 尝试初始化 history_service
        try:
            self.history_service = get_history_service()
            logger.info("History service initialized in OpenCodeClient")
        except Exception as e:
            logger.warning(f"Failed to initialize history service: {e}")
            self.history_service = None

    async def execute_message(
        self,
        session_id: str,
        assistant_message_id: str,
        user_prompt: str,
        mode: str = "auto",
        model_id: str = "new-api/gemini-3-flash-preview",
    ):
        """
        执行单条消息（调用 CLI 并广播事件）

        Args:
            session_id: 会话ID
            assistant_message_id: 助手消息ID
            user_prompt: 用户提示词
            model_id: 模型ID

        流程：
        1. 创建会话目录
        2. 构建并执行 CLI 命令
        3. 解析输出
        4. 转换为 SSE 事件
        5. 广播到 EventStreamManager
        6. 保存文件快照
        """
        session_dir = os.path.join(self.workspace_base, session_id)
        os.makedirs(session_dir, exist_ok=True)

        log_file = os.path.join(session_dir, "run.log")
        status_file = os.path.join(session_dir, "status.txt")

        # 初始化日志文件
        with open(status_file, "w", encoding="utf-8") as f:
            f.write("running")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Session started: {session_id}\n")
            f.write(f"Executing: {user_prompt}\n")

        logger.info(
            f"Executing message {assistant_message_id} for session {session_id}"
        )

        try:
            # 发送开始事件
            await self._broadcast_event(
                session_id,
                {
                    "type": "message.updated",
                    "properties": {
                        "info": {
                            "id": assistant_message_id,
                            "session_id": session_id,
                            "role": "assistant",
                            "time": {"created": int(datetime.now().timestamp())},
                        }
                    },
                },
            )

            # 环境和路径检测
            is_windows = platform.system() == "Windows"

            # 动态搜索配置文件
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file = os.path.join(base_dir, "config_host", "opencode.json")
            if not os.path.exists(config_file):
                # Fallback to current dir plus config
                config_file = os.path.join(base_dir, "config", "opencode.json")

            # 创建日志和状态目录
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # 修复 ENOENT: no such file or directory, open '.claude/transcripts/...'
            # 这是一个已知的 Windows 环境下的 OpenCode CLI 路径问题
            user_home = os.path.expanduser("~")
            claude_transcripts_dir = os.path.join(user_home, ".claude", "transcripts")
            if not os.path.exists(claude_transcripts_dir):
                logger.info(f"Creating missing directory: {claude_transcripts_dir}")
                os.makedirs(claude_transcripts_dir, exist_ok=True)

            # 构建环境变量
            env = {**os.environ}
            if not is_windows:
                path_env = "/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
                env["PATH"] = path_env

            env["FORCE_COLOR"] = "1"
            env["OPENCODE_CONFIG_FILE"] = config_file

            # 构建命令行
            safe_prompt = shlex.quote(user_prompt)
            agent_flag = f" --agent {mode}" if mode in ["plan", "build"] else ""
            inner_cmd = f"opencode run --model {model_id} --format json --thinking {safe_prompt}{agent_flag}"

            if is_windows:
                # Windows 不需要 script 命令且路径不同
                cmd = ["cmd", "/c", inner_cmd]
            else:
                # Linux/Docker 使用 script 伪终端
                cmd = ["script", "-q", "-c", inner_cmd, "/dev/null"]

            logger.info(
                f"Starting CLI process (Platform: {platform.system()}): {inner_cmd[:100]}..."
            )

            # 启动进程
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=session_dir,
                    env=env,
                )
            except FileNotFoundError as fnf:
                logger.error(f"Failed to start process: Command not found ({cmd[0]})")
                raise RuntimeError(f"CLI tool not found: {cmd[0]}")
            except Exception as pe:
                logger.error(f"Failed to start subprocess: {pe}")
                raise

            # 解析输出并生成事件
            line_count = 0
            # 使用本地会话上下文追踪当前活跃步骤，确保 ID 一致性
            # 并根据模式动态设置默认标题
            default_title = (
                "Planning & Analysis"
                if mode == "plan"
                else ("Building & Implementation" if mode == "build" else "Executing")
            )
            session_context = {
                "current_step_id": None,
                "current_step_title": default_title,
                "mode": mode,
            }

            if process.stdout is not None:
                logger.info(
                    f"Starting to read stdout for message {assistant_message_id}"
                )
                async for line in process.stdout:
                    line_text = line.decode(errors="ignore").strip()
                    if not line_text:
                        continue

                    line_count += 1
                    logger.info(f"Processing line {line_count}: {line_text[:100]}")

                    # 写入日志文件
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(line_text + "\n")

                    # 解析并生成事件
                    try:
                        async for event in self._process_line(
                            line_text, session_id, assistant_message_id, session_context
                        ):
                            logger.info(f"Yielded event type: {event.get('type')}")
                            await self._broadcast_event(session_id, event)

                    except Exception as e:
                        logger.error(f"Error processing line {line_count}: {e}")

            # 等待进程结束
            return_code = await process.wait()
            logger.info(f"CLI process finished with return code: {return_code}")

            # 更新状态文件
            with open(status_file, "w", encoding="utf-8") as f:
                f.write("completed")

            # 发送完成事件
            await self._broadcast_event(
                session_id,
                {
                    "type": "message.updated",
                    "properties": {
                        "info": {
                            "id": assistant_message_id,
                            "time": {
                                "created": int(datetime.now().timestamp()),
                                "completed": int(datetime.now().timestamp()),
                            },
                        }
                    },
                },
            )

            logger.info(f"Message {assistant_message_id} execution completed")

        except Exception as e:
            logger.error(f"Error executing message: {e}")
            # 发送错误事件
            await self._broadcast_event(
                session_id,
                {
                    "type": "error",
                    "properties": {"session_id": session_id, "message": str(e)},
                },
            )

            # 更新状态文件
            with open(status_file, "w", encoding="utf-8") as f:
                f.write("error")

    async def _process_line(
        self,
        text: str,
        session_id: str,
        message_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理单行输出，生成 SSE 事件

        Args:
            text: 输出行
            session_id: 会话ID
            message_id: 消息ID

        Yields:
            SSE 事件字典
        """
        # MARKER: 调试日志
        logger.info(f"[_process_line] Processing line: {text[:100]}...")

        # 尝试解析为 JSON
        if text.startswith("{") and text.endswith("}"):
            try:
                event = json.loads(text)
                event_type = event.get("type")
                logger.info(f"[_process_line] Parsed JSON event: type={event_type}, sessionID={event.get('sessionID')}, my session_id={session_id}")

                # 处理不同类型的事件
                if event_type == "text":
                    logger.info(f"[_process_line] Handling text event")
                    async for e in self._handle_text_event(
                        event, session_id, message_id, context
                    ):
                        yield e

                elif event_type == "tool_use":
                    logger.info(f"[_process_line] Handling tool_use event, tool={event.get('part', {}).get('tool')}")
                    async for e in self._handle_tool_use_event(
                        event, session_id, message_id
                    ):
                        yield e

                elif event_type == "thought":
                    logger.info(f"[_process_line] Handling thought event")
                    async for e in self._handle_thought_event(
                        event, session_id, message_id
                    ):
                        yield e

                elif event_type == "step_start" or event_type == "step-start":
                    logger.info(f"[_process_line] Handling step_start event")
                    async for e in self._handle_step_start_event(
                        event, session_id, message_id, context
                    ):
                        yield e

                elif event_type == "step_finish" or event_type == "step-finish":
                    logger.info(f"[_process_line] Handling step_finish event, reason={event.get('reason')}")
                    async for e in self._handle_step_finish_event(
                        event, session_id, message_id, context
                    ):
                        yield e

                elif event_type == "error":
                    logger.info(f"[_process_line] Handling error event")
                    yield self._handle_error_event(event, session_id)

                else:
                    logger.warning(f"[_process_line] Unknown event type: {event_type}")
                # 其他类型忽略
                return

            except json.JSONDecodeError as e:
                logger.error(f"[_process_line] JSON decode error: {e}, text: {text[:100]}")
            except Exception as e:
                logger.error(f"[_process_line] Error processing JSON event: {e}", exc_info=True)

        # 处理非 JSON 行（Thought 等）
        thought_match = re.search(
            r"(?:🤔\s*Thought:|Thought:|Thought\s*>\s*|思考[:：])\s*(.*)",
            text,
            re.IGNORECASE,
        )
        if thought_match:
            content = thought_match.group(1).strip()
            if content:
                yield {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {
                            "id": generate_part_id("thought"),
                            "session_id": session_id,
                            "message_id": message_id,
                            "type": "thought",
                            "content": {"text": content},
                            "time": {"start": int(datetime.now().timestamp())},
                        }
                    },
                }
            return

        # 启发式 Phase 标题检测：捕获形如 "[1/10] Plan" 或 "1. 系统检查" 的行
        phase_header_match = re.search(
            r"^(?:\[\d+/\d+\]|(?:\d+\.))\s*(.*)", text, re.IGNORECASE
        )
        if phase_header_match and context and context.get("current_step_id"):
            new_title = phase_header_match.group(1).strip()
            if new_title and new_title != context.get("current_step_title"):
                context["current_step_title"] = new_title
                logger.info(f"Heuristic title detection: {new_title}")
                yield {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {
                            "id": context["current_step_id"],
                            "session_id": session_id,
                            "message_id": message_id,
                            "type": "step-start",
                            "content": {"text": new_title},
                            "metadata": {"title": new_title},
                        }
                    },
                }

        # 过滤噪音
        # 先检查 ANSI 颜色代码和 CLI 警告（使用原始文本）
        if any(pattern in text for pattern in ["[0m", "[93m", "[1m", "\x1b["]):
            logger.debug(f"[_process_line] Filtered ANSI color code line")
            return

        noise_keywords = [
            "opencode run",
            "options:",
            "positionals:",
            "message  message to send",
            "run opencode with",
            # 过滤 OpenCode CLI 的警告信息
            "agent \"plan\" is a subagent",
            "is a subagent, not a primary agent",
            "falling back to default agent",
        ]
        if not any(keyword in text.lower() for keyword in noise_keywords):
            # 作为普通文本处理
            yield {
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "id": generate_part_id("text"),
                        "session_id": session_id,
                        "message_id": message_id,
                        "type": "text",
                        "content": {"text": text + " "},
                        "time": {"start": int(datetime.now().timestamp())},
                    }
                },
            }

    async def _handle_text_event(
        self,
        event: Dict[str, Any],
        session_id: str,
        message_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理 text 事件"""
        chunk = event.get("part", {}).get("text", "") or event.get("text", "")
        if chunk:
            # 同样对 text chunk 进行启发式标题检测
            if context and context.get("current_step_id"):
                phase_header_match = re.search(
                    r"^(?:\[\d+/\d+\]|(?:\d+\.))\s*(.*)", chunk, re.IGNORECASE
                )
                if phase_header_match:
                    new_title = phase_header_match.group(1).strip()
                    if new_title and new_title != context.get("current_step_title"):
                        context["current_step_title"] = new_title
                        yield {
                            "type": "message.part.updated",
                            "properties": {
                                "part": {
                                    "id": context["current_step_id"],
                                    "session_id": session_id,
                                    "message_id": message_id,
                                    "type": "step-start",
                                    "content": {"text": new_title},
                                    "metadata": {"title": new_title},
                                }
                            },
                        }

            # 同时检查是否有 reasoning_content
            reasoning = event.get("part", {}).get("reasoning_content") or event.get(
                "reasoning_content"
            )
            if reasoning:
                yield {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {
                            "id": generate_part_id("thought"),
                            "session_id": session_id,
                            "message_id": message_id,
                            "type": "thought",
                            "content": {"text": reasoning},
                            "time": {"start": int(datetime.now().timestamp())},
                        }
                    },
                }

            yield {
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "id": generate_part_id("text"),
                        "session_id": session_id,
                        "message_id": message_id,
                        "type": "text",
                        "content": {"text": chunk},
                        "time": {"start": int(datetime.now().timestamp())},
                    }
                },
            }

    async def _handle_tool_use_event(
        self, event: Dict[str, Any], session_id: str, message_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理 tool_use 事件"""
        part = event.get("part", {})
        tool_name = part.get("tool", "unknown")
        state = part.get("state", {})
        status = state.get("status")
        input_data = part.get("input", {})
        output = state.get("output", "")

        # 特殊处理 todowrite：转换为阶段初始化事件
        if tool_name == "todowrite":
            todos = input_data.get("todos", [])
            if todos:
                # 转换为 frontend phases 格式
                phases = []
                for i, todo in enumerate(todos):
                    phases.append(
                        {
                            "id": todo.get("id", f"phase_{i}"),
                            "title": todo.get("content", "New Phase"),
                            "status": todo.get("status", "pending"),
                            "number": i + 1,
                        }
                    )
                # 广播 phases_init 事件
                await self._broadcast_event(
                    session_id,
                    {
                        "type": "phases_init",
                        "phases": phases,
                        "timestamp": int(datetime.now().timestamp()),
                    },
                )
            return

        # 创建工具部分
        tool_part_id = generate_part_id(f"tool_{tool_name}")

        # 提取标题和描述（如果元数据中存在）
        metadata = part.get("metadata", {})
        title = metadata.get("title") or f"Using {tool_name}"

        # 发送工具事件
        yield {
            "type": "message.part.updated",
            "properties": {
                "part": {
                    "id": tool_part_id,
                    "session_id": session_id,
                    "message_id": message_id,
                    "type": "tool",
                    "content": {
                        "tool": tool_name,
                        "call_id": tool_part_id,
                        "state": state,
                        "text": output,
                    },
                    "metadata": {
                        "title": title,
                        "input": input_data,
                        "status": status,
                    },
                    "time": {
                        "start": int(datetime.now().timestamp()),
                    },
                },
                "session_id": session_id,
                "message_id": message_id,
            },
        }

        # 文件操作：生成预览事件（write/edit）
        # 注意：预览事件发送不依赖 history_service，始终发送
        if tool_name in ["write", "edit", "file_editor"]:
            await self._handle_file_operation(
                session_id, message_id, tool_name, input_data, status
            )

        # Bash/Grep 工具：生成终端输出预览
        if tool_name in ["bash", "grep", "terminal"] and output:
            await self._handle_terminal_output(
                session_id, message_id, tool_name, input_data, output
            )

        # Read 工具：生成文件内容预览
        if tool_name == "read" and output:
            await self._handle_read_preview(
                session_id, message_id, input_data, output
            )

    async def _handle_file_operation(
        self,
        session_id: str,
        message_id: str,
        tool_name: str,
        input_data: Dict[str, Any],
        status: str,
    ):
        """
        处理文件操作，生成预览事件

        Args:
            session_id: 会话ID
            message_id: 消息ID
            tool_name: 工具名称
            input_data: 输入参数
            status: 状态
        """
        try:
            file_path = input_data.get("file_path") or input_data.get("path", "")
            content = input_data.get("content", "")

            if not file_path:
                return

            step_id = generate_step_id()

            # 发送预览开始事件
            await self._broadcast_event(
                session_id,
                {
                    "type": "preview_start",
                    "step_id": step_id,
                    "file_path": file_path,
                    "action": "write" if tool_name == "write" else "edit",
                },
            )

            # 打字机效果：逐字符推送内容
            if content:
                logger.info(
                    f"Starting typewriter effect for {file_path} ({len(content)} chars)"
                )
                for i, char in enumerate(content):
                    await self._broadcast_event(
                        session_id,
                        {
                            "type": "preview_delta",
                            "step_id": step_id,
                            "delta": {"type": "insert", "position": i, "content": char},
                        },
                    )
                    # 打字机速度：每个字符间隔 5ms
                    await asyncio.sleep(0.005)
                logger.info(f"Typewriter effect completed for {file_path}")

            # 发送预览结束事件
            await self._broadcast_event(
                session_id,
                {"type": "preview_end", "step_id": step_id, "file_path": file_path},
            )

            # 发送文件生成事件（用于前端文件列表更新）
            # 注意：前端 files-manager.js 期待 data.file 对象包含 name, path, type
            await self._broadcast_event(
                session_id,
                {
                    "type": "file_generated",
                    "file": {
                        "name": file_path.split("/")[-1],
                        "path": file_path,
                        "type": (
                            file_path.split(".")[-1].lower()
                            if "." in file_path
                            else "text"
                        ),
                    },
                },
            )

            # 保存文件快照
            if self.history_service:
                await self.history_service.capture_file_change(
                    step_id=step_id,
                    file_path=file_path,
                    content=content,
                    operation_type="created" if tool_name == "write" else "modified",
                )

            # 发送时间轴更新
            await self._broadcast_event(
                session_id,
                {
                    "type": "timeline_update",
                    "step": {
                        "step_id": step_id,
                        "action": "write" if tool_name == "write" else "edit",
                        "path": file_path,
                        "timestamp": int(datetime.now().timestamp()),
                        "status": status,
                    },
                },
            )

        except Exception as e:
            logger.error(f"Error handling file operation: {e}")

    async def _handle_terminal_output(
        self,
        session_id: str,
        message_id: str,
        tool_name: str,
        input_data: Dict[str, Any],
        output: str,
    ):
        """
        处理 bash/grep/terminal 工具的输出，生成终端预览事件

        Args:
            session_id: 会话ID
            message_id: 消息ID
            tool_name: 工具名称
            input_data: 输入参数
            output: 命令输出
        """
        try:
            if not output:
                return

            step_id = generate_step_id()

            # 生成预览标题
            if tool_name == "bash":
                command = input_data.get("command", "")
                title = f"终端: {command}" if command else "终端输出"
            elif tool_name == "grep":
                pattern = input_data.get("pattern", "")
                title = f"搜索结果: {pattern}" if pattern else "搜索结果"
            else:
                title = "终端输出"

            # 发送终端预览开始事件
            await self._broadcast_event(
                session_id,
                {
                    "type": "preview_start",
                    "step_id": step_id,
                    "title": title,
                    "action": "terminal",
                    "tool": tool_name,
                },
            )

            # 发送输出内容（逐行推送以模拟终端滚动）
            lines = output.split("\n")
            for i, line in enumerate(lines):
                await self._broadcast_event(
                    session_id,
                    {
                        "type": "preview_delta",
                        "step_id": step_id,
                        "delta": {"type": "insert", "position": i, "content": line + "\n"},
                    },
                )
                # 终端输出稍快于打字机效果
                await asyncio.sleep(0.002)

            # 发送预览结束事件
            await self._broadcast_event(
                session_id,
                {"type": "preview_end", "step_id": step_id, "title": title},
            )

        except Exception as e:
            logger.error(f"Error handling terminal output: {e}")

    async def _handle_read_preview(
        self,
        session_id: str,
        message_id: str,
        input_data: Dict[str, Any],
        output: str,
    ):
        """
        处理 read 工具的输出，生成文件内容预览事件

        Args:
            session_id: 会话ID
            message_id: 消息ID
            input_data: 输入参数
            output: 文件内容
        """
        try:
            if not output:
                return

            file_path = input_data.get("path") or input_data.get("file_path", "")
            step_id = generate_step_id()

            # 发送文件预览开始事件
            await self._broadcast_event(
                session_id,
                {
                    "type": "preview_start",
                    "step_id": step_id,
                    "file_path": file_path,
                    "action": "read",
                },
            )

            # 打字机效果：逐字符推送内容（稍快于写入）
            logger.info(
                f"Starting read preview for {file_path} ({len(output)} chars)"
            )
            for i, char in enumerate(output):
                await self._broadcast_event(
                    session_id,
                    {
                        "type": "preview_delta",
                        "step_id": step_id,
                        "delta": {"type": "insert", "position": i, "content": char},
                    },
                )
                # 读取速度稍快
                await asyncio.sleep(0.003)
            logger.info(f"Read preview completed for {file_path}")

            # 发送预览结束事件
            await self._broadcast_event(
                session_id,
                {"type": "preview_end", "step_id": step_id, "file_path": file_path},
            )

        except Exception as e:
            logger.error(f"Error handling read preview: {e}")

    async def _handle_step_start_event(
        self,
        event: Dict[str, Any],
        session_id: str,
        message_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理 step_start 事件"""
        part = event.get("part", {}) or event
        step_id = part.get("id") or part.get("step_id") or generate_part_id("step")

        # 深度标题提取策略
        default_title = (
            "Planning & Analysis"
            if context and context.get("mode") == "plan"
            else (
                "Building & Implementation"
                if context and context.get("mode") == "build"
                else "Executing"
            )
        )

        title = (
            (
                part.get("content", {}).get("text")
                if isinstance(part.get("content"), dict)
                else None
            )
            or (
                part.get("metadata", {}).get("title")
                if isinstance(part.get("metadata"), dict)
                else None
            )
            or (
                event.get("metadata", {}).get("title")
                if isinstance(event.get("metadata"), dict)
                else None
            )
            or part.get("title")
            or event.get("title")
            or part.get("label")
            or event.get("label")
            or part.get("message")
            or event.get("message")
            or default_title
        )

        description = part.get("description") or event.get("description") or ""

        # 补丁：如果标题是通用的 "Executing"，尝试从描述中找更好的
        if title == "Executing" and description:
            title = description
            description = ""

        # 记录到上下文以便后续追踪和启发式更新
        if context:
            context["current_step_id"] = step_id
            context["current_step_title"] = title

        yield {
            "type": "message.part.updated",
            "properties": {
                "part": {
                    "id": step_id,
                    "session_id": session_id,
                    "message_id": message_id,
                    "type": "step-start",
                    "content": {"text": title},
                    "metadata": {"title": title, "description": description},
                    "time": {"start": int(datetime.now().timestamp())},
                }
            },
        }

    async def _handle_step_finish_event(
        self,
        event: Dict[str, Any],
        session_id: str,
        message_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理 step_finish 事件"""
        part = event.get("part", {}) or event
        # 优先使用从上次 step_start 追踪到的 ID
        step_id = (
            part.get("id")
            or part.get("step_id")
            or (context.get("current_step_id") if context else None)
        )
        tokens = event.get("tokens", {}) or part.get("tokens", {})
        reasoning_tokens = tokens.get("reasoning", 0)

        # 尝试提取实际的思考内容
        thought_content = (
            (
                part.get("content", {}).get("text")
                if isinstance(part.get("content"), dict)
                else None
            )
            or event.get("reasoning_content")
            or part.get("reasoning_content")
            or part.get("metadata", {}).get("thought")
        )

        # 如果没有实际思考内容，跳过（不显示 token 数的占位消息）
        if not thought_content:
            return

        # 如果有任何思考信息，生成思考事件
        if thought_content:
            yield {
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "id": generate_part_id("thought"),
                        "session_id": session_id,
                        "message_id": message_id,
                        "type": "thought",
                        "content": {"text": thought_content},
                        "time": {"start": int(datetime.now().timestamp())},
                    }
                },
            }

        # 发送阶段完成信号
        step_id = part.get("id") or part.get("step_id")
        if step_id:
            yield {
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "id": step_id,
                        "session_id": session_id,
                        "message_id": message_id,
                        "type": "step-finish",
                        "content": {"text": "Completed"},
                        "time": {"end": int(datetime.now().timestamp())},
                    }
                },
            }

    def _handle_error_event(
        self, event: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """处理 error 事件"""
        err_msg = event.get("message", "Unknown error")
        return {
            "type": "error",
            "properties": {"session_id": session_id, "message": err_msg},
        }

    async def _handle_thought_event(
        self, event: Dict[str, Any], session_id: str, message_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理显式的 thought 事件"""
        part = event.get("part", {}) or event
        content = (
            part.get("content", {}).get("text")
            or part.get("text")
            or event.get("reasoning_content")
        )

        if content:
            yield {
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "id": generate_part_id("thought"),
                        "session_id": session_id,
                        "message_id": message_id,
                        "type": "thought",
                        "content": {"text": content},
                        "time": {"start": int(datetime.now().timestamp())},
                    }
                },
            }

    async def _broadcast_event(self, session_id: str, event: Dict[str, Any]):
        """
        广播事件到 EventStreamManager

        Args:
            session_id: 会话ID
            event: 事件对象
        """
        try:
            try:
                from .api import event_stream_manager
            except ImportError:
                try:
                    from api import event_stream_manager
                except ImportError:
                    logger.error(
                        "Failed to import event_stream_manager for broadcasting"
                    )
                    return

            logger.info(
                f"Broadcasting event {event.get('type')} to session {session_id}"
            )
            await event_stream_manager.broadcast(session_id, event)
        except Exception as e:
            logger.error(f"Failed to broadcast event: {e}")


# ====================================================================
# 辅助函数
# ====================================================================


async def execute_opencode_message(
    session_id: str,
    message_id: str,
    user_prompt: str,
    workspace_base: str,
    mode: str = "auto",  # New parameter
):
    """
    后台执行 OpenCode 消息的入口函数

    Args:
        session_id: 会话ID
        message_id: 消息ID
        user_prompt: 用户提示词
        workspace_base: 工作区基础路径
    """
    client = OpenCodeClient(workspace_base)
    await client.execute_message(session_id, message_id, user_prompt, mode=mode)


# ====================================================================
# 工具类型映射（兼容前端）
# ====================================================================


def map_tool_to_type(tool_name: str) -> str:
    """映射内部工具名称到前端显示类型"""
    tool = tool_name.lower()

    if "read" in tool:
        return "read"
    if "write" in tool or "save" in tool or "create" in tool:
        return "write"
    if "bash" in tool or "sh" == tool or "shell" in tool:
        return "bash"
    if "terminal" in tool or "command" in tool or "cmd" in tool or "run" in tool:
        return "terminal"
    if (
        "grep" in tool
        or "search" in tool
        and "web" not in tool
        and "google" not in tool
    ):
        return "grep"
    if "browser" in tool or "click" in tool or "visit" in tool or "scroll" in tool:
        return "browser"
    if "web" in tool or "google" in tool:
        return "web_search"
    if "edit" in tool or "replace" in tool:
        return "file_editor"

    return "file_editor"  # Default fallback
