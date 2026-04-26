#!/usr/bin/env python3
"""
重新预测之前失败的比赛。
从 remaining_matches_results.json 中读取失败的比赛，尝试重新预测。
"""
import json
import subprocess
import sys
import os
from datetime import datetime
import re

def load_failed_matches():
    """加载失败的比赛"""
    with open('remaining_matches_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    failed = []
    for match in data:
        if not match.get('success', False):
            failed.append(match)
    return failed

def translate_team_name(team_name):
    """使用 team_translator 翻译队名"""
    try:
        from team_translator import translate_team_name as translate
        return translate(team_name)
    except ImportError:
        # 如果导入失败，直接返回原队名
        return team_name

def run_prediction(home, away, league):
    """运行预测脚本"""
    # 翻译队名
    home_cn = translate_team_name(home)
    away_cn = translate_team_name(away)
    
    # 构建命令
    cmd = ['python3', 'predict.py', home, away, league]
    print(f"运行预测: {home_cn} vs {away_cn} ({league})")
    
    try:
        # 运行预测脚本
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"预测成功: {result.stdout[-500:] if result.stdout else '无输出'}")
            # 查找最新生成的报告文件
            report_files = [f for f in os.listdir('.') if f.startswith('prediction_') and f.endswith('.txt')]
            if report_files:
                latest = max(report_files, key=os.path.getctime)
                print(f"报告文件: {latest}")
                return True, None, latest
            else:
                return True, None, None
        else:
            error = result.stderr or result.stdout or '未知错误'
            print(f"预测失败: {error[:200]}")
            return False, error, None
    except subprocess.TimeoutExpired:
        error = "预测超时（120秒）"
        print(error)
        return False, error, None
    except Exception as e:
        error = f"执行异常: {e}"
        print(error)
        return False, error, None

def update_json_with_result(match_id, success, error=None, report_file=None):
    """更新 JSON 文件中的比赛结果"""
    with open('remaining_matches_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for match in data:
        if match.get('match_id') == match_id:
            if success:
                match['success'] = True
                match.pop('error', None)  # 删除错误字段
                # 这里可以添加更多预测结果字段，但需要从报告文件中解析
                # 暂时只标记成功
                print(f"更新比赛 {match_id}: 成功")
            else:
                match['success'] = False
                match['error'] = error
                print(f"更新比赛 {match_id}: 失败 - {error}")
            match['timestamp'] = datetime.now().isoformat()
            break
    
    with open('remaining_matches_results.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已更新 JSON 文件")

def main():
    print("开始重新预测失败的比赛...")
    failed = load_failed_matches()
    print(f"找到 {len(failed)} 场失败的比赛")
    
    for match in failed:
        match_id = match.get('match_id')
        home = match.get('home')
        away = match.get('away')
        league = match.get('league')
        
        print(f"\n=== 处理比赛 {match_id}: {home} vs {away} ({league}) ===")
        
        # 运行预测
        success, error, report_file = run_prediction(home, away, league)
        
        # 更新 JSON
        update_json_with_result(match_id, success, error, report_file)
    
    print("\n所有比赛处理完成。")

if __name__ == '__main__':
    main()