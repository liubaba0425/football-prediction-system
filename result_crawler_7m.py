#!/usr/bin/env python3
"""
7m比分网结果爬虫 v3 — 三重匹配：联赛 + 时间 + 队名字符校验
"""

import csv, os, re, ssl, time, urllib.request
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from backtest_manager import BacktestManager


# ─── 联赛映射 ───
LEAGUE_MAP_7M = {
    '英超': '英格兰超级联赛', '英冠': '英格兰冠军联赛', '英足總盃': '英格兰足总杯',
    '西甲': '西班牙甲级联赛', '意甲': '意大利甲级联赛', '意盃': '意大利杯',
    '德甲': '德国甲级联赛', '德乙': '德国乙级联赛', '德國盃': '德国杯',
    '法甲': '法国甲级联赛', '法乙': '法国乙级联赛', '法國盃': '法国杯',
    '荷甲': '荷兰甲级联赛', '葡超': '葡萄牙超级联赛',
    '瑞典超': '瑞典超级联赛', '挪超': '挪威超级联赛', '芬超': '芬兰超级联赛',
    '日聯': '日本J联赛', 'K1聯賽': '韩国K联赛',
    '沙地超': '沙特阿拉伯职业联赛', '澳超': '澳大利亚A联赛',
    '美職聯': '美国职业足球大联盟',
    '歐霸盃': '欧洲联赛（欧联杯）', '歐會盃': '欧洲协会联赛（欧会杯）',
    '解放者盃': '南美解放者杯', 'soccer_australia_aleague': '澳大利亚A联赛',
}

# ─── 繁→简映射 ───
_T2S_DICT = {
    '門':'门','蘭':'兰','聯':'联','爾':'尔','亞':'亚','維':'维','羅':'罗','馬':'马',
    '納':'纳','薩':'萨','萊':'莱','錫':'锡','畢':'毕','賓':'宾','費':'费','貝':'贝',
    '盧':'卢','聖':'圣','漢':'汉','諾':'诺','倫':'伦','遜':'逊','達':'达','邁':'迈',
    '紐':'纽','約':'约','華':'华','頓':'顿','澤':'泽','鄧':'邓','隊':'队','競':'竞',
    '體':'体','會':'会','國':'国','際':'际','電':'电','話':'话','員':'员','蘇':'苏',
    '喬':'乔','治':'治','歷':'历','崙':'仑','魯':'鲁','茲':'兹','麗':'丽','岡':'冈',
    '廣':'广','島':'岛','東':'东','樂':'乐','歐':'欧','醫':'医','護':'护','韋':'韦',
    '寶':'宝','龍':'龙','龜':'龟','齊':'齐','齒':'齿','魚':'鱼','鯨':'鲸','鷗':'鸥',
    '鷹':'鹰','獅':'狮','狼':'狼','狐':'狐','慕':'慕','格':'格','雷':'雷','布':'布',
    '斯':'斯','恩':'恩','堡':'堡','克':'克','拉':'拉','福':'福','姆':'姆','海':'海',
    '登':'登','咸':'咸','辛':'辛','提':'提','尼':'尼','茨':'茨','柏':'柏','林':'林',
    '迪':'迪','那':'那','卡':'卡','路':'路','易':'易','噴':'喷','射':'射','機':'机',
    '岸':'岸','水':'水','手':'手','流':'流','浪':'浪','者':'者','墨':'墨','勝':'胜',
    '飛':'飞','腳':'脚','釜':'釜','山':'山','尚':'尚','武':'武','原':'原','項':'项',
    '製':'制','鐵':'铁','穀':'谷','鳥':'鸟','棲':'栖','產':'产','業':'业','運':'运',
    '動':'动','瑪':'玛','絲':'丝','積':'积','極':'极','種':'种','類':'类','團':'团',
    '雲':'云','查':'查','加':'加','史':'史','特':'特','遜':'逊','多':'多','拿':'拿',
    '維':'维','黃':'黄','蜂':'蜂','川':'川','崎':'崎','鹿':'鹿','角':'角','鋼':'钢',
    '巴':'巴','太':'太','陽':'阳','神':'神','鯨':'鲸',
}
def t2s(text: str) -> str:
    return ''.join(_T2S_DICT.get(c, c) for c in text)


