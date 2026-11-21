# C29 calculation completion: execution task

> Önce `feridunfc/YENI` reposunun `baseline/local_import` dalındaki kök `AGENTS.md` dosyasını oku. Çalıştığın dalda belirtilen başlangıç sırasını izle, ardından aşağıdaki görevi yap.

## Deliver the calculation

Complete the revised-model C29 calculation through the existing
`EnginePipelineRunner`, R08, R14 and sealed report. Deliver revised TS 500
factors, design moments and selected-cage PMM at the **18 common physical
case-cuts / 24 finest-mesh element sides**, and evaluate the **full-span
deformation comparison for both members and all three gravity combinations**.
Keep the original-source **2/87 conditional numerical closures** separate.

The next milestone must contain these numerical outputs. A new capture, hash,
replay, source inventory or report with empty revised-TS500 columns does not
complete it. One canonical calculation report is sufficient. Its provenance and
verification support the calculation; copying the same audit to several folders
is not another deliverable.

This is a bounded C29 method-comparison task under GAP-009, with focused
GAP-016 owner comparisons. It does not require finishing C104 or all 14 coupled
wall-frame designs first. Those members must nevertheless remain in the required
story force and stability population. Do not remove them to obtain a result.
Do not require a new general solver, pipeline, database or ETABS connection.

## 1. Start from the actual state

Inspected integration commit: **`d85c6e8670b65ba2236cc5a0960e7e59720a8dd0`**.
The task author inspected that committed source and the existing reference
records. Unpublished Windows changes, private EDBs, scripts and receipts were
**NOT_INSPECTED**. Use a newer local implementation if present; preserve dirty
and untracked work and reconcile it before starting a scoped work branch.

Reuse these completed checkpoints; do not make reproducing them the next sprint:

| Checkpoint | Scope and treatment |
| --- | --- |
| `EV-C29-COMMON-CUT-COMPARISON-20261121` | Published code/ledger inspected. Original C29 reference has 18 physical case-cuts and 24 finest-mesh sides. Both sides at the internal interfaces remain distinct. |
| `RUN-0e263530db30483f95f1013894bc01db` | Private source comparison identified by the user; its bytes were not inspected for this task. |
| Auditor replay `RUN-d3f8a6eee21446b19ab67a38e7d91bfb` | User reports 16/16 stages `IDENTICAL`; not a fresh execution by the task author. |
| Auditor report SHA-256 `c97ed1a0cb267298a37a8bf9990ea86600148fda2027f275c386e5bd90a176ab` | User-reported identity, not independently rehashed here. Four copies are one report. |
| Common 4/8 native-node comparison | Recorded maximum vector differences: 225 = `4.722377174145617e-6 mm`; 142 = `8.035826765051811e-7 mm`. This narrower criterion passed. |
| Remaining calculation | `UNVERIFIED_BETWEEN_NATIVE_JOINTS` and `REVISED_TS500_STORY_BASIS_UNAVAILABLE`; original scenario remains conditionally calculated. |

The **18 case executions** in the 2/4/8-mesh study, **18 physical case-cuts**,
**24 element-side rows**, and **420 existing refined-cut assessments** are
different populations. Preserve their names and denominators.

## 2. Use the existing consumers

All paths below are relative to `src/tbdy_next/` and were verified at the full
commit above. Function names identify existing code, not proposed replacements.

