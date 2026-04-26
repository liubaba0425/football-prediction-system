#!/usr/bin/env python3
"""
批量预测9场比赛 - 包含ML-Analyst支持
"""
from football_predictor import FootballPredictor
from team_translator import translate_team_name
import time
from datetime import datetime

# 9场可预测比赛列表
MATCHES = [
    # J联赛
    {"home": "Gamba Osaka", "away": "Fagiano Okayama", "league": "soccer_japan_j_league"},
    {"home": "Nagoya Grampus", "away": "Avispa Fukuoka", "league": "soccer_japan_j_league"},
    # K联赛
    {"home": "Pohang Steelers", "away": "FC Anyang", "league": "soccer_korea_kleague1"},
    # 意甲
    {"home": "Cremonese", "away": "Torino", "league": "soccer_italy_serie_a"},
    # 英冠
    {"home": "Ipswich Town", "away": "Middlesbrough", "league": "soccer_efl_champ"},
    # 德乙
    {"home": "Greuther Fürth", "away": "SV Darmstadt 98", "league": "soccer_germany_bundesliga2"},
    # 瑞典超
    {"home": "AIK", "away": "Kalmar FF", "league": "soccer_sweden_allsvenskan"},
    # 英超
    {"home": "Nottingham Forest", "away": "Burnley", "league": "soccer_epl"},
    {"home": "Aston Villa", "away": "Sunderland", "league": "soccer_epl"},
]

def get_ml_analyst_confidence(predictor):
    """获取ML-Analyst的信心分数和预测"""
    ml_report = predictor.reports.get("ml", {})
    if ml_report.get("error"):
        return None, None, None, None
    return (
        ml_report.get("prediction", "未知"),
        ml_report.get("confidence", 0),
        ml_report.get("probabilities", {}).get("home_win", 0),
        ml_report.get("probabilities", {}).get("away_win", 0)
    )

