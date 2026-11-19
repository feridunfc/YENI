# YENI engineering pipeline audit

Historical review boundary: commit `1697a968dc30e342b83685bec898bda3109643ca`. Subsequent implementation and verification are tracked in `AUDIT_FIXES_20261119.md`. Findings in this review describe the audited baseline, not automatically every later revision.

## Decision and scope

**The project now has a real, conditional static column to roof joint calculation. It does not yet have a reliable, complete earthquake design product slice.** The remaining work is not merely collecting the last ETABS evidence. This audit reproduced numerical adapter defects, a Web versus CLI scenario mismatch, and missing transitions from source evidence to usable engineering inputs and spectral design methods.

The current source preserves an honest engineering release boundary. That boundary must remain. However, a final `NOT_READY` label does not excuse an incorrect favorable numerical result, a missing calculation, or a design action that behaves differently between interfaces. The next delivery should repair those concrete defects and complete one interior joint and one complete storey through the existing owners. A larger recipe, another solver, another pipeline, or another ETABS connection is not the required next step.

Audit date: 19 November 2026. Intended audience: YENI engineering and implementation owners. This is a read-only audit; no production file, branch, source archive, or engineering acceptance was changed. Audit finding identifiers in this report are not new CHECK identifiers.

## Inspected revision

Both requested GitHub branches resolved to the same commit at initial inspection and at the final remote check:

| Branch | Inspected commit |
| --- | --- |
| `baseline/local_import` | `1697a968dc30e342b83685bec898bda3109643ca` |
| `work/gap-018-spectrum-evidence` | `1697a968dc30e342b83685bec898bda3109643ca` |

Git tree: `25d83cd409dcc2cdf147cb2ac37e4924709811ca`. The full repository was cloned and checked out detached at that revision. The working tree remained clean before and after the official test run and audit probes. These branches are two references to one inspected implementation, not two independently passing implementations.

`SOURCE_MANIFEST.json` records the pinned revision, remote observations, tracked file hashes, sources used, and inspection boundaries. A hash inventory is an identity inventory; it does not claim every tracked file was deeply reviewed. The inspected owner list identifies the substantive review surface.

Unpublished local Windows edits, the private C29 calculation sheet, original/private ETABS captures, and individual rows of the 138 transfer exceptions were **NOT_INSPECTED**. Live ETABS was **NOT_RUN**. The audit does not infer that unpublished progress is absent and does not recommend rolling local work back to an older GitHub snapshot.

## Verification performed

The official command `python -B tools/test_offline.py` ran anew against the clean pinned checkout. It completed with exit code 0: **1,430 Python tests in 147.172 seconds**, followed by the script's compilation, JavaScript and production golden gates. Total wall time was 161.016 seconds. Environment: Linux, CPython 3.12.14, Node 24.22.3. The exact command, timing, environment, revision and log hash are recorded in `VERIFICATION_RESULTS.json` and the included execution log.

The production golden gate evaluated the existing **44 records**: 15 `NUMERICAL_MATCH`, 25 `INSUFFICIENT_SOURCE`, and 4 `ENGINEERING_INTERPRETATION_DIFFERENCE`. Its engineering acceptance remained false. The official software runner deliberately distinguishes software regression success from incomplete engineering acceptance; its successful exit is not a declaration that all 44 examples are accepted.

GitHub Actions run 44556903482 was independently inspected. Its Ubuntu Python 3.11, Ubuntu Python 3.12 and Windows Python 3.12 jobs all succeeded at this exact SHA. Those are observed CI executions, not Windows runs performed by this audit.

Fresh audit probes additionally called actual production owners and adapters. They reproduced three structural adapter defects, Web/CLI scenario divergence, two omitted report projections, and four spectral/alpha scope behaviors. They use explicit synthetic inputs or the repository's public fixtures. They do not reproduce the private building and do not close an engineering check.

