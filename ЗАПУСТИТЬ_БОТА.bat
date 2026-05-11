@echo off
chcp 65001 >nul
title Unekov.help Bot

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   UNEKOV.HELP — Автозапуск           ║
echo  ╚══════════════════════════════════════╝
echo.

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python не найден!
    echo  [!] Скачай с https://www.python.org/downloads/
    echo  [!] При установке поставь галочку "Add to PATH"
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

:: Проверяем Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Docker не найден — запускаем без него
    echo  [!] PostgreSQL должен быть установлен локально
    goto :no_docker
)

echo  [1/5] Запускаем PostgreSQL и Redis через Docker...
docker-compose -f docker-compose.dev.yml up -d >nul 2>&1
echo  [OK] База данных запущена
timeout /t 3 /nobreak >nul

:no_docker

echo  [2/5] Создаём виртуальное окружение...
if not exist "venv" (
    python -m venv venv
)

echo  [3/5] Активируем...
call venv\Scripts\activate.bat

echo  [4/5] Устанавливаем зависимости...
pip install -r requirements.txt -q --no-warn-script-location

echo  [5/5] Запускаем бота...
echo.
echo  ✅ Бот запускается...
echo  ✅ Открой t.me/unekov_bot и напиши /start
echo  ✅ Для остановки нажми Ctrl+C
echo.

python main.py

pause
