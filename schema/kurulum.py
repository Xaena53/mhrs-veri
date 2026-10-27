"""MHRS sentetik veritabanını kurar, CSV'leri yükler ve bütünlüğü denetler.

Kullanım:
    python schema/kurulum.py                  # boş veritabanı: cikti/mhrs.db
    python schema/kurulum.py --ornek          # + elle yazılmış test verisi
    python schema/kurulum.py --csv cikti/csv  # + 2. ekibin ürettiği CSV'ler
    python schema/kurulum.py --ornek --disa-aktar cikti/ornek_csv   # tabloları CSV'ye yaz

CSV sözleşmesi: her tablo için <tablo_adi>.csv, ilk satır sütun adları (schema.sql ile aynı),
UTF-8, boş hücre = NULL. Yükleme sırası yabancı anahtarlara göre aşağıdaki TABLOLAR listesidir.
Klasörde branslar.csv / tatiller.csv yoksa schema/referans/ altındaki sabit listeler kullanılır.
Hatalı satır varsa hiçbir şey yüklenmez; dosya, satır numarası ve ihlal edilen kural yazdırılır.
"""
import argparse
import csv
import io
import re
import sqlite3
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
SEMA = KOK / "schema" / "schema.sql"
ORNEK = KOK / "schema" / "ornek_veri.sql"
REFERANS = KOK / "schema" / "referans"
EN_FAZLA_HATA = 10
ONDALIK_VIRGUL = re.compile(r"^(-?\d+),(\d+)$")

TABLOLAR = [
    "branslar", "hastaneler", "doktorlar", "hastalar", "hava_durumu", "tatiller",
    "doktor_takvimi", "sikayetler", "yanit_ornekleri", "randevular", "yedek_liste", "bildirimler",
]


class YuklemeHatasi(Exception):
    pass


def kur(db_yolu: Path) -> sqlite3.Connection:
    if db_yolu.is_dir():
        raise YuklemeHatasi(f"{db_yolu} bir klasör; --db'ye dosya yolu verin (ör. cikti/mhrs.db).")
    db_yolu.parent.mkdir(parents=True, exist_ok=True)
    if db_yolu.exists():
        # Yanlışlıkla --db schema/schema.sql verilirse kaynak dosya silinmesin: yalnızca SQLite dosyası silinir.
        with db_yolu.open("rb") as f:
            if db_yolu.stat().st_size and f.read(16) != b"SQLite format 3\x00":
                raise YuklemeHatasi(f"{db_yolu} bir SQLite veritabanı değil; üzerine yazılmadı.")
        try:
            db_yolu.unlink()
        except PermissionError:
            raise YuklemeHatasi(f"{db_yolu} başka bir programda açık (DB Browser vb.); kapatıp tekrar deneyin.")
        print(f"Eski veritabanı silindi: {db_yolu}")
    # Yarıda kalmış eski bir çalıştırmanın günlük dosyası kalırsa SQLite onu yeni veritabanına uygulamaya çalışır.
    for ek in ("-journal", "-wal", "-shm"):
        artik = db_yolu.with_name(db_yolu.name + ek)
        if artik.exists():
            artik.unlink()
    con = sqlite3.connect(db_yolu)
    con.executescript(SEMA.read_text(encoding="utf-8"))
    return con


def sema_surumu(con: sqlite3.Connection) -> str:
    v = con.execute("PRAGMA user_version").fetchone()[0]
    return f"v{v // 100}.{v % 100}"


def sutun_bilgisi(con: sqlite3.Connection, tablo: str) -> dict:
    """ad -> CSV'de bulunması zorunlu mu. INTEGER PRIMARY KEY verilmezse SQLite numara atar."""
    satirlar = con.execute(f"PRAGMA table_info({tablo})").fetchall()
    tek_pk = sum(r[5] > 0 for r in satirlar) == 1
    return {r[1]: (bool(r[3]) or r[5] > 0) and r[4] is None
                  and not (tek_pk and r[5] and r[2].upper() == "INTEGER")
            for r in satirlar}


