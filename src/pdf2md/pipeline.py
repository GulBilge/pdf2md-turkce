"""Tek bir PDF'i uçtan uca işler: analiz → dönüşüm → son işleme → doğrulama → kayıt."""

from __future__ import annotations

import json
import re
import shutil
import time
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

from .analyze import analyze_pdf, font_lines
from .engine import Engine

IMAGE_DIR_NAME = "images"
REVIEW_DIR_NAME = "KONTROL-ET"


@dataclass
class FileSummary:
    source: str
    output: str
    pages: int
    ocr_pages: int
    images: int
    seconds: float
    quality: float | None  # 0-100; dijital sayfalarda metin kapsama oranı
    flagged_pages: list[int]


def safe_stem(pdf: Path) -> str:
    """Dosya adını Türkçe karakterleri koruyarak güvenli klasör adına çevirir."""
    stem = unicodedata.normalize("NFC", pdf.stem)
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem).strip(" .")
    return stem or "belge"


def page_marker(page_no: int) -> str:
    return f"<!-- sayfa {page_no} -->"


def convert_file(engine: Engine, pdf: Path, out_root: Path, force_ocr: bool = False) -> FileSummary:
    # Döngüsel import olmasın diye burada.
    from .postprocess import postprocess_pages
    from .validate import validate

    started = time.time()
    stem = safe_stem(pdf)
    out_dir = out_root / stem
    if out_dir.exists():
        shutil.rmtree(out_dir)  # yeniden dönüştürmede eski görseller/kontrol dosyaları kalmasın
    out_dir.mkdir(parents=True)
    image_dir = out_dir / IMAGE_DIR_NAME

    pages = analyze_pdf(pdf)
    result = engine.convert(pdf, pages, image_dir, force_ocr=force_ocr)

    with pymupdf.open(pdf) as doc:
        page_texts = [doc[p.page_no - 1].get_text("text") for p in result.pages]
        # Taranmış sayfalarda metin katmanı yok; başlık tespiti yalnızca dijital sayfalarda yazı boyutuna bakar.
        page_lines = [[] if p.ocr else font_lines(doc[p.page_no - 1]) for p in result.pages]
    cleaned = postprocess_pages([p.markdown for p in result.pages], page_texts, page_lines)
    parts = [f"{page_marker(p.page_no)}\n\n{md}".rstrip() for p, md in zip(result.pages, cleaned)]
    markdown = "\n\n".join(parts).strip() + "\n"

    md_path = out_dir / f"{stem}.md"
    md_path.write_text(markdown, encoding="utf-8")

    report = validate(pdf, pages, result, cleaned, out_dir)
    if not result.images and image_dir.exists():
        shutil.rmtree(image_dir)

    summary = FileSummary(
        source=pdf.name,
        output=str(md_path),
        pages=len(pages),
        ocr_pages=sum(1 for p in result.pages if p.ocr),
        images=len(result.images),
        seconds=round(time.time() - started, 1),
        quality=report["quality"],
        flagged_pages=[f["page"] for f in report["flagged"]],
    )
    report["summary"] = asdict(summary)
    (out_dir / "rapor.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
