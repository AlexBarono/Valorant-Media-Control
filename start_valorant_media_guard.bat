@echo off
setlocal
cd /d "%~dp0"

call :find_python
if defined PYTHON_CMD goto start_app

echo Python wurde nicht gefunden.
choice /C JN /N /M "Python jetzt installieren? [J/N] "
if errorlevel 2 exit /b 1

where winget >nul 2>nul
if %errorlevel%==0 (
    echo Python wird ueber winget installiert...
    winget install -e --id Python.Python.3.12
) else (
    echo winget wurde nicht gefunden. Die Python-Downloadseite wird geoeffnet.
    start "" "https://www.python.org/downloads/windows/"
    pause
    exit /b 1
)

call :find_python
if not defined PYTHON_CMD (
    echo Python wurde installiert. Starte diese Datei bitte erneut.
    pause
    exit /b 1
)

:start_app
start "" %PYTHON_CMD% "%~dp0valorant_media_guard.py"
exit /b 0

:find_python
set "PYTHON_CMD="
where pyw >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=pyw -3"
    exit /b 0
)
where pythonw >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=pythonw"
    exit /b 0
)
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
    exit /b 0
)
where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    exit /b 0
)
exit /b 1
