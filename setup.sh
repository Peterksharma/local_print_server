#!/bin/bash

# Text colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status messages
print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    python3 -c "import sys; exit(0) if sys.version_info >= (3,7) else exit(1)" >/dev/null 2>&1
}

# Function to setup virtual environment
setup_venv() {
    print_status "Setting up virtual environment..."
    
    # Check if venv exists
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            print_error "Failed to create virtual environment"
            exit 1
        fi
    else
        print_status "Virtual environment already exists"
    fi
}

# Function to install system dependencies
install_system_deps() {
    print_status "Checking system dependencies..."
    
    if command_exists "apt-get"; then
        print_status "Debian/Ubuntu system detected"
        print_status "Installing CUPS development files..."
        sudo apt-get update
        sudo apt-get install -y libcups2-dev
    elif command_exists "brew"; then
        print_status "macOS system detected"
        print_status "Installing CUPS..."
        brew install cups
    else
        print_warning "Unable to determine package manager. Please install CUPS development files manually."
        print_warning "For Ubuntu/Debian: sudo apt-get install libcups2-dev"
        print_warning "For macOS: brew install cups"
        read -p "Press Enter to continue once CUPS is installed..."
    fi
}

# Function to setup directory structure
setup_directories() {
    print_status "Setting up directory structure..."
    
    # Create necessary directories if they don't exist
    mkdir -p static/js
    mkdir -p static/css
    mkdir -p templates
}

# Function to install Python requirements
install_requirements() {
    print_status "Installing Python requirements..."
    
    # Create requirements.txt if it doesn't exist
    if [ ! -f "requirements.txt" ]; then
        cat > requirements.txt << EOL
Flask==3.0.0
flask-cors==4.0.0
flask-limiter==3.5.0
pycups==2.0.1
zeroconf==0.131.0
reportlab==4.0.8
requests==2.31.0
python-dateutil==2.8.2
typing-extensions==4.9.0
Werkzeug==3.0.1
click==8.1.7
itsdangerous==2.1.2
Jinja2==3.1.2
MarkupSafe==2.1.3
EOL
    fi
    
    # Install requirements
    ./venv/bin/pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        print_error "Failed to install requirements"
        exit 1
    fi
}

# Function to start the print server
start_server() {
    print_status "Starting print server..."
    
    # Activate virtual environment and start server
    source ./venv/bin/activate
    python3 print_server.py
    
    if [ $? -ne 0 ]; then
        print_error "Failed to start print server"
        exit 1
    fi
}

# Main execution
main() {
    print_status "Starting setup..."
    
    # Check Python version
    print_status "Checking Python version..."
    if ! check_python_version; then
        print_error "Python 3.7 or higher is required"
        exit 1
    fi
    
    # Install system dependencies
    install_system_deps
    
    # Setup virtual environment
    setup_venv
    
    # Setup directory structure
    setup_directories
    
    # Install Python requirements
    install_requirements
    
    print_status "Setup completed successfully!"
    print_status "To start the server, run: ./setup.sh start"
}

# Parse command line arguments
case "$1" in
    "start")
        start_server
        ;;
    *)
        main
        ;;
esac