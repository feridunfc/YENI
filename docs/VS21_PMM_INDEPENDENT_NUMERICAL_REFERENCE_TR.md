# VS21 — PMM bağımsız sayısal kıyas

- Üretim kapasite çözücüsünü çağırmayan şerit/Gauss integrasyonu, eksenel ve açısal ikiye bölme çözümü eklendi; üç çözüm düzeyi, pozitif kökler ve artıklar ayrı kaydedilir.
- Aynı açık malzeme senaryosu kullanılır; malzeme modelinin, sürekli hata sınırının, tüm köklerin tekliğinin veya kritik seçimin bağımsız kabulü değildir.
- 87 kolon × 3 önerinin ana hesapta kritik olan 261 kaydı karşılaştırıldı; 7.236 PMM değerlendirmesinin tamamına genellenmez. Tüm eşitler, çözüm hataları ve radyal olmayan durumların kapsamı korunur.
- Sabit %0,2 + mutlak/eksenel tolerans bütçesinde 255 kıyas içeride, 6 kıyas dışarıda. Ana hesabın seviye yayılımı toleransa eklenmedi; ana PMM sonuçları değiştirilmedi.
- Açık bulgular: 145/16Φ32, 230/16Φ24, 64/16Φ24, 68/16Φ32, 70/16Φ24, 72/16Φ28. Hepsinde referans kapasitesi daha yüksek; en büyük bağıl fark %0,24110346, 72/+9.00/Soil_Ult için 3,697632 kN·m > 3,068851 kN·m bütçe.
- UI: Donatı ve kapasite → PMM bağımsız sayısal kıyas; kısa sonuç tablosu, kapalı kaynak/çözüm ayrıntıları. HTML tüm 261 kaydı, JSON tam hassasiyeti içerir; CLI `inspect-column-demands --quality`. Olağan gezinmede ek çözücü çalışmaz.
- Yerel 803/803 test (31 yeni), dört Node regresyonu ve bağımsız hesap incelemesi PASS. Gerçek arşivde hedef/kaynak bağları ve tüm kıyas durumları ayrıca kontrol edildi; altı uyuşmazlık başarılı testlerle gizlenmez.
- ZIP/SQLite ve önceki hesap hash’leri aynı; CHECK=16. Spektral tasarım talebi, gerçek ikinci mertebe, Ve/SCWB ve donatı seçimi açık: DENIED / NOT_PROVEN / NOT_READY. Ortak Windows/ETABS kabulü ve main merge sonda.
