# Exit recipes for the 18 registered engineering GAPs

Inspected baseline: `c71a4dda4ab9453f428a38b3ed79931f8e6eeea3`. Registered status remains **3 OPEN / 15 PARTIAL / 0 CLOSED**. These are executable work recipes, not completed experiments. Dependencies express required artifacts or method qualification, not a rule to wait until an entire upstream GAP is globally closed. Canonical scheduling is in [ROADMAP_20261121.md](ROADMAP_20261121.md); machine-readable inputs/owners/oracles are in [GAP_EXIT_RECIPES.json](audit_20261121/GAP_EXIT_RECIPES.json).



The machine-readable companion is `gap_recipes.json`. Every recipe below identifies the existing owner, remaining source/method, independent oracle, acceptance and environment split. These are proposed work, not completed gap closure.

### GAP-001 — Approved model profile

Registered: **OPEN / P0**.

**Existing verified scope:** Candidate model contracts and an exact-source adopted model profile exist; conditional computation is possible without normative approval.

**Remaining work:** A complete qualified project model profile and an accepted applicability/approval route are missing. The current adopted profile explicitly requires engineering_approval=NOT_GRANTED; adding an approval-shaped string is not an implementation of acceptance.

**Closure experiment:** Reconcile one complete C29 project profile against original geometry, code applicability and recorded model configuration. Emit a field-by-field qualified or unresolved result and consume it through R03 and the normal runner. Challenge one wrong story role and one wrong system parameter.

**Independent oracle:** Independent engineer worksheet and primary standard clauses, tied to the same native census; no inference from case names or reference report appearance.

**Owners:**

- candidate_model_contracts.py::review_model_profile_candidate
- engineering/analysis_setup.py::normalize_analysis_basis
- engineering/analysis_setup.py::_adopt_calculation_basis

**Required inputs:**

- Standard edition and amendments
- Structural system and ductility by direction
- BKS/DTS/BYS and R/D/I/Ch where applicable
- Physical story and basement roles
- Source-bound model, materials, seismic mass and stiffness policy

**Acceptance:**

- Every required profile field has provenance and a declared responsible decision
- Contradictory native/profile data rejects affected checks
- Conditional assumptions remain distinguishable from approved model facts
- Do not globally clear NOT_READY solely by attaching an approval document

**Dependencies:** No upstream engineering GAP; source/support boundary still applies.

**Offline:** Build applicability schema, exact field/source comparisons and owner consumption offline.

**Windows / physical source:** Read only missing native profile facts; engineering decisions/construction records are not ETABS getters.

**Tests inspected:** `test_vs05_candidate_model_contracts.py`, `test_adopted_analysis_basis.py`, `test_r03_analysis_setup.py`

**Ledger evidence:** `EV-VERTICAL-SLICE-ADOPTED-BASIS-20261121`, `EV-C29-R03-ORDER-AXIAL-BALANCE-20261121`


### GAP-002 — Combination book and design family scope

Registered: **PARTIAL / P0**.

**Existing verified scope:** Native combination definitions, configured design groups and exact assigned role scope are available; mixed signed and scalar spectral routes exist.

**Remaining work:** The required design-family roster is not independently derived from applicable code/system choices. Defined or selected ETABS combinations alone cannot prove completeness.

**Closure experiment:** Freeze the required combination book independently, compare every required expression against the native typed AST, and preserve missing families in the expected denominator. On C29 distinguish the recorded 3 static + 8 assigned seismic combinations from the project-wide required book.

**Independent oracle:** Independent symbolic coefficient table and primary standard expression review; arithmetic checked with rational/Decimal coefficients.

**Owners:**

- engineering/design_assignments.py::design_assignments
- engineering/design_assignments.py::project_role_catalog
- engineering/analysis_setup.py::_adopt_calculation_basis
- engineering/mixed_demands.py::native_graph

**Required inputs:**

- Qualified project profile
- All native case/pattern/combination ASTs and GUIDs
- Independent required family/direction/sign roster
- Gravity/live-load participation, vertical earthquake and overstrength policies

**Acceptance:**

- Required versus available family sets reconcile explicitly
- Every coefficient/operator/role is verified once
- Nested nonconcurrent operators cannot be treated as signed vectors
- An unassigned but required family remains a failure or unresolved obligation

**Dependencies:** GAP-001

**Offline:** Compile and compare expressions, roles and expected scopes offline.

**Windows / physical source:** Acquire only absent definitions/selected native groups with selection restoration.

**Tests inspected:** `test_mixed_design_demands.py`, `test_r03_analysis_setup.py`, `test_adopted_analysis_basis.py`

**Ledger evidence:** `EV-D3B`, `EV-COLUMN-JOINT-SLICE-20261119`


### GAP-003 — Model and analysis generation

Registered: **OPEN / P0**.

**Existing verified scope:** Immutable source/result hashes, native case identities and archived C29 solver/order reconciliation exist. Native first-order assumptions reject explicit contradictory predecessors.

**Remaining work:** A hash or locked model is not independent proof that results were solved from the exact consumed model contents. General analysis-generation qualification remains missing.

**Closure experiment:** On an isolated controlled model, bind analysis start/completion evidence to a semantic model digest and consumed result inventory. Change a section or load after solution and demonstrate rejection of stale results; do not use model-lock state as the oracle.

