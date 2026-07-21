@echo off
chcp 65001 >nul
setlocal
cd /d "D:\AI 프로그램\AgenticWorkflow\ai-news-cards"

REM ============================================================
REM  ai-news-cards : UNATTENDED publisher (no pause).
REM  Run by Windows Task Scheduler on the HOST, where git has
REM  credentials and full .git permissions. The Claude scheduled
REM  task only GENERATES/RENDERS the card files; this publishes.
REM  Idempotent: if nothing new was generated, it just no-ops.
REM ============================================================

if not exist "logs" mkdir "logs"
set "LOG=logs\publish.log"
echo. >> "%LOG%"
echo ===== %DATE% %TIME% : auto_publish start ===== >> "%LOG%"

REM 1) clear any stale lock left by a crashed/sandbox process
if exist ".git\index.lock" (
  del /f /q ".git\index.lock"
  echo removed stale .git\index.lock >> "%LOG%"
)

REM 2) sync branch pointer with origin WITHOUT touching the working
REM    tree, so a locally-behind repo can still fast-forward push.
git fetch origin main >> "%LOG%" 2>&1
git reset --soft origin/main >> "%LOG%" 2>&1

REM 3) stage everything the pipeline generated
git add -A >> "%LOG%" 2>&1

REM 4) commit only if there is something staged
git diff --cached --quiet
if %errorlevel%==0 (
  echo nothing new to publish >> "%LOG%"
  echo ===== done: no changes ===== >> "%LOG%"
  goto :eof
)

git commit -m "news: auto-publish %DATE%" >> "%LOG%" 2>&1
git push origin main >> "%LOG%" 2>&1
if %errorlevel%==0 (
  echo pushed OK - Pages will redeploy in 1-2 min >> "%LOG%"
) else (
  echo PUSH FAILED - see git output above >> "%LOG%"
)
echo ===== done ===== >> "%LOG%"
endlocal
