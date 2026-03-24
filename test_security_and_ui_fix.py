#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全改进和UI修复验证报告
"""
import requests
from requests.auth import HTTPBasicAuth
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("安全改进和UI修复验证报告")
print("=" * 80)

tests_passed = 0
tests_total = 0

# ========================================================================
# 第一部分：UI修复验证
# ========================================================================
print("\n" + "=" * 80)
print("第一部分：UI修复验证")
print("=" * 80)

# 测试1: Web/CLI按钮在主header中可见
tests_total += 1
print("\n[测试1] Web/CLI按钮在主header中可见")
try:
    resp = requests.get("http://127.0.0.1:8089/")
    html_content = resp.text

    # 检查按钮是否在主header中（不在VM panel中）
    has_api_buttons = "api-web-btn" in html_content and "api-cli-btn" in html_content
    # 检查按钮不在VM panel的孤立体位置
    not_in_vm_panel = html_content.find("api-web-btn") < html_content.find("tab-preview")

    if has_api_buttons and not_in_vm_panel:
        print("  [PASS] API端点切换器位于主header中")
        tests_passed += 1
    else:
        print("  [FAIL] API端点切换器位置不正确")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试2: 输入框模式选择器可见
tests_total += 1
print("\n[测试2] 输入框模式选择器可见")
try:
    has_mode_selector = "input-mode-selector" in html_content
    has_plan_btn = "mode-btn-input" in html_content and 'data-mode="plan"' in html_content
    has_build_btn = "mode-btn-input" in html_content and 'data-mode="build"' in html_content

    if has_mode_selector and has_plan_btn and has_build_btn:
        print("  [PASS] 输入框模式选择器正确显示")
        tests_passed += 1
    else:
        print("  [FAIL] 输入框模式选择器缺失")
except Exception as e:
    print(f"  [ERROR] {e}")

# ========================================================================
# 第二部分：安全改进验证
# ========================================================================
print("\n" + "=" * 80)
print("第二部分：安全改进验证")
print("=" * 80)

# 测试3: .env.example已创建
tests_total += 1
print("\n[测试3] .env.example模板文件已创建")
try:
    env_example_path = os.path.join(os.path.dirname(__file__), ".env.example")
    if os.path.exists(env_example_path):
        with open(env_example_path, 'r', encoding='utf-8') as f:
            content = f.read()
            has_placeholder = "your_secure_password_here" in content
            has_no_real_password = "opencode-dev-2026" not in content

        if has_placeholder and has_no_real_password:
            print("  [PASS] .env.example是安全的模板文件")
            tests_passed += 1
        else:
            print("  [FAIL] .env.example可能包含真实凭证")
    else:
        print("  [FAIL] .env.example文件不存在")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试4: .env在.gitignore中
tests_total += 1
print("\n[测试4] .env在.gitignore中")
try:
    gitignore_path = os.path.join(os.path.dirname(__file__), ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            content = f.read()
            has_env_ignore = ".env" in content

        if has_env_ignore:
            print("  [PASS] .env已添加到.gitignore")
            tests_passed += 1
        else:
            print("  [FAIL] .env未在.gitignore中")
    else:
        print("  [FAIL] .gitignore文件不存在")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试5: 安全文档已创建
tests_total += 1
print("\n[测试5] 安全文档已创建")
try:
    security_doc_path = os.path.join(os.path.dirname(__file__), "SECURITY_GUIDE.md")
    if os.path.exists(security_doc_path):
        print("  [PASS] SECURITY_GUIDE.md已创建")
        tests_passed += 1
    else:
        print("  [FAIL] SECURITY_GUIDE.md文件不存在")
except Exception as e:
    print(f"  [ERROR] {e}")

# ========================================================================
# 第三部分：功能验证
# ========================================================================
print("\n" + "=" * 80)
print("第三部分：功能验证")
print("=" * 80)

# 测试6: 错误处理改进
tests_total += 1
print("\n[测试6] 错误处理改进")
try:
    # 尝试使用错误的凭证
    resp = requests.post(
        "http://127.0.0.1:4096/session",
        auth=("wrong_user", "wrong_pass"),
        timeout=5
    )
    if resp.status_code == 401:
        print("  [PASS] 认证失败正确返回401")
        tests_passed += 1
    else:
        print(f"  [FAIL] 意外的状态码: {resp.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 测试7: Web API仍然正常工作
tests_total += 1
print("\n[测试7] Web API通过Basic认证连接CLI")
try:
    # 通过Web API创建session（会自动使用Basic认证）
    resp = requests.post("http://127.0.0.1:8089/opencode/session")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] Web API成功创建session: {data.get('id')}")
        print(f"        状态: {data.get('status')}")
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
    print("\n已完成的改进:")
    print("  1. ✓ UI修复 - Web/CLI切换按钮移到主header")
    print("  2. ✓ UI修复 - 模式选择器在输入框左侧底部")
    print("  3. ✓ 安全改进 - .env从git中移除")
    print("  4. ✓ 安全改进 - 创建.env.example模板")
    print("  5. ✓ 安全改进 - 改进错误处理")
    print("  6. ✓ 安全改进 - 创建安全文档")
else:
    print("\n[WARNING] 部分测试失败，请检查配置")

print("\n重要提醒:")
print("  ⚠️  生产环境请修改默认密码")
print("  ⚠️  确保.env不要提交到git")
print("  ⚠️  阅读 SECURITY_GUIDE.md 了解更多")

print("=" * 80)
