#!/usr/bin/env python3
"""
每日预测快速启动脚本
使用方法: python daily_predict.py
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from export_excel import run_predictions

def print_summary(results):
    """打印预测汇总，不导出Excel"""
    print("\n" + "=" * 60)
    print("📊 预测汇总")
    print("=" * 60)

    sorted_results = sorted(results, key=lambda x: x["confidence"], reverse=True)

    # 筛选推荐场次（最多3场，信心≥65%）
    recommended = [r for r in sorted_results if r["confidence"] >= 65][:3]
    if len(recommended) < 2:
        recommended = [r for r in sorted_results if r["confidence"] >= 60][:2]

    watch = [r for r in sorted_results if r not in recommended and r["confidence"] >= 50]
    wait = [r for r in sorted_results if r["confidence"] < 50]

    print(f"\n🎯 今日推荐 ({len(recommended)}场):")
    for r in recommended:
        print(f"   ⭐ {r['home_team']} vs {r['away_team']}")
        print(f"      推荐: {r['recommendation']} | 信心: {r['confidence']}%")

    if watch:
        print(f"\n👀 可关注 ({len(watch)}场):")
        for r in watch:
            print(f"   • {r['home_team']} vs {r['away_team']}: {r['recommendation']} ({r['confidence']}%)")

    if wait:
        print(f"\n⏸️ 观望 ({len(wait)}场):")
        for r in wait:
            print(f"   • {r['home_team']} vs {r['away_team']}: {r['confidence']}%")

    print(f"\n📊 共 {len(sorted_results)} 场比赛")

if __name__ == "__main__":
    print("🚀 启动每日足球预测...")
    results = run_predictions()
    print_summary(results)
    print("\n✅ 预测完成！如需Excel报告，请手动运行: python export_excel.py")
