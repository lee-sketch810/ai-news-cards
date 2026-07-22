@echo off
REM cd to this script's own folder (no hardcoded non-ASCII path)
cd /d "%~dp0"

echo == ai-news-cards: commit and push ==

REM 1) remove any stale git lock left by a crashed/sandbox process
if exist ".git\index.lock" del /f /q ".git\index.lock"

REM 2) sync branch pointer with origin WITHOUT touching the working tree,
REM    so a locally-behind repo can still fast-forward push.
git fetch origin main
git reset --soft origin/main

REM 3) stage everything the pipeline generated
git add -A

REM 4) commit + push (commit is skipped gracefully if nothing changed)
git commit -m "news: publish pending cards"
git push origin main

echo.
echo Done. GitHub Pages will redeploy in about 1-2 minutes.
echo Check: https://lee-sketch810.github.io/ai-news-cards/
pause
