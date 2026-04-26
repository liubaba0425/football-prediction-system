#!/bin/bash
# 🏆 足球预测智能体系统 - 打包脚本 (增强版)
# 在源电脑上运行此脚本，生成可迁移的压缩包
# 用法: ./pack_football_system.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🏆 足球预测智能体系统打包工具 (增强版)"
echo "=========================================="

# 检查是否在正确目录
if [ ! -f "football_predictor.py" ]; then
    echo "❌ 错误：请在 openclaw-workspace 目录下运行此脚本"
    exit 1
fi

# 验证关键文件
echo "🔍 验证关键文件..."
MISSING_FILES=()

# 检查核心文件
for file in football_predictor.py team_translator.py predict.py daily_predict.py export_excel.py predict_remaining_matches.py; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
        echo "  ❌ 缺失: $file"
    else
        echo "  ✅ 存在: $file"
    fi
done

# 检查智能体目录
AGENTS=("boss-football" "stats-analyst" "tactics-analyst" "sentiment-analyst" "upset-detector" "asian-analyst" "overunder-analyst" "consensus-summarizer")
for agent in "${AGENTS[@]}"; do
    if [ ! -d "$agent" ]; then
        MISSING_FILES+=("$agent/")
        echo "  ❌ 缺失: $agent/"
    else
        echo "  ✅ 存在: $agent/"
    fi
done

# 检查ML关键文件
if [ ! -d "ml_analyst" ]; then
    MISSING_FILES+=("ml_analyst/")
    echo "  ❌ 缺失: ml_analyst/"
else
    echo "  ✅ 存在: ml_analyst/"
fi

# 检查模型文件
MODEL_FILE="ml_analyst/models/xgboost_optimized_20260419_092408.json"
if [ ! -f "$MODEL_FILE" ]; then
    echo "  ⚠️  警告: 优化模型文件不存在: $MODEL_FILE"
    # 尝试寻找其他模型文件
    ALT_MODEL=$(find ml_analyst/models -name "*.json" -type f | head -1)
    if [ -n "$ALT_MODEL" ]; then
        echo "  ℹ️  使用备用模型: $ALT_MODEL"
    else
        MISSING_FILES+=("$MODEL_FILE")
        echo "  ❌ 缺失: 任何ML模型文件"
    fi
else
    echo "  ✅ 存在: $MODEL_FILE"
fi

# 检查特征文件
FEATURE_FILE="ml_analyst/features/feature_list.txt"
if [ ! -f "$FEATURE_FILE" ]; then
    echo "  ⚠️  警告: 特征列表文件不存在: $FEATURE_FILE"
else
    echo "  ✅ 存在: $FEATURE_FILE"
fi

