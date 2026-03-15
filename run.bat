@echo off
cd /d %~dp0

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

if not exist ".venv\Scripts\pip.exe" (
    echo [ERROR] venv pip not found.
    pause
    exit /b 1
)

echo [INFO] Installing dependencies...
.venv\Scripts\pip.exe install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo [INFO] Starting octopath-helper...
.venv\Scripts\python.exe main.py
