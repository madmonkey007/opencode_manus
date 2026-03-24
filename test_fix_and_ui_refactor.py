#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenCode修复和UI重构测试报告
"""
import requests
from requests.auth import HTTPBasicAuth
import json
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("OpenCode修复和UI重构验证报告")
print("=" * 80)

# 测试配置
WEB_API = "http://127.0.0.1:8089"
CLI_API = "http://127.0.0.1:4096"
USERNAME = "opencode"
PASSWORD = "opencode-dev-2026"

# ========================================================================
# 第一部分：Basic认证修复验证
# ========================================================================
print("\n" + "=" * 80)
print("第一部分：Basic认证修复验证")
print("=" * 80)

tests_passed = 0
tests_total = 0

# 测试1: Web API可访问性
tests_total += 1
print("\n[测试1] Web API (8089端口) 可访问性")
try:
    resp = requests.get(f"{WEB_API}/")
    if resp.status_code == 200:
        print("  [PASS] Web API正常访问")
        tests_passed += 1
    else:
        print(f"  [FAIL] 状态码: {resp.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试2: 通过Web API创建session
tests_total += 1
print("\n[测试2] 通过Web API创建session")
try:
    resp = requests.post(f"{WEB_API}/opencode/session")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] Session创建成功: {data.get('id')}")
        print(f"        状态: {data.get('status')}")
        tests_passed += 1
    else:
        print(f"  [FAIL] 状态码: {resp.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试3: CLI API需要认证
tests_total += 1
print("\n[测试3] CLI API (4096端口) 需要认证")
try:
    resp = requests.post(f"{CLI_API}/session")
    if resp.status_code == 401:
        print("  [PASS] 正确返回401（需要认证）")
        tests_passed += 1
    else:
        print(f"  [FAIL] 状态码: {resp.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试4: 使用认证访问CLI API
tests_total += 1
print("\n[测试4] 使用认证访问CLI API")
try:
    resp = requests.post(
        f"{CLI_API}/session",
        auth=HTTPBasicAuth(USERNAME, PASSWORD)
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] Session创建成功: {data.get('id')}")
        tests_passed += 1
    else:
        print(f"  [FAIL] 状态码: {resp.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# ========================================================================
# 第二部分：UI重构验证
# ========================================================================
print("\n" + "=" * 80)
print("第二部分：UI重构验证")
print("=" * 80)

# 测试5: 检查HTML中的新元素
tests_total += 1
print("\n[测试5] 检查HTML中的新元素")
try:
    resp = requests.get(f"{WEB_API}/")
    html_content = resp.text

    checks = {
        "input-mode-selector": "输入框模式选择器",
        "api-web-btn": "Web API按钮",
        "api-cli-btn": "CLI API按钮"
    }

    all_found = True
    for element_id, element_name in checks.items():
        if element_id in html_content:
            print(f"  [OK] 找到: {element_name}")
        else:
            print(f"  [MISSING] 未找到: {element_name}")
            all_found = False

    if all_found:
        print("  [PASS] 所有UI元素都存在")
        tests_passed += 1
    else:
        print("  [FAIL] 部分UI元素缺失")

except Exception as e:
    print(f"  [ERROR] {e}")

# 测试6: 检查JavaScript文件
tests_total += 1
print("\n[测试6] 检查新的JavaScript文件")
try:
    resp = requests.get(f"{WEB_API}/static/ui-layout-refactor.js")
    if resp.status_code == 200:
        js_content = resp.text
        checks = {
            "initInputModeSelector": "模式选择器初始化",
            "initApiEndpointSelector": "API端点切换器初始化",
            "API_ENDPOINTS": "API端点配置",
            "_currentMode": "当前模式变量",
            "_currentApiEndpoint": "当前API端点变量"
        }

        all_found = True
        for check_str, check_name in checks.items():
            if check_str in js_content:
                print(f"  [OK] 找到: {check_name}")
            else:
                print(f"  [MISSING] 未找到: {check_name}")
                all_found = False

        if all_found:
            print("  [PASS] 所有JavaScript功能都存在")
            tests_passed += 1
        else:
            print("  [FAIL] 部分JavaScript功能缺失")
    else:
        print(f"  [FAIL] 状态码: {resp.status_code}")

except Exception as e:
    print(f"  [ERROR] {e}")

# ========================================================================
# 第三部分：功能验证
# ========================================================================
print("\n" + "=" * 80)
print("第三部分：功能验证")
print("=" * 80)

# 测试7: 创建Build模式会话
tests_total += 1
print("\n[测试7] 创建Build模式会话")
try:
    resp = requests.post(
        f"{WEB_API}/opencode/session",
        json={"prompt": "Test build mode", "mode": "build"}
    )
    if resp.status_code == 200:
        data = resp.json()
        mode = data.get('metadata', {}).get('mode')
        print(f"  [PASS] Session创建成功: {data.get('id')}")
        print(f"        模式: {mode}")
        tests_passed += 1
    else:
        print(f"  [FAIL] 状态码: {resp.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# ========================================================================
# 总结
# ========================================================================
print("\n" + "=" * 80)
print("测试总结")
print("=" * 80)
print(f"通过: {tests_passed}/{tests_total}")
print(f"成功率: {tests_passed/tests_total*100:.1f}%")

if tests_passed == tests_total:
    print("\n[SUCCESS] 所有测试通过！✓")
    print("\n修复和重构完成的功能:")
    print("  1. ✓ Basic认证配置 - FastAPI可连接到OpenCode Server CLI")
    print("  2. ✓ UI布局重构 - 模式选择器移到输入框左侧底部")
    print("  3. ✓ API端点切换 - Web/CLI按钮替代原来的Tab")
else:
    print("\n[WARNING] 部分测试失败，请检查配置")

print("=" * 80)
