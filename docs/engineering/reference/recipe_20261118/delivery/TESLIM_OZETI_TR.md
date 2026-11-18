# YENI reçete ve örnek bankası — entegrasyon teslim özeti

**18 Kasım 2026.** İngilizce teknik reçete, 73 kontrol eşlemesi ve korunmuş örnek bankası; kaynak, sürüm ve doğrulama sınırları açık bir teslim paketine dönüştürüldü. PDF ve DOCX, aynı reçetenin 296 sayfalık okunabilir çıktılarıdır. Bu belge teslimi herhangi bir mühendislik kontrolünü kendiliğinden kapatmaz.

## 1. Hangi sürüm incelendi?

| Kayıt | Değer | İnceleme durumu |
| --- | --- | --- |
| Entegrasyon dalı | `baseline/local_import` | Dal adı sürüm kanıtı olarak kullanılmadı. |
| İncelenen yayımlanmış commit | `b255c3030c09c88a17bbec766fc2bb22682ad027` | Alınan kaynak dosyaları bu tam SHA'ya bağlıdır. |
| İncelenen Git tree | `9cf5b99059cd107a1e447c398fd1e93b7292b31b` | Kaynak envanterinde korunmuştur. |
| Kullanıcının bildirdiği son doğrulanmış yerel commit | `a2e26b664d9b2b217e828de2c1df0c3df26068b1` | `NOT_INSPECTED` |
| Bunun üzerindeki tamamlanmamış yerel değişiklikler | Erişilemedi | `NOT_INSPECTED` |

142 alınmış dosyanın SHA-256 ve Git blob kimlikleri kayıtlıdır. 88 ayrı kaynak sembolü dosya içeriği ve AST üzerinden doğrulanmıştır. Bu, dosyalardaki her dalın anlamsal denetimi veya yerel çalışma ağacının incelenmesi anlamına gelmez. Yerel ilerlemeyi eski yayımlanmış sürüme döndürme önerisi yoktur.

## 2. Sayılar birbirine karıştırılmadı

| Kapsam | Adet | Anlamı |
| --- | ---: | --- |
| Korunan özgün kontrol kimliği | 73 | 5 SRC ve 68 mühendislik kimliği; kimlikler yeniden numaralandırılmadı. |
| Birincil örnek | 73 | Her özgün kontrol için bir örnek. |
| Ek adaptör sözleşme örneği | 12 | Getter/setter, kapsam ve revizyon davranışı; yeni CHECK değildir. |
| Reçete bankasının aritmetik iddiası | 333 | 85 örneğin sabit bağımsız hesapları; bu teslimde yeniden çalıştırıldı. |
| Ayrı tarihsel PDF V2 bankası | 467 | Bunun eski karşılaştırılmış 333 kayıtlık alt kümesi ayrı tutuldu; burada yeniden çalıştırılmadı. |
| Korunan tarihsel üretim karşılaştırması | 44 | Yeni bankayla değiştirilmedi; bu teslimde yeniden çalıştırılmadı. |
| Yeni sınırlı üretim fonksiyonu karşılaştırması | 3 | İncelenen commit'teki iki mevcut fonksiyondan üç büyüklük. |
| Ek öncelikli zincir örneği | 1 | 1.294 bağımsız aritmetik iddiası; 73 başlığa ek CHECK değildir. |
| DAG kataloğu | 94 | 30 düğüm 22 kayıtlı aşamayla ilişkili; uygunluk yüzdesi değildir. |

`CHECK_MAPPING.json` içinde 44 kontrol başlığı için **kısmi** kaynak/büyüklük bağlantısı doğrulandı; 29 kontrol kapsamı `UNMAPPED` kaldı. Bu 44 sayısı tarihsel 44 üretim karşılaştırmasıyla aynı küme değildir. Güncel yerel sürümdeki bütün bağlantılar erişim sınırı nedeniyle `UNMAPPED` ve `NOT_INSPECTED` olarak korunur.

## 3. Bu teslimde gerçekten çalıştırılanlar

