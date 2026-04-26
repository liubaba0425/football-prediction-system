#!/usr/bin/env python3
"""
比赛结果自动爬虫 — 从 football-data.org 抓取赛果并回填 backtest.csv
================================================================================
功能:
  1. 读取 backtest.csv 中所有 pending 预测
  2. 按联赛+日期分组查询 football-data.org API
  3. 中→英队名反向匹配
  4. 自动判定预测是否正确（支持亚盘/大小球结算）
  5. 批量回填到 backtest.csv

使用方法:
  python result_crawler.py                    # 抓取所有 pending 比赛
  python result_crawler.py --dry-run          # 预览模式，不实际写入
  python result_crawler.py --date 2026-04-19  # 只抓取指定日期
  python result_crawler.py --league 英超       # 只抓取指定联赛

API 限流: 10 请求/分钟，脚本会自动等待
"""

import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

from backtest_manager import BacktestManager

# ─── 配置 ──────────────────────────────────────────────────
FD_API_TOKEN = "5ca663e49263467e8664864a767f8c31"
FD_BASE_URL = "https://api.football-data.org/v4"
REQUEST_DELAY = 7.0  # 请求间隔秒数 (10/min = 6s, 留余量 7s)

# ─── 联赛映射: backtest 中文名 → football-data.org competition code ───
LEAGUE_TO_COMPETITION = {
    "英格兰超级联赛": "PL",
    "西班牙甲级联赛": "PD",
    "德国甲级联赛": "BL1",
    "意大利甲级联赛": "SA",
    "法国甲级联赛": "FL1",
    "葡萄牙超级联赛": "PPL",
    "荷兰甲级联赛": "DED",
    "英格兰冠军联赛": "ELC",
    "德国乙级联赛": "BL2",
    "法国乙级联赛": "FL2",
    "瑞典超级联赛": "ALL",          # Allsvenskan — 可能不支持
    "韩国K联赛": "KLE",             # K League — 可能不支持
    "日本J联赛": "JL1",             # J League — 可能不支持
    "沙特阿拉伯职业联赛": "SPL",     # 可能不支持
    "澳大利亚A联赛": "ALE",          # A-League — 可能不支持
    "芬兰超级联赛": "VEI",          # Veikkausliiga — 可能不支持
    "欧洲联赛（欧联杯）": "EL",      # Europa League
    "欧洲协会联赛（欧会杯）": "ECL", # Conference League
    "南美解放者杯": "CLI",            # Copa Libertadores
    "美国职业足球大联盟": "MLS",       # MLS
    "挪威超级联赛": "ELI",            # Eliteserien
    "英格兰足总杯": "FAC",            # FA Cup
    "澳大利亚A联赛": "ALE",           # A-League — 可能不支持
    "soccer_australia_aleague": "ALE", # A-League raw key
    # 意大利杯/法国杯/德国杯
    "意大利杯": "CIT",
    "法国杯": "CDF",
    "德国杯": "DFB",
}

# ─── football-data.org 返回的联赛名 → backtest 联赛名 ───
API_LEAGUE_NAMES = {
    "Premier League": "英格兰超级联赛",
    "Primera Division": "西班牙甲级联赛",
    "Bundesliga": "德国甲级联赛",
    "Serie A": "意大利甲级联赛",
    "Ligue 1": "法国甲级联赛",
    "Primeira Liga": "葡萄牙超级联赛",
    "Eredivisie": "荷兰甲级联赛",
    "Championship": "英格兰冠军联赛",
    "2. Bundesliga": "德国乙级联赛",
    "Ligue 2": "法国乙级联赛",
    "UEFA Europa League": "欧洲联赛（欧联杯）",
    "UEFA Conference League": "欧洲协会联赛（欧会杯）",
    "Coppa Italia": "意大利杯",
    "Coupe de France": "法国杯",
    "DFB-Pokal": "德国杯",
    "Allsvenskan": "瑞典超级联赛",
    "K League 1": "韩国K联赛",
    "J.League": "日本J联赛",
}


