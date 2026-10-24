-- =====================================================================
-- MHRS Akıllı Otomasyon — Modül 1: Veri Yönetimi ve Sentetik Veri
-- Veritabanı şeması v0.1  (SQLite 3.28+)
--
-- Zaman alanları ISO-8601 metin: tarih 'YYYY-MM-DD', zaman 'YYYY-MM-DD HH:MM:SS',
-- saat 'HH:MM'. Biçim CHECK ile zorlanır: '2026-3-2', '9:00', 30 Şubat reddedilir.
-- Metin karşılaştırmaları (randevu_zamani >= olusturma_zamani gibi) bu biçime dayanır.
--
-- Tüm veriler sentetiktir; gerçek kişilerle ilgisi yoktur (KVKK).
-- Not: SQLite yabancı anahtarları bağlantı başına açar. Kendi kodunuzda bağlanınca
--      "PRAGMA foreign_keys = ON;" çalıştırın.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1) ANA (SABİT) TABLOLAR
-- ---------------------------------------------------------------------

-- Poliklinik branşları. Yaş/cinsiyet kısıtı: Çocuk Sağlığı <18, Kadın Doğum yalnız K vb.
CREATE TABLE branslar (
    brans_id            INTEGER PRIMARY KEY,
    brans_adi           TEXT    NOT NULL UNIQUE,
    ortalama_muayene_dk INTEGER NOT NULL DEFAULT 15 CHECK (ortalama_muayene_dk > 0),
    yas_min             INTEGER CHECK (yas_min IS NULL OR yas_min >= 0),
    yas_max             INTEGER CHECK (yas_max IS NULL OR yas_max >= 0),
    cinsiyet_kisiti     TEXT    CHECK (cinsiyet_kisiti IN ('K','E')),     -- NULL = herkes
    CHECK (yas_min IS NULL OR yas_max IS NULL OR yas_min <= yas_max)
);

CREATE TABLE hastaneler (
    hastane_id  INTEGER PRIMARY KEY,
    hastane_adi TEXT NOT NULL,
    tur         TEXT NOT NULL CHECK (tur IN ('DEVLET','EGITIM_ARASTIRMA','SEHIR','ILCE')),
    il          TEXT NOT NULL,
    ilce        TEXT NOT NULL,
    enlem       REAL NOT NULL CHECK (enlem  BETWEEN 35 AND 43),          -- Türkiye sınırları
    boylam      REAL NOT NULL CHECK (boylam BETWEEN 25 AND 45)
);

CREATE TABLE doktorlar (
    doktor_id  INTEGER PRIMARY KEY,
    ad         TEXT    NOT NULL,
    soyad      TEXT    NOT NULL,
    unvan      TEXT    NOT NULL CHECK (unvan IN ('Uzm. Dr.','Op. Dr.','Doç. Dr.','Prof. Dr.')),
    brans_id   INTEGER NOT NULL REFERENCES branslar(brans_id),
    hastane_id INTEGER NOT NULL REFERENCES hastaneler(hastane_id),
    aktif      INTEGER NOT NULL DEFAULT 1 CHECK (aktif IN (0,1))
);

-- Hasta profilleri. TC kimlik no TUTULMAZ; yalnızca hasta_id kullanılır.
-- Telefon: gerçek bir kişiye denk gelmesin diye operatörlere atanmamış 0500 ön ekiyle üretilir.
CREATE TABLE hastalar (
    hasta_id        INTEGER PRIMARY KEY,
    ad              TEXT NOT NULL,
    soyad           TEXT NOT NULL,
    cinsiyet        TEXT NOT NULL CHECK (cinsiyet IN ('K','E')),
    dogum_tarihi    TEXT NOT NULL CHECK (date(dogum_tarihi) IS dogum_tarihi),
    telefon         TEXT CHECK (telefon IS NULL OR telefon GLOB '0500[0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    il              TEXT NOT NULL,
    ilce            TEXT NOT NULL,
    enlem           REAL CHECK (enlem  IS NULL OR enlem  BETWEEN 35 AND 43),
    boylam          REAL CHECK (boylam IS NULL OR boylam BETWEEN 25 AND 45),
    kronik_hastalik TEXT,                                               -- virgülle ayrık, ör. 'Diyabet,Hipertansiyon'
    iletisim_kanali TEXT NOT NULL DEFAULT 'SMS'
                    CHECK (iletisim_kanali IN ('WHATSAPP','TELEGRAM','SMS','WEB')),
    kayit_tarihi    TEXT NOT NULL CHECK (date(kayit_tarihi) IS kayit_tarihi),
    CHECK (kayit_tarihi >= dogum_tarihi)
);

-- ---------------------------------------------------------------------
-- 2) DIŞ ETKENLER (No-Show modeli için)
-- ---------------------------------------------------------------------

