#!/usr/bin/env python3
"""
并行智能体处理器 - 在单场比赛内并行执行智能体
"""
import concurrent.futures
import time
from typing import Dict, List, Tuple, Optional
import sys
sys.path.append('.')

from football_predictor import FootballPredictor, translate_team_name, SUPPORTED_LEAGUES
from data_fetcher import RealTimeDataFetcher


class ParallelMatchProcessor:
    """并行处理单场比赛的智能体"""
    
    def __init__(self, predictor: FootballPredictor = None):
        self.predictor = predictor or FootballPredictor()
        self.data_fetcher = RealTimeDataFetcher()
    
    def _fetch_real_time_data_parallel(self, home_team: str, away_team: str, league: str) -> Dict:
        """并行获取实时数据（主队和客队新闻并行）"""
        context = {
            "timestamp": time.time(),
            "data_quality": {
                "real_time_news": True,
                "team_form": False,
                "schedule_data": True,
                "historical_h2h": False
            }
        }
        
        # 并行获取主队和客队新闻
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            home_future = executor.submit(self.data_fetcher.search_team_news, home_team)
            away_future = executor.submit(self.data_fetcher.search_team_news, away_team)
            
            try:
                home_news = home_future.result(timeout=15)
                away_news = away_future.result(timeout=15)
            except concurrent.futures.TimeoutError:
                # 超时回退
                home_news = {"status": "timeout", "summary": "获取超时"}
                away_news = {"status": "timeout", "summary": "获取超时"}
        
        context["home_team_news"] = home_news
        context["away_team_news"] = away_news
        
        # 串行获取其他数据（很快）
        context["home_form"] = self.data_fetcher.estimate_team_form(home_team, league)
        context["away_form"] = self.data_fetcher.estimate_team_form(away_team, league)
        context["schedule_pressure"] = {
            "home": self.data_fetcher.check_schedule_pressure(home_team),
            "away": self.data_fetcher.check_schedule_pressure(away_team)
        }
        
        return context
    
    def _run_parallel_agents_stage1(self, match_info: Dict, pinnacle_data: Dict) -> Dict:
        """
        并行执行第一阶段智能体：Stats, Sentiment, OverUnder
        
        返回: { "stats": report, "sentiment": report, "overunder": report }
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 提交任务
            future_to_agent = {
                executor.submit(self.predictor._run_stats_analyst, match_info, pinnacle_data): "stats",
                executor.submit(self.predictor._run_sentiment_analyst, match_info, pinnacle_data): "sentiment",
                executor.submit(self.predictor._run_overunder_analyst, match_info, pinnacle_data): "overunder"
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    results[agent] = future.result(timeout=10)
                except Exception as e:
                    results[agent] = {"error": str(e), "confidence_weight": 0}
                    print(f"❌ {agent} 执行失败: {e}")
        
        return results
    
    def _run_parallel_agents_stage2(self, match_info: Dict, pinnacle_data: Dict, stats_report: Dict) -> Dict:
        """
        并行执行第二阶段智能体：Tactics, Upset, Asian（依赖Stats）
        
        返回: { "tactics": report, "upset": report, "asian": report }
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 提交任务
            future_to_agent = {
                executor.submit(self.predictor._run_tactics_analyst, match_info, pinnacle_data, stats_report): "tactics",
                executor.submit(self.predictor._run_upset_detector, match_info, pinnacle_data, stats_report): "upset",
                executor.submit(self.predictor._run_asian_analyst, match_info, pinnacle_data, stats_report): "asian"
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    results[agent] = future.result(timeout=10)
                except Exception as e:
                    results[agent] = {"error": str(e), "confidence_weight": 0}
                    print(f"❌ {agent} 执行失败: {e}")
        
        return results
    
    def predict_parallel(self, home_team: str, away_team: str, league: str) -> Dict:
        """
        并行预测单场比赛
        
        返回格式与FootballPredictor.predict相同
        """
        print(f"\n{'='*60}")
        print(f"🚀 并行智能体预测启动")
        print(f"{'='*60}")
        
        total_start = time.time()
        
        # 1. 数据获取
        print(f"\n📊 阶段 1: 获取比赛数据...")
        fetch_start = time.time()
        match_data = self.predictor._fetch_data(home_team, away_team, league)
        fetch_time = time.time() - fetch_start
        
        if not match_data:
            print("❌ 未找到该比赛数据")
            return {"success": False, "error": "未找到比赛数据"}
        
        print(f"✅ 找到比赛: {match_data['home_team']} vs {match_data['away_team']}")
        print(f"⏱️  数据获取耗时: {fetch_time:.2f}s")
        
        # 提取赔率数据
        pinnacle_data = self.predictor.client.extract_pinnacle_data(match_data)
        
        # 比赛信息
        match_info = {
            "home_team": match_data["home_team"],
            "away_team": match_data["away_team"],
            "home_team_cn": translate_team_name(match_data["home_team"]),
            "away_team_cn": translate_team_name(match_data["away_team"]),
            "league": SUPPORTED_LEAGUES.get(league, league),
            "commence_time": match_data.get("commence_time", "未知")
        }
        
        # 2. 并行获取实时数据
        print(f"\n📰 阶段 2: 并行获取实时数据...")
        realtime_start = time.time()
        self.predictor.real_time_data = self._fetch_real_time_data_parallel(
            match_info["home_team"], match_info["away_team"], league
        )
        realtime_time = time.time() - realtime_start
        print(f"⏱️  实时数据耗时: {realtime_time:.2f}s")
        
        # 3. 并行执行智能体
        print(f"\n{'='*60}")
        print(f"📊 阶段 3: 并行智能体执行")
        print(f"{'='*60}")
        
        stage_start = time.time()
        
        # 第一阶段：独立智能体
        print(f"\n🔄 第一阶段: 并行执行 Stats, Sentiment, OverUnder...")
        stage1_start = time.time()
        stage1_results = self._run_parallel_agents_stage1(match_info, pinnacle_data)
        stage1_time = time.time() - stage1_start
        
        stats_report = stage1_results.get("stats", {})
        sentiment_report = stage1_results.get("sentiment", {})
        overunder_report = stage1_results.get("overunder", {})
        
        print(f"⏱️  第一阶段耗时: {stage1_time:.2f}s")
        
        # 第二阶段：依赖Stats的智能体
        print(f"\n🔄 第二阶段: 并行执行 Tactics, Upset, Asian...")
        stage2_start = time.time()
        stage2_results = self._run_parallel_agents_stage2(match_info, pinnacle_data, stats_report)
        stage2_time = time.time() - stage2_start
        
        tactics_report = stage2_results.get("tactics", {})
        upset_report = stage2_results.get("upset", {})
        asian_report = stage2_results.get("asian", {})
        
        print(f"⏱️  第二阶段耗时: {stage2_time:.2f}s")
        
        # 第三阶段：ML-Analyst（串行，依赖所有）
        print(f"\n🔄 第三阶段: 执行 ML-Analyst...")
        ml_report = {}
        if self.predictor.ml_analyst:
            try:
                other_agents_output = {
                    "stats": stats_report,
                    "tactics": tactics_report,
                    "sentiment": sentiment_report,
                    "upset": upset_report,
                    "asian": asian_report,
                    "overunder": overunder_report
                }
                ml_report = self.predictor.ml_analyst.analyze_match(match_info, other_agents_output)
            except Exception as e:
                ml_report = {"error": str(e)}
                print(f"❌ ML-Analyst 失败: {e}")
        else:
            ml_report = {"error": "ML-Analyst 未初始化"}
        
        # 第四阶段：共识汇总
        print(f"\n🔄 第四阶段: 共识汇总...")
        # 收集所有报告
        all_reports = {
            "stats": stats_report,
            "tactics": tactics_report,
            "sentiment": sentiment_report,
            "upset": upset_report,
            "asian": asian_report,
            "overunder": overunder_report,
            "ml": ml_report
        }
        
        # 设置预测器的报告（用于共识汇总）
        self.predictor.reports = all_reports
        consensus = self.predictor._run_consensus_summarizer(match_info)
        
        total_time = time.time() - total_start
        
        # 生成最终输出
        final_output = self.predictor._generate_final_output(match_info, consensus)
        prediction_dict = self.predictor._generate_prediction_dict(match_info, consensus)
        
        # 保存报告
        self.predictor._save_report(match_info, final_output)
        
        # 性能总结
        print(f"\n{'='*60}")
        print(f"📊 并行预测性能总结")
        print(f"{'='*60}")
        print(f"总耗时: {total_time:.2f}s")
        print(f"数据获取: {fetch_time:.2f}s ({fetch_time/total_time*100:.1f}%)")
        print(f"实时数据: {realtime_time:.2f}s ({realtime_time/total_time*100:.1f}%)")
        print(f"智能体阶段1: {stage1_time:.2f}s ({stage1_time/total_time*100:.1f}%)")
        print(f"智能体阶段2: {stage2_time:.2f}s ({stage2_time/total_time*100:.1f}%)")
        
        return prediction_dict


def test_parallel_predictor():
    """测试并行预测器"""
    import sys
    sys.path.append('.')
    
    test_match = ("BK Hacken", "GAIS", "soccer_sweden_allsvenskan")
    
    print("测试并行智能体预测器...")
    
    processor = ParallelMatchProcessor()
    
    start = time.time()
    result = processor.predict_parallel(*test_match)
    elapsed = time.time() - start
    
    print(f"\n⏱️  总耗时: {elapsed:.2f}秒")
    
    if result.get("success"):
        cons = result.get("consensus", {})
        print(f"✅ 预测成功")
        print(f"推荐: {cons.get('recommended_market', '?')} {cons.get('recommendation', '?')}")
        print(f"信心: {cons.get('confidence', 0):.1f}%")
    else:
        print(f"❌ 预测失败: {result.get('error', '未知错误')}")
    
    return result


if __name__ == "__main__":
    test_parallel_predictor()