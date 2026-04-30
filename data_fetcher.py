#!/usr/bin/env python3
"""
实时数据获取工具 v2.0
使用 Bing 搜索 + HTTP 抓取获取真实球队新闻
国内网络可用，无代理依赖
"""
import requests
import re
from typing import Dict, List
from datetime import datetime
from retry_utils import safe_request


class RealTimeDataFetcher:
    """实时数据获取器 v2.0 — Bing搜索，国内可用"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self._cache = {}
        self._timeout = 6  # 国内网络，6秒足够

    # ── 核心：Bing 搜索 ──────────────────────────────────
    def _bing_search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Bing 网页搜索，解析 HTML 提取结果
        返回: [{title, url, snippet, source}, ...]
        """
        encoded = requests.utils.quote(query)
        url = f"https://www.bing.com/search?q={encoded}&count={max_results}"

        try:
            resp = safe_request(
                requests.get, url, headers=self.headers, timeout=self._timeout,
                max_retries=1, silent=True
            )
            if resp is None or resp.status_code != 200:
                return self._bing_news_fallback(query, max_results)

            html = resp.text
            results = self._parse_bing_html(html, max_results)
            if results:
                return results
            return self._bing_news_fallback(query, max_results)

        except Exception:
            return self._bing_news_fallback(query, max_results)

    def _bing_news_fallback(self, query: str, max_results: int = 5) -> List[Dict]:
        """Bing 新闻搜索作为后备"""
        encoded = requests.utils.quote(query)
        url = f"https://www.bing.com/news/search?q={encoded}&count={max_results}&format=rsS"

        try:
            resp = safe_request(
                requests.get, url, headers=self.headers, timeout=self._timeout,
                max_retries=1, silent=True
            )
            if resp is None or resp.status_code != 200:
                return []

            html = resp.text
            return self._parse_bing_html(html, max_results)

        except Exception:
            return []

    def _parse_bing_html(self, html: str, max_results: int) -> List[Dict]:
        """解析 Bing 搜索结果 HTML，提取标题/URL/摘要"""
        results = []

        # 匹配 Bing 搜索结果卡片：<h2><a href="...">标题</a></h2> ... <p>摘要</p>
        # 简化的正则解析（避免依赖 BeautifulSoup）
        # Bing 结果格式: <li class="b_algo"><h2><a href="URL">Title</a></h2>...<p>或<div class="b_caption">Snippet</div></li>

        # 找所有结果区块
        blocks = re.split(r'<li class="b_algo"', html)[1:]  # 第一个split是前缀
        for block in blocks[:max_results]:
            try:
                # 提取链接和标题
                link_match = re.search(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.+?)</a>', block, re.DOTALL)
                if not link_match:
                    continue

                raw_url = link_match.group(1)
                raw_title = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()

                # 提取摘要
                snippet = ""
                snippet_match = re.search(r'<p[^>]*>(.+?)</p>', block, re.DOTALL)
                if not snippet_match:
                    snippet_match = re.search(r'class="b_caption"[^>]*>(.+?)</div>', block, re.DOTALL)
                if snippet_match:
                    snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()[:300]

                # 提取来源
                source = ""
                source_match = re.search(r'class="news_dt[^"]*"[^>]*>\s*([^<]+)', block)
                if not source_match:
                    source_match = re.search(r'cite[^>]*>\s*([^<]+)', block)
                if source_match:
                    source = source_match.group(1).strip()[:50]

                # 清理 URL（Bing 会用重定向链接）
                clean_url = raw_url

                results.append({
                    "title": raw_title[:200],
                    "url": clean_url,
                    "source": source or self._extract_domain(clean_url),
                    "snippet": snippet,
                })

            except Exception:
                continue

        return results

    def _extract_domain(self, url: str) -> str:
        """从URL提取域名"""
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else "Unknown"

    # ── 比赛新闻搜索 ──────────────────────────────────────
    def search_match_news(self, home_team: str, away_team: str,
                          league: str = "") -> Dict:
        """搜索比赛相关实时新闻，返回结构化舆情数据"""
        cache_key = f"{home_team}_{away_team}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        all_articles = []

        # 中文搜索（国内优先）
        cn_queries = [
            f"{home_team} {away_team} 比赛 预测 分析",
            f"{home_team} 伤停 阵容 新闻",
            f"{away_team} 伤病 新闻",
        ]
        # 英文搜索（国际资讯）
        en_queries = [
            f"{home_team} vs {away_team} preview prediction",
            f"{home_team} injury news squad",
        ]

        all_queries = cn_queries + en_queries
        for q in all_queries:
            articles = self._bing_search(q, max_results=3)
            for a in articles:
                if not any(x.get("url") == a["url"] for x in all_articles):
                    all_articles.append(a)

        # 情感分析
        sentiment = self._analyze_news_sentiment(all_articles, home_team, away_team)

        # 检查伤停
        injury_kw = ["injury", "injured", "out", "doubt",
                     "伤病", "受伤", "缺席", "伤停", "缺阵"]
        has_injury = any(
            any(kw in (a.get("title","")+a.get("snippet","")).lower() for kw in injury_kw)
            for a in all_articles
        )

        result = {
            "status": "success" if all_articles else "no_results",
            "articles_found": len(all_articles),
            "articles": all_articles[:10],
            "has_injury_news": has_injury,
            "news_sentiment": sentiment,
            "data_freshness": datetime.now().isoformat(),
        }

        self._cache[cache_key] = result
        return result

    def _analyze_news_sentiment(self, articles: List[Dict],
                                 home_team: str, away_team: str) -> Dict:
        """分析新闻情感倾向"""
        if not articles:
            return {"score": 50, "direction": "中性", "buzz_level": "低",
                    "consistency": "低", "key_headlines": []}

        home_pos = home_neg = away_pos = away_neg = 0
        key_headlines = []

        positive_kw = ["win", "victory", "strong", "confident", "boost",
                       "return", "recover", "back", "fit", "in-form",
                       "胜", "赢", "强", "信心", "复出", "回归", "好状态", "连胜"]
        negative_kw = ["lose", "loss", "defeat", "injury", "doubt", "crisis",
                       "struggle", "weak", "poor", "out", "suspension",
                       "输", "败", "伤病", "缺席", "危机", "低迷", "弱", "停赛"]

        for a in articles[:15]:
            text = (a.get("title", "") + " " + a.get("snippet", "")).lower()
            home_in = home_team.lower() in text
            away_in = away_team.lower() in text

            pos_cnt = sum(1 for kw in positive_kw if kw.lower() in text)
            neg_cnt = sum(1 for kw in negative_kw if kw.lower() in text)

            if home_in:
                if neg_cnt > pos_cnt:
                    home_neg += 1
                elif pos_cnt > neg_cnt:
                    home_pos += 1
            if away_in:
                if neg_cnt > pos_cnt:
                    away_neg += 1
                elif pos_cnt > pos_cnt:
                    away_pos += 1

            if len(key_headlines) < 5:
                label = "neutral"
                if home_in and pos_cnt > neg_cnt:
                    label = "positive_home"
                elif home_in and neg_cnt > pos_cnt:
                    label = "negative_home"
                elif away_in and pos_cnt > neg_cnt:
                    label = "positive_away"
                elif away_in and neg_cnt > pos_cnt:
                    label = "negative_away"

                impact = "high" if abs(pos_cnt-neg_cnt) >= 2 else "medium"
                key_headlines.append({
                    "source": a.get("source", "Unknown"),
                    "headline": a.get("title", "")[:120],
                    "sentiment": label,
                    "impact": impact,
                })

        score = 50 + (home_pos - home_neg) * 10 - (away_pos - away_neg) * 10
        score = max(0, min(100, score))

        direction = "偏向主队" if score > 60 else ("偏向客队" if score < 40 else "中性")
        buzz = "高" if len(articles) >= 6 else ("中" if len(articles) >= 3 else "低")

        total_sig = home_pos + home_neg + away_pos + away_neg
        max_dir = max(home_pos, home_neg, away_pos, away_neg) if total_sig > 0 else 0
        ratio = max_dir / total_sig if total_sig > 0 else 0
        consistency = "高" if ratio > 0.7 else ("中" if ratio > 0.4 else "低")

        return {
            "score": score, "direction": direction,
            "buzz_level": buzz, "consistency": consistency,
            "key_headlines": key_headlines,
        }

    # ── 兼容旧接口 ──────────────────────────────────────
    def search_team_news(self, team_name: str) -> Dict:
        articles = self._bing_search(f"{team_name} 足球 伤停 新闻", max_results=5)
        has_injury = any(
            kw in (a.get("title","")+a.get("snippet","")).lower()
            for a in articles
            for kw in ["injury", "injured", "伤病", "受伤"]
        )
        return {
            "status": "success" if articles else "no_results",
            "articles": articles[:5],
            "has_injury_news": has_injury,
            "has_suspension_news": False,
            "summary": articles[0].get("snippet", "")[:500] if articles else "无最新新闻",
        }

    def estimate_team_form(self, team_name: str, league: str) -> Dict:
        articles = self._bing_search(f"{team_name} 近期 战绩 状态", max_results=5)
        rating = 7 if len(articles) >= 4 else (5 if len(articles) >= 2 else 5)
        return {
            "estimated_rank": "基于新闻推断",
            "form_rating": rating,
            "attack_strength": "中",
            "defense_strength": "中",
            "confidence": "中" if articles else "低",
            "note": f"基于{len(articles)}条实时新闻估算",
        }

    def check_schedule_pressure(self, team_name: str) -> Dict:
        now = datetime.now()
        is_midweek = now.weekday() in [1, 2, 3]
        articles = self._bing_search(f"{team_name} 赛程 密集 疲劳", max_results=3)
        has_congestion = any(
            kw in (a.get("title","")+a.get("snippet","")).lower()
            for a in articles
            for kw in ["密集", "轮换", "疲劳", "congestion", "rotation"]
        )
        fatigue = "高" if (is_midweek and has_congestion) else \
                  "中" if (is_midweek or has_congestion) else "低"
        return {
            "match_day_type": "周中" if is_midweek else "周末",
            "potential_congestion": is_midweek or has_congestion,
            "fatigue_risk": fatigue,
            "note": f"日期分析+{len(articles)}条赛程新闻",
        }

    def get_match_context(self, home_team: str, away_team: str, league: str) -> Dict:
        """获取比赛综合背景信息 v2.0 — Bing搜索版"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "data_quality": {
                "real_time_news": False,
                "team_form": False,
                "schedule_data": True,
                "historical_h2h": False,
            }
        }

        # 比赛新闻搜索（核心）
        match_news = self.search_match_news(home_team, away_team, league)
        context["match_news"] = match_news
        if match_news.get("status") == "success":
            context["data_quality"]["real_time_news"] = True

        # 伤停
        context["home_team_news"] = self.search_team_news(home_team)
        context["away_team_news"] = self.search_team_news(away_team)

        # 状态
        context["home_form"] = self.estimate_team_form(home_team, league)
        context["away_form"] = self.estimate_team_form(away_team, league)

        # 赛程
        context["schedule_pressure"] = {
            "home": self.check_schedule_pressure(home_team),
            "away": self.check_schedule_pressure(away_team),
        }

        return context


# 测试
if __name__ == "__main__":
    fetcher = RealTimeDataFetcher()
    print("=== 测试 Bing 搜索 ===")
    news = fetcher.search_match_news("佛罗伦萨", "萨索洛", "意甲")
    print(f"找到 {news['articles_found']} 条新闻")
    s = news['news_sentiment']
    print(f"舆情: {s['direction']} ({s['score']}/100) 热度: {s['buzz_level']}")
    for h in s.get('key_headlines', [])[:3]:
        print(f"  📰 [{h['source']}] {h['headline'][:60]}... ")
