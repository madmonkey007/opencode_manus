import sqlite3, json

db = sqlite3.connect('workspace/history.db')
db.row_factory = sqlite3.Row

# 所有表结构
for t in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    tname = t[0]
    cols = [c[1] for c in db.execute(f"PRAGMA table_info({tname})").fetchall()]
    print(f"TABLE {tname}: {cols}")

print()

# sessions
try:
    rows = db.execute("SELECT * FROM sessions ORDER BY rowid DESC LIMIT 5").fetchall()
    print("=== sessions (last 5) ===")
    for r in rows:
        print(dict(r))
except Exception as e:
    print(f"sessions error: {e}")

print()

# messages
try:
    rows = db.execute("SELECT * FROM messages ORDER BY rowid DESC LIMIT 10").fetchall()
    print("=== messages (last 10) ===")
    for r in rows:
        print(dict(r))
except Exception as e:
    print(f"messages error: {e}")

print()

# message_parts
try:
    rows = db.execute("SELECT part_id, message_id, part_type, substr(content_json,1,100) as c FROM message_parts ORDER BY rowid DESC LIMIT 10").fetchall()
    print("=== message_parts (last 10) ===")
    for r in rows:
        print(dict(r))
except Exception as e:
    print(f"message_parts error: {e}")

print()

# session_phases
try:
    rows = db.execute("SELECT * FROM session_phases ORDER BY id DESC LIMIT 10").fetchall()
    print("=== session_phases (last 10) ===")
    for r in rows:
        print(dict(r))
except Exception as e:
    print(f"session_phases error: {e}")
