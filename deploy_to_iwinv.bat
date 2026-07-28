@echo off
REM ============================================================
REM  ai-news-cards : iwinv 서버로 자동 업로드 (GitHub push 대체)
REM  Windows Task Scheduler가 매일 이 스크립트를 실행한다.
REM  Claude가 생성한 public\ 폴더 전체를 서버 웹 루트로 scp 복사.
REM ============================================================

cd /d "%~dp0"

REM ---- 설정값 (필요하면 이 4줄만 수정) ----
set "IWINV_HOST=49.247.137.87"
set "IWINV_USER=root"
set "IWINV_PATH=/var/www/ai-news-cards"
set "SSH_KEY=%USERPROFILE%\.ssh\iwinv_deploy"
REM -----------------------------------------

if not exist "logs" mkdir "logs"
set "LOG=logs\deploy_iwinv.log"
echo. >> "%LOG%"
echo ===== %DATE% %TIME% : deploy_to_iwinv start ===== >> "%LOG%"

if not exist "%SSH_KEY%" (
  echo SSH key not found at %SSH_KEY% >> "%LOG%"
  echo SSH key not found at %SSH_KEY%
  echo   IWINV_SETUP.md 7단계를 먼저 진행하세요.
  goto :eof
)

echo uploading public\ to %IWINV_USER%@%IWINV_HOST%:%IWINV_PATH% >> "%LOG%"

scp -i "%SSH_KEY%" -o StrictHostKeyChecking=no -r "public\*" "%IWINV_USER%@%IWINV_HOST%:%IWINV_PATH%/" >> "%LOG%" 2>&1

if %errorlevel%==0 (
  echo upload OK - https://ai-news.wiselab.kr >> "%LOG%"
  echo upload OK - https://ai-news.wiselab.kr
) else (
  echo UPLOAD FAILED - see %LOG% >> "%LOG%"
  echo UPLOAD FAILED - see %LOG%
)
echo ===== done ===== >> "%LOG%"
