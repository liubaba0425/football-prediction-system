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
        
        # 2. 提取球队状态特征
        df_processed = self._extract_team_form_features(df_processed)
        
        # 3. 提取基础特征
        df_processed = self._extract_basic_features(df_processed)
        
        # 4. 提取H2H特征
        df_processed = self._extract_h2h_features(df_processed)
        
        # 5. 提取赔率相关特征（合成赔率，基于球队实力）
        df_processed = self._extract_odds_features(df_processed)
        
        # 6. 创建标签
        df_processed = self._create_labels(df_processed)
        
        # 7. 清理缺失值
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
            default=None
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
            
            # 新增特征的相对差值
            df["win_streak_diff"] = df["home_win_streak"] - df["away_win_streak"]
            df["unbeaten_streak_diff"] = df["home_unbeaten_streak"] - df["away_unbeaten_streak"]
            df["home_away_ratio_diff"] = df["home_home_away_ratio"] - df["away_home_away_ratio"]
            df["defensive_stability_diff"] = df["home_defensive_stability"] - df["away_defensive_stability"]
            df["goal_efficiency_diff"] = df["home_goal_efficiency"] - df["away_goal_efficiency"]
            df["days_since_last_match_diff"] = df["away_days_since_last_match"] - df["home_days_since_last_match"]  # 客队休息时间减去主队休息时间
            
        return df
        
    def _calculate_team_form(self, df: pd.DataFrame, team_id: int) -> pd.DataFrame:
        """计算单个球队的状态特征（增强版，包含连胜等新特征）"""
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
            
            # ==================== 新特征 ====================
            # 1. 连胜计数 (从窗口内最近比赛开始计算)
            win_streak = 0
            unbeaten_streak = 0
            # 按时间倒序检查比赛结果
            reversed_matches = window_matches.iloc[::-1]  # 从最近到最远
            
            for _, match in reversed_matches.iterrows():
                is_home_in_match = match["home_team_id"] == team_id
                result = match["result"]
                
                # 判断该比赛对该球队是否是胜利
                if (is_home_in_match and result == "H") or (not is_home_in_match and result == "A"):
                    win_streak += 1
                    unbeaten_streak += 1
                elif result == "D":
                    # 平局，连胜终止但不败继续
                    win_streak = 0
                    unbeaten_streak += 1
                else:
                    # 输球，两者都终止
                    break
            
            # 2. 主客场优势指数
            home_away_ratio = home_performance / (away_performance + 0.01) if away_performance > 0 else home_performance * 100
            
            # 3. 防守稳定性（失球数的标准差）
            # 收集窗口内每场比赛的失球数
            goals_conceded_list = []
            for _, match in window_matches.iterrows():
                if match["home_team_id"] == team_id:
                    goals_conceded_list.append(match["fulltime_away"])
                else:
                    goals_conceded_list.append(match["fulltime_home"])
            
            defensive_stability = np.std(goals_conceded_list) if len(goals_conceded_list) > 1 else 0
            
            # 4. 比赛间隔天数（当前比赛与窗口内上一场比赛的间隔）
            if i > 0:
                prev_match_date = team_matches.iloc[i-1]["match_date"]
                current_match_date = current_match["match_date"]
                days_since_last_match = (current_match_date - prev_match_date).days
            else:
                days_since_last_match = 7  # 默认值
            
            # 5. 进球效率（平均进球数除以平均失球数，加1避免除零）
            goal_efficiency = avg_goals_scored / (avg_goals_conceded + 0.5)
            # ==================== 新特征结束 ====================
            
            features = {
                "match_id": current_match["match_id"],
                "recent_form": recent_form,
                "avg_goals_scored": avg_goals_scored,
                "avg_goals_conceded": avg_goals_conceded,
                "home_performance": home_performance,
                "away_performance": away_performance,
                "total_matches_last_window": total_matches,
                # 新特征
                "win_streak": win_streak,
                "unbeaten_streak": unbeaten_streak,
                "home_away_ratio": home_away_ratio,
                "defensive_stability": defensive_stability,
                "days_since_last_match": days_since_last_match,
                "goal_efficiency": goal_efficiency,
            }
            
            features_list.append(features)
            
        return pd.DataFrame(features_list)
        
    def _extract_h2h_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取历史交锋特征"""
        # 实现H2H特征提取
        # 由于时间关系，此处简化为基本特征
        df["h2h_exists"] = 1  # 简化，实际需要计算两队历史交锋次数
        return df

    def _extract_odds_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        提取赔率相关特征（合成赔率 — 基于球队历史实力推算）
        
        训练数据没有真实赔率，用球队表现推算「合成赔率」作为代理特征。
        推理时这些特征会被 The Odds API 的真实赔率替换。
        
        核心思路：
        1. 基于球队近期状态推算「实力分」
        2. 实力分差 → 隐含胜率 → 合成赔率
        3. 赔率差 (odds_gap) 反映市场对实力差距的判断
        """
        df = df.copy()
        
        # 确保有必要的列
        needed = ["home_recent_form", "home_avg_goals_scored", "home_avg_goals_conceded",
                   "away_recent_form", "away_avg_goals_scored", "away_avg_goals_conceded"]
        for col in needed:
            if col not in df.columns:
                df[col] = 0.5  # 默认值
        
        # 计算球队实力分 (0-100 scale)
        # 基于: 近期状态(40%) + 进球能力(30%) + 防守能力(30%)
        df["home_strength"] = (
            df["home_recent_form"].fillna(0.5) * 40 +
            (df["home_avg_goals_scored"].fillna(1.0) / 3.0) * 30 +
            (1.0 - df["home_avg_goals_conceded"].fillna(1.0) / 3.0) * 30
        ).clip(10, 90)
        
        df["away_strength"] = (
            df["away_recent_form"].fillna(0.5) * 40 +
            (df["away_avg_goals_scored"].fillna(1.0) / 3.0) * 30 +
            (1.0 - df["away_avg_goals_conceded"].fillna(1.0) / 3.0) * 30
        ).clip(10, 90)
        
        # 实力差 → 隐含胜率（使用逻辑函数转换）
        strength_diff = df["home_strength"] - df["away_strength"]
        # Elo-style: 400 points ≈ 90% win probability
        df["home_win_prob_synthetic"] = 1.0 / (1.0 + 10 ** (-strength_diff / 400.0))
        
        # 平局概率（实力接近时高，差距大时低）
        df["draw_prob_synthetic"] = 0.30 * np.exp(-abs(strength_diff) / 200.0)
        
        # 客胜概率 = 剩余部分
        df["away_win_prob_synthetic"] = 1.0 - df["home_win_prob_synthetic"] - df["draw_prob_synthetic"]
        df["away_win_prob_synthetic"] = df["away_win_prob_synthetic"].clip(0.05, 0.95)
        
        # 合成赔率（隐含概率 → 赔率，含10% margin）
        margin = 0.10
        df["home_odds_synthetic"] = (1.0 / df["home_win_prob_synthetic"].clip(0.05)) * (1.0 - margin)
        df["draw_odds_synthetic"] = (1.0 / df["draw_prob_synthetic"].clip(0.05)) * (1.0 - margin)
        df["away_odds_synthetic"] = (1.0 / df["away_win_prob_synthetic"].clip(0.05)) * (1.0 - margin)
        
        # 实力分差
        df["strength_diff"] = df["home_strength"] - df["away_strength"]
        
        # 胜率差（home - away），对称特征，避免偏向某一方
        df["win_prob_diff"] = df["home_win_prob_synthetic"] - df["away_win_prob_synthetic"]
        
        # 赔率差（反映实力差距的市场认知）
        df["odds_gap_synthetic"] = abs(df["home_odds_synthetic"] - df["away_odds_synthetic"])
        
        # 隐含概率（只保留差值，避免不对称特征）
        total_prob = df["home_win_prob_synthetic"] + df["draw_prob_synthetic"] + df["away_win_prob_synthetic"]
        df["home_implied_prob"] = df["home_win_prob_synthetic"] / total_prob
        df["draw_implied_prob"] = df["draw_prob_synthetic"] / total_prob
        df["away_implied_prob"] = df["away_win_prob_synthetic"] / total_prob
        
        # 对称差量特征
        df["implied_prob_diff"] = df["home_implied_prob"] - df["away_implied_prob"]
        
        self.logger.info(f"Added 10 synthetic odds features (strength-based, symmetric)")
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
                
        # 删除泄露列和标识列（防止数据泄露）
        columns_to_drop = [
            "result", "fulltime_home", "fulltime_away", "halftime_home", "halftime_away",
            "match_date", "utc_date", "status", "match_id", "home_team_id", "away_team_id",
            "home_team_name", "away_team_name", "competition_id", "season_id"
        ]
        existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
        df = df.drop(columns=existing_columns_to_drop, errors="ignore")
        
        return df
        
    def prepare_inference_features(self, match_info: Dict, team_form_data: Dict) -> pd.DataFrame:
        """
        为实时预测准备特征 (v3 — 真实赔率特征)
        
        生成与训练集完全一致的18个赔率特征
        """
        # 提取赔率数据
        home_odds = match_info.get("home_odds", 2.0)
        draw_odds = match_info.get("draw_odds", 3.0)
        away_odds = match_info.get("away_odds", 2.0)
        
        # 基础赔率特征 (7个)
        home_implied = 1.0 / max(home_odds, 1.01)
        draw_implied = 1.0 / max(draw_odds, 1.01)
        away_implied = 1.0 / max(away_odds, 1.01)
        total_implied = home_implied + draw_implied + away_implied
        
        features = {
            "home_odds": home_odds,
            "draw_odds": draw_odds,
            "away_odds": away_odds,
            "home_implied_prob": home_implied / total_implied,
            "draw_implied_prob": draw_implied / total_implied,
            "away_implied_prob": away_implied / total_implied,
            "odds_gap": abs(home_odds - away_odds),
            "implied_prob_diff": (home_implied - away_implied) / total_implied,
        }
        
        # 亚盘特征 (从Pinnacle spreads提取)
        spreads = match_info.get("spreads", {}) or {}
        asian_handicap = 0.0
        for outcome in spreads.get("outcomes", []):
            if outcome.get("name") == match_info.get("home_team"):
                asian_handicap = outcome.get("point", 0.0)
                break
        features["asian_handicap"] = asian_handicap
        features["handicap_magnitude"] = abs(asian_handicap)
        
        # 大小球特征 (从Pinnacle totals提取)
        totals = match_info.get("totals", {}) or {}
        over_odds_val = 1.9
        under_odds_val = 2.0
        for outcome in totals.get("outcomes", []):
            if outcome.get("name") == "Over":
                over_odds_val = outcome.get("price", 1.9)
            elif outcome.get("name") == "Under":
                under_odds_val = outcome.get("price", 2.0)
        features["over_odds"] = over_odds_val
        features["under_odds"] = under_odds_val
        over_implied = 1.0 / max(over_odds_val, 1.01)
        under_implied = 1.0 / max(under_odds_val, 1.01)
        features["over_under_bias"] = over_implied - under_implied
        
        # 派生特征 (6个)
        features["odds_ratio_home"] = away_odds / max(home_odds, 1.01)
        features["odds_ratio_away"] = home_odds / max(away_odds, 1.01)
        features["home_favorite"] = 1 if home_odds < away_odds else 0
        features["clear_favorite"] = 1 if (home_odds < 1.7 or away_odds < 1.7) else 0
        features["days_since_epoch"] = 0  # 推理时无历史日期，填充0
        
        # 创建DataFrame — 只保留训练特征
        df = pd.DataFrame([features])
        df = df.fillna(0)
        return df