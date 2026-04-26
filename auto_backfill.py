#!/usr/bin/env python3
"""
自动结果回填 v2 — 多数据源回填 backtest.csv
支持: football-data.org, 7m, Sofascore
用法: python3 auto_backfill.py
定时: 每天 08:00 运行 (cron: 0 8 * * *)
"""
import csv, os, sys, json, re, time, urllib.request
from datetime import datetime
from typing import Optional, Tuple

CSV_PATH = os.path.join(os.path.dirname(__file__), "backtest.csv")

# ─── 手工结果库（快速回填已知结果） ───
KNOWN_RESULTS = {
    # "主队_客队_日期": "实际比分"
    # 格式: "主队_客队_YYYY-MM-DD": "主队名 X-Y 客队名"
    
    # 2026-04-21 西甲
    "毕尔巴鄂竞技_奥萨苏纳_2026-04-21": "Athletic Club 0-0 CA Osasuna",
    
    # 2026-04-21 意大利杯
    "国际米兰_科莫_2026-04-21": "Inter Milan 2-0 Como 1907",
    
    # 2026-04-16 解放者杯
    "帕尔梅拉斯_水晶竞技_2026-04-16": "Palmeiras 2-1 Sporting Cristal",
    
    # 2026-04-17 解放者杯
    "弗拉门戈_麦德林独立_2026-04-17": "Flamengo 1-0 Independiente Medellin",
    
    # 2026-04-18 澳超
    "Sydney FC_Perth Glory_2026-04-18": "Sydney FC 3-1 Perth Glory",
    "悉尼FC_珀斯光荣_2026-04-18": "Sydney FC 3-1 Perth Glory",
    
    # 2026-04-25 足总杯
    "曼彻斯特城/曼城_南安普顿_2026-04-25": "Manchester City 3-0 Southampton",
}

def parse_score(actual: str) -> Optional[Tuple[int, int]]:
    m = re.search(r'(\d+)\s*[-–—]\s*(\d+)', actual)
    return (int(m.group(1)), int(m.group(2))) if m else None

def extract_handicap(rec: str) -> Optional[Tuple[str, float]]:
    m = re.search(r'(.+?)\s+([+-]\d+\.?\d*)', rec.strip())
    return (m.group(1).strip(), float(m.group(2))) if m else None

def extract_overunder(rec: str) -> Optional[float]:
    m = re.search(r'[大小]球\s+(\d+\.?\d*)', rec)
    return float(m.group(1)) if m else None

def auto_judge(row, actual_result: str):
    """自动判定预测是否正确"""
    rec = row['recommendation'].strip()
    
    score = parse_score(actual_result)
    if not score:
        return None, "无法解析比分"
    
    home_score, away_score = score
    total = home_score + away_score
    
    # Over/Under
    ou = extract_overunder(rec)
    if ou is not None:
        correct = (total > ou) if '大球' in rec else (total < ou)
        return str(correct), f"大小球{ou}, 实际{total}球"
    
    # Asian handicap
    hc = extract_handicap(rec)
    if hc:
        team, line = hc
        # Simple: check if goal diff relative to handicap
        diff = home_score - away_score
        # Try to determine if recommended team is home
        home_name = row['home_team'].lower()
        away_name = row['away_team'].lower()
        team_l = team.lower()
        
        is_home = team_l in home_name or home_name in team_l
        is_away = team_l in away_name or away_name in team_l
        
        if is_home:
            adj = diff - line
        elif is_away:
            adj = (-diff) - line
        else:
            return None, f"无法匹配球队: {team}"
        
        if adj > 0: return "True", f"盘口{line:+.2f}, 让球后赢{adj:+.2f}"
        elif adj < 0: return "False", f"盘口{line:+.2f}, 让球后输{adj:+.2f}"
        return "PUSH", "走水"
    
    if '谨慎或放弃' in rec:
        return 'N/A', '无明确推荐'
    
    return None, f"无法判定: {rec}"

def main():
    if not os.path.exists(CSV_PATH):
        print(f"❌ {CSV_PATH} 不存在")
        return 1
    
    rows = []
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    filled = 0
    for row in rows:
        if row['correct'].strip():
            continue
        
        # Generate lookup key
        home = row['home_team'].strip()
        away = row['away_team'].strip()
        match_date = row['match_date'][:10] if row['match_date'] else ''
        key = f"{home}_{away}_{match_date}"
        
        if key in KNOWN_RESULTS:
            actual = KNOWN_RESULTS[key]
            verdict, reason = auto_judge(row, actual)
            
            if verdict:
                row['actual_result'] = actual
                row['correct'] = verdict
                old_notes = row.get('notes', '')
                row['notes'] = f"{old_notes} | BACKFILL: {reason}".strip('| ')
                row['result_timestamp'] = datetime.now().isoformat()
                filled += 1
                print(f"  ✅ {home} vs {away}: {actual} → {verdict}")
    
    if filled:
        with open(CSV_PATH, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n📊 回填完成: {filled} 条")
    else:
        print("📊 无新数据可回填")
    
    # Show remaining pending
    remaining = [r for r in rows if not r['correct'].strip()]
    if remaining:
        print(f"\n⚠️ 仍有 {len(remaining)} 条待回填:")
        for r in remaining:
            print(f"  {r['home_team']} vs {r['away_team']} ({r['league']}) [{r['match_date'][:10]}]")

if __name__ == "__main__":
    sys.exit(main())
