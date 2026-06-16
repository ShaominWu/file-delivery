#!/bin/bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$BASE_DIR/venv/bin/python"
PLIST_DIR="$HOME/Library/LaunchAgents"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="/opt/homebrew/bin/python3"
fi

echo "Ferrum File Delivery - 修复 Mac 定时任务"
echo "程序目录: $BASE_DIR"
echo "Python: $PYTHON_BIN"
echo ""

python3 - <<PY
import plistlib
from pathlib import Path

python_bin = "$PYTHON_BIN"
plist_dir = Path("$PLIST_DIR")
jobs = {
    "com.ferrum.delivery.0800.plist": [python_bin, "$BASE_DIR/tools/delivery_agent.py"],
    "com.ferrum.delivery.1000.plist": [python_bin, "$BASE_DIR/tools/delivery_agent.py"],
    "com.ferrum.delivery.1130.plist": [python_bin, "$BASE_DIR/tools/delivery_agent.py"],
    "com.ferrum.cleanup.0100.plist": [python_bin, "$BASE_DIR/tools/cleanup_drive.py", "--days", "7"],
}

for name, args in jobs.items():
    path = plist_dir / name
    if not path.exists():
        print(f"跳过，找不到: {path}")
        continue

    with path.open("rb") as handle:
        data = plistlib.load(handle)

    data["ProgramArguments"] = args
    data["WorkingDirectory"] = "$BASE_DIR"

    with path.open("wb") as handle:
        plistlib.dump(data, handle, sort_keys=False)

    print(f"已更新: {name}")
PY

UID_VALUE="$(id -u)"
for label in com.ferrum.delivery.0800 com.ferrum.delivery.1000 com.ferrum.delivery.1130 com.ferrum.cleanup.0100; do
  launchctl bootout "gui/$UID_VALUE/$label" 2>/dev/null || true
done

for plist in \
  "$PLIST_DIR/com.ferrum.delivery.0800.plist" \
  "$PLIST_DIR/com.ferrum.delivery.1000.plist" \
  "$PLIST_DIR/com.ferrum.delivery.1130.plist" \
  "$PLIST_DIR/com.ferrum.cleanup.0100.plist"; do
  if [ -f "$plist" ]; then
    launchctl bootstrap "gui/$UID_VALUE" "$plist" 2>/dev/null || true
  fi
done

echo ""
echo "完成。当前任务状态："
launchctl print "gui/$UID_VALUE/com.ferrum.delivery.0800" | grep -E "program|delivery_agent|Hour|Minute" || true
launchctl print "gui/$UID_VALUE/com.ferrum.delivery.1000" | grep -E "program|delivery_agent|Hour|Minute" || true
launchctl print "gui/$UID_VALUE/com.ferrum.delivery.1130" | grep -E "program|delivery_agent|Hour|Minute" || true
launchctl print "gui/$UID_VALUE/com.ferrum.cleanup.0100" | grep -E "program|cleanup_drive|Hour|Minute" || true
echo ""
echo "可以关闭这个窗口。"
