"""
简化的交付面板测试 - 使用Playwright inspect功能

使用方法：
1. 启动服务器: python run_server.py
2. 运行测试: python test_deliverables_simple.py
"""

from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        print('🚀 启动浏览器...')
        browser = p.chromium.launch(headless=False)  # 使用非headless模式以便观察
        page = browser.new_page()

        # 设置视口大小
        page.set_viewport_size({'width': 1920, 'height': 1080})

        # 监听控制台消息
        def handle_console(msg):
            if 'Deliverables' in msg.text or 'Added file' in msg.text:
                print(f'📋 {msg.text}')

        page.on('console', handle_console)

        try:
            print('📍 访问应用 http://localhost:8088')
            page.goto('http://localhost:8088')
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(3000)

            print('📸 截图1: 初始状态')
            page.screenshot(path='test_screenshots/1_initial.png')

            # 检查页面状态
            has_welcome = page.locator('#welcome-interface').count() > 0
            has_chat = page.locator('#chat-messages').count() > 0

            print(f'🔍 欢迎页: {"✓" if has_welcome else "✗"}')
            print(f'🔍 聊天界面: {"✓" if has_chat else "✗"}')

            if has_welcome:
                print('\n📝 测试场景1: 创建新任务')
                print('-' * 50)

                # 输入提示词
                prompt = page.locator('#prompt-welcome')
                if prompt.count() > 0:
                    prompt.fill('创建一个test.html文件')
                    print('✓ 已输入提示词')

                    # 查找并点击运行按钮
                    run_btn = page.locator('#runStream-welcome')
                    if run_btn.count() > 0:
                        run_btn.click()
                        print('✓ 已点击运行按钮')

                        # 等待任务执行
                        print('⏳ 等待任务完成 (30秒)...')
                        page.wait_for_timeout(30000)

                        print('📸 截图2: 第一轮完成')
                        page.screenshot(path='test_screenshots/2_first_turn.png', full_page=True)

                        # 检查交付物
                        deliverables = page.locator('.web-file-card, .file-card, [class*="deliverable"]').all()
                        print(f'📦 第一轮交付物: {len(deliverables)}个')

                        for i, d in enumerate(deliverables[:5]):
                            try:
                                text = d.inner_text()
                                lines = text.strip().split('\n')
                                filename = lines[0] if lines else 'unknown'
                                print(f'   {i+1}. {filename}')
                            except:
                                print(f'   {i+1}. [无法读取文件名]')

                        # 检查是否有conversation-turn
                        turns = page.locator('.conversation-turn, [class*="turn"]').all()
                        print(f'\n💬 检测到对话轮次: {len(turns)}')

                        if len(turns) > 0:
                            print('\n📝 测试场景2: 追问')
                            print('-' * 50)

                            # 查看第一轮的交付物
                            first_turn_deliverables = turns[0].locator('.web-file-card, .file-card').all()
                            print(f'📦 第一轮交付物面板中的文件: {len(first_turn_deliverables)}个')

                            # 输入追问
                            prompt_input = page.locator('#prompt')
                            if prompt_input.count() > 0:
                                prompt_input.fill('添加一个CSS样式文件')
                                print('✓ 已输入追问')

                                # 点击运行按钮
                                run_btn2 = page.locator('#runStream')
                                if run_btn2.count() > 0:
                                    run_btn2.click()
                                    print('✓ 已点击运行按钮')

                                    # 等待追问执行
                                    print('⏳ 等待追问完成 (30秒)...')
                                    page.wait_for_timeout(30000)

                                    print('📸 截图3: 第二轮完成')
                                    page.screenshot(path='test_screenshots/3_second_turn.png', full_page=True)

                                    # 检查第二轮的交付物
                                    turns = page.locator('.conversation-turn, [class*="turn"]').all()
                                    print(f'\n💬 当前对话轮次: {len(turns)}')

                                    if len(turns) >= 2:
                                        second_turn_deliverables = turns[1].locator('.web-file-card, .file-card').all()
                                        print(f'📦 第二轮交付物面板中的文件: {len(second_turn_deliverables)}个')

                                        print('\n✅ 验证修复效果:')
                                        print('-' * 50)

                                        first_count = len(first_turn_deliverables)
                                        second_count = len(second_turn_deliverables)

                                        print(f'第一轮文件数: {first_count}')
                                        print(f'第二轮文件数: {second_count}')

                                        # 检查是否有重复
                                        if first_count > 0 and second_count > 0:
                                            print(f'\n✓ 测试完成: 两轮都有交付物')

                                            # 尝试读取文件名检查是否有重复
                                            try:
                                                first_files = set()
                                                second_files = set()

                                                for d in first_turn_deliverables:
                                                    text = d.inner_text()
                                                    lines = text.strip().split('\n')
                                                    if lines:
                                                        first_files.add(lines[0].strip())

                                                for d in second_turn_deliverables:
                                                    text = d.inner_text()
                                                    lines = text.strip().split('\n')
                                                    if lines:
                                                        second_files.add(lines[0].strip())

                                                overlap = first_files & second_files

                                                if len(overlap) == 0:
                                                    print('✅ PASS: 两轮文件完全分离，没有重复')
                                                else:
                                                    print(f'❌ FAIL: 发现重复文件: {overlap}')
                                            except Exception as e:
                                                print(f'⚠️  无法检查文件名: {e}')

                                        elif first_count == 0 and second_count == 0:
                                            print('⚠️  WARNING: 两轮都没有交付物')
                                        elif first_count > 0 and second_count == 0:
                                            print('⚠️  WARNING: 第二轮没有交付物')
                                        elif first_count == 0 and second_count > 0:
                                            print('⚠️  WARNING: 第一轮没有交付物（全部跑到第二轮？）')

                                    else:
                                        print('⚠️  WARNING: 对话轮次少于2，无法验证')

            elif has_chat:
                print('📝 已有聊天会话，请创建新任务测试')

            print('\n📸 最终截图')
            page.screenshot(path='test_screenshots/4_final.png', full_page=True)

            print('\n✅ 测试完成！')
            print(f'📁 截图已保存到 test_screenshots/ 目录')
            print(f'\n💡 请检查截图以验证:')
            print(f'   - 第一轮的交付物是否只显示在第一轮？')
            print(f'   - 第二轮的交付物是否只显示在第二轮？')
            print(f'   - 是否有文件重复出现在多轮？')

        except Exception as e:
            print(f'\n❌ 测试出错: {e}')
            import traceback
            traceback.print_exc()

        finally:
            print('\n按Enter键关闭浏览器...')
            input()  # 等待用户按Enter
            browser.close()
            print('✓ 浏览器已关闭')

if __name__ == '__main__':
    import os
    os.makedirs('test_screenshots', exist_ok=True)
    main()