| Population | Meaning and current treatment |
| --- | --- |
| 73 recipe headings and primary examples | Preserved documentation/example identities; not 73 accepted checks |
| 12 additional adapter examples | Separate from the 73; the bank contains 85 total cases |
| 44 production comparisons | Existing production gate, freshly executed as above |
| Historical 333 arithmetic assertions | Separate historical recipe population; not newly rerun here |
| Other historical 333 compared records | A different population; not merged with the first 333 |
| 94 DAG nodes | Catalog identities; 30 bound to stages, 64 unbound |
| 22 registered stages | Registry count; not a count of engineering approvals |
| 18 registered GAPs | Current register: 3 OPEN and 15 PARTIAL; no completion percentage inferred |
| 87 columns and 1,206 static rows | Recorded private model population; not a fresh private replay by this audit |

The six verification levels are separately recorded: document/source consistency, independent arithmetic, production owner comparisons, recorded-source pipeline replay, live ETABS verification, and engineering acceptance. Private replay, live verification, and engineering acceptance remain `NOT_RUN`. A synthetic HTTP/CLI pipeline execution is separately identified and is not promoted to private recorded-source replay.

## Progress that must be preserved

The former blanket criticism that new R10/R08/R14 results are always recomputed when a report opens is obsolete for the inspected new-run path. The existing runner passes selected R10 cages to local R08, records calculation results and derived report evidence, and seals them in finalized snapshots. New standard reports project those recorded outputs. Existing legacy compatibility behavior remains a separate path. Current R14 also requires positive completion and finite results in places where the older audit had found false numerical closure. [S1, S2]

The latest worker record describes a meaningful conditional static slice: 87 selected cages, three signed static combinations, 1,206 force vectors and 7,236 native scalar comparisons. Current repository documentation records selected-cage PMM utilization up to 0.422829 and a worked roof-joint calculation. It also records 0 numerically closed and 87 partial columns with 17 remaining gates. These are historical model results read from the current ledger, not new private-model calculations performed here. [S3]

The supplied C29 rounded numbers are internally consistent. Dividing 379.73 by 1,245.60 gives approximately 0.30486. The two joint ratios are approximately 0.47191 and 0.31322. Five 10 mm legs provide 392.699 mm2. Required area 201.29 mm2 at 90 mm implies an area-density pitch allowance near 175.6 mm before the stated 100 mm joint cap. A selected 90 mm pitch is consistent with those quantities. This arithmetic does not independently validate the reported radial capacity, physical leg participation, anchorage, source force, or joint geometry.

K = 1, Rm = 0 and centered geometry are material assumptions. The moment capacity is a fixed-axial-force, fixed-moment-direction radial result, not a capacity that transfers unchanged to another axial force or direction. The gravity PMM example and capacity-design joint shear are useful outputs of the selected-cage scenario; they are not by themselves the missing earthquake SCWB and storey alpha proof.

## Confirmed defects

### A01 The joint envelope omits governing small or missing shear cases

Priority P1. Existing owner: `engineering/column_r10_live.py::_attach_r13_joint_shear_and_transverse`. The code skips missing upper/lower rows and keeps a combination only when `max(v_up, v_lo) > 1.0`. It then subtracts the minimum retained column shear from the selected-beam tension sum. A smaller deductive term produces a larger joint demand, so omitting a small valid term is unconservative. [S4]

The production-adapter probe used two assigned seismic static combinations and a 1,050 kN beam tension sum. E1 had 200 kN in both upper and lower columns; E2 had 0.5 kN in both. The reference geometric limit was 946.5728 kN.

| Quantity | Current adapter | Complete envelope |
| --- | ---: | ---: |
| Column shear deduction | 200 kN | 0.5 kN |
| Joint demand | 850 kN | 1,049.5 kN |
| Within limit | true | false |

