#!/usr/bin/env python3
"""
使用子进程逐场预测9场比赛，避免单场卡死
"""
import subprocess
import time
import json
from datetime import datetime
import os
import sys

# 9场可预测比赛列表
MATCHES = [
    # J联赛
    {"home": "Gamba Osaka", "away": "Fagiano Okayama", "league": "soccer_japan_j_league", "id": 1},
    {"home": "Nagoya Grampus", "away": "Avispa Fukuoka", "league": "soccer_japan_j_league", "id": 2},
    # K联赛
    {"home": "Pohang Steelers", "away": "FC Anyang", "league": "soccer_korea_kleague1", "id": 3},
    # 意甲
    {"home": "Cremonese", "away": "Torino", "league": "soccer_italy_serie_a", "id": 4},
    # 英冠
    {"home": "Ipswich Town", "away": "Middlesbrough", "league": "soccer_efl_champ", "id": 5},
    # 德乙
    {"home": "Greuther Fürth", "away": "SV Darmstadt 98", "league": "soccer_germany_bundesliga2", "id": 6},
    # 瑞典超
    {"home": "AIK", "away": "Kalmar FF", "league": "soccer_sweden_allsvenskan", "id": 7},
    # 英超
    {"home": "Nottingham Forest", "away": "Burnley", "league": "soccer_epl", "id": 8},
    {"home": "Aston Villa", "away": "Sunderland", "league": "soccer_epl", "id": 9},
]

def create_single_script(match):
    """为单场比赛创建临时预测脚本"""
    script = f'''#!/usr/bin/env python3
import sys
sys.path.append('.')
from football_predictor import FootballPredictor
from team_translator import translate_team_name
import json

def main():
    predictor = FootballPredictor()
    
    home_team = "{match['home']}"
    away_team = "{match['away']}"
    league = "{match['league']}"
    
    try:
        result = predictor.predict(home_team, away_team, league)
        
        output = {{
            "match_id": {match['id']},
            "home": home_team,
            "away": away_team,
            "league": league,
            "success": True,
            "result": result,
            "reports": predictor.reports,
            "ml_report": predictor.reports.get("ml", {{}})
        }}
        
        # 打印JSON输出
        print(json.dumps(output, ensure_ascii=False))
        
    except Exception as e:
        output = {{
            "match_id": {match['id']},
            "home": home_team,
            "away": away_team,
            "league": league,
            "success": False,
            "error": str(e)
        }}
        print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
'''
    return script

def extract_key_info(result_json):
    """从JSON结果中提取关键信息"""
    if not result_json.get("success"):
        return {"error": result_json.get("error", "Unknown error")}
    
    reports = result_json.get("reports", {})
    ml_report = reports.get("ml", {})
    
    # 基础信息
    home = result_json.get("home", "")
    away = result_json.get("away", "")
    
    # 获取ML预测
    ml_prediction = ml_report.get("prediction", "未知")
    ml_confidence = ml_report.get("confidence", 0)
    
    # 获取最终推荐
    asian_value = reports.get("asian", {}).get("value_score", 0)
    overunder_value = reports.get("overunder", {}).get("overunder_value_score", 0)
    
    if asian_value > overunder_value:
        market = "让球盘"
        recommendation = reports.get("asian", {}).get("recommendation", "N/A")
        value = asian_value
    else:
        market = "大小球"
        bias = reports.get("overunder", {}).get("market_bias", "N/A")
        line = reports.get("overunder", {}).get("mainstream_total_line", 2.5)
        recommendation = f"{bias} {line}球"
        value = overunder_value
    
    # 获取隐含概率
    stats_conf = reports.get("stats", {})
    home_prob = stats_conf.get("home_win", 0)
    draw_prob = stats_conf.get("draw", 0)
    away_prob = stats_conf.get("away_win", 0)
    
    # 获取冷门风险
    upset_risk = reports.get("upset", {}).get("upset_risk_score", 50)
    
    # 最终信心分数
    final_confidence = reports.get("final_confidence", 0)
    
    return {
        "match_id": result_json.get("match_id"),
        "home": home,
        "away": away,
        "league": result_json.get("league"),
        "ml_prediction": ml_prediction,
        "ml_confidence": ml_confidence,
        "market": market,
        "recommendation": recommendation,
        "value": value,
        "home_prob": home_prob,
        "draw_prob": draw_prob,
        "away_prob": away_prob,
        "upset_risk": upset_risk,
        "confidence": final_confidence,
        "has_debate": reports.get("debate_triggered", False)
    }

