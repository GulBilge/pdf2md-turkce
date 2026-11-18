"""Gerçek Docling dönüşümü (modeller gerekir, ~1 dk). Atlamak için: pytest -m "not yavas"."""

from pathlib import Path

import pymupdf
import pytest

from pdf2md.analyze import analyze_pdf

FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]
FONT = next((f for f in FONT_CANDIDATES if f.exists()), FONT_CANDIDATES[0])
TEXT = [
    ("Haftalık Rapor", 20),
    ("Bu belge Türkçe karakterleri (ç, ğ, ı, İ, ö, ş, ü) doğru aktarmak için hazırlandı.", 11),
    ("İkinci paragraf: Işık, ağaç, şemsiye ve göğüs kelimeleri burada geçiyor.", 11),
]


def _make_pdf(path: Path, scanned: bool) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for text, size in TEXT:
        page.insert_text((72, y), text, fontsize=size, fontfile=str(FONT), fontname="arial")
        y += size * 2.2
    if scanned:
        pix = page.get_pixmap(dpi=200)
        doc = pymupdf.open()
        doc.new_page().insert_image(pymupdf.Rect(0, 0, 595, 842), pixmap=pix)
    doc.save(path)


pytestmark = [pytest.mark.yavas, pytest.mark.skipif(not FONT.exists(), reason="Türkçe karakterli bir yazı tipi (Arial/DejaVu) gerekli")]


@pytest.fixture(scope="module")
def engine():
    from pdf2md.engine import Engine

    return Engine()


@pytest.mark.parametrize("scanned", [False, True], ids=["dijital", "taranmis"])
def test_convert_file(tmp_path, engine, scanned):
    from pdf2md.pipeline import convert_file

    pdf = tmp_path / "örnek belge.pdf"
    _make_pdf(pdf, scanned)
    assert analyze_pdf(pdf)[0].needs_ocr is scanned

    summary = convert_file(engine, pdf, tmp_path / "out")
    md = Path(summary.output).read_text(encoding="utf-8")

    assert md.startswith("<!-- sayfa 1 -->")
    assert "Haftalık Rapor" in md
    for word in ["Türkçe", "İkinci", "Işık", "ağaç", "şemsiye", "göğüs"]:
        assert word in md, word
    assert (tmp_path / "out" / "örnek belge" / "rapor.json").exists()
    if not scanned:
        assert summary.quality == 100.0
        assert summary.flagged_pages == []
    else:
        assert summary.flagged_pages == [1]  # taranmış sayfa her zaman kontrole gönderilir
