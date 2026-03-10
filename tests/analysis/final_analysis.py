"""
最终分析和决策生成脚本
整合所有调研数据，生成最终决策建议
"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


def load_all_reports() -> Dict:
    """
    加载所有测试报告
    """
    logger.info("加载所有测试报告...")

    reports = {}

    # Day 1: 性能报告
    perf_file = Path(__file__).parent.parent / "results" / "day1_performance.json"
    if perf_file.exists():
        with open(perf_file, "r") as f:
            reports["performance"] = json.load(f)
        logger.info("  ✅ 性能报告已加载")
    else:
        logger.warning("  ⚠️ 性能报告不存在")
        reports["performance"] = None

    # Day 2: API兼容性报告
    api_file = Path(__file__).parent.parent / "results" / "day2_api_compatibility.json"
    if api_file.exists():
        with open(api_file, "r") as f:
            reports["api_compatibility"] = json.load(f)
        logger.info("  ✅ API兼容性报告已加载")
    else:
        logger.warning("  ⚠️ API兼容性报告不存在")
        reports["api_compatibility"] = None

    # Day 2: 功能验证报告
    feature_file = Path(__file__).parent.parent / "results" / "day2_feature_verification.json"
    if feature_file.exists():
        with open(feature_file, "r") as f:
            reports["features"] = json.load(f)
        logger.info("  ✅ 功能验证报告已加载")
    else:
        logger.warning("  ⚠️ 功能验证报告不存在")
        reports["features"] = None

    return reports


def calculate_performance_improvement(perf_report: Dict) -> Dict:
    """
    计算性能提升
    """
    if not perf_report:
        return {"improvement": 0, "confidence": 0}

    current_stats = perf_report.get("current", {}).get("stats", {})
    web_stats = perf_report.get("web", {}).get("stats", {})

    if not current_stats or not web_stats:
        return {"improvement": 0, "confidence": 0}

    current_mean = current_stats.get("mean", 0)
    web_mean = web_stats.get("mean", 0)

    if current_mean == 0:
        return {"improvement": 0, "confidence": 0}

    improvement = (1 - web_mean / current_mean) * 100

    # 计算置信度（基于成功率）
    current_success_rate = current_stats.get("success_rate", 0)
    web_success_rate = web_stats.get("success_rate", 0)
    confidence = min(current_success_rate, web_success_rate) / 100

    return {
        "improvement": improvement,
        "confidence": confidence,
        "current_mean": current_mean,
        "web_mean": web_mean,
        "current_median": current_stats.get("median", 0),
        "web_median": web_stats.get("median", 0)
    }


def calculate_api_compatibility(api_report: Dict) -> Dict:
    """
    计算API兼容性
    """
    if not api_report:
        return {"compatibility": 0, "confidence": 0}

    summary = api_report.get("summary", {})
    compatibility = summary.get("compatibility_rate", 0)

    # 计算置信度（基于端点数量）
    total_endpoints = summary.get("current_endpoints", 0)
    confidence = min(total_endpoints / 20, 1.0)  # 至少20个端点才完全可信

    return {
        "compatibility": compatibility,
        "confidence": confidence,
        "total_endpoints": total_endpoints,
        "compatible": summary.get("compatible", 0),
        "not_in_web": summary.get("not_in_web", 0)
    }


def calculate_data_compatibility(features: Dict) -> Dict:
    """
    计算数据模型兼容性
    """
    if not features:
        return {"compatibility": 0, "details": {}}

    # 基于关键功能评估
    feature_weights = {
        "project_grouping": 0.3,  # 30%权重
        "file_upload": 0.2,       # 20%权重
        "message_parts": 0.5      # 50%权重（最重要）
    }

    compatibility = 0
    details = {}

    for feature, weight in feature_weights.items():
        result = features.get(feature)
        if result is True:
            compatibility += weight * 100
            details[feature] = {"status": "supported", "impact": 0}
        elif result is False:
            details[feature] = {"status": "not_supported", "impact": weight * 100}
        else:
            details[feature] = {"status": "unknown", "impact": weight * 50}

    return {
        "compatibility": compatibility,
        "details": details
    }


def estimate_migration_effort(api_report: Dict, features: Dict) -> Dict:
    """
    估算迁移工作量
    """
    # 需要重写的代码行数（估算）
    base_lines = 2600  # 项目总代码行数

    # 根据API兼容性调整
    if api_report:
        api_compat = api_report.get("summary", {}).get("compatibility_rate", 0)
        rewrite_ratio = 1 - (api_compat / 100)
        estimated_lines = int(base_lines * rewrite_ratio)
    else:
        estimated_lines = int(base_lines * 0.6)  # 默认60%需要重写

    # 根据功能不兼容度调整
    if features:
        unsupported_count = sum(1 for v in features.values() if v is False)
        estimated_lines += unsupported_count * 200  # 每个不兼容功能增加200行

    # 工作量估算
    lines_per_day = 200
    development_days = estimated_lines / lines_per_day
    testing_days = development_days * 0.5
    documentation_days = development_days * 0.2
    buffer_days = (development_days + testing_days + documentation_days) * 0.15

    total_days = development_days + testing_days + documentation_days + buffer_days

    # 成本估算（假设每天1000元）
    daily_cost = 1000
    total_cost = total_days * daily_cost

    return {
        "estimated_lines": estimated_lines,
        "rewrite_ratio": estimated_lines / base_lines * 100,
        "development_days": development_days,
        "testing_days": testing_days,
        "total_days": total_days,
        "total_cost": total_cost,
        "team_1_person": f"{total_days:.1f}天",
        "team_2_persons": f"{total_days * 0.7:.1f}天"
    }


def calculate_roi(perf_data: Dict, effort: Dict) -> Dict:
    """
    计算投资回报率
    """
    improvement = perf_data.get("improvement", 0)
    current_mean = perf_data.get("current_mean", 0)
    web_mean = perf_data.get("web_mean", 0)

    if current_mean == 0:
        return {"roi": 0, "payback_days": 999}

    # 时间节省（每次请求）
    time_saved_per_request = current_mean - web_mean

    # 假设每天100个请求
    daily_requests = 100
    daily_time_saved = time_saved_per_request * daily_requests / 60  # 分钟

    # 转换为成本（假设时间价值100元/小时）
    hourly_value = 100
    daily_cost_saved = daily_time_saved / 60 * hourly_value

    # ROI计算
    total_cost = effort.get("total_cost", 0)
    payback_days = total_cost / daily_cost_saved if daily_cost_saved > 0 else 999

    # 年化ROI
    annual_savings = daily_cost_saved * 365
    annual_roi = (annual_savings - total_cost) / total_cost * 100 if total_cost > 0 else 0

    return {
        "time_saved_per_request": time_saved_per_request,
        "daily_time_saved_minutes": daily_time_saved,
        "daily_cost_saved": daily_cost_saved,
        "annual_savings": annual_savings,
        "payback_days": payback_days,
        "annual_roi": annual_roi
    }


def make_decision(perf_data: Dict, api_data: Dict, data_data: Dict, effort: Dict, roi: Dict) -> str:
    """
    做出最终决策
    """
    improvement = perf_data.get("improvement", 0)
    api_compatibility = api_data.get("compatibility", 0)
    payback_days = roi.get("payback_days", 999)

    # 决策标准
    if (improvement >= 50 and
        api_compatibility >= 60 and
        payback_days <= 90):
        return "approve", "性能提升显著，API兼容性可接受，投资回报期合理"
    elif (improvement >= 30 and
          api_compatibility >= 50):
        return "cautious", "性能提升中等，需要权衡成本和收益"
    else:
        return "reject", "性能提升不足或API兼容性太低，不建议迁移"


def generate_final_report():
    """
    生成最终决策报告
    """
    logger.info("=" * 70)
    logger.info("Day 3: 最终分析和决策")
    logger.info("=" * 70)

    # 加载所有报告
    reports = load_all_reports()

    # 计算各项指标
    perf_data = calculate_performance_improvement(reports.get("performance"))
    api_data = calculate_api_compatibility(reports.get("api_compatibility"))
    data_data = calculate_data_compatibility(reports.get("features"))
    effort = estimate_migration_effort(reports.get("api_compatibility"), reports.get("features"))
    roi = calculate_roi(perf_data, effort)

    # 做出决策
    decision, reason = make_decision(perf_data, api_data, data_data, effort, roi)

    # 生成Markdown报告
    report = f"""# 迁移可行性调研 - 最终决策报告

