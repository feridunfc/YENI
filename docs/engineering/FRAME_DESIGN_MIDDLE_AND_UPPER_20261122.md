# Frame-column design at +4.50 m and +9.00 m

On the original 87-column building, the conditional R14 count rose from **14 to 19 to 26**. The five remaining supported frame members at +4.50 m and the consecutive seven C20–C26 members at +9.00 m were named before solving. All 12 reached the selected-cage, capacity shear, connected beam and joint result. The 14 preceding members retained their numerical designs on the same parent source.

| Storey | Physical columns | Previous end-to-end designs | Current end-to-end designs |
| --- | ---: | ---: | ---: |
| +0.00 m | 32 | 1 | 1 |
| +4.50 m | 32 | 13 | 18 |
| +9.00 m | 23 | 0 | 7 |
| Building | 87 | 14 | 26 |

## Storey inputs used by R08

The preparer reads the column census from original connectivity and checks the signed or envelope step at each native cut, including both physical ends. Compression is the sum of the same-combination peak compression of each frame column. The Euler sum uses each column's original dimensions, material modulus, free length and directional end restraints. Only the existing analysis and material assumptions were inherited. A separate calculation assembled the neighbouring columns and beams at each physical end from the ETABS coordinates, section dimensions and connectivity. Both directional sums and the eleven combination totals agreed with the input consumed by the design runner.

| Storey | Frame contributors | Grav_Ult compression (kN) | Critical load X (kN) | Critical load Y (kN) | Storey factor X | Storey factor Y |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| +4.50 m | 32 | 36,250.288 | 777,505.561 | 799,874.571 | 1.064522 | 1.062604 |
| +9.00 m | 23 | 17,537.481 | 775,726.949 | 787,291.216 | 1.030280 | 1.029822 |

