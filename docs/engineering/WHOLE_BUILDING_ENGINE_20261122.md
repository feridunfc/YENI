# Original building through the production engine

On 22 November 2026 the common engine ran the three occupied storeys of the original `kompakt_b.EDB` source in one invocation. It carried 42 of 87 columns through second order, selected reinforcement, capacity shear, connected beams and joints to a conditional R14 design. It calculated the selected flexural reinforcement and full design shear for 180 of 180 beams. The engineering disposition is `NOT_READY`.

## Run the calculation

Run this from YENI on the Windows workstation with the archived project inputs.

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B -m tbdy_next.cli run-pipeline --whole-building --source '.receipts/c29-self-weight-nmax/RUN-be9d8258796f4dfca1a3609453e94e53/parent.source' --design-scenario '.receipts/c29-self-weight-nmax/request.json' --wall-hinge-aggregate-storey '+4.50' --case Modal --out '.receipts/building-engine-20261122/original-building'
```

The source is the original native capture. The scenario supplies the project's assigned combinations, solver archive, reinforcement settings and two previously supported member bases for C29. The engine obtains the member roster, checks the configured cuts, derives the storey inputs and selects every eligible member from the model. The command also writes `RUN-…/report.html`. A prior cohort, a preparation script and a separate report command are unnecessary.

In the workspace, select a combined source carrying all columns and the intended project settings. Under **Rebar & stirrup selection** enter `+4.50` for this project's storey aggregate assumption and choose **Run whole building**. A sealed building source already carries its assumptions. The corresponding HTTP operation uses `/api/apply-rebar-selection` with `whole_building` and optional `wall_hinge_aggregate_storeys`. Both entry points use the same `EnginePipelineRunner`.

## Physical results

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

The next physical calculation is slab F116/291 at +0.00 m. The original capture assigns `Slab_d=15` to this panel and contains slab property definitions. Its design-strip moment results and face reinforcement have yet to be bound. Use the same ETABS gateway to obtain the strip, local axes and signed design case. Carry demand, material, cover and selected reinforcement into a flexural utilization in this runner. Keep punching as a distinct check with its column or support perimeter. Count the result against the 84 physical slabs.

## Result identity

The production CLI run is `RUN-9b85a9a1dd7b416eab85056c57eae3d5`. The HTTP run is `RUN-aa330b3ed2e34b298fe59f3dc57f3e55`. Their input bytes, full sealed results and all 16 recorded stage payloads match. The printable web view matches the HTML written by its run. The original EDB SHA-256 still begins `0ce0e970988d`. These results use its archived native solution. [Source and results in the verification ledger](../VERIFICATION_LEDGER.json)
