# Create-TaskScheduler.ps1
# PowerShell script to create Windows Task Scheduler entry for NAT Traffic Collector

# Run this script as Administrator

$TaskName = "VATSIM NAT Traffic Collector"
$Description = "Automated NAT traffic data collection from VATSIM network"
$ScriptPath = "D:\GitHub\vatsim-nat\collector_service.py"
$WorkingDir = "D:\GitHub\vatsim-nat"
$PythonPath = (Get-Command python).Source

# Create the action
$Action = New-ScheduledTaskAction -Execute $PythonPath `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkingDir

# Create the trigger (at startup)
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Create additional trigger (at logon) - backup
$TriggerLogon = New-ScheduledTaskTrigger -AtLogOn

# Settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Principal (run with highest privileges)
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

# Register the task
Register-ScheduledTask -TaskName $TaskName `
    -Description $Description `
    -Action $Action `
    -Trigger $Trigger,$TriggerLogon `
    -Settings $Settings `
    -Principal $Principal `
    -Force

Write-Host "✓ Task '$TaskName' created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "The NAT collector will:" -ForegroundColor Cyan
Write-Host "  • Start automatically at system boot" -ForegroundColor White
Write-Host "  • Restart automatically if it crashes (up to 3 times)" -ForegroundColor White
Write-Host "  • Poll VATSIM every 5 minutes" -ForegroundColor White
Write-Host "  • Track NAT crossings (45-66N, 60-10W)" -ForegroundColor White
Write-Host "  • Write one record per complete crossing" -ForegroundColor White
Write-Host ""
Write-Host "To start now:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
Write-Host ""
Write-Host "To check status:" -ForegroundColor Cyan
Write-Host "  Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Cyan
Write-Host "  Get-Content $WorkingDir\nat_collector.log -Tail 20 -Wait" -ForegroundColor Yellow
