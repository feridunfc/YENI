# TBDY-Next-Engine — 73 CHECK reçetesinin `feridunfc/YENI` entegrasyonu

**Tarih:** 13.11.2026 · **İş türü:** mühendislik algoritma ve kaynak sözleşmesi, **kod değişikliği yok**  
**Çalışma referansı:** `recovery/r00-r01-vs27-source-20261112`, HEAD `e2f38ef015ac4398866269b1b24495460a0335c4`  
**Bağımsız dokümantasyon dalı:** `docs/recipe73-source-dag-20261113`  
**Mühendislik yetkisi:** `NOT_PROVEN`; `ENGINEERING_RELEASE=NOT_READY`; merge ve ana dal değişikliği yok.

## 1. Bu entegrasyon neyi çözer?

Yeni bir 73-kontrollü motor yazmak yerine mevcut `YENI` motorunun **Model Tree → Source/Feature Graph → Engineering DAG → Design Solvers → CheckResult → RunResult/Report** yoluna dış reçeteyi adapte eder. Harici ZIP'in `config/check_registry/checks.json` içindeki 73 kısa kimliği, `YENI` içinde kendi başına normatif otorite haline gelmez. `YENI`'nin mevcut `config/dag/tbdy_r1c_94_candidate.json` tanımı **94 düğüm** (16 kaynak kapısı + 10 türetim + 32 düzenleyici + 36 tasarım kontrolü) olan farklı düzeyde bir aday DAG'dır. 73→94 **1:1 eşleme varsayımı yasaktır.** Bir dış CHECK birden çok atomik kuralı, türetim düğümünü veya uygulama koşulunu temsil edebilir.

73 reçete bağımsız kaynak olarak `docs/engineering/reference/RECIPE_73_CANDIDATE_20261113.md` dosyasına değişmeden alınmıştır. Aşağıdaki tablo `YENI`'ye özel **migration/owner planıdır**, mevcut kodun eksiksiz uygulandığını iddia etmez.

## 2. Üç ayrı kaynak nesli ve offline veri

| Kaynak hattı | Ne için kullanılabilir? | Kanıt sınırı |
|---|---|---|
| 09.11.2026 historical native bank + `full-model-evidence.zip` | VS26/R01–R06 sayısal karşılaştırma, 87 kolon, statik/spektral orijin | R06 source/response semantics ve reference golden; bina genelindeki son tasarım nesli kabulü değil |
| 12.11.2026 yeni 87 kolon ZIP | Kaynak nüfus/kimlik denetimi | Recovery status'a göre **kuvvet kaydı 0**, tarihsel kuvvetlerin yerine geçirilemez |
| 13.11.2026 `CAPTURE-20261113T051055Z-751a4137_kompakt_b.EDB(1).zip` | 380 ZIP üyesi, 379 digested kaynak dosyası, fiziksel tablo ve native force, geniş offline yeniden türetme | ZIP SHA-256: `9ae4ab42abd5a899742ebc1de3257342eff67b72ef3b4610bdcd5b05305e4b1b`; manifest `complete=false`, `analysis_generation_proven=false`. Başka koşuya ait kanıtla sessiz birleşim yok |

13 Kasım kaydı için model EDB SHA-256 `4f04bfec08dd246c8e394058640c4f7b658dc464144affc9150d4ca3cf2898ac`; birim kodu `6` (kN-m-C). Sonuçlardaki 27 native FrameForce hata girdisi, fiziksel `Null Line` sınıflamasıyla ayrı kontrol edilmeli; 87 kolon ve 180 kirişin kapsamı kaynak roster'a göre denetlenmeli. `complete=false`, yalnız kapsama bayrağıdır: her koşulun girdi kapsamı ayrı çözülür, fakat analiz nesli kanıtı olmadan **nihai deprem tasarımı PASS yoktur**.

