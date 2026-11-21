# From source studies to an executable design slice

**YENI implementation and audit report — 21 November 2026**

The existing engine now accepts an explicit, source-bound second-order calculation
basis and uses it in the selected-section calculation. The normal CLI and web
paths run the same source-to-report owners. Public one- and two-story examples
exercise actual reinforcement selection, global and local second order, selected
PMM, capacity shear, joint shear and transverse reinforcement. The two-story
example also evaluates the interior strong-column/weak-beam inequality using the
actual section owners. Their numerical completion remains conditional on the
declared inputs; engineering release remains `NOT_READY`.

## 1. Inspected version and limits

The inspected integration baseline is `baseline/local_import` at full commit
`0f1a809299ed0dbb6e0ecfde77be0642e1771ce3`, tree
`541b457b6814586e15dde3e334799239edb080e3`.
The implementation branch is `work/vertical-slice-adopted-basis-20261121`.
The tested executable files and their SHA-256 values are listed in
[TESTED_FILES.json](vertical_slice_20261121/TESTED_FILES.json). Commands,
environment, fresh results and explicit limitations are in
[VERIFICATION_RESULTS.json](vertical_slice_20261121/VERIFICATION_RESULTS.json).

The audit inspected the published source, tests, retained report bank and public
project records. It did not inspect unpublished Windows changes, the current
private original-building source bytes, C104 remesh files or the original solver
logs. Their results in earlier ledger entries remain attributed historical
results, not new reproductions. Original-building replay and live ETABS
verification for this branch are `NOT_RUN`. No original model, private source,
PDF or receipt directory is published in this delivery.

The baseline is 14 commits beyond the earlier remote implementation
`cc98df6f9f6e768ba34a7f20a5c01725b2d30914`. Those commits include real runtime
development and structural studies. The problem was the incomplete transfer of
those studies into the consuming design path, rather than an absence of work.

## 2. Why end-to-end progress stalled

| Observed implementation problem | Consequence | Change in this branch |
| --- | --- | --- |
| R08 retained fixed reference K, creep and sway inputs while newer restraint studies were attached as references. | A new engineering study could leave the selected PMM calculation unchanged. | A strict adopted basis supplies the actual per-axis inputs before EI, Euler load and magnification. |
| The normal R03/R08 outputs always retained admission gates that R14 treated as unfinished numerical work. | A passing selected-section calculation could never complete the conditional numerical slice. | R14 distinguishes qualified adopted calculation inputs from their still-pending engineering acceptance. Native calculation and coverage failures continue to block. |
| Global design feasibility and per-story SCWB applicability shared a terminal disposition. | An unresolved wall-coupled member could erase an independently resolved applicability result elsewhere. | Applicability is retained at its actual physical scope, while the unresolved member and full-building feasibility remain open. |
| Signed roof/beamless ends were routed to an interior two-sign SCWB requirement. | A complete roof calculation was blocked by a check that did not apply to that end. | The existing physical applicability owner runs before the signed interior branch. Missing interior capacity still blocks. |
| The iteration driver stopped when alpha was not required, even if magnified PMM requested a stronger cage. | A valid design-reselection request could have no consuming execution path. | The existing bounded R10/R08 rebuild accepts an identity demand revision and retains the original force vectors. |
| Native spectral shear exceeding the brittle limit could be grouped with an exceeded conservative moment bound. | A known calculated failure could become a generic unresolved review state. | Native-demand failure has its own witness and survives unrelated incomplete inputs. |
| A nonmatching wall edge could evade the shared-node wall-contact guard. | An isolated-column clear-length result could be returned where a coupled method was needed. | A bounded geometric contact guard withholds that isolated calculation. It does not invent a connection constraint. |
| Ready report quantities lacked adapters to existing arithmetic owners. | The 44-record bank stayed partially unconnected despite available inputs. | Shared production scalars are called directly; the independent reference arithmetic remains separate. |

Two additional integration defects were found during independent review of the
new route. Native `Modal - Ritz` and `Modal - Eigen` names now bind to the `MODAL`
role. An explicit native `P-Delta` or unsupported stiffness setting cannot be
adopted as first order. `Nonlinear Case / None` remains an unresolved initial
condition; an explicit calculation assumption does not turn it into solver-log
proof.

