# Pipeline audit corrections and the next vertical slice

## Revision and inspection boundary

The reviewed GitHub baseline and work branch both pointed to
`1697a968dc30e342b83685bec898bda3109643ca` (tree
`25d83cd409dcc2cdf147cb2ac37e4924709811ca`). The corrections in this change
were developed on `work/gap-018-spectrum-evidence` from that exact revision.
The [pinned audit](AUDIT_PIPELINE_20261119.md) describes the pre-correction
behavior; it is historical evidence, not a claim that those defects remain in
this change. The final verification entry identifies the tested file manifest,
commands, environment, initial failure and successful rerun.

The user's Windows working tree, uncommitted changes, original 87-column
capture, private paired analyses and C29 calculation file were not available
in this workspace. They are **NOT_INSPECTED / NOT_RUN here**. Their historical
records remain intact. These changes must be integrated normally with any
newer local work; an old ZIP must never replace that working tree.

## Corrections in the existing production owners

| Audit finding | Change | Observable result |
| --- | --- | --- |
| A01: favorable joint-shear deduction omitted small or missing cases | `engineering/column_r10_live.py` retains the assigned ductile/capacity combination population before reading force rows. Zero, sub-kN and boundary values participate. Missing, unsupported or ambiguous cases remain explicit. | A missing case cannot increase the favorable deduction. Incomplete inputs use the explicitly conditional zero-deduction upper bound. |
| A02: lower-column confinement used the same local-axis label | The shared `column_engine/csi_geometry.py` helper maps the target physical direction to the lower column's parallel or antiparallel V2/V3 axis. Existing live and offline adapters use it. | A 90-degree rotation with unequal confinement values selects the correct physical lower-axis requirement. An oblique or unresolved mapping remains explicit. |
| A03: native I/J labels were treated as physical above/below | Joint neighbors are classified from the independently captured endpoint coordinates. Positive deduction requires a unique physical upper and lower column. | Reversing native connectivity does not change which physical column supplies confinement. Missing coordinates or branched topology cannot fall back to I/J labels. |
| A04: Web selection bypassed the CLI scenario contract | `engineering/design_scenario.py::prepare_pipeline_source` is used by Web and CLI. Both preserve original parent bytes, validate lineage and invoke the existing runner and dependencies. | Equivalent requests produce identical prepared source bytes and complete sealed engineering results. Revising a selected scenario creates a sibling from its original source, not a nested or silently rewritten source. |
| A05: normal print reports omitted existing calculation details | `reporting.py` projects the saved governing PMM cut, forces, factors, radial capacity/reserve and joint shear/tie calculations for single-column and all-column runs. | The standard report follows the recorded calculation. Missing legacy details remain unrecorded; no formula, solver or acquisition is called while rendering. |
| A06: integration branch was outside CI filters | `.github/workflows/ci.yml` includes `baseline/local_import` for push and pull-request events. | The logical integration base is covered by the existing Linux/Windows CI workflow. |

### Joint-shear scope and endpoint rules

The old adapter discarded deductions at or below 1 kN. In an independent
synthetic regression, the reinforcement tension term is 1,050 kN, one case
supplies 200 kN, and the other supplies 0.5 kN. The correct reference envelope
is 1,049.5 kN; choosing only the larger deduction gave 850 kN. With the second
case missing, the corrected conditional upper bound is 1,050 kN. The missing
case is retained in the result and the report.

Native object endpoints are established at station zero and the captured I-J
length. The minimum or maximum **received** station is not used as proof of
an endpoint. A missing endpoint, a displaced/offset cut, an ambiguous element
side, a non-static step or an unclassified/spectral combination cannot supply
a favorable deduction. This narrow rule does not approve a physical joint
face, an end offset, an anchorage length or a complete physical cut census.

The zero-deduction result is conditional on the nonnegative-deduction sway
mechanism stated in the recorded result. A passing valid upper bound can be
useful without seeking a more favorable measured deduction. Conversely, an
exceeded upper bound does not, by itself, prove that the actual demand exceeds
capacity. The R14 consumer now preserves that distinction: an unresolved
upper-bound exceedance requires design revision or qualified refinement, while
its numerical exceedance remains visible. A defined roof-boundary demand or a
resolved supported demand that exceeds the limit is not silently cleared.

### Scenario and report behavior

Selection requests share policy validation, dependency checks, candidate
selection, same-run local second order, alpha iteration and result sealing.
Omitting a policy when revising a scenario inherits it; an explicit null
disables it. The existing scenario and parent are verified before either
replay or revision. A corrupted parent or unknown policy field is rejected
before creating a new run. Existing `RUN-*` contents remain immutable.

