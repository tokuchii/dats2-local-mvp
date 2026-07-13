@echo off
setlocal
cd /d "%~dp0"
if not exist backups mkdir backups
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set d=%%d-%%b-%%c
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set t=%%a%%b
copy /y data\dats2.sqlite3 backups\dats2-%d%-%t%.sqlite3
pause
