# Original building frame-column design at +4.50 m

The original 87-column building now has **14 conditional R14 designs**. The original C29 run had two. The new run adds **12 columns**, increasing this design coverage from 2.30% to 16.09% (+13.79 percentage points). The +4.50 m C20–C37 population was fixed before solving. It contains 13 finished designs, including C29/142, and five columns bearing on walls. The second original C29 member, 225, is at +0.00 m. Both original C29 members retain their previous design utilizations.

## Check population

The recipe defines 68 engineering check IDs and five source IDs. The table names 11 engineering checks followed through the calculations for the 12 newly completed members. Its denominators come from the original design assignment, native physical cuts and beam incidence. Some operations also ran elsewhere in the building. The recipe has no current all-building acceptance total across its 68 IDs. [Recipe inventory](reference/recipe_20261118/delivery/CHECK_MAPPING.json)

| Check | Expected for the 12 new members | Calculation and disposition |
| --- | --- | --- |
| CHK-004, TBDY compression | 96 assigned seismic member–combinations | 96 within the section limit. Across the original building, 696/696 fall within the limit. |
| CHK-005, TS 500 compression | 132 assigned member–combinations | 132 within the section limit. Across the original building, 957/957 fall within the limit. |
| CHK-115, minimum eccentricity | 216 signed gravity cut–axes | 216 use local compression and the 39 mm floor before magnification. |
| CHK-116, free length and slenderness | 12 physical spans and two bending axes per span | 12 clear lengths from physical faces, 24 axis slenderness evaluations. |
| CHK-117, effective length | 24 member–axes | 24 effective-length factors from the two actual framing ends per axis. |
| CHK-119, moment magnification | 72 gravity member–case–axes | 72 factors evaluated with the same-storey compression and Euler sums. |
| CHK-120, final PMM | 108 signed gravity case–cuts and 288 assigned seismic envelope case–cuts | All 108 gravity utilizations and all 288 seismic corner bounds evaluated with the selected cages. |
| CHK-125, strong column / weak beam | 48 physical joint–directions | 40 meet the low-axial exemption and eight meet the interval capacity check. |
| CHK-126, column capacity shear | 72 gravity and 192 seismic case–axes | All gravity capacity demands and all assigned seismic shear bounds evaluated. |
| CHK-127, shear resistance | Same 72 gravity and 192 seismic case–axes | Selected transverse reinforcement compared with these demands. Highest gravity utilization with zero concrete contribution is 79.31% at C28. |
| CHK-128, joint panel shear | 48 physical joint–directions | All 48 geometric bounds satisfy the limit. The panel bound uses zero deduction for unresolved seismic column shear. All 48 also satisfy the joint transverse reference. |

The governing building axial ratios both occur in C29/225 at +0.00 m. The assigned Duct_SeisY compression is 2,539.014 kN against the 8,960 kN TBDY limit (28.34%). Grav_Ult reaches 3,240.466 kN against the 13,440 kN TS 500 limit (24.11%). For all 87 members, these checks were repeated directly from native axial extrema and the material and section limits 0.4 fck Ac and 0.9 fcd Ac.

The 12 designs use **32Φ16** longitudinal bars and **Φ10/90** confinement. They connect to 68 distinct beams with a selected-cage capacity-shear calculation and a bound gravity shear term. The spectral PMM entries bound eight corners at each of three native cuts per assigned seismic combination. They carry no simultaneous signed spectrum force vector or full-domain proof.

## Results by physical column

Each utilization is the largest value in that column for the indicated check. The two shear columns use signed gravity capacity demands. The five open rows identify the missing member input. They are included in the 18-column denominator.