Changing E2 to 1.000000001 kN restores it to the envelope and changes the answer to approximately 1,049 kN and false. Removing expected E2 altogether also leaves the favorable reduced 850 kN result. Missing an expected combination does not establish the complete reduced envelope. A qualified zero-deduction bound would instead be 1,050 kN here, or the comparison must remain unresolved.

Correction: retain the expected applicable combination roster, include valid zero and small shears, and never use force magnitude as a direction-applicability rule. A missing deduction must use a justified conservative bound or a specific unresolved result. Acceptance tests must cover 0, 0.5, 1 and 1 plus epsilon, a removed expected case, both sway directions, and the monotonicity of deductive shear. This proves a general adapter defect; it does not establish that the private C29 input exercises it.

### A02 Lower column confinement is selected by local label instead of physical direction

Priority P1. The live joint adapter reads `confinement_v2` for a target V2 row and `confinement_v3` for V3 without mapping the target column's physical direction to the lower column's local axes. [S5]

The probe has a vertical upper column with V2 along global X and a lower column rotated 90 degrees. The relevant lower direction is V3. Lower V2 requires 300 mm2 and provides 400 mm2 at 100 mm; lower V3 requires 1,000 mm2 and provides 200 mm2. For the tested unenclosed-joint transfer, the current result uses 180/400 = **0.45, satisfied**. The correct physical direction uses 600/200 = **3.0, not satisfied**, with a whole-millimetre pitch bound of 33 mm from the available area.

The offline owner `column_engine/column_joints.py::_tie_rows` already implements the unique physical-axis mapping, and an existing offline regression covers a rotated unequal lower column. The architecture shares scalar formula owners but duplicates engineering assembly policy. That duplicated policy is inconsistent. [S6]

Correction: reuse the existing physical mapping contract at the narrowest common location. Record target axis, global direction and lower source axis. Unsupported oblique/ambiguous mappings must remain explicit. Test through the live projection, not only through the already correct offline owner.

### A03 Native I and J reversal removes a physical joint tie result

Priority P2. The same live adapter classifies upper/lower columns using physical elevation **or** endpoint label, then removes members appearing in both sets. A reversed lower column can therefore be classified as upper solely because its joint endpoint is I. [S7]

The probe reverses the lower member's native endpoints and corresponding valid local-axis basis while preserving physical geometry, reinforcement and the target upper column. The normal representation returns a joint transverse result; the reversed representation returns none. This is a representation-invariance defect, not missing physical data.

Correction: use the physical other-end elevation and uniqueness to determine above/below, as the existing offline owner does. Preserve I/J for cut location and sign mapping. Do not use it as a substitute for geometry. The private 252-of-272 joint-axis output population was unavailable, so this audit does not attribute its 20 uncomputed records to this defect.

### A04 Web and CLI reinforcement selection execute different prerequisite paths

Priority P1. `/api/apply-rebar-selection` copies the source snapshot and changes selection policies directly. It does not call `create_design_scenario` or archive `parent.source`. The CLI does both. The runner builds design dependencies, selected-candidate lineage, alpha iteration and revision evidence only when a scenario exists. [S8, S9]

Fresh execution used the same public synthetic source and default policy intent through the real HTTP endpoint and CLI owner:

| Result | Web action | CLI action |
| --- | --- | --- |
| Transport completion | HTTP 200 | Exit 0 |
| Scenario and parent archive | Absent | Present |
| Dependency and candidate ledgers | Absent | Present |
| Alpha record | Absent | BLOCKED_INPUTS |
| Candidate on this incomplete fixture | Selected reference | Blocked dependency |

Reapplying the CLI scenario through Web fails with HTTP 422. Unchanged policies produce `SCENARIO_PARENT_SOURCE_MISSING_OR_UNSAFE`; changed policy produces `SCENARIO_SOURCE_OR_POLICY_CHANGED`. The validation correctly rejects malformed lineage. The Web adapter fails to prepare the intended scenario.

