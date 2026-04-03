@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo  第一次运行：Google Drive 授权
echo ============================================================
echo.
echo 这个程序只需运行一次。
echo 运行后会弹出浏览器，请用你的 Google 账号登录并授权。
echo.
echo 前提：tools\client_secrets.json 文件必须已经放好。
echo.
pause

python tools\first_auth.py

echo.
echo 如果上面显示成功，以后就不需要再运行这个了。
pause
