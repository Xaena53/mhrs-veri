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

**Eklenenler**
- `PRAGMA user_version = 100` (şema sürümü veritabanının içinde).
- `v_triyaj_veri` (2. grup): şikayet metni + branş **adıyla** etiket + aciliyet. Model eğitiminde doğrudan kullanılabilir.
- `v_bekleyen_randevular` (4. grup): henüz gerçekleşmemiş randevular; hasta adı, telefonu, iletişim kanalı, doktor, hastane.
- `v_aylik_brans_ozet` (6. grup): `v_aylik_ozet`'in ay × hastane × branş kırılımı.
- `schema/referans/branslar.csv` (16 branş, yaş/cinsiyet kısıtlarıyla) ve `schema/referans/tatiller.csv`
  (2025–2026 resmî tatiller, bayramlar, arifeler). `kurulum.py --csv` klasörde bu dosyalar yoksa referansları kullanır.
- `tests/`: 16 otomatik test (`python -m unittest discover tests -v`).

**Düzeltilenler (`kurulum.py`)**
- Windows'ta `newline=""` verilmeden yazılan CSV'lerdeki boş satırlar artık hata sayılmıyor, atlanıyor.
- CSV başlığını okumak için açılan dosya kapatılmıyordu; Windows'ta dosya kilitli kalabiliyordu.

## v0.1.1 — 25 Ekim 2026

- Yaş denetimleri doğum gününe göre tam hesaplanıyor (eski formül 158 bin randevuda 54 yanlış sonuç veriyordu).
- `--db` yanlışlıkla SQLite olmayan bir dosyayı gösterirse üzerine yazılmıyor.
- Türkçe Excel CSV'si (`;` ayırıcı, `4,2` ondalık) okunuyor; UTF-8 olmayan dosyada açık hata.
- `v_doluluk` 6,9 sn → 0,14 sn.
- Yeni denetim: kaynağı `YEDEK_LISTE` olup yedek kaydı olmayan randevu.

## v0.1 — 25 Ekim 2026

İlk taslak: 12 tablo, 4 görünüm, `kurulum.py`, örnek senaryo, ER diyagramı, veri sözlüğü.
