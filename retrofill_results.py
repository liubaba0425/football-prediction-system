#!/usr/bin/env python3
"""
历史预测结果回填工具
============================================================================
功能：
  1. 扫描现有 prediction_*.txt 文件，提取元数据导入 backtest.csv
  2. 交互式模式：逐一展示待回填的预测，让用户输入实际赛果
  3. 批量模式：从 results.txt 文件批量导入结果

使用方法：
  # 扫描并导入历史预测到 backtest.csv
  python retrofill_results.py --scan

  # 交互式回填（逐一确认赛果）
  python retrofill_results.py --interactive

  # 从文件批量回填
  python retrofill_results.py --batch results.txt

  # 查看待回填列表
  python retrofill_results.py --pending

results.txt 格式（每行一条）：
  match_keyword | actual_result | correct | notes
  例: 曼联_利物浦 | 主胜 2-1 | true | 曼联主场轻取
  例: 尤文_博洛尼亚 | 主胜 3-0 | true |
"""

import os
import re
import sys
import csv
from datetime import datetime
from typing import Dict, List, Optional

from backtest_manager import BacktestManager


def parse_prediction_txt(filepath: str) -> Optional[Dict]:
    """
    解析预测 .txt 文件，提取关键元数据。

    返回包含以下字段的字典：
      home_team, away_team, league, match_date, recommended_market,
      recommendation, confidence, signal_clarity, timestamp, filename
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  ⚠️ 无法读取 {filepath}: {e}")
        return None

    result = {"filename": os.path.basename(filepath)}

    # 比赛信息: 📅 比赛: 曼联 vs 利物浦
    match = re.search(r"📅\s*比赛:\s*(.+?)\s+vs\s+(.+?)$", content, re.MULTILINE)
    if match:
        result["home_team"] = match.group(1).strip()
        result["away_team"] = match.group(2).strip()

    # 时间: ⏰ 时间: 2026-04-19T18:45:00Z
    time_match = re.search(r"⏰\s*时间:\s*(.+?)$", content, re.MULTILINE)
    if time_match:
        result["match_date"] = time_match.group(1).strip()

    # 联赛: 📊 联赛: 意大利甲级联赛
    league_match = re.search(r"📊\s*联赛:\s*(.+?)$", content, re.MULTILINE)
    if league_match:
        result["league"] = league_match.group(1).strip()

    # 推荐市场: 推荐市场: 让球盘
    market_match = re.search(r"推荐市场:\s*(.+?)$", content, re.MULTILINE)
    if market_match:
        result["recommended_market"] = market_match.group(1).strip()

    # 推荐选项: 推荐选项: Juventus -1.25
    rec_match = re.search(r"推荐选项:\s*(.+?)$", content, re.MULTILINE)
    if rec_match:
        result["recommendation"] = rec_match.group(1).strip()

    # 信心分数: 💪 信心分数: 75.5%
    conf_match = re.search(r"💪\s*信心分数:\s*([\d.]+)%", content)
    if conf_match:
        result["confidence"] = float(conf_match.group(1))

    # 信号清晰度: 📊 信号清晰度: 清晰
    clarity_match = re.search(r"📊\s*信号清晰度:\s*(.+?)$", content, re.MULTILINE)
    if clarity_match:
        result["signal_clarity"] = clarity_match.group(1).strip()
    else:
        result["signal_clarity"] = ""

    # 报告生成时间: 报告生成时间: 2026-04-19 15:07:39
    ts_match = re.search(r"报告生成时间:\s*(.+?)$", content, re.MULTILINE)
    if ts_match:
        result["timestamp"] = ts_match.group(1).strip()

    # 冷门风险
    risk_match = re.search(r"冷门风险:\s*\S+\s*\((\d+)/100\)", content)
    if risk_match:
        result["upset_risk"] = int(risk_match.group(1))
    else:
        result["upset_risk"] = 0

    risk_level_match = re.search(r"冷门风险:\s*(\S+)", content)
    if risk_level_match:
        result["risk_level"] = risk_level_match.group(1).strip()
    else:
        result["risk_level"] = ""

    # ML预测（如果有）
    ml_match = re.search(r"ML预测.*?:\s*(.+?)$", content, re.MULTILINE)
    if ml_match:
        result["ml_prediction"] = ml_match.group(1).strip()

    # 辩论触发
    result["debate_triggered"] = "⚖️ 辩论记录" in content

    # 裁决类型（从裁决理由推断）
    if "强共识" in content or "各方分析师观点一致" in content:
        result["verdict_type"] = "strong_consensus"
    elif "弱共识" in content or "分析师存在分歧" in content:
        result["verdict_type"] = "weak_consensus"
    elif "严重分歧" in content or "建议谨慎" in content:
        result["verdict_type"] = "divided"
    else:
        result["verdict_type"] = ""

    return result


def scan_and_import(predictions_dir: str = None):
    """
    扫描所有 prediction_*.txt 文件，导入到 backtest.csv。
    跳过已存在的预测（按 prediction_id 去重）。
    """
    if predictions_dir is None:
        predictions_dir = os.path.dirname(os.path.abspath(__file__))

    # 查找所有预测文件
    txt_files = []
    for f in os.listdir(predictions_dir):
        if f.startswith("prediction_") and f.endswith(".txt"):
            txt_files.append(os.path.join(predictions_dir, f))

    if not txt_files:
        print("❌ 未找到任何 prediction_*.txt 文件")
        return

    print(f"📂 找到 {len(txt_files)} 个预测文件，开始解析...\n")

    bm = BacktestManager()
    existing_ids = {r["prediction_id"] for r in bm.get_all_predictions()}

    imported = 0
    skipped = 0
    errors = 0

    for i, filepath in enumerate(sorted(txt_files)):
        filename = os.path.basename(filepath)
        print(f"  [{i+1}/{len(txt_files)}] {filename}...", end=" ")

        parsed = parse_prediction_txt(filepath)
        if not parsed or not parsed.get("home_team"):
            print("❌ 解析失败")
            errors += 1
            continue

        # 构建 prediction_id
        home = parsed.get("home_team", "")
        away = parsed.get("away_team", "")
        match_date = parsed.get("match_date", "")
        safe_home = home.replace(" ", "_").replace("/", "_")[:20]
        safe_away = away.replace(" ", "_").replace("/", "_")[:20]
        date_part = match_date[:10] if match_date else "unknown"
        pid = f"{safe_home}_{safe_away}_{date_part}"

        if pid in existing_ids:
            print("⏭️ 已存在")
            skipped += 1
            continue

        # 构建 prediction_dict 用于回测记录
        pred_dict = {
            "home_team_cn": home,
            "away_team_cn": away,
            "league": parsed.get("league", ""),
            "match_date": match_date,
            "timestamp": parsed.get("timestamp", datetime.now().isoformat()),
            "ml_prediction": {
                "result": parsed.get("ml_prediction", ""),
                "confidence": 0,
            },
            "upset_risk": parsed.get("upset_risk", 0),
            "risk_level": parsed.get("risk_level", ""),
            "consensus": {
                "recommended_market": parsed.get("recommended_market", ""),
                "recommendation": parsed.get("recommendation", ""),
                "confidence": parsed.get("confidence", 0),
                "signal_clarity": parsed.get("signal_clarity", ""),
                "market_value": 0,
                "market_detail": {},
                "debate_triggered": parsed.get("debate_triggered", False),
                "verdict_type": parsed.get("verdict_type", ""),
            },
        }

        bm.record_prediction(pred_dict)
        existing_ids.add(pid)
        imported += 1
        print(f"✅ 导入 (信心: {parsed.get('confidence', '?')}%)")

    print(f"\n{'='*50}")
    print(f"📊 导入完成: {imported} 条新增 | {skipped} 条已存在 | {errors} 条失败")
    print(f"   总计预测: {len(existing_ids)} 条 | 待回填结果: {len(bm.get_pending_predictions())} 条")


def interactive_fill():
    """交互式回填：逐一展示待回填预测，让用户输入实际赛果"""
    bm = BacktestManager()
    pending = bm.get_pending_predictions()

    if not pending:
        print("✅ 没有待回填的预测！全都已结算。")
        return

    print(f"📋 共 {len(pending)} 条预测待回填结果\n")

    for i, pred in enumerate(pending):
        pid = pred.get("prediction_id", "?")
        home = pred.get("home_team", "?")
        away = pred.get("away_team", "?")
        league = pred.get("league", "?")
        match_date = pred.get("match_date", "?")
        rec = pred.get("recommendation", "?")
        conf = pred.get("confidence", "?")
        market = pred.get("recommended_market", "?")

        print(f"\n{'─'*55}")
        print(f"  [{i+1}/{len(pending)}] {home} vs {away}")
        print(f"  联赛: {league} | 时间: {match_date}")
        print(f"  推荐: {rec} ({market}) | 信心: {conf}%")

        # 输入实际结果
        result = input(f"\n  实际结果 (如 '主胜 2-1', '客胜 0-3', '平局 1-1', 回车跳过): ").strip()
        if not result:
            print("  ⏭️ 跳过")
            continue

        # 判断是否正确
        correct_input = input(f"  预测正确? (y/n/回车跳过): ").strip().lower()
        if not correct_input:
            print("  ⏭️ 跳过")
            continue

        correct = correct_input in ("y", "yes", "true", "1")
        notes = input(f"  备注 (可选): ").strip()

        bm.update_result(pid, result, correct, notes)

    # 打印更新后的统计
    bm.print_stats()


def batch_fill(batch_file: str):
    """
    批量回填：从文件读取结果。

    文件格式（每行一条）：
      match_keyword | actual_result | correct | notes(可选)

    例：
      曼联_利物浦 | 主胜 2-1 | true | 曼联主场轻取
      尤文_博洛尼亚 | 主胜 3-0 | true |
    """
    if not os.path.exists(batch_file):
        print(f"❌ 文件不存在: {batch_file}")
        return

    bm = BacktestManager()
    all_preds = bm.get_all_predictions()

    results = []
    with open(batch_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                print(f"  ⚠️ 行 {line_num}: 格式错误，跳过: {line}")
                continue

            keyword = parts[0]
            actual_result = parts[1]
            correct = parts[2].lower() in ("true", "yes", "y", "1", "正确")
            notes = parts[3] if len(parts) > 3 else ""

            # 模糊匹配 prediction_id
            matched = None
            for pred in all_preds:
                pid = pred.get("prediction_id", "")
                if keyword in pid or pid in keyword:
                    matched = pred
                    break

            if not matched:
                print(f"  ⚠️ 未找到匹配预测: {keyword}")
                continue

            results.append({
                "prediction_id": matched["prediction_id"],
                "actual_result": actual_result,
                "correct": correct,
                "notes": notes,
            })

    if not results:
        print("❌ 没有可回填的结果")
        return

    print(f"📋 准备回填 {len(results)} 条结果...")
    confirm = input("确认? (y/n): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("已取消")
        return

    count = bm.batch_update_results(results)
    print(f"\n✅ 成功回填 {count} 条结果")

    bm.print_stats()


def show_pending():
    """显示所有待回填的预测"""
    bm = BacktestManager()
    pending = bm.get_pending_predictions()

    if not pending:
        print("✅ 没有待回填的预测")
        return

    print(f"📋 共 {len(pending)} 条预测待回填:\n")
    for i, pred in enumerate(pending):
        print(f"  [{i+1}] {pred.get('prediction_id', '?')}")
        print(f"      {pred.get('home_team', '?')} vs {pred.get('away_team', '?')}")
        print(f"      联赛: {pred.get('league', '?')} | 推荐: {pred.get('recommendation', '?')} | 信心: {pred.get('confidence', '?')}%")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="历史预测结果回填工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python retrofill_results.py --scan           # 扫描并导入所有历史预测
  python retrofill_results.py --interactive     # 交互式逐一回填赛果
  python retrofill_results.py --batch results.txt  # 从文件批量回填
  python retrofill_results.py --pending         # 查看待回填列表
  python retrofill_results.py --scan --interactive  # 先导入再回填
        """,
    )
    parser.add_argument("--scan", action="store_true", help="扫描 prediction_*.txt 导入 backtest.csv")
    parser.add_argument("--interactive", action="store_true", help="交互式回填实际赛果")
    parser.add_argument("--batch", type=str, metavar="FILE", help="从文件批量回填结果")
    parser.add_argument("--pending", action="store_true", help="显示待回填预测列表")
    parser.add_argument("--dir", type=str, help="预测文件目录（默认当前目录）")

    args = parser.parse_args()

    # 如果没有参数，显示帮助
    if not any([args.scan, args.interactive, args.batch, args.pending]):
        parser.print_help()
        return

    if args.scan:
        scan_and_import(args.dir)

    if args.interactive:
        interactive_fill()

    if args.batch:
        batch_fill(args.batch)

    if args.pending:
        show_pending()


if __name__ == "__main__":
    main()
