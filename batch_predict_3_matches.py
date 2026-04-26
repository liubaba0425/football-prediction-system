#!/usr/bin/env python3
"""
预测前3场比赛 - 测试用
"""
from football_predictor import FootballPredictor
from team_translator import translate_team_name
import time
from datetime import datetime

# 前3场比赛
MATCHES = [
    # J联赛
    {"home": "Gamba Osaka", "away": "Fagiano Okayama", "league": "soccer_japan_j_league"},
    {"home": "Nagoya Grampus", "away": "Avispa Fukuoka", "league": "soccer_japan_j_league"},
    # K联赛
    {"home": "Pohang Steelers", "away": "FC Anyang", "league": "soccer_korea_kleague1"},
]

def main():
    predictor = FootballPredictor()
    results = []
    
    print("=" * 70)
    print("🏆 前3场比赛预测")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    for i, match in enumerate(MATCHES, 1):
        home_cn = translate_team_name(match["home"])
        away_cn = translate_team_name(match["away"])
        league = match["league"]
        
        print(f"\n[{i}/{len(MATCHES)}] 预测: {home_cn} vs {away_cn}")
        print(f"   联赛: {league}")
        
        try:
            # 执行预测
            start_time = time.time()
            result = predictor.predict(match["home"], match["away"], match["league"])
            elapsed = time.time() - start_time
            
            if result:
                # 获取ML-Analyst结果
                ml_report = predictor.reports.get("ml", {})
                ml_prediction = ml_report.get("prediction", "未知")
                ml_confidence = ml_report.get("confidence", 0)
                
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
                
                # 获取隐含概率
                stats_conf = consensus.get("stats", {})
                home_prob = stats_conf.get("home_win", 0)
                draw_prob = stats_conf.get("draw", 0)
                away_prob = stats_conf.get("away_win", 0)
                
                # 获取冷门风险
                upset_risk = consensus.get("upset", {}).get("upset_risk_score", 50)
                
                # 从reports获取最终信心分数
                final_confidence = predictor.reports.get("final_confidence", 0)
                
                # 显示结果
                print(f"   ⏱️ 耗时: {elapsed:.1f}秒")
                print(f"   📊 隐含概率: 主胜{home_prob*100:.1f}% | 平局{draw_prob*100:.1f}% | 客胜{away_prob*100:.1f}%")
                print(f"   🤖 ML预测: {ml_prediction} ({ml_confidence:.1f}%)")
                print(f"   🎯 推荐: {market} {recommendation}")
                print(f"   💪 信心: {final_confidence:.1f}% | 价值: {value}/100")
                print(f"   ⚠️ 冷门风险: {upset_risk}/100")
                
                # 收集结果
                results.append({
                    "match": f"{home_cn} vs {away_cn}",
                    "league": league,
                    "market": market,
                    "recommendation": recommendation,
                    "confidence": final_confidence,
                    "ml_prediction": ml_prediction,
                    "ml_confidence": ml_confidence,
                    "elapsed": elapsed
                })
            else:
                print(f"   ❌ 无数据")
                results.append({
                    "match": f"{home_cn} vs {away_cn}",
                    "error": "无数据"
                })
                
        except Exception as e:
            print(f"   ❌ 错误: {e}")
            results.append({
                "match": f"{home_cn} vs {away_cn}",
                "error": str(e)
            })
        
        # 短暂暂停
        if i < len(MATCHES):
            time.sleep(2)
    
    # 汇总
    print("\n" + "=" * 70)
    print("📊 前3场比赛预测汇总")
    print("=" * 70)
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['match']}")
        if r.get('error'):
            print(f"   状态: ❌ {r['error']}")
        else:
            print(f"   推荐: {r['market']} {r['recommendation']}")
            print(f"   信心: {r['confidence']:.1f}%")
            print(f"   ML预测: {r['ml_prediction']} ({r['ml_confidence']:.1f}%)")
            print(f"   耗时: {r['elapsed']:.1f}秒")
    
    return results

if __name__ == "__main__":
    results = main()