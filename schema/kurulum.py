"""MHRS sentetik veritabanını kurar, CSV'leri yükler ve bütünlüğü denetler.

Kullanım:
    python schema/kurulum.py                  # boş veritabanı: cikti/mhrs.db
    python schema/kurulum.py --ornek          # + elle yazılmış test verisi
    python schema/kurulum.py --csv cikti/csv  # + 2. ekibin ürettiği CSV'ler
    python schema/kurulum.py --disa-aktar cikti/csv_export   # tabloları CSV'ye yaz

CSV sözleşmesi: her tablo için <tablo_adi>.csv, ilk satır sütun adları (schema.sql ile aynı),
UTF-8, boş hücre = NULL. Yükleme sırası yabancı anahtarlara göre aşağıdaki TABLOLAR listesidir.
"""
import argparse
import csv
import sqlite3
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
SEMA = KOK / "schema" / "schema.sql"
ORNEK = KOK / "schema" / "ornek_veri.sql"

TABLOLAR = [
    "branslar", "hastaneler", "doktorlar", "hastalar", "hava_durumu", "tatiller",
    "doktor_takvimi", "sikayetler", "yanit_ornekleri", "randevular", "yedek_liste", "bildirimler",
]


def kur(db_yolu: Path) -> sqlite3.Connection:
    db_yolu.parent.mkdir(parents=True, exist_ok=True)
    if db_yolu.exists():
        db_yolu.unlink()
    con = sqlite3.connect(db_yolu)
    con.executescript(SEMA.read_text(encoding="utf-8"))
    return con


def csv_yukle(con: sqlite3.Connection, klasor: Path) -> None:
    for tablo in TABLOLAR:
        dosya = klasor / f"{tablo}.csv"
        if not dosya.exists():
            print(f"  - {tablo}: CSV yok, atlandı")
            continue
        with dosya.open(encoding="utf-8-sig", newline="") as f:
            okuyucu = csv.reader(f)
            sutunlar = next(okuyucu)
            yer = ",".join("?" * len(sutunlar))
            satirlar = ([h if h != "" else None for h in s] for s in okuyucu)
            con.executemany(f"INSERT INTO {tablo} ({','.join(sutunlar)}) VALUES ({yer})", satirlar)
        print(f"  + {tablo}: {con.execute(f'SELECT COUNT(*) FROM {tablo}').fetchone()[0]} satır")
    con.commit()


def disa_aktar(con: sqlite3.Connection, klasor: Path) -> None:
    klasor.mkdir(parents=True, exist_ok=True)
    for tablo in TABLOLAR:
        cur = con.execute(f"SELECT * FROM {tablo}")
        with (klasor / f"{tablo}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            w.writerows(cur)
    print(f"CSV'ler yazıldı: {klasor}")


# Şemanın CHECK kısıtlarıyla yakalanamayan, tablolar arası mantık kuralları.
DENETIMLER = {
    "Çocuk branşında 18 yaş üstü hasta":
        """SELECT COUNT(*) FROM randevular r JOIN hastalar h USING(hasta_id) JOIN branslar b USING(brans_id)
           WHERE b.yas_max IS NOT NULL
             AND (julianday(r.randevu_zamani) - julianday(h.dogum_tarihi)) / 365.25 >= b.yas_max + 1""",
    "Yaş alt sınırının altında hasta":
        """SELECT COUNT(*) FROM randevular r JOIN hastalar h USING(hasta_id) JOIN branslar b USING(brans_id)
           WHERE b.yas_min IS NOT NULL
             AND (julianday(r.randevu_zamani) - julianday(h.dogum_tarihi)) / 365.25 < b.yas_min""",
    "Cinsiyet kısıtına uymayan randevu":
        """SELECT COUNT(*) FROM randevular r JOIN hastalar h USING(hasta_id) JOIN branslar b USING(brans_id)
           WHERE b.cinsiyet_kisiti IS NOT NULL AND h.cinsiyet <> b.cinsiyet_kisiti""",
    "Randevu branşı doktorun branşından farklı":
        """SELECT COUNT(*) FROM randevular r JOIN doktorlar d USING(doktor_id)
           WHERE r.brans_id <> d.brans_id OR r.hastane_id <> d.hastane_id""",
    "Doktorun çalışmadığı güne randevu":
        """SELECT COUNT(*) FROM randevular r
           WHERE EXISTS (SELECT 1 FROM doktor_takvimi dt) AND NOT EXISTS (
               SELECT 1 FROM doktor_takvimi dt WHERE dt.doktor_id = r.doktor_id
                 AND dt.tarih = date(r.randevu_zamani) AND dt.calisiyor = 1)""",
    "Yedek listeden atanan randevu kaynağı YEDEK_LISTE değil":
        """SELECT COUNT(*) FROM yedek_liste y JOIN randevular r ON r.randevu_id = y.atanan_randevu_id
           WHERE r.kaynak <> 'YEDEK_LISTE' OR r.hasta_id <> y.hasta_id OR r.brans_id <> y.brans_id""",
    "Bildirim hastası randevu hastasıyla uyuşmuyor (hatırlatmada)":
        """SELECT COUNT(*) FROM bildirimler b JOIN randevular r USING(randevu_id)
           WHERE b.tur = 'HATIRLATMA' AND b.hasta_id <> r.hasta_id""",
    "Gelecekteki randevu için GELDI/GELMEDI sonucu":
        """SELECT COUNT(*) FROM randevular
           WHERE durum IN ('GELDI','GELMEDI') AND randevu_zamani > datetime('now','localtime')""",
}


def denetle(con: sqlite3.Connection) -> bool:
    print("\nBütünlük denetimi:")
    hatali = con.execute("PRAGMA foreign_key_check").fetchall()
    print(f"  {'OK ' if not hatali else 'HATA'} yabancı anahtarlar ({len(hatali)} sorun)")
    temiz = not hatali
    for ad, sql in DENETIMLER.items():
        n = con.execute(sql).fetchone()[0]
        temiz &= n == 0
        print(f"  {'OK ' if n == 0 else 'HATA'} {ad}: {n}")
    print("\nSatır sayıları:")
    for tablo in TABLOLAR:
        print(f"  {tablo:<16} {con.execute(f'SELECT COUNT(*) FROM {tablo}').fetchone()[0]:>8}")
    return temiz


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=KOK / "cikti" / "mhrs.db")
    p.add_argument("--ornek", action="store_true", help="elle yazılmış test verisini yükle")
    p.add_argument("--csv", type=Path, help="CSV klasörünü yükle")
    p.add_argument("--disa-aktar", type=Path, help="tabloları bu klasöre CSV olarak yaz")
    a = p.parse_args()

    con = kur(a.db)
    print(f"Veritabanı kuruldu: {a.db}")
    try:
        if a.ornek:
            con.executescript(ORNEK.read_text(encoding="utf-8"))
        if a.csv:
            csv_yukle(con, a.csv)
    except sqlite3.IntegrityError as e:
        print(f"\nYÜKLEME REDDEDİLDİ (şema kuralı ihlali): {e}")
        return 1
    temiz = denetle(con)
    if a.disa_aktar:
        disa_aktar(con, a.disa_aktar)
    con.close()
    return 0 if temiz else 1


if __name__ == "__main__":
    sys.exit(main())
