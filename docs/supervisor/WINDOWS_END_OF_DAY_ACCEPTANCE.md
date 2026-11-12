# Gün sonu Windows / gerçek ETABS kabul protokolü

**Şimdi ÇALIŞTIRILMAYACAK.** Bu belge, offline geliştirme tamamlandıktan sonra gerçek Windows/ETABS oturumunda tek kez ve salt-okunur uygulanacak kabul sırasıdır. Yeni analiz, tasarım başlatma, model kaydetme, as-built veri üretme ve varsayımsal kaynak onayı yok.

## 0. Ön koşullar

- Codespaces recovery dalında VS27 kaynak entegrasyonu tamamlanmış ve değişiklikler incelenmiş olmalı. Aynı HEAD Windows ortamına alınmalı; eski VS26 veya karışık ZIP kodu çalıştırılmamalı.
- ETABS model dosyası \`kompakt_b.EDB\` (veya bilerek seçilen başka model) doğrulanmalı. Yol, model kilit durumu, birimler, ETABS sürümü, dosya hash'i ve kayıtlı analiz nesli ayrı gösterilmeli. Çalışan bellekteki sonuçlar ile diskteki EDB'nin eşdeğerliği otomatik varsayılmaz.
- Önce Windows üzerinde kullanılan \`comtypes\` ve ETABS API dönüş biçimleri, hiçbir model değişikliği yapılmadan doğrulanmalı.

## 1. Başlangıç snapshot'ı (zorunlu)

- \`SapModel.GetModelIsLocked\`, \`GetPresentUnits\`, \`Results.Setup\` seçili case/combo vektörü ve \`DatabaseTables\` display case/combo vektörü.
- Aynı API ile restore edilemeyecek ya da okunamayacak orijinal seçim varsa yeni yakalama başlatma.
- \`Results.FrameForce\` çağrılarını takip eden output seçimi ile \`DatabaseTables\` görüntüleme seçimi **ayrı evrelerde** yönetilmeli. VS27.3 değişikliğinin canlı kabul konusu budur.

## 2. Tek capture, eksik veriyi gizleme yok

- Gerçek 87 kolonun fiziksel Obj listesi ve I/J noktaları aynı modelden; her elemanın analiz nesnesi \`Elm\` ve istasyonları tekil kimlikle alınmalı.
- Her \`Results.FrameForce\` için seçili OutputCase/StepType/StepNum, dönen kod, NumberResults ve tam 13 alan saklanmalı. Başarısız \`GetSummaryResultsColumn\` kaydı başarı gibi yazılmamalı; ETABS tasarım sonuçları mevcut değilse gözlemlenen yokluk ayrı saklanmalı.
- İlk \`FrameForce\` başarısızlığında \`Results.Setup\` seçimleri ve görüntüleme seçimi değişmiş mi ayrıca doğrula; değiştirilmişse capture \`BLOCKED\` olmalı. Hatalı kolonun yerine eski arşivden veri koyma.

## 3. Restore ve kimlik kanıtı

- İşlem sonunda ilk snapshot ile hem \`Results.Setup\` hem \`DatabaseTables\` seçili case/combo kümelerinin eşleştiğini API üzerinden kanıtla.
- Kişisel model verileri ve EDB GitHub'a yazılmayacak. Kaydedilen ZIP/SQLite hash ve kapsam özetini R00/R01 araçlarıyla **offline** değerlendir.
- Birim \`kN-m-C (6)\`, tekil Obj/Elm/ObjSta/ElmSta, kaydedilmiş kombinasyonlar ve analitik nesil nitelendirmesi ayrı doğrulanmalı.

## 4. Final test kapısı (en sonda)

Yalnız offline R00–R03 ve VS27 entegrasyonu tamamlandıktan sonra:
1. Linux bütün Python ve JavaScript regresyonları, eski golden rapor farkları ve koşullu PMM senaryoları.
2. Windows aynı HEAD üzerinde API negatif testleri ve tek salt-okunur ETABS capture.
3. Kaydedilmiş ZIP/SQLite üzerinde bağımsız source/dependency replay, kaynak kapsam defteri, tek kolon ve 87 kolon değerlendirmesi.
4. Supervisor \`ACCEPTED / CHANGES_REQUIRED / HOLD\` kararı. CI yeşil veya 87/87 fiziksel eleman sayımı bu kapıyı tek başına geçirmez.

**Hiçbir zaman:** \`RunAnalysis\`, \`StartDesign\`, \`Save\`, \`SetPresentUnits\`, kalıcı OutputCase/DisplayCase ataması, araştırma sırasında model mutasyonu.

> Bugün Codespaces'te yapılan iş offline kaynak/algoritma geliştirmesidir. Gün sonu canlı ETABS kabulü henüz yapılmamıştır; \`engineering_release=NOT_READY\`.
