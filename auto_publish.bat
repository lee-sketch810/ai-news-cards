@echo off
REM cd to this script's own folder (no hardcoded non-ASCII path)
cd /d "%~dp0"

REM ============================================================
REM  ai-news-cards : UNATTENDED publisher (no pause).
REM  Run by Windows Task Scheduler on the HOST. The Claude scheduled
REM  task only GENERATES/RENDERS the card files; this publishes.
REM  Idempotent: if nothing new was generated, it just no-ops.
REM
REM  2026-07: GitHub Pages 배포는 중단하고 iwinv 서버
REM  (ai-news.wiselab.kr)로 완전히 대체했다. git commit은 로컬
REM  버전 이력 목적으로만 유지하고, origin으로 push는 하지 않는다.
REM  실제 배포는 deploy_to_iwinv.bat 이 담당.
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

REM 2) stop tracking the log (one-time self-heal), then stage the rest
git rm -r --cached logs >nul 2>&1
git add -A >> "%LOG%" 2>&1

REM 3) commit locally only if there is something staged (history only,
REM    no push - GitHub Pages is no longer the publish target)
git diff --cached --quiet
if %errorlevel%==0 (
  echo nothing new to commit locally >> "%LOG%"
) else (
  git commit -m "news: auto-publish %DATE%" >> "%LOG%" 2>&1
  echo committed locally ^(no push - iwinv is the publish target^) >> "%LOG%"
)

REM 4) actual publish: upload public\ to the iwinv server
call deploy_to_iwinv.bat
echo ===== done ===== >> "%LOG%"
