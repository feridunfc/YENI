# Original building calculation and local handoff — 2026-11-21

## Next implementation deliverable

Execute [the C29 calculation completion task](engineering/C29_CALCULATION_COMPLETION_TASK_20261121.md):
extend the existing displacement consumer to six DOFs and complete the source-bound
revised story producer; calculate the 12 finest-mesh axis factors, all 24 common-side
revised TS 500 moment/PMM rows and the full-span deformation outcomes through
R08/R14. Use the named reference examples with the actual production owners.
The task was inspected against full commit
`d85c6e8670b65ba2236cc5a0960e7e59720a8dd0`; preserve newer local work.
This assignment does not change the original-source 2/87 conditional result or
close GAP-009. No engineering tests or live analyses were rerun for this brief.

## C29 common physical cuts and deformation comparison

The independent audit reproduced the archived original-source Nmax run
across all 16 sealed stages. The separate R08 method comparison now uses
its 18 physical case-cuts as the reference for the finest matched-EI
model. Interface cuts keep both refined element sides. The report places
each model's local axial force, the first-order axial maximum, both
orders' moments, design moments and selected-cage PMM at the same location.
Within the eight-part model, the largest direct second-order M2 increments
at the 18 reference cuts are 2.0011 kN·m at the 225 I face and 0.7465 kN·m
on the upper side of the 142 midpoint, each under Grav_Ult.

At the shared 4/8-part nodes, the maximum transverse chord-relative
vector difference is 4.7224e-6 mm (225) and 8.0358e-7 mm (142). The
0.01 mm common-node criterion passes for both members. The observed
peak under Grav_Ult shifts from 3.3375 m to 2.78125 m for 225 and
0.950 m to 1.425 m for 142, measured from the I face. These are samples
at different native joints. The full-span peak between joints is unverified.

The original-source result is 2/87 conditional numerical closures. GAP-009
still requires qualified per-axis critical load and effective-length data
and concurrent column–wall compression from the revised model. The
source-qualified inter-node deformation result is also pending.
See `EV-C29-COMMON-CUT-COMPARISON-20261121`.

## Original C29 with explicit self-weight Nmax

Windows replay `RUN-be9d8258796f4dfca1a3609453e94e53` uses the frozen parent of
the C29 matched-EI scenario. Three signed gravity combinations at three
physical cuts per member give 18/18 eligible and consumed cuts. The largest
absolute primitive-case axial superposition residual is 5.084e-13 kN. The
coefficient uses each combination's Nmax. Eccentricity and PMM use each
cut's local N. Both parts select 32Φ16 and Φ10/90 in this scenario.

| C29 member | Grav_Ult Nmax (kN) | Governing static PMM | Spectral PMM bound | Capacity shear / TS 500 resistance | Capacity shear / zero-concrete resistance |
| --- | ---: | ---: | ---: | ---: | ---: |
| 225 | 3240.466 | 0.213469 | 0.356908 | 0.538602 | 0.757645 |
| 142 | 2158.045 | 0.295470 | 0.353906 | 0.578302 | 0.793044 |

Grav_Ult at each I face governs the signed static PMM. R14 binds design
shear for all eight distinct connected beams. Joint 40 has 16/16 seismic
axial interval checks in each direction. The minimum sampled normalized
SCWB ratios are 2.187944 in X and 3.263833 in Y. R14 records 2/87
conditionally numerically closed, with both C29 members carrying the
explicit axial idealization acceptance gate.

GAP-009 remains partial. The Nmax idealization requires engineering
acceptance. The revised-stiffness gravity comparison still needs qualified
same-run story inputs and peak local deformation. Recover the exact private
run and the next calculation from `EV-C29-SELF-WEIGHT-NMAX-LOCAL-20261121`.

## Executable variable-axial design slice

The inspected integration base is `eb6328290a66484c8ddbc8ba37158be270b8fc5d`.
The new `work/c29-variable-axial-slice-20261121` milestone extends the existing
runner: explicit self-weight Nmax inputs now reach the actual local
magnification, selected-section PMM and R14 consumers. The original source
vectors and each section's local N are retained. No new solver or ETABS route
is introduced.

The public normal-pipeline example calculates two columns, four beams, thirty
signed case-cuts and sixteen unique interior-joint SCWB comparisons. The same
source closes zero columns under the default applicability and two conditionally
under the explicit idealization. Both retain engineering acceptance pending.
The example is `CONTRACT_FIXTURE / GENERATED_OFFLINE_NOT_ETABS`; it is not an
original C29 replay. Fresh commands, results and tested-file identities are in
[the verification record](engineering/variable_axial_slice_20261121/VERIFICATION_RESULTS.json).
The final Linux run passed 1,671 Python tests and 11 JavaScript test files, with
zero Python skips. The isolated wheel passed 519 overlapping tests. Normal
CLI/Web replay is `IDENTICAL`; the existing 44-record golden bank remains
33 numerical matches, 7 insufficient-source records and 4 interpretation
differences. These are fresh runs for this milestone, separate from the older
private Windows results below.

