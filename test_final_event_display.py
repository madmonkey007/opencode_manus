#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final Event Display Test - Complete validation
"""
from playwright.sync_api import sync_playwright
import time

def final_test():
    """Final complete test"""
    print("=" * 70)
    print("FINAL EVENT DISPLAY TEST")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1500)
        context = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = context.new_page()

        # 收集日志
        logs = []
        page.on('console', lambda msg: logs.append(msg.text))

        try:
            # Step 1: Open application
            print("\n[1/7] Opening application...")
            page.goto('http://localhost:8089')
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            page.screenshot(path='D:/manus/opencode/test_screenshots/final_01_open.png')
            print("  Opened")

            # Step 2: Create new task
            print("\n[2/7] Creating new task...")
            textarea = page.locator('textarea').first
            if textarea.count() > 0:
                textarea.fill('Write hello.py with print("Hello World") then run it')
                time.sleep(1)

                submit = page.locator('button[type="submit"], button:has-text("send")').first
                if submit.count() > 0:
                    submit.click()
                else:
                    textarea.press('Enter')

                print("  Task submitted")

            page.screenshot(path='D:/manus/opencode/test_screenshots/final_02_submitted.png')

            # Step 3: Wait for execution
            print("\n[3/7] Waiting for execution (40s)...")
            for i in range(40):
                time.sleep(1)
                if (i+1) % 10 == 0:
                    # Check events on page
                    text = page.locator('body').text_content() or ''
                    events = ['write', 'bash', 'hello.py']
                    found = [e for e in events if e in text.lower()]
                    print(f"  [{i+1}s] Events found: {found}")

            page.screenshot(path='D:/manus/opencode/test_screenshots/final_03_executed.png', full_page=True)
            print("  Execution complete")

            # Step 4: Refresh
            print("\n[4/7] Refreshing browser...")
            page.reload(wait_until='networkidle')
            time.sleep(3)
            page.screenshot(path='D:/manus/opencode/test_screenshots/final_04_refreshed.png')
            print("  Refreshed")

            # Step 5: Click history
            print("\n[5/7] Opening history...")
            history_btn = page.locator('button:has-text("history")').first
            if history_btn.count() > 0:
                history_btn.click()
                time.sleep(2)
                print("  History opened")

            page.screenshot(path='D:/manus/opencode/test_screenshots/final_05_history.png')

            # Step 6: Click session
            print("\n[6/7] Loading session...")
            session = page.locator('[data-session-id], .session-item, li').first
            if session.count() > 0:
                session.click()
                time.sleep(5)  # Wait for timeline loading
                print("  Session loaded")

            page.screenshot(path='D:/manus/opencode/test_screenshots/final_06_session.png', full_page=True)

            # Step 7: Verify
            print("\n[7/7] Verifying events...")
            page_text = page.locator('body').text_content() or ''

            checks = {
                'write event': 'write' in page_text.lower(),
                'bash event': 'bash' in page_text.lower(),
                'hello.py file': 'hello.py' in page_text.lower(),
                'Timeline logs': any('Timeline' in log for log in logs),
                'History logs': any('History' in log for log in logs),
            }

            print("\n  Verification:")
            all_ok = True
            for name, result in checks.items():
                status = "PASS" if result else "FAIL"
                print(f"    [{status}] {name}")
                if not result:
                    all_ok = False

            # Console log summary
            print(f"\n  Console logs: {len(logs)} total")
            timeline_logs = [l for l in logs if 'Timeline' in l]
            history_logs = [l for l in logs if 'History' in l]
            print(f"    Timeline: {len(timeline_logs)}")
            print(f"    History: {len(history_logs)}")

            print("\n" + "=" * 70)
            if all_ok:
                print("RESULT: ALL CHECKS PASS")
            else:
                print("RESULT: SOME CHECKS FAILED")
            print("=" * 70)

            print("\nScreenshots:")
            print("  1. final_01_open.png")
            print("  2. final_02_submitted.png")
            print("  3. final_03_executed.png (full)")
            print("  4. final_04_refreshed.png")
            print("  5. final_05_history.png")
            print("  6. final_06_session.png (full)")

            print("\nKeeping browser open for 30 seconds...")
            time.sleep(30)

        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path='D:/manus/opencode/test_screenshots/final_error.png')

        finally:
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('D:/manus/opencode/test_screenshots', exist_ok=True)
    final_test()