Correction: share one scenario-preparation operation between adapters, using the existing scenario owner and runner. Resolve the immutable native parent, normalize policy, create a new scenario, preserve parent bytes, and invoke the runner. Selection from a previous scenario should derive a valid new scenario from its verified parent according to the existing supported contract. Do not strip lineage to bypass rejection. Acceptance must compare normalized engineering outputs and dependency scope across interfaces, not only return codes.

### A05 The standard print trace omits new governing and joint pitch results

Priority P2. R14 records the governing static station, fixed-N moment demand, radial capacity and reserve. R10 records the joint transverse result and maximum usable whole-millimetre pitch. The normal R14 and R10 HTML sections do not project those new fields. [S10]

A presentation-only probe changed the governing combination, moment demand and capacity while holding the summary ratio fixed. R14 HTML remained identical. Changing the joint pitch bound from 100 to 50 mm and its required area also left R10 HTML unchanged. This is an omitted product projection; the data are present in JSON. It is not evidence that the private C29 worksheet is incorrect.

Correction: expose a normal per-member/per-joint calculation sheet from sealed fields, including physical identity, governing case, assumptions, intermediate terms, capacity and selected reinforcement. Preserve pure rendering: opening the report must invoke no calculation owner. A field-relevance test must demonstrate that changing a recorded governing result changes the corresponding displayed trace.

### A06 Integration branch updates are outside the CI trigger filters

Priority P2. The workflow push and pull-request filters omit `baseline/local_import` and `baseline/**`. The current SHA was tested through the work branch; its present CI result is valid. A future baseline-only update or baseline-target pull request will not trigger this workflow under the current filters. [S11]

Correction: include the actual integration branch in both applicable trigger sets and verify that its update invokes the existing Linux/Windows matrix. Do not treat a work-branch result for an older SHA as validation of a newer baseline.

## Implementation boundaries that evidence collection cannot close

### Engineering inputs have no complete production acceptance transition

R03 always appends missing approved-profile, approved-load-role and analysis-generation gates. Corresponding approval and authorization fields are always false. Reconciliation can recognize assigned design families, but it does not consume an approved project profile or analysis-generation attestation. Local R08 uses reference creep zero and a candidate effective span, with fixed open basis requirements. R14 imports these unresolved dependencies. [S12]

These guards correctly avoid manufacturing approval. The delivery defect is the absent input and transition: collecting better force rows cannot make a function consume an engineering input it does not accept. Replacing false with true would be equally wrong. The existing scenario/profile path needs a versioned engineering-input object containing values, units, axes, physical applicability, source identity, basis, reviewer role and revision.

Keep three distinct outcomes: a calculation under disclosed assumptions; a verified calculation under qualified inputs; and engineering acceptance. A complete conditional calculation can be useful before full-building release. Conversely, an approval checkbox must not erase a missing physical face, unqualified demand method or failed numerical check.

### Spectral source evidence does not reach a qualified SCWB and alpha method

`alpha_iteration.py::qualify_story_alpha` rejects any assigned ductile/capacity combination not classified `STATIC_SIGNED_VECTOR`. R10 SCWB likewise selects static signed combinations. Spectral source qualification fields remain false, and the new source evidence is stored for reporting without being passed into an implemented spectral alpha method. No production CQC force-reconstruction owner was found in the inspected package. The private CQC checkpoint explicitly records no runtime changes. [S13]

Therefore **resolving all 138 original/private comparison exceptions would not, by itself, make this revision run spectral SCWB and alpha**. The source-transfer question and missing engineering method must be tracked separately. The existing integrated recipe already allows a declared design method, a justified conservative bound, or a separately authorized signed-time route. Implement that contract through the existing owners; do not expand the documentation again as a substitute. [S14]

