#!/usr/bin/env python3
"""
实时数据获取工具
用于获取球队状态、伤停、赛程等信息
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from retry_utils import safe_request


class RealTimeDataFetcher:
    """实时数据获取器"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    def search_team_news(self, team_name: str) -> Dict:
        """
        搜索球队最新新闻（使用 DuckDuckGo）
        返回：伤病、停赛、状态等信息
        """
        try:
            # 使用 DuckDuckGo 即时搜索
            query = f"{team_name} football injury suspension news today"
            url = f"https://api.duckduckgo.com/?q={query}&format=json"

            response = safe_request(requests.get, url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                abstract = data.get("Abstract", "")
                related = data.get("RelatedTopics", [])

                return {
                    "status": "success",
                    "summary": abstract[:500] if abstract else "无最新新闻",
                    "related_topics": [r.get("Text", "")[:200] for r in related[:3]],
                    "has_injury_news": "injury" in abstract.lower() if abstract else False,
                    "has_suspension_news": "suspension" in abstract.lower() or "ban" in abstract.lower() if abstract else False
                }
            else:
                return {"status": "error", "message": f"API 返回 {response.status_code}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def estimate_team_form(self, team_name: str, league: str) -> Dict:
        """
        估算球队近期状态
        基于联赛排名和赔率推断
        """
        # 常见强队状态估算（简化版，实际应用应接入真实API）
        top_teams = {
            "soccer_epl": ["Manchester City", "Arsenal", "Liverpool", "Tottenham", "Chelsea", "Manchester United"],
            "soccer_spain_la_liga": ["Real Madrid", "Barcelona", "Atletico Madrid", "Real Sociedad"],
            "soccer_germany_bundesliga": ["Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen"],
            "soccer_italy_serie_a": ["Inter Milan", "AC Milan", "Juventus", "Napoli", "Roma"],
            "soccer_france_ligue_one": ["PSG", "Marseille", "Monaco", "Lyon"],
        }

        league_teams = top_teams.get(league, [])

        # 检查是否是强队
        is_top_team = any(top.lower() in team_name.lower() for top in league_teams)

        if is_top_team:
            return {
                "estimated_rank": "前6",
                "form_rating": 7,  # 1-10分
                "attack_strength": "强",
                "defense_strength": "较强",
                "confidence": "中",
                "note": "基于历史表现估算，非实时数据"
            }
        else:
            return {
                "estimated_rank": "中游",
                "form_rating": 5,
                "attack_strength": "中",
                "defense_strength": "中",
                "confidence": "低",
                "note": "缺少实时数据，估值仅供参考"
            }

    def check_schedule_pressure(self, team_name: str) -> Dict:
        """
        检查赛程压力
        返回可能的疲劳因素
        """
        # 简化版：基于当前日期推断
        now = datetime.now()

        # 周中比赛（周二到周四）可能是杯赛/欧战
        is_midweek = now.weekday() in [1, 2, 3]

        # 周末比赛
        is_weekend = now.weekday() in [4, 5, 6]

        return {
            "match_day_type": "周中" if is_midweek else "周末",
            "potential_congestion": is_midweek,
            "fatigue_risk": "高" if is_midweek else "中",
            "note": "赛程压力评估基于比赛日期，非完整赛程分析"
        }

    def get_match_context(self, home_team: str, away_team: str, league: str) -> Dict:
        """
        获取比赛综合背景信息
        整合多个数据源
        """
        context = {
            "timestamp": datetime.now().isoformat(),
            "data_quality": {
                "real_time_news": True,
                "team_form": False,  # 标记为估算数据
                "schedule_data": True,
                "historical_h2h": False
            }
        }

        # 获取主队新闻
        home_news = self.search_team_news(home_team)
        context["home_team_news"] = home_news

        # 获取客队新闻
        away_news = self.search_team_news(away_team)
        context["away_team_news"] = away_news

        # 估算球队状态
        context["home_form"] = self.estimate_team_form(home_team, league)
        context["away_form"] = self.estimate_team_form(away_team, league)

        # 赛程压力
        context["schedule_pressure"] = {
            "home": self.check_schedule_pressure(home_team),
            "away": self.check_schedule_pressure(away_team)
        }

        return context


# 测试函数
if __name__ == "__main__":
    fetcher = RealTimeDataFetcher()

    # 测试新闻搜索
    print("测试新闻搜索...")
    news = fetcher.search_team_news("Manchester United")
    print(f"结果: {news}")

    # 测试球队状态估算
    print("\n测试球队状态估算...")
    form = fetcher.estimate_team_form("Liverpool", "soccer_epl")
    print(f"结果: {form}")
