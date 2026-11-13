# PDF örnek hesap → ikinci offline doğrulama bankası (V1)

**Tarih:** 2026-11-13  
**Hedef:** `feridunfc/YENI` için PDF hesaplarının bağımsız sayısal oracle olarak izlenebilir biçimde saklanması.  
**Durum:** `REFERENCE_ONLY`; `YENI_RUNTIME_NOT_YET_TESTED`; `ENGINEERING_RELEASE=NOT_READY`.

## Kaynak ve model sınırı

- Kaynak dosya: `4_sikistirilmis_10MB_alti(1).pdf`, 261 fiziksel sayfa, ideCAD 11.28 / `STATİK ŞABLON PROJE` / 03.11.2026.
- SHA-256: `0c6955496aaaa92e2b508ca4eb040927ac8eab2bef92a857f2ff602b8a78fba2`.
- Geometri: 3 kat × 5,00 m = 15,00 m, kolon 40×40 cm; malzeme C30/B420C, R=8, D=3, I=1.
- Bu PDF'nin model kimliği, 13.11.2026 tarihli `kompakt_b.EDB` (dört katlı model) ile **eşit veya aynı analiz nesli** kabul edilmez.
- ETABS ZIP / PDF / GOLDEN / Excel girdileri ayrı source namespace ve SHA taşır.

## Gerçekten oluşturulan offline artefakt

`TBDY_Second_Offline_PDF_Reference_Bank.sqlite`:
- `documents`, `model_parameters`, `report_pages` (261/261), `pages_fts` (aranabilir PDF metni), `reference_cases`, `comparisons`, `independent_source_roles`, `source_review`.
- **134** karşılaştırma kaydı; bunun **79 tanesi PDF'de basılı hedef değere**, **55 tanesi PDF girdi değerlerinden oluşturulmuş türetilmiş ara büyüklüğe** aittir. 79/79 basılı hedef aritmetik tolerans içinde; türetilmiş olanlar bağımsız PDF oracle PASS sayılmaz.
- 27 kolon eksenel tablo satırı × 2 limit ve 27 sürtünme kesmesi satırı kaynak sırası korunarak alınmıştır.
- Birim ve gösterim yuvarlaması sayfa/örnek düzeyinde belgelidir; örneğin `8Ø14+4Ø14` donatı alanı görüntülenen 18,47 cm²'ye önce yuvarlanmadan hesaplanır.

**Kaynakla bağlı PDF sayfaları:** modal 22, etkin öteleme 26, ikinci mertebe 27, A1 28, B2 30, SCWB 252, kolon eksenel 254, sürtünme kesmesi 255, birleşim kesmesi 257. (Fiziksel PDF sayfa numarası; basılı numara -2'dir.)

## Çekirdek karşılaştırması — dürüst yetki ayrımı

1. Yerel bağımsız `TBDY-Next-Engine_Offline_Verified.zip` sürümünde `effective_story_drift`, `story_stability_ratio`, `modal_mass_check` ve `scwb_strength_ratio` **çalıştırıldı**; 64/64 mevcut birim testi de geçti.
2. `YENI` recovery dalında `soft_story_b2.py`, `r05_story_irregularity.py`, `ts500_column.py`, `scwb_kernel.py` ve `joint_kernel.py` formüller ve girdi sözleşmeleri için **kaynak kod düzeyinde incelendi**.
3. Yerel `YENI` runtime kaynak kodu çalıştırılmadı. Dolayısıyla `YENI_GOLDEN_PASS`, `PMM_FINAL_PASS`, `FULL_BUILDING_PASS` veya `RELEASE_READY` iddiası **yoktur**.

**Örnekler:**
- A1 (PDF28) `4.011/[(4.011+3.522)/2]=1.06490`, PDF: `1.065`.
- B2 (PDF30) `(5.865/5)/(3.766/5)=1.5574`, PDF: `1.56`.
- Drift (PDF26) `R/I×Δ=8×2.746=21.968mm`, PDF: `21.970mm`,  `λδ/h≈0.001746`.
- Global `θ` (PDF27): `1577.22×0.002654/(43.81×5)=0.019110`, PDF: `0.0191`.
- SCWB (PDF252): `169.323+197.030=366.353kNm`, `1.2×(80.739+88.359)=202.9176kNm`, PDF: `366.35>202.92`.
- Joint limit (PDF257): C30, 400×400mm: `1.0×400×400√30/1000=876.36kN`; confined `1.7×...=1489.81kN`.
- Sürtünme kesmesi (PDF255): 12Ø14 gerçek alanı ile `Vr=674.65kN`.

## Repo entegrasyon kuralı

SQLite/PDF/CSV/JSON ZIP teslimi bu sohbetin **artefaktıdır**; binary dosyalar GitHub'ın kamuya açık repo'suna gönderilmedi. Codespaces'te kaynak arşivini `.private_sources/pdf_reference_bank_v1/` içine al; manifest SHA'sını kontrol et; sonra **R07 single-column actual YENI runtime** golden harness tüketicisiyle bağla. Kaynak devri, PMM istemi, k/I/β, SCWB ve joint donatısı için PDF numaralarını **farklı modelden ETABS sonuç aktarımı** olarak kullanma. Yeni raporların her biri ayrı `doc_id`, model SHA, analiz nesli ve iddia yetkisiyle eklenmeli.

**Sonraki Golden hedefi:** YENI'nin native `ts500_column`, `soft_story_b2`, `joint_kernel` işlevlerini bu bankaya bağlayıp, PDF ile aynı girdilerde **gerçek yerel runtime ölçümlerini** almak; farklılık varsa `MISMATCH` olarak raporlamak, algoritmik yöntem farklarını saklamamak.
