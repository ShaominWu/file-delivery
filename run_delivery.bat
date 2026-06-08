@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo  Ferrum File Delivery - 发送文件
echo  %date% %time%
echo ============================================================

python tools\delivery_agent.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序运行出错，请查看 logs 文件夹里的日志文件
)
