# YENI engineering audit — 21 November 2026

## Review boundary and disposition

Inspected repository: `feridunfc/YENI`, logical integration base `baseline/local_import`; inspected HEAD `c71a4dda4ab9453f428a38b3ed79931f8e6eeea3`. The worktree was clean at review entry. Root AGENTS, CURRENT_STATE, the worker handoff, project charter, all 18 GAP records, relevant latest verification records, production owners and selected positive/negative tests were inspected. This is a focused source audit across the 18 registered engineering gaps, not a formal proof of every source line or a new live building calculation.

**Disposition: continue development on the existing engine. Software regression is reported passing; whole-building engineering acceptance remains unavailable.** The registry contains **3 OPEN, 15 PARTIAL, 0 CLOSED** gaps. Those counts do not mean that none of the numerical software works: many narrower calculations are complete. They also do not support a defensible percentage of engineering completion, because the gaps differ radically in scope and include algorithms, source qualification, physical detailing, product integration and independent acceptance.

This audit found two reproduced production behaviors requiring correction. No new P0 incorrect-READY building release was demonstrated in this lane. The new issues are P1 source/failure-handling defects; all existing limits still matter. The audit did not inspect the original private Windows receipts or connect to ETABS. References to native C29 and C104 results below come from the public verification ledger; a source hash is not a fresh replay of the private source.

The latest user-supplied Windows run is **1,690 total, 1,689 passed and one skipped**, with 11 JavaScript files passing. Its skipped-test identity and complete log hash are unknown. The independent recorded Linux run is a different run with 1,690 passed and zero skipped. This audit did not rerun either full suite.

## Reproduced finding ENG-01 — absolute elevation is incorrectly constrained to be nonnegative

**Priority P1; GAP-009 and GAP-005.**

`engineering/story_pdelta.py::review_story_pdelta` passes absolute `level_m` through `finite`, whose default branch rejects negative numbers. The numerical theta expression uses drift, cumulative weight, shear and story height; changing the global vertical datum changes none of those inputs. The product adapter `story_second_order.py::bind_story_second_order` passes `level.elevation_m` directly to that owner.

The audit reused the existing `tests/test_engine_r08_story.py::example` input. Before a coordinate translation, the owner returned theta maxima X = `0.01`, Y = `0.014814814814814815`. Shifting all elevations by -10 m changed only the levels from `[9.0, 4.5]` to `[-1.0, -5.5]`. The owner then raised `INVALID_STORY_VALUE:level_m`.

The same experiment through the actual product adapter reused `tests/test_r08_story_second_order.py::fixture`. Its base datum was changed from 0 to -10 m and the source was sealed using the existing helper. The unshifted product returned `NUMERIC_PRECHECK_UNAPPROVED`, four expected and four evaluated story-direction instances. The translated product returned `BLOCKED_SOURCE_INVALID`, **zero expected and zero evaluated**, although the known physical two-story/two-direction population remained unchanged.

This is both a coordinate-origin defect and a local denominator-loss defect. It is not evidence that the reported C29 PMM or deformation values are wrong. It can block a valid negative-datum or basement model and makes a known population vanish from this stage's summary.

**Correction experiment:** introduce a finite signed-coordinate validator for absolute elevations while preserving positive heights/weights/shears and nonnegative drift magnitudes. Freeze the expected story-direction census as soon as valid geometry is established, before subsequent numerical/source checks. Repeat translations across zero, negative base levels and deliberate nonfinite coordinates. The theta values should remain invariant under a uniform coordinate translation; true invalid data should retain four expected unresolved instances, not zero.

Evidence: `src/tbdy_next/engineering/story_pdelta.py::finite`, `review_story_pdelta`; `src/tbdy_next/story_second_order.py::bind_story_second_order`; [ENGINEERING_PROBES.json](audit_20261121/ENGINEERING_PROBES.json) keys `global_theta_vertical_origin` and `global_theta_product_adapter`.

## Reproduced finding ENG-02 — a demonstrated equilibrium failure is not propagated to conditional frame consumption

**Priority P1; GAP-009.**

`engineering/gravity_story_basis.py::_force_results` records a failed signed upper-body equilibrium in the full case's reasons. The nested `frame_column_compression` branch derives its reasons only from column row issues, not from a demonstrated complete upper-body imbalance. `produce_story_basis` therefore still creates nonempty conditional frame `story_inputs`. `gravity_pair_refinement.py::compare_level` explicitly selects those conditional inputs when the full story basis is not calculated.

The probe reused the existing one-column `_example` in `tests/test_gravity_story_basis.py`, attached the existing conditional-frame input contract and same-generation modifier census, then called the production `produce_story_basis` twice. No successful result dictionary or capacity was injected.

