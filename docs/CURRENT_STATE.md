# CURRENT_STATE — yerel checkpoint ve uzak senkronizasyon

**Başlangıç kaydı: 17 Kasım 2026. LOCAL_RECONCILIATION_REQUIRED.**
Bu dosya son incelenmiş GitHub D3B sürümünden başlatıldı. Kullanıcının yerel
Codex ağacı bu sürümün önünde olabilir; yerel kod bu oturumda görülmedi.
Aşağıdaki D3B sayıları yerel güncel durum veya bu hafıza kurulumunda yeniden
çalıştırılmış testler değildir. Önce yerelde uzlaştır; kodu geriye alma.

## 1. Birbirine karıştırılmayacak kimlikler

| Alan | Kayıt |
|---|---|
| Ürün | `feridunfc/YENI` |
| Çalışma modeli | Yerel Codex; her sprint disk checkpoint; GitHub'a 3–5 sprintte bir |
| Yerel dal / HEAD / dirty durum | **Henüz okunmadı**; yerel Codex doldurmalı |
| Yereldeki aktif sprint / son test edilen ağaç | **Henüz uzlaştırılmadı** |
| Son gözlenen uzak geliştirme dalı | `audit/pipeline-pmm-v6-20261117` |
| Son gözlenen uygulama commit'i | `85e720d18683a71737c1919d32e393c9d903737b` (D3B) |
| Bu commit'in Git ağacı | `069342dfd21b828bbaeba73d601db5f49aafb6e3` |
| Push edilmemiş sprint sayısı | **Bilinmiyor**; 0 varsayma |
| Canlı ETABS | Açık kullanıcı yetkisine kadar ertelenmiş |
| Main merge / force-push | HOLD / yasak |

Hafıza dosyalarının commit'i uygulama doğrulama commit'i değildir. Dosyanın
kendi commit SHA'sını içine yazmaya çalışma. Bu dört dosyanın son commit'ini
`git log -1 --format=%H -- AGENTS.md docs/CURRENT_STATE.md docs/ENGINEERING_GAPS.yaml docs/VERIFICATION_LEDGER.json`
ile, gerçek checkout'u `git rev-parse HEAD` ile çöz. Yerel kayıt güncellendiğinde
bu tablonun yalnız değişen alanlarını güncelle; tarihsel D3B kanıtını ledger'da koru.

## 2. İlk yerel devralma işi

Aktif başlangıç görevi: **LOCAL-CONTEXT-RECONCILIATION**; yeni mühendislik sprinti değil.
Repo kökünü, dalı, HEAD'i, staged/unstaged ve untracked kodu incele. Bu dört dosya
zaten yerelde varsa üstüne kopyalama; yeni yerel kararları koruyarak birleştir.
Son yerel test günlüğünü ve gerçek kaynak kimliklerini kontrol et. Ardından
şu checkpoint alanlarını doldur:

```yaml
checkpoint_id: null
updated_at: null
local_branch: null
local_head: null
working_tree_status: NOT_INSPECTED
changed_paths: null
untracked_code_paths: null
active_task: LOCAL-CONTEXT-RECONCILIATION
last_completed_step: null
next_action: Yerel kod ve kanıtla bu başlangıç kaydını uzlaştır.
blockers: []
decisions_and_reasons: []
latest_local_verification_ids: []
last_verified_remote_implementation_sha: 85e720d18683a71737c1919d32e393c9d903737b
sprints_since_sync: null
```

Bir sprint başlamış fakat bitmemişse WIP dosyalarını ve ilk devam adımını yaz.
Sohbetin son cümlesini görev kabulü gibi kullanma. Git fetch/pull, ilk okumanın
zorunlu şartı değil; senkronizasyon ayrı işlem. `origin/...` yerel tracking ref'i
son fetch'ten beri eski olabilir; gerçek uzaktan doğrulama tarihini ayrı tut.

## 3. Korunacak son yayımlanmış kazanımlar

| Dilim | Uygulanmış kapsam | Kanıt |
|---|---|---|
| PMM v6 | Native düğüm koordinatı; çok elemanlı kolon iç düğümünün iki tarafı; desteklenen gerekli kesit alt kümesi | EV-PMM6 |
| D1 | Özgün `parent.source` + açık donatı senaryosu; kaynak hash'i ve seçilmiş aday ilişkisi | EV-D1 |
| D2 | Eleman/düğüm/kat bağımlılıkları, eksik kesitin yerel etkisi, revizyon izleme | EV-D2 |
| D3 | Desteklenen imzalı statik referans dalında sınırlı α → talep → yeniden seçim döngüsü | EV-D3 |
| D3B | Karma imzalı Linear Add deprem ayrıştırması ve kayıtlı spektral aralıklar | EV-D3B |
| Finalized v2 | Kaynak/sonuç/rapor bağları; yeni raporda yeniden hesap yok; legacy yol ayrı | EV-D3B-REPLAY |

Eski audit'teki bütün açıkları otomatik güncel sayma. Örneğin yeni finalized v2
raporunun tekrar hesap yaptığı veya 14 çok elemanlı kolonun hâlâ koordinat alımı
beklediği iddiaları bu baz için güncel değildir. Genel DAG ve tam mühendislik
kapsamı yine ayrı açıklar. Kapanan dar kapsamı ancak somut regresyon veya
source/method/cage revizyonu değişikliği varsa yeniden aç.

## 4. D3B bazının son doğrulama özeti

