import csv
import random
from datetime import datetime, timedelta
from faker import Faker

# Türkçe sahte veri üretmek için Faker'ı ayarlıyoruz
fake = Faker('tr_TR')

# Poliklinik ve doktor eşleşmeleri
hastane_verileri = {
    "Merkez Hastanesi": {
        "Kardiyoloji": ["Uzm. Dr. Ahmet Yılmaz", "Prof. Dr. Mehmet Demir"],
        "Dahiliye": ["Uzm. Dr. Ayşe Kaya", "Dr. Ali Çelik"],
        "Göz Hastalıkları": ["Op. Dr. Zeynep Şahin"],
        "Ortopedi": ["Doç. Dr. Can Aydın"]
    }
}

print("Chatbot ekibinin istediği formatta veriler üretiliyor...")

hastane_adi = "Merkez Hastanesi"
toplam_hasta = 200  # Örnek 200 hasta

# 1. DOSYA: Hastalar Tablosu
with open("hastalar.csv", mode='w', newline='', encoding='utf-8') as f_hasta:
    yazici_hasta = csv.writer(f_hasta)
    # Chatbot ekibinin istediği sütunlar + ekstra gerekli alanlar
    yazici_hasta.writerow(["hasta_id", "ad_soyad", "yas", "cinsiyet", "no_show_sayisi"])
    
    for i in range(1, toplam_hasta + 1):
        hasta_id = f"H{i:03d}"
        cinsiyet = random.choice(["Kadın", "Erkek"])
        ad_soyad = f"{fake.name_female()}" if cinsiyet == "Kadın" else f"{fake.name_male()}"
        yas = random.randint(18, 85)
        no_show_sayisi = random.choices([0, 1, 2, 3], weights=[70, 20, 7, 3])[0]
        
        yazici_hasta.writerow([hasta_id, ad_soyad, yas, cinsiyet, no_show_sayisi])


# 2. DOSYA: Randevular Tablosu (Chatbot ve 2 saat kuralına uygun)
with open("randevular.csv", mode='w', newline='', encoding='utf-8') as f_randevu:
    yazici_randevu = csv.writer(f_randevu)
    
    # Chatbot ekibinin talep ettiği sütun başlıkları
    yazici_randevu.writerow([
        "randevu_id", "hasta_id", "randevu_tarih_saat", "saat_dilimi", 
        "hastane", "bolum", "doktor", "randevu_durumu", 
        "katilim_teyidi", "onay_zamani", "iptal_zamani_ve_nedeni"
    ])
    
    randevu_id_sayac = 1
    for i in range(1, toplam_hasta + 1):
        hasta_id = f"H{i:03d}"
        
        # Her hasta için 1-2 randevu üretelim
        for _ in range(random.randint(1, 2)):
            randevu_id = f"R{randevu_id_sayac:04d}"
            randevu_id_sayac += 1
            
            # Bölüm ve Doktor seçimi
            bolum = random.choice(list(hastane_verileri[hastane_adi].keys()))
            doktor = random.choice(hastane_verileri[hastane_adi][bolum])
            
            # Randevu tarihi (Gelecek veya geçmiş tarihler)
            gun_farki = random.randint(-5, 10)
            randevu_zamanı = datetime.now() + timedelta(days=gun_farki, hours=random.randint(8, 16))
            tarih_str = randevu_zamanı.strftime("%Y-%m-%d %H:%M:%S")
            saat_dilimi = "Europe/Istanbul (+03:00)"
            
            # Durum ve Teyit Senaryoları
            durum_secenekleri = ["Planlandı", "İptal Edildi", "Tamamlandı"]
            durum = random.choices(durum_secenekleri, weights=[50, 20, 30])[0]
            
            katilim_teyidi = "Yanıt bekleniyor"
            onay_zamani = ""
            iptal_nedeni = ""
            
            if durum == "İptal Edildi":
                # İptal nedenlerinde senin bahsettiğin kural ayrımı
                iptal_turu = random.choice(["Hasta İsteği", "Onay Süresi Doldu (2 Saat Kuralı)"])
                iptal_zamanı = (randevu_zamanı - timedelta(hours=random.randint(1, 24))).strftime("%Y-%m-%d %H:%M:%S")
                iptal_nedeni = f"{iptal_zamanı} - {iptal_turu}"
                katilim_teyidi = "Reddedildi / Süre Aşımı"
                
            elif durum == "Tamamlandı" or randevu_zamanı < datetime.now():
                katilim_teyidi = "Geleceğini onayladı"
                onay_zamani = (randevu_zamanı - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                durum = "Tamamlandı"
            else:
                # Planlandı durumundakiler için teyit ihtimali
                if random.choice([True, False]):
                    katilim_teyidi = "Geleceğini onayladı"
                    onay_zamani = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    katilim_teyidi = "Yanıt bekleniyor"

            yazici_randevu.writerow([
                randevu_id, hasta_id, tarih_str, saat_dilimi, 
                hastane_adi, bolum, doktor, durum, 
                katilim_teyidi, onay_zamani, iptal_nedeni
            ])

print("İşlem tamam! 'hastalar.csv' ve 'randevular.csv' dosyaları başarıyla oluşturuldu.")