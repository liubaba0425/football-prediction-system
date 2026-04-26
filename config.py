"""
足球预测智能体系统 - 配置文件
"""
import os
from pathlib import Path

# API配置
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "c7af0126df9eb35c363065dcea447d8d")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# 支持的足球联赛
SUPPORTED_LEAGUES = {
    "soccer_epl": "英超",
    "soccer_spain_la_liga": "西甲",
    "soccer_germany_bundesliga": "德甲",
    "soccer_italy_serie_a": "意甲",
    "soccer_france_ligue_one": "法甲",
    "soccer_uefa_champs_league": "欧冠",
    "soccer_uefa_europa_league": "欧联",
    "soccer_china_super_league": "中超",
    "soccer_korea_kleague1": "K联赛",
    "soccer_japan_j_league": "J联赛",
    "soccer_germany_bundesliga2": "德乙",
    "soccer_efl_champ": "英冠",
    "soccer_sweden_allsvenskan": "瑞典超",
    "soccer_norway_eliteserien": "挪威超",
    "soccer_netherlands_eredivisie": "荷甲",
    "soccer_portugal_primeira_liga": "葡超",
    "soccer_usa_mls": "美职联",
    "soccer_italy_serie_b": "意乙",
}

# 智能体权重配置
AGENT_WEIGHTS = {
    "stats_analyst": 0.40,
    "tactics_analyst": 0.25,
    "sentiment_analyst": 0.20,
    "upset_detector": 0.15,
}

# 冷门风险阈值
UPSET_RISK_THRESHOLD = 60

# 工作空间路径
WORKSPACE_DIR = Path.home() / "openclaw-workspace"
LOGS_DIR = WORKSPACE_DIR / "logs"

# 确保目录存在
LOGS_DIR.mkdir(exist_ok=True)

# 分析配置
ANALYSIS_CONFIG = {
    "recent_matches_count": 5,
    "value_score_threshold": 60,
    "confidence_levels": {
        "high": 75,
        "medium": 50,
        "low": 25,
    }
}
