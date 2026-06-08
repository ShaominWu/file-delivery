#!/bin/bash
cd "$(dirname "$0")"
echo "============================================================"
echo " Ferrum File Delivery - 清理 Google Drive / OneDrive 旧文件"
echo " $(date)"
echo "============================================================"
python3 tools/cleanup_drive.py --days 7