The Windows continuation above prepared the explicit scenario from the
finalized original-source C29 receipt and ran the existing pipeline.
Use the [exact continuation commands](engineering/VARIABLE_AXIAL_SLICE_20261121.md#continue-the-actual-c29-from-its-sealed-original-source).
This continuation reuses the current selected TS 500 inputs; it does not require
another ETABS solve or replace the matched-EI experiment below. Preserve any
newer local basis and use its actual receipt. The published implementation's
public fixture record covers the remote environment. The Windows replay above
records the original-building result.

GAP-009 remains `PARTIAL`. The numerical idealization awaits acceptance for
variable axial force. The public fixture checkpoint predates the Windows
calculation above. See `EV-VARIABLE-AXIAL-NUMERICAL-SLICE-20261121`.

## C29 matched effective stiffness and mesh refinement

The private ETABS study finished 18 cases. Each 2, 4 and 8 part mesh used
the same three full-vector first-order/P–Delta pairs at C29 members 225 and
142. Both local bending axes used the existing selected TS 500 EI of
2.2683142345e14 N·mm². The native material modulus, section inertia and
section modifier give an object modifier of 0.2792206663. The experiment
uses the original stiffness basis for neighboring frames, slabs, walls and
the foundation. The original support joints, frame releases, axes and end
offsets preserve clear lengths of 4.45 m and 3.80 m. The final SHA-256
readback verifies the original EDB.

The normal R08 → R14 comparison retains the original 18-cut control and
separately keeps every signed refined cut, including both sides of internal
junctions. The 2, 4 and 8 part levels have 30, 60 and 120 paired cuts per
member. First-order control, failed PMM assessments and unresolved cuts are
reported separately. Original selected TS 500 design demand is reproduced.

At eight parts, Grav_Ult governs both members on the I physical face.
ETABS P–Delta PMM is 0.118455 for 225 and 0.169611 for 142. All 420 refined
cut assessments resolve within the selected section capacity surface.

Common signed forces, full-mesh force extrema and PMM meet the preset
numerical tolerances from four to eight parts. The comparison uses 1%
relative tolerance and absolute tolerances of 0.1 kN, 0.1 kN·m, 0.001 PMM
and 0.01 mm. The sampled peak node-chord
bow under Grav_Ult changes from 0.9912 to 1.0204 mm (225) and from 0.5430
to 0.5693 mm (142). This exceeds the preset bow tolerance. At the shared
nodes the transverse chord-relative vector changes by at most 4.73e-6 mm
and 8.04e-7 mm respectively. Both peak sample locations move to joints
added in the eight part mesh. The numerical mesh outcome remains
`OUTSIDE_NUMERICAL_TOLERANCE`.

On the revised models, finish the local shape comparison on a denser common
physical grid or with independently verified within-element displacement.
Supply the same-run, simultaneous column and wall compression, supported
critical-load scope and axis-specific effective length factors to run the
revised TS 500 PMM at the exact same cuts. That matched-EI scenario recorded
0/87 numerically closed.
See `EV-C29-MATCHED-EI-REFINEMENT-20261121` for the native and sealed run IDs.

## C29 matched ETABS gravity solutions

The selected calculation remains the existing TS 500 magnification path.
The ETABS pair is a signed comparison input to R08 under the same selected
cage and physical cut identities. R14 records its comparison outcome beside
the selected calculation. The variable-axial gate uses observed signed PMM
cut forces independently of the self-weight breakdown and archived-order log.

The private copy ran `Grav_Ult`, `Grav_TempNeg` and `Grav_TempPos` as six
full-vector static solutions. For each combination the two nonlinear-static
case definitions differ only in geometric nonlinearity, from none to P–Delta.
At all 18 C29 cuts the control reproduced the original six force components.
R08 compares the P–Delta vector on the same cage using minimum eccentricity
and unit amplification, alongside the selected TS 500 design moments.

ETABS used the original stiffness and one analysis frame element per C29
member. The paired scope establishes the effect of changing analysis order
under that setting. ETABS EI was 8.123733e14 N·mm² in both local axes.
Selected TS 500 EI was 2.268314e14 N·mm². The native first-order control
residual was below 7.2e-8 kN and 3.9e-8 kN·m in all six components.

| C29 member | ETABS P–Delta governing cut | ETABS PMM | Selected TS 500 PMM |
| --- | --- | ---: | ---: |
| 225 | Grav_Ult at 2.225 m | 0.130354 | 0.213469 |
| 142 | Grav_Ult at 0.000 m | 0.272729 | 0.295470 |

The largest native moment changes were 1.250076 kN·m in M2 and 0.288289
kN·m in M3, both at the 225 base under Grav_Ult. Local P–delta mesh
convergence and the variable-axial method stay open in R14. The spectral
scope and joint 40 SCWB remain as recorded in the prior calculation. See
`EV-C29-PAIRED-GRAVITY-20261121`.

Use a matched stiffness basis and a converged representation of local
P–delta for any subsequent numerical qualification. The selected TS 500
story method still requires concurrent column and wall compression and the
qualified critical-load population. C104 retains its separate wall
reinforcement and connection dependency.

## C29 project roles, archived solution order and gravity equilibrium

The C29 force request still carries the exact assigned gravity and ductile
groups. The complete same-capture catalog resolves all seven configured upper
project roles. The declared C29 calculation uses six roles, including the
capacity and joint roles on the existing `Cap_Seis*` family, drift on
`Crack_Seis*`, and weight on `WGHT`. Wall design remains outside that scope.
Model, demand and engineering approval remain open.

R03 reads the supplied archived ETABS log and model export. It reconciles all
15 native cases, 100 modal modes and both spectrum parent relations to the
frozen source. EDZ is configured to use the preset. The export shows preset
P–Delta disabled, and the completed solver blocks show zero-state stiffness.
The order record flows to PMM and R08. Independent model-generation approval
remains pending. The solver input artifacts are kept in the private input
archive and sealed reports retain their binding digests.

At the three physical cuts of each C29 member, the primitive signed cases
reproduce the three assigned gravity combinations. LC_DL supplies the entire
observed axial gradient. The model export has a unit weight of 24.992619
kN/m³, the 0.80 × 0.80 m section has weight modifier 1, and the Grav_Ult
factor on LC_DL is 1.4. The observed factored gradient is 22.393386624 kN/m
in both members. See `EV-C29-R03-ORDER-AXIAL-BALANCE-20261121`.

The sealed replay retained the prior PMM and shear utilization and the joint 40
SCWB intervals. It calculated 18 signed PMM cuts, 48 spectral case-cuts and
32 direction-combination shear results for C29. R14 remains partial for all 87
columns. Both C29 members retain the variable-axial method qualification gate.

The newer comparison above ran the exact three gravity coefficient vectors.
Keep joint 40's interval SCWB result and the nonconcurrent spectral-corner
scope during the subsequent method qualification.

## Windows replay: C29 second-order sensitivity through the normal pipeline

The inspected feature commit `32b3158400be1e7c822d40099edbb016ab49c108`
is directly based on the then-current baseline `0f1a809`. Windows rediscovery
ran 1,640 Python tests with one OS symlink skip and passed all 11 JavaScript
test files. The public CLI fixtures repeated 1/1 and 2/2 conditional numeric
column closure. The 44-row report gate reproduced 33 numerical, seven
insufficient-source or method, and four interpretation differences.

Two frozen-source runs used the existing CLI and the same sealed original
ETABS parent. The control retained the existing design policies. The second
added a C29-only sensitivity using the verified physical spans, calibrated
axis-specific K, Rm=1, Cm=1, Eq. (7.21), the effective-length reading of
Eq. (7.29) and unit TBDY global factors. Each member computed nine signed
static cut results and 24 assigned spectral case-cuts (192 sampled corners).

| C29 member | Clear length | K M2 / M3 | Max signed PMM | Max spectral corner PMM |
| --- | ---: | ---: | ---: | ---: |
| 225 at +0.00 | 4.45 m | 1.623 / 1.646 | 0.213469 | 0.356908 |
| 142 at +4.50 | 3.80 m | 2.060 / 2.137 | 0.295470 | 0.353906 |

Both R08 records report `ADOPTED_SECOND_ORDER_CALCULATED_NOT_PROVEN`.
The sensitivity includes all frame-column compression in the story totals,
uses the available frame-column critical loads, and leaves wall-shell
compression and coupled critical loads open. At the three `Grav_Ult` cuts,
the compression varies by 99.651 and 85.095 kN respectively. TS 500 §7.6's
approximate constant-axial-force premise still needs engineering resolution.
Spectral corners are sampled from nonconcurrent envelopes. R10 evaluated all
16 assigned shear direction-case pairs per member without D reduction. Maximum
selected-cage shear resistance utilization was 0.520544 for 225 and 0.654872
for 142. The interval SCWB reference at shared joint 40 was sufficient in both
directions. R14 remains partial for all 87 columns.

The newer checkpoint above records the R03 role and order results. C104 still
requires the W21/W22 connection and reinforcement basis to carry the coupled
section through the wall transition. The actual-owner alpha-below-one example
remains open. See `EV-C29-ADOPTED-BASIS-LOCAL-20261121` for the initial replay
identities.

## Remote implementation: adopted inputs consumed by the normal design path

Feature branch: `work/vertical-slice-adopted-basis-20261121`, based on the inspected
`baseline/local_import` commit `0f1a809299ed0dbb6e0ecfde77be0642e1771ce3`.
This remote task did not inspect unpublished Windows changes or replay the latest
private original-building source. Preserve the original-model checkpoints below.

The existing runner now consumes explicit source-bound K/Rm/EI/sway decisions in
the selected R08 calculation. R03 admits declared calculation assumptions with
complete native definitions and design groups while retaining engineering
acceptance. R14 qualifies that exact source/cage/result context for conditional
numerical completion. Native failures and missing cut populations still block.
No second solver, runner or ETABS connection was introduced.

Public synthetic examples run all actual owners from source to sealed report:
one column/two roof beams and two columns/four beams with an interior joint.
The latter has 30 signed cut rows and 16 actual interior SCWB comparisons.
An explicit Phi10/90 trial remains partial; Phi12/70 completes the two-column
numerical slice. These are `CONTRACT_FIXTURE` examples, not original-building or
live-ETABS verification. Engineering release remains `NOT_READY`.

Other implemented corrections preserve scoped alpha applicability beside an
unresolved member, permit existing bounded cage reselection when alpha is not
required, propagate a proven native brittle-shear exceedance, and withhold the
isolated-column method for possible nonmatching interior wall contacts.
An actual-owner numerical stress test also triggers one native-demand cage retry
from 32Phi16 to 34Phi16, with final PMM utilization 0.9886972. It is a declared
K=5/Rm=1 fixture, not a physically approved restraint model or alpha-below-one test.
The fresh golden result is 33 numerical matches, seven insufficient-source/method
records and four interpretation differences among the same 44 IDs. Exact full
test results, hashes and commands are in [the implementation verification](engineering/vertical_slice_20261121/VERIFICATION_RESULTS.json).
The 73-control recipe map, 44 report comparisons and historical 333 arithmetic
assertions remain separate populations.

The Windows checkpoint above records the subsequent original-model replay and
the remaining calculation inputs.

Read [the implementation report and runnable commands](engineering/VERTICAL_SLICE_20261121.md).
Ledger entry: `EV-VERTICAL-SLICE-ADOPTED-BASIS-20261121`. The report identifies
what was directly executed and what remains `NOT_RUN`.

Start each assignment at [AGENTS.md](../AGENTS.md). The
[worker handoff](context/WORKER_HANDOFF_20261119.md) and
[project charter and source guide](context/PROJECT_CHARTER.md) are available
in a GitHub checkout. Follow the [November 18 full recipe](engineering/reference/recipe_20261118/delivery/RECIPE.md)
and its [six-step calculation sequence](engineering/reference/recipe_20261118/delivery/PRIORITY_CHAIN.json).

## C104 common-joint mesh and assigned spectral sway

The authorized C104 Save As solved all 15 original load cases at both
50 and 25 mm vertical mesh steps. All 103 and 206 C104 segments share
exact nodes with W21/W22, respectively. The 25 mm mesh balances all six
signed loads at 112 generated interior nodes. The largest component
residuals are 2.87 × 10⁻⁹ kN and 2.34 × 10⁻¹¹ kN·m. At elevation
−0.75 m on the lower face, Duct_SeisX Min V2 is −4.08 kN in the
original, −256.19 kN at 50 mm and −276.31 kN at 25 mm. Across the six
matched cut faces, refinement changes V3 by up to 50.46 kN and torsion
by up to 32.09 kN·m. The first three modal frequencies change by at most
0.013% between the two common-joint meshes.

The first-order C104 shear screen covers all 356 reported cut sides
and eight assigned seismic combinations on the 25 mm mesh. It finds a
maximum Vd of 292.99 kN and Vd/Vsw of 0.208 for the 32Φ16 cage with
Φ10/90 ties. Sampled first-order spectral PMM utilization is 0.331,
0.327 and 0.325 for the three models. These checks use the stated
candidate reinforcement and cover first-order actions and sampled PMM
points. R10 withholds capacity shear based on an offset proxy wherever
the physical record shows interior wall coupling. R14 carries this as
an unresolved two-axis capacity shear check.

The supplied model view matches the native parts at C104. W21 runs
from −5.15 to 0.00 m and W22 joins C104 from −1.50 to 0.00 m. For
the centered 80 × 80 cm column and 40 cm walls, the geometric union
counts each overlap once. Its gross area is 3.28 m² below −1.50 m
and 4.48 m² above. Its corresponding centroidal inertia about Y is
16.669 and 38.475 m⁴. These are geometry inputs for the conditional
coupled section. The reinforcement and connection detail are needed
for section strength and effective stiffness. The `xP2` output includes
six shell objects (W21–W26). C104 has a separate frame assignment.
Preserve the specific C104/W21/W22 cut population when comparing actions.
See `EV-GAP006-C104-REFINEMENT-20261121`,
`EV-GAP006-C104-SECTION-PROFILE-20261121` and
`EV-R10-WALL-COUPLED-CAPACITY-SPAN-20261121`.

R08 retains the native cut evidence for the 14 wall-coupled columns and
withholds isolated Euler loads, moment magnification and magnified PMM
for those members. C104's signed axial force changes across interior
nodes where load transfers to the wall. TS 500 §7.6.2 limits the
approximate method to columns with invariant section and axial force
along the height. The normal pipeline replay evaluates the other 73
members and carries the coupled-model requirement into R14.
The alpha design feasibility check now flags those same 14 missing
second-order references.

The eight original assigned seismic combinations now have 48 story/axis
sway references and 1,752 local magnified moment boxes for 73 columns.
The sensitivity uses `Rm = 1`, conditional restraint scenarios and upper
frame-column compression. It gives no wall-frame critical-load credit.
Both readings of Eq. (7.29) use the ordinary maximum branch in the 3,504
member-axis evaluations. C29 utilization reaches 0.362 for 225 and 0.356
for 142 over 576 capacity samples. The samples use axial endpoints and
midpoints. The factors remain separate from TBDY global amplification.
The original ETABS solver log confirms that all 12 named static cases and
the 100-mode Ritz case used unstressed stiffness. RSX and RSY inherit
that modal basis. Each of the 11 assigned combinations uses those cases.
Use `EV-GAP009-ORIGINAL-FIRST-ORDER-20261121` as the first-order reference.
GAP-009 still requires second-order demands for the 14 coupled members.
The design run must bind the chosen model, stiffness and creep basis,
and consume the appropriate order of demand once.

## Wall contacts, complete cut census and C29 story magnification reference

The original mesh, output assignments and offsets independently define
402 column cuts. All 957 member/combination cut inventories and their
7,638 native force rows match, including the element sides at shared
stations and the expected signed or Min/Max step population. This
resolves the independent cut census for the archived original model.

At +4.50, the 14 previously unbound columns now have 3.80 m clear length.
Their basement walls end at the lower slab joint and the upper beam
soffit matches the native J cut. The model now supplies standalone
clear lengths for 73 columns. The other 14, all at +0.00, have wall
mesh contacts inside the column height. Thirteen share an edge with
the wall shells on every frame segment. Member 211 (C104) shares five
of eight edges. A read of the unchanged original ETABS model confirmed
automatic edge constraints on W21 and W22 and placed all three
nonmatching segments on those shell edges. The three signed control
cases provide a displacement comparison. The internal constraint
equations and the local force-transfer basis for the coupled members
remain open. See `EV-GAP006-C104-AUTO-EDGE-20261121`. These 14 members
retain their native cuts and require a coupled wall-frame assessment.

The eight signed static load sets give 48 story/axis comparisons using
TS 500 Eq. (7.27)–(7.28) as a reference. Each numerator includes all
frame-column compression. At +0.00 only the 18 columns with independently
verified spans contribute critical-load credit. The assumed stiffness
uses the `Rm = 1` sensitivity endpoint, bare beam webs, and the largest
of the checked effective-length scenarios for each member. The
largest story factor in each direction is:

| Story | X | Y |
| --- | ---: | ---: |
| +0.00 | 1.526948 | 1.615136 |
| +4.50 | 1.065127 | 1.063191 |
| +9.00 | 1.030506 | 1.030045 |

Using the measured mat reference at C29 and the same signed vectors
and factors, the selected-cage PMM calculation stays within the reference
surface at all 48 cuts across both segments. The governing utilization
is 0.399996 for 225 and 0.396161 for 142. The assigned spectral design
scope still requires a qualified analysis basis, an adopted creep
convention and qualified wall-frame stiffness. See
`EV-GAP006-WALL-MESH-AND-CUTS-20261121` and
`EV-GAP009-SIGNED-STORY-MAGNIFICATION-20261121` in the
[verification ledger](VERIFICATION_LEDGER.json).

## C29 mat rotation and calibrated effective-length reference

The approved second Save As ran four signed 1 kN·m cases at node 934.
ETABS staged analysis activated only the two original mat areas and used
their original soil springs. The horizontal translations were zero.
The applied moments and base reactions balanced to within 9 × 10⁻¹³
kN·m. The isolated mat's rotational stiffness with the orthogonal moment
free was 1,844,987 kN·m/rad about X and 1,903,671 kN·m/rad about Y.

At joints 40 and 6, the connected floor strips changed the flange
comparison for C29. The four full-span single-sided checks and the
three double-sided checks use the TS 500 §6.3.6 inner-span reference
`lp = 0.60L` and its geometric caps. One beam has no verified
continuous strip. The lower column uses the measured mat rotation
in an elastic prismatic sway model with a `3 Ec Σ(Icr/L)` beam-end
reference at joint 40. The upper column uses TS 500 Eq. (7.15).

| C29 member axis | Reference k | Effective length (m) | Slenderness |
| --- | ---: | ---: | ---: |
| 225 M2 | 1.62265 | 7.22081 | 31.2670 |
| 225 M3 | 1.64582 | 7.32389 | 31.7134 |
| 142 M2 | 2.05975 | 7.82706 | 33.8921 |
| 142 M3 | 2.13676 | 8.11970 | 35.1594 |

All four references exceed the sway-permitted neglect limit of 22.
The Eq. (7.29) readings agree in the 16 checked signed instances.
Original primitive column shears reproduced the 24 signed story
references. Twelve signed Eq. (7.23) ratios have opposing permanent
and total shears. Determine their creep convention before applying
them to stiffness. The adopted member stiffness and complete story
Eq. (7.27)–(7.28) sums are required for final moment magnification.
The maximum checked column compression subtotals at the common I cuts
are 47,489 kN at +0.00, 36,570 kN at +4.50 and 17,665 kN at +9.00.
At this checkpoint, both lower stories had 14 unbound column clear lengths.
See `EV-C29-MAT-ROTATION-CALIBRATED-LENGTH-20261121` in the
[verification ledger](VERIFICATION_LEDGER.json).

## R08 mat horizontal boundary

The existing ETABS gateway read the restraints and local axes of all 119
column-end joints. R08 matches the point IDs to the native mat mesh and
the same-source spectral displacement rows. The original model has 32
mat-supported columns. All 32 restrain global UX and UY at the base.
R08 calculates all 64 corresponding endpoint differentials because the
base value is zero in each matching response-spectrum case. For lower
C29 (225), joint 934 to 40, the values are 1.956 mm in RSX/X and
1.931 mm in RSY/Y. The normal report and R14 carry the boundary result.

The fresh run reproduced 7,638 assigned native force rows and 1,392 R10
case/axis shear calculations. R14 still records 11 open conditions for
59 columns and 12 for 28.
See `EV-R08-MAT-HORIZONTAL-BOUNDARY-20261121` in the
[verification ledger](VERIFICATION_LEDGER.json).

## TS 500 sway reference on the private ETABS copy

Under matched vertical loads and signed X/Y lateral loads, ETABS solved
eight first-order, eight P-Delta and eight linear-control cases. The
linear controls agreed at all 1,392 column ends across the eight load
sets. The absolute difference exceeded 5% of the first-order moment in
105 of 2,784 comparisons, with at least one exceedance in each of the
six occupied story directions. C29's upper column 142 was within the
limit in 32 of 32 comparisons. The lower column 225 exceeded it at the
mat end in M3 for both negative-Y cases.

These results do not qualify the sway-prevented shortcut under TS 500
§7.6.2.1 for the tested load sets. The reference cases used the original
`Grav_Service` and `Grav_Ult` factors with signed `LC_EQX` or `LC_EQY`.
The assigned R08 spectral design demand retains its own approval gate.
Use `EV-R08-TS500-PAIRED-STATIC-20261121` for the classification check.
The current calibrated effective-length reference above advances the
sway-permitted route.

## C29 TS 500 effective length reference

R08 now calculates the two directional effective-length scenarios from the
framing at joints 40 and 6. The stiffness ratios use the native member axis
lengths. The effective length uses the verified clear span. A beam web
scenario and an assumed flange comparison bracket the two chosen section
models. At joint 934 the fixed and hinged cases show the sensitivity to
the unresolved mat restraint. These scenarios also give Euler loads at
`Rm = 0` and both readings of Eq. (7.29) for the existing signed combinations.
See `EV-C29-TS500-EFFECTIVE-LENGTH-20261121` in the
[verification ledger](VERIFICATION_LEDGER.json).

For upper C29, the sway-permitted reference has `k = 1.827489–2.380599` and
`lk/i = 30.070384–39.171533`. The sway-prevented reference has `k = 1.00`
and `lk/i = 16.454483`. Both C29 segments require a magnification calculation
in every tested sway-permitted case. In 36 signed case comparisons, both
Eq. (7.29) length readings give the ordinary branch. The reference scenarios
leave the adopted sway, restraint and creep inputs open.

The physical story scope accounts for all six occupied story directions.
+14.5 is a verified empty story. The original archive verification is
indexed by `EV-C29-MAT-HORIZONTAL-SUPPORT-20261121`.

If sway is independently qualified as prevented, §7.6.2.2 permits
`k = 1.0`, giving 19.269065 and 16.454483 for C29's two slenderness
ratios. Eq. (7.13) has separate uncracked-section and load prerequisites
for a first-order stability analysis.

## Column support faces, local slenderness and shear

The existing Windows gateway captured the frame and area insertion points,
slab properties, floor object connectivity and analysis area connectivity on
the original locked model. The capture reproduced all 7,638 assigned force
rows. The normal R10 and R08 stages now use one model clear length whenever
the lower support top and upper soffit also match their own native force cuts.
The projection accounts for ordered floor polygons spanning multiple records.
For C29 the model text provides a separate geometry check. See
`EV-C29-PHYSICAL-CLEAR-LENGTH-20261120` in the [verification ledger](VERIFICATION_LEDGER.json).

| C29 segment | Lower support top (m) | Upper support soffit (m) | Clear length (m) |
| --- | ---: | ---: | ---: |
| 225 | −5.15 | −0.70 | 4.45 |
| 142 | 0.00 | +3.80 | 3.80 |

Four analysis shell elements of the 0.90 m mat share the bottom column
node. Each of the other two C29 nodes has four 0.70 m beams assigned
Top Center. The three slabs connected to the shared column node are
F13, F15 and F30 at +0.00. The audited F29 assignment belongs to +9.00.
All 32 C29 case/axis shear values agree with the previous calculation.
The reference slenderness scenarios use the same physical lengths.

This earlier R08 run resolved the model clear-length gate for 59 of 87
columns and identified the two wall contact groups subsequently
reconciled above. The engineering release is `NOT_READY`.

The offline suite passed 1,552 Python tests and 11 JavaScript test files
with one Windows skip. The clean installed wheel passed 401 tests.

GAP-006 records the later disposition of those wall-connected columns.

## Previous assigned seismic column shear calculation

The R10 selected-cage result now evaluates the eight assigned seismic combinations
for both local axes of all 87 columns. All 1,392 checks meet the resistance and
TBDY Eq. (7.7) brittle limits with unreduced column end moments. The offset-based
clear lengths and selected reinforcement define this result. Both ends have
continuous upper bounds on moment resistance over their own axial intervals.
The analysis shear floor includes both native extrema at every captured cut.
The eight model-defined capacity controls scale horizontal spectrum terms by 2.5.
All 12,864 control shear values reproduce the separate native ETABS read to within
1.8e-13 kN. The assigned check uses full capacity moments. The report also gives
the D-bounded value for each case and axis. See `EV-C29-SPECTRAL-SHEAR-20261120`
in [the verification ledger](VERIFICATION_LEDGER.json).

For C29 the largest unreduced shear bounds are 1,007.794567 kN on the lower
column and 1,053.485642 kN on the upper column. The maximum case-matched Ve/Vr
ratios are 0.520544 and 0.654872. The upper column's governing ratio occurs in
a different combination from its maximum shear. Its axial interval can cross
the low-compression threshold, so the conservative check uses the selected ties
alone. That checkpoint reduced the original building's shared R14 open gates
from 13 to 12. GAP-016 has 20 numerical matches, 20
insufficient-source comparisons and four interpretation differences.
The offline suite passed 1,545 Python tests with one Windows skip and
11 JavaScript test files. The isolated installed wheel passed 394 tests.

The reference provisions are in [TBDY 2018, pp. 118–120](https://fakulte.adu.edu.tr/muhendislik/personel/uploads/eakin/deprem-yonetmeligi-2018-1576678666.pdf#page=140).

## Previous story calculation and R14 projection

The existing Windows gateway read two supplementary linear static earthquake
cases on the locked original model. Each returned 402 signed frame-force rows
for 87 columns. All 7,638 native rows in the eleven assigned combinations
match the preceding capture. Output selection was restored. The exact input,
two CLI replays and independent arithmetic are indexed under
`EV-STORY-STATIC-APPLICABILITY-20261120` in [the ledger](VERIFICATION_LEDGER.json).

At story +4.50, the X-direction reference uses all 32 physical columns at
the common I-end cut. Global X is local V2 for 31 columns and negative V3 for
one column rotated 90 degrees. Each of the three assigned gravity combinations
is paired with both signs of the supplementary static earthquake case at a
unit coefficient. The maximum compression across the X reference is
2,164.366 kN against a 2,240 kN section limit. All 32 columns qualify for
optional low-axial numerator credit under §7.3.6.1. Vis and Vik are each
2,361.123671142073 kN, α is 1.000000 and the unit-factor check gives zero
shear change in one evaluation. The corresponding Y case gives 2,339.746698 kN.
Neither static case appears in the eight assigned response-spectrum families.

For those eight assigned families, all 348 directional column ends across
three stories are accounted for by connectivity, §7.3.5.3, or a sufficient
Eq. (7.3) moment bound. The selected-cage scenario requires zero design
amplification iterations. The R14 summary now carries the normalized moment
bound for the five non-exempt joints. The governing bound is **2.729886**.
All 87 columns still have 13 shared open gates, down from 17.
GAP-016 remains 20 numerical matches, 20 insufficient-source comparisons and
four engineering interpretation differences. Engineering release is `NOT_READY`.

The two copies of the 520-line November 20 audit have the same SHA-256.
Only one of its 160 printed Eq. (7.3) ratios reproduces to six decimal
places against the report's own reference run. All 160 checks in that run
are sufficient. Use the sealed case and sway rows for individual values.
A separate read of the locked model returned 6,432 native rows for eight
model-defined capacity combinations and reproduced all 7,638 assigned
control rows. Model-wide absolute V2/V3 maxima are 326.701488/327.047409 kN
for the ductile combinations and 483.638157/740.226757 kN for the capacity
combinations. The ledger indexes both sources and the full audit cross-check.
Two CLI runs match at all 16 stages. The offline suite passed 1,538 Python
tests with one skip and 11 JavaScript test files. The installed wheel passed
387 tests.

The column shear calculation above supersedes the outstanding seismic-shear
gate at this checkpoint. See the [worker handoff](context/WORKER_HANDOFF_20261119.md#local-auditor-brief).

## Previous original-model joint calculation

The normal R10 pipeline now accounts for all **52 physical joints with a beam
and a column above and below** in the assigned model. Of these, 47 qualify
for the low-axial exception under TBDY 7.3.5.3(a). Each of the other five
meets the conditional strong-column moment check over the recorded axial
intervals for the selected reinforcement. Five joints, two horizontal
directions, eight assigned seismic combinations and both sway signs give
**160 of 160 sufficient comparisons**. The smallest lower ratio is **2.729886**.
The two column resistances total at least 2,425.443 kN·m. The required
beam-side sum, including the 1.20 factor and numerical tolerance, is at most
888.478 kN·m for that comparison. See `EV-R10-LIVE-INTERVAL-20261120` in
[the ledger](VERIFICATION_LEDGER.json).

For each principal axis of a symmetric selected column, the existing section
solver evaluates five equilibria bracketing the entire compression interval.
Steel forces increase along that strain path and the compressed net concrete
area expands. Its force increments and those of the bars act within half the
section depth of the centroid, giving |ΔM| ≤ (h/2) ΔN. Deducting the numerical
tolerances and the maximum distance to the nearer equilibrium bounds every
intermediate resistance. R10 adds the two column lower bounds and compares
them with the signed selected beam-end resistances at N=0 for each sway.
An inconclusive bound carries an unresolved result. An independent strip
integration matched 800 anchor moments within 0.000091 kN·m and checked 640
interior points. The selected cages and the beam N=0 assumption define the scope.

The Windows gateway at `cc98df6` acquired the original locked model with the
same 87 columns, eight seismic and three gravity assignments, and two selection
policies. All 45,828 raw force components at 7,638 native rows exactly matched
the earlier archive. The updated shared pipeline used that fresh frozen input.
The printable report includes the recorded signed analysis shear and governing
cut. Terminal alpha feasibility retains a proven panel failure when another
member has exhausted its cage choices.

Both replays of the fresh input matched across all 16 stages. The final
Windows offline run passed 1,530 Python tests and 11 JavaScript test files.
Windows skipped one symbolic-link test. All 379 overlapping installed-wheel
tests passed. The ledger retains two earlier host-aborted loopback attempts.
GAP-016 currently has 20 numerical matches, 20 insufficient-source records
and four engineering interpretation differences across its 44 comparisons.

That checkpoint left the story alternative unresolved with 17 shared R14 gates.
The current story calculation above supersedes its applicability result.
See [TBDY 2018 §§7.3.5–7.3.7](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf).

## Historical remote correction before the live run

The previous milestone is described in [audit corrections and live handoff](engineering/AUDIT_FIXES_20261120.md).
It starts at `f57e6194155b2f9cfc30e3beecf75e0c83a39c16` on
`work/engine-audit-fixes-20261120`. The execution record is
`EV-AUDIT-FIXES-20261120`; commit ancestry and its tested-file hashes identify
the implementation. The unseen Windows working tree was not inspected.

Final verification passed **1,522 Python tests, 11 JavaScript test files and
370 overlapping isolated-wheel tests**, with the final tested-file manifest
unchanged. The [execution record](context/AUDIT_FIXES_VERIFICATION_20261120.json)
retains the initial incomplete-fixture failure and the final successful runs.

The existing owners now floor first-order moments for minimum eccentricity
before applying local/global factors; use the analysis shear lower bound on
both initial and revised capacity shear; and route embedded legacy selection
policies through the same source/dependency checks as explicit scenarios.
R10's declared method version is now present in the registry even without
declared input contracts. The standard report displays the recorded raw,
floored and final moments.

The supported signed alpha branch consumes qualified per-column low-N credit
under TBDY 7.3.6.1. Credit to Vis and eligibility for 1/alpha demand amplification
are separate recorded populations. The existing axial owner supplies the maximum
over all native cuts, so low end forces cannot hide a higher interior demand.
Terminal feasibility also requires the expected joint panels and physically
mapped ties. A proven joint failure stops with `JOINT_DESIGN_FAILURE`; an
exceeded unresolved bound requires refinement. Neither becomes a fixed point.

The new source-level examples and regressions do not complete the original
building story slice. The next original-model calculation remains
[one interior joint through a full story and direction](engineering/AUDIT_FIXES_20261119.md#next-bounded-delivery-in-order).
Live ETABS and the exact private 87-column replay were **NOT_RUN** for this
milestone. The user will run the existing gateway on Windows after integration.
Engineering release remains `NOT_READY`; no stable GAP or CHECK is closed.

## Previous original-model low-axial checkpoint

R10 now decides the TBDY 7.3.5.3(a) low-axial exception at two connected column
ends. It compares each end's largest compression under the assigned combined
gravity and earthquake cases with that column's 0.10 Ac fck. The normal report
shows the governing seismic combination and the maximum over all assignments.
[TBDY 2018, chapter 7 notation and §7.3.5](https://webdosya.csb.gov.tr/db/yapiisleri/icerikler/tbdy_2018-20210506174126.pdf)
The original C29 worked result is indexed by `EV-C29-INTERIOR-LOW-AXIAL-20261120`.

Of the original model's 52 two-column joints with framing beams, 47 qualify for
the exception and five exceed a column limit under combined seismic demand.
Seven of the 47 exceed a limit only under gravity combinations. The production
replay is indexed by `EV-R10-LOW-AXIAL-20261120`. For the five remaining joints,
evaluate the column moment capacities at direction-compatible axial demands
under 7.3.5.2 for both sway signs. Then bind the full story-direction shear
population and apply the existing alpha iteration.

## GAP-016 report comparisons

The 44 GAP-016 records now contain **20 production numerical matches,
20 insufficient-source labels and four adopted-factor interpretation differences**.
The GOLDEN-01 ground and upper storey theta scalars on PDF page 28 call the
existing global P-delta owner. The reference values are 0.007516853605560383
and 0.005997760967498111; cumulative weight and the mm-to-m drift conversion
are each applied once. These two scalar matches do not approve the story
source, theta limit or global magnification policy. Of the remaining 20
insufficient-source records, 16 already have independent/reference values and
need the stated adapter or method work. See the
[current comparison tasks](context/PROJECT_CHARTER.md#resume-the-44-report-comparisons-gap-016).
The 73 recipe labels, 44 production comparison records and historical 333
arithmetic assertions remain separate populations.

# Remote code audit corrections - 2026-11-19

The reviewed published baseline and work branch were both at
`1697a968dc30e342b83685bec898bda3109643ca`. The new corrections extend the existing
joint adapters, scenario preparation, R14 consumer and sealed report. See
[implementation and next slice](engineering/AUDIT_FIXES_20261119.md) and the
[historical pinned audit](engineering/AUDIT_PIPELINE_20261119.md).

Zero/small/missing seismic cases cannot yield a favorable incomplete joint
deduction. Physical coordinates and directions determine upper/lower columns
and lower confinement axes. Exceeded unresolved zero bounds require refinement
or redesign without being mislabeled as proven demand failures. Web/CLI use the
same verified parent/scenario contract. The normal report displays recorded
PMM cuts, forces, capacity/reserve and joint shear/tie calculations.

Fresh offline verification: **1464 Python tests, 11 JavaScript test files,
293 isolated-wheel tests passed**. The initial invalid-policy/incomplete
fixture failure is retained with its correction; no production guard was
weakened. Exact base, dirty-tree hashes, commands and limits are recorded in
`EV-AUDIT-ADAPTER-FIXES-20261119` and
[the execution record](context/AUDIT_ADAPTER_FIXES_VERIFICATION_20261119.json). No stable
GAP or engineering CHECK is newly closed. Engineering release remains `NOT_READY`.

The Windows working tree and private original 87-column source were not
available to this remote review. The local/private calculation checkpoint
below is retained as historical evidence, not a newly rerun result. Integrate
the published correction normally with any newer local work; do not replace
uncommitted work with this remote snapshot.

Next deliverable: one interior joint with its governing SCWB axial-demand
branch, followed by a complete story-direction denominator and the existing
alpha feedback loop. Preserve a valid passing conservative bound. The spectral
method and the original/private numerical transfer questions remain separate.

# Current local checkpoint — 2026-11-19

**87 column reinforcement candidates are selected and bound to the same pipeline run.**
Final candidate: **32Φ16 + Φ10/90 mm ties, three crossties per local direction**.
Selected As 6,433.98 mm² ≥ 6,400 mm² (1.0053%). The final reference checks pass,
but R14 remains **0 closed / 87 partial**, formal compliance `NOT_PROVEN`,
engineering release `NOT_READY`.

## Selected column and roof-joint calculation

The original selected ETABS scenario runs through the shared pipeline. R08
returns the governing signed static cut, resultant moment demand, radial capacity
at its axial force, and remaining moment for the same selected cage. R10 sizes
the maximum whole-mm tie pitch from the proposed legs, the lower-column required
Ash/s, enclosure class, diameter and code spacing cap. The three signed static
combinations reconstructed 1,206 station vectors (7,236 native scalars) on
87 columns. All 1,206 selected-cage moment reserves were nonnegative. The joint
owner sized 252 of 272 returned member-end/axis records. The worked roof-joint
calculation includes both sway directions, the axial and column shear checks,
and its selected reinforcement. Ledger `EV-COLUMN-JOINT-SLICE-20261119`
identifies the sealed result and verification at `79f534a`. The example also
calculates the lower interior joint with zero deduction. Connecting the actual
earthquake-compatible upper and lower column shears is the next calculation.

## GAP-018 manual ETABS comparison

ETABS finished Modal, RSX, RSY and both zero-eccentricity cases on the private
copy. The two readbacks reproduced the same native spectral forces and case
definitions. The original model's 3,175 input lines match in order after
excluding the file header, six new case-definition lines and three Save As records.

At 402 element-side cuts on 87 columns, the signed half-difference between
the positive and negative eccentric static cases gives 804 direction-specific
static vectors. Its component magnitude matches the increase in the ETABS
spectrum maximum from zero to 5% eccentricity for 4,824/4,824 scalars.
Eight of ten selected internal cases returned rows. The two dedicated torsion
cases returned zero frame rows. Independent CQC on the private model's own
100 modes, using 5% damping and the unadjusted native spectrum, reproduced
4,824/4,824 zero-eccentricity maxima within the recorded tolerance.

Across the original and private analyses, all 100 modal controls matched the
existing tolerance and 4,686/4,824 original force controls passed.
The 138 exceptions affect 103 of 804 case-cuts on 34 columns. The largest
exception is 1.19003e-6 kN m in RSX M2. The original-model transfer gate
remains open. The signed result applies to the static eccentricity component.
Dynamic simultaneity, story allocation and the original scenario's R14/alpha
gates remain open. Ledger `EV-GAP018-MANUAL-PAIR-20261119` links the native
readbacks, independent audit and per-component exceptions.

## Earlier original controls and R14 closure inventory

A fresh read of the original model reproduced all 4,824 native scalar controls at
402 element-side cuts for two spectrum cases, with zero numerical difference.
The selected scenario `RUN-17fbcff4be754227acb61dd1151b94cf` reproduced
16/16 stage payloads on replay. All 87 members have the same 17 open gates.
Fourteen block numerical closure. The other three still require source evidence
for engineering acceptance. The approved project profile, actual faces and
anchorage, axis-specific restraints, creep and spectral story feedback remain open.

The private Save As export reproduced 3,175 original lines byte-for-byte after
excluding the file header and the additional save-history line. The prepared
input added six definition lines for two zero-eccentricity controls. The
original model's solver log identifies eight internal static cases, including
two torsion solves. The first private API analysis invocation returned 1.
The later manual run and its original-control comparison are recorded above.

Ledger `EV-GAP018-PAIR-CONTROL-20261119` links the frozen roster, selected replay and private proof.
R14 is 0 closed / 87 partial. Engineering release is `NOT_READY`.

## Earlier GAP-018 live ETABS checkpoint on the original model

The user-session gateway on port 8876 captured the locked model twice on
2026-11-19. The v8 source is `RUN-9ad3c981cd9a4875bf383530429a1173`,
SHA-256 `61c5417b8f5f11b7352c9c02f2d518b67666fac09f1c7f6f53546fac207d7db9`.
Both reads observed the same model and units (kN/m/°C). The display, output
and mode selections were restored. The EDB digest matched before and after.
Implementation `9e01f92617a3a37a6e6a79ea913dafe5feb2b8da` is on
`work/gap-018-spectrum-evidence`. Baseline at that checkpoint was `24ddc371`.

The native function getter reported 26 points and returned 27 slots per array.
The first live v7 run retained the raw return and blocked the curve. The v8
stage resolved the leading zero pair against all 26 points of the same named
ETABS function table. Its signed, unadjusted curve references agree at printed
resolution for all 200 RSX/RSY case-modes. An exact-fraction calculation checked
1,000 numeric values. XML and array exports contain the same 2,200 text values.

Both cases specify 5% constant damping with zero overrides. All eight material
getters returned zero modal ratios. The one named linear-link property returned
six zero uncoupled damping coefficients. All 5,579 generated link elements map
to two area-spring assignments with user-defined stiffness. The effective modal
ratio is available at display precision. [CSI damping documentation](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Damping.htm)

An independent CQC calculation compared six force components at 402 configured
element-side cuts in each of two cases (4,824 comparisons). It used a uniform
5% effective ratio and the native curve without damping adjustment. All 4,824
ETABS total maxima exceeded that conditional dynamic reference. The model's
15-case catalog contains two spectrum cases, both with 5% eccentricity and
zero eccentricity overrides. Isolated accidental torsion remains **0/804**.
At that checkpoint the next required evidence was a source
for the applied unrounded amplitudes and effective ratios, and a separately
identifiable torsional response at the same cuts. Story allocation and spectral
alpha remain open. [CSI accidental eccentricity guidance](https://web.wiki.csiamerica.com/wiki/spaces/kb/pages/2001549)

Ledger `EV-GAP018-LIVE-SPECTRUM-20261119` records the run identities, frozen
scope, numerical references, replay and test evidence. The selected scenario
`RUN-20e3c9ea485448aeb4c71461e3237f9f` retains the original live input
bytes. All 87 candidate IDs and candidate digests match the earlier selection.
Independent repeats reproduced 16/16 stage payloads for each of the two runs.
The existing gateway served both reports with the same JSON and HTML as the
local projections, where 39 calculation or live entry points were guarded
and received zero calls. The full local suite
ran 1,428 Python tests with one Windows symlink skip and passed 11 JavaScript
test files. The installed wheel passed 252 tests. Engineering release remains
`NOT_READY`. The later paired comparison and calculation are recorded above.

## Earlier GAP-018 archive checkpoint

The local and published `baseline/local_import` were verified at
`24ddc371c66ebcba24bf8672fe3038564e26d48c`. The working branch
`work/gap-018-spectrum-evidence` starts there. The existing mixed-demand stage
used `same-source-spectral-components.v7`. At this checkpoint the
user-session gateway at port 8876 was unavailable.

The selected, sealed scenario supplied 100 native modes and 200 signed
amplitudes from the RSX and RSY display table. The amplitude comparison uses
the native signed participation factor and eigenvalue for the same mode. It
propagates the last printed digit of both acceleration and displacement.
All 200 intervals overlap. A separate exact-rational oracle checked the
predicted center, residual and interval allowance for each row. The largest
displayed-center residual was 0.00000641024 m. Trailing zeros can be suppressed
in the table, so this agreement establishes compatibility at printed resolution.
[CSI response-spectrum analysis FAQ](https://wikicsiamerica.atlassian.net/wiki/spaces/kb/pages/2006323)

On a fresh PMM capture, the gateway records the native modal case, load axis,
function, acceleration scale, curve knots, damping type, constant and mode
overrides through the same model connection. A selected-case XML response and
the in-plane diaphragm force table are retained for inspection. A native-curve
amplitude is an unadjusted reference. Effective damping also depends on material
and link/support contributions. The selected archive predates these new reads.
[CSI Analysis Reference Manual, chapter on response-spectrum analysis](https://docs.csiamerica.com/manuals/etabs/Analysis%20Reference.pdf)

The configured inventory covers 87 members and 402 element-side cuts across
two spectrum cases. Isolated accidental-torsion contributions are **0/804**.
The case eccentricity and in-plane loads cannot isolate the internally applied
torsional response. The next live read must establish effective per-mode
damping, amplitude precision and the applied response before modal/directional
aggregation, story allocation or SCWB/alpha can consume it.
[CSI accidental eccentricity guidance](https://web.wiki.csiamerica.com/wiki/spaces/kb/pages/2001549)

The implementation commit is `f5dc030beb7475c975b0d68a2e8ccc664cc1af7e`.
Both v7 CLI runs produced identical payloads for all 16 receipts. The JSON
and HTML report matched the sealed result with 34 entry points disabled and
zero calculation or live calls. The full local suite ran 1,426 Python tests
with one Windows symlink skip and passed 11 JavaScript test files. The
installed wheel passed 251 tests. An earlier full run exposed a stale report
heading assertion on the published baseline. The corrected assertion retains
the ETABS reinforcement gate heading and all three check identities.

The ledger record `EV-GAP018-SPECTRUM-ARCHIVE-20261119` identifies the 319-file
manifest, independent audit, replay and repeat runs, commands, and private log
hashes. The v7 result digest is
`a44cf26136085d5f73b1d8aa7cd1e04467be070b4a1d074a209ad821977dd105`.
All 16 original candidate receipts also passed integrity verification.
At the archive checkpoint the gateway probe returned socket error 10061.
The live checkpoint above supersedes that connection status.

## Integrated candidate checkpoint and source identity

- Logical integration base: `baseline/local_import`.
- Both verified milestones are integrated locally: native modal identity
  `5e1e10c1b9ffd0be777202873f4b428ded19b152`, then candidate reporting
  `46dcb3ccc5c6dfe052a88c81e1d7758838a0f1b5`. The retained work branches are
  historical milestones integrated into `baseline/local_import`.
- The documentation handoff at `24ddc371` followed `46dcb3c...`. Its published
  ref was rechecked directly with `git ls-remote` before the GAP-018 work.
  Original publication evidence remains in `.receipts/handoff/publication.json`.
- Keep baseline current at every completed, verified milestone. Start scoped work
  from that baseline, synchronize it using a normal push and verify the remote SHA.
  Preserve pending work separately; never reset local changes to an older remote.
- Original live source: `RUN-77039b97519e45029e209f0031d72d36`, SHA
  `9e5535ad2fe5749aa897a16023a3f7288062388df65f23013d243bbdb77bf640`.
- Final selection run: `RUN-4c6e8d795ca94411a1cd6d7f7f54c9de`, derived-source SHA
  `3de017a56036769e7436bac7f16363b552224740d75014678c73119fd1cd2171`.
- Final result SHA: `84740c17a28a7b9542ae21e0eee9dabeb51a7e6f8d2b2d7ced20b285f1365b83`.
- Runtime package SHA: `6cf4e08485fdb7b021a91988faca578c6b5cf9045231fa0f7740969cae731e52`.
- [449-file tested manifest](context/TESTED_FILES_COLUMN_CANDIDATES_20261119.json),
  SHA `731de054fa8350f60aa9b15ee2b49034f2a734fe61e8ce7281b1ce2022544bd7`.
  Final documentation and metadata edits are outside its executable test scope.
  Executable files were rechecked unchanged. Raw Windows hashes differ from Git
  text normalization; preserve the exact LF manifest.

Preserve unrelated `.idea/`, `build.zip` and the root handoff-recipe copy.
Keep `.receipts`, model captures, SQLite/PDFs, credentials and environments private.
`YENI_P0` stays read-only. No reset/clean, old-main merge or force-push.

## Completed selection and product work

[Detailed acceptance and commands](engineering/COLUMN_CAGE_SELECTION_ACCEPTANCE_20261119.md).
The plain live-source run had no selection policy. The requested scenario uses
existing `EnginePipelineRunner`, scenario/dependency owners, R10 selection and
same-cage local R08/PMM, then sealed R14/report outputs. No second solver or
attachment route was added. Calculation algorithms are unchanged.

The initial Φ8/90 trial `RUN-0505da6ae4394ceabd4c5a22f8e8ff4c` is retained. Forty
columns per direction exceeded the zero-concrete Ve reference (maximum 1.2388).
It was not adopted as the final transverse choice. The final explicit policy
allows ties 10/12 mm, keeps 90 mm confinement/midspan pitches and 1%–4%
longitudinal bounds, and preserves the exact original bytes in `parent.source`.
No ETABS analysis, model edit or save occurred.

| Final reference evidence | Result |
| --- | --- |
| Expected / selected / same-run bound columns | 87 / 87 / 87 |
| Transverse, both confinement and both shear references | All recorded criteria satisfied |
| Magnified selected PMM | 1,206/1,206 rows; max utilization 0.422829 |
| Spectral bounding corners | 25,728; max bound utilization 0.646794 |
| Ve TS 500 / zero-concrete reference maxima | 0.578317 / 0.793070 |
| Independent Decimal(80) area comparisons | 435; zero outside 1e-8; max difference 5.524e-13 |
| Source/receipt integrity | 16 receipts; original bytes preserved |
| Spectral alpha iteration | 0; BLOCKED_INPUTS |

`reporting.py` adds a projection of the saved candidate schedule, preserving
blocked members and unique-ID binding. `workspace-source.js` shows selected bars,
As, percentage, minimum As, ties and crossties across all IDs in tabs 4.2, 4.4,
4.5 and 4.6. Original ETABS template gates are explicitly labelled separately.
The data remains full precision; only display precision is reduced.

At the candidate-report checkpoint, the user restarted server 8876. Its JSON,
HTML and workspace script matched the final projection. All four tables contained
the same 87 unique IDs. During local
report verification 27 calculation entry points were disabled; zero were called.
No mouse/browser takeover or visual inspection was performed. The existing
server's session probe observed PID 11788, locked model, units 6; rediscover the
session before future reads rather than making that PID permanent.

Tests at the candidate-report milestone: **30 focused Python tests / 11 JavaScript files passed**. Initial
Node Python-path and view-harness failures are retained with successful retries.
Full Python suite, installed wheel and CI are **NOT_RUN for this presentation
increment**. Do not relabel the prior modal milestone's 1,407 Python / 241 wheel
results as newly run. Environment: Windows 11 build 26200, Python 3.12.10,
Node 24.22.1.

Private proof: `.receipts/verification/column-cage-selection-20261118T193312Z/`.
Ledger IDs: `EV-COLUMN-CAGE-TIE10`, `EV-COLUMN-CAGE-REPORT-TESTS`.

## Engineering boundary at the candidate-selection checkpoint

The candidates are not engineer-approved or as-built. Hooks, splices, anchorage,
physical confinement lengths and complete physical-cut scope remain open.
Magnified PMM uses recorded reference clear/effective-length, sway and creep
assumptions; low utilization does not approve those inputs. Spectral corners
are independent bounds, not simultaneous force vectors. Both Ve/confinement
reference branches passing does not approve their normative applicability.

The final R14 retains 17 gate codes: R03 approved model/load roles and analysis
generation; physical joint faces/cuts/anchorage; local R08 effective-length,
sway, creep and analysis-order approval; spectral SCWB/story-alpha policy and
alpha feedback. No engineering CHECK or stable GAP is newly CLOSED.

The next task at that checkpoint was `SPECTRAL-MODAL-PRECISION-AND-TORSION-QUALIFICATION`,
GAP-018, then GAP-013 / GAP-016. Qualify the remaining applied amplitude,
effective damping and isolated torsional response on the frozen case/mode/cut
scope. Independent modal and directional acceptance and story allocation are
required before qualifying spectral alpha. General scheduler and
complete CheckInstance accounting remain GAP-005 / GAP-017.

## Earlier verified work and recipe

[Native modal acceptance](engineering/LIVE_MODAL_IDENTITY_ACCEPTANCE_20261118.md):
100/100 native numeric modes, 2/2 eccentricity definitions, 500 independent
numeric relationships, 16/16 identical repeat receipts, 1,407 Python / 10 JS /
241 wheel tests. This earlier scope is preserved. Eccentricity definitions do not
prove applied torsion or active damping. The registered method at that checkpoint was
`same-source-spectral-components.v6`.

Historical PMM v6 configured-cut proof remains 2,409 cuts for 73 single-element
columns plus 2,013 for 14 meshed columns, including both sides at 72 internal
joints. Do not convert a configured subset into a complete physical census.

[English recipe entry point](engineering/reference/recipe_20261118/README.md).
Published recipe/v5 source assets remain at a9d053f…; their evidence and the
73-control map are reference coverage, not 73 accepted production checks.
The old exported context ZIP describes b255c303… and is superseded by current
Git documents and ledger. No background GitHub sync is configured.

## Earlier handoff and publication checkpoint

[Worker and new-chat handoff](context/WORKER_HANDOFF_20261119.md) defines the
baseline workflow, reference boundaries and the next bounded acceptance task.
The private local resource index is `.receipts/handoff/LOCAL_RESOURCES_20261119.md`;
it identifies the working directory, Drive connection, reference locations, run
files, SQLite banks and launch command. It is intentionally absent from GitHub.
The baseline handoff at `24ddc371` updated guidance and evidence indexes.
Engineering tests and live ETABS operations were **NOT_RUN for that handoff**.
See `EV-HANDOFF-20261119`; earlier test records retain their original scopes.
