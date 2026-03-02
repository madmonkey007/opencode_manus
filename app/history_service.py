import sqlite3
import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("opencode.history")

class HistoryService:
    def __init__(self, db_path: str = "history.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 会话表 - 添加title和mode字段
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    prompt TEXT,
                    title TEXT,
                    mode TEXT DEFAULT 'auto',
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            # 步骤表 (工具调用)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS steps (
                    step_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    tool_name TEXT,
                    tool_input TEXT,
                    action_type TEXT,
                    file_path TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)
            # 文件快照表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_id TEXT,
                    file_path TEXT,
                    content TEXT,
                    operation_type TEXT, -- 'created' or 'modified'
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (step_id) REFERENCES steps (step_id)
                )
            """)

            # ✅ v=38修复：消息表（解决工具调用Part数据丢失问题）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata_json TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)

            # ✅ v=38修复：消息部分表（工具调用、文本等）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_parts (
                    part_id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    part_type TEXT NOT NULL,
                    content_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
                )
            """)

            # ✅ v=38修复：索引优化
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parts_message ON message_parts(message_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parts_type ON message_parts(part_type)")

            # 添加缺失的列（如果表已存在）
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
            except:
                pass  # 列已存在

            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN mode TEXT DEFAULT 'auto'")
            except:
                pass  # 列已存在

            conn.commit()

    async def capture_tool_use(self, session_id: str, tool_name: str, tool_input: dict, step_id: str = None, mode: str = "auto") -> dict:
        if not step_id:
            step_id = str(uuid.uuid4())

        # 尝试推断 action_type 和 file_path
        action_type = "call"
        file_path = ""

        if tool_name in ["write", "create_file"]:
            action_type = "write"
            file_path = str(tool_input.get("file_path") or tool_input.get("path") or "")
        elif tool_name in ["edit", "file_editor", "patch"]:
            action_type = "edit"
            file_path = str(tool_input.get("file_path") or tool_input.get("path") or "")
        elif tool_name in ["bash", "shell", "terminal"]:
            action_type = "bash"

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # 确保会话存在 - 同时保存mode
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions (session_id, status, mode, start_time)
                    VALUES (?, 'active', ?, CURRENT_TIMESTAMP)
                """, (session_id, mode))

                # 记录步骤
                cursor.execute("""
                    INSERT INTO steps (step_id, session_id, tool_name, tool_input, action_type, file_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (step_id, session_id, tool_name, json.dumps(tool_input, ensure_ascii=False), action_type, file_path))
                conn.commit()

            return {
                "step_id": step_id,
                "action_type": action_type,
                "file_path": file_path,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error capturing tool use: {e}")
            return {"step_id": step_id, "action_type": action_type, "file_path": file_path}

    async def capture_file_change(self, step_id: str, file_path: str, content: str, operation_type: str):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO file_snapshots (step_id, file_path, content, operation_type)
                    VALUES (?, ?, ?, ?)
                """, (step_id, file_path, content, operation_type))
                conn.commit()
        except Exception as e:
            logger.error(f"Error capturing file change: {e}")

    async def get_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT step_id, action_type, file_path as path, timestamp 
                    FROM steps 
                    WHERE session_id = ? 
                    ORDER BY timestamp ASC
                """, (session_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting timeline: {e}")
            return []

    async def get_file_at_step(self, session_id: str, file_path: str, target_step_id: str) -> Optional[str]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT content FROM file_snapshots
                    WHERE file_path = ? AND step_id IN (
                        SELECT step_id FROM steps
                        WHERE session_id = ? AND timestamp <= (
                            SELECT timestamp FROM steps WHERE step_id = ?
                        )
                    )
                    ORDER BY timestamp DESC LIMIT 1
                """, (file_path, session_id, target_step_id))

                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting file at step: {e}")
            return None

    # ✅ v=38修复：添加Message持久化方法（解决工具调用数据丢失问题）
    async def save_message(self, session_id: str, message_id: str, role: str) -> bool:
        """
        保存消息到数据库

        Args:
            session_id: 会话ID
            message_id: 消息ID
            role: 'user' or 'assistant'

        Returns:
            是否保存成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO messages (message_id, session_id, role, created_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (message_id, session_id, role))
                conn.commit()
                logger.debug(f"Saved message: {message_id} for session: {session_id}")
                return True
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False

    async def save_part(self, session_id: str, message_id: str, part: dict) -> bool:
        """
        保存message part到数据库（工具调用、文本等）

        Args:
            session_id: 会话ID
            message_id: 消息ID
            part: part字典，包含id, type, content等字段

        Returns:
            是否保存成功
        """
        try:
            # 确保message存在
            await self.save_message(session_id, message_id, "assistant")

            # 提取part内容
            content_data = part.get("content", {})
            if isinstance(content_data, dict):
                content_json = json.dumps({
                    "text": content_data.get("text"),
                    "tool": content_data.get("tool"),
                    "tool_name": content_data.get("tool_name"),
                    "call_id": content_data.get("call_id"),
                    "state": content_data.get("state"),
                    "input": content_data.get("input"),
                    "output": content_data.get("output"),
                    "status": content_data.get("status"),
                }, ensure_ascii=False)
            else:
                content_json = json.dumps({"text": str(content_data)}, ensure_ascii=False)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO message_parts
                    (part_id, message_id, part_type, content_json, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    part.get("id"),
                    message_id,
                    part.get("type", "text"),
                    content_json
                ))
                conn.commit()
                logger.debug(f"Saved part: {part.get('id')} type={part.get('type')} for message: {message_id}")
                return True
        except Exception as e:
            logger.error(f"Error saving part: {e}")
            return False

    async def get_message_parts(self, session_id: str, message_id: str) -> List[dict]:
        """
        获取消息的所有parts（用于刷新后恢复）

        Args:
            session_id: 会话ID
            message_id: 消息ID

        Returns:
            part字典列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT part_id, message_id, part_type, content_json
                    FROM message_parts
                    WHERE message_id = ?
                    ORDER BY created_at ASC
                """, (message_id,))

                parts = []
                for row in cursor.fetchall():
                    part_id, msg_id, part_type, content_json = row
                    try:
                        content = json.loads(content_json) if content_json else {}
                        parts.append({
                            "id": part_id,
                            "message_id": msg_id,
                            "type": part_type,
                            "content": content
                        })
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse part content: {e}")

                logger.debug(f"Retrieved {len(parts)} parts for message: {message_id}")
                return parts
        except Exception as e:
            logger.error(f"Error getting message parts: {e}")
            return []

_instance = None
def get_history_service():
    global _instance
    if _instance is None:
        _instance = HistoryService()
    return _instance
