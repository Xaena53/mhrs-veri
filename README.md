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
schema/    → schema.sql, ER diyagramı
uretici/   → Faker ile veri üreten Python kodları
docs/      → veri sözlüğü, toplantı notları, diğer grupların istekleri
cikti/     → üretilen CSV / SQLite dosyaları
```

## Diğer Modüllerin Veri İhtiyaçları

| Grup | Modül | İhtiyaç |
|---|---|---|
| 2 | AI Triyaj | Branş etiketli Türkçe şikayet metinleri + ACİL örnekleri |
| 3 | No-Show Tahmini | Geçmiş randevular + geldi/gelmedi + etkileyen özellikler |
| 4 | Chatbot | İletişim bilgisi, yaklaşan randevular, hasta cevap örnekleri |
| 5 | Yedek Liste | Yedek liste kayıtları, iptal olayları, konum |
| 6 | API / Dashboard | Ortak şema, veritabanı, veri sözlüğü |

## Yol Haritası

- [ ] Hafta 1 — Repo, diğer gruplardan sütun listeleri, şema v0
- [ ] Hafta 2 — Şema v1 + ER diyagramı, hasta/hastane/doktor verisi
- [ ] Hafta 3 — Randevu geçmişi + no-show desenleri, 100 satırlık örnek veri
- [ ] Hafta 4 — Şikayet metinleri, yedek liste, mesajlar
- [ ] Hafta 5 — Tam veri seti, doğrulama, veri sözlüğü
- [ ] Sonrası — Geri bildirime göre düzeltmeler, rapor ve sunum

> Tüm veriler yapaydır; gerçek kişilerle ilgisi yoktur.
