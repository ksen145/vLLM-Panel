#!/bin/bash
# vLLM Panel — one-line installer and launcher
# Usage:
#   curl -sSL https://raw.githubusercontent.com/ksen145/vLLM-Panel/master/run.sh | bash
# or:
#   chmod +x run.sh && ./run.sh

set -e

REPO="ksen145/vLLM-Panel"
BRANCH="master"
DIR="vllm-panel"
CLONE_URL="https://github.com/${REPO}.git"

# ------------------------------------------------------------------
# Checks
# ------------------------------------------------------------------

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found. Please install Python 3.10+."
    exit 1
fi

if ! command -v git &>/dev/null; then
    echo "Error: git not found. Please install Git."
    exit 1
fi

# ------------------------------------------------------------------
# Clone or update
# ------------------------------------------------------------------

if [ -d "$DIR" ]; then
    echo "[INFO] Found existing installation in ./${DIR}, updating..."
    cd "$DIR"
    git pull origin "$BRANCH"
else
    echo "[INFO] Cloning ${REPO}..."
    git clone -b "$BRANCH" "$CLONE_URL" "$DIR"
    cd "$DIR"
fi

# ------------------------------------------------------------------
# Virtual environment
# ------------------------------------------------------------------

if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# ------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------

echo "[INFO] Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# ------------------------------------------------------------------
# Launch
# ------------------------------------------------------------------

echo ""
echo "========================================"
echo "  Starting vLLM Panel"
echo "  http://localhost:8500"
echo "========================================"
echo ""
python master.py