def csv_oku(dosya: Path) -> tuple[list[str], list[tuple[int, list[str]]], str]:
    """(başlık, [(satır_no, hücreler)], ayırıcı). Hata varsa YuklemeHatasi."""
    try:
        # Tamamı okunur (Türkçe karakter dosyanın sonunda olabilir); satır sonları csv modülüne olduğu gibi gider.
        metin = dosya.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise YuklemeHatasi(f"{dosya.name} UTF-8 değil (bayt {e.start}). Excel'de 'CSV UTF-8 (virgülle ayrılmış)' "
                            f"olarak kaydedin ya da pandas ile encoding='utf-8' yazın.")
    ilk_satir = metin.split("\n", 1)[0]
    if not ilk_satir.strip():
        raise YuklemeHatasi(f"{dosya.name} boş ya da ilk satırı (sütun adları) boş.")
    # Türkçe Excel CSV'yi noktalı virgülle kaydeder; ikisini de kabul et.
    ayirici = ";" if ilk_satir.count(";") > ilk_satir.count(",") else ","
    okuyucu = csv.reader(io.StringIO(metin, newline=""), delimiter=ayirici)
    try:
        baslik = [s.strip() for s in next(okuyucu)]
        # line_num: tırnak içinde satır atlayan hücrelerde de doğru satır numarası
        satirlar = [(okuyucu.line_num, satir) for satir in okuyucu]
    except csv.Error as e:
        raise YuklemeHatasi(f"{dosya.name} satır {okuyucu.line_num}: CSV okunamadı ({e})")
    return baslik, satirlar, ayirici


def csv_yukle(con: sqlite3.Connection, klasor: Path) -> None:
    if not klasor.is_dir():
        raise YuklemeHatasi(f"CSV klasörü bulunamadı: {klasor}")
    con.execute("BEGIN")
    try:
        hatalar = _csv_tablolari_yukle(con, klasor)
    except BaseException:
        con.rollback()
        raise
    if hatalar:
        con.rollback()
        raise YuklemeHatasi(f"Şema kuralına aykırı satırlar (ilk {EN_FAZLA_HATA}):\n    " + "\n    ".join(hatalar)
                            + "\n  İlk hatadan başlayın: sonraki FOREIGN KEY hataları çoğunlukla ondan kaynaklanır.")
    con.commit()


