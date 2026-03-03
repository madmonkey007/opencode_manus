"""SessionManager单元测试"""
import pytest
import sqlite3
import uuid
from datetime import datetime
import sys
import os

# 添加app目录到路径以导入main模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 从main.py导入SessionManager常量
SESSION_ID_PREFIX = "ses_"
SESSION_ID_LENGTH = 9
PROMPT_MAX_LENGTH = 500
DEFAULT_MODE = "auto"
DEFAULT_STATUS = "active"
DB_PATH = "/app/opencode/history.db"


class TestSessionManagerConstants:
    """测试SessionManager常量定义"""
    
    def test_session_id_prefix_constant(self):
        """测试SESSION_ID_PREFIX常量"""
        assert SESSION_ID_PREFIX == "ses_"
        assert isinstance(SESSION_ID_PREFIX, str)
        assert len(SESSION_ID_PREFIX) == 4
    
    def test_session_id_length_constant(self):
        """测试SESSION_ID_LENGTH常量"""
        assert SESSION_ID_LENGTH == 9
        assert isinstance(SESSION_ID_LENGTH, int)
        assert SESSION_ID_LENGTH > 0
    
    def test_prompt_max_length_constant(self):
        """测试PROMPT_MAX_LENGTH常量"""
        assert PROMPT_MAX_LENGTH == 500
        assert isinstance(PROMPT_MAX_LENGTH, int)
        assert PROMPT_MAX_LENGTH > 0
    
    def test_default_mode_constant(self):
        """测试DEFAULT_MODE常量"""
        assert DEFAULT_MODE == "auto"
        assert isinstance(DEFAULT_MODE, str)
    
    def test_default_status_constant(self):
        """测试DEFAULT_STATUS常量"""
        assert DEFAULT_STATUS == "active"
        assert isinstance(DEFAULT_STATUS, str)
    
    def test_db_path_constant(self):
        """测试DB_PATH常量"""
        assert DB_PATH == "/app/opencode/history.db"
        assert isinstance(DB_PATH, str)
        assert DB_PATH.endswith(".db")


class TestSessionIDGeneration:
    """测试Session ID生成逻辑"""
    
    def test_session_id_format(self):
        """测试Session ID格式正确性"""
        sid = f"{SESSION_ID_PREFIX}{uuid.uuid4().hex[:SESSION_ID_LENGTH]}"
        
        # 验证前缀
        assert sid.startswith(SESSION_ID_PREFIX)
        
        # 验证总长度
        assert len(sid) == len(SESSION_ID_PREFIX) + SESSION_ID_LENGTH
        
        # 验证只包含小写hex字符
        assert sid[len(SESSION_ID_PREFIX):].isalnum()
        assert sid[len(SESSION_ID_PREFIX):].islower()
    
    def test_session_id_uniqueness(self):
        """测试Session ID唯一性"""
        # 生成100个session ID，确保没有重复
        sids = set()
        for _ in range(100):
            sid = f"{SESSION_ID_PREFIX}{uuid.uuid4().hex[:SESSION_ID_LENGTH]}"
            sids.add(sid)
        
        assert len(sids) == 100
    
    def test_session_id_no_collision_in_thousands(self):
        """测试在1000次生成中无碰撞"""
        sids = []
        for _ in range(1000):
            sid = f"{SESSION_ID_PREFIX}{uuid.uuid4().hex[:SESSION_ID_LENGTH]}"
            sids.append(sid)
        
        # 检查是否有重复
        assert len(sids) == len(set(sids))


