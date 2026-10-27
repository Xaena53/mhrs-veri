# Veri Sözlüğü (Şema v1.0)

Kaynak: [`schema/schema.sql`](../schema/schema.sql). Tarih alanları `YYYY-MM-DD`, zaman alanları `YYYY-MM-DD HH:MM:SS` biçimindedir.
**Tüm veriler sentetiktir.** TC kimlik no tutulmaz, hastalar yalnızca `hasta_id` ile tanınır.

**Biçim kuralları (şema zorlar):** `2026-3-2`, `9:00`, `2026-03-02T09:00:00` ya da 30 Şubat gibi değerler reddedilir.
Telefonlar `0500XXXXXXX` biçimindedir; 0500 ön eki GSM operatörlerine atanmış bloklar (50x, 53x, 54x, 55x) arasında kullanılmadığı için gerçek bir kişiye denk gelmez. CSV'yi Excel'de açıp kaydederseniz baştaki 0 silinebilir; şema bu durumda satırı reddeder.
`kurulum.py` Türkçe Excel'in noktalı virgüllü CSV'sini ve ondalık virgülünü (`4,2`) de okur; dosya UTF-8 olmalıdır.

**SQLite notu:** Yabancı anahtar kontrolü bağlantı başına açılır. Kendi kodunuzda bağlandıktan sonra `PRAGMA foreign_keys = ON;` çalıştırın.
Şema sürümü `PRAGMA user_version;` ile okunur (`100` = v1.0). Sürümler arası farklar: [`degisiklikler.md`](degisiklikler.md).

**Referans listeler:** Branşlar ([`schema/referans/branslar.csv`](../schema/referans/branslar.csv), 16 branş) ve
2025–2026 resmî tatilleri ([`schema/referans/tatiller.csv`](../schema/referans/tatiller.csv)) sabittir, üretilmez.
`brans_id` değerleri bu listeden alınmalıdır; triyaj etiketleri de bu adları kullanır.

## Hangi grup hangi tabloyu kullanır?

| Tablo / Görünüm | 2 Triyaj | 3 No-Show | 4 Chatbot | 5 Yedek Liste | 6 Dashboard |
|---|:-:|:-:|:-:|:-:|:-:|
| `sikayetler`, `v_triyaj_veri` | ● | | | ● | |
| `v_noshow_ozellikleri` | | ● | | | ● |
| `randevular` | | ● | ● | ● | ● |
| `v_bekleyen_randevular` | | | ● | | |
| `hastalar` | | ● | ● | ● | ● |
| `doktor_takvimi`, `v_doluluk` | | ● | | ● | ● |
| `hava_durumu`, `tatiller` | | ● | | | |
| `bildirimler`, `yanit_ornekleri` | | | ● | ● | ● |
| `yedek_liste`, `v_bekleyen_yedek` | | | | ● | ● |
| `v_aylik_ozet`, `v_aylik_brans_ozet` | | | | | ● |

---

## Ana tablolar

### `branslar`
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| brans_id | INTEGER PK | | 2 |
| brans_adi | TEXT | MHRS'deki branş adı | Kardiyoloji |
| ortalama_muayene_dk | INTEGER | Slot süresi önerisi | 15 |
| yas_min / yas_max | INTEGER | Yaş sınırı, NULL = sınır yok | 0 / 17 (Çocuk) |
| cinsiyet_kisiti | TEXT | `K`, `E` veya NULL | K (Kadın Doğum) |

### `hastaneler`
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| hastane_id | INTEGER PK | | 1 |
| hastane_adi | TEXT | Kurgusal ad | Odunpazarı Devlet Hastanesi (sentetik) |
| tur | TEXT | `DEVLET`, `EGITIM_ARASTIRMA`, `SEHIR`, `ILCE` | DEVLET |
| il, ilce | TEXT | | Eskişehir, Odunpazarı |
| enlem, boylam | REAL | Mesafe hesabı için | 39.7667, 30.5256 |

### `doktorlar`
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| doktor_id | INTEGER PK | | 2 |
| ad, soyad | TEXT | Faker ile üretilir | Mehmet Demir |
| unvan | TEXT | `Uzm. Dr.`, `Op. Dr.`, `Doç. Dr.`, `Prof. Dr.` | Doç. Dr. |
| brans_id | FK → branslar | | 2 |
| hastane_id | FK → hastaneler | | 2 |
| aktif | 0/1 | | 1 |

