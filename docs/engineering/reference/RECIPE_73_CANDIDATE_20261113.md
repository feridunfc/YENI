> **REFERENCE ONLY / ENGINEERING AUTHORITY DENIED.** This is the user-supplied 73-check recipe copied without normative promotion. Canonical YENI mappings, present owner modules, gates and required evidence are maintained in `docs/engineering/RECIPE73_YENI_INTEGRATION_20261113.md`. Do not execute this file as a normative ruleset or rewrite existing source modules from it.

# TBDY-NEXT-ENGINE — 73 CHECK İÇİN BÜTÜNLEŞİK HESAP MANTIĞI VE KAYNAK REÇETESİ

**Tarih:** 13 Kasım 2026  
**Teslim biçimi:** Yalnız mühendislik mantığı; program kodu yok  
**Temel dosyalar:** Kullanıcının son `Yapıştırılan markdown(5).md` dosyası; `TBDY_NEXT_ENGINE(1).zip` içindeki 73 satırlı `checks.json`; `kompakt_b.EDB` kaynak arşivi; önceki hesap mantığı dosyası; Google Drive örnek ETEX/Excel/hesap raporları; TBDY 2018 ve TS 500 metinleri.

## Özet: tek hesap, birden fazla tüketici

Bu kılavuzun gayesi, **hesabın nasıl yapılacağını ve mevcut kaynaktan hangi ara sonucunun üretileceğini** tarif etmektir. Yeni gönderilen 401 satırlık metin 42 ayrı kontrol kimliğine doğrudan temas eder; gerçek kataloğun diğer 31 kimliği de bu belgenin J bölümünde tamamlayıcı reçetelerle açılmıştır. Böylece 73 ID'nin tamamı için işlem tanımı vardır. Bu sayı **mühendislik uygunluğu onayı almış 73 algoritma** anlamına gelmez.

**Beş zorunlu soru:** (1) NE/hangi fiziksel davranış? (2) NE LAZIM/asgari tipli veri? (3) ELİMDE NE VAR/gerçek kaynak? (4) HOW/kaynak→türetme→normatif sınır? (5) KARAR/uygunluk, kanıt eksiği, sonraki iş.

**Her giriş için karar hiyerarşisi:** mevcut ETABS satırından (`K`) → mevcut kayıttan matematiksel türev (`D`) → donatı/kesit adayı (`A`) → proje/mühendislik profil kararı (`M`) → gerçekten yeni FE veya geoteknik kayıt gerekiyorsa (`Y`). Yalnız bir `K` kaydı ve bağımsız kaynak bağlamı varsa `SOURCE_OBSERVED`; tasarım ve normatif kabul için ilave delil gerekir.

**Hedef ürün:** ETABS'ta mevcut, analiz edilmiş bir binaya yönelik post-processing. Modeli yeniden çözmek veya ETABS sonuçlarından farklı yeni sonlu elemanlar sonucu uydurmak görev değildir.

## Kaynağın doğruladığı fiilî sınır

| Kaynak | Kayıttaki durum | Kullanım |
|---|---|---|
| Kaynak dosya | `kompakt_b.EDB`, yakalama öncesi/sonrası EDB hash'i eşit; kaynak kilitli | Model kimliği doğrulanabilir; analizin aynı nesline ait olduğuna dair ispat **ayrı** |
| Yakalama manifesti | `complete=false`, `engineering_release=NOT_READY`, `results_not_analyzed_or_redesigned=true` | Tasarım uygunluğu için değil, yalnız kaydedilmiş sonuçları yorumlamak için |
| Fiziksel eleman envanteri | 87 kolon, 180 kiriş, 30 perde, 97 döşeme | Fiziksel eleman kontrollü payda ve ID bağları |
| FrameForce | 267/267 kolon-kiriş native sonuç kapsamı; 27 `Null Line` hariç | İmzalı statik kuvvet ve ayrı spektral bileşen kaydı |
| Kaynak tablo family | Story/Joint/Material/Section/Case/Combo/Modal/Displacement/Reaction/Wall verileri | Yeniden kullanılabilir typed feature |
| Eksik temel kanıtı | `analysis_generation_proven=false` | Bağımlı sonuçlar `NOT_PROVEN` olabilir; kaynak okuma ve saf matematik devam eder |

**Kritik ayrım:** `PhysicalStaticForceState` = aynı vaka/step/kesitte birlikte bulunan imzalı `P,V2,V3,T,M2,M3`; `SpectralComponentEnvelope` = mod birleştirme ile bulunan ayrı ayrı istatistiksel enbüyük bileşenler; `CodeDesignDemandCandidate` = normatif birleştirme politikasıyla oluşturulmuş açık talep adayı. Bunlar birbirinin yerine kullanılamaz.

## 73 kimliğin tam indeks ve yürütme kapsamı

Aşağıdaki `uygulama/kaynak` durumları, referans ZIP'in **araştırma/sözleşme kataloğundaki beyanlardır**. Bu entegrasyonla programlanmış veya doğrulanmış hâle getirildikleri iddia edilmiyor. Son sütun veri edinme rotasıdır, yeni veri talebinin kendisi değildir.

