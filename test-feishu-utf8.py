#!/usr/bin/env python3
import requests
import json

webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/899e8328-4975-4241-86e1-2c3837b3a313"

# Test message in English
message = """opencode [OK] OpenCode Task Notification

Status: Completed
Result: success
Files: test.py

Time: 2026-03-14T14:47:00Z

This is a test message to verify encoding."""

payload = {
    "msg_type": "text",
    "content": {
        "text": message
    }
}

print("Sending message to Feishu...")
print(f"Message: {message[:50]}...")

response = requests.post(
    webhook_url,
    headers={"Content-Type": "application/json; charset=utf-8"},
    data=json.dumps(payload, ensure_ascii=False)
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

if response.json().get('StatusCode') == 0:
    print("\n✅ SUCCESS! Message sent to Feishu!")
    print("Check your Feishu group for the message.")
else:
    print("\n❌ FAILED! Check the error above.")
