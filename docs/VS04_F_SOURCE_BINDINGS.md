# VS04-F — Observed ETABS model-source binding / controlled engineering ledger

**Scope:** VS04-D source arithmetic is accepted; VS04-E formula kernels and
normative readiness inventory have CI proof. VS04-F is a **source-contract
reconciliation** against the real 2026-11-07 Windows ETABS
`VS04E_BASIS_PROBE` JSON. It never changes the established 8 check registry.

## Source facts grounded in the specimen

Exactly observed ETABS keys, not guessed aliases:

| ETABS key | Observed engineering candidates | Critical qualification |
|---|---|---|
| `Mass Source Definition` | Default mass-source ID; self mass; load-pattern factors | Not yet authorized as actual TBDY mt |
| `Assembled Joint Masses` | 6151 analysis-element rows; UX/UY/UZ mass in ton | Must sum and reconcile against story/group mass; internal elements are not physical object counts |
| `Mass Summary by Group` | `All` mass in ton | Reconcile with joint and story, not self weight |
| `Mass Summary by Story` | Full story-direction mass census in ton | Physical/basement inclusion still needs sign-off |
| `Mass Summary by Diaphragm` | Diaphragm masses, units ton | All observed X/Y values were zero; reason not established |
| `Load Case Definitions - Response Spectrum` | RSX/RSY; U1/U2; Global angle 0; `TransAccSF` in m/s² | One load case does not prove a valid TBDY design action |
| `Functions - Response Spectrum - TSC-2018` | Named 26-point function and header R/D/I/SD parameters | Exact design spectrum DD level and period-dependent role not independently certified |
| `Modal Case Definitions - Ritz` | Ritz modal source, excitation UX/UY, target ratio and mode count | Selected modal case may use P-Delta stiffness; still requires generation proof |
| `Story Definitions` | Story labels/heights in m | Physical story inventory / roof applicability and basement boundary need review |
| `Tower and Base Story Definitions` | Tower/base elevation in m | Reconcile base+story cumulative elevations |
| `Response Spectrum Modal Info` | Metadata available but table API returns ret code 1 | `CAPTURE_ERROR`, not an empty successful result |

Cross-checks already supported by the uploaded actual records:

- Total story directional mass **4380.4916 ton** X/Y, equals the **Group=All**
  directional mass. This alone is NOT a qualified total seismic mass.
  Separate **6151 joint masses** are left for the VS04-F replay calculation;
  their sum must independently agree within observed printed precision.
- Three diaphragm mass summaries all have `MassX=MassY=0`, despite
  nonzero story mass. The root cause is unknown. ETABS diaphragm eccentricity
  is applied only where diaphragm constraints are present, per CSI manuals.
  Therefore the 5% spectrum accidental eccentricity is **NOT_PROVEN APPLIED**.
- RSX/RSY are response-spectrum definitions, each using
  `RESP_YATAY`, `Modal`, `CQC`, `SRSS`, `Angle=0` and
  `TransAccSF=10 m/s²`. These are the **defined case coefficients**, not
  proof of final scaled seismic effects.
- Function header values include `R=7`, `D=2.5`, `I=1.5`, and
  `SDS=0.52578`; `Ss*Fs = SDS`, `S1*F1 = SD1` can be checked exactly.
  Note source `I` metadata anomalously reports `sec`; use the parameter
  semantics but do not certify metadata correctness.
- The three main drift/result stories observed in VS04-D are different from
  the four `Story Definitions` rows. Verify top story applicability, zero
  mass, response population and basement boundary rather than dropping the
  unmatched story.

## Source compiler scope

`tbdy_next.basis_linkage.review_basis_linkage()` produces four
**source** components:

1. `SEISMIC_MASS_RECONCILIATION`: exact `MsSrc1` source, self/load
   definition and coefficients; story/group/joint totals in X and Y;
   separate diaphragm evidence warning
2. `RESPONSE_SPECTRUM_CASE_BINDINGS`: exact case names and U1/U2 directions,
   source and modal case identity, response-spectrum function, damping,
   field units and parameters; no design scale approval
3. `PHYSICAL_STORY_GEOMETRY`: unit-checked base elevation, story labels,
   heights and positive cumulative differences
4. `SPECTRUM_MODAL_OUTPUT`: source failure retained as a hard
   `NOT_PROVEN` while the read has ret code 1

`SOURCE_CONTRACT_OBSERVED_UNAPPROVED` means *all defined source comparisons
within that component passed*, never code compliance. A missing or inconsistent
source field fails closed. **NO regression test fixture and NO successful
source-compiler output grants engineering release.**

In particular, the following still require explicit proof before normative
calculation:

- original full model and immutable analysis generation bound to both
  the VS04-D and VS04-E capture sessions
- design mass boundaries: foundation/soil/base/story, source duplication, top
  story and diaphragm assignment
- DD-2 and DD-3 spectra at approved directional governing periods, including
  actual scale and `R_a(T)`/`R/I` interpretations
- whether any response-spectrum scaling according to TBDY Eq (4.31) was
  already applied to the analyzed model or to downstream combinations
- B2/B3 irregularities, rigid-wall basement classification, material and
  fill-wall joint applicability
- physical-node displacements, reduced relative story drift, full story
  population and same-case identity (ETABS Story Drifts display alone is
  insufficient)

## Local offline replay — no ETABS connection

In the existing `YENI_VS04` Windows folder:

```powershell
$probe = (Get-ChildItem '.receipts\VS04\VS04E_BASIS_PROBE_*.json' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
.\.venv\Scripts\python.exe tools\review_vs04f_basis.py `
   --input "$probe" `
   --out ".receipts\VS04\VS04F_BASIS_REVIEW.json"
```

This preserves the private source JSON and writes a reduced review file
containing the original source SHA-256, counts, approved **source-only**
comparisons and explicit normative blockers. The output excludes the full
6151 joint rows and full load-combination table. On rerun, choose a distinct
output filename (the script refuses to overwrite).

**Disposition for this stage:** source code and offline unit tests may be
accepted after CI; direct live/model authorization still needs independent
engineering review and additional source provenance.

## External source references

- CSI ETABS response-spectrum case, scaling, modal and eccentricity
  definitions:
  https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Response_Spectrum.htm
- CSI ETABS spectrum function values are normalized; the acceleration
  unit belongs to case scale factor:
  https://docs.csiamerica.com/help-files/etabs/Menus/Define/Functions/Response_Spectrum_Functions/Response_Spectrum_Functions.htm
- TBDY 2018 (AFAD primary text):
  https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf
