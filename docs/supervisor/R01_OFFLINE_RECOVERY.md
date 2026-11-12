# R01 — Tarihsel 87 kolon arşivinden offline kaynak kurtarma

**Çalışma ortamı:** GitHub Codespaces / Linux. Canlı ETABS, Windows COM, RunAnalysis, model mutasyonu ve yeni veri edinimi **yasak**. Bu sprintte yeni bir yapı tasarımı onaylanmıyor.

## İki arşivi asla aynı run olarak birleştirme

| Arşiv | Amaç | Kanıt sınırı |
| --- | --- | --- |
| 09.11.2026 source bank \`YENI_RUN-5cf449..._columns.zip\` | 87 kolonun kaynak kuvvetleri ve altı statik birleşimin aritmetiği | 34.170 native satır; kaynak/nümerik replay; tasarım yetkisi yok |
| \`full-model-evidence.zip\` | İlk arşivin SHA-256 ve native çağrı provenansı | Analiz nesli/eşzamanlılık ispatı değil |
| 12.11.2026 \`YENI_ALL_COLUMNS_...zip\` | Yeni capture arızasının tanısı | Fiziksel kolonlar 87, **force rows 0**; eski veriden doldurulamaz |

Kaynak SHA ve nüfus kayıtları \`config/r01_archived_sources.json\` içindedir. Kişisel model, ZIP, SQLite, EDB ve ham çağrı kayıtları **Git deposuna yüklenmez**.

## Sıra: yalnız kaynak doğrulaması, testler gün sonunda

1. Offline dosyaları \`.private_sources/\` içine koy (Git ignore kapsamında).
2. Tarihsel native kaynak SHA'sını ve bank kuvvet nüfusunu doğrula:

\`\`\`bash
python tools/r01_verify_archived_bank.py \
  --bank .private_sources/YENI_RUN-5cf449b850fc41eeadcdd7528249f932_columns.zip \
  --source-archive .private_sources/full-model-evidence.zip \
  --output /tmp/r01_archived_source_receipt.json
\`\`\`

3. Eğer uygun türetilmiş \`column-bank.sqlite\` yerelde mevcutsa \`--sqlite .private_sources/column-bank.sqlite\` ekle. SQLite \`mode=ro&immutable=1\` ile açılır, \`quick_check\`, application_id, run/source bağları ve satır nüfusu denetlenir. Eksik SQLite yerine yeni bir uydurma veritabanı üretilmez.
4. Yeni 12 Kasım arşivi ayrı olarak \`r00_offline_gate.py\` ile denetlenir. Başarısız \`FrameForce\` kaynağı eski kaynakla **tamamlanmış gibi** gösterilmez.

## Kapanış kriteri

- 87 özgün kolon kimliği, 34.170 native satır, kaynakta aynı Obj/Elm/ObjSta/ElmSta/LoadCase/StepType/StepNum kimlikleri ve SHA'lar doğrulanmalı.
- Altı desteklenen statik Linear Add birleşimi, kaynakta mevcut durumlar üzerinden \`Fraction\` tabanlı **yeniden** hesaplanmalı; beklenen 2.412 satır ve 14.472 bileşen karşılaştırması yapılmalı.
- Normatif nitelik \`NOT_PROVEN\`, \`engineering_release=NOT_READY\`, \`design_demand_authority=DENIED\` kalmalı.
- Source ZIP zaten yeterli olsa bile \`analysis_generation_proven=false\` olayı otomatik açılmaz.
- Bu geçişin sonunda yazılım kaynak yetkinliği ayrı değerlendirilecek; VS27 kod bütünleştirmesi ve 87 gerçek kolon tasarımı ayrı kapıdır.

**Tests:** Supervisor talimatı gereği toplu test çalıştırması/golden/Windows/ETABS kabulü sprint sonunda yapılacak. Bu dosyanın commit edilmesi, test edildiği veya kabul edildiği anlamına gelmez.
