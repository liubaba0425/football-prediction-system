#!/usr/bin/env python3
"""
获取全北现代 vs 仁川联的实时赔率数据
直接调用The Odds API，显示原始让球盘和大小球信息
"""

import requests
import json
from datetime import datetime

def fetch_realtime_odds():
    """获取实时赔率数据"""
    # 导入API密钥
    import sys
    sys.path.insert(0, '/Users/nb888/openclaw-workspace')
    try:
        from config import ODDS_API_KEY
    except ImportError:
        print("无法导入API密钥，请检查config.py")
        return None
    
    api_key = ODDS_API_KEY
    league = 'soccer_korea_kleague1'  # 韩国K联赛
    regions = 'eu'
    markets = 'h2h,spreads,totals'
    
    url = f'https://api.the-odds-api.com/v4/sports/{league}/odds'
    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': markets,
        'oddsFormat': 'decimal'
    }
    
    print(f"🔍 正在获取实时赔率数据...")
    print(f"   联赛: {league}")
    print(f"   区域: {regions}")
    print(f"   市场: {markets}")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ API请求失败: {response.status_code}")
            print(f"   响应: {response.text[:200]}")
            return None
        
        odds_data = response.json()
        
        # 查找全北现代 vs 仁川联的比赛
        target_match = None
        home_en = "Jeonbuk Hyundai Motors"
        away_en = "Incheon United"
        
        for match in odds_data:
            match_home = match.get('home_team', '')
            match_away = match.get('away_team', '')
            # 模糊匹配
            if (home_en.lower() in match_home.lower() or match_home.lower() in home_en.lower()) and \
               (away_en.lower() in match_away.lower() or match_away.lower() in away_en.lower()):
                target_match = match
                break
        
        if not target_match:
            print(f"❌ 未找到比赛: {home_en} vs {away_en}")
            print(f"   可用比赛:")
            for match in odds_data[:3]:  # 显示前3个比赛
                print(f"   - {match.get('home_team')} vs {match.get('away_team')}")
            return None
        
        print(f"✅ 找到比赛: {target_match.get('home_team')} vs {target_match.get('away_team')}")
        print(f"   比赛时间: {target_match.get('commence_time', 'N/A')}")
        print()
        
        return target_match
        
    except Exception as e:
        print(f"❌ 获取数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_pinnacle_data(match_data):
    """从比赛数据中提取Pinnacle的赔率信息"""
    print("📊 提取Pinnacle赔率数据...")
    
    pinnacle_data = {}
    
    for bookmaker in match_data.get('bookmakers', []):
        if bookmaker['key'] == 'pinnacle':
            print(f"✅ 找到Pinnacle数据")
            
            for market in bookmaker['markets']:
                market_key = market['key']
                print(f"\n  市场: {market_key}")
                
                if market_key == 'h2h':
                    print(f"    类型: 胜平负")
                    for outcome in market.get('outcomes', []):
                        print(f"    {outcome.get('name')}: 赔率 {outcome.get('price', 'N/A')}")
                    pinnacle_data['h2h'] = market
                    
                elif market_key == 'spreads':
                    print(f"    类型: 让球盘")
                    for outcome in market.get('outcomes', []):
                        name = outcome.get('name', '')
                        point = outcome.get('point', 'N/A')
                        price = outcome.get('price', 'N/A')
                        print(f"    {name}: 让球 {point} | 赔率 {price}")
                    pinnacle_data['spreads'] = market
                    
                elif market_key == 'totals':
                    print(f"    类型: 大小球")
                    for outcome in market.get('outcomes', []):
                        name = outcome.get('name', '')
                        point = outcome.get('point', 'N/A')
                        price = outcome.get('price', 'N/A')
                        print(f"    {name}: 盘口 {point}球 | 赔率 {price}")
                    pinnacle_data['totals'] = market
    
    if not pinnacle_data:
        print("⚠️  未找到Pinnacle数据，尝试其他庄家...")
        # 列出所有庄家
        for bookmaker in match_data.get('bookmakers', []):
            print(f"   庄家: {bookmaker['key']} - 市场: {[m['key'] for m in bookmaker.get('markets', [])]}")
    
    return pinnacle_data

def analyze_handicap(pinnacle_data):
    """分析让球盘信息"""
    print("\n🔍 分析让球盘信息...")
    
    if 'spreads' not in pinnacle_data:
        print("❌ 无让球盘数据")
        return
    
    spreads = pinnacle_data['spreads']
    outcomes = spreads.get('outcomes', [])
    
    if len(outcomes) < 2:
        print("❌ 让球盘数据不完整")
        return
    
    # 找出主客队
    home_outcome = None
    away_outcome = None
    
    for outcome in outcomes:
        name = outcome.get('name', '')
        if 'Jeonbuk' in name or 'Jeonbuk Hyundai Motors' in name:
            home_outcome = outcome
        elif 'Incheon' in name or 'Incheon United' in name:
            away_outcome = outcome
    
    if not home_outcome or not away_outcome:
        print("❌ 无法识别主客队")
        print(f"   可用选项: {[o.get('name') for o in outcomes]}")
        return
    
    home_handicap = home_outcome.get('point', 0)
    home_price = home_outcome.get('price', 0)
    away_handicap = away_outcome.get('point', 0)
    away_price = away_outcome.get('price', 0)
    
    print(f"  全北现代: 让球 {home_handicap} | 赔率 {home_price}")
    print(f"  仁川联: 让球 {away_handicap} | 赔率 {away_price}")
    
    # 计算隐含概率
    if home_price > 0:
        home_prob = 1 / home_price
        away_prob = 1 / away_price
        total_implied = home_prob + away_prob
        home_prob_norm = home_prob / total_implied * 100
        away_prob_norm = away_prob / total_implied * 100
        
        print(f"  隐含概率:")
        print(f"    全北现代: {home_prob_norm:.1f}%")
        print(f"    仁川联: {away_prob_norm:.1f}%")
        
        # 理论盘口计算
        if home_prob_norm >= 70:
            theoretical = 1.0
        elif home_prob_norm >= 65:
            theoretical = 0.75
        elif home_prob_norm >= 60:
            theoretical = 0.5
        elif home_prob_norm >= 55:
            theoretical = 0.25
        else:
            theoretical = 0
        
        # 实际让球（取绝对值）
        actual_abs = abs(home_handicap)
        
        print(f"  理论盘口: {theoretical:.2f}")
        print(f"  实际盘口: {home_handicap:.2f}")
        
        if actual_abs > theoretical + 0.25:
            print(f"  盘口性质: 高开 (实际让球比理论更深)")
        elif actual_abs < theoretical - 0.25:
            print(f"  盘口性质: 浅开 (实际让球比理论更浅)")
        else:
            print(f"  盘口性质: 实开 (差异在合理范围内)")
    
    return home_handicap, home_price, away_handicap, away_price

def analyze_totals(pinnacle_data):
    """分析大小球信息"""
    print("\n🔍 分析大小球信息...")
    
    if 'totals' not in pinnacle_data:
        print("❌ 无大小球数据")
        return
    
    totals = pinnacle_data['totals']
    outcomes = totals.get('outcomes', [])
    
    over_data = None
    under_data = None
    
    for outcome in outcomes:
        if outcome.get('name') == 'Over':
            over_data = outcome
        elif outcome.get('name') == 'Under':
            under_data = outcome
    
    if not over_data or not under_data:
        print("❌ 大小球数据不完整")
        return
    
    total_line = over_data.get('point', 2.5)
    over_odds = over_data.get('price', 2.0)
    under_odds = under_data.get('price', 2.0)
    
    print(f"  大小球盘口: {total_line}球")
    print(f"  大球赔率: {over_odds}")
    print(f"  小球赔率: {under_odds}")
    
    # 计算隐含概率
    over_prob = 1 / over_odds
    under_prob = 1 / under_odds
    total_implied = over_prob + under_prob
    over_prob_norm = over_prob / total_implied * 100
    under_prob_norm = under_prob / total_implied * 100
    
    print(f"  隐含概率:")
    print(f"    大球: {over_prob_norm:.1f}%")
    print(f"    小球: {under_prob_norm:.1f}%")
    
    # 市场偏向
    if over_prob_norm > under_prob_norm + 5:
        print(f"  市场偏向: 大球 (差异: {over_prob_norm - under_prob_norm:.1f}%)")
    elif under_prob_norm > over_prob_norm + 5:
        print(f"  市场偏向: 小球 (差异: {under_prob_norm - over_prob_norm:.1f}%)")
    else:
        print(f"  市场偏向: 均衡 (差异: {abs(over_prob_norm - under_prob_norm):.1f}%)")
    
    return total_line, over_odds, under_odds

def main():
    print("=" * 60)
    print("📈 全北现代 vs 仁川联 - 实时赔率分析")
    print("=" * 60)
    
    # 获取实时数据
    match_data = fetch_realtime_odds()
    if not match_data:
        print("❌ 无法获取实时赔率数据")
        return
    
    # 提取Pinnacle数据
    pinnacle_data = extract_pinnacle_data(match_data)
    
    if not pinnacle_data:
        print("❌ 无有效赔率数据")
        return
    
    print("\n" + "=" * 60)
    print("📊 详细分析")
    print("=" * 60)
    
    # 分析让球盘
    handicap_info = analyze_handicap(pinnacle_data)
    
    # 分析大小球
    totals_info = analyze_totals(pinnacle_data)
    
    print("\n" + "=" * 60)
    print("💡 数据解读")
    print("=" * 60)
    
    if handicap_info:
        home_handicap, home_price, away_handicap, away_price = handicap_info
        
        print("让球盘分析:")
        if home_handicap < 0:
            print(f"  • 全北现代让{abs(home_handicap):.2f}球")
            print(f"  • 仁川联受让{abs(home_handicap):.2f}球")
            print(f"  • 让球方赔率: {home_price}")
            print(f"  • 受让方赔率: {away_price}")
        else:
            print(f"  • 盘口异常，请检查数据")
    
    if totals_info:
        total_line, over_odds, under_odds = totals_info
        print(f"\n大小球分析:")
        print(f"  • 盘口: {total_line}球")
        print(f"  • 大球赔率: {over_odds}")
        print(f"  • 小球赔率: {under_odds}")
    
    print("\n✅ 分析完成")
    print(f"   时间戳: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()