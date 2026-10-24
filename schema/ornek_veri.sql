-- Şemayı test etmek için elle yazılmış küçük örnek veri.
-- Gerçek veri seti 2. ekibin üreticisinden (uretici/) gelecek.

INSERT INTO branslar (brans_id, brans_adi, ortalama_muayene_dk, yas_min, yas_max, cinsiyet_kisiti) VALUES
 (1,'Dahiliye',15,18,NULL,NULL),
 (2,'Kardiyoloji',15,18,NULL,NULL),
 (3,'Çocuk Sağlığı ve Hastalıkları',15,0,17,NULL),
 (4,'Kadın Hastalıkları ve Doğum',15,15,NULL,'K');

INSERT INTO hastaneler (hastane_id, hastane_adi, tur, il, ilce, enlem, boylam) VALUES
 (1,'Odunpazarı Devlet Hastanesi (sentetik)','DEVLET','Eskişehir','Odunpazarı',39.7667,30.5256),
 (2,'Tepebaşı Eğitim ve Araştırma Hastanesi (sentetik)','EGITIM_ARASTIRMA','Eskişehir','Tepebaşı',39.7845,30.5004);

INSERT INTO doktorlar (doktor_id, ad, soyad, unvan, brans_id, hastane_id, aktif) VALUES
 (1,'Ayşe','Kaya','Uzm. Dr.',1,1,1),
 (2,'Mehmet','Demir','Doç. Dr.',2,2,1);

INSERT INTO hastalar (hasta_id, ad, soyad, cinsiyet, dogum_tarihi, telefon, il, ilce, enlem, boylam,
                      kronik_hastalik, iletisim_kanali, kayit_tarihi) VALUES
 (1,'Ahmet','Yılmaz','E','1981-03-12','05001234567','Eskişehir','Odunpazarı',39.76,30.52,'Hipertansiyon','WHATSAPP','2024-01-05'),
 (2,'Zeynep','Arslan','K','1999-07-30','05009876543','Eskişehir','Tepebaşı',39.79,30.49,NULL,'TELEGRAM','2024-02-11');

INSERT INTO hava_durumu (tarih, il, durum, sicaklik_c) VALUES
 ('2026-03-02','Eskişehir','YAGMURLU',6.5),
 ('2026-03-03','Eskişehir','GUNESLI',9.0),
 ('2026-03-04','Eskişehir','BULUTLU',8.0);

INSERT INTO tatiller (tarih, ad, tur) VALUES ('2026-03-19','Ramazan Bayramı Arifesi','ARIFE');

INSERT INTO doktor_takvimi (doktor_id, tarih, baslangic_saat, bitis_saat, ogle_baslangic, ogle_bitis,
                            slot_dk, toplam_slot, calisiyor) VALUES
 (2,'2026-03-02','08:00','16:00','12:00','13:00',15,28,1),
 (2,'2026-03-03','08:00','16:00','12:00','13:00',15,28,1),
 (2,'2026-03-04','08:00','16:00','12:00','13:00',15,28,1);

INSERT INTO sikayetler (sikayet_id, metin, brans_id, alternatif_brans_id, aciliyet, kaynak) VALUES
 (1,'Gözlerimde kararma var, merdiven çıkarken göğsüm sıkışıyor',2,NULL,'ONCELIKLI','ELLE'),
 (2,'Sol kolum uyuştu, şiddetli göğüs ağrım var',NULL,NULL,'ACIL','ELLE');

INSERT INTO yanit_ornekleri (ornek_id, metin, niyet) VALUES
 (1,'Evet geleceğim','ONAY'),
 (2,'Gelemeyeceğim','IPTAL'),
 (3,'Başka bir güne alabilir miyiz?','ERTELEME');

-- Senaryo: Ahmet 2 Mart'a gelmedi; 3 Mart randevusunu chatbot ile iptal etti;
-- boşalan slot yedek listedeki Zeynep'e verildi; Ahmet 4 Mart'a geldi.
INSERT INTO randevular (randevu_id, hasta_id, doktor_id, brans_id, hastane_id, sikayet_id,
                        olusturma_zamani, randevu_zamani, durum, iptal_zamani, iptal_kanali,
                        kaynak, hatirlatma_gonderildi, mesafe_km) VALUES
 (1,1,2,2,2,1,'2026-02-10 10:00:00','2026-03-02 09:00:00','GELMEDI',NULL,NULL,'NORMAL',1,4.2),
 (2,1,2,2,2,1,'2026-02-20 11:30:00','2026-03-03 10:00:00','IPTAL','2026-03-02 10:05:00','CHATBOT','NORMAL',1,4.2),
 (3,2,2,2,2,NULL,'2026-03-02 10:06:00','2026-03-03 10:00:00','GELDI',NULL,NULL,'YEDEK_LISTE',0,1.1),
 (4,1,2,2,2,1,'2026-03-03 12:00:00','2026-03-04 14:00:00','GELDI',NULL,NULL,'NORMAL',1,4.2);

INSERT INTO yedek_liste (kayit_id, hasta_id, brans_id, hastane_id, sikayet_id, aciliyet_puani,
                         tercih_zaman, kayit_zamani, durum, atanan_randevu_id, guncelleme_zamani) VALUES
 (1,2,2,NULL,NULL,4,'SABAH','2026-02-25 09:00:00','ATANDI',3,'2026-03-02 10:06:00');

INSERT INTO bildirimler (bildirim_id, randevu_id, hasta_id, tur, kanal, mesaj_metni,
                         gonderim_zamani, yanit_metni, yanit_niyeti, yanit_zamani) VALUES
 (1,1,1,'HATIRLATMA','WHATSAPP','Yarın saat 09:00''da Kardiyoloji randevunuz var. Gelecek misiniz? (Evet / İptal Et)',
    '2026-03-01 09:00:00',NULL,NULL,NULL),
 (2,2,1,'HATIRLATMA','WHATSAPP','Yarın saat 10:00''da Kardiyoloji randevunuz var. Gelecek misiniz? (Evet / İptal Et)',
    '2026-03-02 10:00:00','Gelemeyeceğim','IPTAL','2026-03-02 10:05:00'),
 (3,2,2,'BOS_RANDEVU_TEKLIFI','TELEGRAM','Yarın 10:00 için boş randevu oluştu, onaylıyor musunuz?',
    '2026-03-02 10:05:30','Evet','ONAY','2026-03-02 10:06:00'),
 (4,4,1,'HATIRLATMA','WHATSAPP','Yarın saat 14:00''te Kardiyoloji randevunuz var. Gelecek misiniz? (Evet / İptal Et)',
    '2026-03-03 14:00:00','Evet geleceğim','ONAY','2026-03-03 14:20:00');
