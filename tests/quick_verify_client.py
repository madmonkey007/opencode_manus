# -*- coding: utf-8 -*-
"""OpenCode Client 导入验证"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("Testing OpenCode Client imports...")

try:
    from app.opencode_client import OpenCodeClient, execute_opencode_message, map_tool_to_type
    print("[OK] OpenCodeClient imported")
except Exception as e:
    print(f"[FAIL] OpenCodeClient import: {e}")
    sys.exit(1)

try:
    from app.api import router, session_manager, event_stream_manager
    print("[OK] API modules imported")
except Exception as e:
    print(f"[FAIL] API import: {e}")
    sys.exit(1)

try:
    workspace_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../workspace"))
    client = OpenCodeClient(workspace_base)
    print(f"[OK] Client initialized: workspace={workspace_base}")
except Exception as e:
    print(f"[FAIL] Client init: {e}")
    sys.exit(1)

# Test tool mapping
tests = [
    ("read", "read"),
    ("write", "write"),
    ("bash", "bash"),
    ("browser_click", "browser"),
]
all_passed = True
for tool, expected in tests:
    result = map_tool_to_type(tool)
    if result == expected:
        print(f"[OK] {tool} -> {result}")
    else:
        print(f"[FAIL] {tool} -> {result} (expected {expected})")
        all_passed = False

if all_passed:
    print("\n[SUCCESS] All imports and basic tests passed!")
else:
    print("\n[PARTIAL] Some tests failed")
    sys.exit(1)
