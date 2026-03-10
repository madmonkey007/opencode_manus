"""
opencode web API端点探索 - 完整版
"""
import asyncio
import aiohttp
import time
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8888"

async def test_endpoint(method, path, data=None):
    """测试单个端点"""
    url = f"{BASE_URL}{path}"
    
    try:
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    body = await resp.text()
                    return {
                        "method": method,
                        "path": path,
                        "status": resp.status,
                        "headers": dict(resp.headers),
                        "body": body[:1000] if body else ""
                    }
            elif method == "POST":
                async with session.post(
                    url,
                    json=data or {},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    body = await resp.text()
                    return {
                        "method": method,
                        "path": path,
                        "status": resp.status,
                        "headers": dict(resp.headers),
                        "body": body[:1000] if body else ""
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
    
    endpoints = [
        ("GET", "/openapi.json"),
        ("GET", "/docs"),
        ("GET", "/"),
        ("POST", "/session"),
        ("POST", "/api/session"),
        ("GET", "/health"),
    ]
    
    results = []
    for method, path in endpoints:
        print(f"测试: {method} {path}...", flush=True)
        result = await test_endpoint(method, path, {"prompt": "test"})
        results.append(result)
        
        if "error" in result:
            print(f"  ❌ {result['error'][:50]}")
        elif result["status"] == 200:
            print(f"  ✅ 200 OK")
        else:
            print(f"  ⚠️  {result['status']}")
    
    # 保存结果
    output = Path("D:/manus/opencode/api_results.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n结果已保存: {output}")
    
    # 汇总
    successful = [r for r in results if r.get("status") == 200]
    print(f"\n成功端点: {len(successful)}")
    for r in successful:
        print(f"  ✅ {r['method']} {r['path']}")
        if r.get("body") and len(r["body"]) > 20:
            print(f"     预览: {r['body'][:100]}")

if __name__ == "__main__":
    asyncio.run(main())
