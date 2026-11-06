"""MHRS sentetik veri üreticisi: şemadaki tüm tablolar için tutarlı CSV'ler yazar.

Kullanım:
    python uretici/uret.py                                  # 5000 hasta, 12 ay → cikti/csv
    python uretici/uret.py --hasta 200 --ay 3 --cikti cikti/ornek_csv
    python schema/kurulum.py --csv cikti/csv                # yükle ve denetle

Aynı --tohum, --veri-ani ve Faker sürümü (requirements.txt) her bilgisayarda aynı veriyi üretir. Veri --veri-ani anına göre yazılır:
öncesi geçmiş (GELDI/GELMEDI), sonrası gelecek (BEKLIYOR). branslar ve tatiller schema/referans'tan gelir.

Gelmeme olasılığına gömülü desenler (3. grubun bulması gereken ilişkiler), bkz. gelmeme_olasiligi():
geçmiş gelmemeler, kişisel eğilim, yağmur/kar, uzun bekleme, genç yaş, mesafe, tatil yakınlığı,
hatırlatma ve hastanın onayı.
"""
import argparse
import csv
import datetime as dt
import itertools
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metinler as M  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
REFERANS = KOK / "schema" / "referans"
BICIM = "%Y-%m-%d %H:%M:%S"
IL = "Eskişehir"
VARSAYILAN_ANI = "2026-11-06 09:00:00"
GELECEK_GUN = 14            # veri anından sonra kaç günlük randevu defteri açık
YIL_RANDEVU = 6             # hasta başına yıllık ortalama randevu hedefi
YEDEK_ORANI = 0.35          # yedek listeye yazılan hasta oranı
YEDEK_YENI_ORANI = 0.25     # bu kayıtların son bir aya düşen payı (bugün bekleyen liste dolu olsun)
HASTA_AYLIK_SINIR = 1.5     # hasta başına ay başına en fazla randevu; 1 yaşında yılda 91 randevu olmasın
AYNI_BRANS_ARA_GUN = 10     # aynı hasta aynı branşa bu kadar gün içinde yeniden randevu almaz
YEDEK_OMUR_GUN = 30         # yedek kaydının geçerlilik süresi

HASTANELER = [  # ad, tür, ilçe, enlem, boylam, branş kapsamı
    ("Odunpazarı Devlet Hastanesi (sentetik)", "DEVLET", "Odunpazarı", 39.7667, 30.5256, "temel"),
    ("Tepebaşı Eğitim ve Araştırma Hastanesi (sentetik)", "EGITIM_ARASTIRMA", "Tepebaşı", 39.7845, 30.5004, "tum"),
    ("Sivrihisar İlçe Hastanesi (sentetik)", "ILCE", "Sivrihisar", 39.4515, 31.5375, "ilce"),
]
TEMEL_BRANSLAR = ["Dahiliye", "Çocuk Sağlığı ve Hastalıkları", "Kadın Hastalıkları ve Doğum", "Genel Cerrahi",
                  "Ortopedi ve Travmatoloji", "Göz Hastalıkları"]
ILCE_BRANSLARI = ["Dahiliye", "Çocuk Sağlığı ve Hastalıkları", "Kadın Hastalıkları ve Doğum"]
ILCELER = [  # ilçe, enlem, boylam, ağırlık
    ("Odunpazarı", 39.7667, 30.5256, 46), ("Tepebaşı", 39.7845, 30.5004, 42), ("Sivrihisar", 39.4515, 31.5375, 4),
    ("Alpu", 39.7687, 30.9580, 2), ("Seyitgazi", 39.4441, 30.6945, 2), ("Çifteler", 39.3829, 31.0394, 2),
    ("İnönü", 39.8167, 30.1500, 2),
]
UNVANLAR = {"Uzm. Dr.": 60, "Doç. Dr.": 18, "Prof. Dr.": 12, "Op. Dr.": 10}
KRONIK = ["Hipertansiyon", "Diyabet", "Astım", "KOAH", "Kalp Yetmezliği", "Tiroid", "Migren"]
KANALLAR = {"WHATSAPP": 58, "SMS": 25, "TELEGRAM": 9, "WEB": 8}


def zaman(z: dt.datetime) -> str:
    return z.strftime(BICIM)


def tam_yas(dogum: dt.date, gun: dt.date) -> int:
    return gun.year - dogum.year - ((gun.month, gun.day) < (dogum.month, dogum.day))


def mesafe_km(e1, b1, e2, b2) -> float:
    # Kuş uçuşu mesafe, yol için 1,3 ile çarpılır.
    p1, p2 = math.radians(e1), math.radians(e2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b2 - b1) / 2) ** 2
    return round(2 * 6371 * math.asin(math.sqrt(a)) * 1.3, 1)


def buyuk_harfle(metin: str) -> str:
    bas = {"i": "İ", "ı": "I"}.get(metin[0], metin[0].upper())
    return bas + metin[1:]


