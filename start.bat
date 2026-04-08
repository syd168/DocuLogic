@echo off
REM 启动后端 + 前端；与 start.sh 等价，均委托 project_ctl.py
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" project_ctl.py start
) else (
  python project_ctl.py start
)
if errorlevel 1 exit /b 1
