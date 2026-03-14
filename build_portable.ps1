$target = "PortableScraper"

# Create destination directory
if (Test-Path $target) {
    Remove-Item $target -Recurse -Force
}
New-Item -Path $target -ItemType Directory -Force | Out-Null

Write-Host "1/5 - Downloading Portable Python..."
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip" -OutFile "$target\python.zip"
Expand-Archive -Path "$target\python.zip" -DestinationPath "$target\python" -Force

Write-Host "2/5 - Configuring Python and installing requirements..."
$pth = "$target\python\python310._pth"
(Get-Content $pth) -replace '#import site', 'import site' | Set-Content $pth
Add-Content -Path $pth -Value "..\app"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "$target\python\get-pip.py"
& "$target\python\python.exe" "$target\python\get-pip.py" | Out-Null
& "$target\python\python.exe" -m pip install requests beautifulsoup4 pandas | Out-Null

Write-Host "3/5 - Downloading Portable Git (MinGit)..."
Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/MinGit-2.44.0-64-bit.zip" -OutFile "$target\mingit.zip"
Expand-Archive -Path "$target\mingit.zip" -DestinationPath "$target\git" -Force

Write-Host "4/5 - Cloning Project Repository..."
# Use the freshly downloaded portable git to clone
$env:PATH = "$pwd\$target\git\cmd;" + $env:PATH
& git clone https://github.com/kittichon-git/web_scraping.git "$target\app"

Write-Host "5/5 - Creating Portable Batch Script..."
$batContent = @"
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
"@

# Use ASCII to avoid UTF-8 BOM which breaks Windows Command Prompt
[System.IO.File]::WriteAllText("$pwd\$target\RunScraper.bat", $batContent, [System.Text.Encoding]::ASCII)

# Cleanup zips
Remove-Item "$target\python.zip"
Remove-Item "$target\mingit.zip"

Write-Host "============================================="
Write-Host "Done! PortableScraper environment has been created successfully."
Write-Host "============================================="

