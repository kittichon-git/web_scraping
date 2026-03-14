@echo off
echo ===================================================
echo     Auction Web Scraper (Portable Edition)
echo ===================================================
echo.
cd /d "%~dp0"
set PATH=%~dp0python;%~dp0python\Scripts;%~dp0git\cmd;%PATH%

cd app
echo Pulling latest updates from GitHub...
git pull --rebase origin main

echo.
echo Checking dependencies...
python -m pip install -q -r requirements.txt >nul 2>&1

echo.
echo Scraping data from agencies (This may take 1-3 minutes)
echo Please do not close this window...
echo.

python main.py

echo.
echo ===================================================
echo Uploading latest data to GitHub...
echo ===================================================
git config --local user.email "portable@scraper.bot"
git config --local user.name "Portable Scraper"
git add data/history.json reports/data.json reports/index.html
git commit -m "Manual portable update"
git push origin main

echo.
echo ===================================================
echo Done! The website has been updated successfully.
echo You can now close this window.
echo ===================================================
pause
