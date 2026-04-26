@echo off
REM 启动后端 + 前端；与 start.sh 等价，均委托 run_dev.py
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" run_dev.py start
) else (
  python run_dev.py start
)
if errorlevel 1 exit /b 1
