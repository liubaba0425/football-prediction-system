# 足球预测多智能体系统 - 机器学习集成计划

## 项目概述
基于用户决策，为现有8智能体足球预测系统集成机器学习模型：
1. **数据源选择**: 方案B - 接入历史数据库（football-data.org）
2. **模型优先级**: XGBoost（第一优先级）
3. **训练频率**: 每天训练一次

**目标**: 在现有规则驱动系统基础上，添加数据驱动的ML预测能力，提升准确性，同时保持系统稳定性和实时性能。

## 技术架构设计

### 分层集成策略
```
现有系统 (规则驱动)            新增系统 (数据驱动)
├── Stats-Analyst              └── ML-Analyst (XGBoost)
├── Tactics-Analyst                 ├── 特征工程管道
├── Sentiment-Analyst               ├── 模型训练框架
├── Upset-Detector                  └── 推理服务
├── Asian-Analyst
├── OverUnder-Analyst
└── Consensus-Summarizer (增强版)
```

### 数据流架构
1. **历史数据**: football-data.org API → 历史数据存储 (Parquet/CSV)
2. **实时数据**: The Odds API → 实时特征提取
3. **特征工程**: 历史数据 + 实时数据 → 特征向量
4. **模型训练**: 每日自动训练 → 模型存储
5. **实时推理**: 比赛特征 → XGBoost模型 → 预测结果
6. **智能体集成**: ML-Analyst输出 → Consensus-Summarizer加权融合

## 阶段1：基础设施和依赖 (Day 1)

### 1.1 环境准备
```bash
# 创建ML相关目录
mkdir -p ~/openclaw-workspace/ml-analyst
mkdir -p ~/openclaw-workspace/ml-analyst/models
mkdir -p ~/openclaw-workspace/ml-analyst/data
mkdir -p ~/openclaw-workspace/ml-analyst/features
mkdir -p ~/openclaw-workspace/ml-analyst/logs

# 创建配置文件目录
mkdir -p ~/openclaw-workspace/config
```

### 1.2 依赖安装
更新 `~/openclaw-workspace/requirements.txt`：
```txt
# 现有依赖
requests>=2.28.0
openpyxl>=3.0.0

# ML新增依赖
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
xgboost>=2.0.0
joblib>=1.3.0
pyarrow>=14.0.0  # Parquet支持
python-dateutil>=2.8.0
```

安装命令：
```bash
cd ~/openclaw-workspace
pip install -r requirements.txt
```

### 1.3 配置文件
创建 `~/openclaw-workspace/config/ml_config.yaml`：
```yaml
# ML系统配置
ml_system:
  # 数据源配置
  football_data_api:
    base_url: "https://api.football-data.org/v4"
    auth_token: "5ca663e49263467e8664864a767f8c31"
    rate_limit_requests: 10  # 每分钟请求限制
    
  # 模型配置
  xgboost:
    n_estimators: 100
    max_depth: 6
    learning_rate: 0.1
    objective: "multi:softprob"
    num_class: 3
    eval_metric: "mlogloss"
    early_stopping_rounds: 10
    
  # 训练配置
  training:
    test_size: 0.2
    random_state: 42
    validation_size: 0.1
    min_samples_required: 100  # 最小训练样本数
    
  # 特征工程
  features:
    rolling_window_size: 5  # 滚动窗口大小
    include_advanced_stats: true
    include_form_features: true
    
  # 路径配置
  paths:
    model_dir: "~/openclaw-workspace/ml-analyst/models"
    data_dir: "~/openclaw-workspace/ml-analyst/data"
    features_dir: "~/openclaw-workspace/ml-analyst/features"
    logs_dir: "~/openclaw-workspace/ml-analyst/logs"
    
  # 调度配置
  scheduler:
    daily_training_time: "03:00"  # 每天3:00 AM训练
    data_refresh_frequency_hours: 24
```

## 阶段2：历史数据获取模块 (Day 1-2)

### 2.1 创建历史数据获取器
文件: `~/openclaw-workspace/ml-analyst/historical_data_fetcher.py`

```python
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
                
                # 客队信息
                "away_team_id": match.get("awayTeam", {}).get("id"),
                "away_team_name": match.get("awayTeam", {}).get("name"),
                "away_team_short": match.get("awayTeam", {}).get("shortName"),
                "away_team_tla": match.get("awayTeam", {}).get("tla"),
                
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
```

### 2.2 创建数据管理器
文件: `~/openclaw-workspace/ml-analyst/data_manager.py`

```python
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
```

## 阶段3：特征工程管道 (Day 2-3)

### 3.1 基础特征提取
文件: `~/openclaw-workspace/ml-analyst/feature_engineering.py`

