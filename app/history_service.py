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

_instance = None
def get_history_service():
    global _instance
    if _instance is None:
        _instance = HistoryService()
    return _instance