def main():
    results = []
    
    print("=" * 70)
    print("🏆 9场比赛逐场预测 (独立进程)")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    for match in MATCHES:
        match_id = match["id"]
        home = match["home"]
        away = match["away"]
        league = match["league"]
        
        print(f"\n[{match_id}/9] 预测: {home} vs {away}")
        print(f"   联赛: {league}")
        
        # 创建临时脚本
        script_content = create_single_script(match)
        script_path = f"temp_predict_{match_id}.py"
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        # 设置超时：90秒（单场比赛通常需要50-60秒）
        timeout = 90
        start_time = time.time()
        
        try:
            # 运行子进程
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )
            
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                # 解析JSON输出
                try:
                    output_json = json.loads(result.stdout.strip())
                    key_info = extract_key_info(output_json)
                    
                    # 显示结果
                    print(f"   ⏱️ 耗时: {elapsed:.1f}秒")
                    
                    if "error" in key_info:
                        print(f"   ❌ 错误: {key_info['error']}")
                        results.append({
                            "match": f"{home} vs {away}",
                            "league": league,
                            "error": key_info["error"],
                            "elapsed": elapsed
                        })
                    else:
                        print(f"   📊 隐含概率: 主胜{key_info['home_prob']*100:.1f}% | 平局{key_info['draw_prob']*100:.1f}% | 客胜{key_info['away_prob']*100:.1f}%")
                        print(f"   🤖 ML预测: {key_info['ml_prediction']} ({key_info['ml_confidence']:.1f}%)")
                        print(f"   🎯 推荐: {key_info['market']} {key_info['recommendation']}")
                        print(f"   💪 信心: {key_info['confidence']:.1f}% | 价值: {key_info['value']}/100")
                        print(f"   ⚠️ 冷门风险: {key_info['upset_risk']}/100")
                        
                        results.append({
                            "match": f"{home} vs {away}",
                            "league": league,
                            "market": key_info["market"],
                            "recommendation": key_info["recommendation"],
                            "confidence": key_info["confidence"],
                            "ml_prediction": key_info["ml_prediction"],
                            "ml_confidence": key_info["ml_confidence"],
                            "home_prob": key_info["home_prob"],
                            "away_prob": key_info["away_prob"],
                            "elapsed": elapsed,
                            "success": True
                        })
                        
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON解析错误: {e}")
                    print(f"   输出: {result.stdout[:200]}...")
                    results.append({
                        "match": f"{home} vs {away}",
                        "league": league,
                        "error": f"JSON解析错误: {e}",
                        "elapsed": elapsed
                    })
            else:
                print(f"   ❌ 进程失败 (返回码: {result.returncode})")
                print(f"   错误输出: {result.stderr[:200]}...")
                results.append({
                    "match": f"{home} vs {away}",
                    "league": league,
                    "error": f"进程失败: {result.returncode}",
                    "elapsed": elapsed
                })
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ 超时 ({timeout}秒)")
            results.append({
                "match": f"{home} vs {away}",
                "league": league,
                "error": f"超时 ({timeout}秒)",
                "elapsed": timeout
            })
        except Exception as e:
            print(f"   ❌ 系统错误: {e}")
            results.append({
                "match": f"{home} vs {away}",
                "league": league,
                "error": f"系统错误: {e}",
                "elapsed": time.time() - start_time
            })
        
        # 删除临时脚本
        try:
            os.remove(script_path)
        except:
            pass
        
        # 短暂暂停
        if match_id < 9:
            time.sleep(1)
    
    # 汇总报告
    print("\n" + "=" * 70)
    print("📊 9场比赛预测汇总")
    print("=" * 70)
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"\n✅ 成功预测: {len(successful)} 场")
    print(f"❌ 预测失败: {len(failed)} 场")
    
    if successful:
        # 按信心分数排序
        successful.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        print("\n🏆 成功预测的比赛 (按信心分数排序):")
        for i, r in enumerate(successful[:5], 1):  # 显示前5个
            print(f"\n{i}. {r['match']}")
            print(f"   联赛: {r['league']}")
            print(f"   推荐: {r['market']} {r['recommendation']}")
            print(f"   信心: {r['confidence']:.1f}%")
            print(f"   ML预测: {r['ml_prediction']} ({r['ml_confidence']:.1f}%)")
            print(f"   隐含概率: 主胜{r['home_prob']*100:.1f}% | 客胜{r['away_prob']*100:.1f}%")
            print(f"   耗时: {r['elapsed']:.1f}秒")
    
    if failed:
        print("\n❌ 预测失败的比赛:")
        for r in failed[:3]:  # 显示前3个失败
            print(f"   • {r['match']}: {r.get('error', 'Unknown error')}")
    
    # 保存结果到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"batch_predict_results_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total": 9,
                "successful": len(successful),
                "failed": len(failed),
                "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细结果已保存: {output_file}")
    
    # 准备微信消息摘要
    if successful:
        high_confidence = [r for r in successful if r.get("confidence", 0) >= 55]
        
        weixin_message = f"⚽ 9场比赛批量预测完成\n\n"
        weixin_message += f"✅ 成功预测: {len(successful)}/9 场\n"
        weixin_message += f"🎯 高信心推荐(≥55%): {len(high_confidence)} 场\n\n"
        
        if high_confidence:
            weixin_message += "Top 推荐:\n"
            for i, r in enumerate(high_confidence[:3], 1):
                weixin_message += f"{i}. {r['match']}\n"
                weixin_message += f"   推荐: {r['market']} {r['recommendation']}\n"
                weixin_message += f"   信心: {r['confidence']:.1f}%\n"
                weixin_message += f"   ML预测: {r['ml_prediction']}\n\n"
        
        weixin_message += f"详细报告: {output_file}\n"
        weixin_message += "⚠️ 仅供参考"
        
        print(f"\n📨 微信消息摘要已准备 (共 {len(weixin_message)} 字符)")
        print("\n是否发送到微信? (y/n): ", end="")
    
    return results

if __name__ == "__main__":
    main()