**Independent oracle:** Independent before/after semantic export plus solver lifecycle/log evidence and known deliberate stale-model challenge.

**Owners:**

- engineering/analysis_setup.py::audit_model_analysis_setup
- engineering/analysis_setup.py::_adopt_calculation_basis
- engineering/design_scenario.py::verify_parent
- engineering/analysis_archive.py::reconcile_archived_order

**Required inputs:**

- Analysis log and completed case inventory
- Model content identity before/after analysis
- Consumed-result generation identity
- Relevant stiffness, support, loads, mass and solver settings

**Acceptance:**

- Every consumed case belongs to the proven generation
- Any relevant post-analysis model mutation invalidates downstream results
- Output-selection changes remain acquisition transactions, not new structural generations
- Analysis order is independently established, not inferred from NonlinCase=None

**Dependencies:** GAP-001

**Offline:** Specify generation proof, reconcile archived evidence, implement rejection and lineage checks.

**Windows / physical source:** A lifecycle/staleness experiment needs a controlled Windows ETABS copy; no Linux COM claim.

**Tests inspected:** `test_adopted_analysis_basis.py`, `test_r03_analysis_setup.py`, `test_offline_design_scenario.py`

**Ledger evidence:** `EV-C29-R03-ORDER-AXIAL-BALANCE-20261121`, `EV-D3B-REPLAY`


### GAP-004 — Native schema, units and selection transactions

Registered: **PARTIAL / P1**.

**Existing verified scope:** Existing gateway and transactional capture restore output/pattern/mode selections; native modal getters and exact companion identities are implemented and observed on the recorded ETABS installation.

**Remaining work:** The supported-version/schema matrix is not yet a declared and fully accepted product boundary. Unsupported versions, null returns and precision sources must be explicit.

**Closure experiment:** Declare the supported ETABS build(s) and getter/table contracts, then replay one real raw packet per supported schema. On Windows induce a recoverable getter failure and verify every temporary selection is restored. Preserve user-authorized units 6.

**Independent oracle:** Native type-library/API contract and independent before/after getter inventory; malformed raw packets test rejection.

**Owners:**

- etabs_source_gateway_windows.py
- frame_force_capture.py
- basis_probe.py
- engineering/demand_sources.py::native_modal_precision

**Required inputs:**

- Actual ETABS version/type library
- Exact table fields, units, API signatures and raw return codes
- Session selections before/after capture
- Native double versus printed precision metadata

**Acceptance:**

- Unsupported signature/version fails with a precise reason
- All restored selections match their captured original values
- Any restoration failure prevents accepted capture
- Do not restore old tonf units contrary to authorized kN/m/C policy

**Dependencies:** No upstream engineering GAP; source/support boundary still applies.

**Offline:** Replay real raw packets and typed error/ambiguity contracts; build support matrix.

**Windows / physical source:** Capture missing schema versions and selection restoration behavior through existing gateway.

**Tests inspected:** `test_etabs_source_gateway.py`, `test_native_demand_sources.py`, `test_capture_modal_etabs23.py`

**Ledger evidence:** `EV-LIVE-MODAL-IDENTITY`, `EV-LIVE-MODAL-NUMERIC-ORACLE`, `EV-LIVE-MODAL-REPLAY-REPORT`


### GAP-005 — Complete expected check population

Registered: **PARTIAL / P0**.

**Existing verified scope:** Column/member/case/cut scopes are explicit in PMM and many dependent paths; 87 members / 957 assigned pairs and independently predicted cuts are recorded.

**Remaining work:** A general expected-check-instance ledger across all rule families is absent. One reproduced source-error path drops a known 4-instance global second-order population to 0 expected.

**Closure experiment:** Freeze each rule population before numerical evaluation; first repair the reproduced global-second-order 4-to-0 loss. Then produce a check/member/story/case/direction/cut ledger and deliberately remove one required cut, story, beam and case. Each remains in the denominator.

**Independent oracle:** Independent topology/case enumeration from native geometry and reviewed applicability, not the successful result rows.

**Owners:**

- engineering/pipeline.py::STAGES
- engineering/pipeline.py::run_source_pipeline
- engineering/design_scenario.py::design_dependency_ledger
- compiled_dag.py::RegulatoryCompiler
- story_second_order.py::bind_story_second_order

**Required inputs:**

- Qualified physical members/stories/joints
- Rule applicability and demand family definitions
- Independent physical cut and element-side census

**Acceptance:**

- Expected = evaluated + unresolved + proven-not-applicable, with explicit failures retained
- Source failures cannot erase known expected instances
- Duplicate identifiers or sides cannot increase coverage
- Catalog nodes, test counts and engineering instances remain separate

**Dependencies:** GAP-001, GAP-002, GAP-006

**Offline:** Implement and verify population producers and denominator invariance offline.

**Windows / physical source:** Only missing topology/assignment facts require acquisition.

**Tests inspected:** `test_design_member_dependencies.py`, `test_r08_story_second_order.py`, `test_vs05_compiled_dag.py`, `test_vs08_wall_geometry.py`

**Ledger evidence:** `EV-GAP006-WALL-MESH-AND-CUTS-20261121`, `EV-AUDIT-FIXES-20261120`

