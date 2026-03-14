from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


URL = "http://localhost:8089"
SCREENSHOT_PATH = "D:\\manus\\opencode\\tools\\ui_smoke_test.png"
PROMPT = "Please reply with 2+2."


def main():
    with sync_playwright() as p:
        print("[ui-test] launching chromium")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(15000)
        print("[ui-test] navigating")
        try:
            page.goto(URL, wait_until="networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            print("[ui-test] navigation timeout, continuing with current DOM")

        # Basic reconnaissance
        print("[ui-test] taking screenshot")
        page.screenshot(path=SCREENSHOT_PATH, full_page=True)

        # Try to find a text input
        input_locator = None
        for selector in ["textarea", "input[type='text']", "input[type='search']"]:
            loc = page.locator(selector)
            if loc.count() > 0:
                input_locator = loc.first
                break

        if input_locator:
            input_locator.fill(PROMPT)

        # Try common action buttons
        clicked = False
        button_candidates = [
            "button:has-text('Send')",
            "button:has-text('Run')",
            "button:has-text('Submit')",
            "button:has-text('Execute')",
            "button:has-text('执行')",
            "button:has-text('发送')",
            "button:has-text('开始')",
        ]
        for sel in button_candidates:
            btn = page.locator(sel)
            if btn.count() > 0:
                btn.first.click()
                clicked = True
                break

        if not clicked:
            # As a fallback, click the first enabled button if any
            buttons = page.locator("button:enabled")
            if buttons.count() > 0:
                buttons.first.click()
                clicked = True

        # Wait briefly for any result area update
        try:
            page.wait_for_timeout(3000)
            page.screenshot(path=SCREENSHOT_PATH, full_page=True)
        except PlaywrightTimeoutError:
            pass

        browser.close()


if __name__ == "__main__":
    main()
