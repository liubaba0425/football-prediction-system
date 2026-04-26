#!/usr/bin/env python3
"""
特征工程管道 - 从历史比赛数据中构建机器学习特征
"""
import os
import sys
import yaml
import pandas as pd
import numpy as np
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入本地模块
from feature_engineering import FeatureEngineer
from feature_selector import FeatureSelector
from data_manager import DataManager

def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), '../config/ml_config.yaml')
    if not os.path.exists(config_path):
        config_path = 'config/ml_config.yaml'
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件未找到: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config

def main():
    """主特征工程函数"""
    logger.info("=" * 60)
    logger.info("开始特征工程管道 (Phase 3)")
    logger.info("=" * 60)
    
    try:
        # 加载配置
        config = load_config()
        ml_config = config.get("ml_system", {})
        paths = ml_config.get("paths", {})
        
        data_dir = os.path.expanduser(paths.get("data_dir", "ml_analyst/data"))
        features_dir = os.path.expanduser(paths.get("features_dir", "ml_analyst/features"))
        
        os.makedirs(features_dir, exist_ok=True)
        
        # 1. 加载历史比赛数据
        logger.info("步骤1: 加载历史比赛数据...")
        data_manager = DataManager(ml_config)
        
        matches_path = os.path.join(data_dir, "historical_matches.parquet")
        standings_path = os.path.join(data_dir, "historical_standings.parquet")
        
        if not os.path.exists(matches_path):
            logger.error(f"比赛数据文件未找到: {matches_path}")
            logger.error("请先运行 collect_historical_data.py")
            return
        
        matches_df = pd.read_parquet(matches_path)
        logger.info(f"加载 {len(matches_df)} 条比赛记录")
        
        if os.path.exists(standings_path):
            standings_df = pd.read_parquet(standings_path)
            logger.info(f"加载 {len(standings_df)} 条积分榜记录")
            # 可以在这里合并积分榜数据
        else:
            standings_df = pd.DataFrame()
            logger.warning("积分榜数据文件未找到，跳过积分榜特征")
        
        # 2. 特征工程
        logger.info("步骤2: 特征工程...")
        feature_config = ml_config.get("features", {})
        feature_engineer = FeatureEngineer(ml_config)
        
        features_df = feature_engineer.prepare_features(matches_df)
        logger.info(f"特征工程完成，生成 {features_df.shape[1]} 个特征")
        
        # 3. 特征选择
        logger.info("步骤3: 特征选择...")
        feature_selector = FeatureSelector(feature_config)
        
        # 分离特征和标签
        if "label" not in features_df.columns:
            logger.error("标签列 'label' 未找到")
            return
        
        # 只选择数值型特征
        numeric_features = features_df.select_dtypes(include=[np.number]).columns.tolist()
        # 移除标签列
        numeric_features = [col for col in numeric_features if col not in ["label", "label_binary"]]
        X = features_df[numeric_features]
        y = features_df["label"]
        
        logger.info(f"使用 {len(numeric_features)} 个数值特征进行特征选择")
        
        # 执行特征选择
        X_selected_df = feature_selector.select_features(X, y)
        selected_features = feature_selector.selected_features
        logger.info(f"选择了 {len(selected_features)} 个重要特征")
        
        # 创建包含选定特征的数据集
        X_selected = X[selected_features]
        
        # 4. 保存特征数据
        logger.info("步骤4: 保存特征数据...")
        
        # 保存完整特征集
        full_features_path = os.path.join(features_dir, "full_features.parquet")
        features_df.to_parquet(full_features_path, index=False)
        logger.info(f"完整特征集保存至: {full_features_path}")
        
        # 保存选定特征集
        selected_features_df = pd.concat([X_selected, y], axis=1)
        selected_features_path = os.path.join(features_dir, "selected_features.parquet")
        selected_features_df.to_parquet(selected_features_path, index=False)
        logger.info(f"选定特征集保存至: {selected_features_path}")
        
        # 保存特征列表
        features_list_path = os.path.join(features_dir, "feature_list.txt")
        with open(features_list_path, 'w', encoding='utf-8') as f:
            f.write("选定的特征列表:\n")
            for i, feature in enumerate(selected_features, 1):
                f.write(f"{i}. {feature}\n")
        
        logger.info(f"特征列表保存至: {features_list_path}")
        
        # 5. 生成特征报告
        logger.info("步骤5: 生成特征报告...")
        report = {
            "生成时间": datetime.now().isoformat(),
            "总比赛记录数": len(matches_df),
            "总特征数": features_df.shape[1],
            "选定特征数": len(selected_features),
            "标签分布": features_df["label"].value_counts().to_dict(),
            "特征形状": features_df.shape,
            "选定特征": selected_features[:20]  # 仅显示前20个
        }
        
        report_path = os.path.join(features_dir, "feature_report.yaml")
        with open(report_path, 'w', encoding='utf-8') as f:
            yaml.dump(report, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"特征报告保存至: {report_path}")
        
        logger.info("=" * 60)
        logger.info("特征工程管道完成！")
        logger.info("=" * 60)
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("特征工程摘要")
        print("=" * 60)
        print(f"总比赛记录数: {len(matches_df)}")
        print(f"生成特征数: {features_df.shape[1]}")
        print(f"选定特征数: {len(selected_features)}")
        print(f"标签分布: {features_df['label'].value_counts().to_dict()}")
        print(f"数据形状: {features_df.shape}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"特征工程管道失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())