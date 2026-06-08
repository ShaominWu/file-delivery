#!/bin/bash
cd "$(dirname "$0")"
echo "============================================================"
echo " Ferrum File Delivery - 发送文件"
echo " $(date)"
echo "============================================================"
python3 tools/delivery_agent.py