def _csv_tablolari_yukle(con: sqlite3.Connection, klasor: Path) -> list[str]:
    # Dosya adı da sütun adı kadar önemli: 'hasta.csv' sessizce atlanırsa tablo boş kalır.
    # Büyük/küçük harf Windows'ta ve Linux'ta aynı davransın diye adlar küçük harfle eşlenir.
    dosyalar = {p.name.lower(): p for p in klasor.iterdir() if p.is_file() and p.suffix.lower() == ".csv"}
    tanimsiz = sorted(dosyalar[ad].name for ad in dosyalar if ad[:-4] not in TABLOLAR)
    if tanimsiz:
        raise YuklemeHatasi(f"Tanınmayan CSV dosyası: {tanimsiz}. Dosya adı tablo adıyla aynı olmalı: "
                            + ", ".join(f"{t}.csv" for t in TABLOLAR))
    hatalar = []
    for tablo in TABLOLAR:
        dosya, etiket = dosyalar.get(f"{tablo}.csv"), ""
        if dosya is None:
            # Sabit listeler (branşlar, tatiller): tablo boşsa referans dosyası kullanılır.
            # --ornek ile birlikte kullanılınca örnek verinin üzerine yazılmaz.
            bos = con.execute(f"SELECT NOT EXISTS (SELECT 1 FROM {tablo})").fetchone()[0]
            if bos and (REFERANS / f"{tablo}.csv").exists():
                dosya, etiket = REFERANS / f"{tablo}.csv", " (schema/referans)"
            else:
                print(f"  - {tablo}: CSV yok, atlandı")
                continue
        bilgi = sutun_bilgisi(con, tablo)
        sutunlar, satirlar, ayirici = csv_oku(dosya)
        tekrar = sorted({s for s in sutunlar if sutunlar.count(s) > 1})
        bilinmeyen = [s for s in sutunlar if s not in bilgi]
        eksik = [ad for ad, zorunlu in bilgi.items() if zorunlu and ad not in sutunlar]
        if tekrar or bilinmeyen or eksik:
            raise YuklemeHatasi(f"{dosya.name}: tekrarlanan sütun {tekrar or '-'}, bilinmeyen sütun {bilinmeyen or '-'}, "
                                f"eksik zorunlu sütun {eksik or '-'}")
        sql = f"INSERT INTO {tablo} ({','.join(sutunlar)}) VALUES ({','.join('?' * len(sutunlar))})"
        tipler = {r[1]: r[2].upper() for r in con.execute(f"PRAGMA table_info({tablo})")}
        sayisal = {i for i, s in enumerate(sutunlar) if tipler[s] in ("INTEGER", "REAL")}
        for satir_no, satir in satirlar:
            # Windows'ta newline="" verilmeden yazılan CSV'lerde her satır arasında boş satır olur.
            if not any(h.strip() for h in satir):
                continue
            if len(satir) != len(sutunlar):
                hatalar.append(f"{dosya.name} satır {satir_no}: {len(satir)} hücre var, {len(sutunlar)} bekleniyordu")
            else:
                degerler = [h if h != "" else None for h in satir]
                if ayirici == ";":  # Türkçe Excel ondalığı: '4,2' → '4.2'; yalnızca sayı sütunlarında
                    degerler = [ONDALIK_VIRGUL.sub(r"\1.\2", h) if h and i in sayisal else h
                                for i, h in enumerate(degerler)]
                try:
                    con.execute(sql, degerler)
                except sqlite3.DatabaseError as e:
                    hatalar.append(f"{dosya.name} satır {satir_no}: {e}")
            if len(hatalar) >= EN_FAZLA_HATA:
                return hatalar
        print(f"  + {tablo}: {con.execute(f'SELECT COUNT(*) FROM {tablo}').fetchone()[0]} satır{etiket}")
    return hatalar


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
# Her sorgu kurala UYMAYAN satır sayısını döndürür; 0 = temiz.
DENETIMLER = {
    # Yaş sınırları doğum gününe göre tam hesaplanır (365.25'e bölmek doğum günü civarında 1 gün kayar).
    # Branş kısıtları hem randevuya hem yedek listeye uygulanır (yedekte yaş, listeye giriş anına göre).
    "Branşın yaş üst sınırını aşan hasta (randevu / yedek liste)":
        """SELECT COUNT(*) FROM (
             SELECT r.hasta_id, r.brans_id, r.randevu_zamani AS an FROM randevular r
             UNION ALL SELECT y.hasta_id, y.brans_id, y.kayit_zamani FROM yedek_liste y
           ) k JOIN hastalar h USING(hasta_id) JOIN branslar b USING(brans_id)
           WHERE b.yas_max IS NOT NULL
             AND date(k.an) >= date(h.dogum_tarihi, '+' || (b.yas_max + 1) || ' years')""",
    "Branşın yaş alt sınırının altında hasta (randevu / yedek liste)":
        """SELECT COUNT(*) FROM (
             SELECT r.hasta_id, r.brans_id, r.randevu_zamani AS an FROM randevular r
             UNION ALL SELECT y.hasta_id, y.brans_id, y.kayit_zamani FROM yedek_liste y
           ) k JOIN hastalar h USING(hasta_id) JOIN branslar b USING(brans_id)
           WHERE b.yas_min IS NOT NULL
             AND date(k.an) < date(h.dogum_tarihi, '+' || b.yas_min || ' years')""",
    "Cinsiyet kısıtına uymayan hasta (randevu / yedek liste)":
        """SELECT COUNT(*) FROM (
             SELECT hasta_id, brans_id FROM randevular UNION ALL SELECT hasta_id, brans_id FROM yedek_liste
           ) k JOIN hastalar h USING(hasta_id) JOIN branslar b USING(brans_id)
           WHERE b.cinsiyet_kisiti IS NOT NULL AND h.cinsiyet <> b.cinsiyet_kisiti""",
    "Randevu branşı/hastanesi doktorunkinden farklı":
        """SELECT COUNT(*) FROM randevular r JOIN doktorlar d USING(doktor_id)
           WHERE r.brans_id <> d.brans_id OR r.hastane_id <> d.hastane_id""",
    "Aktif olmayan doktora bekleyen randevu":
        """SELECT COUNT(*) FROM randevular r JOIN doktorlar d USING(doktor_id)
           WHERE r.durum = 'BEKLIYOR' AND d.aktif = 0""",
    "Hasta sisteme kaydolmadan alınmış randevu / yedek kaydı":
        """SELECT (SELECT COUNT(*) FROM randevular r JOIN hastalar h USING(hasta_id)
                   WHERE date(r.olusturma_zamani) < h.kayit_tarihi)
                + (SELECT COUNT(*) FROM yedek_liste y JOIN hastalar h USING(hasta_id)
                   WHERE date(y.kayit_zamani) < h.kayit_tarihi)""",
    # Veri 'şu an'a kadar olan geçmişi anlatır; sonradan yapılmış bir işlem olamaz.
    "Şu andan sonraya tarihli işlem kaydı (oluşturma, iptal, mesaj, yanıt, yedek)":
        """SELECT (SELECT COUNT(*) FROM randevular
                   WHERE olusturma_zamani > datetime('now','localtime') OR iptal_zamani > datetime('now','localtime'))
                + (SELECT COUNT(*) FROM bildirimler
                   WHERE gonderim_zamani > datetime('now','localtime') OR yanit_zamani > datetime('now','localtime'))
                + (SELECT COUNT(*) FROM yedek_liste
                   WHERE kayit_zamani > datetime('now','localtime') OR guncelleme_zamani > datetime('now','localtime'))""",
    # Poliklinikler resmî tatil ve bayramlarda kapalı; arifede 13:00'ten sonra kapalı.
    "Resmî tatil / bayram gününe ya da arife öğleden sonrasına randevu":
        """SELECT COUNT(*) FROM randevular r JOIN tatiller t ON t.tarih = date(r.randevu_zamani)
           WHERE t.tur IN ('RESMI','BAYRAM')
              OR (t.tur = 'ARIFE' AND strftime('%H:%M', r.randevu_zamani) >= '13:00')""",
    "Tatil listesinin kapsamadığı yılda randevu (tatil_yakin hep 0 çıkar)":
        """SELECT COUNT(*) FROM randevular r
           WHERE EXISTS (SELECT 1 FROM tatiller) AND NOT EXISTS (
               SELECT 1 FROM tatiller t WHERE substr(t.tarih, 1, 4) = substr(r.randevu_zamani, 1, 4))""",
    "Doktorun çalışmadığı güne randevu":
        """SELECT COUNT(*) FROM randevular r
           WHERE EXISTS (SELECT 1 FROM doktor_takvimi) AND NOT EXISTS (
               SELECT 1 FROM doktor_takvimi dt WHERE dt.doktor_id = r.doktor_id
                 AND dt.tarih = date(r.randevu_zamani) AND dt.calisiyor = 1)""",
    "Mesai dışı / öğle arası / slot ızgarasına oturmayan saat":
        """SELECT COUNT(*) FROM randevular r JOIN doktor_takvimi dt
             ON dt.doktor_id = r.doktor_id AND dt.tarih = date(r.randevu_zamani)
           WHERE strftime('%H:%M', r.randevu_zamani) < dt.baslangic_saat
              OR strftime('%H:%M', r.randevu_zamani) >= dt.bitis_saat
              OR (dt.ogle_baslangic IS NOT NULL
                  AND strftime('%H:%M', r.randevu_zamani) >= dt.ogle_baslangic
                  AND strftime('%H:%M', r.randevu_zamani) <  dt.ogle_bitis)
              OR CAST(round((julianday(r.randevu_zamani)
                             - julianday(dt.tarih || ' ' || dt.baslangic_saat)) * 1440) AS INTEGER)
                 % dt.slot_dk <> 0""",
    "toplam_slot mesai süresiyle uyuşmuyor":
        """SELECT COUNT(*) FROM doktor_takvimi
           WHERE calisiyor = 1 AND toplam_slot <> CAST(round((
                   (julianday('2000-01-01 ' || bitis_saat) - julianday('2000-01-01 ' || baslangic_saat))
                 - COALESCE(julianday('2000-01-01 ' || ogle_bitis) - julianday('2000-01-01 ' || ogle_baslangic), 0)
                 ) * 1440) AS INTEGER) / slot_dk""",
    "Hava durumu kaydı olmayan randevu günü":
        """SELECT COUNT(*) FROM randevular r JOIN hastaneler hs USING(hastane_id)
           WHERE EXISTS (SELECT 1 FROM hava_durumu) AND NOT EXISTS (
               SELECT 1 FROM hava_durumu hd WHERE hd.tarih = date(r.randevu_zamani) AND hd.il = hs.il)""",
    "Zamanı geçmiş ama hâlâ BEKLIYOR":
        """SELECT COUNT(*) FROM randevular
           WHERE durum = 'BEKLIYOR' AND randevu_zamani < datetime('now','localtime')""",
    "Gelecekteki randevu için GELDI/GELMEDI sonucu":
        """SELECT COUNT(*) FROM randevular
           WHERE durum IN ('GELDI','GELMEDI') AND randevu_zamani > datetime('now','localtime')""",
    "Yedekten atanan randevu yedek kaydıyla uyuşmuyor":
        """SELECT COUNT(*) FROM yedek_liste y JOIN randevular r ON r.randevu_id = y.atanan_randevu_id
           WHERE r.kaynak <> 'YEDEK_LISTE' OR r.hasta_id <> y.hasta_id OR r.brans_id <> y.brans_id
              OR r.olusturma_zamani < y.kayit_zamani
              OR (y.hastane_id IS NOT NULL AND r.hastane_id <> y.hastane_id)""",
    "Kaynağı YEDEK_LISTE ama hiçbir yedek kaydına atanmamış randevu":
        """SELECT COUNT(*) FROM randevular r
           WHERE r.kaynak = 'YEDEK_LISTE'
             AND NOT EXISTS (SELECT 1 FROM yedek_liste y WHERE y.atanan_randevu_id = r.randevu_id)""",
    "hatirlatma_gonderildi bayrağı ile HATIRLATMA bildirimi uyuşmuyor":
        """SELECT COUNT(*) FROM randevular r
           WHERE EXISTS (SELECT 1 FROM bildirimler)
             AND r.hatirlatma_gonderildi <> EXISTS (
                 SELECT 1 FROM bildirimler b WHERE b.randevu_id = r.randevu_id AND b.tur = 'HATIRLATMA')""",
    # Bildirim türlerinin her biri için: kime gider, hangi zaman aralığında gider.
    "Hatırlatma randevu sahibine gitmemiş, randevu alınmadan önce / randevudan ya da iptalden sonra gitmiş":
        """SELECT COUNT(*) FROM bildirimler b JOIN randevular r USING(randevu_id)
           WHERE b.tur = 'HATIRLATMA'
             AND (b.hasta_id <> r.hasta_id OR b.gonderim_zamani > r.randevu_zamani
                  OR b.gonderim_zamani < r.olusturma_zamani OR b.gonderim_zamani > r.iptal_zamani)""",
    "İptal onayı randevu sahibine gitmemiş ya da iptal edilmemiş / iptalden önce":
        """SELECT COUNT(*) FROM bildirimler b JOIN randevular r USING(randevu_id)
           WHERE b.tur = 'IPTAL_ONAYI'
             AND (b.hasta_id <> r.hasta_id OR r.durum <> 'IPTAL' OR b.gonderim_zamani < r.iptal_zamani)""",
    "Boş randevu teklifi iptal edilmemiş randevu için, iptalden önce ya da iptal edenin kendisine":
        """SELECT COUNT(*) FROM bildirimler b JOIN randevular r USING(randevu_id)
           WHERE b.tur = 'BOS_RANDEVU_TEKLIFI'
             AND (r.durum <> 'IPTAL' OR b.gonderim_zamani < r.iptal_zamani OR b.hasta_id = r.hasta_id)""",
    # Chatbot (4. grup) akışı: hasta 'iptal' derse randevu iptal edilir; chatbot iptali bir cevaba dayanır.
    "Hatırlatmaya IPTAL cevabı verilmiş ama randevu iptal edilmemiş":
        """SELECT COUNT(*) FROM bildirimler b JOIN randevular r USING(randevu_id)
           WHERE b.tur = 'HATIRLATMA' AND b.yanit_niyeti = 'IPTAL' AND r.durum <> 'IPTAL'""",
    "CHATBOT ile iptal edilmiş ama öncesinde hastadan IPTAL/ERTELEME cevabı yok":
        """SELECT COUNT(*) FROM randevular r
           WHERE r.iptal_kanali = 'CHATBOT' AND NOT EXISTS (
               SELECT 1 FROM bildirimler b WHERE b.randevu_id = r.randevu_id
                 AND b.yanit_niyeti IN ('IPTAL','ERTELEME') AND b.yanit_zamani <= r.iptal_zamani)""",
}


