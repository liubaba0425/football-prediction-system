
#!/usr/bin/env python3
"""足球预测智能体系统 - 无ML版本"""
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 不导入ML-Analyst
ML_ANALYST_AVAILABLE = False

# API 配置
ODDS_API_KEY="c7af01...7d8d"  # 简化的key
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# 支持的联赛
SUPPORTED_LEAGUES = {
    "soccer_germany_bundesliga": "德国甲级联赛",
    "soccer_epl": "英格兰超级联赛",
    "soccer_spain_la_liga": "西班牙甲级联赛",
    "soccer_italy_serie_a": "意大利甲级联赛",
    "soccer_france_ligue_one": "法国甲级联赛",
}

class OddsAPIClient:
    """Odds API 客户端"""
    def __init__(self, api_key: str = ODDS_API_KEY):
        self.api_key = api_key
        self.base_url = ODDS_API_BASE

    def fetch_match_odds(self, league: str = "soccer_epl") -> List[Dict]:
        """获取比赛赔率数据"""
        url = f"{self.base_url}/sports/{league}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "uk,eu",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "decimal",
            "bookmakers": "pinnacle"
        }
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except:
            return []

class SimplePredictor:
    def __init__(self, api_key: str = ODDS_API_KEY):
        self.client = OddsAPIClient(api_key)
        self.reports = {}
        
    def predict(self, home_team: str, away_team: str, league: str) -> str:
        """简化预测函数"""
        print(f"🚀 预测: {home_team} vs {away_team}")
        print(f"联赛: {SUPPORTED_LEAGUES.get(league, league)}")
        
        # 获取数据
        all_matches = self.client.fetch_match_odds(league)
        match_data = None
        for match in all_matches:
            if home_team.lower() in match.get("home_team", "").lower() and away_team.lower() in match.get("away_team", "").lower():
                match_data = match
                break
        
        if not match_data:
            return f"❌ 未找到比赛数据: {home_team} vs {away_team}"
        
        # 提取赔率
        h2h_odds = None
        for bookmaker in match_data.get("bookmakers", []):
            if bookmaker.get("key") == "pinnacle":
                for market in bookmaker.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            if outcome.get("name") == home_team:
                                home_odds = outcome.get("price", 2.0)
                            elif outcome.get("name") == away_team:
                                away_odds = outcome.get("price", 2.0)
                            elif outcome.get("name") == "Draw":
                                draw_odds = outcome.get("price", 3.0)
                        break
        
        if not all(["home_odds" in locals(), "away_odds" in locals(), "draw_odds" in locals()]):
            return f"❌ 赔率数据不完整"
        
        # 计算隐含概率
        home_prob = 1/home_odds
        draw_prob = 1/draw_odds
        away_prob = 1/away_odds
        total = home_prob + draw_prob + away_prob
        home_prob_norm = home_prob/total*100
        draw_prob_norm = draw_prob/total*100
        away_prob_norm = away_prob/total*100
        
        # 生成推荐
        if home_prob_norm > away_prob_norm + 5:
            recommendation = f"主胜 ({home_odds:.2f})"
            confidence = home_prob_norm
        elif away_prob_norm > home_prob_norm + 5:
            recommendation = f"客胜 ({away_odds:.2f})"
            confidence = away_prob_norm
        else:
            recommendation = f"平局 ({draw_odds:.2f})"
            confidence = draw_prob_norm
        
        result = f"""
📅 比赛: {home_team} vs {away_team}
📊 核心数据
  • 主胜: {home_prob_norm:.1f}% (赔率: {home_odds:.2f})
  • 平局: {draw_prob_norm:.1f}% (赔率: {draw_odds:.2f})
  • 客胜: {away_prob_norm:.1f}% (赔率: {away_odds:.2f})

🎯 推荐: {recommendation}
💪 信心分数: {confidence:.1f}%
"""
        return result

if __name__ == "__main__":
    predictor = SimplePredictor()
    result = predictor.predict("Eintracht Frankfurt", "RB Leipzig", "soccer_germany_bundesliga")
    print(result)
