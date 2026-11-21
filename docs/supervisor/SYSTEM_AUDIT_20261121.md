# YENI whole-calculation audit and recovery plan

**Audit date:** 21 November 2026. **Inspected implementation:** [`c71a4dda4ab9453f428a38b3ed79931f8e6eeea3`](https://github.com/feridunfc/YENI/commit/c71a4dda4ab9453f428a38b3ed79931f8e6eeea3). **Disposition:** continue the current product with the bounded corrections and method work below. Engineering release remains **NOT_READY**. This is an architecture, engineering, verification and delivery audit; it is not a new live building calculation.

## Start here

| Document | Use |
| --- | --- |
| [Current architecture](../ARCHITECTURE.md) | Actual owner tree, execution flow, constitutional boundaries and planned evolution |
| [Detailed architecture audit](ARCHITECTURE_AUDIT_20261121.md) | Source-backed architectural strengths, defects and full-product coverage |
| [Engineering audit](ENGINEERING_AUDIT_20261121.md) | Current numerical scope, remaining engineering qualifications and confirmed code behavior |
| [GAP exit recipes](GAP_EXIT_RECIPES_20261121.md) | All 18 GAPs: inputs, experiment, owner, oracle, exit and execution environment |
| [Roadmap and worker tasks](ROADMAP_20261121.md) | Ordered sprints, parallel work, first assignments and stop rules |
| [Research and reference strategy](RESEARCH_AND_REFERENCE_STRATEGY_20261121.md) | Which questions need source acquisition, reverse engineering, analytical work or numerical experiments |
| [Machine-readable work plan](audit_20261121/WORKER_PLAN.json) | Sprint dependencies, GAP mapping, release scopes and acceptance outputs |
| [Audit evidence](audit_20261121/README.md) | Reproducible bounded probes and source identities |

Read the repository-root [AGENTS.md](../../AGENTS.md) first. The existing `src/tbdy_next` runtime, `EnginePipelineRunner`, ETABS gateway and calculation owners remain authoritative for implementation. Historical projects are reference assets. This package introduces no runtime orchestrator, new solver or alternate acquisition route.

## 1. Supervisor judgment

YENI has real numerical capabilities and a real shared source-to-report path. The current weakness is the incomplete qualification and integration of those capabilities across the required physical population. A successful getter, a reconstructed report coefficient, a selected cage and a sealed conditional result each establish a different fact. Treating them as the same milestone has obscured what is still required.

The main causes of slow progress are now identifiable:

1. A single GAP often mixes missing source facts, an unresolved engineering method, an implementation defect and a release decision. Repeating capture cannot resolve all four.
2. The descriptive registry, actual call sequence, candidate 94-node DAG and physical CHECK-instance population are separate mechanisms. Their differences are not consistently visible to a worker.
3. Current numerical results coexist with long historical checkpoints and architecture documents describing an earlier product. A worker can restart already completed work.
4. Reference reports contain useful arithmetic and workflow evidence, but not always the identities, material laws or geometry needed for a complete independent design oracle.
5. Some questions are not identifiable from the available output. Response-spectrum extrema cannot reveal a unique simultaneous response state. More attempts at the same inversion will not supply that information.
6. A limited column-centered product and a complete reinforced-concrete building product have not had a sufficiently explicit delivery boundary. Wall, slab, diaphragm and foundation design require their own complete slices.

The decision is to preserve the existing numerical owners, repair the reproduced defects, qualify the missing source/method interfaces, and complete one named physical result at a time. Whole-product expansion follows the same runner. A new repository or broad kernel rewrite would discard useful evidence without resolving these causes.

## 2. What is established, and at what level

| Evidence | Established scope | Limit |
| --- | --- | --- |
| Linux full offline run associated with the report reconstruction | 1,690 Python tests passed, no skips; 11 JavaScript files passed | Recorded earlier execution; not rerun by this audit |
| User-supplied Windows output for `31a8b08` | 1,690 total, 1,689 passed, one skipped; 11 JavaScript files passed | Full raw log and skipped-test identity were not supplied |
| Native C29 METHOD comparison | 18/18 finished cases on 2/4/8 meshes; 12 conditional factors; 24 PMM sides at 18 physical case-cuts | Full column-wall equilibrium and coupled stability method remain open |
| C29 deformation recovery | Both columns `FULL_SPAN_RECOVERED`; all six 4-to-8 budgets below 0.01 mm | Numerical deformation scope, not whole-building acceptance |
| Golden bank | 44 fixed records: 36 numerical matches, four method differences, four insufficient-source records | Four source gates and four interpretation cases remain unresolved |
| Actual Drive report reconstruction | 26 retained originals: 20 DOCX, six PDF; targeted sway, column, joint and PDF arithmetic | Not complete validation of all 1,256 PDF pages or a full independent PMM solution |
| Current architecture inventory | 139 Python source files; 22 registry entries; 94 candidate nodes/140 edges | Counts describe different things and do not form a completion percentage |
| This audit | Source review, current inventories, primary-source review and three bounded behavior probes | No fresh full regression, live ETABS run or private C29 replay |

Current evidence IDs are `EV-C29-NATIVE-CONDITIONAL-TS500-20261121`, `EV-REPORT-SWAY-RECONSTRUCTION-20261121` and `EV-WINDOWS-OFFLINE-31A8B08-20261121` in the [ledger](../VERIFICATION_LEDGER.json). The audit adds its own evidence ID rather than retargeting those tests.

The original C29 R14 result remains **2/87 conditional**, with eight connected beams and joint 40 checks. This is not 87 designed columns. The latest physical clear-length census supports 73 standalone columns; 14 have wall coupling. Earlier 59-column and 1,392 spectral-shear numerical checkpoints retain their historical scopes. The later wall-coupled capacity-span guard withholds isolated capacity shear for those 14; the earlier count must not be presented as current whole-building acceptance.

## 3. Findings ordered by action

P0 below identifies a release-blocking engineering prerequisite, not an assertion of an unsafe completed building. P1 requires correction or qualification before the affected scope is expanded. P2 is a bounded robustness or maintainability issue. Only findings explicitly labelled reproduced were executed as behavior probes.

| ID | Priority / kind | Evidence and consequence | Required action |
| --- | --- | --- | --- |
| YSA-01 | P1, reproduced defect | `story_pdelta.review_story_pdelta` rejects negative absolute `level_m`; translating the same geometry by -10 m changes the adapter from 4 expected/evaluated instances to 0/0 | Allow finite signed elevations; validate relative height independently; retain expected instances on source rejection |
| YSA-02 | P1, reproduced defect | A known -100 kN free-body residual reaches `STORY_COMPRESSION_INCOMPLETE`, while the conditional child still supplies both axes' `story_inputs` | Propagate proven source/balance failure to dependent eligibility; distinguish failure from an explicitly unresolved wall method |
| YSA-03 | P2, reproduced boundary defect | Receipt writer accepts index 100; two-digit readers omit it, reading 99 of 100 records | Parse arbitrary-width numeric prefixes and sort numerically, with duplicate/finalization checks |
| YSA-04 | P1, architecture | `STAGES` describes a hand-written execution sequence; R14 has no StageSpec; B1/B2 are hidden in report evidence | Make existing registered owners and actual execution trace agree before broader scheduler expansion |
| YSA-05 | P1, coverage | Axial/PMM/dependency scopes exist, but no complete shared expected-instance ledger covers all required families | Freeze rule/subject/case/cut/side/axis/cage instances before successful results; preserve missing and failed rows |
| YSA-06 | P1, ownership | `_build_frame_catalog` lives in the high-level R10 module and is imported by eight other modules | Extract its existing behavior into a neutral geometry owner with archived-output equivalence |
| YSA-07 | P0, engineering method | Full wall-frame critical-load contribution and coupled second-order demands are unsupported | Execute the force-balance, coupled-response and method-decision experiments; do not invent wall Euler credit |
| YSA-08 | P0, demand semantics | Separate RSA extrema contain no unique cross-component time/state correspondence | Qualify scalar reconstruction and a declared design-envelope/signed-state policy separately |
| YSA-09 | P0, project applicability | Complete profile, combination scope and general analysis-generation qualification remain open | Build a source-backed decision record and required-family roster; consume it through existing owners |
| YSA-10 | P1, verification | Report arithmetic and source replay do not yet supply full independent PMM/detailing/alpha feedback acceptance | Complete independent section/cage and actual alpha-below-one examples through the runner |
| YSA-11 | P1, product scope | Complete wall, slab, diaphragm and foundation owners are absent; beam torsion/SLS and some irregularities are incomplete | Track explicit domain slices and release scopes beyond the column recovery GAPs |
| YSA-12 | P1, documentation | The architecture landing page is VS01/VS03-era and historical constitutions belong to different products | Replace the landing architecture and link one current roadmap; retain historical evidence with dates |
| YSA-13 | P1, source-binding review | End-restraint terms validate neighbor membership and target EI, but other EI terms and all term lengths are accepted as positive supplied values | Bind each term to native geometry/material/modifiers or retain an explicitly adopted assumption scope |
| YSA-14 | P1, acceptance design | Whole-product authority is deliberately denied/hard-coded incomplete in candidate and report contracts | Add a scoped acceptance evaluator after qualified methods and complete required instances exist; never clear flags as a substitute |

YSA-01/02 were reproduced with **existing contract-test inputs and actual production owners**, not a fabricated C29 calculation. YSA-03 used a temporary receipt directory. YSA-13 is a code-review observation; no arbitrary-neighbor-stiffness runtime probe was performed. These distinctions are retained in the evidence files.

### Consequences of the reproduced engineering behaviors

An elevation datum is a coordinate choice. Translating every level by the same constant cannot change a dimensionless story stability calculation when heights, loads, shears and drifts are unchanged. Rejecting negative elevation is therefore a validation defect. Returning zero expected instances on that rejection is a separate accounting defect: the physical obligations still exist.

For the conditional frame path, unavailable wall critical-load methodology and a known equilibrium failure are different states. The existing conditional C29 scope may remain calculable when the full wall method is unresolved. A known source inconsistency must remain visible to every dependent design result. Classify imbalance as proven only after required contributor coverage, compatible state and independently obtained external loads are qualified; a residual caused by missing walls is unresolved evidence. The proposed correction must preserve this distinction rather than disabling all conditional work.

No private native C29 balance was re-read in this audit. The probes establish general code behavior, not that the native C29 calculation had the injected imbalance or elevation failure.

## 4. Constitution and authority

The current operational constitution is [AGENTS.md](../../AGENTS.md), with the [project charter](../context/PROJECT_CHARTER.md) and the versioned recipe supplying context. Older Drive constitutions describe TBDY or Column ownership, branches, permissions and runtimes. Their reusable engineering principles remain references; they do not replace current YENI ownership or session authorization.

Use two separate authority questions:

- **What does the product actually do?** Current verified code, source identity and recorded executions answer this.
- **What must a valid engineering method do?** Applicable primary standards, their edition/amendments, project applicability and justified method decisions answer this.

Code is evidence of implemented behavior; it does not override a standard. A successful example report does not override either source identity or the governing rule. This separation corrects the misleading single precedence list present in one historical architecture document.

The retained rules are: one product runtime; one acquisition owner; separate Physical/Analysis/Design/Result identities; explicit units; immutable source and absolute demand transformations; independent expected scope; exact case/step/cut/side identity; separate static states and spectral bounds; actual versus proposed reinforcement; local failure propagation; bounded feedback; and report projection of the sealed result.

The supported section-kernel unit system is **N–mm–MPa**; analysis boundaries use explicitly named **kN–m–kNm** fields. Historical kN–cm conventions from other repositories must not be imported implicitly. The approved operational connection policy is API unit code 6, kN/m/C, with temporary selections restored and verified.

## 5. Engineering method decisions that unblock work

### 5.1 GAP-009: finish equilibrium before deciding critical-load mapping

Use the solved eight-part METHOD source first. At the two existing cuts, preserve 53 and 36 physical contributors. Bind exact-state upper-side shell resultants, native column forces and independently derived external gravity/self weight. Start with `C29G_U_F`, then extend to `C29G_TN_F` and `C29G_TP_F`. The first deliverable is six signed balance tables, not another full 18-case analysis cycle.

The native ledger's shell display rows are `Max/Min`; frame inputs carry exact `Step 1`. Do not relabel one as the other. Demonstrate a compatible state or acquire only the missing exact-step source through the existing gateway. Transform shell point-element local axes before integrating. Distinguish a physical wall from its shell and pier representations so each load path is counted once.

After balance, compare coupled first/second-order response with the same supports, EI, loading and mesh basis. Check integrated forces/moments at physical cuts, not only isolated nodal peaks at a force-transfer discontinuity. C104's construction, reinforcement continuity and two cross-section geometries must be explicit.

A generalized eigen-buckling calculation can diagnose the adopted stiffness and load pattern. Its multiplier is not automatically a TS500 story critical-load sum. If a defensible mapping to the moment-magnification approximation cannot be established, qualify an expressly adopted direct second-order branch through the existing demand owners. Preserve the separate requirements of the applicable general method.

Zero critical-load credit for walls/coupled columns does not alone prove that a frame-only result bounds the full system, because the omitted wall compression changes the numerator too. For frame and wall terms, the sign of the difference between `Nf/Kf` and `(Nf+Nw)/(Kf+Kw)` depends on both `Nw` and `Kw`. The current result is an explicit conditional scope, not a proven whole-building bound.

### 5.2 TS500 interpretation: resolve the method, not the printed factor

The user-supplied February 2000 TS500 PDF was read and printed page 27 visually inspected. Its Eq. 7.24/7.27 denominators place **1.3 with the axial-load numerator**. YENI already has this placement; an inspected historical TBDY owner does not. Copying the old owner would reintroduce an error.

The same source's Eq. 7.29 prose refers to free length while its displayed symbol is `lk/i`. The existing report reconstruction shows all 36 adopted factors matching the product, while none triggers that branch from the printed `lk` values. Preserve both calculations and adjudicate the length/method basis with the standard edition and source geometry. Matching the report by forcing the product is not a resolution.

The approximate method's constant-section/constant-axial-force premises and the general method's requirements matter for the C29 self-weight/Nmax idealization. A successful displacement refinement does not by itself qualify every signed moment or PMM utilization as a conservative code result.

### 5.3 GAP-018: stop attempting an unidentifiable reconstruction

CSI explains that response-spectrum component extrema have no cross-quantity correspondence or time-of-extreme information. Reconstruct applied modal amplitudes, damping/correlation, scales and accidental-torsion contributions as scalar response quantities. Then choose and independently verify an admissible design-envelope policy or a separately identified signed-state analysis route. Do not manufacture concurrence by joining Max N, Max M2 and Max M3.

The recorded 4,686/4,824 force-control reconstruction leaves 138 mismatches. Work on a bounded discrepancy ledger separating precision, missing amplitudes, damping/scaling, eccentricity and source identity. Do not widen the tolerance to make the total green.

### 5.4 Independent design and feedback

For PMM, independently establish bar coordinates, local axes, concrete/steel laws, axial caps and fixed-N directional capacity. Source-force agreement is not an independent capacity check. Compare physical values and intermediate equilibrium, not only one utilization ratio.

For alpha feedback, the current original scenario requires zero iterations. Drive's `strongcol4` report supplies useful nontrivial reference arithmetic: shear-weighted alpha values about 0.908192 and 0.767095, with inverse factors about 1.101089 and 1.303619. Its printed section capacities and low-axial exceptions still need independent qualification. Use a complete same-source case to show demand amplification, cage change, recomputed capacity/shear/joint results and convergence. Do not combine unrelated report generations merely because member labels match.

## 6. Delivery management and mentoring

Start with three parallel, bounded lanes:

1. **Software correctness:** reproduce and fix YSA-01/02/03; preserve numerical scopes and add targeted regression guards.
2. **Native evidence:** complete the C29 two-cut exact-state balance using the already solved model and existing acquisition owner.
3. **Method/verification:** prepare the coupled-method decision, complete section oracle inputs and the alpha-below-one benchmark. Each research question ends with a decision table or a failed hypothesis plus the next bounded experiment.

Only one lane owns integration and each source module has one active writer. Share physical examples and contracts before implementation. A worker handoff must name the exact source/model/case/cut, missing fact or decision, existing producer, consumer, numerical exit and remaining scope. “Blocked” alone is not a handoff.

Use the [roadmap](ROADMAP_20261121.md) to select the next task. A calculation sprint ends at a named numerical outcome and its sealed report; a research sprint ends at an executable experiment and method decision, not a bibliography. A contract test can prove rejection behavior; it cannot be counted as a real-building completion. A low PMM utilization cannot replace source, applicability or detailing evidence.

Track progress with four separate measures: required physical-instance coverage, source qualification, independent numerical/method verification, and product integration. Keep the 18 GAP statuses as broad engineering registers, but show their closed subscopes. Do not report a single percentage from tests, DAG nodes, recipe labels or selected columns.

The first handoff is **S00**, followed by the **S02 balance result** and the **S04 method decision**. Whole-product domain work is explicitly scheduled after or alongside the supported-column chain, with separate applicability and independent examples. The plan does not promise a full building release merely by closing C29.

## 7. Audit boundary and publication

This audit inspected a fixed public implementation, refreshed the actual Drive inventory, verified retained source hashes, read selected historical architecture documents, inspected primary standard/manufacturer references and compared reference repository owners at pinned commits. Private Windows captures and the live ETABS process were unavailable in this environment. Original EDB and reports are not published.

The three reproduced findings are recorded as audit observations. This documentation delivery does **not** fix their production code, run a new full test suite, grant engineering approval or close a GAP. It corrects the architecture entry point, makes the remaining work executable, and supplies an evidence-backed plan for the worker. The current numerical achievements and historical ledger remain intact.