| Work | Existing owner | Required change or use |
| --- | --- | --- |
| Scenario admission | `engineering/design_scenario.py`; `engineering/gravity_order_pair.py::normalize_gravity_order_pair` | Extend the existing `gravity_order_pair` contract and lineage. |
| Refined input | `engineering/gravity_pair_refinement.py::normalize_levels` | Its strict level keys and present schema need an explicit compatible extension for kinematics and source qualification. |
| Mesh and cut identities | `engineering/gravity_pair_refinement.py::_member_mesh`, `_paired_cuts`, `_method_comparison` | Preserve physical faces, element identities, case/step and both interface sides. |
| Displacement consumer | `engineering/gravity_pair_refinement.py::_node_chord_profiles`, `compare_level`, `_mesh_change` | Current input accepts exactly three translations; full-span status is hardcoded unverified. Implement the actual six-DOF consumer and qualified recovery. Capture alone cannot fix this. |
| Existing six-DOF convention | `column_engine/column_kinematics.py` | Reuse its named global displacement convention and m/rad discipline; preserve its distinction between joint and member-section rotations. |
| Revised TS 500 calculation | `engineering/gravity_pair_refinement.py::_refined_ts500` | Feed qualified same-revision story inputs; it already invokes Euler, factor, moment and PMM owners. |
| Effective length and factors | `engineering/column_effective_length.py::effective_length_reference`; `column_engine/ts500_column.py::effective_length_factor`, `euler_load_kn`, `adopted_magnification_factors` | Derive K and Nk from their actual inputs. Do not create an ETABS Nk getter or another factor formula. |
| Design moment and capacity | `engineering/column_r08_local_live.py::_adopted_axis_factor`, `_magnified_moment_demand`; `column_engine/section_capacity.py` | Keep coefficient Nmax, cut-local N, minimum eccentricity and selected-cage assessment in their existing owners. |
| Acquisition | `etabs_source_gateway_windows.py`, `live_etabs.py`, `frame_force_capture.py`, `basis_probe.py` | Use the current connection, guard, units and transaction route. |
| Pipeline and report | `engineering/pipeline.py::EnginePipelineRunner`; `engineering/column_r14_closure.py`; `engineering/pipeline_snapshot.py`; `reporting.py` | Persist the calculation once; JSON/HTML render recorded results. |

The current explicit R08 method identity is
`column-r08-local.adopted-basis.v12`; the gravity pair schema is v1. Version
changed input semantics and method behavior deliberately. Preserve the package
fingerprint and old receipt compatibility. Do not rewrite historical receipts.

## 3. Implement the consumers before the next capture

First extend the strict input contract, the displacement consumer and the
same-revision story producer. Run one actual-owner offline integration case
through the normal runner. Then collect the exact fields these consumers need.
This prevents another live acquisition whose new data are never consumed.

### A. Restore usable private analysis results

The observed private state is an unlocked model with none of the six required
cases finished. The claim that restoring run flags and saving caused the loss
is a hypothesis until the private script and operation log are inspected.
CSI distinguishes run selection, case status and deletion; unlocking deletes
analysis results. Record the actual transition, rather than repeating an assumed
cause. See the primary references below.

1. Inspect the actual private `read_method_sources.py::read_models` and its
   reported `if index:` branch. It was not available to the task author. Through
   the existing session, explicitly open the intended allowed METHOD copy at
   **index zero as well as later indices**, after checking the current session
   and safe file-switch state. Check return code and read back full file identity,
   intended mesh, units and case definitions. Do not discard unsaved unrelated work.
2. Use `KOMPAKT_C29_METHOD_2.EDB`, `_4.EDB`, `_8.EDB` only after checking each
   against its own prepared model and semantic settings. Different meshes should
   not be required to share a binary hash. Preserve the original building EDB.
3. Resolve the exact six declared gravity states per model:
   `C29G_U_F`, `C29G_U_P`, `C29G_TN_F`, `C29G_TN_P`, `C29G_TP_F`, `C29G_TP_P`.
   Verify these names against the actual definitions and original combination
   coefficients. Include genuinely required prerequisite cases. Reuse a completed
   archive only when its model, generation, case definitions and needed fields
   match; otherwise rerun the affected private cases. Avoid unrelated analyses.
4. Verify each required case reached its final solved state and returned the
   expected nonempty force and displacement populations. Distinguish case status
   from its run flag. Capture results before operations that invalidate them.
   Read back state after flag/selection restoration and save/reopen. The handoff
   must identify a usable solved copy or its complete archived source, not an
   unexplained 0/6 model. The original EDB must retain its initial SHA-256.
