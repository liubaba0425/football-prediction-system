"""
数据管理模块 - 管理历史数据的存储、更新和查询
"""
import pandas as pd
import os
from datetime import datetime, timedelta
import logging
from typing import Optional, List
from historical_data_fetcher import HistoricalDataFetcher

class DataManager:
    def __init__(self, config: dict):
        self.config = config
        self.data_dir = os.path.expanduser(config["paths"]["data_dir"])
        self.fetcher = HistoricalDataFetcher(config["football_data_api"]["auth_token"])
        self.logger = logging.getLogger(__name__)
        
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
    def get_data_filepath(self, data_type: str, date_str: Optional[str] = None) -> str:
        """获取数据文件路径"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{data_type}_{date_str}.parquet"
        return os.path.join(self.data_dir, filename)
        
    def load_historical_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        加载历史数据，如果不存在或需要刷新则重新获取
        """
        filepath = self.get_data_filepath("historical_matches")
        
        # 检查是否需要刷新
        if not force_refresh and os.path.exists(filepath):
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_age.days < self.config["data_refresh_frequency_hours"] / 24:
                try:
                    df = pd.read_parquet(filepath)
                    self.logger.info(f"Loaded historical data from {filepath}")
                    return df
                except Exception as e:
                    self.logger.warning(f"Error loading existing data: {e}")
        
        # 获取新数据
        major_leagues = ["PL", "PD", "SA", "BL1", "FL1"]  # 五大联赛
        df = self.fetcher.fetch_multiple_seasons(
            competition_codes=major_leagues,
            start_season=2020,
            end_season=2024
        )
        
        if not df.empty:
            # 保存数据
            self.fetcher.save_to_parquet(df, filepath)
            
            # 保存备份
            backup_path = self.get_data_filepath("historical_matches", "backup")
            self.fetcher.save_to_parquet(df, backup_path)
            
        return df
        
    def get_team_historical_matches(self, team_id: int, df: pd.DataFrame) -> pd.DataFrame:
        """获取指定球队的历史比赛"""
        team_matches = df[
            (df["home_team_id"] == team_id) | (df["away_team_id"] == team_id)
        ].copy()
        
        # 按时间排序
        team_matches["utc_date"] = pd.to_datetime(team_matches["utc_date"])
        team_matches = team_matches.sort_values("utc_date")
        
        return team_matches
        
    def get_head_to_head(self, team1_id: int, team2_id: int, df: pd.DataFrame) -> pd.DataFrame:
        """获取两队历史交锋记录"""
        h2h = df[
            ((df["home_team_id"] == team1_id) & (df["away_team_id"] == team2_id)) |
            ((df["home_team_id"] == team2_id) & (df["away_team_id"] == team1_id))
        ].copy()
        
        h2h["utc_date"] = pd.to_datetime(h2h["utc_date"])
        h2h = h2h.sort_values("utc_date", ascending=False)
        
        return h2h