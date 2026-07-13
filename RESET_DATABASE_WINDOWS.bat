@echo off
setlocal
cd /d "%~dp0"
echo This will remove local submissions, approvals, versions and audit events.
set /p answer=Type RESET to rebuild from the bundled master workbook: 
if /I not "%answer%"=="RESET" exit /b
if exist data\dats2.sqlite3 del /q data\dats2.sqlite3
if exist data\dats2.sqlite3-shm del /q data\dats2.sqlite3-shm
if exist data\dats2.sqlite3-wal del /q data\dats2.sqlite3-wal
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -c "from app.db import init_db; init_db(); print('Database rebuilt.')"
) else (
  python -c "from app.db import init_db; init_db(); print('Database rebuilt.')"
)
pause
