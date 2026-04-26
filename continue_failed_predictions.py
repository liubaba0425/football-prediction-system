#!/usr/bin/env python3
"""
预测之前失败但现在可用的比赛
"""

import subprocess
import time
import json
import os
import sys
from datetime import datetime
import traceback

# 可用的4场比赛
AVAILABLE_MATCHES = [
    {"home": "Greuther Fürth", "away": "SV Darmstadt 98", "league": "soccer_germany_bundesliga2", "id": 1},
    {"home": "AIK", "away": "Kalmar FF", "league": "soccer_sweden_allsvenskan", "id": 2},
    {"home": "Nottingham Forest", "away": "Burnley", "league": "soccer_epl", "id": 3},
    {"home": "Aston Villa", "away": "Sunderland", "league": "soccer_epl", "id": 4},
]

def create_prediction_script(match):
    """创建单场比赛预测脚本"""
    script = f'''#!/usr/bin/env python3
import sys
sys.path.append('.')
from football_predictor import FootballPredictor
from team_translator import translate_team_name
import json
import traceback

try:
    predictor = FootballPredictor()
    home_team = "{match['home']}"
    away_team = "{match['away']}"
    league = "{match['league']}"
    
    result = predictor.predict(home_team, away_team, league)
    
    # 确保result是字典
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except:
            result = {{"success": False, "error": f"Result is string: {{result}}"}}
    
    output = {{
        "match_id": {match['id']},
        "home": home_team,
        "away": away_team,
        "league": league,
        "home_cn": translate_team_name(home_team),
        "away_cn": translate_team_name(away_team),
        "success": result.get("success", False) if isinstance(result, dict) else False,
        "result": result,
        "reports": predictor.reports,
        "ml_report": predictor.reports.get("ml", {{}})
    }}
    
    print(json.dumps(output, ensure_ascii=False, default=str))
    
except Exception as e:
    output = {{
        "match_id": {match['id']},
        "home": "{match['home']}",
        "away": "{match['away']}",
        "league": "{match['league']}",
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc()
    }}
    print(json.dumps(output, ensure_ascii=False, default=str))
'''
    return script

def parse_prediction_result(json_data):
    """解析预测结果，提取关键信息"""
    if not json_data.get("success", False):
        return {"error": json_data.get("error", "Unknown error"), "success": False}
    
    reports = json_data.get("reports", {})
    ml_report = reports.get("ml", {})
    
    # 基础信息
    home_cn = json_data.get("home_cn", json_data.get("home"))
    away_cn = json_data.get("away_cn", json_data.get("away"))
    
    # ML预测
    ml_prediction = ml_report.get("prediction", "未知")
    ml_confidence = ml_report.get("confidence", 0)
    
    # 市场推荐
    asian_value = reports.get("asian", {}).get("value_score", 0)
    overunder_value = reports.get("overunder", {}).get("overunder_value_score", 0)
    
    if asian_value > overunder_value:
        market = "让球盘"
        recommendation = reports.get("asian", {}).get("recommendation", "N/A")
        value = asian_value
        market_detail = reports.get("asian", {}).get("actual_handicap", "N/A")
    else:
        market = "大小球"
        bias = reports.get("overunder", {}).get("market_bias", "N/A")
        line = reports.get("overunder", {}).get("mainstream_total_line", 2.5)
        recommendation = f"{bias} {line}球"
        value = overunder_value
        market_detail = f"{line}球"
    
    # 隐含概率
    stats_conf = reports.get("stats", {})
    home_prob = stats_conf.get("home_win", 0)
    draw_prob = stats_conf.get("draw", 0)
    away_prob = stats_conf.get("away_win", 0)
    
    # 其他指标
    upset_risk = reports.get("upset", {}).get("upset_risk_score", 50)
    final_confidence = reports.get("final_confidence", 0)
    
    return {
        "match_id": json_data.get("match_id"),
        "match": f"{home_cn} vs {away_cn}",
        "home_cn": home_cn,
        "away_cn": away_cn,
        "league": json_data.get("league"),
        "ml_prediction": ml_prediction,
        "ml_confidence": ml_confidence,
        "market": market,
        "recommendation": recommendation,
        "market_detail": market_detail,
        "value": value,
        "home_prob": home_prob,
        "draw_prob": draw_prob,
        "away_prob": away_prob,
        "upset_risk": upset_risk,
        "confidence": final_confidence,
        "has_debate": reports.get("debate_triggered", False),
        "success": True
    }

