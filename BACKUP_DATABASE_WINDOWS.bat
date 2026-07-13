@echo off
setlocal
cd /d "%~dp0"
if not exist backups mkdir backups
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set d=%%d-%%b-%%c
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set t=%%a%%b
pg_dump -F c -f backups\dats2-%d%-%t%.dump %DATABASE_URL%
echo Backup saved to backups\dats2-%d%-%t%.dump
pause