**调研日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 执行摘要 (TL;DR)

### 最终决策

**{decision.upper()}**

**理由**: {reason}

---

## 1. 性能分析

### 性能提升

| 指标 | 当前实现 | opencode web | 提升 |
|------|----------|--------------|------|
| 平均响应时间 | {perf_data.get('current_mean', 0):.2f}s | {perf_data.get('web_mean', 0):.2f}s | **{perf_data.get('improvement', 0):.1f}%** |
| 中位数 | {perf_data.get('current_median', 0):.2f}s | {perf_data.get('web_median', 0):.2f}s | - |

### 评估

"""

    if perf_data.get("improvement", 0) >= 50:
        report += "✅ **性能显著提升** (>=50%)\n\n"
        report += f"opencode web比当前实现快{perf_data.get('improvement', 0):.1f}%，达到预期目标。\n\n"
    elif perf_data.get("improvement", 0) >= 30:
        report += "⚠️ **性能中等提升** (30-50%)\n\n"
        report += f"opencode web比当前实现快{perf_data.get('improvement', 0):.1f}%，性能提升有限。\n\n"
    else:
        report += "❌ **性能提升不足** (<30%)\n\n"
        report += f"opencode web仅比当前实现快{perf_data.get('improvement', 0):.1f}%，未达到预期。\n\n"

    report += """

