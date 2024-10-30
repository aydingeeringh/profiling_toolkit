@echo off
setlocal enabledelayedexpansion

echo Detected Windows OS

REM Check Git
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing Git...
    winget install --id Git.Git -e --source winget
)

REM Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing Node.js 20...
    winget install OpenJS.NodeJS.LTS
)

REM Check npm version
where npm >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=1" %%i in ('npm -v') do set NPM_VERSION=%%i
    if !NPM_VERSION! LSS 7 (
        echo Upgrading npm to latest version...
        npm install -g npm@latest
    )
)

REM Install uv
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    REM Update PATH for current session
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
)

REM Verify installations
echo Verifying installations...
git --version
node --version
npm --version
uv --version

REM Initialize project
echo Initializing project...
uv venv
uv pip install invoke
invoke init
npm install
npm run sources
npm run dev

echo Setup complete!

pause