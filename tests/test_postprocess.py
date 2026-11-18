from pdf2md.postprocess import join_letter_spaced, normalize_chars, postprocess_pages, tidy_blocks


def test_normalize_chars_ligatures_invisible_and_turkish():
    assert normalize_chars("ﬁkir") == "fikir"
    assert normalize_chars("Baş­lık​") == "Başlık"
    assert normalize_chars("a b") == "a b"
    assert normalize_chars("İstanbul") == "İstanbul"  # ayrışık İ → tek karakter
    assert normalize_chars("i̇") == "i"


def test_letter_spaced_heading_joined_only_when_in_pdf_text():
    assert join_letter_spaced("## N İ SAN", "NİSAN 04") == "## NİSAN"
    assert join_letter_spaced("## HAZ İ RAN", "HAZİRAN") == "## HAZİRAN"
    assert join_letter_spaced("K A S I M ayı", "KASIM ayı") == "KASIM ayı"
    # PDF metninde birleşik hâli yoksa dokunma
    assert join_letter_spaced("## N İ SAN", "N İ SAN") == "## N İ SAN"


def test_real_short_words_are_not_joined():
    # "oda" sayfada geçse bile "o da" birleşmemeli
    assert join_letter_spaced("o da geldi", "oda o da geldi") == "o da geldi"
    assert join_letter_spaced("A B testi", "AB A B testi") == "A B testi"


def test_edge_page_numbers_removed_but_content_numbers_kept():
    out = postprocess_pages(["12\n\nMetin 12 adet\n\n- 3\n\n7"])[0]
    assert out == "Metin 12 adet\n\n- 3"


def test_repeated_template_headings_are_kept():
    pages = ["## HAFTALIK PLAN\n\nPAZARTESİ"] * 5
    assert all("HAFTALIK PLAN" in p for p in postprocess_pages(pages))


def test_tidy_blocks_bullets_blank_lines_and_tables():
    md = "Giriş\n## Başlık\nmetin\n• madde\n▪ madde2\nönce\n| a | b |\n| - | - |\n| 1 | 2 |\nsonra\n\n\n\nson"
    assert tidy_blocks(md) == (
        "Giriş\n\n## Başlık\n\nmetin\n- madde\n- madde2\nönce\n\n| a | b |\n| - | - |\n| 1 | 2 |\n\nsonra\n\nson"
    )


def test_leftover_pdf_bullet_after_list_marker_removed():
    assert tidy_blocks("- ·XVI. yüzyıldan\n- •İkinci\n- Üçüncü") == "- XVI. yüzyıldan\n- İkinci\n- Üçüncü"


def test_tidy_blocks_drops_empty_headings_and_unescapes_amp():
    assert tidy_blocks("## \n\nA &amp; B") == "A & B"


# --- Numaralı maddeler ---

from pdf2md.postprocess import fix_headings, join_numbered_items, split_inline_numbered  # noqa: E402


def test_inline_numbered_items_split_when_pdf_has_separate_lines():
    md = "1. Veriyi aktarın. 2. Dosyayı sürükleyin."
    pdf = "1. Veriyi aktarın.\n2. Dosyayı sürükleyin.\n"
    assert split_inline_numbered(md, pdf) == "1. Veriyi aktarın.\n2. Dosyayı sürükleyin."


def test_inline_numbers_in_prose_are_not_split():
    # PDF'te "2. ürün" ayrı satırda başlamıyorsa dokunma
    md = "1. sırada biz varız. 2. ürün ise geride."
    assert split_inline_numbered(md, "1. sırada biz varız. 2. ürün ise geride.") == md
    # noktalama yoksa (metin akışı) dokunma
    assert split_inline_numbered("1. ve 2. maddeler", "") == "1. ve 2. maddeler"


def test_blank_line_between_consecutive_numbered_items_removed():
    assert join_numbered_items("1. Bir\n2. İki\n\n3. Üç") == "1. Bir\n2. İki\n3. Üç"
    assert join_numbered_items("1. Bir\n\nParagraf\n\n1. Yeni liste") == "1. Bir\n\nParagraf\n\n1. Yeni liste"


# --- Başlıklar ---

def _lines(*rows):
    return [(t, s, b) for t, s, b in rows]


def test_large_numbered_list_item_becomes_heading_and_levels_follow_font_size():
    pages = ["## Ana Başlık\n\nGövde metni burada uzun uzun yazıyor.\n1. Bölüm bir\n- madde"]
    lines = [_lines(("Ana Başlık", 24.0, 0), ("Gövde metni burada uzun uzun yazıyor.", 12.0, 1),
                    ("1. Bölüm bir", 18.0, 2), ("• madde", 12.0, 3))]
    out = fix_headings(pages, lines)[0]
    assert out == "# Ana Başlık\n\nGövde metni burada uzun uzun yazıyor.\n\n## 1. Bölüm bir\n\n- madde"


def test_body_sized_numbered_list_is_not_turned_into_heading():
    pages = ["## Başlık\n\n1. Birinci madde\n2. İkinci madde"]
    lines = [_lines(("Başlık", 18.0, 0), ("1. Birinci madde", 12.0, 1), ("2. İkinci madde", 12.0, 1))]
    assert fix_headings(pages, lines)[0] == "# Başlık\n\n1. Birinci madde\n2. İkinci madde"


def test_heading_split_over_two_pdf_lines_is_matched():
    pages = ["## Uzun Başlık Devamı\n\nmetin metin metin metin", "## Alt\n\nmetin"]
    lines = [_lines(("Uzun Başlık", 24.0, 0), ("Devamı", 24.0, 0), ("metin metin metin metin", 12.0, 1)),
             _lines(("Alt", 16.0, 0), ("metin", 12.0, 1))]
    assert fix_headings(pages, lines) == ["# Uzun Başlık Devamı\n\nmetin metin metin metin", "## Alt\n\nmetin"]


def test_without_font_info_levels_only_shift_to_start_at_one():
    assert fix_headings(["## A\n\nx\n\n### B\n\ny"], None) == ["# A\n\nx\n\n## B\n\ny"]