| ID | Katalogdaki hesap/denetim | Orijinal uygulama/kaynak | Veri yolu | Son metinde |
|---|---|---|---|---|
| `SRC-001` | Archive file hash integrity | `UNIT_TESTED/AVAILABLE` | `K` | Açık tarif |
| `SRC-002` | Source model identity unchanged / units | `UNIT_TESTED/AVAILABLE` | `K` | J bölümünde tamamlandı |
| `SRC-003` | FrameForce coverage vs physical frames | `IMPLEMENTED/PARTIAL` | `K` | Açık tarif |
| `SRC-004` | Analysis generation proof flag | `IMPLEMENTED/INVALID` | `K+Y` | Açık tarif |
| `SRC-005` | Combination book replay vs ETABS stored combination rows | `SOURCE_REPLAYED/AVAILABLE` | `K+D` | Açık tarif |
| `CHK-001` | Concrete strength lower bound | `UNIT_TESTED/AVAILABLE` | `K+D` | Açık tarif |
| `CHK-002` | Concrete strength upper range | `UNIT_TESTED/AVAILABLE` | `K+D+M` | Açık tarif |
| `CHK-003` | Column minimum cross-section side | `IMPLEMENTED/AVAILABLE` | `K+D` | Açık tarif |
| `CHK-004` | Column Ac >= Ndm/(0.40 fck) | `IMPLEMENTED/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-005` | Column Nd <= 0.9 fcd Ac | `IMPLEMENTED/PARTIAL` | `K+D+A` | J bölümünde tamamlandı |
| `CHK-006` | Cumulative modal mass participation | `IMPLEMENTED/AVAILABLE` | `K+D` | Açık tarif |
| `CHK-007` | Column first-order PMM + solver-selected reinforcement | `IMPLEMENTED/PARTIAL` | `K+D+A` | J bölümünde tamamlandı |
| `CHK-009` | ETABS-defined column longitudinal ratio | `IMPLEMENTED/PARTIAL` | `K+A` | J bölümünde tamamlandı |
| `CHK-010` | Story drift limits | `CONTRACT_ONLY/MISSING` | `K+D (+Y: ilgili spektral varyant kayıtları)` | Açık tarif |
| `CHK-011` | Design spectrum reconstruction vs ETABS function | `SOURCE_REPLAYED/AVAILABLE` | `K+D` | J bölümünde tamamlandı |
| `CHK-101` | Mass source reconstruction | `CONTRACT_ONLY/PARTIAL` | `K+D` | Açık tarif |
| `CHK-102` | Modal period range | `CONTRACT_ONLY/PARTIAL` | `K+D` | Açık tarif |
| `CHK-103` | Equivalent lateral force base shear | `CONTRACT_ONLY/PARTIAL` | `K+D+M` | J bölümünde tamamlandı |
| `CHK-104` | Modal base shear scaling | `CONTRACT_ONLY/PARTIAL` | `K+D+Y` | J bölümünde tamamlandı |
| `CHK-105` | Effective story drift | `CONTRACT_ONLY/PARTIAL` | `K+D+M (+Y: spektral displacement)` | Açık tarif |
| `CHK-106` | Irregularity A1 torsion | `CONTRACT_ONLY/PARTIAL` | `K+D+Y` | Açık tarif |
| `CHK-107` | Irregularity A2 floor discontinuity | `CONTRACT_ONLY/PARTIAL` | `K+D+M` | J bölümünde tamamlandı |
| `CHK-108` | Irregularity A3 storey discontinuity | `CONTRACT_ONLY/PARTIAL` | `K+D` | J bölümünde tamamlandı |
| `CHK-109` | Irregularity B1 weak storey | `CONTRACT_ONLY/PARTIAL` | `K+D+M` | Açık tarif |
| `CHK-110` | Irregularity B2 soft storey | `CONTRACT_ONLY/PARTIAL` | `K+D+Y (ilgili eksantrisite/spektral senaryolar için)` | Açık tarif |
| `CHK-111` | Irregularity B3 mass irregularity | `CONTRACT_ONLY/PARTIAL` | `K+D` | J bölümünde tamamlandı |
| `CHK-112` | Global overturning | `CONTRACT_ONLY/PARTIAL` | `K+D+Y (RS/base same-cut)` | J bölümünde tamamlandı |
| `CHK-113` | Global second-order indicator | `CONTRACT_ONLY/PARTIAL` | `K+D+M` | Açık tarif |
| `CHK-114` | Foundation force transfer | `CONTRACT_ONLY/PARTIAL` | `K+D+Y` | J bölümünde tamamlandı |
| `CHK-115` | Column minimum eccentricity | `CONTRACT_ONLY/PARTIAL` | `K+D` | Açık tarif |
| `CHK-116` | Column slenderness and unsupported length | `CONTRACT_ONLY/PARTIAL` | `K+D+M` | J bölümünde tamamlandı |
| `CHK-117` | Effective length factors | `CONTRACT_ONLY/PARTIAL` | `K+D+M` | J bölümünde tamamlandı |
| `CHK-118` | Global P-Delta amplification | `CONTRACT_ONLY/PARTIAL` | `K+D+M` | J bölümünde tamamlandı |
| `CHK-119` | Local P-delta (TS 500 magnification) | `CONTRACT_ONLY/PARTIAL` | `K+D+A+M` | J bölümünde tamamlandı |
| `CHK-120` | Biaxial PMM with second-order demand (final) | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-121` | Column longitudinal bar detailing | `CONTRACT_ONLY/PARTIAL` | `K+A` | Açık tarif |
| `CHK-122` | Confinement region length | `CONTRACT_ONLY/PARTIAL` | `K+D` | J bölümünde tamamlandı |
| `CHK-123` | Tie and cross-tie layout | `CONTRACT_ONLY/PARTIAL` | `K+A` | J bölümünde tamamlandı |
| `CHK-124` | Confinement reinforcement Ash | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-125` | Strong column weak beam (SCWB) | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-126` | Column capacity shear Ve | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-127` | Column shear capacity | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-128` | Beam-column joint shear | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-129` | Column design iteration convergence | `CONTRACT_ONLY/PARTIAL` | `D+A+M` | J bölümünde tamamlandı |
| `CHK-130` | Beam geometry and axial applicability | `CONTRACT_ONLY/PARTIAL` | `K+D` | Açık tarif |
| `CHK-131` | Beam design flexure | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-132` | Beam upper/lower reinforcement | `CONTRACT_ONLY/PARTIAL` | `K+A` | Açık tarif |
| `CHK-133` | Beam min/max reinforcement | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | J bölümünde tamamlandı |
| `CHK-134` | Beam end moment capacities | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-135` | Beam shear and capacity shear | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-136` | Beam shear reinforcement | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-137` | Beam torsion | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | J bölümünde tamamlandı |
| `CHK-138` | Beam cracking and deflection | `CONTRACT_ONLY/PARTIAL` | `K+D+A+M` | Açık tarif |
| `CHK-139` | Beam anchorage and continuity | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | J bölümünde tamamlandı |
| `CHK-140` | Wall geometry and pier mapping | `CONTRACT_ONLY/PARTIAL` | `K+D` | Açık tarif |
| `CHK-141` | Wall axial-flexural capacity | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-142` | Wall boundary regions | `CONTRACT_ONLY/PARTIAL` | `K+D+M` | J bölümünde tamamlandı |
| `CHK-143` | Wall reinforcement | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | J bölümünde tamamlandı |
| `CHK-144` | Wall shear and capacity shear | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | Açık tarif |
| `CHK-145` | Coupled wall link beams | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | J bölümünde tamamlandı |
| `CHK-146` | Story shear distribution and story phi | `CONTRACT_ONLY/PARTIAL` | `K+D+Y (tam RS ve aynı kesit kanıtı)` | J bölümünde tamamlandı |
| `CHK-147` | Joint topology | `CONTRACT_ONLY/PARTIAL` | `K+D` | J bölümünde tamamlandı |
| `CHK-148` | Joint confinement | `CONTRACT_ONLY/PARTIAL` | `K+D+A` | J bölümünde tamamlandı |
| `CHK-149` | Slab geometry and thickness | `CONTRACT_ONLY/PARTIAL` | `K+D+M` | Açık tarif |
| `CHK-150` | Slab flexure and reinforcement | `CONTRACT_ONLY/PARTIAL` | `K+A+Y` | Açık tarif |
| `CHK-151` | Slab punching | `CONTRACT_ONLY/PARTIAL` | `K+D+A+Y` | Açık tarif |
| `CHK-152` | Slab deflection and cracking | `CONTRACT_ONLY/PARTIAL` | `K+D+A+M (+Y: seçilmiş zaman-bağımlı analiz varsa)` | Açık tarif |
| `CHK-153` | Diaphragm in-plane forces | `CONTRACT_ONLY/PARTIAL` | `K+D+A+Y` | J bölümünde tamamlandı |
| `CHK-154` | Foundation geometry | `CONTRACT_ONLY/PARTIAL` | `K+Y` | Açık tarif |
| `CHK-155` | Foundation soil pressure | `CONTRACT_ONLY/PARTIAL` | `K+D+Y+M` | Açık tarif |
| `CHK-156` | Foundation one-way shear and punching | `CONTRACT_ONLY/PARTIAL` | `K+D+A+Y` | J bölümünde tamamlandı |
| `CHK-157` | Foundation reinforcement | `CONTRACT_ONLY/PARTIAL` | `A+Y` | Açık tarif |
| `CHK-158` | Foundation-to-superstructure load transfer | `CONTRACT_ONLY/PARTIAL` | `K+D+Y` | J bölümünde tamamlandı |

---

## Ayrıntılı 73 CHECK tarifleri — kaynak / algoritma / karar

**Tür:** Kod içermeyen mühendislik algoritma ve kanıt kılavuzu. **Tarih:** 13 Kasım 2026.  
**Kapsam:** Referans `TBDY_NEXT_ENGINE(1).zip/config/check_registry/checks.json` dosyasındaki **73 CHECK_ID**, kullanıcının `kompakt_b.EDB` kaynak arşivi, Google Drive örnek hesapları ve TBDY 2018 / TS 500 normatif kaynakları.  
**Durum:** Teknik hesap yolu tarifidir; henüz bina mühendislik uygunluğu veya algoritma yazılımının tamamlanmış olduğuna dair kabul değildir.

## A. Ana prensip: bir CHECK için beş soru

1. **NE?** Hangi fiziksel davranış, hangi eleman/kesit/kat/yükleme/kapsam kontrol edilir? Uygulanabilir mi?
2. **NE LAZIM?** En küçük yeterli girdi kümesi; birimler, işaretler, seçilen tasarım dalı ve kaynağın kimliği nedir?
3. **ELİMDE NE VAR?** Bu girdilerin hangisi 13.11.2026 gerçek ETABS ZIP'inde; hangisi Drive Excel'lerinde yalnız karşılaştırma referansı olarak bulunur?
4. **HOW?** Eksik olan doğrudan kaynak satırı mı, mevcut kaynaklardan hesaplanabilen *derived feature* mı, donatı adayının üretileceği bir algoritma mı, mühendis tercihi mi, yoksa yeni FE çözümü mü? Her eksik veri için en kısa kurtarma yolu nedir?
5. **KARAR?** Formül/denge + normatif sınır + uygulanabilirlik + kaynak tamlığı + bağımsız kontrol birlikte sağlandığında ne çıkacak? Yeniden tasarım/analiz veya `NOT_PROVEN` ne zaman oluşur?

**Dört ayrı işlemi karıştırma:** (A) kaynak okuma; (B) kaynaktan mühendislik büyüklüğü türetme; (C) yönetmelik sınırı ile karşılaştırma; (D) ürünün tamamının mühendislik kabulü. (A) ve (B) başarılı olsa bile (C)/(D) ayrı kanıt ister.

**Kanıt yolları:** `K` = kaynak ZIP'inde var; `D` = ZIP verilerinden offline türetilebilir; `A` = aday donatı/kesit tasarımı gerektirir; `M` = model profili, uygulama dalı veya insan mühendis girişi gerekir; `Y` = kaydedilmiş tabloda yok, hedefli ETABS/SAFE/zemin kaydı gerekir. Bir CHECK birden fazla yolu tüketebilir.

## B. Gerçek kaynakta görülenler ve kullanımı

| Kaynak ailesi | Gerçek ZIP'teki gözlem | Ne üretilebilir? |
|---|---|---|
| Geometri | 87 kolon, 180 kiriş, 30 perde, 97 floor, kat/point/joint, kesit ve atamalar | Kesit/gövde, net yükseklik, uç-joint, plan ve düşey yük yolu, model envanteri |
| Native kuvvet | 267/267 fiziksel kolon/kirişte `FrameForce`, toplam 453.985 satır; `P,V2,V3,T,M2,M3`, station/step | Statik imzalı kuvvet, yük ailesine göre kuvvet dağılımı, spektrum bileşenleri, komboların bileşen zarfları |
| Kombinasyon | 271 kombinasyon tanım satırı, 30 `Linear Add`, 5 `Envelope`; kaynağın I/J ve station etiketleri | Terim çözme, aritmetik replay, gösterilen birleşimleri **adından değil tanımından** sınıflama |
| Modal | 100 modal kütle/periyot/katılım satırı, `Mass Source Definition`, `Mass Summary by Story` | Modal kapsam, kütle kaynağı inceleme, spektrum parametre doğrulaması |
| Öteleme/kat | `Story Drifts` 47; `Story Max Over Avg Drifts` 47; `Story Stiffness` 8; `Joint Displacements` 3900; iç mesh dahil displacement 90456; `Story Forces` 36 | Kaydedilmiş **statik** LC_EQX/LC_EQY senaryolarında A1, B2, θ, drift için sayısal girdi; spektral/ek dışmerkezlik senaryosu kendi kaynağıyla ele alınır |
| Perde | `Pier Forces` 360 satır; `Area Assignments – Pier Labels` 29; wall object 30; section/material | Statik pier kuvveti, wall↔pier topoloji eşlemesi, perde kesiti bazında talep |
| Mesnet | `Joint Reactions` 17.496; `Base Reactions` 12 statik sonuç | Statik global kuvvet dengesi ve temel aktarımı için bir tarafın kanıtı |
| Donatı | Column reinforcing section için 1 atama tarifi; beam reinforcing section için 15 tarif, beam uç alanları 0 | **Tasarım ayarları** görülebilir; mevcut/proje onaylı/yerinde donatı bilinmez. Bağımsız aday üretimi gerekir |
| Döşeme | Floor geometry 97, slab property 4, joint Uz sonuçları; `Element Forces – Area Shells` bu yakalamada yok | Geometri ve bazı anlık deplasman türevleri; gerçek döşeme M11/M22 vb için hedefli shell forces kaydı gerekir |
| Eksik/özel | `analysis_generation_proven=false`; bazı load assignment tabloları CAPTURE_ERROR; `Response Spectrum Modal Info` ve `Joint Displacements – Absolute` kısmi; temel/zemin verisi yok | Sadece ilgili CHECK sonuçları askıda; algoritmanın saf matematiksel tanımı veya statik kaynak replay'i yine yapılabilir |

**Önemli native semantiği:** `RSX/RSY` ve depremli combo satırları mevcut olsa bile CQC bileşen `Max` değerleri tek bir anda birlikte gerçekleşmiş işaretli `N–M2–M3` üçlüsü değildir. İmzası gerçek olan `Linear Static` talep ile `SpectralComponentEnvelope` iki farklı veri tipidir. Tasarım için spektral talep kombinasyon politikası ayrı ve sınanmış olmalıdır.

**Kaynak seviyeleri:** Fiziksel eleman/point için `unique_name+story`; analitik frame için `object_id+element_id+station`; sonuç için `case+step+sign+unit+generation`; perde için `wall_object ↔ pier_label ↔ story ↔ top/bottom`; kolon/kiriş yüzü için `joint_I/J + offset + physical face`. Bu anahtarlardan biri bilinmiyorsa farklı kesit sonuçları rastgele eşleştirilmez.

## C. 73 CHECK'in kullanılacak hesap tarifleri

### C1 — Kaynak kapıları (5)

**SRC-001 — ZIP dosya bütünlüğü.** **Lazım:** manifest, her üyenin beklenen boyutu ve SHA-256. **Var:** `archive_manifest.json` ve 380 üye. **How:** her dosyayı yeniden hash et; manifestte fazlalık/eksiklik/çift ad ara; kapsama sayısı tam olsun. **Karar:** kaynağın kendisi güvenilir değilse etkilenen bütün sonuçlara `INVALID_SOURCE`; bu bir taşıyıcı sistem FAIL'i değildir. **Yol:** K.

**SRC-002 — Fiziksel model kimliği ve birim.** **Lazım:** model hash'i, kilitli durum, önce/sonra kimlik, birim kodu. **Var:** `capture_report.source_identity_before/after`, `present_units_code=6`, aynı EDB SHA. **How:** hash/size/units eşitliğini kanıtla; birim kodunu kesin sisteme çevir; her tablo için birim metadatasıyla birim sözleşmesini denetle. **Karar:** `SOURCE_IDENTITY_VERIFIED`; bu tek başına analiz sonuçlarının aynı nesilde üretildiğini ispatlamaz. **Yol:** K.

**SRC-003 — Fiziksel çerçeve elemanları için sonuç tamlığı.** **Lazım:** fiziksel kolon+kiriş listesi, native force nesneleri, başarısız nesne sınıfı. **Var:** 87+180 fiziksel frame için sonuç; 27 `Null Line` başarısızlığı. **How:** beklenen 267 fiziksel ID ile sonuç satırı bulunan 267 ID'yi birleştir; bir frame'i I/J / station nedeniyle iki kez sayma. **Karar:** fiziksel kolon/kiriş capture kapsamı 267/267; `Null Line` kapsam dışı raporlanır, saklanmaz. **Yol:** K.

**SRC-004 — Analiz nesli eşleştirme.** **Lazım:** EDB dosya kimliği, analiz nesli/run serial, load case/combination sonuçlarının aynı çözüme ait olduğunun kaydı. **Var:** dosya hash'i, lock, run ID; `analysis_generation_proven=false`. **How:** sonuç anahtarlarına analysis-generation bağını bir kanıt zinciri olarak ekle; varsa analysis messages/run serial ile bağla; desteklenmiyorsa yalnız matematiksel tutarlılık incele. **Karar:** model hash'i PASS olabilir; analiz-generation bağı `NOT_PROVEN` kalır; yeni yakalama yalnız bu ayrı GAP için gerekir. **Yol:** K+Y.

**SRC-005 — ComboBook ve yeniden hesaplama.** **Lazım:** gerçek combo tanımları (`Type, LoadName, SF`), bütün child case sonuçları, same station/step. **Var:** 30 linear, 5 envelope ve native case/combo satırları. **How:** operator ağacını aç; lineer işaretli bileşenleri katsayıyla topla; envelope için her bileşenin max/min'ini ve argmax kaynak durumunu ayrı üret; kaydedilmiş ETABS değerleriyle farkları ölç. **Karar:** test sonucu `ARITHMETIC_REPLAYED`; spektral korelasyon kanıtı değildir. **Yol:** K+D.

### C2 — Malzeme, ön geometri, modal, ilk tasarım (10)

**CHK-001 — Beton karakteristik dayanımı alt sınırı.** **Lazım:** *kullanılan* betonarme eleman→kesit→malzeme→`fck`, uygulanabilir eleman tipi. **Var:** material/section assignments, fiziksel 87 kolon+180 kiriş+30 perde+97 döşeme kaydı. **How:** malzeme atamasını her fiziksel elemana çöz, MPa'ya çevir, TBDY 7.2.5.1 kapsamında `fck ≥ 25 MPa`. **Karar:** yalnız atanmış elemanları değerlendirme paydasına al; tanımlı ama kullanılmayan malzeme PASS paydasına girmez. **Yol:** K+D.

**CHK-002 — Deprem taşıyan beton malzemesi sınırları.** **Lazım:** CHK-001'in tekil materyal feature'ı, elemanın deprem etkisi taşıma rolü. **Var:** aynı malzeme/atama kaynakları; bütün elemanlar için rol açık değil. **How:** TBDY 7.2.5.3(a) uygulanıyorsa beton sınıfını C25–C80 doğrula; uygulama kapsamını kayıtla. **Karar:** kapsam kanıtlıysa sınır kararı; aksi durumda yalnız o eleman için `NOT_PROVEN`. **Yol:** K+D+M.

**CHK-003 — Kolon geometrik alt sınırı.** **Lazım:** fiziksel kolon sınıfı, gerçek dikdörtgen kenarları veya dairesel çap, döndürülmüş yerel eksen. **Var:** kolon bağlantı ve beton kesit tabloları. **How:** TBDY 7.3.1.1'e göre dikdörtgende iki kenarın küçüğü ≥300 mm, daireselde çap ≥350 mm; genel kesit ailelerini ayrıca sınıflandır. **Karar:** kolon adedine göre tüm envanteri değerlendir. **Yol:** K+D.

**CHK-004 — Kolon TBDY 7.3.1.2 eksenel basınç sınırı.** **Lazım:** `Ac,fck`, geçerli bütün `G+Q+E` tasarım durumlarında **en yüksek basınç** `Ndm`, varsa hareketli yük azaltma. **Var:** geometri/malzeme, statik ve combo FrameForce satırları; spektral tasarım semantiği ayrı doğrulanacak. **How:** seçilen kombinasyonların fiziksel aynı kesit yüklerini çöz, en büyük basıncı al, `Ndm/(0.40 Ac fck) ≤ 1`. **Karar:** eksik tasarım kombinasyonu varsa kısmi sonuç; statik zarf nihai `Ndm` sayılmaz. **Yol:** K+D+A.

**CHK-005 — TS 500 kolon basınç sınırı.** **Lazım:** CHK-004'teki tasarım baskı talebi, `fcd`, brüt `Ac`, TS 500 uygulanabilirlik. **Var:** geometri/malzeme ve kısmi tasarım talepleri. **How:** normatif seçili basınç sınırı `Ndm ≤ 0.9 fcd Ac` ile ayrı kontrol; TBDY 0.40 sınırının yerine geçmez. **Karar:** iki bağımsız oran ve yöneten kombinasyon gösterilir. **Yol:** K+D+A.

**CHK-006 — Modal etkin kütle katılımı.** **Lazım:** modal katılım satırları, kütle kaynağı, X/Y mod katkıları. **Var:** 100 mod ve `SumUX/ SumUY`. **How:** her yön ≥%95, katkısı >%3 olan modları dahil et, 3D analizde iki yönün büyük mod sayısını seç (TBDY 4.8.1.2). **Karar:** bu kaynakta X/Y son katılım yaklaşık %99.99; `MODAL_PARTICIPATION_OBSERVED` sonucu, spektral tasarım onayı anlamına gelmez. **Yol:** K+D.

**CHK-007 — İlk mertebe iki eksenli kolon PMM ve önerilen donatı.** **Lazım:** işaretli tasarım `Nd,M2,M3` vektörü, section/bar centers, `fcd,fyd`, ötelenme eklenmeden 1. mertebe yük seti. **Var:** frame kuvvet ve kesit/malzeme; onaylanmış fiziksel donatı yok. **How:** azami/min donatı kurallarıyla aday bar geometrisi kur → uyumlu şekil değiştirme kesit kapasitesi → her yük durumu için PMM kullanım oranı → uygun donatı adayı. **Karar:** `FIRST_ORDER_CANDIDATE`, nihai tasarım değil; ikinci mertebe ve SCWB bunu tüketecek. **Yol:** K+D+A.

**CHK-009 — ETABS kesit donatı tanımından boyuna oran.** **Lazım:** kolonun gerçek seçilmiş donatı adedi, çap, kesit alanı ve programda `IsDesigned` ayrımı. **Var:** `Frame Section Property Definitions – Concrete Column Reinforcing` bir section tarifi; tüm 87 kolona gerçek onaylı donatı değil. **How:** bu kaynak `design settings` olarak kaydet; bağımsız seçilmiş donatı için `rho=As/Ac` oluştur, TBDY 7.3.2.1 `%1–%4` kontrolüne bağla. **Karar:** ETABS ayarını `EXISTING_REBAR` yapma; geometrik aday durumu `PROPOSED` kalır. **Yol:** K+A.

**CHK-010 — Kat ötelemesi ilk kaba değerlendirme.** **Lazım:** story height, doğru deprem senaryosu, kat içindeki bütün bağlanmış kolon/perde uçlarının yatay yerdeğiştirme farkı. **Var:** `Story Drifts`, `Joint Displacements`, `Story Max Over Avg Drifts` (çoğunlukla kaydedilmiş statik case). **How:** `u_i-u_(i-1)` ve `h_i` eşleşmesini yap; A1 ve etkin drift ile ortak `StoryDriftFeature` kullan. **Karar:** kaba/ham azaltılmış drift `CHK-105` için girdi; `R/I`, DD-3 katsayısı uygulanmadan yönetmelik PASS'i değil. **Yol:** K+D (+Y: ilgili spektral varyant kayıtları).

**CHK-011 — Tasarım spektrumu yeniden üretimi.** **Lazım:** site class, Ss/S1/Fs/F1, `SDS,SD1,TA,TB,TL`, R/D/I ve response spectrum tanımı. **Var:** 26 spektrum eğri satırı ve ETABS `Functions – Response Spectrum – TSC-2018` alanları. **How:** TBDY Bölüm 2'ye göre Sae(T), ilgili Ra(T), SaR(T); aynı periyotlarda ETABS ile karşılaştır. **Karar:** `SPECTRUM_FUNCTION_REPLAYED`; modal sonuçların analitik doğruluğuna eşdeğer değil. **Yol:** K+D.

### C3 — Bina dinamiği ve düzensizlikler (CHK-101...114)

**CHK-101 — Mass source reconstruction.** **Lazım:** mass source katsayıları, self mass, her katta toplanmış mass ve tanımlanan G/Q/WDL. **Var:** `Mass Source Definition`, `Assembled Joint Masses`, `Mass Summary by Story`, load pattern. **How:** self + yük kaynaklarını sürümlü sözlükle topla, her katta kütle merkezine ve toplam kütleye kadar uzlaştır; kaydedilmiş Summary ile karşılaştır. **Karar:** dengesi kanıtlanan katlar `RECONCILED`; shell/duvar yük atamaları bilinmiyorsa bağımlı kütle için kısmi kanıt. **Yol:** K+D.

**CHK-102 — Modal periyot ve periyot sınırları.** **Lazım:** modal T/f, bina yüksekliği, deprem yönü, izin verilen ampirik sınır ve model rijitliği nesli. **Var:** 100 periyot, Story Definition, spectrum, stiffness modifier. **How:** 1/T, 2π/T iç tutarlılığı; yönlü temel modları katılım vektöründen seç; TBDY 4.7.3.2 uygulanıyorsa ampirik periyot sınırını gerekli yöntem dalında denetle. **Karar:** yönlü `Tpx/Tpy`, mod katılımıyla desteklenen tanım; salt ilk mod numarasından yön tahmin etme. **Yol:** K+D.

**CHK-103 — Eşdeğer deprem taban kesmesi.** **Lazım:** `m_t`, doğrultu, `SaR(Tp)`, I/R/D, minimum taban kesme, kat ağırlıkları. **Var:** mass, modal T, spektrum, story geometri, model profili parametreleri. **How:** TBDY 4.7.1 Denk.(4.19), min sınır, ardından 4.7.2 katlara `m_i H_i` ve ilave çatı kuvveti `ΔF_N` dağıtımı; yatay kuvvet toplamı `VtE` ile dengelenmeli. **Karar:** bağımsız `VtE_X/Y` ve kat kuvvet vektörü; normatif yöntem uygulanabilirliği ayrı ön kapı. **Yol:** K+D+M.

**CHK-104 — Modal taban kesmesi ölçeklenmesi.** **Lazım:** CHK-103'teki VtE, RSX/RSY için global taban kesmesi, A1/B2/B3 varlık durumu. **Var:** RSX/RSY native frame bileşenleri ve statik Base Reactions; **RS için eşlenik Base Reaction tablosu yok**. **How:** RS global Vt bağımsız/same-cut yoldan elde edilince `γE = 0.90` (A1/B2/B3) aksi `0.80`, `βtE=max(1,γE VtE/VtRS)`. **Karar:** kuvvet ve yerdeğiştirmede hangi büyüklüğe ölçeğin uygulanacağı raporlanır; açık VtRS olmadan final `βtE` onaylanmaz. **Yol:** K+D+Y.

**CHK-105 — Etkin göreli kat ötelemesi.** **Lazım:** `Δ_i` azaltılmış tasarım deplasmanı, R/I, DD-2/DD-3 spektrum oranı λ, dolgu duvar bağlantısı, `h_i`. **Var:** statik LC_EQX/LC_EQY için drift, joint displacement, Spektrum DD-2; dolgu bağlantısı ve DD-3 verisi proje profilinde ayrıca gerekebilir. **How:** `δ=(R/I)Δ`; `λ=Sae_DD3(Tp)/Sae_DD2(Tp)`; bitişik gevrek dolgu için `λδmax/h≤0.008κ`, esnek bağlantı için `≤0.016κ` ve bağlantı kanıtı. **Karar:** kat+yön+tüm uçlarda kötü durum; sınırsız `0.008` yerine doğru tasarım dalı. **Yol:** K+D+M (+Y: spektral displacement).

**CHK-106 — A1 burulma düzensizliği.** **Lazım:** her kat+yön+deprem vakasında aynı tip `Δmax`, `Δort`, ±ek dışmerkezlik varyantları. **Var:** `Story Max Over Avg Drifts` 47 satır, `Joint Displacements`; ör. LC_EQX için +4.50 katta tabloda `Ratio=1.208`, LC_EQY için +4.50 `1.342`. **How:** senaryo bazlı `ηbi=Δmax/Δort`; >1.20 için A1 var; varsa sonraki ek dışmerkezlik/katsayı ve γE seçimine etki eder. **Karar:** kaydedilmiş oranlar **ham aday gözlem**; zorunlu ±%5 senaryoları tam değilse nihai A1 `NOT_PROVEN`. **Yol:** K+D+Y.

**CHK-107 — A2 kat döşemesi süreksizliği.** **Lazım:** floor poligonları, boşluklar, kat brüt alanı, in-plane aktarım geçitleri. **Var:** 97 floor poligonu, point/joint koordinatları, kat geometrisi. **How:** geometrileri union/holes topolojisiyle kur; boşluk oranı >1/3 veya kuvvet geçişini güçleştiren özel yerel boşluk/in-plane ani azalma dallarını kontrol et. **Karar:** A2 bulunursa membran/shell düzlem-içi deprem transferi gerekir; eksik açıklık tanımı varsa geometrik ön kontrol. **Yol:** K+D+M.

**CHK-108 — A3 planda çıkıntılar.** **Lazım:** kat dış sınırı, ana plan boyutları `Lx,Ly`, ilgili çıkıntılar `ax,ay`. **Var:** floor alanları ve noktaların koordinatları. **How:** aynı kattaki iki doğrultuda projeksiyon oranlarını birlikte değerlendir, `ax>0.2Lx` **ve** `ay>0.2Ly` koşulunun ilgili plan tipi üzerinde oluşup oluşmadığını belirle. **Karar:** plan geometrisi eksikse `UNDETERMINED`, A3 varsa dijital döşeme aktarımı/analiz yöntemi dalına giriş. **Yol:** K+D.

**CHK-109 — B1 zayıf kat.** **Lazım:** her kat ve yönde kolon/perde etkili alanları `Aw,Ag` ve dolgu duvar `Ak`, dolgu malzemesi/boşluk ve kat bazında bağıl tanımlar. **Var:** kolon/perde topolojisi ve kesiti; WDL pattern bulunuyor fakat fiziksel dolgu duvar envanteri kesinleşmemiş. **How:** `Ae=ΣAw+ΣAg+0.15ΣAk`, alt/üst oran `ηci=Ae_i/Ae_i+1`; uygun istisnada dolgu alanı çıkarılır. **Karar:** ≥0.80 düzenli; 0.60–0.80 aralığı R yaptırımı; <0.60 için reanalysis; dolgu envanteri olmadan boş duvar kabul edilmez. **Yol:** K+D+M.

**CHK-110 — B2 yumuşak kat.** **Lazım:** her katın **ortalama** `Δ_i` değeri, `h_i`, her komşu kat, ilgili deprem yönü/senaryosu. **Var:** Story Max Over Avg `Avg Drift`, Story Definitions yükseklikleri, joint displacement, LC_EQX/LC_EQY. **How:** her senaryoda `r_i=Δ_i,ort/h_i`; `r_i/r_(i+1)` ve `r_i/r_(i−1)` mevcut komşular için; 2.0 üzeri durum B2. **Karar:** `Story Stiffness` oranını B2'nin yerine kullanma; ayrı yön ve komşu sonuçlarını tut. **Yol:** K+D+Y (ilgili eksantrisite/spektral senaryolar için).

**CHK-111 — B3 düşey eleman süreksizliği.** **Lazım:** katlar arası fiziksel column/wall uç bağlantıları, kiriş/konsol türü ve düşey yük yolu. **Var:** wall/beam/column/point connectivity, yükseklikler. **How:** alt elemanı olmayan kolonu, kiriş üstünde oturan kolonu, üstten kolonla devam eden perdeyi, kiriş üzerinde sonlanan perdeyi topolojik olarak sınıflandır. **Karar:** TBDY 3.6.2.4 mutlak yasak ile ilave düşey deprem analizi gerektiren koşulları farklı aksiyonlara ayır. **Yol:** K+D.

**CHK-112 — Bina devrilme ve perde payı.** **Lazım:** kat yatay kuvvetleri ve yükseklikleri, taban momentleri, perde taban momentleri, aynı kesit ve deprem senaryosu. **Var:** statik Story Forces, Base Reactions, Pier Forces, joint reactions, fiziksel perde eşlemesi. **How:** `M_o=ΣFi·Hi`; aynı cut'taki perde momentiyle oran kur; uygun karma sistem için TBDY 4.3.4.5'in %40/%75 koşulunu sınıflandır. **Karar:** temel devrilme emniyeti ve sistem seçimi için perde moment payını farklı check'ler olarak tut. **Yol:** K+D+Y (RS/base same-cut).

**CHK-113 — Bina global ikinci mertebe göstergesi.** **Lazım:** `Δ_i,ort`, i üstündeki kat ağırlıkları `Σw`, kesitteki yatay kat kesmesi Vi, hi, R/D/Ch, deprem doğrultusu. **Var:** mass summary, Story Drifts/Max-over-Avg, Story Forces, Story Definitions; statik LC_EQX/LC_EQY için veri yolu açık. **How:** TBDY 4.9.2 `θII,i = Δ_i,ort Σw/(Vi hi)`, max θ; eşiği `0.12 D/(Ch R)`; aşımda ilgili βII veya reanalysis dalı. **Karar:** 1. mertebe/2. mertebe modele gömülü tekrar büyütme engellenir. **Yol:** K+D+M.

**CHK-114 — Temel kuvvet aktarımı.** **Lazım:** kolon/perde taban kesiti kuvvetleri, joint reactions, temas taban düzlemi, temel/zemin geometrisi. **Var:** statik joint reactions/base reactions ve frame/pier uçları. **How:** ortak taban cut'ında `ΣF,ΣM` dengesini kur; destek reaksiyonunu geometriye dağıtılmış yük olarak değil, kuvvet akışı kanıtı olarak raporla. **Karar:** üstyapı taban iletimi sayısal sınanabilir; gerçek temel dayanımı ayrı geometrik/zemin kaynağı gerektirir. **Yol:** K+D+Y.

### C4 — Kolon tasarım zinciri (CHK-115...129)

**CHK-115 — Kolonda minimum dışmerkezlik.** **Lazım:** kolon kesit boyutları, eksenel basınç `Nd`, yönlü ilk mertebe `M2/M3`, yükleme ve işaret. **Var:** fiziksel kesit ve statik FrameForce. **How:** TS 500 Denk. 6.16'nın ilgili minimum dışmerkezlik gereğini iki yönde ayrı uygula; mevcut `M` yeterli değilse aynı basınç yükünden gelen minimum moment talebini oluştur. **Karar:** yalnız `Nd` ve `|M|max` kaybı olmadan bir tasarım durumu yarat; ikinci mertebe hesabına girdi. **Yol:** K+D.

**CHK-116 — Serbest boy, etkin narinlik ve eğrilik.** **Lazım:** joint I/J, elemanın kat/yatay mesnet durumu, net yüzler arası serbest boy `ln`, yönlü dönme kısıtları. **Var:** point/column/beam connectivity, frame end offsets, story heights. **How:** kat yüksekliğini doğrudan `ln` diye almaz; kiriş/başlık/kolon yüzü ve gerçek mesnet boyunca ayır; iki yönde `i=√(I/A)` ve `M1/M2` hesapla, TS 500 7.6.2.3 narinlik ihmal kriterini uygula. **Karar:** bağımsız X/Y narinlik dalı; uç mesnet derecesi bilinmiyorsa hesap yapılabilen alt sınırı ve eksik kısıtı ayrı yaz. **Yol:** K+D+M.

**CHK-117 — Etkili boy katsayısı `k`.** **Lazım:** CHK-116 serbest boy, uç noktalara bağlanan kiriş ve kolonların I/L rijitlik toplamları, katın yanal ötelenmesi önlenmiş/önlenmemiş sınıfı. **Var:** beam+column topolojisi/kesitler, modifiers, Story Forces/Drifts. **How:** TS 500 7.6.2.2'deki uç `α_1,α_2` oranlarını fiziksel joint bağlantısından türet; yanal ötelenmeli/ötelenmesiz dalın kendi k formülünü uygula; `lk=k ln` üret. **Karar:** bilinmeyen bağlantıyı otomatik k=1 ile örtme, gerekirse mühendis girdili conservative scenario ayrı tut. **Yol:** K+D+M.

**CHK-118 — Global P–Δ ve büyütme sahipliği.** **Lazım:** CHK-113 story θ, analizde P–Delta'nın zaten dahil olup olmadığı, kombinasyon nesli, R/D. **Var:** story statik veri ve analysis options şeması; doğrudan analiz durum kanıtı tamamlanmalı. **How:** TBDY 4.9.2'nin gösterge/βII kararını uygula; gerekiyorsa ilgili global deprem etkilerini büyüt; `P–Δ_ALREADY_INCLUDED` işaretli sonuçlar ikinci kez büyütülmesin. **Karar:** `NO_GLOBAL_INCREMENT / APPLY_INCREMENT / REANALYSIS_REQUIRED`. **Yol:** K+D+M.

**CHK-119 — TS 500 yerel P–δ, moment büyütme.** **Lazım:** `Nd`, işaretli iki uç momenti, `lk`, `(EI)eff`, kalıcı yük oranı Rm, sway sınıfı, kiriş/kolon etkileşimi. **Var:** statik FrameForce, geometri, malzeme, k için toparlanabilir ek veriler; aday donatı henüz seçilmedi. **How:** TS 500 7.6.2.4 Euler `Nk=π²(EI)eff/lk²`; 7.6.2.5 nonsway `β`, sway kat `βs=1/(1−1.3ΣNd/ΣNk)` ve `ΣNd≤0.45ΣNk`; özel 7.29 dalında `ββs`. X/Y ayrı, işaretli uç momentleri koru. **Karar:** kritik yük, β/βs, yönlü tasarım momenti ve geçerli dal; `Nk≤0`, uygunsuz sınırlarda rejenerasyon veya redesign. **Yol:** K+D+A+M.

**CHK-120 — Nihai ikinci mertebeli iki eksenli PMM.** **Lazım:** CHK-115/118/119 ile büyütülmüş bağlı `Nd,M2d,M3d`, seçili bar geometrisi, fcd/fyd. **Var:** ilk mertebe statik talepler, kaynak kesit/malzeme; tasarım adaylarından türeyecek kapasite. **How:** her combo+station için şekil değiştirme uyumuyla `N–M2–M3` kapasite yüzeyi üret; aynı talebe uygulanabilir kesişim/radial demand-capacity oranı; basınç/çekme ve iki eğilme yönü. **Karar:** en büyük etkileşim kullanım oranı ≤1 ve tüm senaryolar kapsandığında aday PMM uygun; spektral eşzamanlılık politikası eksikse **nihai** karar `NOT_PROVEN`. **Yol:** K+D+A.

**CHK-121 — Kolon boyuna donatı detay yerleşimi.** **Lazım:** seçilmiş çubuk adedi/çap, köşe/ara bar koordinatları, net örtü, etriye/çiroz, manşon/ek, kolon boyutu. **Var:** kolon kesit geometrisi ve ETABS reinforcement *ayarları*. **How:** TBDY 7.3.2/7.3.3, TS500 ile `rho`, minimum bar çapı, aralık/sığma, simetri, paspayı, ek ve kenetlenme koşullarını tek tek kontrol et. **Karar:** sadece teorik `As` alanı yeterli değil; yerleşim geçmiyorsa aday elenir, solver yeni kafese döner. **Yol:** K+A.

**CHK-122 — Kolon sarılma bölgesi uzunluğu.** **Lazım:** net kolon yüksekliği, büyük kesit boyutu, alt/üst kiriş yüzleri, konsol kolon durumu. **Var:** beam/column topology, offsets, geometriler. **How:** TBDY 7.3.4.1'e göre her uçta `l_s ≥ max(ln/6, 1.5h_max, 500 mm)`; konsol kolonda özel dal. **Karar:** geçerli sarılma bölgesi sınır koordinatlarını fiziksel kolon üzerinde üret; birleştirmede kullan. **Yol:** K+D.

**CHK-123 — Etriye/çiroz geometrisi.** **Lazım:** seçili boyuna çubuk merkezleri, tie çapı/kolu, yatay çiroz açıklıkları, s aralığı, özel deprem kancaları. **Var:** bölüm/boyut; gerçek kafes bağımsız üretilecek. **How:** her yönde sarılma ve orta bölge için TBDY 7.3.4, TS500 enine donatı uygunluğu; sarılmada `50 mm ≤ s ≤ min(b_min/3,6ϕ_long,min,150 mm)` ve yanal kol mesafesi `≤25ϕ_tie`, diğer özel koşulları uygula. **Karar:** tüm uzunluk boyunca seçilmiş çiroz yerleşimini çizelgeye dönüştür; yalnız `s=100` demek PASS değildir. **Yol:** K+A.

**CHK-124 — Sarılma donatısı gerekli `Ash`.** **Lazım:** çekirdek boyutları, enine kollar ve alanları, `Nd/(Ac fck)`, s, `fck,fywk`, seçili donatı. **Var:** malzeme/kesit ve tüm statik N; önerilen kafes üretilebilir. **How:** TBDY 7.3.4.1(b) eksenel yük dalını seç, her iki doğrultuda Denk.(7.1)'in elverişsiz şartını çöz; sağlanan gerçek `Ash` ile karşılaştır. **Karar:** X/Y ve alt/üst sargı alanı uygun olana dek aday tie/rebar yenile. **Yol:** K+D+A.

**CHK-125 — SCWB: kirişten güçlü kolon.** **Lazım:** joint topology, üst/alt kolon `Mr` değerleri, birleştiren kirişlerin mesnet yüzü `Mr`, ilgili `Nd` aralığı ve her deprem yönü. **Var:** 87 kolon+180 kiriş geometrisi/topolojisi; gerçek beam/column design rebar henüz seçilmedi. **How:** CHK-134 kiriş kapasiteleri + CHK-120 kolon kapasiteleri → TBDY 7.3.5 `ΣMr,column≥1.2ΣMr,beam`; 7.3.5.3 muafiyetleri ayrı. Sağlanmayan joint'leri kat/yön bazında 7.3.6 `α_i=V_is/V_ik≥0.70` ile sınıflandır ve gerekiyorsa uygun kolon M/V büyütmesini tekrarla. **Karar:** joint düzeyi karar ile kat düzeyi istisnayı birbirine çevirmeden üret. **Yol:** K+D+A.

**CHK-126 — Kolon kapasite kesmesi `Ve`.** **Lazım:** SCWB joint durumu, her uç için kapasite momenti veya beam Mp dağıtımı, net boy, `D×E` büyütülmüş kesme talebi. **Var:** statik V ve geometri, onaylı combo tanımları; uç kapasitesi tasarımdan gelecek. **How:** TBDY 7.3.7.1–7.3.7.3'e göre joint uygunsa beam-end moment kapasitelerinden kolon paylaşımı; değilse kolon uç Mp; `Ve=(Ma+Mü)/ln` ve D ile büyütülen kesmenin ilgili sınırlama dalı. **Karar:** her X/Y ve deprem işareti için yönetici Ve; sonra CHK-127. **Yol:** K+D+A.

**CHK-127 — Kolon kesme dayanımı.** **Lazım:** CHK-126 Ve, yönlü `Aw,d`, `fck/fctd/fywd`, enine seçilmiş `Asw/s`, eksenel kuvvet, Vc katkısının deprem dalı. **Var:** kesit/malzeme; seçili tie çözümü üretilebilir. **How:** TS 500 8.1.4 `Vr=Vc+Vw`, TBDY 7.3.7 gevrek kırılma sınırı ve beton katkısı istisnaları; `Ve≤Vr` ve `Ve≤0.85Aw√fck` ayrı koşullar. **Karar:** sadece kapasite oranı değil, sarılma ve donatı minimumları da geçmeli; uygunsuzsa tie veya kesit tasarımı yeniden. **Yol:** K+D+A.

**CHK-128 — Kiriş-kolon birleşimi kesme.** **Lazım:** her joint'e bağlanan kirişlerin seçilmiş çekme donatı alanı `As1/As2`, kolon kesmesi `Vkol`, gerçek `bj,h`, kuşatılma koşulu. **Var:** joint/beam/column geometri, FrameForce V; seçilmiş rebar henüz tasarlanacak. **How:** TBDY 7.5.1 ile kuşatılmış/kuşatılmamış sınıflandır; 7.5.2 `Ve=1.25 fyk(As1+As2)−Vkol`, `1.7bj h fck` / `1.0 bj h fck` sınırları ve panel enine donatı. **Karar:** her joint ve deprem işareti için gerçek `bj` seçimi açık; yetersizlik önce kesit/rebar tasarımına döner. **Yol:** K+D+A.

**CHK-129 — Kolon tasarımının yakınsaması.** **Lazım:** CHK-120/125/126/127/128 ve beam-end moment kapasitesi sonuçları, sabit aday dizisi. **Var:** ilk mertebe kuvvet/kesit; diğer hesaplar analitik olarak tanımlanmış. **How:** *önce* beam adayları → kolon aday PMM → uç momentleri → SCWB/α → moment ve kesme güncelleme → tie/joint → yeniden PMM; seçilen donatı değişince bağlı sonuçları geçersiz kıl. **Karar:** bütün bağlı kontrol sonuçları aynı tasarım iterasyonunda geçerse `CONVERGED`; aksi `RETRY / NO_FEASIBLE / REANALYSIS_REQUIRED` ve sebep. **Yol:** D+A+M.

### C5 — Kiriş tasarımı (CHK-130...139)

**CHK-130 — Kiriş geometrisi, sınıf ve eksenel uygulanabilirlik.** **Lazım:** b, h, ln, yerel eksen, mesnetler, kesit malzemesi, eksenel tasarım N, yüksek süneklik sınıfı. **Var:** 180 fiziksel kiriş, bölüm ve FrameForce. **How:** TBDY 7.4.1 yüksek süneklikli kiriş koşullarını, tipleri (çerçeve/konsol/bağ kirişi/kısa kiriş) ve eksenel sınırını sınıflandır; yanlış aileyi standart kiriş hesaplarına sokma. **Karar:** her kiriş için geçerli tasarım algoritması dalı. **Yol:** K+D.

**CHK-131 — Kiriş eğilme hesabı.** **Lazım:** imzalı mesnet ve açıklık M3/M2, kolon yüzüne taşınmış kesit, `d`, malzeme ve doğru tasarım combo ailesi. **Var:** native beam FrameForce statik/spektral bileşenler, offsets, kesitler. **How:** açıklık ve mesnet eğilme yönleri için TS 500 beton basınç ve donatı çekme dengesiyle gereken As'yi çöz; yük durumu alt/üst ve I/J yönünü koru. **Karar:** `As,required(beam,face,sign,combo)`; aşırı basınç/çift donatı gerekirse alternatif dal. **Yol:** K+D+A.

**CHK-132 — Üst/alt seçilmiş kiriş donatısı.** **Lazım:** CHK-131 As talebi, mevcut stok çapı, net örtü, mesnet/komşu açıklık sürekliliği. **Var:** beam section geometry, ETABS reinforcing tablosu; I/J Top/Bottom alanları 0 yani seçili proje donatısı kanıtı değil. **How:** standard bar çap/adet kombinasyonlarından momentleri sağlayan ve sığan upper/lower kafesler seç; düzeni I/J ve açıklıkta sakla. **Karar:** seçilmiş As + net bar merkezi; diğer kiriş hesaplarının tek kapasite kaynağı. **Yol:** K+A.

**CHK-133 — Kiriş minimum/maksimum donatı.** **Lazım:** CHK-132 seçili donatı alanları, `bw,d,fcd/fyd`, yüksek süneklik detayı, kritik bölgeler. **Var:** geometri ve malzeme; aday rebar üretilebilir. **How:** TS 500 min/dengeli/max eğilme donatısı ve TBDY 7.4.2–7.4.3'te moment yönü, sürekli alt/üst oran, kesme/ankraj sınırlamalarını ayrı denetle. **Karar:** her mesnet yüzü ve açıklık için `REBAR_VALID` veya aday revizyonu. **Yol:** K+D+A.

**CHK-134 — Kiriş uç moment kapasiteleri `Mr/Mp`.** **Lazım:** seçilmiş üst ve alt çubuklar, kolon yüzü kesiti, fcd/fyd, gerektiğinde fyk, net `d`. **Var:** kesit ve yükleme, seçilen rebar CHK-132'den. **How:** iki deprem işaretinde her uç için pozitif/negatif moment taşıma gücü `Mr`; TBDY 7.4.5.1 yaklaşık plastik moment `Mp≈1.4 Mr` uygun dalda veya kesit strain compatibility. **Karar:** beam capacity book; CHK-125 SCWB, CHK-135 shear ve CHK-128 joint bu **aynı** kapasite kaydını tüketir. **Yol:** K+D+A.

**CHK-135 — Kiriş kapasite kesmesi.** **Lazım:** yük kombinasyonundan Vdy, CHK-134 beam `Mp_i/Mp_j`, net açıklık `ln`, D ile artırılmış deprem kesme talebi. **Var:** native V ve beam topology; Mp bağımlı hesap. **How:** TBDY 7.4.5.1 `Ve=Vdy ± (Mpi+Mpj)/ln` her iki deprem yönünde; ilgili D ile büyütülmüş kesme sınırlaması; govern Ve. **Karar:** Ve ayrı türetilmeden `max(|V2|)` kapasite kesmesi kabul edilmez. **Yol:** K+D+A.

**CHK-136 — Kiriş etriye hesabı.** **Lazım:** CHK-135 Ve, `bw,d,fck/fctd/fywd`, sargı bölgeleri, seçilmiş etriye çapı/kol sayısı/s. **Var:** geometri/malzeme ve aday seti. **How:** TS 500 kesme katkısı `Vr=Vc+Vw`; TBDY 7.4.5.3'ün sarılma bölgesinde deprem katkısı baskınsa `Vc=0` koşulu; etriye min/max, aralık, sarılma boyu `2h`. **Karar:** `Ve≤Vr`, beton ezilme sınırı ve detailing birlikte geçmedikçe FAIL. **Yol:** K+D+A.

**CHK-137 — Kiriş burulma.** **Lazım:** ilgili tasarım kombosunda `Td,Vd`, kapalı etriye geometrisi, `Ao,Ae`, boyuna burulma donatısı ve malzeme. **Var:** beam native `T` ve `V`, section geometry. **How:** TS 500 Bölüm 8.2 burulma eşiği, V–T etkileşimi, kapalı etriye `Aov+Aot` ve ek boyuna donatıyı doğru yönde çöz; gerekiyorsa kiriş tipi özel dalı. **Karar:** seçilen kesit ve rebar birlikte taşımalı; tek `Tmax` ile farklı load `Vmax` fiziksel eşzamanlı sayılmaz. **Yol:** K+D+A.

**CHK-138 — Kiriş çatlama ve kısa/uzun süreli sehim.** **Lazım:** servis kombinasyonları, mesnet koşulları, `Ec,Ieff`, span, anlık displacement veya moment diagram, yükün süresi, çatlama ve donatı. **Var:** `Joint Displacements`, native statik beam moments, kesit boyları; süreklilik ve kalıcı yük oranı ayrıştırılabilir. **How:** TS500 Bölüm 13 ve uygulanabilir sehim/çatlak yönteminden `δ_i` ve `δ_long` üret; mutlak yer değiştirmeden mesnet hareketini ayır; artımlı servis yüklerini kapsa. **Karar:** uzun süreli sünme/rötre parametresi eksikse anlık sehim ayrı, uzun süreli `NOT_PROVEN`. **Yol:** K+D+A+M.

**CHK-139 — Kiriş boyuna donatıda kenetlenme ve süreklilik.** **Lazım:** actual/proposed bar merkezleri, mesnet kolon yüzü, bindirme/ankraj uzunluğu, kanca, `fcd/fyd`, komşu kirişler. **Var:** beam/column joint topology ve malzeme, önerilen rebar. **How:** TBDY 7.4.3 + TS500 kenetlenme/bindirme, kolon içi mevcut ankraj boyu, açıklık boyunca kesilen çubuklar ve mesnet devamlılığını ayrı kontrol et. **Karar:** kalıp ve çubuk yerleşim geometrisiyle doğrulanmış detay olmadan kapatılamaz; inadmissible rebar candidate yeniden seçilir. **Yol:** K+D+A.

### C6 — Perde, bağlı kiriş ve düğüm topolojisi (CHK-140...148)

**CHK-140 — Fiziksel perde ve pier etiketleri.** **Lazım:** kat bazında wall object, geometrik corner points, assigned pier label, wall thickness, top/bottom source cut. **Var:** 30 wall, 29 `Area Assignments – Pier Labels`, 360 statik `Pier Forces` satırı, 4 wall property. **How:** bir fiziksel duvarın farklı shell parçaları ve aynı pier adındaki parçalar arasında çoktan-bire ilişki kur; wall segment→pier group→story cut eşle. **Karar:** eşleşmeyen fiziksel perdeyi `no-pier-result` diye kaydet; yanlış `P1=P1` isim eşitliğiyle geometrik uyum varsayma. **Yol:** K+D.

**CHK-141 — Perde eksenel+eğilme kapasitesi.** **Lazım:** CHK-140 net plan kesiti, tasarımda kullanılmış imzalı `Nd,M2,M3`, gerçek/aday gövde+uç donatısı, fck/fyd. **Var:** statik Pier Forces ve fiziksel kesit; onaylı perde donatısı bulunmuyor. **How:** dikdörtgen/L/T/U/çok parçalı perde için uyumlu şekil değiştirme veya fiber integrasyonuyla P–M kapasitesini gerçek kesit üzerinde hesapla; aynı case/cut talebiyle kıyasla. **Karar:** gerçek donatı verisi yoksa önerilen tasarım adayı; hem kesit hem kat/yük seti tamamlanmadan kesin PASS değil. **Yol:** K+D+A.

**CHK-142 — Kritik perde yüksekliği ve uç bölge geometrisi.** **Lazım:** net duvar boyu `lw`, kalınlık `bw`, toplam gövde yüksekliği `Hw`, katlar arası geometri değişimi, bağlantılı perdeler. **Var:** wall object coords + sections + story elevations. **How:** TBDY 7.6.2.2 `Hcr` için `lw`, `Hw/6`, `2lw` üst sınırı ve rijit bodrum istisnası; 7.6.2.3 kritik bölgede uç uzunluğu `max(0.20lw,2bw)`, üstte `max(0.10lw,bw)` uygun dal. **Karar:** her kat/perde segmenti `in_critical_zone` ve `boundary_len_required` üret. **Yol:** K+D+M.

**CHK-143 — Perde gövde ve uç donatısı.** **Lazım:** CHK-142 boundary, perde kalınlık ve gövde doğrultusu, donatı dikey/yatay çap/s, uç sıklaştırması, fyk. **Var:** wall geometry/material; seçilmiş wall bar layout yok. **How:** TBDY 7.6.3–7.6.5 gövde min alan/aralık, uç boyuna ve enine donatı, kritik yükseklik ve birleşim/yerleşim koşullarını ayır. **Karar:** kesit As miktarı + konstrüktif düzen doğrulanmadan wall design bitmez. **Yol:** K+D+A.

**CHK-144 — Perde kesme ve kapasite kesmesi.** **Lazım:** `Vd,Md` aynı perdenin aynı kesitinden, `Mpt/Mdt`, `βv`, D, seçili yatay donatı, `Acv,fck`. **Var:** 360 statik pier Top/Bottom P–V–M satırı, perde geometry; donatı ve uygun spektral kutuplaşma ayrı. **How:** TBDY 7.6.6.3 ilgili narin perde dalında `Ve=βv Vd (Mpt/Mdt)` ve D artırımı ile sınır koşulunu; kısa perdede farklı dal; ardından `Ve≤Vr` ve gevrek kesme sınırı. **Karar:** bunlar `Vmax` tablosunun yerine geçmeyen *capacity-design* hesaplarıdır; her yüksekliğin fiziksel story cut'ı kaydedilir. **Yol:** K+D+A.

**CHK-145 — Bağ kirişli perde ve bağ kirişi.** **Lazım:** birbirine bağlanan iki pier, aradaki açıklık/derinlik oranı, bağ kirişi konum/yerel eksen ve V–M–N, düşey süreklilik. **Var:** pier labels, beam/wall connectivity ve frame forces. **How:** bağlantı topolojisiyle **coupled wall** sınıfını belirle; uygun normal kiriş/özel diagonal donatılı bağ kirişi dalı için kesme/eğilme, diyagonal donatı, ankraj ve bağ kapasitesi hesapla. **Karar:** keyfi beam adıyla değil fiziksel perde çiftine göre sınıf; yetersiz bound tasarımına döner. **Yol:** K+D+A.

**CHK-146 — Kat kesmesi paylaşımı ve `story φ` / SAME_CUT.** **Lazım:** her kat ve yönde fiziksel aynı seviyede story shear `V_story`, perdelerin toplam `V_wall`, kolonların toplam `V_col`, varsa bodrum/pier üst-alt ayrımı. **Var:** statik Story Forces, Pier Forces, frame force ve reactions; bağ geometrisi mevcut. **How:** `V_wall/V_story` ancak aynı **physical horizontal cut**, aynı yükleme ve aynı generation için hesaplanır; pier top/bottom ve kolon I/J işaretleri fiziksel kesite dönüştürülür; toplam farkı `ΣV_wall+ΣV_col−V_story` hesapla. **Karar:** önce **force-balance evidence**, sonra yönetmelik maddesinin ihtiyaç duyduğu `φ_i`, kapasite/sistem sınıfı; gözlem uyuşması = mevzuat PASS değildir. **Yol:** K+D+Y (tam RS ve aynı kesit kanıtı).

**CHK-147 — Kolon-kiriş joint topolojisi.** **Lazım:** physical point/joint, frame ends, yerel yön, beam face, kolon alt/üst, edge/interior/corner classification. **Var:** physical connectivity, frame section, local axes. **How:** her joint için yukarı/aşağı kolon ve sağ/sol/ön/arka beam komşularını koordinat ve kesit/offset ile eşle; eşleşmeyen veya yüksekliği farklı uçları nedeni koduyla raporla. **Karar:** CHK-125, 126 ve 128 aynı `JointTopology` kullanır; tekrar tekrar elle toplama yok. **Yol:** K+D.

**CHK-148 — Joint bölgesi sargı.** **Lazım:** CHK-147 joint classification, alt kolonun gereken tie `Ash`, `bw,h`, seçilen çiroz/tie ve devamlı kolon bilgisi. **Var:** joint geometri, kolon aday tie hesabı. **How:** TBDY 7.5.2.3 kuşatılmış joint'te en az alt kolon sargısının %40'ı, kuşatılmamışta %60'ı ve ilgili çap/aralık üst sınırlarını sağla. **Karar:** birleşim kesme dayanımı ile sargı denetimi ayrı sonuç; her ikisi doğruysa panel tasarımı kabul adayı. **Yol:** K+D+A.

### C7 — Döşeme ve diyafram (CHK-149...153)

**CHK-149 — Döşeme geometrisi/kalınlığı.** **Lazım:** fiziksel floor poligonları, boşluklar, kesit kalınlığı, açıklık, mesnet türü, tek/çift yönlü çalışma ve konsol. **Var:** 97 floor object, Slab Property Definitions, point coordinates. **How:** destek çizgileriyle net açıklıklar ve uzun/kısa oranını türet, TS 500 Bölüm 11'e göre tipe özgü minimum kalınlığı kontrol et. **Karar:** destek türü/yük dağılımı bilinmiyorsa geometrik ön kontrol, yanlış `ln` varsayımı yerine nesne bazlı ölçüm. **Yol:** K+D+M.

**CHK-150 — Döşeme eğilme ve donatı.** **Lazım:** shell/membrane eleman sonuçları `M11,M22,M12` ve konum, mesh, malzeme, `d`, mesnet/kenar, yük kombinasyonları. **Var:** floor geometry/material; **Element Forces – Area Shells** mevcut ZIP'de yok, fakat ETABS tablo envanterinde bilinen bir kaynak ailesi. **How:** analizden gerçek shell moment field al, hesap doğrultusunda tasarım momentlerini (gerekirse burulma momentini dahil eden plaka donatı dönüşümü) değerlendir, her yönde üst-alt `As` ve spacing/tie/detailing üret. **Karar:** geometriye bakarak shell `M11` uydurulamaz; FE çıktısı bekleyen yalnız bu bağımlı aile `NOT_PROVEN`. **Yol:** K+A+Y.

**CHK-151 — Döşeme/temelde zımbalama.** **Lazım:** kolon/perde çevresi, efektif derinlik, destek yakın kenarlar/boşluklar, dengelenmemiş moment ve V aktarımı, seçilen kesit ve zımbalama donatısı. **Var:** column/wall floor geometrisi, reaksiyon/kuvvetin statik bir kısmı, zımbalama Excel golden örnekleri. **How:** ilgili TS500 8.3 kritik zımbalama çevresini gerçek geometride kes, açık kenar/boşluk indirimi ve moment aktarımını hesaba kat, `Vpd≤Vpr` ve varsa zımbalama donatısı. **Karar:** kolon eksenel maksimumunu tek başına `Vpd` sanma; destek yüzü ve slab load transferi gerekir. **Yol:** K+D+A+Y.

**CHK-152 — Döşeme ani/uzun süreli sehim ve çatlak.** **Lazım:** servis yük grubu, shell mesh `Uz` deplasman alanı, destek deplasmanı, çatlama/efektif EI, donatı, kalıcı yük oranı ve sünme/rötre parametreleri. **Var:** `Joint Displacements (Including Internal Mesh Joints)` 90.456 statik sonuç, slab properties; geometrik destekler. **How:** mesnetlerin ilgili yerdeğiştirmesini kaldırarak **göreli sehim** çıkar; TS500 anlık ve zamana bağlı ek sehim hesabı (`λ` ve basınç donatısı/kalıcı yük) veya onaylı time-dependent FE sonucu. **Karar:** `δ_short` mevcut kayıttan ön-hesaplanabilir; `δ_long` ancak süre/çatlak/reep alanları doğrulanırsa onaylanır. **Yol:** K+D+A+M (+Y: seçilmiş zaman-bağımlı analiz varsa).

**CHK-153 — Diyafram düzlem-içi yük aktarımı.** **Lazım:** floor shell/membrane `F11,F22,F12`, deprem kat kesmeleri, diyafram collector/chord/yol, perdelerle ortak kesit. **Var:** floor/wall/diaphragm assignments, story and frame forces; bu yakalamada shell in-plane force/diaphragm force tablosu yok. **How:** gerçek deprem yükü akışını düğüm→diyafram→collector→perde/kolon arayüzü üzerinden dengele; A2/A3 varsa TBDY 3.6.2.2 ve 7.11.5 koşullarını kontrol et. **Karar:** sadece kat ötelemesinin PASS olması diyafram aktarımına kanıt değildir; hedefli shell/diaphragm force kaydı. **Yol:** K+D+A+Y.

### C8 — Temel ve zemin aktarımı (CHK-154...158)

**CHK-154 — Temel geometrisi ve support mapping.** **Lazım:** radye/tekil/sürekli temel poligon, kalınlık, destek, temel mesh ve kolon/perde alt yük bağları. **Var:** üstyapı taban joint/kolon/perde ve reaksiyon; gerçek foundation geometry ZIP'de yok. **How:** varsa SAFE/ETABS foundation modelinden temel geometrisini bağımsız fiziksel ağaca ekle, yalnız aynı model-taban nesliyle eşleştir. **Karar:** foundation geometri yoksa temel boyut PASS'i değil; topoloji sözleşmesi hazır. **Yol:** K+Y.

**CHK-155 — Zemin basıncı / taşıma gücü.** **Lazım:** CHK-154 temel alanı ve q(x,y), aynı servis/tasarım yükleri, zemin araştırma raporu `q_allow` veya tasarım taşıma gücü/oturma kriterleri, su seviyesi. **Var:** yüklerden taban reaksiyonu; kompakt modelin geoteknik verisi arşivde yok. **How:** mesnet kuvvet ve momentini temas gerilmesi/SAFE nonlinear spring result ile eşle, yönetmelik ve geoteknik tasarım dalında maksimum-minimum q ve eksantrisiteyi denetle. **Karar:** örnek rapordaki başka yapının zemin basıncı limiti bu projeye ithal edilmez; `NOT_PROVEN` ve minimum veri talebi. **Yol:** K+D+Y+M.

**CHK-156 — Temel tek yönlü kesme + zımbalama.** **Lazım:** temel kalınlık/d, kolon/perde yük aktarım yüzleri, alt zemin reaksiyon dağılımı, kontrol çevreleri, malzeme. **Var:** üstyapı taban kuvvet ve kesit bilgisi; temel geometry/q eksik. **How:** gerçek basınç alanını tek yönlü kritik kesitte entegre et; kolon/perde çevresinde TS500 8.3 zımbalama ve eksantrik moment aktarımı; üstten gelen kuvvetle alt zemin yükünü dengeli al. **Karar:** Vd/Vr ve Vpd/Vpr ayrı fiziksel kontrol. **Yol:** K+D+A+Y.

**CHK-157 — Temel eğilme, donatı ve detay.** **Lazım:** temel moment field, geometry/d, mesh/support, paspayı, fcd/fyd, üst/alt donatı ve mesnet alanları. **Var:** üstyapı yükleri; gerçek temel FE momentleri yok. **How:** shell `M11,M22,M12` / şerit momentlerinden gerekli üst-alt As, donatı aralığı, minimum donatı, ankraj, kesme ve çatlama kriterlerini çıkar. **Karar:** model/zemin sonuçları olmadan başka Excel'den seçilmiş temel donatısı kopyalanmaz. **Yol:** A+Y.

**CHK-158 — Temelden üstyapıya bütünleşik kuvvet aktarımı.** **Lazım:** foundation reaction/equilibrium ve superstructure support joint, wall/column base, aynı combo ve fiziksel kesit; varsa ankraj yükleri. **Var:** `Joint Reactions`, `Base Reactions`, statik pier/frame kuvvetleri. **How:** `ΣF/ΣM` global denge, ortak base cut/tepki konvansiyonu, tekil kolon/perde payı ve radye arayüz transferi; mesnet adlarını section'larla eşle. **Karar:** üstyapı statik kuvvet dengesi hesaplanabilir; zeminden temele tam transfer için CHK-154–157 gereken kaynaklar ayrı. **Yol:** K+D+Y.

## D. Bir kontrolün diğerine sağladığı hazır girdi (tutarlılık zinciri)

| Paylaşılan türetilmiş büyüklük | İlk üretici | Kullanıcı CHECK'ler | Önemi |
|---|---|---|---|
| `MaterialAssignmentFeature` | CHK-001/002 için ortak kaynak hazırlığı | CHK-003..005, 007, 120..128, 131..157 | Beton malzemesi 20 kez yeniden okunmaz |
| `PhysicalFrameTopology` | SRC-003 / CHK-147 | CHK-116/117, 125/126, 130, 139, 145 | Aynı joint/face ölçüsü; id karışmasını önler |
| `SignedForceBook` | SRC-005 | CHK-004/005, 007, 113, 115..120, 131, 135, 137, 141, 144 | Combo/case/step/face aynı tutulur |
| `MassStoryBook` | CHK-101 | CHK-103/113, 112 | Kat toplamları bina kütlesiyle uzlaşır |
| `ModalSpectralBasis` | CHK-006/011/102 | CHK-103/104/105/106, spectral demand | Aynı tasarım depremi ve R/D/I ailesi |
| `StoryDriftFeature` | CHK-010 | CHK-105/106/110/113 | A1, B2 ve θ aynı fiziksel deplasmandan farklı istatistik üretir |
| `BeamRebarLayout` | CHK-131/132/133 | CHK-134/135/136/137/139, 125, 128 | SCWB/kesme/joint öncesi gerçek kapasiteyi sağlar |
| `ColumnRebarLayout` | CHK-007/120/121 | CHK-124/125/126/127/128 | PMM'den çıkan aday kapasiteye gider |
| `WallSegment↔Pier` | CHK-140 | CHK-141..146, 112, 153, 158 | Perde kesme ve devrilme doğru nesneyle hesaplanır |
| `SlabShellForceField` | CHK-150 için kaynak kapısı | CHK-150/151/153/157 | FE üretimi post-process'te **yeniden icat edilmez** |
| `FoundationContactField` | CHK-154/155 | CHK-156/157/158 | Temel tasarımı zemin gerilmesiyle ortak dengeye dayanır |

**Kural:** `CHECK` başka `CHECK`'in `PASS` kelimesini değil, onun ürettiği sayısal *feature*'ı tüketir. Bir alt hesabın sonucu başarısızsa yine sayısal değer raporlanabilir; ancak üst CHECK'in hesap yolu/uygulanabilirlik şartı bunu belirler. Tasarım çevrimi (`beam reinforcement ↔ SCWB ↔ column reinforcement`) DAG'da sahte dairesel kenar yerine tanımlı `DesignIteration` içinde çözülür.

## E. Uçtan uca yürütme sırası — sadece mevcut verilerle başlayarak

1. **Model ve kaynak güvence:** SRC-001..005; `PhysicalTree`, `AnalysisBasis` ve ComboBook, veri türü etiketleri.
2. **Bina profili, geometrik envanter, malzeme:** CHK-001/002/003, 101, 107/108/111, 130, 140, 147, 149; uygulanmayan aileler saklanır.
3. **Statik replay ve bina dinamiği:** 006/011/102/103, 010/106/110/113; CHK-104/105 için mevcut statik senaryolar ve ayrı spektrum gereksinimleri.
4. **Tasarım yük seti:** her fiziksel kesitte statik imzalı altı kuvvet, spektral bileşen sınırı, kodun tasarım politikasıyla türetilen **ayrı** işaretli adaylar.
5. **Kiriş tasarım adayları:** 130–134; ilk seferde minimum sünek/detaylı yerleşim ve mesnet kapasitesi.
6. **Kolon tasarım adayları:** 004/005/007/009/115–124; her yön ve her seçilmiş tasarım kombinasyonu.
7. **Ortak kapasite döngüsü:** 125–129 + 134–136 + 147–148; SCWB/α, kapasite kesmesi, etriye ve joint. Değişen herhangi bir kafes sonucu bütün tüketicileri yeniler.
8. **Perde/bağ kirişi:** 140–146; aynı cut, güçlü yön/zayıf yön, boundary ve rebar iterasyonu.
9. **Döşeme:** 149; shell kuvvet source gelirse 150/151/153, kısa süreli displacement kanıtından uygun olan 152 ve uzun süreli malzeme girdisi.
10. **Temel:** önce üstyapı mesnet dengesi (114/158), daha sonra gerçek temel/zemin kaynakları gelirse 154–157.
11. **Uzlaştırma:** her check için expected/applicable/evaluated/not_proven/pass/fail/not_applicable toplamı ve *köken* satırları; aynı sonucun farklı yerde tekrar hesaplanması yasak.

## F. Yeni canlı ETABS beklemeden kapanacak işler ve en küçük ek kanıtlar

### F1. Mevcut ZIP ile algoritmik olarak doğrudan yapılabilir

- 267 fiziksel çerçeve elemanının kayıt kapsamı, kuvvet case/step/section kimliği.
- Malzeme/section/kolon boyutları ve fiziksel atamalar, 100 mod katılımı.
- 30 linear / 5 envelope combinasyonun yerel aritmetik replay'i (spektrum semantiği ayrı).
- Statik `LC_EQX/LC_EQY` için story average/max drift hesabının yeniden üretilmesi, A1/B2/θ *sayısal adayları* ve katlar arası eşleşme.
- Kolon-kiriş-joint topolojisi, net uzunluk/serbest boy/geometrik kapsam; ilk mertebe kesit ve donatı adayı matematiği.
- Statik pier force → wall segment mapping; statik mesnet reaksiyonu ve kaynak denge tabloları.
- Geleneksel kiriş/kolon/perde kesit kapasitesi ve sünek detaylar için formüllerin bağımsız golden testleri; gerçek proje onayı ayrıca.

### F2. Mühendislik algoritması tanımlanabilir; proje onayı için kaynağın kararı gerekir

- **DesignBasis:** hangi taşıyıcı sistem, R/D/I, DD-2 ve DD-3 değerleri, gevrek dolgu bağlantısı, kullanılacak tasarım kombinasyonları.
- **SpectralDemandPolicy:** CQC `Max` bileşenlerini tek N–M2–M3 vektör sanmadan, normatif tasarım için korunumlu ve bağımsız sınanabilir yük durumu oluşturma politikası.
- **Donatı seviyesi:** ETABS'ın sadece reinforcement settings alanlarını gerçek donatı olarak değil, *candidate generator* girdisi olarak kullanma; önerilen/fiilen seçilmiş donatıyı birbirinden ayırma.
- **Slab long-term:** kullanıcı süneklik/çatlak ve zaman etkisini nasıl modele dahil etti; TS 500 yaklaşık veya gerçekten time-dependent FE yaklaşımı; hizmet yükü süresi.
- **Foundation:** temelin fiziksel yerleşimi ve geoteknik sınırlara ihtiyaç.

### F3. Akşam canlı ETABS/SAFE mümkünse yalnız hedefli istenecek kaynak

| Öncelik | İstenilen en küçük veri | Hangi kontrolleri açar? | Özellikle dikkat |
|---|---|---|---|
| T1 | `RSX/RSY Base Reactions`, RS `Story Forces`, RS `Story Drifts`, RS joint displacement ve ±ek dışmerkezlik sonuçları | 104/105/106/110/112/113/146, tasarım talebi | Aynı modele ve analiz nesline bağlı, X/Y, output max-min semantiği |
| T2 | `Element Forces – Area Shells` (M11/M22/M12, F11/F22/F12), `Diaphragm Forces` ve seçili combo | 150/151/153, döşeme→perde aktarımı | Eleman topoloji ve mesh, hangi kat ve fiziksel shell yüzü |
| T3 | Tasarım donatıları için seçili gerçek uygulama çizelgesi veya ETABS design detayları | 120–129, 131–139, 141–145, 148 | **Required** alanı ile **Provided/Selected** farklı tutulur |
| T4 | Foundation/SAFE mesh+contact/basınç+soils, zemin raporu | 154–158 | Üstyapı ile aynı yükleme ve geometrik taban referansı |
| T5 | Analiz generation/run metadata ve bağlı run serial / model hash kanıtı | SRC-004, nihai kanıt zinciri | EDB hash'ini tekrar almak tek başına yeterli değildir |

Yalnız mevcut ZIP ile yapılan gerçek hesapların üstüne yeni capture geldiğinde eski sonuçları **kaynak ve algoritma sürümleriyle** koru; yalnız değişen bağımlı hesapları yeniden çalıştır.

## G. Üç örnek CHECK'in her soru altında nasıl çözüldüğü

### G1 — A1: “Elimde iki değer zaten var; daha ne gerekiyor?”

- **Ne?** Bir kat, deprem doğrultusu ve uygun ek dışmerkezlik senaryosu için `ηbi`.
- **Lazım?** Aynı senaryonun `Δmax,Δort`, story, direction; story elevation ve uç/kat eşlemesi.
- **Elimde?** `Story Max Over Avg Drifts` içinde LC_EQX +4.50 X için `0.003834/0.003174≈1.208`; LC_EQY +4.50 Y için `0.004311/0.003212≈1.342`. `Joint Displacements` ile re-compute edilebilir. Bunlar **statik case sayısal gözlemleridir**.
- **How?** Bütün doğru senaryo satırlarını kat/yön bazında tarayıp aynı senaryoda max/avg oranı, ardından gerekli +/− dışmerkezlik varyantlarının max'ı. Kaynak etiketi ve oran eşitliğini doğrula.
- **Karar?** Bu iki örnekte aday A1 eşiği aşılmıştır. Bina geneli kararı için gereken bütün ±eksantrisite ve yönetmelik geçerli deprem seti tamamlanır; A1 varlık bilgisi γE=0.90 ve deprem yöntemi kararında tüketilir.

### G2 — B2: “Story Stiffness yoksa da hesap yapabilir miyim?”

- **Ne?** Komşu katın normalize **ortalama** göreli ötelenmesine göre yumuşak kat.
- **Lazım?** `Story Max Over Avg Drifts.Avg Drift`, kat yükseklikleri, aynı deprem durumu/yön.
- **Elimde?** Üç seviye için statik LC_EQX/LC_EQY `Avg Drift` ve `Story Definitions.Height`; ayrıca `Story Stiffness` teyit amaçlı.
- **How?** Her i için `r_i=AvgDrift_i/h_i`, sonra hem üst hem alt `r_i/r_neighbor`. En yüksek oranı vaka+kat+yön ile sakla; satırları farklı yüklemelerden karıştırma.
- **Karar?** `ηki>2` düzensizlik. Aynı `StoryDriftFeature`, A1 ve global θ'nin de ham verisidir; yeni tablo icat etmeden hesap reuse.

### G3 — SCWB: “ETABS'ta SCWB tablosu yok; nasıl çıkar?”

- **Ne?** Düğümde kolonların moment taşıma gücünün birleşen kirişlere göre yeterliliği.
- **Lazım?** Joint topology, üst/alt kolonların *uygun Nd altındaki* moment kapasiteleri, her iki yönde kiriş uç moment kapasiteleri.
- **Elimde?** Kesitler, malzemeler, 180 kiriş + 87 kolon geometrisi/bağlantıları, native tasarım talebi. Beam reinforcing tanımında 0 alanlar gerçek seçilmiş donatı değil.
- **How?** Önce bağımsız kiriş As→seçili fiziksel bar→Mr(±) üret; kolon için N–M2–M3 kapasite→Mr üret; aynı joint ve deprem yönünde `ΣMr_col / ΣMr_beam` oranını hesapla; uygun istisnaları tanı; ardından kat α ve kesme/rebar değişimini tetikle.
- **Karar?** `ΣMr_col≥1.2ΣMr_beam` ilgili dallarda; aksi 7.3.6 α/paylaşım ve tasarım iterasyonu. Eksik olan yeni ETABS `SCWB` raporu **değil**, güçlendirilmiş iki eleman tasarım zinciridir.

## H. Her kontrolün üreteceği aynı biçimli *mühendislik fişi*

| Alan | Anlam |
|---|---|
| `check_id`, `normative_clause`, `applicability` | Ne/nerede uygulanıyor? |
| `physical_id`, `story`, `direction`, `section_station`, `joint_end` | Hangi fiziksel parça ve kesit? |
| `model_sha`, `analysis_generation`, `case_id`, `combo_operator`, `step`, `units`, `sign` | Hangi kaynak ve hangi hesap/işaret temeli? |
| `required_inputs`, `available_inputs`, `derived_inputs`, `missing_inputs` | Hangi bilgi gerekli/var/türetildi/eksik? |
| `derivation_formula`, `intermediate_values`, `computed_value`, `limit` | Nasıl hesaplandı ve hangi sınıra göre? |
| `source_row_refs`, `independent_oracle`, `test_cases` | Kanıta nasıl dönülür, nasıl doğrulanır? |
| `result`, `status_reason`, `recovery_action` | PASS/FAIL/NOT_PROVEN/NOT_APPLICABLE/REANALYSIS_REQUIRED ve gerekli aksiyon |
| `expected_count`, `evaluated_count`, `blocked_count` | Bütün fiziksel elemanlar değerlendirildi mi? |

**Nihai mantık:** “Eksik tablo var” yerine “**CHECK'i hangi hesap büyüklüğü bloke ediyor ve bu büyüklüğü elimizdeki hangi başka veri üretebilir?**” sorusunu sürekli sor. Veri gerçekten FE çıktısı ise yeni analysis/capture; veri geometrik veya matematiksel türevse offline hesap; donatı ya da sistem tipi ise bağımsız mühendislik tasarımı/seçimi; bilinmiyorsa gerekçeli `NOT_PROVEN`. Kaynak alanındaki her sayı mutlaka doğru tüketiciye gider.

## I. Kaynak referansları ve kapsam notu

- `kompakt_b.EDB` kullanıcı kaynak arşivi: `CAPTURE-20261113T051055Z-751a4137_kompakt_b.EDB(1).zip`.
- 73 aday check tanımı: `TBDY_NEXT_ENGINE(1).zip/config/check_registry/checks.json`.
- Kullanıcının önceki karar kuralı: `TBDY_Next_Engineering_Rulebook_No_Code_2026-11-13.md`.
- TBDY 2018 tam metin: https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf
- TS 500 metni (kullanıcı Drive): https://drive.google.com/file/d/1GIaAvx7CDm8PWNmESMKl2GikQcJc1DBH/view
- 2018 TBDY normatif metni (kullanıcı Drive): https://drive.google.com/file/d/1tlILuDbRso80oQLPswhlsw8wd0uMNKnE/view
- `TBDY2018_DD2_Linear_Design_Check_System_FINAL.xlsx` (Drive): https://docs.google.com/spreadsheets/d/10dEe6kcthWLP8bsCnU6a6tvO7OPlxlLt/edit
- `B_Blok_manual_audit_workbook_v1.xlsx` (Drive): https://docs.google.com/spreadsheets/d/1VkOMgxwdm3VUVHGh7jZT3JS2QVa4tnN9/edit
- Örnek kontrol raporları: `ETEX_ORNEK_RAPOR.pdf`, `Hesap rapor.pdf` (Drive).

**Not:** Bu belge 73 **aday CHECK'in hesap yolunu** açıklar. Hepsinin yazılımı çalışıyor, hepsi sahada test edildi veya tüm kuralları onaylandı iddiası yoktur. Bazı kod maddelerinde ana yöntem tanımlanmış; detaylar, özel sistem dalları ve güncel yürürlük sürümü her alt-kontrolün normatif incelemesinde ayrıca gözden geçirilmelidir. Amaç kanıtı bulmadan PASS ilan etmek değil, mevcut veriden **en fazla güvenilir mühendislik hesabını** üreten tutarlı zinciri kurmaktır.


## J. Eklenen 31 kontrolün tamamlayıcı mühendislik reçeteleri

Bu bölüm, kullanıcının son gönderdiği taslakta **açık ID olarak yer almayan**, fakat gerçek 73'lü katalogda bulunan kontrollerin hesap zincirini derinleştirir. Önceki C bölümündeki tüm 73 kaydı geçersiz kılmaz; bunların asgari girdisini, ara sonuç sahipliğini ve yürütme sırasını somutlaştırır.

### J1 — Kaynak, malzeme ve ilk kapasite kapıları

**SRC-002 — Model ve birim kimliği.** **Ne lazım?** EDB'nin yakalama öncesi/sonrası hash'i, birim kodu, eleman isim uzayı, kaynağın kilit/analiz durumu. **Elimde:** `source_identity_before/after`, aynı EDB SHA-256, ETABS `present_units_code=6`, field metadata. **How?** Aynı kaynak dosyasının önce/sonra değişmediğini teyit et; her ham kolonun birimini tanımla; kN–cm–MPa ile N–mm–MPa dönüşümünü izlenebilir yap. **Karar/çıkış:** `SourceIdentityFeature`, `UnitContract`; analiz-generation ispatı için SRC-004'e ayrı kanıt gider. **Yol:** K.

**CHK-005 — TS 500 basınç sınırı.** **Ne lazım?** Her kolonun `Ac`, `fcd`, basınç işareti ve ilgili tüm tasarım kombinasyonlarında en büyük basınç. **Elimde:** fiziksel kesitler ve statik FrameForce; spektral tasarım talebi için ayrı talep politikası gerekiyor. **How?** Aynı kesitteki tüm geçerli tasarım kombinasyonlarını tara; TS 500 §7.4.1 ilgili tasarım basınç sınırını `Nd ≤ 0.9·fcd·Ac` olarak kontrol et; TBDY §7.3.1.2'deki `0.40·fck·Ac` koşulunu onun yerine koyma. **Karar:** iki sonuç ayrı raporlanır; kombolar eksikse nihai projeye `NOT_PROVEN`. **Yol:** K+D+M.

**CHK-007 — Birinci mertebe kolon PMM ve aday donatı.** **Ne lazım?** Geometri, malzeme eğrileri, gerçek yönlü `N,M2,M3` talebi, beton örtüsü, donatı çap/yerleşim adayları. **Elimde:** kolon geometri ve statik imzalı talep kayıtları, malzeme; gerçek uygulanmış donatı yok. **How?** Seçilen donatı kafesi için düzlem kesit varsayımıyla birim şekil değiştirme alanları tara, beton ve çelik iç kuvvetlerini integre ederek `N–M2–M3` etkileşim yüzeyi kur; talebi yalnız eşzamanlılığı kanıtlı aday noktalardan test et; boyuna yerleşim ve min/max donatı kurallarını ayrı doğrula. **Karar:** birinci mertebe aday için `CANDIDATE_FEASIBLE`; CHK-120 tamamlanmadan nihai PMM kararı verme. **Yol:** K+D+A+M.

**CHK-009 — ETABS donatı tanımının niteliği.** **Ne lazım?** ETABS `Reinforcing` tanımının `design preference / required / specified / provided` olup olmadığı, bar koordinatları ve adetleri. **Elimde:** kesit donatı ayarları; bunlar fiilî uygulama donatısının kesin kanıtı değil. **How?** Malzeme-kesit donatı tanımının kaynak türünü sınıflandır, gerekli/atanmış/aday donatıyı farklı nesnelerde sakla; yalnız `actual_selected_rebar` varsa ρ ve detay uygunluğu için doğrudan yapı kararı üret. **Karar:** seçili donatı bilinmiyorsa `CANDIDATE` veya `NOT_PROVEN`; yüzde ve oran hiçbir zaman sıfır bar alanından türetilmez. **Yol:** K+D+A.

**CHK-011 — Tasarım spektrumu yeniden kurulumu.** **Ne lazım?** `Ss,S1,Fs,F1,SDS,SD1,TA,TB,TL`, DD seviyesi, sönüm, yükleme ekseni ve ETABS spektrum fonksiyonu. **Elimde:** spektrum parametre/tanım kayıtlarının önemli bölümü. **How?** TBDY §2.3'teki dört periyot aralığını ayrı formüllerle kur; sonra ETABS fonksiyon noktalarını ve ölçeğini karşılaştır; elastik spektrum ile azaltılmış tasarım spektrumunu ayrı tipte tut. **Karar:** `SPECTRUM_FUNCTION_REPLAYED` yalnız tutarlılık kanıtıdır; modal hareket koşulları ve R/I politikası ayrıca değerlendirilir. **Yol:** K+D+M.

### J2 — Bina, deprem ve düzensizlik akışı

**CHK-103 — Eşdeğer deprem taban kesmesi.** **Ne lazım?** `m_i,H_i,Hn,SaR(Tp),I,R,D,SDS`, uygun yöntem seçimi, periyot hesap politikası. **Elimde:** kat geometrisi, modal/spektrum/kütle kaynakları; proje `DesignBasis` için bazı normatif seçimler gerekir. **How?** Yön bazında normatif periyot seç, TBDY 4.7.1.1 ile `VtE=mt·SaR(Tp)` ve minimum `0.04·mt·I·SDS·g` karşılaştır; tepe ek yükünü 4.7.2.2, kalanını 4.7.2.3 ile katlara dağıt. **Karar:** `VtE(X/Y)` ve `F_i(X/Y)`; mevcut ETABS statik karşılaştırma için replay ancak analiz yöntemi uygunluğunu ayrı raporla. **Yol:** K+D+M.

**CHK-104 — Modal taban kesmesi ölçeklenmesi.** **Ne lazım?** CHK-103'ten `VtE`, aynı analiz neslindeki `Vtx,Vty`, A1/B2/B3 sonuçları, bodrum kuralları. **Elimde:** statik taban reaksiyonları ve bazı modal metadata; ilgili RS taban kesmesi vaka kapsamı tam doğrulanmalı. **How?** TBDY 4.8.4'e göre `γE=0.90` (A1/B2/B3'ten en az biri) aksi halde `0.80`; `βE=max[1,γE·VtE/Vt_modal]` hesabını X/Y ayrı yap; mod birleşimiyle bulunan **ilgili** iç kuvvet ve yer değiştirmelere uygula. **Karar:** ölçeklendirme sırası, daha sonra CHK-105/120'ye kaynak olarak gider; RS verisi eksikse `NOT_PROVEN`. **Yol:** K+D+M+Y gerektiğinde.

**CHK-107 — A2 döşeme süreksizliği.** **Ne lazım?** Kat döşeme brüt poligonu, iç boşluklar, etkili alan, diyafram sınırları, kuvvet transfer yolu. **Elimde:** 97 döşeme poligonu ve bazı area/diaphragm atamaları. **How?** TBDY Tablo 3.6 A2'nin ayrı alt durumlarını incele: boşluk oranı >1/3, deprem aktarımını güçleştiren yerel kesit daralmaları ve ani düzlem içi rijitlik/dayanım değişimleri; sadece alan oranına bağlı karar verme. **Karar:** A2 görülürse 3.6.2.2 gereği membran/shell düzlem içi aktarım kanıtı istenir; sadece geometrik alt kontrol ile `A2_SCREENED` üretilebilir. **Yol:** K+D+M+Y aktarım kuvveti için.

**CHK-108 — A3 planda çıkıntı.** **Ne lazım?** Her katın plan dış sınırının ortogonal çıkıntıları ve toplam Lx,Ly. **Elimde:** joint/slab geometrisi. **How?** Plan dış sınırından `ax/Lx`, `ay/Ly` üret; TBDY Tablo 3.6'ya göre iki doğrultunun birlikte ilgili %20 sınırını aşıp aşmadığını belirle; çok kuleli modelde ayrı bina bloğunu esas al. **Karar:** A3 geometrik sınıflama; varsa döşeme düzlem içi aktarımı CHK-153 ile zorunlu bağ. **Yol:** K+D+M.

**CHK-111 — B3 düşey eleman süreksizliği.** **Ne lazım?** Bir katın kolon/perde üst ve alt ayak izleri, joint connectivity, transfer kiriş/kolon guse bağlantısı. **Elimde:** kolon/joint/wall physical connectivity; bazı transfer ayrıntıları metadata ile teyit edilecek. **How?** Her düşey elemanı alt kata takip et; kolonun kirişe veya guseye oturması, perdenin kolona veya kiriş açıklığına oturması dallarını TBDY Tablo 3.6 ve 3.6.2.4'e göre sınıflandır; bazı dallar yasak, bazıları özel düşey deprem hesabına izinli. **Karar:** `B3_PRESENT`, `PROHIBITED_LAYOUT`, `VERTICAL_EQ_REQUIRED` ayrı sonuçlardır. `CHK-111` ID korunur, fiziksel anlamı düşey süreksizliktir. **Yol:** K+D+M.

**CHK-112 — Global devrilme ve sistem paylaşımı.** **Ne lazım?** Bina kat kuvvetleri/kotları, taban devrilme momenti, perdeye atfedilen aynı kesit momentleri, sistem tipi. **Elimde:** `Base Reactions`, statik `Story Forces`, pier forces ve kat geometrisi. **How?** `M_o=Σ F_i H_i` ile taban reaksiyon momentini aynı analiz durumunda kontrol et; özel perde-çerçeve sistemlerinde §4.3.4.5 kapsamında perde momenti/toplam moment payını `0.40…0.75` dallarına göre değerlendirme yapılabilir; bu paylaşımı tüm sistemlere otomatik uygulama. **Karar:** denge / sistem sınıfı / R-D-BYS aksiyonu ayrı. **Yol:** K+D+M.

**CHK-114 — Üstyapıdan temele kuvvet aktarımı.** **Ne lazım?** Mesnet düğümü, temel koordinat ve rijitlik ilişkisi, aynı kombinasyonun `Fx,Fy,Fz,Mx,My,Mz`, fiziksel yük transfer yolu. **Elimde:** `Joint Reactions`, `Base Reactions`, story/pier/frame kesit sonuçları; temel modeli yok. **How?** Tek bir fiziksel taban kesitinde tüm mesnet reaksiyonlarını aynı vaka/step için topla; pier ve frame kuvvetlerini aynı kesitten bir kez hesaba kat; temele aktarım için `FoundationDemand` üret, ancak zemin teması/temel dayanımı iddia etme. **Karar:** `SUPERSTRUCTURE_BALANCE_REPLAYED` mümkün, `FOUNDATION_DESIGN` için CHK-154…158 gerekir. **Yol:** K+D+Y temel için.

### J3 — Kolon ikinci mertebe, sargı ve tasarım yakınsaması

**CHK-116 — Kolon narinlik/serbest boy.** **Ne lazım?** I/J joint koordinatları, beam-face offsetleri, kat kotu, gerçek yanal mesnetler, lokal 2/3 eksen eylemsizlikleri. **Elimde:** frame section, connectivity, story geometry, bazı offsetler. **How?** `L_analitik`, `L_bağlantı`, `L_serbest` ve `L_etkin`i dört ayrı feature olarak tut; TS 500 §7.6.2.3'te ötelenmesi önlenmiş/önlenmemiş durum için `ℓk/i` ihmal eşiklerini her eksende uygula. **Karar:** narinlik etkisi ihmal edilebilir mi; aksi halde CHK-117/119 tüketici. **Yol:** K+D+M.

**CHK-117 — Etkili boy katsayısı k.** **Ne lazım?** Öteleme önlenmişlik kararı, kolon/bağlanan kiriş EI/ℓ oranları, uç mesnet türleri. **Elimde:** kesit ve bağlanma topolojisi, elastisite malzeme tanımı; bazı mesnet/çatlamış rijitlik varsayımları proje kararına bağlı. **How?** TS 500 §7.6.2.2'deki `α1,α2` ve durumuna uygun 7.14/7.15 dallarından k hesapla; yatay ötelenmesi önlenmiş durumda izin verilen güvenli `k=1` yedeği ayrı kaydet; ötelenme önlenmemiş durumda k=1'i gerekçesiz kullanma. **Karar:** yön-bağımlı `k2,k3` ve kaynak/varsayım statüsü. **Yol:** K+D+M.

**CHK-118 — Global P–Δ uygulama kararı.** **Ne lazım?** CHK-113 `θII`, `Ch,R,D`, ETABS analiz vakasında ikinci mertebenin zaten uygulanıp uygulanmadığı, varsa `PDelta` sonucu. **Elimde:** kat/kuvvet ve kısmi analiz ayarları; her vaka için P–Δ dahil durumu ayrıca teyit edilmeli. **How?** TBDY 4.9.2'nin `θII` göstergesini hesapla, varsa βII ile yön bazında kuvvetleri büyüt; ETABS ikinci mertebe sonuçları bu etkiyi zaten içeriyorsa aynı etkiyi ikinci kez büyütme; farklı yöntemleri aynı kombinasyonda karıştırma. **Karar:** `GLOBAL_SECOND_ORDER_INCLUDED` veya `MAGNIFICATION_REQUIRED` veya `REANALYSIS_REQUIRED`. **Yol:** K+D+M.

**CHK-119 — Yerel P–δ / TS 500 moment büyütmesi.** **Ne lazım?** CHK-116/117 boylar ve k, `Nd,M1,M2` imzalı uç momentleri, beton/donatı EI ve kalıcı yük katkısı. **Elimde:** statik signed uç kuvvetler, kesit ve malzemeler, donatı ancak adayla belirlenir. **How?** Her eksende `Nk=π²(EI)/(k ℓn)²`; TS 500 7.24–7.29'a göre `Cm`, bireysel `β`, kat `βs`, ΣNd/ΣNk ≤0.45 ve büyük narinlikte `ββs` dalını çalıştır. Minimum dışmerkezlik kontrolünü (CHK-115) bundan önce uygula; gerçek uç moment işaretini koru. **Karar:** `M2d,M3d` tüketimi CHK-120; koşul bozulursa kesit büyütme/reanaliz öner. **Yol:** K+D+A+M.

**CHK-122 — Kolon sarılma bölgesi uzunluğu.** **Ne lazım?** Kolon serbest boyu, en büyük kesit boyutu, kolon uç geometrisi, konsol sınıfı. **Elimde:** kolon geometri/joint/kot. **How?** TBDY §7.3.4.1 genel kolonda her uç için `ℓs ≥ max(ℓn/6,1.5·hmax,500 mm)` uygula; konsol kolon için ayrıca `2·hmax` alt sınırı ve temel içine devamı değerlendir. **Karar:** gereken üst/alt sargı bölgeleri; seçili etriye CHK-123 ile kontrol edilir. **Yol:** K+D+M.

**CHK-123 — Etriye/çiroz fiziksel yerleşimi.** **Ne lazım?** CHK-122 bölge boyu, seçili tüm boyuna barların koordinatları, etriye kol sayısı, çiroz kancası, Ø/s, çekirdek yüzeyleri. **Elimde:** fiziksel kesit ve donatı adaylarının üretilebileceği geometri; mevcut uygulama etriyeleri kayıtta yok. **How?** Enine donatı düzlemini gerçek bar koordinatlarında kur; sargı/orta bölge için ayrı aralık, en küçük çap, yatay kol aralığı, mesnet kancaları ve düşey süreklilik testleri yap. Sadece `Ø10/10` metni yeterli değildir; kaç etkin kol ve hangi barın sarıldığı bilinmeli. **Karar:** CHK-124'e gerçek sağlanan Ash geçer. **Yol:** K+D+A+M.

**CHK-129 — Kolon aday iterasyonu ve kapanma.** **Ne lazım?** CHK-120 PMM, CHK-125 SCWB, CHK-126…128 kesme/joint sonuçları; aday bar/etriye listesi ve yeniden hesaplama bağımlılıkları. **Elimde:** kesit/kuvvet bankası, offline aday üretme imkânı. **How?** Aday kafesi deterministik sırayla tara; her adayda PMM→Mr→SCWB→α→Ve→etriye→joint zincirini yeniden hesapla; bir kapasite değişimi tüm tüketici sonuçları geçersiz kılsın; boyut değişikliği gerekiyorsa ETABS yeniden analiz eşiğine geç. **Karar:** `DESIGN_FEASIBLE`, `NO_CANDIDATE`, `INPUT_NOT_PROVEN`, `REANALYSIS_REQUIRED` birbirinden ayrı. **Yol:** D+A+M.

### J4 — Kiriş dayanımı ve detay zinciri

**CHK-133 — Boyuna donatı alt/üst sınırları.** **Ne lazım?** Mesnet/açıklıkta yönlü seçili alt/üst bar alanları, b,d,h, fctd,fyd, süreklilik durumu. **Elimde:** kesit/kuvvet, bağımsız kiriş donatı adayı üretebiliriz; gerçek seçili donatı yok. **How?** TS 500 minimum/eğilme sınırları ile TBDY §7.4.2 ve §7.4.3'e göre en büyük oran, mesnet alt-üst ilişki, iki yönde açıklık sürekliliği ve katman bar aralıklarını ayrı alt-check olarak değerlendir. **Karar:** CHK-134 moment kapasitelerine yalnız uygun seçili yerleşim girer. **Yol:** K+D+A+M.

**CHK-137 — Kiriş burulması.** **Ne lazım?** Aynı kesit-vaka/step `T,V,M`, beton kesit çevresi, kapalı etriye ve ek boyuna bar yerleşimi. **Elimde:** native `T,V2,V3,M2,M3`, geometri; seçili burulma donatısı aday üretimi gerekir. **How?** TS 500 §8.2 ile burulma eşiği, kesme-burulma ortak kapasite ve gerekli kapalı enine/boyuna donatı hesabını iki doğrultuda yap; burada bileşen zarflarını sahte eşzamanlı vektör olarak birleştirme. **Karar:** kapasite/detay kontrolü, yoksa tasarım adayı. **Yol:** K+D+A.

**CHK-139 — Kenetlenme/süreklilik.** **Ne lazım?** Kiriş uçlarındaki gerçek bar çapı/alanı, kolon yüzü, joint çekirdek boyutları, mesnet açıklığı, paspayı, büküm/kanca. **Elimde:** geometri/connectivity, bar adayı; gerçek detay çizelgesi yok. **How?** TBDY §7.4.3 ve TS 500 ankraj hükümleriyle her bar için gereken gelişme/kenetlenme uzunluğunu hesapla; birleşim içindeki mevcut fiziksel boyla karşılaştır; süreklilik, bindirme ve mesnet yönünü ayrıca denetle. **Karar:** CHK-125/128 için etkili kapasite ancak fiziksel olarak kenetlenmiş barlarla doğrulanır. **Yol:** K+D+A+M.

### J5 — Perde, birleşim ve SAME_CUT

**CHK-142 — Perde kritik yükseklik/uç bölgesi.** **Ne lazım?** Perde net boyu `lw`, kalınlık `t`, toplam/etkin yükseklik `Hw`, süreksizlik ve bodrum geçişi, kesit tipi. **Elimde:** wall geometry, story levels, pier mapping kısmen. **How?** TBDY §7.6.2'ye göre kritik yükseklik sınırlarını ve uzunlukta/rijitlikte ani değişim olan başlangıç seviyesini kur; kritik bölge boyunca dikdörtgen uç bölgesi alt sınırını `max(0.20 lw,2t)`, üst bölgelerde ayrıca tanımlı alt sınırı uygula; L/U/T perdeleri geometri tipine göre çöz. **Karar:** sınır ve donatı alanları CHK-143/144 tüketir. **Yol:** K+D+M.

**CHK-143 — Perde gövde/uç donatısı.** **Ne lazım?** Fiziksel wall segment geometrisi, CHK-142 sınırları, seçili düşey/yatay donatı yerleşimi, fyk,fck. **Elimde:** geometri, malzeme ve pier kuvvetleri; yerinde/proje seçili donatı yok. **How?** Gövde ve her uç bölgesini farklı donatı nesnesi olarak kur; düşey/yatay yüzler, minimum oran, aralık, bindirme, kapalı sargı ve boşluk kenarı detaylarını yönetmeliğe göre hesapla. **Karar:** `Provided/Required` her bölge için ayrı; CHK-141 flexural ve CHK-144 shear kapasitesine seçilmiş düzen tüketici olur. **Yol:** K+D+A.

**CHK-145 — Bağ kirişi ve boşluklu perde.** **Ne lazım?** Duvar boşlukları, spandrel/link kirişleri, net açıklık, açıklık/yükseklik oranı, aynı yükleme talebi, donatı. **Elimde:** wall, beam ve pier/spandrel kaynaklarının bir bölümü; tüm link rebar tanımı yok. **How?** Geometriden duvarların bağlı çalışan kol gruplarını bul; bağ kirişi sınıfına göre eğilme, kesme, gerekli özel çapraz donatı ve ankraj dallarını seç; bağ kirişinin taşıdığı normal kuvvet/devrilme katkısını aynı fiziksel seviyede eşle. **Karar:** duvar kapasitesi ve devrilme paylaşımı bu sonuçla güncellenir. **Yol:** K+D+A+M.

**CHK-146 — Kat kesme payı ve kat φ.** **Ne lazım?** Aynı kat-yön, aynı kesit seviyesi, aynı vaka/step için kolon/pier/frame/story signed shear; kat kesme toplamı. **Elimde:** `Story Forces` (statik), pier force, kolon native force, taban reaksiyonları; fiziksel SAME_CUT crosswalk'ı gerekir. **How?** Story cut düzlemini açık tanımla; kesen bütün fiziksel kolon/perde kuvvetlerini lokal→global ve I/J→cut işaretiyle dönüştür; ΣV_kolon + ΣV_perde + diğer etkileri yalnız tek kesitte story shear ile uzlaştır. Farklı yüklemelerden veya kat üst-alt uçlarından pay üretme. **Karar:** önce `NUMERICAL_BALANCE`, sonra `STORY_PHI_ENGINEERING` (pay uygun normatif tanımla) ayrı; eksik cut tanımı varsa `NOT_PROVEN`. **Yol:** K+D+M.

**CHK-147 — Birleşim topolojisi.** **Ne lazım?** Fiziksel joint, aynı düğüme bağlanan üst/alt kolon, X/Y doğrultulu kirişler, kolon yüzleri ve offsetler. **Elimde:** frame/point connectivity ve fiziksel malzeme-kesitler. **How?** ETABS analitik bağlantı noktalarını fiziksel joint kümesine grupla; çakışan/offsetli uçları gerçek kolon yüzüne taşı; beam i/j dönüşü ve kat eşlemesini doğrula; bir beam aynı joint'e iki kez eklenmesin. **Karar:** CHK-125 SCWB, CHK-128 shear, CHK-148 confinement için tek `JointTopologyFeature`. **Yol:** K+D.

**CHK-148 — Birleşim bölgesi sargı.** **Ne lazım?** CHK-147 joint geometrisi, dört taraftan sarılma sınıfı, alttaki kolonun sargı donatısı, seçili etriye/çiroz adımı. **Elimde:** joint/kolon/kiriş geometrisi ve aday transverse reinforcement. **How?** TBDY §7.5.1'e göre kuşatılmış/kuşatılmamış sınıfını fiziksel kiriş yüzleriyle belirle; §7.5.2.3'te kuşatılmışta kolon sarılmasının asgari `%40`ı, kuşatılmamışta `%60`ı ve ayrı çap/aralık koşullarını denetle. **Karar:** CHK-128 birleşim kesme ve CHK-129 yakınsama için `JOINT_DETAIL_PASS` veya açık talep. **Yol:** K+D+A+M.

### J6 — Diyafram ve temel

**CHK-153 — Diyafram düzlem içi kuvvet aktarımı.** **Ne lazım?** Gerçek shell/membran `F11,F22,F12`, shear flow, mesh/topoloji, slab–wall/column collector/cord bağlantıları, deprem talep vakası. **Elimde:** fiziksel slab geometrisi ve diyafram atamaları; ilgili shell iç kuvvetleri bu arşivde tamam değil. **How?** Kat kesitleri boyunca iç düzlem kesme/normal kuvvetlerini aynı yükleme ve konumda integre et; chord/collector ve perdeye bağlama akışını tespit et; mevcut donatı ve malzeme dayanımıyla karşılaştır. **Karar:** geometri ön taraması offline; sonlu eleman aktarım güvenliği `NOT_PROVEN` ve hedefli `Area Shell Forces` ister. **Yol:** K+D+Y+A.

**CHK-156 — Temel tek yönlü kesme ve zımbalama.** **Ne lazım?** Temel kesit kalınlığı/etkili derinlik, kolona ait beton çevre, toprak temas basıncı/reaksiyonu dağılımı, kuvvet/moment, kenar/köşe durumu. **Elimde:** üstyapı joint reactions; gerçek foundation mesh ve temas yükleri yok. **How?** Aynı temel ve yükleme kombinasyonunda kritik tek yönlü kesit/kritik zımbalama çevresini kur; temas kuvvetlerini ilgili alanlarda integre ederek net Vd üret; TS 500 §8.1/8.3 gereğince Vrd ve gerekiyorsa zımbalama donatısı denetle. Ham kolon P'yi doğrudan her durumda zımbalama kuvveti sayma. **Karar:** foundation/soil kanıtı gelmeden mühendislik PASS yok. **Yol:** Y+D+A.

**CHK-158 — Temel–üstyapı çift yönlü aktarım.** **Ne lazım?** CHK-114 üstyapı taban reaksiyonları, foundation/SAFE yük durumları, destek noktası/kesit koordinat dönüşümleri, aynı jenerasyon ve kombinasyon. **Elimde:** üstyapı reactions; foundation tarafı yok. **How?** Taban kuvvet/momentlerini temel modeline kesit düzeyinde eşle, aktarılan yükler ve temel reaksiyon/zemin sonuçları arasında ΣFx,ΣFy,ΣFz,ΣMx,ΣMy,ΣMz dengelerini ayrı kur; pier+column çift sayımını ve base-ref kaymasını engelle. **Karar:** `TRANSFER_RECONCILED` yalnız iki kaynak aynı fiziksel model ve yük durumundan geliyorsa; aksi `NOT_PROVEN`. **Yol:** K+D+Y.

### J7 — Her CHECK'i bağlayan iki yürütme örneği

**Örnek A / Bina-genele giden yön:** `StoryDefinitions → StoryDriftFeature → CHK-106 (A1)`; aynı kaynaktan `CHK-110 (B2)` ve `CHK-113 (θII)` üret. A1/B2/B3 varlığı `CHK-104` için `γE` seçtirir; `CHK-104` RS iç kuvvetler için gerekli ölçeği üretir; `CHK-105` ise ayrı DD2/DD3 oranı ile drift limitini uygular. Böylece **tek drift kaynağı**, birbirinden ayrı ama bağımlı dört hesap dalını besler.

**Örnek B / Kolon-kiriş kapasitesine giden yön:** `source signed loads → beam/column design demands → beam selected As / column selected As → section Mr` → `CHK-125 SCWB` → `CHK-126 & 135 Ve` → `CHK-127 & 136 etriye` → `CHK-128 & 148 joint` → `CHK-129 converge`. Yeni As/etriye seçildiğinde `Mr`, `Ve`, `Joint` ve gerekiyorsa PMM tekrar hesaplanır. **Kesit boyutu/rijitlik değişikliği** ise kendi başına offline iterasyon değildir; ilgili binanın ETABS tekrar analizini gerektirir.

### J8 — İki temel sayısal kuralın uygulanması

**Etkin kat ötelemesi:** Önce `Δi` azaltılmış drift; sonra `δi=(R/I)·Δi`; sonra yön bazında `λ=Sae_DD3(Tp)/Sae_DD2(Tp)`; betonarme için `κ=1` ve dolgu/cephe bağlantı sınıfına göre TBDY 4.9.1.3 koşulu `λ·δi,max/hi ≤ 0.008·κ` veya `≤ 0.016·κ`. Burada `λ` çarpanı sol taraftadır; sınır ile basitçe `λ*0.008` çarpmak değildir. `R/I` iki kere uygulanmaz.

**Kiriş/kolon kapasite kesmesi:** Kiriş §7.4.5.1'de `Ve=Vdy ± (Mpi+Mpj)/ln`; yaklaşık `Mpi≈1.4Mri, Mpj≈1.4Mrj`. Kolon §7.3.7.1'de `Ve=(Ma+Mü)/ln`; `Ma/Mü` her uçtaki SCWB dalına göre §7.3.7.2 veya §7.3.7.3'ten gelir. `D` ile büyütülen deprem kesmesinin alternatif üst sınırı **yönetmelik maddesine göre** değerlendirilir; `Ve`'yi otomatik olarak bir kez daha `D` ile çarpmak doğru bir genel kural değildir. Seçilen `Ve` için §7.3.7.5 / §7.4.5.2 kesit dayanımı ve §7.3.7.6 / §7.4.5.3 beton katkısı koşulları ayrı uygulanır.

**Anlık ve uzun süreli sehim:** TS 500 §13.2.3: `δt=δi+λ·δig`, `λ=γt/(1+50ρ')`; `γt` yükleme süresine göre Çizelge 13.2'den seçilir. Anlık servis yükü ile kalıcı yükten doğan δig'i karıştırma; sırf kullanılan yazılımda “nonlinear” seçeneği bulunduğu için doğrulanmamış 50 yıllık sünme/rötre analizi varmış gibi sonuç üretme. Sehim sınırını TS 500 Çizelge 13.3'teki eleman ve bölme duvar sınıfına göre seç.


---



## Tamamlayıcı kabul ve tekrar-kullanım kuralları

- **Uygulanabilirlik** kaynak verisi bulunmasından önce belirlenir. Bir eleman kapsam dışıysa gerekçeli `NOT_APPLICABLE`, kapsam içindeyse her yükleme/kesit/yön örneği beklenen paydada bulunmalıdır.
- **İz sürme:** sonuç→formül sürümü→türetilmiş feature→ham tablo→`model_sha/analysis_generation/case/step/object/element/station/units` zinciri. İlgili özgül alan yoksa `NOT_PROVEN`.
- **Bina çapında agregasyon:** beklenen = PASS + FAIL + NOT_PROVEN + NOT_APPLICABLE eşitliği her kontrol ailesinde sağlanır; `PASS=0, FAIL=0` bir uygunluk kararı değildir.
- **Öncelik:** kaynak var ve hesap offline türetilebiliyorsa önce türet. Yalnız fiziksel geometri/donatı/temel veya yeni analiz çıktısına gerçekten ihtiyaç varsa hedefli veri iste.
- **Kuvvet/konum:** farklı `station`, `step`, `combo` ve analiz nesillerinden bileşenleri toplamakla eşzamanlı tasarım vektörü oluşturulmaz.
- **Donatı:** `REQUIRED`, `PROPOSED`, `SELECTED`, `EXISTING_AS_BUILT` dört farklı seviye. Seçilmeyen öneri donatı taşıma gücü uygunluğu sayılamaz.
- **Rapor:** mühendislik hesabını yalnız tek kez üret; Excel, UI ve Word/PDF çıktıları *salt okur*. Bir rapordaki ✔, bağımsız kabul oracle'ı yerine geçmez.

## Kısa mühendislik fişi (her CHECK için)

`check_id` · `physical_scope` · `applicability` · `source_ids` · `input_feature_ids` · `available/derived/missing` · `formula_or_algorithm` · `normative_clause` · `units/sign` · `case/step/station` · `value/limit` · `algorithm_status` · `source_status` · `engineering_verdict` · `downstream_consumers` · `reason_code` · `minimum_next_evidence` · `independent_oracle`.

**Karar ayrımı:** bir algoritma tanımlı veya test edilmiş olabilir ama belirli bina için kaynak eksik olduğundan `NOT_PROVEN` döndürebilir. Tüm hesap ailelerinin geçerli verilere bağlandığı ve bağımsız olarak kabul edildiği gösterilmeden `ENGINEERING_RELEASE=READY` olmaz.

## Referanslar ve kullanım rolü

1. Asıl check ID listesi: `TBDY_NEXT_ENGINE(1).zip/config/check_registry/checks.json` (73 kayıt).
2. Gerçek kaynak gözlemi: `CAPTURE-20261113T051055Z-751a4137_kompakt_b.EDB(1).zip` (380 üyelik source archive).
3. Kullanıcının son taslağı: `Yapıştırılan markdown(5).md` (42 ID'yi açıkça örnekleyen yöntem metni).
4. [TBDY 2018 resmî metin (AFAD)](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf) ve [kullanıcının Drive kaydı](https://drive.google.com/file/d/1tlILuDbRso80oQLPswhlsw8wd0uMNKnE/view).
5. [TS 500 kullanıcı Drive kaydı](https://drive.google.com/file/d/1GIaAvx7CDm8PWNmESMKl2GikQcJc1DBH/view).
6. [TBDY2018_DD2_Linear_Design_Check_System_FINAL.xlsx](https://docs.google.com/spreadsheets/d/10dEe6kcthWLP8bsCnU6a6tvO7OPlxlLt/edit) – örnek kontrol alanları ve giriş şablonu.
7. [B_Blok_manual_audit_workbook_v1.xlsx](https://docs.google.com/spreadsheets/d/1VkOMgxwdm3VUVHGh7jZT3JS2QVa4tnN9/edit) – bağımsız sayısal karşılaştırma satırları; bina uygunluğunun kaynağı değildir.
8. [ETEX örnek hesap raporu](https://drive.google.com/file/d/1bbNB8NrOAeA4juuSSopvSvmbi961ZMHG/view) ve [EÜAŞ statik hesap raporu](https://drive.google.com/file/d/1Mj1ZfCiuVQ2BXUUkdUEcnBE6xr7Hscew/view) – rapor ağaçları, hesap sırası ve sunum örnekleri.

---