#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment (.venv)..."
  python3 -m venv .venv
fi

echo "Checking dependencies..."
.venv/bin/pip install -q -r requirements.txt

echo "Starting Book Cover Studio at http://localhost:8765 ..."
(sleep 1 && (xdg-open "http://localhost:8765" 2>/dev/null || open "http://localhost:8765" 2>/dev/null || true)) &
.venv/bin/python server.py
