#!/usr/bin/env python3
import os
import re
import json
from datetime import datetime

def parse_prediction_file(filepath):
    """解析预测文件，提取价值分数（如果存在）"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 尝试查找价值分数 - 但预测文件中可能没有这些信息
    # 我们需要从football_predictor的内部报告中获取
    
    # 从文件名中提取信息
    filename = os.path.basename(filepath)
    # prediction_Real Madrid_Alavés_20260421_134953.txt
    pattern = r'prediction_(.+?)_(.+?)_(\d{8})_\d{6}\.txt'
    match = re.match(pattern, filename)
    if match:
        home = match.group(1)
        away = match.group(2)
        date = match.group(3)
        return {
            'home': home,
            'away': away,
            'date': date,
            'file': filename
        }
    return None

def main():
    # 找到今天的预测文件
    today_str = datetime.now().strftime('%Y%m%d')
    pred_dir = '/Users/nb888/openclaw-workspace'
    
    pred_files = []
    for f in os.listdir(pred_dir):
        if f.startswith('prediction_') and f.endswith('.txt') and today_str in f:
            pred_files.append(os.path.join(pred_dir, f))
    
    print(f"找到 {len(pred_files)} 个今日预测文件")
    
    # 为了获取价值分数，我们需要直接运行预测器
    # 让我们导入football_predictor并运行一个测试
    import sys
    sys.path.insert(0, pred_dir)
    
    try:
        from football_predictor import FootballPredictor
        from team_translator import TeamTranslator
        
        translator = TeamTranslator()
        
        # 测试几场比赛
        test_matches = [
            ("皇家马德里", "阿拉维斯", "soccer_spain_la_liga"),
            ("毕尔巴鄂竞技", "奥萨苏纳", "soccer_spain_la_liga"),
            ("全北现代", "仁川联", "soccer_korea_k_league")
        ]
        
        for home_cn, away_cn, league in test_matches:
            print(f"\n=== 分析 {home_cn} vs {away_cn} ===")
            
            home_en = translator.translate_to_english(home_cn)
            away_en = translator.translate_to_english(away_cn)
            
            if not home_en or not away_en:
                print(f"   ⚠️ 无法翻译球队名称")
                continue
            
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
                import requests
                
                # 从API获取赔率
                api_key = ODDS_API_KEY
                sport = 'soccer'  # 基础sport
                regions = 'eu'
                markets = 'h2h,spreads,totals'
                
                # 转换联赛代码
                league_map = {
                    'soccer_spain_la_liga': 'soccer_spain_la_liga',
                    'soccer_korea_k_league': 'soccer_korea_k_league'
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
                    if (home_en in match['home_team'] or home_en in match.get('home_team', '')) and \
                       (away_en in match['away_team'] or away_en in match.get('away_team', '')):
                        target_match = match
                        break
                
                if not target_match:
                    print(f"   ⚠️ 未找到赔率数据")
                    continue
                
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