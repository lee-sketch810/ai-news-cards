@echo off
REM ============================================================
REM  ai-news-cards : daily GENERATION via local Claude Code CLI.
REM  Run by Windows Task Scheduler at 09:00 KST daily.
REM  This ONLY generates/writes cards (collect->verify->score->write);
REM  auto_publish.bat (separate hourly task) commits + deploys.
REM  workflow.md's Step-0 gap check makes this self-healing: if a
REM  run is skipped, the next run backfills the missing dates first.
REM  Recreated 2026-08-10 after the original schedule for this was
REM  found missing (site was stuck on 2026-08-06 for 4 days).
REM ============================================================
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG=logs\daily_news.log"
echo. >> "%LOG%"
echo ===== %DATE% %TIME% : run_daily_news start ===== >> "%LOG%"
claude -p "/run-daily-news" --dangerously-skip-permissions >> "%LOG%" 2>&1
echo ===== run_daily_news done (exit=%errorlevel%) ===== >> "%LOG%"
