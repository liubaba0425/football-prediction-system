#!/bin/bash
# 🏆 足球预测系统 — 完整打包脚本 (含历史报告)
# 在源电脑上运行：chmod +x pack_full.sh && ./pack_full.sh

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PKG="football_system_full_${TIMESTAMP}"
WORKDIR="${PWD}"

echo "=========================================="
echo "🏆 足球预测智能体系统 — 完整打包"
echo "=========================================="
echo "📦 打包目录: ${PKG}"
echo ""

mkdir -p "${PKG}"

# ── 1. 核心引擎 ──
echo "📋 拷贝核心引擎..."
CORE_FILES=(
    football_predictor.py   # 主预测器 (69KB)
    data_fetcher.py         # 数据抓取 + Bing新闻搜索
    team_translator.py      # 中英文队名翻译
    predict.py              # 单场预测CLI入口
    stats_analyst.py        # 统计分析师
    tactics_analyst.py      # 战术分析师
    config.py               # API密钥配置
    models.py               # 数据模型
    odds_client.py          # 赔率API客户端
    retry_utils.py          # 重试工具
    team_form_fetcher.py    # 球队状态抓取
    result_crawler.py       # 赛果爬虫
    result_crawler_7m.py    # 7m赛果爬虫
)

for f in "${CORE_FILES[@]}"; do
    if [ -f "$f" ]; then
        cp "$f" "${PKG}/"
    else
        echo "  ⚠️ 跳过(不存在): $f"
    fi
done

# ── 2. 批量/工具脚本 ──
echo "📋 拷贝工具脚本..."
TOOL_FILES=(
    batch_predict.py
    batch_parallel_predictor.py
    daily_predict.py
    export_excel.py
    enhanced_batch_predictor.py
    odds_tracker.py
    backtest_manager.py
    backtest_analysis.py
)

for f in "${TOOL_FILES[@]}"; do
    if [ -f "$f" ]; then
        cp "$f" "${PKG}/"
    fi
done

# ── 3. ML-Analyst 完整模块 ──
echo "📋 拷贝 ML-Analyst (模型+特征+数据)..."
if [ -d "ml_analyst" ]; then
    cp -r ml_analyst "${PKG}/"
    echo "  ✅ ml_analyst/ 完整拷贝 (含模型 $(du -sh ml_analyst/models/ | cut -f1))"
fi

# ── 4. 历史预测报告 (全部) ──
echo "📋 拷贝历史预测报告..."
mkdir -p "${PKG}/reports"
REPORT_COUNT=0
for f in prediction_*.txt; do
    if [ -f "$f" ]; then
        cp "$f" "${PKG}/reports/"
        REPORT_COUNT=$((REPORT_COUNT + 1))
    fi
done
echo "  ✅ ${REPORT_COUNT} 份历史报告"

# ── 5. 回测记录 ──
echo "📋 拷贝回测数据..."
if [ -f "backtest.csv" ]; then
    cp backtest.csv "${PKG}/"
    echo "  ✅ backtest.csv"
fi

# ── 6. 微信消息记录 ──
echo "📋 拷贝微信消息记录..."
mkdir -p "${PKG}/weixin_logs"
WEIXIN_COUNT=0
for f in weixin_message_*.txt; do
    if [ -f "$f" ]; then
        cp "$f" "${PKG}/weixin_logs/"
        WEIXIN_COUNT=$((WEIXIN_COUNT + 1))
    fi
done
echo "  ✅ ${WEIXIN_COUNT} 条微信消息"

# ── 7. 配置文件 ──
echo "📋 拷贝依赖配置..."
cp requirements.txt "${PKG}/" 2>/dev/null

# ── 8. 创建部署脚本 ──
echo "📋 生成目标电脑部署脚本..."
cat > "${PKG}/deploy.sh" << 'DEPLOY_EOF'
#!/bin/bash
# 🚀 足球预测系统 — 目标电脑一键部署
# 用法: chmod +x deploy.sh && ./deploy.sh