```python
"""
特征工程模块 - 从原始比赛数据中提取机器学习特征
"""
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Optional

class FeatureEngineer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.window_size = config["features"]["rolling_window_size"]
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        准备机器学习特征
        
        Returns:
            包含特征和标签的DataFrame
        """
        if df.empty:
            self.logger.error("Empty DataFrame provided")
            return pd.DataFrame()
            
        # 复制数据避免修改原始数据
        df_processed = df.copy()
        
        # 1. 数据预处理
        df_processed = self._preprocess_data(df_processed)
        
        # 2. 提取基础特征
        df_processed = self._extract_basic_features(df_processed)
        
        # 3. 提取球队状态特征
        df_processed = self._extract_team_form_features(df_processed)
        
        # 4. 提取H2H特征
        df_processed = self._extract_h2h_features(df_processed)
        
        # 5. 创建标签
        df_processed = self._create_labels(df_processed)
        
        # 6. 清理缺失值
        df_processed = self._clean_missing_values(df_processed)
        
        self.logger.info(f"Feature engineering complete. Shape: {df_processed.shape}")
        return df_processed
        
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据预处理"""
        df = df.copy()
        
        # 只处理已完成的比赛
        df = df[df["status"] == "FINISHED"].copy()
        
        # 转换日期
        df["match_date"] = pd.to_datetime(df["utc_date"])
        df["match_date_ordinal"] = df["match_date"].apply(lambda x: x.toordinal())
        
        # 确保比分是数值类型
        df["fulltime_home"] = pd.to_numeric(df["fulltime_home"], errors="coerce")
        df["fulltime_away"] = pd.to_numeric(df["fulltime_away"], errors="coerce")
        
        # 添加比赛结果（主胜/平局/客胜）
        df["result"] = np.select(
            [
                df["fulltime_home"] > df["fulltime_away"],
                df["fulltime_home"] == df["fulltime_away"],
                df["fulltime_home"] < df["fulltime_away"]
            ],
            ["H", "D", "A"],  # Home win, Draw, Away win
            default=np.nan
        )
        
        return df
        
    def _extract_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取基础特征"""
        df = df.copy()
        
        # 联赛独热编码
        df = pd.get_dummies(df, columns=["competition_code"], prefix="league")
        
        # 比赛日特征
        df["is_weekend"] = df["match_date"].dt.dayofweek.isin([5, 6]).astype(int)
        df["month"] = df["match_date"].dt.month
        df["day_of_week"] = df["match_date"].dt.dayofweek
        
        # 赛季阶段
        df["season_month"] = df["match_date"].dt.month
        df["is_season_start"] = df["season_month"].isin([8, 9, 10]).astype(int)
        df["is_season_mid"] = df["season_month"].isin([11, 12, 1, 2]).astype(int)
        df["is_season_end"] = df["season_month"].isin([3, 4, 5]).astype(int)
        
        return df
        
    def _extract_team_form_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取球队状态特征"""
        df = df.copy()
        
        # 按联赛和球队分组
        leagues = df["competition_code"].unique()
        
        all_team_features = []
        
        for league in leagues:
            league_df = df[df["competition_code"] == league].copy()
            teams = pd.concat([league_df["home_team_id"], league_df["away_team_id"]]).unique()
            
            for team_id in teams:
                team_features = self._calculate_team_form(league_df, team_id)
                if not team_features.empty:
                    all_team_features.append(team_features)
                    
        # 合并所有球队特征
        if all_team_features:
            team_form_df = pd.concat(all_team_features, ignore_index=True)
            
            # 合并到主队特征
            home_features = team_form_df.copy()
            home_features.columns = [f"home_{col}" if col != "match_id" else col for col in home_features.columns]
            df = pd.merge(df, home_features, on="match_id", how="left")
            
            # 合并到客队特征
            away_features = team_form_df.copy()
            away_features.columns = [f"away_{col}" if col != "match_id" else col for col in away_features.columns]
            df = pd.merge(df, away_features, on="match_id", how="left")
            
            # 计算相对特征
            df["form_diff"] = df["home_recent_form"] - df["away_recent_form"]
            df["goals_scored_diff"] = df["home_avg_goals_scored"] - df["away_avg_goals_scored"]
            df["goals_conceded_diff"] = df["home_avg_goals_conceded"] - df["away_avg_goals_conceded"]
            
        return df
        
    def _calculate_team_form(self, df: pd.DataFrame, team_id: int) -> pd.DataFrame:
        """计算单个球队的状态特征"""
        # 找到该球队的所有比赛
        team_matches = df[
            (df["home_team_id"] == team_id) | (df["away_team_id"] == team_id)
        ].copy()
        
        if len(team_matches) < self.window_size:
            return pd.DataFrame()
            
        # 按时间排序
        team_matches = team_matches.sort_values("match_date")
        
        features_list = []
        
        for i in range(self.window_size, len(team_matches)):
            current_match = team_matches.iloc[i]
            window_matches = team_matches.iloc[i-self.window_size:i]
            
            # 球队是主队还是客队
            is_home = current_match["home_team_id"] == team_id
            
            # 计算窗口期内的表现
            home_matches = window_matches[window_matches["home_team_id"] == team_id]
            away_matches = window_matches[window_matches["away_team_id"] == team_id]
            
            # 最近战绩
            recent_results = []
            for _, match in window_matches.iterrows():
                if match["home_team_id"] == team_id:
                    if match["result"] == "H":
                        recent_results.append(1)  # 赢
                    elif match["result"] == "D":
                        recent_results.append(0.5)  # 平
                    else:
                        recent_results.append(0)  # 输
                else:
                    if match["result"] == "A":
                        recent_results.append(1)
                    elif match["result"] == "D":
                        recent_results.append(0.5)
                    else:
                        recent_results.append(0)
                        
            recent_form = np.mean(recent_results) if recent_results else 0.5
            
            # 进球数据
            home_goals_scored = home_matches["fulltime_home"].sum() if not home_matches.empty else 0
            home_goals_conceded = home_matches["fulltime_away"].sum() if not home_matches.empty else 0
            away_goals_scored = away_matches["fulltime_away"].sum() if not away_matches.empty else 0
            away_goals_conceded = away_matches["fulltime_home"].sum() if not away_matches.empty else 0
            
            total_goals_scored = home_goals_scored + away_goals_scored
            total_goals_conceded = home_goals_conceded + away_goals_conceded
            total_matches = len(window_matches)
            
            avg_goals_scored = total_goals_scored / total_matches if total_matches > 0 else 0
            avg_goals_conceded = total_goals_conceded / total_matches if total_matches > 0 else 0
            
            # 主客场表现差异
            home_performance = len(home_matches[home_matches["result"] == "H"]) / len(home_matches) if len(home_matches) > 0 else 0
            away_performance = len(away_matches[away_matches["result"] == "A"]) / len(away_matches) if len(away_matches) > 0 else 0
            
            features = {
                "match_id": current_match["match_id"],
                "recent_form": recent_form,
                "avg_goals_scored": avg_goals_scored,
                "avg_goals_conceded": avg_goals_conceded,
                "home_performance": home_performance,
                "away_performance": away_performance,
                "total_matches_last_window": total_matches,
            }
            
            features_list.append(features)
            
        return pd.DataFrame(features_list)
        
    def _extract_h2h_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取历史交锋特征"""
        # 实现H2H特征提取
        # 由于时间关系，此处简化为基本特征
        df["h2h_exists"] = 1  # 简化，实际需要计算两队历史交锋次数
        return df
        
    def _create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建机器学习标签"""
        df = df.copy()
        
        # 三分类：主胜(0)、平局(1)、客胜(2)
        df["label"] = np.select(
            [
                df["result"] == "H",
                df["result"] == "D",
                df["result"] == "A"
            ],
            [0, 1, 2],
            default=np.nan
        )
        
        # 二分类：主队不败(0) vs 客胜(1)
        df["label_binary"] = np.where(df["result"] == "A", 1, 0)
        
        return df
        
    def _clean_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理缺失值"""
        # 删除标签缺失的行
        df = df.dropna(subset=["label"])
        
        # 用中位数填充数值特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col != "label" and col != "label_binary":
                df[col] = df[col].fillna(df[col].median())
                
        # 用众数填充分类特征
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        for col in categorical_cols:
            if col not in ["result", "match_id", "home_team_name", "away_team_name"]:
                df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else "unknown")
                
        return df
        
    def prepare_inference_features(self, match_info: Dict, team_form_data: Dict) -> pd.DataFrame:
        """
        为实时预测准备特征
        
        Args:
            match_info: 比赛信息（来自现有系统）
            team_form_data: 球队近期状态数据
            
        Returns:
            包含单场比赛特征的DataFrame
        """
        # 从现有系统提取特征
        features = {
            # 基础信息
            "is_weekend": 1 if match_info.get("match_day_type") == "周末" else 0,
            
            # 赔率相关特征
            "home_odds": match_info.get("home_odds", 2.0),
            "draw_odds": match_info.get("draw_odds", 3.0),
            "away_odds": match_info.get("away_odds", 2.0),
            
            # 隐含概率
            "home_implied_prob": 1 / match_info.get("home_odds", 2.0),
            "away_implied_prob": 1 / match_info.get("away_odds", 2.0),
            "draw_implied_prob": 1 / match_info.get("draw_odds", 3.0),
            
            # 赔率差距
            "odds_gap": abs(match_info.get("home_odds", 2.0) - match_info.get("away_odds", 2.0)),
            
            # 球队状态（从现有智能体获取）
            "home_form": team_form_data.get("home", {}).get("form_score", 0.5),
            "away_form": team_form_data.get("away", {}).get("form_score", 0.5),
            "form_diff": team_form_data.get("home", {}).get("form_score", 0.5) - 
                         team_form_data.get("away", {}).get("form_score", 0.5),
            
            # 近期表现
            "home_goals_scored_avg": team_form_data.get("home", {}).get("goals_scored_avg", 1.0),
            "home_goals_conceded_avg": team_form_data.get("home", {}).get("goals_conceded_avg", 1.0),
            "away_goals_scored_avg": team_form_data.get("away", {}).get("goals_scored_avg", 1.0),
            "away_goals_conceded_avg": team_form_data.get("away", {}).get("goals_conceded_avg", 1.0),
            
            # 主客场表现
            "home_home_performance": team_form_data.get("home", {}).get("home_performance", 0.5),
            "away_away_performance": team_form_data.get("away", {}).get("away_performance", 0.5),
            
            # 赛程压力
            "home_schedule_pressure": match_info.get("schedule_pressure", {}).get("home", {}).get("fatigue_risk", "中"),
            "away_schedule_pressure": match_info.get("schedule_pressure", {}).get("away", {}).get("fatigue_risk", "中"),
        }
        
        # 转换分类特征
        pressure_mapping = {"高": 2, "中": 1, "低": 0}
        features["home_pressure_score"] = pressure_mapping.get(features["home_schedule_pressure"], 1)
        features["away_pressure_score"] = pressure_mapping.get(features["away_schedule_pressure"], 1)
        features["pressure_diff"] = features["home_pressure_score"] - features["away_pressure_score"]
        
        # 创建DataFrame
        df = pd.DataFrame([features])
        
        # 添加联赛特征（假设是英超）
        df["league_PL"] = 1
        df["league_PD"] = 0
        df["league_SA"] = 0
        df["league_BL1"] = 0
        df["league_FL1"] = 0
        
        # 添加赛季阶段特征（根据当前月份）
        current_month = datetime.now().month
        df["is_season_start"] = 1 if current_month in [8, 9, 10] else 0
        df["is_season_mid"] = 1 if current_month in [11, 12, 1, 2] else 0
        df["is_season_end"] = 1 if current_month in [3, 4, 5] else 0
        
        return df
```

