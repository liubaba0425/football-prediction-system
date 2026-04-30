#!/usr/bin/env python3
"""
球队近期状态 & 交锋记录获取器
从本地 football-data.co.uk CSV 数据中提取，零网络开销
"""
import os
import re
import pandas as pd
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# CSV league code → 标准联赛名
CSV_LEAGUE_MAP = {
    'E0': 'Premier League', 'E1': 'Championship', 'E2': 'League One', 'E3': 'League Two',
    'SP1': 'La Liga', 'SP2': 'La Liga 2',
    'D1': 'Bundesliga 1', 'D2': 'Bundesliga 2',
    'I1': 'Serie A', 'I2': 'Serie B',
    'F1': 'Ligue 1', 'F2': 'Ligue 2',
    'N1': 'Eredivisie', 'B1': 'Jupiler Pro League',
    'P1': 'Primeira Liga', 'T1': 'Super Lig', 'G1': 'Super League Greece',
}

# API league key → CSV code
API_LEAGUE_TO_CSV = {
    'soccer_epl': 'E0', 'soccer_efl_champ': 'E1',
    'soccer_spain_la_liga': 'SP1', 'soccer_germany_bundesliga': 'D1',
    'soccer_italy_serie_a': 'I1', 'soccer_france_ligue_one': 'F1',
    'soccer_netherlands_eredivisie': 'N1',
    'soccer_portugal_primeira_liga': 'P1',
    'soccer_belgium_first_div': 'B1',
    'soccer_turkey_super_lig': 'T1',
    'soccer_greece_super_league': 'G1',
    'soccer_efl_league_one': 'E2',
    'soccer_germany_bundesliga2': 'D2',
    'soccer_italy_serie_b': 'I2',
    'soccer_france_ligue_two': 'F2',
    'soccer_spain_segunda_division': 'SP2',
}

# 球队名标准化：去掉 FC/AFC/SC/CF 后缀，统一大小写
def normalize_team(name: str) -> str:
    """标准化队名以便匹配"""
    n = name.strip()
    # 去掉常见后缀
    for suffix in [' FC', ' AFC', ' SC', ' CF', ' United', ' City', ' Town']:
        if n.endswith(suffix):
            n = n[:-len(suffix)]
            break
    return n.lower().strip()

