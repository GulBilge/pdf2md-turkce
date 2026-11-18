#!/bin/bash
# pdf2md kurulumu (macOS) — Bilge Gül Koç'tan hediye
cd "$(dirname "$0")" || exit 1
HERE="$(pwd)"

echo
echo "  =================================================="
echo "    pdf2md kurulumu  -  Bilge Gül Koç'tan hediye"
echo "  =================================================="
echo
echo "  Bu işlem bir kez yapılır ve 5-15 dakika sürebilir."
echo "  İnternet bağlantınızın açık olduğundan emin olun."
echo

UV="$HOME/.local/bin/uv"
if [ ! -x "$UV" ]; then
    echo "  [1/3] Kurulum aracı indiriliyor..."
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    if [ ! -x "$UV" ]; then
        echo
        echo "  HATA: Kurulum aracı indirilemedi. İnternet bağlantınızı kontrol edip tekrar deneyin."
        read -r -p "  Kapatmak için Enter'a basın..."
        exit 1
    fi
else
    echo "  [1/3] Kurulum aracı zaten yüklü."
fi

# Çift tıklamayla açılabilmesi için dosyaların indirme karantinasını kaldır.
xattr -dr com.apple.quarantine "$HERE" 2>/dev/null
chmod +x "$HERE"/*.command 2>/dev/null

echo "  [2/3] Python ve gerekli kütüphaneler kuruluyor (yaklaşık 1-2 GB)..."
if ! "$UV" sync --frozen --no-dev --project "$HERE/app" -q; then
    echo
    echo "  HATA: Kütüphaneler kurulamadı. Bu pencerenin ekran görüntüsünü Bilge'ye gönderin."
    read -r -p "  Kapatmak için Enter'a basın..."
    exit 1
fi

echo "  [3/3] Yapay zeka modelleri indiriliyor..."
if ! "$UV" run --frozen --no-dev --project "$HERE/app" pdf2md --hazirla; then
    echo
    echo "  HATA: Modeller indirilemedi. Bu pencerenin ekran görüntüsünü Bilge'ye gönderin."
    read -r -p "  Kapatmak için Enter'a basın..."
    exit 1
fi

echo
echo "  =================================================="
echo "    Kurulum tamamlandı!"
echo "    PDF'lerinizi PDF-BURAYA klasörüne atın ve"
echo "    \"2-DONUSTUR (Mac)\" dosyasına çift tıklayın."
echo "  =================================================="
echo
read -r -p "  Kapatmak için Enter'a basın..."
