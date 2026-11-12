# R05 — Fiziksel kat, STORY_DRIFT, A1/B1/B2 çevrimdışı defteri

**Repo/dal:** \`feridunfc/YENI\`, \`recovery/r00-r01-vs27-source-20261112\`.  
**Çalışma sınırı:** Codespaces/Linux, yalnız eski SHA sabit 8 Kasım \`all_checks.json\`. Canlı ETABS, COM, yeni analiz ve model değiştirme yok.

## Tek kaynak → mevcut saf hesaplar → ayrı sonuç defteri

Üretim algoritmalarının kopyaları yazılmadı; bu sprint *aynı kaynak raporundan* yeniden hesaplayarak karşılaştırır:

| Alan | Mevcut hesap sahibi | R05 muhasebe anlamı |
|---|---|---|
| STORY_DRIFT | \`bind_story_drift\` → \`build_story_slot_ledger\` | Her tanımlı kat×RSX/RSY×X/Y (4n) ayrı; eksik veri görünür |
| Fiziksel geometri | \`review_story_physical_source\` ve \`review_physical_story_scope\` | 87 kolon ucu gözlemi ≠ tam Frame/Area/Joint/Null/mesh census |
| Effective drift | \`review_effective_drift_readiness\` ve 94 aday DAG | 2n birincil kat/yön instance; hesap yetkisi DENIED |
| A1 | \`evaluate_next_capture\` | Gözlenen kat/yön oranları, beyan edilen fakat gözlenmeyen kat ayrı |
| B1 | \`evaluate_b1_sources\` | Duvar kalınlığı, açıklık ve rijitliği *varsayımlı* koşullu senaryo |
| B2 | \`bind_soft_story_b2\` | ETABS AvgDrift/h koşullu komşuluk oranları; ±%5 dışmerkezlik nitelendirilmedi |

## Gerçek tarihsel örnek (ön kabul verisi, R05 çalıştırıldı demek değildir)

- 8 Kasım \`RUN-d176de... \`, 4 tanımlı kat: +0.00, +4.50, +9.00, +14.5.
- 16 kayıtlı STORY_DRIFT kaynak yuvası: 12 sayısal + +14.5'te 4 kaynak eksik. **16/16 muhasebe** hiçbir zaman **16/16 kaynak** demek değildir.
- A1: üç gözlenen kat × iki ana yön, +14.5 için A1 satırı yok; bu kat otomatik BİRLEŞİM UYGULANAMAZ sayılmaz.
- B1: yalnız koşullu 4 kat-yön komşuluk karşılaştırması; +14.5'in senaryoda pasif oluşu tam fiziksel sayım kanıtı değildir.
- B2: 8/12 koşullu komşuluk hesabı; 4 eksik. \`SOURCE_NUMERICAL\` bir yönetmelik sınıflandırması değildir.
- Yalnız 87 Column Object Connectivity ve 325 Point Object Connectivity satırı tam fiziksel model sayımı yapmaz.

**Asla yapılmayacak:** farklı \`run_id\` veya farklı source SHA arasındaki sonuçları birleştirmek, boş/eksik üst katı otomatik \`NOT_APPLICABLE\` saymak, spektral Max uç ötelemelerini çıkarmak, bir dolgu duvarın gerçek davranışını yayılı ölü yükünden çıkarsamak, A1/B1/B2 koşullu sonuçlarını mühendislik \`PASS\` durumuna yükseltmek.

## Codespaces yürütme (kullanıcının isteğiyle testler gün sonuna kaldı)

\`\`\`bash
git switch recovery/r00-r01-vs27-source-20261112
mkdir -p .private_sources .receipts
# SHA'ları onaylı eski all_checks.json, Git'e eklenmeden bu klasöre konulur.

python tools/r05_review_story_irregularities.py \
  --report .private_sources/TBDY_NEXT_RUN-d176de308a3c4742a39ecb7f0128a9b1_all_checks.json \
  --output .receipts/R05_story_irregularities.json
\`\`\`

İsteğe bağlı \`--r04 .receipts/R04_modal_spectrum_review.json\`, ancak yalnız **aynı run ID ve aynı tam kaynak dosyası SHA'sında** kabul edilir. 9 Kasım R01 kolon kuvvet bankasıyla yorum/kombinasyon verisi kendiliğinden birleşmez.

Çıkış kodları: \`0\` = eski kaynak aritmetiği yeniden eşleşti ama NORMATIF YETKİ YOK; \`2\` = kaynak/sonuç çelişkisi nedeniyle BLOCKED; \`3\` = yanlış SHA, eksik, sahte, symlink veya güvensiz girdi.

## R05 halen kapanmış sayılmayacak koşullar

1. Birbirine bağlanmış gerçek 87 kolon Frame/Area/Joint/Null ve mesh nüfusu, fiziksel +14.5 katı dahil.
2. Analiz generation, DD2/DD3, R/I ve modal yatay kesme/esasları.
3. Süneklilik, ±%5 dışmerkezlik, bodrum uygulanabilirliği, gerçek dolgu rijitliği, B2 drift ortalaması.
4. Bağımsız golden eşleştirmesi, tüm birleşim/kat/yön nüfusu, Windows/canlı ETABS doğrulaması.

\`formal_compliance=NOT_PROVEN\` · \`engineering_release=NOT_READY\` · \`MERGE HOLD\`. Testler bu aşamada manuel çalıştırılmadı.
