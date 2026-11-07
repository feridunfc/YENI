# VS04-H — Diaphragm assignments and spectrum-modal source reconciliation

**Authority:** source-only, offline. No ETABS calls or model mutations, no
normative code-check promotions. Preserves the eight VS01–VS03 checks, the
VS04-D and VS04-F evidence, and `main`.

## Real Windows evidence, 2026-11-07

VS04-G raw file `VS04G_DIAPHRAGM_MODAL_20261107_150232.json`;
SHA-256 recorded by the source probe:
`6957010d3c7cd867d1d2520aa51fc7d079f6977de1cb5c9f9f0771066cd4ad75`.

- All 5 **defined** diaphragms (D1–D5) are `Semi-Rigid`.
- Area assignment table: 91 objects. 31 D3 at +9.00, 25 D2 at
  +4.50, 32 D1 at +0.00; 3 `None` (one +0.00, two Base).
- Joint assignment table: 325 point objects. **261 direct** (78 D3 at
  +9.00, 96 D2 at +4.50, 87 D1 at +0.00);
  **64 `From Shell Object`** (one +4.50, twelve +0.00, 51 Base).
  `From Shell Object` is not another directly named diaphragm. Its
  effective analysis assignments require separate shell-to-mesh proof.
- D4/D5: defined but unassigned **within the two captured assignment
  tables**. This cannot establish absence of other object/analysis paths.
- `Mass Summary by Diaphragm`: 3 rows (D1–D3), each X/Y mass=0.
  This is **not** evidence that no semi-rigid diaphragm is assigned.
  Further interpretation of the mass-reporting semantics and analysis
  constraint effects remains required.
- `Response Spectrum Modal Info` under **no case selected**:
  `ETABS ret_code=1`, an error, not a successful zero-row table.
- The same table after temporarily selecting exactly RSX and RSY:
  **200 rows**, 100 modes (1..100) for each, `Modal` case and
  modal damping `0.05`. RSX has positive U1 spectral accelerations
  and zero U2/U3 excitation; RSY has positive U2 and zero U1/U3.
  Active-direction spectral acceleration values match per mode
  (RSX U1Acc = RSY U2Acc), while active modal amplitudes can have
  different signs and magnitudes. Do not combine signed amplitudes to
  produce a concurrent force vector.
- Prior VS04-D 100 modal periods and the RSX 100 periods printed
  by VS04-G are an exact display match. This is cross-capture
  **display identity**, not an immutable analysis-generation proof.

## Spectral interpolation finding — must not be falsely accepted

The 26-point `RESP_YATAY` function and the `TransAccSF=10 m/s²`
parameters were available from VS04-E. We independently tried a
**candidate-only straight-line interpolation** of the displayed 26
points at the **rounded** `Period` values. Including displayed-period
rounding intervals, only 136 of 200 modal rows were bounded by that
particular reconstruction. **64 rows were not explained by the simple
candidate formula**, and this is NOT a verdict that ETABS analysis is
wrong. Possible reasons include the TSC-2018 analytic function
generated between the sparse display points, internal modal-period
precision, or analysis scaling/damping behaviors.

`SOURCE_CONTRACT_OBSERVED_UNAPPROVED` confirms source identity and
population only. A production numerical spectrum oracle must explicitly
derive the *actual function generation semantics*, norm-specific
spectral ordinates, modal period precision and case scale. **Do not
relax an absolute or relative tolerance simply to make 200/200 PASS.**

Official CSI ETABS response-spectrum case and normalized function:
- https://docs.csiamerica.com/help-files/etabs/Menus/Define/Functions/Response_Spectrum_Functions/Response_Spectrum_Functions.htm
- https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Response_Spectrum.htm
- https://docs.csiamerica.com/help-files/etabs/Menus/Define/Diaphragms.htm

## Source compiler and typed gates

`src/tbdy_next/diaphragm_linkage.py` compiles four components:

1. `DIAPHRAGM_DEFINITIONS`: nonduplicate names and GUIDs, recognized
   `Semi-Rigid` vs `Rigid`, source field/row count.
2. `AREA_DIAPHRAGM_ASSIGNMENTS`: unique object identities, defined
   diaphragm references and explicit `None` counts by story.
3. `JOINT_DIAPHRAGM_ASSIGNMENTS`: direct vs `From Shell Object` values
   distinctly counted, no invented inherited effective constraint.
4. `SPECTRUM_MODAL_RSXY_SOURCE`: exact pair of cases, 100 modes each,
   selected-case output, modal damping, zero inactive accelerations,
   identical modal periods and equal active-direction acceleration
   source for the two identical case-function definitions. Optional
   exact display-period comparison with the earlier VS04-D replay.

Each item is either `SOURCE_CONTRACT_OBSERVED_UNAPPROVED` or
`NOT_PROVEN`. The 4/5 original VS04-G read success count is retained
separately; an original-selection error does not disappear from history.

**HOLD**: model/analysis generation; diaphragm distributed mass and
in-plane behavior; 5% accidental eccentricity actually applied; DD-2 /
DD-3 spectra and `lambda`; response-spectrum scale calibration;
TBDY minimum base shear and effective story drift.

## Offline Windows command (no ETABS required)

```powershell
Set-Location "C:\Users\efeya\PycharmProjects\YENI_VS04"
$g = (Get-ChildItem ".receipts\VS04\VS04G_DIAPHRAGM_MODAL_*.json" |
      Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
$modal = (Get-ChildItem ".receipts\VS04\VS04_REPLAY_LATEST.json" |
          Select-Object -First 1).FullName
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
.\.venv\Scripts\python.exe tools\review_vs04h_diaphragm.py `
    --input "$g" --prior-modal "$modal" `
    --out ".receipts\VS04\VS04H_LINKAGE_$stamp.json"
```

Output excludes all raw rows, preserves SHA-256 of both original files
and refuses to overwrite either source or an existing review file.

## Supervisor gates

- VS04-G LIVE SOURCE: selected-case output observed with 200 rows.
- VS04-H SOURCE CODE: accepted only after unit + CI and local RAW replay.
- No release authorization from source linkage alone:
  `FORMAL_COMPLIANCE=NOT_PROVEN`;
  `ENGINEERING_RELEASE=NOT_READY`;
  `MERGE=HOLD`.