**Scope correction:** A declared catalog with 94 nodes or 242 recipe items is not 94/242 completed calculations.


### GAP-006 — Same-cut mesh, offsets and physical faces

Registered: **PARTIAL / P0**.

**Existing verified scope:** The original MinStations=3/zero-I-offset census binds 402 cuts, 957 member-case inventories and 7,638 native rows. Latest recorded physical free lengths cover 73 standalone columns; 14 columns are wall coupled.

**Remaining work:** C104/W21/W22 reinforcement continuity, the two physical section geometries and mesh-insensitive coupled demand are not qualified. Geometric contact alone is not a verified analysis constraint or composite capacity.

**Closure experiment:** Adopt and document each physical composite section at the two geometries, integrate signed section resultants without overlapping area/force credit, and compare successive meshes at identical cuts and states. Use actual reinforcement continuity to decide composite versus interacting members before capacity.

**Independent oracle:** Independent polygon union area/centroid/inertia and manual FBD equilibrium; a distinct section analysis for the chosen physical section; convergence on resultants as well as displacements.

**Owners:**

- engineering/column_clear_length.py::project_column_clear_lengths
- engineering/column_pmm.py::bind_configured_output_cuts
- engineering/column_r08_local_live.py
- engineering/column_r10_live.py::_column_capacity_shear_ve

**Required inputs:**

- C104/W21/W22 construction reinforcement and connection details
- Native shell/frame connectivity and constraints
- Upper/lower cut faces at the -1.50 m transition
- Signed same-state component forces and moments about one origin

**Acceptance:**

- One-to-one physical/analysis cut mapping and complete component census
- No double credit for overlapping concrete or force representations
- Predeclared local-demand/refinement tolerances met at all required cuts
- 14 coupled members never regain an isolated-column clear-span fallback

**Dependencies:** GAP-003, GAP-004

**Offline:** Integrate archived cuts and geometry; build qualified composite source contract within existing owner.

**Windows / physical source:** Missing construction details come from drawings; targeted mesh/coupled-model experiments need Windows copies.

**Tests inspected:** `test_column_clear_length.py`, `test_gravity_story_basis.py`, `test_r14_adopted_basis.py`

**Ledger evidence:** `EV-GAP006-WALL-MESH-AND-CUTS-20261121`, `EV-GAP006-C104-REFINEMENT-20261121`, `EV-GAP006-C104-SECTION-PROFILE-20261121`, `EV-R10-WALL-COUPLED-CAPACITY-SPAN-20261121`

**Scope correction:** 59 proven lengths is historical; latest census records 73. Small global frequency/base-reaction changes do not establish local C104 mesh convergence.


### GAP-007 — Exact static Linear Add

Registered: **PARTIAL / P0**.

**Existing verified scope:** Exact signed Linear Add uses recursive nested expansion and Fraction coefficients; repeated leaf contributions cancel correctly. Recorded original static reconstruction has 1,206 tuples / 7,236 scalar controls.

**Remaining work:** Project-wide nested real-definition qualification, operator-specific consumption and approved family coverage remain. Nonlinear/envelope operators must retain their own semantics rather than be coerced into sums.

**Closure experiment:** Select an actual nested combination from the frozen book; independently flatten it and compare all six components at every expected cut. Exercise repeated coefficients, zero cancellation, cycle/depth rejection and Envelope under Linear Add.

**Independent oracle:** Independent rational expression expansion and native direct-result comparison on the same generation; no nearest-cut matching.

**Owners:**

- engineering/mixed_demands.py::linear_coefficients
- engineering/mixed_demands.py::represent_linear_effect
- engineering/mixed_demands.py::earthquake_row
- engineering/demand_sources.py::component_force_rows

**Required inputs:**

- Full native typed AST
- Primitive same-cut signed rowsets
- Exact case/step/side identities
- Qualified design family roster

**Acceptance:**

- Coefficient identities exact
- Native scalar comparison uses frozen existing tolerance, not widened to fit
- Missing primitive or opposite interface side remains unresolved
- Nonconcurrent nested operators remain rejected by signed consumers

**Dependencies:** GAP-002, GAP-003, GAP-006

**Offline:** Nested algebra and archived replay are offline; do not rewrite existing recursion.

**Windows / physical source:** Acquire only missing primitive rows through existing acquisition route.

**Tests inspected:** `test_mixed_design_demands.py::test_nested_static_repeated_coefficients_cancel`, `test_mixed_design_demands.py::test_envelope_operator_not_accepted_as_linear_sum`, `test_same_source_spectral_replay.py`

**Ledger evidence:** `EV-COLUMN-JOINT-SLICE-20261119`, `EV-LOCAL-ORACLE`

**Scope correction:** The current GAP text is too broad if read as claiming nested Linear Add is unimplemented; it already exists.


### GAP-008 — Design demand in the same generation

Registered: **PARTIAL / P0**.

**Existing verified scope:** Scenario parents, source digests, selected candidate revisions and exact case/cut/side/step identities are retained; changed requests create new scenario identities.

**Remaining work:** Generation proof and applicable seismic vector policy are not established by lineage alone. A coherent hash chain can still faithfully reference an unqualified structural assumption.