The first product milestone should be a supported standalone-member calculation
with its connected joints. C104/W21/W22 remains necessary coupled-section work,
but it should not be the sole prerequisite for demonstrating that supported
calculation. Full-building stability and force accounting must nevertheless keep
all required wall-coupled members in their populations.

## 3. Actual calculation chain

The entry point is still `engineering.pipeline.EnginePipelineRunner`.
There is no new solver, pipeline runner or ETABS attachment path.

| Step | Existing owner used by the example | Result consumed downstream |
| --- | --- | --- |
| Native definitions, design groups and input basis | `analysis_setup`, `design_scenario`, `design_assignments` | Exact source-bound combination scope and declared calculation assumptions |
| Physical roster and independent cuts | `column_pmm`, `column_clear_length` | Member/case/cut population and model support-face length |
| Beam and column reinforcement selection | `beam_r10_live`, `column_r10_live`, `rebar_selection` | Actual selected cages and connected beam capacities |
| Global second-order precheck | `story_pdelta` and the existing global stage | Direction-specific theta and beta-II candidates |
| Local second order | `column_r08_local_live`, `ts500_column` | Selected EI, Nk, minimum eccentricity and final design moments |
| Selected-section resistance | `section_capacity` | Magnified PMM utilization at each required signed force cut |
| Capacity shear and detailing | `column_r10_live`, `transverse_kernel` | Both-axis shear checks, confinement and crosstie geometry |
| Interior SCWB and panel | `scwb_axial`, `scwb_kernel`, `joint_kernel` | Same-joint column/beam resistance comparisons and panel/tie results |
| Design feedback | `alpha_iteration`, `design_dependencies` | Applicability, required cage recalculation and bounded terminal state |
| Final result and report | `column_r14_closure`, `pipeline_snapshot`, `reporting` | Persisted numerical disposition and unchanged engineering-release boundary |

The integration tests construct explicit native-shaped source tables and signed
force rows. They do not supply preselected cages, section capacities, R08/R10
success dictionaries or manufactured R14 outcomes. Only report opening is
guarded with disabled calculation entry points, to verify that the report reads
the sealed results. These tests are classified `CONTRACT_FIXTURE` and
`GENERATED_OFFLINE_NOT_ETABS`; they do not validate an ETABS analysis or establish
equilibrium and design acceptance of a real building.

### Public one-story example

The source contains one 800 mm square column, two roof beams, a model mat contact,
five signed combinations (`G`, `G+EX`, `G-EX`, `G+EY`, `G-EY`) and three independently
specified native cuts per combination. The selected longitudinal cage is 32Phi16.
The column transverse choice is five-legged Phi10 at 90 mm. The actual force-cut
census contains 15 rows and five member-combination pairs; the model clear length
is 2.50 m. The real global owner evaluates both story directions, and the real
local owner evaluates all 15 magnified selected PMM rows.

With the same source and cage, changing K from 1 to 2 and Rm from 0 to 1 changes
the calculated result. For the selected TS 500 Eq. (7.20) branch, this halves EI and
multiplies effective length by two, so Nk becomes one eighth of its original
value. The integration test checks that independent scaling relation, an increased
PMM utilization, different sealed result identity and unchanged parent bytes.
This is a direct test of input consumption, not an assertion that a new reference
field exists.

### Public two-story example and design trial

The extension contains two columns, four beams, ten member-combination pairs and
30 required signed force-cut rows. At the common interior joint, the lower and
upper column axial demands are 2,500 and 1,500 kN. Actual selected column and beam
resistances contribute to 16 unique combination/axis/rotation SCWB comparisons.
This interior result is not inferred from the separate roof exemption.

The initial column Phi10/90 choice leaves the conservative zero-concrete shear
branch unresolved. An explicit Phi12/70 design trial is recalculated through the
same owners and completes both columns numerically. The native source is
identical between trials. Limits and tolerances are not relaxed. This is an
explicit design-policy revision, not a claim that the engine automatically
optimized tie spacing. The iteration status is `ALTERNATIVE_NOT_REQUIRED`; the
example does not exercise a nontrivial alpha below one.

