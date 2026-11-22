# Local development and GitHub worker handoff

## Start with the whole-building engine

Use `EnginePipelineRunner` via `run-pipeline --whole-building` or **Run whole building** in the workspace. The [single original-source command and engineering assumptions](../engineering/WHOLE_BUILDING_ENGINE_20261122.md) reproduce the three occupied storeys. No preparer or preselected column cohort is required. `RUN-c85705a8cb9a48b1a190d24d10198e66` is the original frame and pier reference with section forces. The report reads its sealed calculation.

Preserve 42/87 conditional column designs and 180/180 selected beam flexure and capacity-shear evaluations. All 23 upper-storey columns are already included. The two B2 threshold exceedances and three unmet wall geometry subconditions are genuine numerical outcomes of this source scenario. Keep them visible.

The current run contains 73 column schedules, 180 beam schedules and the proposed rectangular boundary cages of piers P2, P3, P4 and P5. The four C21–C24 base continuation shortfalls must propagate to R14. At mat 9A the model provides 600 mm for an 800 mm requirement. Preserve the 106 beam ends referenced to model cuts separately from the 254 column-face ends.

P2–P5 now have two-curtain webs, both boundary cages, 120/120 signed original-model gravity PMM and shear results, and 192/192 sufficient conditional local seismic shear bounds. The native wall strength assignments are five static combinations and eight Crack_Seis combinations. The eight Cap_Seis combinations provide the separately checked project D controls. All twelve ETABS sections contain one wall and zero lines. The three-case METHOD study has a separate model identity and 72/72 completed cuts.

