#!/usr/bin/env python3
"""
历史数据收集脚本 - Phase 2
从football-data.org API批量下载比赛数据和积分榜数据
"""

import os
import sys
import logging
from datetime import datetime
import pandas as pd

# 添加项目根目录到路径以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_analyst.historical_data_fetcher import HistoricalDataFetcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Token (使用现有的football-data.org token)
API_TOKEN = "5ca663e49263467e8664864a767f8c31"

# 配置要下载的联赛和赛季
LEAGUES = [
    "PL",    # 英超
    "PD",    # 西甲
    "SA",    # 意甲
    "BL1",   # 德甲
    "FL1",   # 法甲
]

SEASONS = [2020, 2021, 2022, 2023, 2024]  # 5个赛季

def main():
    """主数据收集函数"""
    logger.info("=" * 60)
    logger.info("开始历史数据收集 (Phase 2)")
    logger.info("=" * 60)
    
    # 创建数据目录
    data_dir = "ml_analyst/data"
    os.makedirs(data_dir, exist_ok=True)
    
    # 初始化数据获取器
    fetcher = HistoricalDataFetcher(API_TOKEN)
    
    # 1. 下载比赛数据
    logger.info("步骤1: 下载比赛数据...")
    matches_df = fetcher.fetch_multiple_seasons(
        competition_codes=LEAGUES,
        start_season=min(SEASONS),
        end_season=max(SEASONS)
    )
    
    if matches_df.empty:
        logger.error("未能获取任何比赛数据")
        return False
        
    logger.info(f"成功获取 {len(matches_df)} 场比赛数据")
    
    # 保存比赛数据
    matches_file = os.path.join(data_dir, "historical_matches.parquet")
    fetcher.save_to_parquet(matches_df, matches_file)
    logger.info(f"比赛数据已保存至: {matches_file}")
    
    # 2. 下载积分榜数据
    logger.info("步骤2: 下载积分榜数据...")
    standings_df = fetcher.fetch_standings_multiple_seasons(
        competition_codes=LEAGUES,
        start_season=min(SEASONS),
        end_season=max(SEASONS)
    )
    
    if standings_df.empty:
        logger.error("未能获取任何积分榜数据")
    else:
        logger.info(f"成功获取 {len(standings_df)} 条球队积分榜记录")
        
        # 保存积分榜数据
        standings_file = os.path.join(data_dir, "historical_standings.parquet")
        fetcher.save_to_parquet(standings_df, standings_file)
        logger.info(f"积分榜数据已保存至: {standings_file}")
    
    # 3. 生成数据摘要报告
    logger.info("步骤3: 生成数据摘要报告...")
    generate_summary_report(matches_df, standings_df, data_dir)
    
    logger.info("=" * 60)
    logger.info("历史数据收集完成!")
    logger.info("=" * 60)
    
    return True

def generate_summary_report(matches_df: pd.DataFrame, standings_df: pd.DataFrame, data_dir: str):
    """生成数据摘要报告"""
    report_lines = []
    
    report_lines.append("=" * 60)
    report_lines.append("历史数据收集摘要报告")
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 60)
    
    # 比赛数据摘要
    report_lines.append("\n1. 比赛数据:")
    if not matches_df.empty:
        report_lines.append(f"   总比赛场次: {len(matches_df)}")
        report_lines.append(f"   时间范围: {matches_df['utc_date'].min()} 至 {matches_df['utc_date'].max()}")
        
        # 按联赛统计
        league_counts = matches_df['competition_code'].value_counts()
        report_lines.append("   按联赛分布:")
        for league, count in league_counts.items():
            report_lines.append(f"     {league}: {count} 场")
            
        # 按赛季统计
        if 'season_id' in matches_df.columns:
            season_counts = matches_df['season_id'].apply(lambda x: str(x)[:4] if x else '未知').value_counts()
            report_lines.append("   按赛季分布:")
            for season, count in season_counts.items():
                report_lines.append(f"     {season}: {count} 场")
    else:
        report_lines.append("   无比赛数据")
    
    # 积分榜数据摘要
    report_lines.append("\n2. 积分榜数据:")
    if not standings_df.empty:
        report_lines.append(f"   总球队记录: {len(standings_df)}")
        
        # 按联赛统计
        league_counts = standings_df['competition_code'].value_counts()
        report_lines.append("   按联赛分布:")
        for league, count in league_counts.items():
            report_lines.append(f"     {league}: {count} 条记录")
            
        # 按赛季统计
        if 'season' in standings_df.columns:
            season_counts = standings_df['season'].value_counts()
            report_lines.append("   按赛季分布:")
            for season, count in season_counts.items():
                report_lines.append(f"     {season}: {count} 条记录")
    else:
        report_lines.append("   无积分榜数据")
    
    # 数据质量检查
    report_lines.append("\n3. 数据质量检查:")
    if not matches_df.empty:
        # 检查缺失值
        missing_data = matches_df.isnull().sum()
        high_missing = missing_data[missing_data > 0]
        if len(high_missing) > 0:
            report_lines.append("   比赛数据缺失字段:")
            for field, count in high_missing.items():
                percentage = (count / len(matches_df)) * 100
                report_lines.append(f"     {field}: {count} 缺失 ({percentage:.1f}%)")
        else:
            report_lines.append("   比赛数据: 无显著缺失值")
    
    # 保存报告
    report_file = os.path.join(data_dir, "data_collection_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    logger.info(f"摘要报告已保存至: {report_file}")
    
    # 同时在控制台输出
    print('\n'.join(report_lines))

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("用户中断数据收集")
        sys.exit(1)
    except Exception as e:
        logger.error(f"数据收集过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)