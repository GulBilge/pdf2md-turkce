@echo off
chcp 65001 >nul
title pdf2md - Kurulum
cd /d "%~dp0"

echo.
echo  ==================================================
echo    pdf2md kurulumu  -  Bilge Gül Koç'tan hediye
echo  ==================================================
echo.
echo  Bu işlem bir kez yapılır ve 5-15 dakika sürebilir.
echo  İnternet bağlantınızın açık olduğundan emin olun.
echo.

set "UV=%USERPROFILE%\.local\bin\uv.exe"
rem Python ortamı Türkçe karakter içermeyen sabit bir yola kurulur: PDF ayrıştırıcı (docling-parse)
rem "Masaüstü" gibi ASCII olmayan yollarda kendi dosyalarını açamıyor.
set "UV_PROJECT_ENVIRONMENT=%PUBLIC%\pdf2md\venv"
if not defined PUBLIC set "UV_PROJECT_ENVIRONMENT=C:\pdf2md\venv"

if not exist "%UV%" (
    echo  [1/3] Kurulum aracı indiriliyor...
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul
    if not exist "%UV%" (
        echo.
        echo  HATA: Kurulum aracı indirilemedi. İnternet bağlantınızı kontrol edip tekrar deneyin.
        pause
        exit /b 1
    )
) else (
    echo  [1/3] Kurulum aracı zaten yüklü.
)

echo  [2/3] Python ve gerekli kütüphaneler kuruluyor (yaklaşık 1-2 GB)...
"%UV%" sync --frozen --no-dev --project "%~dp0app" -q
if errorlevel 1 (
    echo.
    echo  HATA: Kütüphaneler kurulamadı. Bu pencerenin ekran görüntüsünü Bilge'ye gönderin.
    pause
    exit /b 1
)

echo  [3/3] Yapay zeka modelleri indiriliyor...
"%UV%" run --frozen --no-dev --project "%~dp0app" pdf2md --hazirla
if errorlevel 1 (
    echo.
    echo  HATA: Modeller indirilemedi. Bu pencerenin ekran görüntüsünü Bilge'ye gönderin.
    pause
    exit /b 1
)

echo.
echo  ==================================================
echo    Kurulum tamamlandı!
echo    PDF'lerinizi PDF-BURAYA klasörüne atın ve
echo    "2-DONUSTUR (Windows)" dosyasına çift tıklayın.
echo  ==================================================
echo.
pause
