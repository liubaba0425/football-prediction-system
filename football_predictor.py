#!/usr/bin/env python3
"""
足球预测智能体系统 - 主控脚本
Boss-Football 总协调者实现
"""
import json
import requests
import sys
import threading
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from data_fetcher import RealTimeDataFetcher
from team_translator import translate_team_name, translate_match_info
from backtest_manager import BacktestManager

# 添加当前目录到Python路径，确保可以导入ml_analyst模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from retry_utils import safe_request

# ML-Analyst 导入
try:
    from ml_analyst.ml_analyst import MLAnalyst
    ML_ANALYST_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  ML-Analyst 导入失败: {e}")
    ML_ANALYST_AVAILABLE = False
    MLAnalyst = None

# API 配置
ODDS_API_KEY = "c7af0126df9eb35c363065dcea447d8d"  # 用户提供的 API Key
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# 支持的联赛
SUPPORTED_LEAGUES = {
    "soccer_epl": "英格兰超级联赛",
    "soccer_spain_la_liga": "西班牙甲级联赛",
    "soccer_germany_bundesliga": "德国甲级联赛",
    "soccer_italy_serie_a": "意大利甲级联赛",
    "soccer_france_ligue_one": "法国甲级联赛",
    "soccer_uefa_champs_league": "欧洲冠军联赛",
    "soccer_uefa_europa_league": "欧洲联赛（欧联杯）",
    "soccer_uefa_europa_conference_league": "欧洲协会联赛（欧会杯）",
    "soccer_conmebol_copa_libertadores": "南美解放者杯",
    "soccer_china_super_league": "中国足球超级联赛",
    "soccer_korea_kleague1": "韩国K联赛",
    "soccer_japan_j_league": "日本J联赛",
    "soccer_germany_bundesliga2": "德国乙级联赛",
    "soccer_efl_champ": "英格兰冠军联赛",
    "soccer_sweden_allsvenskan": "瑞典超级联赛",
    "soccer_norway_eliteserien": "挪威超级联赛",
    "soccer_netherlands_eredivisie": "荷兰甲级联赛",
    "soccer_portugal_primeira_liga": "葡萄牙超级联赛",
    "soccer_saudi_arabia_pro_league": "沙特阿拉伯职业联赛",
    "soccer_usa_mls": "美国职业足球大联盟",
    "soccer_australia_aleague": "澳大利亚A联赛",
    "soccer_finland_veikkausliiga": "芬兰超级联赛",
    "soccer_italy_serie_b": "意大利乙级联赛",
    "soccer_france_ligue_two": "法国乙级联赛",
    # 杯赛
    "soccer_italy_coppa_italia": "意大利杯",
    "soccer_france_coupe_de_france": "法国杯",
    "soccer_fa_cup": "英格兰足总杯",
    "soccer_germany_dfb_pokal": "德国杯",
    "soccer_spain_copa_del_rey": "西班牙国王杯",
}


class OddsAPIClient:
    """Odds API 客户端"""

    def __init__(self, api_key: str = ODDS_API_KEY):
        self.api_key = api_key
        self.base_url = ODDS_API_BASE

    def fetch_match_odds(self, league: str = "soccer_epl") -> List[Dict]:
        """获取比赛赔率数据（优先使用Pinnacle）"""
        url = f"{self.base_url}/sports/{league}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "uk,eu",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "decimal",
            # "bookmakers": "pinnacle"  # 只获取Pinnacle数据 - 临时移除以获取所有博彩公司
        }

        try:
            response = safe_request(requests.get, url, params=params, timeout=30)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API 请求错误（已重试后仍失败）: {e}")
            return []

    def find_match(self, data: List[Dict], home_team: str, away_team: str) -> Optional[Dict]:
        """根据球队名称查找特定比赛（支持中英文和别名）"""
        for match in data:
            match_home = match.get("home_team", "").lower()
            match_away = match.get("away_team", "").lower()
            home_lower = home_team.lower()
            away_lower = away_team.lower()
            
            # 1. 直接匹配（英文或中文）
            if (home_lower in match_home and away_lower in match_away):
                return match
            # 反向匹配
            if (away_lower in match_home and home_lower in match_away):
                return match
            
            # 2. 尝试中文匹配：将API返回的英文队名翻译成中文
            match_home_cn = translate_team_name(match.get("home_team", ""))
            match_away_cn = translate_team_name(match.get("away_team", ""))
            
            if (home_lower in match_home_cn.lower() and away_lower in match_away_cn.lower()):
                return match
            if (away_lower in match_home_cn.lower() and home_lower in match_away_cn.lower()):
                return match
            
            # 3. 尝试反向：将用户输入翻译成英文（如果输入是中文）
            # 这里需要中文到英文的反向翻译，暂时跳过
            
        return None

    def extract_pinnacle_data(self, match_data: Dict) -> Dict:
        """提取赔率数据（优先使用 Pinnacle，备选其他博彩公司）"""
        result = {
            "h2h": None,      # 胜平负
            "spreads": None,  # 让球盘
            "totals": None,   # 大小球
            "source": None    # 数据来源
        }

        # 首先尝试找 Pinnacle
        for bookmaker in match_data.get("bookmakers", []):
            if bookmaker.get("key") == "pinnacle":
                result["source"] = "Pinnacle"
                for market in bookmaker.get("markets", []):
                    market_key = market.get("key")
                    if market_key == "h2h" and result["h2h"] is None:
                        result["h2h"] = self._parse_h2h(market, match_data)
                    elif market_key == "spreads" and result["spreads"] is None:
                        result["spreads"] = self._parse_spreads(market, match_data)
                    elif market_key == "totals" and result["totals"] is None:
                        result["totals"] = self._parse_totals(market)
                # 如果找到 Pinnacle 且有数据，直接返回
                if result["h2h"]:
                    break

        # 遍历所有博彩公司，补充缺失的数据
        for bookmaker in match_data.get("bookmakers", []):
            # 跳过已经处理过的 Pinnacle
            if bookmaker.get("key") == "pinnacle" and result["h2h"]:
                continue

            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                if market_key == "h2h" and result["h2h"] is None:
                    result["h2h"] = self._parse_h2h(market, match_data)
                    if result["source"] is None:
                        result["source"] = bookmaker.get("title", "Unknown")
                elif market_key == "spreads" and result["spreads"] is None:
                    result["spreads"] = self._parse_spreads(market, match_data)
                    if result["source"] is None:
                        result["source"] = bookmaker.get("title", "Unknown")
                elif market_key == "totals" and result["totals"] is None:
                    result["totals"] = self._parse_totals(market)
                    if result["source"] is None:
                        result["source"] = bookmaker.get("title", "Unknown")

            # 如果所有数据都找到了，提前退出
            if result["h2h"] and result["spreads"] and result["totals"]:
                break

        return result

    def _parse_h2h(self, market: Dict, match_data: Dict) -> Dict:
        """解析胜平负赔率"""
        outcomes = {}
        for outcome in market.get("outcomes", []):
            name = outcome.get("name", "")
            price = outcome.get("price", 0)

            if name == match_data.get("home_team"):
                outcomes["home"] = price
            elif name == match_data.get("away_team"):
                outcomes["away"] = price
            elif name == "Draw":
                outcomes["draw"] = price

        return outcomes

    def _parse_spreads(self, market: Dict, match_data: Dict) -> Dict:
        """解析让球盘数据"""
        outcomes = []
        for outcome in market.get("outcomes", []):
            outcomes.append({
                "name": outcome.get("name"),
                "price": outcome.get("price"),
                "point": outcome.get("point")
            })
        return {"outcomes": outcomes}

    def _parse_totals(self, market: Dict) -> Dict:
        """解析大小球数据"""
        outcomes = []
        for outcome in market.get("outcomes", []):
            outcomes.append({
                "name": outcome.get("name"),
                "price": outcome.get("price"),
                "point": outcome.get("point")
            })
        return {"outcomes": outcomes}


