# C104 assigned demands and W22/W23 transfer

The four ETABS meshes give different design demands at C104 (frame 211). Of the 456 assigned force and moment comparisons between the coarse and fine models, 61 meet the existing mesh budget. At the same time all 36 physical W22/W23 free bodies balance. The 2×2 experiment locates most of the selected axial-force change in the horizontal mesh spacing. Both horizontal and vertical spacing affect the selected shear. C104's coupled second-order design remains open.

The existing R08 owner produced these results in `RUN-f21f119300d845d78f27e8345a8bdf54`. The printable report reads the sealed results. C29's separate 24 selected-cage PMM face checks and two conditional R14 closures retain their original run identities. [Evidence and exact source hashes](../VERIFICATION_LEDGER.json)

## Assigned cases and directional base shear

The native design assignment and the expanded ETABS combination definitions agree for three gravity and eight ductile combinations. Every ductile combination consumes RSX and RSY. Four include LC_H and LC_HE. Two gravity combinations include LC_T. Neither LC_EQX nor LC_EQY appears as a leaf in any of the eleven combinations. Their global base shears supply the equivalent-static reference. The local LC_EQX moment below is a diagnostic.

Both translational cases apply 10 m/s² once to the reduced RESP_YATAY spectrum. The acceleration normalizer used to derive 10 and any separately intended project amplification remain unidentified. The table gives additional factors on the as-applied ETABS shears, conditional on γE = 0.9 and on using the indicated whole-model base. A and D round to the same equivalent-static reference of 3,971.0084 kN in both directions. The γE = 0.8 whole-model sensitivity gives 1.000000 in both directions.

| Direction | Mesh A modal shear, kN | Mesh D modal shear, kN | Additional factor A | Additional factor D |
| --- | ---: | ---: | ---: | ---: |
| X | 3,495.2856 | 3,495.4404 | 1.022494 | 1.022448 |
| Y | 3,413.4970 | 3,412.8653 | 1.046993 | 1.047187 |

