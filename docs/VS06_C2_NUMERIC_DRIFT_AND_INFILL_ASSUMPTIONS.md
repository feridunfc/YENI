# VS06-C2 — çalışan etkin göreli kat ötelemesi sayısal senaryosu

Repository `feridunfc/YENI`, VS06 working branch `work/vs06-story-drift-coverage-20261108`. All stages remain on one **Draft PR #5**; do not merge until full VS06 final approval.

## CHECK → ETABS → binding → TBDY → test → UI/report

CHECK: existing `STORY_DRIFT` / TBDY 2018 §4.9.1 Eq (4.32)–(4.34). C1 candidate DAG/FCR remains the one owner of expected X/Y physical-story instances. C2 does **not** create a second regulatory check or duplicate formula kernel.

ETABS source: original verified `vs05_delta_source` `Story Drifts`, `Story Max Over Avg Drifts`, `Story Definitions`, physical column/point source and original receipts. Same locked Windows ETABS session can now **optionally** request `Frame Loads - Distributed` and `Beam Object Connectivity` through the existing generic table gateway. A missing/unrecognized table results in a visible missing-wall-source state, not a failed established analysis. No new COM adapter.

### Formula

For every primary direction candidate (RSX–X, RSY–Y) where ETABS already has a source-numeric drift candidate, compute

```text
Δ_ETABS,candidate = observed Story Drift ratio × observed story height
δ_scenario = (R/I) × Δ_ETABS,candidate
q = λ × δ_scenario / h
κ = 1.0 (RC), 0.5 (steel)
limit = 0.008 κ  (BRITTLE, default)
limit = 0.016 κ  (FLEXIBLE, selected only)
utilization = q / limit
conditional_numeric_condition = q <= limit
```

The numerical `(R/I) Δ` and `λ δ/h` operations reuse existing `normative_basis.eq_4_34_effective_drift` in its common brittle arithmetic path; no independent second numerical physics kernel. Zero source drift is a valid zero scenario value.

**Crucial:** Here Δ is calculated from source-published ETABS Story Drifts × h. That is NOT independent proof of the physically matched reduced displacement Δ required by Eq (4.32). As a result, the tool **executes and displays numerical scenario results**, including within/exceeds limit, but every `formal_compliance` remains `NOT_PROVEN` and overall `ENGINEERING_RELEASE=NOT_READY`. A conditional result must never be shown as an approved regulation PASS/FAIL. The real building design decision awaits qualifying the source case/displacement and model generation, not merely supplying R/I/λ by hand.

### Dolgu wall assumptions

- Default: `BRITTLE`, kappa=RC 1, R=7, I=1.5, λ=0.5, net wall height 2.8m, thickness 0.19m, coverage 100%, openings 0%. These are explicitly **editable scenario assumptions**, not independently approved real ETABS model parameters. R=7 and I=1.5 were observed in historical compact model function headers but cannot be silently generalized to all buildings; λ=0.5 is illustrative and must be replaced by genuine DD3/DD2 same-Tp evaluation.
- Alternative `FLEXIBLE`: code limit 0.016κ, only an assumed sensitivity scenario unless joint/connection drift capacity meets the evidence requirements under TBDY §4.9.1.3(b).
- `LOAD_PATTERN_BEAM_CANDIDATE`: read only exact `Frame Loads - Distributed.UniqueName` and `LoadPat=LC_WDL` (default; editable exact ETABS load-pattern name). Join frame identifiers to **actual Beam** assignments, and read `Beam Object Connectivity.Length` only if real metadata says metres. Distinct candidate beams prevent duplicate counting. This yields a **candidate** full beam length, not proven length of physically connected masonry. Nonuniform/partial distributed load spans cannot be silently inferred as full-wall extents.
- `MANUAL`: set total wall length in metres explicitly. Optionally use this when LC_WDL table or exact field/unit metadata are not observed.
- **Assumed net infill face area (m²)** = candidate or manual beam length × wall height × coverage fraction × (1 − openings fraction).
- **Assumed infill volume (m³)** = assumed face area × assumed thickness.
- Wall area is an independent downstream **B1 weak-story** sensitivity input; it does **not** linearly scale 0.008κ / 0.016κ drift limits.

### UI and reporting

The existing left navigation **Kat/sistem sonuçları** tab now hosts C2 with default Gevrek dolgu, Esnek dolgu, material, R, I, λ, LC_WDL (editable load-pattern)/manual mode and wall area assumptions. Selecting a previously archived `run_id` and pressing **Kaydedilmiş ETABS verisiyle hesapla** executes pure source-numeric scenario without another COM connection or new model analysis. It prints all story/direction numeric values and missing source rows.

`/api/vs06-drift-scenario?run_id=...&r=...&i=...&lambda=...&wall_type=...` returns the read-only hashed scenario. The existing `/api/export-checks` and `/report/print` accept the identical optional scenario parameter query and embed exactly the same scenario in the existing JSON and HTML. Scenario inputs are included in its SHA and source input SHA; the old input/receipt records are never overwritten. **No full-model compliance approval** is claimed.

For actual local archived run (existing receipt directory):
```powershell
cd C:\Users\efeya\PycharmProjects\YENI_VS06
$python = ".\.venv\Scripts\python.exe"
& $python -m unittest discover -s tests -q
& $python tools\verify_vs06_c2_archived.py `
  --root "C:\Users\efeya\PycharmProjects\YENI_VS04\.receipts" `
  --run-id RUN-e4a5376365c649b6b7469b0a778617ff `
  --r 7 --i 1.5 --lambda 0.5 --wall-type BRITTLE `
  --expected-checks 8 --expected-numeric 6
```

To inspect archived history on the new C2 UI, serve with the **old source receipt path** (read-only scenario service; live action can create new run when pressed):
```powershell
& $python -m tbdy_next.cli serve --host 127.0.0.1 --port 8765 --out "C:\Users\efeya\PycharmProjects\YENI_VS04\.receipts"
```

### Missing before *formal* regulatory acceptance

Full active physical wall/column/area story census, response-spectrum actual design displacement semantics, permitted period/mass scaling, matched DD-2/DD-3 values, complete applicable infill class/connection capacity, exact load pattern metadata and validated wall line-load extents. The conditional numerical calculation continues to function while these remain open.

## Tests / branch policy

`tests/test_vs06_c2_drift_scenario.py` includes numeric independent oracles, brittle vs flexible, unchanged limit under area changes, source missing, the 12/16 / 8-check denominator, optional observed LC_WDL, manual scenario, corrupted inputs, E2E same-run HTTP/JSON/HTML and no second COM connection. Full old regression and Python 3.11/3.12 CI are mandatory. All changes stay in worker branch. **MERGE HOLD for A/B/C/D/E until full VS06**.

Primary regulation: https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf
ETABS distributed-load semantics: https://docs.csiamerica.com/help-files/etabs/Menus/Assign/Frame_Loads/Distributed_Load.htm
