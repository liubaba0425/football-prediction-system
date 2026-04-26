#!/usr/bin/env python3
"""
增强版批处理并行预测器 - 整合所有优化：
1. 联赛数据缓存
2. 比赛间并行
3. 实时数据获取并行
4. 智能体内并行
"""
import concurrent.futures
import threading
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json
import sys
sys.path.append('.')

from parallel_agent_predictor import ParallelMatchProcessor
from football_predictor import translate_team_name


@dataclass
class MatchTask:
    """比赛任务"""
    home: str
    away: str
    league: str
    match_id: int = 0
    home_cn: str = ""
    away_cn: str = ""


class EnhancedBatchParallelPredictor:
    """增强版批处理并行预测器"""
    
    def __init__(self, max_match_workers: int = 3, use_cache: bool = True):
        """
        初始化
        
        Args:
            max_match_workers: 最大比赛并行数
            use_cache: 是否启用联赛数据缓存
        """
        self.max_match_workers = max_match_workers
        self.use_cache = use_cache
        self.league_cache = {}
        self.cache_lock = threading.Lock()
        
        # 新闻缓存（避免重复获取同一球队新闻）
        self.news_cache = {}
        self.news_cache_lock = threading.Lock()
    
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
    
    def _process_single_match_enhanced(self, task: MatchTask) -> Dict:
        """使用并行处理器处理单场比赛"""
        try:
            # 创建并行处理器
            processor = ParallelMatchProcessor()
            
            # 运行并行预测
            result = processor.predict_parallel(task.home, task.away, task.league)
            
            # 添加额外信息
            result["match_id"] = task.match_id
            result["home_cn"] = task.home_cn
            result["away_cn"] = task.away_cn
            
            return result
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "home": task.home,
                "away": task.away,
                "league": task.league,
                "match_id": task.match_id,
                "home_cn": task.home_cn,
                "away_cn": task.away_cn
            }
    
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
        print(f"🏆 增强版批处理并行预测系统启动")
        print(f"{'='*60}")
        print(f"📋 任务数量: {len(matches)}")
        print(f"⚙️  比赛间并行: {parallel} (最大工作线程: {self.max_match_workers})")
        print(f"📦 缓存启用: {self.use_cache}")
        
        # 准备任务
        tasks = self._prepare_match_tasks(matches)
        
        results = []
        start_total = time.time()
        
        if parallel and len(tasks) > 1:
            # 并行处理（比赛间并行）
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_match_workers) as executor:
                # 提交所有任务
                future_to_task = {
                    executor.submit(self._process_single_match_enhanced, task): task 
                    for task in tasks
                }
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result(timeout=180)  # 每场比赛最多180秒
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
                            "error": "处理超时 (180秒)",
                            "home": task.home,
                            "away": task.away,
                            "league": task.league,
                            "match_id": task.match_id,
                            "home_cn": task.home_cn,
                            "away_cn": task.away_cn
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
                            "match_id": task.match_id,
                            "home_cn": task.home_cn,
                            "away_cn": task.away_cn
                        }
                        results.append(error_result)
                        print(f"⚠️  异常: {task.home} vs {task.away}: {str(e)}")
        else:
            # 串行处理（用于调试或单场比赛）
            for task in tasks:
                print(f"\n📊 处理比赛 {task.match_id}/{len(tasks)}: "
                      f"{task.home_cn} vs {task.away_cn}")
                
                result = self._process_single_match_enhanced(task)
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
                error_short = error[:50] + "..." if len(error) > 50 else error
                report_lines.append(
                    f"{match_id:2d}. ❌ {home} vs {away}: 失败 - {error_short}"
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
    
    def save_results_json(self, results: List[Dict], filename: str = "enhanced_batch_predictions.json"):
        """保存结果到JSON文件"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 详细结果已保存到: {filename}")


def main():
    """使用示例"""
    # 示例比赛列表
    example_matches = [
        ("BK Hacken", "GAIS", "soccer_sweden_allsvenskan"),
        ("Sarpsborg FK", "Tromso", "soccer_norway_eliteserien"),
        ("AIK", "Kalmar FF", "soccer_sweden_allsvenskan"),
    ]
    
    print("测试增强版批处理并行预测器...")
    
    # 创建预测器
    predictor = EnhancedBatchParallelPredictor(max_match_workers=2, use_cache=True)
    
    # 运行批处理预测
    results = predictor.predict_batch(example_matches, parallel=True)
    
    # 生成汇总报告
    report = predictor.generate_summary_report(results)
    print("\n" + report)
    
    # 保存结果
    predictor.save_results_json(results)
    
    return results


if __name__ == "__main__":
    main()