**Closure experiment:** Choose one signed C29 demand and one assigned seismic demand. Trace source through scenario, R08, PMM, Ve, joint and R14; change one upstream item and verify every dependent result is invalidated while unrelated members retain identity.

**Independent oracle:** Independent tuple/identity manifest and byte-level source preservation checks; numerical oracle belongs to the relevant demand/capacity owner.

**Owners:**

- engineering/design_scenario.py::create_design_scenario
- engineering/design_scenario.py::verify_parent
- engineering/design_scenario.py::prepare_pipeline_source
- engineering/design_dependencies.py
- engineering/mixed_demands.py

**Required inputs:**

- Qualified generation and combination policy
- Immutable source parent
- Demand/cage/method revision identities
- Complete cut and neighbor dependency graph

**Acceptance:**

- No cross-generation/cut/step joins
- Web, CLI and report show the same sealed result identity
- Mutating source/cage/method produces a new dependent identity
- Engineering scope is not inferred from matching names

**Dependencies:** GAP-002, GAP-003, GAP-005, GAP-006

**Offline:** Trace and challenge immutable dependencies and artifact lineage offline.

**Windows / physical source:** No new analysis for already qualified archived source; native missing facts only.

**Tests inspected:** `test_offline_design_scenario.py`, `test_design_member_dependencies.py`, `test_pipeline_unification.py`

**Ledger evidence:** `EV-D1`, `EV-D3B-REPLAY`, `EV-LOCAL-SPECTRAL`


### GAP-009 — Global and local second-order effects

Registered: **PARTIAL / P0**.

**Existing verified scope:** C29 native 2/4/8 comparison completed 18 cases, 12 adopted factors, 24 revised PMM sides at 18 physical case-cuts, with FULL_SPAN_RECOVERED and six passing 4-to-8 bounds. Full wall scope is explicitly separate.

**Remaining work:** Full signed column-wall upper-body equilibrium, supported two-axis wall-frame critical-load/second-order method, 14 coupled columns, stiffness/creep acceptance and varying-axial applicability remain. Confirmed code defects affect known-imbalance fallback and negative global elevations.

**Closure experiment:** First fix the two reproduced contract defects. On solved 8-part C29G_U_F, assemble 53/36 physical contributors and independent upper-body balance at the two cuts; extend to TN_F/TP_F. Then qualify a coupled wall-frame stability method using explicit boundary conditions and one consistent load pattern, and consume revised demands in normal R08/R14. Preserve conditional frame output separately.

**Independent oracle:** Independent signed FBD integration and applied-load audit; independent analytical/member and coupled-system stability benchmarks; native direct second-order comparison at identical cuts and consistent EI. Coordinate translation must leave theta unchanged.

**Owners:**

- engineering/gravity_story_basis.py::produce_story_basis
- engineering/gravity_pair_refinement.py::compare_level
- engineering/column_r08_local_live.py
- engineering/story_pdelta.py::review_story_pdelta
- story_second_order.py::bind_story_second_order
- column_engine/ts500_column.py

**Required inputs:**

- Concurrent upper-side wall resultants for 21/4 wall objects
- 32 column forces per story on the same generation/case/cut
- Independent upper external loads and self weight
- Revised stiffness, restraints, coupling, creep and load pattern
- Selected cage and physical variable-axial method scope

**Acceptance:**

- Current FBD gate: abs_tol 0.01 kN, rel_tol 1e-6, with explicit signs and full expected scope
- Known demonstrated imbalance cannot be silently consumed by conditional fallback
- Wall method has a justified per-axis/system basis; no arbitrary isolated-wall Euler sum
- Original six deformation error budgets and 12/24 conditional numbers remain traceable
- Full demands, same selected cage and 18/24 comparison propagate to sealed report

**Dependencies:** GAP-001, GAP-002, GAP-003, GAP-006

**Offline:** Repair source gates; integrate recorded force rows; implement/verify accepted method in current owners.

**Windows / physical source:** Only exact-state wall forces or controlled coupled/stability experiments absent from existing captures need Windows; PID must be rediscovered.

**Tests inspected:** `test_gravity_story_basis.py`, `test_gravity_deformation.py`, `test_variable_axial_vertical_slice.py`, `test_adopted_second_order_basis.py`, `test_engine_r08_story.py`, `test_r08_story_second_order.py`

**Ledger evidence:** `EV-C29-NATIVE-CONDITIONAL-TS500-20261121`, `EV-C29-SELF-WEIGHT-NMAX-LOCAL-20261121`, `EV-GAP009-ASSIGNED-SPECTRAL-SWAY-20261121`

**Scope correction:** A balanced wall resultant does not implement wall critical load. Zero wall Nk with omitted wall Nd is an adopted frame-only scope, not a proved conservative full-system bound.


### GAP-010 — Independent PMM capacity acceptance

Registered: **PARTIAL / P0**.

**Existing verified scope:** Rectangular two-axis-symmetric PMM uses strain compatibility, exact displaced bar-disk concrete subtraction, axial equilibrium roots and a moment-direction root. Required static cuts and selected cages are consumed.

**Remaining work:** Independent full-design capacity acceptance is missing; asymmetric/nonrectangular composite wall sections lie outside this kernel. Angular stability is observed, not a proof of a continuous global error bound.

