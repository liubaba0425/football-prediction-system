#!/usr/bin/env python3
"""
检查训练数据中的结果分布
"""
import pandas as pd
import numpy as np
import os

def check_data_distribution():
    data_path = "ml_analyst/data/historical_matches.parquet"
    if not os.path.exists(data_path):
        print(f"数据文件不存在: {data_path}")
        return
    
    print(f"加载数据: {data_path}")
    df = pd.read_parquet(data_path)
    print(f"数据形状: {df.shape}")
    print(f"列名: {list(df.columns)}")
    
    # 检查结果列
    # 可能是 'result' 或 'outcome' 列
    result_cols = [col for col in df.columns if 'result' in col.lower() or 'outcome' in col.lower() or 'winner' in col.lower()]
    print(f"结果相关列: {result_cols}")
    
    for col in result_cols:
        print(f"\n列 '{col}' 的值分布:")
        print(df[col].value_counts())
        print(df[col].value_counts(normalize=True))
    
    # 检查是否包含主客场信息
    # 可能的结果编码: 'H'=主胜, 'D'=平局, 'A'=客胜
    if 'result' in df.columns:
        print("\n结果编码统计:")
        mapping = {'H': '主胜', 'D': '平局', 'A': '客胜'}
        for code, label in mapping.items():
            count = (df['result'] == code).sum()
            if count > 0:
                print(f"{code} ({label}): {count} ({count/len(df)*100:.1f}%)")
    
    # 检查目标变量 y
    # 训练时可能使用 'target' 列
    if 'target' in df.columns:
        print("\n目标变量分布:")
        print(df['target'].value_counts())
        print(df['target'].value_counts(normalize=True))
        
        # 映射到标签
        mapping = {0: '客胜', 1: '平局', 2: '主胜'}
        for val, label in mapping.items():
            count = (df['target'] == val).sum()
            if count > 0:
                print(f"{val} ({label}): {count} ({count/len(df)*100:.1f}%)")

if __name__ == "__main__":
    check_data_distribution()