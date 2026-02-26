from playwright.sync_api import sync_playwright
import time

def verify_phase():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        print("Navigating to http://localhost:8089/...")
        page.goto('http://localhost:8089/', wait_until='domcontentloaded', timeout=60000)
        # 移除 networkidle 等待，因为外部 CDN 可能会阻塞
        # page.wait_for_load_state('networkidle')
        
        # 查找可见的输入框
        print("Finding visible chat input...")
        chat_input = page.locator('#prompt-welcome')
        if not chat_input.is_visible():
            chat_input = page.locator('#prompt')
        
        chat_input.wait_for(state='visible', timeout=10000)
        
        print("Sending query: '帮我分析当前项目结构'")
        chat_input.fill('帮我分析当前项目结构')
        chat_input.press('Enter')
        
        # 等待一段时间让后端响应并生成 phase
        print("Waiting for response and phases...")
        time.sleep(10) # 给后端足够的时间
        
        # 截图验证
        page.screenshot(path='verify_phase_result.png', full_page=True)
        print("Screenshot saved to verify_phase_result.png")
        
        # 检查 DOM 中是否存在阶段卡片
        phase_card = page.locator('.enhanced-task-panel')
        if phase_card.count() > 0:
            print("SUCCESS: Enhanced task panel found!")
            # 进一步检查是否有 '任务阶段' 文字
            if "任务阶段" in page.content():
                print("SUCCESS: '任务阶段' text found in page!")
            else:
                print("WARNING: Enhanced task panel found but '任务阶段' text not found.")
        else:
            print("FAILURE: Enhanced task panel NOT found.")
            
        browser.close()

if __name__ == "__main__":
    verify_phase()