CREATE TABLE hava_durumu (
    tarih      TEXT NOT NULL CHECK (date(tarih) IS tarih),
    il         TEXT NOT NULL,
    durum      TEXT NOT NULL CHECK (durum IN ('GUNESLI','BULUTLU','YAGMURLU','KARLI')),
    sicaklik_c REAL CHECK (sicaklik_c IS NULL OR sicaklik_c BETWEEN -40 AND 50),
    PRIMARY KEY (tarih, il)
);

CREATE TABLE tatiller (
    tarih TEXT PRIMARY KEY CHECK (date(tarih) IS tarih),
    ad    TEXT NOT NULL,
    tur   TEXT NOT NULL CHECK (tur IN ('RESMI','ARIFE','BAYRAM'))
);

-- ---------------------------------------------------------------------
-- 3) KAPASİTE (Dashboard doluluk oranı + overbooking için)
-- ---------------------------------------------------------------------

-- Doktorun o günkü çalışma planı. Slotlar baslangic'tan itibaren slot_dk aralıklarla,
-- öğle arası hariç. Ör. 08:00-16:00, öğle 12:00-13:00, 15 dk → 28 slot.
CREATE TABLE doktor_takvimi (
    doktor_id        INTEGER NOT NULL REFERENCES doktorlar(doktor_id),
    tarih            TEXT    NOT NULL CHECK (date(tarih) IS tarih),
    baslangic_saat   TEXT    NOT NULL DEFAULT '08:00' CHECK (strftime('%H:%M', baslangic_saat) IS baslangic_saat),
    bitis_saat       TEXT    NOT NULL DEFAULT '16:00' CHECK (strftime('%H:%M', bitis_saat) IS bitis_saat),
    ogle_baslangic   TEXT    DEFAULT '12:00' CHECK (strftime('%H:%M', ogle_baslangic) IS ogle_baslangic),
    ogle_bitis       TEXT    DEFAULT '13:00' CHECK (strftime('%H:%M', ogle_bitis) IS ogle_bitis),
    slot_dk          INTEGER NOT NULL DEFAULT 15 CHECK (slot_dk > 0),
    toplam_slot      INTEGER NOT NULL CHECK (toplam_slot >= 0),
    calisiyor        INTEGER NOT NULL DEFAULT 1 CHECK (calisiyor IN (0,1)),   -- 0 = izin/rapor
    PRIMARY KEY (doktor_id, tarih),
    CHECK (baslangic_saat < bitis_saat),
    CHECK ((ogle_baslangic IS NULL) = (ogle_bitis IS NULL)),
    CHECK (ogle_baslangic IS NULL OR (baslangic_saat <= ogle_baslangic
                                      AND ogle_baslangic < ogle_bitis
                                      AND ogle_bitis <= bitis_saat))
);

-- ---------------------------------------------------------------------
-- 4) METİN KORPUSLARI (Triyaj + Chatbot eğitimi için)
-- ---------------------------------------------------------------------

-- Hasta şikayet metinleri. brans_id NULL ve aciliyet='ACIL' → "Acil servise gidin" vakası.
CREATE TABLE sikayetler (
    sikayet_id          INTEGER PRIMARY KEY,
    metin               TEXT NOT NULL CHECK (length(trim(metin)) > 0),
    brans_id            INTEGER REFERENCES branslar(brans_id),
    alternatif_brans_id INTEGER REFERENCES branslar(brans_id),         -- belirsiz vakalar için 2. seçenek
    aciliyet            TEXT NOT NULL DEFAULT 'RUTIN'
                        CHECK (aciliyet IN ('RUTIN','ONCELIKLI','ACIL')),
    kaynak              TEXT NOT NULL DEFAULT 'SABLON'
                        CHECK (kaynak IN ('SABLON','LLM','ELLE')),
    CHECK (aciliyet = 'ACIL' OR brans_id IS NOT NULL),
    CHECK (alternatif_brans_id IS NULL OR alternatif_brans_id IS NOT brans_id)
);

