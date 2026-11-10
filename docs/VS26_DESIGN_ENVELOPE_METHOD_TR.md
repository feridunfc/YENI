# VS26 — Depremli tasarım zarfının yöntemi ve yetki sınırı

## 1. Hesabın anlamı

VS26, kaydedilmiş ETABS spektrumlu birleşimlerini çevrimdışı tekrarlar; eşleşen bileşen sınırlarından açık bir CSI işaret politikasıyla koşullu PMM adayları üretir. Bütün işlem mevcut kaynak ZIP’i ve salt okunur SQLite üzerinden yürür. Yeni analiz, COM çağrısı, ikinci mertebe hesabı veya otomatik donatı seçimi yapılmaz.

| Sürüm 1 veri tipi | İçerik | İzin verilen anlam |
| --- | --- | --- |
| `PhysicalStaticForceState` | Aynı native vaka/birleşim, adım ve kesitte altı işaretli bileşen | Gerçek statik kaynak vektörü; analiz nesli ve tasarım kabulü ayrıca açık |
| `SpectralComponentEnvelope` | Altı bileşenin ayrı `C−A / C+A` sınırları, iki native adım ve bütün kaynak katkıları | İstatistiksel bileşen zarfı; eşzamanlı N–M2–M3 vektörü değildir |
| `CodeDesignDemandCandidate` | Belgelenmiş politika altında kurulmuş N, M2, M3; kaynak birleşimi, kesit, işaret ve içerik kimliği | Koşullu tasarım kontrolü girdisi; fiziksel analiz durumu veya normatif onay değildir |

Tipler donuktur. PMM aktarımı yalnız `CodeDesignDemandCandidate` kabul eder; sözlük, statik tip veya spektral zarf sessizce dönüştürülemez. V2, V3 ve T, adayın eşzamanlı kesme/burulma değerleri gibi eklenmez; kendi bileşen zarfında kalır.

## 2. Native birleşimin bağımsız tekrarı

Desteklenen tarif, **doğrudan Linear Add** içinde native tip 1 statik ve tip 4 response-spectrum vakalarıdır. Her statik yaprakta `Single Value / StepNum=0`, her spektrum yaprağında negatif olmayan `Max / StepNum=0`, hedef birleşimde ise birer `Max` ve `Min` gerekir. Eksik, fazla veya çift adım tekilleştirilmez. İç içe birleşimler, diğer operatörler, aynı yaprağın tekrarı, çözülmemiş vaka türü ve uygunsuz adımlar açık kapsam nedeni bırakır.

Her native bileşen için:

\[
C_j=\sum_{s\in\mathrm{statik}}a_s F_{s,j},\qquad
A_j=\sum_{r\in\mathrm{spektrum}}|a_r|S_{r,j},\qquad
F_{j,\min}=C_j-A_j,\quad F_{j,\max}=C_j+A_j.
\]

Statik katsayıların işaretleri korunur. Negatif spektrum katsayısı, simetrik bileşen aralığının yarıçapını negatif yapmaz. Kaydedilmiş negatif bir spektral `Max` genliği ise mutlak değer alınarak düzeltilmez; bu tarifin dışında bırakılır. Her hesaplanan sınır, **ayrı kaydedilmiş native birleşim çıktısıyla** karşılaştırılır. Yapraklardan üretilen değer kendisinin doğrulama hedefi değildir.

Aritmetik, kaynak sayılarının ondalık gösteriminden `Fraction` ile kurulur. Kabul bütçesi mevcut statik tekrardaki gibi `1e−9 + 1e−12 × max(|hesap|, |native|)` olup kuvvetlerde kN, momentlerde kN·m birimindedir. Her bileşen/adım için gözlenen değer, hesap, mutlak fark, bütçe ve eşleşme sonucu saklanır.

Kesit anahtarı `(Obj, ObjSta, Elm, ElmSta)`; sonuç anahtarı ayrıca `(LoadCase, StepType, StepNum)` içerir. Yakın istasyon, yuvarlanmış istasyon veya uç seçimi yapılmaz. Aynı ObjSta’daki farklı analiz elemanları ayrı kalır. Native P çekme pozitiftir: gösterilen basınç pozitif N için `N_alt = −P_üst`, `N_üst = −P_alt` uygulanır. Gösterimdeki yuvarlama hesap ve kimliklerde kullanılmaz.