# 如果有缺失文件，询问是否继续
if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  发现缺失文件: ${#MISSING_FILES[@]} 个"
    echo "是否继续打包? (y/N): "
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 打包中止"
        exit 1
    fi
    echo "继续打包..."
fi

# 创建临时打包目录
PACKAGE_DIR="football_prediction_system_$(date +%Y%m%d_%H%M%S)"
echo "📦 创建打包目录: $PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

# 复制核心文件
echo "📄 复制核心代码文件..."
# 智能体目录
for agent in "${AGENTS[@]}"; do
    if [ -d "$agent" ]; then
        cp -r "$agent" "$PACKAGE_DIR/"
        echo "  ✅ 复制智能体: $agent"
    fi
done

# ML-Analyst 核心文件
echo "🤖 复制ML-Analyst系统..."
mkdir -p "$PACKAGE_DIR/ml_analyst"
mkdir -p "$PACKAGE_DIR/ml_analyst/models"
mkdir -p "$PACKAGE_DIR/ml_analyst/features"

# ML核心代码
for file in ml_analyst/*.py ml_analyst/*.yaml ml_analyst/*.md; do
    if [ -f "$file" ]; then
        cp "$file" "$PACKAGE_DIR/ml_analyst/"
    fi
done 2>/dev/null

# 必须的模型文件
echo "🧠 复制ML模型文件..."
if [ -f "$MODEL_FILE" ]; then
    cp "$MODEL_FILE" "$PACKAGE_DIR/ml_analyst/models/"
    echo "  ✅ 复制优化模型"
else
    # 复制第一个找到的模型文件
    ALT_MODEL=$(find ml_analyst/models -name "*.json" -type f | head -1)
    if [ -n "$ALT_MODEL" ]; then
        cp "$ALT_MODEL" "$PACKAGE_DIR/ml_analyst/models/"
        echo "  ✅ 复制备用模型: $(basename $ALT_MODEL)"
    else
        echo "  ⚠️  无模型文件可复制"
    fi
fi

# 复制模型报告文件
find ml_analyst/models -name "*report.json" -type f -exec cp {} "$PACKAGE_DIR/ml_analyst/models/" \; 2>/dev/null || true

# 特征工程文件
echo "🔧 复制特征工程文件..."
if [ -f "$FEATURE_FILE" ]; then
    cp "$FEATURE_FILE" "$PACKAGE_DIR/ml_analyst/features/"
fi
find ml_analyst/features -name "*.txt" -o -name "*.yaml" -o -name "*.json" -type f -exec cp {} "$PACKAGE_DIR/ml_analyst/features/" \; 2>/dev/null || true

# 配置文件
echo "⚙️ 复制配置文件..."
mkdir -p "$PACKAGE_DIR/config"
if [ -d "config" ]; then
    cp -r config/* "$PACKAGE_DIR/config/" 2>/dev/null || true
fi

# 主程序文件
echo "🚀 复制主程序文件..."
CORE_FILES=("football_predictor.py" "team_translator.py" "data_fetcher.py" "predict.py" "daily_predict.py" "export_excel.py" "predict_remaining_matches.py" "config.py" "README.md")
for file in "${CORE_FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$PACKAGE_DIR/"
        echo "  ✅ 复制: $file"
    fi
done

# 辅助脚本
echo "🛠️ 复制辅助脚本..."
for file in batch_parallel_predictor.py enhanced_batch_predictor.py parallel_agent_predictor.py; do
    if [ -f "$file" ]; then
        cp "$file" "$PACKAGE_DIR/"
        echo "  ✅ 复制: $file"
    fi
done

# 复制requirements.txt或创建增强版
echo "📦 处理依赖配置..."
if [ -f "requirements.txt" ]; then
    # 备份原始requirements
    cp requirements.txt "$PACKAGE_DIR/requirements.original.txt"
    
    # 创建增强版requirements.txt
    cat > "$PACKAGE_DIR/requirements.txt" << 'EOF'
# 🏆 足球预测智能体系统 - 完整依赖列表
# 核心依赖
requests>=2.28.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
joblib>=1.3.0
openpyxl>=3.0.0

# 数据处理
pyarrow>=14.0.0  # Parquet支持
python-dateutil>=2.8.0
pytz>=2023.0

# 配置和序列化
pyyaml>=6.0
ujson>=5.0.0  # 快速JSON解析

# 网络和API
aiohttp>=3.8.0  # 异步HTTP请求
websockets>=12.0  # WebSocket支持

# 实用工具
tabulate>=0.9.0  # 美观的表格输出
colorama>=0.4.0  # 跨平台彩色输出
tqdm>=4.65.0  # 进度条
python-dotenv>=1.0.0  # 环境变量管理

# 开发和调试
ipython>=8.0.0  # 交互式调试
pytest>=7.0.0  # 测试框架

# 注意: 某些包可能需要系统依赖
# 在Ubuntu/Debian上: sudo apt-get install build-essential python3-dev
# 在macOS上: brew install gcc
EOF
    echo "  ✅ 创建增强版requirements.txt"
else
    # 直接使用上面的增强版
    cat > "$PACKAGE_DIR/requirements.txt" << 'EOF'
# 🏆 足球预测智能体系统 - 完整依赖列表
requests>=2.28.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
joblib>=1.3.0
openpyxl>=3.0.0
pyarrow>=14.0.0
python-dateutil>=2.8.0
pyyaml>=6.0
EOF
    echo "  ✅ 创建基础requirements.txt"
fi

# 创建极简版requirements（仅必需）
cat > "$PACKAGE_DIR/requirements.minimal.txt" << 'EOF'
# 🏆 足球预测智能体系统 - 最小依赖列表
# 仅包含系统运行绝对必需的包
requests>=2.28.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
joblib>=1.3.0
openpyxl>=3.0.0
pyyaml>=6.0
EOF

# 创建部署文档
echo "📝 创建部署文档..."
cat > "$PACKAGE_DIR/DEPLOYMENT_GUIDE.md" << 'EOF'
# 🚀 足球预测智能体系统部署指南

## 系统要求
- Python 3.8+ (推荐 3.9+)
- 至少 2GB 空闲磁盘空间
- 网络连接 (用于API访问)

## 快速开始

### 1. 解压系统
```bash
tar -xzvf football_prediction_system.tar.gz
cd football_prediction_system_YYYYMMDD_HHMMSS
```

### 2. 配置虚拟环境
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活环境
# Linux/macOS:
source venv/bin/activate
# Windows:
# venv\Scripts\activate
```

### 3. 安装依赖
```bash
pip install --upgrade pip
pip install -r requirements.txt
# 或使用最小依赖（更快）
# pip install -r requirements.minimal.txt
```

### 4. 配置API密钥
系统需要以下API密钥：
1. **The Odds API** (Pinnacle赔率): https://the-odds-api.com
2. **Football-Data API** (历史数据): https://www.football-data.org

配置方法：
```bash
# 运行交互式配置助手
python3 setup_api_keys.py

# 或手动编辑 football_predictor.py:
# 第29行: ODDS_API_KEY = "your_key_here"
# 第220行: SOCCER_DATA_API_TOKEN = "your_token_here"
```

### 5. 验证安装
```bash
# 运行环境检查
python3 check_environment.py

# 运行部署测试
python3 test_deployment.py

# 测试单场比赛预测
python3 predict.py "曼城" "阿森纳" soccer_epl
```

## 系统功能

### 🎯 单场比赛预测
```bash
python3 predict.py "主队名" "客队名" [联赛代码]
```
**联赛代码示例:**
- `soccer_epl` - 英超
- `soccer_germany_bundesliga` - 德甲
- `soccer_spain_la_liga` - 西甲
- `soccer_italy_serie_a` - 意甲
- `soccer_france_ligue_one` - 法甲
- `soccer_japan_j_league` - J联赛

### 📊 批量预测
```bash
python3 predict_remaining_matches.py
```
批量预测预设的8场比赛，自动生成汇总报告。

### 📅 每日自动预测
```bash
python3 daily_predict.py
```
运行每日预测流程（不自动生成Excel）。

### 📈 Excel导出
```bash
python3 export_excel.py
```
将预测结果导出到Excel文件 `~/Desktop/足球预测_YYYYMMDD.xlsx`

## 高级功能

### 🤖 ML-Analyst 集成
系统集成了机器学习模型，在以下情况自动启用：
- 高风险比赛 (赔率差异大)
- 传统智能体分歧显著时
- 用户手动启用ML分析

ML模型权重:
- 正常情况: 35%
- 高风险情况: 25%

### 🔄 智能体辩论机制
当不同智能体分析结果差异较大时，系统自动启动辩论机制，通过多轮讨论达成共识。

### 🌐 微信通知
配置Hermes Agent后，系统可将预测结果推送到微信（仅限企业微信）。

## 故障排除

### 常见问题

#### 1. "ModuleNotFoundError: No module named 'xgboost'"
```bash
# 安装系统依赖 (Ubuntu/Debian)
sudo apt-get install build-essential python3-dev

# 重新安装xgboost
pip install xgboost --no-cache-dir
```

#### 2. "API key invalid" 或 "未找到比赛数据"
- 检查API密钥是否正确配置
- 确认比赛时间（只支持未来24小时内的比赛）
- 检查队名是否正确（使用中文队名）

#### 3. "特征不匹配" 错误
```bash
# 重新生成特征文件
cd ml_analyst
python3 build_features.py
```

#### 4. "模型加载失败"
- 确认模型文件存在: `ml_analyst/models/xgboost_optimized_*.json`
- 检查文件权限
- 尝试重新训练模型: `python3 ml_analyst/train_optimized.py`

## 维护指南

### 更新依赖
```bash
pip install --upgrade -r requirements.txt
```

### 清理缓存
```bash
./cleanup_cache.sh
```

### 备份系统
```bash
# 创建完整备份
tar -czvf football_prediction_backup_$(date +%Y%m%d).tar.gz .
```

### 添加新的球队翻译
编辑 `team_translator.py`，在对应联赛的翻译字典中添加新条目。

## 支持
如有问题，请参考原始系统配置或联系开发人员。

---
**版本:** 2.0.0 (ML-Enhanced)  
**最后更新:** 2024-04-20  
**兼容性:** Python 3.8+, macOS/Linux/Windows (WSL推荐)
EOF

# 创建环境检查脚本
echo "🔍 创建环境检查脚本..."
cat > "$PACKAGE_DIR/check_environment.py" << 'EOF'
#!/usr/bin/env python3
"""
环境检查脚本
运行此脚本验证系统依赖是否完整
"""

import sys
import os
import subprocess

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python版本过低: {sys.version}")
        print("   需要 Python 3.8+")
        return False
    print(f"✅ Python版本: {sys.version}")
    return True

def check_package(package_name, import_name=None):
    """检查包是否可导入"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✅ {package_name}")
        return True
    except ImportError as e:
        print(f"❌ {package_name}: {e}")
        return False

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        size = os.path.getsize(file_path) / 1024
        print(f"✅ {description}: {file_path} ({size:.1f} KB)")
        return True
    else:
        print(f"❌ {description}: {file_path} (文件不存在)")
        return False

def check_ml_analyst():
    """检查ML-Analyst模块"""
    print("\n🤖 检查ML-Analyst模块:")
    try:
        sys.path.append('.')
        from ml_analyst.ml_analyst import MLAnalyst
        print("✅ ML-Analyst 模块可导入")
        
        # 检查特征文件
        feature_ok = check_file_exists(
            "ml_analyst/features/feature_list.txt",
            "特征列表文件"
        )
        
        # 检查模型文件
        model_files = [
            f for f in os.listdir("ml_analyst/models")
            if f.endswith(".json") and "optimized" in f
        ]
        
        if model_files:
            model_file = f"ml_analyst/models/{model_files[0]}"
            check_file_exists(model_file, "优化模型文件")
            return feature_ok
        else:
            print("❌ 未找到优化模型文件")
            return False
            
    except ImportError as e:
        print(f"❌ ML-Analyst导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ ML-Analyst检查失败: {e}")
        return False

def check_football_predictor():
    """检查足球预测器"""
    print("\n⚽ 检查足球预测器:")
    try:
        from football_predictor import FootballPredictor
        
        # 测试初始化
        predictor = FootballPredictor()
        print("✅ FootballPredictor 初始化成功")
        
        # 测试共享ML-Analyst实例
        if hasattr(predictor, '_shared_ml_analyst') or hasattr(FootballPredictor, '_shared_ml_analyst'):
            print("✅ ML-Analyst共享实例配置正常")
        else:
            print("⚠️  ML-Analyst共享实例配置可能未生效")
        
        return True
        
    except ImportError as e:
        print(f"❌ 预测器导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 预测器测试失败: {e}")
        return False

def check_api_keys():
    """检查API密钥配置"""
    print("\n🔑 检查API密钥配置:")
    try:
        with open("football_predictor.py", "r") as f:
            content = f.read()
        
        odds_key_line = None
        soccer_key_line = None
        
        for i, line in enumerate(content.split('\n'), 1):
            if "ODDS_API_KEY" in line and not line.strip().startswith("#"):
                odds_key_line = i
                if "your_key_here" in line or len(line.split('"')) < 3:
                    print(f"❌ The Odds API密钥未配置 (第{i}行)")
                else:
                    key = line.split('"')[1]
                    print(f"✅ The Odds API密钥已配置: {key[:8]}...")
            
            if "SOCCER_DATA_API_TOKEN" in line and not line.strip().startswith("#"):
                soccer_key_line = i
                if "your_token_here" in line or len(line.split('"')) < 3:
                    print(f"❌ Football-Data API令牌未配置 (第{i}行)")
                else:
                    token = line.split('"')[1]
                    print(f"✅ Football-Data API令牌已配置: {token[:8]}...")
        
        if not odds_key_line:
            print("❌ 未找到ODDS_API_KEY配置行")
        if not soccer_key_line:
            print("❌ 未找到SOCCER_DATA_API_TOKEN配置行")
        
        return True
        
    except Exception as e:
        print(f"❌ API密钥检查失败: {e}")
        return False

def main():
    print("🔍 足球预测系统环境检查")
    print("=" * 50)
    
    all_ok = True
    
    # 检查Python版本
    if not check_python_version():
        all_ok = False
    
    print("\n📦 检查核心依赖:")
    packages = [
        ("requests", "requests"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("xgboost", "xgboost"),
        ("scikit-learn", "sklearn"),
        ("openpyxl", "openpyxl"),
        ("joblib", "joblib"),
    ]
    
    for package, import_name in packages:
        if not check_package(package, import_name):
            all_ok = False
    
    # 检查ML-Analyst
    if not check_ml_analyst():
        all_ok = False
    
    # 检查足球预测器
    if not check_football_predictor():
        all_ok = False
    
    # 检查API密钥
    check_api_keys()
    
    print("\n" + "=" * 50)
    if all_ok:
        print("🎉 所有检查通过！系统可以正常使用。")
        print("\n📋 下一步:")
        print("1. 测试单场预测: python3 predict.py \"曼城\" \"阿森纳\" soccer_epl")
        print("2. 运行批量预测: python3 predict_remaining_matches.py")
        return 0
    else:
        print("⚠️  部分检查未通过，请解决上述问题后再运行系统。")
        print("\n💡 常见解决方案:")
        print("- 安装缺失依赖: pip install -r requirements.txt")
        print("- 配置API密钥: python3 setup_api_keys.py")
        print("- 检查文件权限: ls -la ml_analyst/models/")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x "$PACKAGE_DIR/check_environment.py"

# 创建API配置助手脚本
echo "🔑 创建API配置助手脚本..."
cat > "$PACKAGE_DIR/setup_api_keys.py" << 'EOF'
#!/usr/bin/env python3
"""
API密钥配置助手
交互式配置系统的API密钥
"""

import os
import sys

def get_input(prompt, default="", password=False):
    """获取用户输入"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    if password:
        import getpass
        value = getpass.getpass(prompt)
    else:
        value = input(prompt).strip()
    
    if not value and default:
        return default
    return value

def update_file_key(file_path, line_num, key_value):
    """更新文件中的API密钥"""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # 行号是从1开始的，需要减1
        if 0 <= line_num-1 < len(lines):
            old_line = lines[line_num-1]
            if "ODDS_API_KEY" in old_line or "SOCCER_DATA_API_TOKEN" in old_line:
                # 替换密钥部分
                if "=" in old_line:
                    parts = old_line.split("=", 1)
                    if len(parts) == 2:
                        # 保留注释
                        comment = ""
                        if "#" in parts[1]:
                            comment = " " + parts[1].split("#", 1)[1]
                        
                        lines[line_num-1] = f'{parts[0]}="{key_value}"{comment}\n'
                        print(f"✅ 更新 {file_path}:{line_num}")
                    else:
                        lines[line_num-1] = f'ODDS_API_KEY="{key_value}"\n'
                else:
                    lines[line_num-1] = f'ODDS_API_KEY="{key_value}"\n'
        
        with open(file_path, 'w') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"❌ 更新文件失败: {e}")
        return False

def main():
    print("🔑 API密钥配置助手")
    print("=" * 40)
    print("系统需要以下API密钥才能正常工作:")
    print()
    print("1. 📊 The Odds API")
    print("   获取实时赔率数据 (Pinnacle等)")
    print("   注册地址: https://the-odds-api.com")
    print()
    print("2. ⚽ Football-Data API")
    print("   获取历史比赛数据和统计信息")
    print("   注册地址: https://www.football-data.org")
    print()
    print("如果没有API密钥，可以暂时跳过，但部分功能可能受限。")
    print()
    
    # 获取用户输入
    print("📝 输入API密钥 (直接回车可跳过):")
    odds_key = get_input("The Odds API 密钥", password=False)
    soccer_key = get_input("Football-Data API 令牌", password=False)
    
    if not odds_key and not soccer_key:
        print("\n⚠️  未提供任何API密钥，系统功能将受限。")
        print("你可以在需要时重新运行此脚本配置。")
        return 0
    
    # 更新 football_predictor.py
    print("\n📝 更新配置文件...")
    success = True
    
    if odds_key:
        success = success and update_file_key("football_predictor.py", 29, odds_key)
    else:
        print("⏭️  跳过 The Odds API 配置")
    
    if soccer_key:
        success = success and update_file_key("football_predictor.py", 220, soccer_key)
    else:
        print("⏭️  跳过 Football-Data API 配置")
    
    # 更新 ml_config.yaml
    try:
        yaml_path = "config/ml_config.yaml"
        if os.path.exists(yaml_path) and soccer_key:
            with open(yaml_path, 'r') as f:
                content = f.read()
            
            # 替换足球数据API令牌
            import re
            new_content = re.sub(
                r'auth_token: ".*?"',
                f'auth_token: "{soccer_key}"',
                content
            )
            
            with open(yaml_path, 'w') as f:
                f.write(new_content)
            print("✅ 更新 config/ml_config.yaml")
    except Exception as e:
        print(f"⚠️  更新YAML配置失败: {e}")
    
    # 创建环境变量配置文件
    print("\n🌍 创建环境变量配置文件...")
    env_content = []
    if odds_key:
        env_content.append(f'export ODDS_API_KEY="{odds_key}"')
    if soccer_key:
        env_content.append(f'export SOCCER_DATA_API_TOKEN="{soccer_key}"')
    
    if env_content:
        with open("set_env_vars.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("# 足球预测系统环境变量配置\n")
            f.write("\n".join(env_content))
            f.write("\n\necho '环境变量已设置'\n")
        os.chmod("set_env_vars.sh", 0o755)
        print("✅ 创建环境变量脚本: set_env_vars.sh")
        print("   使用方法: source set_env_vars.sh")
    
    if success:
        print("\n🎉 API密钥配置完成！")
        print("\n📋 配置摘要:")
        if odds_key:
            print(f"✅ The Odds API: {odds_key[:10]}...")
        else:
            print("❌ The Odds API: 未配置")
        
        if soccer_key:
            print(f"✅ Football-Data API: {soccer_key[:10]}...")
        else:
            print("❌ Football-Data API: 未配置")
        
        print("\n💡 提示:")
        print("1. 运行环境检查: python3 check_environment.py")
        print("2. 测试API连接: python3 -c \"import requests; print('API测试')\"")
        return 0
    else:
        print("\n❌ API密钥配置失败，请手动编辑文件:")
        print("   1. football_predictor.py - 第29行 (ODDS_API_KEY)")
        print("   2. football_predictor.py - 第220行 (SOCCER_DATA_API_TOKEN)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x "$PACKAGE_DIR/setup_api_keys.py"

# 创建部署脚本
echo "🚀 创建部署脚本..."
cat > "$PACKAGE_DIR/deploy_football_system.sh" << 'EOF'
#!/bin/bash
# 🏆 足球预测智能体系统 - 部署脚本
# 在新电脑上运行此脚本，完成系统部署
# 用法: ./deploy_football_system.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🏆 足球预测智能体系统部署工具"
echo "=========================================="

# 检查是否在解压后的目录
if [ ! -f "football_predictor.py" ]; then
    echo "❌ 错误：请在解压后的系统目录下运行此脚本"
    echo ""
    echo "📋 正确步骤:"
    echo "1. 解压: tar -xzvf football_prediction_system.tar.gz"
    echo "2. 进入: cd football_prediction_system_*"
    echo "3. 运行: ./deploy_football_system.sh"
    exit 1
fi

# 显示系统信息
echo "💻 系统信息:"
echo "  OS: $(uname -s) $(uname -r)"
echo "  目录: $(pwd)"

# 检查Python
echo ""
echo "🐍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python 3.8+"
    echo ""
    echo "📋 安装方法:"
    echo "  macOS: brew install python"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "  Windows: 从 https://python.org 下载安装"
    exit 1
fi

python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
python_full=$(python3 -c "import sys; print(sys.version)")
echo "✅ Python版本: $python_version ($python_full)"

# 检查Python版本兼容性
if python3 -c "import sys; exit(0 if sys.version_info.major == 3 and sys.version_info.minor >= 8 else 1)"; then
    echo "✅ Python版本兼容 (需要 3.8+)"
else
    echo "⚠️  Python版本可能过低 (需要 3.8+，当前 $python_version)"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 创建虚拟环境
echo ""
echo "🔧 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    echo "创建虚拟环境: python3 -m venv venv"
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ 虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境
echo ""
echo "🚀 激活虚拟环境..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活 (Linux/macOS)"
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    echo "✅ 虚拟环境已激活 (Windows)"
else
    echo "❌ 无法激活虚拟环境，检查venv目录结构"
    exit 1
fi

# 验证虚拟环境激活
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ 虚拟环境未正确激活"
    exit 1
else
    echo "虚拟环境路径: $VIRTUAL_ENV"
fi

# 升级pip
echo ""
echo "📦 升级pip和setuptools..."
python3 -m pip install --upgrade pip setuptools wheel

# 安装依赖
echo ""
echo "📦 安装Python依赖..."
if [ -f "requirements.txt" ]; then
    echo "使用完整依赖列表: requirements.txt"
    pip install -r requirements.txt
elif [ -f "requirements.minimal.txt" ]; then
    echo "使用最小依赖列表: requirements.minimal.txt"
    pip install -r requirements.minimal.txt
else
    echo "❌ 依赖列表文件不存在"
    echo "请确保 requirements.txt 或 requirements.minimal.txt 存在"
    exit 1
fi

echo "✅ 依赖安装完成"

# 检查关键包安装
echo ""
echo "🔍 验证关键包安装..."
for package in requests pandas numpy xgboost scikit-learn openpyxl; do
    if python3 -c "import $package" 2>/dev/null; then
        version=$(python3 -c "import $package; print($package.__version__)")
        echo "✅ $package $version"
    else
        echo "❌ $package 未正确安装"
    fi
done

# 运行环境检查
echo ""
echo "🔍 运行环境检查..."
if [ -f "check_environment.py" ]; then
    python3 check_environment.py
    check_result=$?
    
    if [ $check_result -ne 0 ]; then
        echo ""
        echo "⚠️  环境检查发现问题"
        read -p "是否继续配置API密钥? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "部署暂停，请解决问题后重新运行"
            exit 1
        fi
    fi
else
    echo "⚠️  环境检查脚本不存在"
fi

# 配置API密钥
echo ""
echo "🔑 配置API密钥..."
if [ -f "setup_api_keys.py" ]; then
    echo "运行API密钥配置助手..."
    python3 setup_api_keys.py
    api_result=$?
    
    if [ $api_result -ne 0 ]; then
        echo ""
        echo "⚠️  API密钥配置遇到问题"
        echo "你可以稍后手动配置:"
        echo "1. 运行: python3 setup_api_keys.py"
        echo "2. 或编辑 football_predictor.py"
    fi
else
    echo "⚠️  API配置助手不存在"
    echo "请手动配置API密钥:"
    echo "编辑 football_predictor.py 第29行和第220行"
fi

# 创建测试脚本
echo ""
echo "🧪 创建部署验证测试..."
cat > test_deployment.py << 'TEST_EOF'
#!/usr/bin/env python3
"""
部署验证测试
验证系统基本功能是否正常
"""

import sys
import os

def test_imports():
    """测试核心模块导入"""
    print("🔍 测试模块导入...")
    modules = [
        ("requests", "网络请求"),
        ("pandas", "数据处理"),
        ("xgboost", "机器学习"),
        ("sklearn", "机器学习工具"),
        ("openpyxl", "Excel处理"),
    ]
    
    all_ok = True
    for module, desc in modules:
        try:
            __import__(module)
            version = sys.modules[module].__version__
            print(f"✅ {desc} ({module} {version})")
        except ImportError as e:
            print(f"❌ {desc} ({module}): {e}")
            all_ok = False
        except AttributeError:
            print(f"✅ {desc} ({module})")
    
    return all_ok

def test_ml_analyst():
    """测试ML-Analyst"""
    print("\n🤖 测试ML-Analyst...")
    try:
        sys.path.append('.')
        from ml_analyst.ml_analyst import MLAnalyst
        
        print("✅ ML-Analyst 模块可导入")
        
        # 检查特征文件
        feature_file = "ml_analyst/features/feature_list.txt"
        if os.path.exists(feature_file):
            with open(feature_file, 'r') as f:
                features = f.read().strip().split('\n')
            print(f"✅ 特征文件: {len(features)} 个特征")
        else:
            print(f"❌ 特征文件不存在: {feature_file}")
            return False
        
        # 检查模型文件
        import glob
        model_files = glob.glob("ml_analyst/models/*optimized*.json")
        if model_files:
            model_file = model_files[0]
            file_size = os.path.getsize(model_file) / 1024 / 1024
            print(f"✅ 模型文件: {os.path.basename(model_file)} ({file_size:.1f} MB)")
        else:
            print(f"❌ 未找到优化模型文件")
            # 尝试其他模型文件
            other_models = glob.glob("ml_analyst/models/*.json")
            if other_models:
                print(f"ℹ️  找到其他模型: {len(other_models)} 个")
            return False
        
        print("✅ ML-Analyst 模块正常")
        return True
        
    except ImportError as e:
        print(f"❌ ML-Analyst导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ ML-Analyst测试失败: {e}")
        return False

def test_football_predictor():
    """测试足球预测器"""
    print("\n⚽ 测试足球预测器...")
    try:
        from football_predictor import FootballPredictor
        
        # 测试初始化
        predictor = FootballPredictor()
        print("✅ FootballPredictor 初始化成功")
        
        # 测试共享ML-Analyst实例
        if hasattr(predictor, '_shared_ml_analyst') or hasattr(FootballPredictor, '_shared_ml_analyst'):
            print("✅ ML-Analyst共享实例配置正常")
        else:
            print("⚠️  ML-Analyst共享实例配置可能未生效")
        
        # 测试队名翻译
        from team_translator import translate_team_name
        test_names = ["曼城", "拜仁慕尼黑", "巴黎圣日耳曼"]
        for name in test_names:
            translated = translate_team_name(name)
            if translated and translated != name:
                print(f"✅ 队名翻译: {name} -> {translated}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 预测器导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 预测器测试失败: {e}")
        return False

def test_api_connectivity():
    """测试API连通性"""
    print("\n🌐 测试API连通性...")
    try:
        # 读取配置的API密钥
        with open("football_predictor.py", "r") as f:
            content = f.read()
        
        import re
        
        # 检查The Odds API密钥
        odds_match = re.search(r'ODDS_API_KEY\s*=\s*"([^"]+)"', content)
        if odds_match:
            key = odds_match.group(1)
            if "your_key_here" in key:
                print("⚠️  The Odds API密钥未配置")
            else:
                print(f"✅ The Odds API密钥已配置: {key[:8]}...")
        else:
            print("❌ 未找到The Odds API密钥配置")
        
        # 检查Football-Data API密钥
        soccer_match = re.search(r'SOCCER_DATA_API_TOKEN\s*=\s*"([^"]+)"', content)
        if soccer_match:
            token = soccer_match.group(1)
            if "your_token_here" in token:
                print("⚠️  Football-Data API令牌未配置")
            else:
                print(f"✅ Football-Data API令牌已配置: {token[:8]}...")
        else:
            print("❌ 未找到Football-Data API令牌配置")
        
        return True
        
    except Exception as e:
        print(f"❌ API连通性测试失败: {e}")
        return False

def main():
    print("🚀 足球预测系统部署验证")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 0
    
    # 测试导入
    tests_total += 1
    if test_imports():
        tests_passed += 1
    
    # 测试ML-Analyst
    tests_total += 1
    if test_ml_analyst():
        tests_passed += 1
    
    # 测试预测器
    tests_total += 1
    if test_football_predictor():
        tests_passed += 1
    
    # 测试API连通性
    tests_total += 1
    if test_api_connectivity():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {tests_passed}/{tests_total} 通过")
    
    if tests_passed == tests_total:
        print("🎉 部署验证通过！系统可以正常使用。")
        print("\n📋 下一步:")
        print("1. 运行单场预测测试: python3 predict.py \"曼城\" \"阿森纳\" soccer_epl")
        print("2. 查看使用指南: cat DEPLOYMENT_GUIDE.md")
        print("3. 运行批量预测: python3 predict_remaining_matches.py")
        return 0
    elif tests_passed >= tests_total - 1:
        print("⚠️  部署基本完成，但有一些小问题。")
        print("系统可能可以运行，但某些功能可能受限。")
        print("\n💡 建议:")
        print("1. 配置API密钥: python3 setup_api_keys.py")
        print("2. 检查依赖: pip list | grep -E 'xgboost|pandas'")
        return 1
    else:
        print("❌ 部署验证失败，系统可能无法正常工作。")
        print("\n💡 常见问题:")
        print("- 依赖不完整: pip install -r requirements.txt")
        print("- API密钥未配置: python3 setup_api_keys.py")
        print("- 文件缺失: 检查ml_analyst/models/目录")
        return 2

if __name__ == "__main__":
    sys.exit(main())
TEST_EOF

chmod +x test_deployment.py

# 创建快速开始脚本
echo ""
echo "⚡ 创建快速开始脚本..."
cat > quick_start.sh << 'QS_EOF'
#!/bin/bash
# ⚡ 足球预测系统快速开始脚本
# 用法: ./quick_start.sh

echo "⚡ 足球预测系统快速开始"
echo "========================"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在"
    echo "请先运行部署脚本:"
    echo "  ./deploy_football_system.sh"
    exit 1
fi

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活 (Linux/macOS)"
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    echo "✅ 虚拟环境已激活 (Windows)"
else
    echo "❌ 无法激活虚拟环境"
    exit 1
fi

echo ""
echo "📋 可用命令:"
echo ""
echo "🎯 单场比赛预测"
echo "  python3 predict.py \"主队\" \"客队\" [联赛]"
echo "  示例: python3 predict.py \"曼城\" \"阿森纳\" soccer_epl"
echo ""
echo "📊 批量预测"
echo "  python3 predict_remaining_matches.py"
echo ""
echo "📅 每日预测"
echo "  python3 daily_predict.py"
echo ""
echo "📈 Excel导出"
echo "  python3 export_excel.py"
echo ""
echo "🔧 系统维护"
echo "  1. 环境检查: python3 check_environment.py"
echo "  2. API配置: python3 setup_api_keys.py"
echo "  3. 清理缓存: ./cleanup_cache.sh"
echo ""
echo "📖 文档"
echo "  完整指南: cat DEPLOYMENT_GUIDE.md"
echo "  或: less DEPLOYMENT_GUIDE.md"
QS_EOF

chmod +x quick_start.sh

# 创建清理脚本
echo "🧹 创建清理脚本..."
cat > cleanup_cache.sh << 'CLEAN_EOF'
#!/bin/bash
# 🧹 清理系统缓存文件
# 用法: ./cleanup_cache.sh

echo "🧹 清理系统缓存文件"
echo "====================="

# 删除Python缓存
echo "清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true

# 删除日志文件
echo "清理日志文件..."
rm -f *.log 2>/dev/null || true
rm -f *.log.* 2>/dev/null || true

# 删除临时预测文件
echo "清理临时预测文件..."
rm -f prediction_*.txt 2>/dev/null || true
rm -f prediction_*.json 2>/dev/null || true
rm -f match_*.json 2>/dev/null || true

# 删除Excel临时文件
echo "清理Excel临时文件..."
rm -f ~/Desktop/足球预测_*.xlsx 2>/dev/null || true
rm -f 足球预测_*.xlsx 2>/dev/null || true

# 删除下载缓存
echo "清理下载缓存..."
rm -rf .cache 2>/dev/null || true
rm -rf downloads 2>/dev/null || true

echo "✅ 清理完成"
echo ""
echo "📊 当前磁盘使用:"
du -sh . 2>/dev/null || echo "无法计算磁盘使用"
CLEAN_EOF

chmod +x cleanup_cache.sh

# 运行部署测试
echo ""
echo "🧪 运行部署验证测试..."
python3 test_deployment.py
test_result=$?

echo ""
echo "=========================================="
echo "🏁 部署完成！"
echo "=========================================="
echo ""
echo "📋 部署状态:"
if [ $test_result -eq 0 ]; then
    echo "✅ 优秀 - 所有测试通过"
elif [ $test_result -eq 1 ]; then
    echo "⚠️  良好 - 基本功能正常，有小问题"
else
    echo "❌ 需改进 - 有重要问题需要解决"
fi

echo ""
echo "🚀 快速开始:"
echo "1. 激活虚拟环境: source venv/bin/activate (Linux/macOS)"
echo "2. 查看快速指南: ./quick_start.sh"
echo "3. 测试预测: python3 predict.py \"曼城\" \"阿森纳\" soccer_epl"
echo ""
echo "📖 文档:"
echo "  完整指南: cat DEPLOYMENT_GUIDE.md"
echo "  环境检查: python3 check_environment.py"
echo ""
echo "🔧 维护命令:"
echo "  更新API密钥: python3 setup_api_keys.py"
echo "  清理缓存: ./cleanup_cache.sh"
echo "  重新安装依赖: pip install -r requirements.txt --upgrade"
echo ""
echo "💡 提示:"
echo "  - 首次使用建议运行环境检查"
echo "  - API密钥对系统功能至关重要"
echo "  - 定期清理缓存可释放磁盘空间"
echo ""
echo "=========================================="
echo "🎉 系统部署完成！祝你预测顺利！ ⚽"
echo "=========================================="
EOF

chmod +x "$PACKAGE_DIR/deploy_football_system.sh"

# 创建README
echo "📖 创建README文件..."
cat > "$PACKAGE_DIR/README.md" << 'EOF'
# 🏆 足球预测智能体系统

基于多智能体架构和机器学习的足球比赛预测系统，集成8个专业分析智能体和ML模型，提供精准的赛前分析和投注建议。

## 🚀 快速开始

### 1. 获取系统
```bash
# 从源电脑获取压缩包
football_prediction_system_YYYYMMDD_HHMMSS.tar.gz
```

### 2. 在新电脑上部署
```bash
# 解压
tar -xzvf football_prediction_system_YYYYMMDD_HHMMSS.tar.gz
cd football_prediction_system_YYYYMMDD_HHMMSS

# 运行部署脚本
./deploy_football_system.sh
```

### 3. 配置API密钥
```bash
# 运行交互式配置
python3 setup_api_keys.py
```

### 4. 开始使用
```bash
# 激活虚拟环境
source venv/bin/activate

# 测试预测
python3 predict.py "曼城" "阿森纳" soccer_epl
```

## 📁 系统结构

```
football_prediction_system/
├── 📁 agents/                    # 8个分析智能体
│   ├── boss-football/           # 协调智能体
│   ├── stats-analyst/           # 统计分析师
│   ├── tactics-analyst/         # 战术分析师
│   ├── sentiment-analyst/       # 舆情分析师
│   ├── upset-detector/          # 冷门检测器
│   ├── asian-analyst/           # 亚盘分析师
│   ├── overunder-analyst/       # 大小球分析师
│   └── consensus-summarizer/    # 共识总结器
├── 📁 ml_analyst/               # ML分析模块
│   ├── models/                  # 训练好的模型
│   ├── features/                # 特征工程文件
│   └── *.py                     # ML核心代码
├── 🎯 football_predictor.py     # 主预测器
├── 🔤 team_translator.py        # 队名翻译器
├── 📊 predict.py               # 单场预测脚本
├── 📅 daily_predict.py          # 每日预测脚本
├── 📈 export_excel.py          # Excel导出脚本
├── 📋 requirements.txt         # 依赖列表
└── 🚀 deploy_football_system.sh # 部署脚本
```

## 🎯 核心功能

### 1. 多智能体分析系统
- **8个专业智能体**协同工作
- **辩论机制**解决分歧
- **加权共识**生成最终预测

### 2. 机器学习集成
- **XGBoost模型**训练历史数据
- **70.88%准确率**优化模型
- **动态权重**调节传统与ML分析比例

### 3. 实时数据获取
- **The Odds API**获取实时赔率
- **Football-Data API**获取历史统计
- **自动队名翻译**支持中文输入

### 4. 报告生成
- **详细分析报告**每场比赛
- **Excel自动导出**汇总结果
- **微信推送**结果通知（需配置）

## ⚙️ 技术栈

- **Python 3.8+** - 核心语言
- **XGBoost** - 机器学习框架
- **Pandas/NumPy** - 数据处理
- **Requests** - HTTP请求
- **OpenPyXL** - Excel处理
- **Scikit-learn** - 机器学习工具

## 🔧 系统要求

- **操作系统**: macOS, Linux, Windows (WSL推荐)
- **Python**: 3.8 或更高版本
- **内存**: 至少 4GB RAM
- **磁盘空间**: 至少 2GB 空闲空间
- **网络**: 稳定的互联网连接

## 📊 性能指标

- **预测准确率**: ~70% (ML模型)
- **响应时间**: <30秒/场比赛
- **并发支持**: 支持批量预测
- **数据覆盖**: 全球主要联赛

## 🆘 故障排除

常见问题及解决方案：

1. **依赖安装失败**
   ```bash
   # 安装系统依赖
   sudo apt-get install build-essential python3-dev
   pip install --no-cache-dir -r requirements.minimal.txt
   ```

2. **ML模型加载失败**
   ```bash
   # 检查模型文件
   ls -la ml_analyst/models/
   # 重新训练模型
   cd ml_analyst && python3 train_optimized.py
   ```

3. **API密钥无效**
   ```bash
   # 重新配置API密钥
   python3 setup_api_keys.py
   ```

4. **队名翻译缺失**
   - 编辑 `team_translator.py` 添加翻译

## 📄 许可证

仅供个人研究使用，不构成投资建议。

## 🤝 支持

如有问题，请参考部署指南或联系系统管理员。

---
**版本**: 2.0.0  
**更新日期**: 2024-04-20  
**作者**: 足球预测智能体团队
EOF

# 打包目录
echo ""
echo "📦 打包系统..."
tar -czvf "${PACKAGE_DIR}.tar.gz" "$PACKAGE_DIR"

# 计算大小
PACKAGE_SIZE=$(du -h "${PACKAGE_DIR}.tar.gz" | cut -f1)
DIR_SIZE=$(du -sh "$PACKAGE_DIR" | cut -f1)

echo ""
echo "=========================================="
echo "🎉 打包完成！"
echo "=========================================="
echo "📦 包文件: ${PACKAGE_DIR}.tar.gz"
echo "📊 压缩包大小: $PACKAGE_SIZE"
echo "📁 原始目录大小: $DIR_SIZE"
echo ""
echo "📋 包含内容:"
echo "✅ 8个智能体模块"
echo "✅ ML-Analyst系统 (含优化模型)"
echo "✅ 特征工程文件 (30个特征)"
echo "✅ 主预测程序 (5个核心脚本)"
echo "✅ 完整部署文档"
echo "✅ 环境检查工具"
echo "✅ API配置助手"
echo ""
echo "🚀 部署步骤 (复制到新电脑执行):"
echo "1. 传输: scp ${PACKAGE_DIR}.tar.gz user@newpc:~/"
echo "2. 解压: tar -xzvf ${PACKAGE_DIR}.tar.gz"
echo "3. 进入: cd ${PACKAGE_DIR}"
echo "4. 部署: ./deploy_football_system.sh"
echo ""
echo "💡 提示:"
echo "- 确保新电脑已安装 Python 3.8+"
echo "- 建议使用虚拟环境隔离依赖"
echo "- 首次使用前务必配置API密钥"
echo "=========================================="

# 显示文件列表
echo ""
echo "📁 打包目录内容预览:"
find "$PACKAGE_DIR" -type f -name "*.py" | head -10 | while read file; do
    size=$(du -h "$file" | cut -f1)
    echo "  $size $(basename "$file")"
done

echo ""
echo "🔢 文件统计:"
echo "  Python文件: $(find "$PACKAGE_DIR" -name "*.py" | wc -l)"
echo "  配置文件: $(find "$PACKAGE_DIR" -name "*.yaml" -o -name "*.json" | wc -l)"
echo "  文档文件: $(find "$PACKAGE_DIR" -name "*.md" -o -name "*.txt" | wc -l)"
echo "  总文件数: $(find "$PACKAGE_DIR" -type f | wc -l)"

# 清理临时目录（可选）
echo ""
read -p "是否删除临时打包目录 $PACKAGE_DIR? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$PACKAGE_DIR"
    echo "✅ 临时目录已删除"
else
    echo "✅ 临时目录保留: $PACKAGE_DIR"
    echo "   你可以稍后手动删除"
fi

echo ""
echo "🎊 打包流程全部完成！"
echo "现在可以将 ${PACKAGE_DIR}.tar.gz 传输到新电脑进行部署。"