#!/bin/bash
# Office Automa - File Delivery Agent 启动脚本

WORKSPACE="/Users/bear/.openclaw/workspace/file-delivery"
VENV="$WORKSPACE/venv"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🤖 Office Automa - File Delivery Agent${NC}"
echo "=========================================="

# 检查虚拟环境
if [ ! -d "$VENV" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境不存在，正在创建...${NC}"
    cd "$WORKSPACE" && python3 -m venv venv
fi

# 激活虚拟环境
source "$VENV/bin/activate"

cd "$WORKSPACE"

# 根据参数执行不同操作
case "$1" in
    --status)
        echo "📊 检查各客户文件夹状态..."
        for client in MM MIG RITCHIE simcon olsonfab carleton Shao WW KILMARNOCK LEMIRE ALEXANDER JT LEE; do
            folder="/Users/bear/Shared/绿联云同步/$client"
            if [ -d "$folder" ]; then
                count=$(find "$folder" -type f ! -path "*/已发送/*" 2>/dev/null | wc -l)
                if [ "$count" -gt 0 ]; then
                    echo "  📁 $client: $count 个待发送文件"
                fi
            fi
        done
        ;;
    --run)
        echo "🚀 运行文件交付流程..."
        ./run.sh
        ;;
    --client)
        if [ -n "$2" ]; then
            echo "📤 处理客户: $2"
            ./run.sh --client "$2"
        else
            echo "❌ 请指定客户名，例如: ./office-automa.sh --client MM"
        fi
        ;;
    --cleanup)
        echo "🧹 清理云端旧文件..."
        ./run.sh --cleanup
        ;;
    *)
        echo "用法:"
        echo "  ./office-automa.sh --status    查看待发送文件状态"
        echo "  ./office-automa.sh --run       运行完整交付流程"
        echo "  ./office-automa.sh --client X  处理指定客户"
        echo "  ./office-automa.sh --cleanup   清理云端旧文件"
        ;;
esac
