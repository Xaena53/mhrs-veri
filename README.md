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
uretici/   → Faker ile veri üreten Python kodları
docs/      → veri sözlüğü, toplantı notları, diğer grupların istekleri
cikti/     → üretilen CSV / SQLite dosyaları
```

## Kurulum ve Kullanım

Gerekli: Python 3.10+ (veritabanı kurulumu için ek kütüphane gerekmez). Veritabanı SQLite'tır;
`.db` dosyası [DB Browser for SQLite](https://sqlitebrowser.org/) ile açılıp incelenebilir.

```bash
python schema/kurulum.py --ornek          # örnek veriyle cikti/mhrs.db oluşturur ve denetler
python schema/kurulum.py --csv cikti/csv  # üretilen CSV'leri yükler ve denetler
```

- Şema: [`schema/schema.sql`](schema/schema.sql) — **v1.0**, 12 tablo, 7 hazır görünüm, biçim ve tutarlılık kuralları
- ER diyagramı: [`schema/ER.md`](schema/ER.md)
- Veri sözlüğü: [`docs/veri_sozlugu.md`](docs/veri_sozlugu.md) · Değişiklikler: [`docs/degisiklikler.md`](docs/degisiklikler.md)

Şemaya ya da `kurulum.py`'ye dokunduktan sonra testleri çalıştırın: `python -m unittest discover tests -v`

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
- [ ] Hafta 2 — Hasta/hastane/doktor verisi (Sentetik Veri ekibi)
- [ ] Hafta 3 — Randevu geçmişi + no-show desenleri, 100 satırlık örnek veri
- [ ] Hafta 4 — Şikayet metinleri, yedek liste, mesajlar
- [ ] Hafta 5 — Tam veri seti, doğrulama, veri sözlüğü
- [ ] Sonrası — Geri bildirime göre düzeltmeler, rapor ve sunum

> Tüm veriler yapaydır; gerçek kişilerle ilgisi yoktur.
