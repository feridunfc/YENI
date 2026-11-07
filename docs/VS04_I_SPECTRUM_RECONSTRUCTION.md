# VS04-I — Independent source spectrum reconstruction

## Real ETABS evidence (7 November 2026)

The VS04-E evidence captures 26 TSC-2018 spectrum sample ordinates for
RESP_YATAY. Header: SDS=0.52578, SD1=0.263958, R=7, D=2.5, I=1.5,
TL=6 s. Both response-spectrum cases RSX and RSY use acceleration
scale 10 m/s². VS04-G has 200 modal pseudo-acceleration rows, 100 per case.
VS04-D contains 100 modal circular frequencies.

The original 26-point straight-line reconstruction using printed modal
periods left 64/200 rows outside display precision. This was a source
resolution issue, not proof that the ETABS solver was wrong.

Actual corner periods must be calculated from spectrum parameters:

    T_A = 0.2 SD1 / SDS = 0.100406253566... s
    T_B = SD1 / SDS = 0.502031267831... s

The ETABS function table prints these as 0.1 and 0.502. The modal
output prints rounded Period; a more precise modal period can be
recovered as T=2*pi/CircFreq from VS04-D.

With those corrections, simple piecewise-linear reconstruction from the
26 observed normalized ordinate values times acceleration scale 10
yielded all 200 modal accelerations with absolute difference < 0.001
m/s². Mean absolute residual was approximately 0.0000231 m/s²,
maximum approximately 0.0000512 m/s².

The independent continuous TBDY Sae(T)/Ra(T) analytic kernel reproduces
all 26 displayed knot ordinates at their actual formula corner periods
within source decimal display rounding. Note the ETABS modal source
accelerations correspond to its interpolated input function, not necessarily
to the analytic curve evaluated directly at intermediate periods.

## Bounded software contract

src/tbdy_next/spectrum_reconstruction.py:

- Validates exactly 26 function rows and 200 modal-source rows.
- Uses TBDY Eq. (2.2), (4.1) and (4.8) for the normalized function-knot
  arithmetic, not for automatic building code compliance.
- Requires exact source table and case bindings, field units, selected
  RSX U1 / RSY U2, modal frequency and damping.
- Reconstructs actual T_A/T_B from SDS and SD1, with rounding interval
  bounds, and computes mode T from observed CircFreq and its precision.
- Independently interpolates source function values with propagated printed
  decimal precision; no arbitrarily widened percentage tolerance.
- Fails closed for malformed rows, non-finite values, missing modalities,
  changed sources, unsupported case scope or non-overlapping intervals.
- Does not insert a ninth normative check or authorize source model generation,
  applied diaphragm eccentricity, minimum base shear or effective drift.

tools/review_vs04i_spectrum.py produces a reduced hash-bound result file
without modifying any raw input.

### Offline Windows replay

    Set-Location "C:\Users\efeya\PycharmProjects\YENI_VS04"
    $e = (Get-ChildItem ".receipts\VS04\VS04E_BASIS_PROBE_*.json" |
          Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
    $g = (Get-ChildItem ".receipts\VS04\VS04G_DIAPHRAGM_MODAL_*.json" |
          Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
    $m = (Get-Item ".receipts\VS04\VS04_REPLAY_LATEST.json").FullName
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    .\.venv\Scripts\python.exe tools\review_vs04i_spectrum.py --basis "$e" --modal-info "$g" --prior-modal "$m" --out ".receipts\VS04\VS04I_SPECTRUM_$stamp.json"

This output cannot prove the analysis was from the exact same model
generation across all three acquisition sessions.

## Next engineering dependencies

Analysis generation lineage, the DD-2 and DD-3 design basis, actual
RSX/RSY scaling as applied, full irregularity inventory, diaphragm
mass/semirigid constraint semantics, accidental eccentricity effect,
and independently computed code VtE and drift remain NOT_PROVEN.

ENGINEERING_RELEASE=NOT_READY; MERGE=HOLD; main unchanged.

References:
- Official TBDY 2018: https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf
- CSI spectrum function and scaling: https://docs.csiamerica.com/help-files/etabs/Menus/Define/Functions/Response_Spectrum_Functions/Response_Spectrum_Functions.htm
