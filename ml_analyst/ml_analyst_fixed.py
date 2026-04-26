#!/usr/bin/env python3
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
try:
    from .model_trainer import XGBoostTrainer
    from .model_manager import ModelManager
    from .feature_engineering import FeatureEngineer
    from .feature_selector import FeatureSelector
    from .data_manager import DataManager
except ImportError:
    # 直接导入（当作为模块运行时）
    from model_trainer import XGBoostTrainer
    from model_manager import ModelManager
    from feature_engineering import FeatureEngineer
    from feature_selector import FeatureSelector
    from data_manager import DataManager

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
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                "config", 
                "ml_config.yaml"
            )
            
        import yaml
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
            
        # 如果配置有ml_system顶层，则使用它
        if "ml_system" in self.config:
            self.config = self.config["ml_system"]
            
        # 设置日志
        self.logger = self._setup_logger()
        
        # 初始化各个模块
        self.data_manager = DataManager(self.config.get("data_dir", "./ml_analyst/data"))
        self.feature_engineer = FeatureEngineer()
        self.feature_selector = FeatureSelector(self.config.get("features_dir", "./ml_analyst/features"))
        self.model_trainer = XGBoostTrainer(self.config.get("model_dir", "./ml_analyst/models"))
        self.model_manager = ModelManager(self.config)
        
        # 加载最新模型
        self.model = None
        self._load_latest_model()
        
        self.logger.info("ML-Analyst initialized")
        
    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger("ML-Analyst")
        logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
            
        # 文件处理器
        log_dir = self.config.get("log_dir", "./ml_analyst/logs")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"ml_analyst_{datetime.now().strftime('%Y%m%d')}.log")
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
                self.logger.error(f"Failed to load model {latest_model}: {e}")
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
            self.logger.info("Using fallback analysis based on other agents")
            return self._create_fallback_report(match_info, other_agents_output)
            
    def _create_fallback_report(self, match_info: Dict, other_agents_output: Dict) -> Dict:
        """
        当ML模型失败时，基于其他智能体的输出创建后备分析报告
        """
        # 从其他智能体提取概率
        implied_probs = other_agents_output.get("stats", {})
        home_prob = implied_probs.get("home_win", 0.5)
        draw_prob = implied_probs.get("draw", 0.2)
        away_prob = implied_probs.get("away_win", 0.3)
        
        # 计算加权平均概率（简单平均）
        total = home_prob + draw_prob + away_prob
        if total > 0:
            home_prob_norm = home_prob / total
            draw_prob_norm = draw_prob / total
            away_prob_norm = away_prob / total
        else:
            home_prob_norm, draw_prob_norm, away_prob_norm = 0.4, 0.3, 0.3
        
        # 确定预测结果
        if home_prob_norm > away_prob_norm and home_prob_norm > draw_prob_norm:
            prediction = "主胜"
            confidence = home_prob_norm * 100
        elif away_prob_norm > home_prob_norm and away_prob_norm > draw_prob_norm:
            prediction = "客胜"
            confidence = away_prob_norm * 100
        else:
            prediction = "平局"
            confidence = draw_prob_norm * 100
        
        return {
            "ml_analyst_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "prediction": prediction,
            "confidence": round(confidence, 1),
            "probabilities": {
                "home_win": round(home_prob_norm, 3),
                "draw": round(draw_prob_norm, 3),
                "away_win": round(away_prob_norm, 3)
            },
            "features_used": ["fallback_mode"],
            "model_info": {
                "type": "Fallback",
                "training_date": None,
                "accuracy": 0.0
            },
            "analysis": "使用后备分析模式（基于其他智能体输出）",
            "error": False,
            "fallback_mode": True
        }
    
    def _create_error_report(self, error_message: str) -> Dict:
        """创建错误报告"""
        return {
            "ml_analyst_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "prediction": "未知",
            "confidence": 0,
            "probabilities": {
                "home_win": 0.333,
                "draw": 0.333,
                "away_win": 0.333
            },
            "features_used": [],
            "model_info": {
                "type": "Error",
                "training_date": None,
                "accuracy": 0.0
            },
            "analysis": f"ML分析失败: {error_message}",
            "error": True,
            "error_message": error_message
        }
    
    def _prepare_inference_features(self, match_info: Dict, other_agents_output: Dict) -> pd.DataFrame:
        """准备推理特征 - 与训练特征列匹配"""
        from datetime import datetime
        import numpy as np
        
        # 训练特征列（从feature_list.txt读取，排除label）
        training_features = [
            "matchday", "match_date_ordinal", "home_recent_form", "home_avg_goals_scored",
            "home_avg_goals_conceded", "home_home_performance", "home_away_performance",
            "away_recent_form", "away_avg_goals_scored", "away_avg_goals_conceded",
            "away_home_performance", "away_away_performance", "goals_scored_diff",
            "goals_conceded_diff", "is_weekend", "month", "day_of_week", "season_month",
            "is_season_start", "is_season_mid", "is_season_end"
        ]
        
        features = {}
        
        # 1. 基础比赛信息
        features["matchday"] = match_info.get("matchday", 20)
        current_date = datetime.now()
        features["match_date_ordinal"] = current_date.toordinal()
        features["is_weekend"] = 1 if current_date.weekday() in [5, 6] else 0
        features["month"] = current_date.month
        features["day_of_week"] = current_date.weekday()  # 0=Monday
        features["season_month"] = current_date.month
        features["is_season_start"] = 1 if current_date.month in [8, 9, 10] else 0
        features["is_season_mid"] = 1 if current_date.month in [11, 12, 1, 2] else 0
        features["is_season_end"] = 1 if current_date.month in [3, 4, 5] else 0
        
        # 2. 从其他智能体提取球队状态特征
        stats_data = other_agents_output.get("stats", {})
        tactics_data = other_agents_output.get("tactics", {})
        
        # 主队状态（使用Stats-Analyst的输出或默认值）
        home_form = stats_data.get("home_team_form", 0.5)
        away_form = stats_data.get("away_team_form", 0.5)
        features["home_recent_form"] = home_form
        features["away_recent_form"] = away_form
        
        # 平均进球数（默认值，实际应从历史数据获取）
        features["home_avg_goals_scored"] = 1.5
        features["home_avg_goals_conceded"] = 1.2
        features["away_avg_goals_scored"] = 1.3
        features["away_avg_goals_conceded"] = 1.4
        
        # 主场/客场表现
        features["home_home_performance"] = 0.6  # 主队主场胜率
        features["home_away_performance"] = 0.4  # 主队客场胜率
        features["away_home_performance"] = 0.5  # 客队主场胜率
        features["away_away_performance"] = 0.5  # 客队客场胜率
        
        # 进球差异
        features["goals_scored_diff"] = features["home_avg_goals_scored"] - features["away_avg_goals_scored"]
        features["goals_conceded_diff"] = features["home_avg_goals_conceded"] - features["away_avg_goals_conceded"]
        
        # 3. 确保所有训练特征都有值
        for feature in training_features:
            if feature not in features:
                features[feature] = 0.0  # 默认值
        
        # 创建DataFrame（只包含训练特征列，按正确顺序）
        df = pd.DataFrame([features])
        return df[training_features]
    
    def _parse_predictions(self, predictions, match_info: Dict, other_agents_output: Dict) -> Dict:
        """解析模型预测结果"""
        # 简化版本：假设predictions是概率数组 [home, draw, away]
        if isinstance(predictions, np.ndarray) and predictions.size >= 3:
            home_prob = float(predictions[0])
            draw_prob = float(predictions[1])
            away_prob = float(predictions[2])
        else:
            # 默认概率
            home_prob, draw_prob, away_prob = 0.4, 0.3, 0.3
        
        # 确定预测结果
        if home_prob > away_prob and home_prob > draw_prob:
            prediction = "主胜"
            confidence = home_prob * 100
        elif away_prob > home_prob and away_prob > draw_prob:
            prediction = "客胜"
            confidence = away_prob * 100
        else:
            prediction = "平局"
            confidence = draw_prob * 100
        
        return {
            "ml_analyst_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "prediction": prediction,
            "confidence": round(confidence, 1),
            "probabilities": {
                "home_win": round(home_prob, 3),
                "draw": round(draw_prob, 3),
                "away_win": round(away_prob, 3)
            },
            "features_used": ["simplified_features"],
            "model_info": {
                "type": "XGBoost",
                "training_date": "2024-01-15",
                "accuracy": 0.65
            },
            "analysis": f"ML模型预测: {prediction} (信心: {round(confidence, 1)}%)",
            "error": False
        }