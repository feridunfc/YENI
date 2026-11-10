# VS22 — TBDY SCWB yaklaşımının YENI’ye uyarlanması

- Esas: [TBDY 1440df1 kapasite birleştirme çekirdeği](https://github.com/feridunfc/TBDY/blob/1440df1b9300f75b1e604204438f5cada9ebd247/tbdy_engine/design/core/capacity_design.py) ve birleşim/yön orkestrasyonu; yaklaşık As/2 kapasitesi ve eksik üyeyi düşüren toplama taşınmadı.
- 87 kolon, 174 uç, 119 birleşim ve 180 kiriş mevcut ZIP’ten bağlandı; 6 statik birleşim × 3 donatı senaryosu × X/Y × iki dönme yönünde 8.568 vaka kaydı korundu.
- Kanonik kesit çekirdeğiyle kaynak N’ye bağlı 6.264/6.264 saf yerel M2/M3 kapasite referansı üretildi; aynı vakada 8.280 kolon toplamı hesaplandı. Statik örneklem minimumu depremle uyumlu normatif Nd minimumu değildir.
- 1.428 yön/donatı/dönme özetinde 924 kiriş kapasitesi eksik, 456 ilgili yönde kayıtlı kiriş yok, 48 bağlantı geometrisi belirsiz. Kirişin 4.939 gerekli As satırı ve sıfır override alanları seçilmiş donatı değildir; gerçek SCWB oranı üretilmedi.
- Native I/J offset/istasyon bağı yeniden doğrulanır; eksik üye veya vaka toplamı geçersiz kılar. Grafik blokluysa bilinen kolon/uç/kapasite paydaları korunur, bilinmeyen birleşim sayısı null kalır; istisna uygulanmaz.
- UI: Kolon–kiriş birleşimleri → SCWB; kısa özet, kapalı komşu üye ve hesap izleri. HTML tüm özetleri, JSON tam hassasiyeti taşır; CLI `inspect-column-demands --scwb`. Kolon filtresi komşuları korur; spektral filtre statik minimumu kullanmaz.
- Doğrulama: 36 yeni test; toplam 839/839 Python, beş Node regresyonu ve bağımsız uygulama denetimi PASS. Analitik kapasite oraklları, eksik üyeli yanlış kabul, eksen dönüşümü, I/J karışması ve bloklu nüfus sınandı.
- ZIP/SQLite ve önceki hesap hash’leri korundu. Kiriş uç donatısı/kapasitesi, fiziksel yüz/döşeme katkısı, depremli Nd, ikinci mertebe ve istisna uygulanabilirliği açık; DENIED / NOT_PROVEN / NOT_READY, ortak Windows/ETABS kabulüne kadar MERGE HOLD.
