#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Send one Telegram summary of today's completed file deliveries."""

import argparse
import glob
import json
import os
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
BASE_DIR = TOOLS_DIR.parent
LOG_DIR = BASE_DIR / "logs"
STATE_PATH = LOG_DIR / "daily-delivery-report-state.json"


def load_dotenv(path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def completed_deliveries(day):
    """Return successfully emailed files grouped by client for YYYYMMDD."""
    grouped = defaultdict(list)
    pattern = str(LOG_DIR / f"delivery-{day}-*.log")

    for path in sorted(glob.glob(pattern)):
        current_client = None
        pending_files = []
        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        for line in lines:
            client_match = re.search(r"📁\s+([^:]+):\s+发现\s+\d+\s+个文件", line)
            if client_match:
                current_client = client_match.group(1).strip()
                pending_files = []
                continue

            file_match = re.search(r"📤\s+上传:\s+(.+?)\.\.\.$", line)
            if file_match and current_client:
                pending_files.append(file_match.group(1).strip())
                continue

            if "✅ 邮件已发送" in line and current_client:
                grouped[current_client].extend(pending_files)
                current_client = None
                pending_files = []

    return dict(grouped)


def build_message(now, deliveries):
    title = "📦 <b>Ferrum 每日文件传递报告</b>"
    date_line = f"📅 {now:%Y-%m-%d}"
    if not deliveries:
        return f"{title}\n{date_line}\n\nℹ️ 今天没有发送文件。"

    total = sum(len(files) for files in deliveries.values())
    lines = [title, date_line, "", f"✅ 今天已发送 {total} 个文件："]
    for client, files in sorted(deliveries.items()):
        lines.append(f"• <b>{escape(client)}</b>：{len(files)} 个")
        for filename in files[:8]:
            lines.append(f"  - {escape(filename)}")
        if len(files) > 8:
            lines.append(f"  - 另有 {len(files) - 8} 个文件")
    return "\n".join(lines)


def already_sent(day):
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return state.get("last_sent_day") == day


def save_sent(day):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"last_sent_day": day, "sent_at": datetime.now().isoformat()}, indent=2),
        encoding="utf-8",
    )


def send_telegram(message):
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("Telegram token or chat ID is not configured")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }).encode()
    request = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"Telegram returned HTTP {response.status}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    load_dotenv(TOOLS_DIR / ".env")
    now = datetime.now()
    day = now.strftime("%Y%m%d")
    message = build_message(now, completed_deliveries(day))

    if args.dry_run:
        print(message)
        return 0
    if already_sent(day) and not args.force:
        print(f"Daily Telegram report already sent for {day}")
        return 0

    send_telegram(message)
    save_sent(day)
    print(f"Daily Telegram report sent for {day}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
