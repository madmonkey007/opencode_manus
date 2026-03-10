# -*- coding: utf-8 -*-
"""
测试CORS安全修复
"""
import requests
import os

print("=== CORS安全测试 ===\n")

# 测试环境
base_url = "http://localhost:8999"
expected_origins = ["http://localhost:3000", "http://localhost:8999"]

# 测试用例
test_cases = [
    {
        "name": "测试允许的来源",
        "origin": "http://localhost:3000",
        "should_allow": True
    },
    {
        "name": "测试允许的来源（本地）",
        "origin": "http://localhost:8999",
        "should_allow": True
    },
    {
        "name": "测试恶意来源",
        "origin": "http://evil.com",
        "should_allow": False
    },
    {
        "name": "测试空来源",
        "origin": "",
        "should_allow": False
    }
]

for test in test_cases:
    print(f"TEST: {test['name']}")
    
    headers = {"Origin": test['origin']}
    if test['origin']:
        headers["Access-Control-Request-Method"] = "POST"
        headers["Access-Control-Request-Headers"] = "Content-Type"
    
    try:
        response = requests.options(
            f"{base_url}/health",
            headers=headers,
            timeout=5
        )
        
        # 检查CORS头部
        allowed_origin = response.headers.get("Access-Control-Allow-Origin", "")
        allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
        allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
        
        print(f"  - 允许的来源: {allowed_origin}")
        print(f"  - 允许的方法: {allowed_methods}")
        print(f"  - 允许的头部: {allowed_headers}")
        
        if test['should_allow']:
            if allowed_origin in expected_origins:
                print(f"  PASS - 来源被正确允许")
            else:
                print(f"  FAIL - 来源应被允许但被拒绝")
        else:
            if allowed_origin == "*":
                print(f"  FAIL - 来源应被拒绝但被允许（通配符）")
            elif allowed_origin in expected_origins:
                print(f"  FAIL - 来源应被拒绝但被允许")
            else:
                print(f"  PASS - 来源被正确拒绝")
                
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
    
    print()

# 检查环境变量配置
print("📋 环境变量配置:")
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8999")
print(f"  CORS_ORIGINS: {cors_origins}")

print("\n=== TEST COMPLETE ===")