def char_overlap(name1: str, name2: str) -> float:
    """计算两个队名的中文字符重合度"""
    c1 = set(c for c in name1 if '\u4e00' <= c <= '\u9fff')
    c2 = set(c for c in name2 if '\u4e00' <= c <= '\u9fff')
    if not c1 or not c2:
        w1 = set(name1.lower().split()); w2 = set(name2.lower().split())
        if not w1 or not w2: return 0.0
        o = len(w1 & w2)
        return o / min(len(w1), len(w2)) if min(len(w1), len(w2)) > 0 else 0.0
    o = len(c1 & c2)
    return o / min(len(c1), len(c2))


def fetch_7m_data(date_str: str) -> Optional[Dict]:
    url = f"https://data.7m.com.cn/result_data/{date_str}/index_big.js"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.7m.com.cn/"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        js_data = resp.read().decode('utf-8', errors='ignore')
    except: return None
    
    def ps(vn):
        p = re.search(rf"var {vn}\s*=\s*(\[.*?\]);", js_data, re.DOTALL)
        return re.findall(r"'([^']*)'", p.group(1)) if p else []
    def pi(vn):
        p = re.search(rf"var {vn}\s*=\s*(\[.*?\]);", js_data, re.DOTALL)
        return [int(n) for n in re.findall(r'(-?\d+)', p.group(1))] if p else []
    
    ta=ps('Team_A_Arr'); tb=ps('Team_B_Arr'); lg=ps('Match_name_Arr')
    hg=pi('live_a_Arr'); ag=pi('live_b_Arr'); st=ps('Start_time_Arr')
    if not ta: return None
    
    matches = []
    for i in range(len(ta)):
        if i>=len(hg) or i>=len(ag): continue
        parts=st[i].split(',')
        if len(parts)<5: continue
        try:
            t=datetime(int(parts[0]),int(parts[1]),int(parts[2]),
                      int(parts[3]),int(parts[4]),tzinfo=timezone(timedelta(hours=8)))
        except: continue
        matches.append({
            'league_7m':lg[i], 'league_bt':LEAGUE_MAP_7M.get(lg[i],lg[i]),
            'home':ta[i], 'home_s':t2s(ta[i]),
            'away':tb[i], 'away_s':t2s(tb[i]),
            'home_goals':hg[i], 'away_goals':ag[i], 'time':t,
        })
    return {'matches':matches, 'total':len(ta)}


def settle(pred, match):
    hg,ag=match['home_goals'],match['away_goals']
    rec=pred.get('recommendation',''); mkt=pred.get('recommended_market','')
    if rec in ('谨慎或放弃','数据不足','','两个市场均可考虑'): return None,'无推荐'
    # 大小球
    if mkt=='大小球' or '大球' in rec or '小球' in rec:
        total=hg+ag; d='over' if '大球' in rec else 'under'
        lm=re.search(r'(\d+\.?\d*)',rec)
        if lm:
            line=float(lm.group(1))
            if abs(total-line)<0.01: return None,f'走水:{total}={line}'
            c=total>line if d=='over' else total<line
            return c,f"{'大球' if d=='over' else '小球'} {line}, 实际{total}球 → {'✅' if c else '❌'}"
        return None,'无法解析线'
    # 让球盘
    if mkt=='让球盘':
        rm=re.match(r'(.+?)\s+([+-]?\d+\.?\d*)',rec.strip())
        if not rm: return None,'无法解析'
        rt=rm.group(1).strip()
        try: hc=float(rm.group(2))
        except: return None,'盘口错误'
        hc_t=pred.get('home_team',''); aw_cn=pred.get('away_team','')
        ih=rt.lower() in hc_t.lower() or hc_t.lower() in rt.lower()
        ia=rt.lower() in aw_cn.lower() or aw_cn.lower() in rt.lower()
        if ih and not ia: adj=hg+hc-ag; tl=hc_t
        elif ia and not ih: adj=ag+hc-hg; tl=aw_cn
        else: return None,'球队模糊'
        if abs(adj)<0.01: return None,f'走水:{tl} {hc:+.2f}, {hg}-{ag}'
        c=adj>0
        return c,f'{tl} {hc:+.2f}, {hg}-{ag} → {"赢盘✅" if c else "输盘❌"}'
    return None,'未知市场'