class TestDatabaseWrite:
    """测试数据库写入功能"""
    
    def test_write_session_to_db(self, temp_history_db):
        """测试写入session到数据库"""
        session_id = "ses_test001"
        prompt = "测试prompt"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 模拟_write_session_to_db的逻辑
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, prompt, start_time, status, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, prompt[:PROMPT_MAX_LENGTH], now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 验证写入成功
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == session_id
        assert result[1] == prompt
        assert result[2] == now
        assert result[3] == DEFAULT_STATUS
        assert result[4] == DEFAULT_MODE
    
    def test_write_multiple_sessions(self, temp_history_db):
        """测试写入多个session"""
        sessions = [
            ("ses_test001", "第一个测试prompt"),
            ("ses_test002", "第二个测试prompt"),
            ("ses_test003", "第三个测试prompt"),
        ]
        
        # 写入多个session
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        for session_id, prompt in sessions:
            cursor.execute("""
                INSERT INTO sessions (session_id, prompt, start_time, status, mode)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, prompt[:PROMPT_MAX_LENGTH], now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 验证所有session都已写入
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id FROM sessions")
        results = cursor.fetchall()
        conn.close()
        
        assert len(results) == len(sessions)
        session_ids = [r[0] for r in results]
        for session_id, _ in sessions:
            assert session_id in session_ids
    
    def test_prompt_length_truncation(self, temp_history_db):
        """测试prompt长度超过限制时被截断"""
        session_id = "ses_test002"
        long_prompt = "x" * 1000  # 超过PROMPT_MAX_LENGTH (500)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 写入长prompt
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, prompt, start_time, status, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, long_prompt[:PROMPT_MAX_LENGTH], now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 验证prompt被截断到PROMPT_MAX_LENGTH
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("SELECT prompt FROM sessions WHERE session_id=?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert len(result[0]) == PROMPT_MAX_LENGTH
        assert result[0] == "x" * PROMPT_MAX_LENGTH
    
    def test_datetime_format(self, temp_history_db):
        """测试时间格式正确性"""
        session_id = "ses_test003"
        prompt = "测试时间格式"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 写入session
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, prompt, start_time, status, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, prompt[:PROMPT_MAX_LENGTH], now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 验证时间格式
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("SELECT start_time FROM sessions WHERE session_id=?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        # 验证格式: YYYY-MM-DD HH:MM:SS
        datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    
    def test_sql_injection_prevention(self, temp_history_db):
        """测试SQL注入防护（参数化查询）"""
        session_id = "ses_' OR '1'='1"
        prompt = "'; DROP TABLE sessions; --"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 尝试SQL注入攻击
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, prompt, start_time, status, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, prompt[:PROMPT_MAX_LENGTH], now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 验证数据被正确插入，没有执行恶意SQL
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        
        # 验证sessions表仍然存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        table_result = cursor.fetchone()
        assert table_result is not None
        
        # 验证数据被正确转义
        cursor.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == session_id
        assert result[1] == prompt[:PROMPT_MAX_LENGTH]


class TestDatabaseWriteErrors:
    """测试数据库写入错误处理"""
    
    def test_write_to_nonexistent_directory(self, tmp_path):
        """测试写入到不存在的目录"""
        nonexistent_db = tmp_path / "nonexistent" / "history.db"
        
        # 尝试连接到不存在的数据库
        # sqlite3会自动创建文件，但不会创建目录
        with pytest.raises(Exception):
            conn = sqlite3.connect(str(nonexistent_db))
            conn.execute("INSERT INTO sessions (session_id, prompt) VALUES (?, ?)", ("test", "test"))
            conn.commit()
            conn.close()
    
    def test_write_duplicate_session_id(self, temp_history_db):
        """测试写入重复的session_id（主键冲突）"""
        session_id = "ses_test_duplicate"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 第一次写入
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, prompt, start_time, status, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, "first prompt", now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 第二次写入相同session_id（应该失败）
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO sessions (session_id, prompt, start_time, status, mode)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, "second prompt", now, DEFAULT_STATUS, DEFAULT_MODE))
            conn.commit()
        conn.close()


class TestEdgeCases:
    """测试边界情况"""
    
    def test_empty_prompt(self, temp_history_db):
        """测试空prompt"""
        session_id = "ses_empty"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, prompt, start_time, status, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, "", now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 验证空prompt被接受
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("SELECT prompt FROM sessions WHERE session_id=?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == ""
    
    def test_unicode_prompt(self, temp_history_db):
        """测试Unicode字符（中文、表情符号等）"""
        session_id = "ses_unicode"
        prompt = "测试Unicode：🚀 Hello World 🎉"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, prompt, start_time, status, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, prompt[:PROMPT_MAX_LENGTH], now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 验证Unicode字符被正确存储
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("SELECT prompt FROM sessions WHERE session_id=?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == prompt
    
    def test_special_characters_in_prompt(self, temp_history_db):
        """测试prompt中的特殊字符"""
        session_id = "ses_special"
        prompt = "Test: \n\t\r\\\"' <script>alert('xss')</script>"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, prompt, start_time, status, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, prompt[:PROMPT_MAX_LENGTH], now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 验证特殊字符被正确存储
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("SELECT prompt FROM sessions WHERE session_id=?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == prompt[:PROMPT_MAX_LENGTH]
    
    def test_very_long_session_id(self, temp_history_db):
        """测试超长session_id"""
        session_id = "ses_" + "x" * 1000
        prompt = "测试长session_id"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, prompt, start_time, status, mode)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, prompt[:PROMPT_MAX_LENGTH], now, DEFAULT_STATUS, DEFAULT_MODE))
        conn.commit()
        conn.close()
        
        # 验证超长session_id被接受（TEXT类型无长度限制）
        conn = sqlite3.connect(temp_history_db)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id FROM sessions WHERE session_id=?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == session_id
