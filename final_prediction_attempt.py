#!/usr/bin/env python3
"""
最终尝试预测两场比赛
"""
import subprocess
import time
import json
import os
import sys
from datetime import datetime

# 比赛列表 - 为德甲设置更短的超时时间
MATCHES = [
    {
        "home": "SC Freiburg",
        "away": "1. FC Heidenheim",
        "league": "soccer_germany_bundesliga",
        "id": 1,
        "name": "弗赖堡 vs 海登海姆 (德甲)",
        "timeout": 60  # 德甲API可能较慢，设置60秒超时
    },
    {
        "home": "BK Hacken",
        "away": "GAIS",
        "league": "soccer_sweden_allsvenskan",
        "id": 2,
        "name": "赫根 vs 加尔斯 (瑞典超)",
        "timeout": 90  # 瑞典超正常超时
    }
]

def create_prediction_script(match):
    """创建单场比赛预测脚本"""
    script = f'''#!/usr/bin/env python3
import sys
sys.path.append('.')
from football_predictor import FootballPredictor
import json

try:
    predictor = FootballPredictor()
    result = predictor.predict("{match['home']}", "{match['away']}", "{match['league']}")
    
    output = {{
        "match_id": {match['id']},
        "success": result.get("success", False) if isinstance(result, dict) else False,
        "result": result if isinstance(result, dict) else str(result)
    }}
    print(json.dumps(output, ensure_ascii=False))
    
except Exception as e:
    output = {{
        "match_id": {match['id']},
        "success": False,
        "error": str(e)
    }}
    print(json.dumps(output, ensure_ascii=False))
'''
    return script

def run_prediction_with_timeout(match):
    """运行预测，带超时控制"""
    match_id = match["id"]
    name = match["name"]
    timeout = match["timeout"]
    
    print(f"\n[比赛 {match_id}] {name}")
    print(f"   超时设置: {timeout}秒")
    
    # 创建临时脚本
    script_content = create_prediction_script(match)
    script_path = f"temp_pred_{match_id}.py"
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    result_info = {
        "match": name,
        "success": False,
        "error": None,
        "elapsed": 0
    }
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        elapsed = time.time() - start_time
        result_info["elapsed"] = elapsed
        
        if result.returncode == 0:
            try:
                json_data = json.loads(result.stdout.strip())
                if json_data.get("success"):
                    result_data = json_data.get("result", {})
                    
                    # 提取关键信息
                    home_cn = result_data.get("home_team_cn", match["home"])
                    away_cn = result_data.get("away_team_cn", match["away"])
                    implied = result_data.get("implied_probabilities", {})
                    ml = result_data.get("ml_prediction", {})
                    consensus = result_data.get("consensus", {})
                    
                    result_info.update({
                        "success": True,
                        "home_cn": home_cn,
                        "away_cn": away_cn,
                        "implied": implied,
                        "ml_result": ml.get("result", "未知"),
                        "ml_confidence": ml.get("confidence", 0),
                        "recommended_market": consensus.get("recommended_market", "未知"),
                        "recommendation": consensus.get("recommendation", "N/A"),
                        "confidence": consensus.get("confidence", 0),
                        "upset_risk": result_data.get("upset_risk", 0),
                        "risk_level": result_data.get("risk_level", "未知")
                    })
                    
                    print(f"   ✅ 预测成功 ({elapsed:.1f}秒)")
                    print(f"      比赛: {home_cn} vs {away_cn}")
                    print(f"      推荐: {consensus.get('recommended_market', '未知')} {consensus.get('recommendation', 'N/A')}")
                    print(f"      信心: {consensus.get('confidence', 0):.1f}%")
                    
                else:
                    result_info["error"] = json_data.get("error", "预测失败")
                    print(f"   ❌ 预测失败: {result_info['error']}")
                    
            except json.JSONDecodeError:
                result_info["error"] = "JSON解析失败"
                print(f"   ❌ JSON解析失败")
                
        else:
            result_info["error"] = f"进程错误: {result.returncode}"
            print(f"   ❌ 进程错误: {result.returncode}")
            
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        result_info["elapsed"] = elapsed
        result_info["error"] = f"超时 ({timeout}秒)"
        print(f"   ⏰ 预测超时 ({elapsed:.1f}秒)")
        
    except Exception as e:
        elapsed = time.time() - start_time
        result_info["elapsed"] = elapsed
        result_info["error"] = str(e)
        print(f"   ❌ 异常: {e}")
        
    finally:
        try:
            os.remove(script_path)
        except:
            pass
    
    return result_info

def main():
    print("=" * 70)
    print("🏆 足球预测智能体系统 - 最终尝试")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"注意: 德甲API可能出现超时问题")
    print()
    
    results = []
    
    for match in MATCHES:
        result = run_prediction_with_timeout(match)
        results.append(result)
        
        # 短暂暂停
        time.sleep(2)
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("📊 最终预测汇总")
    print("=" * 70)
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"✅ 成功预测: {len(successful)}/{len(MATCHES)} 场")
    print(f"❌ 预测失败: {len(failed)}/{len(MATCHES)} 场")
    
    if successful:
        print(f"\n推荐比赛:")
        for i, result in enumerate(successful, 1):
            print(f"{i}. {result['match']}")
            print(f"   推荐: {result.get('recommended_market', '未知')} {result.get('recommendation', 'N/A')}")
            print(f"   信心: {result.get('confidence', 0):.1f}%")
            
            implied = result.get("implied", {})
            if implied:
                print(f"   隐含概率: 主胜{implied.get('home', 0):.1f}% | 平局{implied.get('draw', 0):.1f}% | 客胜{implied.get('away', 0):.1f}%")
            
            print(f"   ML预测: {result.get('ml_result', '未知')} ({result.get('ml_confidence', 0):.1f}%)")
            print(f"   冷门风险: {result.get('upset_risk', 0)}/100")
            print()
    
    if failed:
        print(f"\n失败比赛:")
        for result in failed:
            print(f"• {result['match']}")
            print(f"  错误: {result.get('error', '未知错误')}")
            print(f"  耗时: {result.get('elapsed', 0):.1f}秒")
            print()
    
    # 生成最终报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"final_prediction_{timestamp}.json"
    
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
    
    # 为成功的比赛生成微信消息
    if successful:
        print(f"\n📱 微信消息草稿:")
        print("-" * 50)
        for result in successful:
            message = f"⚽ 预测完成\\n"
            message += f"比赛: {result.get('home_cn', '')} vs {result.get('away_cn', '')}\\n"
            message += f"推荐: {result.get('recommended_market', '')} {result.get('recommendation', '')}\\n"
            message += f"信心: {result.get('confidence', 0):.1f}%\\n"
            message += f"ML预测: {result.get('ml_result', '')} ({result.get('ml_confidence', 0):.1f}%)\\n"
            message += f"冷门风险: {result.get('upset_risk', 0)}/100"
            print(message)
            print("-" * 50)
    
    print(f"\n是否发送微信消息？ (y/n): ", end="")
    print("(如需发送，请在Hermes Agent中使用 send_message 工具)")

if __name__ == "__main__":
    main()