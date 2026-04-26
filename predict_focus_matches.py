#!/usr/bin/env python3
"""
预测4场焦点比赛并发送结果到微信
"""
import sys
sys.path.append('.')
from football_predictor import FootballPredictor
from team_translator import translate_team_name
import time
import json

FOCUS_MATCHES = [
    # 英超焦点战
    {"home": "Manchester City", "away": "Arsenal", "league": "soccer_epl", "id": 1},
    # 德甲焦点战
    {"home": "Bayern Munich", "away": "VfB Stuttgart", "league": "soccer_germany_bundesliga", "id": 2},
    # 法甲焦点战
    {"home": "Paris Saint-Germain", "away": "Lyon", "league": "soccer_france_ligue_one", "id": 3},
    # 葡超焦点战
    {"home": "Sporting CP", "away": "Benfica", "league": "soccer_portugal_primeira_liga", "id": 4},
]

def predict_match(match):
    """预测单场比赛并返回关键信息"""
    predictor = FootballPredictor()
    home = match["home"]
    away = match["away"]
    league = match["league"]
    
    print(f"[{match['id']}/4] 预测: {translate_team_name(home)} vs {translate_team_name(away)}")
    
    try:
        start_time = time.time()
        result = predictor.predict(home, away, league)
        elapsed = time.time() - start_time
        
        if not result:
            return {"error": "无数据", "elapsed": elapsed}
        
        reports = predictor.reports
        ml_report = reports.get("ml", {})
        
        # 提取关键信息
        ml_prediction = ml_report.get("prediction", "未知")
        ml_confidence = ml_report.get("confidence", 0)
        
        # 市场推荐
        asian_value = reports.get("asian", {}).get("value_score", 0)
        overunder_value = reports.get("overunder", {}).get("overunder_value_score", 0)
        
        if asian_value > overunder_value:
            market = "让球盘"
            recommendation = reports.get("asian", {}).get("recommendation", "N/A")
            value = asian_value
        else:
            market = "大小球"
            bias = reports.get("overunder", {}).get("market_bias", "N/A")
            line = reports.get("overunder", {}).get("mainstream_total_line", 2.5)
            recommendation = f"{bias} {line}球"
            value = overunder_value
        
        # 隐含概率
        stats_conf = reports.get("stats", {})
        home_prob = stats_conf.get("home_win", 0)
        draw_prob = stats_conf.get("draw", 0)
        away_prob = stats_conf.get("away_win", 0)
        
        # 其他指标
        upset_risk = reports.get("upset", {}).get("upset_risk_score", 50)
        final_confidence = reports.get("final_confidence", 0)
        
        return {
            "match": f"{translate_team_name(home)} vs {translate_team_name(away)}",
            "league": league,
            "market": market,
            "recommendation": recommendation,
            "value": value,
            "home_prob": home_prob,
            "draw_prob": draw_prob,
            "away_prob": away_prob,
            "upset_risk": upset_risk,
            "confidence": final_confidence,
            "ml_prediction": ml_prediction,
            "ml_confidence": ml_confidence,
            "elapsed": elapsed,
            "has_debate": reports.get("debate_triggered", False),
            "success": True
        }
        
    except Exception as e:
        return {"error": str(e), "success": False}

def main():
    print("=" * 70)
    print("🏆 4场焦点比赛预测")
    print("=" * 70)
    
    results = []
    
    for match in FOCUS_MATCHES:
        result = predict_match(match)
        results.append(result)
        
        if result.get("success"):
            r = result
            print(f"   ✅ 预测成功 ({r['elapsed']:.1f}s)")
            print(f"      推荐: {r['market']} {r['recommendation']}")
            print(f"      信心: {r['confidence']:.1f}%")
            print(f"      ML预测: {r['ml_prediction']} ({r['ml_confidence']:.1f}%)")
            print(f"      隐含概率: 主胜{r['home_prob']*100:.1f}% | 平局{r['draw_prob']*100:.1f}% | 客胜{r['away_prob']*100:.1f}%")
        else:
            print(f"   ❌ 预测失败: {result.get('error')}")
        
        # 短暂暂停
        if match["id"] < 4:
            time.sleep(2)
    
    # 生成微信消息
    weixin_message = generate_weixin_message(results)
    
    print("\n" + "=" * 70)
    print("📨 微信消息内容:")
    print("=" * 70)
    print(weixin_message)
    
    # 保存结果
    with open("focus_matches_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n💾 结果已保存: focus_matches_results.json")
    print("\n是否发送到微信? (y/n): ", end="")
    
    return results, weixin_message

def generate_weixin_message(results):
    """生成微信消息"""
    successful = [r for r in results if r.get("success")]
    
    message = "⚽ 4场焦点比赛预测结果\n\n"
    
    for i, r in enumerate(successful, 1):
        message += f"{i}. {r['match']}\n"
        message += f"   推荐: {r['market']} {r['recommendation']}\n"
        message += f"   信心: {r['confidence']:.1f}%\n"
        message += f"   ML预测: {r['ml_prediction']} ({r['ml_confidence']:.1f}%)\n"
        message += f"   隐含概率: 主胜{r['home_prob']*100:.1f}% | 客胜{r['away_prob']*100:.1f}%\n\n"
    
    if len(successful) < len(results):
        message += f"⚠️ 注意: {len(results)-len(successful)} 场比赛预测失败\n\n"
    
    message += "🤖 ML-Analyst 权重: 正常35%/高风险25%\n"
    message += "⚠️ 免责: 仅供参考"
    
    return message

if __name__ == "__main__":
    results, weixin_message = main()