Two fresh owner probes expose a further scope problem. The existing two-column signed fixture produces alpha 0.8 and factor 1.25 in both directions. Adding one unsupported spectral combination, without removing any signed input, returns a blocked result with an empty case list. An X-only-response fixture also evaluates the zero-shear Y direction without an explicit combination-to-direction applicability contract and blocks the aggregate. Global completeness must remain false when an applicable case is unresolved, but independently evaluable case results should survive. Applicability must come from declared combination/direction semantics, never from observing a small response.

The strict alpha branch also requires two-sign SCWB at both ends and excludes unverified exemptions. Roof/base/no-beam topology therefore needs an explicit applicability outcome. The regulation's roof exception is a legitimate method branch, not a missing getter. An exemption for the SCWB inequality must not exempt unrelated joint shear, anchorage or detailing requirements. [S15, N1]

### Combination assignment is not a complete combination book

`design_assignments` derives defaults by intersecting known project-family names with combinations already present in ETABS. Its binder checks group keys, known names and duplicates. It does not establish that all required directions and design branches exist. A ledger built only from those selected names can prove that selected requests returned rows; it cannot independently prove that the normative expected book was complete. [S16]

The required product contract is a project-specific expected book established before looking at returned force rows. It needs group, direction, operator, signed/static versus spectral semantics, component cases, factors and applicability. Missing X/Y or required branches must remain missing expected instances. For a model without required combinations, produce an exact proposed definition/selection delta. If model mutation is later authorized, execute it through the existing gateway with return-code checks, exact readback, state restoration and generation invalidation. This audit does not add or execute a setter route.

Selecting an internal candidate cage is separate from writing reinforcement into ETABS. SCWB needs bound selected or actual beam/column reinforcement and capacities in the same scenario; it need not wait for an ETABS reinforcement setter merely to evaluate that candidate. Model writeback, analysis regeneration and recapture are separate operations with their own authority and invalidation consequences.

## P Delta and spectral method decisions

### Second order effects need a declared analysis path

Local R08 currently calculates effective stiffness and buckling loads using reference Rm = 0, then uses the selected cage's steel inertia where available. It multiplies local moment factors by an available global candidate factor and applies minimum eccentricity before calling the existing PMM capacity owner. This is actual calculation, but the source analysis order and approved support/creep basis remain unresolved. [S17]

The next slice must identify whether the source is first order, includes global P Delta, or contains a supported nonlinear/tangent-stiffness state; which effects remain to be added; and which axis-specific effective lengths, sway classification and creep inputs apply. Record the transformation path and factors alongside the demand revision. Tests should show that a qualified already-included effect is not applied twice and that an unknown analysis basis is not silently treated as first order. This audit did not prove an actual double-amplification error in the private C29 run.

K = 1 and Rm = 0 may remain an explicitly named reference scenario. They must not become approved physical values because many force components match ETABS. A normal report should display source order, global treatment, local treatment, effective-length basis, creep basis and final design moments together.

### Do not search for a nonexistent simultaneous spectrum vector

CSI documents response-spectrum quantities as separately estimated maxima without timing/correspondence between response quantities. The ETABS accidental-eccentricity static procedure adds an internally computed static contribution to response-spectrum results. A qualified signed static torsion component is useful; it does not restore a unique simultaneous dynamic P/M/V vector. [N2, N3, N4]

The method chain must be completed in the requested order: numerical modal precision, applied accidental eccentricity, modal/directional combination, SCWB governing axial demand, common-cut storey shear allocation, then alpha feedback. Each consumer needs a declared method rather than an invented simultaneous vector.

For SCWB, the governing axial force is the direction-compatible value that produces the unfavorable column capacity, under the accepted design-demand method. Gravity N alone does not prove the seismic choice. If an N interval is used, endpoint sampling alone needs justification because moment resistance can be nonmonotone over the interval. The existing section capacity owner should evaluate the accepted policy; the independent oracle should remain arithmetically independent. [N1]