| Quantity | Balanced input | Independent load increased by 100 kN |
| --- | ---: | ---: |
| Native signed column cut force | 950 kN | 950 kN |
| Independent external load plus self weight | 950 kN | 1,050 kN |
| Signed balance residual | 0 kN | -100 kN |
| Full case | `STORY_COMPRESSION_BOUND` | `STORY_COMPRESSION_INCOMPLETE` |
| Full failure reason | none | `STORY_FREE_BODY_VERTICAL_IMBALANCE` |
| Conditional child | `REVISED_CONDITIONAL_FRAME_BASIS_CALCULATED` | `REVISED_CONDITIONAL_FRAME_BASIS_CALCULATED` |
| Conditional M2/M3 story inputs | available | still available |

The conditional output retains `Nd=950 kN`, `Nk=33,926.76512874467 kN` and `k=2` in both directions. The full failure remains visible in the nested record, so this is not a claim that the error is literally deleted or that engineering release becomes READY. The defect is that failed evidence remains eligible for downstream conditional factor/PMM consumption without failure propagation.

**Correction experiment:** distinguish absent full-wall data from a proved contradiction in a complete, independently bound balance. Missing wall evidence can retain the explicitly adopted frame-only numerical scenario. A demonstrated full-body imbalance must propagate a terminal ineligibility/failure reason to the factor consumer, while retaining diagnostic numbers. Add paired cases: missing wall evidence does not silently invalidate the documented conditional scope; complete but inconsistent equilibrium cannot be consumed as merely available conditional inputs. Rerun the native archived C29 only after the fix to determine whether it exercises the defect. This audit did not establish that C29 had a known imbalance.

Evidence: `src/tbdy_next/engineering/gravity_story_basis.py::_force_results`, `produce_story_basis`; `src/tbdy_next/engineering/gravity_pair_refinement.py::compare_level`; [ENGINEERING_PROBES.json](audit_20261121/ENGINEERING_PROBES.json) key `conditional_known_imbalance`. The script executes the producer; downstream fallback consumption is established by code inspection, not a new whole-pipeline run.

## Additional qualification concern — end-restraint numbers are not all independently source-bound

This is a source-review concern, not a third reproduced numerical defect. In `gravity_story_basis.py::_end_restraint`, the `TS500_FRAME_JOINT_RATIO` branch independently checks neighbor membership/axes, uniqueness, the presence of all neighbors, and the target member's EI. It accepts other members' `ei_nmm2` and all `length_mm` terms as positive numerical inputs. It does not compare these values against the provided native end-reference terms; `end_references` is consulted for the explicit mat/wall support alternatives. The resulting restraint basis is labeled `ADOPTED_MODEL_BOUND_END_RESTRAINTS`.

Before a full-system critical-load basis is accepted, each EI/L term needs either same-generation source binding (material, section, modifiers, relevant length and axis) or an explicit adopted-assumption classification. Positivity and membership alone cannot establish stiffness correctness. The source can legitimately carry an engineering idealization, but its acceptance must not be inferred from a model SHA and neighbor IDs. Preserve the completed C29 conditional calculation while auditing the exact native terms separately.

## Existing work that must not be redone or reflagged as missing

