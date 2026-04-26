# ML-Analyst (机器学习分析师)

## 角色定义
**ML-Analyst** 是足球预测多智能体系统中的机器学习专家，负责基于历史数据和实时特征，使用XGBoost模型提供数据驱动的预测分析。

## 核心能力
1. **历史学习**: 从数千场历史比赛中学习模式
2. **实时预测**: 基于当前比赛特征进行概率预测
3. **特征工程**: 自动提取和选择最有预测力的特征
4. **模型管理**: 每日自动更新和优化模型

## 输入数据
- 比赛基本信息（主客队、联赛、时间）
- The Odds API实时赔率数据
- 其他智能体的分析结果（Stats, Tactics等）
- 历史比赛数据库（football-data.org）

## 输出格式
```json
{
  "ml_analyst_version": "1.0",
  "timestamp": "2024-01-15T10:30:00",
  "prediction": "主胜|平局|客胜",
  "confidence": 68.5,
  "probabilities": {
    "home_win": 0.523,
    "draw": 0.254,
    "away_win": 0.223
  },
  "features_used": ["home_odds", "away_odds", "form_diff", ...],
  "model_info": {
    "type": "XGBoost",
    "training_date": "2024-01-15",
    "accuracy": 0.632
  },
  "analysis": "机器学习模型较为支持主队获胜，信心指数68.5%。"
}
```

## 置信度权重计算
ML-Analyst的置信度权重基于：
1. **模型准确性**: 历史验证准确率（0-1）
2. **预测确定性**: 预测概率的标准差
3. **数据质量**: 可用特征数量和完整性

计算公式：
```
confidence_weight = min(100, model_accuracy * 70 + prediction_certainty * 30)
```

## 集成方式
- 在Consensus-Summarizer之前调用
- 输出作为Consensus的额外输入
- 在共识计算中分配权重：0.35（可配置）

## 错误处理
- 模型未加载：返回基础概率分布
- 特征缺失：使用默认值填充
- API失败：降级到规则基础预测

## 配置参数
```yaml
ml_analyst:
  model_type: "xgboost"
  daily_training: true
  training_time: "03:00"
  min_confidence: 40
  weight_in_consensus: 0.35
```

## 性能指标
- 预测延迟: < 100ms
- 训练时间: < 5分钟
- 内存占用: < 500MB
- 准确率目标: > 60%

## 依赖项
- xgboost>=2.0.0
- pandas>=2.0.0
- scikit-learn>=1.3.0
- football-data.org API