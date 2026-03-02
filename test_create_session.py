#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试创建新会话功能 - 验证422错误修复
"""
import requests
import json

def test_create_session():
    """测试创建会话API"""
    print("=" * 60)
    print("测试创建新会话 - 422错误修复验证")
    print("=" * 60)

    base_url = "http://localhost:8089"

    # 测试1: 使用正确的JSON格式
    print("\n[测试1] 使用JSON请求体创建会话...")
    url = f"{base_url}/opencode/session"

    headers = {
        'Content-Type': 'application/json'
    }

    data = {
        'title': '测试会话',
        'mode': 'auto'
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            session = response.json()
            session_id = session.get('id')
            print(f"✅ 成功创建会话")
            print(f"   会话ID: {session_id}")
            print(f"   标题: {session.get('title')}")
            print(f"   模式: {session.get('metadata', {}).get('mode')}")
        else:
            print(f"❌ 创建失败")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # 测试2: 使用query参数（旧方式，应该失败）
    print("\n[测试2] 使用query参数创建会话（旧方式）...")
    url_with_params = f"{base_url}/opencode/session?title=测试会话2&mode=auto"

    try:
        response = requests.post(url_with_params, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 422:
            print(f"✅ 预期的422错误（验证失败）")
            print(f"   响应: {response.text[:100]}")
        elif response.status_code == 200:
            print(f"⚠ 意外成功（可能后端支持两种方式）")
        else:
            print(f"❓ 未知状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

    # 测试3: 测试不同模式
    print("\n[测试3] 测试不同模式...")
    modes = ['auto', 'plan', 'build']

    for mode in modes:
        print(f"\n测试模式: {mode}")
        data = {
            'title': f'{mode}模式测试',
            'mode': mode
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                session = response.json()
                print(f"  ✅ {mode}模式创建成功")
                print(f"     会话ID: {session.get('id')}")
            else:
                print(f"  ❌ {mode}模式创建失败: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {mode}模式请求失败: {e}")

    # 测试4: 测试浏览器端的fetch调用
    print("\n[测试4] 模拟浏览器fetch调用...")
    print("使用fetch POST with JSON body:")

    fetch_code = f"""
fetch('{url}', {{
  method: 'POST',
  headers: {{
    'Content-Type': 'application/json'
  }},
  body: JSON.stringify({{ title: '浏览器测试', mode: 'auto' }})
}})
.then(r => r.json())
.then(data => console.log('成功:', data))
.catch(err => console.error('失败:', err));
    """

    print(fetch_code)

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    print("\n修复说明:")
    print("前端 api-client.js 已修改:")
    print("  - 旧方式: POST /session?title=x&mode=y (query参数)")
    print("  - 新方式: POST /session with JSON body (请求体)")
    print("  - Content-Type: application/json")
    print("  - Body: { title: '...', mode: '...' }")

if __name__ == "__main__":
    test_create_session()
