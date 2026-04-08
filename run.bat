@echo off
setlocal enabledelayedexpansion

:: vLLM Panel - one-line installer and launcher
:: Usage:
::   curl -sSL https://raw.githubusercontent.com/ksen145/vLLM-Panel/master/run.bat -o run.bat ^&^& run.bat

set REPO=ksen145/vLLM-Panel
set BRANCH=master
set DIR=vllm-panel
set CLONE_URL=https://github.com/%REPO%.git

:: ------------------------------------------------------------------
:: Check python
:: ------------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: ------------------------------------------------------------------
:: Clone or update
:: ------------------------------------------------------------------
if exist "%DIR%" (
    echo [INFO] Found existing installation in .\%DIR%, updating...
    cd "%DIR%"
    git pull origin %BRANCH%
) else (
    echo [INFO] Cloning %REPO%...
    git clone -b %BRANCH% %CLONE_URL% %DIR%
    cd %DIR%
)

:: ------------------------------------------------------------------
:: Virtual environment
:: ------------------------------------------------------------------
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

:: ------------------------------------------------------------------
:: Dependencies
:: ------------------------------------------------------------------
echo [INFO] Installing dependencies...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q

:: ------------------------------------------------------------------
:: Launch
:: ------------------------------------------------------------------
echo.
echo ========================================
echo   Starting vLLM Panel
echo   http://localhost:8500
echo ========================================
echo.
python master.py
