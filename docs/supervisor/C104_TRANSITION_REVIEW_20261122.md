# C104 transition milestone review and W22/W23 exit recipe

**Date:** 22 November 2026. **Reviewed milestone:**
`a89f70f01d39bd2c88cdbcea3efb7292ff7c7f01`.
**Reviewed implementation:** `983571a2920fc4698c6b390d27964bae28c13bb2`.

## 1. Supervisor disposition

Preserve the completed C104 first-order resultant/equilibrium calculation and
the completed **24/24 C29 selected-cage capacity verification**. No concrete
blocking implementation defect was found in the inspected milestone. Fourteen
existing focused tests passed. The reported native calculations remain the
Windows worker's evidence; this reviewer inspected code, published records and
accessible arithmetic, without replaying the private ETABS captures.

C104's measured two-model sensitivity is substantial and correctly remains
visible. The next calculation is the W22/W23 interface at **x=77.40 m**. The
current results locate the main change; they do not yet establish a unique cause.
Both horizontal and vertical meshes changed, and equivalence of the two models'
physical automatic-seismic loading has not been independently established by
the current preparation code. These are discriminating checks for the next work,
not reasons to discard completed equilibrium evidence.

The user-adopted ETABS view remains the only supplied physical geometry/detail
reference. Preserve its identity and the documented layout: C104/W21 below
-1.50 m, C104/W21/W22 above. The model supplies numerical analysis coordinates
and connectivity. The view does not establish bar continuity, lap lengths or
anchorage. Model-based transfer diagnosis can proceed on this evidence while
construction continuity and the coupled second-order method remain separately
unqualified. Do not repeatedly request an unavailable detail to restart the
completed first-order calculation.

The current [calculation record](../engineering/C104_TRANSITION_AND_C29_CAPACITY_20261122.md)
and [ledger](../VERIFICATION_LEDGER.json) remain authoritative for the achieved
numerical scope. This review and the [next experiment plan](c104_review_20261122/W22_TRANSFER_PLAN.json)
refine the active assignment. No GAP status or engineering release is promoted.

## 2. What is completed, and what the counts mean

| Quantity | Recorded result | Interpretation |
| --- | --- | --- |
| C104 thin-body balances | 12/12 | Six signed linear-static cases in two retained models |
| Independent integration | 288/288 components | Two meshes × six cases × four faces × six components; a second integration of the same ETABS solutions |
| Mesh comparisons, all four faces | 36/144 within budget | Numerical proximity between the retained coarse/fine results |
| Mesh comparisons, immediate transition faces | 16/72 within budget | 13/36 below and 3/36 above -1.50 m |
| C29 independent selected-cage capacities | 24/24, no missing/failed faces | Eighteen combination–physical cuts on members 225/142 |
| C29 conditional design closure | 2/87 | Preserved R14 scope; not whole-building acceptance |

The first two C104 rows establish equilibrium and source/result integration on
the retained solves. They do not demonstrate that the same design demand has
converged. Nor does 288/288 mean an independently solved building model.

The common origin is **O=(74.00, 0.40, -1.50) m**. The thin body spans -1.55 to
-1.45 m and uses four physical faces: lower cap, immediately below the
transition, immediately above it and upper cap. Output N/V2/V3 follows global
Z/X/Y; T/M2/M3 are right-hand moments about those axes. C104's native source uses
`Single Value`, step 0, for the six named linear-static cases. Preserve this
identity; C29's nonlinear Step 1 is a different source convention.

The maximum recorded thin-body residual is **0.0000127695312 kN** for force and
**0.0000472528178 kN m** for moment. Equilibrium uses a component-wise budget of
`max(0.01, 1e-6 * largest same-component term)`. The mesh comparison separately
uses `max(0.05, 0.01 * max(abs(coarse), abs(fine)))`, in the component's kN or
kN m units. These are declared numerical study criteria, not code acceptance
limits. Keep them fixed during the diagnosis.

