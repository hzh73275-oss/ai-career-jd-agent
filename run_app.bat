@echo off
cd /d "%~dp0"

set "LOCAL_PYTHON=%~dp0..\.venv\Scripts\python.exe"

if exist "%LOCAL_PYTHON%" (
  "%LOCAL_PYTHON%" run_app.py
) else (
  python run_app.py
)