def cumle_kur(bas: str, metin: str, son: str) -> str:
    """'son günlerde ' + 'sesim kısık' + ' Ne yapmalıyım?' → 'Son günlerde sesim kısık. Ne yapmalıyım?'"""
    return buyuk_harfle(bas + metin) + ("." if son else "") + son


def saat_eki(saat: str) -> str:
    """'14:00' → "14:00'te"; ek, saatin okunuşundaki son sayıya uyar."""
    h, m = saat.split(":")
    ekler = {"00": None, "10": "da", "15": "te", "20": "de", "30": "da", "40": "ta", "45": "te", "50": "de"}
    saat_ekleri = {"08": "de", "09": "da", "10": "da", "11": "de", "12": "de", "13": "te", "14": "te", "15": "te",
                   "16": "da"}
    return f"{saat}'{ekler.get(m) or saat_ekleri.get(h, 'de')}"


@dataclass
class Hasta:
    id: int
    ad: str
    soyad: str
    cinsiyet: str
    dogum: dt.date
    telefon: str | None
    ilce: str
    enlem: float
    boylam: float
    kronik: str | None
    kanal: str
    kayit: dt.date
    egilim: float           # kişisel gelmeme eğilimi (logit), gözlenmeyen özellik
    aktiflik: float
    gelmeme: int = 0        # o ana kadarki gelmeme sayısı


@dataclass
class Doktor:
    id: int
    brans_id: int
    hastane_id: int
    gun: int
    aktif: int = 1
    son_gun: dt.date | None = None


@dataclass
class Yedek:
    id: int
    hasta: Hasta
    brans_id: int
    hastane_id: int | None
    sikayet_id: int | None
    puan: int
    tercih: str
    kayit: dt.datetime
    durum: str = "BEKLIYOR"
    atanan: int | None = None
    guncelleme: dt.datetime | None = None


