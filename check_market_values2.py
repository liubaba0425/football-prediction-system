#!/usr/bin/env python3
import os
import re
import json
from datetime import datetime

def translate_to_english(chinese_name):
    """中文转英文 - 简单反向查找"""
    from team_translator import TEAM_NAME_TRANSLATIONS
    # 创建反向映射
    reverse_map = {cn: en for en, cn in TEAM_NAME_TRANSLATIONS.items()}
    # 精确匹配
    if chinese_name in reverse_map:
        return reverse_map[chinese_name]
    # 模糊匹配
    for cn, en in reverse_map.items():
        if cn in chinese_name or chinese_name in cn:
            return en
    return chinese_name  # 找不到翻译，返回原名称

def main():
    # 为了获取价值分数，我们需要直接运行预测器
    import sys
    sys.path.insert(0, '/Users/nb888/openclaw-workspace')
    
    try:
        from football_predictor import FootballPredictor
        import requests
        
        # 测试几场比赛
        test_matches = [
            ("皇家马德里", "阿拉维斯", "soccer_spain_la_liga"),
            ("毕尔巴鄂竞技", "奥萨苏纳", "soccer_spain_la_liga"),
            ("全北现代", "仁川联", "soccer_korea_k_league"),
            ("朗斯", "图卢兹", "soccer_france_ligue_one"),  # 法甲
        ]
        
        for home_cn, away_cn, league in test_matches:
            print(f"\n=== 分析 {home_cn} vs {away_cn} ===")
            
            home_en = translate_to_english(home_cn)
            away_en = translate_to_english(away_cn)
            
            print(f"   英文队名: {home_en} vs {away_en}")
            
            predictor = FootballPredictor(league=league)
            
            # 设置球队名称
            predictor.home_team = home_en
            predictor.away_team = away_en
            
            # 运行预测但不生成最终报告
            try:
                # 模拟预测流程直到共识汇总
                match_info = {
                    "home_team": home_en,
                    "away_team": away_en,
                    "league": league
                }
                
                # 需要获取赔率数据
                from config import ODDS_API_KEY
                
                # 从API获取赔率
                api_key = ODDS_API_KEY
                sport = 'soccer'  # 基础sport
                regions = 'eu'
                markets = 'h2h,spreads,totals'
                
                # 转换联赛代码
                league_map = {
                    'soccer_spain_la_liga': 'soccer_spain_la_liga',
                    'soccer_korea_k_league': 'soccer_korea_k_league',
                    'soccer_france_ligue_one': 'soccer_france_ligue_one'
                }
                
                api_league = league_map.get(league, league)
                
                url = f'https://api.the-odds-api.com/v4/sports/{api_league}/odds'
                params = {
                    'apiKey': api_key,
                    'regions': regions,
                    'markets': markets,
                    'oddsFormat': 'decimal'
                }
                
                print(f"   获取赔率数据...")
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code != 200:
                    print(f"   ⚠️ API请求失败: {response.status_code}")
                    continue
                
                odds_data = response.json()
                
                # 查找特定比赛
                target_match = None
                for match in odds_data:
                    match_home = match.get('home_team', '')
                    match_away = match.get('away_team', '')
                    # 模糊匹配
                    if (home_en.lower() in match_home.lower() or match_home.lower() in home_en.lower()) and \
                       (away_en.lower() in match_away.lower() or match_away.lower() in away_en.lower()):
                        target_match = match
                        break
                
                if not target_match:
                    print(f"   ⚠️ 未找到赔率数据")
                    continue
                
                print(f"   找到比赛: {target_match.get('home_team')} vs {target_match.get('away_team')}")
                
                # 提取Pinnacle数据
                pinnacle_data = {}
                for bookmaker in target_match.get('bookmakers', []):
                    if bookmaker['key'] == 'pinnacle':
                        for market in bookmaker['markets']:
                            if market['key'] == 'h2h':
                                pinnacle_data['h2h'] = market
                            elif market['key'] == 'spreads':
                                pinnacle_data['spreads'] = market
                            elif market['key'] == 'totals':
                                pinnacle_data['totals'] = market
                
                if not pinnacle_data:
                    print(f"   ⚠️ 无Pinnacle数据")
                    continue
                
                # 运行分析师
                print(f"   运行分析师...")
                stats_report = predictor._run_stats_analyst(match_info)
                predictor.reports['stats'] = stats_report
                
                asian_report = predictor._run_asian_analyst(match_info, pinnacle_data, stats_report)
                predictor.reports['asian'] = asian_report
                
                overunder_report = predictor._run_overunder_analyst(match_info, pinnacle_data)
                predictor.reports['overunder'] = overunder_report
                
                # 输出价值分数
                asian_value = asian_report.get('value_score', 0)
                overunder_value = overunder_report.get('overunder_value_score', 0)
                
                print(f"   让球盘价值分数: {asian_value}/100")
                print(f"   大小球价值分数: {overunder_value}/100")
                print(f"   推荐市场: {'让球盘' if asian_value > overunder_value else '大小球' if overunder_value > asian_value else '让球盘(平局)'}")
                print(f"   盘口类型: {asian_report.get('opening_analysis', 'N/A')}")
                print(f"   机构意图: {asian_report.get('intention', 'N/A')}")
                print(f"   大小球偏向: {overunder_report.get('market_bias', 'N/A')}")
                
            except Exception as e:
                print(f"   错误: {e}")
                import traceback
                traceback.print_exc()
                
    except ImportError as e:
        print(f"导入错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()