The separately executed CLI results give the following selected magnified PMM
values. Full-precision numbers and method inputs are in the accompanying JSON
summaries; the table rounds only for reading.

| Public scenario/member | Selected longitudinal cage | Column ties | PMM rows | Maximum utilization |
| --- | --- | --- | --- | --- |
| One story / C1 | 32Phi16 | Phi10/90 | 15/15 | 0.099379 |
| Two stories / C1 | 32Phi16 | Phi12/70 | 15/15 | 0.101117 |
| Two stories / C2 | 32Phi16 | Phi12/70 | 15/15 | 0.090222 |
| Numerical stress / C1 after retry | 34Phi16 | Phi12/70 | 15/15 | 0.988697 |

## 4. Adopted second-order inputs

`engineering.second_order_basis` validates
`tbdy.next.second-order-basis.v1`. It contains no structural formulas. The existing
TS500 owner supplies the arithmetic. The document fixes:

- Exact native-source SHA, source order and decision references.
- Member IDs and the complete expected combination set for each adopted member.
- Per-axis K, Rm, EI method, sway classification, Cm policy and Eq.7.29 length reading.
- Explicit story Nd/Nk aggregates when the sway branch requires them.
- One supported global/local interaction policy.
- `basis_role=ADOPTED_CALCULATION_ASSUMPTIONS` and `engineering_approval=NOT_GRANTED`.

The same current selected cage supplies steel inertia and resistance. Physical
length must come from the existing model-face owner. Output-station span is not
promoted to TS500 free length. Missing TS 500 Eq. (7.20) steel stiffness does not silently
switch the selected method to Eq. (7.21). Unlisted members retain their unresolved or
legacy-reference state; a basis for one member is not an approval for all members.

| Supported policy | Requirements and computation |
| --- | --- |
| `PIPELINE_TBDY_PLUS_LOCAL_NONSWAY` | Both local axes are sway-prevented. The complete existing TBDY global factor is consumed once with the local magnification. |
| `TS500_SWAY_WITH_TBDY_UNITY` | The complete existing TBDY precheck must be acceptable and give unity factors within the explicit machine precision allowance. The declared TS500 maximum/product decision then supplies the local/story factor. |

Unknown or nonunit overlapping global treatments block explicitly. The code does
not invent a product of two independently derived sway amplification factors.
A PMM artifact explicitly marked as already second order is not magnified again
by this first-order route. R03 also rejects a conflicting native stiffness record
for conditional numerical completion.
The adopted story aggregates remain external calculation inputs; this branch
does not independently prove a complete coupled-building critical-load census.

An optional `k_source` can select `FRAME_END_RATIOS` with `alpha_web` or
`alpha_flange_comparison`. Both current end references must be
`FRAME_SECTION_REFERENCE`. The existing effective-length owner recomputes K,
checks the declared value within eight ULP and consumes the computed value.
Manual K requires exact consumption. Mat/wall rotational stiffness is not
inferred from restrained horizontal translation. Measured mat calibration can
be cited as an adopted input only when its source and applicability are checked
locally; a private ledger hash is not that measurement.

## 5. Numerical completion and acceptance remain different

R14 accepts a conditional adopted-basis context only after native-source,
prepared-input, selected-cage, member-basis, combination scope and calculated R08
artifact identities agree. Actual K/Rm/EI inputs and each calculated row must
carry that basis. A changed source, cage, method or unprepared input invalidates
the connection. No broad whitelist removes missing calculations.

The relevant pending source and engineering gates remain in `open_gates` even
when `R14_NUMERICALLY_CLOSED_WITH_OPEN_SOURCE_GATES` is produced. The report shows
the actual K, Rm, physical/effective length, selected EI, Nk, factor policy and
decision references used. Both JSON and print reports project the sealed snapshot.

