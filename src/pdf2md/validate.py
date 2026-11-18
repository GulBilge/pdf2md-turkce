"""Çıktıyı orijinal PDF'le karşılaştırır, şüpheli sayfaları işaretler ve KONTROL-ET/ klasörünü hazırlar."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf

from .analyze import PageInfo

MIN_COVERAGE = 0.90  # dijital sayfada PDF metninin en az %90'ı çıktıda olmalı
MIN_OCR_SCORE = 0.60
MIN_LAYOUT_SCORE = 0.50
REVIEW_DPI = 150

WORD = re.compile(r"[^\W\d_]{2,}", re.UNICODE)  # en az 2 harfli kelimeler; sayılar/sayfa no hariç
MD_SYNTAX = re.compile(r"<!--.*?-->|!\[[^\]]*\]\([^)]*\)|\]\([^)]*\)|[*_`#>|\\]")
IMAGE_LINK = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _tr_lower(s: str) -> str:
    return unicodedata.normalize("NFC", s).replace("I", "ı").replace("İ", "i").lower()


def _words(text: str) -> Counter[str]:
    return Counter(WORD.findall(_tr_lower(text)))


HYPHEN_BREAK = re.compile(r"(?<=[^\W\d_])-\s*\n\s*(?=[^\W\d_])")


def text_coverage(pdf_text: str, md_text: str, furniture: str = "") -> float | None:
    # Satır sonunda bölünmüş kelimeler çıktıda birleştirildiği için kaynakta da birleştir.
    src = _words(HYPHEN_BREAK.sub("", pdf_text)) - _words(furniture)
    total = sum(src.values())
    if total < 5:
        return None
    got = _words(MD_SYNTAX.sub(" ", md_text))
    return sum((src & got).values()) / total


def _text_outside(page: pymupdf.Page, boxes: list) -> str:
    """Sayfa metni; görsel olarak kaydedilen alanların (grafik, diyagram) içindeki yazılar hariç."""
    if not boxes:
        return page.get_text("text")
    rects = [pymupdf.Rect(b) for b in boxes]
    kept = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        center = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)
        if not any(center in r for r in rects):
            kept.append(word)
    return " ".join(kept)


def table_problems(md: str) -> list[str]:
    problems = []
    for block in re.findall(r"(?:^\|.*\|\s*$\n?)+", md, re.M):
        rows = [r for r in block.strip().split("\n") if not re.match(r"^\|[\s:|-]+\|$", r)]
        if not rows:
            continue
        # Boş hücre oranına bakmıyoruz: bilimsel tablolarda ve takvimlerde boş hücre normaldir.
        cols = {len(re.split(r"(?<!\\)\|", r.strip().strip("|"))) for r in rows}
        cells = [c.strip() for r in rows for c in re.split(r"(?<!\\)\|", r.strip().strip("|"))]
        if len(cols) > 1:
            problems.append("tablo sütun sayıları tutarsız")
        elif not any(cells):
            problems.append("tablo tamamen boş")
    return problems


def validate(pdf: Path, pages: list[PageInfo], result, cleaned: list[str], out_dir: Path) -> dict:
    page_reports = []
    flagged = []
    weighted, weight = 0.0, 0

    with pymupdf.open(pdf) as doc:
        for i, (info, res, md) in enumerate(zip(pages, result.pages, cleaned)):
            reasons: list[str] = []
            coverage = None

            if not res.ocr:
                pdf_text = _text_outside(doc[info.page_no - 1], res.picture_boxes)
                # Sayfadan taşan paragraflar Docling'de başladığı sayfaya yazılır; komşu sayfalara da bak.
                nearby = "\n".join(cleaned[max(i - 1, 0): i + 2])
                coverage = text_coverage(pdf_text, nearby, res.furniture)
                if coverage is not None:
                    n = sum(_words(pdf_text).values())
                    weighted += coverage * n
                    weight += n
                    if coverage < MIN_COVERAGE:
                        reasons.append(f"metnin %{round((1 - coverage) * 100)}'i çıktıda yok")
            else:
                # Taranmış sayfada karşılaştırılacak metin katmanı yok: OCR hatalarını otomatik
                # ölçemiyoruz, bu yüzden her taranmış sayfa gözle/Claude ile kontrole gönderilir.
                reasons.append("taranmış sayfa: OCR ile okundu, otomatik doğrulanamadı")
                ocr = res.scores.get("ocr_score")
                if ocr is not None and ocr < MIN_OCR_SCORE:
                    reasons.append(f"OCR güveni düşük ({ocr:.2f})")
                if len(md.strip()) < 20:
                    reasons.append("taranmış sayfadan neredeyse hiç metin çıkmadı")

            if res.raw_formulas:
                reasons.append(f"{res.raw_formulas} formül LaTeX'e çevrilmedi")
            layout = res.scores.get("layout_score")
            if layout is not None and layout < MIN_LAYOUT_SCORE:
                reasons.append(f"sayfa düzeni belirsiz ({layout:.2f})")
            reasons += table_problems(md)
            for link in IMAGE_LINK.findall(md):
                if not (out_dir / link).exists():
                    reasons.append(f"görsel bulunamadı: {link}")

            page_reports.append({
                "page": info.page_no,
                "type": "ocr" if res.ocr else "dijital",
                "coverage": None if coverage is None else round(coverage, 3),
                "scores": res.scores,
                "reasons": reasons,
            })
            if reasons:
                flagged.append({"page": info.page_no, "reasons": reasons})

        if flagged:
            _write_review_dir(doc, flagged, out_dir)

    return {
        "quality": round(weighted / weight * 100, 1) if weight else None,
        "has_formulas": result.has_formulas,
        "flagged": flagged,
        "pages": page_reports,
    }


def _write_review_dir(doc: pymupdf.Document, flagged: list[dict], out_dir: Path) -> None:
    from .pipeline import REVIEW_DIR_NAME

    review = out_dir / REVIEW_DIR_NAME
    review.mkdir(exist_ok=True)
    lines = [
        "# Kontrol edilmesi gereken sayfalar",
        "",
        "Bu sayfalar otomatik kontrolde şüpheli bulundu. Düzeltmek için:",
        "",
        "1. claude.ai'de yeni bir sohbet aç (pdf2md skill'i yüklü olmalı).",
        "2. `.md` dosyasını ve bu klasördeki sayfa görsellerini sohbete sürükle.",
        "3. **\"pdf2md: bu sayfaları düzelt\"** yaz.",
        "",
        "| Sayfa | Görsel | Neden |",
        "|---|---|---|",
    ]
    for f in flagged:
        name = f"sayfa-{f['page']:03d}.png"
        doc[f["page"] - 1].get_pixmap(dpi=REVIEW_DPI).save(review / name)
        lines.append(f"| {f['page']} | {name} | {'; '.join(f['reasons'])} |")
    (review / "BENI-OKU.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