| Doğrulama seviyesi | Sonuç | Sınır |
| --- | --- | --- |
| Belge ve şema tutarlılığı | `VALID` | 5 şema, kimlikler, kaynak bağlantıları, 142 dosya hash'i, 88 sembol ve 6 olumsuz sözleşme denemesi. |
| Bağımsız örnek aritmetiği | `333/333 MATCH` | Reçete bankası; YENI veya canlı ETABS testi değildir. |
| Bağımsız öncelikli zincir aritmetiği | `1294/1294 MATCH` | Tek sentetik örneğin belirtilmiş varsayımları altında. |
| Gerçek YENI hesap sahibiyle karşılaştırma | `3/3 MATCH_LIMITED_SCOPE` | Yayımlanmış commit'te `section_axial_limits_kn` ve `minimum_eccentricity_mm`; tam kontrol kapanışı değildir. |
| Erişilemeyen yerel hesap sahibiyle karşılaştırma | `NOT_RUN` | Yerel commit ve değişiklikler incelenmedi. |
| Kaydedilmiş kaynakla pipeline tekrarı | `NOT_RUN` | Mevcut `EnginePipelineRunner` bu teslimde proje kaynağıyla çalıştırılmadı. |
| Canlı ETABS kaynak doğrulaması | `NOT_RUN` | Canlı bağlantı, model değişikliği, analiz veya native geri okuma yapılmadı. |
| Mühendislik kabulü | `NOT_RUN` | Belge teslimiyle kapanan mühendislik kontrolü: **0**. |

Komutlar, ortam, araç/kaynak hash'leri, sonuçlar ve sınırlar `VERIFICATION_RESULTS.json` ve `evidence/` altında bulunur. 296 PDF sayfası tek tek görsel olarak denetlendi; 73 kontrol ve 85 örnek kimliğinin PDF/DOCX içindeki varlığı, 31 içindekiler girdisi ve sayfa sınırları kontrol edildi.

## 4. Korunan tarihsel 44 kayıttaki fark

İncelenen `docs/VS26_GOLDEN_REGRESSION.json` içinde 13 sayısal eşleşme, 27 yetersiz kaynak ve 4 yorum farkı vardır. Daha sonraki EV-GOLDEN ledger kaydı 15/25/4 bildirir. İkisi de 44 kayıtlı kapsamdır; ancak sonraki değişikliği satır satır açıklayan rapor incelenen dosyalar arasında yoktur. Her iki gözlem özgün hash ve sürüm bağlarıyla korunmuştur. Birbirlerinin yerine geçirilmemiş ve yeni çalıştırma olarak sunulmamıştır.

## 5. Öncelikli yöntem zinciri

`PRIORITY_CHAIN.json`, ortak model/kaynak/analiz nesli/kesit kimlikleriyle şu sıralamayı izler:

1. Modal sayısal hassasiyet ve yakın iptal tanığı.
2. Uygulanmış artı/eksi ek dışmerkezliğin dengeli etkileri.
3. CQC modal birleşimi ve açık yönsel birleşim tanımları.
4. SCWB için kapasiteyi belirleyen eksenel talep.
5. Kat kesmesi paylaşımı.
6. Donatı/kapasite girdisi revizyonlarıyla α iterasyonu.

Örnek; 128 işaretli modal satır, 64 skaler birleşim tanımı ve 32 SCWB sınıflaması içerir. Açıkça sınırlanmış orantılı modal alan örneğinde α = 211/240 = 0,8791666667 ve talep büyütmesi 240/211 = 1,1374407583 elde edilir. Bu sayılar kullanıcının yapısına ait değildir.

Kapasite eğrileri bu örnekte tanımlı bağımsız girdilerdir; çözülmüş fiziksel betonarme kafes kapasitesi gibi sunulmaz. Genel orantısız spektral kat kesmesi paylaşımı ve gerçek modelin eksik fiziksel girdileri açıkça listelenmiştir. Spektral Max/Min bileşenleri eşzamanlı kuvvet vektörü sayılmaz. Sekiz köşenin yeterliliği; talep kümesinin içerilmesi, sabit ve konveks dayanım kümesi, tam aralıkta geçerli dönüşüm kanıtı şartlarıyla tarif edilmiştir. Doğrusal olmayan dönüşümde yalnızca köşe değerlerine bakmanın yetersiz olabileceği karşı örnek de vardır.

