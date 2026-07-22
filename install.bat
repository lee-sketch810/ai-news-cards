@echo off
cd /d "%~dp0"

echo ============================================================
echo   ai-news-cards : install auto-publish task (run once)
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_auto_publish.ps1"

echo.
echo ============================================================
echo   verify
echo ============================================================
schtasks /query /tn "ai-news-cards-publish" >nul 2>&1
if %errorlevel%==0 (
  echo [OK] Windows task "ai-news-cards-publish" is registered.
  echo      It will auto-publish the site every day at 09:20.
  echo.
  set /p RUNNOW="Run it once now to test? (y/N): "
  if /I "%RUNNOW%"=="y" (
    schtasks /run /tn "ai-news-cards-publish"
    echo Triggered. Check logs\publish.log in a minute.
  )
) else (
  echo [FAILED] Task was NOT registered.
  echo          Right-click install.bat and choose "Run as administrator", then retry.
)

echo.
pause