-- Chatbot niyet (intent) örnekleri: "Gelemeyeceğim" → IPTAL
CREATE TABLE yanit_ornekleri (
    ornek_id INTEGER PRIMARY KEY,
    metin    TEXT NOT NULL CHECK (length(trim(metin)) > 0),
    niyet    TEXT NOT NULL CHECK (niyet IN ('ONAY','IPTAL','ERTELEME','SORU','BELIRSIZ'))
);

-- ---------------------------------------------------------------------
-- 5) OLAY TABLOLARI
-- ---------------------------------------------------------------------

CREATE TABLE randevular (
    randevu_id            INTEGER PRIMARY KEY,
    hasta_id              INTEGER NOT NULL REFERENCES hastalar(hasta_id),
    doktor_id             INTEGER NOT NULL REFERENCES doktorlar(doktor_id),
    brans_id              INTEGER NOT NULL REFERENCES branslar(brans_id),
    hastane_id            INTEGER NOT NULL REFERENCES hastaneler(hastane_id),
    sikayet_id            INTEGER REFERENCES sikayetler(sikayet_id),
    olusturma_zamani      TEXT    NOT NULL CHECK (datetime(olusturma_zamani) IS olusturma_zamani),
    randevu_zamani        TEXT    NOT NULL CHECK (datetime(randevu_zamani)   IS randevu_zamani),
    durum                 TEXT    NOT NULL DEFAULT 'BEKLIYOR'
                          CHECK (durum IN ('BEKLIYOR','GELDI','GELMEDI','IPTAL')),
    iptal_zamani          TEXT    CHECK (datetime(iptal_zamani) IS iptal_zamani),
    iptal_kanali          TEXT    CHECK (iptal_kanali IN ('CHATBOT','WEB','TELEFON','SISTEM')),
    kaynak                TEXT    NOT NULL DEFAULT 'NORMAL'
                          CHECK (kaynak IN ('NORMAL','YEDEK_LISTE','CHATBOT')),
    hatirlatma_gonderildi INTEGER NOT NULL DEFAULT 0 CHECK (hatirlatma_gonderildi IN (0,1)),
    mesafe_km             REAL    CHECK (mesafe_km IS NULL OR mesafe_km >= 0),
    CHECK (randevu_zamani >= olusturma_zamani),
    CHECK ((durum = 'IPTAL') = (iptal_zamani IS NOT NULL)),
    CHECK ((durum = 'IPTAL') = (iptal_kanali IS NOT NULL)),
    CHECK (iptal_zamani IS NULL OR (iptal_zamani >= olusturma_zamani AND iptal_zamani <= randevu_zamani))
);

-- Aynı doktorun aynı saatine iki aktif randevu verilemez (iptal edilenler hariç).
-- Overbooking (çifte randevu) 3. grubun kararıdır; gerekirse bu indeks kaldırılır.
CREATE UNIQUE INDEX ux_randevu_aktif_slot
    ON randevular(doktor_id, randevu_zamani) WHERE durum <> 'IPTAL';

-- Bir hasta aynı anda iki yerde olamaz.
CREATE UNIQUE INDEX ux_randevu_aktif_hasta
    ON randevular(hasta_id, randevu_zamani) WHERE durum <> 'IPTAL';

CREATE TABLE yedek_liste (
    kayit_id          INTEGER PRIMARY KEY,
    hasta_id          INTEGER NOT NULL REFERENCES hastalar(hasta_id),
    brans_id          INTEGER NOT NULL REFERENCES branslar(brans_id),
    hastane_id        INTEGER REFERENCES hastaneler(hastane_id),         -- NULL = fark etmez
    sikayet_id        INTEGER REFERENCES sikayetler(sikayet_id),
    aciliyet_puani    INTEGER NOT NULL DEFAULT 3 CHECK (aciliyet_puani BETWEEN 1 AND 5),
    tercih_zaman      TEXT    NOT NULL DEFAULT 'FARK_ETMEZ'
                      CHECK (tercih_zaman IN ('SABAH','OGLEDEN_SONRA','FARK_ETMEZ')),
    kayit_zamani      TEXT    NOT NULL CHECK (datetime(kayit_zamani) IS kayit_zamani),
    durum             TEXT    NOT NULL DEFAULT 'BEKLIYOR'
                      CHECK (durum IN ('BEKLIYOR','ATANDI','SURESI_DOLDU','VAZGECTI')),
    atanan_randevu_id INTEGER UNIQUE REFERENCES randevular(randevu_id),  -- bir randevu tek kayda atanır
    guncelleme_zamani TEXT    CHECK (datetime(guncelleme_zamani) IS guncelleme_zamani),
    CHECK ((durum = 'ATANDI') = (atanan_randevu_id IS NOT NULL)),
    CHECK ((durum = 'BEKLIYOR') = (guncelleme_zamani IS NULL)),
    CHECK (guncelleme_zamani IS NULL OR guncelleme_zamani >= kayit_zamani)
);

