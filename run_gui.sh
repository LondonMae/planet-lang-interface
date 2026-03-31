#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

VENV="$DIR/.venv"

if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV"
fi

if ! "$VENV/bin/python" -c "import planet" &>/dev/null; then
    echo "Installing dependencies..."
    "$VENV/bin/pip" install -r requirements.txt
fi

if ! "$VENV/bin/python" -c "import webview" &>/dev/null; then
    echo "Installing pywebview..."
    "$VENV/bin/pip" install pywebview
fi

echo "Launching PLanet Composer..."
"$VENV/bin/python" gui.py
