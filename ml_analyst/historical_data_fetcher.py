"""
历史数据获取模块 - 从football-data.org API获取历史比赛数据
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Optional
import json
import os

# 导入队名翻译
try:
    # 尝试绝对导入（当项目根目录在sys.path中时）
    from team_translator import translate_team_name
    TRANSLATOR_AVAILABLE = True
except ImportError:
    try:
        # 尝试相对导入（当ml_analyst作为包时）
        from ..team_translator import translate_team_name
        TRANSLATOR_AVAILABLE = True
    except ImportError:
        TRANSLATOR_AVAILABLE = False
        print("⚠️  Team translator not available")

class HistoricalDataFetcher:
    def __init__(self, api_token: str):
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": api_token}
        self.logger = logging.getLogger(__name__)
        
    def fetch_competition_matches(self, competition_code: str, season: int = None) -> pd.DataFrame:
        """
        获取指定联赛指定赛季的所有比赛
        
        Args:
            competition_code: 联赛代码 (PL, PD, SA, BL1, FL1)
            season: 赛季年份，如2023表示2023-2024赛季
            
        Returns:
            DataFrame包含所有比赛数据
        """
        endpoint = f"{self.base_url}/competitions/{competition_code}/matches"
        params = {}
        if season:
            params["season"] = season
            
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            matches = data.get("matches", [])
            if not matches:
                self.logger.warning(f"No matches found for {competition_code} season {season}")
                return pd.DataFrame()
                
            # 转换为DataFrame
            df = self._flatten_matches_data(matches)
            self.logger.info(f"Fetched {len(df)} matches for {competition_code} season {season}")
            return df
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching data: {e}")
            return pd.DataFrame()
            
    def _flatten_matches_data(self, matches: List[Dict]) -> pd.DataFrame:
        """
        扁平化嵌套的比赛数据结构
        """
        flattened = []
        
        for match in matches:
            # 提取基本信息
            flat_match = {
                "match_id": match.get("id"),
                "utc_date": match.get("utcDate"),
                "status": match.get("status"),
                "matchday": match.get("matchday"),
                "stage": match.get("stage"),
                "group": match.get("group"),
                
                # 主队信息
                "home_team_id": match.get("homeTeam", {}).get("id"),
                "home_team_name": match.get("homeTeam", {}).get("name"),
                "home_team_short": match.get("homeTeam", {}).get("shortName"),
                "home_team_tla": match.get("homeTeam", {}).get("tla"),
                "home_team_cn": translate_team_name(match.get("homeTeam", {}).get("name")) if TRANSLATOR_AVAILABLE else match.get("homeTeam", {}).get("name"),
                
                # 客队信息
                "away_team_id": match.get("awayTeam", {}).get("id"),
                "away_team_name": match.get("awayTeam", {}).get("name"),
                "away_team_short": match.get("awayTeam", {}).get("shortName"),
                "away_team_tla": match.get("awayTeam", {}).get("tla"),
                "away_team_cn": translate_team_name(match.get("awayTeam", {}).get("name")) if TRANSLATOR_AVAILABLE else match.get("awayTeam", {}).get("name"),
                
                # 比分信息
                "winner": match.get("score", {}).get("winner"),
                "fulltime_home": match.get("score", {}).get("fullTime", {}).get("home"),
                "fulltime_away": match.get("score", {}).get("fullTime", {}).get("away"),
                "halftime_home": match.get("score", {}).get("halfTime", {}).get("home"),
                "halftime_away": match.get("score", {}).get("halfTime", {}).get("away"),
                
                # 联赛信息
                "competition_id": match.get("competition", {}).get("id"),
                "competition_name": match.get("competition", {}).get("name"),
                "competition_code": match.get("competition", {}).get("code"),
                
                # 赛季信息
                "season_id": match.get("season", {}).get("id"),
                "season_start": match.get("season", {}).get("startDate"),
                "season_end": match.get("season", {}).get("endDate"),
            }
            flattened.append(flat_match)
            
        return pd.DataFrame(flattened)
        
    def fetch_multiple_seasons(self, competition_codes: List[str], 
                               start_season: int = 2020, 
                               end_season: int = 2024) -> pd.DataFrame:
        """
        批量获取多个赛季的多个联赛数据
        """
        all_data = []
        
        for code in competition_codes:
            for season in range(start_season, end_season + 1):
                self.logger.info(f"Fetching {code} season {season}")
                df = self.fetch_competition_matches(code, season)
                if not df.empty:
                    all_data.append(df)
                time.sleep(0.5)  # 避免API限流
                
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
        
    def save_to_parquet(self, df: pd.DataFrame, filepath: str):
        """保存数据为Parquet格式"""
        if not df.empty:
            df.to_parquet(filepath, index=False)
            self.logger.info(f"Data saved to {filepath}")
            
    def fetch_standings(self, competition_code: str, season: int = None) -> pd.DataFrame:
        """
        获取联赛积分榜数据
        
        Args:
            competition_code: 联赛代码
            season: 赛季年份
            
        Returns:
            DataFrame包含球队排名和统计数据
        """
        endpoint = f"{self.base_url}/competitions/{competition_code}/standings"
        params = {}
        if season:
            params["season"] = season
            
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            standings = data.get("standings", [])
            if not standings:
                self.logger.warning(f"No standings found for {competition_code} season {season}")
                return pd.DataFrame()
                
            # 提取积分榜数据
            all_teams = []
            for standing in standings:
                if standing.get("type") == "TOTAL":  # 总积分榜
                    table = standing.get("table", [])
                    for team_entry in table:
                        team = team_entry.get("team", {})
                        stats = team_entry.get("statistics", {})
                        
                        team_data = {
                            "season": season,
                            "competition_code": competition_code,
                            "position": team_entry.get("position"),
                            "team_id": team.get("id"),
                            "team_name": team.get("name"),
                            "team_short": team.get("shortName"),
                            "team_tla": team.get("tla"),
                            "team_cn": translate_team_name(team.get("name")) if TRANSLATOR_AVAILABLE else team.get("name"),
                            "played_games": team_entry.get("playedGames"),
                            "won": team_entry.get("won"),
                            "draw": team_entry.get("draw"),
                            "lost": team_entry.get("lost"),
                            "points": team_entry.get("points"),
                            "goals_for": team_entry.get("goalsFor"),
                            "goals_against": team_entry.get("goalsAgainst"),
                            "goal_difference": team_entry.get("goalDifference"),
                            # 额外统计数据
                            "form": team_entry.get("form", ""),
                            "home_wins": stats.get("winsHome", 0),
                            "home_draws": stats.get("drawsHome", 0),
                            "home_losses": stats.get("lossesHome", 0),
                            "away_wins": stats.get("winsAway", 0),
                            "away_draws": stats.get("drawsAway", 0),
                            "away_losses": stats.get("lossesAway", 0),
                        }
                        all_teams.append(team_data)
                        
            df = pd.DataFrame(all_teams)
            self.logger.info(f"Fetched standings for {competition_code} season {season}: {len(df)} teams")
            return df
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching standings: {e}")
            return pd.DataFrame()
            
    def fetch_standings_multiple_seasons(self, competition_codes: List[str],
                                         start_season: int = 2020,
                                         end_season: int = 2024) -> pd.DataFrame:
        """
        批量获取多个赛季的积分榜数据
        """
        all_data = []
        
        for code in competition_codes:
            for season in range(start_season, end_season + 1):
                self.logger.info(f"Fetching standings for {code} season {season}")
                df = self.fetch_standings(code, season)
                if not df.empty:
                    all_data.append(df)
                time.sleep(0.5)  # API限流
                
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()