| Verification level | Meaning in this delivery |
| --- | --- |
| Schema and source-binding consistency | Exercised by positive, stale-input, missing-combination and contradiction tests |
| Independent arithmetic | Selected EI/Nk scaling, scalar report comparisons and existing owner-level oracles; not a new independent whole-building solver |
| Real production-owner comparison | Golden scalar adapters and unmocked normal-pipeline examples |
| Recorded source replay | Public synthetic source replay, web/CLI equality and changed-input difference; current private original source not replayed |
| Live ETABS verification | `NOT_RUN` |
| Engineering acceptance | `NOT_GRANTED`; release `NOT_READY` |

Deleting a required native cut leaves that member-combination pair in the
denominator and prevents numerical completion. A proven native demand failure
is retained beside incomplete neighboring results. A geometric wall-contact
guard continues to withhold an isolated-column method. These are functional
failure paths, not report annotations alone.

## 6. Design feedback and its present boundary

SCWB applicability is evaluated over all required directional ends. A roof,
beamless end, qualified low-N exception or verified interval inequality receives
its actual disposition. A missing interior capacity does not become exempt.
Per-story applicability can remain resolved when another member is infeasible;
full-building design convergence still requires the full required population.

When the alpha alternative is unnecessary but local PMM or capacity shear asks
for a stronger cage, the existing bounded driver invokes the existing R10/R08
rebuild with an empty absolute factor set. Native forces remain unchanged. The
trace records `NATIVE_DEMAND_DESIGN_RESELECTION`, and the final no-alpha state
keeps `feedback_consumed=false`. Cycle, iteration-budget, exhausted-candidate and
joint-design failure states remain explicit.

A separate numerical stress fixture exercises this actual retry through the
normal runner: a declared K=5, Rm=1 scenario with an additional 870 kN m in M3
requires one real reselection from 32Phi16 to 34Phi16. All 15 required PMM rows are
resolved; the final maximum utilization is approximately 0.9886972. The identity
revision applies no alpha factor. This deliberately stressed input does not
validate K=5 for a physical member or represent an ETABS equilibrium solution.
Its purpose is to verify that a real downstream demand changes the selected
cage through the existing owners.

The complete actual-owner alpha-below-one building example is still a separate
acceptance task. Earlier 60/20/20 and two-column driver fixtures contain explicit
SCWB contract inputs and must not be relabelled as that completed example.
The next such example must derive joint resistances, complete story shears,
alpha, revised demands, cages and all downstream checks from one independently
specified source. Scalar spectral Max/Min values must never stand in for a
concurrent signed force vector.

## 7. Report comparison bank

The original 44 IDs, independent expected values and source tolerances are
preserved. The fresh result is 33 numerical matches, seven insufficient-source
or method records, and four engineering-interpretation differences. This adds
13 production comparisons to the inspected baseline's 20 matches. New adapters call existing spectrum, transverse, joint and TS500
owners. Where an existing formula had been inline, it is factored into a shared
scalar called by both the original production consumer and the adapter. The
independent reference does not call that production arithmetic.

The GOLDEN-02 C30 binding records the verified PDF SHA and original PDF page 7
(printed page 5); the private PDF is not distributed. The authoritative fresh
classification is in [golden_comparisons.json](vertical_slice_20261121/golden_comparisons.json).
A rounded scalar match does not qualify the whole domain. In particular the
matched printed local-beta value 1.00 is non-diagnostic for competing
denominator formulas that both clamp to one.

Outstanding work is itemized rather than hidden under a single source label:

| Remaining quantity family | Concrete work |
| --- | --- |
| Historical sway phi and changed-branch quantities | Resolve the report's `1.5 Delta sum(N/L)/V` method against the actual supported production method and complete story inputs; do not invent an equivalent owner. |
| Four adopted second-order report factors | Establish the applicable free/effective length reading and maximum/product rule. Existing agreement with the printed product is not normative agreement. |
| Three-dimensional PMM report gate | Bind full bar coordinates, material and axis policies, concurrent demand, and independent fixed-N/direction resistance. |
| Capacity-shear report gate | Bind the same Ma/Mu, physical clear length, D branch and ordinary-shear floor. Joint shear is a different quantity. |
| GOLDEN-03 and GOLDEN-04 report gates | Complete their report arithmetic and production mapping; a PDF hash alone is insufficient. |

