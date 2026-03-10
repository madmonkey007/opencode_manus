"""
opencode web API端点探索
系统性地测试所有可能的API端点
"""
import asyncio
import aiohttp
import time

BASE_URL = "http://127.0.0.1:8888"

async def test_endpoint(method, path, data=None):
    """测试单个端点"""
    url = f"{BASE_URL}{path}"
    
    try:
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return {
                        "method": method,
                        "path": path,
                        "status": resp.status,
                        "headers": dict(resp.headers),
                        "body": await resp.text()[:500]  # 前500字符
                    }
            elif method == "POST":
                async with session.post(
                    url,
                    json=data or {},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return {
                        "method": method,
                        "path": path,
                        "status": resp.status,
                        "headers": dict(resp.headers),
                        "body": await resp.text()[:500]
                    }
    except Exception as e:
        return {
            "method": method,
            "path": path,
            "error": str(e)
        }

async def main():
    """主函数"""
    print("=" * 70)
    print("opencode web API端点探索")
    print("=" * 70)
    print(f"目标服务器: {BASE_URL}")
    print()

    # 测试的端点列表
    endpoints_to_test = [
        # OpenAPI规范
        ("GET", "/openapi.json"),
        ("GET", "/openapi.yaml"),
        ("GET", "/docs"),
        ("GET", "/swagger.json"),
        
        # Session相关（多种可能的路径）
        ("GET", "/session"),
        ("POST", "/session"),
        ("GET", "/sessions"),
        ("POST", "/sessions"),
        ("GET", "/api/session"),
        ("POST", "/api/session"),
        ("GET", "/api/sessions"),
        ("POST", "/api/sessions"),
        ("GET", "/v1/session"),
        ("POST", "/v1/session"),
        ("GET", "/api/v1/session"),
        ("POST", "/api/v1/session"),
        
        # 根路径
        ("GET", "/"),
        ("GET", "/api"),
        ("GET", "/health"),
    ]

    results = []

    for method, path in endpoints_to_test:
        print(f"测试: {method} {path}... ", end="", flush=True)
        
        result = await test_endpoint(method, path)
        results.append(result)
        
        if "error" in result:
            print(f"❌ 错误: {result['error'][:50]}")
        elif result["status"] == 404:
            print(f"⚠️  404 Not Found")
        elif result["status"] == 200:
            print(f"✅ 200 OK")
        elif result["status"] == 405:
            print(f"🟡 405 Method Not Allowed")
        else:
            print(f"ℹ️  {result['status']}")
    
    # 分析结果
    print("\n" + "=" * 70)
    print("结果汇总")
    print("=" * 70)
    
    successful = [r for r in results if r.get("status") == 200]
    not_found = [r for r in results if r.get("status") == 404]
    errors = [r for r in results if "error" in r]
    
    print(f"\n成功 (200): {len(successful)}")
    for r in successful:
        print(f"  ✅ {r['method']} {r['path']}")
        # 如果响应体包含API信息，显示前100字符
        if r.get("body") and len(r["body"]) > 50:
            print(f"     响应: {r['body'][:100]}...")
    
    print(f"\n不存在 (404): {len(not_found)}")
    
    print(f"\n错误: {len(errors)}")
    for r in errors:
        print(f"  ❌ {r['method']} {r['path']}: {r['error'][:50]}")
    
    # 保存结果
    import json
    from pathlib import Path
    
    output_file = Path("D:/manus/opencode/api_exploration_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.time(),
            "base_url": BASE_URL,
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 详细结果已保存到: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