**Closure experiment:** Recover one complete actual report PMM case with bars, material strengths and concurrent N/M2/M3; solve fixed-N capacity on the same moment ray by an independent implementation. Include rectangular unequal axes, rotated demand, tension/compression endpoints and near-boundary cases.

**Independent oracle:** Independent strain integration/root solution or independently documented section program; hand uniaxial limits plus equilibrium residuals. It must not call the production solver.

**Owners:**

- column_engine/section_capacity.py::Section
- column_engine/section_capacity.py::_Curve
- column_engine/section_capacity.py::_direction_root
- column_engine/section_capacity.py::RadialSolver.assess
- engineering/column_pmm.py::_station_result

**Required inputs:**

- Exact section/material and bar coordinates
- Compression-positive N and CSI local M2/M3
- Same-cut source and minimum eccentricity
- Separate axial code caps and physical cage role

**Acceptance:**

- Force residual and moment-direction residual satisfy the existing owner budgets
- Capacity and utilization match the frozen independent tolerance
- Near-surface decisions remain unresolved within numerical guard
- Axial code cap failures override small PMM utilization
- Unsupported asymmetric/composite sections do not masquerade as accepted rectangles

**Dependencies:** GAP-006, GAP-008, GAP-009, GAP-011

**Offline:** Independent section calculation and actual-report binding are offline.

**Windows / physical source:** No ETABS needed for capacity once bar/source geometry is known; demand capture only if missing.

**Tests inspected:** `test_vs25_pmm_direction_root.py`, `test_vs25_pmm_root_integration.py`, `test_vs21_section_reference.py`, `test_structural_demand_floors.py`

**Ledger evidence:** `EV-PMM6`, `EV-COLUMN-JOINT-SLICE-20261119`, `EV-C29-NATIVE-CONDITIONAL-TS500-20261121`


### GAP-011 — Reinforcement selection and detailing

Registered: **PARTIAL / P0**.

**Existing verified scope:** Candidate selection enforces the 1% minimum longitudinal ratio, coordinates, spacing and selected tie checks. 32Phi16 / Phi10/90 are recorded algorithm-selected scenarios, not automatically as-built.

**Remaining work:** Complete effective crosstie topology, bend/hooks, anchorage/laps, congestion and engineer/as-built role acceptance remain. Restricted cage-family exhaustion is not proof no constructible design exists.

**Closure experiment:** Take the selected C29 cage into one buildable end-region and joint detail; enumerate every effective leg and longitudinal-bar restraint, compute confinement/shear both axes, and check lengths/hooks/congestion. Feed qualified details through current R14 rather than simply changing its role label.

**Independent oracle:** Independent drawing-based bar/leg geometry takeoff and clause-by-clause calculations using actual detail dimensions.

**Owners:**

- engineering/rebar_selection.py::select_column_rebar
- engineering/rebar_selection.py::_evaluate_column_transverse_choice
- column_engine/transverse_kernel.py
- engineering/column_r14_closure.py

**Required inputs:**

- Physical bar/hoop/crosstie coordinates and effective directions
- Cover and clear spacing
- Axial branch across required combinations
- Anchorage, lap, hook and support details
- Explicit candidate versus approved/as-built role

**Acceptance:**

- As >= 0.01Ac without deficit tolerance
- Every credited effective leg is geometrically and mechanically supported
- Pitch, cover, bar spacing, confinement length and anchorage criteria all pass
- Candidate/approved/as-built distinction survives UI and report
- A failed tie-spacing result remains a failure despite PMM pass

**Dependencies:** GAP-001, GAP-008

**Offline:** Geometry enumeration, candidate constraints and independent arithmetic offline.

**Windows / physical source:** Construction drawing/detail evidence, not extra ETABS analysis, is usually the missing source.

**Tests inspected:** `test_rebar_selection.py`, `test_p0_handoff_f01_f13.py`, `test_r14_adopted_basis.py`

**Ledger evidence:** `EV-COLUMN-CAGE-TIE10`, `EV-COLUMN-CAGE-REPORT-TESTS`


### GAP-012 — Beam capacity and end topology

Registered: **PARTIAL / P0**.

**Existing verified scope:** 180 beam candidate scenarios and signed N=0 end capacities are recorded; selected multi-row bars are available through the existing beam owner.

**Remaining work:** Physical end faces, constructible signed top/bottom reinforcement, continuity/anchorage and the applicability of beam N=0 remain qualified assumptions, not a complete beam design.

**Closure experiment:** Close one C29 interior/roof joint with all its incident beam end/sign capacities from actual selected bars; independently reconstruct positive/negative resistance and beam Ve at the physical clear length. Keep all eight distinct connected beams in C29 scope.

**Independent oracle:** Independent section equilibrium at N=0, then sensitivity/qualification if actual beam axial force is relevant; construction detail review for continuity.

**Owners:**

- engineering/beam_r10_live.py::_evaluate_beam_end
- engineering/beam_r10_live.py::_beam_shear_ve
- column_engine/beam_capacity.py::build_selected_beam_cage
- column_engine/beam_capacity.py::signed_beam_capacity

**Required inputs:**

- Every incident beam I/J physical face and local orientation
- Selected top/bottom row coordinates and development length
- Same-source design demands
- Axial force policy and release/offset details

**Acceptance:**

