@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Load DATABASE_URL from .env file
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "key=%%a"
    if not "!key:~0,1!"=="#" (
        if "!key!"=="DATABASE_URL" set "DATABASE_URL=%%b"
    )
)

if not defined DATABASE_URL (
    echo ERROR: DATABASE_URL not found in .env file
    pause
    exit /b 1
)

if not exist backups mkdir backups
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set d=%%d-%%b-%%c
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set t=%%a%%b
pg_dump -F c -f "backups\dats2-%d%-%t%.dump" "%DATABASE_URL%"
if %errorlevel%==0 (
    echo Backup saved to backups\dats2-%d%-%t%.dump
) else (
    echo ERROR: Backup failed. Make sure pg_dump is in your PATH.
)
pause