def load_team_map() -> Dict[str, str]:
    """
    从 team_translator.py 构建 英文→中文 映射表。
    同时构建反向映射: 中文→英文 (取第一个匹配，即主名称)。
    """
    team_translator_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "team_translator.py"
    )

    # 方法: exec 加载 TEAM_NAME_TRANSLATIONS 字典
    namespace = {}
    with open(team_translator_path, "r", encoding="utf-8") as f:
        exec(f.read(), namespace)

    en_to_cn = namespace.get("TEAM_NAME_TRANSLATIONS", {})

    # 构建反向映射: 每个中文名(可能含 / 分隔的多个别名) → 英文名
    cn_to_en = {}
    for en_name, cn_names in en_to_cn.items():
        for cn_name in cn_names.split("/"):
            cn_name = cn_name.strip()
            if cn_name and cn_name not in cn_to_en:
                cn_to_en[cn_name] = en_name

    return cn_to_en


def chinese_to_english(team_cn: str, cn_to_en: Dict[str, str]) -> str:
    """
    中文队名 → 英文队名。
    策略:
    1. 精确匹配
    2. 子串匹配 (API 返回 "Newcastle United FC" vs 翻译 "Newcastle United")
    3. 原文返回（如果已经是英文）
    """
    # 已经是纯英文/ASCII
    if all(ord(c) < 128 for c in team_cn):
        return team_cn

    # 精确匹配
    if team_cn in cn_to_en:
        return cn_to_en[team_cn]

    # 子串匹配：中文名包含在翻译的某个键中
    for cn_name, en_name in cn_to_en.items():
        if team_cn in cn_name or cn_name in team_cn:
            return en_name

    # 尝试从复合名中提取 (如 "纽卡斯尔/纽卡斯尔联")
    for cn_name, en_name in cn_to_en.items():
        if "/" in cn_name:
            parts = cn_name.split("/")
            if team_cn in [p.strip() for p in parts]:
                return en_name

    return team_cn  # fallback


def api_team_name_matches(api_name: str, expected_en_name: str) -> bool:
    """
    判断 API 返回的队名是否匹配预期的英文队名。
    API 返回格式: "Newcastle United FC", "FC Bayern München"
    我们预期: "Newcastle United", "Bayern Munich"
    """
    api_lower = api_name.lower().replace(" fc", "").replace(" afc", "")
    expected_lower = expected_en_name.lower()

    # 直接包含
    if expected_lower in api_lower or api_lower in expected_lower:
        return True

    # 单词级匹配: 至少 60% 的单词重合
    api_words = set(api_lower.replace(".", " ").split())
    exp_words = set(expected_lower.replace(".", " ").split())
    if api_words and exp_words:
        overlap = len(api_words & exp_words)
        if overlap >= max(1, len(exp_words) * 0.6):
            return True

    return False


def get_competition_code(league_cn: str) -> Optional[str]:
    """获取 football-data.org 的 competition code"""
    # 先查硬编码映射
    code = LEAGUE_TO_COMPETITION.get(league_cn)
    if code:
        return code

    # 尝试模糊匹配
    for key, code in LEAGUE_TO_COMPETITION.items():
        if key in league_cn or league_cn in key:
            return code

    return None


def fetch_finished_matches(
    competition_code: str, date_from: str, date_to: str
) -> List[Dict]:
    """
    从 football-data.org 获取指定联赛+日期范围的已完成比赛。

    Returns:
        [{id, utcDate, homeTeam.name, awayTeam.name, score.fullTime}, ...]
    """
    url = (
        f"{FD_BASE_URL}/competitions/{competition_code}/matches"
        f"?status=FINISHED"
        f"&dateFrom={date_from}"
        f"&dateTo={date_to}"
    )

    headers = {"X-Auth-Token": FD_API_TOKEN}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        remaining = resp.headers.get("X-Requests-Available-Minute", "?")
        print(f"     API: {competition_code} {date_from}~{date_to} "
              f"→ {resp.status_code} (剩余{remaining}次/分钟)")

        if resp.status_code == 200:
            data = resp.json()
            return data.get("matches", [])

        elif resp.status_code == 429:
            print("     ⚠️ 触发限流，等待 60 秒...")
            time.sleep(60)
            return fetch_finished_matches(competition_code, date_from, date_to)

        else:
            print(f"     ⚠️ API 错误: {resp.status_code} {resp.text[:100]}")
            return []

    except requests.RequestException as e:
        print(f"     ❌ 网络错误: {e}")
        return []


