# pdf2md

PDF dosyalarını Claude'un verimli okuyabileceği temiz Markdown'a çeviren yerel araç + claude.ai skill'i.
**Bilge Gül Koç**'un danışanlarına hediyesi.

- **Uygulama** (`src/pdf2md`): Docling ile yerelde, ücretsiz, toplu dönüşüm. Teknik olmayan kullanıcılar için çift tıklamalı kurulum/çalıştırma (`paket/`).
- **Skill** (`skill/pdf2md`): claude.ai'de şüpheli sayfaları görselden düzeltir, büyük `.md`'leri az token ile okur, uygulama yoksa küçük PDF'leri doğrudan çevirir.

## İndir ve kullan

1. **[Son sürüm sayfasından](https://github.com/GulBilge/pdf2md-turkce/releases/latest)** iki dosyayı indirin:
   - **[pdf2md.zip](https://github.com/GulBilge/pdf2md-turkce/releases/latest/download/pdf2md.zip)** → bilgisayarınıza kurulan uygulama (içinde adım adım `NASIL-KULLANILIR.pdf` rehberi var)
   - **[pdf2md-skill.zip](https://github.com/GulBilge/pdf2md-turkce/releases/latest/download/pdf2md-skill.zip)** → claude.ai'ye yüklenen skill
2. `pdf2md.zip` dosyasını açın ve `NASIL-KULLANILIR.pdf` rehberindeki adımları izleyin.
3. claude.ai'de **Customize → Skills** bölümünden `pdf2md-skill.zip` dosyasını yükleyin (Ayarlar → Yetenekler'de kod çalıştırma açık olmalı).

Gereksinimler: Windows 10/11 veya Apple işlemcili Mac (M1–M4), en az 8 GB RAM, ~4 GB boş disk, kurulum sırasında internet.

Lisans: [MIT](LICENSE)

## Danışana gönderilecek paket

```bash
uv run python rehber/build_rehber.py   # paket/NASIL-KULLANILIR.pdf (rehber.html'den)
uv run python build_paket.py           # dist/pdf2md.zip + dist/pdf2md-skill.zip
```

`dist/pdf2md.zip` → bilgisayara, `dist/pdf2md-skill.zip` → claude.ai → Ayarlar → Skills.

## Geliştirme

```bash
uv sync
uv run pdf2md KLASOR_VEYA_PDF -o CIKTI     # --ocr, --formul, --hepsini-yeniden
uv run pytest -m "not yavas"               # hızlı birim testleri
uv run pytest                              # + gerçek Docling dönüşümü (~1 dk)
```

## Akış

```
analyze.py     PyMuPDF ile sayfa sayfa: dijital mi, taranmış mı, metin katmanı bozuk mu?
engine.py      Docling; ardışık aynı tür sayfalar tek seferde. OCR (EasyOCR tr+en) yalnızca taranmış sayfalarda.
postprocess.py Karakter normalizasyonu, harf aralıklı başlıklar, sayfa numaraları, boşluk/liste/tablo düzeni.
validate.py    PDF metin katmanıyla kelime kapsama oranı; şüpheli sayfalar → KONTROL-ET/ (PNG + BENI-OKU.md).
pipeline.py    Tek PDF uçtan uca; <!-- sayfa N --> işaretli .md + images/ + rapor.json.
cli.py         Türkçe ilerleme çıktısı, daha önce dönüştürülenleri atlama.
```

## Tasarım kararları (ve nedenleri)

| Karar | Neden |
|---|---|
| Motor: Docling, CPU | Hedef makinelerde GPU yok. Marker CPU'da çok yavaş; `pymupdf4llm` iki sütunlu sayfalarda metni karıştırıyor. |
| OCR yalnızca taranmış sayfalarda | Tüm sayfalarda OCR 11 sayfalık belgede 28 sn → 305 sn. Türkçe OCR doğruluğu testte %99,8. |
| Formül modeli varsayılan kapalı (`--formul` ile açılır) | CodeFormulaV2 CPU'da 15 sayfalık makalede 20+ dk. Formüller ham metinle bırakılır, sayfa işaretlenir, skill görselden LaTeX'e çevirir. |
| Tekrarlayan satırlar silinmez | Şablon belgelerde (planlayıcı) her sayfadaki başlıklar gerçek içerik; üst/alt bilgiyi Docling zaten ayırıyor. |
| Satır sonu tire birleştirme kuralı yok | Docling zaten birleştiriyor; ek kural "son- fikir" gibi yanlış birleştirmeler yapıyordu. |
| Harf aralıklı kelimeler yalnızca PDF metninde geçiyorsa birleşir | "N İ SAN" → "NİSAN" ama "o da" → "oda" olmaz. |
| Birleşik tablo hücresi yalnızca ilk hücrede | Docling her hücreye tekrar yazıyor; token israfı. |
| Doğrulamada komşu sayfalara da bakılır | Sayfadan taşan paragraf Docling'de başladığı sayfaya yazılıyor. |
| Windows'ta Python ortamı `%PUBLIC%\pdf2md\venv` | docling-parse (C++) "Masaüstü" gibi ASCII olmayan yollarda kendi kaynak dosyalarını açamıyor. |
| Başlık seviyeleri PDF yazı boyutundan | Docling numaralı bölüm başlıklarını ("1. Giriş") liste maddesi sanıyor ve ana başlığa `##` yazıyor. Gövdeden %15+ büyük satırlar başlık olur; en büyük boyut `#`. |
| Yapışık numaralı maddeler yalnızca PDF'te ayrı satırdaysa bölünür | "1. Bir. 2. İki." → iki madde, ama "1. sırada 2. ürün" bozulmaz. |
| Taranmış sayfalar her zaman KONTROL-ET'e gider | Karşılaştırılacak metin katmanı yok; OCR hataları (kayan kelime, noktalama) otomatik ölçülemiyor. Kalite yüzdesi yalnızca dijital sayfaları ölçer. |
| Sayfa işaretleri `<!-- sayfa N -->` | Görüntülenmez, az token; Claude kaynak sayfa gösterebilir, skill sayfa bazlı düzeltme yapabilir. |

## Bilinen sınırlar

- Mac script'leri (`*.command`) henüz gerçek bir Mac'te denenmedi. Intel Mac'lerde PyTorch wheel'i olmadığı için kurulum başarısız olabilir (Apple Silicon hedefleniyor).
- Taranmış sayfalar CPU'da sayfa başı ~30-40 sn.
- claude.ai menü adları (Customize → Skills) Claude güncellemeleriyle değişebilir; rehber buna göre güncellenmeli.
