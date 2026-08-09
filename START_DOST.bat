@echo off
setlocal
cd /d "%~dp0"
title Start DOST Agent

if not exist ".venv\Scripts\python.exe" (
  echo First-time installation is required. Running install.bat...
  call install.bat
)

if not exist ".venv\Scripts\python.exe" (
  echo Installation did not complete.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -c "from agent.config import validate; import sys; p=validate(); [print(' - '+x) for x in p]; sys.exit(1 if p else 0)"
if errorlevel 1 (
  echo Update .env with your Discord details, then run START_DOST.bat again.
  notepad ".env"
  pause
  exit /b 1
)

echo Starting DOST Agent...
call run.bat
