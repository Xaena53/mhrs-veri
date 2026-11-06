"""Sentetik veri üreticisinin testleri: üretilen veri şemaya ve tüm denetimlere uymalı.

Faker kurulu değilse (pip install -r requirements.txt) bu testler atlanır.
"""
import contextlib
import hashlib
import importlib.util
import io
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "schema"))
import kurulum  # noqa: E402

FAKER_VAR = importlib.util.find_spec("faker") is not None
ORNEK_CSV = KOK / "cikti" / "ornek_csv"


def uret(klasor, *argumanlar):
    return subprocess.run([sys.executable, str(KOK / "uretici" / "uret.py"), "--cikti", str(klasor), *map(str, argumanlar)],
                          capture_output=True, text=True, encoding="utf-8")


def yukle(klasor, db):
    with contextlib.redirect_stdout(io.StringIO()):
        con = kurulum.kur(db)
        kurulum.csv_yukle(con, klasor)
    return con


def ozet(klasor):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(klasor.glob("*.csv"))}


@unittest.skipUnless(FAKER_VAR, "Faker kurulu değil")
class UreticiTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gecici = Path(tempfile.mkdtemp())
        cls.addClassCleanup(shutil.rmtree, cls.gecici, ignore_errors=True)
        sonuc = uret(cls.gecici / "a", "--hasta", 600, "--ay", 4)
        assert sonuc.returncode == 0, sonuc.stdout + sonuc.stderr
        cls.con = yukle(cls.gecici / "a", cls.gecici / "a.db")
        cls.addClassCleanup(cls.con.close)

    def sayi(self, sql):
        return self.con.execute(sql).fetchone()[0]

    def test_tum_denetimlerden_gecer(self):
        bozuk = {ad: n for ad, sql in kurulum.DENETIMLER.items() if (n := self.con.execute(sql).fetchone()[0])}
        self.assertEqual(bozuk, {})
        self.assertEqual(self.con.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_tum_tablolar_dolu(self):
        for tablo in kurulum.TABLOLAR:
            self.assertGreater(self.sayi(f"SELECT COUNT(*) FROM {tablo}"), 0, tablo)

    def test_ayni_tohum_ayni_veri_farkli_tohum_farkli_veri(self):
        uret(self.gecici / "b", "--hasta", 600, "--ay", 4)
        uret(self.gecici / "c", "--hasta", 600, "--ay", 4, "--tohum", 7)
        self.assertEqual(ozet(self.gecici / "a"), ozet(self.gecici / "b"))
        self.assertNotEqual(ozet(self.gecici / "a"), ozet(self.gecici / "c"))

    def test_tum_durumlar_ve_akislar_var(self):
        # Ceyda'nın ilk sürümünde GELMEDI yoktu: 3. grup model eğitemezdi.
        for sutun, tablo, degerler in [
            ("durum", "randevular", {"BEKLIYOR", "GELDI", "GELMEDI", "IPTAL"}),
            ("katilim_teyidi", "randevular", {"BEKLENIYOR", "ONAYLADI", "REDDETTI", "SURE_ASIMI"}),
            ("kaynak", "randevular", {"NORMAL", "CHATBOT", "YEDEK_LISTE"}),
            ("tur", "bildirimler", {"HATIRLATMA", "IPTAL_ONAYI", "BOS_RANDEVU_TEKLIFI"}),
            ("aciliyet", "sikayetler", {"RUTIN", "ONCELIKLI", "ACIL"}),
            ("niyet", "yanit_ornekleri", {"ONAY", "IPTAL", "ERTELEME", "SORU", "BELIRSIZ"}),
        ]:
            bulunan = {r[0] for r in self.con.execute(f"SELECT DISTINCT {sutun} FROM {tablo}")}
            self.assertEqual(bulunan, degerler, sutun)

    def test_gelmeme_orani_makul(self):
        oran = self.sayi("SELECT AVG(hedef_gelmedi) FROM v_noshow_ozellikleri")
        self.assertTrue(0.08 < oran < 0.35, oran)

    def test_kucuk_veride_de_doluluk_anlamli(self):
        ort = self.sayi("SELECT AVG(doluluk_yuzde) FROM v_doluluk WHERE tarih <= (SELECT date(veri_ani) FROM veri_bilgisi)")
        self.assertGreater(ort, 35)

    def test_klasor_kendi_basina_yeterli(self):
        for ad in ("branslar", "tatiller"):
            self.assertTrue((self.gecici / "a" / f"{ad}.csv").exists(), ad)

    def test_kalip_no_egitim_test_ayrimi_icin_dolu(self):
        self.assertEqual(self.sayi("SELECT COUNT(*) FROM sikayetler WHERE kalip_no IS NULL"), 0)
        self.assertEqual(self.sayi("SELECT COUNT(*) FROM yanit_ornekleri WHERE kalip_no IS NULL"), 0)
        # Bir kalıbın tüm cümleleri aynı etiketi taşır.
        self.assertEqual(self.sayi("""SELECT COUNT(*) FROM (SELECT kalip_no FROM sikayetler GROUP BY kalip_no
                                     HAVING COUNT(DISTINCT aciliyet) > 1 OR COUNT(DISTINCT COALESCE(brans_id, 0)) > 1)"""), 0)
        self.assertEqual(self.sayi("""SELECT COUNT(*) FROM (SELECT kalip_no FROM yanit_ornekleri GROUP BY kalip_no
                                     HAVING COUNT(DISTINCT niyet) > 1)"""), 0)

    def test_randevular_mesai_icinde_ve_hafta_ici(self):
        self.assertEqual(self.sayi("SELECT COUNT(*) FROM randevular WHERE strftime('%w', randevu_zamani) IN ('0','6')"), 0)
        self.assertEqual(self.sayi("""SELECT COUNT(*) FROM randevular WHERE strftime('%H', randevu_zamani) < '08'
                                      OR strftime('%H', randevu_zamani) >= '16'"""), 0)

    def test_adlarda_unvan_yok(self):
        self.assertEqual(self.sayi("SELECT COUNT(*) FROM hastalar WHERE ad LIKE '%.%' OR soyad LIKE '%.%'"), 0)
        self.assertEqual(self.sayi("SELECT COUNT(*) FROM doktorlar WHERE ad LIKE '%.%' OR soyad LIKE '%.%'"), 0)

    def test_hasta_basina_randevu_makul(self):
        en_cok = self.sayi("SELECT MAX(n) FROM (SELECT COUNT(*) n FROM randevular GROUP BY hasta_id)")
        self.assertLessEqual(en_cok, 8)  # 4 ay × 1,5 + yedek/çifte payı

    def test_metinlerde_noktalama_ve_anlam_hatasi_yok(self):
        sikayetler = [r[0] for r in self.con.execute("SELECT metin FROM sikayetler")]
        yanitlar = [r[0] for r in self.con.execute("SELECT metin FROM yanit_ornekleri")]
        for metin in sikayetler + yanitlar:
            self.assertNotRegex(metin, r"[?!]\.|[?!],|\.\.$(?<!\.\.\.)", metin)
        for metin in sikayetler:
            # Cümle ortasında noktasız yeni cümle: "...arttı Doktora görünmek istiyorum."
            self.assertNotRegex(metin, r"[a-zçğıöşü] (Hangi|Randevu|Ne yapmalıyım|Doktora|Çok|Artık|Yardım)\b", metin)
            ilk_cumle = metin.split(".")[0]  # kapanış cümlesi ("Randevu almak istiyorum.") sayılmaz
            self.assertNotRegex(ilk_cumle, r"(?i)(saattir|haftadır|gündür|aylardır|dünden beri|zamandır|günlerde|zamanlarda)"
                                           r" .*(hamileyim|tahlili yaptırmak|randevu almak|düştüm)", metin)
            self.assertNotRegex(metin, r"(?i)^(az önce|şu an) .*(aniden|bir anda)", metin)

    def test_egitim_verisi_yeterli_ve_tekrarsiz(self):
        for sql, en_az in [("SELECT COUNT(*) n FROM sikayetler WHERE brans_id IS NOT NULL GROUP BY brans_id", 25),
                           ("SELECT COUNT(*) n FROM sikayetler WHERE aciliyet = 'ACIL'", 100),
                           ("SELECT COUNT(*) n FROM yanit_ornekleri GROUP BY niyet", 40)]:
            for (n,) in self.con.execute(sql):
                self.assertGreaterEqual(n, en_az, sql)
        self.assertEqual(self.sayi("SELECT COUNT(*) - COUNT(DISTINCT metin) FROM sikayetler"), 0)
        self.assertEqual(self.sayi("SELECT COUNT(*) - COUNT(DISTINCT metin) FROM yanit_ornekleri"), 0)

    def test_hatirlatma_mesajinda_saat_eki_dogru(self):
        spec = importlib.util.spec_from_file_location("uret", KOK / "uretici" / "uret.py")
        modul = importlib.util.module_from_spec(spec)
        sys.modules["uret"] = modul  # dataclass modülü sys.modules'te arar
        spec.loader.exec_module(modul)
        for saat, ek in [("09:00", "09:00'da"), ("14:00", "14:00'te"), ("10:30", "10:30'da"), ("11:15", "11:15'te"),
                         ("08:40", "08:40'ta"), ("13:20", "13:20'de"), ("15:45", "15:45'te")]:
            self.assertEqual(modul.saat_eki(saat), ek)

    def test_chatbot_gorunumleri_istenen_sutunlarda(self):
        cur = self.con.execute("SELECT * FROM v_chatbot_randevular LIMIT 1")
        self.assertEqual([d[0] for d in cur.description],
                         ["randevu_id", "hasta_id", "randevu_tarih_saat", "saat_dilimi", "hastane", "bolum", "doktor",
                          "randevu_durumu", "katilim_teyidi", "onay_zamani", "iptal_zamani_ve_nedeni"])
        cur = self.con.execute("SELECT * FROM v_chatbot_hastalar LIMIT 1")
        self.assertEqual([d[0] for d in cur.description][:5], ["hasta_id", "ad_soyad", "yas", "cinsiyet", "no_show_sayisi"])
        # no_show_sayisi rastgele değil, randevularla tutarlı.
        self.assertEqual(self.sayi("SELECT SUM(no_show_sayisi) FROM v_chatbot_hastalar"),
                         self.sayi("SELECT COUNT(*) FROM randevular WHERE durum = 'GELMEDI'"))

    def test_gorunumler_buyuk_veride_hizli(self):
        # v_hasta_profili ilk hâlinde 5000 hastada 100 sn sürüyordu; hasta başına tarama geri gelmesin.
        # Yavaşlık küçük veride görünmez, o yüzden bu test kendi büyük verisini üretir.
        sonuc = uret(self.gecici / "buyuk", "--hasta", 3000, "--ay", 12)
        self.assertEqual(sonuc.returncode, 0, sonuc.stdout + sonuc.stderr)
        con = yukle(self.gecici / "buyuk", self.gecici / "buyuk.db")
        self.addCleanup(con.close)
        for gorunum in ("v_hasta_profili", "v_chatbot_hastalar"):
            baslangic = time.perf_counter()
            con.execute(f"SELECT * FROM {gorunum}").fetchall()
            self.assertLess(time.perf_counter() - baslangic, 3, gorunum)

    def test_gecersiz_arguman(self):
        self.assertNotEqual(uret(self.gecici / "d", "--veri-ani", "2026-11-06").returncode, 0)
        self.assertNotEqual(uret(self.gecici / "d", "--hasta", 5).returncode, 0)

    def test_tatil_listesi_kapsamadigi_donem_acikca_reddedilir(self):
        sonuc = uret(self.gecici / "d", "--veri-ani", "2031-01-10 09:00:00")
        self.assertNotEqual(sonuc.returncode, 0)
        self.assertIn("tatiller.csv", sonuc.stdout + sonuc.stderr)


class OrnekCsvTesti(unittest.TestCase):
    """Repodaki hazır örnek veri her zaman temiz yüklenmeli (Faker gerekmez)."""

    @unittest.skipUnless(ORNEK_CSV.is_dir(), "cikti/ornek_csv yok")
    def test_ornek_csv_temiz(self):
        gecici = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, gecici, ignore_errors=True)
        con = yukle(ORNEK_CSV, gecici / "o.db")
        self.addCleanup(con.close)
        bozuk = {ad: n for ad, sql in kurulum.DENETIMLER.items() if (n := con.execute(sql).fetchone()[0])}
        self.assertEqual(bozuk, {})
        self.assertIsNotNone(con.execute("SELECT veri_ani FROM veri_bilgisi").fetchone())


if __name__ == "__main__":
    unittest.main()