**Doğrulanmış tablo/alan adları** (`field_schemas.json.gz`, 13 Kasım capture):
- `Modal Participating Mass Ratios`: `Case,Mode,Period,UX,UY,SumUX,SumUY`
- `Story Drifts`: `Story,OutputCase,StepType,StepNumber,Direction,Drift,Drift/`
- `Story Max Over Avg Drifts`: `Story,OutputCase,StepType,Direction,Max Drift,Avg Drift,Ratio`
- `Story Forces`: `Story,OutputCase,StepType,Location,P,VX,VY,T,MX,MY`
- `Pier Forces`: `Story,Pier,OutputCase,StepType,Location,P,V2,V3,T,M2,M3`
- `Joint Displacements`: `Story,UniqueName,OutputCase,StepType,Ux,Uy,Uz,Rx,Ry,Rz`
- `Base Reactions`: `OutputCase,StepType,FX,FY,FZ,MX,MY,MZ,X,Y,Z`
- `Mass Source Definition`: `Name,SourceSelf,SourceAdded,SourceLoads,LoadPattern,Multiplier`
- `Load Combination Definitions`: `Name,Type,LoadName,Mode,SF,GUID`

Bu adlar, 13 Kasım veri kümesinin **gözlemlenmiş** şemasıdır. Diğer ETABS sürüm/analiz koşularında `TableKey/FieldKey` alias'ları ancak kaynak üzerinden doğrulanarak eklenir.

## 3. Karar yetkisi ve veri durumunun ayrılması

Her `CheckInstance` çıktısında birbirinden bağımsız boyutlar vardır:

`data_status = COMPLETE | PARTIAL | MISSING | CONFLICT`  
`numeric_status = SOLVED | NUMERIC_UNRESOLVED | NOT_RUN`  
`applicability = APPLICABLE | EXEMPT_BY_CODE | UNKNOWN`  
`engineering_decision = PASS | FAIL | NOT_APPLICABLE | NOT_PROVEN`  
`release = READY | NOT_READY`

`source_gate` sadece bir rapor satırı değildir; her bağımlı düğümün **yürütme önkoşulu** olur. Bozuk ZIP / hash / model kimliği / birim → genel `INVALID_SOURCE`; dıştaki sayısal `PASS` görünse bile normatif `PASS` olamaz. Parçalı kapsama durumunda **yalnız ilgili türetimler** durur; bağımsız materyal/geometri ekranları sınırlı ve açık kaynak durumuyla çalışabilir. SOURCE_GATE sonrası hesap eksikliği, otomatik `NOT_APPLICABLE` veya `PASS` üretmez.

Bunun gerekçesi, harici ZIP'in `src/tbdy_next/engine.py` yürütücüsünde `gate_ok` hesaplanmasına rağmen `run()` içinde önce tüm `reg.chk_*` fonksiyonlarının çağrılması ve `finalize()`'ın `gate_ok` kontrolünü yapmamasıdır. Bu **gerçek dış motor entegrasyon riski** olup `YENI`'ye kopyalanmayacaktır. `YENI/src/tbdy_next/compiled_dag.py` aday planlara yetki verilmesini zaten engelliyor; gerçek CHECK yürütmesi başladığında bu kural işletme seviyesine taşınmalıdır.

## 4. Kimlik ve normatif semantik sözleşmesi

Bir CHECK'in kimliği metinsel `CHK-108` gibi kısa bir tanımla taşınmaz; kalıcı kanonik anahtar `{standard}:{clause}:{rule}:{physical_scope}:{revision}` biçimindedir. Örnekler:
- `TBDY2018:TABLO3.6:A3_PLAN_PROTRUSION:STORY:v1` ← eski `LEGACY73:CHK-108`
- `TBDY2018:TABLO3.6:B3_VERTICAL_MEMBER_DISCONTINUITY:STORY:v1` ← eski `LEGACY73:CHK-111`
- `TBDY2018:7.3.5:SCWB:JOINT_AXIS_SIGN:v1` ← eski `LEGACY73:CHK-125`
- `TBDY2018:7.5.2:JOINT_SHEAR:JOINT_AXIS_SIGN:v1` ← eski `LEGACY73:CHK-128`

**İki alias kesinlikle düzeltilmeli:** harici katalogdaki “A3 storey discontinuity” yanlış; A3 **planda çıkıntı** kontrolüdür. Harici katalogdaki “B3 mass irregularity” yanlış; B3 **düşey kolon/perde süreksizliği** kontrolüdür. Eski ad `source_name` olarak saklanır ama mühendislik algoritmasını veya veri bağını belirleyemez. `LEGACY242` ve `LEGACY73` kimlik havuzları ayrıca namespacelenir; aynı metin ID'si farklı norma bağlanıyorsa otomatik birleştirme yasak, adjudication gerekir.