The report displays object station, analysis element and element station,
combination/step, axial force, source and design moments, amplification
factors, radial capacity and reserve from the recorded governing static row.
Joint details show both sway demands, the deduction basis, expected/missing
cases, topology diagnostics, the physical lower-axis mapping, required and
provided tie area, selected spacing and maximum usable whole-mm spacing.
These are saved values, including zero values; report generation does not
reconstruct absent historical calculations.

## Verification and acceptance boundary

The final execution record is linked from `EV-AUDIT-ADAPTER-FIXES-20261119` in
[the verification ledger](../VERIFICATION_LEDGER.json). It separates baseline
audit reproductions, focused regression tests, the complete offline suite,
installed-wheel tests, and external CI observations. The tested base commit
and exact file manifest identify the dirty tree tested before publication.

New regressions exercise zero/small/boundary deductions, missing expected
cases and endpoint rows, ambiguous native element sides, reversed I/J,
rotated unequal confinement, oblique axes, missing coordinates, branched
topology, unchanged roof behavior, Web/CLI identity, sibling revisions,
corrupt parents, legacy reports, escaping and sealed report projection.
Independent fixture arithmetic is written separately from the production
arithmetic being compared.

No live ETABS acquisition, private original-model replay or engineering
acceptance is claimed for this implementation. The 73 recipe/example
identities, 44 production comparison records and separate 333-record
arithmetic populations keep their existing meanings. New software tests do
not replace or add accepted engineering checks to those populations.

## Why a complete seismic slice still needs implementation

The prior selected-cage static calculation is a real vertical slice: source
vectors reach the same selected section, local magnification, capacity shear
and a worked joint. It must not be dismissed because building-wide release
is still `NOT_READY`. The missing work is the transition from those supported
reference calculations to a qualified building decision.

Three different problems must be solved separately. First, physical faces,
length/restraint/sway/creep and analysis-generation inputs need an explicit,
versioned engineering acceptance path that the existing calculation owners
actually consume. Second, the spectral method needs a qualified production
consumer for SCWB axial demand and story allocation; more matching scalars
alone cannot create that consumer. Third, the slice must expose a useful
design outcome in the normal report, including a reasoned redesign when it
does not meet the requirement. Adding another evidence file is not an
alternative to implementing one of those transitions.

## Next bounded delivery, in order

1. **Complete one interior joint using existing owners.** Use one original
   source generation, bound column and beam cages, physical directions,
   endpoint/face applicability and the full assigned earthquake population.
   Report both sway demands and tie sizing. Keep a valid passing zero bound;
   obtain compatible end shears only where refinement can change the design
   outcome. A failing design produces a concrete cage/geometry revision.
2. **Qualify the governing SCWB axial-demand branch.** Read the existing
   `scwb_kernel`/R10 behavior and the applicable TBDY 7.3.5 conditions. Bind the
   column capacities to the intended governing axial-force rule, cage and
   direction. Do not use an arbitrary force row or a spectrum Max/Min tuple
   as a simultaneous N-M-V vector. Record justified exemptions, including
   applicable roof conditions, without turning unexamined joints into passes.
3. **Complete one entire story-direction population.** Freeze all physical
   columns and relevant joints independently of returned successful rows.
   Compute the denominator and qualifying share at the required compatible
   cuts using the existing story-alpha owner. One passing C29 joint cannot
   establish the story coefficient. Missing members remain in the population.
4. **Consume alpha and repeat the existing design loop.** Apply the qualified
   demand revision once, retain source vectors, reselect or reevaluate the
   same cages, and recompute dependent PMM, capacity shear, joints and story
   allocation. Finish with convergence, a concrete redesign, or a specific
   method/input deficiency. Seal the result and show it in the same report.

For the spectral branch, keep the method order explicit: modal numerical
precision; applied accidental eccentricity; modal and directional combination;
SCWB axial demand; story-shear allocation; alpha iteration. The 138 original/
private generation comparison exceptions and their component scales need a
reviewed error budget. They are not automatically 138 structural failures,
nor does accepting that budget automatically qualify nonlinear PMM, SCWB or
story-alpha use. Component-box corners require their own monotonicity,
convexity/domain and transformation evidence. An exceeded bound can lead to
redesign or a qualified refined method; it must not promise a simultaneous
response-spectrum vector that the source does not provide.

All of this extends the existing `EnginePipelineRunner`, calculation owners,
scenario/dependency contracts and ETABS gateway. No second solver, pipeline,
connection route or report-time calculation is introduced. No stable GAP or
engineering CHECK is closed by this document.
