@echo off
cd /d "%~dp0"

where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 "%~dp0valorant_media_guard.py"
) else (
    where pythonw >nul 2>nul
    if %errorlevel%==0 (
        start "" pythonw "%~dp0valorant_media_guard.py"
    ) else (
        where py >nul 2>nul
        if %errorlevel%==0 (
            start "" py -3 "%~dp0valorant_media_guard.py"
        ) else (
            start "" python "%~dp0valorant_media_guard.py"
        )
    )
)

exit /b 0
