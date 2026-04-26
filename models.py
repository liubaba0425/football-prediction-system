"""
数据模型定义
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLevel(Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class MarketType(Enum):
    ASIAN_HANDICAP = "让球盘"
    OVER_UNDER = "大小球"
    MATCH_WINNER = "胜平负"


@dataclass
class Team:
    name: str
    key: str
    recent_form: List[str] = field(default_factory=list)  # W, D, L
    goals_scored: int = 0
    goals_conceded: int = 0
    ranking: Optional[int] = None


@dataclass
class Match:
    id: str
    home_team: Team
    away_team: Team
    league: str
    commence_time: datetime
    status: str = "upcoming"


@dataclass
class BookmakerOdds:
    bookmaker: str
    market_type: str
    outcomes: Dict[str, float]  # outcome_name -> price
    point: Optional[float] = None  # for handicap/over_under


@dataclass
class MarketAnalysis:
    market_type: str
    bookmaker_count: int
    mainstream_count: int
    average_odds: float
    market_consistency: str  # 高/中/低
    value_score: float
    recommended_outcome: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentReport:
    agent_name: str
    agent_type: str
    analysis: Dict[str, Any]
    confidence: float
    risk_level: RiskLevel
    recommendation: str
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConsensusReport:
    match: Match
    agent_reports: List[AgentReport]
    weighted_score: float
    consensus_recommendation: str
    confidence: float
    risk_level: RiskLevel
    asian_analysis: MarketAnalysis
    over_under_analysis: MarketAnalysis
    recommended_market: str
    final_suggestion: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PredictionOutput:
    """标准化输出格式"""
    match_info: Dict[str, str]
    market_analysis: Dict[str, Any]
    value_assessment: Dict[str, Any]
    final_recommendation: Dict[str, Any]