---

## 2. API兼容性分析

### 兼容性统计

| 指标 | 数值 |
|------|------|
| API兼容性 | **{api_data.get('compatibility', 0):.1f}%** |
| 兼容端点 | {api_data.get('compatible', 0)}个 |
| 缺失端点 | {api_data.get('not_in_web', 0)}个 |

### 评估

"""

    if api_data.get("compatibility", 0) >= 80:
        report += "✅ **高度兼容** (>=80%)\n\n迁移风险低，大部分功能可以直接迁移。\n\n"
    elif api_data.get("compatibility", 0) >= 60:
        report += "⚠️ **中等兼容** (60-80%)\n\n迁移风险中等，部分功能需要特殊处理。\n\n"
    else:
        report += "❌ **低兼容** (<60%)\n\n迁移风险高，可能需要放弃部分功能。\n\n"

    report += """

---

## 3. 功能兼容性分析

### 关键功能支持

"""

    feature_names = {
        "project_grouping": "项目分组",
        "file_upload": "文件上传",
        "message_parts": "细粒度内容(message_parts)"
    }

    for key, name in feature_names.items():
        detail = data_data.get("details", {}).get(key, {})
        status = detail.get("status", "unknown")

        if status == "supported":
            report += f"### ✅ {name}\n\n支持该功能，无需额外开发。\n\n"
        elif status == "not_supported":
            report += f"### ❌ {name}\n\n不支持该功能，需要放弃或自己实现。\n\n"
        else:
            report += f"### ⚠️ {name}\n\n无法验证（测试失败或API规范获取失败）。\n\n"

    report += f"""
### 数据模型兼容性

**兼容性**: {data_data.get('compatibility', 0):.1f}%

---

## 4. 迁移成本估算

### 工作量

| 项目 | 估算 |
|------|------|
| 需要重写的代码 | {effort.get('estimated_lines', 0)}行 ({effort.get('rewrite_ratio', 0):.1f}%) |
| 开发时间 | {effort.get('development_days', 0):.1f}天 |
| 测试时间 | {effort.get('testing_days', 0):.1f}天 |
| 文档时间 | {effort.get('development_days', 0) * 0.2:.1f}天 |
| **总计（含缓冲）** | **{effort.get('total_days', 0):.1f}天** |

### 团队配置建议

- 1人开发: **{effort.get('team_1_person', 'N/A')}**
- 2人并行: **{effort.get('team_2_persons', 'N/A')}**

### 成本估算

**总成本**: ¥{effort.get('total_cost', 0):,.0f}

---

## 5. 成本效益分析

### 投资回报

| 指标 | 数值 |
|------|------|
| 每次请求节省时间 | {roi.get('time_saved_per_request', 0):.2f}秒 |
| 每天节省时间 | {roi.get('daily_time_saved_minutes', 0):.1f}分钟 |
| 每天节省成本 | ¥{roi.get('daily_cost_saved', 0):.2f} |
| 每年节省成本 | ¥{roi.get('annual_savings', 0):,.0f} |
| **投资回报期** | **{roi.get('payback_days', 0):.0f}天** |
| **年化ROI** | **{roi.get('annual_roi', 0):.1f}%** |

### 评估

"""

    if roi.get("payback_days", 999) <= 90:
        report += "✅ **投资回报期合理** (<=90天)\n\n"
        report += f"预计{roi.get('payback_days', 0):.0f}天收回投资，之后开始产生净收益。\n\n"
    elif roi.get("payback_days", 999) <= 180:
        report += "⚠️ **投资回报期较长** (90-180天)\n\n"
        report += f"预计{roi.get('payback_days', 0):.0f}天收回投资，需要权衡。\n\n"
    else:
        report += "❌ **投资回报期过长** (>180天)\n\n"
        report += f"预计{roi.get('payback_days', 0):.0f}天收回投资，成本高于收益。\n\n"

    report += """

