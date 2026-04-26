#!/usr/bin/env python3
import os
import joblib
import xgboost as xgb
import numpy as np
import pandas as pd

# 加载模型字典
models_dir = '/Users/nb888/openclaw-workspace/ml_analyst/models'
model_path = os.path.join(models_dir, 'xgboost_football_20260419_092257.joblib')
model_dict = joblib.load(model_path)

booster = model_dict['model']
print(f"✅ Booster类型: {type(booster)}")

# 获取特征名称
feature_names = booster.feature_names
print(f"📋 Booster特征名称数量: {len(feature_names) if feature_names else 'None'}")

# 读取feature_list.txt
feature_list_path = '/Users/nb888/openclaw-workspace/ml_analyst/features/feature_list.txt'
with open(feature_list_path, 'r') as f:
    lines = f.readlines()

training_features = []
for line in lines:
    line = line.strip()
    if not line or line.startswith('选定的特征列表:') or line.startswith('#'):
        continue
    if '.' in line:
        feature = line.split('.', 1)[1].strip()
    else:
        feature = line
    if feature and feature != 'label':
        training_features.append(feature)

print(f"📄 Feature list.txt特征数量: {len(training_features)}")

# 特征重要性
print("\n🔍 特征重要性 (权重):")
importance = booster.get_score(importance_type='weight')
if importance:
    # 转换为DataFrame以便排序
    importance_df = pd.DataFrame(list(importance.items()), columns=['feature', 'weight'])
    importance_df = importance_df.sort_values('weight', ascending=False)
    
    print(f"📊 总特征数: {len(importance_df)}")
    print(f"🏆 前20个最重要特征:")
    for idx, row in importance_df.head(20).iterrows():
        print(f"  {row['feature']}: {row['weight']}")
    
    # 统计特征重要性总和
    total_weight = importance_df['weight'].sum()
    print(f"📈 总权重: {total_weight}")
    
    # 检查客队相关特征
    away_features = [f for f in importance_df['feature'] if 'away_' in f]
    print(f"\n🚌 客队相关特征数量: {len(away_features)}")
    away_weight = importance_df[importance_df['feature'].isin(away_features)]['weight'].sum()
    print(f"🚌 客队特征总权重: {away_weight:.0f} ({away_weight/total_weight*100:.1f}%)")
    
    # 检查主队相关特征
    home_features = [f for f in importance_df['feature'] if 'home_' in f]
    print(f"🏠 主队相关特征数量: {len(home_features)}")
    home_weight = importance_df[importance_df['feature'].isin(home_features)]['weight'].sum()
    print(f"🏠 主队特征总权重: {home_weight:.0f} ({home_weight/total_weight*100:.1f}%)")
    
    # 检查通用特征
    general_features = [f for f in importance_df['feature'] if 'home_' not in f and 'away_' not in f]
    print(f"📊 通用特征数量: {len(general_features)}")
    general_weight = importance_df[importance_df['feature'].isin(general_features)]['weight'].sum()
    print(f"📊 通用特征总权重: {general_weight:.0f} ({general_weight/total_weight*100:.1f}%)")
    
    # 分析每个类别的前3个特征
    print(f"\n🎯 客队特征Top 3:")
    away_top = importance_df[importance_df['feature'].isin(away_features)].head(3)
    for idx, row in away_top.iterrows():
        print(f"  {row['feature']}: {row['weight']}")
        
    print(f"\n🎯 主队特征Top 3:")
    home_top = importance_df[importance_df['feature'].isin(home_features)].head(3)
    for idx, row in home_top.iterrows():
        print(f"  {row['feature']}: {row['weight']}")
        
    print(f"\n🎯 通用特征Top 3:")
    general_top = importance_df[importance_df['feature'].isin(general_features)].head(3)
    for idx, row in general_top.iterrows():
        print(f"  {row['feature']}: {row['weight']}")
    
else:
    print("❌ 无法获取特征重要性")

# 创建一个典型的特征向量（基于ML-Analyst的默认值）
print("\n🧪 分析典型特征向量...")
# 使用ML-Analyst的默认值
typical_features = {
    'matchday': 25.0,
    'match_date_ordinal': 739725.0,
    'home_recent_form': 0.2,
    'home_avg_goals_scored': 1.5,
    'home_avg_goals_conceded': 1.2,
    'home_home_performance': 0.6,
    'home_away_performance': 0.4,
    'home_win_streak': 1.0,
    'home_unbeaten_streak': 1.0,
    'home_home_away_ratio': 1.5,
    'away_recent_form': 0.8,
    'away_avg_goals_scored': 1.3,
    'away_avg_goals_conceded': 1.4,
    'away_home_performance': 0.5,
    'away_away_performance': 0.5,
    'away_win_streak': 0.0,
    'away_unbeaten_streak': 0.0,
    'away_home_away_ratio': 1.0,
    'home_defensive_stability': 0.8333,
    'away_defensive_stability': 0.7143,
    'home_days_since_last_match': 7.0,
    'away_days_since_last_match': 7.0,
    'home_goal_efficiency': 1.25,
    'away_goal_efficiency': 0.9286,
    'is_weekend': 1.0,
    'month': 4.0,
    'day_of_week': 6.0,
    'season_month': 4.0,
    'is_season_start': 0.0,
    'is_season_mid': 0.0,
    'is_season_end': 1.0
}

# 确保所有特征都存在
for feat in feature_names:
    if feat not in typical_features:
        print(f"⚠️  缺失特征: {feat}")
        typical_features[feat] = 0.0

# 创建DataFrame
df = pd.DataFrame([typical_features])[feature_names]
dmatrix = xgb.DMatrix(df)

# 预测
predictions = booster.predict(dmatrix)
print(f"📈 典型特征向量预测: {predictions[0]}")
print(f"  主胜: {predictions[0][0]:.3f}, 平局: {predictions[0][1]:.3f}, 客胜: {predictions[0][2]:.3f}")

# 分析特征对预测的贡献（使用Tree SHAP近似值）
print("\n🔎 特征贡献分析 (SHAP近似值):")
try:
    import shap
    explainer = shap.TreeExplainer(booster)
    shap_values = explainer.shap_values(df)
    
    # 对于多分类，shap_values是三维数组
    if isinstance(shap_values, list):
        shap_values = np.array(shap_values)
    
    if shap_values.ndim == 3:
        # 形状为 (n_classes, n_samples, n_features)
        print(f"SHAP值形状: {shap_values.shape}")
        
        # 查看每个类别的特征贡献
        classes = ['主胜', '平局', '客胜']
        for class_idx, class_name in enumerate(classes):
            shap_class = shap_values[class_idx][0]  # 第一个样本
            # 创建DataFrame
            shap_df = pd.DataFrame({
                'feature': feature_names,
                'shap': shap_class
            })
            shap_df = shap_df.sort_values('shap', key=abs, ascending=False)
            
            print(f"\n📊 {class_name}的Top 10贡献特征:")
            for idx, row in shap_df.head(10).iterrows():
                print(f"  {row['feature']}: {row['shap']:.4f}")
                
            # 计算客胜的净贡献
            if class_name == '客胜':
                total_shap_away = shap_class.sum()
                print(f"  📈 客胜总SHAP值: {total_shap_away:.4f}")
                
except ImportError:
    print("⚠️  SHAP库未安装，跳过SHAP分析")
except Exception as e:
    print(f"⚠️  SHAP分析失败: {e}")

print("\n✅ 分析完成")