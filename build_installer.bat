@echo off
setlocal

:: Перейти в директорию, где лежит installer.py и installer.spec
cd /d "%~dp0installer"

:: Установка PyInstaller (если ещё не установлен)
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Устанавливаю PyInstaller...
    pip install --quiet pyinstaller
)

:: Сборка exe через PyInstaller
echo Собираю установщик...
pyinstaller --noconfirm installer.spec

:: Проверка на ошибку
if errorlevel 1 (
