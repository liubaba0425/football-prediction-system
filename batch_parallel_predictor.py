#!/usr/bin/env python3
"""
批处理并行足球预测器 - 重构为部分并行 + 批处理模式

主要优化：
1. 批处理数据获取：按联赛分组，一次性获取所有比赛数据
2. 比赛间并行：使用线程池并行处理不同比赛
3. 智能体内并行：独立智能体（Stats, Sentiment, OverUnder）可并行执行
4. 缓存机制：联赛数据缓存，避免重复API调用
"""
import concurrent.futures
import threading
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from queue import Queue
import json
import sys
sys.path.append('.')

from football_predictor import FootballPredictor, OddsAPIClient, translate_team_name
from team_translator import translate_team_name as translate_team_name_orig


@dataclass
class MatchTask:
    """比赛任务"""
    home: str
    away: str
    league: str
    match_id: int = 0
    home_cn: str = ""
    away_cn: str = ""


class BatchParallelPredictor:
    """批处理并行预测器"""
    
    def __init__(self, max_workers: int = 3, use_cache: bool = True):
        """
        初始化
        
        Args:
            max_workers: 并行工作线程数
            use_cache: 是否启用联赛数据缓存
        """
        self.max_workers = max_workers
        self.use_cache = use_cache
        self.league_cache = {}  # 联赛数据缓存：league -> 原始数据
        self.cache_lock = threading.Lock()
        self.client = OddsAPIClient()
        
        # 初始化单个预测器（用于模型加载）
        self.base_predictor = FootballPredictor()
        self.ml_analyst = self.base_predictor.ml_analyst
        self.data_fetcher = self.base_predictor.data_fetcher
        
        # 线程局部存储，每个线程有自己的预测器实例
        self.thread_local = threading.local()
    
    def _get_thread_predictor(self):
        """获取线程专用的预测器实例"""
        if not hasattr(self.thread_local, 'predictor'):
            # 创建新的预测器实例（避免线程安全问题）
            self.thread_local.predictor = FootballPredictor()
            # 共享ML-Analyst（如果线程安全的话）
            # 注意：如果ML-Analyst不是线程安全的，需要每个线程单独初始化
            self.thread_local.predictor.ml_analyst = self.ml_analyst
            self.thread_local.predictor.data_fetcher = self.data_fetcher
        return self.thread_local.predictor
    
    def _fetch_league_data_batch(self, league: str) -> List[Dict]:
        """
        批量获取联赛数据（带缓存）
        
        Args:
            league: 联赛标识
            
        Returns:
            联赛所有比赛数据
        """
        if self.use_cache:
            with self.cache_lock:
                if league in self.league_cache:
                    print(f"📦 使用缓存数据: {league}")
                    return self.league_cache[league]
        
        print(f"🌐 获取联赛数据: {league}")
        start_time = time.time()
        data = self.client.fetch_match_odds(league)
        elapsed = time.time() - start_time
        
        if data:
            print(f"✅ 获取到 {len(data)} 场比赛数据 (耗时: {elapsed:.1f}s)")
            if self.use_cache:
                with self.cache_lock:
                    self.league_cache[league] = data
        else:
            print(f"⚠️  未获取到数据: {league}")
        
        return data
    
    def _extract_match_data(self, league_data: List[Dict], home: str, away: str) -> Optional[Dict]:
        """从联赛数据中提取特定比赛数据"""
        return self.client.find_match(league_data, home, away)
    
    def _process_single_match(self, match: MatchTask) -> Dict:
        """
        处理单场比赛（线程安全）
        
        Args:
            match: 比赛任务
            
        Returns:
            预测结果
        """
        predictor = self._get_thread_predictor()
        
        try:
            # 获取联赛数据（可能从缓存）
            league_data = self._fetch_league_data_batch(match.league)
            
            if not league_data:
                return {
                    "success": False,
                    "error": f"未找到联赛数据: {match.league}",
                    "home": match.home,
                    "away": match.away,
                    "league": match.league,
                    "match_id": match.match_id
                }
            
            # 提取特定比赛数据
            match_data = self._extract_match_data(league_data, match.home, match.away)
            
            if not match_data:
                return {
                    "success": False,
                    "error": f"未找到比赛: {match.home} vs {match.away}",
                    "home": match.home,
                    "away": match.away,
                    "league": match.league,
                    "match_id": match.match_id
                }
            
            # 使用预测器的预测方法
            # 注意：这里仍然使用串行预测，但不同比赛之间是并行的
            # 未来可以进一步优化为智能体级别的并行
            result = predictor.predict(match.home, match.away, match.league)
            
            # 添加额外信息
            result["match_id"] = match.match_id
            result["home_cn"] = match.home_cn or translate_team_name(match.home)
            result["away_cn"] = match.away_cn or translate_team_name(match.away)
            
            return result
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "home": match.home,
                "away": match.away,
                "league": match.league,
                "match_id": match.match_id
            }
    
    def _prepare_match_tasks(self, matches: List[Tuple[str, str, str]]) -> List[MatchTask]:
        """准备比赛任务列表"""
        tasks = []
        for idx, (home, away, league) in enumerate(matches):
            home_cn = translate_team_name(home)
            away_cn = translate_team_name(away)
            task = MatchTask(
                home=home,
                away=away,
                league=league,
                match_id=idx + 1,
                home_cn=home_cn,
                away_cn=away_cn
            )
            tasks.append(task)
        return tasks
    
    def predict_batch(self, matches: List[Tuple[str, str, str]], 
                     parallel: bool = True) -> List[Dict]:
        """
        批量预测
        
        Args:
            matches: 比赛列表，每个元素为 (home, away, league)
            parallel: 是否并行处理
            
        Returns:
            预测结果列表
        """
        print(f"\n{'='*60}")
        print(f"🏆 批处理并行预测系统启动")
        print(f"{'='*60}")
        print(f"📋 任务数量: {len(matches)}")
        print(f"⚙️  并行模式: {parallel} (最大工作线程: {self.max_workers})")
        print(f"📦 缓存启用: {self.use_cache}")
        
        # 准备任务
        tasks = self._prepare_match_tasks(matches)
        
        results = []
        start_total = time.time()
        
        if parallel and len(tasks) > 1:
            # 并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_task = {
                    executor.submit(self._process_single_match, task): task 
                    for task in tasks
                }
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result(timeout=120)  # 每场比赛最多120秒
                        results.append(result)
                        
                        # 打印进度
                        success = result.get("success", False)
                        status = "✅" if success else "❌"
                        print(f"{status} 完成: {task.home_cn} vs {task.away_cn} "
                              f"(ID: {task.match_id})")
                        
                        if not success:
                            print(f"   错误: {result.get('error', '未知错误')}")
                            
                    except concurrent.futures.TimeoutError:
                        error_result = {
                            "success": False,
                            "error": "处理超时 (120秒)",
                            "home": task.home,
                            "away": task.away,
                            "league": task.league,
                            "match_id": task.match_id
                        }
                        results.append(error_result)
                        print(f"⏱️  超时: {task.home} vs {task.away}")
                        
                    except Exception as e:
                        error_result = {
                            "success": False,
                            "error": f"处理异常: {str(e)}",
                            "home": task.home,
                            "away": task.away,
                            "league": task.league,
                            "match_id": task.match_id
                        }
                        results.append(error_result)
                        print(f"⚠️  异常: {task.home} vs {task.away}: {str(e)}")
        else:
            # 串行处理（用于调试或单场比赛）
            for task in tasks:
                print(f"\n📊 处理比赛 {task.match_id}/{len(tasks)}: "
                      f"{task.home_cn} vs {task.away_cn}")
                
                result = self._process_single_match(task)
                results.append(result)
                
                success = result.get("success", False)
                status = "✅" if success else "❌"
                print(f"{status} 完成: {task.home_cn} vs {task.away_cn}")
                
                if not success:
                    print(f"   错误: {result.get('error', '未知错误')}")
        
        total_time = time.time() - start_total
        print(f"\n{'='*60}")
        print(f"📊 批量预测完成")
        print(f"{'='*60}")
        print(f"⏱️  总耗时: {total_time:.1f}秒")
        print(f"📈 平均每场: {total_time/len(tasks):.1f}秒")
        
        success_count = sum(1 for r in results if r.get("success", False))
        print(f"✅ 成功: {success_count}/{len(tasks)}")
        print(f"❌ 失败: {len(tasks) - success_count}/{len(tasks)}")
        
        return results
    
    def generate_summary_report(self, results: List[Dict]) -> str:
        """生成汇总报告"""
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("📊 批处理预测汇总报告")
        report_lines.append("=" * 60)
        
        for result in results:
            match_id = result.get("match_id", 0)
            home = result.get("home_cn", result.get("home", "未知"))
            away = result.get("away_cn", result.get("away", "未知"))
            success = result.get("success", False)
            
            if success:
                consensus = result.get("consensus", {})
                recommendation = consensus.get("recommendation", "未知")
                confidence = consensus.get("confidence", 0)
                market = consensus.get("recommended_market", "未知")
                
                report_lines.append(
                    f"{match_id:2d}. ✅ {home} vs {away}: "
                    f"{market} {recommendation} (信心: {confidence:.1f}%)"
                )
            else:
                error = result.get("error", "未知错误")
                report_lines.append(
                    f"{match_id:2d}. ❌ {home} vs {away}: 失败 - {error}"
                )
        
        # 高信心推荐
        high_confidence = []
        for result in results:
            if result.get("success", False):
                consensus = result.get("consensus", {})
                confidence = consensus.get("confidence", 0)
                if confidence >= 55:
                    home = result.get("home_cn", result.get("home", "未知"))
                    away = result.get("away_cn", result.get("away", "未知"))
                    recommendation = consensus.get("recommendation", "未知")
                    market = consensus.get("recommended_market", "未知")
                    high_confidence.append(
                        (confidence, f"{home} vs {away}: {market} {recommendation}")
                    )
        
        if high_confidence:
            report_lines.append("\n🎯 高信心推荐 (信心 ≥ 55%):")
            high_confidence.sort(reverse=True)
            for confidence, desc in high_confidence:
                report_lines.append(f"   • {desc} (信心: {confidence:.1f}%)")
        
        report_lines.append("\n" + "=" * 60)
        return "\n".join(report_lines)


# 使用示例
def main():
    """使用示例"""
    # 示例比赛列表
    example_matches = [
        ("BK Hacken", "GAIS", "soccer_sweden_allsvenskan"),
        ("Sarpsborg FK", "Tromso", "soccer_norway_eliteserien"),
        ("AIK", "Kalmar FF", "soccer_sweden_allsvenskan"),
    ]
    
    print("测试批处理并行预测器...")
    
    # 创建预测器
    predictor = BatchParallelPredictor(max_workers=2, use_cache=True)
    
    # 运行批处理预测
    results = predictor.predict_batch(example_matches, parallel=True)
    
    # 生成汇总报告
    report = predictor.generate_summary_report(results)
    print("\n" + report)
    
    # 保存结果
    with open("batch_predictions.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("💾 详细结果已保存到: batch_predictions.json")


if __name__ == "__main__":
    main()