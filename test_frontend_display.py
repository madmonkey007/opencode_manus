#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端显示验证 - 检查历史记录中的事件和文件
"""
from playwright.sync_api import sync_playwright
import time
import json

def check_frontend_display():
    """检查前端页面显示"""
    print("=" * 70)
    print("前端显示验证 - 检查事件和文件")
    print("=" * 70)

    with sync_playwright() as p:
        # 启动浏览器（非headless，便于观察）
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={'width': 1400, 'height': 900})
        page = context.new_page()

        # 收集控制台日志
        console_messages = []
        def handle_console(msg):
            console_messages.append({
                'type': msg.type,
                'text': msg.text,
                'timestamp': time.time()
            })
        page.on('console', handle_console)

        try:
            # ========== 步骤1：访问应用 ==========
            print("\n[步骤1] 访问应用...")
            page.goto('http://localhost:8089')
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            print("页面已加载")

            # 截图初始状态
            page.screenshot(path='D:/manus/opencode/test_screenshots/frontend_01_homepage.png')
            print("已保存: homepage.png")

            # ========== 步骤2：查找并点击历史会话 ==========
            print("\n[步骤2] 查找历史会话...")

            # 检查页面上的会话列表
            page_content = page.content()

            # 查找可能的会话按钮/链接
            session_selectors = [
                'button:has-text("历史")',
                'a:has-text("历史")',
                '[data-testid="history"]',
                '#history',
                '.history-button',
                'button:has-text("会话")',
            ]

            history_button = None
            for selector in session_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        history_button = page.locator(selector).first
                        print(f"找到历史按钮: {selector}")
                        history_button.click()
                        time.sleep(2)
                        break
                except:
                    continue

            # 截图
            page.screenshot(path='D:/manus/opencode/test_screenshots/frontend_02_after_history_click.png')
            print("已保存: after_history_click.png")

            # ========== 步骤3：查找会话列表 ==========
            print("\n[步骤3] 查找会话列表项...")

            # 查找所有可能的会话项
            item_selectors = [
                '[data-session-id]',
                '.session-item',
                '.history-item',
                'li',
                '[role="listitem"]',
            ]

            session_items = []
            for selector in item_selectors:
                try:
                    items = page.locator(selector).all()
                    if len(items) > 0:
                        print(f"通过 {selector} 找到 {len(items)} 个元素")
                        # 过滤出可能是会话的元素
                        for item in items:
                            text = item.text_content() or ''
                            if text and len(text) > 0:
                                session_items.append(item)
                        if len(session_items) >= 3:  # 找到足够多的元素就停止
                            break
                except:
                    continue

            print(f"总共找到 {len(session_items)} 个可能的会话项")

            if len(session_items) == 0:
                print("未找到历史会话，尝试直接访问API获取会话列表...")
                # 使用API获取会话
                import requests
                import sqlite3

                conn = sqlite3.connect('D:/manus/opencode/history.db')
                cursor = conn.cursor()
                cursor.execute("SELECT session_id FROM sessions LIMIT 1")
                result = cursor.fetchone()
                conn.close()

                if result:
                    session_id = result[0]
                    print(f"从数据库获取会话ID: {session_id}")
                    # 直接导航到会话页面
                    page.goto(f'http://localhost:8089?session={session_id}')
                    page.wait_for_load_state('networkidle')
                    time.sleep(3)
            else:
                # 点击第一个会话
                print("\n点击第一个历史会话...")
                try:
                    session_items[0].click()
                    time.sleep(3)
                except Exception as e:
                    print(f"点击失败: {e}")

            # 截图会话加载后
            page.screenshot(path='D:/manus/opencode/test_screenshots/frontend_03_session_loaded.png')
            print("已保存: session_loaded.png")

            # ========== 步骤4：检查事件显示 ==========
            print("\n[步骤4] 检查页面上的事件显示...")

            # 查找事件相关元素
            event_indicators = {
                '工具调用': [
                    'button:has-text("tool")',
                    '[data-tool-call]',
                    '.tool-use',
                    '.function-call',
                    '[class*="tool"]',
                ],
                '文件操作': [
                    '[data-file]',
                    '.file-operation',
                    '[class*="file"]',
                    'text=write',
                    'text=edit',
                    'text=read',
                ],
                '思考过程': [
                    '[data-thinking]',
                    '.thinking',
                    '[class*="think"]',
                    'text=Think',
                ],
                '消息': [
                    '.message',
                '[role="log"]',
                '[class*="message"]',
                '.chat-message',
                ],
            }

            events_found = {}
            for event_type, selectors in event_indicators.items():
                count = 0
                for selector in selectors:
                    try:
                        c = page.locator(selector).count()
                        if c > 0:
                            count += c
                            print(f"  ✓ 找到 {event_type}: {c} 个 (选择器: {selector})")
                    except:
                        pass
                events_found[event_type] = count

            # 检查具体的文本内容
            print("\n检查页面文本内容...")
            body_text = page.locator('body').text_content() or ''

            keywords_to_check = {
                'write': '写文件操作',
                'edit': '编辑文件操作',
                'bash': '命令执行',
                'call': '函数调用',
                'think': '思考过程',
                'read': '读文件操作',
            }

            print("\n关键词出现情况:")
            for keyword, description in keywords_to_check.items():
                if keyword.lower() in body_text.lower():
                    count = body_text.lower().count(keyword.lower())
                    print(f"  ✓ '{keyword}' 出现 {count} 次 ({description})")
                else:
                    print(f"  ✗ '{keyword}' 未找到 ({description})")

            # ========== 步骤5：检查文件显示 ==========
            print("\n[步骤5] 检查生成的文件显示...")

            file_indicators = [
                'text=.py',
                'text=.js',
                'text=.txt',
                'text=.md',
                '[href*=".py"]',
                '[href*=".js"]',
                'a:has-text("file")',
            ]

            files_found = 0
            for indicator in file_indicators:
                try:
                    count = page.locator(indicator).count()
                    if count > 0:
                        files_found += count
                        print(f"  ✓ 找到文件引用: {count} 个 (选择器: {indicator})")
                except:
                    pass

            if files_found == 0:
                print("  ⚠ 未找到明显的文件引用")

            # ========== 步骤6：刷新页面测试持久化 ==========
            print("\n[步骤6] 刷新页面验证数据持久化...")

            page.reload(wait_until='networkidle')
            time.sleep(3)

            page.screenshot(path='D:/manus/opencode/test_screenshots/frontend_04_after_refresh.png')
            print("已保存: after_refresh.png")

            # 再次检查内容
            print("\n刷新后重新检查事件...")
            body_text_after = page.locator('body').text_content() or ''

            events_after_refresh = 0
            for keyword in ['write', 'edit', 'bash', 'call', 'tool']:
                if keyword.lower() in body_text_after.lower():
                    events_after_refresh += 1
                    print(f"  ✓ 刷新后仍有: {keyword}")

            # ========== 步骤7：检查网络请求 ==========
            print("\n[步骤7] 检查API请求...")

            # 获取会话ID
            import sqlite3
            conn = sqlite3.connect('D:/manus/opencode/history.db')
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM sessions LIMIT 1")
            result = cursor.fetchone()
            conn.close()

            if result:
                session_id = result[0]
                print(f"测试会话: {session_id}")

                # 测试API
                import requests

                # 测试messages
                try:
                    msg_resp = requests.get(f'http://localhost:8089/opencode/session/{session_id}/messages')
                    if msg_resp.status_code == 200:
                        data = msg_resp.json()
                        msg_count = data.get('count', 0)
                        print(f"  ✓ Messages API: {msg_count} 条消息")

                        # 检查消息内容
                        messages = data.get('messages', [])
                        for msg in messages[:3]:
                            info = msg.get('info', {})
                            role = info.get('role', '')
                            print(f"    - {role}: {info.get('id', '')}")
                except Exception as e:
                    print(f"  ✗ Messages API 失败: {e}")

                # 测试timeline
                try:
                    tl_resp = requests.get(f'http://localhost:8089/opencode/session/{session_id}/timeline')
                    if tl_resp.status_code == 200:
                        data = tl_resp.json()
                        tl_count = data.get('count', 0)
                        print(f"  ✓ Timeline API: {tl_count} 个事件")

                        # 显示事件类型
                        timeline = data.get('timeline', [])
                        if timeline:
                            print("    事件列表:")
                            for event in timeline[:5]:
                                action = event.get('action', '')
                                path = event.get('path', '')
                                print(f"      - [{action}] {path or '(无路径)'}")
                except Exception as e:
                    print(f"  ✗ Timeline API 失败: {e}")

            # ========== 步骤8：保存详细报告 ==========
            print("\n[步骤8] 生成详细报告...")

            report = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'url': 'http://localhost:8089',
                'events_found': events_found,
                'files_found': files_found,
                'keywords_in_page': {
                    keyword: (keyword.lower() in body_text.lower())
                    for keyword in keywords_to_check.keys()
                },
                'events_after_refresh': events_after_refresh,
                'console_messages': console_messages[-20:],  # 最后20条
                'page_title': page.title(),
            }

            with open('D:/manus/opencode/test_screenshots/frontend_check_report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            print("✓ 已保存详细报告: frontend_check_report.json")

            # ========== 总结 ==========
            print("\n" + "=" * 70)
            print("前端显示验证总结")
            print("=" * 70)

            print(f"\n事件显示情况:")
            for event_type, count in events_found.items():
                status = "✓" if count > 0 else "✗"
                print(f"  {status} {event_type}: {count} 个")

            print(f"\n文件显示情况:")
            if files_found > 0:
                print(f"  ✓ 找到 {files_found} 个文件引用")
            else:
                print(f"  ✗ 未找到文件引用")

            print(f"\n刷新后数据持久化:")
            if events_after_refresh > 0:
                print(f"  ✓ 刷新后仍有 {events_after_refresh} 种事件类型")
            else:
                print(f"  ✗ 刷新后内容丢失")

            print("\n截图已保存:")
            print("  1. frontend_01_homepage.png")
            print("  2. frontend_02_after_history_click.png")
            print("  3. frontend_03_session_loaded.png")
            print("  4. frontend_04_after_refresh.png")
            print("  5. frontend_check_report.json")

            print("\n" + "=" * 70)

            # 保持浏览器打开15秒
            print("\n浏览器将在15秒后关闭...")
            time.sleep(15)

        except Exception as e:
            print(f"\n✗ 测试过程出错: {e}")
            import traceback
            traceback.print_exc()

            try:
                page.screenshot(path='D:/manus/opencode/test_screenshots/frontend_error.png')
                print("已保存错误截图")
            except:
                pass

        finally:
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('D:/manus/opencode/test_screenshots', exist_ok=True)
    check_frontend_display()