5. Compare a new solve with its matching archived mesh at identical physical
   cuts, cases and steps using declared numerical tolerances. Do not demand
   byte-identical floating-point results from a new analysis. Hash identity checks
   immutable bytes; numerical agreement checks solved quantities.

Capture six displacement components with native point/element identities,
case, final step, units, output axes, mesh coordinates and generation. Translations
must resolve to metres and rotations to radians. Include frame axes, rigid-end
factors, offsets, releases and relevant panel-zone/constraint transformations.
Read enough numeric precision to resolve the adopted `0.01 mm` comparison.
Do not append rotations to the old three-value arrays and assume they will work.

Capture the first-order frame and wall force populations required by each
relevant horizontal story cut. The proposed `+0.00` and `+4.50` levels are
identities to reconcile with actual physical faces, not assumed coordinates.
Bind every contribution to the same revised model, case and final step.

### B. Finish full-span deformation recovery

Keep the present **original-endpoint-joint chord / global X-Y** diagnostic.
Define the new comparison over the same physical clear interval in both meshes.
If using a physical-face chord, derive both face displacements consistently;
do not relabel the old joint chord as a face chord.

Qualify a recovery appropriate to the actual frame formulation. CSI describes
cubic bending and linear shear contributions between rigid ends. Raw joint
rotations are therefore not unconditional Euler-Bernoulli slopes. Resolve axes,
rotation signs, shear, releases and rigid offsets before selecting an expression.
Use a documented within-element recovery or a qualified native result route;
do not build a second finite-element solver.

Required calculation and checks:

- An independent analytical or manufactured displacement case with a known
  nonzero interior maximum and location. Its expected arithmetic must not call
  the production recovery. Exercise the model features used by C29; a bending-only
  example alone does not qualify a shear/offset recovery.
- Evaluate the 4-part recovery at the added 8-part native joints without fitting
  to those values. Report that this tests combined recovery/discretization effects;
  it is not an independent derivation of the recovery formula.
- Evaluate both recovered fields at common physical coordinates. Find the maximum
  absolute difference of each signed component and the maximum norm of the vector
  difference, retaining signed differences at the governing locations. Find each
  field's maximum norm and location over every segment. Locate endpoints and interior stationary points, or
  bound the numerical extremum-search error. A dense grid with no error bound is
  not a verified full-span maximum. Do not combine component maxima at different
  stations into one displacement vector.
- Declare one error budget for recovery, mesh difference and extremum search
  against `BOW_TOL_MM = 0.01 mm`. Report quantities separately; do not spend the
  full tolerance independently on all error sources. Retain the existing
  common-node result as a separate diagnostic.
- Replace the unconditional `full_span_peak_status` with a calculated result
  for both members and all three gravity combinations. Missing prerequisites
  remain unresolved; a calculated excess is a visible failure. First diagnose a
  failed quantity before prescribing 16/32 meshes or loosening a tolerance.

The defensible completion claim concerns the peak of the stated numerical
displacement representation and its mesh comparison. It is not an exact physical
continuum solution or a general proof that constant Nmax is conservative.

### C. Produce and consume the revised TS 500 basis

The existing consumer takes the following fields; this is its current shape,
not a new parallel schema. Extend its surrounding provenance contract as needed:

```text
gravity_order_pair.refined_levels[level].story_inputs[member_id][M2 or M3]
    k
    story_aggregates[exact_original_gravity_combination]
        nd_kn
        nk_kn
```

For each mesh, member, axis and gravity combination:

1. Build the expected physical story-cut population from geometry before
   summing successful rows. Transform local forces into the required compression
   direction with a declared sign convention. Count each physical contributor
   once. Preserve both interface force sides for local design, but do not count
   both in a story total. Do not add pier and shell representations of the same
   wall, or add `Story Forces` to member sums. Use story equilibrium as a
   reconciliation check with an explicit free body and self-weight allocation.