**CHK-104, TBDY 4.8.4.1:** A1/B2/B3 en az biri varsa `γE=0.90`; **Tablo 3.6 düzensizliklerinden hiçbiri yoksa** `γE=0.80`. Yalnız A2/A3/B1 bulunuyorsa metindeki iki açık dalın tam eşleştirmesi yoktur: normal `γE` alanı `UNRESOLVED_NORMATIVE_BRANCH` kalır. Güvenli tarafta geçici `0.90` sayısal tarama yapılabilir ama standart onayını bu tek başına sağlamaz. Aday sayısal tarama ile tasarım onayını ayır.

**CHK-105:** Denklem 4.34'te oran `λ×δmax/hi ≤ κ×0.008` (bitişik) veya `≤ κ×0.016` (esnek koşullu). `δmax/hi ≤ λ×0.008` biçimindeki cebirsel ters yazım başka bir kuraldır, otomatik kabul edilmez. `δ=(R/I)Δ`, `λ=Sa(DD3,Tp)/Sa(DD2,Tp)`, betonarme için `κ=1`.

**CHK-119:** TS 500 narinlik ile iki eksendeki `k`, `EI`, `Nk`, `Cm`, `β`, `βs` ve Eq.7.29 dallarını sahiplenir. `βs=1/[1-1.3ΣNd/ΣNk]` koşullu ve `ΣNd≤0.45ΣNk` ayrı koşuldur. Global P–Δ'nin zaten analize işlendiği kaynaklarda ikinci kez büyütme yapılmaz.

**CHK-125/126/128/129:** Düğüm/topoloji/gerçek yüz/kuvvet işareti bilinmeden SCWB veya joint güvenliği PASS değil. `ΣMr_c≥1.2ΣMr_b` TBDY 7.3.5 özel istisnaları ve 7.3.6 `α_i` sonrasında karar verir; kolon uçlarının Ve hesabı ve birleşim panelindeki Vj bu seçilmiş donatıyı tüketir. Değişen donatı → etkilenen kapasiteler/etriye yeniden hesaplanır.

**Spektral semantik:** `PhysicalStaticForceState` (aynı kesitte aynı adımın signed altı bileşeni), `SpectralComponentEnvelope` (eşzamanlı OLMAYAN skaler ekstremumlar) ve `CodeDesignDemandCandidate` (şartlı işaret eşleştirme) farklı tipler olarak korunur. VS26 koşullu sekiz köşe, nihai concurrent force state değildir. Ara eksenel kuvvet dağılımı, onaylı kombinasyon rolleri, second-order ve bütün kesit istasyonları kapanmadan PMM final `PASS` verilmez. 

## 5. 73 harici CHECK kimliği → YENI owner/hesap/karar haritası