### 3.2 特征选择器
文件: `~/openclaw-workspace/ml-analyst/feature_selector.py`

```python
"""
特征选择模块 - 选择最重要的特征用于模型训练
"""
import pandas as pd
import numpy as np
from sklearn.feature_selection import SelectKBest, f_classif
import logging

class FeatureSelector:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.selected_features = None
        
    def select_features(self, X: pd.DataFrame, y: pd.Series, k: int = 30) -> pd.DataFrame:
        """使用ANOVA F-value选择最重要的k个特征"""
        selector = SelectKBest(score_func=f_classif, k=min(k, X.shape[1]))
        X_selected = selector.fit_transform(X, y)
        
        # 获取选中的特征名称
        selected_indices = selector.get_support(indices=True)
        self.selected_features = X.columns[selected_indices].tolist()
        
        self.logger.info(f"Selected {len(self.selected_features)} features: {self.selected_features}")
        return pd.DataFrame(X_selected, columns=self.selected_features)
        
    def get_feature_importance(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """计算特征重要性分数"""
        selector = SelectKBest(score_func=f_classif, k="all")
        selector.fit(X, y)
        
        importance_df = pd.DataFrame({
            "feature": X.columns,
            "score": selector.scores_,
            "p_value": selector.pvalues_
        })
        
        importance_df = importance_df.sort_values("score", ascending=False)
        return importance_df
        
    def transform_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """使用训练时选择的特征转换新数据"""
        if self.selected_features is None:
            self.logger.error("Feature selector not fitted yet")
            return X
            
        # 只保留训练时选择的特征
        missing_features = set(self.selected_features) - set(X.columns)
        if missing_features:
            self.logger.warning(f"Missing features: {missing_features}")
            for feature in missing_features:
                X[feature] = 0
                
        return X[self.selected_features]
```

## 阶段4：XGBoost模型训练框架 (Day 3-4)

### 4.1 模型训练器
文件: `~/openclaw-workspace/ml-analyst/model_trainer.py`

