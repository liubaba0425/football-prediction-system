#!/usr/bin/env python3
"""
单场比赛预测 - 悉尼FC vs 珀斯光荣
"""
import sys
sys.path.append('.')

from football_predictor import FootballPredictor
from team_translator import translate_team_name

def main():
    # 初始化预测器
    predictor = FootballPredictor()
    
    # 比赛信息
    home_team = "Sydney FC"
    away_team = "Perth Glory"
    league = "soccer_australia_aleague"  # 澳大利亚A联赛
    
    print(f"预测比赛: {translate_team_name(home_team)} vs {translate_team_name(away_team)}")
    print(f"联赛: {league}")
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
        else:
            print("\n❌ 预测失败: 未找到比赛数据或数据不足")
            
    except Exception as e:
        print(f"\n❌ 预测过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()