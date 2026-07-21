@echo off
chcp 65001 >nul
cd /d "D:\AI 프로그램\AgenticWorkflow\ai-news-cards"

echo == ai-news-cards: commit and push ==

REM 1) remove any stale git lock left by a crashed/sandbox process
if exist ".git\index.lock" del /f /q ".git\index.lock"

REM 2) sync branch pointer with origin WITHOUT touching the working tree.
REM    The local repo is often behind origin (published 7/16~7/20 came from
REM    an earlier run), which makes a plain push get rejected. --soft moves
REM    HEAD up to origin while keeping all locally rendered files intact.
git fetch origin main
git reset --soft origin/main

REM 3) stage everything the pipeline generated (new day cards + re-renders)
git add -A

REM 4) commit + push. If nothing new, commit is skipped gracefully.
git commit -m "news: publish pending cards"
git push origin main

echo.
echo Done. GitHub Pages will redeploy in about 1-2 minutes.
echo Check: https://lee-sketch810.github.io/ai-news-cards/
pause
