# ViralCutter Installation Guide

This guide will help you install ViralCutter and all its dependencies on your system.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+), macOS, or Windows (with WSL2 recommended)
- **Python**: 3.8 or higher (3.10+ recommended)
- **Memory**: At least 8GB RAM (16GB+ recommended for large videos)
- **Storage**: 10GB+ free space for dependencies and temporary files
- **GPU**: NVIDIA GPU with CUDA support (optional but recommended for faster processing)

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git
```

#### macOS (with Homebrew)
```bash
brew install python ffmpeg git
```

#### Windows (WSL2/Ubuntu)
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git
```

## 🚀 Quick Installation

### Option 1: Automatic Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/RafaelGodoyEbert/ViralCutter.git
cd ViralCutter

# Run the setup script
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Installation

#### Step 1: Clone the Repository
```bash
git clone https://github.com/RafaelGodoyEbert/ViralCutter.git
cd ViralCutter
```

#### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 3: Install Python Dependencies

**IMPORTANT**: Install PyTorch first with the correct CUDA version for your GPU:

##### For RTX 5090 / RTX 50-Series (CUDA 12.8):
```bash
# Upgrade pip first
pip install --upgrade pip

# Install PyTorch with CUDA 12.8 support (RTX 5090 compatible)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Install remaining dependencies
pip install -r requirements.txt
```

##### For RTX 40/30-Series / Other GPUs (CUDA 12.1):
```bash
# Upgrade pip first
pip install --upgrade pip

# Install PyTorch with CUDA 12.1 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install remaining dependencies
pip install -r requirements.txt
```

##### For CPU Only:
```bash
# Upgrade pip first
pip install --upgrade pip

# Install PyTorch CPU version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
pip install -r requirements.txt
```

## 🎯 GPU Support (Optional but Recommended)

### NVIDIA GPU with CUDA
If you have an NVIDIA GPU, install CUDA support for faster processing:

#### RTX 5090 / RTX 50-Series (Latest GPUs - CUDA 12.8+)
For the newest RTX 5090 and RTX 50-series GPUs, use CUDA 12.8:
```bash
# Check CUDA availability
nvidia-smi

# Install PyTorch with CUDA 12.8 support (RTX 5090 compatible)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

#### RTX 40-Series / RTX 30-Series / Other GPUs (CUDA 12.1)
For older RTX GPUs and most NVIDIA cards:
```bash
# Check CUDA availability
nvidia-smi

# Install PyTorch with CUDA 12.1 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### Verify GPU Installation
After installation, verify your GPU is working:
```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"No GPU\"}')"
```

### Apple Silicon (M1/M2/M3 Macs)
```bash
# Install PyTorch optimized for Apple Silicon
pip install torch torchvision torchaudio
```

## 🎤 Transcription Engine Choice

ViralCutter supports two transcription engines. Choose based on your hardware and needs:

### OpenAI Whisper (Recommended - Currently Default)
- **Pros**: Reliable, stable, works with all hardware including RTX 5090
- **Cons**: Slightly slower than WhisperX
- **Best for**: RTX 5090 users, production use, stability
- **Installation**: Included in requirements.txt by default

### WhisperX (Advanced - Optional)
- **Pros**: Faster transcription, better alignment features
- **Cons**: Dependency conflicts with RTX 5090/newer PyTorch versions
- **Best for**: RTX 40-series and older GPUs, advanced users
- **Installation**: 
```bash
# Only install if you don't have RTX 5090 and want faster transcription
pip install whisperx>=3.3.4
```

**Note**: The default setup uses OpenAI Whisper for maximum compatibility. Advanced users with compatible hardware can switch to WhisperX for better performance.

## 🔧 Installation Options

### Lightweight Installation (CPU Only)
For systems without GPU or with limited resources:
```bash
# Install CPU-only versions
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Full Installation with Development Tools
For contributors or advanced users:
```bash
pip install -r requirements.txt
pip install pytest black flake8  # Development tools
```

## 🐳 Docker Installation (Alternative)

### Using Docker
```bash
# Build the Docker image
docker build -t viralcutter .

# Run the container
docker run -it --rm -v $(pwd)/output:/app/output viralcutter
```

### Using Docker Compose
```bash
docker-compose up --build
```

## ✅ Verify Installation

After installation, verify everything works:

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Test the installation
python -c "import torch, cv2, mediapipe, whisperx; print('All dependencies installed successfully!')"

# Run ViralCutter
python main.py
```

## 🚨 Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'X'"
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall the missing package
pip install <package-name>
```

#### 2. "ffmpeg not found"
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows (with chocolatey)
choco install ffmpeg
```

