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