For storey allocation, spatial aggregation and modal combination do not generally commute. An elementary illustration uses member modal contributions (1, 0) and (-1, 1). Their separate SRSS maxima are 1 and square root of 2. The common signed sum has modal contributions (0, 1), with maximum 1. Adding the separate maxima gives a different quantity. This illustrates why maxima cannot be summed as simultaneous equilibrium forces; it is not a proposed TBDY alpha formula.

### Eight corners are a conditional sufficient bound

The current corner owner appropriately says that eight evaluated vertices are not proof of concurrent demand or of nonlinear convexity between vertices. Its success remains conditional. However, an exceeded corner currently demands `CONCURRENT_VECTOR_REQUIRED`. The correct next action is a qualified tighter demand method or bound, not necessarily a recoverable concurrent RSA vector. [S18]

To infer whole-box inclusion from vertices, the actual fixed-cage admissible set must be convex and contain those vertices, and the physical demand domain must be contained in the box. An N-dependent nonlinear magnifier does not automatically preserve that argument. Its full-domain image, branch changes and singular denominators need a justified bound. Interior samples are useful diagnostics but are not a continuum proof. An excessive conservative box is an inconclusive sufficient test, not automatic proof of physical failure.

### Classify the 138 exceptions without erasing them

The ledger records 4,824 of 4,824 private same-analysis torsion-increment controls and 4,824 of 4,824 conditional CQC controls. Original/private transfer passes 4,686 of 4,824, leaving 138 exceptions on 103 of 804 case-cuts and 34 columns. The frozen criterion is absolute difference no greater than `1e-8 + 1e-8 * max(abs(a), abs(b))`. The largest reported moment exception is about 1.19003e-6 kN m, or 1.19 N mm. [S3]

That magnitude describes scale, not acceptance. Individual private residuals and downstream margins were unavailable. Preserve the original failed comparison. Separately assess same-input replay, cross-analysis numerical equivalence and engineering decision robustness. Any new equivalence policy needs a prospective, versioned justification for native-unit absolute floors, relative allowance, near-zero behavior and propagation into governing case, capacity branch, cage selection and alpha classification.

A legitimate alternative is to adopt the complete private analysis as a new coherent generation and capture all required inputs and results together through the existing gateway. Do not transplant only its torsion values into an older source. This avoids making backward transfer to the original archive a prerequisite for all future product progress.

## Why delivery stalls

The strongest evidence is not a shortage of hashes. The project has solved substantial source identity and replay problems, but the next consumer is often absent or different between routes.

First, scalar ownership does not guarantee engineering ownership. The live and offline routes share kernels while rebuilding physical-axis mapping, topology and expected combinations independently. The reproduced rotation and I/J defects are a concrete consequence.

Second, a shared runner does not guarantee a shared scenario lifecycle. Web can reach the runner without the prerequisite lineage and feedback records that CLI creates. More source evidence cannot repair this orchestration difference.

Third, some open statuses are permanent outputs of the current functions. Without executable input contracts, evidence can be observed and archived but never consumed to change the supported calculation state.

Fourth, the spectral work mixes three completion questions: reproduce ETABS scalars, approve an engineering demand method, and deliver a consumer result. Finishing the first does not implement the other two. The private investigation has value; it should now become a bounded method consumed by R10 and alpha.

Fifth, a single unsupported combination can suppress supported case outputs, while a legitimate roof exemption can appear as an unimplemented end condition. This makes a narrow useful slice look impossible until the entire building is solved. Scoped results and global completeness must coexist.

Sixth, the new calculation detail is not yet consistently available through the normal user report. A worker can extract a useful private calculation sheet while the standard product still shows utilization summaries. That is a delivery gap, not a need for another calculation engine.

The 1,430-test success remains useful regression evidence. The new counterexamples show missing physical and adapter invariants in that tested surface. Increasing raw test count is a poor completion target. Add tests that can change an engineering decision or demonstrate an entire product path.

## Ordered recovery plan

### Delivery one Repair the current calculation path

