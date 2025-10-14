@echo off
echo 🚀 Starting P2P Monitoring Bot...
echo.

:: Check if requirements are installed
pip show python-telegram-bot >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing requirements...
    pip install -r requirements.txt
    echo.
)

:: Start the bot
echo 🤖 Launching bot...
python bot/main.py

pause