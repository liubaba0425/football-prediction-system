# Odds API V4 使用指南

## 基本信息

**Base URL**: `https://api.the-odds-api.com/v4/`

## 主要端点

### 1. 获取比赛赔率 (GET odds)
```
GET /v4/sports/{sport}/odds/
```

**参数说明**:
| 参数 | 必填 | 说明 | 示例 |
|:---|:---|:---|:---|
| `apiKey` | ✅ | API密钥 | `c7af0126df9eb35c363065dcea447d8d` |
| `regions` | ✅ | 地区 | `us`, `uk`, `eu`, `au` |
| `markets` | ❌ | 市场类型 | `h2h,spreads,totals` |
| `oddsFormat` | ❌ | 赔率格式 | `american`, `decimal` |
| `bookmakers` | ❌ | 博彩公司筛选 | `pinnacle,bet365` |
| `dateFormat` | ❌ | 日期格式 | `iso`, `unix` |

**示例请求**:
```
https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=YOUR_KEY&regions=uk&markets=h2h,spreads,totals&oddsFormat=decimal
```

## 市场类型说明

| 市场键 | 说明 | 用途 |
|:---|:---|:---|
| `h2h` | 胜平负 | 主胜/平局/客胜赔率 |
| `spreads` | 让球盘 | 亚洲盘口让球 |
| `totals` | 大小球 | 总进球数盘口 |

## 响应数据结构

```json
[
  {
    "id": "比赛唯一ID",
    "sport_key": "soccer_epl",
    "sport_nice": "EPL",
    "commence_time": "2024-04-18T19:00:00Z",
    "home_team": "Chelsea",
    "away_team": "Manchester United",
    "bookmakers": [
      {
        "key": "pinnacle",
        "title": "Pinnacle",
        "last_update": "2024-04-17T10:00:00Z",
        "markets": [
          {
            "key": "h2h",
            "outcomes": [
              {"name": "Chelsea", "price": 2.10},
              {"name": "Draw", "price": 3.40},
              {"name": "Manchester United", "price": 3.50}
            ]
          },
          {
            "key": "spreads",
            "outcomes": [
              {"name": "Chelsea", "price": 1.95, "point": -0.5},
              {"name": "Manchester United", "price": 1.95, "point": 0.5}
            ]
          },
          {
            "key": "totals",
            "outcomes": [
              {"name": "Over", "price": 1.90, "point": 2.5},
              {"name": "Under", "price": 2.00, "point": 2.5}
            ]
          }
        ]
      }
    ]
  }
]
```

## 赔率格式

### Decimal (欧洲赔率)
- 示例: `2.10`
- 含义: 投注1元，赢了返回2.10元（含本金）
- 隐含概率 = 1 / 赔率

### American (美国赔率)
- 正数: `+150` 表示投注100元可赢150元
- 负数: `-200` 表示需要投注200元才能赢100元

## 常用足球联赛代码

| 代码 | 联赛 |
|:---|:---|
| `soccer_epl` | 英超 |
| `soccer_spain_la_liga` | 西甲 |
| `soccer_germany_bundesliga` | 德甲 |
| `soccer_italy_serie_a` | 意甲 |
| `soccer_france_ligue_one` | 法甲 |
| `soccer_uefa_champs_league` | 欧冠 |
| `soccer_uefa_europa_league` | 欧联 |

## 配额限制

- 每个请求根据返回的比赛数量消耗配额
- 免费账户每月500次请求
- 响应头 `x-requests-remaining` 显示剩余配额

## 最佳实践

1. **优先使用 Pinnacle**: 被认为是最准确的赔率源
2. **使用 decimal 格式**: 便于计算隐含概率
3. **筛选地区**: 使用 `regions=uk` 获取欧洲博彩公司
4. **缓存结果**: 避免重复请求相同数据

## 错误处理

| 状态码 | 说明 |
|:---|:---|
| 200 | 成功 |
| 401 | API Key 无效 |
| 422 | 请求参数错误 |
| 429 | 请求频率超限 |
