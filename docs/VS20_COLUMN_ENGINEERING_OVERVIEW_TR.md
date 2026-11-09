# VS20 — Kolon mühendislik özeti

- 87 kolonun her biri için kritik statik birleşim, aynı kaydın N/M2/M3 vektörü, donatı senaryosu, koşullu PMM, kesme ve ikinci mertebe durumu tek satırda gösterilir.
- 16Φ24/28/32 yalnız görüntüleme senaryolarıdır; otomatik donatı seçimi yapılmaz. Altı statik birleşim kullanılır; 24 spektral birleşimin tasarım talebi ve Nd/M2d/M3d açık kalır.
- Kritik seçim tam hassasiyetlidir; eşitler korunur. Eksenel sınır aşımı, yalnız N, belirsiz/eksik PMM ve kesmenin gövde/gevrek sınır bulguları düşük bir oranla gizlenmez; kesme dalları kendi durumlarına bağlıdır.
- 402 tasarım satırı / 1.206 referans: 529 tekil statik bağ, 245 çoklu native durum, 432 belirsiz istasyon referansı. Kesin istasyonu bulunmayan 342 referansın tamamı bu 432 içindedir; 144 belirsiz satır ayrıca sayılır.
- 50 sıfıra yakın/negatif payda karşılaştırması beş kolonun varsayımsal boy/rijitlik referansına aittir; gerçek göçme veya stabilite kabulü oluşturmaz. ln/k/lk/Cm/β/Md doğrulanmadı.
- Varsayılan UI kolon özetidir; kolon/vaka ve donatı senaryosu seçilir. Ayrıntılar açılır; HTML aynı özeti öne alır, tam JSON hassasiyeti korunur; CLI `inspect-column-demands --overview` eklendi.
- Gerçek kaynakta 261 kritik/tie grubu, 1.827 native anahtar alanı, 1.566 kuvvet bileşeni ve 522 aynı-durum kesme bağı kıyaslandı. En büyük koşullu oran yine 136 / +4.50 / 16Φ24 / Soil_Ult: 0,40952621697133795.
- Önceki hesaplar ve ZIP/SQLite hash’leri aynı; CHECK=16. Yerel 772/772, 25 yeni test ve üç Node regresyonu PASS; bağımsız inceleme PASS. Chromium indirme otomatik incelemede çevrimdışı sınırı nedeniyle reddedildi; görsel tarayıcı kontrolü yapılmadı. DENIED / NOT_PROVEN / NOT_READY; ortak Windows/ETABS kabulü ve merge sonda.
