"""Şikayet ve hasta cevabı metinleri (2. ve 4. grubun eğitim verisi).

Metinler küçük harfle başlar; üretici başına zaman ifadesi ekleyip ilk harfi büyütür.
Biçim: (metin, aciliyet, alternatif branş adı ya da None).
"""

SIKAYETLER = {
    "Dahiliye": [
        ("sürekli halsizim ve çabuk yoruluyorum", "RUTIN", None),
        ("midem yanıyor, yemeklerden sonra şişkinlik oluyor", "RUTIN", None),
        ("sık sık ateşim çıkıyor ve iştahım kesildi", "ONCELIKLI", None),
        ("kilo veriyorum ama nedenini bilmiyorum", "ONCELIKLI", "Endokrinoloji"),
        ("tansiyonum dengesiz, ilaçlarımı kontrol ettirmek istiyorum", "RUTIN", "Kardiyoloji"),
        ("karnımın üst tarafı ağrıyor, bulantım var", "RUTIN", "Genel Cerrahi"),
        ("kan tahlili yaptırmak istiyorum, kansızlığım olabilir", "RUTIN", None),
    ],
    "Kardiyoloji": [
        ("gözlerimde kararma var, merdiven çıkarken göğsüm sıkışıyor", "ONCELIKLI", None),
        ("çarpıntım oluyor, kalbim çok hızlı atıyor", "ONCELIKLI", None),
        ("yürürken çabuk nefesim kesiliyor ve bacaklarım şişiyor", "ONCELIKLI", "Göğüs Hastalıkları"),
        ("tansiyonum yükseliyor, ensem ağrıyor", "RUTIN", "Dahiliye"),
        ("eforla gelen hafif göğüs baskısı hissediyorum", "ONCELIKLI", None),
        ("kalp ilacımı kontrol ettirmem gerekiyor", "RUTIN", None),
    ],
    "Çocuk Sağlığı ve Hastalıkları": [
        ("çocuğumun ateşi düşmüyor ve öksürüyor", "ONCELIKLI", None),
        ("bebeğimin aşı takvimi için kontrole gelmek istiyorum", "RUTIN", None),
        ("oğlum iştahsız, kilo almıyor", "RUTIN", None),
        ("kızımın karnı ağrıyor ve kusuyor", "ONCELIKLI", None),
        ("çocuğumun boğazı şiş, yutkunamıyor", "ONCELIKLI", "Kulak Burun Boğaz"),
        ("bebeğimde pişik ve döküntü var", "RUTIN", "Dermatoloji"),
    ],
    "Kadın Hastalıkları ve Doğum": [
        ("adetlerim düzensiz ve çok ağrılı geçiyor", "RUTIN", None),
        ("hamileyim, rutin kontrol için gelmek istiyorum", "RUTIN", None),
        ("kasıklarımda ağrı ve akıntı var", "ONCELIKLI", None),
        ("gebelik testim pozitif çıktı, muayene olmak istiyorum", "RUTIN", None),
        ("yıllık smear testimi yaptırmak istiyorum", "RUTIN", None),
        ("adet dönemi dışında kanamam oldu", "ONCELIKLI", None),
    ],
    "Genel Cerrahi": [
        ("kasığımda şişlik var, öksürünce büyüyor", "RUTIN", None),
        ("makattan kanamam oluyor", "ONCELIKLI", None),
        ("safra kesesinde taş çıktı, ameliyat için görüşmek istiyorum", "RUTIN", "Dahiliye"),
        ("göbeğimin çevresinde ele gelen bir şişlik var", "RUTIN", None),
        ("memede ele gelen bir kitle fark ettim", "ONCELIKLI", None),
    ],
    "Ortopedi ve Travmatoloji": [
        ("dizim ağrıyor, merdiven inerken zorlanıyorum", "RUTIN", "Fiziksel Tıp ve Rehabilitasyon"),
        ("ayak bileğimi burktum, basarken ağrıyor", "ONCELIKLI", None),
        ("omzum ağrıyor, kolumu kaldıramıyorum", "RUTIN", "Fiziksel Tıp ve Rehabilitasyon"),
        ("topuğumda sabah kalkınca batma oluyor", "RUTIN", None),
        ("düştükten sonra bileğim şişti", "ONCELIKLI", None),
        ("belimden bacağıma vuran ağrı var", "RUTIN", "Nöroloji"),
    ],
    "Göz Hastalıkları": [
        ("gözlerim kızarıyor, yanma ve batma var", "RUTIN", None),
        ("uzağı net göremiyorum, gözlük numaram değişti galiba", "RUTIN", None),
        ("gözümün önünde siyah noktalar uçuşuyor", "ONCELIKLI", None),
        ("gözlerim çok sulanıyor", "RUTIN", None),
        ("göz tansiyonu kontrolü yaptırmak istiyorum", "RUTIN", None),
    ],
    "Kulak Burun Boğaz": [
        ("kulağım ağrıyor ve uğulduyor", "RUTIN", None),
        ("boğazım yanıyor, yutkunurken ağrıyor", "RUTIN", None),
        ("burnum sürekli tıkalı, nefes alamıyorum", "RUTIN", None),
        ("sesim günlerdir kısık", "RUTIN", None),
        ("kulağımdan akıntı geliyor, az duyuyorum", "ONCELIKLI", None),
        ("baş dönmesi ve kulak çınlaması var", "RUTIN", "Nöroloji"),
    ],
    "Dermatoloji": [
        ("cildimde kaşıntılı kızarıklıklar çıktı", "RUTIN", None),
        ("yüzümde sivilceler geçmiyor", "RUTIN", None),
        ("saçlarım aşırı dökülüyor", "RUTIN", None),
        ("vücudumdaki bir ben büyüdü ve renk değiştirdi", "ONCELIKLI", None),
        ("tırnaklarımda mantar oldu", "RUTIN", None),
    ],
    "Nöroloji": [
        ("şiddetli baş ağrılarım var, bulantı da yapıyor", "ONCELIKLI", None),
        ("ellerimde titreme başladı", "RUTIN", None),
        ("unutkanlığım arttı", "RUTIN", "Psikiyatri"),
        ("elimde ve parmaklarımda karıncalanma oluyor", "RUTIN", "Fiziksel Tıp ve Rehabilitasyon"),
        ("migren ataklarım sıklaştı", "RUTIN", None),
        ("zaman zaman baş dönmesi ve denge kaybı yaşıyorum", "ONCELIKLI", "Kulak Burun Boğaz"),
    ],
    "Üroloji": [
        ("idrar yaparken yanma oluyor", "RUTIN", None),
        ("böğrümde ağrı var, böbrek taşım olabilir", "ONCELIKLI", None),
        ("geceleri çok sık tuvalete kalkıyorum", "RUTIN", None),
        ("idrarımda kan gördüm", "ONCELIKLI", None),
        ("idrarımı tutmakta zorlanıyorum", "RUTIN", "Kadın Hastalıkları ve Doğum"),
    ],
    "Göğüs Hastalıkları": [
        ("haftalardır geçmeyen öksürüğüm var", "ONCELIKLI", None),
        ("nefes darlığım var, hırıltılı soluyorum", "ONCELIKLI", "Kardiyoloji"),
        ("astım ilaçlarımı kontrol ettirmek istiyorum", "RUTIN", None),
        ("uykuda horluyorum, nefesim duruyormuş", "RUTIN", "Kulak Burun Boğaz"),
        ("balgamım çok, sigarayı bırakmak istiyorum", "RUTIN", None),
    ],
    "Psikiyatri": [
        ("uzun zamandır hiçbir şeyden keyif alamıyorum", "RUTIN", None),
        ("uyuyamıyorum, kaygılarım çok arttı", "RUTIN", None),
        ("durduk yere kalbim sıkışıyor, panik atak geçiriyor olabilirim", "RUTIN", "Kardiyoloji"),
        ("kontrol edemediğim takıntılı düşüncelerim var", "RUTIN", None),
        ("ilaç kontrolüm için randevu almak istiyorum", "RUTIN", None),
    ],
    "Fiziksel Tıp ve Rehabilitasyon": [
        ("boynum tutuluyor, kollarıma yayılıyor", "RUTIN", "Nöroloji"),
        ("bel fıtığım için fizik tedavi görmek istiyorum", "RUTIN", None),
        ("eklemlerim sabahları sertleşiyor", "RUTIN", None),
        ("felç sonrası rehabilitasyon için başvuruyorum", "ONCELIKLI", None),
        ("kas ağrılarım geçmiyor", "RUTIN", None),
    ],
    "Endokrinoloji": [
        ("şekerim yüksek çıktı, çok su içiyorum", "ONCELIKLI", "Dahiliye"),
        ("boynumda şişlik var, tiroidim olabilir", "RUTIN", None),
        ("durduk yere kilo alıyorum ve üşüyorum", "RUTIN", None),
        ("diyabet ilaçlarımı ayarlatmak istiyorum", "RUTIN", None),
        ("guatr kontrolüm var", "RUTIN", None),
    ],
    "Çocuk Cerrahisi": [
        ("oğlumun kasığında şişlik fark ettim", "ONCELIKLI", None),
        ("çocuğumun sünnet için görüşme yapmak istiyorum", "RUTIN", None),
        ("bebeğimin göbeğinde fıtık var", "RUTIN", None),
        ("çocuğumda inmemiş testis olduğu söylendi", "RUTIN", None),
    ],
}

