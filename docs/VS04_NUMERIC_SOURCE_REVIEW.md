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
Drift:  observed Drift × denominator(Drift/) ≈ 1 with displayed precision
        e.g. Drift/ = "1/1289" means displayed 1/N, N=1289 (not 1/1289
        as an arithmetic multiplier).
```

Modal identities use explicit observed units, finite positive quantities,
exact case/mode IDs and no duplicate/omitted modes. After real replay,
modes 83-100 included 14 conflicts with the obsolete fixed 1% tolerance
because ETABS rendered very short periods to three decimal places (e.g.,
T=0.005 s and f=221.99 Hz at mode 99). The revised comparator uses
**half of the exact displayed decimal quantum** to construct precision
intervals for T, f, omega and eigenvalue. It requires the admissible frequency
intervals from all four observations to intersect. This is not a blanket
tolerance increase: contradictory f, omega and eigen remain NOT_PROVEN.
The actual 14 Eigenvalue cells were not provided in the pasted diagnostic,
so their live replay conclusion remains PENDING.

Base reactions bind by exact case and `LinRespSpec + Max` and require **one**
row per requested X/Y case. Missing/ambiguous rows, wrong field units or
nonfinite values block the source fact. The six displayed components are not
assumed simultaneous, and sign/magnitude are not used as a signed design
vector. No auto-scaling of response-spectrum results or minimum-base-shear
TBDY rule is performed.

Story drifts bind by exact story/case/direction/step/label/coordinate grain.
Actual ETABS 23.2 `Drift/` cells displayed `1/1289`, `1/1255`,
`1/1963` (X) and `1/836`, `1/848`, `1/2587` (Y), rather than plain
floating-point denominators. The parser accepts this **exact unity-over-
positive-integer syntax**, compares `1/N` to the rounding interval of the
observed positive `Drift`, and also preserves the previous numeric denominator
representation. Arbitrary fractions, invalid/zero denominators, duplicate
identities, and mismatching rounded values become NOT_PROVEN. The textual
representation does not itself prove the physical meaning or normative units
of the ETABS field.
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
| First actual RAW replay (previous algorithm) | 2/5 components; 14 modal rows rejected and 6 Drift/ fields could not parse |
| Corrected RAW replay | PENDING; local VS04_RAW is required again |
| Source-to-analysis generation qualification | NOT_PROVEN |
| R/D, spectrum case-role, scaling, mass, minimum base shear | NOT_PROVEN |
| TBDY effective story drift / λ / R/I / applicability | NOT_PROVEN |
| Formal engineering compliance / release | NOT_READY |

**Supervisor must not mark VS04 LIVE NUMERICAL ACCEPTED solely because
synthetic tests and CI pass**. Full VS04 normative closure requires the
actual raw source plus approved project analysis basis and an independent
calculation oracle. Never merge directly to main without separate acceptance.