class TeamFormFetcher:
    """从本地历史数据获取球队近期状态和交锋记录"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), 'ml_analyst', 'data', 'odds_raw')
        self.data_dir = data_dir
        self._cache: Dict[str, pd.DataFrame] = {}  # league_code → DataFrame
        
    def _load_league(self, csv_code: str) -> Optional[pd.DataFrame]:
        """加载联赛 CSV 数据（带缓存）"""
        if csv_code in self._cache:
            return self._cache[csv_code]
        
        # 找最新赛季文件
        csv_dir = self.data_dir
        files = sorted([
            f for f in os.listdir(csv_dir) 
            if f.startswith(csv_code) and f.endswith('.csv')
        ], reverse=True)
        
        if not files:
            return None
        
        dfs = []
        for f in files:
            path = os.path.join(csv_dir, f)
            try:
                df = pd.read_csv(path)
                dfs.append(df)
            except Exception:
                continue
        
        if not dfs:
            return None
        
        combined = pd.concat(dfs, ignore_index=True)
        # 标准化日期列
        if 'Date' in combined.columns:
            combined['Date'] = pd.to_datetime(combined['Date'], dayfirst=True, errors='coerce')
        self._cache[csv_code] = combined
        return combined
    
    def _find_csv_code(self, league_api_key: str) -> Optional[str]:
        """API league key → CSV code"""
        return API_LEAGUE_TO_CSV.get(league_api_key)
    
    def _find_team_in_df(self, df: pd.DataFrame, team_name: str) -> str:
        """
        在 DataFrame 中找到匹配的球队名
        返回 DataFrame 中实际使用的队名
        """
        norm_target = normalize_team(team_name)
        
        all_teams = set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())
        
        # 精确匹配（标准化后）
        for t in all_teams:
            if normalize_team(t) == norm_target:
                return t
        
        # 子串匹配
        for t in all_teams:
            if norm_target in normalize_team(t) or normalize_team(t) in norm_target:
                return t
        
        return None
    
    def get_recent_form(self, team_name: str, league_api_key: str, n: int = 5) -> Dict:
        """
        获取球队近期状态（最近 n 场比赛）
        
        Returns:
            {
                "status": "success" | "no_data",
                "matches": [...],  # 最近 n 场比赛
                "form": "W-D-L-W-D",  # 赛果字符串
                "goals_scored": int,
                "goals_conceded": int,
                "wins": int, "draws": int, "losses": int,
                "last_match_date": str,
            }
        """
        csv_code = self._find_csv_code(league_api_key)
        if not csv_code:
            return {"status": "no_data", "message": f"联赛 {league_api_key} 无本地历史数据"}
        
        df = self._load_league(csv_code)
        if df is None:
            return {"status": "no_data", "message": f"未找到联赛 {csv_code} 的数据文件"}
        
        actual_name = self._find_team_in_df(df, team_name)
        if not actual_name:
            return {"status": "no_data", "message": f"在历史数据中未找到球队: {team_name}"}
        
        # 筛选涉及该球队的比赛
        team_matches = df[
            (df['HomeTeam'] == actual_name) | (df['AwayTeam'] == actual_name)
        ].copy()
        
        if team_matches.empty:
            return {"status": "no_data", "message": f"球队 {actual_name} 无比赛记录"}
        
        # 按日期排序，取最近 n 场
        team_matches = team_matches.sort_values('Date', ascending=False).head(n)
        
        matches = []
        wins = draws = losses = 0
        goals_scored = goals_conceded = 0
        
        for _, row in team_matches.iterrows():
            is_home = row['HomeTeam'] == actual_name
            gf = row['FTHG'] if is_home else row['FTAG']
            ga = row['FTAG'] if is_home else row['FTHG']
            result = row['FTR']  # H/D/A
            
            if is_home:
                if result == 'H': 
                    outcome = 'W'
                    wins += 1
                elif result == 'A': 
                    outcome = 'L'
                    losses += 1
                else: 
                    outcome = 'D'
                    draws += 1
            else:
                if result == 'A': 
                    outcome = 'W'
                    wins += 1
                elif result == 'H': 
                    outcome = 'L'
                    losses += 1
                else: 
                    outcome = 'D'
                    draws += 1
            
            goals_scored += gf
            goals_conceded += ga
            
            matches.append({
                "date": str(row['Date'].date()) if pd.notna(row['Date']) else 'N/A',
                "opponent": row['AwayTeam'] if is_home else row['HomeTeam'],
                "venue": "H" if is_home else "A",
                "score": f"{gf}-{ga}",
                "result": outcome,
            })
        
        form_str = '-'.join([m['result'] for m in matches])
        
        return {
            "status": "success",
            "team_name": actual_name,
            "matches_analyzed": len(matches),
            "matches": matches,
            "form": form_str,
            "goals_scored": int(goals_scored),
            "goals_conceded": int(goals_conceded),
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "win_rate": f"{wins/len(matches)*100:.0f}%" if matches else "N/A",
            "last_match_date": matches[0]['date'] if matches else 'N/A',
        }
    
    def get_h2h(self, team1: str, team2: str, league_api_key: str, n: int = 5) -> Dict:
        """
        获取两队交锋记录
        
        Returns:
            {
                "status": "success" | "no_data",
                "matches": [...],
                "summary": "team1胜X场, team2胜Y场, 平Z场",
                "team1_wins": int, "team2_wins": int, "draws": int,
            }
        """
        csv_code = self._find_csv_code(league_api_key)
        if not csv_code:
            return {"status": "no_data", "message": f"联赛 {league_api_key} 无本地历史数据"}
        
        df = self._load_league(csv_code)
        if df is None:
            return {"status": "no_data", "message": f"未找到联赛 {csv_code} 的数据文件"}
        
        name1 = self._find_team_in_df(df, team1)
        name2 = self._find_team_in_df(df, team2)
        
        if not name1 or not name2:
            return {"status": "no_data", 
                    "message": f"未找到 {team1 if not name1 else ''}{' 和 ' if not name1 and not name2 else ''}{team2 if not name2 else ''}"}
        
        h2h = df[
            ((df['HomeTeam'] == name1) & (df['AwayTeam'] == name2)) |
            ((df['HomeTeam'] == name2) & (df['AwayTeam'] == name1))
        ].sort_values('Date', ascending=False).head(n)
        
        if h2h.empty:
            return {"status": "no_data", "message": f"{name1} 与 {name2} 无历史交锋记录"}
        
        matches = []
        t1_wins = t2_wins = draws = 0
        
        for _, row in h2h.iterrows():
            home = row['HomeTeam']
            gf = row['FTHG']
            ga = row['FTAG']
            
            if home == name1:
                if gf > ga:
                    result = f"{name1}胜"
                    t1_wins += 1
                elif gf < ga:
                    result = f"{name2}胜"
                    t2_wins += 1
                else:
                    result = "平"
                    draws += 1
            else:
                if ga > gf:
                    result = f"{name1}胜"
                    t1_wins += 1
                elif ga < gf:
                    result = f"{name2}胜"
                    t2_wins += 1
                else:
                    result = "平"
                    draws += 1
            
            matches.append({
                "date": str(row['Date'].date()) if pd.notna(row['Date']) else 'N/A',
                "home_team": row['HomeTeam'],
                "away_team": row['AwayTeam'],
                "score": f"{gf}-{ga}",
                "result": result,
            })
        
        return {
            "status": "success",
            "team1": name1,
            "team2": name2,
            "matches_analyzed": len(matches),
            "matches": matches,
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "summary": f"{name1}胜{t1_wins}场, {name2}胜{t2_wins}场, 平{draws}场",
        }
    
    def get_match_context(self, home_team: str, away_team: str, league_api_key: str) -> Dict:
        """
        获取比赛综合背景：主队状态 + 客队状态 + 交锋记录
        """
        context = {
            "home_form": self.get_recent_form(home_team, league_api_key),
            "away_form": self.get_recent_form(away_team, league_api_key),
            "h2h": self.get_h2h(home_team, away_team, league_api_key),
        }
        
        # 简单的数据质量标记
        has_data = any(v.get('status') == 'success' for v in context.values())
        context['data_quality'] = 'historical' if has_data else 'unavailable'
        
        return context


# 测试
if __name__ == '__main__':
    fetcher = TeamFormFetcher()
    
    # 测试 Excelsior vs Utrecht (今天预测的荷甲)
    print("=" * 60)
    print("测试: Excelsior vs FC Utrecht (Eredivisie)")
    print("=" * 60)
    
    form_home = fetcher.get_recent_form("Excelsior", "soccer_netherlands_eredivisie")
    print(f"\nExcelsior 近期状态: {form_home}")
    
    form_away = fetcher.get_recent_form("FC Utrecht", "soccer_netherlands_eredivisie")
    print(f"\nFC Utrecht 近期状态: {form_away}")
    
    h2h = fetcher.get_h2h("Excelsior", "FC Utrecht", "soccer_netherlands_eredivisie")
    print(f"\n交锋记录: {h2h}")
