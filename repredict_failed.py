#!/usr/bin/env python3
"""
重新预测之前失败的比赛，使用 FootballPredictor 直接调用。
"""
import json
import os
import sys
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from football_predictor import FootballPredictor
except ImportError as e:
    print(f"导入 FootballPredictor 失败: {e}")
    sys.exit(1)

def load_failed_matches():
    """加载失败的比赛"""
    with open('remaining_matches_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    failed = []
    for match in data:
        if not match.get('success', False):
            failed.append(match)
    return failed

def predict_match(home, away, league):
    """直接使用 FootballPredictor 预测"""
    print(f"预测: {home} vs {away} ({league})")
    
    try:
        predictor = FootballPredictor()
        # 运行预测
        result = predictor.predict(home, away, league)
        
        if result.get('success'):
            print(f"预测成功，信心分数: {result.get('final_confidence', 'N/A')}%")
            # 生成报告文件
            report = predictor.get_report()
            if report:
                # 保存报告（FootballPredictor 内部已经保存了）
                pass
            return True, None, result
        else:
            error = result.get('error', '未知错误')
            print(f"预测失败: {error}")
            return False, error, None
    except Exception as e:
        error = f"预测异常: {e}"
        print(error)
        import traceback
        traceback.print_exc()
        return False, error, None

def update_json_with_result(match_id, success, error=None, result=None):
    """更新 JSON 文件中的比赛结果"""
    with open('remaining_matches_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for match in data:
        if match.get('match_id') == match_id:
            if success and result:
                # 更新成功结果
                match['success'] = True
                match.pop('error', None)
                # 复制结果字段
                match.update({
                    'implied_probabilities': result.get('implied_probabilities', {}),
                    'ml_prediction': result.get('ml_prediction', {}),
                    'consensus': result.get('consensus', {}),
                    'upset_risk': result.get('upset_risk', 0),
                    'timestamp': datetime.now().isoformat()
                })
                print(f"更新比赛 {match_id}: 成功")
            else:
                match['success'] = False
                match['error'] = error
                match['timestamp'] = datetime.now().isoformat()
                print(f"更新比赛 {match_id}: 失败 - {error}")
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
        success, error, result = predict_match(home, away, league)
        
        # 更新 JSON
        update_json_with_result(match_id, success, error, result)
    
    print("\n所有比赛处理完成。")

if __name__ == '__main__':
    main()