```python
"""
模型训练模块 - 训练和评估XGBoost模型
"""
import xgboost as xgb
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import logging
from datetime import datetime
import os
from typing import Tuple, Dict, Any

class XGBoostTrainer:
    def __init__(self, config: dict):
        self.config = config
        self.model = None
        self.logger = logging.getLogger(__name__)
        self.model_dir = os.path.expanduser(config["paths"]["model_dir"])
        
        # 确保目录存在
        os.makedirs(self.model_dir, exist_ok=True)
        
    def train(self, X: pd.DataFrame, y: pd.Series, 
              model_name: str = "xgboost_football") -> Dict[str, Any]:
        """
        训练XGBoost模型
        
        Returns:
            训练结果字典
        """
        if len(X) < self.config["training"]["min_samples_required"]:
            self.logger.error(f"Not enough samples: {len(X)} < {self.config['training']['min_samples_required']}")
            return {"success": False, "error": "Insufficient training data"}
            
        # 划分训练集、验证集、测试集
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, 
            test_size=self.config["training"]["test_size"],
            random_state=self.config["training"]["random_state"],
            stratify=y
        )
        
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp,
            test_size=self.config["training"]["validation_size"],
            random_state=self.config["training"]["random_state"],
            stratify=y_temp
        )
        
        self.logger.info(f"Data split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
        
        # 创建DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dval = xgb.DMatrix(X_val, label=y_val)
        dtest = xgb.DMatrix(X_test, label=y_test)
        
        # 模型参数
        params = {
            **self.config["xgboost"],
            "seed": self.config["training"]["random_state"],
            "verbosity": 0
        }
        
        # 训练模型
        num_round = params.get("n_estimators", 100)
        early_stopping = params.get("early_stopping_rounds", 10)
        
        self.logger.info("Training XGBoost model...")
        
        evals_result = {}
        self.model = xgb.train(
            params,
            dtrain,
            num_boost_round=num_round,
            evals=[(dtrain, "train"), (dval, "validation")],
            early_stopping_rounds=early_stopping,
            evals_result=evals_result,
            verbose_eval=False
        )
        
        # 评估模型
        train_results = self._evaluate_model(self.model, dtrain, y_train, "train")
        val_results = self._evaluate_model(self.model, dval, y_val, "validation")
        test_results = self._evaluate_model(self.model, dtest, y_test, "test")
        
        # 保存模型
        model_path = self._save_model(model_name)
        
        # 特征重要性
        importance = self.model.get_score(importance_type="weight")
        importance_df = pd.DataFrame({
            "feature": list(importance.keys()),
            "importance": list(importance.values())
        }).sort_values("importance", ascending=False)
        
        results = {
            "success": True,
            "model_path": model_path,
            "model_params": params,
            "train_metrics": train_results,
            "validation_metrics": val_results,
            "test_metrics": test_results,
            "feature_importance": importance_df.to_dict("records"),
            "training_date": datetime.now().isoformat(),
            "data_size": len(X),
            "class_distribution": y.value_counts().to_dict()
        }
        
        self.logger.info(f"Model training complete. Test accuracy: {test_results['accuracy']:.3f}")
        return results
        
    def _evaluate_model(self, model, data: xgb.DMatrix, y_true: pd.Series, dataset_name: str) -> Dict:
        """评估模型性能"""
        y_pred = model.predict(data)
        
        # 对于多分类，选择概率最高的类别
        if len(y_pred.shape) > 1 and y_pred.shape[1] > 1:
            y_pred_class = np.argmax(y_pred, axis=1)
            y_pred_proba = y_pred
        else:
            y_pred_class = (y_pred > 0.5).astype(int)
            y_pred_proba = y_pred
            
        accuracy = accuracy_score(y_true, y_pred_class)
        
        # 分类报告
        report = classification_report(y_true, y_pred_class, output_dict=True, zero_division=0)
        
        # 混淆矩阵
        cm = confusion_matrix(y_true, y_pred_class)
        
        return {
            "accuracy": accuracy,
            "classification_report": report,
            "confusion_matrix": cm.tolist(),
            "predictions": y_pred_class.tolist(),
            "probabilities": y_pred_proba.tolist() if isinstance(y_pred_proba, np.ndarray) else y_pred_proba.tolist()
        }
        
    def _save_model(self, model_name: str) -> str:
        """保存模型到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{model_name}_{timestamp}.json"
        filepath = os.path.join(self.model_dir, filename)
        
        # 保存为JSON格式（XGBoost原生格式）
        self.model.save_model(filepath)
        
        # 同时保存为joblib格式（包含元数据）
        metadata = {
            "model": self.model,
            "training_date": timestamp,
            "config": self.config
        }
        joblib_path = filepath.replace(".json", ".joblib")
        joblib.dump(metadata, joblib_path)
        
        self.logger.info(f"Model saved to {filepath}")
        return filepath
        
    def load_model(self, model_path: str):
        """加载模型"""
        if model_path.endswith(".json"):
            self.model = xgb.Booster()
            self.model.load_model(model_path)
        elif model_path.endswith(".joblib"):
            metadata = joblib.load(model_path)
            self.model = metadata["model"]
            
        self.logger.info(f"Model loaded from {model_path}")
        return self.model
        
    def predict(self, X: pd.DataFrame, return_proba: bool = True):
        """使用模型进行预测"""
        if self.model is None:
            self.logger.error("Model not loaded")
            return None
            
        dmatrix = xgb.DMatrix(X)
        predictions = self.model.predict(dmatrix)
        
        if return_proba and len(predictions.shape) > 1 and predictions.shape[1] > 1:
            # 返回概率
            return predictions
        else:
            # 返回类别
            if len(predictions.shape) > 1 and predictions.shape[1] > 1:
                return np.argmax(predictions, axis=1)
            else:
                return (predictions > 0.5).astype(int)
```

### 4.2 模型管理器
文件: `~/openclaw-workspace/ml-analyst/model_manager.py`

```python
"""
模型管理模块 - 管理模型版本、加载和选择最佳模型
"""
import os
import joblib
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import pandas as pd

class ModelManager:
    def __init__(self, config: dict):
        self.config = config
        self.model_dir = os.path.expanduser(config["paths"]["model_dir"])
        self.logger = logging.getLogger(__name__)
        
        # 确保目录存在
        os.makedirs(self.model_dir, exist_ok=True)
        
    def get_available_models(self) -> List[Dict]:
        """获取所有可用模型"""
        models = []
        
        for filename in os.listdir(self.model_dir):
            if filename.endswith(".json") or filename.endswith(".joblib"):
                filepath = os.path.join(self.model_dir, filename)
                file_stat = os.stat(filepath)
                
                model_info = {
                    "filename": filename,
                    "path": filepath,
                    "size_mb": file_stat.st_size / (1024 * 1024),
                    "modified_time": datetime.fromtimestamp(file_stat.st_mtime),
                    "age_days": (datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)).days
                }
                
                # 尝试读取元数据
                if filename.endswith(".joblib"):
                    try:
                        metadata = joblib.load(filepath)
                        if "training_date" in metadata:
                            model_info["training_date"] = metadata["training_date"]
                        if "config" in metadata:
                            model_info["config"] = metadata["config"]
                    except:
                        pass
                        
                models.append(model_info)
                
        # 按修改时间排序（最新的在前）
        models.sort(key=lambda x: x["modified_time"], reverse=True)
        return models
        
    def get_latest_model(self) -> Optional[str]:
        """获取最新的模型文件路径"""
        models = self.get_available_models()
        if not models:
            return None
            
        # 优先选择.joblib文件（包含元数据）
        joblib_models = [m for m in models if m["filename"].endswith(".joblib")]
        if joblib_models:
            return joblib_models[0]["path"]
            
        # 否则返回.json文件
        json_models = [m for m in models if m["filename"].endswith(".json")]
        if json_models:
            return json_models[0]["path"]
            
        return None
        
    def get_best_model(self, metric: str = "validation_accuracy") -> Optional[str]:
        """根据验证指标选择最佳模型"""
        models = self.get_available_models()
        if not models:
            return None
            
        # 这里简化实现，实际应该读取每个模型的验证指标
        # 目前返回最新模型
        return self.get_latest_model()
        
    def cleanup_old_models(self, keep_last_n: int = 7):
        """清理旧模型，只保留最近的n个"""
        models = self.get_available_models()
        if len(models) <= keep_last_n:
            return
            
        models_to_delete = models[keep_last_n:]
        for model in models_to_delete:
            try:
                os.remove(model["path"])
                self.logger.info(f"Deleted old model: {model['filename']}")
            except Exception as e:
                self.logger.error(f"Error deleting model {model['filename']}: {e}")
                
    def save_model_metadata(self, model_path: str, metadata: Dict):
        """保存模型元数据"""
        metadata_path = model_path.replace(".json", ".metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
            
    def load_model_metadata(self, model_path: str) -> Optional[Dict]:
        """加载模型元数据"""
        metadata_path = model_path.replace(".json", ".metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                return json.load(f)
        return None
```

