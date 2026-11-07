# VS04-E — Normative input dependency closure and ETABS basis probe

**Scope**: The preceding VS04-D source arithmetic is accepted. This stage
builds deterministic TBDY Chapter 4 calculation kernels and an explicit source
dependency graph. **It does not increase the eight accepted/check-registry
items, it does not authorize engineering release, and it does not claim that
an ETABS output row itself is an approved regulatory demand.**

## Verified normative relations

Source of rules (TBDY 2018, Chapter 4, official publication):
https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf

- §4.7.1.1, Eq (4.19): `VtE = max(mt * SaR(Tp), 0.04 * mt * I * SDS * g)`.
  Kernel input units: `mt` kg, `SaR` m/s², `g` m/s², output kN.
  `mt` is the actual approved **seismic** mass, not gross building mass
  inferred from selfweight.
- §4.8.4.1, Eq (4.31): `beta_tE = max(1, gamma_E * VtE / Vtx)`.
  `gamma_E=0.90` if A1/B2/B3 exists, otherwise `0.80`. All applicable
  irregularities must be resolved before `0.80` can be selected, including
  B2 and B3; VS03 A1-only source classification cannot decide gamma.
  Basement upper/lower-part boundary must be qualified separately.
- §4.9.1.1–4, Eq (4.32–34):
  `Delta_i = u_i - u_(i-1)`,
  `delta_i = (R/I) * Delta_i`,
  `lambda * delta_i,max/h_i <= 0.008*kappa` or `0.016*kappa`.
  The `0.016` path requires the flexible joint/wall-capacity evidence
  in §4.9.1.3(b). Concrete `kappa=1`, steel `kappa=0.5`; special
  one-storey steel exception not automatically applied.
- `lambda = Sae_DD3(Tp) / Sae_DD2(Tp)`, evaluated at the **same qualified
  direction-specific dominant Tp**. Neither arbitrary case naming nor
  `Drift` display field is sufficient to prove the required source.
  X and Y need separate parameter lineage.

These kernels return `FORMULA_ONLY_UNQUALIFIED` and conditional numeric
values. They **never** label the model PASS/FAIL. Applying their outputs as
actual code results requires independent proof of every input's physical
meaning, dimensions, model generation, selected analysis case and scaling.

## Canonical source dependency graph

```mermaid
flowchart TD
    M[ETABS model / analysis generation proof] --> C[Approved case and story identity]
    C --> B[RSX/RSY spectrum load definition and scaling state]
    C --> H[Story geometry, h_i and physical node association]
    M --> Q[Qualified seismic mass / story masses]
    Q --> VE[Eq 4.19 VtE]
    P[Approved Tp and DD2 spectrum / R(T) / I] --> VE
    B --> VTX[Unscaled Vtx before beta scaling]
    IR[A1+B2+B3 full irregularity inventory] --> GAMMA[gamma E 0.90/0.80]
    VE --> SCALE[Eq 4.31 beta]
    VTX --> SCALE
    GAMMA --> SCALE
    H --> DELTA[Reduced physical Delta_i]
    B --> DELTA
    P --> LAMBDA[DD3/DD2 spectral acceleration at same Tp]
    DELTA --> DRIFT[Eq 4.33/4.34]
    LAMBDA --> DRIFT
    WALL[Material, connection and wall-capacity proof] --> DRIFT
    SCALE --> R[Scoped engineering report]
    DRIFT --> R
```

The five **precompiled expected instances** are:
`modal_case_lineage`, `base_shear_X`, `base_shear_Y`,
`effective_drift_X`, `effective_drift_Y`. If inputs are absent, each
remains `NOT_PROVEN` with a complete missing-evidence list. No
`check_registry` mutation is permitted by this source inventory alone.

### Existing VS04-D real sample facts (not yet design-authorized)

- RSX `|FX| = 3493.6901 kN`; RSY `|FY| = 3416.597 kN`.
- `Story Drifts` display at three X and three Y stories is internally
  reciprocal-consistent, but `Drift` and `Drift/` field units are blank.
- The full original `VS04_RAW` remains on the user's Windows workstation;
  the uploaded replay omits raw sources. The reported SHA-256 is a source
  fingerprint, not independent model/analysis-generation certification.

**Do not substitute these numbers for `Vtx` or `Delta_i/h_i` in the
formal regulatory rule without explicit source qualification.**

## New read-only Windows ETABS targeted probe

From `C:\Users\efeya\PycharmProjects\YENI_VS04`, with ETABS 23.2
open and the *existing* model analyzed and locked:

```powershell
.\.venv\Scripts\python.exe tools\probe_vs04e_basis_windows.py `
    --out ".receipts\VS04\VS04E_BASIS_PROBE_20261107.json" `
    --max-tables 24
```

It reads `DatabaseTables.GetAvailableTables` and records **all exact keys**
and their names/import-type metadata. It marks candidate categories (story
geometry, mass, case definitions, spectrum functions and combinations) by
keyword; **no semantic mapping is automatically approved**. It attempts
complete raw row capture plus `GetAllFieldsInTable` metadata for up to
24 candidate tables and lists any overflow keys unambiguously.

It **never** calls `SetPresentUnits`, `SetLoadCasesSelectedForDisplay`,
`RunAnalysis`, `StartDesign`, `File.Save`, or writes model properties.
The entire inventory is stored locally. The tool checks that display-case
selection and present-units state remain unchanged, and refuses to overwrite
an existing output.

### Local replay with new readiness ledger

```powershell
$raw = (Get-ChildItem ".receipts\VS04\VS04_RAW_*.json" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1).FullName
.\.venv\Scripts\python.exe tools\replay_vs04_raw.py `
    --input $raw `
    --out ".receipts\VS04\VS04E_REPLAY.json"
```

The output includes `normative_readiness`, a five-instance missing-evidence
ledger, after source arithmetic. The eight prior check results stay intact.
New VS04 web captures also seal a `vs04-readiness` receipt under the same
`run_id` and re-verify it on report export. Replaying old original
VS04-D captures remains backward-compatible.

**Next acceptance gate:** real Windows `VS04E_BASIS_PROBE_....json`
evidence and its fields/cases/units must be reviewed. Unknown case format,
source empty table, missing spectral function, unqualified layer/basement
or model generation all remain `NOT_PROVEN`.

**Supervisor scope:** VS04-E can be accepted as an *offline formula and
dependency module* upon successful tests. Full normative engineering acceptance,
live source binding, and merge require separate evidence and review.
