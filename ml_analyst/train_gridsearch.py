#!/usr/bin/env python3
"""
网格搜索调优XGBoost参数 - 优化足球预测模型
"""
import os
import sys
import yaml
import pandas as pd
import numpy as np
import logging
import json
from datetime import datetime
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import xgboost as xgb
import joblib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    """主网格搜索函数"""
    logger.info("=" * 60)
    logger.info("开始XGBoost超参数网格搜索优化")
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
            return 1
        
        data = pd.read_parquet(selected_features_path)
        logger.info(f"加载数据形状: {data.shape}")
        
        # 检查标签列
        if "label" not in data.columns:
            logger.error("标签列 'label' 未找到")
            return 1
        
        # 2. 准备训练数据
        logger.info("步骤2: 准备训练数据...")
        X = data.drop(columns=["label", "label_binary"], errors='ignore')
        y = data["label"]
        
        # 检查特征数量
        if X.shape[1] == 0:
            logger.error("没有可用的特征")
            return 1
        
        logger.info(f"特征维度: {X.shape[1]}, 样本数: {X.shape[0]}")
        logger.info(f"标签分布: {y.value_counts().to_dict()}")
        
        # 3. 分割数据集
        logger.info("步骤3: 分割数据集...")
        test_size = training_config.get("test_size", 0.2)
        random_state = training_config.get("random_state", 42)
        validation_size = training_config.get("validation_size", 0.1)
        
        # 分割训练集和测试集（保持测试集独立）
        X_train_val, X_test, y_train_val, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # 进一步分割训练集和验证集
        val_ratio = validation_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_val, y_train_val, test_size=val_ratio, random_state=random_state, stratify=y_train_val
        )
        
        logger.info(f"训练集: {X_train.shape[0]} 样本")
        logger.info(f"验证集: {X_val.shape[0]} 样本")
        logger.info(f"测试集: {X_test.shape[0]} 样本")
        
        # 4. 设置参数网格
        logger.info("步骤4: 设置XGBoost参数网格...")
        
        # 基础参数
        base_params = {
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
            "seed": random_state,
            "verbosity": 0,
        }
        
        # 参数网格
        param_grid = {
            "max_depth": [3, 6, 9],
            "learning_rate": [0.01, 0.1, 0.3],
            "n_estimators": [50, 100, 200],
            "subsample": [0.8, 1.0],
            "colsample_bytree": [0.8, 1.0],
            "gamma": [0, 0.1, 0.2],
        }
        
        logger.info(f"参数网格组合数: {np.prod([len(v) for v in param_grid.values()])}")
        
        # 5. 网格搜索
        logger.info("步骤5: 开始网格搜索...")
        
        # 创建XGBoost分类器
        xgb_model = xgb.XGBClassifier(**base_params)
        
        # 设置网格搜索
        grid_search = GridSearchCV(
            estimator=xgb_model,
            param_grid=param_grid,
            scoring="accuracy",
            cv=3,
            verbose=2,
            n_jobs=-1,
            return_train_score=True,
        )
        
        # 在训练集上执行网格搜索
        logger.info("在训练集上执行网格搜索（3折交叉验证）...")
        grid_search.fit(X_train, y_train)
        
        logger.info(f"网格搜索完成！最佳参数: {grid_search.best_params_}")
        logger.info(f"最佳交叉验证准确率: {grid_search.best_score_:.4f}")
        
        # 6. 评估最佳模型
        logger.info("步骤6: 评估最佳模型...")
        best_model = grid_search.best_estimator_
        
        # 在验证集上评估
        y_val_pred = best_model.predict(X_val)
        val_accuracy = accuracy_score(y_val, y_val_pred)
        logger.info(f"验证集准确率: {val_accuracy:.4f}")
        
        # 在测试集上评估
        y_test_pred = best_model.predict(X_test)
        y_test_pred_proba = best_model.predict_proba(X_test)
        test_accuracy = accuracy_score(y_test, y_test_pred)
        logger.info(f"测试集准确率: {test_accuracy:.4f}")
        
        # 分类报告
        class_report = classification_report(y_test, y_test_pred, output_dict=True)
        
        # 混淆矩阵
        conf_matrix = confusion_matrix(y_test, y_test_pred)
        
        # 7. 特征重要性分析
        logger.info("步骤7: 特征重要性分析...")
        feature_importance = best_model.feature_importances_
        importance_dict = dict(zip(X.columns, feature_importance))
        importance_df = pd.DataFrame(
            sorted(importance_dict.items(), key=lambda x: x[1], reverse=True),
            columns=["feature", "importance"]
        )
        
        # 打印前20个重要特征
        logger.info("前20个重要特征:")
        for i, (feature, imp) in enumerate(importance_df.head(20).values, 1):
            logger.info(f"  {i:2d}. {feature:30s}: {imp:.4f}")
        
        # 8. 保存结果
        logger.info("步骤8: 保存网格搜索结果...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"xgboost_gridsearch_v{timestamp}"
        
        # 保存最佳模型
        model_path = os.path.join(model_dir, f"{model_name}.joblib")
        joblib.dump({
            "model": best_model,
            "best_params": grid_search.best_params_,
            "best_score": grid_search.best_score_,
            "feature_names": X.columns.tolist(),
            "grid_search_results": {
                "cv_results": grid_search.cv_results_,
                "best_index": grid_search.best_index_,
            },
            "training_date": timestamp,
            "config": ml_config,
        }, model_path)
        logger.info(f"最佳模型保存至: {model_path}")
        
        # 保存评估报告
        report = {
            "model_name": model_name,
            "version": timestamp,
            "training_date": datetime.now().isoformat(),
            "data_summary": {
                "total_samples": len(data),
                "feature_count": X.shape[1],
                "train_samples": len(X_train),
                "val_samples": len(X_val),
                "test_samples": len(X_test),
                "class_distribution": y.value_counts().to_dict()
            },
            "best_parameters": grid_search.best_params_,
            "performance_metrics": {
                "cv_best_score": float(grid_search.best_score_),
                "validation_accuracy": float(val_accuracy),
                "test_accuracy": float(test_accuracy),
            },
            "grid_search_summary": {
                "total_combinations": int(np.prod([len(v) for v in param_grid.values()])),
                "cv_folds": 3,
                "scoring": "accuracy",
            },
            "classification_report": class_report,
            "confusion_matrix": conf_matrix.tolist(),
            "feature_importance": importance_df.to_dict("records"),
        }
        
        report_path = os.path.join(model_dir, f"{model_name}_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"评估报告保存至: {report_path}")
        
        # 保存特征重要性为CSV
        importance_path = os.path.join(model_dir, f"{model_name}_feature_importance.csv")
        importance_df.to_csv(importance_path, index=False, encoding='utf-8')
        logger.info(f"特征重要性保存至: {importance_path}")
        
        # 保存网格搜索结果为CSV（简化版）
        cv_results_df = pd.DataFrame(grid_search.cv_results_)
        cv_results_path = os.path.join(model_dir, f"{model_name}_cv_results.csv")
        # 只保存重要列
        important_cols = ["params", "mean_test_score", "std_test_score", "rank_test_score"]
        cv_results_df[important_cols].to_csv(cv_results_path, index=False, encoding='utf-8')
        logger.info(f"交叉验证结果保存至: {cv_results_path}")
        
        # 9. 与默认参数模型比较
        logger.info("步骤9: 与默认参数模型比较...")
        default_model = xgb.XGBClassifier(**base_params, **xgboost_config)
        default_model.fit(X_train, y_train)
        default_test_accuracy = accuracy_score(y_test, default_model.predict(X_test))
        logger.info(f"默认参数测试准确率: {default_test_accuracy:.4f}")
        logger.info(f"网格搜索提升: {test_accuracy - default_test_accuracy:.4f} (相对提升: {(test_accuracy - default_test_accuracy)/default_test_accuracy*100:.2f}%)")
        
        logger.info("=" * 60)
        logger.info("网格搜索优化完成！")
        logger.info("=" * 60)
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("网格搜索优化摘要")
        print("=" * 60)
        print(f"模型名称: {model_name}")
        print(f"最佳参数: {grid_search.best_params_}")
        print(f"交叉验证准确率: {grid_search.best_score_:.4f}")
        print(f"验证集准确率: {val_accuracy:.4f}")
        print(f"测试集准确率: {test_accuracy:.4f}")
        print(f"默认参数测试准确率: {default_test_accuracy:.4f}")
        print(f"准确率提升: {test_accuracy - default_test_accuracy:.4f}")
        print(f"特征数量: {X.shape[1]}")
        print("前5个重要特征:")
        for i, (feature, imp) in enumerate(importance_df.head(5).values, 1):
            print(f"  {i}. {feature}: {imp:.4f}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"网格搜索失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())