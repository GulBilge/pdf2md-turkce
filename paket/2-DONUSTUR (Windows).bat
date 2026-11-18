@echo off
chcp 65001 >nul
title pdf2md - PDF'ten Markdown'a
cd /d "%~dp0"

set "UV=%USERPROFILE%\.local\bin\uv.exe"
rem Kurulumdaki ile aynı olmalı (bkz. 1-KURULUM).
set "UV_PROJECT_ENVIRONMENT=%PUBLIC%\pdf2md\venv"
if not defined PUBLIC set "UV_PROJECT_ENVIRONMENT=C:\pdf2md\venv"

if not exist "%UV%" (
    echo.
    echo  Önce "1-KURULUM (Windows)" dosyasına çift tıklayarak kurulumu yapın.
    echo.
    pause
    exit /b 1
)

echo.
echo  pdf2md  -  Bilge Gül Koç'tan hediye
echo  ---------------------------------------------
echo.
"%UV%" run --frozen --no-dev --project "%~dp0app" pdf2md "%~dp0PDF-BURAYA" -o "%~dp0SONUCLAR"

start "" "%~dp0SONUCLAR"
echo.
pause