| Harici ID | Harici ZIP'deki ad | YENI hedef evre | Sahip modül (mevcut/aday) | En az veri ve hesap mantığı |
|---|---|---|---|---|
| `SRC-001` | Archive file hash integrity | R00 | `r00_offline_gate.py` | ZIP bytes + manifest file_digests; **Every byte hashes; no mismatch** |
| `SRC-002` | Source model identity unchanged / units | R00/R02 | `source.py / physical_story_scope.py` | model SHA + units + capture identity; **Model before=after; units typed** |
| `SRC-003` | FrameForce coverage vs physical frames | R01/R02 | `native_archive.py / source_bank.py` | physical frame registry + exact force rows; **267 concrete frames; null lines exempt only with classification** |
| `SRC-004` | Analysis generation proof flag | R00/R03 | `vs05_d4_source_authority.py` | model/generation/run provenance; **Same analysis generation proven or blocked** |
| `SRC-005` | Combination book replay vs ETABS stored combination rows | R01/R03/R06 | `earthquake_combinations.py / r06_demand_semantics.py` | case+combo operators, signed force rows; **Static replay scalar; spectrum separate** |
| `CHK-001` | Concrete strength lower bound | R02/R19 | `normative_checks.py + assignments` | concrete material fck on used elements; **Applicable lower-bound fck** |
| `CHK-002` | Concrete strength upper range | R02/R19 | `normative_checks.py + assignments` | concrete grade on actual assigned element; **Allowed strength class upper range** |
| `CHK-003` | Column minimum cross-section side | R07 | `column_prechecks.py` | section shape, b/h/diameter; **Geometry minimum for applicable column type** |
| `CHK-004` | Column Ac >= Ndm/(0.40 fck) | R06/R07 | `column_prechecks.py / demand_chain.py` | design Nd from approved G+Q+E; Ac fck; **Nd/(0.40 Ac fck) ≤ 1** |
| `CHK-005` | Column Nd <= 0.9 fcd Ac | R07 | `ts500_column.py` | TS500 Nd, Ac fcd and validated role; **Nd/(0.90 Ac fcd) ≤ 1 under applicable design basis** |
| `CHK-006` | Cumulative modal mass participation | R04 | `etabs_modal.py / r04_offline_evidence.py` | modal per-case SumUX/SumUY + mode list; **95% both + all >3% modes** |
| `CHK-007` | Column first-order PMM + solver-selected reinforcement | R07/R09 | `column_pmm.py / section_capacity.py` | native signed vector + trial cage; **FIRST_ORDER_CANDIDATE only until R08/R09** |
| `CHK-009` | ETABS-defined column longitudinal ratio | R09 | `column_prechecks.py` | ETABS-defined versus selected versus existing bars; **No promotion of ETABS-design template to actual** |
| `CHK-010` | Story drift limits | R05 | `story_drift_binding.py` | Story Drifts, story heights, run/scenario; **Raw drift feature, not normative drift PASS alone** |
| `CHK-011` | Design spectrum reconstruction vs ETABS function | R04 | `spectrum_reconstruction.py` | recorded spectrum and SDS SD1 + Ra(T); **Compare independent function; project profile approval separate** |
| `CHK-101` | Mass source reconstruction | R03/R04 | `analysis_sources.py` | Mass Source Definition, pattern factors, story mass; **Mass numerically reconcile by story and units** |
| `CHK-102` | Modal period range | R04 | `etabs_modal.py` | Modal Periods And Frequencies, Hn, Ct, method; **Tp X/Y and relevant empirical cap policy** |
| `CHK-103` | Equivalent lateral force base shear | R04 | `base_shear_screening.py` | W, T, SDS, R/I, eligibility; **TBDY 4.7.1.1 Eq4.19 + floor** |
| `CHK-104` | Modal base shear scaling | R04/R05 | `base_shear_screening.py` | RS base reactions, EQ force, all irregularities; **γE 0.9/0.8/exclusive-unresolved; β ≥ 1** |
| `CHK-105` | Effective story drift | R05 | `effective_drift_readiness.py` | Delta, R/I, DD2-DD3 spectra, infill classification; **λ×δ/h ≤ κ×0.008 or κ×0.016** |
| `CHK-106` | Irregularity A1 torsion | R05 | `r05_story_irregularity.py` | Story Max Over Avg Drifts, ±ecc; **A1 max/avg >1.2 triggers irregularity** |
| `CHK-107` | Irregularity A2 floor discontinuity | R05/R19 | `story_geometry.py` | floor polygon, openings and transfer; **A2 slab discontinuity, area and load path** |
| `CHK-108` | A3 — Planda çıkıntılar bulunması (TBDY Tablo 3.6) | R05/R19 | `story_geometry.py` | plan polygon projections Lx/Ly, ax/ay; **A3 PLAN PROTRUSIONS; NOT storey discontinuity** |
| `CHK-109` | Irregularity B1 weak storey | R05 | `weak_story_b1.py / b1_source_bridge.py` | Aw, Ag, Ak per story; infill policy; **B1 Ae ratio + code-required R/branch** |
| `CHK-110` | Irregularity B2 soft storey | R05 | `soft_story_b2.py` | mean drift/height and adjacent story both sides; **B2 eta>2; case and eccentricity completeness** |
| `CHK-111` | B3 — Taşıyıcı sistem düşey elemanlarının süreksizliği (TBDY Tablo 3.6) | R05/R19 | `story_physical_source.py / wall_geometry.py` | joint connectivity, column/wall continuity; **B3 VERTICAL MEMBER DISCONTINUITY; NOT mass** |
| `CHK-112` | Global overturning | R04/R19 | `base_shear_screening.py / wall geometry` | same-cut base moment and full wall share; **R/D/BYS conditional wall-frame overturning policy** |
| `CHK-113` | Global second-order indicator | R05/R08 | `r05_story_irregularity.py / column_stability.py` | Delta_ort, W_above, Vstory, height, R D Ch; **thetaII and second-order action without duplication** |
| `CHK-114` | Foundation force transfer | R02/R19 | `source_control_bundle.py` | base reactions + interface cuts; **Same cut load path; foundation model distinct** |
| `CHK-115` | Column minimum eccentricity | R07/R08 | `ts500_column.py` | Nd, section h in bending plane; **emin=15mm+0.03h, each principal axis** |
| `CHK-116` | Column slenderness and unsupported length | R02/R08 | `column_kinematics.py` | physical face-to-face length, restraints; **Ln/unsupported and station roles** |
| `CHK-117` | Effective length factors | R08 | `column_stability.py` | frame stiffness, alpha1/alpha2, EI; **k about both axes and sway branch** |
| `CHK-118` | Global P-Delta amplification | R05/R08 | `r05_story_irregularity.py / column_stability.py` | global sway, analysis settings; **Global P-Delta ownership, do not amplify twice** |
| `CHK-119` | Local P-delta (TS 500 magnification) | R08 | `ts500_column.py / column_stability.py` | Nd,Nk,EI,k,Cm,β,βs,sway; **TS500 7.24-7.29, local P-delta each axis** |
| `CHK-120` | Biaxial PMM with second-order demand (final) | R07/R09 | `section_capacity.py / spectral_pmm.py` | approved signed demand + selected cage; **Full 3D biaxial interaction with min ecc & 2nd order** |
| `CHK-121` | Column longitudinal bar detailing | R09 | `column_prechecks.py` | bar dia/coordinates, clear cover, spacing, splice; **Actual or selected longitudinal detail geometry** |
| `CHK-122` | Confinement region length | R12 | `column_transverse.py` | column free height, max section dim, joint faces; **TBDY 7.3.4.1 confinement zone length** |
| `CHK-123` | Tie and cross-tie layout | R12 | `transverse_kernel.py` | ties/crossties legs, pitches, steel diameters; **Tie and cross-tie location/layout** |
| `CHK-124` | Confinement reinforcement Ash | R12 | `column_transverse.py` | core dimensions, Nd, fck/fywk, Ash; **Required Ash x/y vs supplied** |
| `CHK-125` | Strong column weak beam (SCWB) | R10/R11 | `column_scwb.py / scwb_kernel.py` | full joint roster; beam+column Mr; signed Nd; **Joint/axis/sign SCWB≥1.2, exceptions and αi** |
| `CHK-126` | Column capacity shear Ve | R11/R12 | `scwb_kernel.py / transverse_kernel.py` | beam/column end capacity, clear length; **Column Ve per 7.3.7.1-7.3.7.3 conditional** |
| `CHK-127` | Column shear capacity | R12 | `column_transverse.py` | Ve, Vc/Vw, cross ties, Nd; **Ve≤Vr and concrete shear branch** |
| `CHK-128` | Beam-column joint shear | R13 | `joint_kernel.py / column_joints.py` | joint b_j h, beam bars, Vkol, confinement; **TBDY 7.5.2 panel demand/capacity** |
| `CHK-129` | Column design iteration convergence | R09/R14 | `column_pmm.py / scwb_kernel.py` | cage iteration, dependent checks; **Converge or NO_FEASIBLE_CANDIDATE with cause** |
| `CHK-130` | Beam geometry and axial applicability | R10/R19 | `beam_references.py` | physical beam faces and axial type; **Applicable flexural member / section family** |
| `CHK-131` | Beam design flexure | R10/R19 | `beam_capacity.py` | design M2/M3 at beam sections; **TS500 equilibrium and required As** |
| `CHK-132` | Beam upper/lower reinforcement | R10/R19 | `beam_capacity.py` | available bar layouts, cover and spacing; **As_selected+placement per face** |
| `CHK-133` | Beam min/max reinforcement | R10/R19 | `beam_capacity.py` | rebar ratio min/max, ductile detailing; **Min/max and upper/lower continuity check** |
| `CHK-134` | Beam end moment capacities | R10 | `beam_capacity.py / beam_references.py` | selected top/bottom As and section; **Signed positive/negative face Mr for SCWB** |
| `CHK-135` | Beam shear and capacity shear | R12/R19 | `beam_capacity.py / transverse_kernel.py` | Vdy and Mpi/Mpj, clear span; **Ve = Vdy ± (Mpi+Mpj)/ln; both earthquake signs** |
| `CHK-136` | Beam shear reinforcement | R12/R19 | `transverse_kernel.py` | Ve, Vc branch, Asw/s, 2h confinement; **Required stirrup and placement** |
| `CHK-137` | Beam torsion | R19 | `new beam torsion contract` | T plus V and section transverse geometry; **Combined torsion/shear, not a scalar max alone** |
| `CHK-138` | Beam cracking and deflection | R19 | `new beam serviceability contract` | G/Q displacements, Ieff, retained rebar; **Instant + long-term delta under TS500 Table13.3** |
| `CHK-139` | Beam anchorage and continuity | R19 | `new anchorage/detailing contract` | bar extensions, laps, physical joints; **Anchorage and longitudinal continuity** |
| `CHK-140` | Wall geometry and pier mapping | R02/R19 | `wall_geometry.py` | WallSegments, Pier Labels, actual cut topology; **Exact wall segment↔pier↔cut identity** |
| `CHK-141` | Wall axial-flexural capacity | R19 | `new wall PMM contract` | N-M demand+wall section+selected cage; **Wall end/web section interaction** |
| `CHK-142` | Wall boundary regions | R19 | `new wall boundary contract` | Hcr, Lw, t, Hw and wall cuts; **Critical height/boundary geometry** |
| `CHK-143` | Wall reinforcement | R19 | `new wall rebar design contract` | web+boundary As and placement; **Vertical/horizontal reinforcement and splice** |
| `CHK-144` | Wall shear and capacity shear | R19 | `new wall capacity shear contract` | Vd,Md,Mpt,D,beta_v, wall type; **TBDY 7.6.6.3 conditional Ve, not max(D×Vd) blindly** |
| `CHK-145` | Coupled wall link beams | R19 | `new coupling beam contract` | opening geometry, link beam forces; **Coupling-beam load path and detailing** |
| `CHK-146` | Story shear distribution and story phi | R02/R19 | `new SAME_CUT story phi contract` | pier+frame story shear, all objects and one cut; **Story shear wall/frame share and physical cut reconciliation** |
| `CHK-147` | Joint topology | R10/R13 | `column_joints.py / joint_kernel.py` | all incident beam/column physical faces; **Full joint topology and orientation** |
| `CHK-148` | Joint confinement | R13 | `joint_kernel.py` | confined/nonconfined joint, Ash and tie layout; **TBDY 7.5.2.3 detailing** |
| `CHK-149` | Slab geometry and thickness | R19 | `new slab geometry contract` | slab polygon, openings, thickness, span; **TS500 slab classification/thickness** |
| `CHK-150` | Slab flexure and reinforcement | R19 | `new slab flexure contract` | M11/M22/M12 shell, top/bottom; **Transformed/design moments and required As map** |
| `CHK-151` | Slab punching | R19 | `new slab punching contract` | column-punching perimeter and transfer moments; **Vpd/Vpr and eccentric action** |
| `CHK-152` | Slab deflection and cracking | R19 | `new slab serviceability contract` | area displacement, rho', sustained load; **delta_i+lambda delta_ig and correct limits** |
| `CHK-153` | Diaphragm in-plane forces | R19 | `new diaphragm transfer contract` | F11/F22/F12, collector load path; **In-plane force transfer and reinforcement** |
| `CHK-154` | Foundation geometry | R19 | `new foundation geometry contract` | SAFE/footing geometry, bearing contact; **Footing/raft physical model validated** |
| `CHK-155` | Foundation soil pressure | R19 | `new soil bearing contract` | q_data, contact pressures, combined N-M; **Bearing check for correct soil limit state** |
| `CHK-156` | Foundation one-way shear and punching | R19 | `new foundation shear/punching contract` | one-way shear & punching design cuts; **TS500 shear/punching on physical sections** |
| `CHK-157` | Foundation reinforcement | R19 | `new foundation reinforcement contract` | foundation M11/M22 and reinforcement layout; **Top/bottom As plus development/detailing** |
| `CHK-158` | Foundation-to-superstructure load transfer | R19 | `new foundation load transfer contract` | base joint, raft reaction; same cut; coordinate systems; **Equilibrium with approved foundation model** |

