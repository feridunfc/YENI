# VS05-D4 — Source Authority and Audit Reconciliation

**Disposition:** LOCAL PATCH / SOURCE AUTHORITY REVIEW. `COMMIT=HOLD`, `PUSH=HOLD`, `MERGE=HOLD`.
**Reference branch:** `work/vs05-normative-base-shear-drift-20261107` at `b4f6a9ea8ddd0224ab9109ca418f55768850e202`.
**Accepted main:** `895e6b5b55a2e133b34e199577940ec7cee20837` (VS04 PR #3).
**Regulatory status:** `FORMAL_COMPLIANCE=NOT_PROVEN` / `ENGINEERING_RELEASE=NOT_READY`.

## Audit disposition, item by item

| Claim | Classification | Technical basis |
|---|---|---|
| 94 candidate nodes / 140 edges; no authorized formal execution | CONFIRMED | D1 catalog validates the graph, but every node has execution authority `DENIED`. |
| ModelProfile and ComboBook are unapproved | CONFIRMED / P0 | D2 candidate model and combination contracts only check data identity and graph shapes. They cannot independently establish complete physical census, combo roles or approved design basis. |
| Analysis generation identity is unproven | CONFIRMED / P0 | Shared `run_id`, locked SapModel, same request and SHA-256 receipt do not prove that analysis mass/stiffness and all response results belong to the same independently certified epoch. |
| Envelope components are already being combined as a concurrent PMM vector | NOT CONFIRMED AS AN ACTIVE DEFECT; RISK REMAINS | D2 rejects nested SRSS/ENVELOPE for consumers requiring concurrent vectors. The 271 actual combination rows and response-spectrum modal result envelopes still require explicit reconciliation. D4 audits this boundary without emitting a design vector. |
| Unknown B2/B3 is silently interpreted as gammaE=0.80 | NOT CONFIRMED AS AN ACTIVE DEFECT; INPUT GAP CONFIRMED | VS05 numerical kernel requires explicit classifications of A1, B2 and B3. All three cannot be inferred from source-only A1 observations. Engineering approval remains blocked. |
| D3 Windows replay is missing | SUPERSEDED | 2026-11-07 local PowerShell evidence shows 283/283 tests and D3 replay for real `kompakt_b.EDB` receipt `RUN-f86e77b...`, with 267 frames, 4 upper stories, 271 raw combination rows and 10/10 `NOT_PROVEN` FCR. This is offline Windows replay, *not* a live D3 COM analysis. |
| VS05 has been integrated into one-button UI | FALSE | VS05 D1/D2/D3 run in offline tools. The accepted one-click application is still VS04. |
| Overall engineering release may proceed | FALSE | Production and engineering release remain NOT_READY. |

## New D4 source-bound functionality

1. Receipts first. A dedicated CLI reads the original run directory through `reporting.build_complete_report`, which replays the archived source and stage receipts. An exported JSON report is **not** accepted as proof of receipt integrity.
2. Case identity. Reads the exact ETABS `Load Case Definitions - Summary` and `Load Case Definitions - Response Spectrum` tables. Unique case names and GUIDs are checked; candidate RSX/U1 and RSY/U2 mappings are observations, never accepted design roles.
3. Full raw combination table observation. Decodes `Load Combination Definitions` row groups, first-row operator plus `None` continuation rows, exact Decimal coefficients, typed case versus combination dependencies, unknown references and nested cycles. Recognizes `Linear Add`, `Envelope`, `SRSS`, `Absolute Add` and `Range Add` as **source shapes**, not approved combination physics.
4. Non-concurrence guard. A SUM containing RSX/RSY or an envelope/SRSS at any nested depth is marked risky. **No** combination is promoted to signed concurrent P/M2/M3 design force; source provenance requires separately proven same member/case/step/station.
5. Mass source gate. Observes the VS04-F story/group/joint mass reconciliation and candidate mass, but keeps approved upper-building seismic `m_t`, basement boundary and semi-rigid diaphragm scope **NOT_PROVEN**.
6. Analysis-generation gate. Same-request and restored selection are logged separately from model/analysis epoch. A claimed `analysis_generation_proven=true` in a raw report is rejected; the actual independent analysis generation remains unknown.
7. D3/FCR provenance. Reuses D3 candidate facts and checks same source snapshot hash, same run ID and 100% candidate FCR accounting. All normative execution remains denied.
8. Output is an exclusive new D4 sidecar, not a rewrite of accepted VS04 receipts, `RunResult`, or UI. The audit has no live Windows COM calls.

## Safety and scope

This patch does **not** automatically approve ModelProfile, ComboBook, B2/B3 classifications, DD-2/DD-3 design spectra, the directional governing period, pre-beta modal `Vtx`, a design force vector, full equivalent base shear, story drift or engineering release. It also does not create an independent analysis generation certificate. It is a *diagnostic and proof-dependency* sprint, not a normative PASS sprint.

The source code is in `src/tbdy_next/vs05_d4_source_authority.py`; its receipt-only CLI is `tools/audit_vs05_d4_source_authority.py` and tests are `tests/test_vs05_d4_source_authority.py`.

## Local Windows replay — only after a clean working tree

In PowerShell, from the existing correct VS05 branch and repo root, after extracting new files from this ZIP:

```powershell
$python = ".\.venv\Scripts\python.exe"
& $python -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw "Regression failed" }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
& $python -m tools.audit_vs05_d4_source_authority `
  --receipts-root .receipts `
  --run-id RUN-f86e77b043d841b38bc9aec8b689bc8d `
  --catalog config/dag/tbdy_r1c_94_candidate.json `
  --out ".receipts/VS05/VS05_D4_AUTHORITY_$stamp.json"
if ($LASTEXITCODE -ne 0) { throw "D4 offline replay failed" }
```

Expected: same `run_id`, case and combination source census, mass candidate if the VS04-F observed component is present, and a new FCR-linked record with zero promoted normative checks. Any unexpected source shape fails or is reported as an unresolved blocker. Do not infer 15/15 or 271/271 approved combination semantics from printed source row counts.

## Final merge gate

`D4 TARGETED UNIT TESTS=16 PASS` (local Python 3.13); full VS05 test suite and D4 real Windows receipt replay **not executed here**. No Git commit, push, or merge performed. Owner must review the D4 sidecar and run the full suite; only then can a separate engineering acceptance decision be considered.
