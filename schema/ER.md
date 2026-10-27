# ER Diyagramı (Şema v1.0)

GitHub bu diyagramı otomatik çizer. Tüm sütunlar gösterilir; kurallar ve açıklamalar için
[veri sözlüğüne](../docs/veri_sozlugu.md) bakın.

```mermaid
erDiagram
    branslar   ||--o{ doktorlar      : "uzmanlık"
    hastaneler ||--o{ doktorlar      : "çalışır"
    doktorlar  ||--o{ doktor_takvimi : "çalışma günü"
    hastalar   ||--o{ randevular     : "alır"
    doktorlar  ||--o{ randevular     : "muayene eder"
    branslar   ||--o{ randevular     : "branşı"
    hastaneler ||--o{ randevular     : "hastanesi"
    sikayetler |o--o{ randevular     : "şikayet"
    branslar   |o--o{ sikayetler     : "doğru branş"
    hastalar   ||--o{ yedek_liste    : "bekler"
    branslar   ||--o{ yedek_liste    : "istenen branş"
    hastaneler |o--o{ yedek_liste    : "tercih edilen"
    sikayetler |o--o{ yedek_liste    : "şikayet"
    randevular |o--o| yedek_liste    : "atanan randevu"
    randevular ||--o{ bildirimler    : "hakkında"
    hastalar   ||--o{ bildirimler    : "alır"

    branslar {
        int brans_id PK
        text brans_adi UK
        int ortalama_muayene_dk
        int yas_min
        int yas_max
        text cinsiyet_kisiti
    }
    hastaneler {
        int hastane_id PK
        text hastane_adi
        text tur
        text il
        text ilce
        real enlem
        real boylam
    }
    doktorlar {
        int doktor_id PK
        text ad
        text soyad
        text unvan
        int brans_id FK
        int hastane_id FK
        int aktif
    }
    hastalar {
        int hasta_id PK
        text ad
        text soyad
        text cinsiyet
        text dogum_tarihi
        text telefon
        text il
        text ilce
        real enlem
        real boylam
        text kronik_hastalik
        text iletisim_kanali
        text kayit_tarihi
    }
    doktor_takvimi {
        int doktor_id PK,FK
        text tarih PK
        text baslangic_saat
        text bitis_saat
        text ogle_baslangic
        text ogle_bitis
        int slot_dk
        int toplam_slot
        int calisiyor
    }
    sikayetler {
        int sikayet_id PK
        text metin
        int brans_id FK
        int alternatif_brans_id FK
        text aciliyet
        text kaynak
    }
    randevular {
        int randevu_id PK
        int hasta_id FK
        int doktor_id FK
        int brans_id FK
        int hastane_id FK
        int sikayet_id FK
        text olusturma_zamani
        text randevu_zamani
        text durum
        text iptal_zamani
        text iptal_kanali
        text kaynak
        int hatirlatma_gonderildi
        real mesafe_km
    }
    yedek_liste {
        int kayit_id PK
        int hasta_id FK
        int brans_id FK
        int hastane_id FK
        int sikayet_id FK
        int aciliyet_puani
        text tercih_zaman
        text kayit_zamani
        text durum
        int atanan_randevu_id FK,UK
        text guncelleme_zamani
    }
    bildirimler {
        int bildirim_id PK
        int randevu_id FK
        int hasta_id FK
        text tur
        text kanal
        text mesaj_metni
        text gonderim_zamani
        text yanit_metni
        text yanit_niyeti
        text yanit_zamani
    }
    hava_durumu {
        text tarih PK
        text il PK
        text durum
        real sicaklik_c
    }
    tatiller {
        text tarih PK
        text ad
        text tur
    }
    yanit_ornekleri {
        int ornek_id PK
        text metin
        text niyet
    }
```

`sikayetler.alternatif_brans_id` de `branslar` tablosuna bağlıdır (diyagramı sade tutmak için çizilmedi).
`hava_durumu` ve `tatiller` tablolarına yabancı anahtar ile değil, **tarih** (ve hastanenin ili) üzerinden bağlanılır;
bu bağlantıyı `v_noshow_ozellikleri` görünümü yapar. `yanit_ornekleri` bağımsız bir eğitim korpusudur.

## Görünümler

| Görünüm | Kaynak tablolar | Kimin için |
|---|---|---|
| `v_triyaj_veri` | sikayetler, branslar | 2. grup (Triyaj) |
| `v_noshow_ozellikleri` | randevular, hastalar, hastaneler, hava_durumu, tatiller | 3. grup (No-Show) |
| `v_bekleyen_randevular` | randevular, hastalar, branslar, doktorlar, hastaneler | 4. grup (Chatbot) |
| `v_bekleyen_yedek` | yedek_liste, hastalar | 5. grup (Yedek Liste) |
| `v_aylik_ozet`, `v_aylik_brans_ozet`, `v_doluluk` | randevular, hastaneler, branslar, doktor_takvimi | 6. grup (Dashboard) |
