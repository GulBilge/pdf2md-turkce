"""Komut satırı: pdf2md GIRDI [-o CIKTI]. Girdi tek PDF veya PDF klasörü olabilir."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import warnings
from pathlib import Path

from . import __version__


def _quiet() -> None:
    # Kütüphanelerin teknik uyarıları teknik olmayan kullanıcıyı korkutmasın.
    warnings.filterwarnings("ignore")
    logging.basicConfig(level=logging.ERROR, format="%(message)s")
    for name in ("docling", "easyocr", "transformers", "torch", "PIL", "rapidocr"):
        logging.getLogger(name).setLevel(logging.ERROR)
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("HF_HUB_VERBOSITY", "error")
    try:
        from transformers.utils import logging as hf_logging

        hf_logging.disable_progress_bar()
    except ImportError:
        pass


def _fmt_time(sec: float) -> str:
    return f"{sec:.0f} sn" if sec < 90 else f"{sec / 60:.1f} dk"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # Windows konsolu (cp1254) için
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(prog="pdf2md", description="PDF dosyalarını temiz Markdown'a çevirir.")
    parser.add_argument("girdi", nargs="?", type=Path, help="PDF dosyası veya PDF'lerin olduğu klasör")
    parser.add_argument("-o", "--cikti", type=Path, help="Sonuç klasörü (varsayılan: girdinin yanında 'SONUCLAR')")
    parser.add_argument("--ocr", action="store_true", help="Tüm sayfalarda OCR'ı zorla (bozuk metinli PDF'ler için)")
    parser.add_argument("--formul", action="store_true",
                        help="Formülleri yerel modelle LaTeX'e çevir (çok yavaş; varsayılan: Claude ile düzeltme)")
    parser.add_argument("--hepsini-yeniden", action="store_true", help="Daha önce dönüştürülmüş PDF'leri de yeniden işle")
    parser.add_argument("--hazirla", action="store_true", help="Modelleri indir ve hazırla (kurulumda bir kez)")
    parser.add_argument("--version", action="version", version=f"pdf2md {__version__}")
    args = parser.parse_args(argv)

    _quiet()
    from .engine import Engine
    from .pipeline import convert_file, safe_stem

    engine = Engine(decode_formulas=args.formul)
    if args.hazirla:
        print("Modeller indiriliyor ve hazırlanıyor (bir kez, birkaç dakika sürebilir)...", flush=True)
        engine.warm_up()
        print("Hazır ✓")
        return 0

    if args.girdi is None:
        parser.error("bir PDF dosyası veya klasör belirtin")
    src: Path = args.girdi
    if not src.exists():
        print(f"Bulunamadı: {src}")
        return 1
    pdfs = sorted(src.glob("*.pdf")) + sorted(src.glob("*.PDF")) if src.is_dir() else [src]
    pdfs = sorted(set(pdfs))
    out_root = args.cikti or (src if src.is_dir() else src.parent).parent / "SONUCLAR"
    out_root.mkdir(parents=True, exist_ok=True)

    if not pdfs:
        print(f"'{src}' içinde PDF bulunamadı.")
        return 0

    todo = []
    for pdf in pdfs:
        md = out_root / safe_stem(pdf) / f"{safe_stem(pdf)}.md"
        if not args.hepsini_yeniden and md.exists() and md.stat().st_mtime > pdf.stat().st_mtime:
            continue
        todo.append(pdf)
    skipped = len(pdfs) - len(todo)
    if skipped:
        print(f"{skipped} PDF daha önce dönüştürülmüş, atlanıyor.")
    if not todo:
        print("Dönüştürülecek yeni PDF yok.")
        return 0

    print(f"{len(todo)} PDF dönüştürülecek → {out_root}\n", flush=True)
    started = time.time()
    ok, failed, need_review = 0, [], []
    for i, pdf in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {pdf.name} ...", end=" ", flush=True)
        try:
            s = convert_file(engine, pdf, out_root, force_ocr=args.ocr)
        except Exception as exc:  # bir PDF bozuksa diğerleri yine işlensin
            print(f"HATA: {exc}")
            failed.append(pdf.name)
            continue
        ok += 1
        parts = [f"{s.pages} sayfa", _fmt_time(s.seconds)]
        if s.quality is not None:
            parts.append(f"kalite %{s.quality:.0f}" + (" (dijital sayfalar)" if s.ocr_pages else ""))
        if s.ocr_pages:
            parts.append(f"{s.ocr_pages} sayfa OCR")
        if s.images:
            parts.append(f"{s.images} görsel")
        mark = "✓"
        if s.flagged_pages:
            mark = "⚠"
            parts.append(f"kontrol et: sayfa {', '.join(map(str, s.flagged_pages[:8]))}"
                         + (" ..." if len(s.flagged_pages) > 8 else ""))
            need_review.append(pdf.name)
        print(f"{mark} ({', '.join(parts)})", flush=True)

    print(f"\nBitti: {ok} başarılı, {len(failed)} hatalı — toplam {_fmt_time(time.time() - started)}")
    if need_review:
        print(f"⚠ {len(need_review)} dosyada kontrol edilmesi gereken sayfa var: "
              "ilgili klasördeki KONTROL-ET/BENI-OKU.md dosyasına bakın.")
    if failed:
        print("Hatalı dosyalar: " + ", ".join(failed))
    return 1 if failed and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
