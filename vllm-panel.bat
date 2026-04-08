@echo off
setlocal enabledelayedexpansion
title vLLM Panel

:MENU
cls
echo ================================================
echo   vLLM Panel
echo ================================================
echo.
echo   1. Install dependencies
echo   2. Install vLLM backend
echo   3. Start Panel
echo   4. Stop Panel
echo   5. Check status
echo   6. Open browser
echo   7. View log
echo   8. Exit
echo.
echo ================================================

set /p choice="Choice (1-8): "

if "%choice%"=="1" goto INSTALL
if "%choice%"=="2" goto INSTALL_BACKEND
if "%choice%"=="3" goto START
if "%choice%"=="4" goto STOP
if "%choice%"=="5" goto STATUS
if "%choice%"=="6" goto BROWSER
if "%choice%"=="7" goto LOG
if "%choice%"=="8" goto EXIT

:INSTALL
echo.
echo Installing core dependencies...
python -m pip install --upgrade pip
pip install fastapi uvicorn psutil pydantic huggingface_hub
echo Done!
pause
goto MENU

:INSTALL_BACKEND
echo.
echo Installing vLLM backend...
echo This requires CUDA and an NVIDIA GPU.
pip install vllm
echo Done!
pause
goto MENU

:START
echo.
echo Checking if Panel is running...
netstat -ano | findstr :8500 >nul 2>&1
if !errorlevel! equ 0 (
    echo Panel is already running on port 8500
) else (
    echo Starting vLLM Panel...
    start "vLLM Panel" /MIN cmd /c "python master.py > server.log 2>&1"
    timeout /t 3 >nul
    echo Started!
    echo   Panel: http://localhost:8500
    echo   vLLM:  http://localhost:8001/v1
)
echo.
pause
goto MENU

:STOP
echo.
echo Stopping Panel...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8500') do (
    taskkill /F /PID %%a >nul 2>&1
    echo Terminated PID %%a
)
echo Done.
pause
goto MENU

:STATUS
echo.
echo Panel status:
netstat -ano | findstr :8500
if !errorlevel! equ 0 (
    echo.
    echo Status: RUNNING
    curl -s http://localhost:8500/api/info 2>nul | python -m json.tool 2>nul
) else (
    echo Status: NOT RUNNING
)
echo.
pause
goto MENU

:BROWSER
start http://localhost:8500
goto MENU

:LOG
echo.
if exist server.log (
    echo === Last 50 lines of server.log ===
    powershell -Command "Get-Content server.log -Tail 50"
) else (
    echo No log file found.
)
echo.
pause
goto MENU

:EXIT
echo.
echo Goodbye!
exit /b 0
