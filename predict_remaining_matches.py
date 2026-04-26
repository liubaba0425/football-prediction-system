#!/usr/bin/env python3
"""
批量预测剩余12场比赛
"""
import sys
import os
import json
import subprocess
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from football_predictor import FootballPredictor

def send_wechat_message(message):
    """
    通过hermes chat命令发送消息到微信
    """
    # 转义消息中的单引号
    escaped_message = message.replace("'", "'\\''")
    
    # 构建命令 - 使用安静模式
    cmd = [
        "hermes", "chat", "-Q", "-q",
        f"请使用 send_message 工具发送消息到微信，消息内容是：'{escaped_message}'"
    ]
    
    try:
        # 打印简化日志
        print(f"[微信发送] 正在发送消息到微信...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"[微信发送] 失败，返回码: {result.returncode}")
            if result.stderr:
                print(f"[微信发送] stderr: {result.stderr[:200]}")
        else:
            # 检查输出中是否有成功提示
            if "测试消息已成功发送到微信" in result.stdout or "消息ID：" in result.stdout:
                print(f"[微信发送] 成功 ✓")
            else:
                print(f"[微信发送] 完成，输出: {result.stdout[-300:] if len(result.stdout) > 300 else result.stdout}")
                
    except subprocess.TimeoutExpired:
        print("[微信发送] 命令执行超时（60秒）")
    except Exception as e:
        print(f"[微信发送] 异常: {e}")

def predict_match(home, away, league, match_id):
    """
    预测单场比赛
    """
    print(f"\n{'='*60}")
    print(f"[{match_id}] 预测: {home} vs {away} ({league})")
    print(f"{'='*60}")
    
    try:
        predictor = FootballPredictor()
        result = predictor.predict(home, away, league)
        
        if result.get('success'):
            # 提取关键信息
            home_cn = result.get('home_team_cn', home)
            away_cn = result.get('away_team_cn', away)
            
            # 隐含概率
            implied = result.get('implied_probabilities', {})
            home_prob = implied.get('home', 0)
            draw_prob = implied.get('draw', 0)
            away_prob = implied.get('away', 0)
            
            # 共识推荐
            consensus = result.get('consensus', {})
            recommended_market = consensus.get('recommended_market', '')
            recommendation = consensus.get('recommendation', '')
            confidence = consensus.get('confidence', 0)
            market_value = consensus.get('market_value', 0)
            
            # ML预测
            ml_prediction = result.get('ml_prediction', {})
            ml_result = ml_prediction.get('result', '')
            ml_confidence = ml_prediction.get('confidence', 0)
            
            # 冷门风险
            upset_risk = result.get('upset_risk', 0)
            
            # 构建结果字典
            match_result = {
                'match_id': match_id,
                'home': home_cn,
                'away': away_cn,
                'league': league,
                'implied_probabilities': {
                    'home': home_prob,
                    'draw': draw_prob,
                    'away': away_prob
                },
                'ml_prediction': {
                    'result': ml_result,
                    'confidence': ml_confidence
                },
                'consensus': {
                    'recommended_market': recommended_market,
                    'recommendation': recommendation,
                    'confidence': confidence,
                    'market_value': market_value
                },
                'upset_risk': upset_risk,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            # 发送微信消息
            message = f"✅ 预测完成 [{match_id}]:\n"
            message += f"🏆 {home_cn} vs {away_cn}\n"
            message += f"📊 隐含概率: 主胜{home_prob:.1f}% | 平局{draw_prob:.1f}% | 客胜{away_prob:.1f}%\n"
            if ml_result:
                message += f"🤖 ML预测: {ml_result} ({ml_confidence:.1f}%)\n"
            message += f"🎯 系统推荐: {recommended_market} {recommendation}\n"
            message += f"信心: {confidence:.1f}% | 价值: {market_value}/100\n"
            message += f"⚠️ 冷门风险: {upset_risk}/100"
            
            send_wechat_message(message)
            
            return match_result
            
        else:
            error = result.get('error', '未知错误')
            print(f"❌ 预测失败: {error}")
            
            # 发送失败消息
            message = f"❌ 预测失败 [{match_id}]:\n"
            message += f"🏆 {home} vs {away}\n"
            message += f"错误: {error}"
            send_wechat_message(message)
            
            return {
                'match_id': match_id,
                'home': home,
                'away': away,
                'league': league,
                'success': False,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        print(f"❌ 预测异常: {e}")
        import traceback
        traceback.print_exc()
        
        message = f"❌ 预测异常 [{match_id}]:\n"
        message += f"🏆 {home} vs {away}\n"
        message += f"异常: {str(e)}"
        send_wechat_message(message)
        
        return {
            'match_id': match_id,
            'home': home,
            'away': away,
            'league': league,
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def main():
    # 剩余比赛列表 (home, away, league)
    matches = [
        # 格式: (home, away, league_code)
        ("Everton", "Liverpool", "soccer_epl"),
        ("Verona", "AC Milan", "soccer_italy_serie_a"),
        ("Freiburg", "Heidenheim", "soccer_germany_bundesliga"),
        # 瑞典超 - 需要确认球队英文名
        ("Häcken", "GAIS", "soccer_sweden_allsvenskan"),
        # 挪威超
        ("Sarpsborg", "Tromsø", "soccer_norway_eliteserien"),
        # 法甲
        ("Strasbourg", "Rennes", "soccer_france_ligue_one"),
        # 意乙/意甲 - 比萨 vs 热那亚 (尝试意甲)
        ("Pisa", "Genoa", "soccer_italy_serie_b"),  # 尝试意乙
        # 荷甲
        ("AZ Alkmaar", "NEC Nijmegen", "soccer_netherlands_eredivisie"),
        # 德甲
        ("Mönchengladbach", "Mainz", "soccer_germany_bundesliga"),
        # 意甲
        ("Juventus", "Bologna", "soccer_italy_serie_a"),
        # 葡超
        ("Braga", "Famalicão", "soccer_portugal_primeira_liga"),
        # 美职联
        ("Los Angeles FC", "San Jose Earthquakes", "soccer_usa_mls"),
    ]
    
    print(f"\n{'='*60}")
    print(f"📋 剩余12场比赛批量预测")
    print(f"{'='*60}")
    
    results = []
    
    for i, (home, away, league) in enumerate(matches, 1):
        start_time = time.time()
        
        result = predict_match(home, away, league, i)
        results.append(result)
        
        elapsed = time.time() - start_time
        print(f"⏱️  用时: {elapsed:.1f}s")
        
        # 预测间隔，避免API限制
        if i < len(matches):
            print(f"⏳ 等待3秒...")
            time.sleep(3)
    
    # 汇总统计
    successful = sum(1 for r in results if r.get('success'))
    failed = len(results) - successful
    
    print(f"\n{'='*60}")
    print(f"📊 批量预测完成")
    print(f"✅ 成功: {successful}场")
    print(f"❌ 失败: {failed}场")
    print(f"{'='*60}")
    
    # 保存结果到文件
    output_file = "remaining_matches_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"💾 结果已保存: {output_file}")
    
    # 发送汇总消息
    summary = f"📊 剩余12场比赛预测汇总:\n"
    summary += f"✅ 成功: {successful}场\n"
    summary += f"❌ 失败: {failed}场\n"
    summary += f"⏱️  总用时: {time.time() - start_time:.0f}s\n\n"
    
    for i, result in enumerate(results, 1):
        if result.get('success'):
            summary += f"{i}. ✅ {result['home']} vs {result['away']}\n"
            summary += f"   推荐: {result['consensus']['recommended_market']} {result['consensus']['recommendation']}\n"
            summary += f"   信心: {result['consensus']['confidence']:.1f}%\n"
        else:
            summary += f"{i}. ❌ {result['home']} vs {result['away']}\n"
            summary += f"   错误: {result.get('error', '未知')}\n"
    
    summary += f"\n🤖 ML-Analyst 权重: 正常情况35%/高风险25%"
    summary += f"\n⚠️ 免责: 仅供参考，不构成投资建议"
    
    send_wechat_message(summary)
    
    print("🎉 批量预测流程完成")

if __name__ == "__main__":
    main()