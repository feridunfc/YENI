# TBDY Next Engine

Small, project-owned Turkish structural-engineering application. The older `TBDY`, `Column-Engine`, and R1-C codebases are **references only**; none are runtime dependencies. Each iteration implements **one bounded vertical slice** and records which stage was actually verified.

## VS01 — Modal effective-mass ratio (numerical subcondition)

1. From the Windows UI, attach to an already-running ETABS 23.2.0 instance.
2. Read the **complete** `Modal Participating Mass Ratios` table via the project-owned adapter. Offline JSON imports are optional.
3. Validate real source fields, all rows, selected modal case, contiguous modes, and cumulative fractions.
4. Evaluate the 95% mass-ratio subcondition of TBDY 2018 §4.8.1.2; this is **not** a complete seismic engineering verdict.
5. Show live X/Y results and old CLI results in the UI; write local receipts with source SHA-256. Never issue global engineering release.

## Installation and tests

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Windows / PyCharm — direct ETABS web connection

ETABS 23.2.0 must already be running with an analyzed, locked model. This
application never saves the model or starts analysis. Run from the repository
root with the project interpreter:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install comtypes
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m tbdy_next.cli serve --host 127.0.0.1 --port 8765 --out .receipts
```

Open `http://127.0.0.1:8765`, choose **Modal analiz**, then press **ETABS'a
bağlan ve hesapla**. No JSON file selection is required. The local server
reads only `Modal Participating Mass Ratios` from the active ETABS instance,
restores any temporary output-case selection, validates the rows, performs the
same VS01 numerical check as the CLI, and saves the input + stage receipts
under `.receipts/RUN-*`. Existing CLI results appear in the UI automatically.

The web server only listens on localhost; actual COM access is lazy and occurs
only after clicking the live button. Windows COM live acceptance is separate
from mock-based CI verification. In Codespaces/Linux the live button does not
connect to ETABS. **Modal Analiz (VS01)**, **Kirişler/Kolonlar (VS02)** ve **Malzeme/Düzensizlikler (VS03 adayı)** kontrolleri etkin; diğer çalışma alanları planlıdır. The 95% result is a numerical subcondition,
not a global seismic-design release.

## Command-line usage

```bash
python -m tbdy_next.cli inspect-preflight --input path/to/etabs_readonly_preflight.json --out .receipts
python -m tbdy_next.cli check-modal --input tests/fixtures/modal_meets.json --case Modal --out .receipts
```

The repository includes **synthetic fixtures only**. Real project files, EDB models, and ETABS snapshots are excluded from git and must remain local/private. VS01 does not establish engineering release. Real modal tables and all used fields require targeted source review before a complete engineering check can be claimed.

Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Selective reference reuse: [`docs/REUSE_REGISTER.md`](docs/REUSE_REGISTER.md).

## VS02 — Five checks with one live ETABS acquisition

The **5 kontrolü birlikte çalıştır** button reads the existing modal case
plus six geometry tables from the same Windows ETABS COM session. It validates
actual field metadata, the `SectProp` assignment and the `UniqueName + Story`
join across frame summary, beam/column connectivity, and concrete rectangular
section definitions. Dimensions `t2` (width) and `t3` (depth) are read in meters
and converted to millimeters **only if the observed source field metadata
confirms `m` and present-units enum is 6**.

Five implemented checks: modal mass 95% numerical subcondition, rectangular
column minimum 300 mm, beam web width 250 mm, beam depth 300 mm, beam h/b ≤3.5.
Geometry checks are **numerical screenings**, not full TBDY compliance: seismic
ductility/applicability, beam/frame exceptions, beam slab-thickness condition,
and attached column/wall width are not inferred. Unmatched elements or missing
units are shown as `NOT_PROVEN`, never silently skipped.

The left navigation tree is automatically populated from the actual five check
definitions. Five-check outputs and original complete source rows stay under
`.receipts` only, not in the public GitHub repository.

## Used-material scope (VS02 candidate)

The RC member geometry screen uses an exact member/section/material join:
`Frame Assignments - Summary.UniqueName` → `Frame Assignments - Section Properties.SectProp` →
`Frame Section Property Definitions - Summary.Material` → `PropMaterial.GetTypeOAPI`.
The ETABS material type code **2** identifies concrete; a different documented
material type is **NOT_APPLICABLE** to these concrete-only screens, not a failure.
Unknown types, missing section bindings, unrecognized shapes, and conflict rows
remain **NOT_PROVEN**. The inventory denominator retains each identified beam/column.
This is a pure project-owned adaptation of prior TBDY material-population semantics,
not a runtime import or whole-building code compliance claim.

## VS02 — Full reports and audit JSON

After **5 kontrolü birlikte çalıştır** succeeds, open **Modal Analiz → 05 · Hızlı geometri kontrolleri**. Two controls appear for the selected, previously recorded run:

