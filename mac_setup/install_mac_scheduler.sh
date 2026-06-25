#!/bin/bash
# Mac版定时任务安装脚本
# 运行方法：bash mac_setup/install_mac_scheduler.sh

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$BASE_DIR/venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="/opt/homebrew/bin/python3"
fi
echo "程序目录: $BASE_DIR"
echo "Python: $PYTHON_BIN"

PLIST_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$PLIST_DIR"

# 任务1: 每天08:00 发送文件
cat > "$PLIST_DIR/com.ferrum.delivery.0800.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ferrum.delivery.0800</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$BASE_DIR/tools/delivery_agent.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$BASE_DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$BASE_DIR/logs/delivery-0800.log</string>
    <key>StandardErrorPath</key>
    <string>$BASE_DIR/logs/delivery-0800-error.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
PLIST

# 任务2: 每天10:00 发送文件
cat > "$PLIST_DIR/com.ferrum.delivery.1000.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ferrum.delivery.1000</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$BASE_DIR/tools/delivery_agent.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$BASE_DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>10</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$BASE_DIR/logs/delivery-1000.log</string>
    <key>StandardErrorPath</key>
    <string>$BASE_DIR/logs/delivery-1000-error.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
PLIST


# 任务3: 每天11:30 发送文件
cat > "$PLIST_DIR/com.ferrum.delivery.1130.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ferrum.delivery.1130</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$BASE_DIR/tools/delivery_agent.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$BASE_DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>11</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$BASE_DIR/logs/delivery-1130.log</string>
    <key>StandardErrorPath</key>
    <string>$BASE_DIR/logs/delivery-1130-error.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
PLIST

# 任务3: 每天01:00 清理云端
cat > "$PLIST_DIR/com.ferrum.cleanup.0100.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ferrum.cleanup.0100</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$BASE_DIR/tools/cleanup_drive.py</string>
        <string>--days</string>
        <string>7</string>
        <string>--local-days</string>
        <string>30</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$BASE_DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>1</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$BASE_DIR/logs/cleanup.log</string>
    <key>StandardErrorPath</key>
    <string>$BASE_DIR/logs/cleanup-error.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
PLIST

# 加载定时任务
launchctl load "$PLIST_DIR/com.ferrum.delivery.0800.plist"
launchctl load "$PLIST_DIR/com.ferrum.delivery.1000.plist"
launchctl load "$PLIST_DIR/com.ferrum.delivery.1130.plist"
launchctl load "$PLIST_DIR/com.ferrum.cleanup.0100.plist"

echo ""
echo "✅ 4个定时任务已安装："
echo "   每天 08:00 - 发送文件"
echo "   每天 10:00 - 发送文件"
echo "   每天 11:30 - 发送文件"
echo "   每天 01:00 - 清理 Google Drive / Dropbox / OneDrive 云端旧文件 + 本地已发送"
