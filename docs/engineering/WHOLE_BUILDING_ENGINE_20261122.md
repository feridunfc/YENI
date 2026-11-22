# Original building through the production engine

On 22 November 2026 the common engine ran the three occupied storeys of the original `kompakt_b.EDB` source in one invocation. It carried 42 of 87 columns through second order, selected reinforcement, capacity shear, connected beams and joints to a conditional R14 design. It calculated the selected flexural reinforcement and full design shear for 180 of 180 beams. The engineering disposition is `NOT_READY`.

## Frame and wall confinement

The production run `RUN-9c84d56ca73741ff9318421bf73adf76` used the archived original model and the command below. R10 calculates the column schedule on the final selected cage. R14 consumes its result, including any insufficient foundation depth. The whole-building result includes the beam tie stations and the two-direction pier boundary calculations. The command writes every member and its disposition to the sealed results and printable report.

| Calculation | Original building result |
| --- | --- |
| Column confinement | 73/87 clear members, 3,265 distinct stations. 69 schedules satisfy the evaluated spacing and gross-depth checks, four have insufficient continuation depth, and 14 wall-coupled members lack discrete clear faces. |
| Beam confinement | 180/180 model spans, 10,588 distinct stations. The two end regions overlap on 29 beams. Of 360 ends, 254 match the connected column half width, native offset and design cut. The other 106 use the ETABS model cut for the proposed schedule. |
| Pier boundary reinforcement | 4 continuous rectangular piers, 12/30 wall objects, 24 storey-end sections. Seventeen objects belong to multi-panel or varying sections. One has no pier assignment. |
| Column R14 | 42 conditional, four numerical failures and 41 held. The four failures were previously held. |
| Slab flexure and punching | Deferred by the project owner. |

For C29/225 and C29/142 the clear lengths are 4,450 and 3,800 mm. Each end requires 1,200 mm of confinement. The selected Ø10/90 cage produces 50 and 43 distinct tie stations, with three interior crossties per direction at a station. The first and last ties are 45 mm from the modelled faces. C29/225 has a 900 mm mat and requires 800 mm of continuation. For C21–C24 at +0.00 m (217–220), the column base joints share shell elements of F186/9A. Its `Foundation_60cm` property gives 600 mm gross depth, 200 mm short against the 800 mm minimum. This finding applies to the archived model and the adopted high-ductility detailing branch.

Beam B350/981 has 3,050 mm clear length, 1,400 mm of confinement at each end and 36 tie stations. Its full capacity shear is 628.210 kN, with 971.314 kN resistance and 64.68% utilization. All selected beam cages in this model have a governing effective depth of 640 mm. The engine uses the selected tension-steel centroids for both bending signs and the three selected stations, and uses the effective depth in the end pitch limit and shear resistances.

| Pier | Width per end (mm) | Minimum / proposed longitudinal steel per end (mm²) | Proposed bars per end | Ø10/80 legs along / across wall |
| --- | ---: | ---: | ---: | ---: |
| P2 | 800 | 3,200 / 3,386.6 | 22Ø14 | 3 / 4 |
| P3 | 800 | 2,240 / 2,463.0 | 16Ø14 | 3 / 4 |
| P4 and P5, each | 880 | 3,520 / 3,694.5 | 24Ø14 | 3 / 5 |

The pier labels reconcile against the source export and each pair of adjacent panels shares both edge joints. The four stacks are 400 mm thick and span –5.15 to +9.00 m. Both the lowest-base and rigid-first-basement scenarios require boundary regions on these stacks. The proposal carries the critical detail over all three storeys. It adopts 40 mm cover and the 500 MPa tie steel from the source frame catalogue. Under TBDY 7.6.5.2(b), both directions meet the transverse area minimum. The largest required/provided ratio is 0.633, and the largest tie-line gap is 240.7 mm against 250 mm. The proposed critical tie pitch is 80 mm against an 84 mm upper bound. For Ø10 closed hoops the specified 135° hooks have a minimum 50 mm inside bend diameter and an 80 mm straight tail. Anchorage, end-column interference, installation, and force-based web and pier design require further calculation or drawings. [TBDY 2018, §§7.2.8, 7.3.4.1, 7.4.4, 7.6.2 and 7.6.5](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf)

## Run the calculation

