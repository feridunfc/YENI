# C104 transition forces and independent C29 capacity checks

## C104 first-order free body

The common point is the C104 axis at global (74.00, 0.40, −1.50) m. W21 continues through both regions. W22 starts at −1.50 m. The original 80 × 80 cm column and wall geometry gives gross union areas of 3.28 m² below and 4.48 m² above. The user identified the ETABS view as the only available detail. Its SHA-256 matches the previously surveyed view. Anchorage, lap lengths and construction reinforcement continuity remain unverified. The calculation uses the connections in the solved analysis model. [Original geometry and scope](../VERIFICATION_LEDGER.json)

R08 reads six signed linear-static cases from each archived model. ETABS 23.2 returned `Single Value`, step number 0. The projectors rotate the native joint forces and couples and add the force moment arm about the common origin. The positive cut face has an upward normal. Actions are expressed on the lower body. The output axes for N, V2 and V3 are +Z, +X and +Y. T, M2 and M3 are right-hand moments about these axes. The frozen export contains no point-axis overrides. It sets C104 vertically with the default local axes. [CSI shell joint results](https://docs.csiamerica.com/help-files/etabs-api-2016/html/e6826614-bf6b-d3cd-a0e5-5d70e06cbc07.htm) · [CSI joint coordinate systems](https://docs.csiamerica.com/manuals/etabs/Analysis%20Reference.pdf) · [CSI frame force conventions](https://docs.csiamerica.com/help-files/sap/Output/Frame_Element_Internal_Forces_Output_Conventions.htm)

The free body spans −1.55 m to −1.45 m. Its boundary uses the inner face of each cap, the lateral edges and the W22 soffit. End nodes on a cap belong to that cap once. The lateral transfer uses separate native corner and frame-end rows on the retained body's rim. Interior joints have an additional equilibrium check. The coarse strip contains 18 shell cells and two frame elements. The fine strip contains 72 shell cells and four frame elements. External loads come from the signed model assignments, material weights, analytical frame area, shell thickness, surface normals and geometry. Both model objects carry self-weight in the analysis. The original model has one tower and no named story elevation in the strip. The two automatic lateral cases have no additional assigned object loads. CSI distributes each automatic static seismic story force to joints at the story elevation. [CSI manual, chapter 3](https://docs.csiamerica.com/manuals/etabs/Welcome%20to%20ETABS.pdf)

All **12 case–mesh free bodies** met the fixed equilibrium budgets. The largest absolute residual was **0.000012770 kN** for force and **0.000047253 kN·m** for moment. The strip self-weight is 10.296959 kN. LC_H supplies 29.493000 kN in +Y and a −73.257900 kN·m torque about the common point. A separate integration of all shell corners and frame stations on all four faces reproduced **288/288** sealed force and moment components. This cross-check uses the same ETABS solves.

| Physical face | Passing 50 vs 25 mm comparisons | Expected |
| --- | ---: | ---: |
| −1.55 m, above | 13 | 36 |
| −1.50 m, just below | 13 | 36 |
| −1.50 m, just above | 3 | 36 |
| −1.45 m, below | 7 | 36 |

The mesh budget for each component was fixed before evaluation at the greater of 0.05 kN or kN·m and 1% of the larger absolute component. Equilibrium used 0.01 kN or kN·m and a relative floor of 10⁻⁶ of the largest term in the same component. These are numerical study criteria. The 50 and 25 mm labels refer to **vertical** pitch. W21 horizontal pitch changed from 1.0 to 0.5 m and W22 horizontal pitch from 0.85 to 0.425 m.

| Component | Governing signed case on the immediate faces | 50 mm | 25 mm | Change | Allowed change |
| --- | --- | ---: | ---: | ---: | ---: |
| N, kN | LC_EQX, above | 95.306 | 145.599 | +50.293 | 1.456 |
| V2, kN | LC_EQX, above | 603.174 | 569.484 | −33.690 | 6.032 |
| V3, kN | LC_H, above | −100.527 | −121.361 | −20.834 | 1.214 |
| T, kN·m | LC_H, above | 320.032 | 417.880 | +97.849 | 4.179 |
| M2, kN·m | LC_H, above | 328.564 | 323.586 | −4.978 | 3.286 |
| M3, kN·m | LC_EQX, above | 275.493 | 55.959 | −219.533 | 2.755 |

W22 accounts for −194.297 kN·m of the last difference, W21 for −26.621 kN·m and C104 for +1.385 kN·m. On W22, the point-couple change is +0.093 kN·m and the vertical-force moment-arm change is −194.390 kN·m. The latter is concentrated at x = 77.40 m, 3.40 m from C104, where the model geometry meets W23. The result identifies the location to investigate. The archived corner forces cover W21/W22. They do not independently establish W23's share or the cause of the redistribution.

**Next C104 calculation.** Establish the W22–W23 shared-edge and constraint roster at that end. Compare vertical force and the equivalent moment about C104 across both sides of the interface, using the same load, the same cut and separately controlled horizontal and vertical refinement. Carry this component budget into a direct second-order study after the first-order demand is qualified. Fourteen wall-coupled columns retain their second-order gate.

The native solve snapshots were replayed offline through `run-pipeline`. The attached result is at `r08_local_slenderness.per_member.211.coupled_wall_transition` in `RUN-7dc0634b19e44a1c8286fb6368f5721d`. The sealed HTML includes every case, cut, balance residual, mesh difference and tolerance. The ledger holds the private paths and result hashes. [Scenario preparation](../../tools/prepare_c104_transition.py) · [R08 projector](../../src/tbdy_next/engineering/coupled_wall_transition.py) · [Verification ledger](../VERIFICATION_LEDGER.json)

## C29 independent selected-cage capacity

The fixed-axial-load calculation now covers **24/24 element faces** at 18 distinct combination–physical cuts on members 225 and 142. It uses the exact selected 32Φ16 cage and Φ10/90 ties, unrounded same-step axial load and the two signed revised design moments at each face. All 23 additional faces passed the predeclared 0.01 kN·m comparison. The previous governing face reproduced identically. The maximum absolute difference from production radial capacity was 0.000471272 kN·m. The largest last spatial refinement change was 0.001411241 kN·m. The maximum sampled axial equilibrium error was below 0.0000001 N.

| Maximum independent utilization per member | Grav_Ult | Negative temperature combination | Positive temperature combination |
| --- | ---: | ---: | ---: |
| 225 | 12.794845% | 9.734882% | 9.590256% |
| 142 | 17.647308% | 13.621418% | 13.746236% |

Independent radial capacity ranged from 1,303.815270 to 1,518.172460 kN·m. Member 142, lower end, Grav_Ult governs the 24-face population. The comparison validates this calculation for the two selected model cages and three gravity combinations. Axial-limit cases, other sections, as-built reinforcement and overall engineering acceptance remain open. The C29 R14 result remains 2/87 conditional. [C29 source and method](C29_S00_S02_20261122.md) · [Verification ledger](../VERIFICATION_LEDGER.json)
