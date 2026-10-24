# ER Diyagramı (Şema v0)

GitHub bu diyagramı otomatik çizer.

```mermaid
erDiagram
    branslar   ||--o{ doktorlar      : "uzmanlık"
    hastaneler ||--o{ doktorlar      : "çalışır"
    doktorlar  ||--o{ doktor_takvimi : "çalışma günü"
    hastalar   ||--o{ randevular     : "alır"
    doktorlar  ||--o{ randevular     : "muayene eder"
    branslar   ||--o{ randevular     : ""
    hastaneler ||--o{ randevular     : ""
    sikayetler |o--o{ randevular     : "şikayet"
    branslar   |o--o{ sikayetler     : "doğru branş"
    hastalar   ||--o{ yedek_liste    : "bekler"
    branslar   ||--o{ yedek_liste    : ""
    randevular |o--o| yedek_liste    : "atanan randevu"
    randevular ||--o{ bildirimler    : "hakkında"
    hastalar   ||--o{ bildirimler    : "alır"

    branslar {
        int brans_id PK
        text brans_adi
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
    }
    hastalar {
        int hasta_id PK
        text ad
        text soyad
        text cinsiyet
        text dogum_tarihi
        text telefon
        text ilce
        text kronik_hastalik
        text iletisim_kanali
    }
    doktor_takvimi {
        int doktor_id PK
        text tarih PK
        int toplam_slot
        int calisiyor
    }
    sikayetler {
        int sikayet_id PK
        text metin
        int brans_id FK
        text aciliyet
    }
    randevular {
        int randevu_id PK
        int hasta_id FK
        int doktor_id FK
        int sikayet_id FK
        text olusturma_zamani
        text randevu_zamani
        text durum
        text kaynak
        real mesafe_km
    }
    yedek_liste {
        int kayit_id PK
        int hasta_id FK
        int brans_id FK
        int aciliyet_puani
        text durum
        int atanan_randevu_id FK
    }
    bildirimler {
        int bildirim_id PK
        int randevu_id FK
        int hasta_id FK
        text tur
        text yanit_niyeti
    }
    hava_durumu {
        text tarih PK
        text il PK
        text durum
    }
    tatiller {
        text tarih PK
        text tur
    }
    yanit_ornekleri {
        int ornek_id PK
        text metin
        text niyet
    }
```

`hava_durumu` ve `tatiller` tablolarına yabancı anahtar ile değil, **tarih** (ve il) üzerinden bağlanılır.
Bu bağlantıyı `v_noshow_ozellikleri` görünümü yapar.
