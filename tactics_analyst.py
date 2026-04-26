"""
🎯 Tactics-Analyst - 战术分析师
分析战术特点、攻防能力
"""
from typing import Dict, Any, List
from datetime import datetime
from models import AgentReport, RiskLevel, Match, BookmakerOdds


class TacticsAnalyst:
    """战术分析师"""

    def __init__(self):
        self.name = "Tactics-Analyst"
        self.agent_type = "战术分析"
        self.weight = 0.25

    def analyze(self, match: Match, odds_data: List[BookmakerOdds]) -> AgentReport:
        """
        执行战术分析

        分析维度：
        1. 让球盘分析 - 反映实力差距
        2. 大小球分析 - 反映攻防风格
        3. 综合攻防评估
        """
        # 分析让球盘数据
        spreads_data = [o for o in odds_data if o.market_type == "spreads"]
        totals_data = [o for o in odds_data if o.market_type == "totals"]

        analysis = {}

        # 让球盘分析 - 反映实力差距和战术风格
        if spreads_data:
            handicap_analysis = self._analyze_handicap(spreads_data, match)
            analysis["让球盘分析"] = handicap_analysis
        else:
            analysis["让球盘分析"] = {"状态": "数据不足"}

        # 大小球分析 - 反映攻防风格
        if totals_data:
            totals_analysis = self._analyze_totals(totals_data)
            analysis["大小球分析"] = totals_analysis
        else:
            analysis["大小球分析"] = {"状态": "数据不足"}

        # 综合战术评估
        tactical_assessment = self._assess_tactics(analysis)
        analysis["战术评估"] = tactical_assessment

        # 生成推荐
        recommendation = tactical_assessment.get("推荐", "无法评估")
        confidence = tactical_assessment.get("信心分数", 50)
        risk_level = self._determine_risk_level(confidence)

        reasoning = self._generate_reasoning(analysis, match)

        return AgentReport(
            agent_name=self.name,
            agent_type=self.agent_type,
            analysis=analysis,
            confidence=confidence,
            risk_level=risk_level,
            recommendation=recommendation,
            reasoning=reasoning
        )

    def _analyze_handicap(self, spreads: List[BookmakerOdds], match: Match) -> Dict:
        """分析让球盘"""
        home_handicaps = []
        away_handicaps = []

        for spread in spreads:
            outcomes = spread.outcomes
            point = spread.point

            if point is None:
                continue

            # 让球盘通常负值给主队
            if point < 0:  # 主队让球
                home_handicaps.append(abs(point))
            else:  # 客队让球
                away_handicaps.append(point)

        if not home_handicaps and not away_handicaps:
            return {"状态": "无法解析让球数据"}

        # 计算平均让球数
        if home_handicaps:
            avg_handicap = sum(home_handicaps) / len(home_handicaps)
            stronger_team = match.home_team.name
        else:
            avg_handicap = sum(away_handicaps) / len(away_handicaps)
            stronger_team = match.away_team.name

        return {
            "主流让球": f"{avg_handicap:.2f}球",
            "强势方": stronger_team,
            "实力差距": self._classify_strength_gap(avg_handicap),
            "博彩公司数": len(spreads)
        }

    def _analyze_totals(self, totals: List[BookmakerOdds]) -> Dict:
        """分析大小球"""
        total_lines = []
        over_odds = []
        under_odds = []

        for total in totals:
            if total.point:
                total_lines.append(total.point)
                outcomes = total.outcomes
                over_price = outcomes.get("Over", 0)
                under_price = outcomes.get("Under", 0)
                if over_price:
                    over_odds.append(over_price)
                if under_price:
                    under_odds.append(under_price)

        if not total_lines:
            return {"状态": "无法解析大小球数据"}

        avg_line = sum(total_lines) / len(total_lines)
        avg_over = sum(over_odds) / len(over_odds) if over_odds else 0
        avg_under = sum(under_odds) / len(under_odds) if under_odds else 0

        # 评估攻防风格
        if avg_line >= 2.5:
            style = "进攻型比赛"
        elif avg_line >= 2.0:
            style = "均衡型比赛"
        else:
            style = "防守型比赛"

        return {
            "主流大小球": f"{avg_line:.2f}球",
            "大球平均赔率": f"{avg_over:.3f}",
            "小球平均赔率": f"{avg_under:.3f}",
            "比赛风格预判": style,
            "博彩公司数": len(totals)
        }

    def _classify_strength_gap(self, handicap: float) -> str:
        """分类实力差距"""
        if handicap >= 1.5:
            return "明显优势"
        elif handicap >= 0.75:
            return "中等优势"
        elif handicap >= 0.25:
            return "微弱优势"
        else:
            return "势均力敌"

    def _assess_tactics(self, analysis: Dict) -> Dict:
        """综合战术评估"""
        handicap = analysis.get("让球盘分析", {})
        totals = analysis.get("大小球分析", {})

        if "状态" in handicap or "状态" in totals:
            return {"推荐": "数据不足", "信心分数": 30}

        # 根据让球和大小球综合判断
        strength_gap = handicap.get("实力差距", "势均力敌")
        game_style = totals.get("比赛风格预判", "均衡型比赛")

        if strength_gap in ["明显优势", "中等优势"]:
            stronger = handicap.get("强势方", "")
            recommendation = f"关注{stronger}"
            confidence = 70
        elif game_style == "进攻型比赛":
            recommendation = "关注进球数"
            confidence = 60
        else:
            recommendation = "比赛可能胶着"
            confidence = 50

        return {
            "推荐": recommendation,
            "信心分数": confidence,
            "综合评估": f"{strength_gap}，{game_style}"
        }

    def _determine_risk_level(self, confidence: float) -> RiskLevel:
        """确定风险等级"""
        if confidence >= 70:
            return RiskLevel.LOW
        elif confidence >= 50:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    def _generate_reasoning(self, analysis: Dict, match: Match) -> str:
        """生成分析推理"""
        parts = []

        handicap = analysis.get("让球盘分析", {})
        if "主流让球" in handicap:
            parts.append(f"让球盘显示{handicap.get('强势方', '某方')}有{handicap.get('实力差距', '一定优势')}")

        totals = analysis.get("大小球分析", {})
        if "主流大小球" in totals:
            parts.append(f"大小球{totals.get('主流大小球', '2.5球')}，预判为{totals.get('比赛风格预判', '均衡型')}比赛")

        if parts:
            return "。".join(parts) + "。"
        else:
            return "战术数据不足，无法进行详细分析。"
