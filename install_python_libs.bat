@echo off
chcp 65001 >nul
echo ============================================================
echo  安装 Python 依赖库
echo ============================================================
echo.

pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib dropbox

echo.
echo 安装完成！
pause
