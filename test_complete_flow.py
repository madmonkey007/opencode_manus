#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试流程 - 创建任务、验证事件、检查文件、刷新后验证历史记录
"""
from playwright.sync_api import sync_playwright
import time
import os

def complete_test():
    """完整测试流程"""
    print("=" * 70)
    print("完整测试流程 - 开始")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context(viewport={'width': 1600, 'height': 900})
        page = context.new_page()

        # 收集所有日志
        all_logs = []
        def log_handler(msg):
            all_logs.append({
                'type': msg.type,
                'text': msg.text,
                'time': time.strftime('%H:%M:%S')
            })
        page.on('console', log_handler)

        try:
            # ========== 第一步：访问应用 ==========
            print("\n[第一步] 访问应用...")
            page.goto('http://localhost:8089')
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            page.screenshot(path='D:/manus/opencode/test_screenshots/complete_01_home.png')
            print("  ✓ 应用已打开")

            # ========== 第二步：创建第一个任务 ==========
            print("\n[第二步] 创建第一个任务...")

            # 查找输入框
            textarea = page.locator('textarea').first
            if textarea.count() == 0:
                textarea = page.locator('[contenteditable="true"]').first

            if textarea.count() > 0:
                print("  - 找到输入框")
                textarea.fill('创建文件hello.py，内容是print("Hello from task 1")')
                time.sleep(1)

                # 提交
                submit_btn = page.locator('button[type="submit"], button:has-text("send"), button:has-text("submit")').first
                if submit_btn.count() > 0:
                    submit_btn.click()
                    print("  - 任务1已提交")
                else:
                    textarea.press('Enter')
                    print("  - 任务1已提交（Enter键）")

                # 等待执行
                print("  - 等待执行（20秒）...")
                time.sleep(20)

                page.screenshot(path='D:/manus/opencode/test_screenshots/complete_02_task1_executed.png', full_page=True)

                # 检查页面上的事件
                page_text = page.locator('body').text_content() or ''
                task1_events = {
                    'write': 'write' in page_text.lower(),
                    'hello.py': 'hello.py' in page_text.lower(),
                    'print': 'print' in page_text.lower(),
                }
                print(f"  - 任务1事件: {task1_events}")

            # ========== 第三步：创建第二个任务 ==========
            print("\n[第三步] 创建第二个任务...")

            if textarea.count() > 0:
                textarea.fill('创建文件world.py，内容是print("World from task 2")，然后执行它')
                time.sleep(1)

                if submit_btn.count() > 0:
                    submit_btn.click()
                    print("  - 任务2已提交")
                else:
                    textarea.press('Enter')
                    print("  - 任务2已提交（Enter键）")

                print("  - 等待执行（20秒）...")
                time.sleep(20)

                page.screenshot(path='D:/manus/opencode/test_screenshots/complete_03_task2_executed.png', full_page=True)

                # 检查页面
                page_text = page.locator('body').text_content() or ''
                task2_events = {
                    'write': 'write' in page_text.lower(),
                    'world.py': 'world.py' in page_text.lower(),
                    'bash': 'bash' in page_text.lower(),
                }
                print(f"  - 任务2事件: {task2_events}")

            # ========== 第四步：检查文件是否真的生成 ==========
            print("\n[第四步] 检查文件是否真的生成...")

            # 检查工作目录
            workspace_dir = 'D:/manus/opencode/_temp_workspace'
            if os.path.exists(workspace_dir):
                # 列出所有Python文件
                python_files = []
                for root, dirs, files in os.walk(workspace_dir):
                    for file in files:
                        if file.endswith('.py'):
                            filepath = os.path.join(root, file)
                            python_files.append(filepath)

                print(f"  - 找到 {len(python_files)} 个Python文件:")
                for f in python_files[:10]:
                    size = os.path.getsize(f) if os.path.exists(f) else 0
                    print(f"    * {os.path.basename(f)} ({size} bytes)")

                    # 读取内容验证
                    if size > 0 and size < 10000:
                        try:
                            with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                                content = file.read()
                                if 'print' in content:
                                    print(f"      内容: {content.strip()[:100]}")
                        except:
                            pass

                # 检查特定文件
                hello_found = any('hello.py' in f for f in python_files)
                world_found = any('world.py' in f for f in python_files)

                print(f"\n  ✓ 文件生成验证:")
                print(f"    - hello.py: {'✓ 存在' if hello_found else '✗ 不存在'}")
                print(f"    - world.py: {'✓ 存在' if world_found else '✗ 不存在'}")

            else:
                print(f"  ⚠ 工作目录不存在: {workspace_dir}")

            # ========== 第五步：刷新浏览器 ==========
            print("\n[第五步] 刷新浏览器...")
            page.reload(wait_until='networkidle')
            time.sleep(3)
            page.screenshot(path='D:/manus/opencode/test_screenshots/complete_04_after_refresh.png')
            print("  ✓ 浏览器已刷新")

            # ========== 第六步：点击历史记录 ==========
            print("\n[第六步] 点击历史记录...")

            # 查找历史按钮
            history_btn = page.locator('button:has-text("history"), button:has-text("历史")').first
            if history_btn.count() > 0:
                print("  - 找到历史按钮，点击")
                history_btn.click()
                time.sleep(2)
            else:
                print("  ⚠ 未找到历史按钮，尝试直接查找会话列表")

            page.screenshot(path='D:/manus/opencode/test_screenshots/complete_05_history_open.png')

            # 查找会话项
            sessions = page.locator('[data-session-id], .session-item, li').all()
            print(f"  - 找到 {len(sessions)} 个会话项")

            if len(sessions) >= 2:
                # 点击第一个会话
                print("\n  - 点击第一个会话...")
                sessions[0].click()
                time.sleep(4)

                page.screenshot(path='D:/manus/opencode/test_screenshots/complete_06_first_session.png', full_page=True)

                # 检查第一个会话的内容
                page_text = page.locator('body').text_content() or ''
                session1_content = {
                    'hello.py': 'hello.py' in page_text.lower(),
                    'write': 'write' in page_text.lower(),
                    'task 1': 'task 1' in page_text.lower() or 'hello from task 1' in page_text.lower(),
                }
                print(f"  - 第一个会话内容: {session1_content}")

                # 点击第二个会话
                print("\n  - 点击第二个会话...")
                if len(sessions) > 1:
                    # 重新打开历史
                    if history_btn.count() > 0:
                        history_btn.click()
                        time.sleep(2)

                    sessions = page.locator('[data-session-id], .session-item, li').all()
                    if len(sessions) > 1:
                        sessions[1].click()
                        time.sleep(4)

                        page.screenshot(path='D:/manus/opencode/test_screenshots/complete_07_second_session.png', full_page=True)

                        # 检查第二个会话的内容
                        page_text = page.locator('body').text_content() or ''
                        session2_content = {
                            'world.py': 'world.py' in page_text.lower(),
                            'write': 'write' in page_text.lower(),
                            'bash': 'bash' in page_text.lower(),
                            'task 2': 'task 2' in page_text.lower() or 'world from task 2' in page_text.lower(),
                        }
                        print(f"  - 第二个会话内容: {session2_content}")

            # ========== 第七步：检查控制台日志 ==========
            print("\n[第七步] 检查控制台日志...")

            timeline_logs = [l for l in all_logs if 'Timeline' in l['text']]
            event_logs = [l for l in all_logs if 'Event' in l['text']]
            history_logs = [l for l in all_logs if 'History' in l['text']]

            print(f"  - Timeline日志: {len(timeline_logs)} 条")
            print(f"  - Event日志: {len(event_logs)} 条")
            print(f"  - History日志: {len(history_logs)} 条")

            # 显示关键日志
            print("\n  关键日志（最后20条）:")
            for log in all_logs[-20:]:
                if any(kw in log['text'] for kw in ['Timeline', 'Event', 'History', 'Loaded', 'Rendering']):
                    print(f"    [{log['time']}] {log['text'][:100]}")

            # ========== 测试总结 ==========
            print("\n" + "=" * 70)
            print("测试总结")
            print("=" * 70)

            print("\n任务创建:")
            print(f"  ✓ 任务1 (hello.py): {task1_events}")
            print(f"  ✓ 任务2 (world.py): {task2_events}")

            print("\n文件生成:")
            print(f"  ✓ hello.py: {'存在' if hello_found else '不存在'}")
            print(f"  ✓ world.py: {'存在' if world_found else '不存在'}")

            print("\n历史记录:")
            print(f"  ✓ 会话数量: {len(sessions)}")
            if len(sessions) >= 2:
                print(f"  ✓ 第一个会话: {session1_content}")
                print(f"  ✓ 第二个会话: {session2_content}")

            print("\n事件显示:")
            print(f"  ✓ Timeline日志: {len(timeline_logs)} 条")
            print(f"  ✓ History日志: {len(history_logs)} 条")

            print("\n截图:")
            print("  1. complete_01_home.png")
            print("  2. complete_02_task1_executed.png (full)")
            print("  3. complete_03_task2_executed.png (full)")
            print("  4. complete_04_after_refresh.png")
            print("  5. complete_05_history_open.png")
            print("  6. complete_06_first_session.png (full)")
            print("  7. complete_07_second_session.png (full)")

            print("\n" + "=" * 70)

            # 保持浏览器打开
            print("\n浏览器保持打开30秒供观察...")
            time.sleep(30)

        except Exception as e:
            print(f"\n✗ 测试出错: {e}")
            import traceback
            traceback.print_exc()

            try:
                page.screenshot(path='D:/manus/opencode/test_screenshots/complete_error.png', full_page=True)
                print("  ✓ 已保存错误截图")
            except:
                pass

        finally:
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('D:/manus/opencode/test_screenshots', exist_ok=True)
    complete_test()
