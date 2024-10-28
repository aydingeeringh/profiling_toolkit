#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare version numbers
version_compare() {
    echo "$@" | awk -F. '{ printf("%d%03d%03d%03d\n", $1,$2,$3,$4); }'
}

# Function to get Python version
get_python_version() {
    if command_exists python3; then
        python3 --version 2>&1 | awk '{print $2}'
    elif command_exists python; then
        python --version 2>&1 | awk '{print $2}'
    else
        echo "0"
    fi
}

# Function to get Node.js version
get_node_version() {
    if command_exists node; then
        node --version 2>&1 | sed 's/v//'
    else
        echo "0"
    fi
}

# Function to get npm version
get_npm_version() {
    if command_exists npm; then
        npm --version
    else
        echo "0"
    fi
}

# Function to get Git version
get_git_version() {
    if command_exists git; then
        git --version | sed 's/git version //'
    else
        echo "0"
    fi
}

# Function to install Git
install_git() {
    echo "=== Checking Git Installation ==="
    
    # Check existing Git installation
    CURRENT_GIT_VERSION=$(get_git_version)
    
    if [ "$CURRENT_GIT_VERSION" != "0" ]; then
        echo "Git is already installed (version $CURRENT_GIT_VERSION)"
        return 0
    fi
    
    echo "Git is not installed. Proceeding with installation..."
    
    # Install Git based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Installing Git for macOS..."
        if ! command_exists brew; then
            echo "Installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install git
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Installing Git for Linux..."
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y git
        elif command_exists yum; then
            sudo yum update -y
            sudo yum install -y git
        elif command_exists dnf; then
            sudo dnf update -y
            sudo dnf install -y git
        fi
        
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win"* ]]; then
        echo "Installing Git for Windows..."
        # Create temporary directory for Git installer
        mkdir -p ~/git_temp
        cd ~/git_temp
        
        # Download and install Git
        curl -o git-setup.exe https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe
        ./git-setup.exe /VERYSILENT /NORESTART
        
        # Cleanup
        cd ..
        rm -rf ~/git_temp
    fi
    
    # Verify installation
    NEW_GIT_VERSION=$(get_git_version)
    if [ "$NEW_GIT_VERSION" != "0" ]; then
        echo "Git installed successfully!"
        echo "Git version: $NEW_GIT_VERSION"
    else
        echo "Git installation failed!"
        exit 1
    fi
}

# Function to install Node.js and npm
install_node() {
    echo "=== Checking Node.js and npm Installation ==="
    
    # Define minimum required versions
    MIN_NODE_VERSION="20.0.0"
    MIN_NPM_VERSION="7.0.0"
    
    # Check existing Node.js installation
    CURRENT_NODE_VERSION=$(get_node_version)
    CURRENT_NPM_VERSION=$(get_npm_version)
    
    if [ "$CURRENT_NODE_VERSION" != "0" ]; then
        echo "Found Node.js version: $CURRENT_NODE_VERSION"
        echo "Found npm version: $CURRENT_NPM_VERSION"
        
        # Compare versions
        if [ $(version_compare $CURRENT_NODE_VERSION) -ge $(version_compare $MIN_NODE_VERSION) ] && \
           [ $(version_compare $CURRENT_NPM_VERSION) -ge $(version_compare $MIN_NPM_VERSION) ]; then
            echo "Current Node.js and npm versions meet requirements. Skipping installation."
            return 0
        else
            echo "Current versions are below minimum required versions (Node.js $MIN_NODE_VERSION, npm $MIN_NPM_VERSION)"
            echo "Proceeding with installation..."
        fi
    else
        echo "Node.js is not installed. Proceeding with installation..."
    fi
    
    # Install Node.js and npm based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Installing Node.js LTS for macOS..."
        if ! command_exists brew; then
            echo "Installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install node@20
        brew link node@20
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Installing Node.js LTS for Linux..."
        # Using NodeSource repository
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        
        if command_exists apt-get; then
            sudo apt-get install -y nodejs
        elif command_exists yum; then
            sudo yum install -y nodejs
        elif command_exists dnf; then
            sudo dnf install -y nodejs
        fi
        
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win"* ]]; then
        echo "Installing Node.js LTS for Windows..."
        mkdir -p ~/node_temp
        cd ~/node_temp
        curl -o node-setup.msi https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi
        msiexec /i node-setup.msi /quiet /qn /norestart
        cd ..
        rm -rf ~/node_temp
    fi
    
    # Verify installation
    NEW_NODE_VERSION=$(get_node_version)
    NEW_NPM_VERSION=$(get_npm_version)
    
    if [ "$NEW_NODE_VERSION" != "0" ]; then
        echo "Node.js installed successfully!"
        echo "Node.js version: $NEW_NODE_VERSION"
        echo "npm version: $NEW_NPM_VERSION"
    else
        echo "Node.js installation failed!"
        exit 1
    fi
}

