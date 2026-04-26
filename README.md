# 🏆 足球预测智能体系统

基于多智能体架构的足球比赛预测分析系统，通过8个专业智能体协同工作，提供全面的比赛分析和推荐。

## 📋 系统架构

### 8个专业智能体

1. **Boss-Football** - 总协调者
   - 负责数据获取和流程调度
   - 不参与具体分析

2. **Stats-Analyst** - 统计数据分析师 (40%权重)
   - 分析隐含概率
   - 评估数据面结论

3. **Tactics-Analyst** - 战术分析师 (25%权重)
   - 阵型克制分析
   - 战术风格评估

4. **Sentiment-Analyst** - 市场情绪分析师 (20%权重)
   - 赔率趋势分析
   - 市场情绪判断

5. **Upset-Detector** - 冷门风险检测器 (15%权重)
   - 风险因素识别
   - 冷门概率评估

6. **Asian-Analyst** - 亚洲盘口分析师
   - 让球盘深度分析
   - 机构意图判断

7. **OverUnder-Analyst** - 大小球分析师
   - 进球数市场分析
   - 价值评估

8. **Consensus-Summarizer** - 共识汇总师
   - 加权共识计算
   - 最终推荐生成

## 🔄 运行流程

```
用户请求
    ↓
Boss-Football (数据获取)
    ↓
Stats-Analyst (统计分析)
    ↓
Tactics-Analyst (战术分析)
    ↓
Sentiment-Analyst (情绪分析)
    ↓
Upset-Detector (风险检测)
    ↓
Asian-Analyst (让球盘)
    ↓
OverUnder-Analyst (大小球)
    ↓
Consensus-Summarizer (共识汇总)
    ↓
最终输出
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `football_predictor.py`，将 `ODDS_API_KEY` 替换为你的 API Key：

```python
ODDS_API_KEY = "your_api_key_here"
```

获取 API Key: https://the-odds-api.com/

### 3. 运行预测

#### 交互式运行
```bash
python football_predictor.py
```

#### 命令行运行
```bash
# 英超
python predict.py "Manchester United" "Liverpool"

# 西甲
python predict.py "Barcelona" "Real Madrid" soccer_spain_la_liga

# 意甲
python predict.py "Juventus" "Inter Milan" soccer_italy_serie_a
```

## 📊 支持的联赛

| 代码 | 联赛 |
|:---|:---|
| soccer_epl | 英格兰超级联赛 |
| soccer_spain_la_liga | 西班牙甲级联赛 |
| soccer_germany_bundesliga | 德国甲级联赛 |
| soccer_italy_serie_a | 意大利甲级联赛 |
| soccer_france_ligue_one | 法国甲级联赛 |
| soccer_uefa_champs_league | 欧洲冠军联赛 |
| soccer_china_super_league | 中国足球超级联赛 |

## 📝 智能体配置

每个智能体的详细配置在对应的 `AGENTS.md` 文件中：

```
openclaw-workspace/
├── boss-football/
│   └── AGENTS.md
├── stats-analyst/
│   └── AGENTS.md
├── tactics-analyst/
│   └── AGENTS.md
├── sentiment-analyst/
│   └── AGENTS.md
├── upset-detector/
│   └── AGENTS.md
├── asian-analyst/
│   └── AGENTS.md
├── overunder-analyst/
│   └── AGENTS.md
└── consensus-summarizer/
    └── AGENTS.md
```

## ⚙️ 加权计算模型

### 基础权重
- Stats-Analyst: 40%
- Tactics-Analyst: 25%
- Sentiment-Analyst: 20%
- Upset-Detector: 15%

### 动态调整
当冷门风险分数 > 60 时：
- Upset-Detector 权重提升至 30%
- Stats-Analyst 权重降至 30%

### 计算公式
```
加权总分 = (Stats × 权重) + (Tactics × 权重) + (Sentiment × 权重) + ((100 - Upset风险) × 权重)
```

## ⚠️ 免责声明

本系统仅供娱乐和参考，不构成任何投注建议。
博彩有风险，投注需谨慎。
