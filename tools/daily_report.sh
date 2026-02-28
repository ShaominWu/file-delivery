#!/bin/bash
# 绿联云每日状态通知脚本
# 每天早上10点运行

cd /home/wuyongjie/.openclaw/skills/file-delivery/tools

# 运行发送脚本并捕获输出
OUTPUT=$(python3 nas_email_sender.py 2>&1)

# 统计结果
SUCCESS=$(echo "$OUTPUT" | grep -c "✓" || echo "0")
FAILED=$(echo "$OUTPUT" | grep -c "✗" || echo "0")

# 生成报告
REPORT="📧 绿联云每日发送报告 ($(date '+%Y-%m-%d %H:%M'))

成功: $SUCCESS
失败: $FAILED

详情:
$OUTPUT"

# 通过 OpenClaw 发送通知（需要在 OpenClaw 环境中运行）
echo "$REPORT"