def settle_asian_handicap(
    recommendation: str, home_goals: int, away_goals: int
) -> Tuple[Optional[bool], str]:
    """
    结算亚盘推荐。

    Args:
        recommendation: 如 "Juventus -1.25", "AIK -0.75", "Newcastle United +1.25"
        home_goals, away_goals: 实际比分

    Returns:
        (correct, detail) — correct 为 None 表示无法判定
    """
    # 解析推荐: "TeamName [+-]X.XX"
    match = re.match(
        r"(.+?)\s+([+-]?\d+\.?\d*)", recommendation.strip()
    )
    if not match:
        return None, f"无法解析推荐格式: {recommendation}"

    team_name = match.group(1).strip()
    try:
        handicap = float(match.group(2))
    except ValueError:
        return None, f"无法解析盘口: {match.group(2)}"

    # 盘口方向: 正=受让, 负=让球
    # 结算: 实际分差 = 推荐方进球 - 对手进球, 然后加上盘口
    # 这里简化: 只判定输赢方向（不处理 half-win/half-loss）

    # 判断推荐方是主队还是客队
    # 我们无法从推荐文本中直接知道主客，但可以推断:
    # - 如果 recommendation 中球队名是主队 → 让球方是主队
    # 这里用简单的启发式: 看 home_goals/away_goals 的差值方向

    # 简化处理: 假定推荐文本中的球队名就是被推荐的球队
    # 实际分差: goals_for - goals_against
    # 但我们不知道哪个是 goals_for...

    # 更实用的方法: 让调用方传入主客标记
    # 这里返回需要外部判断的结果
    return None, f"亚盘结算需要主客标记: {recommendation}"


def settle_over_under(
    recommendation: str, home_goals: int, away_goals: int
) -> Tuple[Optional[bool], str]:
    """
    结算大小球推荐。

    Args:
        recommendation: 如 "大球 2.5球", "小球 3.0球", "均衡 2.5球"
        home_goals, away_goals: 实际比分

    Returns:
        (correct, detail)
    """
    total_goals = home_goals + away_goals

    # 解析
    if "大球" in recommendation or "Over" in recommendation.lower():
        direction = "over"
    elif "小球" in recommendation or "Under" in recommendation.lower():
        direction = "under"
    else:
        return None, f"无法判定方向: {recommendation}"

    line_match = re.search(r"(\d+\.?\d*)", recommendation)
    if not line_match:
        return None, f"无法解析盘口线: {recommendation}"

    line = float(line_match.group(1))

    # 结算逻辑
    if abs(total_goals - line) < 0.01:
        # 正好等于线 → 走水 (push)
        return None, f"走水: 总进球{total_goals} = 盘口{line}"

    if direction == "over":
        correct = total_goals > line
    else:
        correct = total_goals < line

    detail = f"大球" if direction == "over" else f"小球"
    detail += f" {line}球, 实际{total_goals}球 → {'✅' if correct else '❌'}"

    return correct, detail


def auto_settle_prediction(
    pred: Dict, match_data: Dict, cn_to_en: Dict[str, str]
) -> Tuple[Optional[bool], str]:
    """
    自动判定一条预测是否正确。

    Args:
        pred: backtest.csv 中的一行
        match_data: football-data.org 返回的比赛数据
        cn_to_en: 中文→英文队名映射

    Returns:
        (correct, detail_message)
    """
    score = match_data.get("score", {}).get("fullTime", {})
    home_goals = score.get("home")
    away_goals = score.get("away")

    if home_goals is None or away_goals is None:
        return None, "比分数据缺失"

    recommendation = pred.get("recommendation", "")
    market = pred.get("recommended_market", "")
    home_team_cn = pred.get("home_team", "")
    away_team_cn = pred.get("away_team", "")

    # 无法结算的情况
    if recommendation in ("谨慎或放弃", "数据不足", ""):
        return None, f"无推荐内容: {recommendation}"

    if market == "跳过":
        return None, f"市场跳过"

    # 大小球结算
    if market == "大小球" or "大球" in recommendation or "小球" in recommendation:
        correct, detail = settle_over_under(recommendation, home_goals, away_goals)
        return correct, detail

    # 让球盘结算
    if market == "让球盘":
        correct, detail = settle_asian_handicap_auto(
            recommendation, home_team_cn, away_team_cn,
            home_goals, away_goals, cn_to_en
        )
        return correct, detail

    # fallback: 简单的胜平负方向判定
    home_en = chinese_to_english(home_team_cn, cn_to_en)
    away_en = chinese_to_english(away_team_cn, cn_to_en)

    if home_goals > away_goals:
        outcome = "主胜"
    elif home_goals < away_goals:
        outcome = "客胜"
    else:
        outcome = "平局"

    return None, f"简单比分: {home_en} {home_goals}-{away_goals} {away_en} ({outcome})"


