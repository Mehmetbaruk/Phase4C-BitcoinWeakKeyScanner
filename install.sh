#!/bin/bash
# Bitcoin Weak Key Scanner - Installation Script
# AWS-optimized installation for Ubuntu/Debian systems

set -e  # Exit on error

echo "======================================================================"
echo "Bitcoin Weak Key Scanner - Installation"
echo "======================================================================"

# Check Python version
echo "Checking Python version..."
python3 --version

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

# Create virtual environment (optional but recommended)
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip3 install --upgrade pip

# Install Python dependencies
echo "Installing Python packages..."
pip3 install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p results
mkdir -p data/test_vectors

# Verify installation
echo ""
echo "======================================================================"
echo "Verifying installation..."
echo "======================================================================"

python3 << EOF
import sys
try:
    import bitcoinlib
    import ecdsa
    import requests
    import yaml
    import numpy
    import scipy
    import pytest
    print("✓ All required packages installed successfully")
    sys.exit(0)
except ImportError as e:
    print(f"✗ Missing package: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "Installation Complete!"
    echo "======================================================================"
    echo ""
    echo "To activate the virtual environment:"
    echo "  source venv/bin/activate"
    echo ""
    echo "To run the scanner:"
    echo "  cd src"
    echo "  python3 main.py --addresses 100"
    echo ""
    echo "To run tests:"
    echo "  pytest tests/ -v"
    echo ""
else
    echo "Installation failed. Please check error messages above."
    exit 1
fi
