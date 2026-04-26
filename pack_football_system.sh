#!/bin/bash
# 🏆 足球预测智能体系统 - 打包脚本
# 在源电脑上运行此脚本，生成可迁移的压缩包
# 用法: ./pack_football_system.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🏆 足球预测智能体系统打包工具"
echo "=========================================="

# 检查是否在正确目录
if [ ! -f "football_predictor.py" ]; then
    echo "❌ 错误：请在 openclaw-workspace 目录下运行此脚本"
    exit 1
fi

# 创建临时打包目录
PACKAGE_DIR="football_prediction_system_$(date +%Y%m%d_%H%M%S)"
echo "📦 创建打包目录: $PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

# 复制核心文件
echo "📄 复制核心代码文件..."
# 智能体目录
for agent in boss-football stats-analyst tactics-analyst sentiment-analyst upset-detector asian-analyst overunder-analyst consensus-summarizer; do
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
for file in ml_analyst/*.py ml_analyst/*.yaml ml_analyst/*.md 2>/dev/null; do
    if [ -f "$file" ]; then
        cp "$file" "$PACKAGE_DIR/ml_analyst/"
    fi
done

# 必须的模型文件
echo "🧠 复制ML模型文件..."
cp ml_analyst/models/xgboost_optimized_20260419_092408.json "$PACKAGE_DIR/ml_analyst/models/" 2>/dev/null || echo "  ⚠️ 模型文件可能不存在"
cp ml_analyst/models/xgboost_optimized_20260419_092408_report.json "$PACKAGE_DIR/ml_analyst/models/" 2>/dev/null || true

# 特征工程文件
echo "🔧 复制特征工程文件..."
cp ml_analyst/features/feature_list.txt "$PACKAGE_DIR/ml_analyst/features/" 2>/dev/null || echo "  ⚠️ 特征列表文件可能不存在"
cp ml_analyst/features/feature_report.yaml "$PACKAGE_DIR/ml_analyst/features/" 2>/dev/null || true

# 配置文件
echo "⚙️ 复制配置文件..."
mkdir -p "$PACKAGE_DIR/config"
cp config/*.yaml "$PACKAGE_DIR/config/" 2>/dev/null || true

# 主程序文件
echo "🚀 复制主程序文件..."
cp football_predictor.py "$PACKAGE_DIR/"
cp team_translator.py "$PACKAGE_DIR/"
cp predict.py "$PACKAGE_DIR/"
cp daily_predict.py "$PACKAGE_DIR/"
cp export_excel.py "$PACKAGE_DIR/"
cp predict_remaining_matches.py "$PACKAGE_DIR/"
cp requirements.txt "$PACKAGE_DIR/"
cp README.md "$PACKAGE_DIR/"

# 辅助脚本
echo "🛠️ 复制辅助脚本..."
for file in batch_parallel_predictor.py enhanced_batch_predictor.py parallel_agent_predictor.py; do
    if [ -f "$file" ]; then
        cp "$file" "$PACKAGE_DIR/"
    fi
done

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
cd football_prediction_system
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
```

### 4. 配置API密钥
编辑 `football_predictor.py`，更新以下密钥：
- 第29行: `ODDS_API_KEY` (The Odds API)
- 第220行: `SOCCER_DATA_API_TOKEN` (足球数据API)

或者设置环境变量：
```bash
export ODDS_API_KEY="你的API密钥"
export SOCCER_DATA_API_TOKEN="你的足球数据API令牌"
```

### 5. 验证安装
```bash
# 测试依赖
python3 -c "import requests, pandas, xgboost; print('✅ 依赖正常')"

# 测试ML模型加载
python3 -c "from ml_analyst.ml_analyst import MLAnalyst; analyst = MLAnalyst(); print('✅ ML-Analyst加载成功')"

# 测试预测器
python3 predict.py "曼城" "阿森纳" soccer_epl
```

## 系统功能

### 单场比赛预测
```bash
python3 predict.py "主队名" "客队名" [联赛代码]
```

### 批量预测
```bash
python3 predict_remaining_matches.py
```

### 每日自动预测
```bash
python3 daily_predict.py
```

### Excel导出
```bash
python3 export_excel.py
```

## 故障排除

### 1. ML-Analyst加载失败
错误：特征不匹配
解决：确保 `ml_analyst/features/feature_list.txt` 文件存在

### 2. API请求失败
错误：Invalid API key
解决：注册并配置正确的API密钥

### 3. 球队翻译缺失
编辑 `team_translator.py` 添加翻译

## 支持
如有问题，请参考原始系统配置或联系开发人员。
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

def main():
    print("🔍 环境检查开始")
    print("=" * 40)
    
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
        ("pyarrow", "pyarrow"),
        ("pyyaml", "yaml"),
    ]
    
    for package, import_name in packages:
        if not check_package(package, import_name):
            all_ok = False
    
    print("\n🤖 检查ML-Analyst模块:")
    try:
        sys.path.append('.')
        from ml_analyst.ml_analyst import MLAnalyst
        print("✅ ML-Analyst 模块可导入")
        
        # 检查特征文件
        import os
        if os.path.exists("ml_analyst/features/feature_list.txt"):
            print("✅ 特征列表文件存在")
        else:
            print("❌ 特征列表文件缺失")
            all_ok = False
            
        # 检查模型文件
        model_file = "ml_analyst/models/xgboost_optimized_20260419_092408.json"
        if os.path.exists(model_file):
            print(f"✅ 模型文件存在: {model_file}")
        else:
            print(f"❌ 模型文件缺失: {model_file}")
            all_ok = False
            
    except ImportError as e:
        print(f"❌ ML-Analyst导入失败: {e}")
        all_ok = False
    except Exception as e:
        print(f"❌ ML-Analyst检查失败: {e}")
        all_ok = False
    
    print("\n" + "=" * 40)
    if all_ok:
        print("🎉 所有检查通过！系统可以正常使用。")
        return 0
    else:
        print("⚠️  部分检查未通过，请解决上述问题后再运行系统。")
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

def get_input(prompt, default=""):
    """获取用户输入"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
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
                        lines[line_num-1] = f'{parts[0]}="{key_value}"  # 用户配置的API密钥\n'
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
    print("1. The Odds API - 获取实时赔率数据")
    print("2. Football-Data API - 获取历史比赛数据")
    print()
    print("如果没有API密钥，请先注册:")
    print("- The Odds API: https://the-odds-api.com")
    print("- Football-Data: https://www.football-data.org")
    print()
    
    # 获取用户输入
    odds_key = get_input("请输入 The Odds API 密钥")
    soccer_key = get_input("请输入 Football-Data API 令牌")
    
    if not odds_key or not soccer_key:
        print("❌ API密钥不能为空")
        return 1
    
    # 更新 football_predictor.py
    print("\n📝 更新配置文件...")
    success = True
    success = success and update_file_key("football_predictor.py", 29, odds_key)
    success = success and update_file_key("football_predictor.py", 220, soccer_key)
    
    # 更新 ml_config.yaml
    try:
        yaml_path = "config/ml_config.yaml"
        if os.path.exists(yaml_path):
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
    
    if success:
        print("\n🎉 API密钥配置完成！")
        print("\n📋 配置摘要:")
        print(f"The Odds API: {odds_key[:10]}...")
        print(f"Football-Data API: {soccer_key[:10]}...")
        print("\n💡 提示: 你还可以通过环境变量设置API密钥:")
        print(f'export ODDS_API_KEY="{odds_key}"')
        print(f'export SOCCER_DATA_API_TOKEN="{soccer_key}"')
        return 0
    else:
        print("\n❌ API密钥配置失败，请手动编辑文件")
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
    echo "   先运行: tar -xzvf football_prediction_system.tar.gz"
    echo "   然后: cd football_prediction_system_*"
    exit 1
fi

# 检查Python
echo "🐍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python 3.8+"
    echo "   推荐安装方法:"
    echo "   macOS: brew install python"
    echo "   Ubuntu: sudo apt-get install python3 python3-pip"
    echo "   Windows: 从 https://python.org 下载安装"
    exit 1
fi

python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python版本: $python_version"

if [[ $(python3 -c "import sys; print(1 if sys.version_info.major == 3 and sys.version_info.minor >= 8 else 0)") == "0" ]]; then
    echo "⚠️  推荐使用Python 3.8+，当前版本可能不兼容"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 创建虚拟环境
echo "🔧 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
echo "🚀 激活虚拟环境..."
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

# 升级pip
echo "📦 升级pip..."
pip install --upgrade pip

# 安装依赖
echo "📦 安装Python依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ 依赖安装完成"
else
    echo "❌ requirements.txt 文件不存在"
    exit 1
fi

# 运行环境检查
echo "🔍 运行环境检查..."
if [ -f "check_environment.py" ]; then
    python3 check_environment.py
    check_result=$?
    
    if [ $check_result -ne 0 ]; then
        echo "⚠️  环境检查发现问题，请解决后重新运行部署脚本"
        echo "是否继续配置API密钥? (y/N): "
        read -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo "⚠️  环境检查脚本不存在"
fi

# 配置API密钥
echo "🔑 配置API密钥..."
if [ -f "setup_api_keys.py" ]; then
    echo "运行API密钥配置助手..."
    python3 setup_api_keys.py
    
    if [ $? -ne 0 ]; then
        echo "⚠️  API密钥配置失败，你可以手动编辑文件:"
        echo "   1. football_predictor.py - 第29行 (ODDS_API_KEY)"
        echo "   2. football_predictor.py - 第220行 (SOCCER_DATA_API_TOKEN)"
        echo "   3. config/ml_config.yaml - auth_token"
    fi
else
    echo "⚠️  API配置助手不存在，请手动配置API密钥"
    echo "编辑以下文件:"
    echo "1. football_predictor.py - 第29行 (ODDS_API_KEY)"
    echo "2. football_predictor.py - 第220行 (SOCCER_DATA_API_TOKEN)"
fi

# 创建测试脚本
echo "🧪 创建测试脚本..."
cat > test_deployment.py << 'TEST_EOF'
#!/usr/bin/env python3
"""
部署测试脚本
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
    ]
    
    all_ok = True
    for module, desc in modules:
        try:
            __import__(module)
            print(f"✅ {desc} ({module})")
        except ImportError as e:
            print(f"❌ {desc} ({module}): {e}")
            all_ok = False
    
    return all_ok

def test_ml_analyst():
    """测试ML-Analyst"""
    print("\n🤖 测试ML-Analyst...")
    try:
        sys.path.append('.')
        from ml_analyst.ml_analyst import MLAnalyst
        
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
        model_file = "ml_analyst/models/xgboost_optimized_20260419_092408.json"
        if os.path.exists(model_file):
            file_size = os.path.getsize(model_file) / 1024 / 1024
            print(f"✅ 模型文件: {model_file} ({file_size:.1f} MB)")
        else:
            print(f"❌ 模型文件不存在: {model_file}")
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
        
        return True
        
    except ImportError as e:
        print(f"❌ 预测器导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 预测器测试失败: {e}")
        return False

def main():
    print("🚀 部署验证测试")
    print("=" * 40)
    
    all_ok = True
    
    # 测试导入
    if not test_imports():
        all_ok = False
    
    # 测试ML-Analyst
    if not test_ml_analyst():
        all_ok = False
    
    # 测试预测器
    if not test_football_predictor():
        all_ok = False
    
    print("\n" + "=" * 40)
    if all_ok:
        print("🎉 部署验证通过！系统可以正常使用。")
        print("\n📋 下一步:")
        print("1. 运行单场预测测试: python3 predict.py \"曼城\" \"阿森纳\" soccer_epl")
        print("2. 查看使用指南: cat DEPLOYMENT_GUIDE.md")
        return 0
    else:
        print("⚠️  部署验证发现问题，请检查以上错误信息。")
        print("\n💡 常见问题:")
        print("- API密钥未配置: 运行 python3 setup_api_keys.py")
        print("- 依赖不完整: 运行 pip install -r requirements.txt")
        print("- 文件缺失: 确保所有文件已正确解压")
        return 1

if __name__ == "__main__":
    sys.exit(main())
TEST_EOF

chmod +x test_deployment.py

# 运行部署测试
echo "🧪 运行部署验证测试..."
python3 test_deployment.py
test_result=$?

echo ""
echo "=========================================="
if [ $test_result -eq 0 ]; then
    echo "🎉 系统部署完成！"
    echo ""
    echo "📋 快速开始:"
    echo "1. 激活虚拟环境: source venv/bin/activate (Linux/macOS)"
    echo "2. 测试单场预测: python3 predict.py \"曼城\" \"阿森纳\" soccer_epl"
    echo "3. 查看完整指南: cat DEPLOYMENT_GUIDE.md"
    echo ""
    echo "💡 提示: 记得定期更新API密钥和维护系统"
else
    echo "⚠️  部署完成，但测试发现问题"
    echo "请检查以上错误信息，解决后重新运行测试"
fi
echo "=========================================="
EOF

chmod +x "$PACKAGE_DIR/deploy_football_system.sh"

# 创建快速开始脚本
echo "⚡ 创建快速开始脚本..."
cat > "$PACKAGE_DIR/quick_start.sh" << 'EOF'
#!/bin/bash
# ⚡ 足球预测系统快速开始脚本
# 用法: ./quick_start.sh

echo "⚡ 足球预测系统快速开始"
echo "========================"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行部署脚本:"
    echo "   ./deploy_football_system.sh"
    exit 1
fi

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    echo "✅ 虚拟环境已激活 (Windows)"
else
    echo "❌ 无法激活虚拟环境"
    exit 1
fi

echo ""
echo "📋 可用命令:"
echo "1. 单场预测: python3 predict.py \"主队\" \"客队\" [联赛]"
echo "2. 批量预测: python3 predict_remaining_matches.py"
echo "3. 每日预测: python3 daily_predict.py"
echo "4. Excel导出: python3 export_excel.py"
echo "5. 环境检查: python3 check_environment.py"
echo ""
echo "🔧 维护命令:"
echo "1. 更新API密钥: python3 setup_api_keys.py"
echo "2. 重新安装依赖: pip install -r requirements.txt"
echo ""
echo "📖 查看完整文档: cat DEPLOYMENT_GUIDE.md"
EOF

chmod +x "$PACKAGE_DIR/quick_start.sh"

# 创建清理脚本（可选）
echo "🧹 创建清理脚本..."
cat > "$PACKAGE_DIR/cleanup_cache.sh" << 'EOF'
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

# 删除日志文件
echo "清理日志文件..."
rm -f *.log 2>/dev/null || true
rm -f logs/*.log 2>/dev/null || true

# 删除临时预测文件
echo "清理临时预测文件..."
rm -f prediction_*.txt 2>/dev/null || true
rm -f prediction_*.json 2>/dev/null || true

# 删除Excel临时文件
echo "清理Excel临时文件..."
rm -f ~/Desktop/足球预测_*.xlsx 2>/dev/null || true

echo "✅ 清理完成"
EOF

chmod +x "$PACKAGE_DIR/cleanup_cache.sh"

# 打包目录
echo "📦 打包系统..."
tar -czvf "${PACKAGE_DIR}.tar.gz" "$PACKAGE_DIR"

# 计算大小
PACKAGE_SIZE=$(du -h "${PACKAGE_DIR}.tar.gz" | cut -f1)

echo ""
echo "=========================================="
echo "🎉 打包完成！"
echo "=========================================="
echo "📦 包文件: ${PACKAGE_DIR}.tar.gz"
echo "📊 大小: $PACKAGE_SIZE"
echo ""
echo "📋 包含内容:"
echo "✅ 8个智能体模块"
echo "✅ ML-Analyst系统（含优化模型）"
echo "✅ 特征工程文件"
echo "✅ 主预测程序"
echo "✅ 部署脚本和文档"
echo ""
echo "🚀 部署步骤:"
echo "1. 将 ${PACKAGE_DIR}.tar.gz 复制到新电脑"
echo "2. 解压: tar -xzvf ${PACKAGE_DIR}.tar.gz"
echo "3. 进入目录: cd ${PACKAGE_DIR}"
echo "4. 运行部署: ./deploy_football_system.sh"
echo ""
echo "💡 提示: 部署前请确保新电脑已安装Python 3.8+"
echo "=========================================="

# 清理临时目录（可选）
read -p "是否删除临时打包目录 $PACKAGE_DIR? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$PACKAGE_DIR"
    echo "✅ 临时目录已删除"
fi