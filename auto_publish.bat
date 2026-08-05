@echo off
REM cd to this script's own folder (no hardcoded non-ASCII path)
cd /d "%~dp0"

REM ============================================================
REM  ai-news-cards : UNATTENDED publisher (no pause).
REM  Run by Windows Task Scheduler on the HOST.
REM
REM  2026-08 변경: 뉴스 "생성"은 더 이상 이 PC에서 하지 않는다.
REM  GitHub Actions(클라우드)가 매일 09:00 KST에 뉴스를 생성해서
REM  origin/main 에 직접 push한다. 이 스크립트는 이제:
REM    1) origin/main 을 pull 해서 GitHub Actions가 만든 새 카드/파일을 받고
REM    2) deploy_to_iwinv.bat 으로 public\ 을 iwinv 서버에 올리기만 한다.
REM  로컬에서 뭔가를 직접 만들어서 커밋하는 로직은 제거했다(더 이상 필요 없음).
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

REM 2) pull whatever GitHub Actions generated & pushed overnight.
REM    Working tree here should always be clean (nothing is edited locally
REM    anymore), so a plain fast-forward pull is safe. If it ever isn't
REM    (e.g. you edited something by hand), this will fail loudly in the
REM    log instead of silently discarding your edit.
git fetch origin main >> "%LOG%" 2>&1
git merge --ff-only origin/main >> "%LOG%" 2>&1
if %errorlevel% neq 0 (
  echo PULL FAILED - working tree not in sync, check %LOG% and resolve manually >> "%LOG%"
  echo PULL FAILED - see %LOG%
  goto :eof
)
echo pulled latest from origin/main >> "%LOG%"

REM 3) actual publish: upload public\ to the iwinv server
call deploy_to_iwinv.bat
echo ===== done ===== >> "%LOG%"
