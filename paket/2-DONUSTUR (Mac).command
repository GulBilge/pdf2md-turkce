#!/bin/bash
# pdf2md — PDF'ten Markdown'a (macOS)
cd "$(dirname "$0")" || exit 1
HERE="$(pwd)"

UV="$HOME/.local/bin/uv"
if [ ! -x "$UV" ]; then
    echo
    echo "  Önce \"1-KURULUM (Mac)\" dosyasına çift tıklayarak kurulumu yapın."
    echo
    read -r -p "  Kapatmak için Enter'a basın..."
    exit 1
fi

echo
echo "  pdf2md  -  Bilge Gül Koç'tan hediye"
echo "  ---------------------------------------------"
echo
"$UV" run --frozen --no-dev --project "$HERE/app" pdf2md "$HERE/PDF-BURAYA" -o "$HERE/SONUCLAR"

open "$HERE/SONUCLAR"
echo
read -r -p "  Kapatmak için Enter'a basın..."
