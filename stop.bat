@echo off
REM 与 stop.sh 等价，均委托 project_ctl.py
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" project_ctl.py stop
) else (
  python project_ctl.py stop
)
if errorlevel 1 exit /b 1
