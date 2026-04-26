#!/usr/bin/env python3
"""
朗斯 vs 图卢兹 预测脚本
尝试法甲联赛，如果失败则尝试法国杯
"""
import subprocess
import sys
import os
import time
import json
from pathlib import Path

def run_single_match(home_team_en: str, away_team_en: str, league: str, match_id: str):
    """
    运行单场比赛预测（子进程隔离）
    """
    script_content = f'''
import sys
sys.path.append('.')

from football_predictor import FootballPredictor
from team_translator import translate_team_name

print(f"开始预测 {{translate_team_name('{home_team_en}')}} vs {{translate_team_name('{away_team_en}')}} (联赛: {league})")
predictor = FootballPredictor()
try:
    result = predictor.predict('{home_team_en}', '{away_team_en}', '{league}')
    if result and result.get('success'):
        print("✅ 预测成功")
        # 打印关键信息
        print(f"隐含概率: 主胜{{result.get('implied_probabilities', {{}}).get('home', 0)}}% | 平局{{result.get('implied_probabilities', {{}}).get('draw', 0)}}% | 客胜{{result.get('implied_probabilities', {{}}).get('away', 0)}}%")
        print(f"最终推荐: {{result.get('consensus', {{}}).get('recommendation', '未知')}}")
        print(f"信心分数: {{result.get('consensus', {{}}).get('confidence', 0)}}%")
    else:
        error_msg = result.get('error', '未知错误') if result else '无结果'
        print(f"❌ 预测失败: {{error_msg}}")
except Exception as e:
    print(f"❌ 预测过程中发生错误: {{e}}")
    import traceback
    traceback.print_exc()
'''
    
    # 创建临时脚本
    temp_script = f"/tmp/predict_{match_id}.py"
    with open(temp_script, 'w') as f:
        f.write(script_content)
    
    # 运行子进程
    cmd = [sys.executable, temp_script]
    print(f"执行命令: {' '.join(cmd)}")
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        success = result.returncode == 0
        return success, result.stdout
    except subprocess.TimeoutExpired:
        print("⏰ 预测超时 (120秒)")
        return False, "超时"
    finally:
        # 清理临时脚本
        try:
            os.unlink(temp_script)
        except:
            pass

def main():
    home_team = "Lens"
    away_team = "Toulouse"
    
    # 尝试的联赛列表
    leagues_to_try = [
        ("soccer_france_ligue_one", "法甲联赛"),
        ("soccer_france_coupe_de_france", "法国杯"),
    ]
    
    success = False
    for league_code, league_name in leagues_to_try:
        print(f"\n{'='*60}")
        print(f"尝试预测: {home_team} vs {away_team} ({league_name})")
        print(f"{'='*60}")
        
        match_id = f"{home_team}_{away_team}_{league_code}"
        success, output = run_single_match(home_team, away_team, league_code, match_id)
        
        if success:
            # 检查输出中是否有成功信息
            if "预测成功" in output:
                print(f"\n✅ 预测成功 - 联赛: {league_name}")
                break
            else:
                print(f"\n⚠️  预测完成但可能未找到数据，尝试下一个联赛...")
        else:
            print(f"\n❌ 预测失败 - 联赛: {league_name}")
    
    if not success:
        print("\n❌ 所有联赛尝试均失败，可能该比赛当前无赔率数据")
    
    print(f"\n{'='*60}")
    print("预测流程结束")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()