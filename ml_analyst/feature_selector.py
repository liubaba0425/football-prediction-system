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