Run this from YENI on the Windows workstation with the archived project inputs.

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B -m tbdy_next.cli run-pipeline --whole-building --source '.receipts/c29-self-weight-nmax/RUN-be9d8258796f4dfca1a3609453e94e53/parent.source' --design-scenario '.receipts/c29-self-weight-nmax/request.json' --wall-hinge-aggregate-storey '+4.50' --case Modal --out '.receipts/verification/building-confinement-20261122/building'
```

The source is the original native capture. The scenario supplies the project's assigned combinations, solver archive, reinforcement settings and two previously supported member bases for C29. The engine obtains the member roster, checks the configured cuts, derives the storey inputs and selects every eligible member from the model. The command also writes `RUN-…/report.html`. A prior cohort, a preparation script and a separate report command are unnecessary.

In the workspace, select a combined source carrying all columns and the intended project settings. Under **Rebar & stirrup selection** enter `+4.50` for this project's storey aggregate assumption and choose **Run whole building**. A sealed building source already carries its assumptions. The corresponding HTTP operation uses `/api/apply-rebar-selection` with `whole_building` and optional `wall_hinge_aggregate_storeys`. Both entry points use the same `EnginePipelineRunner`.

## Earlier frame design results

| Storey | Columns in model | Conditional R14 design | Awaiting an input or method |
| --- | ---: | ---: | ---: |
| +0.00 m | 32 | 1 | 31 |
| +4.50 m | 32 | 18 | 14 |
| +9.00 m | 23 | 23 | 0 |
| **Building** | **87** | **42** | **45** |

The previous 26 column designs retain their cage, static and spectral utilization, capacity shear and joint utilization. The 16 additional upper-storey members are C1, C2, C5, C27 through C37, C77 and C78 (ETABS IDs 62 through 77). They add 144 signed gravity case-cuts and 384 assigned seismic case-cut bounds. The 42 designs cover 378 and 1,008 respectively. Spectral component bounds do not establish simultaneous signed actions.

C2/73 at +9.00 m governs static PMM among the 16 additions. At 3.80 m under Grav_Ult, local compression is 780.179 kN and the coefficient uses 865.274 kN. The design moments are −491.214 and −31.471 kN·m. Utilization with 32Φ16 and Φ10/90 is 41.432%. An independent section integration at the same axial force and moment direction returned 1,188.021031 kN·m radial capacity. The engine returned 1,188.021065 kN·m.

All 180 physical beams reached signed flexural capacities for their selected end and span reinforcement, full design shear including assigned gravity, and web, confinement and span resistance checks. B350/981 at +0.00 m governs in confinement with 628.210 kN demand, 971.314 kN resistance and 64.676% utilization. Independent recombination used the three original gravity cases and the same selected end capacities on all 180 beams. The largest shear difference was 1.14 × 10⁻¹³ kN. Beam flexural capacity uses the recorded zero-axial-force scenario. Torsion, deflection and crack width are open.

| Other checks in the same run | Evaluated / expected | Recorded result |
| --- | ---: | --- |
| TS 500 column compression under assigned combinations | 957 / 957 | Numerical |
| Occupied-storey drift rows | 12 / 12 | Source coverage complete |
| Global second-order storey prechecks | 6 / 6 | Conditional |
| B1 weak-storey comparisons | 4 / 4 | No numerical trigger |
| B2 soft-storey directions | 6 / 6 | +4.50 m over +0.00 m exceeds 2.0 in X (2.084575) and Y (3.283272) |
| Wall geometry | 30 / 30 walls | 3 of 90 evaluated geometry conditions below the required value |

## Limits and next physical calculation

The frame calculation assumes sway permitted, rectangular beam webs, Rm = 1, TS 500 Eq. 7.21 stiffness and Cm = 1. The +4.50 m frame aggregate uses the explicit wall-end hinge assumption. Each new column still requires stiffness at its own two physical ends. The independent comparison covers 22 compression sums and four directional critical loads across the upper two storeys. The maximum difference was 2.33 × 10⁻¹⁰ kN.

The 45 holds comprise 17 ground-storey members with unresolved mat rotational stiffness, 14 middle-storey members with unresolved supporting-wall rotational stiffness and 14 ground-storey wall-coupled members. Their reasons pass through R08 to R14. C104/211 stays in the last group. Resume its W21/W22/W23 work when the assigned P and V3 horizontal convergence, V2 vertical convergence, coupled second order and reinforcement continuity can be checked.

The same report inventories 30 wall objects pending reinforcement design, three occupied-storey diaphragms pending collector/chord design, 84 slab objects pending flexure/punching, two mat objects pending contact and structural design, and 180 beams pending torsion/serviceability. Coupling-beam classification has an unknown denominator.

The active scope is the force-based design of the four named rectangular piers and their connected frames. Keep slab F116/291, punching and local C104 convergence deferred.

## Result identity

The earlier frame-only CLI run is `RUN-9b85a9a1dd7b416eab85056c57eae3d5`. The HTTP run is `RUN-aa330b3ed2e34b298fe59f3dc57f3e55`. Their input bytes, full sealed results and all 16 recorded stage payloads match. The printable web view matches the HTML written by its run. The original EDB SHA-256 still begins `0ce0e970988d`. These results use its archived native solution. [Source and results in the verification ledger](../VERIFICATION_LEDGER.json)
