# MHRS Akıllı Otomasyon — Modül 1: Veri Yönetimi ve Sentetik Veri

Yapay Zekâ Destekli Otomasyon Sistemleri dersi, **1. Grup** projesi.

KVKK nedeniyle gerçek hasta verisi kullanılamadığından, MHRS otomasyon sisteminin diğer 5 modülünün
(AI Triyaj, No-Show Tahmini, Chatbot, Yedek Liste, Dashboard) kullanacağı **sentetik (yapay) veritabanını** üretiyoruz.

## Ekip ve Görevler

| Ekip | Üyeler | Sorumluluk | Klasör |
|---|---|---|---|
| Veritabanı & Altyapı | Bedirhan Ç., Eylül Y. | Şema, tablolar, SQL/CSV yapısı | `schema/` |
| Sentetik Veri Kodlama | Ceyda O., Nevra E. | Python + Faker ile veri üretimi | `uretici/` |
| Koordinasyon | Duygu K. | Diğer gruplarla sütun ihtiyaçları, notlar | `docs/` |

## Klasör Yapısı

```
schema/    → schema.sql, ER diyagramı, kurulum.py, referans/ (branşlar, tatiller)
tests/     → otomatik testler
uretici/   → uret.py (veri üreticisi), metinler.py (şikayet ve cevap metinleri), ilk_surum/ (ilk deneme)
docs/      → veri sözlüğü, toplantı notları, diğer grupların istekleri
cikti/     → üretilen dosyalar; ornek_csv/ ve ornek_gorunum/ repoda hazır küçük örnek
```

## Kurulum ve Kullanım

Gerekli: Python 3.10+. Veritabanı kurulumu ek kütüphane istemez, veri üretmek için `pip install -r requirements.txt`. Veritabanı SQLite'tır;
`.db` dosyası [DB Browser for SQLite](https://sqlitebrowser.org/) ile açılıp incelenebilir.

```bash
python uretici/uret.py                    # 5000 hasta, 12 aylık veri → cikti/csv (birkaç saniye)
python schema/kurulum.py --csv cikti/csv  # CSV'leri yükler, denetler → cikti/mhrs.db
python schema/kurulum.py --csv cikti/csv --gorunum-aktar cikti/gorunum   # hazır görünümleri de CSV yazar

python schema/kurulum.py --csv cikti/ornek_csv   # Faker kurmadan: repodaki küçük örnekle dene
```

- Şema: [`schema/schema.sql`](schema/schema.sql) — **v1.1**, 13 tablo, 10 hazır görünüm, biçim ve tutarlılık kuralları
- ER diyagramı: [`schema/ER.md`](schema/ER.md)
- Veri sözlüğü: [`docs/veri_sozlugu.md`](docs/veri_sozlugu.md) · Değişiklikler: [`docs/degisiklikler.md`](docs/degisiklikler.md)

Şemaya ya da `kurulum.py`'ye dokunduktan sonra testleri çalıştırın: `python -m unittest discover tests -v`

### Üretici ayarları

`python uretici/uret.py --hasta 8000 --ay 12 --tohum 42 --veri-ani "2026-11-06 09:00:00" --cikti cikti/csv`

Aynı tohum, veri anı ve Faker sürümü aynı veriyi üretir; gruplar aynı veri üzerinde çalışabilir. Gelmeme olasılığına gömülü
desenler: geçmiş gelmemeler, yağmur/kar, uzun bekleme, genç yaş, mesafe, tatil yakınlığı, hatırlatma ve hastanın onayı
(`gelmeme_olasiligi()`). Basit bir modelle AUC yaklaşık 0,70 çıkar; yani öğrenilebilir ama ezberlenemez.

### Sentetik Veri ekibi için CSV sözleşmesi

Üretici kod her tablo için `cikti/csv/<tablo_adi>.csv` yazar: ilk satır sütun adları (şemayla birebir),
UTF-8, boş hücre = NULL (Türkçe Excel'in `;` ayırıcısı da kabul edilir). `kurulum.py --csv` dosyaları doğru sırayla yükler; şema kuralına aykırı satır
varsa hiçbir şeyi yüklemez; dosya adı, satır numarası ve ihlal edilen kuralı gösterir.
Sütun adında (`dogumtarihi`) ya da dosya adında (`hasta.csv`) yazım hatası varsa bunu da söyler.
Yüklenen verinin uyması gereken tablolar arası kurallar [veri sözlüğünde](docs/veri_sozlugu.md#üretilen-verinin-uyması-gereken-kurallar) listelidir.
`branslar.csv` ve `tatiller.csv` üretmenize gerek yok: klasörde yoksa `schema/referans/` altındakiler yüklenir.
Pandas ile yazarken `df.to_csv(yol, index=False, encoding="utf-8")` yeterli. Örnek biçim için:
`python schema/kurulum.py --ornek --disa-aktar cikti/ornek_csv`

## Diğer Modüllerin Veri İhtiyaçları

| Grup | Modül | İhtiyaç |
|---|---|---|
| 2 | AI Triyaj | Branş etiketli Türkçe şikayet metinleri + ACİL örnekleri |
| 3 | No-Show Tahmini | Geçmiş randevular + geldi/gelmedi + etkileyen özellikler |
| 4 | Chatbot | İletişim bilgisi, yaklaşan randevular, hasta cevap örnekleri |
| 5 | Yedek Liste | Yedek liste kayıtları, iptal olayları, konum |
| 6 | API / Dashboard | Ortak şema, veritabanı, veri sözlüğü |

## Yol Haritası

- [x] Hafta 1 — Repo, şema v0 (12 tablo + 4 görünüm), ER diyagramı, veri sözlüğü
- [x] Hafta 1 — Şema diğer 5 gruba iletildi, ilk dönüşlerde eksik yok ([notlar](docs/toplanti_notlari.md)); kalan gruplardan dönüş bekleniyor
- [x] Hafta 2 — Şema v1.0 sabitlendi, ER diyagramı tüm sütunlarla, branş/tatil referansları, 3 yeni görünüm, 65 test ([değişiklikler](docs/degisiklikler.md))
- [x] Hafta 2–5 — Üretici tüm tabloları yazıyor: hasta/hastane/doktor, randevu geçmişi ve no-show desenleri, şikayet metinleri, yedek liste, mesajlar; örnek veri repoda; 90 test ([değişiklikler](docs/degisiklikler.md))
- [ ] Chatbot grubunun sütun isteklerinin ve 2 saat kuralının teyidi (koordinasyon)
- [ ] Metinlerin ve desenlerin ekipçe gözden geçirilmesi, diğer grupların geri bildirimi
- [ ] Sonrası — Geri bildirime göre düzeltmeler, rapor ve sunum

> Tüm veriler yapaydır; gerçek kişilerle ilgisi yoktur.
