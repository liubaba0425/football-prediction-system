#!/usr/bin/env python3
"""
模型训练管道 - 训练和评估XGBoost模型
"""
import os
import sys
import yaml
import pandas as pd
import numpy as np
import logging
import json
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import xgboost as xgb
import joblib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入本地模块
from model_trainer import XGBoostTrainer as ModelTrainer
from model_manager import ModelManager

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
    """主模型训练函数"""
    logger.info("=" * 60)
    logger.info("开始模型训练管道 (Phase 4)")
    logger.info("=" * 60)
    
    try:
        # 加载配置
        config = load_config()
        ml_config = config.get("ml_system", {})
        paths = ml_config.get("paths", {})
        xgboost_config = ml_config.get("xgboost", {})
        training_config = ml_config.get("training", {})
        
        model_dir = os.path.expanduser(paths.get("model_dir", "ml_analyst/models"))
        features_dir = os.path.expanduser(paths.get("features_dir", "ml_analyst/features"))
        
        os.makedirs(model_dir, exist_ok=True)
        
        # 1. 加载特征数据
        logger.info("步骤1: 加载特征数据...")
        selected_features_path = os.path.join(features_dir, "selected_features.parquet")
        
        if not os.path.exists(selected_features_path):
            logger.error(f"特征数据文件未找到: {selected_features_path}")
            logger.error("请先运行 build_features.py")
            return
        
        data = pd.read_parquet(selected_features_path)
        logger.info(f"加载数据形状: {data.shape}")
        
        # 检查标签列
        if "label" not in data.columns:
            logger.error("标签列 'label' 未找到")
            return
        
        # 2. 准备训练数据
        logger.info("步骤2: 准备训练数据...")
        X = data.drop(columns=["label", "label_binary"], errors='ignore')
        y = data["label"]
        
        # 检查特征数量
        if X.shape[1] == 0:
            logger.error("没有可用的特征")
            return
        
        logger.info(f"特征维度: {X.shape[1]}, 样本数: {X.shape[0]}")
        logger.info(f"标签分布: {y.value_counts().to_dict()}")
        
        # 3. 分割数据集
        logger.info("步骤3: 分割数据集...")
        test_size = training_config.get("test_size", 0.2)
        random_state = training_config.get("random_state", 42)
        validation_size = training_config.get("validation_size", 0.1)
        
        # 分割训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # 进一步分割训练集和验证集
        val_ratio = validation_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=val_ratio, random_state=random_state, stratify=y_train
        )
        
        logger.info(f"训练集: {X_train.shape[0]} 样本")
        logger.info(f"验证集: {X_val.shape[0]} 样本")
        logger.info(f"测试集: {X_test.shape[0]} 样本")
        
        # 4. 训练XGBoost模型
        logger.info("步骤4: 训练XGBoost模型...")
        
        # 使用XGBoostTrainer
        model_trainer = ModelTrainer(ml_config)
        
        # 训练模型（XGBoostTrainer内部会分割验证集）
        training_results = model_trainer.train(
            X_train, y_train, 
            model_name="xgboost_football"
        )
        
        # 获取训练好的模型
        model = model_trainer.model
        
        if model is None:
            logger.error("模型训练失败")
            return
        
        logger.info(f"训练完成 - 测试集准确率: {training_results.get('test_metrics', {}).get('accuracy', 'N/A')}")
        
        # 注意：XGBoostTrainer已经包含了验证集和测试集的评估结果
        # 但我们仍然使用之前分割的独立测试集进行评估
        
        # 5. 评估模型
        logger.info("步骤5: 评估模型...")
        
        # 在测试集上评估
        y_pred = model_trainer.predict(X_test, return_proba=False)
        y_pred_proba = model_trainer.predict(X_test, return_proba=True)
        
        test_accuracy = accuracy_score(y_test, y_pred)
        logger.info(f"测试集准确率: {test_accuracy:.4f}")
        
        # 分类报告
        class_report = classification_report(y_test, y_pred, output_dict=True)
        logger.info("分类报告生成完成")
        
        # 混淆矩阵
        conf_matrix = confusion_matrix(y_test, y_pred)
        
        # 6. 保存模型和结果
        logger.info("步骤6: 保存模型和结果...")
        
        # 使用ModelManager保存模型
        model_manager = ModelManager(ml_config)
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"xgboost_football_v{version}"
        
        model_path = model_manager.save_model(
            model=model,
            model_name=model_name,
            feature_names=X.columns.tolist(),
            training_data_shape=X_train.shape,
            performance_metrics={
                "test_accuracy": float(test_accuracy),
                "best_iteration": int(training_results.get("best_iteration", 0)),
                "val_accuracy": float(training_results.get("val_accuracy", 0.0))
            },
            config=ml_config
        )
        
        logger.info(f"模型保存至: {model_path}")
        
        # 保存评估报告
        report = {
            "model_name": model_name,
            "version": version,
            "training_date": datetime.now().isoformat(),
            "data_summary": {
                "total_samples": len(data),
                "feature_count": X.shape[1],
                "train_samples": len(X_train),
                "val_samples": len(X_val),
                "test_samples": len(X_test),
                "class_distribution": y.value_counts().to_dict()
            },
            "performance_metrics": {
                "test_accuracy": float(test_accuracy),
                "best_iteration": int(training_results.get("best_iteration", 0)),
                "val_accuracy": float(training_results.get("val_accuracy", 0.0))
            },
            "classification_report": class_report,
            "confusion_matrix": conf_matrix.tolist(),
            "feature_importance": training_results.get("feature_importance", {}),
            "xgboost_config": xgboost_config
        }
        
        report_path = os.path.join(model_dir, f"{model_name}_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"评估报告保存至: {report_path}")
        
        # 7. 特征重要性分析
        logger.info("步骤7: 特征重要性分析...")
        if hasattr(model, "feature_importances_"):
            importance_dict = dict(zip(X.columns, model.feature_importances_))
            importance_df = pd.DataFrame(
                sorted(importance_dict.items(), key=lambda x: x[1], reverse=True),
                columns=["feature", "importance"]
            )
            importance_path = os.path.join(model_dir, f"{model_name}_feature_importance.csv")
            importance_df.to_csv(importance_path, index=False, encoding='utf-8')
            logger.info(f"特征重要性保存至: {importance_path}")
            
            # 打印前10个重要特征
            logger.info("前10个重要特征:")
            for i, (feature, imp) in enumerate(importance_df.head(10).values, 1):
                logger.info(f"  {i}. {feature}: {imp:.4f}")
        
        # 8. 标记为最新模型
        latest_model_path = os.path.join(model_dir, "latest_model.pkl")
        joblib.dump(model, latest_model_path)
        logger.info(f"标记最新模型: {latest_model_path}")
        
        logger.info("=" * 60)
        logger.info("模型训练管道完成！")
        logger.info("=" * 60)
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("模型训练摘要")
        print("=" * 60)
        print(f"模型名称: {model_name}")
        print(f"训练样本: {X_train.shape[0]}")
        print(f"测试样本: {X_test.shape[0]}")
        print(f"特征数量: {X.shape[1]}")
        print(f"测试准确率: {test_accuracy:.4f}")
        print(f"最佳迭代次数: {training_results.get('best_iteration', 'N/A')}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"模型训练管道失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())