set -e

echo "=========================================="
echo "🚀 足球预测系统 — 一键部署"
echo "=========================================="

# 检查 Python
echo ""
echo "🔍 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYVER=$(python3 --version)
    echo "  ✅ ${PYVER}"
else
    echo "  ❌ 需要 Python 3.8+"
    exit 1
fi

# 创建虚拟环境 (可选)
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    echo "  ✅ venv 创建完成"
fi

echo ""
echo "📦 激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt

echo ""
echo "🔍 验证 ML 模型..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from ml_analyst.ml_analyst import MLAnalyst
    print('  ✅ ML-Analyst 模型加载成功')
except Exception as e:
    print(f'  ⚠️ ML-Analyst: {e}')
"

echo ""
echo "🔍 验证预测引擎..."
python3 -c "
from football_predictor import FootballPredictor
p = FootballPredictor()
print(f'  ✅ 预测引擎初始化成功')
print(f'  📡 API Key: {p.client.api_key[:8]}...{p.client.api_key[-4:]}')
"

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "🚀 快速测试:"
echo "  source venv/bin/activate"
echo "  python3 predict.py \"Manchester City\" \"Arsenal\" soccer_epl"
echo ""
echo "📋 历史报告: reports/ 目录 (${REPORT_COUNT} 份)"
echo "📊 回测数据: backtest.csv"
echo ""
DEPLOY_EOF

# ── 9. 创建 README ──
cat > "${PKG}/README_MIGRATION.txt" << 'README_EOF'
足球预测智能体系统 — 迁移包
================================

目录结构:
  *.py                  - 核心引擎文件
  ml_analyst/           - ML模型 + 特征 + 训练数据 (15MB)
  reports/              - 历史预测报告 (全部)
  weixin_logs/          - 微信推送记录
  backtest.csv          - 回测记录
  requirements.txt      - Python依赖
  deploy.sh             - 目标电脑一键部署脚本

迁移步骤:
  1. 将此目录打包传到目标电脑
  2. cd 到此目录
  3. chmod +x deploy.sh && ./deploy.sh
  4. source venv/bin/activate
  5. python3 predict.py "队名" "队名" league_key

注意事项:
  - API Key 已在 football_predictor.py 中配置 (无需重新设置)
  - 如果目标电脑架构不同 (M1/M2 vs Intel), 可能需要重新 pip install
  - 确保目标电脑有稳定网络连接 (需访问 the-odds-api.com)
README_EOF

# ── 10. 统计打包结果 ──
echo ""
echo "=========================================="
echo "📊 打包统计"
echo "=========================================="
PKG_SIZE=$(du -sh "${PKG}" | cut -f1)
FILE_COUNT=$(find "${PKG}" -type f | wc -l | tr -d ' ')
echo "  总大小: ${PKG_SIZE}"
echo "  文件数: ${FILE_COUNT}"
echo "  历史报告: ${REPORT_COUNT} 份"
echo "  微信记录: ${WEIXIN_COUNT} 条"

# ── 11. 压缩 ──
echo ""
echo "📦 压缩打包..."
tar -czf "${PKG}.tar.gz" "${PKG}"
TAR_SIZE=$(du -sh "${PKG}.tar.gz" | cut -f1)
echo "  ✅ ${PKG}.tar.gz (${TAR_SIZE})"

echo ""
echo "=========================================="
echo "✅ 打包完成！"
echo "=========================================="
echo ""
echo "📦 压缩包: ${WORKDIR}/${PKG}.tar.gz"
echo "📁 源目录: ${WORKDIR}/${PKG}/"
echo ""
echo "➡️  传输到目标电脑后执行:"
echo "   tar -xzf ${PKG}.tar.gz"
echo "   cd ${PKG}"
echo "   chmod +x deploy.sh && ./deploy.sh"
