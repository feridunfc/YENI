# VS26 — Spektral tasarım talebi: sayısal denetim ve teslim

**Durum:** `NUMERICAL REPLAY VERIFIED` · `CONDITIONAL DESIGN ENVELOPE CALCULATED` · **`NORMATIVE DESIGN AUTHORITY NOT YET PROVEN`**.

Supervisor, 10.11.2026 tarihinde VS26'nın mevcut `work/vs07-b2-soft-story-20261108` dalına commit edilip gönderilmesine izin verdi. **MERGE HOLD** sürüyor. Bu yayın izni mühendislik kabulü değildir. Genel mühendislik release durumu `NOT_READY`, tasarım yetkisi `DENIED`, normatif nitelik `NOT_PROVEN` olarak kalır. Yeni zorunlu golden rapor kabul kapısı da kapsam eksikleri nedeniyle açıktır.

## 1. Sabit taban ve kaynak

| Kimlik | Doğrulanan değer |
| --- | --- |
| Depo / dal | `feridunfc/YENI` / `work/vs07-b2-soft-story-20261108` |
| Yerel ve son okunan uzak HEAD | `4827e6d06740a6f696290cd7ca1aed4b6e86b4aa` |
| Taban Git tree | `cc1ae9a45364218d7b8034e8b4c30754222712f3` |
| Kaynak çalışması | `RUN-927f46bf3c0449b3927c6221485085e4` |
| Native ZIP SHA-256 | `3882b659937626bb3bbfe841e6dbd6c57798fcfcce8e6fa54a683a221210fee3` |
| SQLite SHA-256 | `98bef804508076a13d39e12227c5909b93c2e3de19ec2ce297873c1e80dce381` |
| Kaynak banka sonuç kimliği | `ed129ba879527ed1b1097174828e21f1aaee4b57e4fe5c2e64fc61ff300b2bde` |

ZIP ve SQLite işlem öncesi/sonrası aynıdır. Türetmeler kaynak veritabanına yazılmadı. Mevcut arşiv tanımları bu sprint için yeterliydi; canlı ETABS, COM, birim değiştirme, model kaydetme, tasarım veya yeni analiz yapılmadı. Kaynağın SHA ile korunması, analiz neslinin mühendislik açısından nitelendirildiği anlamına gelmez.

## 2. Native spektral birleşimlerin bağımsız yeniden hesabı

Arşivdeki 87 kolon, 402 tam native kesit anahtarı ve 35 birleşim incelendi. Altı statik Linear Add yolu değişmedi; 24 spektrum içeren doğrudan Linear Add birleşim yeniden hesaplandı. Beş Envelope operatörü tasarım işaret adayı üretimine alınmadı.

| Sayısal hedef | Gerçekleşen |
| --- | ---: |
| Desteklenen spektral birleşim | 24/24 |
| Max/Min çifti | 9.648/9.648 |
| Kayıtlı Max/Min satırı | 19.296/19.296 |
| Bağımsız bileşen karşılaştırması | 115.776 |
| Tolerans dışı bileşen | 0 |
| Eksik, yinelenen veya belirsiz çift | 0 |
| En büyük kuvvet farkı | 1,058 × 10⁻¹² kN |
| En büyük moment farkı | 4,505 × 10⁻¹³ kN·m |

Hesap, basılı/yuvarlanmış tablo sonuçlarından değil native çağrı satırlarından üretildi. Statik merkez işaretli katsayılarla, spektral yarıçap simetrik bileşen büyüklükleriyle kuruldu. Negatif statik katsayı işareti korunur; simetrik spektral bileşenin negatif katsayısı Max/Min uçlarını değiştirir ve yarıçapa mutlak katsayıyla girer. Gerçek kaynak `Max` ve `Min` değerleri her bileşen için ayrı ayrı karşılaştırıldı. Aritmetik `Fraction(str(native_value))` üzerinden yürür; tolerans `atol=10⁻⁹`, `rtol=10⁻¹²` olarak korundu.

