"""
简化的opencode web性能测试
测试session创建的响应时间
"""
import asyncio
import aiohttp
import time
import json
from pathlib import Path

OPENCODE_WEB_URL = "http://127.0.0.1:8888"
TEST_NUM_RUNS = 5  # 减少到5次测试（节省时间）

async def test_opencode_web_create_session():
    """测试opencode web创建session的性能"""

    print("=" * 70)
    print("opencode web 性能测试")
    print("=" * 70)
    print(f"目标服务器: {OPENCODE_WEB_URL}")
    print(f"测试次数: {TEST_NUM_RUNS}")
    print()

    results = []

    for i in range(1, TEST_NUM_RUNS + 1):
        print(f"[运行 {i}/{TEST_NUM_RUNS}] 开始测试...")

        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                # 尝试创建session
                # 注意: API端点可能需要调整
                async with session.post(
                    f"{OPENCODE_WEB_URL}/session",
                    json={
                        "prompt": f"性能测试_{i}",
                        "mode": "build"
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        session_id = result.get("id")

                        # 等待一小段时间模拟真实使用
                        await asyncio.sleep(2)

                        total_time = time.time() - start_time

                        results.append({
                            "run": i,
                            "total_time": total_time,
                            "session_id": session_id,
                            "success": True
                        })

                        print(f"  ✅ 完成: {total_time:.2f}s (session: {session_id})")

                    else:
                        error_text = await resp.text()
                        total_time = time.time() - start_time

                        results.append({
                            "run": i,
                            "total_time": total_time,
                            "error": f"HTTP {resp.status}: {error_text[:100]}",
                            "success": False
                        })

                        print(f"  ❌ 失败: HTTP {resp.status}")

        except asyncio.TimeoutError:
            total_time = time.time() - start_time
            results.append({
                "run": i,
                "total_time": total_time,
                "error": "超时",
                "success": False
            })
            print(f"  ❌ 超时: {total_time:.2f}s")

        except Exception as e:
            total_time = time.time() - start_time
            results.append({
                "run": i,
                "total_time": total_time,
                "error": str(e),
                "success": False
            })
            print(f"  ❌ 异常: {e}")

        # 间隔时间
        if i < TEST_NUM_RUNS:
            await asyncio.sleep(1)

    # 统计分析
    print("\n" + "=" * 70)
    print("测试结果统计")
    print("=" * 70)

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    print(f"成功: {len(successful)}/{len(results)}")
    print(f"失败: {len(failed)}/{len(results)}")

    if successful:
        times = [r["total_time"] for r in successful]
        print(f"\n响应时间:")
        print(f"  平均: {sum(times)/len(times):.2f}s")
        print(f"  最小: {min(times):.2f}s")
        print(f"  最大: {max(times):.2f}s")
        print(f"  中位数: {sorted(times)[len(times)//2]:.2f}s")

        # 对比第一个和后续session
        if len(successful) >= 2:
            first_time = successful[0]["total_time"]
            avg_subsequent = sum(r["total_time"] for r in successful[1:]) / (len(successful) - 1)
            improvement = (1 - avg_subsequent / first_time) * 100

            print(f"\n关键发现:")
            print(f"  第一个session: {first_time:.2f}s")
            print(f"  后续session平均: {avg_subsequent:.2f}s")
            print(f"  改善幅度: {improvement:.1f}%")

    if failed:
        print(f"\n失败原因:")
        for r in failed[:3]:
            print(f"  运行{r['run']}: {r.get('error', 'Unknown')}")

    # 保存结果
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    results_file = results_dir / "opencode_web_performance.json"

    with open(results_file, "w") as f:
        json.dump({
            "target_url": OPENCODE_WEB_URL,
            "num_runs": TEST_NUM_RUNS,
            "results": results,
            "timestamp": time.time()
        }, f, indent=2)

    print(f"\n✅ 结果已保存到: {results_file}")

    return results

async def test_api_endpoints():
    """测试opencode web的API端点"""
    print("\n" + "=" * 70)
    print("API端点探索")
    print("=" * 70)

    endpoints_to_try = [
        "/",
        "/session",
        "/sessions",
        "/api/session",
        "/api/sessions",
        "/openapi.json",
        "/docs"
    ]

    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints_to_try:
            try:
                url = f"{OPENCODE_WEB_URL}{endpoint}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    print(f"  GET {endpoint}: {resp.status}")
            except:
                print(f"  GET {endpoint}: 失败")

async def main():
    """主函数"""
    try:
        # 1. 测试API端点
        await test_api_endpoints()

        # 2. 性能测试
        results = await test_opencode_web_create_session()

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
