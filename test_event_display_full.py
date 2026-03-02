#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的前端事件显示测试
使用Playwright验证所有事件正确显示
"""
from playwright.sync_api import sync_playwright
import time
import json

def test_complete_event_display():
    """测试完整的事件显示流程"""
    print("=" * 70)
    print("前端事件显示完整测试")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})

        # 收集控制台日志
        console_logs = []
        def handle_console(msg):
            log_entry = {
                'type': msg.type,
                'text': msg.text,
                'timestamp': time.time()
            }
            console_logs.append(log_entry)

            # 打印重要日志
            if 'Timeline' in msg.text or 'Event' in msg.text or 'History' in msg.text:
                print(f"  [Console] {msg.text}")

        page.on('console', handle_console)

        try:
            # ========== 步骤1: 访问应用 ==========
            print("\n[步骤1] 访问应用...")
            page.goto('http://localhost:8089')
            page.wait_for_load_state('networkidle')
            time.sleep(2)

            page.screenshot(path='D:/manus/opencode/test_screenshots/event_test_01_home.png')
            print("  首页已加载")

            # ========== 步骤2: 创建新任务 ==========
            print("\n[步骤2] 创建新任务...")

            # 点击新任务按钮
            new_task_btn = page.locator('button:has-text("new"), button:has-text("task"), button:has-text("create")').first
            if new_task_btn.count() > 0:
                new_task_btn.click()
                time.sleep(1)
            else:
                # 直接输入prompt
                print("  查找输入框...")

            # 查找输入框
            textarea = page.locator('textarea, [contenteditable="true"]').first
            if textarea.count() > 0:
                print("  找到输入框，输入任务...")
                textarea.fill('创建一个Python文件hello.py，内容是print("Hello World")，然后执行它')
                time.sleep(1)

                # 查找发送/提交按钮
                submit_btn = page.locator('button:has-text("send"), button:has-text("submit"), button[type="submit"]').first
                if submit_btn.count() > 0:
                    submit_btn.click()
                    print("  任务已提交")
                else:
                    # 尝试按Enter
                    textarea.press('Enter')
                    print("  任务已提交（Enter键）")
            else:
                print("  未找到输入框")

            page.screenshot(path='D:/manus/opencode/test_screenshots/event_test_02_task_submitted.png')

            # ========== 步骤3: 等待任务执行并观察事件 ==========
            print("\n[步骤3] 等待任务执行（30秒）...")
            print("  观察事件显示...")

            # 等待30秒让任务执行
            for i in range(30):
                time.sleep(1)
                if (i + 1) % 5 == 0:
                    print(f"  已等待 {i + 1} 秒...")

                    # 检查页面上的事件
                    page_text = page.locator('body').text_content() or ''

                    events_found = {
                        'write': 'write' in page_text.lower(),
                        'bash': 'bash' in page_text.lower(),
                        'read': 'read' in page_text.lower(),
                        'hello.py': 'hello.py' in page_text,
                    }

                    print(f"    当前页面事件: {events_found}")

            page.screenshot(path='D:/manus/opencode/test_screenshots/event_test_03_execution.png', full_page=True)
            print("  执行阶段完成")

            # ========== 步骤4: 刷新浏览器 ==========
            print("\n[步骤4] 刷新浏览器...")
            page.reload(wait_until='networkidle')
            time.sleep(3)

            page.screenshot(path='D:/manus/opencode/test_screenshots/event_test_04_after_refresh.png')
            print("  浏览器已刷新")

            # ========== 步骤5: 点击历史记录 ==========
            print("\n[步骤5] 点击历史记录...")

            # 查找历史按钮
            history_btn = page.locator('button:has-text("history")').first
            if history_btn.count() > 0:
                history_btn.click()
                time.sleep(2)
                print("  已点击历史按钮")

                page.screenshot(path='D:/manus/opencode/test_screenshots/event_test_05_history_list.png')

                # 点击第一个会话
                session_item = page.locator('.session-item, [data-session-id]').first
                if session_item.count() > 0:
                    session_item.click()
                    time.sleep(3)
                    print("  已点击第一个历史会话")

                    page.screenshot(path='D:/manus/opencode/test_screenshots/event_test_06_session_loaded.png', full_page=True)
                else:
                    print("  未找到会话项")
            else:
                print("  未找到历史按钮")

            # ========== 步骤6: 验证历史记录中的事件 ==========
            print("\n[步骤6] 验证历史记录中的事件...")

            page_text = page.locator('body').text_content() or ''

            # 检查关键内容
            checks = {
                'write事件': 'write' in page_text.lower(),
                'bash事件': 'bash' in page_text.lower(),
                'hello.py文件': 'hello.py' in page_text.lower(),
                'print命令': 'print' in page_text.lower(),
            }

            print("\n  事件检查结果:")
            all_ok = True
            for check_name, result in checks.items():
                status = "✓" if result else "✗"
                print(f"    {status} {check_name}: {result}")
                if not result:
                    all_ok = False

            # ========== 步骤7: 检查控制台日志 ==========
            print("\n[步骤7] 分析控制台日志...")

            timeline_logs = [log for log in console_logs if 'Timeline' in log['text']]
            event_logs = [log for log in console_logs if 'Event' in log['text']]
            history_logs = [log for log in console_logs if 'History' in log['text']]

            print(f"  Timeline相关日志: {len(timeline_logs)} 条")
            print(f"  Event相关日志: {len(event_logs)} 条")
            print(f"  History相关日志: {len(history_logs)} 条")

            # 显示最近的关键日志
            print("\n  最近的关键日志:")
            for log in console_logs[-20:]:
                if any(keyword in log['text'] for keyword in ['Timeline', 'Event', 'History', 'Loaded', 'Rendering']):
                    print(f"    {log['text']}")

            # ========== 步骤8: 保存详细报告 ==========
            print("\n[步骤8] 生成测试报告...")

            report = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'url': 'http://localhost:8089',
                'steps_executed': 8,
                'event_checks': checks,
                'all_events_ok': all_ok,
                'console_logs': {
                    'timeline_count': len(timeline_logs),
                    'event_count': len(event_logs),
                    'history_count': len(history_logs),
                },
                'recent_logs': console_logs[-50:]
            }

            with open('D:/manus/opencode/test_screenshots/event_display_report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            print("  ✓ 报告已保存")

            # ========== 总结 ==========
            print("\n" + "=" * 70)
            print("测试总结")
            print("=" * 70)

            print(f"\n事件显示验证:")
            for check_name, result in checks.items():
                status = "✓ PASS" if result else "✗ FAIL"
                print(f"  {status}: {check_name}")

            if all_ok:
                print("\n✓ 所有事件正确显示！")
            else:
                print("\n✗ 部分事件未显示，需要检查")

            print(f"\n控制台日志:")
            print(f"  Timeline: {len(timeline_logs)} 条")
            print(f"  Events: {len(event_logs)} 条")
            print(f"  History: {len(history_logs)} 条")

            print("\n截图已保存:")
            print("  1. event_test_01_home.png")
            print("  2. event_test_02_task_submitted.png")
            print("  3. event_test_03_execution.png (full page)")
            print("  4. event_test_04_after_refresh.png")
            print("  5. event_test_05_history_list.png")
            print("  6. event_test_06_session_loaded.png (full page)")
            print("  7. event_display_report.json")

            print("\n" + "=" * 70)

        except Exception as e:
            print(f"\n✗ 测试过程出错: {e}")
            import traceback
            traceback.print_exc()

            try:
                page.screenshot(path='D:/manus/opencode/test_screenshots/event_test_error.png', full_page=True)
                print("  ✓ 已保存错误截图")
            except:
                pass

        finally:
            print("\n浏览器将在30秒后关闭...")
            time.sleep(30)
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('D:/manus/opencode/test_screenshots', exist_ok=True)
    test_complete_event_display()
