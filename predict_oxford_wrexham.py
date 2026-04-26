#!/usr/bin/env python3
"""
牛津联 vs 雷克瑟姆 预测脚本
"""
import sys
sys.path.append('.')

from football_predictor import FootballPredictor
from team_translator import translate_team_name

def main():
    # 初始化预测器
    predictor = FootballPredictor()
    
    # 比赛信息 - 使用英文队名
    home_team = "Oxford United"
    away_team = "Wrexham AFC"
    league = "soccer_efl_champ"  # 英格兰冠军联赛
    
    print(f"预测比赛: {translate_team_name(home_team)} vs {translate_team_name(away_team)}")
    print(f"联赛: 英格兰冠军联赛")
    print("=" * 60)
    
    try:
        # 执行预测
        result = predictor.predict(home_team, away_team, league)
        
        if result:
            print("\n🎯 预测完成!")
            # result 是字符串，直接打印
            print(result)
            
            # 显示ML-Analyst结果（如果可用）
            if predictor.reports.get('ml'):
                ml_report = predictor.reports['ml']
                if not ml_report.get('error'):
                    print(f"\n🤖 ML-Analyst 预测: {ml_report.get('prediction')} (信心: {ml_report.get('confidence', 0)}%)")
                    print(f"   主胜概率: {ml_report.get('probabilities', {}).get('home_win', 0):.3f}")
                    print(f"   平局概率: {ml_report.get('probabilities', {}).get('draw', 0):.3f}")
                    print(f"   客胜概率: {ml_report.get('probabilities', {}).get('away_win', 0):.3f}")
                    
                    # 显示ML模型信息
                    model_info = ml_report.get('model_info', {})
                    if model_info:
                        print(f"   模型类型: {model_info.get('type', '未知')}")
                        print(f"   训练日期: {model_info.get('training_date', '未知')}")
                        print(f"   模型准确率: {model_info.get('accuracy', 0)*100:.2f}%")
        else:
            print("\n❌ 预测失败: 未找到比赛数据或数据不足")
            
    except Exception as e:
        print(f"\n❌ 预测过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()