"""
Odds API 客户端 - 获取博彩市场数据
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime
from config import ODDS_API_KEY, ODDS_API_BASE, SUPPORTED_LEAGUES
from models import Match, Team, BookmakerOdds


class OddsAPIClient:
    """Odds API 数据客户端"""

    def __init__(self, api_key: str = ODDS_API_KEY):
        self.api_key = api_key
        self.base_url = ODDS_API_BASE
        self.headers = {"Accept": "application/json"}

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """发送API请求"""
        if params is None:
            params = {}
        params["apiKey"] = self.api_key

        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API请求错误: {e}")
            return None

    def get_sports(self) -> List[Dict]:
        """获取支持的体育项目"""
        return self._make_request("/sports") or []

    def get_matches(self, league: str = "soccer_epl", markets: str = "h2h,spreads,totals") -> List[Match]:
        """
        获取比赛数据和赔率

        Args:
            league: 联赛标识
            markets: 市场类型 (h2h=胜平负, spreads=让球, totals=大小球)
        """
        data = self._make_request(f"/sports/{league}/odds", {
            "regions": "uk,eu",
            "markets": markets,
            "oddsFormat": "decimal"
        })

        if not data:
            return []

        matches = []
        for item in data:
            try:
                match = Match(
                    id=item["id"],
                    home_team=Team(
                        name=item["home_team"],
                        key=item.get("home_team", "").lower().replace(" ", "_")
                    ),
                    away_team=Team(
                        name=item["away_team"],
                        key=item.get("away_team", "").lower().replace(" ", "_")
                    ),
                    league=league,
                    commence_time=datetime.fromisoformat(item["commence_time"].replace("Z", "+00:00"))
                )
                matches.append(match)
            except (KeyError, ValueError) as e:
                print(f"解析比赛数据错误: {e}")
                continue

        return matches

    def get_match_odds(self, match_id: str, league: str = "soccer_epl") -> List[BookmakerOdds]:
        """获取特定比赛的赔率数据"""
        matches = self.get_matches(league)
        for match_data in self._make_request(f"/sports/{league}/odds", {
            "regions": "uk,eu",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "decimal"
        }) or []:
            if match_data["id"] == match_id:
                return self._parse_bookmaker_odds(match_data)
        return []

    def _parse_bookmaker_odds(self, match_data: Dict) -> List[BookmakerOdds]:
        """解析博彩公司赔率"""
        odds_list = []

        for bookmaker in match_data.get("bookmakers", []):
            bm_name = bookmaker["title"]

            for market in bookmaker.get("markets", []):
                market_key = market["key"]
                outcomes = {}

                for outcome in market.get("outcomes", []):
                    outcomes[outcome["name"]] = outcome["price"]

                point = None
                if market_key == "spreads":
                    point = market["outcomes"][0].get("point") if market["outcomes"] else None
                elif market_key == "totals":
                    point = market["outcomes"][0].get("point") if market["outcomes"] else None

                odds = BookmakerOdds(
                    bookmaker=bm_name,
                    market_type=market_key,
                    outcomes=outcomes,
                    point=point
                )
                odds_list.append(odds)

        return odds_list

    def get_all_leagues_matches(self, leagues: List[str] = None) -> Dict[str, List[Match]]:
        """获取多个联赛的比赛数据"""
        if leagues is None:
            leagues = list(SUPPORTED_LEAGUES.keys())

        all_matches = {}
        for league in leagues:
            matches = self.get_matches(league)
            if matches:
                all_matches[league] = matches

        return all_matches

    def calculate_implied_probability(self, odds: float) -> float:
        """将赔率转换为隐含概率"""
        if odds <= 0:
            return 0
        return 1 / odds

    def remove_vig(self, implied_probs: Dict[str, float]) -> Dict[str, float]:
        """去除博彩公司的利润边际（vig）"""
        total = sum(implied_probs.values())
        if total <= 0:
            return implied_probs

        return {k: v / total for k, v in implied_probs.items()}
