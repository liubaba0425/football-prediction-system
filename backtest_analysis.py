#!/usr/bin/env python3
"""
回测分析仪表盘
============================================================================
对 backtest.csv 进行全面分析，输出可操作的优化建议。

使用方法：
  python backtest_analysis.py              # 完整分析报告
  python backtest_analysis.py --json       # JSON 格式输出（供程序调用）
  python backtest_analysis.py --export     # 导出权重校准数据
  python backtest_analysis.py --chart      # ASCII 可视化
"""

import os
import sys
import json
import csv
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

from backtest_manager import BacktestManager


def load_data(bm: BacktestManager) -> List[Dict]:
    """加载所有已结算的预测数据"""
    return bm.get_all_predictions(with_results_only=True)


def analyze_overall(resolved: List[Dict]) -> Dict:
    """总体分析"""
    total = len(resolved)
    correct = sum(1 for r in resolved if r.get("correct", "").lower() == "true")
    wrong = total - correct
    accuracy = correct / total * 100 if total > 0 else 0
    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy": round(accuracy, 1),
    }


def analyze_by_league(resolved: List[Dict]) -> Dict:
    """按联赛分析"""
    groups = defaultdict(lambda: {"total": 0, "correct": 0, "confidences": []})
    for r in resolved:
        league = r.get("league", "未知")
        groups[league]["total"] += 1
        if r.get("correct", "").lower() == "true":
            groups[league]["correct"] += 1
        try:
            groups[league]["confidences"].append(float(r.get("confidence", 0)))
        except (ValueError, TypeError):
            pass

    result = {}
    for league, data in sorted(groups.items(), key=lambda x: -x[1]["total"]):
        acc = data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
        avg_conf = sum(data["confidences"]) / len(data["confidences"]) if data["confidences"] else 0
        result[league] = {
            "total": data["total"],
            "correct": data["correct"],
            "accuracy": round(acc, 1),
            "avg_confidence": round(avg_conf, 1),
            "calibration": round(acc - avg_conf, 1),  # 正=低估, 负=过度自信
        }
    return result


def analyze_by_confidence_band(resolved: List[Dict]) -> Dict:
    """信心校准分析 — 高信心是否真的更准？"""
    bands = [
        (70, 90, "70-90% 高信心"),
        (60, 69, "60-69% 中高"),
        (50, 59, "50-59% 中等"),
        (40, 49, "40-49% 中低"),
        (5, 39, "5-39% 低信心"),
    ]
    result = {}
    for low, high, label in bands:
        subset = [
            r for r in resolved
            if low <= float(r.get("confidence", 0)) <= high
        ]
        correct = sum(1 for r in subset if r.get("correct", "").lower() == "true")
        total = len(subset)
        acc = correct / total * 100 if total > 0 else 0
        result[label] = {
            "total": total,
            "correct": correct,
            "accuracy": round(acc, 1),
            "expected_accuracy": round((low + high) / 2, 1),
            "calibration": round(acc - (low + high) / 2, 1),
        }
    return result


def analyze_by_market(resolved: List[Dict]) -> Dict:
    """按市场类型分析"""
    groups = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in resolved:
        market = r.get("recommended_market", "未知")
        groups[market]["total"] += 1
        if r.get("correct", "").lower() == "true":
            groups[market]["correct"] += 1

    result = {}
    for market, data in sorted(groups.items()):
        acc = data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
        result[market] = {
            "total": data["total"],
            "correct": data["correct"],
            "accuracy": round(acc, 1),
        }
    return result


def analyze_by_clarity(resolved: List[Dict]) -> Dict:
    """信号清晰度验证"""
    groups = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in resolved:
        clarity = r.get("signal_clarity", "未知")
        if not clarity:
            clarity = "未知"
        groups[clarity]["total"] += 1
        if r.get("correct", "").lower() == "true":
            groups[clarity]["correct"] += 1

    result = {}
    for clarity in ["清晰", "模糊", "无信号", "未知"]:
        data = groups.get(clarity, {"total": 0, "correct": 0})
        acc = data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
        if data["total"] > 0:
            result[clarity] = {
                "total": data["total"],
                "correct": data["correct"],
                "accuracy": round(acc, 1),
            }
    return result


