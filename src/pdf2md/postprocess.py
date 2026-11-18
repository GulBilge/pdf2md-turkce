"""Docling çıktısını temizler: karakterler, listeler, boşluklar, sayfa numaraları."""

from __future__ import annotations

import re
import unicodedata

LIGATURES = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st",
}
# yumuşak tire, sıfır genişlikli boşluk/birleştirici, kelime birleştirici, BOM
INVISIBLE = dict.fromkeys(map(ord, "\u00ad\u200b\u200c\u200d\u2060\ufeff"), None)
# bölünmez boşluk ve tipografik boşluklar
SPACES = dict.fromkeys(map(ord, "\u00a0\u2002\u2003\u2007\u2009\u202f"), " ")
BULLETS = "•●○◦▪▫■□►▸‣⁃∙·–"

BULLET_LINE = re.compile(rf"^(\s*)[{re.escape(BULLETS)}]\s+", re.M)
PAGE_NUMBER_LINE = re.compile(r"^\s*(?:sayfa\s*)?-?\s*\d{1,4}\s*(?:/\s*\d{1,4})?\s*-?\s*$", re.I)
TABLE_LINE = re.compile(r"^\s*\|")
HEADING_LINE = re.compile(r"^#{1,6}\s")
# En az iki kısa (1-3 harfli) harf grubu art arda: "N İ SAN", "K A S I M"
LETTER_SPACED = re.compile(r"(?<!\S)(?:[^\W\d_]{1,3} )+[^\W\d_]{1,3}(?!\S)")


def normalize_chars(text: str) -> str:
    for lig, rep in LIGATURES.items():
        text = text.replace(lig, rep)
    text = text.translate(INVISIBLE).translate(SPACES)
    text = unicodedata.normalize("NFC", text)
    # "i̇" (i + birleşik nokta): İ'nin hatalı küçültülmesinden kalır.
    text = text.replace("i̇", "i")
    return text


def tidy_blocks(text: str) -> str:
    text = BULLET_LINE.sub(r"\1- ", text)
    # Docling'in liste işaretinden sonra kalan PDF madde işareti: "- ·Madde" → "- Madde"
    text = re.sub(rf"^(\s*- )[{re.escape(BULLETS)}]\s*", r"\1", text, flags=re.M)
    text = text.replace("&amp;", "&")
    lines = [ln.rstrip() for ln in text.split("\n")]

    out: list[str] = []
    for i, line in enumerate(lines):
        if re.fullmatch(r"#{1,6}\s*", line):
            continue  # boş başlık
        if HEADING_LINE.match(line) and out and out[-1] == "" and len(out) > 1 and out[-2] == line:
            out.pop()
            continue  # art arda aynı başlık
        is_table = bool(TABLE_LINE.match(line))
        prev = out[-1] if out else ""
        # Tablo ve başlıkların öncesinde boş satır olmalı, yoksa Markdown düzgün görüntülenmez.
        if out and prev != "" and (HEADING_LINE.match(line) or (is_table and not TABLE_LINE.match(prev))):
            out.append("")
        if out and prev != "" and line != "" and TABLE_LINE.match(prev) and not is_table:
            out.append("")
        if HEADING_LINE.match(prev) and line != "":
            out.append("")
        out.append(line)

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def drop_edge_page_numbers(md: str) -> str:
    """Docling'in kaçırdığı, sayfanın ilk/son satırında tek başına duran sayfa numaralarını siler.

    Tekrarlayan satırları silmiyoruz: şablon belgelerde (planlayıcı, form) aynı başlıklar
    her sayfada gerçek içeriktir. Üst/alt bilgiyi Docling zaten ayırıyor.
    """
    lines = md.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.strip()]
    for i in {idx[0], idx[-1]} if idx else ():
        if PAGE_NUMBER_LINE.match(lines[i]):
            lines[i] = ""
    return "\n".join(lines)