## 3. Sekiz tasarım işareti

Politika: `CSI_MAX_MIN_P_M2_M3_EIGHT_CORNERS_CONDITIONAL_V1`.

\[
N=-(C_P+s_P A_P),\qquad M_2=C_{M2}+s_2A_{M2},\qquad
M_3=C_{M3}+s_3A_{M3},\qquad(s_P,s_2,s_3)\in\{-1,+1\}^3.
\]

`P+1` etiketi **native P’nin üst sınırını**, dolayısıyla basınç pozitif N’nin alt sınırını seçer. İşaret kimliğini N işareti gibi yorumlamak hatalıdır. Sıfır genlikte bile sekiz politika kimliği korunur; eşit sayısal problemler yalnız kapasite çözücüsünün tam girdileri bakımından önbelleğe alınabilir.

Aday üretimi için kaynakta tek global U1 veya U2 doğrultusuna bağlı bir ya da iki spektrum gerekir. Yön tanımı eksik, yerel/döndürülmüş veya tekrarlı yön içeren tarifler skaler tekrarda görülebilir; bu sınırlı işaret politikasına otomatik alınmaz. Bu koşul analiz neslinin, modal kapsamın veya proje uygulanabilirliğinin kabulü değildir.

Gerçek kaynakta RSX/U1 ve RSY/U2; `Global`, sıfır açı ve kaydedilmiş ölçek 10 gözlenir. Birleşimlerin gerçek 1/0,3 veya 2,5/0,75 katsayıları **bir kez** kullanılır. Native sonuç zaten vaka ölçeğini içerir. Yeniden ölçekleme, ek 100/30 veya ortak katsayıyı D kabul edip ikinci kez büyütme yoktur. VS10’un mevcut tam katsayı ve eş yön kapsamı algoritmaları yeniden kullanılır; birleşim isimleri mühendislik rolü belirlemez.