def analyze_debate_impact(resolved: List[Dict]) -> Dict:
    """辩论机制效果分析"""
    debated = [r for r in resolved if r.get("debate_triggered", "").lower() == "true"]
    not_debated = [r for r in resolved if r.get("debate_triggered", "").lower() != "true"]

    d_correct = sum(1 for r in debated if r.get("correct", "").lower() == "true")
    nd_correct = sum(1 for r in not_debated if r.get("correct", "").lower() == "true")

    # 按裁决类型
    by_verdict = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in debated:
        verdict = r.get("verdict_type", "unknown")
        by_verdict[verdict]["total"] += 1
        if r.get("correct", "").lower() == "true":
            by_verdict[verdict]["correct"] += 1

    verdict_detail = {}
    verdict_names = {
        "strong_consensus": "强共识",
        "weak_consensus": "弱共识",
        "divided": "严重分歧",
    }
    for v, data in by_verdict.items():
        acc = data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
        verdict_detail[verdict_names.get(v, v)] = {
            "total": data["total"],
            "correct": data["correct"],
            "accuracy": round(acc, 1),
        }

    return {
        "debated_total": len(debated),
        "debated_accuracy": round(d_correct / len(debated) * 100, 1) if debated else 0,
        "not_debated_total": len(not_debated),
        "not_debated_accuracy": round(nd_correct / len(not_debated) * 100, 1) if not_debated else 0,
        "debate_helps": "辩论有效" if (debated and not_debated and d_correct / len(debated) > nd_correct / len(not_debated)) else "需优化",
        "by_verdict": verdict_detail,
    }


def analyze_recent_trend(resolved: List[Dict], window: int = 20) -> Dict:
    """最近 N 场的准确率趋势"""
    # 按时间排序
    sorted_preds = sorted(resolved, key=lambda r: r.get("timestamp", ""))
    recent = sorted_preds[-window:] if len(sorted_preds) >= window else sorted_preds
    correct = sum(1 for r in recent if r.get("correct", "").lower() == "true")
    older = sorted_preds[:-window] if len(sorted_preds) > window else []
    older_correct = sum(1 for r in older if r.get("correct", "").lower() == "true")

    recent_acc = correct / len(recent) * 100 if recent else 0
    older_acc = older_correct / len(older) * 100 if older else 0

    return {
        "recent_total": len(recent),
        "recent_accuracy": round(recent_acc, 1),
        "older_accuracy": round(older_acc, 1),
        "trend": "📈 提升" if recent_acc > older_acc + 3 else ("📉 下降" if recent_acc < older_acc - 3 else "➡️ 持平"),
    }