# Randevu beklenmemesi gereken acil vakalar: brans_id boş kalır.
ACIL_SIKAYETLER = [
    "sol kolum uyuştu, şiddetli göğüs ağrım var",
    "göğsümde ezici bir ağrı var, soğuk soğuk terliyorum",
    "nefes alamıyorum, dudaklarım morardı",
    "konuşmam bozuldu, yüzümün bir tarafı kaydı",
    "bir anda kolumu ve bacağımı hareket ettiremez oldum",
    "hayatımın en şiddetli baş ağrısı aniden başladı",
    "kanamam durmuyor, başım dönüyor",
    "kan kustum, siyah dışkı yaptım",
    "bayıldım ve kendime gelmekte zorlanıyorum",
    "yüksekten düştüm, başımı çarptım ve kusuyorum",
    "karnımda dayanılmaz bir ağrı var, sertleşti",
    "yüzüm ve dilim şişti, nefesim daralıyor",
    "çocuğum nöbet geçiriyor, tepki vermiyor",
    "bebeğim morardı, nefes almakta zorlanıyor",
    "hamileyim, şiddetli kanama ve ağrım var",
    "aşırı dozda ilaç aldım",
    "kendime zarar vermeyi düşünüyorum",
    "gözüme kimyasal madde sıçradı, göremiyorum",
    "derin bir kesiğim var, kan fışkırıyor",
    "elektrik çarptı, göğsüm ağrıyor",
]