### `hastalar`
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| hasta_id | INTEGER PK | | 1 |
| ad, soyad | TEXT | Faker `tr_TR` | Ahmet Yılmaz |
| cinsiyet | TEXT | `K` / `E` | E |
| dogum_tarihi | TEXT | Yaş buradan hesaplanır | 1981-03-12 |
| telefon | TEXT | Sahte, `0500XXXXXXX` | 05001234567 |
| il, ilce | TEXT | | Eskişehir, Odunpazarı |
| enlem, boylam | REAL | Ev konumu (yaklaşık) | 39.76, 30.52 |
| kronik_hastalik | TEXT | Virgülle ayrık, NULL = yok | Hipertansiyon |
| iletisim_kanali | TEXT | `WHATSAPP`, `TELEGRAM`, `SMS`, `WEB` | WHATSAPP |
| kayit_tarihi | TEXT | Sisteme ilk kayıt | 2024-01-05 |

## Dış etkenler

### `hava_durumu` — PK (tarih, il)
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| durum | TEXT | `GUNESLI`, `BULUTLU`, `YAGMURLU`, `KARLI` | YAGMURLU |
| sicaklik_c | REAL | Günlük ortalama, −40…50 | 6.5 |

### `tatiller`
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| tarih | TEXT PK | | 2026-03-19 |
| ad | TEXT | | Ramazan Bayramı Arifesi |
| tur | TEXT | `RESMI`, `ARIFE`, `BAYRAM` | ARIFE |

### `doktor_takvimi` — PK (doktor_id, tarih)
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| baslangic_saat / bitis_saat | TEXT | Mesai (`HH:MM`) | 08:00 / 16:00 |
| ogle_baslangic / ogle_bitis | TEXT | Öğle arası, ikisi birlikte NULL olabilir | 12:00 / 13:00 |
| slot_dk | INTEGER | Slot süresi | 15 |
| toplam_slot | INTEGER | (Mesai − öğle arası) / slot_dk; denetim uyuşmazlığı yakalar | 28 |
| calisiyor | 0/1 | 0 = izin/rapor | 1 |

## Metin korpusları

### `sikayetler` (2. grup eğitim verisi)
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| metin | TEXT | Hastanın kendi cümlesi | Merdiven çıkarken göğsüm sıkışıyor |
| brans_id | FK, NULL olabilir | Doğru branş; ACİL vakada NULL | 2 |
| alternatif_brans_id | FK | Belirsiz vakalarda 2. seçenek | NULL |
| aciliyet | TEXT | `RUTIN`, `ONCELIKLI`, `ACIL` | ONCELIKLI |
| kaynak | TEXT | `SABLON`, `LLM`, `ELLE` | ELLE |

Kural: `aciliyet` ACIL değilse `brans_id` boş olamaz.

### `yanit_ornekleri` (4. grup niyet sınıflandırma verisi)
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| metin | TEXT | Hastanın kısa cevabı | Gelemeyeceğim |
| niyet | TEXT | `ONAY`, `IPTAL`, `ERTELEME`, `SORU`, `BELIRSIZ` | IPTAL |

## Olay tabloları

### `randevular`
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| randevu_id | INTEGER PK | | 1 |
| hasta_id, doktor_id, brans_id, hastane_id | FK | Branş ve hastane doktorunkiyle aynı olmalı | |
| sikayet_id | FK, NULL olabilir | Randevu alınırken yazılan şikayet | 1 |
| olusturma_zamani | TEXT | Randevunun alındığı an | 2026-02-10 10:00:00 |
| randevu_zamani | TEXT | Muayene saati | 2026-03-02 09:00:00 |
| durum | TEXT | `BEKLIYOR`, `GELDI`, `GELMEDI`, `IPTAL` | GELMEDI |
| iptal_zamani | TEXT | Yalnızca IPTAL ise dolu | |
| iptal_kanali | TEXT | `CHATBOT`, `WEB`, `TELEFON`, `SISTEM` | |
| kaynak | TEXT | `NORMAL`, `YEDEK_LISTE`, `CHATBOT` | NORMAL |
| hatirlatma_gonderildi | 0/1 | 24 saat önce mesaj gitti mi | 1 |
| mesafe_km | REAL | Ev ile hastane arası | 4.2 |

