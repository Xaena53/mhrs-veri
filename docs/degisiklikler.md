# Şema Değişiklikleri

Sürüm veritabanında da yazılıdır: `PRAGMA user_version;` → `100` = v1.0, `101` = v1.1.

## Sürüm kuralı (v1.0'dan itibaren)

- **Küçük sürüm (v1.1, v1.2):** yalnızca **ekleme**. Yeni görünüm, yeni isteğe bağlı sütun, yeni denetim.
  Mevcut sütun ve görünümler değişmez, diğer grupların kodu bozulmaz.
- **Büyük sürüm (v2.0):** sütun adı/tipi değişir, sütun ya da tablo kalkar. Önce Duygu K. diğer gruplara haber verir,
  değişiklik bu dosyaya "ne değişti, ne yapmanız gerekir" diye yazılır.
- Diğer gruplardan gelen istekler `docs/toplanti_notlari.md`'ye işlenir, şemaya Veritabanı ekibi (Bedirhan Ç., Eylül Y.) uygular.

## v1.0 — 27 Ekim 2026

Şema sabitlendi. v0.1.1'deki 12 tablonun **hiçbir sütunu değişmedi**; v0.1.1'e göre yazılmış kod aynen çalışır.
Yalnızca kurallar sıkılaştı: daha önce sessizce kabul edilen hatalı değerler artık reddediliyor (aşağıda).

**Eklenenler**
- `PRAGMA user_version = 100` (şema sürümü veritabanının içinde).
- `v_triyaj_veri` (2. grup): şikayet metni + branş **adıyla** etiket + aciliyet. Model eğitiminde doğrudan kullanılabilir.
- `v_bekleyen_randevular` (4. grup): henüz gerçekleşmemiş randevular; hasta adı, telefonu, iletişim kanalı, doktor, hastane.
- `v_aylik_brans_ozet` (6. grup): `v_aylik_ozet`'in ay × hastane × branş kırılımı.
- `schema/referans/branslar.csv` (16 branş, yaş/cinsiyet kısıtlarıyla) ve `schema/referans/tatiller.csv`
  (2025–2026 resmî tatiller, bayramlar, arifeler). `kurulum.py --csv` klasörde bu dosyalar yoksa referansları kullanır.
- `tests/`: 65 otomatik test (`python -m unittest discover tests -v`). Aşağıdaki her düzeltmenin bir testi var.
- Üretilen verinin uyması gereken kuralların listesi: veri sözlüğünde "Üretilen verinin uyması gereken kurallar".

**Yeni ve genişleyen denetimler (`kurulum.py`)** — daha önce hiçbiri yakalanmıyordu
- Branş yaş/cinsiyet kuralları yalnız randevulara uygulanıyordu; artık yedek listeye de (erkek hasta Kadın Doğum
  yedek listesinde, yetişkin Çocuk Sağlığı listesinde). Hasta kaydından önce yedek listeye giriş de yakalanıyor.
- Tatil listesi tutuluyor ama hiç denetlenmiyordu: resmî tatil/bayram gününe, arife öğleden sonrasına randevu;
  tatil listesinin kapsamadığı yıldaki randevu (no-show modelinde `tatil_yakin` sessizce hep 0 çıkardı).
- Boş randevu teklifi için konan kurallar diğer bildirim türlerine taşınmamıştı: iptal onayı yanlış hastaya,
  iptal edilmemiş randevuya ya da iptalden önce; hatırlatma iptalden sonra; boş yer teklifi iptal edenin kendisine.
- Chatbot akışı: hatırlatmaya IPTAL cevabı verilmiş ama iptal edilmemiş randevu; CHATBOT kanalıyla iptal edilmiş
  ama öncesinde hastanın IPTAL/ERTELEME cevabı olmayan randevu.
- "Gelecekteki GELDI" kuralının diğer zaman alanlarına genişletilmesi: şu andan sonraya tarihli oluşturma, iptal,
  mesaj, yanıt, yedek kaydı.
- Aktif olmayan doktora bekleyen randevu.
- Boş yer teklifi yedek listede olmayan hastaya; yedek kaydının randevu oluşmadan ATANDI sayılması;
  gelecek tarihli hasta kaydı.
- Yanlış alarm düzeltmesi: doktor izne çıkınca sistemin iptal ettiği randevu (`SISTEM`) artık
  "çalışmadığı güne randevu" sayılmıyor.

