#!/usr/bin/env bash
# =====================================================================
# SO-101 ROBOTICS STUDIO V4 - ONE-CLICK LAUNCHER (Linux / Raspberry Pi)
# =====================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "====================================================================="
echo "          SO-101 ROBOTICS STUDIO V4 - LINUX / RPI LAUNCHER"
echo "====================================================================="

# 1. Verify system Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found!"
    echo "Please install Python 3.10+ using: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

# 2. Check / Create Isolated Virtual Environment
if [ ! -f ".venv/bin/python" ]; then
    echo "[*] Creating isolated virtual environment in .venv ..."
    python3 -m venv .venv
    echo "[OK] Virtual environment created successfully."

    echo "[*] Installing GUI dependencies from requirements_gui.txt ..."
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements_gui.txt || {
        echo "[WARNING] Some dependencies had warnings during initial install. Continuing..."
    }
else
    echo "[*] Virtual environment verified (.venv)."
fi

# 3. Launch SO-101 Studio V4 GUI Application
echo "[*] Launching SO-101 Studio V4 Application..."
echo ""
.venv/bin/python app_v4.py "$@"
