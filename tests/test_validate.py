from pdf2md.analyze import PageInfo, page_runs
from pdf2md.validate import table_problems, text_coverage


def test_coverage_full_when_all_words_present():
    assert text_coverage("Birinci adım ikinci adım üçüncü adım", "# Birinci adım\n\n- ikinci adım\n- üçüncü adım") == 1.0


def test_coverage_detects_missing_text():
    cov = text_coverage("bir iki üç dört beş altı yedi sekiz", "bir iki üç dört")
    assert cov == 0.5


def test_coverage_turkish_case_insensitive():
    assert text_coverage("İSTANBUL ISPARTA IĞDIR ÇORUM ŞIRNAK", "istanbul ısparta ığdır çorum şırnak") == 1.0


def test_coverage_ignores_furniture_and_hyphen_breaks():
    pdf = "KURUM ADI RAPORU\nMudanya Antlaşması'nın onaylan-\nması gerekiyordu burada"
    md = "Mudanya Antlaşması'nın onaylanması gerekiyordu burada"
    assert text_coverage(pdf, md, furniture="KURUM ADI RAPORU") == 1.0


def test_coverage_none_for_nearly_empty_page():
    assert text_coverage("04", "") is None


def test_table_problems():
    good = "| a | b |\n| - | - |\n| 1 |  |\n"
    assert table_problems(good) == []
    bad = "| a | b |\n| - | - |\n| 1 | 2 | 3 |\n"
    assert table_problems(bad) == ["tablo sütun sayıları tutarsız"]
    escaped = "| a | b |\n| - | - |\n| x \\| y | 2 |\n"
    assert table_problems(escaped) == []


def _page(n, ocr):
    return PageInfo(page_no=n, text_chars=0, image_coverage=0, garbage_ratio=0, needs_ocr=ocr, reason="")


def test_page_runs_groups_consecutive_pages_by_type():
    pages = [_page(1, False), _page(2, False), _page(3, True), _page(4, True), _page(5, False)]
    assert page_runs(pages) == [(1, 2, False), (3, 4, True), (5, 5, False)]
