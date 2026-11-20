# Audit corrections and the next live calculation — 2026-11-20

## Revision and acceptance boundary

This milestone extends `baseline/local_import` at the exact base commit
`f57e6194155b2f9cfc30e3beecf75e0c83a39c16`, on
`work/engine-audit-fixes-20261120`. The base SHA does not identify the modified
working tree. `EV-AUDIT-FIXES-20261120` in the
[verification ledger](../VERIFICATION_LEDGER.json) records the tested-file
manifest, environment, commands and outcomes. The final offline gate passed
**1,522 Python tests and 11 JavaScript test files**; the isolated installed
wheel passed **370 tests**. Wheel and focused tests overlap the full suite and
must not be added to its count. The [execution record](../context/AUDIT_FIXES_VERIFICATION_20261120.json)
pins the exact tested files and preserves the initial fixture failure and its
correction. The enclosing Git commit identifies the distributed revision.

The Windows working tree is `NOT_INSPECTED`. Live ETABS acquisition and replay
of the exact private original 87-column source are **NOT_RUN for this
milestone**. Earlier original-model counts remain historical evidence. Preserve
newer local changes when integrating this work; never replace them with this
remote snapshot.

All changes use the existing `EnginePipelineRunner`, calculation owners,
scenario/dependency contracts, immutable receipts and ETABS gateway. No second
solver, runtime, pipeline or acquisition route is introduced. All 18 stable
GAP identities are retained; none is closed. GAP-017 and GAP-018 remain
`PARTIAL`, and engineering release remains `NOT_READY`.

## Three reproduced defects corrected in their owners

### 1. Minimum eccentricity must precede moment magnification

[`column_r08_local_live.py`](../../src/tbdy_next/engineering/column_r08_local_live.py)
now applies the signed first-order eccentricity floor before local and global
magnification, for signed static demands and the existing spectral-corner
adapter. Raw source moments remain unchanged.

The independent regression uses an 800 × 800 mm section, 12Φ25 bars,
5,000 kN compression, a 3,800 mm reference effective length, K = 1, Rm = 0,
and a global factor of 1. The 39 mm eccentricity gives a 195 kN·m first-order
minimum. The independent stiffness calculation gives
β = 1.030504912300101, so the final magnitude is
**200.9484578985 kN·m**, not the previous **195 kN·m**. Both moment signs and
local axes are tested. The normal report displays the saved raw moment,
first-order floored moment, factors and final moment in that order.

This correction does not approve physical clear length, K, sway, creep,
global-factor applicability or the nonlinear validity of a spectral box.
Spectral corners remain nonconcurrent bounds, not simultaneous force vectors.

### 2. Initial capacity shear must also respect analysis shear

[`column_r10_live.py::_compute_capacity_shear_axes`](../../src/tbdy_next/engineering/column_r10_live.py)
now uses the analysis-shear lower bound in the initial calculation as well as
after an alpha demand revision. With 300 kN·m at each end and a 3 m span,
the unreduced capacity-shear term is 280 kN. An independently specified
analysis shear of 500 kN requires **Ve = 500 kN**, rather than **280 kN**.
Against a 600 kN shear capacity, utilization changes from 0.4667 to 0.8333.

The result retains `ve_unreduced_kn`, `vd_floor_kn`, `vd_floor_basis` and the
native `vd_governing_cut`, including the signed shear, combination, element
side and both stations. An alpha revision changes the demand once; it does
not multiply the end plastic capacities. Missing, ambiguous, nonfinite or
unsupported required force cases cannot become a zero demand or a successful
utilization. Governing axial-demand selection for SCWB versus capacity shear
remains a separate method task.

### 3. Embedded legacy selection policies cannot bypass dependency checks

[`design_scenario.py::prepare_pipeline_source`](../../src/tbdy_next/engineering/design_scenario.py)
normalizes embedded `beam_selection`/`column_selection` policies through the
same preparation contract as explicit requests. Exact native parent bytes
are archived; an existing scenario and its parent remain immutable. A direct
unprepared selection call to `run_source_pipeline` is rejected before
calculation. Runs without a selection policy retain their existing behavior.

The regression removes C1's required 1.5 m middle cut from its configured
0, 1.5 and 3 m population. C1 remains visible with **2/3 cuts**, is
`BLOCKED_DEPENDENCY`, and receives **no selected cage**. Complete C2 remains
eligible and receives a real same-run candidate. The expected four
member–combination pairs are retained. Web and CLI, and embedded versus
explicit policies, produce identical prepared source bytes and sealed
engineering results in the same environment. This is a synthetic production
runner regression, not a replay of the original 87 columns.

## Alpha: useful credit and terminal design outcomes