Fix A01 through A04 first: governing shear coverage, physical axis mapping, I/J invariance and one shared scenario-preparation path. Reuse the correct existing offline topology contract where appropriate. Add the precise counterexamples in this audit to production regressions, including the missing expected combination. Preserve the full expected population and explicit unresolved outcomes.

Exit criterion: identical physical input produces invariant results under native I/J reversal and correct axis rotation; zero/small/missing deductions cannot produce an unjustified favorable envelope; equivalent Web and CLI policies produce equivalent normalized dependency, candidate and alpha outcomes. The existing full suite remains green.

### Delivery two Make the C29 result a normal product scenario

Retain the C29 roof example with its disclosed assumptions. Capture or prepare a lawful, reproducible fixture containing the required inputs, or keep original-source validation explicitly pending while public synthetic fixtures test the product path. Add the recorded governing PMM and joint tie trace to the standard report. Fix the integration-branch CI filters.

Exit criterion: a user can select a cage, run the existing engine, inspect the governing cut and selected reinforcement, reopen the same calculation sheet, and replay the same result without private extraction scripts or report-time recalculation. Changes to cage or engineering inputs produce a new revision and visible dependent changes.

### Delivery three Complete one interior joint under a qualified demand method

Freeze one source generation, physical interior joint, upper/lower column end cuts, both relevant beam faces, selected cages, physical axes, and the complete applicable combination or demand family for the chosen direction and both earthquake signs. Implement the supported engineering-input consumer for analysis order, effective length, creep and face basis.

Use a qualified zero-Vkol upper bound first when its sign and mechanism conditions hold. If that bound passes, do not require a favorable actual-shear deduction merely to prove the same inequality. If a reduced demand is needed, require complete compatible upper/lower shear evidence. Bound the SCWB axial-demand policy for the same direction and source generation.

Exit criterion: one independent worksheet follows demand, minimum eccentricity, second-order treatment, PMM, SCWB, capacity shear, joint demand/limit and tie pitch through the existing owners. Include one passing case, one deliberate exceedance and one removed expected row. Missing data block dependent results while preserving independently complete results.

### Delivery four Complete one storey and one direction with alpha feedback

A joint is insufficient to define the storey denominator. Freeze the complete applicable column population at one common physical cut, explicit direction and earthquake-demand family. Represent roof/base/low-axial exceptions according to the code and physical applicability. Retain both satisfied and unsatisfied SCWB members in the required population.

Demonstrate a declared supported signed-earthquake example, or a qualified spectral method when available. Do not relabel `Grav_Ult` as earthquake evidence. An intentionally simplified public contract fixture may exercise the route while actual-source verification remains separate.

Exit criterion: demonstrate alpha at 1, in the permitted amplification interval, at the threshold and below it; use unrounded decisions; apply feedback from immutable base demands; reevaluate affected selected-cage, shear and joint consumers; detect nonconvergence; and record one final source/cage/demand revision shared by all consumers and the report. No report should display an alpha from one iteration with capacities from another.

### Delivery five Implement the bounded spectral chain

Choose a coherent source generation and one supported modal/damping branch first. Complete precision and applied eccentricity qualification, implement the accepted modal/directional operation in the existing owner path, bind SCWB N selection, and qualify the common-cut storey allocation. Preserve the independent oracle and existing 44 production comparisons.

Exit criterion: one reproducible source-to-modal/eccentric-effect-to-SCWB-to-storey-share-to-alpha-to-rechecked-design-to-sealed-report example. Each evidence improvement must change an actual consumer outcome or close an explicitly necessary input requirement. Do not wait for a generalized 94-node scheduler, a merged offline database, or all wall/slab checks before completing this bounded frame slice.

## Acceptance and worker instructions

The next worker should deliver the smallest verified changes in the order above, not an automatic release or a wholesale rewrite. Production changes should remain attributable to their existing owners. This audit package itself changes no engineering status.