2. Derive end-restraint contributions, per-axis K, physical ln, lk and member Nk
   with the existing owners. Record E, native I, section/object modifiers, selected
   EI, creep convention and boundary assumptions. Check actual resulting EI;
   `IMod = 0.2792206663` is the previous C29 setup, not a universal modifier.
   Do not reduce the already selected EI twice or apply that ratio to the building.
3. Produce the corresponding story critical-load sum with its contributor list
   and supported method. Retain every required column/wall in the population.
   A missing wall method is not zero load, a generic gross-section Euler capacity,
   or an unexplained `qualified: true`. Identify the exact unsupported term and
   current calculation owner. Calculate all supported terms and C29 outputs that
   remain valid; do not wait for unrelated reinforcement drawings to compute
   available frame terms. An explicitly adopted scenario must retain that status.
4. Feed the verified same-revision values to `_refined_ts500`. Original-model
   totals cannot be silently reused. Derive coefficient Nmax from revised
   first-order cuts while retaining each cut's local N for eccentricity and PMM.
   Use the existing selected 32Phi16 cage and Phi10/90 transverse scenario and
   its immutable identity. Preserve the current factor/length interpretation;
   a proposed interpretation change is a separate, explicit scenario.
5. Populate original TS500, direct native P-Delta and revised TS500 columns
   at all 24 finest-mesh reference sides. Direct second-order vectors must not
   receive the same second-order amplification again. Preserve source forces.

For the finest mesh this produces **12 axis factors** (2 members x 3 cases x
2 axes), and **24 revised design-moment/PMM rows** at the 18 physical case-cuts.
Retain every additional refined cut; the common reference set is not the entire
analysis population. If a real stability limit prevents a factor, report its
inputs, denominator, limit and failure at the affected row. Do not replace a
demonstrated failure with a generic request for more evidence.

Show signed moment change, absolute-magnitude change and utilization separately.
For example, `-12.486 -> -10.485 kN.m` is a positive signed change and a decrease
in magnitude. It is not a 2.0011 kN.m increase in bending demand.

## 4. Use the existing examples to check the owners

Read [the source guide](../context/PROJECT_CHARTER.md) and
[the preserved recipe](reference/recipe_20261118/README.md). The frozen recipe
describes its historical import; its old status counts are not today's state.
Do not rewrite that package to make old runs appear fresh.

Drive examples are available: the task author read `ex_Hesap Raporu6.pdf`,
including its second-order and joint-shear tables. The local source copy matches
recipe `GE-S04`. It is not GOLDEN-01. Two relevant calculation examples below
also have accessible, hash-checked source copies. Thus this step is a specific
source-to-owner comparison, not another general search for example reports.

| Existing example | Source and locator | Required production comparison |
| --- | --- | --- |
| `GE-CHK-117` / `CHK-117` | `GE-S11`, `sway1.docx`, S1 / Storey 3; PDF and atlas pages not applicable | Call `effective_length_factor` and the applicable `effective_length_reference` adapter. For the `SWAY_PREVENTED` example, end ratios 1.975/1.975 and ln = 2550 mm give independent K = 0.8975 and lk = 2288.625 mm; printed K is 0.90. Exercise zero-ratio boundary and missing-neighbor rejection. Missing restraint is not zero restraint. |
| `GE-CHK-119` / `CHK-119` | `GE-S02` / GOLDEN-02, `2.pdf`, SZ01 ground storey, original PDF page 186, printed page 184, atlas page 11 | Finish factor selection through actual design-moment consumption. Existing member beta = 1.549351615064668 and story beta = 1.1927649705815873 are already scalar matches. The report's 1.85 corresponds to product 1.848012333563144. The printed-lk reading gives 60.390838 < 83.789339, so the existing effective-length policy chooses MAXIMUM. Preserve `G02_USED_FACTOR_SZ01_ground` as an interpretation difference until the method is resolved; do not tune code to force 1.85. |

Source identities:

| Source | SHA-256 |
| --- | --- |
| `GE-S11` | `6e8863ae52834af5febbdd30db0648de186a713f7da991e05db660bb2425b0d7` |
| `GE-S02` / GOLDEN-02 | `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31` |
| `GE-S04` | `f63e5de2b80fbee33eec9d5cf957820b592aa7821fc854d325c8699047ef87b9` |

These examples test defined operations. Their K, loads and story totals must not
be transplanted into C29. Reported Nk does not independently verify EI or creep;
back-calculating EI from Nk is only a consistency check. `GE-CHK-118` is an
effect-ownership contract fixture, not a physical displacement oracle.

Keep 73 recipe examples, the 44 production comparisons, and both historical
333-record arithmetic scopes distinct. The stored current 44-record result is
**33 numerical matches, 7 source/method records, 4 interpretation differences**.
It was not rerun for this task brief. Existing sources that already supply
numbers must not be relabelled as missing PDFs when the actual issue is a
production adapter or a method decision. No new CHECK identifiers are required.

## 5. Validate the changed calculation, then publish

Extend existing tests, starting with
`tests/test_adopted_second_order_basis.py` and
`tests/test_variable_axial_vertical_slice.py`:

1. One normal-runner positive fixture must reach real R08 factors, actual
   selected-section PMM, R14 and the sealed report. Do not replace stage outputs
   or capacities with success dictionaries. Include an interior deformation peak.
2. Check missing rotation/axis metadata, wrong units, missing or duplicate
   joint/case/side, stale model generation, omitted wall/column contribution,
   mismatched K/EI and an actual stability or PMM failure. Retain the expected
   population and report the affected item.
3. Change Nd, Nk or K and show the real factor/design-moment result changes.
   Change a rotation and show recovery changes where physically expected.
   Verify old three-translation records remain readable but do not acquire
   a new full-span qualification.
4. Render JSON/HTML with calculation owners prohibited, using the existing
   projection test pattern. Rendering must not calculate engineering results.
5. Run focused tests during implementation. Once the calculation changes are
   complete, run `python -B tools/test_offline.py` with the actual project
   interpreter; record the returned Python/JavaScript counts. Follow the existing
   installed-wheel gate when packaging changes require it. Run the recorded-source
   calculation and one explicit `--compare-run` after the final method change.
   Existing 1,671-test and 16-stage records are historical, not new executions.

Current `_mesh_change` force comparison covers P, M2 and M3. Either keep that
scope explicit or extend it to V2, V3 and T before claiming convergence of all
six force components. Passing PMM does not qualify missing displacement inputs.

Use the normal runner to seal the original-building comparison. Preserve the
original-source design result, eight connected beams and joint 40. Revised-model
gravity demands must not silently replace the original model's seismic SCWB or
beam demands. Any changed selected demand requires same-revision downstream
inputs through the existing dependency owner.

Commit explicit, reviewed source/test/document paths on a scoped work branch.
After the required checks, integrate the completed milestone into the current
local `baseline/local_import` and publish normally. Recheck remote HEAD and
preserve concurrent work; no force push. Record the actual full published SHA.
Keep private models, captures, receipts, PDFs, account links and machine paths
out of GitHub. Update CURRENT_STATE, GAP-009's achieved scope, the append-only
verification ledger and worker handoff with the actual numerical outcome.

## 6. Return a calculation-first result

The next worker reply and canonical report must start with this information:

| Deliverable | Required content |
| --- | --- |
| Source and analysis | Actual code SHA/dirty-file manifest, model/generation/case identity, required solved-case coverage and usable archived source. |
| Revised factor table | For 225/142, all three combinations and both axes: EI, K, ln, lk, member Nk, story Nd/Nk, coefficient Nmax, beta and applicability. |
| Common-cut table | All 18 physical case-cuts / 24 finest-mesh sides, original TS500 / native P-Delta / revised TS500 moments and PMM, local N, signs and governing row. Keep extra native cuts. |
| Full-span table | Both members x three combinations: stated recovery and physical interval, 4/8 peak values and locations, field difference, error budget and numerical outcome. |
| Downstream result | Original conditional R14 result preserved; revised comparison outcome separate; changed design inputs consumed by the existing dependent owners where applicable. |
| Independent examples | Actual production calls and outputs for the two selected existing examples, and an independent displacement benchmark. Interpretation differences remain visible. |
| Verification and publication | Fresh commands/environment/results, precise remaining inputs or engineering decisions, full GitHub SHA and canonical report locator. |