### Low axial force contributes to Vis without asserting Eq. 7.3

[`scwb_axial.py::alpha_low_axial_credit`](../../src/tbdy_next/engineering/scwb_axial.py)
supplies the optional per-column TBDY 7.3.6.1 credit to the existing signed
alpha consumer. It checks source/dependency identity, exact assigned combined
gravity–earthquake cases, both configured ends and the existing axial owner's
maximum compression over the native cuts. Low end forces cannot conceal a
higher interior maximum. This individual-column credit differs from the
two-column low-axial joint exception.

[`alpha_iteration.py`](../../src/tbdy_next/engineering/alpha_iteration.py)
records three distinct populations: `eligible_member_ids` for the numerator,
`amplification_member_ids` for the demand revision, and
`low_axial_credit_member_ids` for the optional credit. Credit alone does not
assert that both-end Eq. 7.3 is satisfied and does not authorize amplification
of that column.

The three-column consumer example has earthquake shears 60, 20 and 20 kN.
C1 satisfies the two-end criterion; C2 receives the qualified low-N credit;
C3 satisfies neither. Thus Vis/Vik = 80/100 = 0.8 and the factor is 1.25,
but **only C1 is amplified**. C2's native demands remain unchanged. A 900 kN
interior compression invalidates C2's 720 kN low-N limit despite lower end
forces. The tests use actual axial/end-evidence owners and an explicit SCWB
Boolean consumer fixture; they do not prove whole-building capacity or
spectral-alpha qualification.

### Joint panels and ties are part of terminal feasibility

The existing alpha driver now consumes R10 joint results before declaring
`FIXED_POINT_REFERENCE`. It derives the two required ends from dependency
topology, checks the physical `member_joint_ends`, applicable axes, beam-face
census, required seismic combinations, panel demand and physically mapped
tie results. Beamless applicability requires explicit empty topology; no
base, roof or unframed exemption is inferred from missing data.

A missing or incomplete required result is
`NUMERIC_OR_DEPENDENCY_UNRESOLVED`. An exceeded unresolved conservative
zero-deduction bound carries `JOINT_SHEAR_BOUND_REFINEMENT_REQUIRED`; it is
not mislabeled as a proved demand failure. A qualified panel or tie failure
stops with **`JOINT_DESIGN_FAILURE`** and explicit `failure_codes`, without
repeatedly reselecting a column cage that cannot repair the joint geometry.
A valid passing conservative bound is retained. No joint formula is
duplicated in this terminal consumer.
The report combines qualification reasons, feasibility reasons and proved
failure codes, so a concurrent unresolved dependency cannot hide a proved
joint failure.

## Method identity and golden comparisons

The registry exports every declared method version independently of whether
the stage declares `consumes`. Package fingerprinting is retained.

| Stage | Declared method version |
| --- | --- |
| Local second order | `column-r08-local.v6` |
| R10 | `column-r10-low-axial.v2` |
| Alpha feedback | `alpha-feedback.mixed-signed-same-cut.v3` |

The existing global P-delta owner now exposes
[`story_pdelta.py::theta_ii_reference`](../../src/tbdy_next/engineering/story_pdelta.py).
The existing story review and golden adapter call this same scalar owner.
GOLDEN-01 page 28 supplies the two existing records `G01_THETA_GROUND` and
`G01_THETA_UPPER`: **0.007516853605560383** and
**0.005997760967498111**, respectively. Cumulative weight is used once and
reduced average drift is converted from mm to m once. Independent Decimal
arithmetic checks these values; the absolute tolerance of 0.00005 reflects
the source's four-decimal printed precision.

The 44 production comparison records now classify as **20
`NUMERICAL_MATCH`, 20 `INSUFFICIENT_SOURCE`, and 4
`ENGINEERING_INTERPRETATION_DIFFERENCE`**. The two scalar bindings do not
qualify the full story source population, theta limit or global magnification
policy. The remaining labels include adapter and method work as well as
missing inputs; see the [current comparison tasks](../context/PROJECT_CHARTER.md#resume-the-44-report-comparisons-gap-016).
The 73 recipe identities, 44 production comparisons, historical arithmetic
populations of 333, 94 DAG nodes and software-test counts remain separate.

## Reproduce offline, then acquire through the existing live server

Start with `AGENTS.md`, `git status --short --branch` and
`git rev-parse HEAD`. Use the installed environment for the integrated code;
confirm its import path. These PowerShell values are deliberate placeholders
for the user's exact source, recorded modal case and private output root.
Keep the whole archived run, including `parent.source` when present.

```powershell
$YeniPython = ".\.venv\Scripts\python.exe"
$YeniSource = "<absolute path to exact archived input.source>"
$YeniCase = "<exact recorded modal case>"
$YeniOutput = "<private receipt root>"
& $YeniPython -c "import tbdy_next.engineering.pipeline as p; print(p.__file__)"

$YeniFirst = (& $YeniPython -B -m tbdy_next.cli run-pipeline `
  --source $YeniSource --case $YeniCase --out $YeniOutput | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) { throw "First replay failed; retain its diagnostic output." }