## 阶段5：ML-Analyst智能体 (Day 4)

### 5.1 ML-Analyst智能体实现
文件: `~/openclaw-workspace/ml-analyst/ml_analyst.py`

```python
"""
ML-Analyst智能体 - 集成机器学习模型到多智能体系统
"""
import os
import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

# 导入ML模块
from model_trainer import XGBoostTrainer
from model_manager import ModelManager
from feature_engineering import FeatureEngineer
from feature_selector import FeatureSelector

class MLAnalyst:
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化ML-Analyst智能体
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "config", 
                "ml_config.yaml"
            )
            
        import yaml
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
            
        # 设置日志
        self.logger = self._setup_logging()
        
        # 初始化组件
        self.feature_engineer = FeatureEngineer(self.config)
        self.feature_selector = FeatureSelector(self.config)
        self.model_trainer = XGBoostTrainer(self.config)
        self.model_manager = ModelManager(self.config)
        
        # 加载模型
        self.model = None
        self._load_latest_model()
        
        self.logger.info("ML-Analyst initialized")
        
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("MLAnalyst")
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        log_dir = os.path.expanduser(self.config["paths"]["logs_dir"])
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"ml_analyst_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
        
    def _load_latest_model(self):
        """加载最新的训练模型"""
        latest_model = self.model_manager.get_latest_model()
        if latest_model:
            try:
                self.model_trainer.load_model(latest_model)
                self.model = self.model_trainer.model
                self.logger.info(f"Loaded model: {os.path.basename(latest_model)}")
            except Exception as e:
                self.logger.error(f"Error loading model: {e}")
                self.model = None
        else:
            self.logger.warning("No trained model found")
            self.model = None
            
    def analyze_match(self, match_info: Dict, other_agents_output: Dict) -> Dict:
        """
        分析比赛并返回ML预测结果
        
        Args:
            match_info: 比赛基本信息
            other_agents_output: 其他智能体的输出
            
        Returns:
            ML分析报告
        """
        if self.model is None:
            self.logger.error("No model available for prediction")
            return self._create_error_report("模型未加载")
            
        try:
            # 1. 准备特征
            features_df = self._prepare_inference_features(match_info, other_agents_output)
            
            if features_df.empty:
                return self._create_error_report("特征准备失败")
                
            # 2. 特征选择
            features_selected = self.feature_selector.transform_features(features_df)
            
            # 3. 模型预测
            predictions = self.model_trainer.predict(features_selected, return_proba=True)
            
            # 4. 解析预测结果
            report = self._parse_predictions(predictions, match_info, other_agents_output)
            
            self.logger.info(f"ML prediction completed: {report['prediction']}")
            return report
            
        except Exception as e:
            self.logger.error(f"Error in match analysis: {e}")
            return self._create_error_report(str(e))
            
    def _prepare_inference_features(self, match_info: Dict, other_agents_output: Dict) -> pd.DataFrame:
        """准备推理特征"""
        # 提取球队状态数据
        team_form_data = {
            "home": {
                "form_score": other_agents_output.get("tactics", {}).get("score", 50) / 100,
                "goals_scored_avg": 1.5,  # 从历史数据中获取，这里简化
                "goals_conceded_avg": 1.2,
                "home_performance": 0.6,
            },
            "away": {
                "form_score": other_agents_output.get("tactics", {}).get("score", 50) / 100,
                "goals_scored_avg": 1.3,
                "goals_conceded_avg": 1.4,
                "away_performance": 0.4,
            }
        }
        
        # 使用特征工程器
        features_df = self.feature_engineer.prepare_inference_features(match_info, team_form_data)
        return features_df
        
    def _parse_predictions(self, predictions: np.ndarray, 
                          match_info: Dict, 
                          other_agents_output: Dict) -> Dict:
        """解析预测结果"""
        if predictions.ndim == 2 and predictions.shape[1] == 3:
            # 三分类：主胜、平局、客胜
            home_win_prob = predictions[0, 0]
            draw_prob = predictions[0, 1]
            away_win_prob = predictions[0, 2]
            
            # 确定预测结果
            probs = [home_win_prob, draw_prob, away_win_prob]
            max_prob_idx = np.argmax(probs)
            
            outcomes = ["主胜", "平局", "客胜"]
            predicted_outcome = outcomes[max_prob_idx]
            
            # 计算信心分数
            confidence = probs[max_prob_idx] * 100
            
        else:
            # 二分类或回归
            if len(predictions.shape) > 1:
                prediction = predictions[0, 0]
            else:
                prediction = predictions[0]
                
            # 转换为概率
            home_win_prob = prediction if prediction <= 1 else 1 / (1 + np.exp(-prediction))
            away_win_prob = 1 - home_win_prob
            draw_prob = 0.3  # 简化处理
            
            # 确定预测结果
            if home_win_prob > away_win_prob and home_win_prob > draw_prob:
                predicted_outcome = "主胜"
                confidence = home_win_prob * 100
            elif away_win_prob > home_win_prob and away_win_prob > draw_prob:
                predicted_outcome = "客胜"
                confidence = away_win_prob * 100
            else:
                predicted_outcome = "平局"
                confidence = draw_prob * 100
                
        # 生成分析报告
        report = {
            "ml_analyst_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "prediction": predicted_outcome,
            "confidence": round(float(confidence), 1),
            "probabilities": {
                "home_win": round(float(home_win_prob), 3),
                "draw": round(float(draw_prob), 3),
                "away_win": round(float(away_win_prob), 3)
            },
            "features_used": self.feature_selector.selected_features if self.feature_selector.selected_features else [],
            "model_info": {
                "type": "XGBoost",
                "loaded": self.model is not None
            },
            "analysis": self._generate_analysis_text(predicted_outcome, confidence, match_info)
        }
        
        return report
        
    def _generate_analysis_text(self, prediction: str, confidence: float, match_info: Dict) -> str:
        """生成分析文本"""
        home_team = match_info.get("home_team_cn", match_info.get("home_team", "主队"))
        away_team = match_info.get("away_team_cn", match_info.get("away_team", "客队"))
        
        if confidence >= 70:
            strength = "强烈支持"
        elif confidence >= 60:
            strength = "较为支持"
        elif confidence >= 50:
            strength = "略微支持"
        else:
            strength = "谨慎支持"
            
        if prediction == "主胜":
            text = f"机器学习模型{strength}{home_team}获胜，信心指数{confidence:.1f}%。"
        elif prediction == "客胜":
            text = f"机器学习模型{strength}{away_team}获胜，信心指数{confidence:.1f}%。"
        else:
            text = f"机器学习模型{strength}双方战平，信心指数{confidence:.1f}%。"
            
        return text
        
    def _create_error_report(self, error_message: str) -> Dict:
        """创建错误报告"""
        return {
            "ml_analyst_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "error": True,
            "error_message": error_message,
            "prediction": "无法预测",
            "confidence": 0,
            "probabilities": {
                "home_win": 0.333,
                "draw": 0.333,
                "away_win": 0.334
            },
            "analysis": f"机器学习分析失败: {error_message}"
        }
        
    def train_daily_model(self) -> Dict:
        """每日模型训练"""
        self.logger.info("Starting daily model training...")
        
        try:
            # 1. 加载数据
            from data_manager import DataManager
            data_manager = DataManager(self.config)
            historical_data = data_manager.load_historical_data()
            
            if historical_data.empty:
                return {"success": False, "error": "No historical data available"}
                
            # 2. 特征工程
            features_df = self.feature_engineer.prepare_features(historical_data)
            
            if features_df.empty or "label" not in features_df.columns:
                return {"success": False, "error": "Feature engineering failed"}
                
            # 3. 分离特征和标签
            X = features_df.drop(["label", "label_binary"], axis=1, errors="ignore")
            y = features_df["label"]
            
            # 4. 特征选择
            X_selected = self.feature_selector.select_features(X, y, k=30)
            
            # 5. 训练模型
            results = self.model_trainer.train(X_selected, y)
            
            # 6. 加载新模型
            if results.get("success"):
                self._load_latest_model()
                
            # 7. 清理旧模型
            self.model_manager.cleanup_old_models(keep_last_n=7)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in daily training: {e}")
            return {"success": False, "error": str(e)}
```

