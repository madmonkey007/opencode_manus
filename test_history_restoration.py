#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试历史数据显示修复
使用Playwright自动化浏览器测试
"""
from playwright.sync_api import sync_playwright
import time
import json
import sys
import io

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_history_restoration():
    """测试历史会话恢复功能"""
    print("=" * 60)
    print("开始测试历史数据显示修复")
    print("=" * 60)

    with sync_playwright() as p:
        # 启动浏览器（非headless模式以便观察）
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()

        try:
            # 步骤1：访问应用
            print("\n[步骤1] 访问OpenCode应用...")
            page.goto('http://localhost:8089')
            page.wait_for_load_state('networkidle')
            print("✓ 页面加载完成")

            # 等待页面完全加载
            time.sleep(2)

            # 步骤2：查找历史会话列表
            print("\n[步骤2] 查找历史会话列表...")

            # 截图保存当前页面状态
            page.screenshot(path='D:/manus/opencode/test_screenshots/01_initial_page.png', full_page=True)
            print("✓ 已保存初始页面截图")

            # 查找会话列表元素
            # 尝试多种选择器
            selectors_to_try = [
                '[data-testid="session-list"]',
                '.session-list',
                '#session-list',
                '[role="list"]',
                'ul',
            ]

            session_list = None
            for selector in selectors_to_try:
                try:
                    session_list = page.locator(selector).first
                    if session_list.count() > 0:
                        print(f"✓ 找到会话列表元素: {selector}")
                        break
                except:
                    continue

            if not session_list:
                print("⚠ 未找到明显的会话列表元素，尝试查找历史按钮...")
                # 查找可能的历史/会话按钮
                history_buttons = page.locator('button, a').filter(has_text='历史')
                if history_buttons.count() > 0:
                    print(f"✓ 找到 {history_buttons.count()} 个历史相关按钮")
                    history_buttons.first.click()
                    time.sleep(2)

            # 步骤3：查找并点击历史会话
            print("\n[步骤3] 查找历史会话...")

            # 获取页面内容用于调试
            page_content = page.content()

            # 查找所有可能的会话项
            session_items = page.locator('[data-session-id], .session-item, li').all()
            print(f"✓ 找到 {len(session_items)} 个可能的会话项")

            if len(session_items) > 0:
                # 点击第一个会话
                first_session = session_items[0]
                first_session.click()
                print("✓ 已点击第一个历史会话")
                time.sleep(3)

                # 步骤4：验证会话内容
                print("\n[步骤4] 验证会话内容显示...")

                # 截图
                page.screenshot(path='D:/manus/opencode/test_screenshots/02_session_loaded.png', full_page=True)
                print("✓ 已保存会话加载截图")

                # 检查是否有消息显示
                messages = page.locator('.message, [role="log"], .log-entry').all()
                print(f"✓ 找到 {len(messages)} 条消息")

                # 检查工具调用事件
                tool_calls = page.locator('[data-tool-call], .tool-use, .event').all()
                print(f"✓ 找到 {len(tool_calls)} 个工具调用事件")

                # 检查控制台日志
                print("\n[步骤5] 检查浏览器控制台...")
                console_logs = []
                page.on('console', lambda msg: console_logs.append({'type': msg.type, 'text': msg.text}))

                # 等待一会收集日志
                time.sleep(2)

                # 保存控制台日志
                with open('D:/manus/opencode/test_screenshots/console_logs.json', 'w', encoding='utf-8') as f:
                    json.dump(console_logs, f, ensure_ascii=False, indent=2)
                print(f"✓ 已保存 {len(console_logs)} 条控制台日志")

                # 步骤6：测试API端点
                print("\n[步骤6] 测试后端API端点...")

                # 获取第一个会话的ID（从页面或数据库）
                import sqlite3
                conn = sqlite3.connect('D:/manus/opencode/history.db')
                cursor = conn.cursor()
                cursor.execute("SELECT session_id FROM sessions LIMIT 1")
                result = cursor.fetchone()
                conn.close()

                if result:
                    session_id = result[0]
                    print(f"测试会话ID: {session_id}")

                    # 测试messages API
                    try:
                        messages_response = page.request.get(f'http://localhost:8089/opencode/session/{session_id}/messages')
                        messages_data = messages_response.json()
                        print(f"✓ Messages API返回: {messages_data.get('count', 0)} 条消息")
                    except Exception as e:
                        print(f"✗ Messages API调用失败: {e}")

                    # 测试timeline API
                    try:
                        timeline_response = page.request.get(f'http://localhost:8089/opencode/session/{session_id}/timeline')
                        timeline_data = timeline_response.json()
                        print(f"✓ Timeline API返回: {timeline_data.get('count', 0)} 个事件")
                        if timeline_data.get('timeline'):
                            print("  事件类型:")
                            for event in timeline_data['timeline'][:5]:
                                print(f"    - [{event.get('action')}] {event.get('path', 'N/A')}")
                    except Exception as e:
                        print(f"✗ Timeline API调用失败: {e}")

            else:
                print("⚠ 未找到历史会话，可能是新安装的系统")
                print("提示：需要先创建一些会话才能测试历史功能")

            # 步骤7：刷新页面测试持久化
            print("\n[步骤7] 测试刷新后数据持久化...")
            page.reload(wait_until='networkidle')
            time.sleep(3)

            page.screenshot(path='D:/manus/opencode/test_screenshots/03_after_refresh.png', full_page=True)
            print("✓ 已保存刷新后截图")

            print("\n" + "=" * 60)
            print("测试完成！")
            print("=" * 60)
            print(f"\n截图和日志已保存到: D:/manus/opencode/test_screenshots/")

        except Exception as e:
            print(f"\n✗ 测试过程中出错: {e}")
            import traceback
            traceback.print_exc()

            # 即使出错也保存截图
            try:
                page.screenshot(path='D:/manus/opencode/test_screenshots/error_screenshot.png', full_page=True)
                print("✓ 已保存错误截图")
            except:
                pass

        finally:
            # 保持浏览器打开10秒供观察
            print("\n浏览器将在10秒后关闭...")
            time.sleep(10)
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('D:/manus/opencode/test_screenshots', exist_ok=True)
    test_history_restoration()
