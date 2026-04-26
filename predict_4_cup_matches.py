#!/usr/bin/env python3
"""
预测4场足球比赛（根据用户提供的联赛信息）
使用子进程隔离，避免单场失败影响整体
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

print(f"开始预测 {{translate_team_name('{home_team_en}')}} vs {{translate_team_name('{away_team_en}')}}")
predictor = FootballPredictor()
try:
    result = predictor.predict('{home_team_en}', '{away_team_en}', '{league}')
    if result and result.get('success'):
        print("✅ 预测成功")
    else:
        print(f"❌ 预测失败: {{result.get('error', '未知错误') if result else '无结果'}}")
except Exception as e:
    print(f"❌ 预测异常: {{e}}")
    import traceback
    traceback.print_exc()
'''

    # 创建临时脚本
    temp_script = f"/tmp/predict_{match_id}.py"
    with open(temp_script, 'w') as f:
        f.write(script_content)
    
    # 运行子进程
    proc = subprocess.Popen(
        [sys.executable, temp_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(timeout=120)  # 2分钟超时
    
    # 打印输出
    print(f"\n{'='*60}")
    print(f"比赛 {match_id}: {home_team_en} vs {away_team_en}")
    print(f"联赛: {league}")
    print(f"{'='*60}")
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    
    # 清理临时脚本
    os.unlink(temp_script)
    
    return proc.returncode == 0

def main():
    # 比赛列表：英文队名，联赛标识，备注
    matches = [
        # (home_en, away_en, league, match_id)
        ("Inter Milan", "Como", "soccer_italy_coppa_italia", "inter_como_coppa"),
        ("Lens", "Toulouse", "soccer_france_coupe_de_france", "lens_toulouse_coupe"),
        ("Real Madrid", "Alaves", "soccer_spain_la_liga", "madrid_alaves_liga"),
        ("Oxford United", "Rotherham United", "soccer_efl_champ", "oxford_rotherham"),
    ]
    
    print("🎯 开始批量预测4场比赛（根据用户提供的联赛信息）")
    print("=" * 60)
    
    results = []
    for home_en, away_en, league, match_id in matches:
        start = time.time()
        success = run_single_match(home_en, away_en, league, match_id)
        elapsed = time.time() - start
        results.append({
            "match_id": match_id,
            "home": home_en,
            "away": away_en,
            "league": league,
            "success": success,
            "time_sec": round(elapsed, 2)
        })
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 预测汇总")
    print("=" * 60)
    for r in results:
        status = "✅ 成功" if r["success"] else "❌ 失败"
        print(f"{r['match_id']}: {r['home']} vs {r['away']} - {status} ({r['time_sec']}秒)")
    
    # 检查生成的预测文件
    prediction_files = list(Path(".").glob("prediction_*.txt"))
    print(f"\n📁 生成的预测文件: {len(prediction_files)} 个")
    # 只显示最近生成的几个
    recent_files = sorted(prediction_files, key=os.path.getmtime, reverse=True)[:5]
    for f in recent_files:
        print(f"  {f.name}")
    
    # 提示
    print("\n⚠️  注意:")
    print("   1. 如果比赛在API中没有当前赔率数据，预测会失败。")
    print("   2. '雷克斯' 暂时按 'Rotherham United (罗瑟汉姆)' 处理。")
    print("      如果是其他球队，请提供正确的英文队名。")

if __name__ == "__main__":
    main()