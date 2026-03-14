from playwright.sync_api import sync_playwright
import time
import os

log_path = r"D:/manus/opencode/output/playwright/diag_log.txt"

def log(msg):
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"{time.time():.3f} {msg}\n")

log('start')
try:
    with sync_playwright() as p:
        log('got playwright')
        browser = p.chromium.launch(headless=True, timeout=10000)
        log('launched')
        browser.close()
        log('closed')
except Exception as e:
    log(f'error {e!r}')