**Sıkılaşan kurallar (`schema.sql`)**
- Bir hasta aynı branş için yedek listede yalnızca bir kez BEKLIYOR olabilir (`ux_yedek_bekleyen_hasta`).
- Telefonu olmayan hasta yalnız `WEB` kanalını seçebilir (chatbot mesajı telefona gider).
- Sayısal sütunlarda tip denetimi (`typeof`): SQLite tip zorlamadığı için `4.2 km` gibi bir metin `mesafe_km`'ye
  girip `>= 0` kontrolünü de geçiyordu. Tam sayı sütunlarında (`slot_dk`, `toplam_slot`, `aciliyet_puani`,
  `ortalama_muayene_dk`, `yas_min/max`) `15.5` reddedilir; pandas'ın yazdığı `15.0` ise 15 olarak kabul edilir.
- `tatiller.tarih` boş bırakılabiliyordu (SQLite'ta metin birincil anahtar NULL alabilir); `NOT NULL` eklendi.

**Düzeltilenler (`kurulum.py`)**
- Büyük bir CSV'de UTF-8 dışı karakter ilk 8 KB'tan sonra geliyorsa program açıklamasız çöküyordu; artık
  "UTF-8 değil" mesajı ve bozuk baytın yeri veriliyor.
- `--ornek` ile `--csv` birlikte kullanılınca referans branşlar örnek branşların üzerine yüklenmeye çalışıp
  her şeyi reddediyordu; referans artık yalnızca tablo boşsa yüklenir.
- Metin birincil anahtarlı tablolarda (`hava_durumu`: tarih + il) eksik anahtar sütunu başlıkta yakalanmıyordu.
- Tekrarlanan sütun adı ve boş dosya için yanıltıcı mesaj yerine açık mesaj.
- Tırnak içinde satır atlayan hücreden sonra satır numaraları doğru; hata listesinin sonunda
  "ilk hatadan başlayın" ipucu (bir hatalı hasta satırı onlarca FOREIGN KEY hatasına yol açar).
- Yükleme yarıda bir istisnayla kesilirse işlem geri alınıyor (yarım veri kalmıyor).
- Windows'ta `newline=""` verilmeden yazılan CSV'lerdeki boş satırlar artık hata sayılmıyor, atlanıyor.
- CSV başlığını okumak için açılan dosya kapatılmıyordu; Windows'ta dosya kilitli kalabiliyordu.
- Türkçe Excel ondalık düzeltmesi (`4,2` → `4.2`) metin sütunlarına da uygulanıyordu: "10,30" cevabı "10.30" oluyordu.
  Artık yalnız sayı sütunlarında.
- Dosya adı yazım hatası (`hasta.csv`) sessizce atlanıp tablo boş kalıyordu; artık reddediliyor. `Hastalar.CSV` gibi
  büyük harfli adlar Windows'ta ve Linux'ta aynı şekilde kabul ediliyor.
- `--db` bir klasörü gösterirse açıklamasız hata yerine açık mesaj; yarıda kalmış eski çalıştırmanın
  `-journal`/`-wal` dosyaları yeni veritabanına karışmasın diye siliniyor.
- Yükleme reddedildiğinde önceki çalışan `mhrs.db` silinmiş oluyordu (diğer grupların kullandığı veritabanı
  bir hatalı CSV denemesiyle kayboluyordu). Artık yeni veritabanı yanına kurulur, yalnız yükleme başarılıysa
  eskisinin yerine geçer.
- Referans tatil listesinde yazım: "Millî Birlik".
- Veri sözlüğüne eksik anahtar sütunları eklendi; "2. ekip" ifadesi 2. grupla (Triyaj) karışmasın diye
  "Sentetik Veri ekibi" yapıldı.

## v0.1.1 — 25 Ekim 2026

- Yaş denetimleri doğum gününe göre tam hesaplanıyor (eski formül 158 bin randevuda 54 yanlış sonuç veriyordu).
- `--db` yanlışlıkla SQLite olmayan bir dosyayı gösterirse üzerine yazılmıyor.
- Türkçe Excel CSV'si (`;` ayırıcı, `4,2` ondalık) okunuyor; UTF-8 olmayan dosyada açık hata.
- `v_doluluk` 6,9 sn → 0,14 sn.
- Yeni denetim: kaynağı `YEDEK_LISTE` olup yedek kaydı olmayan randevu.

## v0.1 — 25 Ekim 2026

İlk taslak: 12 tablo, 4 görünüm, `kurulum.py`, örnek senaryo, ER diyagramı, veri sözlüğü.