Next, use the same original capture to build the TBDY 7.6.6.1 design moment diagram by base and critical-height scenario, then bound axial force with both moments at all 192 cuts using the recorded bar coordinates. Retain the 7.6.6.2 strong-direction capacity requirement and joint checks. Compute the applicable Fig. 7.12(c) shear distribution over height. The ETEX workbook comparison is complete for all 12 rectangular lower cuts with the proposed cage. At P2/472 Bottom, two curtains of Ø12/200 give 346.920 tf in the workbook and 346.963 tf in the engine. For the separate 633.56 tf Quick Result, obtain the upstream calculation with its steel input if it becomes available. The two ETEX axial views already confirm the original Cap_SeisX_Soil and Crack_SeisX_Soil result rows (10/10 and 9/9 visible). Preserve the 192 local shear outcomes, the four mat-continuation failures and the remaining 18 wall panels in the building coverage. Slabs, punching and C104 local convergence are deferred. [Numbers, assumptions and one-command replay](../engineering/WHOLE_BUILDING_ENGINE_20261122.md#pier-web-gravity-capacity-and-seismic-shear)

## Earlier 26-column frame-design checkpoint

The previous original-building run `RUN-2e424431e3ff491087e2359543e9c9dc` covered 26/87 at R14. The completed +4.50 m C1, C2, C5, C77 and C78 and +9.00 m C20–C26 are included. The whole-building calculation above consumed the same original source.

The storey totals used all 23 upper-storey frame contributors and eleven assigned combinations. C22/57 provided the earlier upper-storey comparison. The 34 low-axial and 14 terminating-column directions have separate SCWB dispositions. Every direction still has a panel shear and transverse outcome. [Member designs and reproduction](../engineering/FRAME_DESIGN_MIDDLE_AND_UPPER_20261122.md)

## Previous +4.50 m frame-design checkpoint

The preceding checkpoint used `RUN-47067d0f1896415ba5ffc8e61031a024`. Its frozen parent matches the original C29 run. At that checkpoint R14 covered 14/87 columns under the stated frame assumptions. The newly completed members are 134, 135, 136, 137, 140, 141, 143, 146, 147, 148, 149 and 157. C29 members 142 and 225 retain their previous results. [Full population, assumptions, source and reproduction commands](../engineering/FRAME_STORY_DESIGN_SLICE_20261122.md)

The two-storey sprint above completed the five queued middle-storey members and derived the upper storey inputs. The listed wall-supported lower ends and construction anchorage still require separate work. The C104 work below remains available when its independent refinement is resumed.

## Prior C104 four-mesh result for the assigned demands

Start with the [four-mesh numerical result](../engineering/C104_ASSIGNED_DEMAND_AND_W23_20261122.md) and the [current GAP assignment](../ENGINEERING_GAPS.yaml). The original working model and the solved A/B/C/D private captures are identified in the [verification ledger](../VERIFICATION_LEDGER.json). Local replay uses the existing R08 pipeline and its sealed report. The implementation is `9e070be487be102d54293fd6e19d01831c676d35`. The engineering receipt is `RUN-f21f119300d845d78f27e8345a8bdf54`.

- Reuse the four existing mesh solutions, 36 complete W22/W23 balances, 456 assigned frame comparisons and 144 signed coupled section comparisons. A/D has 61/456 assigned fields in the existing budget. Under Duct_SeisX_Soil the axial change immediately above −1.50 m is −44.308 kN, dominated by horizontal refinement.
- The next mesh comparison holds the D vertical pitch of 25 mm and the W23 mesh and edge policy fixed. Refine W21/W22 horizontally, compare the assigned soil P above and V3 below −1.50 m, and report all 456 components. Track the V2 response in a separate vertical sequence. Keep each load, step, face and sign from the sealed reference.
- Eleven native assignments establish LC_EQX/LC_EQY as auxiliary cases. The whole-base/0 m scale alternatives have been evaluated. Resolve the applicable basement classification, upper-building mass scope and acceleration normalization before assigning a project beta_tE.
- C29 retains its six signed story balances, 12 conditional factors, 24 independently checked cage faces and 2/87 conditional R14 result. For the fourteen coupled columns the second-order method and construction continuity still require separate evidence. The user-supplied model view remains the sole detail. [C29 and earlier C104 scope](../engineering/C104_TRANSITION_AND_C29_CAPACITY_20261122.md)

The evidence IDs are `EV-C104-W22-W23-FOUR-MESH-20261122` and `EV-WINDOWS-C104-FOUR-MESH-20261122`. The [review-time experiment](../supervisor/C104_TRANSITION_REVIEW_20261122.md) and [LC_EQX scope correction](../supervisor/LC_EQX_ROLE_CORRECTION_20261122.md) explain how the current assignment was selected.

## Assignment issued with the system audit on 21 November 2026

Read the [system audit](../supervisor/SYSTEM_AUDIT_20261121.md) and
[canonical roadmap](../supervisor/ROADMAP_20261121.md). The inspected base is
`c71a4dda4ab9453f428a38b3ed79931f8e6eeea3`; inspect the current remote before
starting new code work. The audit changes documentation and adds bounded
diagnostics only. All S00–S15 packages were proposals when the audit was issued. The 22 November checkpoint above supersedes the work assignment in this section.

**Offline worker: S00.** Reproduce the signed-datum/expected-count defect,
the complete-data balance/conditional-consumer defect and the receipt
99/100 boundary using [the audit commands](../supervisor/audit_20261121/README.md).
Correct the existing owners with targeted regressions. Preserve the
conditional frame calculation where full-wall evidence is merely absent;
only qualified complete-contributor, same-state, independently loaded
equilibrium can establish the contradiction that blocks dependent use.
Retain diagnostic values and every expected unresolved instance. Then
replay the actual archived C29 source/scenario to establish impact.

**Windows worker: S02 in parallel.** Continue the exact two-cut first-order
balance below, beginning with `C29G_U_F` and extending to TN_F/TP_F. Rediscover
the active source/PID and installed API; reuse a valid solved generation.
Report physical contributor counts 53 and 36 separately from generated
shell row counts. A balance table is a valid partial delivery while the
wall critical-load method remains open.

**Research/verification lane:** prepare E09-B/C/D/E and the independent
fixed-N/direction section oracle; qualify the `strongcol4.docx` alpha-below-one
example's actual capacity/source inputs. Calculate viable alternatives
before method review. A failed eigenvalue-to-story-Nk mapping is not a
reason to fabricate Nk or to prohibit a qualified direct-demand candidate.

One integration owner and one writer per module. Each return must include
source/case/cut, expected/evaluated population, actual owner and downstream
consumer, numerical values/error budget, independent check, remaining
scope and the next exact action. The completed C29 full-span recovery is
not restarted as a substitute for these missing calculations. Existing
native results and test counts below remain historical evidence.

## Windows regression checkpoint

`EV-WINDOWS-OFFLINE-31A8B08-20261121` records the user's completed Windows
offline suite against reported clean tracked commit
`31a8b08c0553156cd612585513d9ac3a22e25573`: 1,690 Python tests total,
1,689 passed, one skipped, no failures or errors, 304.503 seconds,
11 JavaScript files passed, Node.js `v26.13.1`, and
`OFFLINE_SOFTWARE_REGRESSIONS=PASS`. Golden counts remain 36/4/4 across
44 records and engineering release remains `NOT_READY`. The original excerpt omitted the skip identity. The subsequently supplied full transcript names the Windows symlink-permission test. Its hash is recorded with the 22 November Windows checkpoint. Keep this user-reported evidence separate from the recorded
Linux run; neither test count substitutes for original-building evidence.

## Next GAP-009 calculation

Use the matched physical faces and native case/step populations from the four-mesh C104 result above. The first-order spacing study found a real change in the assigned P, V2 and V3. The next level must quantify the change in the assigned design demand. Verify coupled second-order behavior under explicit stiffness, restraint, creep and axial-load assumptions after identifying a stable first-order result. [Measured effects and open method work](../engineering/C104_ASSIGNED_DEMAND_AND_W23_20261122.md)

### Historical W22/W23 experiment instructions

The 22 November four-mesh receipt completes steps 1–5 below to the scope stated in the current calculation. Step 6 remains open.

1. Read `release-summary.json` and `w22-transfer.json` under the private verification directory `.receipts/verification/c104-transition-20261122`. The archived face arrays are already consumed in R08. Keep the 1% / 0.05 kN or kN·m mesh budget and the separate body-equilibrium budget. Preserve all 12 passed balances. The governing M3 difference belongs to `above_transition` immediately above −1.50 m, not the `upper` cap at −1.45 m.
2. Inventory actual W22/W23 IDs, planes, points, axes, incident members, shared/coincident nodes, DOFs and constraints at x = 77.40 m. Use the archived models first; acquire missing W23 rows through the existing gateway. Qualify equivalent physical automatic-seismic loading across models: mass, period/scale, base/story forces, torsion and application centres. Different mesh DOF populations do not require literal equality of raw nodal vectors.
3. Assemble both-side unaveraged actions about O=(74.00, 0.40, −1.50) m with all incident members, edge loads and constraint transfer. If constraint forces are unavailable, enclose the tied points in a complete free body. Preserve `Single Value`, step 0, for the six C104 linear-static cases. Separate direct My, `(z-zO)*Fx` and `−(x-xO)*Fz`; net vertical force alone cannot explain the moment change. Begin diagnosis with LC_EQX and include all six cases before acceptance.
4. If needed after those controls, reuse the existing coarse-H/50 mm and fine-H/25 mm models and add coarse-H/25 mm plus fine-H/50 mm. W21/W22 coarse horizontal pitches are 1.00/0.85 m; fine pitches are 0.50/0.425 m. Record and control W23's mesh and connection policy. These two proposed analyses separate H/V effects and interaction; they do not alone prove convergence.
5. Extend/version `tbdy.next.coupled-wall-transition.v1` explicitly where the additional interface or four-model experiment requires it. The current contract is one upward frame, two coplanar rectangular walls and a fixed two-mesh pair. Reuse `gravity_wall_cut.joint_action_at_origin`, the existing preparer, R08 and sealed reporting; do not merely remove the scope assertions. Publish the source census, physical loading comparison, both-side tables, first moments and governing numerical outcome.
6. After qualifying first-order demand, compare coupled second-order alternatives under explicit effective stiffness, restraint, creep and axial variation. Method preparation can proceed in parallel. Keep all 14 coupled columns visible, and qualify any mapping from whole-system critical load to story Nk separately. Construction continuity/anchorage remains a distinct open design premise; the sole available model view does not block model-based transfer diagnosis.

S02 closed the six first-order force balances. The existing conditional frame-column scenario supplies the 12 C29 factors and 24 side-specific PMM values. Its governing values and the two physical free bodies are in the [calculation record](../engineering/C29_S00_S02_20261122.md). The full-system stiffness branch retains `STORY_WALL_CRITICAL_LOAD_METHOD_UNSUPPORTED`.

## Verified native C29 conditional method result

Start with [the native C29 results](../CURRENT_STATE.md#completed-c29-conditional-comparison-on-native-method-meshes)
and `EV-C29-NATIVE-CONDITIONAL-TS500-20261121`. The private 2/4/8 ETABS meshes supplied all 18 gravity
case results. R08 v15 sealed 12 conditional TS 500 axes and 24 revised
PMM sides across 18 physical case-cuts. Both C29 members meet the
4-to-8 full-span error limit in all three combinations.

The first-order column–wall free body is now completed by S02. Active GAP-009
work is the coupled C104 six-component transfer and directional wall-frame
second-order/critical-load method. Preserve the existing 2/87 original conditional
result, eight beams and joint 40.
Use each refined level's independent same-generation modifier census and
the existing [acquisition contracts](../engineering/C29_STORY_INPUT_FIX_20261121.md).
The private resource index locates the sealed report and native packets.

## Report reconstruction and current comparison scope

Read [the report reconstruction](../engineering/REPORT_SWAY_RECONSTRUCTION_20261121.md)
and `EV-REPORT-SWAY-RECONSTRUCTION-20261121`. The private companion bundle
contains 26 genuine Drive reports: 20 DOCX and six PDFs totalling 1,256
PDF pages. Inventory and text extraction do not imply complete checking.
The reviewed scope includes 54 story Q/beta-s rows, 864 frame-column k
rows, 53/54 reconstructed story Nk sums, 124 exact frame-column critical-end
bindings, eight wall designs with six unresolved M22 transformations,
172 PDF theta rows and 12 selected PDF column-shear cases.

GOLDEN-01 ground/upper phi and the GOLDEN-02 numerical threshold change
now call the existing TS 500 owner's `sway_phi_reference` scalar. Preserve
the 44 IDs: 36 numerical matches, four interpretation differences and four
insufficient-source records. Source population qualification and automatic
sway assignment remain false. The 36-row GOLDEN-02 reconstruction matches
beta times beta-s in every row and MAX in none; the displayed-lk product
condition also triggers in none. Resolve the length/selection interpretation
before changing the adopted-factor owner or transferring those factors to PMM.

Use the bundle's source hashes, exact XML/page locators and independent
arithmetic when resolving the remaining cases. Keep raw reports, Drive
identities and complete rows private. The report work made no new live
ETABS calculation and did not alter the then-recorded native C29 conditional
result or free-body gate. The later S02 checkpoint above closes those six
first-order balances while retaining the coupled critical-load method gate.
Fresh verification on baseline `35fd32326f9014e77a31080ee69591eea8775378`
plus the recorded patch passed 1,690 Python tests with zero skips and
11 JavaScript test files; the ledger pins the tested files and commands.

## Earlier original-source C29 calculation with explicit axial idealization

Windows ran the actual original-source C29 vertical slice from
`RUN-464231f1e18f465f88da868f7306a753` into
`RUN-be9d8258796f4dfca1a3609453e94e53`. R08 and R14 consume 18/18 cuts at
members 225 and 142. All eight distinct connected beams have bound design
shear. Joint 40 has 16 X and 16 Y interval checks. R14 records 2/87
conditional numerical closures with explicit second-order and method
acceptance gates. See [current results](../CURRENT_STATE.md) and
`EV-C29-SELF-WEIGHT-NMAX-LOCAL-20261121`.

The independent local audit of the original run repeated 16/16 stages with
identical results. Use the existing 18-cut common physical comparison and
the matched-joint deformation table from
`EV-C29-COMMON-CUT-COMPARISON-20261121`. That run's common native-node criterion passed for both members. The
later METHOD checkpoint above completes the full-span and conditional
same-run frame comparison. Read the C104 and alpha work below for their
scopes.

## Earlier branches

The earlier C29 work tips have identical trees to the published
checkpoints `5f7a3aa`, `1676af9`, `4aaaf6d` and `eb63282`. The current
engine and tests carry the earlier modal, A1, capture-unit, R08 story and
execution-console behavior. The separate [15 November status report](../engineering/STATUS_20261115.md)
is preserved from `4bbf7b4` as a dated record of the earlier 44-row
comparison and its original run locator.

## Earlier published implementation and replay method

This historical remote software milestone started at full baseline commit
`eb6328290a66484c8ddbc8ba37158be270b8fc5d`. Read
[the method and exact commands](../engineering/VARIABLE_AXIAL_SLICE_20261121.md)
before the historical steps below. The existing selected TS 500 path now consumes
an explicit self-weight Nmax idealization with independently complete source
cuts, primitive superposition and local-N section evaluation. The public example
calculates the real production owners through conditional R14 completion.

To reproduce, run `tools/prepare_axial_idealization_scenario.py` against the
finalized C29 matched-EI scenario receipt, then the normal `run-pipeline` command.
Keep the existing K/EI/Rm/global decisions, selected cage and joint 40. This step
needs the already recorded original source, not another ETABS analysis. Inspect
the actual C29 source-premise outcome, coefficient Nmax/local N, magnified PMM,
column and beam shear and joint outcomes. Preserve every remaining condition.
Do not substitute the synthetic 2/2 result for C29 or the building's 87 members.

This declared idealization is not an approved variable-axial TS 500 method.
Method qualification, coupled C104 design and alpha-below-one acceptance
remain separate work. The refined frame-model story inputs were subsequently
bound by the native METHOD checkpoint above; full column-wall inputs remain
open. The private local capture and Windows working tree were not inspected
at this earlier remote checkpoint. Never overwrite newer local work
to match the published baseline. Fresh verification is
`EV-VARIABLE-AXIAL-NUMERICAL-SLICE-20261121`.

## November 21 consuming-design milestone

The remote feature branch `work/vertical-slice-adopted-basis-20261121` starts at
`0f1a809299ed0dbb6e0ecfde77be0642e1771ce3`. Its adopted-basis inputs are consumed by
the existing selected R08 and R14 path. See the
[implementation report](../engineering/VERTICAL_SLICE_20261121.md) and
[fresh verification](../engineering/vertical_slice_20261121/VERIFICATION_RESULTS.json).
The public examples are executable synthetic contract fixtures, not the current
original building or a new live capture. Preserve the local/private history below.

The feature commit `32b3158` was checked against the actual Windows baseline.
The existing pipeline then computed the C29 sensitivity from the frozen
original model at members 225 and 142. It evaluated 18 signed static cuts and
48 assigned spectral case-cuts, with shared joint 40 in the same sealed
results. Both R08 members consumed the scenario. R14 closes zero original
columns. See `EV-C29-ADOPTED-BASIS-LOCAL-20261121` and the
[current checkpoint](../CURRENT_STATE.md) for the exact scope and next input.

The next Windows run bound six C29 project roles separately from its two force
request roles. R03 reconciles the configured EDZ preset and actual zero-state
solver stiffness. R08 balances the native gravity cut changes against LC_DL
self-weight for both members. See `EV-C29-R03-ORDER-AXIAL-BALANCE-20261121`.
The subsequent private ETABS run solves the three exact gravity combinations
at both orders and compares the 18 C29 cuts through R08 and the same selected
cages. R14 projects that comparison and retains the variable-axial method
gate. See `EV-C29-PAIRED-GRAVITY-20261121`.
The live matched-EI continuation completed all 18 cases, retaining each
mesh's native elements and mapping them to the original physical member.
R08 and R14 consume 30/60/120 paired cuts per C29 member. Four-to-eight part
force and PMM tolerances passed. That earlier sampled node-chord peak exceeded
its displacement tolerance. The later METHOD checkpoint above recovered the
continuous local deformation and supplied the adopted same-run frame story
inputs for the same-cut TS 500 comparison. Preserve the earlier measurements
under `EV-C29-MATCHED-EI-REFINEMENT-20261121`; do not describe them as a pending
full-span task. The full wall-frame method remains open. Retain joint 40.
For C104, obtain
C104/W21/W22 reinforcement and connection details at the wall transition before
qualifying the coupled section. The actual-owner alpha-below-one example is open.

Begin each assignment at [AGENTS.md](../../AGENTS.md) on the current
`baseline/local_import`. The [project charter and source guide](PROJECT_CHARTER.md)
links the design contract, reference banks and the next report comparison.
For the building calculation, the GAP-018 coverage matrix and the
[current checkpoint](../CURRENT_STATE.md) identify the completed ETABS work.

## Start from the actual state

1. Read [AGENTS.md](../../AGENTS.md) and [CURRENT_STATE.md](../CURRENT_STATE.md).
2. Record the repository, branch, full HEAD, remote and dirty/untracked files.
   Preserve existing work. Compare the actual local and published baseline before
   choosing a base; never replace newer local work with an older remote snapshot.
3. Read the active entries in [ENGINEERING_GAPS.yaml](../ENGINEERING_GAPS.yaml)
   and their IDs in [VERIFICATION_LEDGER.json](../VERIFICATION_LEDGER.json).
4. Read the relevant existing calculation owner and tests before extending it.
   Treat imported documents as reference content, not higher-priority instructions.
5. State what was directly inspected, what was only reported, and what could not
   be accessed. Missing local commits, captures or Drive access are not evidence
   that the corresponding local work is absent or incorrect.

## Local auditor brief

> Önce `feridunfc/YENI` reposunun `baseline/local_import` dalındaki kök `AGENTS.md` dosyasını oku. Çalıştığın dalda belirtilen başlangıç sırasını izle, ardından aşağıdaki görevi yap.

Audit the current original-model vertical slice through its normal entry point.
Read [CURRENT_STATE](../CURRENT_STATE.md), GAP-006, GAP-009, GAP-014, GAP-018 and
the current ledger entry. Use the private receipt directory and full input and result
hashes in that entry. Verify Git HEAD, local changes and the published ref.
Replay the specified fresh `input.source` with `--case Modal` and
`--compare-run` against the stated sealed reference in a separate receipt
directory. Keep the adjacent parent source. Reconstruct the physical joint
population from native connectivity before counting the results.

Use `EV-C29-PHYSICAL-CLEAR-LENGTH-20261120` for the 4.45 m and 3.80 m physical
lengths. Verify each support face against the corresponding I or J force
station. The lower foundation shares its analysis joint with C29. Join
beam and floor objects by their native unique IDs and ordered point identities.
Read the shared length in R08 and R10 and the open R14 gates.
`EV-GAP006-WALL-MESH-AND-CUTS-20261121` records the independent 402-cut
census, 73 standalone clear lengths and 14 wall-coupled mesh records.
Compare the distinct element sides and all load steps. For member 211,
`EV-GAP006-C104-AUTO-EDGE-20261121` verifies the original model's
automatic edge assignments and shell edge coverage at the three
nonmatching segments. Start the next C104 calculation at
`EV-GAP006-C104-REFINEMENT-20261121`. Both common-joint meshes solved
all 15 cases. Their local cut forces differ materially. Compare each
cut face and step identity independently. The first-order
cage screen covers the new cut census. Use the wall-boundary detail
and coupled section to qualify the next design demand.
`EV-GAP006-C104-SECTION-PROFILE-20261121` gives the model-based
gross geometry on both sides of −1.50 m. Preserve the separate
W21/W22/C104 scope. The native `xP2` group also includes W23–W26.
`EV-R10-WALL-COUPLED-CAPACITY-SPAN-20261121` records the R10 guard for
members with interior wall contact. The R14 design check remains open
until the physical span or the coupled design section has been established.
For C29 effective lengths use `EV-C29-TS500-EFFECTIVE-LENGTH-20261121`.
Trace the axis-length frame terms and the two clear spans into R08. Use
`EV-R08-MAT-HORIZONTAL-BOUNDARY-20261121` for the production mat restraint
and displacement calculation. Reconstruct the 32-column base roster
from native connectivity and verify both directions against the matching
RSX/RSY point rows. At joint 934, both global horizontal DOFs are restrained.
Use `EV-R08-TS500-PAIRED-STATIC-20261121` for the completed matched
ETABS first- and second-order comparison. Each occupied story direction
has an exceedance of the 5% threshold with the original signed static
reference loads. Use `EV-C29-MAT-ROTATION-CALIBRATED-LENGTH-20261121`
for the four mat-only perturbations and the resulting two-axis C29
effective-length reference. Match the beam strips against the actual
floor polygons. Check equilibrium, reciprocity and the opposed
permanent and total shears in the signed reference scope.
`EV-GAP009-SIGNED-STORY-MAGNIFICATION-20261121` records the 48 signed
story/axis checks and 48 C29 signed PMM checks under the specified
`Rm = 1` sensitivity model. Qualify the wall-frame stiffness, adopted
creep convention and assigned design demand before applying the
factors to design. The physical scope accounts for six
occupied story directions and the empty +14.5 story.
`EV-GAP009-ASSIGNED-SPECTRAL-SWAY-20261121` extends the same calculation
to the eight inlet seismic combinations. Sum the upper column compression
for each story and keep source cut and step identity. Use the two Eq. (7.29)
readings to bound the local factor, then apply the minimum eccentricity
before magnification. For the 14 coupled columns continue from
`EV-R08-WALL-COUPLED-ISOLATED-GUARD-20261121`. R08 returns the native cut
evidence and the coupled-model requirement. Use a coupled second-order
analysis for their interior force transfer.
`EV-GAP009-ORIGINAL-FIRST-ORDER-20261121` identifies the original
first-order baseline. The archived ETABS log shows zero-state stiffness
for both the static and Ritz stages. RSX and RSY use the resulting modal
basis. For a second-order comparison, keep the load definitions and
cuts fixed and track the changed stiffness basis through both spectra.

For assigned C29 shear use `EV-C29-SPECTRAL-SHEAR-20261120`. Both C29 segments
have eight assigned cases for V2 and V3 inside the selected R10 capacity shear
result at `assigned_spectral.axes`. Verify the two end cuts, the continuous
upper moment bound, ordinary shear floor, full-moment demand, and resistance at
the lowest compression within each case. The independently captured model-D
controls are indexed in the same ledger entry. Compare all Min/Max values
at the same native cut. Local resources index the two segments, their
shared joint, the private audit and the source files.

For the earlier story calculation, use `EV-STORY-STATIC-APPLICABILITY-20261120`.
Trace the +4.50/X result across the 32 common bottom cuts. Recompute the signed
global force from each column's recorded axis angle and both local shears.
Reconstruct maximum compression from each assigned gravity combination plus
and minus one supplementary static case, over all native cuts. Check both
the numerator population and the source load definitions. Then inspect the
separate applicability result for the eight assigned spectral families and
the R14 column ratios. The ledger indexes the 16-stage comparison.

For C29 the same ledger entry identifies a separate native read for all
eight model-defined capacity combinations, together with eleven original
control combinations. Use its existing rows and cuts for both members.
The earlier 520-line November 20 audit reproduces one of 160 transcribed moment ratios
at six decimal places. Use the sealed numerical rows for the remaining 159
and the already factored beam sum for each sway. Local resources point to
the corrected 40-row table. The subsequent 293-line audit reproduced all 160
ratios, all 160 axial endpoints and all 120 moment values at printed precision.

Starting from a governing non-exempt joint, reconstruct column-end component
extrema, selected cages, section equilibrium, beam-end signs and the required
1.20 moment sum. Check both sways and both directions across every assigned
seismic family. Cross-check the report with the sealed numerical witness and
trace the result into R14. Test a missing end or case, an insufficient interval,
and a proven panel failure beside an exhausted cage. Establish §7.3.6
applicability for a full story-direction from both ends of every column.
When the alternative is needed, inspect the original story shear population
and identify the first missing compatible quantity for alpha.
A review finding should name the source line, a reproducer, the
observed numerical effect and the smallest correction. Record commands, tested
revision and input hash for each result. Keep any private captures local.

## Baseline and local ownership

`baseline/local_import` is the logical main. The user wants it kept current.
Develop mainly in the existing local checkout. Start scoped `work/<scope>`
branches from the latest verified baseline; integrate completed and verified
milestones back into baseline before handoff. Keep unfinished work separate.
Synchronize baseline to GitHub with a normal push and verify the returned remote
HEAD against the exact local commit. Record failed or pending publication rather
than claiming synchronization. There is no scheduled background sync.

The historical `main` and audit branches are references, not the integration base.
Do not merge to main, change the default branch, force-push, reset, clean, replace
the checkout, or stage everything indiscriminately. Stage the selected changes.

A GitHub worker must record its exact published base and work on the requested
scope. If it cannot inspect the local checkout, say so. Return a branch/commit,
changed-file list, evidence and limits for local integration. Do not overwrite
baseline with a competing snapshot or claim that a remote review includes local
unpublished files. A delivery ZIP is imported selectively after comparison; it
does not authorize wholesale replacement of the production tree.

## One engine, one acquisition route

The production runtime is `src/tbdy_next`; web and CLI share
`engineering/pipeline.py::EnginePipelineRunner`. Reuse the owners listed in
[AGENTS.md](../../AGENTS.md) and
[PIPELINE_UNIFICATION](../engineering/PIPELINE_UNIFICATION_20261115.md).
New checks belong in the existing registered pipeline and sealed-result flow.
Do not add a second solver, COM attachment path, report-time calculation or a
collection of production scripts. Private one-off verification is evidence only.

Use terminal/API operations without taking over the user's mouse. The local
user-launched server can access ETABS even when an isolated terminal cannot.
Rediscover the session/PID. The existing gateway may set kN/m/C (API code 6) as
authorized; API code 12 means tonf/m/C. Restore temporary output, pattern and mode
selections and verify restoration. Do not infer permission to run analysis,
change the model/design or save the EDB from permission to read results.

Use ETABS unique member IDs and preserve model, source, case, step, physical cut,
analysis-element side, station, local axes, sign and units. Freeze expected scope
independently of successful rows. Reuse the original precision for arithmetic;
round only presentation. Selected column As must be at least 0.01 Ac. Selected
candidates, recorded ETABS templates, approved cages and as-built cages differ.
Spectral component bounds and their corners do not prove concurrent force vectors.

## Earlier candidate-selection checkpoint

The initial selected scenario was `RUN-4c6e8d795ca94411a1cd6d7f7f54c9de`:
87/87 columns have the same-run bound candidate of 32 bars of 16 mm diameter,
10 mm ties at 90 mm, and three crossties per local direction. As is 6,433.98 mm²
against the 6,400 mm² minimum. The earlier 8 mm tie trial is retained but was
not adopted. JSON/HTML and workspace tabs 4.2, 4.4, 4.5 and 4.6 project the saved
candidate schedule for all 87 unique IDs; they do not recalculate it.

| Evidence scope | Recorded result | Limit |
| --- | --- | --- |
| Native modal milestone | 100 modes, 2 eccentricity definitions; 500 independent numeric relationships; 16/16 identical repeat receipts | Definitions do not prove applied torsion or active damping |
| Candidate reference calculations | 1,206 magnified PMM rows; 25,728 spectral corners; 435 independent bar-area comparisons | Reference assumptions and component bounds are not complete normative acceptance |
| Earlier modal tests | 1,407 Python tests, 1 OS-specific skip; 10 JS files; 241 installed-wheel tests | Historical milestone scope; not rerun for this handoff |
| Candidate-report tests | 30 focused Python tests; 11 JS files; sealed report made zero calls to 27 disabled calculation entry points | Full Python/wheel/CI were not run for that presentation increment |
| Initial handoff at `24ddc371` | Documentation, evidence links, hashes and Git identity checks | Engineering tests and live ETABS capture were outside that checkpoint |

Read [native modal acceptance](../engineering/LIVE_MODAL_IDENTITY_ACCEPTANCE_20261118.md)
and [candidate acceptance](../engineering/COLUMN_CAGE_SELECTION_ACCEPTANCE_20261119.md)
for commands, environment, tested-file manifests, failures/retries and provenance.
Do not retarget their test results to an untested version.

At this earlier candidate-selection checkpoint, R14 was **0 closed / 87 partial**,
with 17 unresolved gates, and spectral alpha iteration was **0 / BLOCKED_INPUTS**.
Use the later C29 and story checkpoints for their distinct current scopes.
Formal compliance remains **NOT_PROVEN** and
engineering release is **NOT_READY**. Selection and low numerical utilization
do not approve physical lengths, effective-length factors, sway/creep, hooks,
anchorage, analysis generation, SCWB or spectral alpha policy.

## Reference resources

The [English recipe](../engineering/reference/recipe_20261118/README.md) is the
current entry point for the recipe, 73 stable example identities, mappings and
provenance. Its original delivery inspected an older published snapshot; use the
local binding and later evidence to interpret it. Preserve source/derived/contract
fixture distinctions. A 73-entry catalog is not 73 accepted production checks.

`YENI_P0` is strictly read-only. The TBDY, Column and Column-Engine repositories
and other historical local projects provide reference contracts and independent
lineage, not additional production runtimes. Use pinned revisions and hashes
from their provenance; do not promote a changing reference HEAD to an authority.

Google Drive contains private reports, standards and reference examples. Access
depends on the connected account. The local resource index records the verified
connection and useful file/folder identities; do not assume a GitHub worker has
that access. Use existing private SQLite/PDF banks and source manifests before
searching again. Similar filenames or models are not a valid cross-model join.

Private paths/account information are in the ignored
`.receipts/handoff/LOCAL_RESOURCES_20261119.md`. Raw EDB, SQLite, PDF reports,
captures, credentials, environments and build copies are excluded from public
publication. GitHub code backup is not a backup of those private artifacts.

## Continue the column and joint calculation

Read `GAP-018.coverage_matrix` before requesting another capture. The finished
private comparison isolates static eccentricity at 804 direction-cuts and
reproduces the zero-eccentricity spectrum under the tested 5% damping model.
The original/private transfer still has 138 scalar exceptions. Keep each result
with its own analysis generation.

Replay the original selected scenario through `tbdy_next.cli run-pipeline`.
Read `r14_closure.columns[].pillars.second_order_selected_pmm.governing_static_station`
for the coincident force row, selected radial capacity and reserve at fixed N.
On each joint axis, `joint_transverse_7_5_2_3.max_whole_spacing_for_selected_tie_mm`
sizes the pitch for the proposed legs. The local worked roof-joint example follows
the signed load sum through both sway directions and tie sizing. At the same
column's lower interior joint it also gives the conservative demand upper bound
with zero shear deduction. The original
selected input, a command and a compact result census are indexed by
`EV-COLUMN-JOINT-SLICE-20261119`. Public fixtures exercise both calculations.

Retain the interior joint's zero-deduction result as a conditional upper bound when the
physical mechanism and sign convention establish a nonnegative deductive column shear.
A passing qualified upper bound does not need a favorable measured deduction to prove
that inequality. When a reduced demand is needed, bind complete upper/lower column-end
shears to the same applicable earthquake demand family, direction, physical cuts and
source generation. Missing, ambiguous or nonconcurrent rows cannot authorize a reduced
deduction. Compute both sway demands and the selected tie pitch through the existing owners.

Complete the interior SCWB axial-demand policy, physical end applicability and one full
storey/direction population before alpha feedback. The original/private 138-control
transfer question is separate from the missing production spectral method transition;
fixing those comparisons alone does not enable spectral SCWB or alpha. Implement the
accepted bounded method already described in the recipe through the existing R08/R10/
alpha owners and gateway. See ../engineering/AUDIT_FIXES_20261119.md for the current adapter milestone.

GAP-005 general scheduling and GAP-017 complete CheckInstance accounting remain
open. Do not relabel the current pipeline as a fully accepted structural engine.
