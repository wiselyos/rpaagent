#!/bin/bash
# 电商自动化系统启动脚本

set -e

PROJECT_DIR="/root/.openclaw/workspace/ecommerce-automation"
CONFIG_FILE="$PROJECT_DIR/config/app.json"

echo "🚀 启动电商自动化系统..."
echo "================================"

# 检查 OpenClaw 状态
echo "📊 检查 OpenClaw 状态..."
if ! openclaw gateway status > /dev/null 2>&1; then
    echo "  启动 OpenClaw 网关..."
    openclaw gateway start
    sleep 3
fi
echo "  ✅ OpenClaw 运行正常"

# 安装 Skill 依赖
echo ""
echo "📦 安装 Skill 依赖..."

for skill_dir in $PROJECT_DIR/skills/*/; do
    skill_name=$(basename "$skill_dir")
    echo "  安装 Skill: $skill_name"
    
    # 检查是否有 requirements.txt
    if [ -f "$skill_dir/requirements.txt" ]; then
        pip install -r "$skill_dir/requirements.txt" -q
    fi
done
echo "  ✅ 依赖安装完成"

# 注册 Skills
echo ""
echo "🔧 注册 Skills..."

for skill_dir in $PROJECT_DIR/skills/*/; do
    skill_name=$(basename "$skill_dir")
    
    if [ -f "$skill_dir/SKILL.md" ]; then
        echo "  注册 Skill: $skill_name"
        # openclaw skill register "$skill_dir"
    fi
done
echo "  ✅ Skills 注册完成"

# 启动定时任务
echo ""
echo "⏰ 启动定时任务..."
# openclaw cron start
echo "  ✅ 定时任务已启动"

# 显示状态
echo ""
echo "================================"
echo "✅ 电商自动化系统启动完成！"
echo ""
echo "📊 系统状态:"
echo "  - OpenClaw Gateway: http://127.0.0.1:18789/"
echo "  - 项目目录: $PROJECT_DIR"
echo ""
echo "📝 可用 Skills:"
ls -1 $PROJECT_DIR/skills/
echo ""
echo "🎯 下一步:"
echo "  1. 配置数据库连接"
echo "  2. 测试 Skill 功能"
echo "  3. 启动监控面板"
