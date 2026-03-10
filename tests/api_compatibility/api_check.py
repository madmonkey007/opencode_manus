"""
API兼容性检查脚本
对比当前实现和opencode web的API差异
"""
import asyncio
import aiohttp
import json
import logging
from pathlib import Path
from typing import Dict, List, Set
from benchmark.config import (
    logger,
    CURRENT_IMPLEMENTATION_URL,
    OPENCODE_WEB_URL,
    TEST_PROJECT_ID
)


async def fetch_openapi_spec(base_url: str) -> Dict:
    """
    获取OpenAPI规范
    """
    logger.info(f"获取OpenAPI规范: {base_url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/openapi.json",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    spec = await resp.json()
                    logger.info(f"  ✅ 成功获取规范")
                    return spec
                else:
                    logger.error(f"  ❌ 获取失败: {resp.status}")
                    return {}

    except Exception as e:
        logger.error(f"  ❌ 异常: {e}")
        return {}


def extract_endpoints_from_spec(spec: Dict) -> Set[tuple]:
    """
    从OpenAPI规范中提取端点
    返回: {(method, path), ...}
    """
    endpoints = set()

    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                endpoints.add((method.upper(), path))

    return endpoints


def extract_parameters(spec: Dict, path: str, method: str) -> Dict:
    """
    提取端点的参数信息
    """
    try:
        endpoint_spec = spec.get("paths", {}).get(path, {}).get(method.lower(), {})
        request_body = endpoint_spec.get("requestBody", {})
        content = request_body.get("content", {})
        json_schema = content.get("application/json", {}).get("schema", {})
        properties = json_schema.get("properties", {})

        return {
            "required": json_schema.get("required", []),
            "properties": list(properties.keys())
        }
    except:
        return {"required": [], "properties": []}


async def compare_api_endpoints():
    """
    对比API端点
    """
    logger.info("=" * 70)
    logger.info("Day 2: API兼容性检查")
    logger.info("=" * 70)

    # 获取两个API规范
    current_spec = await fetch_openapi_spec(CURRENT_IMPLEMENTATION_URL)
    web_spec = await fetch_openapi_spec(OPENCODE_WEB_URL)

    if not current_spec:
        logger.error("❌ 无法获取当前实现的API规范")
        return None

    if not web_spec:
        logger.error("❌ 无法获取opencode web的API规范")
        logger.error("这可能是因为:")
        logger.error("  1. opencode web服务器未启动")
        logger.error("  2. 端点路径不是/openapi.json")
        return None

    # 提取端点
    current_endpoints = extract_endpoints_from_spec(current_spec)
    web_endpoints = extract_endpoints_from_spec(web_spec)

    logger.info(f"\n当前实现端点数: {len(current_endpoints)}")
    logger.info(f"opencode web端点数: {len(web_endpoints)}")

    # 对比分析
    compatible = current_endpoints & web_endpoints
    not_in_web = current_endpoints - web_endpoints
    not_in_current = web_endpoints - current_endpoints

    compatibility_rate = len(compatible) / len(current_endpoints) * 100 if current_endpoints else 0

    logger.info(f"\n兼容端点数: {len(compatible)}")
    logger.info(f"仅在当前实现中: {len(not_in_web)}")
    logger.info(f"仅在opencode web中: {len(not_in_current)}")
    logger.info(f"兼容性比例: {compatibility_rate:.1f}%")

    # 详细对比参数
    param_comparison = {}
    for method, path in compatible:
        current_params = extract_parameters(current_spec, path, method)
        web_params = extract_parameters(web_spec, path, method)

        if current_params != web_params:
            param_comparison[(method, path)] = {
                "current": current_params,
                "web": web_params
            }

    # 生成报告
    report = {
        "summary": {
            "current_endpoints": len(current_endpoints),
            "web_endpoints": len(web_endpoints),
            "compatible": len(compatible),
            "not_in_web": len(not_in_web),
            "not_in_current": len(not_in_current),
            "compatibility_rate": compatibility_rate
        },
        "compatible": sorted(list(compatible)),
        "not_in_web": sorted(list(not_in_web)),
        "not_in_current": sorted(list(not_in_current)),
        "parameter_differences": param_comparison
    }

    # 保存结果
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)
    results_file = results_dir / "day2_api_compatibility.json"

    with open(results_file, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n✅ 结果已保存到: {results_file}")

    return report


async def verify_key_features():
    """
    验证关键功能
    """
    logger.info("\n" + "=" * 70)
    logger.info("验证关键功能")
    logger.info("=" * 70)

    results = {}

    # 1. 验证项目分组功能
    logger.info("\n[1/3] 验证项目分组功能")
    try:
        async with aiohttp.ClientSession() as session:
            # 检查是否支持project_id参数
            web_spec = await fetch_openapi_spec(OPENCODE_WEB_URL)

            if web_spec:
                # 查找session创建端点
                session_path = web_spec.get("paths", {}).get("/session", {})
                post_spec = session_path.get("post", {})
                request_body = post_spec.get("requestBody", {})
                content = request_body.get("content", {})
                json_schema = content.get("application/json", {}).get("schema", {})
                properties = json_schema.get("properties", {})

                has_project_id = "project_id" in properties

                if has_project_id:
                    logger.info("  ✅ opencode web支持project_id参数")
                    results["project_grouping"] = True
                else:
                    logger.warning("  ❌ opencode web不支持project_id参数")
                    logger.warning("     影响: 需要放弃项目分组功能或在前端实现虚拟分组")
                    results["project_grouping"] = False
            else:
                logger.warning("  ⚠️ 无法验证（API规范获取失败）")
                results["project_grouping"] = None

    except Exception as e:
        logger.error(f"  ❌ 验证失败: {e}")
        results["project_grouping"] = None

    # 2. 验证文件上传功能
    logger.info("\n[2/3] 验证文件上传功能")
    try:
        async with aiohttp.ClientSession() as session:
            # 检查是否有upload端点
            web_spec = await fetch_openapi_spec(OPENCODE_WEB_URL)

            if web_spec:
                has_upload = any(
                    "upload" in path.lower()
                    for path in web_spec.get("paths", {}).keys()
                )

                if has_upload:
                    logger.info("  ✅ opencode web支持文件上传")
                    results["file_upload"] = True
                else:
                    logger.warning("  ❌ opencode web不支持文件上传")
                    results["file_upload"] = False
            else:
                logger.warning("  ⚠️ 无法验证（API规范获取失败）")
                results["file_upload"] = None

    except Exception as e:
        logger.error(f"  ❌ 验证失败: {e}")
        results["file_upload"] = None

    # 3. 验证细粒度内容（message_parts）
    logger.info("\n[3/3] 验证细粒度内容功能")
    try:
        # 通过实际测试验证
        async with aiohttp.ClientSession() as session:
            # 创建一个测试session
            async with session.post(
                f"{OPENCODE_WEB_URL}/session",
                json={"prompt": "测试", "mode": "build"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    session_id = result.get("id")

                    # 监听SSE事件
                    async with session.get(
                        f"{OPENCODE_WEB_URL}/session/{session_id}/events",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        event_count = 0
                        has_parts = False

                        async for line in resp.content:
                            if line:
                                event_count += 1
                                line_str = line.decode('utf-8', errors='ignore')

                                # 检查是否包含parts相关的字段
                                if any(keyword in line_str.lower() for keyword in
                                       ['part_type', 'part_id', 'message_delta']):
                                    has_parts = True
                                    break

                                if event_count >= 10:  # 只检查前10个事件
                                    break

                        if has_parts:
                            logger.info("  ✅ SSE事件包含细粒度parts")
                            results["message_parts"] = True
                        else:
                            logger.warning("  ❌ SSE事件不包含细粒度parts")
                            results["message_parts"] = False
                else:
                    logger.warning("  ⚠️ 无法验证（创建session失败）")
                    results["message_parts"] = None

    except Exception as e:
        logger.error(f"  ❌ 验证失败: {e}")
        results["message_parts"] = None

    # 保存结果
    results_dir = Path(__file__).parent.parent / "results"
    results_file = results_dir / "day2_feature_verification.json"

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n✅ 功能验证结果已保存到: {results_file}")

    return results


async def generate_api_report():
    """
    生成API兼容性报告
    """
    # 执行对比
    comparison = await compare_api_endpoints()

    if not comparison:
        logger.error("无法生成报告（API对比失败）")
        return

    # 验证功能
    features = await verify_key_features()

    # 生成Markdown报告
    report = f"""# Day 2: API兼容性检查报告

## 执行摘要

- **API兼容性**: {comparison['summary']['compatibility_rate']:.1f}%
- **兼容端点**: {comparison['summary']['compatible']}个
- **缺失端点**: {comparison['summary']['not_in_web']}个
- **新增端点**: {comparison['summary']['not_in_current']}个

---

## 1. API端点对比

### 统计摘要

| 指标 | 当前实现 | opencode web |
|------|----------|--------------|
| 端点总数 | {comparison['summary']['current_endpoints']} | {comparison['summary']['web_endpoints']} |
| 兼容端点 | {comparison['summary']['compatible']} | - |
| 独有端点 | {comparison['summary']['not_in_web']} | {comparison['summary']['not_in_current']} |

### 兼容的端点 ({len(comparison['compatible'])}个)

"""

    for method, path in sorted(comparison['compatible']):
        report += f"- **{method} {path}**\n"

    report += f"""

### 仅在当前实现中的端点 ({len(comparison['not_in_web'])}个)

**这些功能需要放弃或自己实现**

"""

    for method, path in sorted(comparison['not_in_web']):
        report += f"- **{method} {path}**\n"

    report += f"""

### 仅在opencode web中的端点 ({len(comparison['not_in_current'])}个)

**这些是新功能，可以考虑添加**

"""

    for method, path in sorted(comparison['not_in_current']):
        report += f"- **{method} {path}**\n"

    report += """

---

## 2. 关键功能验证

"""

    feature_names = {
        "project_grouping": "项目分组",
        "file_upload": "文件上传",
        "message_parts": "细粒度内容(message_parts)"
    }

    for key, name in feature_names.items():
        result = features.get(key)
        if result is True:
            report += f"### ✅ {name}\n\n支持该功能\n\n"
        elif result is False:
            report += f"### ❌ {name}\n\n不支持该功能，需要放弃或自己实现\n\n"
        else:
            report += f"### ⚠️ {name}\n\n无法验证（API规范获取失败或测试失败）\n\n"

    report += """

---

## 3. 兼容性评估

"""

    compatibility = comparison['summary']['compatibility_rate']
    if compatibility >= 80:
        report += "### ✅ 高度兼容 (>=80%)\n\n迁移风险低，大部分功能可以直接迁移。\n"
    elif compatibility >= 60:
        report += "### ⚠️ 中等兼容 (60-80%)\n\n迁移风险中等，部分功能需要特殊处理。\n"
    else:
        report += "### ❌ 低兼容 (<60%)\n\n迁移风险高，可能需要放弃部分功能。\n"

    report += f"""

## 4. 迁移建议

### 需要处理的不兼容端点

"""

    if comparison['not_in_web']:
        report += "**优先级分类**:\n\n"

        # 按功能重要性分类
        critical = [ep for ep in comparison['not_in_web'] if 'project' in ep[1].lower()]
        high = [ep for ep in comparison['not_in_web'] if 'upload' in ep[1].lower() or 'file' in ep[1].lower()]
        medium = [ep for ep in comparison['not_in_web'] if 'event' in ep[1].lower() or 'message' in ep[1].lower()]
        low = [ep for ep in comparison['not_in_web'] if ep not in critical + high + medium]

        if critical:
            report += "#### 🔴 高优先级: 项目管理功能\n"
            for method, path in critical:
                report += f"- {method} {path}\n"
            report += "\n建议: 在前端实现虚拟分组，或放弃该功能\n\n"

        if high:
            report += "#### 🟡 中优先级: 文件操作\n"
            for method, path in high:
                report += f"- {method} {path}\n"
            report += "\n建议: 评估是否为必需功能，考虑替代方案\n\n"

        if medium:
            report += "#### 🟢 低优先级: 其他功能\n"
            for method, path in medium:
                report += f"- {method} {path}\n"
            report += "\n"
    else:
        report += "\n✅ 所有端点都兼容，无需特殊处理\n\n"

    report += """

---

## 5. 下一步行动

"""

    if compatibility >= 60:
        report += "1. ✅ API兼容性可接受，继续Day 3数据模型分析\n"
        report += "2. ⚠️ 需要评估不兼容功能的影响范围\n"
        report += "3. 📝 准备功能迁移方案\n"
    else:
        report += "1. ❌ API兼容性不足，建议重新考虑迁移\n"
        report += "2. 🔄 考虑方案B（优化当前实现）\n"

    report += "\n---\n\n"
    report += "**生成时间**: " + str(asyncio.get_event_loop().time()) + "\n"

    # 保存报告
    reports_dir = Path(__file__).parent.parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / "day2_api_compatibility.md"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"\n✅ API兼容性报告已保存到: {report_file}")

    # 输出报告摘要
    print("\n" + report)


async def main():
    """主函数"""
    try:
        await generate_api_report()
    except Exception as e:
        logger.error(f"❌ 生成报告失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
