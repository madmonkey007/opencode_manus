"""测试配置和fixtures"""
import pytest
import sqlite3
import tempfile
import os
from typing import Generator


@pytest.fixture
def temp_history_db() -> Generator[str, None, None]:
    """
    创建临时history.db数据库用于测试
    
    数据库Schema与实际opencode history.db保持一致:
    - session_id: TEXT PRIMARY KEY
    - prompt: TEXT
    - start_time: TEXT (格式: YYYY-MM-DD HH:MM:SS)
    - status: TEXT
    - mode: TEXT
    """
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # 创建数据库表
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            prompt TEXT,
            start_time TEXT,
            status TEXT,
            mode TEXT
        )
    """)
    conn.commit()
    conn.close()
    
    yield path
    
    # 清理：删除临时文件
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def sample_session_data() -> dict:
    """示例session数据"""
    return {
        "session_id": "ses_test123",
        "prompt": "测试prompt",
        "start_time": "2026-03-03 12:00:00",
        "status": "active",
        "mode": "auto"
    }
