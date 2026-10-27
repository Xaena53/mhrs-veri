"""Şema ve kurulum.py testleri. Çalıştırma: python -m unittest discover tests -v

Her test örnek veriyi CSV'ye döker, bir kuralı bozar ve kurulum.py'nin bunu yakaladığını doğrular.
"""
import contextlib
import csv
import io
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "schema"))
import kurulum  # noqa: E402

GORUNUMLER = ["v_noshow_ozellikleri", "v_aylik_ozet", "v_doluluk", "v_bekleyen_yedek",
              "v_aylik_brans_ozet", "v_triyaj_veri", "v_bekleyen_randevular"]


def sessiz(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args)


class KurulumTesti(unittest.TestCase):
    def setUp(self):
        self.gecici = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.gecici, ignore_errors=True)
        con = sessiz(kurulum.kur, self.gecici / "ornek.db")
        con.executescript(kurulum.ORNEK.read_text(encoding="utf-8"))
        self.csv = self.gecici / "csv"
        sessiz(kurulum.disa_aktar, con, self.csv)
        con.close()

    def yukle(self, klasor=None):
        con = sessiz(kurulum.kur, self.gecici / "test.db")
        self.addCleanup(con.close)
        sessiz(kurulum.csv_yukle, con, klasor or self.csv)
        return con

    def degistir(self, tablo, eski, yeni):
        dosya = self.csv / f"{tablo}.csv"
        metin = dosya.read_text(encoding="utf-8")
        self.assertIn(eski, metin, f"test verisi değişmiş: {tablo}.csv içinde {eski!r} yok")
        dosya.write_text(metin.replace(eski, yeni, 1), encoding="utf-8")

    def reddedilmeli(self, *parcalar):
        with self.assertRaises(kurulum.YuklemeHatasi) as h:
            self.yukle()
        for p in parcalar:
            self.assertIn(p, str(h.exception))

    # --- doğru veri ---------------------------------------------------------

    def test_ornek_veri_temiz(self):
        con = self.yukle()
        self.assertTrue(sessiz(kurulum.denetle, con))

    def test_sema_surumu(self):
        con = self.yukle()
        self.assertEqual(kurulum.sema_surumu(con), "v1.0")

    def test_csv_gidis_donus_satir_sayilari_ayni(self):
        con = self.yukle()
        kaynak = sqlite3.connect(self.gecici / "ornek.db")
        self.addCleanup(kaynak.close)
        for tablo in kurulum.TABLOLAR:
            sorgu = f"SELECT COUNT(*) FROM {tablo}"
            self.assertEqual(con.execute(sorgu).fetchone(), kaynak.execute(sorgu).fetchone(), tablo)

    def test_gorunumler_calisiyor(self):
        con = self.yukle()
        for v in GORUNUMLER:
            con.execute(f"SELECT * FROM {v}").fetchall()
        # Senaryo: Ahmet ilk randevuya gelmedi, sonrakine geldi; ikincide geçmiş gelmeme sayısı 1.
        satirlar = con.execute("""SELECT randevu_id, onceki_gelmeme_sayisi, hedef_gelmedi
                                  FROM v_noshow_ozellikleri WHERE hasta_id = 1 ORDER BY randevu_id""").fetchall()
        self.assertEqual(satirlar, [(1, 0, 1), (4, 1, 0)])
        self.assertEqual(con.execute("SELECT brans_adi FROM v_triyaj_veri WHERE sikayet_id = 1").fetchone(),
                         ("Kardiyoloji",))

    def test_referans_listeler_yuklenir(self):
        bos = self.gecici / "bos"
        bos.mkdir()
        con = self.yukle(bos)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM branslar").fetchone()[0], 16)
        self.assertGreater(con.execute("SELECT COUNT(*) FROM tatiller").fetchone()[0], 0)
        self.assertTrue(sessiz(kurulum.denetle, con))

    def test_referans_branslar_ornek_veriyle_uyumlu(self):
        # ornek_veri.sql'deki ilk 4 branş, referans listesindeki ilk 4 branşla aynı olmalı.
        ornek = sqlite3.connect(self.gecici / "ornek.db")
        self.addCleanup(ornek.close)
        bos = self.gecici / "bos"
        bos.mkdir()
        ref = self.yukle(bos)
        sorgu = "SELECT * FROM branslar WHERE brans_id <= 4 ORDER BY brans_id"
        self.assertEqual(ornek.execute(sorgu).fetchall(), ref.execute(sorgu).fetchall())

    def test_turkce_excel_csv_kabul_edilir(self):
        for dosya in self.csv.glob("*.csv"):
            okunan = list(csv.reader(dosya.read_text(encoding="utf-8").splitlines()))
            cikti = io.StringIO()
            yazici = csv.writer(cikti, delimiter=";")
            for s in okunan:
                yazici.writerow([h.replace(".", ",") if h.replace(".", "", 1).isdigit() else h for h in s])
            # write_text Windows'ta satır sonlarını ikiler (satır arası boş satır); bu da kabul edilmeli.
            dosya.write_text(cikti.getvalue(), encoding="utf-8-sig")
        con = self.yukle()
        self.assertEqual(con.execute("SELECT typeof(mesafe_km), mesafe_km FROM randevular WHERE randevu_id = 1")
                         .fetchone(), ("real", 4.2))

    # --- satır düzeyinde reddedilmesi gerekenler ---------------------------

    def test_yanlis_tarih_bicimi(self):
        self.degistir("hastalar", "1981-03-12", "1981-3-12")
        self.reddedilmeli("hastalar.csv satır 2", "CHECK")

    def test_sutun_adi_yazim_hatasi(self):
        self.degistir("hastalar", "dogum_tarihi", "dogumtarihi")
        self.reddedilmeli("bilinmeyen sütun", "dogumtarihi")

    def test_telefonun_bastaki_sifiri_silinmis(self):
        self.degistir("hastalar", "05001234567", "5001234567")
        self.reddedilmeli("hastalar.csv satır 2")

    def test_utf8_olmayan_dosya(self):
        dosya = self.csv / "hastalar.csv"
        dosya.write_bytes(dosya.read_text(encoding="utf-8").encode("cp1254"))
        self.reddedilmeli("UTF-8 değil")

    def test_hatali_yukleme_hic_satir_birakmaz(self):
        self.degistir("randevular", "2026-03-04 14:00:00", "2026-03-04 14:00")
        con = sessiz(kurulum.kur, self.gecici / "test.db")
        self.addCleanup(con.close)
        with self.assertRaises(kurulum.YuklemeHatasi):
            sessiz(kurulum.csv_yukle, con, self.csv)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM hastalar").fetchone()[0], 0)

    def test_buyuk_dosyada_sonradan_gelen_utf8_disi_karakter(self):
        # Okuma tamponundan (8 KB) sonra gelen bozuk bayt eskiden programı çökertiyordu.
        satirlar = ["ornek_id,metin,niyet"] + [f"{i},Evet geliyorum,ONAY" for i in range(10, 3000)]
        satirlar.append("5000,Gelemeyeceğim,IPTAL")
        (self.csv / "yanit_ornekleri.csv").write_bytes(("\n".join(satirlar) + "\n").encode("cp1254"))
        self.reddedilmeli("yanit_ornekleri.csv UTF-8 değil")

    def test_sayi_sutununa_metin(self):
        # SQLite tip zorlamaz; '4.2 km' typeof CHECK'i olmadan REAL sütuna metin olarak girerdi.
        self.degistir("randevular", ",4.2\n", ",4.2 km\n")
        self.reddedilmeli("randevular.csv satır 2", "typeof(mesafe_km)")

    def test_tam_sayi_sutununa_ondalik(self):
        self.degistir("doktor_takvimi", ",15,28,1", ",15.5,28,1")
        self.reddedilmeli("doktor_takvimi.csv satır 2", "typeof(slot_dk)")

    def test_pandas_tam_sayilari_ondalikli_yazsa_da_kabul(self):
        # pandas boş hücreli tam sayı sütununu '1.0' yazar; INTEGER sütunda 1'e dönüşür.
        self.degistir("randevular", "\n1,1,2,2,2,1,", "\n1,1.0,2.0,2,2,1.0,")
        con = self.yukle()
        self.assertEqual(con.execute("SELECT typeof(hasta_id), typeof(sikayet_id) FROM randevular "
                                     "WHERE randevu_id = 1").fetchone(), ("integer", "integer"))
        self.assertTrue(sessiz(kurulum.denetle, con))

    def test_tatil_tarihi_bos_olamaz(self):
        self.degistir("tatiller", "\n2026-03-19,", "\n,")
        self.reddedilmeli("NOT NULL constraint failed: tatiller.tarih")

    def test_tekrarlanan_sutun(self):
        self.degistir("yanit_ornekleri", "ornek_id,metin,niyet", "ornek_id,metin,metin")
        self.reddedilmeli("tekrarlanan sütun ['metin']")

    def test_bos_dosya(self):
        (self.csv / "tatiller.csv").write_text("", encoding="utf-8")
        self.reddedilmeli("tatiller.csv boş")

    def test_eksik_birincil_anahtar_sutunu(self):
        # INTEGER olmayan birincil anahtar (hava_durumu: tarih + il) CSV'de zorunludur.
        dosya = self.csv / "hava_durumu.csv"
        satirlar = [s.split(",", 1)[1] for s in dosya.read_text(encoding="utf-8").splitlines()]
        dosya.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        self.reddedilmeli("eksik zorunlu sütun ['tarih']")

    def test_ornek_veriyle_birlikte_referans_yuklenmez(self):
        con = sessiz(kurulum.kur, self.gecici / "test.db")
        self.addCleanup(con.close)
        con.executescript(kurulum.ORNEK.read_text(encoding="utf-8"))
        bos = self.gecici / "bos"
        bos.mkdir()
        sessiz(kurulum.csv_yukle, con, bos)  # eskiden referans branşlar örnek branşlarla çakışıyordu
        self.assertEqual(con.execute("SELECT COUNT(*) FROM branslar").fetchone()[0], 4)

    def test_satir_numarasi_cok_satirli_hucreden_sonra_dogru(self):
        # Tırnak içinde satır atlayan hücre satır sayımını kaydırmamalı.
        self.degistir("sikayetler", "Sol kolum uyuştu, şiddetli", "Sol kolum uyuştu,\nşiddetli")
        self.degistir("yanit_ornekleri", "\n3,", "\n3x,")
        self.reddedilmeli("yanit_ornekleri.csv satır 4")

    # --- yüklenen ama denetimde yakalanması gerekenler ---------------------

    def denetimde_yalniz(self, beklenen):
        """Denetim yalnızca `beklenen` kurallarda (ad → aykırı satır sayısı) hata vermeli."""
        con = self.yukle()
        bulunan = {ad: n for ad, sql in kurulum.DENETIMLER.items() if (n := con.execute(sql).fetchone()[0])}
        self.assertEqual(bulunan, beklenen)
        self.assertFalse(sessiz(kurulum.denetle, con))

    def test_ogle_arasina_randevu(self):
        self.degistir("randevular", "2026-03-04 14:00:00", "2026-03-04 12:15:00")
        self.degistir("bildirimler", "2026-03-03 14:00:00", "2026-03-03 12:15:00")
        self.denetimde_yalniz({"Mesai dışı / öğle arası / slot ızgarasına oturmayan saat": 1})

    def test_slot_izgarasina_oturmayan_saat(self):
        self.degistir("randevular", "2026-03-04 14:00:00", "2026-03-04 14:07:00")
        self.degistir("bildirimler", "2026-03-03 14:00:00", "2026-03-03 14:07:00")
        self.denetimde_yalniz({"Mesai dışı / öğle arası / slot ızgarasına oturmayan saat": 1})

    def test_cinsiyet_kisiti(self):
        # Kardiyolojiyi yalnız kadınlara açınca Ahmet'in (E) 3 randevusu kurala aykırı düşer.
        self.degistir("branslar", "Kardiyoloji,15,18,,", "Kardiyoloji,15,18,,K")
        self.denetimde_yalniz({"Cinsiyet kısıtına uymayan randevu": 3})

    def test_on_sekizinci_dogum_gunu_siniri(self):
        # 2008-03-03 doğumlu: 2 Mart'ta 17 yaşında (aykırı), 3 Mart'ta tam 18 (uygun).
        self.degistir("hastalar", "1981-03-12", "2008-03-03")
        self.denetimde_yalniz({"Branşın yaş alt sınırının altında hasta": 1})

    def test_yedek_kaydi_olmayan_yedek_randevu(self):
        self.degistir("randevular", "NORMAL,1,4.2\n", "YEDEK_LISTE,1,4.2\n")
        self.denetimde_yalniz({"Kaynağı YEDEK_LISTE ama hiçbir yedek kaydına atanmamış randevu": 1})

    def test_hatirlatma_bayragi_bildirimle_uyusmuyor(self):
        self.degistir("randevular", "YEDEK_LISTE,0,1.1", "YEDEK_LISTE,1,1.1")
        self.denetimde_yalniz({"hatirlatma_gonderildi bayrağı ile HATIRLATMA bildirimi uyuşmuyor": 1})

    def test_kur_sqlite_olmayan_dosyayi_silmez(self):
        hedef = self.gecici / "schema.sql"
        hedef.write_text("CREATE TABLE x (a);", encoding="utf-8")
        with self.assertRaises(kurulum.YuklemeHatasi):
            sessiz(kurulum.kur, hedef)
        self.assertTrue(hedef.exists())


if __name__ == "__main__":
    unittest.main()
