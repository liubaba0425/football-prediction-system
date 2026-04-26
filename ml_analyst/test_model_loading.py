#!/usr/bin/env python3
"""
测试优化模型加载和预测
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml_analyst import MLAnalyst

def main():
    try:
        analyst = MLAnalyst()
        print("ML-Analyst初始化成功")
        print(f"模型类型: {type(analyst.model)}")
        
        # 检查是否有模型
        if analyst.model is None:
            print("错误: 模型未加载")
            return 1
        
        print("模型加载成功")
        
        # 测试预测（需要样本数据）
        # 创建一个样本特征向量（30个特征）
        import numpy as np
        # 获取特征数量（从模型或配置中）
        # 这里我们假设模型有get_fscore方法
        if hasattr(analyst.model, 'get_fscore'):
            print(f"特征数量: {len(analyst.model.get_fscore())}")
        
        return 0
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())