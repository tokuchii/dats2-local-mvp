@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Load REVIEWER_TOKEN from .env file
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "key=%%a"
    if not "!key:~0,1!"=="#" (
        if "!key!"=="REVIEWER_TOKEN" set "REVIEWER_TOKEN=%%b"
    )
)

if not defined REVIEWER_TOKEN (
    echo ERROR: REVIEWER_TOKEN not found in .env file
    pause
    exit /b 1
)

where curl >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: curl is required for export. Install it from https://curl.se/download.html
    pause
    exit /b 1
)

if not exist exports mkdir exports

echo Exporting DATS 2.0 database...
echo.

REM Export XLSX
echo [1/2] Exporting Excel file...
curl -s -o "exports\DATS_2.0_Current_Database.xlsx" -H "Authorization: Bearer %REVIEWER_TOKEN%" "http://localhost:8501/export/current.xlsx"
if %errorlevel%==0 (
    echo     Saved: exports\DATS_2.0_Current_Database.xlsx
) else (
    echo     ERROR: XLSX export failed
)

REM Export CSV
echo [2/2] Exporting CSV file...
curl -s -o "exports\DATS_2.0_Current_Database.csv" -H "Authorization: Bearer %REVIEWER_TOKEN%" "http://localhost:8501/export/current.csv"
if %errorlevel%==0 (
    echo     Saved: exports\DATS_2.0_Current_Database.csv
) else (
    echo     ERROR: CSV export failed
)

echo.
echo Export complete. Files saved to exports\ folder.
pause