def find_best_match(pred, all_matches):
    mds=pred.get('match_date',''); league=pred.get('league','')
    home=pred.get('home_team',''); away=pred.get('away_team','')
    try:
        if 'Z' in mds: pt=datetime.fromisoformat(mds.replace('Z','+00:00'))
        else: pt=datetime.fromisoformat(mds)
        if pt.tzinfo is None: pt=pt.replace(tzinfo=timezone.utc)
    except: return None
    
    home_s=t2s(home); away_s=t2s(away)
    candidates=[]
    for m in all_matches:
        ml=m['league_bt']
        if league and ml:
            if not (league in ml or ml in league or m['league_7m'] in league): continue
        td=abs((pt-m['time']).total_seconds())
        if td>2700: continue
        hs=max(char_overlap(home_s,m['home_s']),char_overlap(home_s,m['away_s']))
        aws=max(char_overlap(away_s,m['away_s']),char_overlap(away_s,m['home_s']))
        avg=(hs+aws)/2
        candidates.append((avg,td,m))
    
    if not candidates: return None
    candidates.sort(key=lambda x:(-x[0],x[1]))
    best=candidates[0]
    if best[0]<0.35: return None
    return best[2]


def crawl_7m_and_fill(dry_run=False):
    bm=BacktestManager()
    pending=bm.get_pending_predictions()
    if not pending: print("✅ 无待回填"); return {"filled":0,"skipped":0}
    
    dg=defaultdict(list)
    for p in pending:
        md=p.get('match_date','')[:10]
        if md: dg[md].append(p)
    
    print(f"📋 {len(pending)} 条待回填，{len(dg)} 个日期\n")
    filled=skipped=0
    
    for ds,preds in sorted(dg.items()):
        print(f"\n📅 {ds}: {len(preds)} 条")
        results=fetch_7m_data(ds)
        if not results: print("  ⚠️ 无数据"); skipped+=len(preds); continue
        
        for pred in preds:
            pid=pred.get('prediction_id','?')
            matched=find_best_match(pred,results['matches'])
            if not matched:
                print(f"    ⚠️ {pred['home_team']} vs {pred['away_team']} ({pred['league']}): 未匹配")
                skipped+=1; continue
            
            hg,ag=matched['home_goals'],matched['away_goals']
            actual=f"{matched['home']} {hg}-{ag} {matched['away']}"
            correct,detail=settle(pred,matched)
            
            if correct is None:
                s="🤔"
                if not dry_run: bm.update_result(pid,actual,"",f"需人工判定: {detail}")
                skipped+=1
            else:
                s="✅" if correct else "❌"
                if not dry_run: bm.update_result(pid,actual,correct,detail)
                filled+=1
            print(f"    {s} {pred['home_team']} vs {pred['away_team']}: {detail if correct is not None else '需人工: '+detail}")
    
    print(f"\n{'='*55}")
    print(f"📊 完成: 自动回填 {filled} 条 | 需人工 {skipped} 条 | 总计 {len(pending)} 条")
    if not dry_run and filled>0: bm.print_stats()
    return {"filled":filled,"skipped":skipped}


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--dry-run",action="store_true")
    a=p.parse_args(); crawl_7m_and_fill(dry_run=a.dry_run)
