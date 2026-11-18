"""Docling ile dönüşüm. OCR yalnızca ihtiyaç duyan sayfalarda çalışır (CPU'da ~10 kat fark)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ContentLayer, DocItemLabel, ImageRefMode, PictureItem, TextItem

from .analyze import page_runs, PageInfo

log = logging.getLogger(__name__)

# Bu boyuttan küçük görseller (ikon, süs, çizgi) atlanır.
MIN_IMAGE_PX = 80
IMAGE_SCALE = 2.0


@dataclass
class PageResult:
    page_no: int
    markdown: str
    ocr: bool
    scores: dict = field(default_factory=dict)  # docling güven skorları (0-1)
    furniture: str = ""  # bilerek çıkarılan sayfa üst/alt bilgisi (doğrulamada hariç tutulur)
    raw_formulas: int = 0  # LaTeX'e çevrilemeyip ham metin olarak bırakılan formül sayısı
    picture_boxes: list[tuple[float, float, float, float]] = field(default_factory=list)  # (x0, y0, x1, y1), üst-sol


@dataclass
class EngineResult:
    pages: list[PageResult]
    images: list[str]
    has_formulas: bool


class Engine:
    """Dönüştürücüleri bir kez kurup tüm PDF'lerde yeniden kullanır (model yüklemesi pahalı)."""

    def __init__(self, ocr_langs: tuple[str, ...] = ("tr", "en"), decode_formulas: bool = False):
        self.ocr_langs = list(ocr_langs)
        # Formül modeli CPU'da çok yavaş (15 sayfalık makalede 20+ dk). Varsayılan olarak kapalı:
        # formüller PDF metin katmanından alınır ve sayfa Claude ile düzeltilmek üzere işaretlenir.
        self.decode_formulas = decode_formulas
        self._converters: dict[tuple[bool, bool], DocumentConverter] = {}

    def _converter(self, ocr: bool, formulas: bool) -> DocumentConverter:
        key = (ocr, formulas)
        if key not in self._converters:
            opts = PdfPipelineOptions(
                accelerator_options=AcceleratorOptions(num_threads=os.cpu_count() or 4, device="cpu"),
                do_ocr=ocr,
                do_table_structure=True,
                do_formula_enrichment=formulas,
                generate_picture_images=True,
                images_scale=IMAGE_SCALE,
            )
            if ocr:
                opts.ocr_options = EasyOcrOptions(lang=self.ocr_langs, force_full_page_ocr=True)
            opts.heading_hierarchy_options.enabled = True
            self._converters[key] = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
            )
        return self._converters[key]

    def warm_up(self) -> None:
        """Modelleri önceden indirir/yükler (kurulum sırasında çağrılır)."""
        for ocr in (False, True):
            self._converter(ocr, False).initialize_pipeline(InputFormat.PDF)

    def convert(self, pdf: Path, pages: list[PageInfo], image_dir: Path, force_ocr: bool = False) -> EngineResult:
        if force_ocr:
            for p in pages:
                p.needs_ocr = True
        results: list[PageResult] = []
        images: list[str] = []
        has_formulas = False

        for first, last, ocr in page_runs(pages):
            conv = self._converter(ocr, formulas=False)
            res = conv.convert(pdf, page_range=(first, last))
            doc = res.document

            if any(t.label == DocItemLabel.FORMULA for t in doc.texts):
                has_formulas = True
                if self.decode_formulas:
                    # Formül modeli ağır; yalnızca formül içeren bölümlerde çalıştırılır.
                    log.info("Formül bulundu (sayfa %d-%d), formül modeliyle yeniden işleniyor", first, last)
                    res = self._converter(ocr, formulas=True).convert(pdf, page_range=(first, last))
                    doc = res.document

            images += self._save_images(doc, image_dir)
            self._unspan_table_cells(doc)

            for page_no in range(first, last + 1):
                md = doc.export_to_markdown(
                    page_no=page_no,
                    image_mode=ImageRefMode.REFERENCED,
                    image_placeholder="",
                    escape_underscores=False,
                    compact_tables=True,
                )
                md, raw_formulas = self._fill_raw_formulas(doc, page_no, md)
                scores = {}
                conf = res.confidence.pages.get(page_no) if res.confidence else None
                if conf is not None:
                    for k in ("parse_score", "layout_score", "table_score", "ocr_score"):
                        v = getattr(conf, k, None)
                        if v is not None and v == v:  # NaN'ı ele
                            scores[k] = round(float(v), 3)
                furniture = " ".join(
                    item.text
                    for item, _ in doc.iterate_items(page_no=page_no, included_content_layers={ContentLayer.FURNITURE})
                    if isinstance(item, TextItem)
                )
                height = doc.pages[page_no].size.height
                picture_boxes = [
                    tuple(prov.bbox.to_top_left_origin(height).as_tuple())
                    for item, _ in doc.iterate_items(page_no=page_no)
                    if isinstance(item, PictureItem) and item.image is not None
                    for prov in item.prov
                    if prov.page_no == page_no
                ]
                results.append(PageResult(page_no=page_no, markdown=md, ocr=ocr, scores=scores, furniture=furniture,
                                          raw_formulas=raw_formulas, picture_boxes=picture_boxes))

        return EngineResult(pages=results, images=images, has_formulas=has_formulas)

    @staticmethod
    def _unspan_table_cells(doc) -> None:
        """Birleşik hücrenin değeri yalnızca ilk hücreye yazılsın (Docling her hücreye tekrar yazıyor)."""
        for table in doc.tables:
            for cell in table.data.table_cells:
                if cell.row_span > 1 or cell.col_span > 1:
                    cell.row_span = cell.col_span = 1
                    cell.end_row_offset_idx = cell.start_row_offset_idx + 1
                    cell.end_col_offset_idx = cell.start_col_offset_idx + 1

    @staticmethod
    def _fill_raw_formulas(doc, page_no: int, md: str) -> tuple[str, int]:
        """Çözülemeyen formül yer tutucularını PDF'teki ham formül metniyle doldurur."""
        placeholder = "<!-- formula-not-decoded -->"
        if placeholder not in md:
            return md, 0
        originals = [
            item.orig.strip()
            for item, _ in doc.iterate_items(page_no=page_no)
            if isinstance(item, TextItem) and item.label == DocItemLabel.FORMULA and not item.text
        ]
        count = 0
        for orig in originals:
            if placeholder not in md:
                break
            md = md.replace(placeholder, f"`{orig}`" if orig else "[formül okunamadı]", 1)
            count += 1
        return md.replace(placeholder, "[formül okunamadı]"), count

    @staticmethod
    def _save_images(doc, image_dir: Path) -> list[str]:
        saved: list[str] = []
        counters: dict[int, int] = {}
        for item, _level in doc.iterate_items():
            if not isinstance(item, PictureItem):
                continue
            img = item.get_image(doc)
            if img is None or min(img.size) < MIN_IMAGE_PX * IMAGE_SCALE / 2:
                item.image = None  # küçük/boş görsel: md'ye hiç yazılmaz
                continue
            page_no = item.prov[0].page_no if item.prov else 0
            counters[page_no] = counters.get(page_no, 0) + 1
            name = f"sayfa-{page_no:03d}-gorsel-{counters[page_no]}.png"
            image_dir.mkdir(parents=True, exist_ok=True)
            img.save(image_dir / name)
            item.image.uri = f"{image_dir.name}/{name}"
            saved.append(name)
        return saved
