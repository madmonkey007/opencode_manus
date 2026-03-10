"""
opencode web性能测试 - 简化版
测试session创建的响应时间
"""
import asyncio
import aiohttp
import time
import json
from pathlib import Path

OPENCODE_WEB_URL = "http://127.0.0.1:8888"
TEST_NUM_RUNS = 5  # 测试5次

async def test_opencode_web():
    """测试opencode web性能"""
    print("=" * 70)
    print("opencode web 性能测试")
    print("=" * 70)
    print(f"服务器: {OPENCODE_WEB_URL}")
    print(f"测试次数: {TEST_NUM_RUNS}")
    print()

    results = []

    for i in range(1, TEST_NUM_RUNS + 1):
        print(f"[运行 {i}/{TEST_NUM_RUNS}] 开始...")
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                # 尝试创建session
                async with session.post(
                    f"{OPENCODE_WEB_URL}/session",
                    json={"prompt": f"测试{i}", "mode": "build"},
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        session_id = result.get("id", "unknown")
                        total_time = time.time() - start_time
                        
                        results.append({
                            "run": i,
                            "time": total_time,
                            "session_id": session_id,
                            "success": True
                        })
                        print(f"  ✅ {total_time:.2f}s")
                    else:
                        error = await resp.text()
                        total_time = time.time() - start_time
                        results.append({
                            "run": i,
                            "time": total_time,
                            "error": f"HTTP {resp.status}",
                            "success": False
                        })
                        print(f"  ❌ HTTP {resp.status}")

        except Exception as e:
            total_time = time.time() - start_time
            results.append({
                "run": i,
                "time": total_time,
                "error": str(e)[:100],
                "success": False
            })
            print(f"  ❌ {str(e)[:50]}")

        await asyncio.sleep(1)

    # 统计
    print("\n" + "=" * 70)
    print("结果统计")
    print("=" * 70)
    
    successful = [r for r in results if r.get("success")]
    print(f"成功: {len(successful)}/{TEST_NUM_RUNS}")

    if successful:
        times = [r["time"] for r in successful]
        print(f"平均: {sum(times)/len(times):.2f}s")
        print(f"最小: {min(times):.2f}s")
        print(f"最大: {max(times):.2f}s")
        
        if len(successful) >= 2:
            first = successful[0]["time"]
            avg_rest = sum(r["time"] for r in successful[1:]) / (len(successful)-1)
            print(f"\n第1个session: {first:.2f}s")
            print(f"后续平均: {avg_rest:.2f}s")
            print(f"改善: {(1-avg_rest/first)*100:.1f}%")

    # 保存结果
    output_file = Path("D:/manus/opencode/opencode_web_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n结果已保存: {output_file}")

    return results

if __name__ == "__main__":
    asyncio.run(test_opencode_web())