@dataclass
class Uretici:
    tohum: int
    veri_ani: dt.datetime
    hasta_sayisi: int
    ay: int
    r: random.Random = field(init=False)
    randevular: list = field(default_factory=list)
    bildirimler: list = field(default_factory=list)
    dolu: set = field(default_factory=set)
    sayac: dict = field(default_factory=dict)
    son_brans: dict = field(default_factory=dict)

    def __post_init__(self):
        self.r = random.Random(self.tohum)
        self.fake = Faker("tr_TR")
        self.fake.seed_instance(self.tohum)
        self.bas = self.veri_ani.date() - dt.timedelta(days=round(self.ay * 30.44))
        self.bit = self.veri_ani.date() + dt.timedelta(days=GELECEK_GUN)
        self.branslar = self.csv_oku("branslar.csv")
        self.tatiller = {s["tarih"]: s["tur"] for s in self.csv_oku("tatiller.csv")}
        yillar = {t[:4] for t in self.tatiller}
        for y in {str(self.bas.year), str(self.bit.year)} - yillar:
            sys.exit(f"HATA: schema/referans/tatiller.csv {y} yılını kapsamıyor; önce o yılın tatillerini ekleyin.")
        self.brans_ad = {int(b["brans_id"]): b["brans_adi"] for b in self.branslar}
        self.brans_no = {v: k for k, v in self.brans_ad.items()}
        self.kisit = {int(b["brans_id"]): (int(b["yas_min"]) if b["yas_min"] else None,
                                           int(b["yas_max"]) if b["yas_max"] else None,
                                           b["cinsiyet_kisiti"] or None) for b in self.branslar}
        self.slot_dk = {int(b["brans_id"]): int(b["ortalama_muayene_dk"]) for b in self.branslar}

    @staticmethod
    def csv_oku(ad):
        with (REFERANS / ad).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def isim(self, uretec) -> str:
        # Faker bazı adlara 'Dr.' gibi unvan ve kısaltma katabiliyor; yalnız düz ad kabul edilir.
        while True:
            ad = uretec()
            if "." not in ad:
                return ad

    def uygun(self, h: Hasta, brans_id: int, gun: dt.date) -> bool:
        ymin, ymax, c = self.kisit[brans_id]
        yas = tam_yas(h.dogum, gun)
        return (ymin is None or yas >= ymin) and (ymax is None or yas <= ymax) and (c is None or h.cinsiyet == c)

    # --- sabit tablolar --------------------------------------------------------

    def hastaneler_uret(self):
        self.hastaneler = [(i, ad, tur, IL, ilce, e, b) for i, (ad, tur, ilce, e, b, _) in enumerate(HASTANELER, 1)]
        self.hastane_konum = {h[0]: (h[5], h[6]) for h in self.hastaneler}

    def doktorlar_uret(self):
        kapsamlar = []
        for i, (*_, kapsam) in enumerate(HASTANELER, 1):
            adlar = {"temel": TEMEL_BRANSLAR, "ilce": ILCE_BRANSLARI, "tum": list(self.brans_no)}[kapsam]
            kapsamlar += [(i, self.brans_no[a]) for a in adlar]
        # Her kapsam için bir doktor; hasta sayısı büyüdükçe en yoğun branşlara ek doktor.
        hedef = max(len(kapsamlar), self.hasta_sayisi // 200)
        yogun = [k for k in kapsamlar if self.brans_ad[k[1]] in TEMEL_BRANSLAR]
        ek = [yogun[i % len(yogun)] for i in range(hedef - len(kapsamlar))]
        self.doktorlar, self.doktor_satirlari = [], []
        for no, (hastane, brans) in enumerate(kapsamlar + ek, 1):
            erkek = self.r.random() < 0.5
            ad = self.isim(self.fake.first_name_male if erkek else self.fake.first_name_female)
            unvan = self.r.choices(list(UNVANLAR), list(UNVANLAR.values()))[0]
            self.doktorlar.append(Doktor(no, brans, hastane, gun=no % 5))
            self.doktor_satirlari.append([no, ad, self.isim(self.fake.last_name), unvan, brans, hastane, 1])
        # Kapsamı başka doktorla karşılanan bir doktor emekli olur: takvimi bir ay önce biter.
        sayac = {}
        for d in self.doktorlar:
            sayac[(d.hastane_id, d.brans_id)] = sayac.get((d.hastane_id, d.brans_id), 0) + 1
        for d, satir in zip(reversed(self.doktorlar), reversed(self.doktor_satirlari)):
            if sayac[(d.hastane_id, d.brans_id)] > 1:
                d.aktif, satir[6] = 0, 0
                d.son_gun = self.veri_ani.date() - dt.timedelta(days=30)
                break

    def hastalar_uret(self):
        self.hastalar, telefonlar = [], self.r.sample(range(10_000_000), self.hasta_sayisi)
        ilce_agirlik = [i[3] for i in ILCELER]
        for no in range(1, self.hasta_sayisi + 1):
            cinsiyet = "K" if self.r.random() < 0.52 else "E"
            ad = self.isim(self.fake.first_name_female if cinsiyet == "K" else self.fake.first_name_male)
            yas = self.r.choices([self.r.randint(0, 17), self.r.randint(18, 35), self.r.randint(36, 64),
                                  self.r.randint(65, 92)], [20, 28, 36, 16])[0]
            dogum = self.veri_ani.date() - dt.timedelta(days=yas * 365 + self.r.randint(0, 364))
            ilce, e, b, _ = self.r.choices(ILCELER, ilce_agirlik)[0]
            kanal = self.r.choices(list(KANALLAR), list(KANALLAR.values()))[0]
            telefon = f"0500{telefonlar[no - 1]:07d}"
            if kanal == "WEB" and self.r.random() < 0.3:
                telefon = None
            kronik = None
            if self.r.random() < min(0.75, max(yas - 25, 0) / 70):
                kronik = ",".join(self.r.sample(KRONIK, self.r.choice([1, 1, 2])))
            # Çoğu hasta veri döneminden önce kayıtlıdır; %12'si dönem içinde katılır.
            en_erken = max(dogum, dt.date(2019, 1, 1))
            if self.r.random() < 0.12:
                kayit = self.bas + dt.timedelta(days=self.r.randint(0, (self.veri_ani.date() - self.bas).days))
            else:
                kayit = en_erken + dt.timedelta(days=self.r.randint(0, max((self.bas - en_erken).days, 0)))
            kayit = max(kayit, dogum)
            self.hastalar.append(Hasta(no, ad, self.isim(self.fake.last_name), cinsiyet, dogum, telefon, ilce,
                                       round(e + self.r.uniform(-0.03, 0.03), 4),
                                       round(b + self.r.uniform(-0.03, 0.03), 4), kronik, kanal, kayit,
                                       egilim=self.r.gauss(0, 0.7), aktiflik=self.r.lognormvariate(0, 0.7)))

    def hava_uret(self):
        self.hava, self.hava_durum = [], {}
        gun = self.bas - dt.timedelta(days=1)
        while gun <= self.bit + dt.timedelta(days=1):
            mevsim = math.cos(2 * math.pi * (gun.timetuple().tm_yday - 15) / 365)  # 1 = ocak, -1 = temmuz
            sicaklik = round(11 - 12 * mevsim + self.r.gauss(0, 3.5), 1)
            if sicaklik < 1 and self.r.random() < 0.45:
                durum = "KARLI"
            elif self.r.random() < 0.20 + 0.12 * mevsim:
                durum = "YAGMURLU"
            else:
                durum = self.r.choices(["GUNESLI", "BULUTLU"], [55 - 25 * mevsim, 45 + 25 * mevsim])[0]
            self.hava.append([gun.isoformat(), IL, durum, sicaklik])
            self.hava_durum[gun.isoformat()] = durum
            gun += dt.timedelta(days=1)

    def takvim_uret(self):
        """Doktor başına haftada poliklinik_gun gün; resmî tatil/bayramda çalışılmaz, arifede 13:00'e kadar."""
        self.takvim, self.gunler = [], {}
        hafta = ((self.bit - self.bas).days + 1) / 7
        kapasite = sum(self.slot_sayisi(d.brans_id) for d in self.doktorlar) * hafta
        hedef = self.hasta_sayisi * YIL_RANDEVU * self.ay / 12
        poliklinik_gun = min(5, max(1, round(hedef / 0.72 / kapasite)))
        self.doluluk = min(0.88, hedef / (kapasite * poliklinik_gun))
        gun = self.bas
        while gun <= self.bit:
            tatil = self.tatiller.get(gun.isoformat())
            if gun.weekday() < 5 and tatil not in ("RESMI", "BAYRAM"):
                for d in self.doktorlar:
                    if (gun.weekday() - d.gun) % 5 >= poliklinik_gun or (d.son_gun and gun > d.son_gun):
                        continue
                    bitis, ogle = ("13:00", (None, None)) if tatil == "ARIFE" else ("16:00", ("12:00", "13:00"))
                    slot = self.slot_dk[d.brans_id]
                    dakika = 300 if tatil == "ARIFE" else 420
                    calisiyor = 0 if self.r.random() < 0.015 else 1
                    self.takvim.append([d.id, gun.isoformat(), "08:00", bitis, ogle[0], ogle[1], slot,
                                        dakika // slot, calisiyor])
                    self.gunler.setdefault(gun, []).append((d, calisiyor, bitis, ogle[0], slot))
            gun += dt.timedelta(days=1)

    def slot_sayisi(self, brans_id):
        return 420 // self.slot_dk[brans_id]

    def sikayetler_uret(self):
        self.sikayetler, self.brans_sikayet, gorulen = [], {}, set()
        no = itertools.count(1)
        for brans, kaliplar in M.SIKAYETLER.items():
            brans_id = self.brans_no[brans]
            for metin, aciliyet, alternatif in kaliplar:
                sureli = not any(k in metin for k in M.SURESIZ_KALIPLAR)
                baslar = [""] + (M.ZAMAN_IFADELERI if sureli else [])
                sonlar = [""] + M.KAPANISLAR + (M.SURELI_KAPANISLAR if sureli else [])
                if "istiyorum" in metin:  # "...istiyorum. Randevu almak istiyorum." tekrarı olmasın
                    sonlar = ["", " Hangi bölüme gitmeliyim?", " Ne yapmalıyım?"]
                for bas in baslar:
                    for son in sonlar:
                        cumle = cumle_kur(bas, metin, son)
                        # Yalın cümle hep girer; çeşitlemelerin bir kısmı alınır.
                        if cumle in gorulen or (bas + son and self.r.random() > 0.6):
                            continue
                        gorulen.add(cumle)
                        s = next(no)
                        self.sikayetler.append([s, cumle, brans_id, self.brans_no.get(alternatif), aciliyet, "SABLON"])
                        self.brans_sikayet.setdefault(brans_id, []).append((s, aciliyet))
        for metin in M.ACIL_SIKAYETLER:
            if any(k in metin for k in M.ACIL_SURESIZ_KALIPLAR):
                baslar = [""]
            elif any(k in metin for k in M.ACIL_OLAY_KALIPLARI):
                baslar = ["", "az önce "]
            else:
                baslar = ["", "şu an ", "az önce başladı, "]
            for bas in baslar:
                for son in [""] + M.ACIL_KAPANISLAR:
                    cumle = cumle_kur(bas, metin, son)
                    if cumle not in gorulen:
                        gorulen.add(cumle)
                        self.sikayetler.append([next(no), cumle, None, None, "ACIL", "SABLON"])

    def yanitlar_uret(self):
        no = itertools.count(1)
        # Hasta aynı şeyi farklı yazar: küçük harf, selam, noktalama. Niyet sınıflandırması için çeşitlilik.
        self.yanit_ornekleri, gorulen = [], set()
        for niyet, liste in M.YANITLAR.items():
            for metin in liste:
                kucuk = metin.replace("I", "ı").replace("İ", "i").lower()
                noktali = metin[-1] in ".?!"
                for cesit in (metin, kucuk, metin if noktali else f"{metin}.", f"Merhaba, {kucuk}",
                              f"{metin} Kolay gelsin" if noktali else f"{metin}, kolay gelsin",
                              kucuk.replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u")
                              .replace("ö", "o").replace("ç", "c")):
                    if cesit not in gorulen:
                        gorulen.add(cesit)
                        self.yanit_ornekleri.append([next(no), cesit, niyet])

    def yedek_uret(self):
        self.yedekler, self.yedek_brans, ciftler = [], {}, set()
        no = itertools.count(1)
        toplam_sn = int((self.veri_ani - dt.datetime.combine(self.bas, dt.time(8))).total_seconds())
        son_ay_sn = min(toplam_sn, YEDEK_OMUR_GUN * 86400)
        for h in self.r.sample(self.hastalar, int(self.hasta_sayisi * YEDEK_ORANI)):
            if self.r.random() < YEDEK_YENI_ORANI:
                kayit = self.veri_ani - dt.timedelta(seconds=self.r.randint(0, son_ay_sn))
            else:
                kayit = dt.datetime.combine(self.bas, dt.time(8)) + dt.timedelta(seconds=self.r.randint(0, toplam_sn))
            adaylar = [b for b in self.brans_ad if self.uygun(h, b, kayit.date())]
            brans = self.r.choice(adaylar)
            if kayit.date() < h.kayit or (h.id, brans) in ciftler:
                continue
            ciftler.add((h.id, brans))
            sikayet = self.r.choice(self.brans_sikayet[brans])
            puan = self.r.randint(3, 5) if sikayet[1] == "ONCELIKLI" else self.r.randint(1, 3)
            hastane = self.r.choice([None, None, self.en_yakin_hastane(h, brans)])
            y = Yedek(next(no), h, brans, hastane, sikayet[0], puan,
                      self.r.choice(["SABAH", "OGLEDEN_SONRA", "FARK_ETMEZ"]), kayit)
            self.yedekler.append(y)
            self.yedek_brans.setdefault(brans, []).append(y)

    def en_yakin_hastane(self, h, brans):
        secenek = {d.hastane_id for d in self.doktorlar if d.brans_id == brans}
        return min(secenek, key=lambda i: mesafe_km(h.enlem, h.boylam, *self.hastane_konum[i]))

    # --- randevu akışı -----------------------------------------------------------

    def hasta_havuzlari(self):
        """(hastane, branş) → aday hastalar ve birikimli ağırlıklar; yakındaki ve branşa uygun yaştaki hasta seçilir."""
        self.havuz = {}
        for hastane, brans in {(d.hastane_id, d.brans_id) for d in self.doktorlar}:
            e, b = self.hastane_konum[hastane]
            adaylar, agirlik = [], []
            ymin, ymax, c = self.kisit[brans]
            for h in self.hastalar:
                yas = tam_yas(h.dogum, self.veri_ani.date())
                if (c and h.cinsiyet != c) or (ymin is not None and yas < ymin) or (ymax is not None and yas > ymax + 1):
                    continue
                yas_etkisi = 1 + yas / 45 if self.brans_ad[brans] in ("Kardiyoloji", "Nöroloji", "Dahiliye") else 1
                adaylar.append(h)
                agirlik.append(h.aktiflik * yas_etkisi / (1 + mesafe_km(h.enlem, h.boylam, e, b) / 6))
            self.havuz[(hastane, brans)] = (adaylar, list(itertools.accumulate(agirlik)))

    def gelmeme_olasiligi(self, h, d, t, bekleme, km, hatirlatma, teyit):
        gun = t.date()
        yas = tam_yas(h.dogum, gun)
        x = -2.15 + h.egilim
        x += 0.45 * min(h.gelmeme, 3)
        x += {"YAGMURLU": 0.45, "KARLI": 0.85}.get(self.hava_durum.get(gun.isoformat()), 0)
        x += 0.9 * min(bekleme, 45) / 45
        x += 0.45 if 18 <= yas <= 35 else (-0.2 if yas >= 65 else 0)
        x += 0.7 * min(km, 40) / 40
        yakin = {(gun + dt.timedelta(days=k)).isoformat() for k in (-1, 1)}
        x += 0.45 if yakin & set(self.tatiller) else 0
        x += -0.5 if hatirlatma else 0
        x += {"ONAYLADI": -0.7}.get(teyit, 0.25 if hatirlatma else 0)
        return 1 / (1 + math.exp(-x))

    def bildirim(self, randevu_id, h, tur, mesaj, gonderim, yanit=None, niyet=None, yanit_ani=None):
        self.bildirimler.append([len(self.bildirimler) + 1, randevu_id, h.id, tur, h.kanal, mesaj, zaman(gonderim),
                                 yanit, niyet, zaman(yanit_ani) if yanit_ani else None])

    def randevu_yaz(self, h, d, t, olusturma, kaynak, sikayet, cifte=0, yedek_doldur=True, izinli=False):
        """Bir randevunun tüm yaşam döngüsü: hatırlatma, teyit, iptal, sonuç. Veri anından sonrası yaşanmamıştır."""
        rid = len(self.randevular) + 1
        an, r = self.veri_ani, self.r
        km = mesafe_km(h.enlem, h.boylam, *self.hastane_konum[d.hastane_id])
        bekleme = (t.date() - olusturma.date()).days
        saat, brans = t.strftime("%H:%M"), self.brans_ad[d.brans_id]
        satir = dict(id=rid, durum="BEKLIYOR", iptal=None, kanal=None, neden=None, teyit="BEKLENIYOR", onay=None, hat=0)
        self.randevular.append(satir)
        satir.update(h=h.id, d=d.id, b=d.brans_id, hs=d.hastane_id, s=sikayet, olusturma=olusturma, t=t,
                     kaynak=kaynak, km=km, cifte=cifte)
        self.dolu.add((h.id, t))
        self.sayac[h.id] = self.sayac.get(h.id, 0) + 1
        self.son_brans[(h.id, d.brans_id)] = t.date()

        if izinli:  # doktor izinli: sistem iptal eder
            ip = t - dt.timedelta(days=r.randint(1, 3))
            ip = min(max(ip, olusturma), an)
            satir.update(durum="IPTAL", iptal=ip, kanal="SISTEM", neden="DOKTOR_IZNI")
            return satir

        hat_ani = t - dt.timedelta(hours=24)
        web_iptal = None
        if r.random() < 0.06 and t - dt.timedelta(hours=1) > olusturma:
            aday = olusturma + (t - dt.timedelta(hours=1) - olusturma) * r.random()
            aday = aday.replace(microsecond=0)
            if aday <= an:
                web_iptal = aday
        gonderildi = olusturma <= hat_ani <= an and r.random() < 0.92 and (web_iptal is None or hat_ani < web_iptal)
        iptal_ani = None
        if gonderildi:
            satir["hat"] = 1
            mesaj = f"Yarın saat {saat_eki(saat)} {brans} randevunuz var. Gelecek misiniz? (Evet / İptal Et)"
            niyet = r.choices(["ONAY", "IPTAL", "ERTELEME", "SORU", "BELIRSIZ", None],
                              [52, 7, 3, 3, 4, 31])[0] if web_iptal is None else None
            yanit_ani = hat_ani + dt.timedelta(seconds=r.randint(40, 7000))
            if niyet and yanit_ani > an:
                niyet = None
            if niyet is None:
                self.bildirim(rid, h, "HATIRLATMA", mesaj, hat_ani)
                sure = hat_ani + dt.timedelta(hours=2)
                # Chatbot grubunun 2 saat kuralı: cevapsız randevuların bir kısmı onay süresi dolunca iptal edilir.
                if web_iptal is None and sure <= an and r.random() < 0.08:
                    iptal_ani = sure
                    satir.update(durum="IPTAL", iptal=sure, kanal="SISTEM", neden="ONAY_SURESI_DOLDU", teyit="SURE_ASIMI")
            else:
                self.bildirim(rid, h, "HATIRLATMA", mesaj, hat_ani, r.choice(M.YANITLAR[niyet]), niyet, yanit_ani)
                if niyet == "ONAY":
                    satir.update(teyit="ONAYLADI", onay=yanit_ani)
                elif niyet in ("IPTAL", "ERTELEME"):
                    iptal_ani = yanit_ani
                    satir.update(durum="IPTAL", iptal=yanit_ani, kanal="CHATBOT", teyit="REDDETTI",
                                 neden="HASTA_ISTEGI" if niyet == "IPTAL" else "ERTELEME")
                    self.bildirim(rid, h, "IPTAL_ONAYI", f"{brans} randevunuz iptal edildi.",
                                  yanit_ani + dt.timedelta(seconds=5))
        if web_iptal is not None:
            iptal_ani = web_iptal
            satir.update(durum="IPTAL", iptal=web_iptal, kanal=r.choice(["WEB", "WEB", "TELEFON"]),
                         neden="HASTA_ISTEGI", teyit="REDDETTI")

        if satir["durum"] == "IPTAL":
            if yedek_doldur:
                self.yedekten_doldur(h, d, t, iptal_ani, sikayet)
            return satir
        if t <= an:
            p = self.gelmeme_olasiligi(h, d, t, bekleme, km, satir["hat"], satir["teyit"])
            if r.random() < p:
                satir["durum"] = "GELMEDI"
                h.gelmeme += 1
            else:
                satir["durum"] = "GELDI"
        return satir

    def yedekten_doldur(self, iptal_eden, d, t, iptal_ani, sikayet):
        """Kılavuzdaki akış: aciliyet ve konuma göre en uygun hastalara teklif, ilk onaylayana randevu."""
        r, an = self.r, self.veri_ani
        if r.random() > 0.75 or t - iptal_ani < dt.timedelta(minutes=30):
            return
        konum = self.hastane_konum[d.hastane_id]
        adaylar = [y for y in self.yedek_brans.get(d.brans_id, [])
                   if y.durum == "BEKLIYOR" and y.kayit <= iptal_ani
                   and iptal_ani < y.kayit + dt.timedelta(days=YEDEK_OMUR_GUN)
                   and y.hastane_id in (None, d.hastane_id) and y.hasta is not iptal_eden
                   and (y.hasta.id, t) not in self.dolu and self.uygun(y.hasta, d.brans_id, t.date())]
        adaylar.sort(key=lambda y: (-y.puan, mesafe_km(y.hasta.enlem, y.hasta.boylam, *konum), y.kayit))
        gonderim = iptal_ani + dt.timedelta(seconds=30)
        rid = len(self.randevular)  # iptal edilen randevu
        saat, brans = t.strftime("%H:%M"), self.brans_ad[d.brans_id]
        mesaj = f"{t.strftime('%d.%m.%Y')} {saat} için {brans} branşında boş randevu oluştu, onaylıyor musunuz?"
        for y in adaylar[:3]:
            if gonderim > an:
                return
            yanit = gonderim + dt.timedelta(seconds=r.randint(30, 1500))
            if yanit < t and yanit <= an and r.random() < 0.55:
                self.bildirim(rid, y.hasta, "BOS_RANDEVU_TEKLIFI", mesaj, gonderim, r.choice(M.YANITLAR["ONAY"]), "ONAY", yanit)
                y.durum, y.guncelleme = "ATANDI", yanit
                yeni = self.randevu_yaz(y.hasta, d, t, yanit, "YEDEK_LISTE", y.sikayet_id, yedek_doldur=False)
                y.atanan = yeni["id"]
                return
            if yanit <= an and r.random() < 0.4:
                self.bildirim(rid, y.hasta, "BOS_RANDEVU_TEKLIFI", mesaj, gonderim, r.choice(M.BOS_TEKLIF_RED), "IPTAL", yanit)
            else:
                self.bildirim(rid, y.hasta, "BOS_RANDEVU_TEKLIFI", mesaj, gonderim)

    def hasta_sec(self, d, t):
        adaylar, birikimli = self.havuz[(d.hastane_id, d.brans_id)]
        if not adaylar:
            return None
        for _ in range(8):
            h = self.r.choices(adaylar, cum_weights=birikimli)[0]
            son = self.son_brans.get((h.id, d.brans_id))
            if (self.uygun(h, d.brans_id, t.date()) and (h.id, t) not in self.dolu
                    and self.sayac.get(h.id, 0) < self.hasta_siniri
                    and (son is None or (t.date() - son).days >= AYNI_BRANS_ARA_GUN)):
                return h
        return None

    def olusturma_sec(self, h, t):
        """Randevunun alındığı an: bekleme süresi çoğunlukla kısa; veri anından ve hasta kaydından önce olmalı."""
        r, an = self.r, self.veri_ani
        en_az = max((t.date() - an.date()).days, 1)
        bekleme = max(en_az, min(60, int(r.expovariate(1 / 11)) + 1))
        o = dt.datetime.combine(t.date() - dt.timedelta(days=bekleme), dt.time(r.randint(7, 22), r.randint(0, 59), r.randint(0, 59)))
        if o > an:
            o = an - dt.timedelta(minutes=r.randint(1, 600))
        return None if o.date() < h.kayit else o

    def randevular_uret(self):
        r, an = self.r, self.veri_ani
        self.hasta_siniri = max(3, round(HASTA_AYLIK_SINIR * self.ay))
        for gun in sorted(self.gunler):
            ileri = (gun - an.date()).days
            # Gelecekteki günlerin defteri tarih uzaklaştıkça boşalır.
            azalma = 1 if ileri <= 0 else max(0.08, 1 - ileri / (GELECEK_GUN + 2))
            haftanin_etkisi = {0: 1.1, 4: 0.92}.get(gun.weekday(), 1)
            for d, calisiyor, bitis, ogle, slot in self.gunler[gun]:
                oran = self.doluluk * azalma * haftanin_etkisi * r.uniform(0.85, 1.15)
                if not calisiyor:
                    oran *= 0.4
                t = dt.datetime.combine(gun, dt.time(8))
                son = dt.datetime.combine(gun, dt.time(int(bitis[:2])))
                while t < son:
                    if ogle and dt.time(12) <= t.time() < dt.time(13):
                        t += dt.timedelta(minutes=slot)
                        continue
                    if r.random() < oran:
                        self.slot_doldur(d, t, calisiyor)
                    t += dt.timedelta(minutes=slot)

    def slot_doldur(self, d, t, calisiyor):
        r = self.r
        h = self.hasta_sec(d, t)
        o = h and self.olusturma_sec(h, t)
        if not o:
            return
        sik = self.brans_sikayet.get(d.brans_id)
        sikayet = r.choice(sik)[0] if sik and r.random() < 0.7 else None
        kaynak = "CHATBOT" if r.random() < 0.18 else "NORMAL"
        self.randevu_yaz(h, d, t, o, kaynak, sikayet, izinli=not calisiyor)
        # 3. grubun overbooking'i: geçmişi riskli hastanın slotuna ek randevu yazılır.
        if calisiyor and t <= self.veri_ani and h.gelmeme >= 2 and r.random() < 0.3:
            ek = self.hasta_sec(d, t)
            ek_o = ek and self.olusturma_sec(ek, t)
            if ek_o:
                self.randevu_yaz(ek, d, t, ek_o, "NORMAL", None, cifte=1, yedek_doldur=False)

    def yedek_sonlandir(self):
        for y in self.yedekler:
            if y.durum != "BEKLIYOR":
                continue
            bitis = y.kayit + dt.timedelta(days=YEDEK_OMUR_GUN)
            vazgecti = y.kayit + dt.timedelta(days=self.r.randint(1, YEDEK_OMUR_GUN - 1))
            if self.r.random() < 0.12 and vazgecti <= self.veri_ani:
                y.durum, y.guncelleme = "VAZGECTI", vazgecti
            elif bitis <= self.veri_ani:
                y.durum, y.guncelleme = "SURESI_DOLDU", bitis

    # --- çıktı -------------------------------------------------------------------

    def yaz(self, klasor: Path):
        klasor.mkdir(parents=True, exist_ok=True)

        def dosya(ad, basliklar, satirlar):
            with (klasor / f"{ad}.csv").open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(basliklar)
                w.writerows(satirlar)
            print(f"  {ad:<16}{len(satirlar):>8} satır")

        z = lambda v: zaman(v) if v else None  # noqa: E731
        dosya("veri_bilgisi", ["tek", "veri_ani", "tohum"], [[1, zaman(self.veri_ani), self.tohum]])
        dosya("hastaneler", ["hastane_id", "hastane_adi", "tur", "il", "ilce", "enlem", "boylam"], self.hastaneler)
        dosya("doktorlar", ["doktor_id", "ad", "soyad", "unvan", "brans_id", "hastane_id", "aktif"], self.doktor_satirlari)
        dosya("hastalar", ["hasta_id", "ad", "soyad", "cinsiyet", "dogum_tarihi", "telefon", "il", "ilce", "enlem", "boylam",
                           "kronik_hastalik", "iletisim_kanali", "kayit_tarihi"],
              [[h.id, h.ad, h.soyad, h.cinsiyet, h.dogum.isoformat(), h.telefon, IL, h.ilce, h.enlem, h.boylam, h.kronik,
                h.kanal, h.kayit.isoformat()] for h in self.hastalar])
        dosya("hava_durumu", ["tarih", "il", "durum", "sicaklik_c"], self.hava)
        dosya("doktor_takvimi", ["doktor_id", "tarih", "baslangic_saat", "bitis_saat", "ogle_baslangic", "ogle_bitis",
                                 "slot_dk", "toplam_slot", "calisiyor"], self.takvim)
        dosya("sikayetler", ["sikayet_id", "metin", "brans_id", "alternatif_brans_id", "aciliyet", "kaynak"], self.sikayetler)
        dosya("yanit_ornekleri", ["ornek_id", "metin", "niyet"], self.yanit_ornekleri)
        dosya("randevular", ["randevu_id", "hasta_id", "doktor_id", "brans_id", "hastane_id", "sikayet_id", "olusturma_zamani",
                             "randevu_zamani", "durum", "iptal_zamani", "iptal_kanali", "kaynak", "hatirlatma_gonderildi",
                             "mesafe_km", "katilim_teyidi", "onay_zamani", "iptal_nedeni", "cifte_randevu"],
              [[s["id"], s["h"], s["d"], s["b"], s["hs"], s["s"], zaman(s["olusturma"]), zaman(s["t"]), s["durum"], z(s["iptal"]),
                s["kanal"], s["kaynak"], s["hat"], s["km"], s["teyit"], z(s["onay"]), s["neden"], s["cifte"]]
               for s in self.randevular])
        dosya("yedek_liste", ["kayit_id", "hasta_id", "brans_id", "hastane_id", "sikayet_id", "aciliyet_puani", "tercih_zaman",
                              "kayit_zamani", "durum", "atanan_randevu_id", "guncelleme_zamani"],
              [[y.id, y.hasta.id, y.brans_id, y.hastane_id, y.sikayet_id, y.puan, y.tercih, zaman(y.kayit), y.durum, y.atanan,
                z(y.guncelleme)] for y in self.yedekler])
        dosya("bildirimler", ["bildirim_id", "randevu_id", "hasta_id", "tur", "kanal", "mesaj_metni", "gonderim_zamani",
                              "yanit_metni", "yanit_niyeti", "yanit_zamani"], self.bildirimler)

    def calistir(self, klasor: Path):
        self.hastaneler_uret()
        self.doktorlar_uret()
        self.hastalar_uret()
        self.hava_uret()
        self.takvim_uret()
        self.sikayetler_uret()
        self.yanitlar_uret()
        self.yedek_uret()
        self.hasta_havuzlari()
        self.randevular_uret()
        self.yedek_sonlandir()
        self.yaz(klasor)


def main():
    for akis in (sys.stdout, sys.stderr):  # Windows konsolunda Türkçe hata mesajları bozulmasın
        if hasattr(akis, "reconfigure"):
            akis.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hasta", type=int, default=5000)
    p.add_argument("--ay", type=int, default=12, help="veri anından geriye kaç aylık geçmiş")
    p.add_argument("--tohum", type=int, default=42)
    p.add_argument("--veri-ani", default=VARSAYILAN_ANI, help="verinin 'şu an'ı, YYYY-MM-DD HH:MM:SS")
    p.add_argument("--cikti", type=Path, default=KOK / "cikti" / "csv")
    a = p.parse_args()
    try:
        veri_ani = dt.datetime.strptime(a.veri_ani, BICIM)
    except ValueError:
        p.error(f"--veri-ani biçimi YYYY-MM-DD HH:MM:SS olmalı: {a.veri_ani}")
    if a.hasta < 50 or a.ay < 1:
        p.error("--hasta en az 50, --ay en az 1 olmalı")
    print(f"Üretiliyor: {a.hasta} hasta, {a.ay} ay, tohum {a.tohum}, veri anı {a.veri_ani}")
    Uretici(a.tohum, veri_ani, a.hasta, a.ay).calistir(a.cikti)
    print(f"Yazıldı: {a.cikti}\nDenetlemek için: python schema/kurulum.py --csv {a.cikti}")


if __name__ == "__main__":
    main()
