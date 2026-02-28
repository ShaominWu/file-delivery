#!/bin/bash
# 绿联云每日发送报告脚本 - 每天10点运行

REPORT_FILE="/tmp/nas_daily_report_$(date +%Y%m%d).txt"

# 运行发送脚本并生成报告
cd /home/wuyongjie/.openclaw/skills/file-delivery/tools
python3 nas_email_sender.py --report > "$REPORT_FILE" 2>&1

# 检查是否有 openclaw 命令可用，发送 Telegram 通知
if command -v openclaw &> /dev/null; then
    # 读取报告内容
    REPORT=$(cat "$REPORT_FILE")
    
    # 发送 Telegram 通知（通过 openclaw）
    openclaw message send --target "1201696151" --channel telegram --message "$REPORT" || true
fi

# 清理旧报告文件（保留7天）
find /tmp -name "nas_daily_report_*.txt" -mtime +7 -delete 2>/dev/null || true
