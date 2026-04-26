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