At +9.00 m all 23 frame contributors have model-derived framing at both ends on both axes. Four wall objects occur in the original inventory at this level. Their compression and stability contribution remain outside the frame-only scenario. The +4.50 m storey sum retains the preceding wall-supported hinge assumption where used. All twelve new member designs use two resolved framing ends on each bending axis. The calculation adopts sway permitted, rectangular beam webs, creep ratio 1, Eq. 7.21, unity Cm and the effective-length reading of Eq. 7.29. The global second-order multiplier is 1.0. The two-axis storey ratio meets Eq. 7.28 for each of the eleven assigned combinations under this scope. [TS 500, February 2000, §7.6.2](https://abs.cu.edu.tr/Dokumanlar/2016/IMZ312/363439620_ts_500_-_betonarme_yapilarin_tasarimi_ve_yapim_kurallari.pdf#page=33)

## Member designs

All new columns use **32Φ16 longitudinal reinforcement and Φ10/90 confinement**. The table shows the governing utilization for each member within the indicated calculation. The spectral column gives the nonconcurrent corner bound. The two shear columns use signed gravity capacity cases.

| Storey | Column | ETABS ID | k M2 | k M3 | Static PMM | Spectral PMM bound | Shear / TS 500 | Shear / zero-concrete resistance | Joint panel bound |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| +4.50 | C1 | 152 | 3.265 | 2.381 | 29.61% | 46.71% | 52.40% | 70.56% | 44.60% |
| +4.50 | C2 | 153 | 3.265 | 2.207 | 35.63% | 41.45% | 54.13% | 73.29% | 53.62% |
| +4.50 | C5 | 156 | 3.265 | 2.027 | 26.72% | 37.20% | 50.95% | 68.32% | 42.11% |
| +4.50 | C77 | 154 | 2.695 | 2.202 | 20.22% | 33.32% | 47.60% | 63.26% | 35.37% |
| +4.50 | C78 | 155 | 2.695 | 2.019 | 8.47% | 27.73% | 43.83% | 57.68% | 26.55% |
| +9.00 | C20 | 55 | 2.289 | 2.887 | 42.58% | 51.25% | 44.47% | 58.63% | 43.77% |
| +9.00 | C21 | 56 | 2.289 | 2.138 | 43.12% | 51.02% | 47.63% | 63.30% | 43.77% |
| +9.00 | C22 | 57 | 2.289 | 2.138 | 44.00% | 48.15% | 47.71% | 63.42% | 45.32% |
| +9.00 | C23 | 58 | 2.289 | 2.138 | 43.81% | 44.39% | 47.66% | 63.35% | 43.77% |
| +9.00 | C24 | 59 | 2.289 | 2.138 | 43.35% | 43.04% | 47.70% | 63.40% | 44.49% |
| +9.00 | C25 | 60 | 2.289 | 2.887 | 43.21% | 42.07% | 44.49% | 58.65% | 36.30% |
| +9.00 | C26 | 61 | 1.892 | 2.887 | 36.68% | 44.97% | 46.29% | 61.30% | 42.11% |

At +9.00 m the governing signed face is the upper end of C22/57 in Grav_Ult. The member peak compression is 887.915 kN for the magnification factors. The local compression is 802.820 kN at the 3.800 m PMM cut. The design moments are +524.472 and −32.413 kN·m. Radial resistance is 1,194.321519 kN·m in production and 1,194.321456 kN·m in the independent integration of the selected bar coordinates. Both give 44.00% utilization. For the five +4.50 m columns, C2/153 governs at 35.63%. Its directional capacity differs from the independent value by 0.000176 kN·m. Both comparisons meet the 0.01 kN·m numerical tolerance.

## Expected checks on the 12 named columns

| Calculation | Evaluated / expected | Outcome |
| --- | ---: | --- |
| Assigned axial limits | 96/96 TBDY and 132/132 TS 500 | Native demands and section limits checked |
| Effective length and second-order coefficients | 24/24 member–axes and 72/72 gravity case–axes | Governing native compression used for coefficients |
| Selected-cage PMM | 108/108 signed cuts and 288/288 spectral case–cut bounds | All within the adopted surface or corner bound |
| Column design shear and resistance | 72/72 gravity and 192/192 seismic case–axes | Highest gravity zero-concrete utilization 73.29% at +4.50 m C2 |
| Beam and joint calculation | 55 distinct connected beams and 48/48 joint–directions | All panel bounds and joint transverse checks satisfied |

For strong column / weak beam, 34 joint–directions satisfy the low-axial exemption. In the other 14, the column terminates at the roof. These are the separate dispositions of TBDY 7.3.5.3(a) and (b). All 48 still have a joint panel calculation. Its shear deduction is conservatively zero in 34 directions and zero by the roof boundary condition in 14. These members do not require the story α alternative under the adopted scenario. [TBDY 2018, §7.3.5.3](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf)

## Replay and next members

Use the frozen original source in both runs. In the second preparation, `--derive-storey` requests new +9.00 m inputs. The default preparation keeps the same-storey requirement. Engineering release remains NOT_READY. The remaining +9.00 m population contains 16 columns. The next named group is C27–C37, using the +9.00 m anchor C22/57.

```powershell
$prior = '.receipts/verification/frame-column-design-slice-20261122/cohort-runs/RUN-47067d0f1896415ba5ffc8e61031a024'
$out = '.receipts/frame-storey-replay'
& './.venv/Scripts/python.exe' -X utf8 -B tools/prepare_frame_story_slice.py --from-run $prior --anchor 142 --story '+4.50' --columns C1 C2 C5 C77 C78 --scenario-id original-middle-frame-storey-completion --out "$out/middle.json"
& './.venv/Scripts/python.exe' -X utf8 -B -m tbdy_next.cli run-pipeline --source "$prior/parent.source" --design-scenario "$out/middle.json" --case Modal --out "$out/middle-runs"
$mid = (Get-ChildItem -LiteralPath "$out/middle-runs" -Directory -Filter 'RUN-*' | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
& './.venv/Scripts/python.exe' -X utf8 -B tools/prepare_frame_story_slice.py --from-run $mid --anchor 142 --story '+9.00' --derive-storey --columns C20 C21 C22 C23 C24 C25 C26 --scenario-id original-upper-frame-c20-c26 --out "$out/upper.json"
& './.venv/Scripts/python.exe' -X utf8 -B -m tbdy_next.cli run-pipeline --source "$mid/parent.source" --design-scenario "$out/upper.json" --case Modal --out "$out/upper-runs"
```

The middle run is `RUN-81c4226a75aa44cb8c1612672bca211d`. The final run is `RUN-2e424431e3ff491087e2359543e9c9dc`, with sealed results SHA-256 `41c8487e69daec322e12705c7f1a0ad9cccbbf24965c17b7851d3e5402ddb903`. [Prior designs](FRAME_STORY_DESIGN_SLICE_20261122.md) · [Verification ledger](../VERIFICATION_LEDGER.json)