1. **C29 computation is completed within its conditional frame scope.** `EV-C29-NATIVE-CONDITIONAL-TS500-20261121` records all 18 native 2/4/8 cases, 12 revised TS 500 factors, 24 revised PMM sides at 18 physical case-cuts, and recovered full-span fields. Six 4-to-8 comparisons meet 0.01 mm; the largest recorded bound is 0.0004012824 mm. The original 2/87 conditional R14 result, eight connected beams and joint 40 remain. FULL_SPAN_RECOVERED is not a pending task.
2. **Native Frame/Shell name filtering and non-paired-column modifier admission are implemented.** `bind_pmm_mesh_source` and the revised story producer filter Frame namespaces; the dedicated modifier schema admits the complete non-paired column census without corrupting the paired mesh contract. Do not demand another synthetic fixture as a substitute for the already completed real C29 computation.
3. **Latest standalone length census is 73, not 59.** `EV-GAP006-WALL-MESH-AND-CUTS-20261121` records 73 proven free lengths, 14 new relative to the older checkpoint, and 14 wall-coupled columns. It predicts 402 cuts and matches 957 member/case inventories and 7,638 native rows. The captured scope still has its documented MinStations=3/zero-I-offset restriction.
4. **The old all-87 capacity-shear numerical screen is not the latest accepted coupled scope.** The later `EV-R10-WALL-COUPLED-CAPACITY-SPAN-20261121` deliberately withholds capacity shear for the 14 coupled members and leaves 73 other R10 records unchanged. Retain the 1,392 historical assigned comparisons but do not describe them as current full-building closure. This guard is a correction, not a regression to be bypassed.
5. **C104 mesh equilibrium is implemented; local convergence is still not established.** The 25 mm mesh binds 206 frame segments and 672 signed joint balances, with tiny force/moment residuals. Yet local force changes remain material: one reported V2 changes from -256.192974 kN at 50 mm to -276.312894 kN at 25 mm, and the maximum partial-section moment change is 151.319704 kN·m. Similar frequencies or base reactions do not resolve local section demands. The gross union changes at elevation -1.50 m; construction reinforcement/continuity remains missing.
6. **Nested Linear Add already exists.** `mixed_demands.linear_coefficients` recursively expands typed combinations with exact `Fraction` coefficients, removes zero cancellations and rejects cycles/depth, operator or reference conflicts. `test_nested_static_repeated_coefficients_cancel` covers it. GAP-007 should distinguish real-scope acceptance and unsupported operators from missing recursion.
7. **The original selected scenario legitimately requires zero alpha iteration.** Recorded 47 low-axial exempt and five interval-qualified non-exempt joints resolve its applicability. A unit factor or `ALTERNATIVE_NOT_REQUIRED` is not failure. The missing experiment is a separate complete example that genuinely produces alpha below one through actual capacities.
8. **Axial cap, minimum eccentricity, axis conversion and reinforcement-role guards exist.** Current `ts500_column`, `column_gates`, PMM adapters and `test_p0_handoff_f01_f13.py` distinguish code axial limits from the section surface, floor moments, convert native axes once, and do not make a 12Phi20 template into an approved selected cage. `test_structural_demand_floors.py` proves floors precede magnification and initial/revised Ve retains native Vd witnesses. Historical findings must be evaluated against these owners rather than copied as current P0s.
9. **PMM uses a moment-direction root.** `section_capacity._direction_root` solves axial equilibrium at each angular step. The old concern that the selected capacity is merely an interpolated polygon point is not current. Its honest limits remain two-axis-symmetric rectangular sections and an observed angular error criterion; independent complete-design acceptance is still needed.
10. **Failure priority and sealed report projection have real coverage.** Existing tests preserve known native brittle/joint failures beside missing cases or an exhausted cage; finalized reports project sealed results and the recorded 16-stage replay is identical. Do not generalize those narrow fixes into complete catalog-wide execution or acceptance.

## Why collection and tests alone cannot finish these gaps

A native row can establish a force value and its source identity. It cannot select the physical coupled wall section, identify actual reinforcement continuity, decide creep/stiffness applicability, prove response-spectrum components simultaneous, or approve an Eq.7.29 branch. Likewise, a formula reproduced from a printed report establishes that the report used that arithmetic; it does not establish the report's full source population or normative correctness.

The remaining work must be separated into executable experiments:

- **Data acquisition:** only missing same-state wall boundary forces, original precise modal/torsion inputs and missing native geometry/definition facts. Reuse solved sources first.
- **Physical/model decisions:** wall-column composite versus interacting behavior, base/end restraints, actual reinforcement, anchorage and beam N=0 applicability. Most of these require drawings and engineering decisions, not additional COM getters.
- **Algorithm implementation:** coupled-system critical load/second-order demands, actual-owner nontrivial alpha feedback validation, full wall design, general check-instance ledger and catalog execution.
- **Independent acceptance:** complete PMM/shear/joint/wall examples, frozen tolerances and source-qualified code rule interpretations. Report imitation is not the acceptance oracle.


## Delivery and reproduction

Use the [canonical roadmap](ROADMAP_20261121.md) for sprint ownership and the [18 GAP exit recipes](GAP_EXIT_RECIPES_20261121.md) for exact inputs, owners, oracles and acceptance. The [audit bundle](audit_20261121/README.md) contains portable commands and production-source hashes. These are bounded diagnostics using existing repository fixtures, not new C29 fixtures or building acceptance evidence.

For ENG-02 / YSA-02, a demonstrated imbalance means that physical contributor coverage, exact-state identities and an independent external-load basis are complete and qualified. Missing wall contributors alone cannot establish that contradiction. The correction must retain the existing conditional frame scope when only full-system evidence is unavailable.

The supervisor report names ENG-01 as YSA-01 and ENG-02 as YSA-02. The separate architecture receipt finding is YSA-03. No production calculation was corrected by this documentation milestone.