#### 3. CUDA Issues
```bash
# Check CUDA installation
nvidia-smi
nvcc --version

# For RTX 5090 / RTX 50-series GPUs
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# For RTX 40-series / RTX 30-series / Other GPUs
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### 4. RTX 5090 Specific Issues
If you see warnings about CUDA capability `sm_120` not being supported:
```bash
# This indicates you need CUDA 12.8+ for RTX 5090
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Verify RTX 5090 is working
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}'); print(f'CUDA Capability: sm_{torch.cuda.get_device_capability(0)[0]}{torch.cuda.get_device_capability(0)[1]}')"
```

#### 5. Memory Issues
- Reduce video resolution or length
- Close other applications
- Use CPU-only mode if GPU memory is insufficient

#### 6. WhisperX vs OpenAI Whisper Issues
If you encounter transcription errors:

```bash
# Check which transcription engine is being used
python -c "import whisperx; print('WhisperX available')" 2>/dev/null || echo "Using OpenAI Whisper"

# If WhisperX causes issues (especially with RTX 5090), switch to OpenAI Whisper:
pip uninstall whisperx
pip install openai-whisper

# If you have dependency conflicts:
pip install "numpy>=1.26.4,<2.0"  # Fix mediapipe compatibility
```

#### 7. Transcription Performance Issues
```bash
# For RTX 5090 users experiencing slow transcription:
# This is expected - RTX 5090 currently uses CPU mode for compatibility
# Performance: CPU mode ~5-10 minutes for 10-minute video

# For other GPUs, verify CUDA is working:
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# If CUDA not available, reinstall PyTorch with correct CUDA version
```

#### 8. Permission Issues (Linux/macOS)
```bash
# Make scripts executable
chmod +x setup.sh

# Fix pip permissions
pip install --user -r requirements.txt
```

### Performance Tips

1. **Use GPU**: Install CUDA for 10x faster processing
2. **SSD Storage**: Use SSD for temporary files
3. **RAM**: More RAM allows processing longer videos
4. **Close Apps**: Close unnecessary applications during processing

## 📝 Environment Variables (Optional)

Create a `.env` file for custom settings:
```bash
# GPU settings
CUDA_VISIBLE_DEVICES=0
TORCH_HOME=/path/to/torch/models

# Temporary directory
TEMP_DIR=/path/to/fast/storage

# WhisperX model cache
WHISPERX_CACHE_DIR=/path/to/model/cache
```

## 🔄 Updating ViralCutter

```bash
# Pull latest changes
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## 💡 Alternative Installation Methods

### Conda/Mamba (Alternative Package Manager)
```bash
# Create conda environment
conda create -n viralcutter python=3.10
conda activate viralcutter

# Install dependencies
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
pip install -r requirements.txt
```

### Using pipx (For Global Installation)
```bash
# Install pipx
pip install pipx

# Install ViralCutter globally
pipx install .
```

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs**: Look for error messages in the terminal
2. **Search issues**: Check [GitHub Issues](https://github.com/RafaelGodoyEbert/ViralCutter/issues)
3. **Create an issue**: If your problem isn't listed, create a new issue
4. **Discord**: Join the [AI Hub Brasil Discord](https://discord.gg/aihubbrasil)

## 📊 System Requirements by Use Case

| Use Case | RAM | Storage | GPU | CUDA Version | Processing Time (10min video) |
|----------|-----|---------|-----|--------------|-------------------------------|
| Basic    | 8GB | 5GB     | No  | N/A          | 30-60 minutes                |
| Standard | 16GB| 10GB    | GTX 1060+ | 12.1     | 10-20 minutes          |
| High-end | 32GB| 20GB    | RTX 3080+ | 12.1     | 3-8 minutes            |
| Ultimate | 32GB| 20GB    | RTX 5090  | 12.8     | 1-3 minutes            |

### GPU Performance Comparison

#### Transcription Performance (10-minute video):
| GPU | OpenAI Whisper | WhisperX | Notes |
|-----|---------------|----------|-------|
| **CPU Only** | 30-60 min | 20-40 min | Works on any system |
| **GTX 1060-1080** | 5-15 min | 3-8 min | CUDA 12.1 |
| **RTX 2070-3070** | 3-10 min | 2-5 min | CUDA 12.1 |
| **RTX 3080-4080** | 2-6 min | 1-3 min | CUDA 12.1 |
| **RTX 5090** | 30-60 min (CPU) | Not Compatible | CUDA 12.8, CPU fallback |

#### Current Status:
- **OpenAI Whisper**: Reliable on all hardware, CPU fallback for RTX 5090
- **WhisperX**: Faster when compatible, but has RTX 5090 dependency conflicts
- **RTX 5090 Users**: Currently limited to CPU transcription until WhisperX compatibility is resolved

#### Video Processing Performance:
- **RTX 5090**: Still provides 30-50x faster video processing compared to CPU
- **GPU acceleration**: Fully working for video editing and face detection

---

**Ready to create viral content? Run `python main.py` and start generating!** 🎬✨