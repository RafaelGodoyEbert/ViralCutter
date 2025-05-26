#!/bin/bash
# ViralCutter Automated Setup Script
# This script automatically installs ViralCutter and all its dependencies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt; then
            echo "ubuntu"
        elif command_exists yum; then
            echo "centos"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Install system dependencies
install_system_deps() {
    local os=$(detect_os)
    print_status "Installing system dependencies for $os..."
    
    case $os in
        ubuntu)
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv python3-dev ffmpeg git build-essential
            ;;
        centos)
            sudo yum update -y
            sudo yum install -y python3 python3-pip python3-venv python3-devel ffmpeg git gcc gcc-c++
            ;;
        macos)
            if ! command_exists brew; then
                print_error "Homebrew not found. Please install Homebrew first: https://brew.sh"
                exit 1
            fi
            brew install python ffmpeg git
            ;;
        windows)
            print_warning "Windows detected. Please ensure you have Python 3.8+, git, and ffmpeg installed."
            print_warning "Consider using Windows Subsystem for Linux (WSL2) for better compatibility."
            ;;
        *)
            print_error "Unsupported operating system: $os"
            print_warning "Please install Python 3.8+, pip, ffmpeg, and git manually."
            ;;
    esac
    
    print_success "System dependencies installed!"
}

# Check Python version
check_python() {
    print_status "Checking Python version..."
    
    if ! command_exists python3; then
        print_error "Python 3 not found. Please install Python 3.8 or higher."
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.8"
    
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_error "Python $python_version found, but Python $required_version or higher is required."
        exit 1
    fi
    
    print_success "Python $python_version found!"
}

# Check available space
check_disk_space() {
    print_status "Checking available disk space..."
    
    # Get available space in GB
    if command_exists df; then
        available_gb=$(df . | tail -1 | awk '{print int($4/1024/1024)}')
        if [[ $available_gb -lt 10 ]]; then
            print_warning "Low disk space: ${available_gb}GB available. Recommend at least 10GB."
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            print_success "Sufficient disk space: ${available_gb}GB available"
        fi
    fi
}

# Detect GPU
detect_gpu() {
    print_status "Detecting GPU..."
    
    if command_exists nvidia-smi; then
        gpu_info=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)
        print_success "NVIDIA GPU detected: $gpu_info"
        echo "gpu_cuda" > .gpu_type
    elif [[ $(uname -m) == "arm64" ]] && [[ "$OSTYPE" == "darwin"* ]]; then
        print_success "Apple Silicon detected"
        echo "gpu_mps" > .gpu_type
    else
        print_warning "No GPU detected or unsupported GPU. Will use CPU mode."
        echo "cpu" > .gpu_type
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating Python virtual environment..."
    
    if [[ -d "venv" ]]; then
        print_warning "Virtual environment already exists. Removing..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip wheel setuptools
    
    print_success "Virtual environment created and activated!"
}

# Install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    # Make sure we're in the virtual environment
    if [[ -z "$VIRTUAL_ENV" ]]; then
        source venv/bin/activate
    fi
    
    # Read GPU type
    gpu_type="cpu"
    if [[ -f ".gpu_type" ]]; then
        gpu_type=$(cat .gpu_type)
    fi
    
    # Install PyTorch based on GPU type
    case $gpu_type in
        gpu_cuda)
            print_status "Installing PyTorch with CUDA support..."
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
            ;;
        gpu_mps)
            print_status "Installing PyTorch with Apple Silicon support..."
            pip install torch torchvision torchaudio
            ;;
        *)
            print_status "Installing PyTorch (CPU only)..."
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
            ;;
    esac
    
    # Install other dependencies
    print_status "Installing other dependencies..."
    pip install -r requirements.txt
    
    print_success "Python dependencies installed!"
}

# Verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    # Make sure we're in the virtual environment
    if [[ -z "$VIRTUAL_ENV" ]]; then
        source venv/bin/activate
    fi
    
    # Test imports
    python3 -c "
import sys
import torch
import cv2
import mediapipe
import yt_dlp
print('✓ All core dependencies imported successfully!')
print(f'✓ Python version: {sys.version}')
print(f'✓ PyTorch version: {torch.__version__}')
print(f'✓ CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'✓ CUDA device: {torch.cuda.get_device_name(0)}')
" || {
        print_error "Installation verification failed!"
        exit 1
    }
    
    print_success "Installation verified successfully!"
}

# Create directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p tmp final subs subs_ass burned_sub output models
    
    print_success "Directories created!"
}

# Main installation function
main() {
    echo "🎬 ViralCutter Automated Setup"
    echo "=============================="
    echo
    
    # Check if we're in the right directory
    if [[ ! -f "main.py" ]]; then
        print_error "main.py not found. Please run this script from the ViralCutter directory."
        exit 1
    fi
    
    # Run installation steps
    check_disk_space
    install_system_deps
    check_python
    detect_gpu
    create_venv
    install_python_deps
    create_directories
    verify_installation
    
    # Clean up
    rm -f .gpu_type
    
    echo
    print_success "🎉 ViralCutter installation completed successfully!"
    echo
    echo "To use ViralCutter:"
    echo "1. Activate the virtual environment: source venv/bin/activate"
    echo "2. Run the application: python main.py"
    echo
    echo "For more information, see INSTALL.md"
    echo
}

# Handle interruption
trap 'print_error "Installation interrupted!"; exit 1' INT

# Run main installation
main "$@"