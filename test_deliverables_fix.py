"""
测试交付面板按轮次显示的修复效果

测试场景：
1. 创建新任务，生成文件
2. 进行追问，生成更多文件
3. 验证第一轮只显示第一轮的文件
4. 验证第二轮只显示第二轮的文件
"""

from playwright.sync_api import sync_playwright
import time
import json

def test_deliverables_per_turn():
    """测试交付物按轮次显示"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 启用控制台日志
        page.on('console', lambda msg: print(f'Console: {msg.text}'))

        try:
            print('=== 步骤1: 访问应用 ===')
            page.goto('http://localhost:5000')
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)  # 等待页面完全加载

            # 截图初始状态
            page.screenshot(path='test_screenshots/01_initial.png')
            print('✓ 页面加载完成')

            print('\n=== 步骤2: 创建新任务 ===')
            # 查找输入框
            prompt_input = page.locator('#prompt, #prompt-welcome').first
            if prompt_input.count() > 0:
                prompt_input.fill('创建一个简单的HTML页面，包含标题和段落')
                print('✓ 输入框已填写')

                # 点击运行按钮
                run_button = page.locator('#runStream, #runStream-welcome').first
                if run_button.count() > 0:
                    run_button.click()
                    print('✓ 已点击运行按钮')

                    # 等待任务执行（最多60秒）
                    print('⏳ 等待任务执行...')
                    page.wait_for_timeout(30000)  # 等待30秒

                    # 截图第一轮结果
                    page.screenshot(path='test_screenshots/02_first_turn.png')
                    print('✓ 第一轮执行完成')

                    # 检查交付面板
                    deliverables_first = page.locator('.web-file-card, .file-card').all()
                    print(f'✓ 第一轮交付物数量: {len(deliverables_first)}')

                    for i, card in enumerate(deliverables_first[:5]):  # 最多显示5个
                        text = card.inner_text()
                        print(f'  文件{i+1}: {text[:50]}...')

                    print('\n=== 步骤3: 进行追问 ===')
                    # 在输入框输入追问
                    prompt_input.fill('添加一个CSS样式，使标题居中')
                    print('✓ 追问已填写')

                    # 点击运行按钮
                    run_button = page.locator('#runStream').first
                    if run_button.count() > 0:
                        run_button.click()
                        print('✓ 已点击运行按钮')

                        # 等待任务执行
                        print('⏳ 等待追问执行...')
                        page.wait_for_timeout(30000)

                        # 截图第二轮结果
                        page.screenshot(path='test_screenshots/03_second_turn.png')
                        print('✓ 第二轮执行完成')

                        # 检查所有交付面板
                        all_deliverables = page.locator('.web-file-card, .file-card').all()
                        print(f'✓ 总交付物数量: {len(all_deliverables)}')

                        print('\n=== 步骤4: 验证按轮次显示 ===')

                        # 检查conversation-turn元素
                        turns = page.locator('.conversation-turn').all()
                        print(f'✓ 检测到 {len(turns)} 轮对话')

                        for turn_idx in range(len(turns)):
                            turn = turns[turn_idx]
                            deliverables_in_turn = turn.locator('.web-file-card, .file-card').all()
                            print(f'\n第{turn_idx + 1}轮交付物: {len(deliverables_in_turn)}个')

                            for card in deliverables_in_turn:
                                text = card.inner_text()
                                # 提取文件名
                                lines = text.split('\n')
                                filename = lines[0] if lines else 'unknown'
                                print(f'  - {filename}')

                        print('\n=== 验证结果 ===')

                        # 验证逻辑
                        if len(turns) >= 2:
                            first_turn_deliverables = turns[0].locator('.web-file-card, .file-card').all()
                            second_turn_deliverables = turns[1].locator('.web-file-card, .file-card').all()

                            if len(first_turn_deliverables) > 0 and len(second_turn_deliverables) > 0:
                                # 检查文件名是否不同
                                first_files = [card.inner_text().split('\n')[0] for card in first_turn_deliverables]
                                second_files = [card.inner_text().split('\n')[0] for card in second_turn_deliverables]

                                # 检查是否有重复
                                overlap = set(first_files) & set(second_files)

                                if len(overlap) == 0:
                                    print('✅ PASS: 两轮交付物完全分离，没有重复')
                                else:
                                    print(f'❌ FAIL: 发现重复文件: {overlap}')
                            else:
                                print('⚠️  WARNING: 某一轮没有交付物')
                        else:
                            print('⚠️  WARNING: 对话轮次少于2轮，无法验证')

                    else:
                        print('❌ 未找到运行按钮')
                else:
                    print('❌ 未找到运行按钮')
            else:
                print('❌ 未找到输入框')

        except Exception as e:
            print(f'❌ 测试出错: {e}')
            import traceback
            traceback.print_exc()

        finally:
            print('\n=== 清理 ===')
            browser.close()
            print('✓ 测试完成')

if __name__ == '__main__':
    import os
    os.makedirs('test_screenshots', exist_ok=True)
    test_deliverables_per_turn()