---

## 6. 决策依据

### ✅ 支持迁移的因素

"""

    # 列出支持因素
    if perf_data.get("improvement", 0) >= 30:
        report += f"- 性能提升显著 ({perf_data.get('improvement', 0):.1f}%)\n"

    if api_data.get("compatibility", 0) >= 60:
        report += f"- API兼容性可接受 ({api_data.get('compatibility', 0):.1f}%)\n"

    if roi.get("payback_days", 999) <= 90:
        report += f"- 投资回报期合理 ({roi.get('payback_days', 0):.0f}天)\n"

    report += "\n### ❌ 反对迁移的因素\n\n"

    # 列出反对因素
    if effort.get("total_days", 0) > 15:
        report += f"- 工作量大 ({effort.get('total_days', 0):.1f}天)\n"

    if api_data.get("not_in_web", 0) > 3:
        report += f"- 缺失端点多 ({api_data.get('not_in_web', 0)}个)\n"

    if data_data.get("compatibility", 0) < 70:
        report += f"- 数据模型兼容性低 ({data_data.get('compatibility', 0):.1f}%)\n"

    report += "\n### ⚠️ 风险因素\n\n"
    report += "- 第一个session仍需较长时间（可能6-13秒）\n"
    report += "- 依赖官方项目路线（API可能变化）\n"
    report += "- 部署复杂度增加（需要管理opencode web服务器）\n"
    report += "- 数据迁移风险（测试环境已验证，生产环境需谨慎）\n\n"

    report += """

---

## 7. 最终建议

"""

    if decision == "approve":
        report += "### ✅ 批准迁移\n\n"
        report += "**建议采取的行动**:\n\n"
        report += "1. **第一阶段（Week 1）**: 实施POC（概念验证）\n"
        report += "   - 迁移单个API端点\n"
        report += "   - 验证性能提升真实\n"
        report += "   - 识别潜在问题\n\n"
        report += "2. **第二阶段（Week 2-3）**: 全面迁移\n"
        report += "   - 重写后端API调用逻辑\n"
        report += "   - 适配前端SSE处理\n"
        report += "   - 完整测试\n\n"
        report += "3. **第三阶段（Week 4）**: 部署和监控\n"
        report += "   - 灰度发布\n"
        report += "   - 性能监控\n"
        report += "   - 用户反馈收集\n\n"
    elif decision == "cautious":
        report += "### ⚠️ 谨慎考虑\n\n"
        report += "**建议采取的行动**:\n\n"
        report += "1. **方案A**: 继续调研\n"
        report += "   - 进行更详细的技术验证\n"
        report += "   - 评估是否有更简单的迁移方案\n\n"
        report += "2. **方案B**: 同时进行快速优化\n"
        report += "   - 实施方案B（提示词缓存、并行化、UI反馈）\n"
        report += "   - 立即获得1-2s提升\n"
        report += "   - 降低短期风险\n\n"
    else:
        report += "### ❌ 拒绝迁移\n\n"
        report += "**建议采取的行动**:\n\n"
        report += "1. **采用方案B（优化当前实现）**\n\n"
        report += "2. **具体措施**:\n"
        report += "   - 提示词缓存（0.5天，节省0.3-0.5s）\n"
        report += "   - 并行初始化（1天，节省0.5-1s）\n"
        report += "   - UI即时反馈（0.5天，感知改善80%）\n\n"
        report += "3. **预期收益**:\n"
        report += "   - 实际提升: 1-2s\n"
        report += "   - 用户感知改善: 80%\n"
        report += "   - 总成本: 2天\n"
        report += "   - 风险: 低\n\n"

    report += """

---

## 8. 附录

### 详细报告

- [Day 1: 性能测试详细报告](day1_performance.md)
- [Day 2: API兼容性详细报告](day2_api_compatibility.md)
- [测试数据](../tests/results/)

### 决策记录

**调研完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**最终决策**: {decision.upper()}

**批准人**: ___________

**备注**:

---

*本报告由自动化调研工具生成，基于实际测试数据*
"""

    # 保存报告
    reports_dir = Path(__file__).parent.parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / "FINAL_DECISION.md"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"\n✅ 最终决策报告已保存到: {report_file}")

    # 输出报告摘要
    print("\n" + "=" * 70)
    print(report)
    print("=" * 70)


# 设置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    try:
        generate_final_report()
    except Exception as e:
        logger.error(f"❌ 生成最终报告失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
