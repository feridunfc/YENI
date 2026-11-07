# VS04-J — Conditional base-shear source screening (engineering firewall)

## Objective and evidence boundary

After VS04-I source arithmetic was observed at 26/26 function knots,
200/200 modal accelerations and 201/201 Windows tests, this sprint
adds a bounded handoff to the TBDY 2018 minimum equivalent-base-shear
term. It does **not** manufacture dominant modal period, design spectrum
authorization, a basement exclusion or a gamma_E decision.

Exact input files:

- VS04-E `VS04E_BASIS_PROBE_*.json` (mass, spectrum definition,
  Ritz and model story source rows)
- VS04-G `VS04G_DIAPHRAGM_MODAL_*.json` (RSX/RSY modal output)
- VS04-D `VS04_REPLAY_LATEST.json` (100 modal period/frequency
  source checks and separate X/Y Base Reactions components)

`src/tbdy_next/base_shear_screening.py` **revalidates** the source
contracts. It does not trust a hand-written success marker in a
standalone JSON; it reruns the earlier VS04-F and VS04-I calculations
against the full selected source rows. Input provenance SHA-256 hashes
are written by the offline CLI.

## Exact source-only quantity

TBDY Eq. (4.19) contains the lower-bound term:

    V_min = 0.04 m_t I S_DS g

with m_t (kg), I dimensionless, S_DS dimensionless and g (m/s²);
the result is converted to kN.

This sprint calculates that term only as a **conditional source-screening
scalar** using the *candidate* total from the current mass-source
inventory, observed spectral-function header `I,SDS` and standard
gravity `g = 9.80665 m/s²`.

Real observed candidates from the 2026-11-07 source set:

- Group=All, by-story and 6151 assembled-node X/Y mass reconciled:
  `m_candidate = 4380.4916 ton = 4,380,491.6 kg`.
- `I_candidate = 1.5`, `SDS_candidate = 0.52578`
  from `RESP_YATAY`. The ETABS field metadata anomalously displays
  `I` unit as `sec`; this is not a formal I approval.
- Conditional floor from those values:
  `V_min,conditional = 1355.185792361929752 kN`.
- Separate *displayed* response-spectrum base components:
  `RSX FX = 3493.6901 kN`, `RSY FY = 3416.597 kN`.
  These are not confirmed pre-beta `V_tx`, nor a concurrent signed vector.

Do **not** compare the RSX/RSY numbers directly against this floor and
declare code PASS. Eq. (4.19) also requires independently qualified
`S_aR(T_p)` and full `V_tE`. Eq. (4.31) requires
`gamma_E` from *complete* A1/B2/B3 classification, pre-beta modal
`V_tx`, applied case scales and explicit basement boundary. Source
headers alone cannot provide those authorities.

The software returns `CONDITIONAL_MINIMUM_TERM_SOURCE_SCREENING` and
sets `full_equivalent_base_shear_kn` and both beta factors to null.
Every normative status remains `NOT_PROVEN`; engineering release
remains `NOT_READY`.

## Negative design conditions

The screening is suppressed when any of these is missing or invalid:
- assembled-joint/group/story mass inconsistency or duplicate source
- exact RSX/RSY spectrum-function/modal direction binding
- 26-knot analytic function and 200-modal source calculation
- VS04-D Base Reactions case/type/direction identity
- missing/NaN/invalid source units, modal period, spectrum value, or
  non-concurrent source sematics

The suite checks multiple tamper conditions and the eight-check
registry identity without adding any ninth regulatory check.

## Run offline on Windows

```powershell
Set-Location "C:\Users\efeya\PycharmProjects\YENI_VS04"

$basis = (Get-ChildItem ".receipts\VS04\VS04E_BASIS_PROBE_*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1).FullName
$modal = (Get-ChildItem ".receipts\VS04\VS04G_DIAPHRAGM_MODAL_*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1).FullName
$prior = (Get-Item ".receipts\VS04\VS04_REPLAY_LATEST.json").FullName
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

.\.venv\Scripts\python.exe tools\review_vs04j_base_shear.py `
    --basis "$basis" --modal-info "$modal" --prior-modal "$prior" `
    --out ".receipts\VS04\VS04J_SCREENING_$stamp.json"
```

Source files are never changed. The output contains the three input
SHA-256 values, no original analysis arrays, independent derived
screening values and explicit missing-authority flags.

## Normative acceptance and release gate

A full calculation can be built only after acquiring:
1. Immutable provenance linking a single model and analysis generation
   to modal, mass and base-reaction data
2. Physical basement / upper-building seismic-mass scope, and
   ground-motion DD-2 and code parameter approval
3. An independently qualified `T_p,X` and `T_p,Y`, and the applicable
   elastic/reduced acceleration `S_aR(T_p)`
4. A1, B2 and B3 irregularity status and correct `gamma_E`
5. Pre-beta response-spectrum base shears and actual spectral scaling,
   including the state of case and combination multipliers

VS04-J is **not** completion of TBDY Chapter 4 design verification.

`ENGINEERING_RELEASE=NOT_READY`, `FORMAL_COMPLIANCE=NOT_PROVEN`,
`MERGE=HOLD`; accepted VS03 controls and `main` unchanged.