-- Hastaya giden her mesaj ve hastanın yanıtı (hatırlatma, boş randevu teklifi...).
CREATE TABLE bildirimler (
    bildirim_id     INTEGER PRIMARY KEY,
    randevu_id      INTEGER NOT NULL REFERENCES randevular(randevu_id),
    hasta_id        INTEGER NOT NULL REFERENCES hastalar(hasta_id),
    tur             TEXT    NOT NULL CHECK (tur IN ('HATIRLATMA','BOS_RANDEVU_TEKLIFI','IPTAL_ONAYI')),
    kanal           TEXT    NOT NULL CHECK (kanal IN ('WHATSAPP','TELEGRAM','SMS','WEB')),
    mesaj_metni     TEXT    NOT NULL,
    gonderim_zamani TEXT    NOT NULL CHECK (datetime(gonderim_zamani) IS gonderim_zamani),
    yanit_metni     TEXT,
    yanit_niyeti    TEXT    CHECK (yanit_niyeti IN ('ONAY','IPTAL','ERTELEME','SORU','BELIRSIZ')),
    yanit_zamani    TEXT    CHECK (datetime(yanit_zamani) IS yanit_zamani),
    CHECK ((yanit_metni IS NULL) = (yanit_zamani IS NULL)),
    CHECK (yanit_niyeti IS NULL OR yanit_metni IS NOT NULL),
    CHECK (yanit_zamani IS NULL OR yanit_zamani >= gonderim_zamani)
);

-- ---------------------------------------------------------------------
-- 6) İNDEKSLER
-- ---------------------------------------------------------------------
CREATE INDEX ix_randevu_hasta    ON randevular(hasta_id, randevu_zamani);
CREATE INDEX ix_randevu_brans    ON randevular(brans_id, randevu_zamani);
CREATE INDEX ix_randevu_durum    ON randevular(durum);
CREATE INDEX ix_randevu_doktor   ON randevular(doktor_id, randevu_zamani);
CREATE INDEX ix_yedek_bekleyen   ON yedek_liste(brans_id, durum, kayit_zamani);
CREATE INDEX ix_bildirim_randevu ON bildirimler(randevu_id);
CREATE INDEX ix_doktor_brans     ON doktorlar(brans_id, hastane_id);

-- ---------------------------------------------------------------------
-- 7) GÖRÜNÜMLER (diğer grupların doğrudan sorgulayacağı hazır tablolar)
-- ---------------------------------------------------------------------

