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

The following pier calculation consumes these four boundary cages. Slab F116/291, punching and local C104 convergence are deferred.

## Pier web, gravity capacity and seismic shear

Both ends of 12 panels in four continuous piers were checked on the original locked ETABS solution. The native section properties give one area and zero lines per pier and storey. Each centroid, material, width, thickness and major-axis orientation matches the physical panel. The nearest column footprints have a positive clearance on all twelve panels. The entire rectangular concrete section enters the calculation once.

The design proposal uses C35/45, 500 MPa reinforcing steel and 40 mm cover. Both web curtains use Ø12 vertical bars and Ø12 horizontal bars at 200 mm. P2 and P3 have vertical bars at 200 mm. P4 and P5 have vertical bars at 188.57 mm. The existing constant-width end cages and Ø10/80 boundary hoops continue through all three storeys. Gravity ratios below use simultaneous signed P, M2 and M3 and the radial capacity of the selected cage at that axial force. The shear column gives the governing upper utilization across both wall classifications.

| Pier | Gravity PMM and shear cut combinations | Governing gravity PMM | Gravity member and face | Seismic shear cut combinations | Governing seismic shear bound |
| --- | ---: | ---: | --- | ---: | ---: |
| P2 | 30/30 | 13.67% | 472 bottom, Grav_Ult | 48/48 | 58.05% |
| P3 | 30/30 | 16.17% | 465 bottom, Grav_TempPos | 48/48 | 43.60% |
| P4 | 30/30 | 17.76% | 415 top, Grav_Ult | 48/48 | 38.38% |
| P5 | 30/30 | 6.91% | 469 bottom, Grav_Ult | 48/48 | 29.96% |
| **Four piers** | **120/120** | **17.76%** | **415 top, Grav_Ult** | **192/192 local bounds** | **58.05%** |

For P3 the governing gravity cut has 1,069.2474 kN compression, M2 = 8.1823 kN·m and M3 = −740.6207 kN·m. Its capacity along that moment direction is 4,579.1076 kN·m. For P2 the governing Crack_SeisX_Soil cut has a 1,975.2499 kN conditional upper shear and 3,402.5455 kN resistance. Structural results are in the sealed run and the printable report.

The original export assigns Grav_Service, Grav_Ult, Grav_TempNeg, Grav_TempPos and WGHT to Wall strength design. It also assigns eight Crack_Seis combinations. Their horizontal spectral coefficients match the eight project Cap_Seis controls after one multiplication by the model D = 2.5. The engine compares the signed centre and width of each native V2 interval with its amplified control. It then uses the alternate shear limit in 7.6.6.3 to bound demand, checking the 1.2 and 1.4 branches against Vr and the corresponding concrete limits. For each branch it takes the larger result with the signed vertical earthquake contribution held fixed or amplified. This is a sufficient bound for the local cut comparison. That earlier local check left the heightwise demand and seismic flexure open. The subsequent seismic pier design below uses the alternate shear bound. [TBDY 2018, §§7.6.3, 7.6.6 and 7.6.7](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf)

The matched-EI eight-part solution is a different analysis revision. It supplies three final-step gravity load sets at the same 24 wall ends. All 72 cut combinations have their own PMM and shear results. At 24 bottom cuts the six pier components were checked against the signed shell corner forces, including moment transport to the section centroid. The largest absolute discrepancies were below 0.000051 kN or kN·m.