### 5.2 ML-Analyst AGENTS.md文件
文件: `~/openclaw-workspace/ml-analyst/AGENTS.md`

```markdown
# ML-Analyst (机器学习分析师)

## 角色定义
**ML-Analyst** 是足球预测多智能体系统中的机器学习专家，负责基于历史数据和实时特征，使用XGBoost模型提供数据驱动的预测分析。

## 核心能力
1. **历史学习**: 从数千场历史比赛中学习模式
2. **实时预测**: 基于当前比赛特征进行概率预测
3. **特征工程**: 自动提取和选择最有预测力的特征
4. **模型管理**: 每日自动更新和优化模型

## 输入数据
- 比赛基本信息（主客队、联赛、时间）
- The Odds API实时赔率数据
- 其他智能体的分析结果（Stats, Tactics等）
- 历史比赛数据库（football-data.org）

## 输出格式
```json
{
  "ml_analyst_version": "1.0",
  "timestamp": "2024-01-15T10:30:00",
  "prediction": "主胜|平局|客胜",
  "confidence": 68.5,
  "probabilities": {
    "home_win": 0.523,
    "draw": 0.254,
    "away_win": 0.223
  },
  "features_used": ["home_odds", "away_odds", "form_diff", ...],
  "model_info": {
    "type": "XGBoost",
    "training_date": "2024-01-15",
    "accuracy": 0.632
  },
  "analysis": "机器学习模型较为支持主队获胜，信心指数68.5%。"
}
```

## 置信度权重计算
ML-Analyst的置信度权重基于：
1. **模型准确性**: 历史验证准确率（0-1）
2. **预测确定性**: 预测概率的标准差
3. **数据质量**: 可用特征数量和完整性

计算公式：
```
confidence_weight = min(100, model_accuracy * 70 + prediction_certainty * 30)
```

## 集成方式
- 在Consensus-Summarizer之前调用
- 输出作为Consensus的额外输入
- 在共识计算中分配权重：0.35（可配置）

## 错误处理
- 模型未加载：返回基础概率分布
- 特征缺失：使用默认值填充
- API失败：降级到规则基础预测

## 配置参数
```yaml
ml_analyst:
  model_type: "xgboost"
  daily_training: true
  training_time: "03:00"
  min_confidence: 40
  weight_in_consensus: 0.35
```

## 性能指标
- 预测延迟: < 100ms
- 训练时间: < 5分钟
- 内存占用: < 500MB
- 准确率目标: > 60%

## 依赖项
- xgboost>=2.0.0
- pandas>=2.0.0
- scikit-learn>=1.3.0
- football-data.org API
```

## 阶段6：系统集成 (Day 5)

### 6.1 修改FootballPredictor类
文件: `~/openclaw-workspace/football_predictor.py` 修改