def generate_optimization_suggestions(analysis: Dict) -> List[str]:
    """基于分析结果生成优化建议"""
    suggestions = []

    overall = analysis.get("overall", {})
    acc = overall.get("accuracy", 0)

    if acc < 50:
        suggestions.append("🔴 总体准确率 < 50%，系统需要根本性改进。检查ML模型是否过拟合、特征是否泄漏。")
    elif acc < 55:
        suggestions.append("🟡 总体准确率偏低(50-55%)，考虑调整智能体权重或增加赔率变动特征。")
    elif acc < 60:
        suggestions.append("🟢 总体准确率中等(55-60%)，持续优化特征工程可进一步提升。")
    else:
        suggestions.append("✅ 总体准确率良好(>60%)，系统处于健康状态。")

    # 信心校准
    conf_bands = analysis.get("by_confidence_band", {})
    for band, data in conf_bands.items():
        cal = data.get("calibration", 0)
        if cal < -10 and data["total"] >= 3:
            suggestions.append(f"🔴 {band} 严重过度自信 (偏差{cal:.0f}%)，需降低该区间权重或增加辩论惩罚。")
        elif cal < -5 and data["total"] >= 3:
            suggestions.append(f"🟡 {band} 略有过度自信 (偏差{cal:.0f}%)。")

    # 市场
    markets = analysis.get("by_market", {})
    asian = markets.get("让球盘", {})
    overunder = markets.get("大小球", {})
    if asian and overunder:
        if asian.get("accuracy", 0) > overunder.get("accuracy", 0) + 5:
            suggestions.append(f"💡 让球盘准确率({asian['accuracy']}%) 明显高于大小球({overunder['accuracy']}%)，考虑优先推让球盘。")
        elif overunder.get("accuracy", 0) > asian.get("accuracy", 0) + 5:
            suggestions.append(f"💡 大小球准确率({overunder['accuracy']}%) 明显高于让球盘({asian['accuracy']}%)，考虑优先推大小球。")

    # 信号清晰度
    clarity = analysis.get("by_signal_clarity", {})
    clear = clarity.get("清晰", {})
    fuzzy = clarity.get("模糊", {})
    if clear.get("accuracy", 0) > 0 and fuzzy.get("accuracy", 0) > 0:
        if clear["accuracy"] > fuzzy["accuracy"] + 10:
            suggestions.append(f"✅ 信号清晰度有效：'清晰'({clear['accuracy']}%) >> '模糊'({fuzzy['accuracy']}%)，继续信任此标签。")
        else:
            suggestions.append(f"⚠️ 信号清晰度区分度不足，'清晰'和'模糊'准确率接近，需优化判断阈值。")

    # 辩论
    debate = analysis.get("debate_impact", {})
    if debate.get("debate_helps") == "需优化":
        suggestions.append("⚠️ 辩论机制未提升准确率，考虑调整辩论触发条件或惩罚力度。")

    # 联赛
    leagues = analysis.get("by_league", {})
    top_leagues = sorted(leagues.items(), key=lambda x: x[1]["total"], reverse=True)[:5]
    for league, data in top_leagues:
        if data["total"] >= 5 and data["accuracy"] < 45:
            suggestions.append(f"🔴 {league} 准确率仅{data['accuracy']}% ({data['correct']}/{data['total']})，考虑调整该联赛的分析逻辑。")

    return suggestions


