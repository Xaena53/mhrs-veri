"""Tablolar arası denetim kurallarının testleri. Çalıştırma: python -m unittest discover tests -v

Her test örnek veriye tek bir hata ekler ve YALNIZCA beklenen kuralın, beklenen satır sayısıyla
tetiklendiğini doğrular. Kural adları uzun olduğu için beklenen kural adın bir parçasıyla verilir.
"""
import datetime as dt
import sqlite3
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "schema"))
import kurulum  # noqa: E402

GELECEK = dt.date.today() + dt.timedelta(days=30)  # 'şu an'a göre değişen kurallar için


def kural(parca: str) -> str:
    adlar = [ad for ad in kurulum.DENETIMLER if parca in ad]
    if len(adlar) != 1:
        raise AssertionError(f"{parca!r} tek bir kurala denk gelmiyor: {adlar}")
    return adlar[0]


class DenetimTesti(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        self.con.executescript(kurulum.SEMA.read_text(encoding="utf-8"))
        self.con.executescript(kurulum.ORNEK.read_text(encoding="utf-8"))

    def calistir(self, *sqller):
        for sql in sqller:
            self.con.execute(sql)

    def yalniz(self, beklenen: dict):
        bulunan = {ad: n for ad, sql in kurulum.DENETIMLER.items() if (n := self.con.execute(sql).fetchone()[0])}
        self.assertEqual(bulunan, {kural(k): n for k, n in beklenen.items()})

    def gun_hazirla(self, tarih: str):
        """Doktor 2 için o güne takvim ve hava kaydı (yoksa başka kurallar da tetiklenir)."""
        self.calistir(f"INSERT INTO doktor_takvimi VALUES (2,'{tarih}','08:00','16:00','12:00','13:00',15,28,1)",
                      f"INSERT INTO hava_durumu VALUES ('{tarih}','Eskişehir','GUNESLI',10)",
                      # Yılı tatil listesinde olsun (yoksa "kapsamadığı yıl" kuralı tetiklenir); günün kendisi değil.
                      f"INSERT OR IGNORE INTO tatiller VALUES "
                      f"('{tarih[:4]}-{'01-01' if tarih[5:] != '01-01' else '12-31'}','Yıl kaydı','RESMI')")

    def randevu(self, zaman: str, durum="GELDI", olusturma="2026-03-01 10:00:00"):
        self.calistir(f"""INSERT INTO randevular (hasta_id, doktor_id, brans_id, hastane_id, olusturma_zamani,
                          randevu_zamani, durum) VALUES (2, 2, 2, 2, '{olusturma}', '{zaman}', '{durum}')""")

    def test_ornek_veri_temiz(self):
        self.yalniz({})

    # --- branş kısıtları yedek listede de geçerli --------------------------

    def test_yedek_liste_cinsiyet(self):
        self.calistir("INSERT INTO yedek_liste (hasta_id, brans_id, kayit_zamani) VALUES (1, 4, '2026-03-01 10:00:00')")
        self.yalniz({"Cinsiyet": 1})

    def test_yedek_liste_yas_ust_siniri(self):
        self.calistir("INSERT INTO yedek_liste (hasta_id, brans_id, kayit_zamani) VALUES (1, 3, '2026-03-01 10:00:00')")
        self.yalniz({"yaş üst": 1})

    def test_yedek_liste_hasta_kaydindan_once(self):
        self.calistir("INSERT INTO yedek_liste (hasta_id, brans_id, kayit_zamani) VALUES (1, 2, '2023-01-01 10:00:00')")
        self.yalniz({"kaydolmadan": 1})

    def test_ayni_brans_icin_iki_bekleyen_yedek_kaydi(self):
        self.calistir("INSERT INTO yedek_liste (hasta_id, brans_id, kayit_zamani) VALUES (1, 2, '2026-03-01 10:00:00')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.calistir("INSERT INTO yedek_liste (hasta_id, brans_id, kayit_zamani) VALUES (1, 2, '2026-03-01 11:00:00')")
        # Farklı branş, ya da eski kaydı düşmüş aynı branş serbest.
        self.calistir("INSERT INTO yedek_liste (hasta_id, brans_id, kayit_zamani) VALUES (1, 1, '2026-03-01 11:00:00')",
                      "UPDATE yedek_liste SET durum = 'VAZGECTI', guncelleme_zamani = '2026-03-01 12:00:00' "
                      "WHERE hasta_id = 1 AND brans_id = 2",
                      "INSERT INTO yedek_liste (hasta_id, brans_id, kayit_zamani) VALUES (1, 2, '2026-03-01 13:00:00')")
        self.yalniz({})

    # --- tatiller -------------------------------------------------------------

    def test_bayram_gunune_randevu(self):
        self.calistir("INSERT INTO tatiller VALUES ('2026-03-20','Ramazan Bayramı 1. Gün','BAYRAM')")
        self.gun_hazirla("2026-03-20")
        self.randevu("2026-03-20 09:00:00")
        self.yalniz({"Resmî tatil": 1})

    def test_arife_sabahi_serbest_ogleden_sonrasi_degil(self):
        self.gun_hazirla("2026-03-19")  # örnek veride arife
        self.randevu("2026-03-19 11:45:00")
        self.yalniz({})
        self.randevu("2026-03-19 13:00:00")
        self.yalniz({"Resmî tatil": 1})

    def test_tatil_listesinin_kapsamadigi_yil(self):
        self.calistir("INSERT INTO doktor_takvimi VALUES (2,'2029-02-01','08:00','16:00','12:00','13:00',15,28,1)",
                      "INSERT INTO hava_durumu VALUES ('2029-02-01','Eskişehir','KARLI',-2)")
        self.randevu("2029-02-01 09:00:00", durum="BEKLIYOR", olusturma="2026-10-01 10:00:00")
        self.yalniz({"Tatil listesinin": 1})

    # --- doktor ----------------------------------------------------------------

    def test_aktif_olmayan_doktora_bekleyen_randevu(self):
        self.gun_hazirla(GELECEK.isoformat())
        self.randevu(f"{GELECEK} 09:00:00", durum="BEKLIYOR", olusturma="2026-10-01 10:00:00")
        self.yalniz({})
        self.calistir("UPDATE doktorlar SET aktif = 0 WHERE doktor_id = 2")
        self.yalniz({"Aktif olmayan": 1})

    # --- zaman ----------------------------------------------------------------

    def test_gelecekte_gonderilmis_bildirim(self):
        self.calistir(f"""INSERT INTO bildirimler (randevu_id, hasta_id, tur, kanal, mesaj_metni, gonderim_zamani)
                          VALUES (2, 1, 'IPTAL_ONAYI', 'SMS', 'İptal edildi', '{GELECEK} 10:00:00')""")
        self.yalniz({"Şu andan sonraya": 1})

    def test_gelecekte_yedek_kaydi(self):
        self.calistir(f"INSERT INTO yedek_liste (hasta_id, brans_id, kayit_zamani) VALUES (2, 1, '{GELECEK} 10:00:00')")
        self.yalniz({"Şu andan sonraya": 1})

    # --- bildirim türleri ------------------------------------------------------

    def bildirim(self, randevu_id, hasta_id, tur, zaman):
        self.calistir(f"""INSERT INTO bildirimler (randevu_id, hasta_id, tur, kanal, mesaj_metni, gonderim_zamani)
                          VALUES ({randevu_id}, {hasta_id}, '{tur}', 'SMS', 'mesaj', '{zaman}')""")

    def test_iptal_onayi_dogru_kullanim(self):
        self.bildirim(2, 1, "IPTAL_ONAYI", "2026-03-02 10:05:10")
        self.yalniz({})

    def test_iptal_onayi_iptal_edilmemis_randevuya(self):
        self.bildirim(4, 1, "IPTAL_ONAYI", "2026-03-03 13:00:00")
        self.yalniz({"İptal onayı": 1})

    def test_iptal_onayi_baska_hastaya(self):
        self.bildirim(2, 2, "IPTAL_ONAYI", "2026-03-02 10:06:00")
        self.yalniz({"İptal onayı": 1})

    def test_iptal_onayi_iptalden_once(self):
        self.bildirim(2, 1, "IPTAL_ONAYI", "2026-03-02 10:04:00")
        self.yalniz({"İptal onayı": 1})

    def test_bos_randevu_teklifi_iptal_edenin_kendisine(self):
        self.bildirim(2, 1, "BOS_RANDEVU_TEKLIFI", "2026-03-02 10:06:00")
        self.yalniz({"Boş randevu": 1})

    def test_hatirlatma_iptalden_sonra(self):
        self.bildirim(2, 1, "HATIRLATMA", "2026-03-02 10:30:00")
        self.yalniz({"Hatırlatma randevu sahibine": 1})

    # --- chatbot akışı ---------------------------------------------------------

    def test_iptal_cevabi_verilmis_randevu_iptal_edilmemis(self):
        self.calistir("UPDATE bildirimler SET yanit_metni = 'Gelemem', yanit_niyeti = 'IPTAL' WHERE bildirim_id = 4")
        self.yalniz({"IPTAL cevabı": 1})

    def test_chatbot_iptali_cevaba_dayanmali(self):
        self.calistir("UPDATE bildirimler SET yanit_niyeti = 'ONAY' WHERE bildirim_id = 2")
        self.yalniz({"CHATBOT ile": 1})

    def test_chatbot_iptali_erteleme_cevabiyla_da_olur(self):
        self.calistir("UPDATE bildirimler SET yanit_niyeti = 'ERTELEME' WHERE bildirim_id = 2")
        self.yalniz({})

    # --- yanlış alarm vermemesi gereken geçerli durumlar -----------------------

    def test_doktor_izne_cikinca_sistem_iptali_gecerli(self):
        self.calistir("INSERT INTO doktor_takvimi VALUES (2,'2026-03-05','08:00','16:00','12:00','13:00',15,28,0)",
                      "INSERT INTO hava_durumu VALUES ('2026-03-05','Eskişehir','GUNESLI',9)",
                      """INSERT INTO randevular (hasta_id, doktor_id, brans_id, hastane_id, olusturma_zamani,
                             randevu_zamani, durum, iptal_zamani, iptal_kanali)
                         VALUES (2, 2, 2, 2, '2026-02-20 10:00:00', '2026-03-05 09:00:00', 'IPTAL',
                                 '2026-03-01 08:00:00', 'SISTEM')""")
        self.yalniz({})
        # Aynı randevu hasta tarafından (WEB) iptal edildiyse o gün zaten hiç verilmemeliydi.
        self.calistir("UPDATE randevular SET iptal_kanali = 'WEB' WHERE randevu_zamani = '2026-03-05 09:00:00'")
        self.yalniz({"çalışmadığı güne": 1})

    def test_ogle_arasi_olmayan_ve_20_dakikalik_takvim(self):
        self.calistir("INSERT INTO doktor_takvimi VALUES (2,'2026-03-05','08:00','12:00',NULL,NULL,20,12,1)",
                      "INSERT INTO hava_durumu VALUES ('2026-03-05','Eskişehir','GUNESLI',9)")
        self.randevu("2026-03-05 11:40:00")
        self.yalniz({})

    def test_web_iptali_chatbot_cevabi_gerektirmez(self):
        self.calistir("UPDATE randevular SET iptal_kanali = 'WEB' WHERE randevu_id = 2",
                      "UPDATE bildirimler SET yanit_niyeti = 'ONAY' WHERE bildirim_id = 2")
        self.yalniz({})

    def test_yanitsiz_hatirlatma_ve_gelmeme_gecerli(self):
        self.calistir("UPDATE bildirimler SET yanit_metni = NULL, yanit_niyeti = NULL, yanit_zamani = NULL "
                      "WHERE bildirim_id = 4",
                      "UPDATE randevular SET durum = 'GELMEDI' WHERE randevu_id = 4")
        self.yalniz({})

    # --- son taramada eklenenler ---------------------------------------------

    def test_bos_randevu_teklifi_yedek_listede_olmayana(self):
        self.calistir("""INSERT INTO hastalar (hasta_id, ad, soyad, cinsiyet, dogum_tarihi, telefon, il, ilce,
                             iletisim_kanali, kayit_tarihi)
                         VALUES (3, 'Ece', 'Er', 'K', '1990-01-01', '05001112233', 'Eskişehir', 'Tepebaşı',
                                 'SMS', '2020-01-01')""")
        self.bildirim(2, 3, "BOS_RANDEVU_TEKLIFI", "2026-03-02 10:06:00")
        self.yalniz({"Boş randevu": 1})

    def test_yedek_randevu_olusmadan_atandi_sayilmis(self):
        self.calistir("UPDATE yedek_liste SET guncelleme_zamani = '2026-03-02 09:00:00' WHERE kayit_id = 1")
        self.yalniz({"Yedekten atanan": 1})

    def test_gelecekte_hasta_kaydi(self):
        self.calistir(f"UPDATE hastalar SET kayit_tarihi = '{GELECEK}' WHERE hasta_id = 2")
        # Hastanın geçmiş randevuları da artık kayıttan önce kalır.
        self.yalniz({"Şu andan sonraya": 1, "kaydolmadan": 2})

    def test_telefonsuz_hasta_yalniz_web_kanali(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.calistir("UPDATE hastalar SET telefon = NULL WHERE hasta_id = 1")
        self.calistir("UPDATE hastalar SET telefon = NULL, iletisim_kanali = 'WEB' WHERE hasta_id = 1")

    def test_chatbot_iptali_cevaptan_once_olamaz(self):
        self.calistir("UPDATE randevular SET iptal_zamani = '2026-03-02 10:04:00' WHERE randevu_id = 2")
        self.yalniz({"CHATBOT ile": 1})


if __name__ == "__main__":
    unittest.main()