# Function to install Python and pip
install_python() {
    echo "=== Checking Python Installation ==="
    
    # Define minimum required Python version
    MIN_PYTHON_VERSION="3.8.0"
    
    # Check existing Python installation
    CURRENT_VERSION=$(get_python_version)
    
    if [ "$CURRENT_VERSION" != "0" ]; then
        echo "Found Python version: $CURRENT_VERSION"
        
        # Compare versions
        if [ $(version_compare $CURRENT_VERSION) -ge $(version_compare $MIN_PYTHON_VERSION) ]; then
            echo "Current Python version meets requirements. Skipping Python installation."
            
            # Check pip installation
            if command_exists pip3 || command_exists pip; then
                echo "pip is already installed."
            else
                echo "Installing pip..."
                curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
                python3 get-pip.py || python get-pip.py
                rm get-pip.py
            fi
            
            return 0
        else
            echo "Current Python version ($CURRENT_VERSION) is below minimum required version ($MIN_PYTHON_VERSION)"
            echo "Proceeding with Python installation..."
        fi
    else
        echo "Python is not installed. Proceeding with installation..."
    fi
    
    # Install Python based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Detected macOS..."
        if ! command_exists brew; then
            echo "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Detected Linux..."
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
        elif command_exists yum; then
            sudo yum update -y
            sudo yum install -y python3 python3-pip python3-devel
        elif command_exists dnf; then
            sudo dnf update -y
            sudo dnf install -y python3 python3-pip python3-devel
        else
            echo "Unsupported Linux distribution"
            exit 1
        fi
        
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win"* ]]; then
        echo "Detected Windows..."
        mkdir -p ~/python_temp
        cd ~/python_temp
        curl -O https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe
        ./python-3.11.0-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
        cd ..
        rm -rf ~/python_temp
    fi
    
    # Verify installation
    NEW_VERSION=$(get_python_version)
    if [ "$NEW_VERSION" != "0" ]; then
        echo "Python installed successfully!"
        echo "Installed version: $NEW_VERSION"
    else
        echo "Python installation failed!"
        exit 1
    fi
    
    # Install/upgrade pip
    echo "Upgrading pip..."
    if command_exists python3; then
        python3 -m pip install --upgrade pip
    else
        python -m pip install --upgrade pip
    fi
}

# Function to create Python virtual environment
create_virtual_env() {
    echo "=== Setting up Python Virtual Environment ==="
    
    # Check if we're in a directory with requirements.txt
    if [ ! -f "requirements.txt" ]; then
        echo "Warning: requirements.txt not found in current directory"
        echo "Will create virtual environment without installing dependencies"
    fi
    
    # Create .env directory if it doesn't exist
    if [ -d ".env" ]; then
        echo "Warning: .env directory already exists"
        read -p "Do you want to remove it and create a new one? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf .env
        else
            echo "Keeping existing .env directory"
            return 0
        fi
    fi
    
    echo "Creating new Python virtual environment in .env..."
    if command_exists python3; then
        python3 -m venv .env
    else
        python -m venv .env
    fi
    
    # Activate the virtual environment
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win"* ]]; then
        source .env/Scripts/activate
    else
        source .env/bin/activate
    fi
    
    # Upgrade pip in the virtual environment
    echo "Upgrading pip..."
    pip install --upgrade pip
    
    # Install requirements if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        echo "Installing dependencies from requirements.txt..."
        pip install -r requirements.txt
    else
        echo "No requirements.txt found. Skipping dependency installation."
    fi
    
    echo "Virtual environment created and activated in .env"
    echo "To activate the virtual environment in the future, run:"
    echo "source .env/bin/activate  # For Unix-like systems"
    echo "# OR"
    echo "source .env/Scripts/activate  # For Windows"
}

# Function to check system requirements
check_requirements() {
    echo "Checking system requirements..."
    
    # Check for Docker
    if ! command_exists docker; then
        echo "Docker is not installed. Please install Docker first."
        echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check system resources
    CPU_COUNT=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null)
    TOTAL_MEM=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}' || sysctl -n hw.memsize 2>/dev/null | awk '{print $1/1024/1024/1024}')
    
    echo "Available CPU cores: $CPU_COUNT"
    echo "Available Memory: ${TOTAL_MEM}GB"
}

