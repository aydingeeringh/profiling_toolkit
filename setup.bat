@echo off
setlocal enabledelayedexpansion

echo Detected Windows OS

REM Store the script path
set "SCRIPT_PATH=%~f0"

REM Check if running with updated PATH
if not defined UPDATED_PATH (
    REM Install Git if needed
    where git >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Installing Git...
        winget install --id Git.Git -e --source winget
    )

    REM Install Node.js if needed
    where node >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Installing Node.js 20...
        winget install OpenJS.NodeJS.LTS
    )

    REM Update npm if needed
    where npm >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        for /f "tokens=1" %%i in ('npm -v') do set NPM_VERSION=%%i
        if !NPM_VERSION! LSS 7 (
            echo Upgrading npm to latest version...
            npm install -g npm@latest
        )
    )

    REM Install uv if needed
    where uv >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Installing uv...
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    )

    REM Get updated PATH from registry
    for /f "tokens=2*" %%a in ('reg query HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment /v Path') do set "system_path=%%b"
    for /f "tokens=2*" %%a in ('reg query HKEY_CURRENT_USER\Environment /v Path') do set "user_path=%%b"

    REM Create a temporary script with the updated PATH
    echo @echo off > "%TEMP%\temp_setup.bat"
    echo setlocal enabledelayedexpansion >> "%TEMP%\temp_setup.bat"
    echo set "PATH=%system_path%;%user_path%;%ProgramFiles%\Git\cmd;%ProgramFiles%\nodejs;%USERPROFILE%\.cargo\bin" >> "%TEMP%\temp_setup.bat"
    echo set "UPDATED_PATH=1" >> "%TEMP%\temp_setup.bat"
    echo call "%SCRIPT_PATH%" >> "%TEMP%\temp_setup.bat"
    echo exit >> "%TEMP%\temp_setup.bat"

    REM Execute the temporary script
    call "%TEMP%\temp_setup.bat"
    del "%TEMP%\temp_setup.bat"
    exit /b
) else (
    REM Verify installations
    echo.
    echo Verifying installations...
    echo.
    echo Git version:
    git --version
    echo.
    echo Node version:
    node --version
    echo.
    echo NPM version:
    npm --version
    echo.
    echo UV version:
    uv --version
    echo.

    REM Initialize project
    echo Initializing project...
    echo.

    REM Create and activate virtual environment
    call uv venv
    if exist .venv\Scripts\activate.bat (
        call .venv\Scripts\activate.bat
    ) else (
        echo Error: Virtual environment activation script not found
        goto :error
    )

    REM Add virtual environment Scripts to PATH
    set "PATH=%CD%\.venv\Scripts;%PATH%"

    REM Install invoke and run setup commands
    call uv pip install invoke
    if %ERRORLEVEL% NEQ 0 goto :error

    call invoke init
    if %ERRORLEVEL% NEQ 0 goto :error

    call npm install
    if %ERRORLEVEL% NEQ 0 goto :error

    call npm run sources
    if %ERRORLEVEL% NEQ 0 goto :error

    call npm run dev
    if %ERRORLEVEL% NEQ 0 goto :error

    echo.
    echo Setup completed successfully!
    goto :end

:error
    echo.
    echo An error occurred during setup.
    exit /b 1

:end
    echo.
    pause
)