`Obj`, `ObjSta`, `Elm`, `ElmSta`, yük durumu ve adım kimliği birlikte kullanılır. İstasyon yuvarlama, en yakın satır seçimi, çift kayıtları sessiz birleştirme veya eksik değeri sıfır yapma yoktur. Altı signed native bileşen; kaynak satırı, çağrı/shard kimliği, birimler ve kaynak SHA bağı sonuçta tutulur. Tam forensic dışa aktarım her bileşenin kaydedilmiş, yeniden hesaplanmış, fark ve tolerans değerini içerir.

Desteklenmeyen iç içe/nonlineer operatör, eksik case tanımı, farklı eleman/istasyon, yinelenen Max/Min ve sonlu olmayan sayılar bağımsız negatif testlerde reddedilir. Altı statik birleşim bu doğrulama yoluna dönüştürülmedi.

## 3. Üç ayrı kuvvet anlamı ve işaret adayları

| Tip | Anlam | Yetki |
| --- | --- | --- |
| `PhysicalStaticForceState` | Aynı statik durum/adım/kesitte işaretli kuvvet vektörü | Kaynak statik vektörü; tasarım kabulü ayrı |
| `SpectralComponentEnvelope` | Her bileşenin istatistiksel Max/Min sınırı | Eşzamanlı fiziksel N–M2–M3 değildir |
| `CodeDesignDemandCandidate` | Açık politika altında kurulmuş tasarım kontrol adayı | Koşullu tasarım zarfı; fiziksel eşzamanlılık veya normatif kabul değil |

Her uygun Max/Min çifti için sekiz P–M2–M3 işaret adayı üretildi: **77.184 aday**. İşaretler native çekme-pozitif P üzerinde tanımlıdır; PMM girişinde **N=−P**, basınç pozitif dönüşümü açıkça uygulanır. N–M2–M3 dışındaki bileşenlere hayali fiziksel eşzamanlılık veya kapasite kesmesi yetkisi verilmez.

Kayıtlı RSX/RSY tanımlarının global U1/U2 doğrultuları ve gerçek katsayıları korundu. Arşivdeki 24 birleşimde %100/%30 katsayı örüntüsü ve sekiz karşılıklı hâkim doğrultu grubu doğrulandı. Bu katsayı alt koşuludur; birleşim adlarının `Cap`, `Crack` veya başka bir metin içermesi yönetmelik uygulanabilirliği sayılmaz. %100/%30, spektrum ölçeği ve ortak çarpanlar yeniden uygulanmadı.

Aday kimliği, yalnız satır adlarını değil zarfın tüm kaynak içeriğini de kapsar. Bağımsız incelemede bulunan içeriği değiştirip eski kimlikleri koruma ve eksik kapsamı özet alanı üzerinden yükseltme açıkları kapatıldı. Statik içerik, zarf içeriği, aday nüfusu, replay ve türetme özetleri PMM öncesi tekrar bağlanır.

## 4. Mevcut VS25 PMM çekirdeğiyle koşullu sonuçlar

Yeni kapasite motoru yazılmadı. VS25'in sabit N ve sabit moment doğrultusunda şekil değiştirme uyumlu solver'ı ve mevcut üç donatı önerisi kullanıldı. **77.184 × 3 = 231.552 değerlendirme**, 154.368 farklı tam sayısal problem olarak çözüldü. Memoization aday kimliğini veya çıktı nüfusunu azaltmaz. İkinci mertebe momenti ve minimum dışmerkezlik eklenmedi.

İlk tam Linux koşusu yaklaşık **671 saniye** sürdü. Arayüz ilk hesapta bu maliyeti taşır; aynı süreçte sonraki sayfalar doğrulanmış önbelleği kullanır. Sunucu yeniden başlatıldığında kalıcı türetme veritabanı olmadığı için hesap tekrar gerekir. Teslimdeki hazır HTML sayısal sonucu yeniden hesaplatmadan incelemek içindir.

| Öneri | Değerlendirme | Yüzey içinde | Yüzey aşımı | Sayısal belirsiz | Aşım görülen farklı kolon | En büyük çözülen oran |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 16Φ24 | 77.184 | 77.074 | 108 | 2 | 5 | 1,435605327 |
| 16Φ28 | 77.184 | 77.172 | 10 | 2 | 3 | 1,071795114 |
| 16Φ32 | 77.184 | 77.184 | 0 | 0 | 0 | 0,842511511 |

