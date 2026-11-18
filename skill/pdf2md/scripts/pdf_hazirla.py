"""PDF'i sayfa sayfa hazırlar: sayfa-NNN.png + sayfa-NNN.txt + ozet.json.

Kullanım: python pdf_hazirla.py GIRDI.pdf CIKTI_KLASORU [--dpi 150]
PyMuPDF yoksa pypdfium2 + pdfplumber ile çalışır; ikisi de yoksa kurmayı dener.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

MIN_TEXT_CHARS = 40


def _ensure(pkg: str, module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        pass
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        __import__(module)
        return True
    except Exception:
        return False


def with_pymupdf(pdf: Path, out: Path, dpi: int) -> list[dict]:
    import pymupdf

    pages = []
    with pymupdf.open(pdf) as doc:
        for page in doc:
            n = page.number + 1
            text = page.get_text("text")
            page.get_pixmap(dpi=dpi).save(out / f"sayfa-{n:03d}.png")
            pages.append(_record(out, n, text))
    return pages


def with_pdfium(pdf: Path, out: Path, dpi: int) -> list[dict]:
    import pdfplumber
    import pypdfium2 as pdfium

    pages = []
    doc = pdfium.PdfDocument(str(pdf))
    with pdfplumber.open(pdf) as plumber:
        for i in range(len(doc)):
            n = i + 1
            doc[i].render(scale=dpi / 72).to_pil().save(out / f"sayfa-{n:03d}.png")
            text = plumber.pages[i].extract_text() or ""
            pages.append(_record(out, n, text))
    return pages


def _record(out: Path, n: int, text: str) -> dict:
    chars = len("".join(text.split()))
    kind = "dijital" if chars >= MIN_TEXT_CHARS and "�" not in text else "taranmis"
    if kind == "dijital":
        (out / f"sayfa-{n:03d}.txt").write_text(text, encoding="utf-8")
    return {"sayfa": n, "tur": kind, "karakter": chars}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("cikti", type=Path)
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args()
    args.cikti.mkdir(parents=True, exist_ok=True)

    if _ensure("pymupdf", "pymupdf"):
        pages = with_pymupdf(args.pdf, args.cikti, args.dpi)
    elif _ensure("pypdfium2", "pypdfium2") and _ensure("pdfplumber", "pdfplumber"):
        pages = with_pdfium(args.pdf, args.cikti, args.dpi)
    else:
        print("HATA: PDF okuma kütüphanesi bulunamadı ve kurulamadı.", file=sys.stderr)
        return 1

    summary = {
        "pdf": args.pdf.name,
        "sayfa_sayisi": len(pages),
        "dijital": sum(p["tur"] == "dijital" for p in pages),
        "taranmis": sum(p["tur"] == "taranmis" for p in pages),
        "sayfalar": pages,
    }
    (args.cikti / "ozet.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "sayfalar"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
