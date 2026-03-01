#!/bin/bash
# File Delivery Skill - 快速入口

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

# 使用虚拟环境的 Python
if [ -f "$SKILL_DIR/venv/bin/python3" ]; then
    PYTHON="$SKILL_DIR/venv/bin/python3"
else
    PYTHON="python3"
fi

echo "🚀 Ferrum File Delivery System"
echo "=============================="

# 检查参数
if [ "$1" == "--client" ] && [ -n "$2" ]; then
    echo "处理客户: $2"
    $PYTHON "$SKILL_DIR/tools/delivery_agent.py" --client "$2"
elif [ "$1" == "--cleanup" ]; then
    echo "清理云端文件..."
    $PYTHON "$SKILL_DIR/tools/cleanup_drive.py"
elif [ "$1" == "--status" ]; then
    echo "检查待发送文件..."
    $SKILL_DIR/tools/check_status.sh
else
    # 默认：处理所有客户
    echo "扫描所有客户文件夹..."
    $PYTHON "$SKILL_DIR/tools/delivery_agent.py"
fi
