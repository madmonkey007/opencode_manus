"""
OpenCode History Tracking Service
实时预览与历史追踪核心服务
"""
import sqlite3
import json
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger("opencode.history")


class HistoryService:
    """历史追踪服务 - 管理日志捕获和历史内容聚合"""

    def __init__(self, db_path: str = "workspace/history.db", workspace_base: str = "workspace"):
        """
        初始化历史服务

        Args:
            db_path: SQLite 数据库文件路径
            workspace_base: 工作空间基础路径
        """
        self.db_path = db_path
        self.workspace_base = Path(workspace_base)
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        # 读取 schema 文件
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
        else:
            # 如果 schema 文件不存在，使用内联定义
            schema_sql = """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'running',
                workspace_path TEXT
            );

            CREATE TABLE IF NOT EXISTS steps (
                step_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                phase_id TEXT,
                action_type TEXT NOT NULL,
                file_path TEXT,
                command TEXT,
                brief TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS file_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                step_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content_hash TEXT,
                content_size INTEGER,
                operation_type TEXT NOT NULL,
                FOREIGN KEY (step_id) REFERENCES steps(step_id) ON DELETE CASCADE,
                UNIQUE(step_id, file_path)
            );

            CREATE TABLE IF NOT EXISTS live_deltas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                step_id TEXT NOT NULL,
                delta_type TEXT NOT NULL,
                position INTEGER,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (step_id) REFERENCES steps(step_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_steps_session ON steps(session_id);
            CREATE INDEX IF NOT EXISTS idx_steps_sequence ON steps(session_id, sequence_number);
            CREATE INDEX IF NOT EXISTS idx_files_step ON file_snapshots(step_id);
            CREATE INDEX IF NOT EXISTS idx_files_path ON file_snapshots(file_path);
            CREATE INDEX IF NOT EXISTS idx_deltas_step ON live_deltas(step_id);
            """

        # 执行 schema
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(schema_sql)
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        finally:
            conn.close()

    async def capture_tool_use(
        self,
        session_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        step_id: str
    ) -> Dict[str, Any]:
        """
        捕获工具使用事件

        Args:
            session_id: 会话 ID
            tool_name: 工具名称 (write, edit, bash, read, grep)
            tool_input: 工具输入参数
            step_id: 步骤 ID

        Returns:
            捕获结果字典 {step_id, action_type, file_path, timestamp}
        """
        action_type = self._map_tool_to_action(tool_name)
        file_path = tool_input.get('file_path') or tool_input.get('path')
        command = tool_input.get('command', '')

        # 生成简短描述
        brief = self._generate_brief(action_type, file_path, command)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 插入步骤记录
            cursor.execute("""
                INSERT INTO steps (step_id, session_id, sequence_number, action_type, file_path, command, brief)
                VALUES (?, ?,
                    (SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM steps WHERE session_id = ?),
                    ?, ?, ?, ?
                )
            """, (step_id, session_id, session_id, action_type, file_path, command, brief))

            conn.commit()
            logger.info(f"Captured tool use: {tool_name} -> {action_type}")

            return {
                "step_id": step_id,
                "action_type": action_type,
                "file_path": file_path,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to capture tool use: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    async def capture_file_change(
        self,
        step_id: str,
        file_path: str,
        content: str,
        operation_type: str
    ):
        """
        捕获文件内容变更

        Args:
            step_id: 关联的步骤 ID
            file_path: 文件路径
            content: 文件内容
            operation_type: 操作类型 (created, modified, deleted)
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 插入文件快照
            cursor.execute("""
                INSERT OR REPLACE INTO file_snapshots
                (step_id, file_path, content_hash, content_size, operation_type)
                VALUES (?, ?, ?, ?, ?)
            """, (step_id, file_path, content_hash, len(content), operation_type))

            conn.commit()
            logger.info(f"Captured file change: {file_path} ({operation_type})")

            # 保存完整内容到 JSON 文件
            await self._save_content_to_json(step_id, file_path, content_hash, content)
        except Exception as e:
            logger.error(f"Failed to capture file change: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    async def capture_delta(
        self,
        step_id: str,
        delta_type: str,
        position: int,
        content: str
    ):
        """
        捕获实时增量（用于打字机效果）

        Args:
            step_id: 关联的步骤 ID
            delta_type: 增量类型 (insert, delete, replace)
            position: 操作位置
            content: 增量内容
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO live_deltas (step_id, delta_type, position, content)
                VALUES (?, ?, ?, ?)
            """, (step_id, delta_type, position, content))

            conn.commit()
        except Exception as e:
            logger.error(f"Failed to capture delta: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    async def get_file_at_step(
        self,
        session_id: str,
        file_path: str,
        target_step_id: str
    ) -> Optional[str]:
        """
        获取指定步骤时刻的文件内容（历史内容聚合）

        Args:
            session_id: 会话 ID
            file_path: 文件路径
            target_step_id: 目标步骤 ID

        Returns:
            文件内容字符串，如果不存在则返回 None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 查询目标步骤之前的最新快照
            cursor.execute("""
                SELECT fs.step_id, fs.content_hash, fs.operation_type
                FROM file_snapshots fs
                JOIN steps s ON fs.step_id = s.step_id
                WHERE s.session_id = ?
                  AND fs.file_path = ?
                  AND s.step_id <= ?
                ORDER BY s.sequence_number DESC
                LIMIT 1
            """, (session_id, file_path, target_step_id))

            snapshot = cursor.fetchone()

            if not snapshot:
                logger.warning(f"No snapshot found for {file_path} before step {target_step_id}")
                return None

            last_step_id, content_hash, operation_type = snapshot

            # 从 JSON 文件加载完整内容
            content = await self._load_content_from_json(session_id, file_path, content_hash)

            if content is None:
                logger.warning(f"Failed to load content for {file_path} with hash {content_hash}")
                return None

            return content
        except Exception as e:
            logger.error(f"Failed to get file at step: {e}")
            return None
        finally:
            conn.close()

    async def get_timeline(self, session_id: str) -> List[Dict]:
        """
        获取会话的时间轴

        Args:
            session_id: 会话 ID

        Returns:
            时间轴数据列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT step_id, sequence_number, action_type,
                       file_path, timestamp, brief
                FROM steps
                WHERE session_id = ?
                ORDER BY sequence_number ASC
            """, (session_id,))

            steps = cursor.fetchall()

            return [
                {
                    "step_id": row[0],
                    "sequence": row[1],
                    "action": row[2],
                    "path": row[3],
                    "timestamp": row[4],
                    "brief": row[5]
                }
                for row in steps
            ]
        except Exception as e:
            logger.error(f"Failed to get timeline: {e}")
            return []
        finally:
            conn.close()

    def _map_tool_to_action(self, tool_name: str) -> str:
        """映射工具名称到操作类型"""
        tool_map = {
            'write': 'write',
            'edit': 'edit',
            'file_editor': 'edit',
            'bash': 'bash',
            'terminal': 'bash',
            'read': 'read',
            'grep': 'grep'
        }
        return tool_map.get(tool_name.lower(), 'unknown')

    def _generate_brief(self, action_type: str, file_path: str, command: str) -> str:
        """生成简短描述"""
        if action_type == 'write':
            return f"创建 {file_path.split('/')[-1] if file_path else '文件'}"
        elif action_type == 'edit':
            return f"编辑 {file_path.split('/')[-1] if file_path else '文件'}"
        elif action_type == 'bash':
            return f"执行: {command[:30]}..." if len(command) > 30 else f"执行: {command}"
        elif action_type == 'read':
            return f"读取 {file_path.split('/')[-1] if file_path else '文件'}"
        elif action_type == 'grep':
            return f"搜索"
        else:
            return f"{action_type}"

    async def _save_content_to_json(self, step_id: str, file_path: str, content_hash: str, content: str):
        """
        保存完整内容到 JSON 文件

        文件路径: workspace/{session_id}/.history/file_{content_hash}.json
        """
        # 这里简化实现，实际需要根据 session_id 确定路径
        # 暂时跳过文件系统操作
        pass

    async def _load_content_from_json(self, session_id: str, file_path: str, content_hash: str) -> Optional[str]:
        """
        从 JSON 文件加载内容

        文件路径: workspace/{session_id}/.history/file_{content_hash}.json
        """
        # 这里简化实现，实际需要从文件系统读取
        # 暂时返回 None
        return None


# 全局历史服务实例
_history_service = None


def get_history_service() -> HistoryService:
    """获取历史服务单例"""
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service
