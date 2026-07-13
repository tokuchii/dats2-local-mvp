@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set PYTHON=py -3
) else (
  set PYTHON=python
)

if not exist .venv\Scripts\python.exe (
  echo Creating local Python environment...
  %PYTHON% -m venv .venv
)

call .venv\Scripts\activate.bat

REM Install/upgrade dependencies if requirements.txt changed or first run
if not exist .venv\.dats2_ready (
  echo Installing dependencies for the first launch...
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  type nul > .venv\.dats2_ready
) else (
  REM Check if requirements.txt is newer than the marker file
  for %%A in (requirements.txt) do set "REQ_TIME=%%~tA"
  for %%A in (.venv\.dats2_ready) do set "MARK_TIME=%%~tA"
  if "!REQ_TIME!" GTR "!MARK_TIME!" (
    echo Requirements changed, updating dependencies...
    pip install -r requirements.txt
    copy /y requirements.txt .venv\.dats2_ready >nul
  )
)

if not exist .env copy .env.example .env >nul
start "DATS2 browser" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8501"
python run_local.py
pause