- Every required I/J sign has a capacity and complete bar coordinates
- Native axes and physical faces map exactly
- No source beam is dropped because its cage cannot be built
- Beam shear includes gravity term and applicable lower/brittle bounds
- N=0 remains explicit until accepted for the scenario

**Dependencies:** GAP-006, GAP-008, GAP-011

**Offline:** End-capacity, sign and detail checks on archived source.

**Windows / physical source:** Only absent end geometry/releases/native forces require capture; anchorage requires drawings.

**Tests inspected:** `test_beam_r10_live.py`, `test_vs23_beam_capacity.py`, `test_vs23_beam_references.py`

**Ledger evidence:** `EV-D1`, `EV-D2`, `EV-COLUMN-JOINT-SLICE-20261119`


### GAP-013 — SCWB and alpha demand feedback

Registered: **PARTIAL / P0**.

**Existing verified scope:** Original selected case has 47 qualified low-axial exempt joints and 5 non-exempt joints with 160 sufficient interval comparisons; its alpha alternative is not required. Bounded feedback and actual-owner candidate reselection exist.

**Remaining work:** No complete independent actual-owner example requiring alpha < 1 has demonstrated alpha -> revised demand -> reselected cage -> PMM/Ve/joint -> recomputed alpha and stable termination. Scalar 60/20/20 fixture is not that example.

**Closure experiment:** Choose an independent actual report/model whose calculated capacities genuinely give 0.70 <= alpha < 1. Run the existing owners without injecting success dictionaries; independently calculate numerator/denominator and factor, then demonstrate one changed design and all downstream rechecks. Separately exercise alpha < 0.70, oscillation and exhausted candidate family.

**Independent oracle:** Independent story force/moment equilibrium and a complete hand/spreadsheet design example with documented branch applicability; not manually supplied SCWB flags.

**Owners:**

- engineering/alpha_iteration.py::qualify_story_alpha
- engineering/alpha_iteration.py::run_bounded_feedback
- engineering/alpha_iteration.py::run_alpha_design_iteration
- engineering/scwb_axial.py
- column_engine/story_alpha.py
- engineering/design_dependencies.py

**Required inputs:**

- Complete physical story and both directional end populations
- Same-case earthquake shear components
- Actual selected beam/column capacities and low-N qualification
- Initial and revised demand/cage revisions

**Acceptance:**

- All required directional ends stay in the denominator
- Low-N numerator credit and eligibility for demand amplification remain separate
- Factor applies once to the qualified earthquake component at the same cuts
- Joint/panel/tie failures survive terminal-state precedence
- Convergence, design failure and nonconvergence are distinct reproducible outcomes

**Dependencies:** GAP-002, GAP-005, GAP-008, GAP-009, GAP-010, GAP-011, GAP-012, GAP-014

**Offline:** A complete archived independent example can drive this offline; no need to force the already passing original model to fail.

**Windows / physical source:** Windows needed only if an independently specified reference model lacks native analysis source.

**Tests inspected:** `test_alpha_design_iteration.py`, `test_alpha_low_axial_credit.py`, `test_alpha_joint_feasibility.py`, `test_vertical_slice_pipeline.py`, `test_scwb_axial_interval.py`

**Ledger evidence:** `EV-R10-LIVE-INTERVAL-20261120`, `EV-STORY-STATIC-APPLICABILITY-20261120`, `EV-VERTICAL-SLICE-ADOPTED-BASIS-20261121`

**Scope correction:** The original alpha=1 or ALTERNATIVE_NOT_REQUIRED result is not an algorithm failure; it cannot validate the nontrivial feedback branch.


### GAP-014 — Capacity shear, ties and joint panel

Registered: **PARTIAL / P0**.

**Existing verified scope:** Signed Vd floors, full end-moment capacity shear, zero-concrete comparisons, brittle limits and joint/tie reference branches exist. Earlier 1,392 assigned spectral checks remain recorded.

**Remaining work:** Current R10 intentionally withholds isolated capacity-shear spans for 14 wall-coupled columns. Full physical anchorage/enclosure and detailing remain; current 73-supported-column behavior must not be confused with earlier all-87 numerical screens.

**Closure experiment:** Complete one physical joint/column example independently through Ve, Vd floor, concrete/zero-concrete branch, brittle ceiling, tie sizing and joint panel. Then reconcile the expected 73 standalone versus 14 coupled population explicitly; supply coupled demand only after GAP-006/009 method qualification.

**Independent oracle:** Independent equilibrium and section/shear worksheet using actual end capacities and joint bar forces; retaining failed results beside missing siblings.

**Owners:**

- engineering/column_r10_live.py::_column_capacity_shear_ve
- engineering/column_r10_live.py::_attach_r13_joint_shear_and_transverse
- engineering/column_spectral_shear.py
- column_engine/joint_kernel.py
- column_engine/transverse_kernel.py
- engineering/column_r14_closure.py

**Required inputs:**

- Qualified physical spans and signed capacities both ends
- Native same-case Vd at all required cuts
- Effective transverse legs/material/spacing
- Joint enclosure, offsets and anchorage
- Compatible column shear deduction and axial branch evidence

**Acceptance:**