Required acceptance evidence is finite: exact source revision; one normalized Web/CLI scenario; complete expected physical case population; independent arithmetic; existing-owner comparison; saved-source replay where the source is actually available; normal report projection; and explicit live/engineering levels. Every new gate must identify the value or method it needs, its existing producer and consumer, and how a positive supported example can satisfy it.

The project should measure delivered capability by a repeatable user operation and an explainable numerical result. Counts of retrieved forces, receipts, tests and hashes remain supporting evidence. They do not substitute for that operation.

## Source references

All S references below identify the inspected commit. The machine-readable manifest supplies SHA-256 values and the inspected-owner list. Normative PDFs and private model files are not redistributed in this package.

S1. [Pipeline owner](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/pipeline.py): selected cages, stages, scenario dependencies and sealed report evidence.

S2. [R14 closure](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/column_r14_closure.py): required completion and finite-value gates; governing static output.

S3. [Current state](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/docs/CURRENT_STATE.md) and [verification ledger](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/docs/VERIFICATION_LEDGER.json): private worker results and limitations.

S4. [Joint shear adapter](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/column_r10_live.py#L1574): missing rows, 1 kN threshold and deduction envelope.

S5. [Live confinement transfer](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/column_r10_live.py#L1630): source-axis selection.

S6. [Existing offline joint topology owner](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/column_engine/column_joints.py#L176): physical lower member and axis mapping.

S7. [Live upper and lower classification](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/column_r10_live.py#L1498).

S8. [Web selection action](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/web.py#L602).

S9. [CLI scenario preparation](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/cli_adapter.py#L41) and [scenario owner](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/design_scenario.py).

S10. [Standard reporting](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/reporting.py#L2077): R10 and R14 rendering.

S11. [CI workflow](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/.github/workflows/ci.yml) and [observed Actions run](https://github.com/feridunfc/YENI/actions/runs/44556903482).

S12. [R03 setup audit](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/analysis_setup.py#L95) and [local R08](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/column_r08_local_live.py).

S13. [Alpha owner](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/alpha_iteration.py#L52), [native demand evidence](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/demand_sources.py#L519), and R10 lines 564 onward.

S14. [Existing integration recipe](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/docs/engineering/reference/recipe_20261118/delivery/RECIPE.md#L418).

S15. Alpha owner lines 90 and 120 onward; R10 SCWB assembly lines 605 and 634 onward.

S16. [Design group assignment](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/engineering/design_assignments.py) and [project group configuration](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/config/design_combination_groups.json).

S17. Local R08 lines 179 through 220 and 303 through 387; [global story second order](https://github.com/feridunfc/YENI/blob/1697a968dc30e342b83685bec898bda3109643ca/src/tbdy_next/story_second_order.py).

S18. Local R08 `_evaluate_spectral_bounding_corners`, lines 438 through 575.

N1. [TBDY 2018 official publication](https://www.resmigazete.gov.tr/eskiler/2018/03/20180318M1-2-1.pdf). Official PDF available among provided local sources, SHA-256 `8d3a9a463d4a534ec2c6834c557b5f706e2ad976c2d6837f6c9b6242e38a6bb2`. Inspected PDF pages 137, 139 and 146-147, printed pages 116, 118 and 125-126. Clauses 7.3.5.2, 7.3.5.3(b), 7.3.6 and 7.5.2. Fresh official web retrieval timed out; the local primary publication was inspected directly.

N2. [CSI Analysis Reference Manual](https://docs.csiamerica.com/manuals/etabs/Analysis%20Reference.pdf), response-spectrum and correspondence sections. Web source accessed during this audit.

N3. [CSI accidental eccentricity for response spectrum analysis](https://web.wiki.csiamerica.com/wiki/spaces/kb/pages/2001549). Web source accessed during this audit.

N4. [CSI ETABS response spectrum load case help](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Response_Spectrum.htm). Web source accessed during this audit.