class FootballPredictor:
    """足球预测智能体系统"""
    _shared_ml_analyst = None
    _ml_analyst_lock = threading.Lock()

    def __init__(self, api_key: str = ODDS_API_KEY):
        self.client = OddsAPIClient(api_key)
        self.data_fetcher = RealTimeDataFetcher()  # 新增：实时数据获取器
        self.reports = {}
        self.real_time_data = {}  # 新增：存储实时数据
        
        # 初始化ML-Analyst（共享实例）
        self.ml_analyst = None
        if ML_ANALYST_AVAILABLE and MLAnalyst:
            try:
                with FootballPredictor._ml_analyst_lock:
                    if FootballPredictor._shared_ml_analyst is None:
                        FootballPredictor._shared_ml_analyst = MLAnalyst()
                        print("✅ ML-Analyst 共享实例创建成功")
                    else:
                        print("✅ ML-Analyst 重用共享实例")
                self.ml_analyst = FootballPredictor._shared_ml_analyst
            except Exception as e:
                print(f"⚠️  ML-Analyst 初始化失败: {e}")
                self.ml_analyst = None
        else:
            print("⚠️  ML-Analyst 不可用，将跳过机器学习分析")

        # 初始化回测管理器（单例）
        self.backtest_manager = BacktestManager()

    def predict(self, home_team: str, away_team: str, league: str = "soccer_epl"):
        """
        执行完整预测流程

        Args:
            home_team: 主队名称
            away_team: 客队名称
            league: 联赛标识
        """
        print(f"\n{'='*60}")
        print(f"🏆 足球预测智能体系统启动")
        print(f"{'='*60}")

        # 阶段 1: 数据获取
        print(f"\n📊 阶段 1: 获取比赛数据...")
        match_data = self._fetch_data(home_team, away_team, league)

        if not match_data:
            print("❌ 未找到该比赛数据")
            return {"success": False, "error": "未找到比赛数据"}

        print(f"✅ 找到比赛: {match_data['home_team']} vs {match_data['away_team']}")

        # 提取赔率数据
        pinnacle_data = self.client.extract_pinnacle_data(match_data)
        data_source = pinnacle_data.get("source", "未知")
        print(f"📊 数据来源: {data_source}")

        # 检查是否有有效的赔率数据
        h2h_data = pinnacle_data.get("h2h")
        spreads_data = pinnacle_data.get("spreads")
        totals_data = pinnacle_data.get("totals")

        if not h2h_data or len(h2h_data) < 3:
            print("❌ 赔率数据不足，无法分析")
            return {"success": False, "error": "赔率数据不足", "report": self._generate_no_data_report(home_team, away_team)}

        # 创建比赛信息（包含中英文队名）
        match_info = {
            "home_team": match_data["home_team"],
            "away_team": match_data["away_team"],
            "home_team_cn": translate_team_name(match_data["home_team"]),
            "away_team_cn": translate_team_name(match_data["away_team"]),
            "league": SUPPORTED_LEAGUES.get(league, league),
            "commence_time": match_data.get("commence_time", "未知")
        }
        print(f"⚽ 比赛: {match_info['home_team_cn']} vs {match_info['away_team_cn']}")

        # 新增：获取实时数据（新闻、状态、赛程压力）
        print(f"\n📰 获取实时数据...")
        self.real_time_data = self.data_fetcher.get_match_context(
            match_info["home_team"],
            match_info["away_team"],
            league
        )
        print(f"✅ 实时数据获取完成")

        # 阶段 2: 串行调度各分析师
        print(f"\n{'='*60}")
        print(f"📊 阶段 2: 启动专业分析师团队")
        print(f"{'='*60}")

        # 2.1 Stats-Analyst
        print(f"\n1️⃣ 调用 Stats-Analyst (统计数据分析师)...")
        stats_report = self._run_stats_analyst(match_info, pinnacle_data)
        self.reports["stats"] = stats_report

        # 2.2 Tactics-Analyst
        print(f"\n2️⃣ 调用 Tactics-Analyst (战术分析师)...")
        tactics_report = self._run_tactics_analyst(match_info, pinnacle_data, stats_report)
        self.reports["tactics"] = tactics_report

        # 2.3 Sentiment-Analyst
        print(f"\n3️⃣ 调用 Sentiment-Analyst (市场情绪分析师)...")
        sentiment_report = self._run_sentiment_analyst(match_info, pinnacle_data)
        self.reports["sentiment"] = sentiment_report

        # 2.4 Upset-Detector
        print(f"\n4️⃣ 调用 Upset-Detector (冷门风险检测器)...")
        upset_report = self._run_upset_detector(match_info, pinnacle_data, stats_report)
        self.reports["upset"] = upset_report

        # 2.5 Asian-Analyst
        print(f"\n5️⃣ 调用 Asian-Analyst (亚洲盘口分析师)...")
        asian_report = self._run_asian_analyst(match_info, pinnacle_data, stats_report)
        self.reports["asian"] = asian_report

        # 2.6 OverUnder-Analyst
        print(f"\n6️⃣ 调用 OverUnder-Analyst (大小球分析师)...")
        overunder_report = self._run_overunder_analyst(match_info, pinnacle_data)
        self.reports["overunder"] = overunder_report

        # 2.7 ML-Analyst (新增)
        print(f"\n7️⃣  调用 ML-Analyst (机器学习分析师)...")
        if self.ml_analyst:
            # 收集其他智能体的输出作为ML-Analyst的输入
            other_agents_output = {
                "stats": stats_report,
                "tactics": tactics_report,
                "sentiment": sentiment_report,
                "upset": upset_report,
                "asian": asian_report,
                "overunder": overunder_report
            }
            
            ml_report = self.ml_analyst.analyze_match(match_info, other_agents_output)
            self.reports["ml"] = ml_report
            
            if not ml_report.get("error"):
                print(f"   ✅ ML预测: {ml_report.get('prediction')} (信心: {ml_report.get('confidence', 0):.1f}%)")
            else:
                print(f"   ❌ ML分析失败: {ml_report.get('error_message', '未知错误')}")
        else:
            ml_report = {"error": True, "error_message": "ML-Analyst未初始化"}
            self.reports["ml"] = ml_report
            print("   ⚠️  ML-Analyst不可用")

        # 阶段 3: 共识汇总
        print(f"\n{'='*60}")
        print(f"📊 阶段 3: 共识汇总")
        print(f"{'='*60}")

        consensus = self._run_consensus_summarizer(match_info)

        # 阶段 4: 最终输出
        print(f"\n{'='*60}")
        print(f"📊 阶段 4: 最终报告")
        print(f"{'='*60}")

        final_output = self._generate_final_output(match_info, consensus)

        # 保存报告
        self._save_report(match_info, final_output)

        # 生成程序化调用用的预测字典
        prediction_dict = self._generate_prediction_dict(match_info, consensus)

        # 记录到回测系统
        self.backtest_manager.record_prediction(prediction_dict)

        return prediction_dict

    def _fetch_data(self, home_team: str, away_team: str, league: str) -> Optional[Dict]:
        """获取比赛数据"""
        all_matches = self.client.fetch_match_odds(league)
        return self.client.find_match(all_matches, home_team, away_team)

    def _run_stats_analyst(self, match_info: Dict, pinnacle_data: Dict) -> Dict:
        """运行统计分析师"""
        h2h = pinnacle_data.get("h2h", {}) or {}
        if not h2h:
            return {"error": "无胜平负数据", "confidence_weight": 0}

        # 计算隐含概率
        home_odds = h2h.get("home", 0)
        draw_odds = h2h.get("draw", 0)
        away_odds = h2h.get("away", 0)

        if not all([home_odds, draw_odds, away_odds]):
            return {"error": "赔率数据不完整", "confidence_weight": 0}

        # 隐含概率计算
        home_prob = 1 / home_odds
        draw_prob = 1 / draw_odds
        away_prob = 1 / away_odds

        # 归一化（去除抽水）
        total = home_prob + draw_prob + away_prob
        home_prob_norm = home_prob / total * 100
        draw_prob_norm = draw_prob / total * 100
        away_prob_norm = away_prob / total * 100

        # 数据面结论
        if home_prob_norm > away_prob_norm + 10:
            conclusion = f"数据面支持{match_info.get('home_team_cn', match_info['home_team'])}，主场优势明显"
            confidence = home_prob_norm
        elif away_prob_norm > home_prob_norm + 10:
            conclusion = f"数据面支持{match_info.get('away_team_cn', match_info['away_team'])}，客队实力占优"
            confidence = away_prob_norm
        else:
            conclusion = "双方实力接近，比赛存在较大不确定性"
            confidence = 50

        report = {
            "implied_probability": {
                "home": round(home_prob_norm, 1),
                "draw": round(draw_prob_norm, 1),
                "away": round(away_prob_norm, 1)
            },
            "odds": {
                "home": home_odds,
                "draw": draw_odds,
                "away": away_odds
            },
            "conclusion": conclusion,
            "confidence_weight": round(confidence, 0)
        }

        print(f"   ✅ 隐含概率: 主胜 {home_prob_norm:.1f}% | 平局 {draw_prob_norm:.1f}% | 客胜 {away_prob_norm:.1f}%")
        return report

    def _run_tactics_analyst(self, match_info: Dict, pinnacle_data: Dict, stats_report: Dict) -> Dict:
        """运行战术分析师（增强版：集成实时数据）"""
        h2h = pinnacle_data.get("h2h", {}) or {}  # 处理 None 的情况
        home_odds = h2h.get("home", 2.0)
        away_odds = h2h.get("away", 2.0)

        # 基于赔率差距推断战术匹配度
        odds_gap = abs(home_odds - away_odds)

        if home_odds < away_odds:
            formation_advantage = "主队"
            if odds_gap > 1.0:
                style = f"{match_info.get('home_team_cn', match_info['home_team'])}可能采取控球进攻战术，{match_info.get('away_team_cn', match_info['away_team'])}预计防守反击"
                score = 70
            else:
                style = "双方战术风格接近，中场争夺将是关键"
                score = 55
        elif away_odds < home_odds:
            formation_advantage = "客队"
            if odds_gap > 1.0:
                style = f"{match_info['away_team']}实力更强，可能主导比赛节奏"
                score = 35
            else:
                style = "客队略有优势，但主场因素不可忽视"
                score = 45
        else:
            formation_advantage = "均势"
            style = "双方势均力敌，战术执行力将决定胜负"
            score = 50

        # === 整合实时数据 ===
        # 伤停影响评估
        home_news = self.real_time_data.get("home_team_news", {})
        away_news = self.real_time_data.get("away_team_news", {})

        injury_impacts = []
        if home_news.get("has_injury_news"):
            injury_impacts.append(f"{match_info['home_team']}有伤病情况")
            score -= 5  # 主队伤病降低评分
        if away_news.get("has_injury_news"):
            injury_impacts.append(f"{match_info['away_team']}有伤病情况")
            score += 5  # 客队伤病对主队有利

        # 状态影响评估
        home_form = self.real_time_data.get("home_form", {})
        away_form = self.real_time_data.get("away_form", {})

        home_rating = home_form.get("form_rating", 5)
        away_rating = away_form.get("form_rating", 5)

        if home_rating >= 7 and away_rating <= 5:
            style += f"，{match_info['home_team']}状态正佳"
            score += 5
        elif away_rating >= 7 and home_rating <= 5:
            style += f"，{match_info['away_team']}状态出色"
            score -= 5

        # 限制分数范围
        score = max(20, min(90, score))

        # 伤停评估等级
        if len(injury_impacts) >= 2:
            injury_assessment = "高"
        elif len(injury_impacts) == 1:
            injury_assessment = "中"
        else:
            injury_assessment = "低"

        report = {
            "tactical_match_score": score,
            "formation_advantage": formation_advantage,
            "style_analysis": style,
            "key_player_impact": "; ".join(injury_impacts) if injury_impacts else "暂无伤停信息",
            "injury_assessment": injury_assessment,
            "confidence_weight": 65,
            "home_form_rating": home_rating,
            "away_form_rating": away_rating
        }

        print(f"   ✅ 战术匹配度: {score}/100 | 阵型优势: {formation_advantage}")
        if injury_impacts:
            print(f"      伤停影响: {', '.join(injury_impacts)}")
        return report

    def _run_sentiment_analyst(self, match_info: Dict, pinnacle_data: Dict) -> Dict:
        """运行市场情绪分析师"""
        h2h = pinnacle_data.get("h2h", {}) or {}
        if not h2h:
            return {"market_sentiment_score": 50, "confidence_weight": 0}

        home_odds = h2h.get("home", 2.0)
        draw_odds = h2h.get("draw", 3.0)
        away_odds = h2h.get("away", 2.0)

        # 计算隐含概率
        home_prob = (1 / home_odds) / (1/home_odds + 1/draw_odds + 1/away_odds) * 100
        draw_prob = (1 / draw_odds) / (1/home_odds + 1/draw_odds + 1/away_odds) * 100
        away_prob = (1 / away_odds) / (1/home_odds + 1/draw_odds + 1/away_odds) * 100

        # 市场情绪评分
        if home_prob > away_prob:
            sentiment_score = 50 + (home_prob - away_prob)
            trend = f"市场偏向{match_info['home_team']}"
        else:
            sentiment_score = 50 - (away_prob - home_prob)
            trend = f"市场偏向{match_info['away_team']}"

        # 市场一致性评估
        if abs(home_prob - away_prob) > 20:
            consistency = "高"
        elif abs(home_prob - away_prob) > 10:
            consistency = "中"
        else:
            consistency = "低"

        report = {
            "market_sentiment_score": round(sentiment_score, 0),
            "implied_probability_home": round(home_prob, 1),
            "implied_probability_draw": round(draw_prob, 1),
            "implied_probability_away": round(away_prob, 1),
            "odds_trend": trend,
            "market_consistency": consistency,
            "anomaly_detected": False,
            "confidence_weight": 75
        }

        print(f"   ✅ 市场情绪: {trend} | 一致性: {consistency}")
        return report

    def _run_upset_detector(self, match_info: Dict, pinnacle_data: Dict, stats_report: Dict) -> Dict:
        """运行冷门风险检测器（增强版：集成实时数据）"""
        h2h = pinnacle_data.get("h2h", {}) or {}
        home_odds = h2h.get("home", 2.0)
        away_odds = h2h.get("away", 2.0)

        # 检测冷门风险
        risk_factors = []
        risk_weights = []

        # === 风险因素1：赔率接近程度 (30%) ===
        if abs(home_odds - away_odds) < 0.3:
            risk_factors.append("双方赔率极为接近，比赛结果难以预测")
            risk_weights.append(30)
        elif abs(home_odds - away_odds) < 0.5:
            risk_factors.append("双方赔率较为接近")
            risk_weights.append(15)

        # === 风险因素2：强队赔率异常 (25%) ===
        if home_odds < 1.5 and away_odds > 5.0:
            risk_factors.append(f"{match_info['home_team']}赔率过低，可能存在冷门风险")
            risk_weights.append(25)
        elif away_odds < 1.5 and home_odds > 5.0:
            risk_factors.append(f"{match_info['away_team']}赔率过低，可能存在冷门风险")
            risk_weights.append(25)

        # === 风险因素3：伤停新闻 (25%) ===
        home_news = self.real_time_data.get("home_team_news", {})
        away_news = self.real_time_data.get("away_team_news", {})

        if home_news.get("has_injury_news"):
            risk_factors.append(f"{match_info['home_team']}有伤病新闻")
            risk_weights.append(25)
        if away_news.get("has_injury_news"):
            risk_factors.append(f"{match_info['away_team']}有伤病新闻")
            risk_weights.append(25)

        # === 风险因素4：赛程压力 (15%) ===
        schedule = self.real_time_data.get("schedule_pressure", {})
        home_schedule = schedule.get("home", {})
        away_schedule = schedule.get("away", {})

        if home_schedule.get("fatigue_risk") == "高":
            risk_factors.append(f"{match_info['home_team']}赛程密集，体能存疑")
            risk_weights.append(15)
        if away_schedule.get("fatigue_risk") == "高":
            risk_factors.append(f"{match_info['away_team']}赛程密集，体能存疑")
            risk_weights.append(15)

        # === 风险因素5：状态差异 (10%) ===
        home_form = self.real_time_data.get("home_form", {})
        away_form = self.real_time_data.get("away_form", {})

        home_rating = home_form.get("form_rating", 5)
        away_rating = away_form.get("form_rating", 5)

        if abs(home_rating - away_rating) >= 3:
            risk_factors.append("双方状态差距较大，弱队可能超常发挥")
            risk_weights.append(10)

        # 计算综合风险分数
        if risk_weights:
            risk_score = min(100, sum(risk_weights) + 20)  # 基础分20
        else:
            risk_score = 25

        # 确定风险等级
        if risk_score >= 60:
            risk_level = "高"
        elif risk_score >= 40:
            risk_level = "中"
        else:
            risk_level = "低"

        primary_risk = risk_factors[0] if risk_factors else "无明显冷门风险"

        # 数据质量标记
        data_quality = self.real_time_data.get("data_quality", {})
        quality_notes = []
        if data_quality.get("team_form") == False:
            quality_notes.append("球队状态为估算数据")
        if data_quality.get("historical_h2h") == False:
            quality_notes.append("缺少历史交锋数据")

        report = {
            "upset_risk_score": risk_score,
            "risk_level": risk_level,
            "primary_risk_factor": primary_risk,
            "secondary_risk_factors": risk_factors[1:] if len(risk_factors) > 1 else [],
            "recommendation": "谨慎投注" if risk_score > 50 else "可正常投注",
            "confidence_weight": 60 if quality_notes else 75,
            "data_quality_notes": quality_notes
        }

        print(f"   ✅ 冷门风险: {risk_level} ({risk_score}/100)")
        if risk_factors:
            print(f"      风险因素: {', '.join(risk_factors)}")
        return report

    def _run_asian_analyst(self, match_info: Dict, pinnacle_data: Dict, stats_report: Dict) -> Dict:
        """运行亚洲盘口分析师"""
        spreads = pinnacle_data.get("spreads", {})
        h2h = pinnacle_data.get("h2h", {}) or {}

        if not spreads or not spreads.get("outcomes"):
            return {
                "value_score": 0,
                "recommendation": "数据不足",
                "confidence_weight": 0
            }

        # 获取让球盘数据
        outcomes = spreads["outcomes"]
        if len(outcomes) < 2:
            return {"value_score": 0, "recommendation": "数据不足", "confidence_weight": 0}

        # 确定主客队让球
        home_outcome = None
        away_outcome = None
        for o in outcomes:
            if match_info["home_team"] in o.get("name", ""):
                home_outcome = o
            elif match_info["away_team"] in o.get("name", ""):
                away_outcome = o

        if not home_outcome or not away_outcome:
            return {"value_score": 0, "recommendation": "无法解析让球数据", "confidence_weight": 0}

        actual_handicap = home_outcome.get("point", 0)
        home_price = home_outcome.get("price", 2.0)
        away_price = away_outcome.get("price", 2.0)

        # 计算理论盘口（基于隐含概率）
        h2h_data = pinnacle_data.get("h2h", {})
        home_odds = h2h_data.get("home", 2.0)
        home_prob = 1 / home_odds

        # 换算理论盘口
        if home_prob >= 0.70:
            theoretical_raw = 1.0
        elif home_prob >= 0.65:
            theoretical_raw = 0.75
        elif home_prob >= 0.60:
            theoretical_raw = 0.5
        elif home_prob >= 0.55:
            theoretical_raw = 0.25
        else:
            theoretical_raw = 0

        # 理论盘口符号：主队让球时为负，客队让球时为正
        if home_prob > 0.5:
            theoretical_signed = -theoretical_raw  # 主队让球，负值
        else:
            theoretical_signed = theoretical_raw   # 客队让球或平手盘，正值或0

        # 判断盘口性质（基于让球幅度绝对值比较）
        abs_actual = abs(actual_handicap)
        abs_theoretical = abs(theoretical_signed)
        
        # 检查盘口方向是否一致（同号表示让球方相同）
        same_direction = (actual_handicap * theoretical_signed >= 0) or (abs_actual < 0.1 and abs_theoretical < 0.1)
        
        if not same_direction:
            # 盘口方向改变，特殊处理
            opening_type = "变盘"
        elif abs_actual > abs_theoretical + 0.25:
            opening_type = "高开"   # 实际让球比理论更深
        elif abs_actual < abs_theoretical - 0.25:
            opening_type = "浅开"   # 实际让球比理论更浅
        else:
            opening_type = "实开"   # 差异在0.25以内

        # 价值评估
        # 确定上盘（让球方）和下盘（受让方）
        if actual_handicap < 0:
            upper_team = match_info['home_team']   # 主队让球，上盘
            lower_team = match_info['away_team']   # 客队受让，下盘
            upper_handicap = actual_handicap
            lower_handicap = -actual_handicap
        elif actual_handicap > 0:
            upper_team = match_info['away_team']   # 客队让球，上盘
            lower_team = match_info['home_team']   # 主队受让，下盘
            upper_handicap = -actual_handicap      # 客队让球盘口为正值，转换为负值表示让球
            lower_handicap = actual_handicap       # 主队受让盘口为正值
        else:
            # 平手盘，无让球方
            upper_team = None
            lower_team = None
            upper_handicap = 0
            lower_handicap = 0
        
        if opening_type == "浅开":
            value_score = 75
            intention = "阻上盘"
            # 阻上盘：机构在阻止投注上盘，上盘可能有机会
            recommendation = f"{upper_team} {upper_handicap:+.2f}" if upper_team else "谨慎或放弃"
        elif opening_type == "高开":
            value_score = 65
            intention = "诱上盘"
            # 诱上盘：机构在诱导投注上盘，下盘可能有机会
            recommendation = f"{lower_team} {lower_handicap:+.2f}" if lower_team else "谨慎或放弃"
        elif opening_type == "变盘":
            value_score = 60
            intention = "盘口方向改变"
            recommendation = "谨慎或放弃"
        else:
            value_score = 50
            intention = "无明确意图"
            recommendation = "谨慎或放弃"

        report = {
            "qsda_value": round(home_prob * 100, 0),
            "theoretical_handicap": f"{theoretical_signed:+.2f}",
            "actual_handicap": f"{actual_handicap:+.2f}",
            "opening_analysis": opening_type,
            "pull_direction": "主队" if home_prob > 0.5 else "客队",
            "intention": intention,
            "value_score": value_score,
            "recommendation": recommendation,
            "confidence_weight": 70,
            "risk_warning": "临场走势需持续关注"
        }

        print(f"   ✅ 让球盘: {actual_handicap:+.2f} | 性质: {opening_type} | 价值: {value_score}/100")
        return report

    def _run_overunder_analyst(self, match_info: Dict, pinnacle_data: Dict) -> Dict:
        """运行大小球分析师"""
        totals = pinnacle_data.get("totals", {})

        if not totals or not totals.get("outcomes"):
            return {
                "overunder_value_score": 0,
                "recommendation": "数据不足",
                "confidence_weight": 0
            }

        outcomes = totals["outcomes"]
        over_data = None
        under_data = None

        for o in outcomes:
            if o.get("name") == "Over":
                over_data = o
            elif o.get("name") == "Under":
                under_data = o

        if not over_data or not under_data:
            return {"overunder_value_score": 0, "recommendation": "数据不足", "confidence_weight": 0}

        total_line = over_data.get("point", 2.5)
        over_odds = over_data.get("price", 2.0)
        under_odds = under_data.get("price", 2.0)

        # 计算隐含概率
        over_prob = 1 / over_odds
        under_prob = 1 / under_odds
        total_implied = over_prob + under_prob
        over_prob_norm = over_prob / total_implied * 100
        under_prob_norm = under_prob / total_implied * 100

        # 市场偏向
        if over_prob_norm > under_prob_norm + 5:
            bias = "大球"
            value_score = 60 + (over_prob_norm - under_prob_norm)
        elif under_prob_norm > over_prob_norm + 5:
            bias = "小球"
            value_score = 60 + (under_prob_norm - over_prob_norm)
        else:
            bias = "均衡"
            value_score = 50

        value_assessment = f"市场倾向{bias}，大球赔率{over_odds:.2f}，小球赔率{under_odds:.2f}"

        report = {
            "overunder_value_score": round(value_score, 0),
            "mainstream_total_line": total_line,
            "over_odds": over_odds,
            "under_odds": under_odds,
            "market_bias": bias,
            "value_assessment": value_assessment,
            "confidence_weight": 70
        }

        print(f"   ✅ 大小球: {total_line}球 | 偏向: {bias} | 价值: {value_score:.0f}/100")
        return report

    # 联赛校准表（基于回测数据 106场）
    # penalty_mult < 1.0 → 降低信心（该联赛系统表现差）
    # bonus_mult  > 1.0 → 提升信心（该联赛系统表现好）
    LEAGUE_CALIBRATION = {
        "西班牙甲级联赛":      {"mult": 0.70, "reason": "回测0%准确率"},
        "欧洲协会联赛（欧会杯）": {"mult": 0.80, "reason": "回测25%准确率"},
        "英格兰超级联赛":      {"mult": 1.08, "reason": "回测75%准确率"},
        "法国甲级联赛":        {"mult": 1.05, "reason": "回测67%准确率"},
        "韩国K联赛":           {"mult": 1.05, "reason": "回测67%准确率"},
        "欧洲联赛（欧联杯）":   {"mult": 1.05, "reason": "回测67%准确率"},
        "日本J联赛":           {"mult": 1.05, "reason": "回测67%准确率"},
    }
    # 大小球 vs 让球盘权重调整：大小球58%准确率 > 让球盘41%
    OVERUNDER_MARKET_BOOST = 8   # 大小球在比较时获得+8分加成
    # 低信心抑制阈值：<38%信心强推只有27%准确率
    LOW_CONFIDENCE_THRESHOLD = 38
    # 高信心加强：60%+信心带准确率82%
    HIGH_CONFIDENCE_BOOST = 5    # 额外+5分
    HIGH_CONFIDENCE_THRESHOLD = 60

    def _run_consensus_summarizer(self, match_info: Dict) -> Dict:
        """运行共识汇总师 - 生成单一推荐和信心分数"""
        # 提取各分析师的分数
        stats_conf = self.reports.get("stats", {}).get("confidence_weight", 50)
        tactics_score = self.reports.get("tactics", {}).get("tactical_match_score", 50)
        sentiment_score = self.reports.get("sentiment", {}).get("market_sentiment_score", 50)
        upset_risk = self.reports.get("upset", {}).get("upset_risk_score", 50)
        asian_value = self.reports.get("asian", {}).get("value_score", 0)
        overunder_value = self.reports.get("overunder", {}).get("overunder_value_score", 0)
        # ML-Analyst分数
        ml_report = self.reports.get("ml", {})
        if ml_report.get("error"):
            ml_score = 50  # 默认值
            ml_prediction = "未知"
            ml_confidence = 50
        else:
            ml_score = ml_report.get("confidence", 50)
            ml_prediction = ml_report.get("prediction", "未知")
            ml_confidence = ml_report.get("confidence", 50)

        # 检查是否需要启动辩论机制
        debate_needed, debate_reason = self._check_debate_conditions(
            asian_value, overunder_value, upset_risk, stats_conf, tactics_score, ml_score
        )

        if debate_needed:
            print(f"\n   ⚖️ 检测到分歧，启动辩论机制...")
            print(f"      原因: {debate_reason}")
            debate_result = self._run_debate(match_info, debate_reason)
        else:
            debate_result = None

        # 动态权重调整（含ML信心动态降权）
        ml_effective_weight = 0.25 if upset_risk > 60 else 0.35
        ml_effective_weight = ml_effective_weight if ml_confidence >= 45 else 0.10

        if upset_risk > 60:
            weights = {
                "stats": 0.20,
                "tactics": 0.15,
                "sentiment": 0.15,
                "upset": 0.25,
                "ml": ml_effective_weight
            }
        else:
            weights = {
                "stats": 0.25,
                "tactics": 0.15,
                "sentiment": 0.15,
                "upset": 0.10,
                "ml": ml_effective_weight
            }

        # ML信心低时，将剩余权重分配给Stats
        weight_remainder = (0.25 if upset_risk > 60 else 0.35) - ml_effective_weight
        if weight_remainder > 0:
            weights["stats"] += weight_remainder

        # 计算基础信心分
        base_score = (
            stats_conf * weights["stats"] +
            tactics_score * weights["tactics"] +
            sentiment_score * weights["sentiment"] +
            (100 - upset_risk) * weights["upset"] +
            ml_score * weights["ml"]
        )

        # 二选一：比较让球盘和大小球价值
        # 回测优化：大小球准确率(58%) > 让球盘(41%)，给大小球+8分加成
        effective_overunder_value = overunder_value + self.OVERUNDER_MARKET_BOOST
        if asian_value > effective_overunder_value:
            selected_market = "让球盘"
            selected_value = asian_value
            recommendation = self.reports.get("asian", {}).get("recommendation", "无法推荐")
            market_detail = {
                "type": "asian",
                "handicap": self.reports.get("asian", {}).get("actual_handicap", "N/A"),
                "intention": self.reports.get("asian", {}).get("intention", "N/A")
            }
        elif effective_overunder_value > asian_value:
            selected_market = "大小球"
            selected_value = overunder_value
            bias = self.reports.get("overunder", {}).get("market_bias", "均衡")
            line = self.reports.get("overunder", {}).get("mainstream_total_line", 2.5)
            recommendation = f"{bias} {line}球"
            market_detail = {
                "type": "overunder",
                "line": line,
                "bias": bias,
                "over_odds": self.reports.get("overunder", {}).get("over_odds", "N/A"),
                "under_odds": self.reports.get("overunder", {}).get("under_odds", "N/A")
            }
        else:
            # 如果两个市场价值相同（含加成后），优先选大小球（准确率更高）
            selected_market = "大小球"
            selected_value = overunder_value
            bias = self.reports.get("overunder", {}).get("market_bias", "均衡")
            line = self.reports.get("overunder", {}).get("mainstream_total_line", 2.5)
            recommendation = f"{bias} {line}球"
            market_detail = {
                "type": "overunder",
                "line": line,
                "bias": bias,
                "over_odds": self.reports.get("overunder", {}).get("over_odds", "N/A"),
                "under_odds": self.reports.get("overunder", {}).get("under_odds", "N/A")
            }

        # 最终信心分数 = 基础分数 × 市场价值系数
        # 市场价值越高，信心越强
        market_factor = selected_value / 100 if selected_value > 0 else 0.5
        final_confidence = base_score * (0.7 + 0.3 * market_factor)

        # 市场价值阈值检查 - 两个市场价值都低时建议跳过
        max_market_value = max(asian_value, overunder_value)
        if max_market_value < 55:
            selected_market = "跳过"
            recommendation = "放弃（市场价值不足）"
            if "market_detail" in locals():
                market_detail["intention"] = "无明确价值"
            final_confidence = min(final_confidence, 35)  # 强制降低信心

        # 应用辩论调整
        if debate_result:
            final_confidence += debate_result.get("confidence_adjustment", 0)
            # 如果辩论裁决是观望，大幅降低信心
            if "观望" in debate_result.get("verdict", ""):
                final_confidence = min(final_confidence, 45)

        # 联赛校准 — 基于回测数据的联赛级信心调整
        league = match_info.get("league", "")
        calib = self.LEAGUE_CALIBRATION.get(league, {"mult": 1.0, "reason": "无回测数据"})
        original_confidence = final_confidence
        final_confidence *= calib["mult"]
        if calib["mult"] != 1.0:
            print(f"   📊 联赛校准: {league} ×{calib['mult']} ({calib['reason']}) "
                  f"{original_confidence:.1f}% → {final_confidence:.1f}%")

        # 低信心抑制 — 回测显示<38%信心带准确率仅27%，强推不如观望
        if final_confidence < self.LOW_CONFIDENCE_THRESHOLD:
            original_rec = recommendation
            recommendation = "谨慎或放弃"
            selected_market = "让球盘"
            if "market_detail" in locals():
                market_detail["intention"] = "低信心抑制"
            print(f"   ⚠️ 低信心抑制: {final_confidence:.1f}% < {self.LOW_CONFIDENCE_THRESHOLD}%阈值 "
                  f"(原推荐: {original_rec})")

        # 高信心加强 — 回测显示60%+信心带准确率82%
        if final_confidence >= self.HIGH_CONFIDENCE_THRESHOLD and upset_risk < 40:
            final_confidence += self.HIGH_CONFIDENCE_BOOST
            print(f"   🚀 高信心加强: +{self.HIGH_CONFIDENCE_BOOST}% → {final_confidence:.1f}% (冷门风险低)")

        # 确保信心分数在合理范围内
        final_confidence = max(5, min(90, final_confidence))

        # 信号清晰度标签 - 帮助用户区分"有信号"和"模糊"
        if final_confidence >= 60:
            signal_clarity = "清晰"
        elif final_confidence >= 40:
            signal_clarity = "模糊"
        else:
            signal_clarity = "无信号"

        consensus = {
            "final_confidence": round(final_confidence, 1),  # 唯一的信心分数
            "signal_clarity": signal_clarity,                # 信号清晰度标签
            "selected_market": selected_market,
            "recommendation": recommendation,
            "market_detail": market_detail,
            "base_score": round(base_score, 1),
            "selected_value": selected_value,
            "upset_risk": upset_risk,
            "primary_risk": self.reports.get("upset", {}).get("primary_risk_factor", "无明显风险"),
            "debate_triggered": debate_result is not None,
            "debate_result": debate_result
        }

        print(f"\n   📊 最终计算:")
        print(f"      基础分数: {base_score:.1f} | 市场价值: {selected_value}/100")
        print(f"      最终信心: {final_confidence:.1f}%")
        print(f"      推荐市场: {selected_market} | 推荐: {recommendation}")

        return consensus

    def _check_debate_conditions(self, asian_value: float, overunder_value: float,
                                  upset_risk: float, stats_conf: float, tactics_score: float,
                                  ml_score: float) -> tuple:
        """
        检查是否需要启动辩论机制

        返回: (是否需要辩论, 辩论原因)
        """
        reasons = []

        # 条件1: 让球盘和大小球价值接近
        if asian_value > 0 and overunder_value > 0:
            if abs(asian_value - overunder_value) < 10:
                reasons.append(f"让球盘({asian_value})和大小球({overunder_value})价值接近")

        # 条件2: 冷门风险高但其他分析师信心也高
        if upset_risk > 50 and stats_conf > 70:
            reasons.append(f"冷门风险({upset_risk})较高但统计分析信心({stats_conf})也高")

        # 条件3: 统计分析和战术分析方向明显不同
        # stats_conf高表示看好赔率低的一方，tactics_score高表示主队战术优势
        if stats_conf > 70 and tactics_score < 40:
            reasons.append(f"统计分析({stats_conf})看好但战术分析({tactics_score})不看好")
        elif stats_conf < 40 and tactics_score > 70:
            reasons.append(f"战术分析({tactics_score})看好但统计分析({stats_conf})不看好")
        
        # 条件4: ML分析与传统分析显著差异
        traditional_avg = (stats_conf + tactics_score) / 2
        if abs(ml_score - traditional_avg) > 25:
            reasons.append(f"ML分析({ml_score})与传统分析平均分({traditional_avg:.1f})差异显著")

        if reasons:
            return True, "; ".join(reasons)
        return False, ""

    def _run_debate(self, match_info: Dict, debate_reason: str) -> Dict:
        """
        运行辩论机制

        当分析师意见分歧时，进行辩论并做出裁决
        使用三级裁决体系：strong_consensus / weak_consensus / divided
        """
        home_cn = match_info.get("home_team_cn", match_info["home_team"])
        away_cn = match_info.get("away_team_cn", match_info["away_team"])

        # 收集各方观点
        stats_view = self.reports.get("stats", {}).get("conclusion", "数据不足")
        tactics_view = self.reports.get("tactics", {}).get("style_analysis", "战术数据不足")
        upset_view = self.reports.get("upset", {}).get("primary_risk_factor", "无明显风险")

        asian_recommendation = self.reports.get("asian", {}).get("recommendation", "N/A")
        overunder_recommendation = self.reports.get("overunder", {}).get("market_bias", "N/A")

        upset_risk = self.reports.get("upset", {}).get("upset_risk_score", 50)
        stats_conf = self.reports.get("stats", {}).get("confidence_weight", 50)
        tactics_score = self.reports.get("tactics", {}).get("tactical_match_score", 50)
        ml_report = self.reports.get("ml", {})
        ml_confidence = ml_report.get("confidence", 50) if not ml_report.get("error") else 50

        # 模拟辩论过程
        print(f"\n   ⚖️ 辩论过程:")
        print(f"   【Stats观点】: {stats_view}")
        print(f"   【Tactics观点】: {tactics_view}")
        print(f"   【Upset观点】: {upset_view}")

        # === 动态裁决逻辑 ===

        # 风险太高的情况
        if upset_risk > 60:
            verdict_type = "divided"
            verdict = "观望"
            verdict_reason = f"冷门风险({upset_risk})过高，风险控制优先"
            confidence_adjustment = -20
        elif "数据不足" in stats_view or "不足" in tactics_view:
            # 数据不足
            verdict_type = "divided"
            verdict = "观望"
            verdict_reason = "数据不足，无法做出可靠判断"
            confidence_adjustment = -25
        else:
            # 计算分析师之间的一致性
            traditional_avg = (stats_conf + tactics_score) / 2
            ml_aligned_with_traditional = abs(ml_confidence - traditional_avg) <= 15
            asian_value = self.reports.get("asian", {}).get("value_score", 0)
            overunder_value = self.reports.get("overunder", {}).get("overunder_value_score", 0)

            # 判断是否强共识
            if ml_aligned_with_traditional and upset_risk < 40:
                # ML与传统分析一致，且风险低 -> 强共识
                verdict_type = "strong_consensus"
                if asian_value >= overunder_value:
                    verdict = f"让球盘 {asian_recommendation}"
                    verdict_reason = "各方分析师观点一致，让球盘价值更高"
                else:
                    verdict = f"大小球 {overunder_recommendation}"
                    verdict_reason = "各方分析师观点一致，大小球价值更高"
                confidence_adjustment = 0
            elif upset_risk < 55:
                # 弱共识 - 有分歧但风险可控
                verdict_type = "weak_consensus"
                if asian_value > overunder_value:
                    verdict = f"让球盘 {asian_recommendation}"
                    verdict_reason = "分析师存在分歧但让球盘价值略高"
                else:
                    verdict = f"大小球 {overunder_recommendation}"
                    verdict_reason = "分析师存在分歧但大小球价值略高"
                confidence_adjustment = -8
            else:
                # 严重分歧
                verdict_type = "divided"
                if asian_value > overunder_value:
                    verdict = f"让球盘 {asian_recommendation}"
                    verdict_reason = "分析师严重分歧，建议谨慎"
                else:
                    verdict = f"大小球 {overunder_recommendation}"
                    verdict_reason = "分析师严重分歧，建议谨慎"
                confidence_adjustment = -20

        debate_result = {
            "debate_triggered": True,
            "debate_reason": debate_reason,
            "verdict_type": verdict_type,          # strong_consensus / weak_consensus / divided
            "stats_view": stats_view,
            "tactics_view": tactics_view,
            "upset_view": upset_view,
            "verdict": verdict,
            "verdict_reason": verdict_reason,
            "confidence_adjustment": confidence_adjustment
        }

        print(f"\n   ⚖️ 辩论裁决:")
        print(f"      裁决类型: {verdict_type}")
        print(f"      裁决: {verdict}")
        print(f"      理由: {verdict_reason}")
        print(f"      信心调整: {confidence_adjustment}%")

        return debate_result

    def _generate_final_output(self, match_info: Dict, consensus: Dict) -> str:
        """生成最终输出报告 - 简化版，只有一个信心分数"""

        # 获取中文队名
        home_cn = match_info.get("home_team_cn", match_info["home_team"])
        away_cn = match_info.get("away_team_cn", match_info["away_team"])

        # 获取关键数据
        stats_prob = self.reports.get('stats', {}).get('implied_probability', {})
        upset_risk = self.reports.get('upset', {}).get('upset_risk_score', 0)
        risk_level = self.reports.get('upset', {}).get('risk_level', '中')
        primary_risk = self.reports.get('upset', {}).get('primary_risk_factor', '无明显风险')

        # 构建推荐详情
        if consensus['selected_market'] == '跳过':
            market_info = "无推荐市场"
            analysis_note = "市场价值不足，建议跳过该比赛"
        elif consensus['market_detail']['type'] == 'asian':
            market_info = f"让球盘 {consensus['market_detail'].get('handicap', 'N/A')}"
            analysis_note = f"盘口: {consensus['market_detail'].get('handicap', 'N/A')} | 机构意图: {consensus['market_detail'].get('intention', 'N/A')}"
        else:
            market_info = f"大小球 {consensus['market_detail'].get('line', 2.5)}球 ({consensus['market_detail'].get('bias', 'N/A')})"
            analysis_note = f"盘口: {consensus['market_detail'].get('line', 2.5)}球 | 大球赔率: {consensus['market_detail'].get('over_odds', 'N/A')} | 小球赔率: {consensus['market_detail'].get('under_odds', 'N/A')}"

        report = f"""
{'='*60}
🏆 足球比赛预测报告
{'='*60}

📅 比赛: {home_cn} vs {away_cn}
⏰ 时间: {match_info['commence_time']}
📊 联赛: {match_info['league']}

{'='*60}
📊 核心数据
{'='*60}

隐含概率:
  • {home_cn} 胜: {stats_prob.get('home', 'N/A')}%
  • 平局: {stats_prob.get('draw', 'N/A')}%
  • {away_cn} 胜: {stats_prob.get('away', 'N/A')}%

冷门风险: {risk_level} ({upset_risk}/100)
主要风险: {primary_risk}
"""

        # 如果触发了辩论，显示辩论结果
        if consensus.get("debate_triggered"):
            debate = consensus.get("debate_result", {})
            report += f"""
{'='*60}
⚖️ 辩论记录
{'='*60}

触发原因: {debate.get('debate_reason', 'N/A')}

【Stats观点】: {debate.get('stats_view', 'N/A')}
【Tactics观点】: {debate.get('tactics_view', 'N/A')}
【Upset观点】: {debate.get('upset_view', 'N/A')}

【协调员裁决】: {debate.get('verdict', 'N/A')}
【裁决类型】: {'强共识' if debate.get('verdict_type') == 'strong_consensus' else '弱共识' if debate.get('verdict_type') == 'weak_consensus' else '严重分歧'}
【裁决理由】: {debate.get('verdict_reason', 'N/A')}
"""

        report += f"""
{'='*60}
🎯 最终推荐
{'='*60}

推荐市场: {consensus['selected_market']}
推荐选项: {consensus['recommendation']}
{analysis_note}

💪 信心分数: {consensus['final_confidence']}%
📊 信号清晰度: {consensus.get('signal_clarity', 'N/A')}
（信心分数越高越可信，信号清晰度帮助判断是否值得下注）

{'='*60}
⚠️ 免责声明
{'='*60}
本报告仅供娱乐和参考，不构成任何投注建议。
博彩有风险，投注需谨慎。

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return report

    def _generate_no_data_report(self, home_team: str, away_team: str) -> str:
        """生成无数据报告"""
        home_cn = translate_team_name(home_team)
        away_cn = translate_team_name(away_team)

        return f"""
{'='*60}
🏆 足球比赛预测报告
{'='*60}