- Ve >= applicable Vd at the governing native witness
- Both axes/all cases and physical sides accounted
- A lower/upper bound that fails is not mislabeled as a proved physical demand failure unless justified
- Proven native brittle or joint failures cannot become only BLOCKED because a sibling is missing
- All accepted physical details are consumed in R14 and sealed report

**Dependencies:** GAP-006, GAP-008, GAP-009, GAP-010, GAP-011, GAP-012

**Offline:** Independent Ve/tie/panel calculations and source-bound adapter qualification.

**Windows / physical source:** Missing coupled demands or physical source facts need targeted capture; anchorage is drawing evidence.

**Tests inspected:** `test_structural_demand_floors.py`, `test_r13_joint_adapters.py`, `test_column_spectral_shear.py`, `test_spectral_shear_failure_propagation.py`, `test_alpha_joint_feasibility.py`

**Ledger evidence:** `EV-C29-SPECTRAL-SHEAR-20261120`, `EV-AUDIT-FIXES-20261120`, `EV-R10-WALL-COUPLED-CAPACITY-SPAN-20261121`


### GAP-015 — Wall/pier factor and wall design

Registered: **OPEN / P1**.

**Existing verified scope:** Wall rectangular geometry screening exists, including explicit unsupported special branches and missing-panel denominator preservation. It is not a full wall design engine.

**Remaining work:** Wall/pier/frame identity, overlapping area/force ownership, signed coupled demand, wall flexure/shear and complete boundary/web/coupling-beam detailing are not implemented as one accepted vertical slice.

**Closure experiment:** Select one real wall/pier from the report/model bank, establish a physical object independent of ETABS pier label, reconcile integrated section resultants and overlapping columns, then implement its first complete flexure/shear/detail result through the current runner. Start with the geometry family actually supported; do not claim every wall shape.

**Independent oracle:** Independent polygon/section equilibrium, reinforced wall capacity and clause review from a complete worked example; printed wall M22 transformations must first be identified.

**Owners:**

- wall_geometry.py::bind_wall_geometry
- engineering/column_clear_length.py
- engineering/gravity_story_basis.py
- engineering/pipeline.py

**Required inputs:**

- Physical wall/arm polygons and boundary elements
- Shell/pier membership with a nonoverlap ownership map
- Concurrent integrated resultants
- Actual wall reinforcement and connections
- Applicable wall-system parameters and detailing rules

**Acceptance:**

- No duplicated shell/pier/frame contributions
- Complete physical wall/arm population and force state
- All required failure modes/detail branches have results or explicit unsupported reasons
- Normal runner consumes wall results and report projects them
- No blanket engineering closure from wall aspect-ratio pass

**Dependencies:** GAP-001, GAP-002, GAP-003, GAP-005, GAP-006, GAP-008

**Offline:** Physical wall mapping, independent report reconstruction and existing-runner vertical-slice implementation.

**Windows / physical source:** Missing integrated native wall demands require targeted Windows capture; reinforcement/continuity requires drawings.

**Tests inspected:** `test_vs08_wall_geometry.py`, `test_column_clear_length.py`, `test_gravity_story_basis.py`

**Ledger evidence:** `EV-RECIPE18-INTAKE`, `EV-GAP006-C104-SECTION-PROFILE-20261121`, `EV-REPORT-SWAY-RECONSTRUCTION-20261121`


### GAP-016 — Golden coverage and complete independent example

Registered: **PARTIAL / P0**.

**Existing verified scope:** The fixed 44-ID comparison has 36 numerical matches, four interpretation differences and four insufficient-source records. Actual Drive report reconstruction and production phi scalar binding are completed in recorded scopes.

**Remaining work:** PMM, capacity shear, GOLDEN-03 and GOLDEN-04 need complete page/source-bound owner cases; four adopted-factor rows need a justified length/maximum-product policy. A complete actual-owner alpha-below-one design oracle is missing.

**Closure experiment:** Resolve one insufficient-source record at a time by a complete real report calculation through the production owner, keeping original IDs and expectations. For GOLDEN-02 compare all printed factors against both declared branches; identify the report convention before deciding normative implementation. Then run a full independent actual-owner design chain.

**Independent oracle:** Independent formulas/solver and source extraction with printed-resolution uncertainty; no oracle importing the production numerical function.

**Owners:**

- verification/golden_gate.py
- verification/report_oracles.py
- column_engine/ts500_column.py::sway_phi_reference
- column_engine/ts500_column.py::select_sway_magnification_factor

**Required inputs:**

- Original source hash/page/XML locator
- Complete governing inputs and intermediate calculations
- Bar geometry for PMM
- Both end capacities/clear span/D/Vd for capacity shear
- Unambiguous Eq.7.29 length and chosen-factor provenance

**Acceptance:**

- 44 comparison IDs and denominator preserved
- Expected values/tolerances not adjusted to force agreement
- Arithmetic agreement, source completeness and normative acceptance separately recorded
- All 36 product matches do not by themselves authorize the product rule
- Any remaining discrepancy is retained with its exact data and cause

**Dependencies:** GAP-007, GAP-009, GAP-010, GAP-012, GAP-013, GAP-014

**Offline:** All report extraction, arithmetic reconstruction and owner binding can be offline when originals are available.

**Windows / physical source:** No ETABS dependency for report-only or capacity references.