Completing a numerical comparison does not automatically grant engineering
acceptance or close the whole-building GAP-009. A valid failed calculation is
also a result: show the governing values and a concrete design/method correction.
Do not promise a passing result or silently lower acceptance criteria.

If live ETABS becomes unavailable, complete and publish the schema, producers,
consumers, independent examples and normal-runner integration that can be done
offline. State **original revised-model replay: NOT_RUN** and list only the
specific missing model/case/field or unsupported method term. Do not substitute
an unchanged replay or a new audit plan for the executable work.

## 7. Review boundary and primary references

This publication assigns implementation; it does not claim that the assigned
work has been executed. Runtime code, engineering statuses and historical
verification records are unchanged by this documentation milestone. Document
references, owner symbols, source hashes and scope were checked. New production
comparison, pipeline replay, live ETABS and engineering acceptance: **NOT_RUN**.

Reviewed code-file SHA-256 values at the inspected commit are recorded below.
They identify this review only; the worker must record its actual tested revision.

| Reviewed path | SHA-256 |
| --- | --- |
| `src/tbdy_next/engineering/gravity_pair_refinement.py` | `a65c5e99d657e359aa6b91a2b1a10eb111a2b8bf9905e9d887c09ea155e867c0` |
| `src/tbdy_next/engineering/gravity_order_pair.py` | `fdd72cefc42fd47deb98534ceecd217441d09c433f2d18ea697fae5f5b65b7d3` |
| `src/tbdy_next/engineering/column_effective_length.py` | `5d3bff4348833c2dbba0475c886917e824da506f5b1760decdb846a52952651d` |
| `src/tbdy_next/column_engine/column_kinematics.py` | `1524b8ea2703347f2dd2554e47a72a44856bf4f08c95ed2e3c1a3fb72c9fa3f4` |
| `src/tbdy_next/column_engine/ts500_column.py` | `3dd473cc979f0ec81f5065ba7549a69fa5f1adb9922bce09dc0482de0e84d9c9` |
| `src/tbdy_next/engineering/column_r08_local_live.py` | `5047b017634fd9375d5990ad099ddfa49c4d5d20a305925c890c8a063390c47e` |
| `src/tbdy_next/engineering/pipeline.py` | `0f45fd2441211381a2a0eb13085bb673c82f00a70e64afdcd45894f6b7e179d1` |
| `src/tbdy_next/reporting.py` | `61b33f84eeaa07b8bd3a95461e238b7b0addad1c347898c873df639be70e9564` |

Primary CSI references checked for this task:

- [Lock Model](https://docs.csiamerica.com/help-files/etabs/Menus/Analyze/Lock_Model.htm): result invalidation on unlocking and preservation in separate model copies.
- [Set Load Cases to Run](https://docs.csiamerica.com/help-files/etabs/Menus/Analyze/Set_Load_Cases_to_Run.htm): run flags, solved status, prerequisites and result deletion are distinct operations.
- [JointDispl API](https://docs.csiamerica.com/help-files/etabs-api-2016/html/1bb2ca14-4532-795c-4e5a-50160dc144a4.htm): six components and case/step identity. This page documents the 2016 API; confirm actual installed-version return signatures and semantics.
- [Displacement output conventions](https://docs.csiamerica.com/help-files/etabs/Output_Conventions/Displacements.htm): normal global point output and panel-zone exception; record the actual API/table contract.
- [Analysis Reference Manual](https://docs.csiamerica.com/manuals/etabs/Analysis%20Reference.pdf), printed pages 415-416: bending/shear representation, rigid ends and within-element axial-force averaging. PDF viewers can number the cover pages differently; use the printed page labels and section titles.
