#!/bin/bash

# Function to check if a command exists
check_command() {
    command -v "$1" >/dev/null 2>&1
}

# Create a temporary Windows batch script for CMD operations
create_windows_script() {
    cat > setup.bat << 'EOL'
@echo off
setlocal enabledelayedexpansion

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
)

REM Verify installations
echo Verifying installations...
git --version
node --version
npm --version
uv --version

REM Initialize project
echo Initializing project...
uv init
npm install
npm run sources
npm run dev

echo Setup complete!
EOL
}

# Create a temporary PowerShell script
create_powershell_script() {
    cat > setup.ps1 << 'EOL'
# Check Git
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Git..."
    winget install --id Git.Git -e --source winget
}

# Check Node.js
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Node.js 20..."
    winget install OpenJS.NodeJS.LTS
}

# Check npm version
if (Get-Command npm -ErrorAction SilentlyContinue) {
    $npmVersion = (npm -v).Split(".")[0]
    if ([int]$npmVersion -lt 7) {
        Write-Host "Upgrading npm to latest version..."
        npm install -g npm@latest
    }
}

# Install uv
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    iex (irm https://astral.sh/uv/install.ps1)
}

# Verify installations
Write-Host "Verifying installations..."
git --version
node --version
npm --version
uv --version

# Initialize project
Write-Host "Initializing project..."
uv init
npm install
npm run sources
npm run dev

Write-Host "Setup complete!"
EOL
}

# Detect OS and execute appropriate script
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows setup
    echo "Detected Windows OS"
    
    # Check if running in PowerShell
    if [[ $(ps -p $$ -o comm=) == *"pwsh"* ]] || [[ $(ps -p $$ -o comm=) == *"powershell"* ]]; then
        create_powershell_script
        powershell -ExecutionPolicy ByPass -File setup.ps1
        rm setup.ps1
    else
        create_windows_script
        cmd.exe /c setup.bat
        rm setup.bat
    fi
    
else
    # Unix-like systems (macOS/Linux)
    echo "Detected Unix-like OS"
    
    # Check Git
    if ! check_command "git"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            echo "Installing Git..."
            brew install git
        else
            # Linux
            echo "Installing Git..."
            sudo apt-get update && sudo apt-get install -y git
        fi
    fi
    
    # Check Node.js
    if ! check_command "node"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            echo "Installing Node.js 20..."
            brew install node@20
        else
            # Linux
            echo "Installing Node.js 20..."
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            sudo apt-get install -y nodejs
        fi
    fi
    
    # Check npm version and upgrade if needed
    if check_command "npm"; then
        NPM_VERSION=$(npm -v)
        if [[ "${NPM_VERSION%%.*}" -lt 7 ]]; then
            echo "Upgrading npm to latest version..."
            npm install -g npm@latest
        fi
    fi
    
    # Install uv
    if ! check_command "uv"; then
        echo "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    
    # Verify installations
    echo "Verifying installations..."
    git --version
    node --version
    npm --version
    uv --version
    
    # Initialize project
    echo "Initializing project..."
    uv venv
    invoke init
fi

echo "Setup complete!"
