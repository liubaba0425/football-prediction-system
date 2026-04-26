#!/usr/bin/env python3
import sys
import json
import time
sys.path.append('.')
from football_predictor import FootballPredictor

def predict_match(home_team, away_team, league, match_name):
    """预测单场比赛并返回结构化结果"""
    print(f"\n{'='*60}")
    print(f"⚽ 开始预测: {match_name}")
    print(f"{'='*60}")
    
    predictor = FootballPredictor()
    start_time = time.time()
    
    try:
        result = predictor.predict(home_team, away_team, league)
        elapsed = time.time() - start_time
        
        if result.get('success'):
            print(f"✅ 预测成功 ({elapsed:.1f}秒)")
            
            # 提取关键信息
            home_cn = result['home_team_cn']
            away_cn = result['away_team_cn']
            implied = result['implied_probabilities']
            ml = result['ml_prediction']
            upset = result['upset_risk']
            consensus = result['consensus']
            
            print(f"   比赛: {home_cn} vs {away_cn}")
            print(f"   隐含概率: 主胜{implied['home']:.1f}% | 平局{implied['draw']:.1f}% | 客胜{implied['away']:.1f}%")
            print(f"   🤖 ML预测: {ml['result']} (信心: {ml['confidence']:.1f}%)")
            print(f"   ⚠️ 冷门风险: {upset}/100 ({result['risk_level']})")
            print(f"   🎯 系统推荐: {consensus['recommended_market']} {consensus['recommendation']}")
            print(f"   💪 信心分数: {consensus['confidence']:.1f}%")
            print(f"   📊 市场价值: {consensus['market_value']}/100")
            
            if consensus.get('market_detail'):
                detail = consensus['market_detail']
                if detail.get('type') == 'asian':
                    print(f"   🏷️ 让球盘性质: {detail.get('intention', 'N/A')}")
            
            return {
                'success': True,
                'match': f"{home_cn} vs {away_cn}",
                'home_cn': home_cn,
                'away_cn': away_cn,
                'implied_probabilities': implied,
                'ml_prediction': ml,
                'upset_risk': upset,
                'risk_level': result['risk_level'],
                'consensus': consensus,
                'elapsed': elapsed
            }
        else:
            print(f"❌ 预测失败: {result.get('error', '未知错误')}")
            return {
                'success': False,
                'error': result.get('error', '未知错误'),
                'elapsed': elapsed
            }
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ 预测异常: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'elapsed': elapsed
        }

def main():
    print("🏆 足球预测智能体系统 - 两场比赛预测")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 定义要预测的比赛
    matches = [
        {
            'home': 'SC Freiburg',
            'away': '1. FC Heidenheim',
            'league': 'soccer_germany_bundesliga',
            'name': '弗赖堡 vs 海登海姆 (德甲)'
        },
        {
            'home': 'BK Hacken',
            'away': 'GAIS',
            'league': 'soccer_sweden_allsvenskan',
            'name': '赫根 vs 加尔斯 (瑞典超)'
        }
    ]
    
    all_results = []
    
    for i, match in enumerate(matches, 1):
        print(f"\n[{i}/{len(matches)}] ", end="")
        result = predict_match(
            match['home'],
            match['away'],
            match['league'],
            match['name']
        )
        result['match_info'] = match
        all_results.append(result)
        
        # 短暂暂停，避免API限流
        if i < len(matches):
            time.sleep(2)
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("📊 预测汇总")
    print(f"{'='*60}")
    
    successful = [r for r in all_results if r.get('success')]
    failed = [r for r in all_results if not r.get('success')]
    
    print(f"✅ 成功预测: {len(successful)}/{len(matches)} 场")
    print(f"❌ 预测失败: {len(failed)}/{len(matches)} 场")
    
    if successful:
        print(f"\n推荐比赛 (按信心分数排序):")
        # 按信心分数排序
        successful_sorted = sorted(
            successful,
            key=lambda x: x.get('consensus', {}).get('confidence', 0),
            reverse=True
        )
        
        for i, result in enumerate(successful_sorted, 1):
            match_info = result['match_info']
            consensus = result.get('consensus', {})
            implied = result.get('implied_probabilities', {})
            
            print(f"{i}. {result['match']}")
            print(f"   推荐: {consensus.get('recommended_market', 'N/A')} {consensus.get('recommendation', 'N/A')}")
            print(f"   信心: {consensus.get('confidence', 0):.1f}%")
            print(f"   隐含概率: 主胜{implied.get('home', 0):.1f}% | 平局{implied.get('draw', 0):.1f}% | 客胜{implied.get('away', 0):.1f}%")
            print(f"   冷门风险: {result.get('upset_risk', 0)}/100")
            print()
    
    # 保存结果到文件
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = f"prediction_results_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total': len(matches),
                'successful': len(successful),
                'failed': len(failed),
                'timestamp': timestamp
            },
            'results': all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 详细结果已保存: {output_file}")
    
    # 检查是否需要微信发送
    print(f"\n是否发送微信消息？ (y/n): ", end="")
    # 注意: 这里需要用户输入，但在批处理中我们可以跳过
    print("(如需发送微信消息，请在Hermes Agent中手动发送)")

if __name__ == "__main__":
    main()