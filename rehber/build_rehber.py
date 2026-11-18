"""rehber.html → paket/NASIL-KULLANILIR.pdf (Türkçe karakterler için gömülü font ile).

Kullanım: uv run python rehber/build_rehber.py
"""

from pathlib import Path

import pymupdf

HERE = Path(__file__).parent
OUT = HERE.parent / "paket" / "NASIL-KULLANILIR.pdf"
# Türkçe karakterli yazı tipi: Windows'ta Arial, yoksa (Linux) DejaVu.
WIN_FONTS = Path("C:/Windows/Fonts")
DEJAVU = Path("/usr/share/fonts/truetype/dejavu")
FONT_DIR, FONTS = (
    (WIN_FONTS, ("arial.ttf", "arialbd.ttf", "ariali.ttf", "consola.ttf"))
    if (WIN_FONTS / "arial.ttf").exists()
    else (DEJAVU, ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "DejaVuSansMono.ttf"))
)
MEDIABOX = pymupdf.paper_rect("a4")
WHERE = MEDIABOX + (48, 48, -48, -56)


def main() -> None:
    html = (HERE / "rehber.html").read_text(encoding="utf-8")
    font_css = """
    @font-face {{ font-family: sans-serif; src: url({0}); }}
    @font-face {{ font-family: sans-serif; src: url({1}); font-weight: bold; }}
    @font-face {{ font-family: sans-serif; src: url({2}); font-style: italic; }}
    @font-face {{ font-family: monospace; src: url({3}); }}
    """.format(*FONTS)
    archive = pymupdf.Archive(str(FONT_DIR))
    story = pymupdf.Story(html=html, user_css=font_css, archive=archive)

    writer = pymupdf.DocumentWriter(str(OUT))
    more = True
    while more:
        device = writer.begin_page(MEDIABOX)
        more, _ = story.place(WHERE)
        story.draw(device)
        writer.end_page()
    writer.close()

    # Sayfa numarası ekle.
    doc = pymupdf.open(OUT)
    for page in doc:
        page.insert_text((MEDIABOX.width / 2 - 20, MEDIABOX.height - 28), f"{page.number + 1} / {doc.page_count}",
                         fontsize=8, color=(0.45, 0.45, 0.5))
    doc.saveIncr()
    print(f"{OUT} ({doc.page_count} sayfa)")


if __name__ == "__main__":
    main()
