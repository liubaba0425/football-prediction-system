import requests, sys

API_KEY = "c7af0126df9eb35c363065dcea447d8d"
BASE = "https://api.the-odds-api.com/v4"

# 先查支持的联赛
sports = requests.get(f"{BASE}/sports", params={"apiKey": API_KEY}, timeout=15).json()
for s in sports:
    if "australia" in s["key"].lower():
        print(f"AU: {s['key']} - {s['title']}")

# 澳超
league = "soccer_australia_aleague"
res = requests.get(f"{BASE}/sports/{league}/odds", params={"apiKey": API_KEY, "regions": "uk,eu", "markets": "h2h,spreads,totals", "oddsFormat": "decimal", "dateFormat": "iso"}, timeout=30)
if res.status_code != 200:
    print(f"Error: {res.status_code}")
    sys.exit(1)

data = res.json()
print(f"\n澳超比赛数: {len(data)}")

for m in data:
    home = m["home_team"].lower()
    away = m["away_team"].lower()
    if "melbourne" in home or "melbourne" in away or "newcastle" in home or "newcastle" in away:
        print(f"\n{'='*60}")
        print(f"{m['home_team']} vs {m['away_team']}")
        print(f"开赛: {m['commence_time']}")
        for bm in m.get("bookmakers", []):
            print(f"\n  [{bm['title']}]")
            for market in bm.get("markets", []):
                print(f"    {market['key']}:")
                for o in market.get("outcomes", []):
                    print(f"      {o['name']}: {o['price']}")
