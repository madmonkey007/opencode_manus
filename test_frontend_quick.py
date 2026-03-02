#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版前端验证 - 快速检查事件和文件
"""
from playwright.sync_api import sync_playwright
import time
import sqlite3
import requests

def quick_check():
    """快速检查前端显示"""
    print("=" * 60)
    print("前端显示快速验证")
    print("=" * 60)

    # 先测试API
    print("\n[1] 测试API端点...")

    conn = sqlite3.connect('D:/manus/opencode/history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT session_id FROM sessions LIMIT 1")
    result = cursor.fetchone()
    conn.close()

    if not result:
        print("No sessions in database")
        return

    session_id = result[0]
    print(f"Session ID: {session_id}")

    # 测试messages API
    try:
        resp = requests.get(f'http://localhost:8089/opencode/session/{session_id}/messages')
        if resp.status_code == 200:
            data = resp.json()
            msg_count = data.get('count', 0)
            print(f"Messages API: {msg_count} messages")
        else:
            print(f"Messages API failed: {resp.status_code}")
    except Exception as e:
        print(f"Messages API error: {e}")

    # 测试timeline API
    try:
        resp = requests.get(f'http://localhost:8089/opencode/session/{session_id}/timeline')
        if resp.status_code == 200:
            data = resp.json()
            tl_count = data.get('count', 0)
            print(f"Timeline API: {tl_count} events")

            if tl_count > 0:
                timeline = data.get('timeline', [])
                print("\nEvents found:")
                for event in timeline[:5]:
                    action = event.get('action', '')
                    path = event.get('path', '')
                    print(f"  - [{action}] {path or '(no path)'}")
        else:
            print(f"Timeline API failed: {resp.status_code}")
    except Exception as e:
        print(f"Timeline API error: {e}")

    # 浏览器检查
    print("\n[2] 检查前端页面...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()

        try:
            # 访问页面
            print("Loading page...")
            page.goto('http://localhost:8089')
            page.wait_for_load_state('networkidle')
            time.sleep(2)

            # 截图
            page.screenshot(path='D:/manus/opencode/test_screenshots/quick_01_home.png')
            print("Screenshot saved: home.png")

            # 查找历史按钮
            history_btn = page.locator('button:has-text("history")').first
            if history_btn.count() > 0:
                print("Found history button, clicking...")
                history_btn.click()
                time.sleep(2)

                page.screenshot(path='D:/manus/opencode/test_screenshots/quick_02_history.png')
                print("Screenshot saved: history.png")

                # 点击第一个会话
                session_item = page.locator('.session-item').first
                if session_item.count() > 0:
                    print("Clicking first session...")
                    session_item.click()
                    time.sleep(3)

                    page.screenshot(path='D:/manus/opencode/test_screenshots/quick_03_session.png', full_page=True)
                    print("Screenshot saved: session.png (full page)")

                    # 检查页面内容
                    print("\n[3] 检查页面内容...")

                    body_text = page.locator('body').text_content() or ''

                    # 检查关键词
                    keywords = ['write', 'edit', 'bash', 'tool', 'call', 'file']
                    found_keywords = []
                    for kw in keywords:
                        if kw.lower() in body_text.lower():
                            found_keywords.append(kw)

                    print(f"Keywords found on page: {', '.join(found_keywords)}")

                    # 检查元素
                    checks = {
                        'Messages': page.locator('.message').count(),
                        'Tool calls': page.locator('[data-tool-call], .tool-use').count(),
                        'File refs': page.locator('text=.py, text=.js, text=.txt').count(),
                    }

                    print("\nElements on page:")
                    for name, count in checks.items():
                        status = "OK" if count > 0 else "NOT FOUND"
                        print(f"  {name}: {count} [{status}]")

                    # 刷新测试
                    print("\n[4] 刷新页面测试...")
                    page.reload(wait_until='networkidle')
                    time.sleep(3)

                    page.screenshot(path='D:/manus/opencode/test_screenshots/quick_04_refresh.png', full_page=True)
                    print("Screenshot saved: refresh.png")

                    body_text_after = page.locator('body').text_content() or ''

                    keywords_after = []
                    for kw in keywords:
                        if kw.lower() in body_text_after.lower():
                            keywords_after.append(kw)

                    print(f"After refresh - Keywords: {', '.join(keywords_after)}")

                    print("\n" + "=" * 60)
                    print("检查完成!")
                    print("=" * 60)
                    print("\n结果:")
                    print(f"  - API messages: {msg_count}")
                    print(f"  - API events: {tl_count}")
                    print(f"  - 页面前关键词: {len(found_keywords)}")
                    print(f"  - 刷新后关键词: {len(keywords_after)}")

                    if len(found_keywords) > 0 and len(keywords_after) > 0:
                        print("\n状态: 成功 - 事件和文件在刷新后正常显示")
                    else:
                        print("\n状态: 需要检查 - 部分内容可能未显示")

            else:
                print("History button not found")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            print("\nKeeping browser open for 10 seconds...")
            time.sleep(10)
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('D:/manus/opencode/test_screenshots', exist_ok=True)
    quick_check()
