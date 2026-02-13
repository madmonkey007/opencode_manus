-- ================================================================
-- OpenCode History Tracking Database Schema
-- 实时预览与历史追踪功能 - 数据库表结构
-- ================================================================

-- ================================================================
-- 会话表 (sessions)
-- ================================================================
-- 存储所有用户会话的基本信息
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,              -- 会话 ID (UUID)
    prompt TEXT NOT NULL,              -- 用户输入提示
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'running',     -- running, completed, error
    workspace_path TEXT                -- 工作空间路径
);

-- ================================================================
-- 执行步骤表 (steps)
-- ================================================================
-- 记录每个工具执行的步骤
CREATE TABLE IF NOT EXISTS steps (
    step_id TEXT PRIMARY KEY,          -- 步骤 ID (UUID)
    session_id TEXT NOT NULL,          -- 关联会话
    sequence_number INTEGER NOT NULL,  -- 执行顺序
    phase_id TEXT,                     -- 所属阶段
    action_type TEXT NOT NULL,         -- write, edit, bash, read, grep
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 操作上下文
    file_path TEXT,                    -- 文件路径 (文件操作)
    command TEXT,                      -- Shell 命令 (bash 操作)
    brief TEXT,                        -- 简短描述

    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- ================================================================
-- 文件内容表 (file_snapshots)
-- ================================================================
-- 存储文件内容的快照信息
CREATE TABLE IF NOT EXISTS file_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    step_id TEXT NOT NULL,             -- 关联步骤
    file_path TEXT NOT NULL,           -- 文件路径
    content_hash TEXT,                 -- 内容哈希 (SHA256)
    content_size INTEGER,              -- 内容大小
    operation_type TEXT NOT NULL,      -- created, modified, deleted

    FOREIGN KEY (step_id) REFERENCES steps(step_id) ON DELETE CASCADE,
    UNIQUE(step_id, file_path)
);

-- ================================================================
-- 实时增量表 (live_deltas)
-- ================================================================
-- 存储打字机效果的增量数据
CREATE TABLE IF NOT EXISTS live_deltas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    step_id TEXT NOT NULL,             -- 关联步骤
    delta_type TEXT NOT NULL,          -- insert, delete, replace
    position INTEGER,                  -- 操作位置
    content TEXT,                      -- 增量内容
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (step_id) REFERENCES steps(step_id) ON DELETE CASCADE
);

-- ================================================================
-- 索引优化
-- ================================================================
-- 加速按会话查询步骤
CREATE INDEX IF NOT EXISTS idx_steps_session ON steps(session_id);

-- 加速按会话和顺序查询步骤
CREATE INDEX IF NOT EXISTS idx_steps_sequence ON steps(session_id, sequence_number);

-- 加速按步骤查询文件快照
CREATE INDEX IF NOT EXISTS idx_files_step ON file_snapshots(step_id);

-- 加速按文件路径查询快照
CREATE INDEX IF NOT EXISTS idx_files_path ON file_snapshots(file_path);

-- 加速按步骤查询增量
CREATE INDEX IF NOT EXISTS idx_deltas_step ON live_deltas(step_id);
