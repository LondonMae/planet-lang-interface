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

echo "Starting PLanet Composer at http://127.0.0.1:8000"
"$VENV/bin/uvicorn" app:app --host 127.0.0.1 --port 8000 --reload