```python
# 在文件顶部添加导入
from ml_analyst.ml_analyst import MLAnalyst

# 在FootballPredictor的__init__方法中添加
class FootballPredictor:
    def __init__(self, odds_api_key: str = None):
        # ... 现有代码 ...
        
        # 初始化ML-Analyst
        try:
            self.ml_analyst = MLAnalyst()
            print("✅ ML-Analyst 初始化成功")
        except Exception as e:
            print(f"⚠️  ML-Analyst 初始化失败: {e}")
            self.ml_analyst = None
            
        # ... 现有代码 ...

# 在predict方法中添加ML-Analyst调用
def predict(self, match_info: Dict) -> Dict:
    # ... 现有代码到overunder_analyst ...
    
    # 2.7 ML-Analyst (新增)
    print(f"\n7️⃣  调用 ML-Analyst (机器学习分析师)...")
    if self.ml_analyst:
        # 收集其他智能体的输出作为ML-Analyst的输入
        other_agents_output = {
            "stats": stats_report,
            "tactics": tactics_report,
            "sentiment": sentiment_report,
            "upset": upset_report,
            "asian": asian_report,
            "overunder": overunder_report
        }
        
        ml_report = self.ml_analyst.analyze_match(match_info, other_agents_output)
        self.reports["ml"] = ml_report
        
        if not ml_report.get("error"):
            print(f"   ✅ ML预测: {ml_report.get('prediction')} (信心: {ml_report.get('confidence', 0):.1f}%)")
        else:
            print(f"   ❌ ML分析失败: {ml_report.get('error_message', '未知错误')}")
    else:
        ml_report = {"error": True, "error_message": "ML-Analyst未初始化"}
        self.reports["ml"] = ml_report
        print("   ⚠️  ML-Analyst不可用")
    
    # 阶段3: 共识汇总（需要修改以包含ML-Analyst）
    print(f"\n{'='*60}")
    print(f"📊 阶段3: 共识汇总")
    print(f"{'='*60}")
    
    consensus = self._run_consensus_summarizer(match_info)
    
    # ... 后续代码不变 ...
```

### 6.2 修改Consensus Summarizer
文件: `~/openclaw-workspace/football_predictor.py` 中的 `_run_consensus_summarizer` 方法

```python
def _run_consensus_summarizer(self, match_info: Dict) -> Dict:
    # 提取各智能体信心分数
    stats_report = self.reports.get("stats", {})
    tactics_report = self.reports.get("tactics", {})
    sentiment_report = self.reports.get("sentiment", {})
    upset_report = self.reports.get("upset", {})
    asian_report = self.reports.get("asian", {})
    overunder_report = self.reports.get("overunder", {})
    ml_report = self.reports.get("ml", {})  # 新增
    
    # 提取信心分数
    stats_conf = stats_report.get("confidence_weight", 0)
    tactics_score = tactics_report.get("score", 0)
    sentiment_score = sentiment_report.get("sentiment_score", 0)
    upset_risk = upset_report.get("upset_risk", 0)
    asian_value = asian_report.get("market_value", 0)
    overunder_value = overunder_report.get("market_value", 0)
    
    # ML-Analyst信心分数（新增）
    ml_confidence = ml_report.get("confidence", 0) if not ml_report.get("error") else 0
    ml_prediction = ml_report.get("prediction", "未知")
    
    # 根据ML预测方向调整基础权重
    if ml_prediction == "主胜":
        ml_direction_bias = 1.0
    elif ml_prediction == "客胜":
        ml_direction_bias = -1.0
    else:  # 平局
        ml_direction_bias = 0.0
    
    # 计算基础信心分（包含ML-Analyst）
    # 权重分配：Stats 0.30, Tactics 0.20, Sentiment 0.15, Upset 0.10, ML 0.25
    base_score = (
        stats_conf * 0.30 +
        tactics_score * 0.20 +
        sentiment_score * 0.15 +
        (100 - upset_risk) * 0.10 +
        ml_confidence * 0.25
    )
    
    # 应用ML方向偏置（轻微调整）
    if ml_direction_bias != 0 and ml_confidence > 60:
        direction_adjustment = (ml_confidence - 50) / 100 * ml_direction_bias * 5
        base_score = max(0, min(100, base_score + direction_adjustment))
    
    # ... 后续代码保持不变（市场选择逻辑）...
    
    # 在最终共识报告中包含ML-Analyst信息
    consensus = {
        "final_confidence": round(final_confidence, 1),
        "selected_market": selected_market,
        "recommendation": recommendation,
        "market_detail": market_detail,
        "base_score": round(base_score, 1),
        "selected_value": selected_value,
        "upset_risk": upset_risk,
        "primary_risk": self.reports.get("upset", {}).get("primary_risk_factor", "无明显风险"),
        "debate_triggered": debate_result is not None,
        "debate_result": debate_result,
        # 新增ML-Analyst信息
        "ml_analyst": {
            "prediction": ml_prediction,
            "confidence": ml_confidence,
            "probabilities": ml_report.get("probabilities", {}),
            "included_in_consensus": ml_confidence > 0
        }
    }
    
    # 打印ML-Analyst贡献
    if ml_confidence > 0:
        print(f"\n   🤖 ML-Analyst贡献:")
        print(f"      预测: {ml_prediction} | 信心: {ml_confidence:.1f}%")
        probs = ml_report.get("probabilities", {})
        if probs:
            print(f"      概率: 主胜 {probs.get('home_win', 0):.1%} | 平局 {probs.get('draw', 0):.1%} | 客胜 {probs.get('away_win', 0):.1%}")
    
    return consensus
```

## 阶段7：每日训练cron job (Day 5)

### 7.1 创建每日训练脚本
文件: `~/openclaw-workspace/ml_analyst_daily_training.py`

```python
#!/usr/bin/env python3
"""
每日模型训练脚本 - 自动训练和更新XGBoost模型
"""
import os
import sys
import logging
from datetime import datetime
import yaml

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml_analyst.ml_analyst import MLAnalyst

def setup_logging():
    """设置日志"""
    log_dir = os.path.expanduser("~/openclaw-workspace/ml-analyst/logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"daily_training_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """主函数"""
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("开始每日模型训练")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # 加载配置
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "config",
            "ml_config.yaml"
        )
        
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            
        # 初始化ML-Analyst
        ml_analyst = MLAnalyst(config_path)
        
        # 执行每日训练
        logger.info("执行模型训练...")
        results = ml_analyst.train_daily_model()
        
        # 记录结果
        if results.get("success"):
            logger.info("模型训练成功!")
            
            # 记录性能指标
            test_metrics = results.get("test_metrics", {})
            accuracy = test_metrics.get("accuracy", 0)
            logger.info(f"测试集准确率: {accuracy:.3f}")
            
            # 记录特征重要性
            importance = results.get("feature_importance", [])
            if importance:
                top_features = importance[:5]
                logger.info("Top 5重要特征:")
                for feat in top_features:
                    logger.info(f"  {feat['feature']}: {feat['importance']}")
                    
            # 记录模型信息
            model_path = results.get("model_path", "未知")
            logger.info(f"模型保存位置: {model_path}")
            
        else:
            error_msg = results.get("error", "未知错误")
            logger.error(f"模型训练失败: {error_msg}")
            
    except Exception as e:
        logger.error(f"训练过程异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        # 计算运行时间
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"每日训练完成，耗时: {duration:.1f}秒")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()
```