def run_single_prediction(match):
    """运行单场比赛预测"""
    match_id = match["id"]
    home = match["home"]
    away = match["away"]
    league = match["league"]
    
    print(f"\n[{match_id}/{len(AVAILABLE_MATCHES)}] 预测: {home} vs {away}")
    print(f"   联赛: {league}")
    
    # 创建临时脚本
    script_content = create_prediction_script(match)
    script_path = f"temp_predict_{match_id}.py"
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    
    start_time = time.time()
    try:
        # 设置超时：90秒
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=os.getcwd()
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            try:
                output_json = json.loads(result.stdout.strip())
                
                # 解析结果
                if output_json.get("success"):
                    parsed_result = parse_prediction_result(output_json)
                    parsed_result["elapsed"] = elapsed
                    print(f"   ✅ 预测成功 (用时: {elapsed:.1f}s)")
                    print(f"       推荐: {parsed_result.get('market')} {parsed_result.get('recommendation')}")
                    print(f"       信心: {parsed_result.get('confidence', 0):.1f}%")
                    return parsed_result
                else:
                    print(f"   ❌ 预测失败: {output_json.get('error', 'Unknown error')}")
                    return {
                        "match": f"{home} vs {away}",
                        "league": league,
                        "success": False,
                        "error": output_json.get("error", "Unknown error"),
                        "elapsed": elapsed
                    }
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON解析失败: {e}")
                print(f"   输出: {result.stdout[:200]}...")
                return {
                    "match": f"{home} vs {away}",
                    "league": league,
                    "success": False,
                    "error": f"JSON解析错误: {e}",
                    "elapsed": elapsed
                }
        else:
            print(f"   ❌ 脚本执行失败 (退出码: {result.returncode})")
            print(f"   错误输出: {result.stderr[:200]}")
            return {
                "match": f"{home} vs {away}",
                "league": league,
                "success": False,
                "error": f"脚本退出码: {result.returncode}",
                "elapsed": elapsed
            }
            
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"   ⏰ 超时 (90秒)")
        return {
            "match": f"{home} vs {away}",
            "league": league,
            "success": False,
            "error": "超时 (90秒)",
            "elapsed": elapsed
        }
    finally:
        # 清理临时文件
        try:
            os.remove(script_path)
        except:
            pass

def main():
    print("=" * 70)
    print("🏆 继续预测之前失败的比赛")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总比赛数: {len(AVAILABLE_MATCHES)}")
    print()
    
    results = []
    
    # 预测所有可用比赛
    for i, match in enumerate(AVAILABLE_MATCHES, 1):
        result = run_single_prediction(match)
        results.append(result)
        
        # 短暂暂停，避免API限流
        if i < len(AVAILABLE_MATCHES):
            print("   等待2秒...")
            time.sleep(2)
    
    # 分析结果
    print("\n" + "=" * 70)
    print("📊 预测汇总")
    print("=" * 70)
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"\n✅ 成功预测: {len(successful)}/{len(AVAILABLE_MATCHES)} 场")
    print(f"❌ 预测失败: {len(failed)}/{len(AVAILABLE_MATCHES)} 场")
    
    if failed:
        print("\n失败比赛:")
        for r in failed:
            print(f"  • {r['match']}: {r.get('error', 'Unknown error')}")
    
    # 按信心分数排序
    successful.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    # 保存详细结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"continue_predict_results_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total": len(AVAILABLE_MATCHES),
                "successful": len(successful),
                "failed": len(failed),
                "timestamp": timestamp
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细结果已保存: {output_file}")
    
    # 显示Top推荐
    if successful:
        print(f"\n🏆 Top推荐 (按信心排序):")
        for i, r in enumerate(successful[:3], 1):
            print(f"{i}. {r['match']}")
            print(f"   推荐: {r.get('market', '未知')} {r.get('recommendation', '未知')}")
            print(f"   信心: {r.get('confidence', 0):.1f}%")
            print(f"   ML预测: {r.get('ml_prediction', '未知')} ({r.get('ml_confidence', 0):.1f}%)")
            print()
    
    return results, output_file

if __name__ == "__main__":
    results, output_file = main()
    print(f"\n🎉 预测完成！结果保存在: {output_file}")