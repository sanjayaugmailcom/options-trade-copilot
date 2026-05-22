@echo off
REM Windows Task Scheduler Script for Options Data Ingestion
REM This script runs the scheduled ingestion every hour
REM
REM To set up:
REM   1. Save this as ingest.bat in your project directory
REM   2. Open Task Scheduler (taskschd.msc)
REM   3. Create Basic Task
REM   4. Trigger: Daily, repeat every 1 hour
REM   5. Action: Start program with script: C:\path\to\ingest.bat

setlocal enabledelayedexpansion

REM Set working directory
cd /d "%~dp0"

REM Activate Python virtual environment (if using venv)
REM Uncomment the line below if you're using a virtual environment
REM call venv\Scripts\activate.bat

REM Log file location
set LOG_FILE=ingestion_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%.log

REM Run ingestion
echo Starting options data ingestion at %date% %time% >> %LOG_FILE%

python scheduled_ingestion.py --mode once >> %LOG_FILE% 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Ingestion completed successfully >> %LOG_FILE%
) else (
    echo [%date% %time%] Ingestion FAILED with error code %ERRORLEVEL% >> %LOG_FILE%
)

echo. >> %LOG_FILE%
endlocal
