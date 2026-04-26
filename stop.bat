@echo off
REM 与 stop.sh 等价，均委托 run_dev.py
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" run_dev.py stop
) else (
  python run_dev.py stop
)
if errorlevel 1 exit /b 1