The 73-control recipe map, the 44 registered comparisons, the 333 historical recipe
arithmetic assertions, the DAG nodes, unit tests and source-cut rows remain
separate populations. This delivery does not rerun or reclassify the historical
333 assertions, replace the 44 bank, or add new CHECK IDs.

## 8. Reproduce through the product entry point

Use a normal source checkout with its editable installation. On Windows, use
the project's existing `.venv\\Scripts\\python.exe`; on Linux, use its normal
environment Python. Commands below use `python` for that chosen interpreter.
Run them from the repository root. Use new output directories; the exporter
refuses to overwrite existing example files.

```sh
python -B tools/write_vertical_slice_example.py --out .receipts/public-one --stories 1
python -B -m tbdy_next.cli run-pipeline --source .receipts/public-one/input.source --design-scenario .receipts/public-one/design-scenario.json --case Modal --out .receipts/public-one-runs

python -B tools/write_vertical_slice_example.py --out .receipts/public-two --stories 2
python -B -m tbdy_next.cli run-pipeline --source .receipts/public-two/input.source --design-scenario .receipts/public-two/design-scenario.json --case Modal --out .receipts/public-two-runs

python -B tools/write_vertical_slice_example.py --out .receipts/public-two-trial --stories 2 --tie-diameter-mm 10 --tie-spacing-mm 90
python -B -m tbdy_next.cli run-pipeline --source .receipts/public-two-trial/input.source --design-scenario .receipts/public-two-trial/design-scenario.json --case Modal --out .receipts/public-two-trial-runs
```

The CLI prints the actual new run directory. Repeating the same source and
scenario with `--compare-run <that-RUN-directory>` must return `IDENTICAL`.
The two-story Phi10/90 trial must stay partial. A K/Rm revision must change the
result identity. Serve the chosen receipt root with the existing command:

```sh
python -B -m tbdy_next.cli serve --host 127.0.0.1 --port 8876 --out .receipts/public-two-runs
```

Open `/report/print?run_id=<actual-run-id>` on that server. The report contains
the calculation, selected cages and retained conditions. This server does not
require ETABS for the archived example. No guessed process ID is supplied.

## 9. Apply this to the current original building

1. Integrate this reviewed feature branch into the current local baseline without
   replacing newer unpublished work. Record the full local SHA and dirty files.
2. Use the latest original same-acquisition `input.source`, with its original
   parent when it is already a derived scenario. Keep all required physical
   members, combinations and force cuts in scope.
3. Build an explicit scenario for C29 member225 and member142 from the inspected
   original source. Transfer the chosen source order, axis-specific K, creep/EI
   policy and applicable story sums from their actual local calculations.
   Do not copy the public example's K=1, Rm=0 or standalone-frame assumptions.
4. Run the normal pipeline. Inspect the two C29 segments and their common joint
   in the sealed result: source cut, selected cage, actual magnified demand,
   capacity, governing combination and every remaining condition.
5. If a required live quantity is absent, identify its exact getter/table/field
   and capture it through the existing gateway. Rediscover the current session.
   Analysis, model edits and saving require their corresponding task authority;
   this delivery performed none of those operations.
6. Continue the C104 coupled-section task independently: the W21/W22/C104
   reinforcement and connection detail, the physical section on each side of
   -1.50 m, and coupled second-order demand remain necessary. Do not substitute
   isolated-column Euler magnification or silently drop these 14 members from
   global story sums.

The 138 original-to-private spectral residuals retain their frozen tolerance
and source scope. Their reported small magnitude alone does not authorize a
tolerance change. The original 0/87 R14 result is historical and has not been
recomputed by this branch. The public 1/1 and 2/2 numerical results must not replace
that original-building denominator.

## 10. Milestone rule for subsequent work

Each next task should name one consuming calculation and finish with the same
source-to-result demonstration. For example: “consume the adopted C29 basis in
the normal runner and show its governing PMM, capacity shear and common-joint
results.” A necessary source study finishes when its result is either consumed
or rejected with a concrete numerical reason. New documents, more source hashes
or a larger passing test count are supporting work, not the product milestone.

Keep the 18 GAP identities and historical entries. This implementation closes
specific software defects; it does not automatically close a regulatory check
or grant full-building engineering acceptance.