# Function to install Airbyte
install_airbyte() {
    echo "=== Installing Airbyte ==="
    
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Installing abctl for Mac/Linux..."
        curl -LsfS https://get.airbyte.com | bash -
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win"* ]]; then
        echo "Installing abctl for Windows..."
        mkdir -p ~/airbyte_temp
        cd ~/airbyte_temp
        curl -LO https://github.com/airbytehq/abctl/releases/download/v0.19.0/abctl-v0.19.0-windows-amd64.zip
        unzip abctl-v0.19.0-windows-amd64.zip
        mkdir -p ~/airbyte
        mv abctl/* ~/airbyte/
        echo "export PATH=\$PATH:~/airbyte" >> ~/.bashrc
        source ~/.bashrc
        cd ..
        rm -rf ~/airbyte_temp
    else
        echo "Unsupported operating system"
        exit 1
    fi
}

# Function to start Airbyte
start_airbyte() {
    echo "Starting Airbyte..."
    
    if [ "$CPU_COUNT" -lt 4 ] || [ $(echo "$TOTAL_MEM < 8" | bc) -eq 1 ]; then
        echo "Running in low resource mode due to system specifications..."
        abctl local install --low-resource-mode
    else
        abctl local install
    fi
    
    echo "Retrieving Airbyte credentials..."
    abctl local credentials
}

# Function to start PostgreSQL container
start_postgres() {
    echo "=== Starting PostgreSQL Container ==="
    
    # Check if docker-compose.yml exists
    if [ ! -f "docker-compose.yml" ]; then
        echo "Error: docker-compose.yml not found in current directory"
        exit 1
    fi
    
    # Check if containers are already running
    if docker-compose ps | grep -q "Up"; then
        echo "Docker containers are already running"
        echo "Current containers status:"
        docker-compose ps
        
        read -p "Do you want to restart the containers? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Restarting containers..."
            docker-compose down
            docker-compose up -d
        else
            echo "Keeping existing containers running"
            return 0
        fi
    else
        echo "Starting Docker containers..."
        docker-compose up -d
    fi
    
    # Wait for PostgreSQL to be ready
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5  # Initial sleep to give PostgreSQL time to start
    
    # Get the PostgreSQL container name
    PG_CONTAINER=$(docker-compose ps | grep postgres | awk '{print $1}')
    
    if [ -n "$PG_CONTAINER" ]; then
        # Try to connect to PostgreSQL for up to 30 seconds
        for i in {1..6}; do
            if docker exec $PG_CONTAINER pg_isready > /dev/null 2>&1; then
                echo "PostgreSQL is ready!"
                echo "Container name: $PG_CONTAINER"
                echo "Container status:"
                docker-compose ps
                return 0
            fi
            echo "Waiting for PostgreSQL to be ready... (attempt $i/6)"
            sleep 5
        done
        echo "Warning: PostgreSQL container may not be fully ready. Please check the logs:"
        echo "docker-compose logs postgres"
    else
        echo "Warning: Could not find PostgreSQL container"
    fi
}

# Main execution
echo "=== Complete Development Environment Setup ==="
echo "This script will install and configure:"
echo "- Git"
echo "- Python and pip"
echo "- Node.js and npm"
echo "- Airbyte"
echo "- Virtual Environment"
echo "- PostgreSQL (Docker container)"

# Prompt for confirmation
read -p "Do you want to proceed with the installation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

# Install Git first
install_git

# Install Python
install_python

# Install Node.js and npm
install_node

# Create Python virtual environment
create_virtual_env

# Check requirements for Airbyte
check_requirements

# Execute Airbyte installation steps
install_airbyte

# Verify Airbyte installation
if ! command_exists abctl; then
    echo "Airbyte installation failed. Please try again or install manually."
    exit 1
fi

echo "Verifying Airbyte installation..."
abctl version

# Start Airbyte
start_airbyte

# Start PostgreSQL container
start_postgres

echo "=== Installation Complete ==="
echo "All components have been installed successfully!"
echo "Python virtual environment is created in .env"
echo "You can access Airbyte at http://localhost:8000"
echo "Use the credentials shown above to log in."
echo "To get your credentials again, run: abctl local credentials"
echo "PostgreSQL is running in Docker container"
echo "To check PostgreSQL logs: docker-compose logs postgres"
echo "To stop PostgreSQL: docker-compose down"