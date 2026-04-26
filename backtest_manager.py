#!/usr/bin/env python3
"""
回测追踪系统 - 记录预测结果与实际赛果，支持事后校准
============================================================================
职责：
  1. 每次预测后自动记录到 backtest.csv
  2. 赛后手动/自动回填实际结果
  3. 提供统计分析：总准确率、按联赛、按信心带、按市场、按信号清晰度
  4. 支持权重重校准的数据导出
"""

import csv
import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class BacktestManager:
    """回测管理器 — 单例模式，确保所有预测写入同一个 backtest.csv"""

    _instance = None
    _csv_path = None

    # backtest.csv 列定义
    COLUMNS = [
        "prediction_id",
        "timestamp",
        "match_date",
        "league",
        "home_team",
        "away_team",
        "recommended_market",
        "recommendation",
        "confidence",
        "signal_clarity",
        "ml_prediction",
        "ml_confidence",
        "upset_risk",
        "risk_level",
        "debate_triggered",
        "verdict_type",
        "market_value",
        "actual_result",
        "correct",
        "result_timestamp",
        "notes",
    ]

    def __new__(cls, csv_dir: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, csv_dir: str = None):
        if self._initialized:
            return

        if csv_dir is None:
            csv_dir = os.path.dirname(os.path.abspath(__file__))

        self._csv_path = os.path.join(csv_dir, "backtest.csv")
        self._ensure_csv_exists()
        self._initialized = True

    def _ensure_csv_exists(self):
        """确保 backtest.csv 存在且有正确的表头"""
        if not os.path.exists(self._csv_path):
            with open(self._csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.COLUMNS)
                writer.writeheader()
            print(f"📊 回测系统已初始化: {self._csv_path}")

    def _generate_prediction_id(self, home: str, away: str, match_date: str) -> str:
        """生成唯一的预测 ID: home_away_matchdate"""
        safe_home = home.replace(" ", "_").replace("/", "_")[:20]
        safe_away = away.replace(" ", "_").replace("/", "_")[:20]
        date_part = match_date[:10] if match_date else datetime.now().strftime("%Y%m%d")
        return f"{safe_home}_{safe_away}_{date_part}"

    def record_prediction(self, prediction_dict: Dict) -> str:
        """
        记录一条新预测到 backtest.csv。

        Args:
            prediction_dict: _generate_prediction_dict() 返回的字典（已扩展）

        Returns:
            prediction_id
        """
        home = prediction_dict.get("home_team_cn", "")
        away = prediction_dict.get("away_team_cn", "")
        match_date = prediction_dict.get("match_date", "")
        ts = prediction_dict.get("timestamp", datetime.now().isoformat())

        pid = self._generate_prediction_id(home, away, match_date)

        consensus = prediction_dict.get("consensus", {})
        ml = prediction_dict.get("ml_prediction", {})
        upset = prediction_dict.get("upset_risk", 0)

        row = {
            "prediction_id": pid,
            "timestamp": ts,
            "match_date": match_date,
            "league": prediction_dict.get("league", ""),
            "home_team": home,
            "away_team": away,
            "recommended_market": consensus.get("recommended_market", ""),
            "recommendation": consensus.get("recommendation", ""),
            "confidence": consensus.get("confidence", 0),
            "signal_clarity": consensus.get("signal_clarity", ""),
            "ml_prediction": ml.get("result", ""),
            "ml_confidence": ml.get("confidence", 0),
            "upset_risk": upset if isinstance(upset, (int, float)) else 0,
            "risk_level": prediction_dict.get("risk_level", ""),
            "debate_triggered": str(consensus.get("debate_triggered", False)),
            "verdict_type": consensus.get("verdict_type", ""),
            "market_value": consensus.get("market_value", 0),
            "actual_result": "pending",
            "correct": "",
            "result_timestamp": "",
            "notes": "",
        }

        # 追加写入
        file_exists = os.path.exists(self._csv_path) and os.path.getsize(self._csv_path) > 0
        with open(self._csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.COLUMNS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        print(f"📊 回测记录已保存: {pid} (信心: {row['confidence']}%, 市场: {row['recommended_market']})")
        return pid

    def update_result(
        self,
        prediction_id: str,
        actual_result: str,
        correct: bool,
        notes: str = "",
    ) -> bool:
        """
        回填一条预测的实际结果。

        Args:
            prediction_id: 预测ID（支持模糊匹配）
            actual_result: 实际结果描述 (如: "主胜 2-1", "客胜 0-3", "void")
            correct: 预测是否正确
            notes: 备注

        Returns:
            是否成功更新
        """
        if not os.path.exists(self._csv_path):
            print("❌ backtest.csv 不存在")
            return False

        rows = self._read_all()
        updated = False

        for row in rows:
            pid = row.get("prediction_id", "")
            # 支持模糊匹配：完全匹配 或 包含匹配
            if pid == prediction_id or prediction_id in pid:
                row["actual_result"] = actual_result
                row["correct"] = str(correct)
                row["result_timestamp"] = datetime.now().isoformat()
                row["notes"] = notes
                updated = True
                break

        if updated:
            self._write_all(rows)
            if isinstance(correct, bool):
                status = "✅ 正确" if correct else "❌ 错误"
            else:
                status = "🤔 待确认"
            print(f"📊 结果已回填: {prediction_id} → {actual_result} ({status})")
        else:
            print(f"⚠️ 未找到预测: {prediction_id}")

        return updated

    def batch_update_results(self, results: List[Dict]) -> int:
        """
        批量回填结果。

        Args:
            results: [{"prediction_id": ..., "actual_result": ..., "correct": ..., "notes": ...}, ...]

        Returns:
            成功更新的数量
        """
        count = 0
        for r in results:
            if self.update_result(
                r["prediction_id"],
                r["actual_result"],
                r["correct"],
                r.get("notes", ""),
            ):
                count += 1
        return count

    def get_all_predictions(self, with_results_only: bool = False) -> List[Dict]:
        """获取所有预测记录"""
        if not os.path.exists(self._csv_path):
            return []
        rows = self._read_all()
        if with_results_only:
            rows = [r for r in rows if r.get("actual_result", "pending") != "pending"]
        return rows

    def get_pending_predictions(self) -> List[Dict]:
        """获取所有等待回填结果的预测"""
        return [r for r in self.get_all_predictions() if r.get("actual_result", "pending") == "pending"]

    def get_stats(self) -> Dict:
        """获取完整的回测统计报告"""
        all_rows = self.get_all_predictions()
        resolved = [r for r in all_rows if r.get("actual_result", "pending") != "pending"]

        if not resolved:
            return {
                "total_predictions": len(all_rows),
                "resolved": 0,
                "message": "尚无已结算的预测结果",
            }

        correct_count = sum(1 for r in resolved if r.get("correct", "").lower() == "true")
        overall_accuracy = correct_count / len(resolved) * 100

        # 按联赛分组
        by_league = defaultdict(lambda: {"total": 0, "correct": 0})
        for r in resolved:
            league = r.get("league", "未知")
            by_league[league]["total"] += 1
            if r.get("correct", "").lower() == "true":
                by_league[league]["correct"] += 1

        league_stats = {}
        for league, counts in sorted(by_league.items()):
            acc = counts["correct"] / counts["total"] * 100 if counts["total"] > 0 else 0
            league_stats[league] = {
                "total": counts["total"],
                "correct": counts["correct"],
                "accuracy": round(acc, 1),
            }

        # 按信心带分组
        by_confidence = defaultdict(lambda: {"total": 0, "correct": 0})
        for r in resolved:
            conf = float(r.get("confidence", 0))
            if conf >= 70:
                band = "70-90 (高信心)"
            elif conf >= 55:
                band = "55-69 (中高)"
            elif conf >= 40:
                band = "40-54 (中低)"
            else:
                band = "5-39 (低信心)"
            by_confidence[band]["total"] += 1
            if r.get("correct", "").lower() == "true":
                by_confidence[band]["correct"] += 1

        conf_stats = {}
        for band in ["70-90 (高信心)", "55-69 (中高)", "40-54 (中低)", "5-39 (低信心)"]:
            counts = by_confidence.get(band, {"total": 0, "correct": 0})
            acc = counts["correct"] / counts["total"] * 100 if counts["total"] > 0 else 0
            conf_stats[band] = {
                "total": counts["total"],
                "correct": counts["correct"],
                "accuracy": round(acc, 1),
            }

        # 按市场分组
        by_market = defaultdict(lambda: {"total": 0, "correct": 0})
        for r in resolved:
            market = r.get("recommended_market", "未知")
            by_market[market]["total"] += 1
            if r.get("correct", "").lower() == "true":
                by_market[market]["correct"] += 1

        market_stats = {}
        for market, counts in sorted(by_market.items()):
            acc = counts["correct"] / counts["total"] * 100 if counts["total"] > 0 else 0
            market_stats[market] = {
                "total": counts["total"],
                "correct": counts["correct"],
                "accuracy": round(acc, 1),
            }

        # 按信号清晰度分组
        by_clarity = defaultdict(lambda: {"total": 0, "correct": 0})
        for r in resolved:
            clarity = r.get("signal_clarity", "未知")
            by_clarity[clarity]["total"] += 1
            if r.get("correct", "").lower() == "true":
                by_clarity[clarity]["correct"] += 1

        clarity_stats = {}
        for clarity, counts in sorted(by_clarity.items()):
            acc = counts["correct"] / counts["total"] * 100 if counts["total"] > 0 else 0
            clarity_stats[clarity] = {
                "total": counts["total"],
                "correct": counts["correct"],
                "accuracy": round(acc, 1),
            }

        # 按辩论裁决类型分组
        by_verdict = defaultdict(lambda: {"total": 0, "correct": 0})
        for r in resolved:
            verdict = r.get("verdict_type", "none")
            if verdict:
                by_verdict[verdict]["total"] += 1
                if r.get("correct", "").lower() == "true":
                    by_verdict[verdict]["correct"] += 1

        verdict_stats = {}
        for verdict, counts in sorted(by_verdict.items()):
            acc = counts["correct"] / counts["total"] * 100 if counts["total"] > 0 else 0
            verdict_stats[verdict] = {
                "total": counts["total"],
                "correct": counts["correct"],
                "accuracy": round(acc, 1),
            }

        return {
            "total_predictions": len(all_rows),
            "resolved": len(resolved),
            "pending": len(all_rows) - len(resolved),
            "overall_accuracy": round(overall_accuracy, 1),
            "correct": correct_count,
            "wrong": len(resolved) - correct_count,
            "by_league": league_stats,
            "by_confidence_band": conf_stats,
            "by_market": market_stats,
            "by_signal_clarity": clarity_stats,
            "by_verdict_type": verdict_stats,
            "generated_at": datetime.now().isoformat(),
        }

    def export_weight_calibration_data(self) -> List[Dict]:
        """
        导出用于权重重校准的数据。
        每行包含：各智能体分数、ML信心、冷门风险、最终推荐、是否正确。
        """
        resolved = [
            r
            for r in self.get_all_predictions()
            if r.get("actual_result", "pending") != "pending"
        ]
        # backtest.csv 目前不存储各智能体分数，需要扩展
        # 此方法为占位，等 prediction_dict 扩展后再实现
        return resolved

    def print_stats(self):
        """打印格式化的统计报告"""
        stats = self.get_stats()

        print(f"\n{'=' * 60}")
        print(f"📊 回测统计报告")
        print(f"{'=' * 60}")

        if stats.get("message"):
            print(f"\n   {stats['message']}")
            return

        print(f"\n   总预测: {stats['total_predictions']} | 已结算: {stats['resolved']} | 待结算: {stats['pending']}")
        print(f"   总准确率: {stats['overall_accuracy']}% ({stats['correct']}/{stats['resolved']})")

        # 按信心带
        print(f"\n   📈 按信心带:")
        for band, s in stats.get("by_confidence_band", {}).items():
            bar = "█" * int(s["accuracy"] / 5) if s["total"] > 0 else ""
            print(f"      {band:20s}: {s['accuracy']:5.1f}% ({s['correct']}/{s['total']}) {bar}")

        # 按市场
        print(f"\n   🎯 按市场:")
        for market, s in stats.get("by_market", {}).items():
            print(f"      {market:15s}: {s['accuracy']:5.1f}% ({s['correct']}/{s['total']})")

        # 按信号清晰度
        print(f"\n   📶 按信号清晰度:")
        for clarity, s in stats.get("by_signal_clarity", {}).items():
            print(f"      {clarity:10s}: {s['accuracy']:5.1f}% ({s['correct']}/{s['total']})")

        # 按联赛
        if stats.get("by_league"):
            print(f"\n   🏟️ 按联赛:")
            for league, s in sorted(stats["by_league"].items()):
                print(f"      {league:25s}: {s['accuracy']:5.1f}% ({s['correct']}/{s['total']})")

        # 按辩论裁决
        if stats.get("by_verdict_type"):
            print(f"\n   ⚖️ 按辩论裁决:")
            verdict_names = {
                "strong_consensus": "强共识",
                "weak_consensus": "弱共识",
                "divided": "严重分歧",
            }
            for verdict, s in stats["by_verdict_type"].items():
                name = verdict_names.get(verdict, verdict)
                print(f"      {name:10s}: {s['accuracy']:5.1f}% ({s['correct']}/{s['total']})")

        print(f"\n{'=' * 60}")

    # ─── 内部辅助方法 ───

    def _read_all(self) -> List[Dict]:
        """读取 backtest.csv 全部行"""
        with open(self._csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_all(self, rows: List[Dict]):
        """覆写 backtest.csv"""
        with open(self._csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.COLUMNS)
            writer.writeheader()
            writer.writerows(rows)


# ─── 快捷函数 ───

def get_backtest_manager(csv_dir: str = None) -> BacktestManager:
    """获取回测管理器单例"""
    return BacktestManager(csv_dir)


# ─── 自测 ───

if __name__ == "__main__":
    bm = BacktestManager()

    # 模拟记录一条预测
    test_pred = {
        "home_team_cn": "曼联",
        "away_team_cn": "利物浦",
        "match_date": "2026-04-26T15:00:00Z",
        "league": "英超",
        "timestamp": datetime.now().isoformat(),
        "consensus": {
            "recommended_market": "让球盘",
            "recommendation": "曼联 -0.5",
            "confidence": 72.5,
            "signal_clarity": "清晰",
            "market_value": 78,
            "debate_triggered": False,
            "verdict_type": "strong_consensus",
        },
        "ml_prediction": {"result": "主胜", "confidence": 80},
        "upset_risk": 25,
        "risk_level": "低",
    }

    pid = bm.record_prediction(test_pred)
    print(f"\n记录预测: {pid}")

    # 模拟回填结果
    bm.update_result(pid, "主胜 2-1", True, "曼联主场轻取利物浦")

    # 打印统计
    bm.print_stats()