def denetle(con: sqlite3.Connection) -> bool:
    print("\nBütünlük denetimi:")
    hatali = con.execute("PRAGMA foreign_key_check").fetchall()
    print(f"  {'OK ' if not hatali else 'HATA'} yabancı anahtarlar: {len(hatali)}")
    temiz = not hatali
    for ad, sql in DENETIMLER.items():
        n = con.execute(sql).fetchone()[0]
        temiz &= n == 0
        print(f"  {'OK ' if n == 0 else 'HATA'} {ad}: {n}")
    print("\nSatır sayıları:")
    for tablo in TABLOLAR:
        print(f"  {tablo:<16} {con.execute(f'SELECT COUNT(*) FROM {tablo}').fetchone()[0]:>8}")
    print("\nSONUÇ:", "TEMİZ" if temiz else "SORUNLU — yukarıdaki HATA satırlarına bakın")
    return temiz


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=KOK / "cikti" / "mhrs.db")
    p.add_argument("--ornek", action="store_true", help="elle yazılmış test verisini yükle")
    p.add_argument("--csv", type=Path, help="CSV klasörünü yükle")
    p.add_argument("--disa-aktar", type=Path, help="tabloları bu klasöre CSV olarak yaz")
    a = p.parse_args()

    try:
        con = kur(a.db)
        print(f"Veritabanı kuruldu: {a.db}  (şema {sema_surumu(con)})")
        if a.ornek:
            con.executescript(ORNEK.read_text(encoding="utf-8"))
        if a.csv:
            csv_yukle(con, a.csv)
    except (YuklemeHatasi, sqlite3.IntegrityError) as e:
        print(f"\nYÜKLEME REDDEDİLDİ: {e}")
        return 1
    temiz = denetle(con)
    if a.disa_aktar:
        disa_aktar(con, a.disa_aktar)
    con.close()
    return 0 if temiz else 1


if __name__ == "__main__":
    sys.exit(main())
