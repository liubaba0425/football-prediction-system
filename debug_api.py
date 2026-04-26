#!/usr/bin/env python3
"""
调试脚本：查看 API 返回的比赛数据
"""
import requests

API_KEY = "c7af0126df9eb35c363065dcea447d8d"
BASE_URL = "https://api.the-odds-api.com/v4"

# 测试多个联赛
leagues = ["soccer_epl", "soccer_spain_la_liga", "soccer_uefa_champs_league"]

for league in leagues:
    print(f"\n{'='*60}")
    print(f"📊 联赛: {league}")
    print(f"{'='*60}")

    url = f"{BASE_URL}/sports/{league}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "uk",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"比赛数量: {len(data)}")

            if data:
                print("\n可用比赛:")
                for match in data[:5]:  # 只显示前5场
                    print(f"  - {match['home_team']} vs {match['away_team']}")
                    print(f"    时间: {match.get('commence_time', 'N/A')}")

                    # 检查是否有 Pinnacle 数据
                    for bm in match.get('bookmakers', []):
                        if bm.get('key') == 'pinnacle':
                            print(f"    ✅ 有 Pinnacle 数据")
                            break
            else:
                print("暂无比赛数据")
        else:
            print(f"错误: {response.text}")

    except Exception as e:
        print(f"请求失败: {e}")

print(f"\n{'='*60}")
print("调试完成")
