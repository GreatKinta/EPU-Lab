@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" -OpenBrowser %*
if errorlevel 1 (
    echo.
    echo Startup failed. Check that Docker Desktop is running, then try again.
    pause
    exit /b 1
)
endlocal
