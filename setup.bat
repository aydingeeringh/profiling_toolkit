@echo off
setlocal enabledelayedexpansion

:: Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed.
    echo Installing Python...
    winget install Python.Python.3.11
    if %errorlevel% neq 0 (
        echo Failed to install Python.
        pause
        exit /b 1
    )
    :: Refresh PATH
    call RefreshEnv.cmd
)

:: Check if uv is installed
uv --version > nul 2>&1
if %errorlevel% neq 0 (
    echo uv is not installed.
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo Failed to install uv.
        pause
        exit /b 1
    )
    :: Refresh PATH
    call RefreshEnv.cmd
)

:: Initialize uv and install requirements
echo Setting up virtual environment and installing requirements...
uv init
if %errorlevel% neq 0 (
    echo Failed to initialize uv environment.
    pause
    exit /b 1
)

:: Install requirements if requirements.txt exists
if exist requirements.txt (
    uv pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Failed to install requirements.
        pause
        exit /b 1
    )
) else (
    echo requirements.txt not found.
    pause
    exit /b 1
)

:: Activate virtual environment and run streamlit
echo Starting Streamlit application...
call .\.venv\Scripts\activate
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

streamlit run 01_connector.py
if %errorlevel% neq 0 (
    echo Failed to run Streamlit application.
    pause
    exit /b 1
)

pause
endlocal
