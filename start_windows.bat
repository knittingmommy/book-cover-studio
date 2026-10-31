@echo off
cd /d "%~dp0"

if not exist ".venv" (
    echo Creating Python virtual environment (.venv)...
    python -m venv .venv
)

echo Checking dependencies...
.venv\Scripts\pip install -q -r requirements.txt

echo Starting Book Cover Studio at http://localhost:8765 ...
start "" "http://localhost:8765"
.venv\Scripts\python server.py
pause