## 6. Ürünü gerçekten ilerletecek uygulama sırası

| Eşik | Konu | Kanıt / kabul ölçütü |
|---|---|---|
| **P0-0** | Source gate ve ID namespace | Bozuk/yanlış model ZIP'de hiçbir bağımlı CheckInstance PASS değil. 73/242 çakışmaları ayrık. Legacy A3/B3 yeniden bağlandı. |
| **P0-1 (R00–R03)** | Offline kaynak census ve approved ModelProfile/ComboBook | Kaynak digest, gerçek I/J uç ve station, case-role/provenance, kapsama/payda. 13 Kasım bankası 9 Kasım analiziyle sessiz birleştirilmez. |
| **P0-2 (R04–R06)** | Modal + tasarım kuvveti türleri | Statik vektörler ve spektral skaler zarf ayrık; `γE` belirsiz dallar ayrı. A1/B1/B2, story/case/yön tüm nüfus tamamlanır veya NOT_PROVEN. |
| **P0-3 (R07)** | Tek gerçek kolon, independent PMM oracle | Aynı kaynak kesiti + actual source rows + seçilmiş kafes + bağımsız kesit sayısalı + JSON/HTML. FIRST_ORDER_CANDIDATE hiçbir zaman nihai kolon PASS değil. |
| **P0-4 (R08–R09)** | TS500 P–Δ/P–δ ve donatı iterasyonu | k/EI/Nk/uç koşulları, e_min, tek sahipli second-order, ara N talep taraması, konverjans veya no-candidate. |
| **P0-5 (R10–R14)** | Beam Mr → SCWB → Ve/Vr → joint panel | Her fiziksel joint/axis/sign, A19–A23 benzeri gerekli narinlik senaryoları, α_i ve relayout geri beslemesi; tek kolon uçtan uca kapanır. |
| **P0-6 (R15–R16)** | 87 kolon + dört golden | Her applicable CHECK örneğinde tam payda, source/engine/oracle/report tutarlılığı, beklenen 4 yorum farkının hükme bağlanması. |
| **P1 (R17–R19)** | UI/report/store ve kiriş/perde/döşeme/temel aileleri | Her aile ayrı source→math→oracle→report slice. Yeni shell/SAFE kaynakları yoksa ilgili aile NOT_PROVEN. |
| **P0 final (R20)** | Release | TÜM kabul kapsamı complete, bağımsız golden ve source run sabit, supervisor engineering signoff. |

