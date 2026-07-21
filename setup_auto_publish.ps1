# ============================================================
#  ONE-TIME SETUP — run once, then forget.
#  Registers a Windows Scheduled Task that publishes the
#  ai-news-cards site automatically each morning, so pushing
#  no longer depends on you double-clicking a .bat.
#
#  How to run:
#    Right-click this file  ->  "Run with PowerShell"
#    (or in PowerShell:  powershell -ExecutionPolicy Bypass -File .\setup_auto_publish.ps1 )
# ============================================================

$ErrorActionPreference = "Stop"

$repo = "D:\AI 프로그램\AgenticWorkflow\ai-news-cards"
$bat  = Join-Path $repo "auto_publish.bat"
$taskName = "ai-news-cards-publish"

if (-not (Test-Path $bat)) {
    Write-Host "auto_publish.bat 를 찾을 수 없습니다: $bat" -ForegroundColor Red
    exit 1
}

# Action: run the unattended publisher in the repo folder
$action = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $repo

# Trigger: daily 09:20, then retry hourly for 4h so it still fires
# even if that morning's card generation finishes a bit late.
$trigger = New-ScheduledTaskTrigger -Daily -At 9:20AM
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At 9:20AM `
    -RepetitionInterval (New-TimeSpan -Minutes 60) `
    -RepetitionDuration (New-TimeSpan -Hours 4)).Repetition

# Settings: catch up if the PC was asleep/off at 09:20 (StartWhenAvailable),
# don't stack instances, and cap runtime.
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "ai-news-cards: commit & push generated cards to GitHub (auto publish)" `
    -Force | Out-Null

Write-Host ""
Write-Host "설치 완료 - Windows 작업 '$taskName' 등록됨." -ForegroundColor Green
Write-Host "매일 09:20에 (필요시 4시간 동안 1시간 간격 재시도) auto_publish.bat 이 실행됩니다."
Write-Host ""
Write-Host "지금 바로 한 번 실행해 테스트하려면:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName '$taskName'"
Write-Host "제거하려면:"
Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
Write-Host ""
Read-Host "엔터를 누르면 종료합니다"