📅 比赛: {home_cn} vs {away_cn}

{'='*60}
⚠️ 数据不足
{'='*60}

❌ 无法获取该比赛的有效赔率数据
❌ 不推荐任何投注

{'='*60}
⚠️ 免责声明
{'='*60}
本报告仅供娱乐和参考，不构成任何投注建议。
博彩有风险，投注需谨慎。

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    def _save_report(self, match_info: Dict, report: str):
        """保存报告到文件"""
        filename = f"prediction_{match_info['home_team']}_{match_info['away_team']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n💾 报告已保存: {filename}")
        except Exception as e:
            print(f"保存报告失败: {e}")

    def _generate_prediction_dict(self, match_info: Dict, consensus: Dict) -> Dict:
        """生成预测结果字典，供程序化调用和回测追踪"""
        # 获取中文队名
        home_cn = match_info.get("home_team_cn", match_info["home_team"])
        away_cn = match_info.get("away_team_cn", match_info["away_team"])
        
        # 获取隐含概率
        stats_report = self.reports.get("stats", {})
        implied_prob = stats_report.get("implied_probability", {})
        
        # 获取ML预测
        ml_report = self.reports.get("ml", {})
        ml_prediction = ml_report.get("prediction", "")
        ml_confidence = ml_report.get("confidence", 0)
        
        # 获取冷门风险
        upset_report = self.reports.get("upset", {})
        upset_risk = upset_report.get("upset_risk_score", 0)
        risk_level = upset_report.get("risk_level", "中")
        
        # 获取辩论结果
        debate_result = consensus.get("debate_result", {})
        
        # 构建字典（扩展回测字段）
        prediction_dict = {
            "success": True,
            "home_team_cn": home_cn,
            "away_team_cn": away_cn,
            "league": match_info.get("league", ""),
            "match_date": match_info.get("commence_time", ""),
            "implied_probabilities": {
                "home": implied_prob.get("home", 0),
                "draw": implied_prob.get("draw", 0),
                "away": implied_prob.get("away", 0)
            },
            "ml_prediction": {
                "result": ml_prediction,
                "confidence": ml_confidence
            },
            "upset_risk": upset_risk,
            "risk_level": risk_level,
            "consensus": {
                "recommended_market": consensus.get("selected_market", ""),
                "recommendation": consensus.get("recommendation", ""),
                "confidence": consensus.get("final_confidence", 0),
                "signal_clarity": consensus.get("signal_clarity", ""),
                "market_value": consensus.get("selected_value", 0),
                "market_detail": consensus.get("market_detail", {}),
                "debate_triggered": consensus.get("debate_triggered", False),
                "verdict_type": debate_result.get("verdict_type", "") if debate_result else "",
            },
            "timestamp": datetime.now().isoformat()
        }
        return prediction_dict


def main():
    """主函数 - 示例用法"""
    print("="*60)
    print("🏆 足球预测智能体系统 v1.1")
    print("="*60)

    # 示例：预测英超比赛
    predictor = FootballPredictor()

    # 可以修改这里的参数来预测不同比赛
    home_team = "Manchester United"
    away_team = "Liverpool"
    league = "soccer_epl"

    print(f"\n请输入比赛信息（直接回车使用默认值）:")
    user_input = input("主队名称 [Manchester United]: ").strip()
    if user_input:
        home_team = user_input

    user_input = input("客队名称 [Liverpool]: ").strip()
    if user_input:
        away_team = user_input

    user_input = input("联赛代码 [soccer_epl]: ").strip()
    if user_input:
        league = user_input

    # 执行预测
    result = predictor.predict(home_team, away_team, league)

    if result:
        print(result)


if __name__ == "__main__":
    main()
