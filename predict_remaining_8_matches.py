#!/usr/bin/env python3
"""
逐场预测9场比赛，并发送最终汇总报告到微信
"""
import subprocess
import time
import json
import os
import sys
from datetime import datetime
import traceback

# 比赛列表（跳过第1场，因为已经预测过）
MATCHES = [
    # 第2场
    {"home": "Nagoya Grampus", "away": "Avispa Fukuoka", "league": "soccer_japan_j_league", "id": 2},
    # 第3场
    {"home": "Pohang Steelers", "away": "FC Anyang", "league": "soccer_korea_kleague1", "id": 3},
    # 第4场
    {"home": "Cremonese", "away": "Torino", "league": "soccer_italy_serie_a", "id": 4},
    # 第5场
    {"home": "Ipswich Town", "away": "Middlesbrough", "league": "soccer_efl_champ", "id": 5},
    # 第6场
    {"home": "Greuther Fürth", "away": "SV Darmstadt 98", "league": "soccer_germany_bundesliga2", "id": 6},
    # 第7场
    {"home": "AIK", "away": "Kalmar FF", "league": "soccer_sweden_allsvenskan", "id": 7},
    # 第8场
    {"home": "Nottingham Forest", "away": "Burnley", "league": "soccer_epl", "id": 8},
    # 第9场
    {"home": "Aston Villa", "away": "Sunderland", "league": "soccer_epl", "id": 9},
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
    
    output = {{
        "match_id": {match['id']},
        "home": home_team,
        "away": away_team,
        "league": league,
        "home_cn": translate_team_name(home_team),
        "away_cn": translate_team_name(away_team),
        "success": True,
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
        return {"error": json_data.get("error", "Unknown error")}
    
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
    
    print(f"[{match_id}/8] 开始预测: {home} vs {away}")
    
    # 创建临时脚本
    script_content = create_prediction_script(match)
    script_path = f"temp_pred_{match_id}.py"
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    result_info = {
        "match": f"{home} vs {away}",
        "league": league,
        "success": False,
        "error": None,
        "elapsed": 0
    }
    
    start_time = time.time()
    
    try:
        # 运行预测，设置120秒超时
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.getcwd()
        )
        
        elapsed = time.time() - start_time
        result_info["elapsed"] = elapsed
        
        if result.returncode == 0:
            try:
                # 解析JSON输出
                json_data = json.loads(result.stdout.strip())
                
                if json_data.get("success", False):
                    parsed = parse_prediction_result(json_data)
                    result_info.update(parsed)
                    result_info["success"] = True
                    
                    print(f"   ✅ 预测成功 ({elapsed:.1f}s)")
                    print(f"      推荐: {parsed['market']} {parsed['recommendation']}")
                    print(f"      信心: {parsed['confidence']:.1f}%")
                    print(f"      ML预测: {parsed['ml_prediction']} ({parsed['ml_confidence']:.1f}%)")
                else:
                    result_info["error"] = json_data.get("error", "预测失败")
                    print(f"   ❌ 预测失败: {result_info['error']}")
                    
            except json.JSONDecodeError as e:
                result_info["error"] = f"JSON解析错误: {e}"
                print(f"   ❌ JSON解析错误: {e}")
        else:
            result_info["error"] = f"进程失败 (返回码: {result.returncode})"
            print(f"   ❌ 进程失败: {result.returncode}")
            if result.stderr:
                print(f"       错误: {result.stderr[:200]}")
                
    except subprocess.TimeoutExpired:
        result_info["error"] = "超时 (120秒)"
        print(f"   ⏰ 超时 (120秒)")
    except Exception as e:
        result_info["error"] = f"系统错误: {e}"
        print(f"   ❌ 系统错误: {e}")
    
    # 清理临时文件
    try:
        os.remove(script_path)
    except:
        pass
    
    return result_info

def main():
    print("=" * 70)
    print("🏆 开始逐场预测剩余8场比赛")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    # 添加第1场比赛的结果（之前已经预测过）
    results.append({
        "match": "大阪钢巴 vs 冈山绿雉",
        "home_cn": "大阪钢巴",
        "away_cn": "冈山绿雉",
        "league": "soccer_japan_j_league",
        "ml_prediction": "客胜",
        "ml_confidence": 94.0,
        "market": "让球盘",
        "recommendation": "Gamba Osaka -0.50",
        "market_detail": "-0.50",
        "value": 75,
        "home_prob": 0.481,
        "draw_prob": 0.345,
        "away_prob": 0.173,
        "upset_risk": 25,
        "confidence": 59.4,
        "has_debate": True,
        "success": True,
        "elapsed": 44.9
    })
    
    # 预测剩余8场比赛
    for i, match in enumerate(MATCHES, 2):
        result = run_single_prediction(match)
        results.append(result)
        
        # 短暂暂停，避免API限流
        if i < len(MATCHES) + 1:
            time.sleep(2)
    
    # 分析结果
    print("\n" + "=" * 70)
    print("📊 9场比赛预测汇总")
    print("=" * 70)
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"\n✅ 成功预测: {len(successful)}/9 场")
    print(f"❌ 预测失败: {len(failed)}/9 场")
    
    if failed:
        print("\n失败比赛:")
        for r in failed:
            print(f"  • {r['match']}: {r.get('error', 'Unknown error')}")
    
    # 按信心分数排序
    successful.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    # 保存详细结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"batch_predict_9_matches_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total": 9,
                "successful": len(successful),
                "failed": len(failed),
                "timestamp": timestamp
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    # 生成微信消息
    weixin_message = generate_weixin_message(successful, failed)
    
    print(f"\n💾 详细结果已保存: {output_file}")
    print(f"📨 微信消息已准备 (共 {len(weixin_message)} 字符)")
    
    # 保存微信消息到文件
    weixin_file = f"weixin_message_{timestamp}.txt"
    with open(weixin_file, "w", encoding="utf-8") as f:
        f.write(weixin_message)
    
    print(f"\n微信消息内容:")
    print("-" * 50)
    print(weixin_message)
    print("-" * 50)
    
    return results, weixin_message, output_file

def generate_weixin_message(successful_results, failed_results):
    """生成微信消息"""
    message = "⚽ 9场比赛批量预测完成\n\n"
    
    message += f"✅ 成功预测: {len(successful_results)}/9 场\n"
    if failed_results:
        message += f"❌ 预测失败: {len(failed_results)} 场\n"
    
    # 按信心分类
    high_conf = [r for r in successful_results if r.get("confidence", 0) >= 55]
    medium_conf = [r for r in successful_results if 40 <= r.get("confidence", 0) < 55]
    low_conf = [r for r in successful_results if r.get("confidence", 0) < 40]
    
    message += f"\n🎯 信心分布:\n"
    message += f"高信心(≥55%): {len(high_conf)} 场\n"
    message += f"中信心(40-55%): {len(medium_conf)} 场\n"
    message += f"低信心(<40%): {len(low_conf)} 场\n"
    
    # Top 3推荐
    if high_conf:
        message += "\n🏆 Top 3高信心推荐:\n"
        for i, r in enumerate(high_conf[:3], 1):
            message += f"{i}. {r['match']}\n"
            message += f"   推荐: {r['market']} {r['recommendation']}\n"
            message += f"   信心: {r['confidence']:.1f}%\n"
            message += f"   ML预测: {r['ml_prediction']} ({r['ml_confidence']:.1f}%)\n\n"
    
    # ML极端预测分析
    ml_extreme = [r for r in successful_results if r.get("ml_confidence", 0) >= 80 and 
                  abs(r.get("home_prob", 0) - (1 - r.get("away_prob", 0))) > 0.3]
    if ml_extreme:
        message += f"\n🤖 ML极端预测 ({len(ml_extreme)} 场):\n"
        for r in ml_extreme[:3]:
            message += f"• {r['match']}: ML预测{r['ml_prediction']}({r['ml_confidence']:.1f}%) "
            message += f"vs 传统概率(主{r['home_prob']*100:.1f}% 客{r['away_prob']*100:.1f}%)\n"
    
    # 辩论触发情况
    debates = [r for r in successful_results if r.get("has_debate")]
    if debates:
        message += f"\n⚖️ 触发辩论: {len(debates)} 场\n"
    
    message += "\n⚠️ 免责声明: 本报告仅供娱乐参考，不构成投注建议"
    
    return message

if __name__ == "__main__":
    results, weixin_message, output_file = main()
    
    print("\n是否发送微信消息？ (y/n): ", end="")