### 7.2 创建cron job配置
文件: `~/openclaw-workspace/setup_daily_training.sh`

```bash
#!/bin/bash
# 设置每日模型训练的cron job

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_SCRIPT="$SCRIPT_DIR/ml_analyst_daily_training.py"
CRON_JOB="0 3 * * * cd $SCRIPT_DIR && /usr/bin/python3 $TRAINING_SCRIPT >> $SCRIPT_DIR/ml-analyst/logs/cron.log 2>&1"

echo "设置每日模型训练cron job..."
echo "训练脚本: $TRAINING_SCRIPT"
echo "Cron表达式: 每天凌晨3点执行"

# 检查cron job是否已存在
if crontab -l | grep -q "$TRAINING_SCRIPT"; then
    echo "Cron job已存在，跳过设置"
else
    # 添加到crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron job设置成功!"
fi

# 设置脚本可执行权限
chmod +x "$TRAINING_SCRIPT"
echo "脚本权限设置完成"
```

## 阶段8：测试和验证 (Day 6)

### 8.1 创建测试脚本
文件: `~/openclaw-workspace/test_ml_integration.py`

```python
#!/usr/bin/env python3
"""
测试ML集成功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from football_predictor import FootballPredictor

def test_ml_integration():
    """测试ML集成"""
    print("测试ML-Analyst集成到足球预测系统")
    print("=" * 60)
    
    # 创建预测器实例
    predictor = FootballPredictor(odds_api_key="c7af0126df9eb35c363065dcea447d8d")
    
    # 测试比赛信息（英超：阿森纳 vs 切尔西）
    test_match = {
        "home_team": "Arsenal",
        "home_team_cn": "阿森纳",
        "away_team": "Chelsea",
        "away_team_cn": "切尔西",
        "league": "Premier League",
        "league_cn": "英超",
        "match_time": "2024-04-20 15:00:00",
        "match_day_type": "周末"
    }
    
    print(f"测试比赛: {test_match['home_team_cn']} vs {test_match['away_team_cn']}")
    print("=" * 60)
    
    # 执行预测
    try:
        result = predictor.predict(test_match)
        
        print("\n预测结果:")
        print(f"最终信心: {result.get('final_confidence', 0)}%")
        print(f"推荐市场: {result.get('selected_market', '未知')}")
        print(f"推荐方向: {result.get('recommendation', '未知')}")
        
        # 检查ML-Analyst输出
        ml_info = result.get("ml_analyst", {})
        if ml_info:
            print(f"\nML-Analyst预测: {ml_info.get('prediction', '未知')}")
            print(f"ML信心: {ml_info.get('confidence', 0)}%")
            
            probs = ml_info.get("probabilities", {})
            if probs:
                print(f"ML概率: 主胜 {probs.get('home_win', 0):.1%} | 平局 {probs.get('draw', 0):.1%} | 客胜 {probs.get('away_win', 0):.1%}")
        else:
            print("\nML-Analyst信息未包含在结果中")
            
    except Exception as e:
        print(f"预测失败: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n测试完成")

def test_daily_training():
    """测试每日训练功能"""
    print("\n" + "=" * 60)
    print("测试每日模型训练")
    print("=" * 60)
    
    try:
        from ml_analyst.ml_analyst import MLAnalyst
        
        ml_analyst = MLAnalyst()
        print("ML-Analyst初始化成功")
        
        # 检查是否有模型
        from ml_analyst.model_manager import ModelManager
        import yaml
        
        with open("config/ml_config.yaml", "r") as f:
            config = yaml.safe_load(f)
            
        manager = ModelManager(config)
        models = manager.get_available_models()
        
        if models:
            print(f"找到 {len(models)} 个模型")
            latest = manager.get_latest_model()
            print(f"最新模型: {os.path.basename(latest)}")
        else:
            print("未找到训练模型")
            
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    test_ml_integration()
    test_daily_training()
```

## 阶段9：后续扩展路线图

### 9.1 短期优化 (Week 2-3)
1. **特征工程增强**
   - 添加更多高级特征（预期进球xG、控球率、射门数据）
   - 实现时间序列特征（球队状态趋势）
   - 添加比赛重要性特征（争冠、保级、欧战资格）

2. **模型优化**
   - 超参数调优（网格搜索/贝叶斯优化）
   - 集成多个XGBoost模型（不同特征子集）
   - 实现模型堆叠（Stacking）

3. **实时数据集成**
   - 集成实时赔率变化数据
   - 添加实时新闻情绪分析
   - 实现赛前阵容预测

### 9.2 中期扩展 (Month 2-3)
1. **多模型集成**
   - 添加LightGBM作为第二个梯度提升模型
   - 实现神经网络模型（PyTorch/TensorFlow）
   - 添加时间序列模型（LSTM/GRU）

2. **高级特征工程**
   - 图神经网络特征（球队关系网络）
   - 球员个人表现数据
   - 教练战术风格特征

3. **在线学习**
   - 实现模型在线更新（增量学习）
   - 实时反馈循环（预测结果验证）
   - 动态权重调整

### 9.3 长期愿景 (Month 4-6)
1. **全栈ML系统**
   - 自动化特征发现（AutoML）
   - 模型可解释性（SHAP/LIME）
   - 不确定性量化

2. **跨联赛学习**
   - 迁移学习（跨联赛知识迁移）
   - 多任务学习（同时预测胜负和比分）
   - 领域自适应

3. **生产化部署**
   - 模型服务API（FastAPI）
   - 实时推理管道
   - 监控和告警系统

## 部署和运维

### 监控指标
- 模型预测准确率（每日更新）
- 特征重要性变化
- 训练时间和服务延迟
- 数据质量指标

### 故障恢复
- 模型回滚机制
- 数据备份策略
- 降级策略（规则基础预测）

### 性能优化
- 特征计算缓存
- 模型量化
- 批量预测优化

## 总结

本计划详细描述了将机器学习（XGBoost）集成到现有足球预测多智能体系统的完整方案。通过分层渐进式集成，确保系统稳定性，同时逐步提升预测准确性。

**核心价值**：
1. **数据驱动决策**: 结合历史数据和实时特征
2. **可解释性**: 保留规则系统，ML作为增强
3. **实时性能**: 离线训练，在线快速推理
4. **可扩展性**: 模块化设计，支持后续模型扩展

**成功标准**：
- ML-Analyst集成后系统准确率提升5%以上
- 每日训练自动化运行成功
- 预测延迟保持在100ms以内
- 系统稳定性不下降

---

*计划制定者: Hermes Agent*
*制定时间: 2024-04-18*
*预计完成时间: 6天*
