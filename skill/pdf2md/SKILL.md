---
name: pdf2md
description: PDF'leri kusursuz Markdown'a çevirme ve pdf2md uygulamasının ürettiği .md dosyalarıyla çalışma (Bilge Gül Koç'tan hediye). Şu durumlarda kullan - kullanıcı "pdf2md" dediğinde; içinde "sayfa N" yorum işaretleri olan bir .md dosyası yüklediğinde; KONTROL-ET klasöründen "sayfa-012.png" gibi sayfa görselleri yükleyip düzeltme istediğinde; "bu sayfaları düzelt", "md'yi düzelt", "PDF'i markdown'a çevir", "PDF'i md yap" dediğinde; ya da pdf2md ile üretilmiş büyük bir .md hakkında soru sorduğunda.
---

# pdf2md

Bu skill, bilgisayarda çalışan **pdf2md uygulamasının** yardımcısıdır. Uygulama PDF'leri yerelde ve ücretsiz olarak `.md` dosyasına çevirir. Otomatik kontrolden geçemeyen sayfaları da `KONTROL-ET/` klasörüne PNG olarak koyar. Bu skill dört işi yapar:

| Kullanıcı ne yükledi? | Mod |
|---|---|
| `.md` + `sayfa-NNN.png` görselleri (ve/veya `BENI-OKU.md`) | **A. Düzeltme** |
| Sadece pdf2md `.md` dosyası (dosyalar) + bir soru veya görev | **B. Verimli okuma** |
| Doğrudan bir PDF + "md'ye çevir" | **C. Yedek dönüşüm** |
| "Uygulamayı nasıl kullanırım/kurarım?" veya C modundaki öneriye "evet" | **D. Uygulama rehberi** |

Kullanıcılar teknik değil. Konuşma dili **Türkçe**, sade ve kısa olmalı. Teknik ayrıntı verme, ne yaptığını tek cümleyle söyle.

---

## Markdown standardı (tüm modlar için)

Bu kurallar pdf2md çıktısıyla birebir uyumludur. Düzeltme yaparken de, sıfırdan yazarken de bunlara uy:

1. **Sadakat her şeyden önce gelir.** Sayfada ne yazıyorsa o yazılır. Özetleme, yorum ekleme, "düzeltme" amaçlı yeniden ifade etme, yazım hatalarını düzeltme yok. Okunamayan kısım varsa `[okunamadı]` yaz, tahmin etme.
2. **Türkçe karakterler** (ç ğ ı İ ö ş ü â î û) birebir korunur. `I/ı` ve `İ/i` ayrımına dikkat et.
3. **Sayfa işaretleri:** Her sayfa `<!-- sayfa N -->` satırıyla başlar. Bu işaretler asla silinmez, değiştirilmez veya taşınmaz.
4. **Başlıklar:** Belgenin görsel hiyerarşisine göre `#`, `##`, `###` kullanılır. Başlık seviyesi atlanmaz. Başlıktan önce ve sonra boş satır olur.
5. **Paragraflar:** Satır sonunda bölünmüş kelimeler birleştirilir (`onaylan-` + `ması` → `onaylanması`). Bir paragraf tek satırdır.
6. **Listeler:** Madde işaretleri `- ` ile yazılır. Numaralı listelerde orijinal numaralar korunur (`1.`, `a)`).
7. **Tablolar:** GitHub tablo biçimi kullanılır (`| a | b |` + `|---|---|`) ve hizalama boşluğu eklenmez. Birleşik hücrelerde değer ilk hücreye yazılır, diğerleri boş bırakılır. Her satırda sütun sayısı aynı olur.
8. **Formüller:** Satır içi formül `$...$`, blok formül `$$...$$` ile LaTeX olarak yazılır.
9. **Görseller:** Mevcut `![...](images/...)` linkleri korunur. Yeni görsel linki uydurulmaz.
10. **Çıkarılacaklar:** Her sayfada tekrar eden üst bilgi, alt bilgi ve sayfa numaraları yazılmaz.
11. Belgenin içine kendi notunu, açıklamanı veya imzanı **ekleme**.

---

## A. Düzeltme modu

Kullanıcı bir `.md` dosyası ve `sayfa-NNN.png` görselleri yükler.

1. Görsel adlarından sayfa numaralarını çıkar (`sayfa-012.png` → 12). `BENI-OKU.md` varsa her sayfanın neden şüpheli bulunduğunu oradan oku.
2. Her sayfa için:
   - `.md` içinde `<!-- sayfa N -->` ile bir sonraki sayfa işareti arasındaki bölümü bul.
   - Sayfa görseline dikkatle bak ve bölümü **görselle satır satır karşılaştır**. Eksik metinleri, yanlış okunmuş karakterleri, bozuk tabloları, yanlış başlık seviyelerini ve karışmış sütun sırasını tespit et.
   - Bölümü Markdown standardına göre yeniden yaz. Doğru olan kısımlara dokunma.
   - Neden "N formül LaTeX'e çevrilmedi" ise: pdf2md formülleri PDF'in ham metniyle ters tırnak içinde bırakmıştır, örneğin `` `Attention(Q, K, V ) = softmax( QKT √dk )V (1)` ``. Her birini görseldeki formüle bakarak LaTeX'e çevir. Ayrı satırdaysa `$$ ... $$`, metin içindeyse `$ ... $` kullan. Denklem numarası varsa `\tag{1}` ile koru.
3. **Sadece bu bölümleri değiştir.** Dosyanın geri kalanı birebir aynı kalmalı. Bunun için dosyayı bir script ile düzenle (Python'da bölümü işaretler arasından değiştir), dosyanın tamamını elle yeniden yazma.
4. Düzeltilmiş dosyayı **aynı adla** çıktı olarak ver (`/mnt/user-data/outputs/` klasörüne kaydet).
5. Kısa bir özet ver:
   > ✓ 3 sayfa düzeltildi:
   > - **Sayfa 4:** eksik iki paragraf eklendi
   > - **Sayfa 7:** tablo yeniden kuruldu (5 sütun)
   > - **Sayfa 12:** sorun yoktu, dokunulmadı

Görsel yüklenmemiş ama `BENI-OKU.md` yüklenmişse, kullanıcıdan `KONTROL-ET` klasöründeki PNG dosyalarını da sürüklemesini iste.

## B. Verimli okuma modu

pdf2md çıktıları büyük olabilir. Amaç, gereksiz token harcamadan doğru cevabı vermek.

1. Dosya küçükse (~40 KB altı) tamamını oku.
2. Büyükse önce **yapıyı** çıkar ve sadece gerekli bölümleri oku:
   ```bash
   grep -n -E '^#{1,4} |<!-- sayfa' dosya.md      # içindekiler + sayfa haritası
   grep -n -i 'aranan kelime' dosya.md              # ilgili yerleri bul
   sed -n '120,210p' dosya.md                       # sadece o aralığı oku
   ```
3. Cevaplarda kaynak sayfayı belirt: "(s. 12)". Sayfa numarası `<!-- sayfa N -->` işaretinden gelir ve orijinal PDF'in sayfasıdır.
4. Birden fazla dosya yüklendiyse önce her birinin başlık yapısına bak, sonra ilgili dosyaya odaklan.

## C. Yedek dönüşüm modu

Bu yol, kullanıcı pdf2md uygulamasını kuramadıysa veya elinde tek bir küçük PDF varsa kullanılır. **Uygulamaya göre daha yavaştır ve kullanıcının Claude kullanım hakkından yer.** 30 sayfadan büyük PDF'lerde dönüştürmeye başlamadan önce şunu sor:

> Bu PDF büyük (N sayfa). Bilgisayarınızdaki pdf2md uygulamasıyla daha hızlı ve kullanım hakkınızdan yemeden çevirebilirsiniz. Size adım adım göstereyim mi?

- **Evet** derse → **D. Uygulama rehberi**'ne geç.
- **Hayır, burada çevir** derse → aşağıdaki adımlarla devam et.

1. Sayfaları hazırla:
   ```bash
   python scripts/pdf_hazirla.py GIRDI.pdf /tmp/pdf2md
   ```
   Script her sayfa için `sayfa-NNN.png` (görsel) ve `sayfa-NNN.txt` (varsa PDF'in metin katmanı), ayrıca `ozet.json` üretir. `ozet.json` her sayfanın `dijital` mi `taranmis` mı olduğunu söyler. Gerekli kütüphane yoksa script kendisi `pip install` dener.
2. Sayfaları **5'erli gruplar** hâlinde işle. Her sayfa için:
   - **Dijital sayfa:** `.txt` dosyasındaki metni esas al (karakterleri doğrudur). Yapıyı (başlık, tablo, liste, sütun sırası) PNG'ye bakarak kur.
   - **Taranmış sayfa:** metni PNG'den oku.
   - Sonucu Markdown standardına göre `<!-- sayfa N -->` işaretiyle başlatarak `/mnt/user-data/outputs/<pdf-adı>.md` dosyasına **ekle** (append). Böylece uzun belgelerde bağlam dolsa bile iş kaybolmaz.
3. Belgedeki fotoğraf ve grafikleri sadece `[Görsel: kısa açıklama]` olarak belirt. Bu modda görsel dosyası çıkarılmaz.
4. Bitince dosyayı ver ve tek satırla özetle: sayfa sayısı ve varsa okunamayan yerler.

## D. Uygulama rehberi

Kullanıcıyı bilgisayarındaki pdf2md uygulamasıyla PDF dönüştürmeye adım adım götürür. Sen kullanıcının bilgisayarında hiçbir şey çalıştıramazsın; işleri kullanıcı yapar, sen yol gösterirsin.

**Kurallar**
- Her mesajda **tek adım** ver. Adımın sonunda "Bitince 'tamam' yazın" de ve cevabı bekle.
- Kısa ve sade yaz. Dosya ve klasör adlarını **kalın** yaz, birebir aynı yaz.
- Kullanıcı bir hata, uyarı ya da beklenmedik ekran söylerse aşağıdaki "Sorun çıkarsa" bölümüne bak. Orada yoksa ekran görüntüsü iste. Tahmin edip yeni adım uydurma.

**1. Durumu öğren** (iki soruyu tek mesajda sor)
- Bilgisayarınız Windows mu, Mac mi?
- pdf2md uygulamasını daha önce kurdunuz mu?

Kurduysa doğrudan **Dönüştürme adımları**'na geç.

**Kurulum adımları (bir kez)**
1. Size verilen **pdf2md.zip** dosyasını bulun ve Masaüstüne çıkarın.
   - Windows: dosyaya sağ tıklayın → **Tümünü ayıkla**.
   - Mac: dosyaya çift tıklayın.
   - Elinde zip yoksa: dosyayı Bilge Gül Koç'tan istemesini söyle ve dur.
2. Açılan **pdf2md** klasörünü açın.
   - Windows: **1-KURULUM (Windows)** dosyasına çift tıklayın. "Windows bilgisayarınızı korudu" uyarısı çıkarsa **Ek bilgi** → **Yine de çalıştır**.
   - Mac: **1-KURULUM (Mac)** dosyasına sağ tıklayın → **Aç**, çıkan pencerede tekrar **Aç**.
3. Siyah bir pencere açılır. 5-15 dakika sürebilir, pencereyi kapatmayın. **"Kurulum tamamlandı!"** yazısını görünce pencereyi kapatın.

**Dönüştürme adımları (her seferinde)**
1. Dönüştürmek istediğiniz PDF'i **pdf2md** klasöründeki **PDF-BURAYA** klasörüne kopyalayın.
2. **2-DONUSTUR (Windows)** veya **2-DONUSTUR (Mac)** dosyasına çift tıklayın. Pencerede ilerlemeyi görürsünüz. Büyük ve taranmış PDF'ler uzun sürebilir.
3. Bitince **SONUCLAR** klasörü kendiliğinden açılır. PDF'inizin adını taşıyan klasörün içindeki **.md** dosyasını bu sohbete sürükleyin.
   - Pencerede **⚠ kontrol et** yazıyorsa: aynı klasördeki **KONTROL-ET** klasöründeki görselleri de sürükleyin ve "bu sayfaları düzelt" yazın → **A. Düzeltme modu**.
   - Sadece .md geldiyse ve kullanıcının bir sorusu varsa → **B. Verimli okuma modu**.

**Sorun çıkarsa**
- **Mac "açılamıyor" / "geliştirici doğrulanamadı" diyor:** Sistem Ayarları → Gizlilik ve Güvenlik → aşağıdaki **Yine de Aç** düğmesi.
- **"Önce 1-KURULUM dosyasına çift tıklayarak kurulumu yapın" yazıyor:** Kurulum yapılmamış ya da yarıda kalmış. Kurulum adımlarına dön.
- **Kurulumda "HATA" yazıyor:** Önce internet bağlantısını kontrol edip kurulumu tekrar çalıştırmasını söyle. Yine olursa pencerenin ekran görüntüsünü Bilge Gül Koç'a göndermesini söyle.
- **"Dönüştürülecek yeni PDF yok" yazıyor:** PDF ya **PDF-BURAYA** klasöründe değil ya da daha önce dönüştürülmüş. Sonucu **SONUCLAR** klasöründe aramasını söyle.
- **Intel işlemcili eski bir Mac:** Kurulum çalışmayabilir. Bu durumda C modunu (Claude içinde dönüştürme) öner.

---

## Sık karşılaşılan durumlar

- **Neden "taranmış sayfa: OCR ile okundu" ise:** Sayfa görselini metinle kelime kelime karşılaştır; OCR'ın tipik hataları yer değiştirmiş kelimeler, değişmiş noktalama (`,` → `;`) ve kaybolmuş tirelerdir.
- **"Kalite %85" gibi bir değer soruldu:** pdf2md, dijital sayfalarda PDF'teki kelimelerin yüzde kaçının çıktıda bulunduğunu ölçer. %95 üstü iyidir. Düşükse ilgili sayfalar `KONTROL-ET` klasöründedir.
- **Kullanıcı sadece görsel yükleyip "bunu md yap" dedi:** Görseli C modundaki gibi tek sayfa olarak dönüştür.
- **Uygulama hata verdi:** Hata mesajını iste. Kurulum sorunlarında kullanıcıyı `NASIL-KULLANILIR.pdf` rehberine ve Bilge Gül Koç'a yönlendir.
