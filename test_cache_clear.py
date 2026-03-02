#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清除缓存并重新测试
"""
from playwright.sync_api import sync_playwright
import time

print("="*70)
print("清除缓存测试")
print("="*70)

with sync_playwright() as p:
    # 清除缓存启动浏览器
    browser = p.chromium.launch(headless=False, slow_mo=2000)
    context = browser.new_context(
        viewport={'width': 1600, 'height': 900},
        # 忽略缓存
        ignore_http_errors=True
    )
    page = context.new_page()

    # 设置清除缓存
    page.route("**/*", lambda route: route.continue_())

    try:
        print("\n[1] 访问应用（清除缓存）...")
        page.goto('http://localhost:8089', wait_until='networkidle', force=True)
        time.sleep(3)

        # 检查页面内容
        page_text = page.locator('body').text_content() or ''

        # 检查mode
        has_build = 'build' in page_text.lower()
        has_plan = 'plan' in page_text.lower()

        print(f"  页面中提到build: {has_build}")
        print(f"  页面中提到plan: {has_plan}")

        # 查找mode选择器
        mode_selectors = page.locator('[data-mode], [value*="mode"], select').all()
        print(f"  找到 {len(mode_selectors)} 个mode相关元素")

        # 截图
        page.screenshot(path='D:/manus/opencode/test_screenshots/cache_test_01_home.png')
        print("  截图已保存")

        print("\n[2] 检查前端代码是否加载...")
        # 执行JavaScript检查
        check_code = '''
        // 检查是否有loadSessionTimeline函数
        if (typeof loadSessionTimeline !== 'undefined') {
            'loadSessionTimeline exists';
        } else {
            'loadSessionTimeline NOT found';
        }
        '''

        result = page.evaluate(check_code)
        print(f"  {result}")

        print("\n提示：")
        print("  1. 在浏览器按 Ctrl+Shift+R 强制刷新")
        print("  2. 或者按 F12 打开开发者工具")
        print("  3. 在Network标签勾选 'Disable cache'")
        print("  4. 然后刷新页面")

        print("\n浏览器保持打开30秒...")
        time.sleep(30)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        browser.close()

print("\n"+"="*70)