# "Yarım saattir hamileyim", "dünden beri kan tahlili yaptırmak istiyorum" olmasın: süre ifadesi yalnız
# süregelen şikayetlere eklenir. Bu kalıpları içeren cümleler bir istek ya da olaydır, süre almaz.
SURESIZ_KALIPLAR = ("istiyorum", "gerekiyor", "kontrolüm", "söylendi", "başvuruyorum", "hamileyim", "çıktı", "burktum",
                    "düştükten", "oldu", "fark ettim", "büyüdü", "gördüm", "şişti", "başladı", "sıklaştı", "değişti")
ZAMAN_IFADELERI = ["son günlerde ", "bir haftadır ", "uzun zamandır ", "dünden beri ", "son zamanlarda ",
                   "birkaç gündür ", "aylardır "]
KAPANISLAR = [" Hangi bölüme gitmeliyim?", " Randevu almak istiyorum.", " Ne yapmalıyım?", " Doktora görünmek istiyorum."]
SURELI_KAPANISLAR = [" Çok rahatsız ediyor.", " Artık dayanamıyorum."]

# Acil cümlelerde: olay anlatanlar "az önce" alır, süren durumlar "şu an" da alır, zaten ani olanlar hiçbir şey almaz.
ACIL_OLAY_KALIPLARI = ("uştu", "kaydı", "bozuldu", "morardı", "kustum", "bayıldım", "düştüm", "şişti", "aldım", "sıçradı",
                       "çarptı")
ACIL_SURESIZ_KALIPLAR = ("aniden", "bir anda", "hamileyim", "düşünüyorum", "çocuğum", "bebeğim")
ACIL_KAPANISLAR = [" Ne yapmalıyım?", " Çok korkuyorum.", " Yardım edin.", " Randevu alabilir miyim?"]

YANITLAR = {
    "ONAY": ["Evet", "Evet geleceğim", "Geleceğim", "Tamam", "Tamamdır gelirim", "Onaylıyorum", "Evet, orada olacağım",
             "Olur", "Gelirim", "Evet teşekkürler", "Kesinlikle geleceğim", "Evet hocam", "Geliyorum", "Tamam oradayım",
             "Randevuma geleceğim", "Evet onaylıyorum", "Ok geleceğim", "İnşallah geleceğim", "Evet uygun"],
    "IPTAL": ["Gelemeyeceğim", "İptal Et", "İptal", "Hayır gelemem", "Randevumu iptal edin", "Maalesef gelemiyorum",
              "Gelmeyeceğim", "Vazgeçtim", "İşim çıktı gelemem", "İptal etmek istiyorum", "Hayır", "Şehir dışındayım gelemem",
              "Hastanelik bir durum kalmadı iptal edin", "Lütfen iptal edin", "Gelmem mümkün değil", "Yetişemem iptal olsun"],
    "ERTELEME": ["Başka bir güne alabilir miyiz?", "Ertelemek istiyorum", "Daha ileri bir tarihe alın",
                 "Yarın olmaz, haftaya uygunum", "Saatini değiştirebilir miyiz?", "Başka güne alın lütfen",
                 "Öğleden sonraya alabilir miyiz?", "Randevuyu ileri atın", "Başka saat var mı?", "Pazartesiye alabilir misiniz?"],
    "SORU": ["Hangi binaya gideceğim?", "Yanımda ne getirmeliyim?", "Aç mı gelmeliyim?", "Doktorum kim?",
             "Kaç dakika önce orada olmalıyım?", "Tahlil sonuçlarımı getireyim mi?", "Otopark var mı?", "Sevk gerekiyor mu?",
             "Randevu saatim kaçtı?", "Refakatçi gelebilir mi?"],
    "BELIRSIZ": ["Bakacağım", "Bilmiyorum", "Belki", "Emin değilim", "Sonra haber veririm", "Hmm", "Duruma göre",
                 "Yazarım size", "Bir sorayım", "...", "Kim bu?", "Yanlış numara galiba"],
}

BOS_TEKLIF_RED = ["Hayır teşekkürler", "Uygun değilim", "Gelemem", "O saat olmaz"]
