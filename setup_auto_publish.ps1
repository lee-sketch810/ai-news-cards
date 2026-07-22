# ============================================================
#  ONE-TIME SETUP - registers a Windows Scheduled Task that
#  publishes the ai-news-cards site automatically each morning.
#  Run via install.bat (recommended) so encoding/policy are handled.
# ============================================================

$ErrorActionPreference = "Stop"

# Resolve repo folder from this script's own location (avoids any
# hardcoded non-ASCII path that could be mis-decoded).
$repo = $PSScriptRoot
$bat  = Join-Path $repo "auto_publish.bat"
$taskName = "ai-news-cards-publish"

if (-not (Test-Path $bat)) {
    Write-Host "auto_publish.bat not found at: $bat" -ForegroundColor Red
    exit 1
}

$action = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $repo

# Daily 09:20, then retry hourly for 4h in case generation runs late.
$trigger = New-ScheduledTaskTrigger -Daily -At 9:20AM
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At 9:20AM `
    -RepetitionInterval (New-TimeSpan -Minutes 60) `
    -RepetitionDuration (New-TimeSpan -Hours 4)).Repetition

# Catch up if the PC was asleep/off at 09:20; no stacked instances.
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "ai-news-cards: commit and push generated cards to GitHub (auto publish)" `
    -Force | Out-Null

Write-Host ""
Write-Host "Installed. Windows task '$taskName' registered." -ForegroundColor Green
Write-Host "It runs auto_publish.bat every day at 09:20 (retries hourly for 4h)."
Write-Host ""
Write-Host "Test now:   Start-ScheduledTask -TaskName '$taskName'"
Write-Host "Remove:     Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
Write-Host ""