**Kısa sonuç:** Reçete bir *araştırma listesi* olmaktan çıktı: fiziksel kaynak, kaynak nesli, hesap sahibi, normatif uygulama ve bağımsız kabul kapılarına bağlandı. **Yeni mühendislik kodu yazılmadı**; bu dosyanın varlığı hiçbir kontrole `IMPLEMENTED`, `PASS` veya `READY` yetkisi vermez.

## 7. Kabul için teslim edilecek üç gözlemlenebilir kanıt

1. `SOURCE_GATE_NEGATIVE_MATRIX`: bozuk SHA, yanlış birim, farklı EDB, farklı analysis generation, eksik frame, eksik joint, yanlış combo rolü, yanlış schema ve duplicate station testlerinde fail-closed.
2. `ONE_REAL_COLUMN_END_TO_END`: aynı seçili kolonun source→approved demand→k/EI/Nk→biaxial PMM→rebar→SCWB→shear→joint→rapor zinciri, sayısal oracle ve ara tablolarla.
3. `FULL_DENOMINATOR_INVENTORY`: tüm kat, tüm fiziksel kolon/kiriş/perde, tüm ilgili yön/işaret ve kombinasyonların beklenen/gözlenen/bloke edilen adetleri; eksik çocuk kalırken bina PASS verilemez.

**Değişmeyecekler:** 9 Kasım native bankası, 13 Kasım capture ve mevcut geçmiş receipt'ler immutable; `main` ve Supervisor merge gate korunur; eski kabul edilmiş hesaplar yeniden yazılmaz.
