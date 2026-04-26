#!/usr/bin/env python3
"""
预测两场比赛：弗赖堡vs海登海姆 和 赫根vs加尔斯
使用子进程隔离，避免单场卡死
"""
import subprocess
import time
import json
import os
import sys
from datetime import datetime

# 比赛列表
MATCHES = [
    {
        "home": "SC Freiburg",
        "away": "1. FC Heidenheim",
        "league": "soccer_germany_bundesliga",
        "id": 1,
        "name": "弗赖堡 vs 海登海姆"
    },
    {
        "home": "BK Hacken",
        "away": "GAIS",
        "league": "soccer_sweden_allsvenskan",
        "id": 2,
        "name": "赫根 vs 加尔斯"
    }
]

def create_prediction_script(match):
    """创建单场比赛预测脚本"""
    script = f'''#!/usr/bin/env python3
import sys
sys.path.append('.')
from football_predictor import FootballPredictor
import json
import traceback

try:
    predictor = FootballPredictor()
    home_team = "{match['home']}"
    away_team = "{match['away']}"
    league = "{match['league']}"
    
    result = predictor.predict(home_team, away_team, league)
    
    # 输出JSON格式的结果
    output = {{
        "match_id": {match['id']},
        "home_team": home_team,
        "away_team": away_team,
        "league": league,
        "success": result.get("success", False) if isinstance(result, dict) else False,
        "result": result if isinstance(result, dict) else str(result),
        "reports": predictor.reports if hasattr(predictor, 'reports') else {{}}
    }}
    print(json.dumps(output, ensure_ascii=False))
    
except Exception as e:
    output = {{
        "match_id": {match['id']},
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc()
    }}
    print(json.dumps(output, ensure_ascii=False))
'''
    return script

def run_single_prediction(match):
    """运行单场比赛预测"""
    match_id = match["id"]
    home = match["home"]
    away = match["away"]
    league = match["league"]
    name = match["name"]
    
    print(f"[{match_id}/{len(MATCHES)}] 开始预测: {name}")
    print(f"   球队: {home} vs {away}")
    print(f"   联赛: {league}")
    
    # 创建临时脚本
    script_content = create_prediction_script(match)
    script_path = f"temp_pred_{match_id}.py"
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    result_info = {
        "match": name,
        "home": home,
        "away": away,
        "league": league,
        "success": False,
        "error": None,
        "elapsed": 0
    }
    
    start_time = time.time()
    
    try:
        # 运行预测，设置90秒超时
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=os.getcwd()
        )
        
        elapsed = time.time() - start_time
        result_info["elapsed"] = elapsed
        
        if result.returncode == 0:
            try:
                # 解析JSON输出
                json_data = json.loads(result.stdout.strip())
                
                if json_data.get("success", False):
                    result_data = json_data.get("result", {})
                    reports = json_data.get("reports", {})
                    
                    # 提取关键信息
                    home_cn = result_data.get("home_team_cn", home)
                    away_cn = result_data.get("away_team_cn", away)
                    
                    implied = result_data.get("implied_probabilities", {})
                    home_prob = implied.get("home", 0)
                    draw_prob = implied.get("draw", 0)
                    away_prob = implied.get("away", 0)
                    
                    ml_prediction = result_data.get("ml_prediction", {})
                    ml_result = ml_prediction.get("result", "未知")
                    ml_confidence = ml_prediction.get("confidence", 0)
                    
                    consensus = result_data.get("consensus", {})
                    recommended_market = consensus.get("recommended_market", "未知")
                    recommendation = consensus.get("recommendation", "N/A")
                    confidence = consensus.get("confidence", 0)
                    
                    upset_risk = result_data.get("upset_risk", 0)
                    risk_level = result_data.get("risk_level", "未知")
                    
                    result_info.update({
                        "success": True,
                        "home_cn": home_cn,
                        "away_cn": away_cn,
                        "home_prob": home_prob,
                        "draw_prob": draw_prob,
                        "away_prob": away_prob,
                        "ml_result": ml_result,
                        "ml_confidence": ml_confidence,
                        "recommended_market": recommended_market,
                        "recommendation": recommendation,
                        "confidence": confidence,
                        "upset_risk": upset_risk,
                        "risk_level": risk_level,
                        "result_data": result_data
                    })
                    
                    print(f"   ✅ 预测成功 ({elapsed:.1f}秒)")
                    print(f"      比赛: {home_cn} vs {away_cn}")
                    print(f"      推荐: {recommended_market} {recommendation}")
                    print(f"      信心: {confidence:.1f}%")
                    print(f"      ML预测: {ml_result} ({ml_confidence:.1f}%)")
                    print(f"      冷门风险: {upset_risk}/100 ({risk_level})")
                    
                else:
                    result_info["error"] = json_data.get("error", "预测失败")
                    print(f"   ❌ 预测失败: {result_info['error']}")
                    
            except json.JSONDecodeError as e:
                result_info["error"] = f"JSON解析错误: {e}"
                print(f"   ❌ JSON解析错误: {e}")
                print(f"   输出: {result.stdout[:200]}...")
                
        else:
            result_info["error"] = f"子进程返回码: {result.returncode}"
            print(f"   ❌ 子进程失败: {result.returncode}")
            print(f"   错误输出: {result.stderr[:200]}...")
            
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        result_info["elapsed"] = elapsed
        result_info["error"] = "超时 (90秒)"
        print(f"   ⏰ 预测超时 ({elapsed:.1f}秒)")
        
    except Exception as e:
        elapsed = time.time() - start_time
        result_info["elapsed"] = elapsed
        result_info["error"] = str(e)
        print(f"   ❌ 异常错误: {e}")
        
    finally:
        # 清理临时文件
        try:
            os.remove(script_path)
        except:
            pass
    
    return result_info