$YeniRepeat = (& $YeniPython -B -m tbdy_next.cli run-pipeline `
  --source (Join-Path $YeniFirst.run_dir "input.source") `
  --case $YeniCase --out $YeniOutput `
  --compare-run $YeniFirst.run_dir | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $YeniRepeat.compare.status -ne "IDENTICAL") {
  throw "Same-environment repeat differed; inspect the comparison."
}
```

For a native source without selection, append the existing
`--beam-selection <policy.json>` and `--column-selection <policy.json>`
options to the first command using the intended recorded project policies.
Do not invent a replacement policy or strip a scenario's lineage. Compare
the **new run with a second new run in the same environment**. A comparison
against a pre-fix run is expected to expose method/result changes and must
not be forced to `IDENTICAL`.

When ETABS is available, rediscover its current process ID and start the
existing server in the session that can access it:

```powershell
$YeniEtabsPid = <current ETABS process ID>
& $YeniPython -B -m tbdy_next.cli serve --host 127.0.0.1 `
  --port 8876 --out $YeniOutput --etabs-pid $YeniEtabsPid
```

Use the existing **All Columns** capture and selection actions with the
intended design-combination groups. Confirm source generation, units, exact
case identities, physical cuts and restoration of temporary selections.
This handoff does not authorize new analysis, model changes or saving ETABS.
Use `/api/pipeline`, `/api/export-checks?run_id=<RUN-id>` and
`/report/print?run_id=<RUN-id>` from that server. New finalized reports project
sealed results without rerunning calculations.

Inspect these saved outputs in the standard JSON/print report:

| Result | Required observation |
| --- | --- |
| `design_dependencies` and candidate ledger | Expected members/cases/cuts retained; incomplete member has no cage; complete members continue. |
| `r08_local_slenderness` selected PMM rows | Raw `first_order_m2_knm`/`first_order_m3_knm`, floored `first_order_m2_design_knm`/`first_order_m3_design_knm`, factors and final moments describe the same native cut and cage. |
| `r10_live` capacity-shear cases | `vd_floor_kn`, `vd_governing_cut`, unreduced and final Ve; original and revised demands are distinguishable. |
| `alpha_iteration.final_qualification` | Full story denominator, compatible cases/cuts, low-N credit and amplification memberships are separate. |
| `alpha_iteration.final_feasibility` | Joint-panel/tie results consumed; `reason_codes` or `failure_codes` explain unresolved or completed failure outcomes. |
| `r14_closure` | Blocked or failed dependencies stay visible; numerical results do not imply engineering approval. |

The milestone execution record must retain exact commands, environment,
tested-file hashes, focused test results, full offline and isolated-wheel
results separately. Existing full-suite commands are
`python -B tools/test_offline.py` and
`python -B tools/test_installed_wheel.py <wheel-directory>` after a clean
wheel build. Do not add overlapping focused counts or reuse historical
execution logs as fresh results.

## Next bounded delivery; remaining work is explicit

The historical original-model checkpoint has five of 52 framed two-column
joints outside the low-N exception. Their direction-compatible governing
axial-demand branch under TBDY 7.3.5.2, capacities for both sway signs and
selected cages still require completion. This milestone does not reevaluate
those five joints or close that task.

Then complete one **entire original story and direction** through the
existing pipeline: independently frozen member/joint/cut population,
qualified SCWB decisions, compatible earthquake shears, alpha demand revision
applied once, and recomputed PMM, Ve, panels and ties. The normal sealed report
must end in a supported fixed point, a specific completed design failure or
an identified missing method/input. A single passing C29 roof example is not
that story calculation.

Spectral whole-story qualification and the W05 method work remain open. Keep
the order: modal precision → applied accidental eccentricity → modal and
directional combination → governing SCWB axial demand → story-shear share →
alpha iteration. Component extrema cannot be promoted into simultaneous
N–M–V vectors; corner bounds need their own domain and nonlinear-transformation
proof. The signed-reference low-N increment does not supply that proof.

The next acceptance test is this finite calculation through existing owners
and the existing report, with an independently checked worked example. More
evidence files alone, another runner, or a reduced denominator do not complete
it. Engineering acceptance, physical length/restraint/creep approval and the
broader recipe remain separate unfinished work.
