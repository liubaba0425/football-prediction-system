#!/usr/bin/env python3
"""
蔚山现代 vs 光州FC 预测脚本
"""
import sys
import os
sys.path.append('.')

# 临时添加K联赛支持
SUPPORTED_LEAGUES_KLEAGUE = {
    "soccer_korea_kleague1": "韩国K联赛",
    "soccer_epl": "英格兰超级联赛",
    "soccer_spain_la_liga": "西班牙甲级联赛",
    "soccer_germany_bundesliga": "德国甲级联赛",
    "soccer_italy_serie_a": "意大利甲级联赛",
    "soccer_france_ligue_one": "法国甲级联赛",
    "soccer_uefa_champs_league": "欧洲冠军联赛",
    "soccer_uefa_europa_league": "欧洲联赛（欧联杯）",
    "soccer_uefa_europa_conference_league": "欧洲协会联赛（欧会杯）",
    "soccer_conmebol_copa_libertadores": "南美解放者杯",
    "soccer_china_super_league": "中国足球超级联赛",
}

# 临时添加球队翻译
KLEAGUE_TEAM_TRANSLATIONS = {
    "Ulsan Hyundai FC": "蔚山现代",
    "Gwangju FC": "光州FC",
    "FC Anyang": "安养FC",
    "Pohang Steelers": "浦项制铁",
    "Jeonbuk Hyundai Motors": "全北现代",
    "Seongnam FC": "城南FC",
    "Incheon United": "仁川联",
    "Suwon Samsung Bluewings": "水原三星",
    "Daegu FC": "大邱FC",
    "Jeju United": "济州联",
    "Gangwon FC": "江原FC",
    "Seoul FC": "首尔FC",
}

def translate_team_name(english_name: str) -> str:
    """翻译球队名称"""
    return KLEAGUE_TEAM_TRANSLATIONS.get(english_name, english_name)

def main():
    from football_predictor import FootballPredictor
    
    # 比赛信息
    home_team = "Ulsan Hyundai FC"
    away_team = "Gwangju FC"
    league = "soccer_korea_kleague1"
    
    print(f"预测比赛: {translate_team_name(home_team)} vs {translate_team_name(away_team)}")
    print(f"联赛: {SUPPORTED_LEAGUES_KLEAGUE.get(league, league)}")
    print("=" * 60)
    
    try:
        # 初始化预测器
        predictor = FootballPredictor()
        
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