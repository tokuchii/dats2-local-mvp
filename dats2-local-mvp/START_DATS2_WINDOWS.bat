@echo off
setlocal
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
if not exist .venv\.dats2_ready (
  echo Installing open-source dependencies for the first launch...
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  type nul > .venv\.dats2_ready
)

if not exist .env copy .env.example .env >nul
start "DATS2 browser" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8501"
python run_local.py
pause
