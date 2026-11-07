# VS04 — ETABS analysis source schema acquisition (candidate)

**Base**: VS03 merged `main` at `a53f29f65f62b7e15911283aa4e4b6c750d8d0f7`.  
**Development branch**: `work/vs04-analysis-source-schema-20261107`.  
**Authority**: SOURCE OBSERVATION ONLY. No new regulatory checks, no engineering PASS; release `NOT_READY`.

## Objective

Collect the **actual ETABS 23.2 table field metadata and full display rows** for:

1. `Modal Periods And Frequencies`
2. `Base Reactions`
3. `Story Drifts`

The previously accepted eight VS01–VS03 checks are unchanged. VS04 is a distinct source stage, not a ninth fabricated check. No field name, ETABS load case, code formula, units or result freshness is inferred from a label.

## Windows live procedure

Start ETABS 23.2 with an already analyzed, locked model. Run from this repository branch:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install comtypes
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m tbdy_next.cli serve --host 127.0.0.1 --port 8765 --out .receipts
```

Open `http://127.0.0.1:8765` and select **VS04 · 3 analiz tablosunun şemasını al**. This attaches to the already-open ETABS session only when clicked. It uses the selected modal case from the UI and the **unapproved capture candidates** `RSX` and `RSY`, both previously observed in VS03; these are not universal names or reviewed spectrum roles.

The capture reads `GetAllFieldsInTable` (version, field keys, field names, descriptions, units, importable flags) and `GetTableForDisplayArray` (full field list and rows) for all three tables. It reads with temporarily selected display cases and **restores and verifies original display selection**. It never calls RunAnalysis, StartDesign, Save, SetPresentUnits or alters properties. A failed restore rejects the whole capture.

Inspect the **VS04 Analiz kaynakları** area and export **Tam JSON dışa aktar** for the selected run. Full raw rows plus observed schema are in `source_snapshot.analysis_sources`; the printable HTML contains the schema census and full three raw tables. All artifacts are local, with source and receipt SHA-256. Do not commit private models or raw captures to GitHub.

## Exact status contract

`SOURCE_SCHEMA_CAPTURED_PENDING_REVIEW`: three tables have structurally coherent observed fields, metadata and nonempty complete row arrays, and temporary display selection was restored. **This is not a reviewed field schema or qualified calculation input.**

`SOURCE_SCHEMA_INCOMPLETE`: missing table, failed read, invalid fields/metadata, row-count conflict, unstable units, or capture-selection/lineage proof mismatch. Individual tables report `NOT_PROVEN` with reason codes.  
`SOURCE_UNAVAILABLE`: no valid VS04 capture present.

Every outcome retains:

```text
formal_compliance = NOT_PROVEN
engineering_release = NOT_READY
analysis_generation_proven = false
numeric_checks_executed = 0
```

Real `GetPresentUnits() == 6` before and after is required for this bounded source stage. Field-specific units are recorded unmodified. They are **not assumed** from the present-units enum, and no conversions or seismic formulas are authorized by capture alone.

## Gate to numerical controls

**VS04-A live source acceptance** requires observed ETABS 23.2 result: the exact three table schemas (all field keys/units), complete source rows, selected case list, meaningful row identities, a stable model/source fingerprint, and accepted per-table source interpretation. Separate the three table types; modal period/frequency data cannot substitute for modal participating mass, and base reactions must not be mistaken for the minimum base-shear code requirement.

**VS04-B numerical engineering** follows only after explicit review:

- modal period/frequency consistency by identical case/mode identities, with explicit unit proof;
- story drift `Δ/h` or already-reported ratio semantics reconciled to units, story heights, directions, and selected analysis cases; then TBDY effective drift needs its own R/I/λ, DD levels and applicable rule context;
- base `FX/FY` magnitudes with force units, signed axis direction, case step and output scaling; then TBDY base shear limit needs full mass/spectrum/R/D/basis and specific spectrum combination roles, not an arbitrary max or envelope;
- approve any nonlinear/spectrum output interpretation before any vector arithmetic; generation/analysis-result lineage qualification is separate from model locked status.

The next worker must not promote this diagnostic stage into `SCHEMA_VERIFIED`, `PASS`, or a ninth check without approved real source evidence and an independently verified numerical oracle.

## Engineering acceptance ledger

| Gate | Status |
|---|---|
| Existing VS03 eight checks | ACCEPTED on main, must remain unchanged |
| VS04 capture/metadata/restore implementation | CANDIDATE (CI + Windows tests required) |
| VS04 actual live three-table schema evidence | NOT_PROVEN (Windows ETABS required) |
| VS04 source field role/unit review | HOLD |
| VS04 period / drift / base shear engineering rules | NOT_IMPLEMENTED |
| Full TBDY/TS500 engineering release | NOT_READY |

**Repository governance**: no changes to `main`; branch only. No merge until supervisor accepts live evidence and regression results.