| Label | ETABS ID | R14 outcome | k M2 / M3 | Static PMM | Spectral PMM bound | Shear / TS 500 | Shear / zero-concrete resistance | Joint panel bound |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| C20 | 133 | Wall below at I | — | — | — | — | — | — |
| C21 | 134 | New | 1.959 / 2.381 | 36.33% | 64.74% | 53.53% | 72.34% | 26.87% |
| C22 | 135 | New | 1.959 / 2.381 | 38.24% | 59.68% | 53.68% | 72.57% | 28.27% |
| C23 | 136 | New | 1.959 / 2.381 | 38.95% | 55.07% | 53.66% | 72.55% | 28.27% |
| C24 | 137 | New | 1.959 / 2.381 | 37.24% | 55.25% | 53.67% | 72.55% | 27.33% |
| C25 | 138 | Wall below at I | — | — | — | — | — | — |
| C26 | 139 | Wall below at I | — | — | — | — | — | — |
| C27 | 140 | New | 2.094 / 2.381 | 28.18% | 46.24% | 57.58% | 78.89% | 26.87% |
| C28 | 141 | New | 2.094 / 2.381 | 28.12% | 38.30% | 57.83% | 79.31% | 27.33% |
| C29 | 142 | Retained | 2.060 / 2.137 | 29.55% | 35.39% | 57.83% | 79.30% | 49.68% |
| C30 | 143 | New | 2.094 / 2.381 | 26.74% | 34.66% | 57.66% | 79.03% | 26.87% |
| C31 | 144 | Wall below at I | — | — | — | — | — | — |
| C32 | 146 | New | 2.060 / 2.147 | 23.66% | 45.36% | 53.94% | 72.98% | 40.19% |
| C33 | 147 | New | 2.060 / 2.207 | 21.20% | 36.56% | 57.39% | 78.57% | 27.82% |
| C34 | 148 | New | 2.060 / 2.027 | 20.70% | 33.15% | 53.78% | 72.73% | 21.72% |
| C35 | 149 | New | 2.053 / 1.930 | 26.96% | 47.95% | 50.77% | 68.04% | 26.87% |
| C36 | 151 | Wall below at I | — | — | — | — | — | — |
| C37 | 157 | New | 3.265 / 1.930 | 29.00% | 50.46% | 48.33% | 64.35% | 46.46% |

C23/136 governs the new signed PMM results at its lower station under Grav_Ult. Local compression is 1,570.644 kN. The amplified local moments are −530.866 and +66.196 kN·m. The selected cage has a radial resistance of 1,373.650349 kN·m. A separate fixed-axial section integration using the actual bar coordinates gives 1,373.650116 kN·m, a difference of 0.000233 kN·m against a 0.01 kN·m budget. Both utilizations round to 38.95%. C21 governs the new spectral PMM bound at 64.74%. C37 governs the joint panel bound at 46.46%.

## Adopted design scope

The engine uses the signed original gravity combinations and the eight assigned seismic combinations. For each new standalone member, R08 computes its own effective length from both physical framing ends. The scenario uses rectangular beam webs, sway permitted, Rm = 1, TS 500 Eq. 7.21, unity Cm and the effective-length interpretation of Eq. 7.29. The global second-order multiplier is 1.0. The selected axial idealization uses each gravity combination's maximum member compression for coefficients and the actual compression at each cut for PMM.

All 32 frame columns of the storey contribute to its conditional compression and Euler sums. The storey compression was recovered from all eleven assigned native result sets. Under Grav_Ult it is 36,250.288 kN. With original model material moduli and the previously adopted hinge at wall-supported lower ends for this storey sum, Euler totals are 777,505.561 kN in X and 799,874.571 kN in Y. The member design extension requires both frame ends on each axis. C20, C25, C26, C31 and C36 require the supporting wall's rotational response at the lower end. Full wall–frame stability, acceptance of the member assumptions, anchorage and construction details remain open. The original C29 refined ETABS study retains its own two-member scope.

## Reproduce

Use the prior C29 design run's frozen parent source. The preparation command verifies the sealed anchor, both global storey totals, the assignment and physical framing. The existing runner performs the full design. The final report is generated from its sealed output.

```powershell
$prior = '.receipts/c29-self-weight-nmax/RUN-be9d8258796f4dfca1a3609453e94e53'
$columns = 20..37 | ForEach-Object { "C$_" }
$scenario = '.receipts/frame-story-replay.json'
& './.venv/Scripts/python.exe' -X utf8 -B tools/prepare_frame_story_slice.py --from-run $prior --anchor 142 --story '+4.50' --columns $columns --scenario-id original-450-frame-column-design-c20-c37 --out $scenario
& './.venv/Scripts/python.exe' -X utf8 -B -m tbdy_next.cli run-pipeline --source "$prior/parent.source" --design-scenario $scenario --case Modal --out .receipts/frame-story-replay
```

Run `RUN-47067d0f1896415ba5ffc8e61031a024` uses parent source `703e202fc8b08f60043c571d9970945b6307e5cee99e8a45e6377c8446da56fc` and scenario input `07efbb3a4334db8ff490e79ddcbadeec6698187e746cbfcba59f0ab23d8d1007`. The sealed result SHA-256 is `957a5dae5782d9840464d76082cd84bc21be9cf81363ed34e43248aa38bd45bb`. [Verification ledger](../VERIFICATION_LEDGER.json)