def main():
    predictor = FootballPredictor()
    results = []
    detailed_reports = []
    
    print("=" * 70)
    print("🏆 9场比赛批量预测 (包含ML-Analyst)")
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
            result = predictor.predict(match["home"], match["away"], match["league"])
            
            if result:
                # 获取ML-Analyst结果
                ml_prediction, ml_confidence, ml_home_prob, ml_away_prob = get_ml_analyst_confidence(predictor)
                
                # 提取关键信息
                consensus = predictor.reports
                asian_value = consensus.get("asian", {}).get("value_score", 0)
                overunder_value = consensus.get("overunder", {}).get("overunder_value_score", 0)
                
                # 获取最终推荐
                if asian_value > overunder_value:
                    market = "让球盘"
                    recommendation = consensus.get("asian", {}).get("recommendation", "N/A")
                    value = asian_value
                    market_detail = consensus.get("asian", {}).get("actual_handicap", "N/A")
                else:
                    market = "大小球"
                    bias = consensus.get("overunder", {}).get("market_bias", "N/A")
                    line = consensus.get("overunder", {}).get("mainstream_total_line", 2.5)
                    recommendation = f"{bias} {line}球"
                    value = overunder_value
                    market_detail = f"{line}球"
                
                # 获取隐含概率
                stats_conf = consensus.get("stats", {})
                home_prob = stats_conf.get("home_win", 0)
                draw_prob = stats_conf.get("draw", 0)
                away_prob = stats_conf.get("away_win", 0)
                
                # 获取冷门风险
                upset_risk = consensus.get("upset", {}).get("upset_risk_score", 50)
                
                # 使用predictor中的共识计算逻辑
                # 从predictor获取最终信心分数
                final_confidence = 0
                # 尝试从reports中查找最终信心分数
                if predictor.reports.get("final_confidence"):
                    final_confidence = predictor.reports["final_confidence"]
                else:
                    # 手动计算简化版本
                    stats_score = consensus.get("stats", {}).get("confidence_weight", 50)
                    tactics_score = consensus.get("tactics", {}).get("tactical_match_score", 50)
                    sentiment_score = consensus.get("sentiment", {}).get("market_sentiment_score", 50)
                    ml_score = ml_confidence if ml_confidence else 50
                    
                    # 动态权重（基于冷门风险）
                    if upset_risk > 60:
                        weights = {"stats": 0.20, "tactics": 0.15, "sentiment": 0.15, "upset": 0.25, "ml": 0.25}
                    else:
                        weights = {"stats": 0.25, "tactics": 0.15, "sentiment": 0.15, "upset": 0.10, "ml": 0.35}
                    
                    base_score = (
                        stats_score * weights["stats"] +
                        tactics_score * weights["tactics"] +
                        sentiment_score * weights["sentiment"] +
                        (100 - upset_risk) * weights["upset"] +
                        ml_score * weights["ml"]
                    )
                    
                    market_factor = value / 100 if value > 0 else 0.5
                    final_confidence = base_score * (0.7 + 0.3 * market_factor)
                    final_confidence = max(5, min(90, final_confidence))
                
                # 收集结果
                match_result = {
                    "match": f"{home_cn} vs {away_cn}",
                    "home_cn": home_cn,
                    "away_cn": away_cn,
                    "league": league,
                    "market": market,
                    "recommendation": recommendation,
                    "market_detail": market_detail,
                    "value": value,
                    "confidence": round(final_confidence, 1),
                    "asian_value": asian_value,
                    "overunder_value": overunder_value,
                    "home_prob": round(home_prob, 3),
                    "draw_prob": round(draw_prob, 3),
                    "away_prob": round(away_prob, 3),
                    "upset_risk": upset_risk,
                    "ml_prediction": ml_prediction,
                    "ml_confidence": ml_confidence,
                    "ml_home_prob": round(ml_home_prob, 3) if ml_home_prob else 0,
                    "ml_away_prob": round(ml_away_prob, 3) if ml_away_prob else 0,
                    "has_debate": consensus.get("debate_triggered", False)
                }
                
                results.append(match_result)
                detailed_reports.append(result)  # 保存完整报告
                
                # 显示简略结果
                print(f"   📊 隐含概率: 主胜{home_prob*100:.1f}% | 平局{draw_prob*100:.1f}% | 客胜{away_prob*100:.1f}%")
                if ml_prediction:
                    print(f"   🤖 ML预测: {ml_prediction} ({ml_confidence:.1f}%) [主:{ml_home_prob*100:.1f}% 客:{ml_away_prob*100:.1f}%]")
                print(f"   🎯 推荐: {market} {recommendation}")
                print(f"   💪 信心: {final_confidence:.1f}% | 价值: {value}/100")
                print(f"   ⚠️ 冷门风险: {upset_risk}/100")
                
            else:
                print(f"   ❌ 无数据")
                results.append({
                    "match": f"{home_cn} vs {away_cn}",
                    "market": "N/A",
                    "recommendation": "无数据",
                    "confidence": 0,
                    "error": True
                })
                
        except Exception as e:
            print(f"   ❌ 错误: {e}")
            results.append({
                "match": f"{home_cn} vs {away_cn}",
                "market": "N/A", 
                "recommendation": "预测失败",
                "confidence": 0,
                "error": True
            })
        
        # 短暂暂停，避免API限流
        if i < len(MATCHES):
            time.sleep(1)
    
    # 汇总报告
    print("\n" + "=" * 70)
    print("📊 9场比赛预测汇总报告")
    print("=" * 70)
    
    # 按信心分数排序
    valid_results = [r for r in results if not r.get("error") and r["confidence"] > 0]
    sorted_results = sorted(valid_results, key=lambda x: x["confidence"], reverse=True)
    
    print(f"\n✅ 成功预测 {len(valid_results)}/{len(MATCHES)} 场比赛")
    
    if sorted_results:
        print("\n🏆 最终推荐（按信心分数排序）:\n")
        
        for i, r in enumerate(sorted_results, 1):
            print(f"{i}. {r['match']}")
            print(f"   联赛: {r['league']}")
            print(f"   隐含概率: 主胜{r['home_prob']*100:.1f}% | 平局{r['draw_prob']*100:.1f}% | 客胜{r['away_prob']*100:.1f}%")
            if r.get('ml_prediction'):
                print(f"   ML预测: {r['ml_prediction']} ({r['ml_confidence']:.1f}%)")
            print(f"   推荐市场: {r['market']}")
            print(f"   推荐选项: {r['recommendation']}")
            print(f"   价值分数: {r['value']}/100")
            print(f"   信心分数: {r['confidence']}%")
            if r.get('has_debate'):
                print(f"   ⚖️ 触发辩论机制")
            print()
    
    # 筛选高信心推荐
    high_confidence = [r for r in sorted_results if r["confidence"] >= 55]
    medium_confidence = [r for r in sorted_results if 40 <= r["confidence"] < 55]
    low_confidence = [r for r in sorted_results if r["confidence"] < 40]
    
    print("=" * 70)
    print("🎯 推荐分类分析:")
    print("=" * 70)
    
    print(f"\n🟢 高信心推荐 (≥55%): {len(high_confidence)} 场")
    if high_confidence:
        for i, r in enumerate(high_confidence, 1):
            print(f"   {i}. {r['match']}: {r['recommendation']} ({r['confidence']:.1f}%)")
    
    print(f"\n🟡 中信心推荐 (40-55%): {len(medium_confidence)} 场")
    if medium_confidence:
        for i, r in enumerate(medium_confidence, 1):
            print(f"   {i}. {r['match']}: {r['recommendation']} ({r['confidence']:.1f}%)")
    
    print(f"\n🔴 低信心推荐 (<40%): {len(low_confidence)} 场")
    if low_confidence:
        for i, r in enumerate(low_confidence, 1):
            print(f"   {i}. {r['match']}: {r['recommendation']} ({r['confidence']:.1f}%)")
    
    # ML-Analyst表现分析
    print("\n" + "=" * 70)
    print("🤖 ML-Analyst 表现分析:")
    print("=" * 70)
    
    ml_results = [r for r in valid_results if r.get('ml_prediction')]
    if ml_results:
        print(f"ML-Analyst 参与了 {len(ml_results)} 场比赛预测")
        
        # 计算ML与传统分析的差异
        ml_extreme_cases = []
        for r in ml_results:
            # 判断ML预测是否极端
            if r['ml_confidence'] >= 80 and abs(r['ml_home_prob'] - r['home_prob']) > 0.3:
                ml_extreme_cases.append(r)
        
        if ml_extreme_cases:
            print(f"ML有 {len(ml_extreme_cases)} 场极端预测（信心≥80%且与传统分析差异>30%）:")
            for r in ml_extreme_cases:
                print(f"   {r['match']}: ML预测{r['ml_prediction']}({r['ml_confidence']:.1f}%) vs 传统概率(主{r['home_prob']*100:.1f}% 客{r['away_prob']*100:.1f}%)")
    
    print("\n" + "=" * 70)
    print("⚠️ 免责声明: 本报告仅供娱乐参考，不构成投注建议")
    print("=" * 70)
    
    # 准备微信消息
    weixin_message = prepare_weixin_message(sorted_results, high_confidence)
    
    return sorted_results, detailed_reports, weixin_message

