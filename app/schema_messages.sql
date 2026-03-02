-- ================================================================
-- Messages and Parts Schema
-- 用于持久化消息和工具调用Part数据
-- 解决刷新页面后工具调用记录丢失的问题
-- ================================================================

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata_json TEXT,   -- JSON格式存储metadata
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- 消息部分表（工具调用、文本等）
CREATE TABLE IF NOT EXISTS message_parts (
    part_id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    part_type TEXT NOT NULL,  -- 'text', 'tool', 'step-start', 'step-finish', 'thought'
    content_json TEXT,        -- JSON格式存储PartContent
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_parts_message ON message_parts(message_id);
CREATE INDEX IF NOT EXISTS idx_parts_type ON message_parts(part_type);
