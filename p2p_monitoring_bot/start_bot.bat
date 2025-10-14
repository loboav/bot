@echo off
color 0A
echo ================================
echo   P2P MONITORING BOT LAUNCHER
echo ================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo.
    echo Please create .env file with your bot token:
    echo BOT_TOKEN=your_token_here
    echo.
    echo Press any key to exit...
    pause > nul
    exit /b 1
)

REM Check and install requirements
echo [INFO] Checking dependencies...
pip show python-telegram-bot >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing requirements...
    pip install -r requirements.txt
    echo.
)

REM Check if python-dotenv is installed
python -c "import dotenv" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing python-dotenv...
    pip install python-dotenv
)

echo [INFO] Starting P2P Monitoring Bot...
echo [INFO] Press Ctrl+C to stop the bot
echo ================================
echo.
python bot/main.py
echo.
echo ================================
echo Bot stopped. Press any key to exit...
color
pause > nul
