# ViralCutter Dockerfile
FROM nvidia/cuda:12.1-devel-ubuntu22.04 as cuda-base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    ffmpeg \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install Python dependencies
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip wheel setuptools && \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p tmp final subs subs_ass burned_sub output models

# Set permissions
RUN chmod +x setup.sh

# Create non-root user for security
RUN useradd -m -u 1000 viralcutter && \
    chown -R viralcutter:viralcutter /app

USER viralcutter

# Activate virtual environment by default
ENV PATH="/app/venv/bin:$PATH"

# Expose volume for output
VOLUME ["/app/output"]

# Default command
CMD ["/bin/bash"]

# ============================================
# CPU-only variant
# ============================================
FROM ubuntu:22.04 as cpu-base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    ffmpeg \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install CPU-only PyTorch and other dependencies
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip wheel setuptools && \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

COPY . .

RUN mkdir -p tmp final subs subs_ass burned_sub output models
RUN chmod +x setup.sh

RUN useradd -m -u 1000 viralcutter && \
    chown -R viralcutter:viralcutter /app

USER viralcutter

ENV PATH="/app/venv/bin:$PATH"

VOLUME ["/app/output"]

CMD ["/bin/bash"]