**118 aşım, değerlendirme satırı sayısıdır; 118 ayrı kolon değildir.** Her öneri kendi koşullu nüfusunda değerlendirilir. 16Φ32 nüfusunun hesaplanan yüzey içinde kalması, donatının seçildiği veya binanın uygun olduğu anlamına gelmez.

En büyük çözülen oran: **kolon 127**, `Cap_SeisY_UpSoil`, `Obj=127, ObjSta=0, Elm=127, ElmSta=0`, `P+1_M2+1_M3+1`, 16Φ24. Kuvvetler **N=−414,676265919 kN**, **M2=555,198107039 kN·m**, **M3=1.267,149546227 kN·m**; koşullu PMM oranı **1,435605327**. Negatif N burada çekmedir; mutlak değere çevrilmedi. Bu değer doğrulanmış nihai tasarım talebi veya fiziksel kolon göçmesi hükmü değildir.

Dört `NEAR_NUMERICAL_SURFACE_BOUNDARY` kaydı `NUMERIC_UNRESOLVED` kaldı: kolon 127/16Φ28 için `Cap_SeisY_Up` altında iki işaret, kolon 139/16Φ24 ve kolon 151/16Φ24 için birer işaret. Sıfır veya PASS yapılmadılar; çözülmüş en büyük oranın yanında görünür tutulurlar.

Kritik seçim, bütün üretilen kesit/birleşim/işaret adayları arasındaki **en büyük çözülen sonlu radyal oran** esasına dayanır. Sekiz köşenin, olası bütün ara eksenel kuvvet değerlerinden daha elverişsiz olduğu kanıtlanmadı. Bu yüzden `continuous_axial_envelope_complete=False`; bütün sonuçlar `CONDITIONAL` kalır.

Üç önerinin maksimumu ve dört belirsiz kayıt için mevcut bağımsız şerit/Gauss integrasyonu referansı tekrar çalıştırıldı: **7/7 seçili sayısal karşılaştırma uyumlu**. En büyük kapasite farkı yaklaşık `0,000143257 kN·m`; mevcut `0,001 + 0,002×kapasite` bütçesi değiştirilmedi. Bu yedi kontrol, 231.552 değerlendirmenin tamamına bağımsız oracle doğrulaması verilmiş sayılmaz; dört birincil belirsiz statü korunur.

## 5. Eski sonuçların korunması ve SHA kaydı

Altı statik birleşimin **2.412 kuvvet vektörü ve 7.236 PMM değerlendirmesi** tekrar çalıştırıldı. On beş eski türetmenin tamamının sonuç kimliği VS25 ile aynı kaldı; 261 seçili bağımsız PMM karşılaştırması da korundu. Eski statik maksimum **0,40891027311777534**, kolon 136/16Φ24/`Soil_Ult` olarak aynıdır. Yeni 1,435605327 farklı bir talep nüfusundandır; eski hesap üzerine keyfî büyütme uygulanması değildir.

| Yeni türetme | Sonuç SHA-256 |
| --- | --- |
| Spektral native replay | `13d908ffa544a2629ac355463c84f0c2689774519e7cf3974268a421320b4424` |
| Tasarım işaret nüfusu | `31bbde08fd7879db2e185be7ca9a3c0f62ef1650c95c55bc98a37a9d0303e746` |
| Koşullu spektral PMM | `3ac3b0190858027bee19d81a8acb71a122fbac1e4038999280c4443bf8c8ca9a` |
| Golden regresyon kapısı | `8abd607c92655b66dcaea2d857b8a6f1901fc09a7e4497eeb01d0e1129f2b965` |

Kaynak ZIP, SQLite, 15 eski sonuç kimliği, korunan 19 çekirdek/kaynak dosyasının önce/sonra SHA'ları ve güncel değişiklik dosyalarının SHA'ları [VS26_RESULT_SHA_LEDGER.json](VS26_RESULT_SHA_LEDGER.json) içindedir. Golden kapısının eklenmesi üç spektral hesap kimliğini değiştirmedi; sunum ve forensic doğrulama içeriği genişledi.

## 6. Yeni zorunlu golden rapor kapısı