**Kod bazına ait tarihsel sonuç; yerel yeni sprintlere otomatik aktarılmaz.**
1307 Python testi, 10 JavaScript test dosyası, 141 izole wheel testi başarılı;
32 yeni test toplamın içinde. CI run `44109479090`: Ubuntu 3.11, Ubuntu 3.12,
Windows 3.12 başarılı. Windows CI canlı ETABS değildir. Bkz. EV-D3B, EV-D3B-CI.

Gerçek offline senaryo: 87 kolon, 957 kolon–birleşim çifti, 4422/4422 gerekli
alt-kesit; spektral aralık 696 çift / 3216 kesit. α = BLOCKED_INPUTS, iterasyon
0; R14/R15 = 0 kapanış, 87 partial/unbound, 0 kayıtlı normatif FAIL. Sıfır FAIL
87 PASS demek değildir. Aynı ortam tekrarı IDENTICAL; raporda 17 hesaplayıcı
devre dışıyken çağrı 0. Kaynak/senaryo/sonuç SHA'ları EV-D3B-REPLAY içinde.

**FORMAL_COMPLIANCE=NOT_PROVEN; ENGINEERING_RELEASE=NOT_READY.**
73 CHECK, 94 DAG düğümü, 242 atomik aday ve test sayıları ayrı tutulur. 73 CHECK
bazında tam kabul sayısı mevcut kanıtla ilan edilmiyor. Düğüm eşleştirmesi genel
DAG yürütmesi değildir. Golden: canonical 467 / 3 PDF / 716 sayfa; üretim golden
komutundaki 44 kayıt ayrı kapsamdır (15 eşleşme, 25 yetersiz kaynak, 4 yorum farkı).

## 5. Yerel ilerleme bunu aşmadıysa sıradaki mühendislik işi

Öncelik **GAP-018 + GAP-013 + GAP-016**: spektral yön/mod birleştirmesi,
SCWB governing Nd ve kat kesmesi paylaşımını aynı kabul edilmiş yöntemle bağla;
bağımsız tam hesap örneğiyle iterasyonu doğrula. D3B bu işi tamamlamadı.
Yeni canlı veri istemeden mevcut özel kaynakları ve bankaları salt okunur tara.

Son bilinen kaynak sınırı: yeni yakalamada primitive force kayıtları ve Load
Pattern Definitions eksik; ayrı native bankada modal frame kuvveti yalnız mod 1.
EDZ ve bazı düşey vakalarda StiffType etiketleri farklı; pattern benzerliğinden
case kuvvet eşitliği veya analiz nesli çıkarma. Bunlar ayrı source namespace'leridir.
Eksik girdinin tam adı/amacı çıkmadan yeni geniş capture isteme.

Kabul ölçütü: özgün kaynak değişmez; doğru yük/cut/sign kapsamı; α büyütmesi
birikmez; yalnız etkilenen aday ve bağlı kapasite yeniden değerlendirilir;
bağımsız beklenen sayılar/toleranslarla kıyas; aynı kayıtlı sonuç rapora yansır;
yakınsama, eksik veri, aday yok ve döngü ayrı. Mevcut owner'ları kullan.

İlgili dosyalar: `engineering/mixed_demands.py`, `alpha_iteration.py`,
`column_r10_live.py`, `column_r08_local_live.py`, `design_dependencies.py` ve
`column_engine/spectral_envelope.py` (hepsi `src/tbdy_next/` altında).
Başlangıç testleri: `tests/test_mixed_design_demands.py`,
`tests/test_alpha_design_iteration.py`, `tests/test_design_member_dependencies.py`.

## 6. Tekrar komutları ve özel kanıt

Repo kökünde önce interpreter/import yolunu doğrula; mevcut yerel sanal ortamı
kullan. PowerShell'de gerekirse `python` yerine `.\.venv\Scripts\python.exe` seç.

```text
python -c "import sys,tbdy_next; print(sys.executable); print(tbdy_next.__file__)"
python -m unittest discover -s tests -p test_mixed_design_demands.py -v
python -m unittest discover -s tests -p test_alpha_design_iteration.py -v
python tools/test_offline.py
```

Özel paketin yolu doğrulandıktan sonra:
`python tools/replay_design_scenario.py --bundle <private-build.zip> --scenario config/scenarios/offline_tight_ties_v1.json --case Modal --out .receipts`

Ham paket, kaynaklar, SQLite ve makbuzlar public repoda yoktur. Dosya adını
bulmak yeterli değil, ledger'daki hash'i doğrula. Eksikse başka sohbet/container
konumunu var sayma. Kaynak yoksa sentetik test çalışabilir ama gerçek replay
`NOT_RUN` kalır. Çıktıyı veya kaynak hash'ini kabul almak için değiştirme.

## 7. Sprint kapanışı ve 3–5 sprintlik aktarım

Her sprint: yerel checkpoint + ilgili GAP güncellemesi + gerçek test kayıtları.
Yerel commit yetkisi varsa küçük checkpoint commit; push beklemek hafızayı
bekletmez. 3–5 sprintlik aktarımda veya kullanıcı istediğinde: değişen dosyaları
ve özel veri sızıntısı riskini denetle, uzak farkı uzlaştır, izinli dala push et,
uzak HEAD ve o SHA'nın CI sonucunu doğrula. Push edilmeden `synced` yazma.
Başarısız/çalıştırılmamış testleri saklama. Main merge ayrı yetki ister.

Uzun geçmiş için tek kaynak Git geçmişi + mevcut `docs/engineering/OFFLINE_*`
notlarıdır. Bu dosyaya bütün sohbeti kopyalama; kısa aktif durum ve kanıt ID'si tut.
