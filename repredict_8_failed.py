#!/usr/bin/env python3
"""
预测之前失败的8场比赛，直接使用FootballPredictor，避免子进程问题。
"""
import json
import sys
import os
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from football_predictor import FootballPredictor
    from team_translator import translate_team_name
except ImportError as e:
    print(f"导入失败: {e}")
    sys.exit(1)

# 比赛列表（与predict_remaining_8_matches.py相同）
MATCHES = [
    # 第2场
    {"home": "Nagoya Grampus", "away": "Avispa Fukuoka", "league": "soccer_japan_j_league", "id": 2},
    # 第3场
    {"home": "Pohang Steelers", "away": "FC Anyang", "league": "soccer_korea_kleague1", "id": 3},
    # 第4场
    {"home": "Cremonese", "away": "Torino", "league": "soccer_italy_serie_a", "id": 4},
    # 第5场
    {"home": "Ipswich Town", "away": "Middlesbrough", "league": "soccer_efl_champ", "id": 5},
    # 第6场
    {"home": "Greuther Fürth", "away": "SV Darmstadt 98", "league": "soccer_germany_bundesliga2", "id": 6},
    # 第7场
    {"home": "AIK", "away": "Kalmar FF", "league": "soccer_sweden_allsvenskan", "id": 7},
    # 第8场
    {"home": "Nottingham Forest", "away": "Burnley", "league": "soccer_epl", "id": 8},
    # 第9场
    {"home": "Aston Villa", "away": "Sunderland", "league": "soccer_epl", "id": 9},
]

def predict_match(match):
    """预测单场比赛"""
    match_id = match['id']
    home = match['home']
    away = match['away']
    league = match['league']
    
    print(f"[{match_id}] 预测: {home} vs {away} ({league})")
    
    try:
        predictor = FootballPredictor()
        result = predictor.predict(home, away, league)
        
        if result.get('success'):
            # 提取关键信息
            home_cn = result.get('home_team_cn', home)
            away_cn = result.get('away_team_cn', away)
            implied_prob = result.get('implied_probabilities', {})
            ml_pred = result.get('ml_prediction', {})
            consensus = result.get('consensus', {})
            upset_risk = result.get('upset_risk', 0)
            final_confidence = consensus.get('final_confidence', 0)
            
            # 确定市场和推荐
            selected_market = consensus.get('selected_market', 'N/A')
            recommendation = consensus.get('recommendation', 'N/A')
            market_detail = consensus.get('market_detail', {})
            handicap = market_detail.get('handicap', 'N/A') if market_detail else 'N/A'
            
            # 构建结果
            match_result = {
                "match_id": match_id,
                "match": f"{home_cn} vs {away_cn}",
                "home_cn": home_cn,
                "away_cn": away_cn,
                "league": league,
                "ml_prediction": ml_pred.get('result', '未知'),
                "ml_confidence": ml_pred.get('confidence', 0),
                "market": selected_market,
                "recommendation": recommendation,
                "market_detail": handicap if selected_market == '让球盘' else market_detail,
                "value": 0,  # 占位符
                "home_prob": implied_prob.get('home', 0),
                "draw_prob": implied_prob.get('draw', 0),
                "away_prob": implied_prob.get('away', 0),
                "upset_risk": upset_risk,
                "confidence": final_confidence,
                "has_debate": consensus.get('debate_triggered', False),
                "success": True,
                "elapsed": 0,  # 占位符
                "timestamp": datetime.now().isoformat()
            }
            print(f"   ✅ 成功，信心: {final_confidence}%")
            return match_result
        else:
            error = result.get('error', '未知错误')
            print(f"   ❌ 失败: {error}")
            return {
                "match_id": match_id,
                "match": f"{home} vs {away}",
                "league": league,
                "success": False,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        error = f"异常: {str(e)}"
        print(f"   ❌ 异常: {error}")
        traceback.print_exc()
        return {
            "match_id": match_id,
            "match": f"{home} vs {away}",
            "league": league,
            "success": False,
            "error": error,
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }

def main():
    print("=" * 70)
    print("🏆 重新预测之前失败的8场比赛")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    for match in MATCHES:
        result = predict_match(match)
        results.append(result)
        # 短暂延迟，避免API限流
        time.sleep(2)
    
    # 分离成功和失败
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    print(f"\n✅ 成功预测: {len(successful)}/{len(MATCHES)} 场")
    print(f"❌ 预测失败: {len(failed)}/{len(MATCHES)} 场")
    
    if failed:
        print("\n失败比赛:")
        for r in failed:
            print(f"  • {r['match']}: {r.get('error', 'Unknown error')}")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"re_predicted_8_matches_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": {
                "total": len(MATCHES),
                "successful": len(successful),
                "failed": len(failed),
                "timestamp": timestamp
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 结果已保存: {output_file}")
    
    # 生成简要报告
    if successful:
        print("\n🎯 成功比赛详情:")
        for r in successful:
            print(f"  {r['match']}: {r['market']} {r['recommendation']} (信心 {r['confidence']}%)")
    
    return results

if __name__ == '__main__':
    import time
    main()