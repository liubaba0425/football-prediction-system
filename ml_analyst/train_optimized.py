#!/usr/bin/env python3
"""
使用网格搜索得到的最佳参数训练XGBoost Booster模型
"""
import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
import json
from datetime import datetime
from sklearn.model_selection import train_test_split

def main():
    # 路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    features_path = os.path.join(base_dir, "features", "selected_features.parquet")
    model_dir = os.path.join(base_dir, "models")
    
    if not os.path.exists(features_path):
        print(f"特征文件不存在: {features_path}")
        return 1
    
    # 加载数据
    data = pd.read_parquet(features_path)
    X = data.drop(columns=["label", "label_binary"], errors='ignore')
    y = data["label"]
    
    print(f"数据形状: {data.shape}")
    print(f"特征维度: {X.shape[1]}")
    print(f"标签分布: {y.value_counts().to_dict()}")
    
    # 分割数据集（与网格搜索相同）
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    val_ratio = 0.1 / (1 - 0.2)  # validation_size = 0.1
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_ratio, random_state=42, stratify=y_train_val
    )
    
    print(f"训练集: {X_train.shape[0]}")
    print(f"验证集: {X_val.shape[0]}")
    print(f"测试集: {X_test.shape[0]}")
    
    # 最佳参数
    best_params = {
        "max_depth": 9,
        "learning_rate": 0.3,
        "n_estimators": 200,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "gamma": 0,
        "objective": "multi:softprob",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "seed": 42,
    }
    
    # 转换为xgb.DMatrix
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    dtest = xgb.DMatrix(X_test, label=y_test)
    
    # 训练模型
    evals_result = {}
    model = xgb.train(
        best_params,
        dtrain,
        num_boost_round=best_params["n_estimators"],
        evals=[(dtrain, "train"), (dval, "val")],
        evals_result=evals_result,
        verbose_eval=False,
    )
    
    # 评估
    y_pred = model.predict(dtest)
    y_pred_labels = np.argmax(y_pred, axis=1)
    accuracy = np.mean(y_pred_labels == y_test)
    print(f"测试集准确率: {accuracy:.4f}")
    
    # 保存模型
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = f"xgboost_optimized_{timestamp}"
    model_path = os.path.join(model_dir, f"{model_name}.json")
    model.save_model(model_path)
    
    # 保存评估报告
    report = {
        "model_name": model_name,
        "best_params": best_params,
        "test_accuracy": float(accuracy),
        "train_size": len(X_train),
        "val_size": len(X_val),
        "test_size": len(X_test),
        "training_date": datetime.now().isoformat(),
    }
    
    report_path = os.path.join(model_dir, f"{model_name}_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"优化模型保存至: {model_path}")
    print(f"评估报告保存至: {report_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())