At the bottom of the +4.50 m storey in the same solution, the static shear is 3,102.1433 kN in either direction. The D modal shears are 2,845.9602 and 2,838.0528 kN. Under γE = 0.9 the additional factor at this cut is 1.000000 on both meshes in both directions. A project scale decision still needs the applicable basement classification, its mass/model boundary, the irregularity decision and the acceleration normalization. The upper-storey cut alone supplies no upper-building-only mass solution. The engine retains both cut hypotheses and leaves the project factors unassigned. [TBDY 2018, §§3.3.1.1 and 4.8.4](https://www.imo.org.tr/Eklenti/89,depremyonetmeligipdf.pdf?0=) · [CSI response-spectrum case definitions](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Response_Spectrum.htm)

All 36 signed base-reaction comparisons and all 144 storey-bottom comparisons meet the mesh budget. The latter include 108 fields from six signed cases and 36 fields from two spectral cases. Horizontal storey masses agree to displayed precision. The maximum centre-of-mass changes are 0.0040 m in X and 0.0046 m in Y. These checks establish agreement at the observed resolution. They leave detailed nodal force allocation unresolved.

## Physical interface and independent equilibrium

At x = 77.40 m, y = 0.40 m, W22 and W23 overlap vertically from −1.50 m to 0.00 m. W22 has 31 edge nodes in A and 61 in D. W23 has two edge nodes in each mesh. The only shared analysis node is 697. No coincident distinct IDs were found on this edge. W21 and W22 have automatic edge constraints disabled and W23 has them enabled on all four meshes. W23's 24 analysis polygons retain the same corner coordinates in A, B, C and D.

The calculation uses unaveraged `AreaJointForceShell` rows for each element corner, with the ETABS point-element axes, global coordinates and a common moment origin O = (74.00, 0.40, −1.50) m. The signed forces below act on the individual walls. The tabulated values are for LC_EQX. [CSI shell joint actions](https://docs.csiamerica.com/help-files/etabs-api-2016/html/e6826614-bf6b-d3cd-a0e5-5d70e06cbc07.htm)

| Interface owner | Fz A, kN | Fz D, kN | My about O, A, kN·m | My about O, D, kN·m |
| --- | ---: | ---: | ---: | ---: |
| W22 | +366.711 | +357.994 | −1,138.830 | −1,149.085 |
| W23 | −181.157 | −202.703 | +626.394 | +706.378 |

On the horizontal cut immediately above −1.50 m the combined LC_EQX M3 changes by −219.533 kN·m. The contributions to that difference are −194.297 from W22, −26.621 from W21 and +1.384 kN·m from C104. On W22 the change in the vertical-force moment-arm term is −194.390 kN·m and the change in the direct point moment is +0.093 kN·m. The force-arm term comes from summing each native corner force at its own x coordinate.

The W23 vertical-edge My changes by +79.984 kN·m. The earlier −194.297 kN·m W22 result belongs to its horizontal transition cut. The report keeps the two surfaces and signs identifiable. Direct support reactions recorded on the sampled interface points are zero. The measured material actions do not uniquely identify a separate force in each generated edge constraint.

For A and D the solver returned every element-corner action on W22 (5.10 m²) and W23 (18.54 m²). Model geometry, unit weight and the two wall pressures give the independent applied loads. For six static cases, the 24 individual-wall balances and 12 balances enclosing both walls all pass. Across the 36 checks the largest force residual is 1.925 × 10⁻⁹ kN and the largest moment residual is 0.000943 kN·m. The check on the thin C104 transition body also passes in each of the six cases in each of the four meshes.

## Common faces and two-factor mesh response

| Mesh | Vertical pitch, mm | Horizontal pitch W21 / W22, m | Connected C104 segments |
| --- | ---: | ---: | ---: |
| A | 50 | 1.00 / 0.85 | 103 |
| B | 25 | 1.00 / 0.85 | 206 |
| C | 50 | 0.50 / 0.425 | 103 |
| D | 25 | 0.50 / 0.425 | 206 |

All variants retain the original fifteen physical load cases. Two archived meshes and independent A/D reads agree in 19,260/19,260 signed frame controls. Recalculated assigned frame ordinates agree with the original A/D archives in 456/456 checks **per mesh**. The four comparison faces are immediately above −1.55 m, immediately below and above −1.50 m, and immediately below −1.45 m. The budget for each component is the greater of 0.05 kN (or kN·m for a moment) and 1% of the larger absolute value. A/D counts within this budget are respectively 18, 22, 10 and 11 out of 114 per face. Overall, 14/72 signed gravity fields and 47/384 native spectral combination extrema meet it. The spectral rows retain their componentwise Max/Min semantics.

| Quantity and cut | A | B | C | D | Vertical B−A | Horizontal C−A | Interaction D−B−C+A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Duct_SeisX_Soil Min, P above −1.50 m, kN | −359.497 | −356.857 | −405.403 | −403.805 | +2.640 | −45.906 | −1.042 |
| Duct_SeisY_Soil Min, V3 below −1.50 m, kN | −80.807 | −81.164 | −59.478 | −58.770 | −0.357 | +21.330 | +1.065 |
| Duct_SeisX Max, V2 below −1.45 m, kN | +126.847 | +101.174 | +106.079 | +81.669 | −25.673 | −20.768 | +1.262 |
| LC_EQX, combined M3 above −1.50 m, kN·m | +275.493 | +186.104 | +113.853 | +55.959 | −89.389 | −161.640 | +31.495 |

The first three rows are C104 frame results from assigned combinations. The last is a combined wall–frame section under the auxiliary reference case. Horizontal refinement has the largest observed effect on the selected P and V3 values. V2 responds appreciably to either refinement. A two-level experiment measures these effects over the tested interval. A further level is needed to demonstrate convergence of the affected design demands.

| Within the fixed component budget | A/B | C/D | A/C | B/D | A/D |
| --- | ---: | ---: | ---: | ---: | ---: |
| Assigned frame, 456 fields | 258 | 286 | 76 | 66 | 61 |
| Signed coupled section, 144 fields | 72 | 81 | 38 | 41 | 36 |

The four native frame arrays independently reproduce all 1,824 assigned ordinates and the signed shell/frame cut integration reproduces all 576 section ordinates. All 432 signed increments from matched soil and temperature combinations reproduce the changes in the native frame combinations to 5.69 × 10⁻¹⁴. The production report includes all 600 rows of four-mesh results, the cumulative edge-force distributions and the three separate free bodies per case.

## Next calculation

At fixed D vertical spacing and unchanged W23, test the next horizontal refinement against D for the identified P and V3 rows. Retain the full fixed population and the signed equilibrium checks. Track V2 independently along the vertical refinement sequence before selecting any governing coupled demand. A W23 conformity change would be a separate topology experiment. Establish the project spectral scale from the adopted basement and normalization basis before applying an extra factor. The available model view provides geometry. Bar continuity and a qualified coupled second-order method still require their own engineering basis. [Current GAP assignment](../ENGINEERING_GAPS.yaml)