Source: `EV-S03-C104-TRANSITION-20261122`. Its sealed run is
`RUN-7dc0634b19e44a1c8286fb6368f5721d`, result SHA-256
`9a17508e2a1b22f9f22f5215d0dbf68214b1cf468c60db7992903cabc4e3e11b`.
The model-view SHA-256 remains
`e75186bbedb15d618bda5eb59b76da4f43ee157ef3066fad88ab43f8be2903e0`.
Those identities do not imply that the private image or source rows were reread
by this reviewer.

## 3. The moment change is a force-distribution question

Independent Decimal arithmetic reproduces the published governing component
differences, their C104/W21/W22 contribution sums and their fixed tolerances.
For `LC_EQX` at `above_transition`, immediately above z=-1.50 m, M3 changes from **275.492503279** to
**55.959224477 kN m**, a difference of **-219.533278803 kN m**.
The comparison allowance is 2.754925033 kN m. This face is distinct from the
`upper` cap at z=-1.45 m.

| Contribution to the M3 change | kN m |
| --- | ---: |
| C104 | +1.384478885 |
| W21 | -26.620902161 |
| W22 | -194.296855527 |
| Total | -219.533278803 |

W22 contributes approximately **88.5045%** of that signed total change. Its
contribution splits into **+0.092698424 kN m** from point couples and
**-194.389553951 kN m** from force moment arms. W22's net N change is only
**+16.317183865 kN**. Total N therefore cannot identify the moment redistribution.

At the transition plane, common M3 is global My. Retain these terms separately:

`My(O) = sum(My_point + (z-zO)*Fx - (x-xO)*Fz)`.

The `(z-zO)*Fx` term vanishes only for actions exactly at z=zO. At other interface
heights, keep it. Report signed cumulative Fz and its first spatial moment over
the same physical edge segments. A single equivalent force inferred by dividing
194.390 kN m by 3.40 m would be a conditional diagnostic, not a measured W23
force. Read the W23 side and other incident contributors before assigning shares.

## 4. Two causal questions remain unresolved

### 4.1 Both mesh directions changed together

The 50/25 mm labels refer to vertical pitch. The horizontal pitch also changed:

| Direction / member | Coarse model | Fine model |
| --- | ---: | ---: |
| Vertical | 0.050 m | 0.025 m |
| W21 horizontal | 1.000 m | 0.500 m |
| W22 horizontal | 0.850 m | 0.425 m |

The current comparison does not separate vertical and horizontal approximation,
their interaction, or changes in generated interface constraints. It identifies
sensitivity, not a proven singularity or a specific bad connection.

### 4.2 The automatic load basis must be compared physically

The preparation code binds a hashed input deck, case names, linear-static
settings, unit scale, TSC-2018 pattern metadata, story limits and absence of
additional object loads. The local seismic scope check establishes that no
automatic-seismic story application plane lies on or inside the thin body.
These support the local balance calculation.

The current public path does **not** additionally compare the two models'
automatic base/story forces, torsional moments, application locations or the
period/scale basis used to generate them. This review has not found that those
loads differ; their equivalence is an untested causal condition.

For the next comparison, qualify **the same physical loading**, not equal raw
nodal vectors with different DOF counts. Reduce each model's assigned loads to
the same physical story/interface regions and common force/moment resultants.
Compare the mass source, total/story masses, automatic load factors, period
policy and distribution. If a load or another physical input changes, quantify
that difference separately before attributing all response change to the mesh.

## 5. Smallest useful next delivery

### A. Inventory the actual W22/W23 connection

Use the existing retained models and capture route first. Enumerate W22/W23
physical IDs, native shells/points, coordinates, point axes, shared nodes,
coincident-but-unmerged points, hanging nodes, connected DOFs, incident members,
releases, offsets and generated constraints. Record W23's actual plane and mesh;
do not assume that it is coplanar with the current two-wall strip. Match the two
meshes by physical coordinates/topology, not regenerated element names.