**Tests inspected:** `test_golden_scalar_adapters.py`, `test_vs26_golden_gate.py`, `test_vs25_pmm_direction_root.py`, `test_vertical_slice_pipeline.py`

**Ledger evidence:** `EV-REPORT-SWAY-RECONSTRUCTION-20261121`, `EV-GOLDEN01-OWNER-BINDINGS-20261119`, `EV-VERTICAL-SLICE-ADOPTED-BASIS-20261121`


### GAP-017 — One pipeline, dependency graph and sealed reports

Registered: **PARTIAL / P0**.

**Existing verified scope:** Web and CLI share EnginePipelineRunner; finalized v2 reports project sealed results; recorded 16-stage replay and zero-calculator report projection exist. Dependency contracts and method identities are present.

**Remaining work:** Catalog-wide topological execution and a general check-instance ledger are not complete. Existing STAGES and candidate regulatory graph are not interchangeable, and some legacy entry paths remain.

**Closure experiment:** Trace one complete column/joint chain, then migrate the next existing rule family to typed dependency execution without a parallel solver. Show missing upstream blocks, cycles reject, changed upstream invalidates only dependents, and report opening never recalculates. Report declared/bound/executed/accepted coverage separately.

**Independent oracle:** Independent expected DAG topology and sealed payload comparisons with numerical entrypoints disabled during projection.

**Owners:**

- engineering/pipeline.py::StageSpec
- engineering/pipeline.py::STAGES
- engineering/pipeline.py::EnginePipelineRunner
- compiled_dag.py::RegulatoryCompiler
- engineering/pipeline_snapshot.py
- reporting.py

**Required inputs:**

- One explicit supported-check registry
- Typed produces/consumes and method revisions
- Independent expected instances
- Immutable source/scenario/result identities

**Acceptance:**

- One canonical calculation owner per rule
- No successful stage inferred from node binding alone
- Every known required instance obtains a terminal result/reason
- Identical source/method gives identical sealed stage payloads
- UI/CLI/report share identities and values

**Dependencies:** GAP-005, GAP-008

**Offline:** Refactor the existing runner/registry incrementally and replay archived source.

**Windows / physical source:** No Windows dependency except new source acquisition for a newly supported rule.

**Tests inspected:** `test_pipeline_unification.py`, `test_design_member_dependencies.py`, `test_recorded_column_calculation_report.py`, `test_vs05_compiled_dag.py`

**Ledger evidence:** `EV-D3B-REPLAY`, `EV-LOCAL-REPORT`, `EV-AUDIT-FIXES-20261120`


### GAP-018 — Spectral design demands and simultaneity

Registered: **PARTIAL / P0**.

**Existing verified scope:** Native modes/eccentricities and source precision contracts exist; the private same-analysis study matches 4,824/4,824 increments and zero-eccentricity CQC maxima. Original-to-private controls match 4,686/4,824, leaving 138 exceptions at 34 columns.

**Remaining work:** Original full-precision applied amplitudes/effective damping and transferable static eccentricity vectors remain unresolved; signed dynamic design allocation and physical simultaneity are separate policy/method issues, not resolved by componentwise maxima.

**Closure experiment:** Partition the 138 original/private exceptions by case, cut, component, amplitude precision and torsion contribution without changing tolerance. Resolve native precision/transfer on one affected column, then the fixed 4,824 denominator. Separately qualify the demand policy used by SCWB/alpha/PMM; retain proved interval sufficient results when exact concurrency is unavailable.

**Independent oracle:** Independent high-precision CQC/scaling calculation and signed static torsion equilibrium on the same analysis; orthogonal/damping limits and exact perturbations. Physical concurrency is not an oracle output of SRSS/CQC component extrema.

**Owners:**

- engineering/demand_sources.py::native_modal_precision
- engineering/mixed_demands.py::spectral_component_evidence
- column_engine/spectral_envelope.py::replay_component_envelope
- spectrum_reconstruction.py
- engineering/scwb_axial.py
- engineering/column_spectral_shear.py

**Required inputs:**

- Original generation modal amplitudes, effective damping and function/scaling facts
- Accidental torsion definition and signed static effects
- Same-cut modal force components
- Required design direction/sign policy
- Full expected scalar control inventory

**Acceptance:**

- All 4,824 controls accounted at frozen tolerance
- Each exception has a resolved cause or remains open
- No double spectrum scaling, 100/30 or alpha factor
- No scalar interval corner labeled a simultaneous physical vector
- Any sufficient bound is explicitly scoped; failed bound alone is not a proven physical failure

**Dependencies:** GAP-002, GAP-003, GAP-004, GAP-006, GAP-008

**Offline:** Exception clustering, high-precision reconstruction and method-policy validation on archived packets.

**Windows / physical source:** Missing original applied modal/torsion data and controlled paired analysis require Windows; existing solved evidence should be reused first.

**Tests inspected:** `test_native_demand_sources.py`, `test_same_source_spectral_replay.py`, `test_vs26_spectral_envelopes.py`, `test_scwb_axial_interval.py`, `test_column_spectral_shear.py`

**Ledger evidence:** `EV-GAP018-MANUAL-PAIR-20261119`, `EV-GAP018-PAIR-CONTROL-20261119`, `EV-R10-LIVE-INTERVAL-20261120`, `EV-STORY-STATIC-APPLICABILITY-20261120`