The original capture and analysis receipts are local. Replay the entire original building and its report from the repository using the existing engine.

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B -m tbdy_next.cli run-pipeline --whole-building --case Modal --source '.receipts/c29-self-weight-nmax/RUN-be9d8258796f4dfca1a3609453e94e53/parent.source' --design-scenario '.receipts/c29-self-weight-nmax/request.json' --wall-hinge-aggregate-storey '+4.50' --pier-forces '.receipts/verification/pier-section-design-20261122/original-piers.json' --out '.receipts/verification/pier-section-design-20261122/original-building'
```

At this earlier checkpoint the seismic flexural envelope, web crossties and horizontal joints were pending. The [seismic pier design](#seismic-pier-design-on-the-original-building) below records the subsequent results.

### Commercial cross-check at P2

Use the original P2/W6 wall 472, lower face of storey +0.00 m at (69.00, 18.60, −5.15) m. Under Crack_SeisX_Soil its native local V2 endpoints are +286.3160 and +1,023.0396 kN. Under Cap_SeisX_Soil they are −266.2267 and +1,575.5823 kN. With the stated double Ø12/200 horizontal reinforcement, the solid and coupled shear upper bounds are 1,784.8081 and 1,975.2499 kN respectively, and Vr is 3,402.5455 kN. The first ETEX shear and axial views each reported 15 pier-storey checks. Ten rows were fully legible in each view. For **10/10** common rows, ETEX's axial compression and displayed Ve match the bottom-cut native Cap_SeisX_Soil compression and maximum absolute V2, respectively, to 0.005 tf (1 tf = 9.80665 kN). The axial capacity also reproduces for all ten rows using the displayed C35 value of 3,569 tf/m², net area and coefficient 0.35. In the first axial view the selectors showed Crack_SeisX_Soil while the rows displayed Cap_SeisX_Soil. In a subsequent axial view both selectors and rows displayed Crack_SeisX_Soil. All nine fully visible rows in that view (P2, P3 and P4 on all three storeys) reproduce the native bottom-cut compression, concrete-area limit and utilization at displayed precision. ETEX reported 15 passing rows and zero failures. The largest visible ratio was 11.31% at P4/+0.00 m (248.73 tf against 2,198.50 tf).

| P2 at the lower face of +0.00 m | Original ETABS or engine | ETEX result |
| --- | ---: | ---: |
| Compression under Cap_SeisX_Soil | 314.3855 tf | 314.39 tf |
| Compression under Crack_SeisX_Soil | 213.6947 tf | 213.69 tf (10.69% of the axial limit) |
| Axial limit with ETEX displayed inputs | 1,998.64 tf | 1,998.64 tf |
| Maximum absolute local V2 under Cap_SeisX_Soil | 160.6647 tf | Ve = 160.66 tf |
| Displayed resistance | 346.96 tf for proposed two-face Ø12/200 horizontal steel | 633.56 tf exported section limit |
| Utilization at that same native shear | 46.31% | 25.36% |

The axial view evaluates concrete area under compression. For the high-ductility branch the applicable storeys, basement-wall classification, project G+Q+E combinations and live-load reductions govern the full 7.6.1.1 check. The axial limit uses concrete area and strength. The shear view shows βv = 1.5 in its list and 1.0 in the adjoining field, and displays Ve1 as blank. The effective βv, steel stresses and actual horizontal steel are unavailable from these summaries. The paired reference exports below explain the Quick Result arithmetic. The installed steel at the compact P2 remains unverified. The user reported no defined section cuts for overturning. These comparisons used native Pier Forces. [TBDY 2018, §§7.6.1.1, 7.6.6.3 and 7.6.7.1](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf)

#### ETEX shear workbook at the same lower cuts

The supplied ETEX file had header-only `DATA` and `DATA_CIROZ` sheets. A private copy now contains the 15 original `Cap_SeisX_Soil` lower pier-storey cuts and seven distinct pier geometry keys. Twelve cuts are single-panel rectangular sections of P2–P5. The three basement-only piers have multiple panels. The copy uses `PERDE_KESME!G4 = Hayır` to compare the native maximum absolute bottom V2 at all 15 cuts. The original Fig. 7.12 selector was on. Ten Quick Result values at displayed precision are available for that branch. The remaining five adjusted inputs are marked unavailable. The envelope components in a row have no simultaneity guarantee.

At P2/W6 (472), the lower face of storey +0.00 m carries 160.6647 tf of in-plane shear under this combination. The section is 4.00 m by 0.40 m. All resistances below are in tf.

| Resistance | Source or calculation | P2 value |
| --- | --- | ---: |
| Concrete section limit | `PERDE_KESME!P7`, solid-wall coefficient 0.85 | 820.4533 |
| Concrete contribution | `X7`, C35 lookup with fctd = 1.38 MPa | 146.3502 |
| Horizontal-steel contribution, template default | `Y7`, two curtains of Ø10/200, B500C | 139.2846 |
| Concrete plus horizontal steel, template default | `Z7`, X7 + Y7 | 285.6348 |
| Concrete plus horizontal steel, proposed Ø12/200 | Same Z7 formula with the two-curtain engine cage | 346.9200 |
| Engine resistance, proposed Ø12/200 | Sealed original building calculation | 346.9631 |
| Quick Result Vr | Screen value, copied into the previously empty `DATA!AU2` input | 633.56 |

The like-cage P2 difference is 0.0431 tf (0.0124%). The workbook uses tabulated fctd and a rounded MPa-to-tf/m² conversion. With the original formulas exercised on the proposed cage at all 12 rectangular cuts, the largest absolute difference from the engine is 0.04742 tf. The delivered workbook retains its default Ø10/200, giving a P2 utilization of 56.25%. Neither the section limit nor the reinforced resistance reads `DATA!AU2`. The filled A/B exports below supply the missing inputs for reconstructing the Quick Result value. The template and the proposed cage give no evidence of the actual installed steel. These comparisons cover the selected raw shear envelope. The seismic pier design below adds the heightwise design shear and seismic PMM. [Workbook comparison record](../VERIFICATION_LEDGER.json)

#### Filled ETEX A and B Block wall files

In the A and B Block exports, `DATA!AU` (“Vr”) holds values written by the postprocessor. For **47/47 A Block** and **32/32 B Block** rows, the ratio AU divided by width, thickness and `DATA!AW` is 0.65. All 79 rows use C35 with AV = 3569 and AW = 609.192027772, numerically equal to 10.1972 × √3569. The workbook's separate C35 material lookup gives 603.274487642. For the compact P2 section, 0.65 × 4.00 × 0.40 × 609.192027772 = **633.559709 tf**. The ten visible compact-building Quick Result capacities, paired native demands and displayed percentages agree at printed precision. The maximum source-row residual for the reconstructed AU value is below 0.000000001 tf.

B Block P2 has two 4.00 m × 0.40 m sections with different selected horizontal reinforcement. Both export 633.559709 tf in `DATA!AU15:AU16`. The same workbook shows the following values in `PERDE_KESME!O20:AA21`.

| B Block P2 | Horizontal steel per face | Demand (tf) | Reinforced resistance (tf) | Utilization |
| --- | --- | ---: | ---: | ---: |
| +4.50 m | Ø10/150 | 328.097 | 332.063 | 98.81% |
| +9.00 m | Ø10/200 | 187.437 | 285.635 | 65.62% |

Both archived configurations select a solid wall, and `PERDE_KESME` applies 0.85 to its solid-wall section limit. Its value at the same dimensions is 820.4533 tf. The source did not reveal why the exported AU has an effective factor of 0.65. The original building’s proposed Ø12/200 cage is assessed against 346.9631 tf in the engine. The A/B examples use a different model and `ENVE_PerdeUst_1.2D` rows marked `Top`. Their forces and selected reinforcement belong to those projects. [TBDY 2018, §7.6.7.1, Eqs. 7.17–7.18](https://muhendis.web.tr/dosyalar/standartlar_yonetmelikler/turkiye_bina_deprem_yonetmeligi.pdf#page=152)

The companion B Block vertical schedule at P2/+4.50 m gives two 0.80 m end zones of 16Ø20 each, a 2.40 m web of 24Ø12 and 127.67 cm² of total vertical steel. A Block P12/+14.5 m provides a heightwise shear comparison with a visible effect of the adjustment, 132.787 tf in `AS` and 223.661 tf in `AT`. The adjusted value is half the stored governing shear at the comparison level. In both overturning sheets, the displayed Y numerator in D8 selects `DATA_MDev!I2` from the X spectrum even though the Y spectrum is on row 3. Verify case, moment axis and cut before using these external ratios. [Calculation records](../VERIFICATION_LEDGER.json)

## Seismic pier design on the original building

The building runner follows each of the eight native wall strength combinations to both ends of each panel. An end keeps its own ETABS pier, wall object, storey, elevation and axial interval. The separate Cap_Seis companions supply the amplified horizontal shear control. P2–P5 each have three continuous rectangular panels. At a shared floor the two end resultants remain distinct. The joint strength and friction checks each count the physical plane once per combination.

The original run `RUN-a5a2859f6b874fcdb6180c8c2fb79da8` produced the following maximum ratios. Each pier accounts for 48 physical face–combinations, 24 joint friction checks and 24 strong-axis checks. The 12 panels use 3,312 proposed web crossties. Seventeen distinct selected beam ends enter the strong-axis comparisons.

| Pier | Compression / 0.35 fck Ac | PMM upper | In-plane shear upper | Joint friction upper | 1.2 ΣMr beam / ΣMr wall upper |
| --- | ---: | ---: | ---: | ---: | ---: |
| P2 | 10.69% | 42.74% | 58.05% | 31.19% | 4.15% |
| P3 | 9.17% | 30.81% | 43.60% | 24.28% | 12.64% |
| P4 | 11.31% | 33.40% | 38.38% | 20.47% | 4.68% |
| P5 | 7.95% | 29.81% | 29.96% | 15.98% | 2.41% |

At the P2 base, member 472 Bottom under `Crack_SeisX_UpSoil` governs the PMM bound. Compression spans 284.5857–1,601.1725 kN. The two design moment bounds are 87.3665 and 3,210.1722 kN·m. Its shear maximum occurs under a different combination, `Crack_SeisX_Soil`. The latter gives 1,975.2499 kN against a reinforced resistance of 3,402.5455 kN.

**Design moment and shear.** For each possible base, the engine retains the base moment over the critical height. Above it, the diagram has the slope of the line joining base and roof. It uses absolute upper ordinates to bound all spectral signs and retains a larger actual local demand. It applies the shift to both moment components as a conservative design choice. In Fig. 7.12(c) the upper two-thirds line joins the increased shear at one-third height to half the base ordinate at the roof. The intermediate ordinate comes from linear interpolation between the ends of its own panel. Each floor preserves the larger of the incident ordinates at a jump. Every design face retains the larger local or redistributed shear. Both −5.15 m and rigid-basement +0.00 m bases and both solid and coupled shear limits participate. The interpolation describes the adopted storey diagram. Interior ETABS force measurements at one-third height would independently test that assumption. [TBDY 2018 §§7.6.2.2, 7.6.6 and Fig. 7.12](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf#page=153)

**Axial load and PMM.** Compression is positive and equals minus the native pier P. The engine compares the largest compression to 0.35 fck Ac for each assigned combination. The original project combinations govern this comparison. Project adoption of TS 498 live-load reduction and the retaining-wall classification remain separate decisions. For bending resistance the engine uses the entire interval between native P extrema and both signs of each design moment. Each section uses both boundary cages, both web curtains, displaced concrete and the existing strain-compatible section model. Displayed native forces and moments receive an outward allowance of 0.001 kN or kN·m.

For a symmetric rectangle, the distance from a material point to the compressed corner projected on the strain normal has two nonnegative coordinate terms. On any first-quadrant angle interval, componentwise cosine and sine extrema enclose that distance. Solving axial equilibrium on the two bounding planes brackets the neutral depth over the axial cell. The resulting lower and upper stresses enclose the concrete stress at each point outside the bar disks and the steel stress at each bar centroid. For a nonnegative stress increment the change in each moment is bounded by half the corresponding section dimension times the force increment. The engine uses these two component floors in each angle and axial cell. At least one component must clear the full demand rectangle in every cell. Symmetry covers the other quadrants. This supplies a sufficient numerical upper utilization under the adopted material model. An inconclusive box stays open. The independent check uses strip integration and a separate axial and angular root search on the same cage.

**Reinforcement and connections.** For each panel the proposed Ø12 web crossties connect both curtains at every web bar station and horizontal layer. The engine checks wall proportions, the number of ties and the minimum density in the critical region. The horizontal-joint calculation uses both adjacent faces, all proposed vertical steel, μ = 1 for an anchored joint roughened by at least 5 mm, and reserves steel for any direct tension. It checks both TBDY Eq. 7.19 caps and the TS 500 §8.1.7 cap with fcd limited to 25 MPa. At each floor the strong-axis comparison sums the lower wall Mr over each incident face's entire axial interval. It compares that sum with 1.2 times the sum of the larger signed capacity magnitude of every participating beam end, including its numerical tolerance. Each beam uses its selected rectangular section at zero beam axial force and its physical wall-face design station. The roof is evaluated with the lower wall alone. [TBDY 2018 §§7.6.1–7.6.7](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf#page=147)

A separate section integration checked 576 end/combination/axial-force samples against the PMM upper ratios and 480 strong-direction wall moment samples against the wall strength lower bounds. All 1,056 comparisons lay on the stated side of their bound. The greatest sampled PMM at P2 was 41.73%, compared with the 42.74% upper bound.

In the workspace, 7.2–7.6 show base scenarios, physical panel reinforcement, shear, friction and compression. Check 7.8 shows seismic designs by wall face, 7.9 shows Eq. 7.3 by pier, storey and combination under §7.6.6.2, and 7.10 gives signed gravity results. Column-side SCWB is shown in 4.8 with its own target member, end, physical joint, direction and §7.3.5 decision. Adjacent column ends can refer to the same joint.

Project detailing must establish the actual bar placement, development, laps and horizontal-joint anchorage. The other 18 wall objects include 17 panels in the three multi-panel basement piers xP2, yP1 and yP2, and one object without a bound pier label. The original archived pier table contains combination envelopes. The model has no identified wall overturning section cut or signed modal wall totals about a common reference for the two directions.

**Commercial arithmetic.** In the two ETEX friction workbooks the cached ratios agree with a separate calculation in 47/47 and 32/32 rows. Both use a 0.75% longitudinal steel assumption. The second concrete cap converts MPa to tf/m² with a factor of 100, approximately 1.93% below the SI conversion of 101.972. Applying the TS 500 §8.1.7 cap also leaves the governing ratios unchanged on those 79 examples. The 79 axial-sheet capacities and ratios reproduce under the selected gravity combination 1.4G + 1.6Q. The original project uses its own seismic load combinations for the axial check. The B Block vertical schedule reproduces the steel area of all 32 limbs across 23 pier–storeys. The original pipeline uses the bar count and positions of its proposed cages. [External workbook evidence and original run](../VERIFICATION_LEDGER.json)

## Basement pier yP1

The same whole-building command above also designs the five yP1 basement webs between −5.15 m and +0.00 m. Open workspace check **7.11** for the native pier ends and **7.12** for the proposed two-face reinforcement and pressure strips. The printable report includes both tables. The original force table supplies one six-component resultant at each end of the assembly. Both faces have a native origin at X = 103.494 m, Y = 11.356 m and a local-2 direction parallel to global Y.

The five centreline strips have a nominal area of **9.96 m²**. Their physical footprints cover **9.88 m²** after removing the two inside-corner overlaps. The six 800 × 800 mm columns retain their concrete and bars. The net web concrete between column faces covers **8.36 m²**, centred at X = 103.4928 m and Y = 11.5103 m. ETABS assigns five shells and zero line objects to this pier.

| Panel / ETABS ID | Span between column axes (m) | Vertical bars on each face (mm) | Horizontal bars on each face (mm) | PMM upper | Pressure bending | Pressure cracking shear |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| W27 / 443 | 3.00 | Ø12 @ 200.00 | Ø12 @ 198.08 | 15.18% | 67.89% | 33.95% |
| W28 / 460 | 8.00 | Ø12 @ 200.00 | Ø22 @ 99.04 | 30.83% | 94.31% | 94.68% |
| W29 / 461 | 3.00 | Ø12 @ 200.00 | Ø12 @ 198.08 | 27.91% | 67.89% | 33.95% |
| W30 / 463 | 3.80 | Ø14 @ 200.00 | Ø14 @ 198.08 | 15.32% | 83.27% | 43.38% |
| W33 / 473 | 7.10 | Ø12 @ 196.88 | Ø22 @ 122.62 | 21.44% | 90.57% | 84.03% |

**Vertical section demand.** The five wall strength gravity assignments, eight seismic assignments and two additional static soil combinations give 30 pier-end combinations. For each one the engine distributes the axial force and two first moments in equilibrium over the five clear rectangles. It assumes an affine vertical stress field. It transports the demands from the native pier centroid, includes the offset to the net centroid and allows for the rounding of the source ordinates and origin. For seismic cases it encloses the scalar ranges and both signs of bending. It checks the resulting axial interval and bending bounds against a strain-compatible section for each proposed grid. The resulting 150 web checks include the governing W28 bottom face under `Crack_SeisY_Soil`.

**Horizontal pressure.** ETABS assigns uniform local-normal loads of −33.90 kN/m² under `LC_H` and −21.66 kN/m² under `LC_HE` to each panel. Four assigned seismic combinations include both loads and govern at 55.56 kN/m². The two additional static soil combinations give 54.24 kN/m². The design uses a horizontal one-metre strip spanning the column axes, with zero relative transverse support movement and independent passive end rotations. Under these assumptions the pin and fixed limits bound moment magnitude by `|q| L²/8` and end reaction by `5 |q| L/8`. At W28 the values are **444.48 kN·m/m** and **277.80 kN/m**. The zero-axial flexural resistance uses the two-face grid and the section solver allowance. TS 500 §8.1.3 supplies the diagonal cracking resistance for this strip.

**Reinforcement and applicability.** The C35 and B500C proposal uses 40 mm cover, two curtains and one crosstie at each intersection of a vertical station and a horizontal layer. The project grid uses a 0.0025 minimum ratio in each direction and a maximum 200 mm pitch. TS 500 §§6, 7, 8 and 12 govern the section and detailing checks used here. TBDY §7.6.1 limits its cross-section conditions to walls outside the basement-wall category. The native shell-force distribution, development into columns and slabs, joint/interface shear, torsion, combined orthogonal loading and relative support movement each require additional qualification. The native pier-end tables retain V2, V3 and T for those checks. [TBDY 2018 §§4.5.5, 7.6.1 and 16.11](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf)

**Building scope.** Of the 17 panels in three multi-panel piers, five now have proposed grids. On the 13 assigned combinations, 26 of 78 pier-end PMM checks and 65 of 221 panel pressure checks are calculated. The additional static cases contribute four pier-end and ten pressure checks at yP1. In yP2 one end lacks a registered column support. In xP2 the base elevation changes within the pier. One further wall has no pier label. The four rectangular piers retain their separate seismic design coverage.

## All wall checks in one building run

The original `RUN-b613c30f60fc40cd956be1913ec09192` is available in the local source picker. One workspace action or `run-pipeline --whole-building` executes the existing rectangular and basement owners and the population-wide checks. The overview shows all named pier–storeys and wall 471. For a missing original pier table the wall action can read all piers once through the configured ETABS PID and the existing gateway. A sealed source with the pier table replays offline. The project-original SHA-256 remains `0ce0e970988def9776f9d4804b8897f6e08d6ac3e4937aa72ebec941314cfb15`.

Both physical faces of the 15 pier–storeys retain five assigned static, eight assigned seismic and eight amplified companion outputs. The 390 assigned faces have a net-area axial ratio, an in-plane web reference ratio, and a horizontal joint reference ratio. For the assigned cases the largest respective values are 14.45% at P4/+0.00 Bottom under Grav_Ult, and 30.07% and 13.80% at P2/+0.00 Bottom under Crack_SeisX_Soil. The three basement-only piers have bottom/top clear areas of 11.20/12.40 m² (xP2), 8.36/8.36 m² (yP1) and 9.24/9.24 m² (yP2). The one-sided physical cut integrates the shell footprint once and reserves column concrete. The directional web uses only concrete parallel to the shear, excluding overlaps and perpendicular returns.

The web reference uses two Ø12/200 horizontal curtains. The rough-joint reference uses 0.75% anchored crossing steel, μ = 1.0, and a steel reservation for net tension. A two-component shear bound is compared with Eq. 7.19 and the TS 500 concrete cap. These reference ratios use native cut forces. The design owner supplies the heightwise design moments, Ve, proposed reinforcement and shared joint-face demands for the twelve rectangular pier–storeys. The basement net-web PMM owner supplies a thirteenth pier–storey. Seventeen of the 30 physical panels have proposed schedules. Basement applicability and the project-approved reinforcement remain separate decisions. [TBDY 2018 §§7.6.1, 7.6.6 and 7.6.7](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf)

| P2/+0.00 Bottom, Cap_SeisX | Value |
| --- | ---: |
| Original component envelope, maximum absolute V2 | 1,052.7926 kN / 107.3550 tf |
| Reference horizontal-plane shear bound | 1,053.6654 kN |
| Reference resistance, net tension reserved | 7,091.9615 kN |
| Reference utilization | 14.86% |
| ETEX displayed Ve / Vs1 / Vs2 | 107.35 / 788.05 / 462.11 tf |
| ETEX displayed utilization | 23.23% |

The supplied Quick Result reports 15 passes. All 11 visible demands, governing cap values and percentages reproduce to the displayed precision. In those rows `(3.3 + 0.08 × 3569) × Ac` reproduces the displayed Vs2 in tf. Eq. 7.19 takes fck in MPa. In SI its corresponding cap for C35 and 1.60 m² is 9,760 kN. The ETEX quick-screen computation of Vs1 and the four offscreen results remain unverified. The stored ETEX workbook controls belong to their own project and unit conventions.

Individual RSX/RSY pier bending amplitudes are identifiable without adding section cuts. The model’s linear-add combination radii supply two independent directional equations and 16 consistency checks per moment. At P2/+0.00 Bottom, RSX bending about global Y is 1,267.867 kN·m and RSY bending about global X is 22.329 kN·m. Six whole-storey bottom moment references are retained separately. The building ratio requires its design base and wall population, treatment of coupled walls and a compatible system numerator. [TBDY 2018 §§4.3.4.8, 4.5.3.7(d), 4.5.4.3 and Annex 4B](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf)

At yP1 the five panel grids give ten pressure-end developments and 150 end–combination checks including two additional static soil combinations. Four initial straight-bar details exceeded available column depth. The revised W28 Ø14/39.5 mm horizontal grid gives 88.73% bending and 91.33% cracking shear. Both ends have 740.80 mm required bond, 745 mm specified and 750 mm available. Dedicated Ø12 dowels carry 277.80 kN/m with a 295.04 kN/m resistance at μ = 0.6. The pressure strip has zero relative support translation and zero direct normal tension at this vertical joint. The bar families at all six yP1 support columns satisfy the proposed clearances. The as-built cages, hoops, aggregate and continuous detailing require project confirmation. The wall–column pressure check uses its own interface, steel and reaction. The horizontal construction-joint control appears separately in 7.5 and 7.14.

## Result identity

The earlier frame-only CLI run is `RUN-9b85a9a1dd7b416eab85056c57eae3d5`. The HTTP run is `RUN-aa330b3ed2e34b298fe59f3dc57f3e55`. Their input bytes, full sealed results and all 16 recorded stage payloads match. The printable web view matches the HTML written by its run. The original EDB SHA-256 still begins `0ce0e970988d`. These results use its archived native solution. [Source and results in the verification ledger](../VERIFICATION_LEDGER.json)
