@echo off
cd /d "%~dp0"
schtasks /create /tn "ai-news-cards-generate" /tr "\"%~dp0run_daily_news.bat\"" /sc daily /st 09:00 /f > "logs\create_task.txt" 2>&1
echo DONE >> "logs\create_task.txt"
