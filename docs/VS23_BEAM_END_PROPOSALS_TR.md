# VS23 — Kiriş uç kaynakları, donatı önerileri ve işaretli kapasite

- Mevcut ZIP’teki 180 kirişten kayıtlı kolon birleşimlerine bağlı 140 kirişin iki ucu, toplam 280 uç korundu; 254 uç kolon birleşiminde, diğer 40 kiriş açık kapsam listesinde.
- Native I/J offset, Obj/ObjSta/Elm/ElmSta ve 4.939 satırlı tasarım tablosundan 279/280 uç tekil bağlandı; 361/J’de üç native kesit ve üç tasarım satırı bulunduğundan üç adayı da bloklu kaldı.
- Üst/alt gerekli alan, minimum ve toplam alanın aynı satırdaki zarfı; kontrol birleşimleri model tanımlarına tam adla bağlı. Bu alanlar uygulanmış donatı veya eşzamanlı tasarım kuvveti değildir; yuvarlama, en büyük alan veya son satır fallback’i yok.
- Φ16/20/24 tek sıra önerilerinde çubuk adedi alan hedefini örten en küçük tamsayıdır. [CSI örtüsü](https://docs.csiamerica.com/help-files/etabs-api-2016/html/45d94bde-0567-8528-d8cf-daea0b892a8c.htm) boyuna donatı ağırlık merkezine ölçülür; yan net örtü 30 mm/etriye Φ10 açık öneri, çap/25 mm aralık referansı agregasız koşulludur.
- 837/840 öneride kanonik kesit çekirdeğiyle N=0 için yerel +M3 ve −M3 ayrı hesaplandı; üst/alt simetrisi varsayılmadı. Kaynak kiriş N’si kullanılmadı; donatı seçimi ve SCWB oranı üretilmedi.
- UI: Kolon–kiriş birleşimleri → Kiriş uç donatısı ve kapasitesi; Φ20 başlangıç görünümü, üç çap seçeneği, kolon filtresi, öneri çizimi ve kapalı kaynak izleri. HTML bütün uçları, JSON tam hassasiyeti içerir; CLI `inspect-column-demands --beams`.
- Doğrulama: 36 yeni test; toplam 875/875 Python ve altı Node regresyonu, bağımsız uygulama denetimi PASS. 70 benzersiz kafeste ayrı şerit integrasyonu/bisection ile 1.674 işaretli değer kıyaslandı; en büyük fark 0,000291 kN·m. Aynı malzeme modelinin sayısal kıyasıdır.
- ZIP/SQLite ve önceki 13 hesap kimliği değişmedi. 361/J, gerçek/seçilmiş donatı, agrega/burulma/ankraj/süreklilik, fiziksel yüz/döşeme, depremli Nd ve birleşim işaret toplamı açık; DENIED / NOT_PROVEN / NOT_READY, ortak kabulüne kadar MERGE HOLD.