def main():
    print("=" * 70)
    print("🏆 足球预测智能体系统 - 两场比赛预测")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"预测 {len(MATCHES)} 场比赛")
    print()
    
    results = []
    
    for i, match in enumerate(MATCHES, 1):
        result = run_single_prediction(match)
        results.append(result)
        
        # 短暂暂停，避免API限流
        if i < len(MATCHES):
            time.sleep(2)
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("📊 预测汇总")
    print("=" * 70)
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"✅ 成功预测: {len(successful)}/{len(MATCHES)} 场")
    print(f"❌ 预测失败: {len(failed)}/{len(MATCHES)} 场")
    
    if successful:
        print(f"\n推荐比赛 (按信心分数排序):")
        # 按信心分数排序
        successful_sorted = sorted(
            successful,
            key=lambda x: x.get("confidence", 0),
            reverse=True
        )
        
        for i, result in enumerate(successful_sorted, 1):
            print(f"{i}. {result['match']}")
            print(f"   推荐: {result.get('recommended_market', '未知')} {result.get('recommendation', 'N/A')}")
            print(f"   信心: {result.get('confidence', 0):.1f}%")
            print(f"   隐含概率: 主胜{result.get('home_prob', 0)*100:.1f}% | 平局{result.get('draw_prob', 0)*100:.1f}% | 客胜{result.get('away_prob', 0)*100:.1f}%")
            print(f"   ML预测: {result.get('ml_result', '未知')} ({result.get('ml_confidence', 0):.1f}%)")
            print(f"   冷门风险: {result.get('upset_risk', 0)}/100")
            print()
    
    # 保存结果到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"two_matches_prediction_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total": len(MATCHES),
                "successful": len(successful),
                "failed": len(failed),
                "timestamp": timestamp
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 详细结果已保存: {output_file}")
    
    # 微信消息提示
    print(f"\n是否发送微信消息？ (y/n): ", end="")
    # 在实际使用中，这里可以添加微信发送逻辑
    print("(如需发送微信消息，请在Hermes Agent中手动发送)")

if __name__ == "__main__":
    main()