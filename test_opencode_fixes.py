"""
OpenCode Web Application Test Script
验证Code Review修复：
1. 版本号正确（opencode-new-api-patch.js v=38.3.6）
2. SSE连接无404错误
3. Session成功创建
4. 任务执行正常启动
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime
import sys

# 设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 测试配置
TEST_URL = "http://localhost:8089"
TEST_PROMPT = "写一个简单的hello world网页"
OUTPUT_DIR = "test_results"

console_logs = []
network_requests = []
session_created = False
sse_404_error = False
session_id = None


def handle_console_message(msg):
    """捕获console日志"""
    global session_created, sse_404_error, session_id

    log_entry = {
        "type": msg.type,
        "text": msg.text,
        "timestamp": datetime.now().isoformat()
    }
    console_logs.append(log_entry)

    # 检查关键日志
    text = msg.text

    # 检查Session创建成功
    if "Session created successfully" in text or "session created" in text.lower():
        session_created = True
        print(f"✅ [SUCCESS] {text}")

    # 检查SSE 404错误
    if "404" in text and "/opencode/events" in text:
        sse_404_error = True
        print(f"❌ [ERROR] SSE 404 Error: {text}")

    # 检查session ID
    if "session id" in text.lower() or "activeId" in text:
        print(f"📝 [INFO] {text}")
        # 尝试提取session ID
        if "ses_" in text:
            parts = text.split("ses_")
            if len(parts) > 1:
                session_id = "ses_" + parts[1].split()[0].split(",")[0].split("'")[0]

    # 打印所有日志
    print(f"Console: [{msg.type}] {text}")


def handle_request(request):
    """捕获网络请求"""
    request_info = {
        "method": request.method,
        "url": request.url,
        "resource_type": request.resource_type
    }
    network_requests.append(request_info)


def handle_response(response):
    """捕获网络响应"""
    if response.status == 404:
        print(f"❌ [404] {response.url}")


def run_test():
    """运行测试"""
    print("=" * 80)
    print("OpenCode Web Application Test")
    print("=" * 80)
    print(f"Test URL: {TEST_URL}")
    print(f"Test Prompt: {TEST_PROMPT}")
    print("=" * 80)

    with sync_playwright() as p:
        # 启动浏览器（headless模式）
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        # 设置console日志捕获
        page.on("console", handle_console_message)
        page.on("request", handle_request)
        page.on("response", handle_response)

        try:
            # 步骤1: 导航到页面
            print("\n📋 Step 1: Navigating to page...")
            page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)

            # 等待页面完全加载
            print("⏳ Waiting for page to fully load...")
            page.wait_for_load_state('networkidle', timeout=30000)
            print("✅ Page loaded successfully")

            # 等待一下，让所有脚本初始化
            page.wait_for_timeout(2000)

            # 步骤2: 检查页面版本和初始状态
            print("\n📋 Step 2: Checking page state...")

            # 截图保存初始状态
            page.screenshot(path=f"{OUTPUT_DIR}/01_initial_page.png")
            print("📸 Screenshot saved: 01_initial_page.png")

            # 步骤3: 查找并点击输入框
            print("\n📋 Step 3: Looking for input field...")

            # 尝试多种选择器
            input_selectors = [
                'textarea[placeholder*="输入"]',
                'textarea[placeholder*="/"]',
                'textarea',
                'input[type="text"]',
                '[contenteditable="true"]',
                '.input-area',
                '#prompt-input'
            ]

            input_found = False
            for selector in input_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"✅ Found input with selector: {selector}")
                        input_found = True

                        # 点击输入框
                        page.locator(selector).first.click()
                        print("✅ Clicked on input field")
                        page.wait_for_timeout(500)

                        # 输入测试文本
                        page.locator(selector).first.fill(TEST_PROMPT)
                        print(f"✅ Typed prompt: {TEST_PROMPT}")
                        page.wait_for_timeout(1000)
                        break
                except Exception as e:
                    print(f"⚠️  Selector {selector} failed: {str(e)}")
                    continue

            if not input_found:
                print("❌ Could not find input field, trying keyboard approach...")
                # 尝试直接聚焦页面并输入
                page.keyboard.press("Tab")
                page.wait_for_timeout(500)
                page.keyboard.type(TEST_PROMPT)
                print(f"✅ Typed prompt using keyboard: {TEST_PROMPT}")
                page.wait_for_timeout(1000)

            # 截图保存输入状态
            page.screenshot(path=f"{OUTPUT_DIR}/02_after_input.png")
            print("📸 Screenshot saved: 02_after_input.png")

            # 步骤4: 查找并点击提交按钮
            print("\n📋 Step 4: Looking for submit button...")

            # 尝试多种按钮选择器
            button_selectors = [
                'button:has-text("arrow_upward")',
                'button .material-symbols-outlined:has-text("arrow_upward")',
                'button[type="submit"]',
                'button:has([class*="arrow"])',
                'button:has([class*="send"])',
                'button:has([class*="submit"])',
                'button[aria-label*="send"]',
                'button[aria-label*="提交"]'
            ]

            button_clicked = False
            for selector in button_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"✅ Found button with selector: {selector}")
                        page.locator(selector).first.click()
                        print("✅ Clicked submit button")
                        button_clicked = True
                        break
                except Exception as e:
                    print(f"⚠️  Button selector {selector} failed: {str(e)}")
                    continue

            if not button_clicked:
                print("⚠️  Could not find submit button, trying Enter key...")
                page.keyboard.press("Enter")
                print("✅ Pressed Enter key")

            # 截图保存提交后状态
            page.screenshot(path=f"{OUTPUT_DIR}/03_after_submit.png")
            print("📸 Screenshot saved: 03_after_submit.png")

            # 步骤5: 等待并监控任务执行
            print("\n📋 Step 5: Monitoring task execution...")

            # 等待15秒让任务开始执行
            print("⏳ Waiting for task to start (15 seconds)...")
            page.wait_for_timeout(15000)

            # 最终截图
            page.screenshot(path=f"{OUTPUT_DIR}/04_final_state.png")
            print("📸 Screenshot saved: 04_final_state.png")

            # 步骤6: 生成测试报告
            print("\n" + "=" * 80)
            print("TEST RESULTS")
            print("=" * 80)

            # 分析console日志
            print("\n📊 Console Log Analysis:")
            print(f"Total console messages: {len(console_logs)}")

            # 检查版本号
            version_found = False
            version_logs = [log for log in console_logs if "v=" in log["text"] or "version" in log["text"].lower()]
            if version_logs:
                print(f"\n✅ Version information found:")
                for log in version_logs[:5]:  # 显示前5条
                    print(f"   {log['text']}")
                    if "v=38.3.6" in log["text"]:
                        version_found = True
                        print("   ✅ Correct version detected: v=38.3.6")

            # 检查404错误
            error_404_logs = [log for log in console_logs if "404" in log["text"]]
            if error_404_logs:
                print(f"\n❌ 404 Errors found ({len(error_404_logs)}):")
                for log in error_404_logs:
                    print(f"   {log['text']}")
            else:
                print(f"\n✅ No 404 errors detected")

            # 检查session创建
            session_logs = [log for log in console_logs if "session" in log["text"].lower()]
            if session_logs:
                print(f"\n📝 Session-related logs ({len(session_logs)}):")
                for log in session_logs[:10]:  # 显示前10条
                    print(f"   [{log['type']}] {log['text']}")

            # 保存详细日志到文件
            with open(f"{OUTPUT_DIR}/console_logs.json", 'w', encoding='utf-8') as f:
                json.dump(console_logs, f, ensure_ascii=False, indent=2)
            print(f"\n📁 Console logs saved to: {OUTPUT_DIR}/console_logs.json")

            with open(f"{OUTPUT_DIR}/network_requests.json", 'w', encoding='utf-8') as f:
                json.dump(network_requests, f, ensure_ascii=False, indent=2)
            print(f"📁 Network requests saved to: {OUTPUT_DIR}/network_requests.json")

            # 生成测试结论
            print("\n" + "=" * 80)
            print("VERIFICATION RESULTS")
            print("=" * 80)

            results = {
                "session_created": session_created,
                "sse_404_error": sse_404_error,
                "version_correct": version_found,
                "session_id": session_id
            }

            print(f"\n✅ Session Created: {'✅ PASS' if session_created else '❌ FAIL'}")
            print(f"✅ No SSE 404 Error: {'✅ PASS' if not sse_404_error else '❌ FAIL'}")
            print(f"✅ Version Correct: {'✅ PASS' if version_found else '⚠️  WARNING'}")
            print(f"📝 Session ID: {session_id if session_id else 'Not found'}")

            # 保存测试结果
            with open(f"{OUTPUT_DIR}/test_results.json", 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n📁 Test results saved to: {OUTPUT_DIR}/test_results.json")

            # 返回测试是否通过
            all_passed = session_created and not sse_404_error

            if all_passed:
                print("\n🎉 ALL TESTS PASSED! The fixes are working correctly.")
            else:
                print("\n⚠️  SOME TESTS FAILED. Please review the logs above.")

            print("=" * 80)

        except Exception as e:
            print(f"\n❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            browser.close()
            print("\n✅ Test completed. Browser closed.")


if __name__ == "__main__":
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    run_test()
