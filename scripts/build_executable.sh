#!/bin/bash
set -e

# Ensure we are in the root directory
cd "$(dirname "$0")/.."

# Prefer /usr/bin/python3 on Linux as it usually has shared libs enabled
if [ -f "/usr/bin/python3" ]; then
    PYTHON_EXE="/usr/bin/python3"
else
    PYTHON_EXE="python3"
fi

echo "Using Python: $($PYTHON_EXE --version)"

# Check for venv capability
if ! $PYTHON_EXE -c "import venv" 2>/dev/null; then
    echo "Error: python3-venv is not installed. Please install it (e.g., sudo apt install python3.12-venv)."
    exit 1
fi

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_EXE -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

echo "Building executable..."
pyinstaller --clean agent-sync.spec

echo "Build complete. Executable is in dist/agent-sync"