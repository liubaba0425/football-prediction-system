"""
📊 Stats-Analyst - 统计数据分析师
分析球队统计数据、排名、近期状态
"""
from typing import Dict, Any, List
from datetime import datetime
from models import AgentReport, RiskLevel, Match, BookmakerOdds


class StatsAnalyst:
    """统计数据分析师"""

    def __init__(self):
        self.name = "Stats-Analyst"
        self.agent_type = "统计分析"
        self.weight = 0.40

    def analyze(self, match: Match, odds_data: List[BookmakerOdds]) -> AgentReport:
        """
        执行统计分析

        分析维度：
        1. 隐含概率计算
        2. 赔率分布分析
        3. 市场一致性评估
        4. 主客场优劣势
        """
        # 收集H2H赔率数据
        h2h_odds = [o for o in odds_data if o.market_type == "h2h"]

        if not h2h_odds:
            return self._create_insufficient_data_report(match)

        # 计算平均隐含概率
        home_probs = []
        draw_probs = []
        away_probs = []

        for odds in h2h_odds:
            outcomes = odds.outcomes
            total_implied = sum(1/v for v in outcomes.values() if v > 0)

            for name, price in outcomes.items():
                implied = (1/price) / total_implied if price > 0 else 0
                if match.home_team.name in name:
                    home_probs.append(implied)
                elif match.away_team.name in name:
                    away_probs.append(implied)
                else:
                    draw_probs.append(implied)

        avg_home_prob = sum(home_probs) / len(home_probs) if home_probs else 0
        avg_draw_prob = sum(draw_probs) / len(draw_probs) if draw_probs else 0
        avg_away_prob = sum(away_probs) / len(away_probs) if away_probs else 0

        # 确定推荐
        prob_dict = {
            "主胜": avg_home_prob,
            "平局": avg_draw_prob,
            "客胜": avg_away_prob
        }
        recommendation = max(prob_dict, key=prob_dict.get)
        max_prob = prob_dict[recommendation]

        # 评估信心水平
        confidence = max_prob * 100
        risk_level = self._assess_risk_level(confidence, prob_dict)

        # 市场一致性
        consistency = self._calculate_consistency(home_probs, draw_probs, away_probs)

        analysis = {
            "隐含概率": {
                "主胜": f"{avg_home_prob:.1%}",
                "平局": f"{avg_draw_prob:.1%}",
                "客胜": f"{avg_away_prob:.1%}"
            },
            "数据源数量": len(h2h_odds),
            "市场一致性": consistency,
            "主客场分析": {
                "主场优势": "明显" if avg_home_prob > avg_away_prob + 0.1 else "一般",
                "客队实力": "较强" if avg_away_prob > avg_home_prob else "一般"
            }
        }

        reasoning = (
            f"基于{len(h2h_odds)}家博彩公司数据分析，"
            f"主队胜率{avg_home_prob:.1%}，"
            f"平局概率{avg_draw_prob:.1%}，"
            f"客队胜率{avg_away_prob:.1%}。"
            f"市场一致性{consistency}。"
        )

        return AgentReport(
            agent_name=self.name,
            agent_type=self.agent_type,
            analysis=analysis,
            confidence=confidence,
            risk_level=risk_level,
            recommendation=recommendation,
            reasoning=reasoning
        )

    def _assess_risk_level(self, confidence: float, prob_dict: Dict) -> RiskLevel:
        """评估风险等级"""
        probs = list(prob_dict.values())
        sorted_probs = sorted(probs, reverse=True)

        # 如果前两个概率差距小，风险较高
        if sorted_probs[0] - sorted_probs[1] < 0.1:
            return RiskLevel.HIGH
        elif confidence > 60:
            return RiskLevel.LOW
        else:
            return RiskLevel.MEDIUM

    def _calculate_consistency(self, home: List, draw: List, away: List) -> str:
        """计算市场一致性"""
        if not home or not draw or not away:
            return "数据不足"

        home_std = (max(home) - min(home)) / len(home) if len(home) > 1 else 0
        draw_std = (max(draw) - min(draw)) / len(draw) if len(draw) > 1 else 0
        away_std = (max(away) - min(away)) / len(away) if len(away) > 1 else 0

        avg_std = (home_std + draw_std + away_std) / 3

        if avg_std < 0.05:
            return "高"
        elif avg_std < 0.1:
            return "中"
        else:
            return "低"

    def _create_insufficient_data_report(self, match: Match) -> AgentReport:
        """创建数据不足的报告"""
        return AgentReport(
            agent_name=self.name,
            agent_type=self.agent_type,
            analysis={"error": "数据不足，无法进行统计分析"},
            confidence=0,
            risk_level=RiskLevel.HIGH,
            recommendation="数据不足",
            reasoning="无法获取足够的赔率数据进行分析"
        )