def settle_asian_handicap_auto(
    recommendation: str,
    home_team_cn: str,
    away_team_cn: str,
    home_goals: int,
    away_goals: int,
    cn_to_en: Dict[str, str],
) -> Tuple[Optional[bool], str]:
    """
    自动结算亚盘推荐。

    从推荐文本中解析出被推荐的球队和盘口，然后结算。
    """
    # 解析: "Juventus -1.25" 或 "AIK +0.00"
    match = re.match(r"(.+?)\s+([+-]?\d+\.?\d*)", recommendation.strip())
    if not match:
        return None, f"亚盘格式无法解析: {recommendation}"

    rec_team_raw = match.group(1).strip()
    try:
        handicap = float(match.group(2))
    except ValueError:
        return None, f"盘口数值无法解析: {match.group(2)}"

    # 判断推荐球队是主队还是客队
    # 用中文名匹配
    rec_team_cn = rec_team_raw
    # 如果推荐文本是英文，尝试翻译
    if all(ord(c) < 128 for c in rec_team_raw):
        rec_team_cn = rec_team_raw  # 保持原样

    # 判断被推荐的是主队还是客队
    home_en = chinese_to_english(home_team_cn, cn_to_en)
    away_en = chinese_to_english(away_team_cn, cn_to_en)

    # 匹配推荐球队
    is_home = (
        rec_team_raw.lower() in home_team_cn.lower()
        or home_team_cn.lower() in rec_team_raw.lower()
        or rec_team_raw.lower() in home_en.lower()
        or home_en.lower() in rec_team_raw.lower()
    )
    is_away = (
        rec_team_raw.lower() in away_team_cn.lower()
        or away_team_cn.lower() in rec_team_raw.lower()
        or rec_team_raw.lower() in away_en.lower()
        or away_en.lower() in rec_team_raw.lower()
    )

    if is_home and is_away:
        # 都匹配 → 模糊
        return None, f"球队名同时匹配主客队: {rec_team_raw}"

    if not is_home and not is_away:
        return None, f"推荐球队无法匹配: {rec_team_raw}"

    # 计算让球后的比分
    if is_home:
        adjusted_home = home_goals + handicap
        adjusted_away = away_goals
        team_label = home_team_cn
    else:
        adjusted_home = home_goals
        adjusted_away = away_goals + handicap
        team_label = away_team_cn

    # 判定胜负
    if abs(adjusted_home - adjusted_away) < 0.01:
        # 正好平局 → 走水
        return None, f"走水: {team_label} {handicap:+.2f}, 比分{home_goals}-{away_goals} → 平局"

    if is_home:
        correct = adjusted_home > adjusted_away
    else:
        correct = adjusted_away > adjusted_home

    detail = (
        f"{team_label} {handicap:+.2f}, "
        f"比分{home_goals}-{away_goals} "
        f"→ {'赢盘✅' if correct else '输盘❌'}"
    )

    return correct, detail


