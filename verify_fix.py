#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Basic认证修复是否生效
"""
import requests
from requests.auth import HTTPBasicAuth
import json
import sys

# 设置输出编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("OpenCode Server Basic Authentication Fix Verification")
print("=" * 60)

# 测试配置
BASE_URL_WEB = "http://127.0.0.1:8089"
BASE_URL_SERVER = "http://127.0.0.1:4096"
USERNAME = "opencode"
PASSWORD = "opencode-dev-2026"

# 测试1: 直接访问OpenCode Server（无认证）
print("\nTest 1: Access OpenCode Server CLI (port 4096) - No Auth")
try:
    resp = requests.post(f"{BASE_URL_SERVER}/session")
    if resp.status_code == 401:
        print("[OK] Correctly returned 401 Unauthorized (auth required)")
    else:
        print(f"[FAIL] Unexpected status code: {resp.status_code}")
except Exception as e:
    print(f"[ERROR] {e}")

# 测试2: 使用Basic认证访问OpenCode Server
print("\nTest 2: Access OpenCode Server CLI (port 4096) - With Basic Auth")
try:
    resp = requests.post(
        f"{BASE_URL_SERVER}/session",
        auth=HTTPBasicAuth(USERNAME, PASSWORD)
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"[OK] Successfully created session: {data.get('id')}")
    else:
        print(f"[FAIL] Status code: {resp.status_code}")
except Exception as e:
    print(f"[ERROR] {e}")

# 测试3: 通过FastAPI创建session
print("\nTest 3: Create session via FastAPI Web (port 8089)")
try:
    resp = requests.post(f"{BASE_URL_WEB}/opencode/session")
    if resp.status_code == 200:
        data = resp.json()
        print(f"[OK] Successfully created session: {data.get('id')}")
        print(f"      Status: {data.get('status')}")
    else:
        print(f"[FAIL] Status code: {resp.status_code}")
        print(f"      Response: {resp.text[:200]}")
except Exception as e:
    print(f"[ERROR] {e}")

# 测试4: 检查前端是否可访问
print("\nTest 4: Access frontend page")
try:
    resp = requests.get(BASE_URL_WEB)
    if resp.status_code == 200 and "html" in resp.text.lower():
        print("[OK] Frontend page accessible")
    else:
        print(f"[FAIL] Status code: {resp.status_code}")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "=" * 60)
print("Verification Complete!")
print("=" * 60)
