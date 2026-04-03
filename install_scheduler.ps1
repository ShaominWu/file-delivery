# 安装 Ferrum File Delivery 定时任务
# 以管理员身份运行此脚本
# 运行方法：右键 → 以管理员身份运行 PowerShell，然后输入：
#   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\install_scheduler.ps1

# ============================================================
# 请修改这一行为你实际的文件夹路径
$BASE_DIR = "C:\file-delivery"
# ============================================================

$DELIVERY_BAT = "$BASE_DIR\run_delivery.bat"
$CLEANUP_BAT  = "$BASE_DIR\run_cleanup.bat"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 安装 Ferrum File Delivery 定时任务" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "程序目录: $BASE_DIR"
Write-Host ""

# 检查文件是否存在
if (-not (Test-Path $DELIVERY_BAT)) {
    Write-Host "[错误] 找不到 $DELIVERY_BAT" -ForegroundColor Red
    Write-Host "请先修改脚本第8行的 BASE_DIR 路径" -ForegroundColor Yellow
    Read-Host "按回车退出"
    exit 1
}

# ----- 任务1：每天 08:00 发送文件 -----
$taskName1 = "Ferrum_Delivery_0800"
Unregister-ScheduledTask -TaskName $taskName1 -Confirm:$false -ErrorAction SilentlyContinue

$action1  = New-ScheduledTaskAction -Execute $DELIVERY_BAT -WorkingDirectory $BASE_DIR
$trigger1 = New-ScheduledTaskTrigger -Daily -At "08:00"
$settings1 = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName $taskName1 `
    -Action $action1 `
    -Trigger $trigger1 `
    -Settings $settings1 `
    -Description "Ferrum 文件交付 - 每天8点" `
    -RunLevel Highest | Out-Null

Write-Host "[OK] 任务1已安装：每天 08:00 扫描并发送文件" -ForegroundColor Green

# ----- 任务2：每天 10:00 发送文件 -----
$taskName2 = "Ferrum_Delivery_1000"
Unregister-ScheduledTask -TaskName $taskName2 -Confirm:$false -ErrorAction SilentlyContinue

$action2  = New-ScheduledTaskAction -Execute $DELIVERY_BAT -WorkingDirectory $BASE_DIR
$trigger2 = New-ScheduledTaskTrigger -Daily -At "10:00"
$settings2 = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName $taskName2 `
    -Action $action2 `
    -Trigger $trigger2 `
    -Settings $settings2 `
    -Description "Ferrum 文件交付 - 每天10点" `
    -RunLevel Highest | Out-Null

Write-Host "[OK] 任务2已安装：每天 10:00 扫描并发送文件" -ForegroundColor Green

# ----- 任务3：每天 01:00 清理云端旧文件 -----
$taskName3 = "Ferrum_Cleanup_0100"
Unregister-ScheduledTask -TaskName $taskName3 -Confirm:$false -ErrorAction SilentlyContinue

$action3  = New-ScheduledTaskAction -Execute $CLEANUP_BAT -WorkingDirectory $BASE_DIR
$trigger3 = New-ScheduledTaskTrigger -Daily -At "01:00"
$settings3 = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName $taskName3 `
    -Action $action3 `
    -Trigger $trigger3 `
    -Settings $settings3 `
    -Description "Ferrum 云端清理 - 每天凌晨1点" `
    -RunLevel Highest | Out-Null

Write-Host "[OK] 任务3已安装：每天 01:00 清理7天以上的云端文件" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 安装完成！3个定时任务已创建：" -ForegroundColor Cyan
Write-Host "   每天 08:00 - 发送文件" -ForegroundColor White
Write-Host "   每天 10:00 - 发送文件" -ForegroundColor White
Write-Host "   每天 01:00 - 清理云端" -ForegroundColor White
Write-Host ""
Write-Host " 可在「任务计划程序」里查看和管理（搜索「任务计划程序」）" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车退出"
