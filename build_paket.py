"""Danışanlara gönderilecek zip'leri üretir: dist/pdf2md.zip (uygulama) ve dist/pdf2md-skill.zip (claude.ai).

Kullanım: uv run python build_paket.py
"""

from __future__ import annotations

import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
APP_FILES = ["pyproject.toml", "uv.lock", ".python-version"]
TOP = "pdf2md"


def _add(zf: zipfile.ZipFile, arcname: str, data: bytes, executable: bool = False) -> None:
    info = zipfile.ZipInfo(arcname, date_time=(2026, 10, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = 0o755 if executable else 0o644
    info.external_attr = (stat.S_IFREG | mode) << 16  # Mac'te .command dosyaları çalıştırılabilir kalsın
    zf.writestr(info, data)


def build_app() -> Path:
    out = DIST / "pdf2md.zip"
    with zipfile.ZipFile(out, "w") as zf:
        for script in sorted((ROOT / "paket").iterdir()):
            data = script.read_bytes()
            if script.suffix == ".bat":
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")  # cmd.exe CRLF ister
                _add(zf, f"{TOP}/{script.name}", data)
            elif script.suffix == ".command":
                _add(zf, f"{TOP}/{script.name}", data.replace(b"\r\n", b"\n"), executable=True)
            else:
                _add(zf, f"{TOP}/{script.name}", data)
        for name in APP_FILES:
            _add(zf, f"{TOP}/app/{name}", (ROOT / name).read_bytes())
        for py in sorted((ROOT / "src" / "pdf2md").glob("*")):
            if py.is_file() and py.suffix in {".py", ".typed"}:
                _add(zf, f"{TOP}/app/src/pdf2md/{py.name}", py.read_bytes())
        # Boş klasörler bazı zip araçlarında kaybolur; içlerine kısa bir not koyuyoruz.
        _add(zf, f"{TOP}/PDF-BURAYA/PDF'lerinizi bu klasöre koyun.txt",
             "Dönüştürmek istediğiniz PDF dosyalarını bu klasöre kopyalayın,\r\n"
             "sonra 2-DONUSTUR dosyasına çift tıklayın.\r\n".encode("utf-8"))
        _add(zf, f"{TOP}/SONUCLAR/Markdown dosyaları burada oluşur.txt",
             "Her PDF için bu klasörde ayrı bir klasör ve içinde .md dosyası oluşur.\r\n".encode("utf-8"))
    return out


def build_skill() -> Path:
    out = DIST / "pdf2md-skill.zip"
    skill = ROOT / "skill" / "pdf2md"
    with zipfile.ZipFile(out, "w") as zf:
        for f in sorted(skill.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                _add(zf, f"pdf2md/{f.relative_to(skill).as_posix()}", f.read_bytes())
    return out


if __name__ == "__main__":
    DIST.mkdir(exist_ok=True)
    for path in (build_app(), build_skill() if (ROOT / "skill" / "pdf2md").exists() else None):
        if path:
            print(f"{path.relative_to(ROOT)}  ({path.stat().st_size / 1024:.0f} KB)")
