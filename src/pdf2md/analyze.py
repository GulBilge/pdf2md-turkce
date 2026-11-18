"""PDF'i dönüştürmeden önce sayfa sayfa inceler: hangi sayfa dijital, hangisi taranmış?"""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf

# Bir sayfanın "dijital" sayılması için gereken en az anlamlı karakter sayısı.
MIN_TEXT_CHARS = 40
# Sayfanın bu oranından fazlasını kaplayan görsel + az metin = taranmış sayfa.
SCANNED_IMAGE_COVERAGE = 0.5
# Metin katmanında bu oranın üstünde bozuk karakter varsa katman güvenilmezdir.
MAX_GARBAGE_RATIO = 0.15


@dataclass
class PageInfo:
    page_no: int  # 1'den başlar
    text_chars: int
    image_coverage: float
    garbage_ratio: float
    needs_ocr: bool
    reason: str


def _garbage_ratio(text: str) -> float:
    """Yazı tipi eşlemesi bozuk PDF'lerde çıkan anlamsız karakterlerin oranı."""
    if not text:
        return 0.0
    bad = sum(
        1
        for ch in text
        if ch == "�" or (0xE000 <= ord(ch) <= 0xF8FF) or (ord(ch) < 32 and ch not in "\n\r\t")
    )
    bad += text.count("(cid:") * 5
    return bad / len(text)


def _image_coverage(page: pymupdf.Page) -> float:
    area = abs(page.rect)
    if not area:
        return 0.0
    covered = 0.0
    for info in page.get_image_info():
        bbox = pymupdf.Rect(info["bbox"]) & page.rect
        covered += abs(bbox)
    return min(covered / area, 1.0)


def analyze_pdf(path) -> list[PageInfo]:
    pages: list[PageInfo] = []
    with pymupdf.open(path) as doc:
        for page in doc:
            text = page.get_text("text")
            chars = len("".join(text.split()))
            coverage = _image_coverage(page)
            garbage = _garbage_ratio(text)

            if garbage > MAX_GARBAGE_RATIO:
                needs_ocr, reason = True, "metin katmanı bozuk"
            elif chars < MIN_TEXT_CHARS and coverage > SCANNED_IMAGE_COVERAGE:
                needs_ocr, reason = True, "taranmış sayfa"
            else:
                needs_ocr, reason = False, "dijital"

            pages.append(
                PageInfo(
                    page_no=page.number + 1,
                    text_chars=chars,
                    image_coverage=round(coverage, 3),
                    garbage_ratio=round(garbage, 3),
                    needs_ocr=needs_ocr,
                    reason=reason,
                )
            )
    return pages


def page_runs(pages: list[PageInfo]) -> list[tuple[int, int, bool]]:
    """Ardışık, aynı türdeki sayfaları gruplar: [(ilk, son, ocr_gerekli), ...]."""
    runs: list[tuple[int, int, bool]] = []
    for p in pages:
        if runs and runs[-1][2] == p.needs_ocr and runs[-1][1] == p.page_no - 1:
            first, _, ocr = runs[-1]
            runs[-1] = (first, p.page_no, ocr)
        else:
            runs.append((p.page_no, p.page_no, p.needs_ocr))
    return runs


def font_lines(page: pymupdf.Page) -> list[tuple[str, float, int]]:
    """Sayfanın metin satırları: (metin, yazı boyutu, blok no). Başlık tespitinde kullanılır."""
    lines = []
    for b_no, block in enumerate(page.get_text("dict")["blocks"]):
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = "".join(s["text"] for s in line["spans"]).strip()
            size = max(s["size"] for s in spans)
            lines.append((text, round(size, 1), b_no))
    return lines