- **Tam JSON dışa aktar**: downloadable `TBDY_NEXT_RUN-..._all_checks.json`. Contains all five check results, all element-by-element geometry results (including NOT_APPLICABLE and NOT_PROVEN), the complete ETABS modal source table, the six geometry source tables with original rows/fields, material type facts, and receipt/source hashes. It is meant for independent verification and may include model path or other sensitive project details. Review before sharing.
- **Mühendislik raporu / PDF**: standalone, printable HTML containing the full check summary, complete per-element tables, the full modal table, source census, materials, and source fingerprints. Print or save to PDF using your browser's **Ctrl+P** command.

The dropdown switches between stored full five-check runs. Exports read `.receipts/RUN-...` only; **no new ETABS connection, recalculation authority, model mutation or upload occurs**. Existing modal and geometry evaluators revalidate the archived data and receipts. An incomplete or tampered run does not produce a report. `ENGINEERING_RELEASE=NOT_READY` and `FORMAL_COMPLIANCE=NOT_PROVEN` remain explicit.


## VS03 — Beton malzeme ve A1 X/Y kaynak bazlı alt kontrolleri (canlı kabul bekliyor)

Yeni *YENI* uygulaması aynı Windows ETABS oturumunda iki yeni tablo okur:
`Material Properties - Concrete Data` (`Material`, `Fc`) ve
`Story Max Over Avg Drifts` (`Story`, `OutputCase`, `Direction`, `MaxDrift`, `AvgDrift`, `Ratio`).
Malzeme hesabı yalnız daha önce `PropMaterial.GetTypeOAPI` ile **beton** olduğu
belirlenen ve modelde kullanılan malzemelere uygulanır; bilinen kaynaktan gelen
`Fc` değerleri, alan birimi doğrulandığında MPa'ya çevrilerek **fck ≥ 25 MPa**
alt koşuluyla karşılaştırılır. X/Y kat oranlarında **1,20 üzeri A1 gözlendi**
şeklinde sınıflandırılır; bina uygunluk kararı değildir.

VS03 için ön testte gerçek `RSX` ve `RSY` vakaları gözlenmiştir; bu iki vaka
geçici seçilir, seçim her durumda geri yüklenir. Yeni tabloların **bu modeldeki
alan/satır kabulü henüz yapılmadı**. Alan, birim veya vaka örtüşmüyorsa kontrol
`NOT_PROVEN` bırakılır ve raporda şema bilgisi görünür. Eski beş kontrollü
raporlar bozulmaz; yeni sekiz kontrollü canlı kayıtlar bütün kaynak satırları,
malzeme değerleri ve kat bazlı A1 sınıflandırmalarıyla JSON/HTML'e aktarılır.

Windows/PyCharm: açık ETABS'ta `kompakt_b.EDB` modeliyle arayüzü açın ve
**8 kontrolü birlikte çalıştır (VS03)** düğmesini kullanın. Kontrol sonucu ve
şema hatalarını görüntüleyin; **Tam JSON dışa aktar** ile gerçek veriyi ayrıca
incelemeye gönderin. `main` henüz VS03'ü içermiyor; geliştirme dalı
`work/vs03-material-torsion-20261107`.

## VS04 — Actual analysis source table acquisition (no new compliance check)

The **VS04 · 3 analiz tablosunun şemasını al** button captures all rows and
field metadata for ETABS `Modal Periods And Frequencies`, `Base Reactions`, and
`Story Drifts`, under one existing Windows COM session. It restores the original
display case selection, keeps the previous eight results intact, and records a
separate `vs04-schema` receipt in the same run. Source and schema fingerprints
appear in JSON and complete raw tables in the printable HTML. No case naming,
analysis generation, code compliance, or numerical readiness is inferred.

See [VS04 source/acceptance protocol](docs/VS04_ANALYSIS_SOURCE_SCHEMA.md).

## VS04 — bounded analysis-source arithmetic (review candidate)

For a VS04 web run, the same signed source archive now produces a second receipt,
`vs04-numerics`. It checks exactly the observed ETABS modal T/f/omega/eigen
identities, separately records X/Y Base Reactions components (without asserting
concurrent vectors or spectrum scaling), and tests algebraic `Drift × Drift/`
consistency for exactly selected X/Y rows (without approving the drift units or
TBDY effective-drift semantics). Five **source components**, zero new formal
regulatory checks. The existing eight accepted VS01–VS03 checks remain unchanged.

HTML and JSON show the complete source arithmetic and its blockers. Missing,
changed, or forged receipts reject the export for newly captured VS04 runs.
See [VS04 numerical source protocol](docs/VS04_NUMERIC_SOURCE_REVIEW.md).

### Recheck a locally captured VS04_RAW file without ETABS

The `tools/replay_vs04_raw.py` script replays the same pure source math
against the private RAW JSON. It does not connect to ETABS, touch the
analytical model or claim normatively approved drift/base-shear calculations.

