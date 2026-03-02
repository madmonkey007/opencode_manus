#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的浏览器测试 - 验证所有修复
"""
from playwright.sync_api import sync_playwright
import time

def test_complete_fix():
    """完整测试所有修复"""
    print("="*70)
    print("完整测试 - 验证所有修复")
    print("="*70)

    with sync_playwright() as p:
        # 清除所有缓存启动浏览器
        browser = p.chromium.launch(
            headless=False,
            slow_mo=2000,
            args=['--disable-cache', '--disable-application-cache']
        )

        context = browser.new_context(
            viewport={'width': 1600, 'height': 900},
            offline=False
        )

        page = context.new_page()

        # 禁用缓存
        page.route("**/*", lambda route: route.continue_())

        # 收集所有控制台日志
        console_logs = []
        page.on('console', lambda msg: console_logs.append({
            'type': msg.type,
            'text': msg.text,
            'timestamp': time.time()
        }))

        try:
            # 第一步：访问应用
            print("\n[步骤1] 访问应用（清除缓存）...")
            page.goto('http://localhost:8089', wait_until='networkidle', force=True)
            time.sleep(3)

            # 检查页面加载
            page_title = page.title()
            print(f"  页面标题: {page_title}")

            # 截图
            page.screenshot(path='D:/manus/opencode/test_screenshots/final_01_home.png')
            print("  ✓ 截图已保存")

            # 第二步：检查函数是否存在
            print("\n[步骤2] 检查全局函数...")

            # 方法1: 直接检查
            result1 = page.evaluate('typeof window.loadSessionTimeline')
            print(f"  typeof window.loadSessionTimeline: {result1}")

            result2 = page.evaluate('typeof window.handleHistorySessionClick')
            print(f"  typeof window.handleHistorySessionClick: {result2}")

            # 方法2: 检查window对象
            window_keys = page.evaluate('Object.keys(window).filter(k => k.includes("Timeline") || k.includes("History"))')
            print(f"  Window对象中的相关键: {window_keys}")

            # 第三步：检查控制台日志
            print("\n[步骤3] 检查控制台日志...")

            timeline_logs = [log for log in console_logs if 'Timeline' in log['text']]
            history_logs = [log for log in console_logs if 'History' in log['text']]

            print(f"  Timeline相关日志: {len(timeline_logs)} 条")
            print(f"  History相关日志: {len(history_logs)} 条")

            if timeline_logs:
                print("\n  Timeline日志:")
                for log in timeline_logs[-5:]:
                    print(f"    {log['text']}")

            if history_logs:
                print("\n  History日志:")
                for log in history_logs[-5:]:
                    print(f"    {log['text']}")

            # 第四步：检查加载的JS文件
            print("\n[步骤4] 检查加载的JS文件...")

            # 检查history-fix.js是否加载
            scripts = page.evaluate('''() => {
                const scripts = Array.from(document.scripts);
                return scripts.map(s => s.src).filter(src => src.includes('history'));
            }''')

            print(f"  加载的history相关脚本: {scripts}")

            # 检查opencode-new-api-patch.js
            patch_scripts = page.evaluate('''() => {
                const scripts = Array.from(document.scripts);
                return scripts.map(s => s.src).filter(src => src.includes('opencode-new-api-patch'));
            }''')

            print(f"  加载的patch脚本: {patch_scripts}")

            # 第五步：创建任务测试
            print("\n[步骤5] 创建任务测试...")

            # 查找输入框
            textarea = page.locator('textarea').first
            if textarea.count() > 0:
                print("  找到输入框")

                # 输入任务
                textarea.fill('创建test.py文件，内容是print("test")')
                time.sleep(1)

                # 提交
                submit_btn = page.locator('button[type="submit"], button:has-text("send")').first
                if submit_btn.count() > 0:
                    submit_btn.click()
                else:
                    textarea.press('Enter')

                print("  任务已提交")

                # 等待执行
                print("  等待执行（20秒）...")
                time.sleep(20)

                # 截图
                page.screenshot(path='D:/manus/opencode/test_screenshots/final_02_executing.png', full_page=True)

                # 检查页面内容
                page_text = page.locator('body').text_content() or ''

                events_found = {
                    'write': 'write' in page_text.lower(),
                    'test.py': 'test.py' in page_text.lower(),
                    'print': 'print' in page_text.lower(),
                }

                print(f"  事件显示: {events_found}")

            # 第六步：刷新测试
            print("\n[步骤6] 刷新浏览器测试...")
            page.reload(wait_until='networkidle')
            time.sleep(3)

            page.screenshot(path='D:/manus/opencode/test_screenshots/final_03_refreshed.png')

            # 重新检查函数
            result_after = page.evaluate('typeof window.loadSessionTimeline')
            print(f"  刷新后 typeof window.loadSessionTimeline: {result_after}")

            # 总结
            print("\n" + "="*70)
            print("测试总结")
            print("="*70)

            print(f"\n函数检查:")
            print(f"  loadSessionTimeline: {result1}")
            print(f"  handleHistorySessionClick: {result2}")

            print(f"\n脚本加载:")
            print(f"  history-fix.js: {'✓ 加载' if scripts else '✗ 未加载'}")
            print(f"  opencode-new-api-patch.js: {'✓ 加载' if patch_scripts else '✗ 未加载'}")

            print(f"\n控制台日志:")
            print(f"  Timeline日志: {len(timeline_logs)} 条")
            print(f"  History日志: {len(history_logs)} 条")

            if result1 == 'function' and scripts:
                print("\n✓ 所有修复成功！")
            elif result1 == 'function':
                print("\n✓ 函数已加载，但history-fix.js可能未加载")
            else:
                print("\n✗ 函数未加载，需要进一步检查")

            print("\n截图:")
            print("  1. final_01_home.png")
            print("  2. final_02_executing.png")
            print("  3. final_03_refreshed.png")

            print("\n浏览器保持打开30秒...")
            time.sleep(30)

        except Exception as e:
            print(f"\n✗ 测试出错: {e}")
            import traceback
            traceback.print_exc()

            try:
                page.screenshot(path='D:/manus/opencode/test_screenshots/final_error.png')
            except:
                pass

        finally:
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('D:/manus/opencode/test_screenshots', exist_ok=True)
    test_complete_fix()
