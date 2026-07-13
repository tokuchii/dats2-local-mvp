@echo off
setlocal
cd /d "%~dp0"
echo WARNING: This will DELETE ALL DATA from the database.
set /p answer=Type DELETE to confirm:
if /I not "%answer%"=="DELETE" exit /b
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe reset_db.py
) else (
  python reset_db.py
)
pause