def crawl_and_fill(
    dry_run: bool = False,
    target_date: str = None,
    target_league: str = None,
) -> Dict:
    """
    主流程: 爬取所有 pending 预测的赛果并回填。
    """
    bm = BacktestManager()
    pending = bm.get_pending_predictions()

    if not pending:
        print("✅ 没有待回填的预测")
        return {"filled": 0, "skipped": 0, "errors": 0}

    # 过滤
    if target_date:
        pending = [p for p in pending if target_date in p.get("match_date", "")]
    if target_league:
        pending = [p for p in pending if target_league in p.get("league", "")]

    if not pending:
        print("✅ 过滤后没有待回填的预测")
        return {"filled": 0, "skipped": 0, "errors": 0}

    print(f"📋 {len(pending)} 条待回填预测")

    # 加载队名映射
    cn_to_en = load_team_map()
    print(f"📖 加载 {len(cn_to_en)} 条中→英队名映射")

    # 按 (联赛, 日期) 分组，减少 API 调用
    groups = defaultdict(list)
    for pred in pending:
        league = pred.get("league", "")
        match_date = pred.get("match_date", "")[:10]  # YYYY-MM-DD
        if league and match_date:
            key = (league, match_date)
            groups[key].append(pred)

    print(f"📦 分组: {len(groups)} 个 (联赛,日期) 组合")
    print(f"⏱️  预计 {len(groups) * REQUEST_DELAY / 60:.1f} 分钟完成 (速率限制)\n")

    filled = 0
    skipped = 0
    errors = 0
    api_calls = 0

    for i, ((league, date_str), preds) in enumerate(sorted(groups.items())):
        comp_code = get_competition_code(league)

        if not comp_code:
            print(f"  [{i+1}/{len(groups)}] ⚠️ {league} — 无 competition code 映射，跳过 {len(preds)} 条")
            skipped += len(preds)
            continue

        # API 限流等待
        if api_calls > 0:
            time.sleep(REQUEST_DELAY)

        # 日期范围: 前后各 1 天 (处理时区偏差)
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            date_from = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
            date_to = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            date_from = date_str
            date_to = date_str

        # 获取比赛数据
        matches = fetch_finished_matches(comp_code, date_from, date_to)
        api_calls += 1

        print(f"  [{i+1}/{len(groups)}] {league} {date_str} → {len(matches)} 场比赛中")

        # 匹配每条预测
        for pred in preds:
            pid = pred.get("prediction_id", "?")
            home_cn = pred.get("home_team", "")
            away_cn = pred.get("away_team", "")

            # 找出匹配的比赛
            home_en = chinese_to_english(home_cn, cn_to_en)
            away_en = chinese_to_english(away_cn, cn_to_en)

            matched = None
            for m in matches:
                api_home = m.get("homeTeam", {}).get("name", "")
                api_away = m.get("awayTeam", {}).get("name", "")

                home_ok = api_team_name_matches(api_home, home_en)
                away_ok = api_team_name_matches(api_away, away_en)

                if home_ok and away_ok:
                    # 双重确认: 日期也要在合理范围内
                    api_date = m.get("utcDate", "")[:10]
                    if api_date == date_str or abs(
                        (datetime.strptime(api_date, "%Y-%m-%d")
                         - datetime.strptime(date_str, "%Y-%m-%d")).days
                    ) <= 1:
                        matched = m
                        break

            if not matched:
                print(f"    ⚠️ {home_cn} vs {away_cn}: 未找到赛果")
                skipped += 1
                continue

            # 自动结算
            correct, detail = auto_settle_prediction(pred, matched, cn_to_en)

            # 构建实际结果描述
            score = matched.get("score", {}).get("fullTime", {})
            hg = score.get("home", "?")
            ag = score.get("away", "?")
            api_home = matched.get("homeTeam", {}).get("name", home_cn)
            api_away = matched.get("awayTeam", {}).get("name", away_cn)
            actual_result = f"{api_home} {hg}-{ag} {api_away}"

            if correct is None:
                # 无法自动判定: 记录比分但标记为需要人工确认
                if dry_run:
                    print(f"    🤔 {home_cn} vs {away_cn}: {actual_result} — 需人工判定 ({detail})")
                else:
                    bm.update_result(pid, actual_result, "", f"需人工判定: {detail}")
                skipped += 1
            else:
                status = "✅" if correct else "❌"
                if dry_run:
                    print(f"    {status} {home_cn} vs {away_cn}: {detail}")
                else:
                    bm.update_result(pid, actual_result, correct, detail)
                filled += 1

    # 汇总
    print(f"\n{'='*55}")
    print(f"📊 完成: 自动回填 {filled} 条 | 需人工 {skipped} 条 | 总计 {len(pending)} 条")
    if dry_run:
        print(f"   (dry-run 模式，未实际写入)")

    # 打印更新后的统计
    if not dry_run and filled > 0:
        bm.print_stats()

    return {"filled": filled, "skipped": skipped, "errors": errors}


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="比赛结果自动爬虫 — 从 football-data.org 抓取赛果并回填 backtest.csv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python result_crawler.py                      # 抓取所有 pending
  python result_crawler.py --dry-run             # 预览，不写入
  python result_crawler.py --date 2026-04-19     # 只抓指定日期
  python result_crawler.py --league 英超         # 只抓指定联赛
  python result_crawler.py --dry-run --date 2026-04-25  # 预览指定日期
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入 backtest.csv")
    parser.add_argument("--date", type=str, help="只抓取指定日期 (YYYY-MM-DD)")
    parser.add_argument("--league", type=str, help="只抓取指定联赛 (中文名)")

    args = parser.parse_args()

    crawl_and_fill(
        dry_run=args.dry_run,
        target_date=args.date,
        target_league=args.league,
    )


if __name__ == "__main__":
    main()