CSI betonarme tasarım kılavuzunun §2.1 açıklaması, spektrum gibi çok değerli çıktılarda etkileşen kuvvetlerin maksimum/minimum permütasyonlarıyla tasarım yapılmasını anlatır. Bu genel yazılım konvansiyonu, burada kullanılan malzeme modelinin veya projenin TBDY uygunluğunun bağımsız kabulü değildir. [CSI kılavuzu](https://docs.csiamerica.com/manuals/etabs/Concrete%20Frame%20Design/CFD-ACI-318-08.pdf) · [CSI spektrum SSS](https://wikicsiamerica.atlassian.net/wiki/spaces/kb/pages/2006323/Response-spectrum+analysis+FAQ).

## 4. TBDY 4.4 ve Ek 4B ile ilişki

Resmî yönetmelik eki üzerinden 4.4.2–4.4.4 metinleri ve denklem görselleri kontrol edildi:

| Kural | Denetlenecek ilişki | VS26’nın yetki sınırı |
| --- | --- | --- |
| 4.4.2.1, Denk. 4.9 | `±EX ±0,3EY` ve `±0,3EX ±EY`; ayrıca 4.10 iç kuvvet esasları | Kaydedilmiş doğrultu katsayıları ve eş baskın yönler incelenir. Ortak çarpanın amacı ve PMM’de tasarıma esas alınması onaylanmaz. |
| 4.4.2.2 | Zaman tanım alanında iki yatay bileşenin birlikte uygulanması | Bu spektrum tarifine dönüştürülmez. |
| 4.4.3.1 | Belirtilen DTS/eleman koşullarında düşey modal hesap; R/I=1, D=1 | Açıklık/konsol, kirişe oturan veya eğik kolon koşulları bu sprintte sınıflandırılmaz. |
| 4.4.3.2, Denk. 4.10 | Uygun diğer kapsamda yaklaşık `EZ ≈ (2/3) SDS G` | Düşey etkinin kaynak rolü ve uygulanabilirliği ayrıca bağlanmalıdır. |
| 4.4.4.1, Denk. 4.11–4.12 | `G+Q+0,2S+EH+0,3EZ`; `0,9G+H+EH−0,3EZ` | G/Q/S/H/EZ rolleri ve seçilmiş tasarım birleşimleri isimden atanmaz. |
| Ek 4B.2 | Her davranış büyüklüğünün modal istatistiksel birleşimi; ardından doğrultu birleşimi | Bileşen maksimumları fiziksel eşzamanlı vektör olarak sunulmaz. Modal yöntem/kütle/ölçek ve analiz nesli kabulü açık kalır. |

Kaynak: [Resmî yönetmelik sayfası](https://www.aile.gov.tr/eyhgm/mevzuat/ulusal-mevzuat/yonetmelikler/turkiye-bina-deprem-yonetmeligi/) ve [yönetmelik eki](https://www.aile.gov.tr/media/vixjx01s/deprem_yonetmelik_eki.docx). İncelenen ekin SHA-256’sı `122b7eea53099c42b5cb080f0a6fcff89bdea445d2b0e9005e9e8acae557db5d`.

Kayıtlı EDZ vakasında üç sabit yük deseni için 0,351 katsayısı vardır; kayıtlı SDS=0,52578 ile `(2/3)SDS=0,35052` bulunur. Bu yakınlık, düşey deprem rolünü veya yuvarlamanın kabulünü kendiliğinden kanıtlamaz. Benzer biçimde bazı birleşimlerdeki LC_S katsayısı 1’dir; bunun tasarım rolü, Denk. 4.11’deki kar yükü katsayısıyla ilişkilendirilmeden önce kaynak tanımı ve proje amacıyla doğrulanmalıdır. VS26 bu kayıtları değiştirmez.

## 5. Mevcut VS25 PMM çekirdeği

Üç mevcut öneri (`16Φ24`, `16Φ28`, `16Φ32`) ve bunların kaynak kesit/malzeme bağları korunur. Yeni bir kapasite solver’ı yazılmadı. `section_capacity.py` içindeki **sabit N ve sabit moment doğrultusunda gerinim uyumlu kök** kullanılır. N kN→N; M kN·m→N·mm dönüşümü yalnız açık PMM aktarımında yapılır. Kayıtlı kuvvetlere hayalî büyütme veya minimum dışmerkezlik momenti eklenmez.

VS25’in 1 N eksenel artık, 1.000 N·mm doğrultu artığı ve mevcut kapasite karşılaştırma bütçeleri korunur. Kesit geometrisi, çubuk koordinatları ve malzemenin tümü sayısal problem anahtarına dahildir. Sayısal belirsizlik, sınır bandı veya eksenel aralık aşımı sıfır orana çevrilmez. Yalnız eksenel durumda eksenel kullanım, radyal PMM oranından ayrı kalır.

Kritik seçim, bütün üretilmiş adaylar içindeki **en büyük çözülen radyal oran**dır. Eşit kritiklerin sayısı ve tüm aday kayıtları korunur. Bir grubun çözülemeyen veya eksenel sınır dışı kaydı varsa küçük bir çözülen oran bu kaydı gizlemez; `numerical_selection_complete=False` kalır. Kaynak kapsamı eksikliği de sayısal seçim tamlığına yükseltilemez.

### Sekiz köşenin kanıtlamadığı husus

Bu sprint, iki eksenel uç arasında kapasitenin gerekli dışbükeylik/tekdüzelik özelliklerini ve tam talep kümesinin kapsanmasını ispatlamaz. Sonlu köşe örneklerinin kontrolü, ara N durumlarının daha elverişli olduğunu tek başına göstermez. Bağımsız test, gerçek kesitte daha küçük basınç kuvvetli köşenin kritik olabildiğini de gösterir. Genel mantık testindeki iç minimumlu örnek yalnız sonlu örneklemenin sınırını anlatır; betonarme malzeme modeli değildir.

Bu nedenle `continuous_axial_envelope_complete=False`, `engineering_status=CONDITIONAL`, `normative_qualification=NOT_PROVEN`, `final_design_eligible=False` bütün aday ve özetlerde korunur.

## 6. Kaynak bütünlüğü ve tekrar kullanılabilirlik

Native arşiv, manifest ve shard hash’leriyle doğrulanır. Skaler tekrarda tanımlar ve her kolonun kuvvet dizileri arşivden yeniden okunur. Aynı satır kimliğini koruyup yaprak ve hedef kuvveti birlikte değiştirmek kabul edilmez. Tipli zarfın içeriği ayrıca hash’lenir; aday kimliği bu hash’i içerir. PMM girişinde özet, replay, zarf, statik referans ve aday manifestleri yeniden denetlenir. Değiştirilmiş kapsam bayrağı eski sonuç kimliği altında kullanılamaz.

Yalnız bir süreç içi son tasarım sonucu saklanır; eşzamanlı HTTP isteklerinin aynı büyük hesabı birlikte üretmesi kilitle önlenir. Sayısal kanıtlar bellekte sıkıştırılır. Native ZIP ve SQLite’a yeni hesap satırı yazılmaz. Yeni bir importun run kimliği farklıysa, aynı sayısal kaynak için türetilmiş sonuç kimliklerinin değişmesi beklenir; mevcut kabul defteri belirtilen run’a bağlıdır.

Salt okunur TBDY başvuru sürümü: `1440df1b9300f75b1e604204438f5cada9ebd247`. İncelenen dosyalar `design_demand_states.py`, `combo_pattern_engine.py`, `column_design_demand_engine.py` oldu. Adı esas almayan sınıflandırma ve sekiz işaret fikri kullanıldı; eski uçla sınırlı seçim, istasyon yuvarlama ve tasarım kabul bayrakları alınmadı. Dosya hash’leri teslim SHA defterindedir.

## 7. Kullanım ve ayrı dışa aktarımlar

Arayüz: **Kolonlar → Kuvvetler ve birleşimler → Depremli tasarım talebi**. İlk tablo, seçili donatı için kolon başına kritik sonucu gösterir. **Senaryoları aç** ilgili kolon/birleşimin sınırlı aday sayfasına geçer. Katsayılar, kaynak kimlikleri ve ara hesaplar açılır ayrıntıda kalır. Ham kuvvet nüfusu ilk isteğe yüklenmez.

CLI örneğinde `RUN_ID`, mevcut panelde seçilmiş gerçek run kimliğiyle değiştirilmelidir:

```text
python -m tbdy_next.cli inspect-spectral-design --out .receipts --run-id RUN_ID
python -m tbdy_next.cli inspect-spectral-design --out .receipts --run-id RUN_ID --member 127 --cage 16Φ24 --candidates --limit 8
python -m tbdy_next.cli inspect-spectral-design --out .receipts --run-id RUN_ID --html VS26_ozet.html
python -m tbdy_next.cli inspect-spectral-design --out .receipts --run-id RUN_ID --member 127 --candidates --json VS26_127.json
python -m tbdy_next.cli inspect-spectral-design --out .receipts --run-id RUN_ID --forensic VS26_tam_dokum.zip
```

JSON ve HTML, seçilmiş filtre/sayfayı aynı türetimden verir. Forensic ZIP ise açıkça **bütün VS26 nüfusunu** içerir; filtrelerle birlikte istenirse reddedilir. Yeni dosya yazma kipleri mevcut dosyayı ezmez. ZIP içindeki manifest; her JSON/NDJSON bölümünün SHA-256’sını, byte ve kayıt sayılarını, kaynak ve sonuç kimliklerini taşır. Nümerik kanıtlar tam kesit ve talep girdilerine; değerlendirmeler adaylara; adaylar tipli zarflara; zarflar native kaynak satırlarına bağlanır.

**NUMERICAL REPLAY VERIFIED**, **CONDITIONAL DESIGN ENVELOPE CALCULATED** ve **NORMATIVE DESIGN AUTHORITY NOT YET PROVEN** ayrı kabul ifadeleridir. Supervisor’ın sonraki canlı kaynak/model doğrulaması ve mühendislik kabulü yerine geçmezler.

## 8. Zorunlu golden rapor regresyon kapısı

Supervisor'ın ek kabul koşulu doğrultusunda üç banka ayrıdır:

| Banka | Sınadığı konu | Sağlamadığı yetki |
| --- | --- | --- |
| GOLDEN-01/02 raporları ve özgün 23+7 audit | Belirli rapor girdisiyle YENI hesabı → bağımsız aritmetik → basılı rapor → farkın açıklaması | Raporun kendi tasarımının otomatik doğruluğu veya bütün algoritmanın kabulü |
| Column B7 / mevcut VS25 bağımsız kesit referansı | Tanımlı sayısal/malzeme modeli altında kesit çözümünün karşılaştırılması | GOLDEN-01/02'nin birebir rapor doğrulaması |
| 87 kolonlu native ETABS arşivi | Kaynak, kesit/istasyon/bileşen bağları ve kaydedilmiş sonuçların yeniden hesabı | Bağımsız yönetmelik algoritması veya normatif tasarım kabulü |

Rapor kaynakları [GOLDEN_EVIDENCE](https://github.com/feridunfc/Column-Engine/blob/df754b202415a58508f60b27d96f731a7b840041/tbdy_column_workflow/recipe_v11/GOLDEN_EVIDENCE.json) ile, araştırma sözleşmeleri aynı sürümdeki [RULE_CARDS](https://github.com/feridunfc/Column-Engine/blob/df754b202415a58508f60b27d96f731a7b840041/tbdy_column_workflow/recipe_v11/RULE_CARDS.json) ile sabitlendi. Rule card metni normatif kaynağın veya proje uygulanabilirlik kabulünün yerine geçirilmez; özellikle TS500 7.29'un geçmişte seçilmiş politikası YENI'ye otomatik taşınmaz.

`verification/golden_gate.py`, orijinal küçük audit ZIP'leri ve seçili rapor dökümlerini her çağrıda hash'ler. Dört tam PDF'nin ilk denetimdeki SHA doğrulaması kayıtlıdır. `--source-dir` verilirse bütün PDF/ZIP byte'ları tekrar doğrulanır; verilmezse durum açıkça `PINNED_REVIEWED_EXCERPTS_AND_AUDIT_BYTES` olur. CI'da tam PDF'ler yeniden okunmuş gibi davranılmaz.

Karşılaştırmalar yalnız `NUMERICAL_MATCH`, `ENGINEERING_INTERPRETATION_DIFFERENCE` ve `INSUFFICIENT_SOURCE` sınıflarına ayrılır. YENI–bağımsız hesap arasındaki açıklanamayan sayısal sapma bir hata üretir; genel bir “yorum farkı” kaçışına yönlendirilemez. Yorum farkı yalnız açık TS500 7.29 karar/aktarımı satırlarında kullanılır: bireysel β ve kat βs sayısal uyumu ayrıca aranırken YENI nihai çarpanı boş kalır. Raporun “Alındı” β değeri, bireysel β ile aynı büyüklük sayılmaz.

Donatı alanı karşılaştırmasındaki 12Ø14 yerleşimleri yalnız sayım/alan test düzenidir; rapora bağlı gerçek çubuk koordinatı veya PMM girişi değildir. SCWB karşılaştırmasındaki I/J işaretleri de basılı alt/üst/sağ/sol katılımcıların test rolleridir; native uç eşleşmesi olduğu iddia edilmez. Bu sınırlı karşılaştırmaların geçmesi tam PMM, SCWB veya donatı tasarım kabulünü sağlamaz.

Zorunlu ikinci mertebe, PMM, SCWB, kapasite kesmesi ve kat α alanları için tam rapor golden kapsamı tamamlanmadığından `acceptance_eligible=False`, `REQUIRED_REPORT_GOLDEN_COVERAGE_INCOMPLETE` korunur. GOLDEN-03/04 yalnız kaynakları doğrulanmış raporlardır; eksik audit paketleri tamamlanmış gibi sayılmaz. Bu gate spektral UI/JSON/HTML'de aynı özet kimliğiyle, tam forensic ZIP'te bütün karşılaştırmalarıyla yer alır. CLI:

```text
python -m tbdy_next.cli inspect-golden-regression
python -m tbdy_next.cli inspect-golden-regression --html golden.html
python -m tbdy_next.cli inspect-golden-regression --source-dir GOLDEN_KAYNAK_DIZINI --json golden_kaynak_denetimi.json
python -m tbdy_next.cli inspect-golden-regression --require-complete
```

`--require-complete` mevcut açık kapsam nedeniyle 3 döndürür. Normal JSON üretiminin 0 ile bitmesi yalnız inceleme işleminin başarıyla tamamlandığını gösterir. Yeni rapor testleri seçilerek eski kanıtların üstü örtülmez; kaynaklar ve mevcut aritmetik karşılaştırmalar sonraki sprintlerde aynı banka üzerinden genişletilir.
