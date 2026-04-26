#!/usr/bin/env python3
"""
足球预测快速启动脚本
用法: python predict.py "主队" "客队" [联赛]
"""
import sys
from football_predictor import FootballPredictor, SUPPORTED_LEAGUES

def main():
    # 支持的联赛
    leagues = list(SUPPORTED_LEAGUES.keys())

    # 解析命令行参数
    if len(sys.argv) < 3:
        print("用法: python predict.py \"主队\" \"客队\" [联赛]")
        print("\n示例:")
        print('  python predict.py "Manchester United" "Liverpool"')
        print('  python predict.py "Arsenal" "Chelsea" soccer_epl')
        print('  python predict.py "巴塞罗那" "皇家马德里" soccer_spain_la_liga')
        print("\n支持的联赛:")
        for code, name in SUPPORTED_LEAGUES.items():
            print(f"  {code}: {name}")
        return

    home_team = sys.argv[1]
    away_team = sys.argv[2]
    league = sys.argv[3] if len(sys.argv) > 3 else "soccer_epl"

    if league not in SUPPORTED_LEAGUES:
        print(f"错误: 不支持的联赛 '{league}'")
        print("支持的联赛:")
        for code, name in SUPPORTED_LEAGUES.items():
            print(f"  {code}: {name}")
        return

    print(f"\n🎯 预测比赛: {home_team} vs {away_team}")
    print(f"📊 联赛: {SUPPORTED_LEAGUES[league]}")

    predictor = FootballPredictor()
    result = predictor.predict(home_team, away_team, league)

    if result:
        print(result)

if __name__ == "__main__":
    main()
