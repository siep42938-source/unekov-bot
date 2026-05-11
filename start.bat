@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════╗
echo ║   UNEKOV.HELP — Starting Bot...      ║
echo ╚══════════════════════════════════════╝
echo.
call venv\Scripts\activate.bat
python main.py
pause