def _tr_lower(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def join_letter_spaced(md: str, page_text: str) -> str:
    """Harf aralıklı dizilmiş kelimeleri birleştirir ("N İ SAN" → "NİSAN").

    Yalnızca birleşik hâl sayfanın PDF metin katmanında geçiyorsa birleştirilir; tahmin yapılmaz.
    """
    vocab = {_tr_lower(w) for w in re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", page_text))}
    if not vocab:
        return md

    def repl(m: re.Match) -> str:
        tokens = m.group(0).split(" ")
        out, i = [], 0
        while i < len(tokens):
            # tokens[i]'den başlayan, sözlükte geçen en uzun pencereyi bul.
            # En az 3 parça ve 2 tek harf (tümü BÜYÜK harfse 1 yeterli: "HAZ İ RAN"),
            # böylece "o da" → "oda" gibi gerçek kelime çiftleri birleşmez.
            for j in range(len(tokens), i + 2, -1):
                window = tokens[i:j]
                singles = sum(len(t) == 1 for t in window)
                needed = 1 if all(t.isupper() for t in window) else 2
                if singles >= needed and _tr_lower("".join(window)) in vocab:
                    out.append("".join(window))
                    i = j
                    break
            else:
                out.append(tokens[i])
                i += 1
        return " ".join(out)

    return LETTER_SPACED.sub(repl, md)


NUMBERED_LINE = re.compile(r"^(\d{1,3})\.\s+\S")


def split_inline_numbered(md: str, page_text: str) -> str:
    """Tek satıra yapışmış numaralı maddeleri ayırır: "1. Bir. 2. İki." → iki satır.

    Yalnızca bir sonraki numara noktalama işaretinden sonra geliyorsa ve (PDF metin katmanı varsa)
    o madde PDF'te ayrı bir satırla başlıyorsa bölünür; "1. sırada 2. ürün" gibi metinler bozulmaz.
    """
    pdf_lines = [ln.strip() for ln in page_text.split("\n")]
    out = []
    for line in md.split("\n"):
        m = NUMBERED_LINE.match(line)
        if not m or HEADING_LINE.match(line) or TABLE_LINE.match(line):
            out.append(line)
            continue
        n, rest = int(m.group(1)), line
        while True:
            nxt = re.search(rf"(?<=[.!?:;])\s+{n + 1}\.\s+(?=[^\W\d_])", rest)
            if not nxt:
                break
            follow = rest[nxt.end():].split(" ", 1)[0]
            if page_text.strip() and not any(ln.startswith(f"{n + 1}. {follow}") for ln in pdf_lines):
                break
            out.append(rest[: nxt.start()])
            rest = rest[nxt.start():].strip()
            n += 1
        out.append(rest)
    return "\n".join(out)


def join_numbered_items(md: str) -> str:
    """Ardışık numaralı maddeler arasındaki boş satırı kaldırır (liste tek parça kalsın)."""
    lines = md.split("\n")
    out: list[str] = []
    for line in lines:
        m = NUMBERED_LINE.match(line)
        if m and len(out) >= 2 and out[-1] == "":
            prev = NUMBERED_LINE.match(out[-2])
            if prev and int(prev.group(1)) + 1 == int(m.group(1)):
                out.pop()
        out.append(line)
    return "\n".join(out)


# --- Başlık düzeltme (PDF yazı boyutlarına göre) ---

HEADING_PARTS = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
HEADING_SIZE_RATIO = 1.15  # gövde metninden en az %15 büyük yazılan satırlar başlık adayıdır
MAX_HEADING_CHARS = 150


def _norm(s: str) -> str:
    s = normalize_chars(s)
    for a, b in (("“", '"'), ("”", '"'), ("„", '"'), ("‘", "'"), ("’", "'"), ("—", "-"), ("–", "-")):
        s = s.replace(a, b)
    return " ".join(_tr_lower(s).split())


def _line_groups(lines: list[tuple[str, float, int]]) -> list[tuple[str, float]]:
    """Aynı blokta, aynı boyutta art arda gelen satırları birleştirir (iki satıra bölünmüş başlıklar)."""
    groups: list[list] = []
    for text, size, block in lines:
        if groups and groups[-1][2] == block and abs(groups[-1][1] - size) < 0.3:
            groups[-1][0] += " " + text
        else:
            groups.append([text, size, block])
    return [(_norm(t), s) for t, s, _ in groups]


def _body_size(page_lines: list[list[tuple[str, float, int]]]) -> float | None:
    weights: dict[float, int] = {}
    for lines in page_lines:
        for text, size, _ in lines:
            weights[size] = weights.get(size, 0) + len(text)
    return max(weights, key=weights.get) if weights else None


def fix_headings(pages: list[str], page_lines: list[list[tuple[str, float, int]]] | None) -> list[str]:
    """Başlık seviyelerini PDF'teki yazı boyutlarına göre düzeltir.

    - Docling'in liste maddesi ya da paragraf sandığı büyük puntolu satırlar başlık yapılır
      ("1. Giriş" gibi numaralı bölüm başlıkları).
    - En az iki farklı başlık boyutu varsa seviye boyuta göre verilir: en büyük → #.
    - En küçük seviye # olacak şekilde tüm başlıklar kaydırılır (Docling ana başlığa ## yazıyor).
    Yazı boyutu bilinmeyen başlıklar (taranmış sayfalar) Docling'in seviyesini korur.
    """
    page_lines = page_lines or [[] for _ in pages]
    body = _body_size(page_lines)
    split_pages = [md.split("\n") for md in pages]
    # (sayfa, satır, metin, docling seviyesi veya None, yazı boyutu veya None)
    entries: list[list] = []

    for pi, lines in enumerate(split_pages):
        groups = _line_groups(page_lines[pi]) if pi < len(page_lines) else []
        for li, line in enumerate(lines):
            h = HEADING_PARTS.match(line)
            if h:
                text = _norm(h.group(2))
                size = next((s for g, s in groups if g == text), None) or next(
                    (s for g, s in groups if len(g) >= 3 and (text.startswith(g) or g.startswith(text))), None)
                entries.append([pi, li, h.group(2), len(h.group(1)), size])
            elif body and line.strip() and not TABLE_LINE.match(line) and len(line) <= MAX_HEADING_CHARS:
                plain = line[2:] if line.startswith("- ") else line
                text = _norm(plain)
                size = next((s for g, s in groups if g == text), None)
                if size and size >= body * HEADING_SIZE_RATIO:
                    entries.append([pi, li, plain.strip(), None, size])

    if not entries:
        return pages

    sizes = sorted({round(e[4] * 2) / 2 for e in entries if e[4]}, reverse=True)
    rank = {s: i + 1 for i, s in enumerate(sizes)}
    by_text: dict[str, int] = {}
    if len(sizes) >= 2:
        # Aynı boyuttaki başlıklar arasında Docling'in ayrımını (1. / 1.1) koru.
        group_min: dict[float, int] = {}
        for e in entries:
            if e[4] and e[3]:
                k = round(e[4] * 2) / 2
                group_min[k] = min(group_min.get(k, 9), e[3])
        for e in entries:
            if e[4]:
                k = round(e[4] * 2) / 2
                offset = (e[3] - group_min[k]) if e[3] and k in group_min else 0
                e[3] = min(rank[k] + offset, 6)
                by_text.setdefault(_norm(e[2]), e[3])
    else:
        known = [e[3] for e in entries if e[3]]
        for e in entries:
            if e[3] is None:
                e[3] = min(known) if known else 1
    # Boyutu bilinmeyen başlık başka sayfada aynı metinle geçiyorsa onun seviyesini al.
    for e in entries:
        if not e[4] and _norm(e[2]) in by_text:
            e[3] = by_text[_norm(e[2])]

    shift = min(e[3] for e in entries) - 1
    for pi, li, text, level, _ in entries:
        split_pages[pi][li] = "#" * max(level - shift, 1) + " " + text

    return [tidy_blocks("\n".join(lines)) for lines in split_pages]


def postprocess_pages(
    pages: list[str],
    page_texts: list[str] | None = None,
    page_lines: list[list[tuple[str, float, int]]] | None = None,
) -> list[str]:
    page_texts = page_texts or [""] * len(pages)
    cleaned = [
        join_numbered_items(tidy_blocks(split_inline_numbered(
            drop_edge_page_numbers(join_letter_spaced(normalize_chars(md), text)), text)))
        for md, text in zip(pages, page_texts)
    ]
    return [join_numbered_items(md) for md in fix_headings(cleaned, page_lines)]