def print_report(analysis: Dict):
    """打印格式化的分析报告"""
    print(f"\n{'='*60}")
    print(f"📊 回测分析仪表盘")
    print(f"{'='*60}")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 总体
    overall = analysis.get("overall", {})
    print(f"\n{'─'*60}")
    print(f"📈 总体表现")
    print(f"{'─'*60}")
    acc = overall.get("accuracy", 0)
    bar = "█" * int(acc / 2) + "░" * (50 - int(acc / 2))
    print(f"   准确率: {acc}% [{bar}]")
    print(f"   正确/错误/总计: {overall.get('correct', 0)}/{overall.get('wrong', 0)}/{overall.get('total', 0)}")

    # 趋势
    trend = analysis.get("recent_trend", {})
    if trend:
        print(f"\n   最近{trend.get('recent_total', 0)}场: {trend.get('recent_accuracy', 0)}% "
              f"| 之前: {trend.get('older_accuracy', 0)}% {trend.get('trend', '')}")

    # 信心校准
    print(f"\n{'─'*60}")
    print(f"📊 信心校准")
    print(f"{'─'*60}")
    print(f"   {'信心带':<20s} {'场次':>5s} {'准确率':>8s} {'预期':>8s} {'偏差':>8s}")
    print(f"   {'─'*50}")
    for band, data in analysis.get("by_confidence_band", {}).items():
        cal = data.get("calibration", 0)
        cal_str = f"{cal:+.1f}"
        flag = "⚠️" if cal < -5 else ("✅" if cal > 5 else "  ")
        print(f"   {band:<20s} {data['total']:>5d} {data['accuracy']:>7.1f}% {data['expected_accuracy']:>7.1f}% {cal_str:>8s} {flag}")

    # 按市场
    print(f"\n{'─'*60}")
    print(f"🎯 按市场类型")
    print(f"{'─'*60}")
    for market, data in analysis.get("by_market", {}).items():
        bar = "█" * int(data["accuracy"] / 5) if data["total"] > 0 else ""
        print(f"   {market:<15s}: {data['accuracy']:5.1f}% ({data['correct']}/{data['total']}) {bar}")

    # 按信号清晰度
    print(f"\n{'─'*60}")
    print(f"📶 信号清晰度验证")
    print(f"{'─'*60}")
    for clarity, data in analysis.get("by_signal_clarity", {}).items():
        bar = "█" * int(data["accuracy"] / 5) if data["total"] > 0 else ""
        print(f"   {clarity:<10s}: {data['accuracy']:5.1f}% ({data['correct']}/{data['total']}) {bar}")

    # 按联赛 (Top 10)
    print(f"\n{'─'*60}")
    print(f"🏟️ 按联赛 (按场次排序 Top 10)")
    print(f"{'─'*60}")
    leagues = sorted(
        analysis.get("by_league", {}).items(),
        key=lambda x: x[1]["total"],
        reverse=True,
    )[:10]
    for league, data in leagues:
        bar = "█" * int(data["accuracy"] / 5) if data["total"] > 0 else ""
        cal = data.get("calibration", 0)
        cal_flag = "⚠️" if cal < -8 else ""
        print(f"   {league[:25]:<25s}: {data['accuracy']:5.1f}% ({data['correct']:>2d}/{data['total']:<2d}) "
              f"均信{data['avg_confidence']:.0f}% {cal_flag} {bar}")

    # 辩论机制
    debate = analysis.get("debate_impact", {})
    if debate.get("debated_total", 0) > 0:
        print(f"\n{'─'*60}")
        print(f"⚖️ 辩论机制效果")
        print(f"{'─'*60}")
        print(f"   触发辩论: {debate['debated_total']}场, 准确率 {debate['debated_accuracy']}%")
        print(f"   未触发:   {debate['not_debated_total']}场, 准确率 {debate['not_debated_accuracy']}%")
        print(f"   结论: {debate['debate_helps']}")
        print(f"   按裁决类型:")
        for v, d in debate.get("by_verdict", {}).items():
            print(f"      {v:10s}: {d['accuracy']:5.1f}% ({d['correct']}/{d['total']})")

    # 优化建议
    suggestions = analysis.get("suggestions", [])
    if suggestions:
        print(f"\n{'─'*60}")
        print(f"💡 优化建议 ({len(suggestions)}条)")
        print(f"{'─'*60}")
        for i, s in enumerate(suggestions, 1):
            print(f"   {i}. {s}")

    print(f"\n{'='*60}")


def run_analysis(bm: BacktestManager = None) -> Dict:
    """运行完整分析并返回结果字典"""
    if bm is None:
        bm = BacktestManager()

    resolved = load_data(bm)

    if not resolved:
        print("⚠️ 没有已结算的预测数据。请先通过 retrofill_results.py --interactive 回填结果。")
        return {"error": "no_resolved_predictions"}

    analysis = {
        "overall": analyze_overall(resolved),
        "by_league": analyze_by_league(resolved),
        "by_confidence_band": analyze_by_confidence_band(resolved),
        "by_market": analyze_by_market(resolved),
        "by_signal_clarity": analyze_by_clarity(resolved),
        "debate_impact": analyze_debate_impact(resolved),
        "recent_trend": analyze_recent_trend(resolved),
    }
    analysis["suggestions"] = generate_optimization_suggestions(analysis)
    return analysis


def export_weight_calibration():
    """导出权重重校准所需的原始数据"""
    bm = BacktestManager()
    resolved = load_data(bm)

    if not resolved:
        print("⚠️ 无数据可导出")
        return

    output_path = os.path.join(os.path.dirname(bm._csv_path), "weight_calibration.csv")
    fields = [
        "league", "confidence", "signal_clarity", "recommended_market",
        "debate_triggered", "verdict_type", "correct",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(resolved)

    print(f"✅ 校准数据已导出: {output_path} ({len(resolved)} 条)")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="回测分析仪表盘")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--export", action="store_true", help="导出权重校准数据")
    parser.add_argument("--chart", action="store_true", help="ASCII 可视化（同默认输出）")

    args = parser.parse_args()

    if args.export:
        export_weight_calibration()
        return

    analysis = run_analysis()

    if "error" in analysis:
        return

    if args.json:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
    else:
        print_report(analysis)


if __name__ == "__main__":
    main()
