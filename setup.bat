@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════╗
echo ║   UNEKOV.HELP — Setup ^& Start        ║
echo ╚══════════════════════════════════════╝
echo.

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден! Установи Python 3.12+
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Создаём виртуальное окружение...
if not exist "venv" (
    python -m venv venv
)

echo [2/5] Активируем venv...
call venv\Scripts\activate.bat

echo [3/5] Устанавливаем зависимости...
pip install -r requirements.txt --quiet

echo [4/5] Проверяем .env файл...
if not exist ".env" (
    copy .env.example .env
    echo.
    echo [!] Создан файл .env
    echo [!] ОБЯЗАТЕЛЬНО заполни:
    echo     BOT_TOKEN=  (получи у @BotFather)
    echo     SECRET_KEY= (любая строка 32+ символа)
    echo     OPENAI_API_KEY= (если нужен AI анализ)
    echo.
    echo Открываю .env для редактирования...
    notepad .env
    echo.
    echo После заполнения .env запусти setup.bat снова
    pause
    exit /b 0
)

echo [5/5] Запускаем бота...
echo.
echo ✅ Бот запускается в режиме polling (без webhook)
echo    Нажми Ctrl+C для остановки
echo.
python main.py

pause