CSI describes automatic edge constraints as an interpolation/connection
mechanism that can move load between intermediate and corner joints. It also
identifies consequences for local response of collinear frame/link objects.
This is a relevant **hypothesis to inspect**, not proof that these assignments
caused the present change. Preserve the current model while reading its actual
constraint roster. [CSI Auto Edge Constraints](https://docs.csiamerica.com/help-files/etabs/Menus/Assign/Shell/Auto_Edge_Constraints.htm).

**Exit:** complete physical/native interface membership and constraint/load
ownership, with missing information explicit. Acquire only missing rows if the
archive lacks W23 data. Do not obtain W23's share merely by subtracting W22's
result from a desired balance.

### B. Assemble a two-sided, complete interface balance

Use unaveraged element-specific native force/couple records. Transform both
sides to global axes and transport them to O through the existing
[`joint_action_at_origin`](../../src/tbdy_next/engineering/gravity_wall_cut.py):

`F_O = R F_local`

`M_O = R M_local + (r-O) cross F_O`.

The documented `AreaJointForceShell` fields are point-element-local actions with
case, step, object, element and point identities; verify the installed API
semantics because the cited public page is versioned 2016.
[CSI native shell point actions](https://docs.csiamerica.com/help-files/etabs-api-2016/html/e6826614-bf6b-d3cd-a0e5-5d70e06cbc07.htm).

Retain W22-side and W23-side contributions, other incident members, external
edge loads and constraint transfer. If constraint forces are unavailable, choose
an enclosing physical free body that contains the relevant tied/master/slave
points so their internal transfer cancels; its external boundary must still be
complete. Two arbitrary wall-side nodal sums are not necessarily an isolated
action–reaction pair. Keep cap/edge/corner ownership deterministic.

A separately defined section cut can corroborate the result only after matching
its group, retained side and reference point. CSI's section-cut FAQ distinguishes
those choices; some details are SAP2000-specific and need an ETABS 23.2 check.
[CSI Section cut FAQ](https://web.wiki.csiamerica.com/wiki/spaces/kb/pages/2004950/Section%2Bcut%2BFAQ).
Do not integrate averaged contour values as discrete nodal forces: shell
F11/F22/F12 are force per length, while corner actions are discrete forces.
[CSI shell output definitions](https://docs.csiamerica.com/help-files/etabs/Menus/Display/Show_Member_Force_and_Stress_Diagrams/Shell_Forces_Stresses_Form.htm).

**Exit:** two source-bound six-component interface/free-body tables, cumulative
vertical force and first-moment decomposition, contributor census and unchanged
balance criteria. Begin with controlling `LC_EQX`; retain all six cases for final
qualification. A balanced larger free body with changing wall shares would
localize redistribution, not automatically qualify each wall's design demand.

### C. If needed, separate horizontal and vertical refinement

After source, loading and connection-policy checks, complete this diagnostic
matrix using isolated copies of the same full model:

| Model | Vertical pitch | W21 / W22 horizontal pitch | State |
| --- | ---: | --- | --- |
| A | 50 mm | 1.000 / 0.850 m | Existing |
| B | 25 mm | 1.000 / 0.850 m | Proposed, not run |
| C | 50 mm | 0.500 / 0.425 m | Proposed, not run |
| D | 25 mm | 0.500 / 0.425 m | Existing |

Reuse A and D. Two cross-direction models initially distinguish vertical effects
`B-A`, `D-C`, horizontal effects `C-A`, `D-B`, and interaction `D-B-C+A` for every
same-cut component. Freeze the physical loading, geometry, extraction region,
origin, material/modifier basis and connection policy. Inventory W23's neighboring
mesh explicitly. If its change introduces a third independent factor, disclose
that factor instead of claiming this table isolated two effects.

This matrix diagnoses sensitivity; it does not establish a converged answer by
itself. Add a targeted finer level only if the resulting evidence requires it.
Do not infer Richardson order from two models changing two directions, enlarge
the budget, average incompatible results or relabel a local peak as a stable
design resultant. A finite-region design quantity or regularization choice needs
its own engineering basis.

### D. Use the existing production integration with an explicit extension

The current [`coupled_wall_transition`](../../src/tbdy_next/engineering/coupled_wall_transition.py)
contract supports one upward frame, two coplanar rectangular walls and a fixed
two-level 50/25 mm pair. It does not yet support an arbitrary W23 plane or a
four-model experiment. Extend/version the needed source contract deliberately,
reuse six-action transport and the existing runner/report, and preserve the
current scoped positive calculation. Removing the two-wall assertions alone
would not implement the required three-dimensional interface behavior.

The next handoff must include topology, equivalent physical loading, both-side
actions, complete free-body residuals, unrounded moment decomposition, any actual
mesh experiment and the governing acceptance outcome. Keep failed or missing
required components in the denominator. Record causal hypotheses as resolved,
rejected or still untested; do not replace this delivery with another general
literature summary.

## 6. C29's 24-face capacity subscope is complete

`EV-S06-C29-24-FACES-20261122` extends the previous one-face result by 23 faces.
The record gives 24/24 numerical passes at 18 physical case-cuts, identical
reproduction of the earlier face before rounding, and exact source/result/oracle
hashes. Preserve this completed subscope. The next task is not the old request
to finish those 23 faces.

The maximum production-versus-independent radial-capacity difference is
**0.000471271156 kN m**, below the 0.01 kN m declared comparison budget.
The largest last spatial-refinement change is separately
**0.001411240637 kN m**, also below its 0.01 kN m budget. A small cross-method
difference is not the entire independent calculation's numerical error bound.
All seven published maxima lie within their respective numerical budgets.

The governing face remains member 142, I end / element 142-1 / UPPER side,
`Grav_Ult`. Independent Decimal arithmetic on its published moment components
gives radial demand 256.0407367678566 kN m; division by the recorded independent
capacity 1450.8770407730078 kN m gives utilization
**0.1764730777126651**, or **17.6473077713%**.

The private 24-row file and independent oracle code were unavailable here.
The reviewer checked accessible source identities, aggregate bounds and the
published governing-face arithmetic, not all private face inputs or the oracle's
implementation independence. Next S06 domains are axial-limit cases, other
sections/members and independent full-design verification. Construction cages,
anchorage and overall normative acceptance remain separate from these two
selected model cages.

## 7. Verification, retained gates and publication

This review ran **14 existing focused tests**, all passing without skips:
four transport/seismic-scope tests, eight story-source tests and two sealed-report
tests. Exact commands, import path, test IDs, source hashes and independent
arithmetic are in [REVIEW_EVIDENCE.json](c104_review_20261122/REVIEW_EVIDENCE.json).
The complete native transition run and twelve negative controls remain the
separately recorded private worker evidence; they were not rerun here.

The recorded Windows suite is **1,705 total Python tests = 1,704 passed + one
symlink-permission skip**, plus **11 JavaScript files**. Its tested tree matches
983571a, and `src/tests/tools` have no differences between that commit and
a89f70f. No fresh full suite, live ETABS or new analysis is claimed by this review.

The immediate measured numerical obstacle is C104 mesh sensitivity. GAP-006
also retains construction connection/continuity evidence. GAP-009 retains
effective stiffness, restraint, creep, varying-axial applicability and a qualified
coupled second-order path for 14 columns. Those tasks may progress alongside
the interface diagnosis. The producer preserves
`CONSTRUCTION_CONTINUITY_UNVERIFIED` and
`COUPLED_SECOND_ORDER_DEMAND_UNQUALIFIED`; keep them until their own evidence is
available. S00, S02, C104 equilibrium and the C29 24-face verification are preserved.

`EV-SUPERVISOR-C104-MILESTONE-REVIEW-20261122` appends this review after the 90
existing ledger records. [Validation](c104_review_20261122/VALIDATION.json)
checks record preservation, unchanged GAP statuses, document links and hashes.
The publication changes documentation only and grants no whole-building release.
