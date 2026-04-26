#!/usr/bin/env python3
"""
检查9场比赛批量预测中失败的8场比赛是否在API中可用
"""

import requests
import json

api_key = "c7af0126df9eb35c363065dcea447d8d"

# 9场比赛批量预测中失败的8场比赛
failed_matches = [
    {"home": "Nagoya Grampus", "away": "Avispa Fukuoka", "league": "soccer_japan_j_league"},
    {"home": "Pohang Steelers", "away": "FC Anyang", "league": "soccer_korea_kleague1"},
    {"home": "Cremonese", "away": "Torino", "league": "soccer_italy_serie_a"},
    {"home": "Ipswich Town", "away": "Middlesbrough", "league": "soccer_efl_champ"},
    {"home": "Greuther Fürth", "away": "SV Darmstadt 98", "league": "soccer_germany_bundesliga2"},
    {"home": "AIK", "away": "Kalmar FF", "league": "soccer_sweden_allsvenskan"},
    {"home": "Nottingham Forest", "away": "Burnley", "league": "soccer_epl"},
    {"home": "Aston Villa", "away": "Sunderland", "league": "soccer_epl"},
]

def check_match_in_api(home, away, league):
    """检查比赛是否在API中"""
    url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/"
    params = {
        "apiKey": api_key,
        "regions": "uk",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            matches = response.json()
            for match in matches:
                if match['home_team'].lower() == home.lower() and match['away_team'].lower() == away.lower():
                    return True, match
            return False, None
        else:
            return False, f"API错误: {response.status_code}"
    except Exception as e:
        return False, f"异常: {str(e)}"

print("检查9场比赛批量预测中失败的8场比赛...")
print("=" * 70)

available_matches = []
unavailable_matches = []

for match in failed_matches:
    home = match["home"]
    away = match["away"]
    league = match["league"]
    
    print(f"检查: {home} vs {away} ({league})")
    available, result = check_match_in_api(home, away, league)
    
    if available:
        print(f"  ✅ 在API中找到")
        available_matches.append(match)
    else:
        print(f"  ❌ 未在API中找到")
        unavailable_matches.append(match)
    
    print()

print("=" * 70)
print(f"总结: {len(available_matches)} 场比赛可用，{len(unavailable_matches)} 场比赛不可用")

if available_matches:
    print("\n可预测的比赛:")
    for i, match in enumerate(available_matches, 1):
        print(f"{i}. {match['home']} vs {match['away']} ({match['league']})")

# 保存结果
with open("available_matches.json", "w") as f:
    json.dump({
        "available": available_matches,
        "unavailable": unavailable_matches
    }, f, indent=2)

print("\n结果已保存到 available_matches.json")