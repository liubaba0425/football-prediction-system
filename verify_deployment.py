#!/usr/bin/env python3
"""
足球预测系统 — 部署完整性验证
用法: python3 verify_deployment.py
"""

import sys
import os
import importlib

PASS = 0
FAIL = 0
WARN = 0

def check(name, condition, detail=""):
    global PASS, FAIL, WARN
    if condition is True:
        print(f"  ✅ {name}")
        PASS += 1
    elif condition is False:
        print(f"  ❌ {name}  {detail}")
        FAIL += 1
    else:  # None or other = warning
        print(f"  ⚠️  {name}  {detail}")
        WARN += 1

def check_file(path, desc):
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    if exists and size > 0:
        check(desc, True)
    elif exists:
        check(desc, None, "(文件为空)")
    else:
        check(desc, False, f"(缺少: {path})")
    return exists

print("=" * 50)
print("🔍 足球预测系统 — 部署完整性验证")
print("=" * 50)

# ── 1. Python 环境 ──
print("\n📌 1. Python 环境")
ver = sys.version_info
check(f"Python {ver.major}.{ver.minor}.{ver.micro}", ver >= (3, 8))

# ── 2. 依赖包 ──
print("\n📌 2. 依赖包")
for pkg, import_name in [
    ("requests", "requests"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("xgboost", "xgboost"),
    ("sklearn", "sklearn"),
    ("openpyxl", "openpyxl"),
    ("pyarrow", "pyarrow"),
    ("yaml", "yaml"),
]:
    try:
        m = importlib.import_module(import_name)
        v = getattr(m, "__version__", "?")
        check(f"{pkg} {v}", True)
    except ImportError:
        check(pkg, False, "pip install 缺失")

# ── 3. 核心文件 ──
print("\n📌 3. 核心引擎文件")
core_files = {
    "football_predictor.py": "主预测器",
    "data_fetcher.py": "数据抓取+Bing搜索",
    "team_translator.py": "中英文队名翻译",
    "predict.py": "单场预测入口",
    "stats_analyst.py": "统计分析师",
    "tactics_analyst.py": "战术分析师",
    "config.py": "API密钥配置",
    "requirements.txt": "依赖清单",
}
for f, desc in core_files.items():
    check_file(f, f"{f} ({desc})")

# ── 4. ML模型和数据 ──
print("\n📌 4. ML-Analyst 模块")
ml_checks = {
    "ml_analyst/__init__.py": "ML模块入口",
    "ml_analyst/ml_analyst.py": "ML主逻辑",
    "ml_analyst/models/xgboost_v3_latest.json": "XGBoost模型",
    "ml_analyst/features/feature_list.txt": "特征列表",
    "ml_analyst/features/selected_features.parquet": "选定特征",
    "ml_analyst/data/historical_matches.parquet": "历史比赛数据",
}
for f, desc in ml_checks.items():
    check_file(f, f"{f} ({desc})")

# ── 5. ML模型加载测试 ──
print("\n📌 5. ML模型加载")
try:
    sys.path.insert(0, ".")
    from ml_analyst.ml_analyst import MLAnalyst
    ml = MLAnalyst()
    check("ML-Analyst 初始化", True, f"(模型已加载)")
except Exception as e:
    check("ML-Analyst 初始化", False, str(e)[:80])

# ── 6. 预测引擎初始化 ──
print("\n📌 6. 预测引擎")
try:
    from football_predictor import FootballPredictor
    p = FootballPredictor()
    key_len = len(p.client.api_key)
    check("FootballPredictor 初始化", True, f"(API Key: {key_len}字符)")
except Exception as e:
    check("FootballPredictor 初始化", False, str(e)[:80])

# ── 7. API Key ──
print("\n📌 7. API Key")
try:
    from football_predictor import OddsAPIClient
    c = OddsAPIClient()
    if c.api_key and len(c.api_key) == 32:
        check("API Key 格式", True, f"({c.api_key[:6]}...{c.api_key[-4:]})")
    else:
        check("API Key 格式", False, f"长度异常: {len(c.api_key)}")
except Exception as e:
    check("API Key 读取", False, str(e)[:80])

# ── 8. API连通性 (需要网络, 快速超时) ──
print("\n📌 8. API 连通性")
try:
    import requests
    from football_predictor import ODDS_API_KEY
    url = "https://api.the-odds-api.com/v4/sports/"
    resp = requests.get(url, params={"apiKey": ODDS_API_KEY}, timeout=8)
    if resp.status_code == 200:
        count = len(resp.json())
        check("The Odds API", True, f"({count}个体育项目可用)")
    elif resp.status_code == 401:
        check("The Odds API", False, "API Key无效(401)")
    else:
        check("The Odds API", None, f"HTTP {resp.status_code}")
except Exception as e:
    check("The Odds API", False, str(e)[:60])

# ── 9. 队名翻译 ──
print("\n📌 9. 队名翻译")
try:
    from team_translator import translate_team_name, TEAM_NAME_TRANSLATIONS
    total = sum(len(v) for v in TEAM_NAME_TRANSLATIONS.values()) if isinstance(TEAM_NAME_TRANSLATIONS, dict) else len(TEAM_NAME_TRANSLATIONS)
    check("翻译字典加载", True, f"(约{total}条)")
    # Test a known translation
    result = translate_team_name("Arsenal")
    check("翻译功能测试 (Arsenal→阿森纳)", "阿森纳" in str(result))
except Exception as e:
    check("队名翻译", False, str(e)[:80])

# ── 10. 历史报告 ──
print("\n📌 10. 历史数据")
import glob
reports = glob.glob("prediction_*.txt")
check(f"预测报告", True, f"({len(reports)}份)")

csv_exists = os.path.exists("backtest.csv")
check("回测数据 backtest.csv", csv_exists)

# ── 总结 ──
print("\n" + "=" * 50)
total = PASS + FAIL + WARN
print(f"📊 验证结果: {PASS}✅ / {FAIL}❌ / {WARN}⚠️  (共{total}项)")
print("=" * 50)

if FAIL == 0 and WARN == 0:
    print("\n🎉 部署完整！系统就绪，可以开始预测。")
    print("   试试: python3 predict.py \"Arsenal\" \"Chelsea\" soccer_epl")
elif FAIL == 0:
    print(f"\n⚠️  有 {WARN} 项警告，系统基本可用。")
else:
    print(f"\n❌ 有 {FAIL} 项失败，请根据上方提示修复。")

sys.exit(0 if FAIL == 0 else 1)
