#!/usr/bin/env python3
"""
批量预测脚本 - 预测多场比赛并汇总推荐
"""
from football_predictor import FootballPredictor
from team_translator import translate_team_name

# 所有比赛列表
MATCHES = [
    # 欧联杯
    {"home": "Nottingham Forest", "away": "Porto", "league": "soccer_uefa_europa_league", "time": "03:00"},
    {"home": "Real Betis", "away": "SC Braga", "league": "soccer_uefa_europa_league", "time": "03:00"},
    {"home": "Aston Villa", "away": "Bologna", "league": "soccer_uefa_europa_league", "time": "03:00"},

    # 欧会杯
    {"home": "Fiorentina", "away": "Crystal Palace", "league": "soccer_uefa_europa_conference_league", "time": "03:00"},
    {"home": "Strasbourg", "away": "FSV Mainz 05", "league": "soccer_uefa_europa_conference_league", "time": "03:00"},
    {"home": "AEK Athens", "away": "Rayo Vallecano", "league": "soccer_uefa_europa_conference_league", "time": "03:00"},

    # 解放者杯
    {"home": "Palmeiras-SP", "away": "Sporting Cristal", "league": "soccer_conmebol_copa_libertadores", "time": "06:00"},
    {"home": "Flamengo-RJ", "away": "Independiente Medellín", "league": "soccer_conmebol_copa_libertadores", "time": "08:30"},
]

def main():
    predictor = FootballPredictor()
    results = []

    print("=" * 70)
    print("🏆 批量比赛预测")
    print("=" * 70)

    for i, match in enumerate(MATCHES, 1):
        home_cn = translate_team_name(match["home"])
        away_cn = translate_team_name(match["away"])

        print(f"\n[{i}/{len(MATCHES)}] 预测: {home_cn} vs {away_cn}")

        try:
            result = predictor.predict(match["home"], match["away"], match["league"])

            if result:
                # 提取关键信息
                consensus = predictor.reports
                asian_value = consensus.get("asian", {}).get("value_score", 0)
                overunder_value = consensus.get("overunder", {}).get("overunder_value_score", 0)

                # 获取最终推荐
                if asian_value > overunder_value:
                    market = "让球盘"
                    recommendation = consensus.get("asian", {}).get("recommendation", "N/A")
                    value = asian_value
                else:
                    market = "大小球"
                    bias = consensus.get("overunder", {}).get("market_bias", "N/A")
                    line = consensus.get("overunder", {}).get("mainstream_total_line", 2.5)
                    recommendation = f"{bias} {line}球"
                    value = overunder_value

                # 获取信心分数
                base_score = (
                    consensus.get("stats", {}).get("confidence_weight", 50) * 0.4 +
                    consensus.get("tactics", {}).get("tactical_match_score", 50) * 0.25 +
                    consensus.get("sentiment", {}).get("market_sentiment_score", 50) * 0.2 +
                    (100 - consensus.get("upset", {}).get("upset_risk_score", 50)) * 0.15
                )
                market_factor = value / 100 if value > 0 else 0.5
                final_confidence = base_score * (0.7 + 0.3 * market_factor)
                final_confidence = max(5, min(90, final_confidence))

                results.append({
                    "match": f"{home_cn} vs {away_cn}",
                    "time": match["time"],
                    "market": market,
                    "recommendation": recommendation,
                    "value": value,
                    "confidence": round(final_confidence, 1),
                    "asian_value": asian_value,
                    "overunder_value": overunder_value
                })
                print(f"   ✅ 推荐: {recommendation} | 信心: {final_confidence:.1f}%")
            else:
                print(f"   ❌ 无数据")
                results.append({
                    "match": f"{home_cn} vs {away_cn}",
                    "time": match["time"],
                    "market": "N/A",
                    "recommendation": "无数据",
                    "value": 0,
                    "confidence": 0,
                    "asian_value": 0,
                    "overunder_value": 0
                })

        except Exception as e:
            print(f"   ❌ 错误: {e}")
            results.append({
                "match": f"{home_cn} vs {away_cn}",
                "time": match["time"],
                "market": "N/A",
                "recommendation": "预测失败",
                "value": 0,
                "confidence": 0,
                "asian_value": 0,
                "overunder_value": 0
            })

    # 汇总报告
    print("\n" + "=" * 70)
    print("📊 预测汇总报告")
    print("=" * 70)

    # 按信心分数排序
    sorted_results = sorted(results, key=lambda x: x["confidence"], reverse=True)

    print("\n🏆 最终推荐（按信心分数排序）:\n")

    for i, r in enumerate(sorted_results, 1):
        if r["confidence"] > 0:
            print(f"{i}. {r['match']} ({r['time']})")
            print(f"   推荐市场: {r['market']}")
            print(f"   推荐选项: {r['recommendation']}")
            print(f"   价值分数: {r['value']}/100")
            print(f"   信心分数: {r['confidence']}%")
            print()

    # 筛选高信心推荐
    high_confidence = [r for r in sorted_results if r["confidence"] >= 55]

    print("=" * 70)
    print("🎯 最值得投注的推荐 (信心≥55%):")
    print("=" * 70)

    if high_confidence:
        for i, r in enumerate(high_confidence, 1):
            print(f"\n{i}. {r['match']} ({r['time']})")
            print(f"   推荐: {r['recommendation']}")
            print(f"   信心: {r['confidence']}%")
    else:
        print("\n⚠️ 今晚没有高信心推荐")

    print("\n" + "=" * 70)
    print("⚠️ 免责声明: 本报告仅供娱乐参考，不构成投注建议")
    print("=" * 70)


if __name__ == "__main__":
    main()