```powershell
cd C:\Users\efeya\PycharmProjects\YENI_VS04
$raw = (Get-ChildItem ".receipts\VS04\VS04_RAW_*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
if (-not $raw) { throw "VS04_RAW is missing" }
.\.venv\Scripts\python.exe tools\replay_vs04_raw.py --input "$raw" --out ".receipts\VS04\VS04_REPLAY_LATEST.json"
```

The new `VS04_REPLAY_LATEST.json` has source-schema diagnostics, five
component-level source-math results, and input SHA-256, but excludes the complete
raw source rows. Share this replay first; real source data is still necessary
for independent row-by-row acceptance. Full engineering release stays NOT_READY.

## VS04-E — Normative readiness and targeted ETABS basis inventory

The five planned TBDY rule instances are compiled with **all missing input
requirements shown**, rather than treating a 5/5 source-arithmetic result as
formal compliance. Eq (4.19), (4.31), (4.33), and (4.34) are implemented as
unit-checked, **formula-only** kernels. No additional check becomes PASS.

`tools/probe_vs04e_basis_windows.py` captures a read-only index and bounded
source fields/rows for *candidate* seismic-mass, story-geometry, response-
spectrum and case-definition tables from the already-open ETABS model. No
source key is auto-approved by fuzzy matching. Review the
[VS04-E source and normative dependency contract](docs/VS04_E_NORMATIVE_BASIS.md).

## VS04-F — Exact ETABS source binding review

After VS04-E raw table probe, execute `tools/review_vs04f_basis.py` against
its original local `VS04E_BASIS_PROBE_*.json`. The offline source compiler
reconciles story/group/joint masses, binds response-spectrum and Ritz case
identities, validates story heights, and retains `Response Spectrum Modal Info`
API errors. It **cannot** grant TBDY compliance, spectrum scale validity,
full drift approval, or analysis generation lineage. See
[VS04-F source binding contract](docs/VS04_F_SOURCE_BINDINGS.md).

## VS04-G — Targeted diaphragm + selected spectrum-modal source probe

After the VS04-F real-source replay, capture only the exact diaphragm definition,
area/joint assignment tables and the response-spectrum modal output under
original and temporarily selected RSX/RSY display cases. See
[VS04-G source capture and safety protocol](docs/VS04_G_DIAPHRAGM_MODAL_EVIDENCE.md).
This is a read-only structural model capture with a fully restored display
selection, **not** a TBDY compliance calculation. The 8 accepted checks stay
unchanged and `engineering_release` remains `NOT_READY`.

## VS04-H — Offline diaphragm/mode source linkage

The [VS04-H source-review protocol](docs/VS04_H_DIAPHRAGM_LINKAGE.md)
reconciles the real 5 semi-rigid diaphragm definitions, 91 area and
325 point-object assignment rows, and 100+100 RSX/RSY modal source
rows against the previous accepted modal period display (optional).
`tools/review_vs04h_diaphragm.py` writes a source-only review without
raw rows, never promotes source consistency to regulatory compliance.

## VS04-I — Independent source spectrum reconstruction

After VS04-H, run tools/review_vs04i_spectrum.py offline with the earlier
VS04-E, VS04-G and VS04-D replay files. It checks the 26 TSC2018 function
knots analytically, and the 200 modal source accelerations via actual corner
periods and higher-precision modal circular frequencies. It never promotes
source arithmetic to building code PASS or engineering release. See
[VS04-I protocol](docs/VS04_I_SPECTRUM_RECONSTRUCTION.md).

## VS04-J — Conditional equivalent base-shear floor source screening

Run `tools/review_vs04j_base_shear.py` with the original VS04-E / VS04-G
and VS04-D replay JSON files. This independently revalidates source
bindings and computes **only** the Eq (4.19) minimum term on candidate
seismic mass, I, and SDS. It **does not** compute or approve design VtE,
pre-beta Vtx, gammaE or beta_tE. See
[VS04-J engineering and source contract](docs/VS04_J_BASE_SHEAR_SCREENING.md).

## VS04 single-action UI and product integration hold

The primary web UI now uses one live calculation action and the existing
/api/live-vs04 route, with eight bounded checks, VS04 schema, source
arithmetic and readiness in one archived run. VS04-F through VS04-J
are NOT integrated into this live route; they are offline evidence tools.
Read docs/VS04_EMERGENCY_PRODUCT_AUDIT_20261107.md before any merge.
ENGINEERING_RELEASE=NOT_READY; MERGE=HOLD.

## VS04 E–J integrated one-click source chain

The one main ETABS calculation action captures the six additional E–J source
stages under the **same locked SapModel COM session**, archived input hash
and `run_id`. The `vs04-pipeline` receipt is rechecked before JSON/HTML
exports or history. Conditional base-shear output and A1 findings are visible,
but formal TBDY VtE, beta, drift, source generation and applied eccentricity
remain NOT_PROVEN. See
[VS04 one-run source integration and Windows gate](docs/VS04_SINGLE_RUN_EJ_INTEGRATION.md).

`MERGE=HOLD`, `ENGINEERING_RELEASE=NOT_READY` until Windows live E2E.