-- 3. Grup (No-Show): randevu başına model özellikleri.
-- TAHMİN ANI = randevudan 24 saat önce. Geçmiş sayaçlar yalnızca bu andan en az 24 saat
-- önce gerçekleşmiş randevulardan hesaplanır; gelecekten bilgi sızmaz.
-- hedef_gelmedi: 1 = gelmedi, 0 = geldi, NULL = henüz gerçekleşmedi (BEKLIYOR).
CREATE VIEW v_noshow_ozellikleri AS
WITH gecmis AS (
    SELECT r.*,
           COALESCE(SUM(r.durum IN ('GELDI','GELMEDI')) OVER w, 0) AS onceki_randevu_sayisi,
           COALESCE(SUM(r.durum = 'GELMEDI')            OVER w, 0) AS onceki_gelmeme_sayisi,
           COALESCE(SUM(r.durum = 'IPTAL')              OVER w, 0) AS onceki_iptal_sayisi
    FROM randevular r
    WINDOW w AS (PARTITION BY r.hasta_id ORDER BY julianday(r.randevu_zamani)
                 RANGE BETWEEN UNBOUNDED PRECEDING AND 1.0 PRECEDING)
)
SELECT
    g.randevu_id,
    g.hasta_id,
    g.brans_id,
    g.hastane_id,
    -- tam yaş: yıl farkı, doğum günü henüz gelmediyse bir eksik
    CAST(strftime('%Y', g.randevu_zamani) AS INTEGER) - CAST(strftime('%Y', h.dogum_tarihi) AS INTEGER)
      - (strftime('%m-%d', g.randevu_zamani) < strftime('%m-%d', h.dogum_tarihi))            AS yas,
    h.cinsiyet,
    CASE WHEN h.kronik_hastalik IS NULL OR h.kronik_hastalik = '' THEN 0 ELSE 1 END          AS kronik_var,
    CAST(julianday(date(g.randevu_zamani)) - julianday(date(g.olusturma_zamani)) AS INTEGER) AS bekleme_gun,
    CAST(strftime('%w', g.randevu_zamani) AS INTEGER)                                        AS haftanin_gunu,  -- 0=Pazar
    CAST(strftime('%H', g.randevu_zamani) AS INTEGER)                                        AS saat,
    hd.durum                                                                                 AS hava,
    CASE WHEN EXISTS (SELECT 1 FROM tatiller t
                      WHERE t.tarih BETWEEN date(g.randevu_zamani,'-1 day')
                                        AND date(g.randevu_zamani,'+1 day'))
         THEN 1 ELSE 0 END                                                                   AS tatil_yakin,
    g.mesafe_km,
    g.hatirlatma_gonderildi,
    g.kaynak,
    g.onceki_randevu_sayisi,
    g.onceki_gelmeme_sayisi,
    g.onceki_iptal_sayisi,
    CASE g.durum WHEN 'GELMEDI' THEN 1 WHEN 'GELDI' THEN 0 END                               AS hedef_gelmedi
FROM gecmis g
JOIN hastalar h          ON h.hasta_id = g.hasta_id
JOIN hastaneler hs       ON hs.hastane_id = g.hastane_id
LEFT JOIN hava_durumu hd ON hd.tarih = date(g.randevu_zamani) AND hd.il = hs.il
WHERE g.durum <> 'IPTAL';

-- 6. Grup (Dashboard): aylık özet.
CREATE VIEW v_aylik_ozet AS
SELECT
    strftime('%Y-%m', randevu_zamani)                          AS ay,
    COUNT(*)                                                   AS toplam_randevu,
    SUM(durum = 'GELDI')                                       AS geldi,
    SUM(durum = 'GELMEDI')                                     AS gelmedi,
    SUM(durum = 'IPTAL')                                       AS iptal,
    SUM(kaynak = 'YEDEK_LISTE')                                AS yedek_listeden_dolan,
    ROUND(100.0 * SUM(durum = 'GELMEDI')
          / NULLIF(SUM(durum IN ('GELDI','GELMEDI')), 0), 1)   AS gelmeme_orani_yuzde
FROM randevular
GROUP BY ay;

-- 6. Grup (Dashboard): doktor-gün doluluk oranı. Overbooking varsa %100'ü aşabilir.
CREATE VIEW v_doluluk AS
SELECT
    dt.doktor_id,
    dt.tarih,
    dt.toplam_slot,
    COUNT(r.randevu_id) AS dolu_slot,
    ROUND(100.0 * COUNT(r.randevu_id) / NULLIF(dt.toplam_slot, 0), 1) AS doluluk_yuzde
FROM doktor_takvimi dt
LEFT JOIN randevular r
       ON r.doktor_id = dt.doktor_id
      AND r.randevu_zamani >= dt.tarih                    -- date() yerine aralık: indeks kullanılır
      AND r.randevu_zamani <  date(dt.tarih, '+1 day')
      AND r.durum <> 'IPTAL'
WHERE dt.calisiyor = 1
GROUP BY dt.doktor_id, dt.tarih;

-- 5. Grup (Yedek Liste): şu an bekleyenler, aciliyete ve kayıt sırasına göre.
CREATE VIEW v_bekleyen_yedek AS
SELECT y.*, h.ilce, h.enlem, h.boylam, h.iletisim_kanali
FROM yedek_liste y
JOIN hastalar h ON h.hasta_id = y.hasta_id
WHERE y.durum = 'BEKLIYOR'
ORDER BY y.brans_id, y.aciliyet_puani DESC, y.kayit_zamani;
