import asyncio
import os
import sys
import json
import sqlite3
import shutil
from pathlib import Path

# 将项目根目录添加到 python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.history_service import HistoryService


async def test_history_persistence():
    # 使用测试数据库和工作区
    test_dir = Path("d:/manus/opencode/tests/temp_test_history")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    db_path = test_dir / "test_history.db"
    workspace_base = test_dir / "workspace"
    workspace_base.mkdir()

    service = HistoryService()
    service.db_path = str(db_path)
    service.workspace_base = workspace_base

    # 初始化数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS steps (step_id TEXT PRIMARY KEY, session_id TEXT, timestamp TEXT)"
    )
    cursor.execute(
        "INSERT INTO steps (step_id, session_id, timestamp) VALUES (?, ?, ?)",
        ("step_1", "ses_test", "2024-01-01T00:00:00"),
    )
    conn.commit()
    conn.close()

    # 测试保存
    step_id = "step_1"
    file_path = "test.txt"
    content_hash = "abc123hash"
    content = "Hello History Persistence!"

    print(f"Testing save_content_to_json for step_id: {step_id}")
    await service._save_content_to_json(step_id, file_path, content_hash, content)

    # 检查文件是否存在
    save_path = workspace_base / "ses_test" / ".history" / f"file_{content_hash}.json"
    assert save_path.exists(), f"Snapshot file {save_path} should exist"

    with open(save_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["content"] == content
        print(f"File content verified: {data['content']}")

    # 测试加载
    print("Testing load_content_from_json...")
    loaded_content = await service._load_content_from_json(
        "ses_test", file_path, content_hash
    )
    assert loaded_content == content
    print(f"Loaded content verified: {loaded_content}")

    print("Test History Persistence: PASSED")

    # 清理
    # shutil.rmtree(test_dir)


if __name__ == "__main__":
    asyncio.run(test_history_persistence())
