# VS05-ARCH-D3 — Archived ETABS Source → Candidate Facts → Plan → FCR

## Role

Continue the owner-approved source-driven engineering architecture without
refactoring VS04 or asserting a complete real-building normative pass.

**Run boundary:** `tools/audit_vs05_archived_run.py` calls
`build_complete_report(receipts_root, run_id)`, which independently
recalculates the accepted VS04 source/receipt chain. Only after that
successful verification does D3 derive candidate typed source facts.
A bare previously exported JSON file is NOT accepted as an equivalent
source/receipt verification.

The extension writes an exclusive **sidecar**, carrying the same
`run_id` but never overwriting original `input.source`,
original VS04 receipts, the current single-button UI, or its historical
JSON/HTML contract.

## Exact observed source rows (kompakt_b.EDB)

Candidate provenance observed in earlier live VS04 report:

- ETABS 23.2 / present unit enum 6, kN-m-C
- Story Definitions: four tower T1 story levels; base row BSElev = -5.15m
- FRAME_ASSIGNMENTS: 294 objects in prior live report;
  87 column, 180 beam and 27 Null frame types.
- COLUMN_CONNECTIVITY: 87 frame I/J object IDs.
- BEAM_CONNECTIVITY: 180 frame I/J object IDs.
- Response Spectrum cases RSX U1 and RSY U2, Modal parent.
- Load Case Definitions - Summary: 15 case source rows.
- Load Combination Definitions: 271 **raw** rows, not proven full
  nested ComboBook semantics. No concurrent design vector is compiled.

These numbers are historical observed live values, NOT hardcoded
acceptance counts in D3; future runs are compiled from actual receipts.
D3 stores the raw non-column/beam type count as a separate scope gap.
The four story labels are candidates only; deriving their elevations
by reversing ETABS top-to-bottom story order is unapproved structural
topology until independently verified. Unknown Frame/Area/Wall members
must not be silently counted as verified or discarded.

## D3 typed compile

`src/tbdy_next/archived_source_bridge.py` validates the exact source
schemas and field-unit metadata, then:

1. Uses Tower Base and Story Definition rows to create the candidate
   per-story height/elevation identities.
2. Reconciles frame assignments with unique Column/Beam I/J connectivity
   by story and UniqueName. Unknown story, missing/duplicate Frame,
   mismatched Type, identical I/J, changing units → reject.
3. Compiles an **incomplete** candidate physical member list (only
   observed column/beam connectivity). The absence of physical wall,
   Area, Null frame position and full analysis mesh remains an explicit
   source gap; no completeness claim.
4. Creates a case-only ComboBook from genuine case name/GUID and selected
   RSX/RSY direction. The 271+ raw combination terms are observed but
   NOT promoted to typed nested combination operators or concurrent
   signed design-demand vectors.
5. Runs the D2 `compile_limited_source_candidates` for
   two directional BASE_SHEAR instances plus two STORY_DRIFT instances
   per candidate upper story (including a story with no captured vertical
   members).
6. Freezes the D1 plan ID and runs fail-closed FCR. Every candidate
   outcome remains NOT_PROVEN. No source-asserted PASS is accepted.

The result is a reduced candidate source trace and FCR, not a second
production run or a finished norm-compliance report.

## Windows offline acceptance (no live COM)

From original YENI working directory, after acquiring D3 branch:

```powershell
$python = ".\.venv\Scripts\python.exe"
$stamp = Get-Date -Format yyyyMMdd_HHmmss

& $python tools\audit_vs05_archived_run.py `
  --receipts-root .receipts `
  --run-id RUN-f86e77b043d841b38bc9aec8b689bc8d `
  --catalog config\dag\tbdy_r1c_94_candidate.json `
  --out ".receipts\VS05\VS05_D3_FCR_$stamp.json"

if ($LASTEXITCODE -ne 0) { throw "ARCH-D3 replay failed" }
```

The user-supplied run_id is historical ETABS evidence; the operator
can select any available actual VS04 live run with its complete source
receipt directory. This script does not trigger or modify ETABS.

## Scope and acceptance limits

- D3 source-backed candidate CheckInstance inventory is NOT the complete
  68-check-node / whole-model mandatory denominator.
- D3 does not independently approve the physical model, AnalysisGeneration,
  actual DD2/DD3 design spectra or unique ETABS model/case generation.
- D3 does not execute the directional VtE/beta and effective drift
  normative kernels on real-building data.
- A FCR result with expected=N, reconciled=N and NOT_PROVEN=N is a
  truthful completeness statement for that **candidate denominator**;
  it is not a building-wide satisfactory assessment.
- The accepted VS04 eight existing numerical checks, receipt formats,
  live UI and previously exported JSON/HTML remain unchanged.

Next: verify D3 on actual Windows receipt source, then link a
**versioned**, authorized model/ComboBook/analysis generation and
typed displacement evidence to bounded normative checks, and only
later wire a sealed whole-model RunResult to the single-button UI.

ENGINEERING_RELEASE=NOT_READY.
FORMAL_COMPLIANCE=NOT_PROVEN.
VS05 MERGE=HOLD.