def prepare_weixin_message(sorted_results, high_confidence):
    """准备微信消息"""
    message = "⚽ 9场比赛批量预测结果\n\n"
    
    message += f"✅ 成功预测 {len(sorted_results)}/9 场比赛\n\n"
    
    if high_confidence:
        message += "🎯 高信心推荐 (≥55%):\n"
        for i, r in enumerate(high_confidence[:3], 1):  # 只显示前3个
            message += f"{i}. {r['match']}\n"
            message += f"   推荐: {r['recommendation']}\n"
            message += f"   信心: {r['confidence']:.1f}%\n"
            message += f"   ML预测: {r['ml_prediction']} ({r['ml_confidence']:.1f}%)\n\n"
    else:
        message += "⚠️ 无高信心推荐\n\n"
    
    message += "📊 信心分布:\n"
    message += f"高信心(≥55%): {len([r for r in sorted_results if r['confidence'] >= 55])} 场\n"
    message += f"中信心(40-55%): {len([r for r in sorted_results if 40 <= r['confidence'] < 55])} 场\n"
    message += f"低信心(<40%): {len([r for r in sorted_results if r['confidence'] < 40])} 场\n\n"
    
    message += "🤖 ML极端预测分析:\n"
    ml_extreme = [r for r in sorted_results if r.get('ml_confidence', 0) >= 80 and abs(r.get('ml_home_prob', 0) - r.get('home_prob', 0)) > 0.3]
    if ml_extreme:
        message += f"ML有 {len(ml_extreme)} 场极端预测:\n"
        for r in ml_extreme[:2]:  # 只显示前2个
            message += f"• {r['match']}: ML预测{r['ml_prediction']}({r['ml_confidence']:.1f}%)\n"
    else:
        message += "无极端预测\n\n"
    
    message += "⚠️ 免责: 仅供参考"
    
    return message

if __name__ == "__main__":
    sorted_results, detailed_reports, weixin_message = main()
    
    # 保存结果到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"batch_predict_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write("9场比赛批量预测结果\n\n")
        for i, r in enumerate(sorted_results, 1):
            f.write(f"{i}. {r['match']}\n")
            f.write(f"   联赛: {r['league']}\n")
            f.write(f"   推荐: {r['market']} {r['recommendation']}\n")
            f.write(f"   信心: {r['confidence']:.1f}%\n")
            f.write(f"   ML预测: {r['ml_prediction']} ({r['ml_confidence']:.1f}%)\n")
            f.write(f"   隐含概率: 主胜{r['home_prob']*100:.1f}% | 平局{r['draw_prob']*100:.1f}% | 客胜{r['away_prob']*100:.1f}%\n")
            f.write("\n")
    
    print(f"\n💾 详细报告已保存: batch_predict_{timestamp}.txt")
    print(f"📨 微信消息已准备，共 {len(weixin_message)} 字符")
    print("\n是否发送微信消息？ (y/n): ", end="")