[Column-Engine GOLDEN_EVIDENCE](https://github.com/feridunfc/Column-Engine/blob/df754b202415a58508f60b27d96f731a7b840041/tbdy_column_workflow/recipe_v11/GOLDEN_EVIDENCE.json) ve [RULE_CARDS](https://github.com/feridunfc/Column-Engine/blob/df754b202415a58508f60b27d96f731a7b840041/tbdy_column_workflow/recipe_v11/RULE_CARDS.json) sabitlendi. Dört gerçek PDF ve iki eski audit ZIP'in tam dosya hash'leri doğrulandı; kritik rapor tabloları görsel olarak incelendi. Büyük PDF'ler Git'e/ETABS veritabanına kopyalanmadı. Küçük iki eski audit ZIP, seçili sayfa dökümleri ve kaynak kayıtları yaklaşık 146 kB'lık yeniden kullanılabilir banka olarak taşındı.

- GOLDEN-01'in **23 sayısal/boole karşılaştırması** özgün üç unittest metodu içinde korunup çalıştırıldı. Bağımsız `calculate` fonksiyonu birebir korundu.
- GOLDEN-02'nin **yedi özgün unittest metodu** korunup çalıştırıldı. Test gruplarının her biri yeni kapıda izlenebilir.
- Üretim çağrısı, bağımsız aritmetik, rapor ve açıklamayı birlikte tutan kapıda **44 kayıt: 13 `NUMERICAL_MATCH`, 4 `ENGINEERING_INTERPRETATION_DIFFERENCE`, 27 `INSUFFICIENT_SOURCE`** vardır. Bunlar 44 yeni golden rapor testi olarak sunulmaz.
- Gerçek YENI karşılaştırmaları 12Ø14 alanı, geometrik alan/birleşim sınırları, basılı SCWB kapasitelerinin toplamı ve bireysel/kat β aritmetiğini kapsar. SCWB toplam uyumu, kapasitelerin türetilmesi veya gerçek birleşim topolojisinin doğrulandığı anlamına gelmez.
- SZ01 için bireysel β≈1,549351615, rapordaki bireysel 1,55 ile uyumludur. Rapordaki “Alındı” 1,85, β×βs aritmetiğine uyar; YENI nihai çarpanı `None / EQ729_DECISION_NOT_PROVEN` tutar. Bu ayrı büyüklükler birbirine karıştırılmaz; açıklanamayan aritmetik sapma yorum farkı sınıfına atılamaz.
- GOLDEN-02 zemin α≈0,6262267 ve GOLDEN-01 A15/perdesiz sistem uyarısı negatif kaynak referansı olarak korunur. Tek kolonda donatı artırma veya otomatik 1/α büyütmesi kabul yaratmaz.
- GOLDEN-03/04'ün kaynakları doğrulandı; tamamlanmış rapor temelli hesap testleri varmış gibi gösterilmedi.

[Column B7 kaynakları](https://github.com/feridunfc/Column/blob/9269a00f5f5471ab68413c039912cafb2cf4db39/tests/test_b7_oracle_matrix.py) ayrı sayısal banka olarak kullanıldı. İki eski 400×600 mm kafes, N=500 kN ve 0°/45°/90° olmak üzere altı mevcut durum tekrar kullanıldı: dört aynı-model uyumu; iki durumda eski noktasal çubuk beton çıkarımı ile VS25'in sürekli disk çıkarımı ayrıldı. Eski M3 işareti açık dönüştürüldü. Model farkı bulunan iki durumda mevcut bağımsız sürekli-disk referansı YENI'yi ayrıca kontrol etti. B7 sentetik verileri rapor PMM golden'ı sayılmaz; bütün eski B7 test paketinin YENI üzerinde birebir çalıştırıldığı iddia edilmez.

**Golden kabul kapısı kapanmadı.** Özellikle rapora bağlı tam PMM geometrisi ve referansı, gerçek ikinci mertebe seçimi/aktarımı, kapasite kesmesi ve tam kat α yolu eksiktir. Bağımsız denetçi banka/karşılaştırma altyapısını kapsamıyla kabul etti; mühendislik hesaplarının tamamlanmış olduğunu kabul etmedi. Ayrıntılar [VS26_GOLDEN_REGRESSION.html](VS26_GOLDEN_REGRESSION.html), [JSON](VS26_GOLDEN_REGRESSION.json) ve [tam kaynak yeniden hash kaydı](VS26_GOLDEN_SOURCE_REHASH.json) içindedir.

## 7. UI, CLI ve dışa aktarım

**Kolonlar → Kuvvetler ve birleşimler → Depremli tasarım talebi** görünümü; seçilen donatı için kolon başına kritik birleşim, tam kesit/eleman, işaret, N/M2/M3, öneri, koşullu oran ve belirsizliği gösterir. “Senaryoları aç” ilgili kolon/birleşime iner. Kaynak ayrıntıları açılır bölümdedir. Golden kapsamı ve kabul blokajı görünürdür.

İlk gerçek-model JSON'u **205.291 byte**, 87 kolon özetidir; 77.184 aday ve 231.552 değerlendirme ilk yüklemede indirilmez. Aday görünümü 200 satırlık sayfa, API üst sınırı 500 satırdır. UI, CLI, JSON ve HTML aynı production projection'ı kullanır. Sayfa JSON/HTML dışa aktarımı seçili filtreye aittir. Tam forensic ZIP ayrı uçtur ve filtre/paging parametrelerini reddeder.

Tam forensic export bu koşuda **156.554.643 byte**, SHA-256 **`460437d13045a9c6b94697edf490fcf4444cf8beaf913866492d12d5a7de50e6`** olarak üretildi. İçindeki her dosyanın byte sayısı ve SHA'sı yeniden okuma ile doğrulandı. Native ZIP yerine geçmez ve Git/veritabanına eklenmedi. Scalar replay, fiziksel statik kayıtlar, spektral zarflar, tasarım adayları, bütün PMM değerlendirmeleri, sayısal kanıtlar ve golden kapısı ayrı dosyalardadır.

```bash
python -m tbdy_next.cli inspect-column-demands --out .receipts --run-id RUN_ID --spectral
python -m tbdy_next.cli inspect-spectral-design --out .receipts --run-id RUN_ID --cage '16Φ24'
python -m tbdy_next.cli inspect-spectral-design --out .receipts --run-id RUN_ID --member 127 --candidates --limit 200 --html kolon127.html
python -m tbdy_next.cli inspect-spectral-design --out .receipts --run-id RUN_ID --forensic vs26_forensic.zip
python -m tbdy_next.cli inspect-golden-regression --html golden.html
python -m tbdy_next.cli inspect-golden-regression --require-complete
```

Son komut, mevcut zorunlu golden kapsamı tamamlanmadığı için **çıkış kodu 3** verir. Sayısal bozukluk/kaynak değişimi ayrıca hata üretir. Normal inceleme komutunun başarıyla JSON üretmesi mühendislik kabulü değildir. Dışa aktarım dosyaları var olan dosyanın üzerine yazılmaz. Tam PDF/ZIP hash'lerini yeniden denetlemek için golden komutuna orijinal dosyaların dizini `--source-dir` ile verilebilir.

## 8. Testler ve bağımsız inceleme

| Kontrol | Sonuç / kapsam |
| --- | --- |
| Tüm Python regresyonları | **1.015/1.015**, 68,177 s |
| Mevcut ve yeni Node UI kontrolleri | **9/9 script** |
| Son golden UI yetki/hash düzeltmesi | 10 HTTP/HTML testinin ve VS26 design Node scriptinin hedefli yeniden koşusu başarılı |
| Golden banka testleri | 13/13; özgün 23 karşılaştırma + 7 test içeride yeniden çalışır |
| Bağımsız kaynak/işaret/PMM çekirdek denetimi | Kaynak bağları ve 20 aday/PMM testiyle kapsamı sınırlı kabul |
| Golden bağımsız denetimi | Kaynak, üç sınıf ve yetki sınırları için kapsamı sınırlı kabul; iki UI/HTML koruma bulgusu kapalı |
| Paketleme | Offline wheel üretimi ve paketin içinden golden banka okuma başarılı |
| Sözdizimi/çalışma ağacı | compileall, node --check, git diff --check başarılı |

Gerçek tarayıcıyla piksel incelemesi bu Linux ortamında tamamlanamadı: Chromium process-singleton `socket() failed: Operation not permitted` hatasıyla açılmadı. DOM davranışı, HTTP, HTML, filtre/paging, kaçış ve kaynak/yetki sözleşmeleri test edildi. Gerçek Windows UI ve canlı ETABS kaynak kabulü Supervisor aşamasında kalır.

## 9. VS25 CI bulgusu — ayrı açık konu

Aynı HEAD'in [push koşusu 42672806070](https://github.com/feridunfc/YENI/actions/runs/42672806070) Linux 3.11/3.12 ve Windows ile başarılı. [PR koşusu 42672817318](https://github.com/feridunfc/YENI/actions/runs/42672817318) genel olarak `failure`; dönen iki PR Linux check'i başarılıdır, PR için Windows check kaydı dönmemiştir. Bu gözlem Windows testinin başarısız olduğunu kanıtlamaz. Eldeki kayıtlarla genel failure'ın kök nedeni **`NOT_PROVEN`** kaldı; “CI düzeldi” sonucu verilmedi.

Windows işi ve mevcut kontroller korunmuştur; VS26 testleri eklenmiştir. Yeni hash-sabitli golden metinleri için Git LF checkout niteliği tanımlanmıştır; Windows'un otomatik CRLF dönüşümü kaynak SHA'larını değiştirmemelidir. Bu yeni banka için taşınabilirlik önlemidir, VS25 PR failure'ının açıklaması değildir. [VS26_CI_AUDIT.json](VS26_CI_AUDIT.json) yayından önceki CI gözlemini kaydeder; yeni VS26 uzak koşusu dal yayını sonrasında ayrı izlenir. Codespaces/Linux tekrar girişi `bash tools/test_vs26_offline.sh` komutudur; Python, dokuz Node scripti ve eksik golden kabul kapısının korunmasını denetler. Bu komut 87 kolonlu native arşiv tekrarının yerine geçmez.

## 10. Kabulü açık tutan mühendislik bağımlılıkları

1. Analiz nesli, model/sonuç eşleşmesi, modal kapsam, ölçekleme ve aktif analiz koşulları henüz nitelendirilmedi.
2. CSI işaret permütasyonu konvansiyonu tek başına TBDY 4.4.2/4.4.3/4.4.4, 4.10 ve Ek 4B uygunluğu sağlamaz. Yük rolleri ve hangi birleşimin hangi tasarım kontrolüne ait olduğu doğrulanmalıdır.
3. `EDZ` katsayısı, spektrum parametreleri, aktif sönüm yöntemi, düşey deprem uygulanabilirliği ve ortak 2,5 çarpanının yetkisi açık kaldı; isimlerden karar verilmedi.
4. Gerçek `ln/k/lk`, Cm/kat stabilitesi, global P–Δ/yerel P–δ kapsamı, minimum dışmerkezlik ve moment aktarımı tamamlanmadı.
5. Sekiz işaret köşesinin ara eksenel kuvvet durumlarını kapsadığı kanıtlanmadı; dört PMM sınır belirsizliği açık kaldı.
6. Öneri donatılar gerçek seçilmiş donatı veya tüm detay kurallarıyla onaylanmış tasarım değildir; SCWB–Ve ve kat α tam bina kabulü bu sprintte kapatılmadı.
7. Rapor golden bankası tam algoritma kabulüne yetmiyor; açık alanlar zorunlu gate kapsamında korunur. 87 kolonlu ETABS kaynak replay'i bu gereksinimin yerine geçmez.
8. Tarihsel 342 tam istasyon eşleşmesi olmayan tasarım referansı ve 144 çift istasyon kaydı bu sprintte düzeltilmiş sayılmaz. Yeni adaylar doğrudan tam native kesit anahtarıyla kurulmuştur.

Yöntem ve birincil referanslar [VS26_DESIGN_ENVELOPE_METHOD_TR.md](VS26_DESIGN_ENVELOPE_METHOD_TR.md); okunabilir gerçek-model görünümü [VS26_RESULTS_16phi24.html](VS26_RESULTS_16phi24.html); bütün sayısal özet ve seçili bağımsız sonuçlar [VS26_NUMERICAL_RESULTS.json](VS26_NUMERICAL_RESULTS.json) içindedir.
