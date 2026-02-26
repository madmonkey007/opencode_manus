from browser_use import Browser, BrowserConfig, ContextConfig
import asyncio
import os

async def main():
    browser = Browser(
        config=BrowserConfig(
            headless=True,
        )
    )
    async with await browser.new_context() as context:
        page = await context.get_current_page()
        print("Navigating to http://localhost:8089/...")
        await page.goto('http://localhost:8089/')
        await asyncio.sleep(2) # Wait for page load
        
        # Take initial screenshot
        await page.screenshot(path='screenshot_home.png')
        print("Home screenshot saved.")
        
        # Click Plan mode if available
        # Based on opencode.js, there might be buttons for modes
        # Let's look for buttons or elements
        elements = await context.get_tabs_info()
        print(f"Tabs info: {elements}")
        
        # Try to find the input and type something
        # The input ID is 'prompt-welcome' or 'prompt'
        try:
            await page.fill('#prompt-welcome', '写入一个网页版闹钟，黑白灰，像素游戏风格')
            await page.press('#prompt-welcome', 'Enter')
            print("Prompt submitted.")
        except Exception as e:
            print(f"Could not find #prompt-welcome: {e}")
            try:
                await page.fill('#prompt', '写入一个网页版闹钟，黑白灰，像素游戏风格')
                await page.press('#prompt', 'Enter')
                print("Prompt submitted via #prompt.")
            except Exception as e2:
                print(f"Could not find #prompt: {e2}")
        
        await asyncio.sleep(5) # Wait for processing
        await page.screenshot(path='screenshot_result.png')
        print("Result screenshot saved.")
        
    await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
