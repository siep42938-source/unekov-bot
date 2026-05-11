@echo off
chcp 65001 >nul
echo Загружаем бота на GitHub...

git init
git add .
git commit -m "unekov bot"
git branch -M main
git remote add origin https://github.com/siep42938-source/unekov-bot.git
git push -u origin main

echo.
echo Готово! Теперь иди на Railway.
pause
