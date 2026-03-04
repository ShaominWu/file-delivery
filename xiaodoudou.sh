#!/bin/bash
# 小豆豆 (Xiaodoudou) - 办公自动化助手 🫘

WORKSPACE="/Users/bear/.openclaw/workspace/file-delivery"
VENV="$WORKSPACE/venv"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PINK='\033[1;35m'
NC='\033[0m'

echo -e "${PINK}🫘 小豆豆上班啦~${NC}"
echo "======================"

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
        echo "📊 让我看看各客户有多少文件..."
        found=0
        for client in MM MIG RITCHIE simcon olsonfab carleton Shao WW KILMARNOCK LEMIRE ALEXANDER JT LEE; do
            folder="/Users/bear/Shared/绿联云同步/$client"
            if [ -d "$folder" ]; then
                count=$(find "$folder" -type f ! -name ".*" ! -path "*/已发送/*" 2>/dev/null | wc -l)
                if [ "$count" -gt 0 ]; then
                    echo "  📁 $client: $count 个文件待发送"
                    found=1
                fi
            fi
        done
        if [ "$found" -eq 0 ]; then
            echo "  📭 暂时没有发现新文件~"
        fi
        echo -e "${GREEN}🫘 检查完毕！${NC}"
        ;;
    --run)
        echo "🚀 开始处理文件..."
        ./run.sh
        echo -e "${GREEN}🫘 搞定！${NC}"
        ;;
    --client)
        if [ -n "$2" ]; then
            echo "📤 专门处理 $2 的文件..."
            ./run.sh --client "$2"
            echo -e "${GREEN}🫘 $2 处理完毕！${NC}"
        else
            echo "❌ 请告诉我处理哪个客户，比如: ./xiaodoudou.sh --client MM"
        fi
        ;;
    --cleanup)
        echo "🧹 清理云端旧文件 (Google Drive + Dropbox)..."
        ./run.sh --cleanup
        echo -e "${GREEN}🫘 清理完毕！${NC}"
        ;;
    --cleanup-drive)
        echo "🧹 清理 Google Drive..."
        ./run.sh --cleanup-drive
        echo -e "${GREEN}🫘 Google Drive 清理完毕！${NC}"
        ;;
    --cleanup-dropbox)
        echo "🧹 清理 Dropbox..."
        ./run.sh --cleanup-dropbox
        echo -e "${GREEN}🫘 Dropbox 清理完毕！${NC}"
        ;;
    *)
        echo "小豆豆能帮你："
        echo ""
        echo "  ./xiaodoudou.sh --status           查看各客户待发送文件"
        echo "  ./xiaodoudou.sh --run              运行完整交付流程"
        echo "  ./xiaodoudou.sh --client X         处理指定客户"
        echo "  ./xiaodoudou.sh --cleanup          清理所有云端旧文件"
        echo "  ./xiaodoudou.sh --cleanup-drive    只清理 Google Drive"
        echo "  ./xiaodoudou.sh --cleanup-dropbox  只清理 Dropbox"
        echo ""
        echo -e "${PINK}🫘 有事叫我，没事我不吵你~${NC}"
        ;;
esac
