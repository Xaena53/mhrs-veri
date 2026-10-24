-- Şemayı test etmek için elle yazılmış küçük örnek veri.
-- Gerçek veri seti 2. ekibin üreticisinden (uretici/) gelecek.

INSERT INTO branslar VALUES
 (1,'Dahiliye',15,18,NULL,NULL),
 (2,'Kardiyoloji',15,18,NULL,NULL),
 (3,'Çocuk Sağlığı ve Hastalıkları',15,0,17,NULL),
 (4,'Kadın Hastalıkları ve Doğum',15,15,NULL,'K');

INSERT INTO hastaneler VALUES
 (1,'Merkez Devlet Hastanesi (sentetik)','DEVLET','Eskişehir','Odunpazarı',39.7667,30.5256),
 (2,'Tepebaşı Eğitim ve Araştırma Hastanesi (sentetik)','EGITIM_ARASTIRMA','Eskişehir','Tepebaşı',39.7845,30.5004);

INSERT INTO doktorlar VALUES
 (1,'Ayşe','Kaya','Uzm. Dr.',1,1,1),
 (2,'Mehmet','Demir','Doç. Dr.',2,2,1);

INSERT INTO hastalar VALUES
 (1,'Ahmet','Yılmaz','E','1981-03-12','05321234567','Eskişehir','Odunpazarı',39.76,30.52,'Hipertansiyon','WHATSAPP','2024-01-05'),
 (2,'Zeynep','Arslan','K','1999-07-30','05439876543','Eskişehir','Tepebaşı',39.79,30.49,NULL,'TELEGRAM','2024-02-11');

INSERT INTO hava_durumu VALUES
 ('2026-03-02','Eskişehir','YAGMURLU',6.5),
 ('2026-03-03','Eskişehir','GUNESLI',9.0),
 ('2026-03-04','Eskişehir','BULUTLU',8.0);

INSERT INTO tatiller VALUES ('2026-03-19','Ramazan Bayramı Arifesi','ARIFE');

INSERT INTO doktor_takvimi VALUES
 (2,'2026-03-02','08:00','16:00',15,28,1),
 (2,'2026-03-03','08:00','16:00',15,28,1),
 (2,'2026-03-04','08:00','16:00',15,28,1);

INSERT INTO sikayetler VALUES
 (1,'Gözlerimde kararma var, merdiven çıkarken göğsüm sıkışıyor',2,NULL,'ONCELIKLI','ELLE'),
 (2,'Sol kolum uyuştu, şiddetli göğüs ağrım var',NULL,NULL,'ACIL','ELLE');

INSERT INTO yanit_ornekleri VALUES
 (1,'Evet geleceğim','ONAY'),
 (2,'Gelemeyeceğim','IPTAL'),
 (3,'Başka bir güne alabilir miyiz?','ERTELEME');

INSERT INTO randevular VALUES
 (1,1,2,2,2,1,'2026-02-10 10:00:00','2026-03-02 09:00:00','GELMEDI',NULL,NULL,'NORMAL',1,4.2),
 (2,1,2,2,2,1,'2026-02-20 11:30:00','2026-03-03 10:00:00','IPTAL','2026-03-02 10:05:00','CHATBOT','NORMAL',1,4.2),
 (3,2,2,2,2,NULL,'2026-03-02 10:06:00','2026-03-03 10:00:00','GELDI',NULL,NULL,'YEDEK_LISTE',0,1.1),
 (4,1,2,2,2,1,'2026-03-03 12:00:00','2026-03-04 14:00:00','GELDI',NULL,NULL,'NORMAL',1,4.2);

INSERT INTO yedek_liste VALUES
 (1,2,2,NULL,NULL,4,'SABAH','2026-02-25 09:00:00','ATANDI',3,'2026-03-02 10:06:00');

INSERT INTO bildirimler VALUES
 (1,2,1,'HATIRLATMA','WHATSAPP','Yarın saat 10:00''da Kardiyoloji randevunuz var. Gelecek misiniz? (Evet / İptal Et)',
    '2026-03-02 10:00:00','Gelemeyeceğim','IPTAL','2026-03-02 10:05:00'),
 (2,2,2,'BOS_RANDEVU_TEKLIFI','TELEGRAM','Yarın 10:00 için boş randevu oluştu, onaylıyor musunuz?',
    '2026-03-02 10:05:30','Evet','ONAY','2026-03-02 10:06:00');
