# VS04-B — Bounded numerical source consistency (implementation candidate)

**Authority:** SOURCE_ONLY. No full code compliance and no independently
qualified analysis generation. Existing 8 VS01–VS03 checks are unchanged.
This stage does not make a ninth regulatory check; it produces five pure source
arithmetic/quantity components in a separate immutable receipt.

## Observed ETABS 23.2 fields (from 2026-11-07 Windows capture)

- Modal Periods And Frequencies: 100 rows; `Case`, `Mode`, `Period` (sec),
  `Frequency` (cyc/sec), `CircFreq` (rad/sec), `Eigenvalue` (rad2/sec2).
- Base Reactions: 14 rows; `OutputCase`, `CaseType`, `StepType`,
  `StepNumber`, `FX/FY/FZ` (kN), `MX/MY/MZ` (kN-m), `X/Y/Z` (m).
- Story Drifts: 79 rows; `Story`, `OutputCase`, `CaseType`,
  `StepType`, `StepNumber`, `Direction`, `Drift`, `Drift/`, `Label`,
  `X/Y/Z` (m). ETABS **did not supply affirmative units for Drift
  or Drift/**. A blank unit is retained as unknown engineering semantics.
- `StepLabel` was part of base/stories metadata but absent from the display
  projection; it is not fabricated as a row field.
- These are **source-shape evidence**, not proof that any particular RSX/RSY
  row exists or qualifies as the project-design earthquake case.
- The exact 193 raw rows and the actual row values are NOT in the repository;
  the original private VS04_RAW JSON must be inspected for live numerical
  acceptance.

## Pure math vs regulatory scope

```text
Modal:  f = 1/T; omega = 2*pi*f; eigenvalue = omega**2
Base:   independently qualified FX or FY source component, not Vt/VtE
Drift:  Drift * Drift/ = 1 (display scalar identity only, if parsable)
```

Modal identities use explicit observed units, finite positive quantities, exact
case/mode IDs, no duplicate/omitted modes and 1% tolerance for formatted
source values. That tolerance is a screening criterion, not a precision proof.
If displayed values round too coarsely, the mode is NOT_PROVEN rather than
silently repaired. No positive source consistency can be inferred if the
selected modal-case rows are absent.

Base reactions bind by exact case and `LinRespSpec + Max` and require **one**
row per requested X/Y case. Missing/ambiguous rows, wrong field units or
nonfinite values block the source fact. The six displayed components are not
assumed simultaneous, and sign/magnitude are not used as a signed design
vector. No auto-scaling of response-spectrum results or minimum-base-shear
TBDY rule is performed.

Story drifts bind by exact story/case/direction/step/label/coordinate grain.
Only finite nonzero positive `Drift` and `Drift/` scalars with a consistent
reciprocal product may receive SOURCE_ARITHMETIC_OBSERVED. Duplicate identities,
unrecognized representations or blank required identities become NOT_PROVEN.
**This cannot determine physical drift, relative drift ratio, effective drift,
lambda, R/I, or code compliance; no story-population completeness is proven.**

## Execution and rollback boundary

VS04 uses the **existing single Windows COM owner/session and read-only
capture**, restores the original display selection and appends source-only
receipts `vs04-schema` and `vs04-numerics` under the same `run_id`.
The local JSON/HTML exporter compares the two receipts with re-evaluations
from the exact archived source. A new VS04 run records
`numeric_stage_required=true` in the sealed input; missing or altered
numeric receipts block export. Pre-existing VS03 and legacy VS04 reports
remain readable if their original receipts are valid.

No source data, project paths or raw ETABS tables are committed to GitHub.

## Acceptance checklist / live dependencies

| Item | State |
|---|---|
| VS04 source acquisition (Windows) | OBSERVED 3/3; 193 rows |
| Source-only arithmetic unit tests | CI REQUIRED |
| Five arithmetic/source components wired to UI and JSON/HTML | CANDIDATE |
| Real 193-row numerical replay | NOT_PROVEN until local VS04_RAW supplied |
| Source-to-analysis generation qualification | NOT_PROVEN |
| R/D, spectrum case-role, scaling, mass, minimum base shear | NOT_PROVEN |
| TBDY effective story drift / λ / R/I / applicability | NOT_PROVEN |
| Formal engineering compliance / release | NOT_READY |

**Supervisor must not mark VS04 LIVE NUMERICAL ACCEPTED solely because
synthetic tests and CI pass**. Full VS04 normative closure requires the
actual raw source plus approved project analysis basis and an independent
calculation oracle. Never merge directly to main without separate acceptance.