Kurallar: `randevu_zamani ≥ olusturma_zamani`. Aynı doktor ve saate, ya da aynı hastaya aynı saatte iki aktif randevu olamaz.
`IPTAL` ⇔ `iptal_zamani` ve `iptal_kanali` dolu. Randevu saati doktorun mesaisinde, öğle arası dışında ve slot ızgarasında olmalıdır (denetim).
`hatirlatma_gonderildi = 1` ise `bildirimler` tablosunda o randevu için bir `HATIRLATMA` kaydı bulunmalıdır (denetim).

### `yedek_liste`
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| kayit_id | INTEGER PK | | 1 |
| hasta_id, brans_id | FK | | 2, 2 |
| hastane_id | FK, NULL olabilir | NULL = fark etmez | |
| sikayet_id | FK | | |
| aciliyet_puani | 1–5 | 5 = en acil | 4 |
| tercih_zaman | TEXT | `SABAH`, `OGLEDEN_SONRA`, `FARK_ETMEZ` | SABAH |
| kayit_zamani | TEXT | Listeye girdiği an (sıra için) | 2026-02-25 09:00:00 |
| durum | TEXT | `BEKLIYOR`, `ATANDI`, `SURESI_DOLDU`, `VAZGECTI` | ATANDI |
| atanan_randevu_id | FK, UNIQUE | Yalnızca ATANDI ise dolu; bir randevu tek kayda atanır | 3 |
| guncelleme_zamani | TEXT | Durum değiştiği an; BEKLIYOR iken NULL | 2026-03-02 10:06:00 |

### `bildirimler`
| Sütun | Tip | Açıklama | Örnek |
|---|---|---|---|
| randevu_id | FK | İlgili randevu / boş slot | 2 |
| hasta_id | FK | Mesajı alan hasta | 1 |
| tur | TEXT | `HATIRLATMA`, `BOS_RANDEVU_TEKLIFI`, `IPTAL_ONAYI` | HATIRLATMA |
| kanal | TEXT | `WHATSAPP`, `TELEGRAM`, `SMS`, `WEB` | WHATSAPP |
| mesaj_metni | TEXT | Bot mesajı | Yarın saat 10:00'da... |
| gonderim_zamani / yanit_zamani | TEXT | Yanıt süresi buradan hesaplanır | |
| yanit_metni | TEXT | Hastanın cevabı, NULL = yanıtsız (o zaman yanit_zamani da NULL) | Gelemeyeceğim |
| yanit_niyeti | TEXT | `yanit_ornekleri.niyet` ile aynı etiketler | IPTAL |

## Hazır görünümler

| Görünüm | Kimin için | Ne verir |
|---|---|---|
| `v_noshow_ozellikleri` | 3. grup | Randevu başına model özellikleri: yaş (doğum gününe göre tam), cinsiyet, kronik_var, bekleme_gun, gün/saat, hava, tatil_yakin (±1 gün), mesafe, hatırlatma, önceki randevu/gelmeme/iptal sayısı ve hedef `hedef_gelmedi` (1 = gelmedi, 0 = geldi, NULL = henüz gerçekleşmedi). **Tahmin anı randevudan 24 saat öncedir**; geçmiş sayaçlar yalnızca bu andan önce gerçekleşmiş randevulardan hesaplanır, gelecekten bilgi sızmaz. |
| `v_aylik_ozet` | 6. grup | Ay bazında toplam, geldi, gelmedi, iptal, yedek listeden dolan, gelmeme oranı |
| `v_doluluk` | 6. grup | Doktor-gün başına doluluk yüzdesi |
| `v_bekleyen_yedek` | 5. grup | Bekleyen yedek liste kayıtları, hasta konumu ve iletişim kanalıyla birlikte, aciliyete göre sıralı |
| `v_triyaj_veri` | 2. grup | Şikayet metni, aciliyet, doğru branşın id'si **ve adı**, varsa alternatif branş. ACIL vakada branş boştur |
| `v_bekleyen_randevular` | 4. grup | Durumu BEKLIYOR olan randevular: hasta adı, telefon, iletişim kanalı, branş, doktor (unvanıyla), hastane, hatırlatma gitti mi. Zaman süzmesi sorguda yapılır, ör. yarınkiler: `WHERE date(randevu_zamani) = date('now','localtime','+1 day')` |
| `v_aylik_brans_ozet` | 6. grup | `v_aylik_ozet` ile aynı sayılar, ay × hastane × branş kırılımında (adlarıyla) |
