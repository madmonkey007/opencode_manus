from playwright.sync_api import sync_playwright
import sys
print('start', flush=True)
with sync_playwright() as p:
    print('launch', flush=True)
    browser = p.chromium.launch(headless=True)
    print('launched', flush=True)
    browser.close()
print('done', flush=True)