## 6. P–Delta, birleşimler ve donatı bağımlılıkları

Reçete; native başlangıç P–Delta ayarını, doğrusal olmayan rijitlik durumunu, kat düzeyinde global ikinci mertebe kontrolünü ve kolonun yerel ikinci mertebesini ayrı etki ve kaynak kimlikleriyle ele alır. Aynı etkinin iki kez büyütülmesini önleyen bağlar tariflidir.

Tasarım birleşimi grupları, beklenen eleman × birleşim × kesit kapsamını belirler. Eksik TBDY birleşimleri için katalog okuma, beklenen tanımla fark, seçilmiş hazırlama işlemi, setter dönüş kodu ve getter ile eşdeğer geri okuma, gerektiğinde yeniden analiz ve yeni nesle bağlı kuvvet alımı akışı tanımlanmıştır. Aynı isim farklı tanımı örtemez. Native kurulu sürüm davranışı canlı kabul çalışması gerektirir.

SCWB, kapasite kesmesi, birleşim bölgesi ve PMM; ortak aday/gerçek/seçili donatı revizyonunu kullanmalıdır. Donatı değişikliği kapasite ve bağlı sonuçları geçersizleştirir; kesit/rijitlik değişikliğinin analiz nesline etkisi ayrıca değerlendirilir. ETABS şablon donatısı, onaylı gerçek kafes veya seçilmiş tasarım gibi sunulmaz.

## 7. Entegrasyon sırası

1. `tools/inspect_local_binding.py` ile gerçek yerel HEAD, dal, ilgili değişmiş/izlenmeyen dosya hash'leri ve sembol imzalarını salt okunur olarak kaydedin. Çıktı özel yerel kanıttır; otomatik yöntem onayı değildir.
2. İncelenen snapshot ile yerel dosya/fonksiyon farklarını değerlendirin. Erişilemeyen yerel bağlantıları ancak gerçek inceleme sonrası güncelleyin.
3. Banka girdilerini mevcut hesap sahiplerine bağlayan adaptörleri tamamlayın. JSON formül metnini çalıştırmayın. Bağımsız oracle ile üretim aritmetiğini ortaklaştırmayın.
4. Mevcut 44 üretim karşılaştırmasını koruyarak yeni örnekleri ve dört senaryo türünü gerçek sahiplerle karşılaştırın. Tanımlı olmayan senaryoların durumunu açık bırakın.
5. Aynı mevcut runner üzerinden kayıtlı kaynakla tam kapsam ve sonuç envanteri tekrarını çalıştırın.
6. Canlı ETABS mevcut olduğunda getter/setter, seçim geri yükleme, birleşim kapsamı, analiz nesli ve kesit tarafı doğrulamalarını aynı mevcut bağlantı üzerinden tamamlayın.
7. Mühendislik kabulünü bağımsız ve yetkili karar olarak kaydedin.

## 8. Dosyalar ve dağıtım

Yayımlanabilir paket; `RECIPE.md`, `RECIPE.pdf`, `RECIPE.docx`, `CHECK_MAPPING.json`, `GOLDEN_CASES.json`, `SOURCE_MANIFEST.json`, `VERIFICATION_RESULTS.json`, `PRIORITY_CHAIN.json`, `REVISION_NOTES.md`, beş JSON şeması, doğrulama araçları ve yeni kanıt kayıtlarını içerir.

Ayrı özel kanıt paketi; özgün raporlar, çalışma kitapları, kaynak atlası, eski banka/kanıtlar, erişim kayıtları ve incelenen yayımlanmış kaynak dosyalarını içerir. Özgün 18 golden kaynağının tamamı korunmuştur. Eski kayıtlarda adı geçen fakat alınamayan 23 makbuz yolu `NOT_AVAILABLE` olarak belirtilmiştir; var olmayan dosya incelenmiş sayılmamıştır.

Üretim kodu değiştirilmedi. İkinci solver, pipeline veya ETABS bağlantısı oluşturulmadı. Paket, mevcut yerel ilerlemenin üzerine sürüm kontrollü entegrasyon için kanıt ve sözleşme sağlar.
