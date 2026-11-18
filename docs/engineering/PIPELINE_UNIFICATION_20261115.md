# Single pipeline owner — 2026-11-15

Historical baseline: 2026-11-15. The original working-tree-only status below was superseded by the published D1–D3 audit-branch commits. On 2026-11-17 the local implementation and durable context were preserved on `baseline/local_import`, now the logical integration base. Older verification sections retain their own base commits and file/method hashes. The newest local increment is identified separately below; no GitHub push or old `main` merge was performed.

D3B continuation: [mixed demands, spectral interval evidence and remaining acceptance limits](OFFLINE_D3B_MIXED_DEMANDS_20261117.md). Coverage counts in the historical sections are not engineering completion percentages.

## Native modal numeric adapters — 2026-11-18 local work branch

`same-source-spectral-components.v5` extends the same stage and owners with numeric
modal inputs and eccentricity definitions. `frame_force_capture.py` reads
`Results.ModalPeriod` and `Results.ModalParticipationFactors` within the existing
selected all-mode output transaction. The same `SapModel` also supplies the requested
spectrum cases' default eccentricity and overrides. `column_axial.py` supplies the
existing source plan; `engineering/demand_sources.py` qualifies the recorded inputs.
No second connection, solver, pipeline stage or model/analysis operation is added.

The native result contracts validate field order, counts, native return codes,
finite numeric values, mode/case identity, duplicates and nonpositive modal properties.
Missing modes remain in the independently derived denominator. Cross-API period,
frequency, angular-frequency, eigenvalue and modal stiffness/mass relationships use
a declared **32-ULP numerical consistency budget**. This budget does not establish
solver accuracy. Display-table comparisons validate field units and printed digits;
trimmed trailing zeros prevent treating this as a true source-precision bound.
Native numbers are retained rather than reconstructed from rounded strings.

CSI documents the double-array signatures for
[ModalPeriod](https://docs.csiamerica.com/help-files/etabs-api-2016/html/07dd92be-7f20-d55e-676a-22af467bfa9c.htm)
and [ModalParticipationFactors](https://docs.csiamerica.com/help-files/etabs-api-2016/html/eeed62fb-02ee-ccc7-294e-801669425bf0.htm).
Those public pages describe ETABS 2016. This increment separately inspected the
installed ETABS 23 DLL and verified matching field order/types; it did not execute
those methods against live ETABS. DLL SHA:
`e031587eed3956cde4377d3940a1eeeab4101c7c92b498e2538915b620fb78aa`.

Default eccentricity is a ratio; overwrites are absolute lengths in metres at API
units 6, consistent with CSI's
[overwrite definition](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Patterns/Overwrite_Eccentricities_Form.htm).
The [override getter](https://docs.csiamerica.com/help-files/etabs-api-2016/html/8179bd55-b99e-df62-2723-e94b77a676c5.htm)
does not return a separate story field. Its identifiers and lengths are retained;
nonempty overrides stay partial until story identity is independently bound.
An API error is not an empty override list. Neither zero nor nonzero definitions
qualify applied torsional forces or their decomposition.

The report projects these nested sealed artifacts and their counts/reasons.
Amplitude and active-damping precision, modal force reconstruction, applied torsion,
modal/directional aggregation, SCWB governing N and alpha authority remain unqualified.
Temporary selection/mode restoration failures still invalidate capture.

### Executed evidence and limits

Dirty-tree base: `a2e26b664d9b2b217e828de2c1df0c3df26068b1`, branch
`work/spectral-modal-source`. Package SHA:
`fd204205682c2d88c404ca4a7420631fc56638ec6fff2e36ce6f29c2f5e1f5e4`.
The 410-entry Windows raw-byte manifest is
`docs/context/TESTED_FILES_MODAL_NUMERIC_20261118.json`; all tracked hashes matched
before the documentation update. Configuration SHA remains `244536913d755dc77f372bd72f7a3f1f8ceb6d2f77837e3d73a98ab6d2c946a1`.

| Verification | Actual result |
| --- | --- |
| Synthetic native getter/binding contracts | 25 new tests, included in totals; positive, missing, duplicate, wrong unit/identity, return/restore failures, 32/33-ULP boundary and authority guards |
| `python -B tools/test_offline.py` | 1,393 Python tests OK; one OS symlink skip; 10/10 JavaScript files pass |
| Clean tracked-file wheel / `python -B tools/test_installed_wheel.py <wheel-directory>` | 227 tests OK |
| Existing CLI replay / repeat | 16/16 IDENTICAL receipts |
| Existing report/HTTP owners | 24 calculation entry points disabled; zero calculation/live calls; sealed JSON/HTML projections equal |
| New getters on live ETABS | NOT_RUN |

Windows 11 / CPython 3.12.10 / Node 24.22.1. A first concurrent run had two HTTP
timeouts and a consequent temporary-file cleanup error; the initial HTTP projection
also timed out. The unchanged full suite and report script passed sequentially at
the original deadlines. Both attempts are retained; no production guard or test
deadline was relaxed. No new GitHub CI or push is claimed.

Same accepted source SHA: `8b4851511cdcae04734866924bbacb079f9e7903a01d6c7a9b2bd8ebcd32a311`.
Replay: `RUN-567d448b129c4adebbeb983f433d4577`; result SHA:
`c172474dc5e3cdab8357a865d38e8ea03c1fd88ebdcfd471b21e06836cffa9f5`.
Repeat: `RUN-746b866854eb482ab63664c5ee05849c`.

This old acquisition lacks the new getter fields: numeric inputs are NOT_CAPTURED
at **0/100 unique modal modes**, eccentricity getters at **0/2 cases**. Prior displayed
parameters remain **200/200 case-mode rows**. Existing axial, PMM, column-gate, R14/R15,
local slenderness and mixed-component artifacts equal the prior sealed run. No new
independent force arithmetic was performed. R14/R15 remain 0 closed / 87 partial,
no alpha iteration ran, and release stays `NOT_READY`.

See EV-LOCAL-MODAL-NUMERIC-ADAPTER, EV-LOCAL-MODAL-NUMERIC-TESTS and
EV-LOCAL-MODAL-NUMERIC-REPLAY. Private evidence lives under
`.receipts/verification/modal-numeric-final-20261118T153106Z/`. The next acceptance is
a fresh same-session native getter capture with independent population, restored
selection, correct units/identity, repeat and sealed report proof. Source capture
acceptance will not by itself approve spectral force reconstruction or design.

## Native modal parameter binding — 2026-11-17 local work branch

The existing `engineering/demand_sources.py` owner now binds selected-case modal
parameters into the existing `mixed-demand-components` stage, registered as
`same-source-spectral-components.v4`. The same runner, gateway, stage contracts and
report owner remain in use. This increment adds no solver, acquisition route, stage
or model operation. It reuses the strict native table and numeric contracts from
`diaphragm_linkage.py`, without adopting that older review's fixed case/mode assumptions.

**Source correction:** the earlier statement that `Response Spectrum Modal Info`
had no rows described the initial unselected read only. The unchanged accepted
capture already contains **200 rows** at
`vs04_diaphragm_probe.spectrum_modal_selected_cases`. Its existing temporary selection
and restoration evidence are reused. The failed initial read remains recorded.
This corrects the handoff's source inventory; it does not replace the previous scalar
arithmetic evidence or pretend that a new live capture occurred.

Expected cases come from native combination leaves and case definitions. Expected
modes come from the separate modal period inventory, never successful parameter rows.
Each bound row retains case/modal GUID lineage, local excitation axis, period, active
damping, three accelerations and three amplitudes, native strings and hashes. Missing,
duplicate or unexpected modes remain visible; wrong periods, GUIDs, units, axis data,
nonfinite numbers or unverified restoration block the affected scope. The single-axis
definition branch rejects ambiguous/multicomponent definitions rather than inferring
their decomposition. Variable per-mode damping is supported by the binding contract.

The report shows case-mode coverage, active damping, combination settings and torsion
limits from the sealed artifact. **Bound parameters are not qualified reconstructed
forces.** Display precision is retained and explicitly unqualified for reconstruction.
No spectrum scale is applied here. A defined eccentricity ratio does not establish
applied accidental-torsion contributions; no concurrent force vector or story-alpha
authority is granted. CSI describes modal/directional combination and spectrum scaling
as separate settings in its [response-spectrum case documentation](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Response_Spectrum.htm).

### Acceptance actually executed on this increment

Local branch: `work/spectral-modal-source`; dirty-tree base
`0f9437f9f3624c76690f559ecbf74a1f2343fcd3`. Tested Windows package SHA:
`07cb453700ee00d5b8914290dcd53bd02031ed78de8b7e0e301967cf2fdcf8c0`.
Configuration SHA remains
`244536913d755dc77f372bd72f7a3f1f8ceb6d2f77837e3d73a98ab6d2c946a1`.
The 409-file raw manifest is `docs/context/TESTED_FILES_MODAL_PARAMETERS_20261117.json`;
all 409 matched before this acceptance/context update. Source/test/tool/config bytes
were not changed after the successful tests. Environment: Windows 11, CPython 3.12.10,
Node 24.22.1. Resolve the eventual local checkpoint SHA with `git rev-parse HEAD`.

| Verified scope | Result |
| --- | --- |
| Native selected-case rows | RSX/U1: 100/100; RSY/U2: 100/100; active damping 0.05 |
| Independent source binding audit, no application imports | 1,600 exact native numeric fields; 200 independent period matches; zero mismatches |
| Existing CLI replay and repeat | 16/16 IDENTICAL receipts |
| Sealed report projection | 22 disabled calculation entry points; zero calculation/live calls; HTTP JSON and HTML equal local projection |
| Focused source/pipeline/report suite | 143 tests, OK |
| `python -B tools/test_offline.py` | 1,368 tests, OK; one OS symlink skip; 10/10 JavaScript files passed |
| Clean tracked-file wheel and `python -B tools/test_installed_wheel.py <wheel-directory>` | 202 tests, OK |

The 21 new modal-binding tests are included in those totals; they are not new
engineering CHECKs. Initial sandbox attempts failed on localhost socket permissions.
After permission was granted, unchanged code passed the network-enabled retries.
Both failed and successful logs are retained. No GitHub CI result is claimed.

Replay: `RUN-808308d1a3e54129b9612b5f0920b92a`; result SHA
`e831cd7cd9ee28279b1eefa62a291584bb4ace131f6db32f6cea107489dd1469`.
Source remains `8b4851511cdcae04734866924bbacb079f9e7903a01d6c7a9b2bd8ebcd32a311`.
Repeat: `RUN-57c3e232233f4b80b260b54438b6a28e`.
The prior mixed-component artifact and force-coverage rows are identical. This preserves
the prior 38,592-comparison arithmetic evidence; that independent arithmetic program
was not rerun and relabeled. The new independent audit verifies source binding only.

Private evidence directory:
`.receipts/verification/modal-parameters-final-20261117T185349Z/` contains exact commands,
logs, file hashes, clean wheel, binding audit, repeat and report projection records.
The user's port 8876 server was not running at observation. HTTP validation used a
temporary localhost instance of the existing `web.make_handler`, closed afterward;
no user-server restart or live ETABS acceptance is claimed. An offline HTML report
is retained in that directory. Ledger IDs: `EV-LOCAL-MODAL-PARAMETERS`,
`EV-LOCAL-MODAL-BINDING-AUDIT`, `EV-LOCAL-MODAL-REPORT`, `EV-LOCAL-MODAL-TESTS`.

R14/R15 remains **0 closed / 87 partial**; 1,206 signed-static PMM station evaluations
are unchanged and no alpha iteration ran. Engineering release remains `NOT_READY`.
Next acceptance work is modal precision and applied accidental-torsion lineage, then
independent aggregation within each mode before combination. Only after qualification
can common SCWB axial-demand and story-shear/alpha policies consume those demands.

## Same-source spectral component replay — 2026-11-17 working tree

The existing `mixed-demand-components` stage now reconstructs a direct Linear Add
combination from the **same acquisition's primitive case forces**, and compares all six
components against both recorded Max/Min limits. The bank and live adapters call the
same `column_engine.spectral_envelope.replay_component_envelope` arithmetic owner.
There is no extra solver, COM attachment, analysis run or pipeline entry point.

The registered method is `same-source-spectral-components.v3`. Exact rational case
coefficients form the signed static center and nonnegative spectral radius; 100/30,
response-spectrum scale and strength factors are not applied a second time. N = -P
reverses the axial interval. Every contributing native row retains its case GUID,
full object/analysis-element-side/station/step identity and source-row hash. The existing
unique ULP station matcher is reused. Opposite element sides, ambiguous matches,
unknown steps, missing leaves or changed source/selection contracts block qualification.

The existing scalar source tolerance remains `1e-9 + 1e-12 * max(abs(calculated), abs(native))`
in kN or kN·m. All expected member/combination/cut denominators remain visible. Recorded
arithmetic agreement and upstream scope qualification are separate: a blocked mesh cannot
become a qualified demand just because its scalar arithmetic matches.

The sealed artifact stores unrounded reconstructed centers/radii, compression bounds,
row lineage, comparison hashes, counts and per-unit maximum discrepancies. Failed
comparisons additionally retain their operands and tolerance. Passing comparison operands
are not redundantly repeated at every cut; the captured source is retained in full.
JSON/HTML project this artifact without rerunning the arithmetic. Older captures without
primitive forces remain explicitly observed-only (`NOT_CAPTURED` for primitive replay).

Acceptance requires a real same-source replay, a separate Decimal(80) arithmetic oracle,
failure-path tests, unchanged bank behavior, sealed-report projection, repeat identity,
full offline checks and clean wheel installation. Final verification is recorded below.

This step validates case-to-combination arithmetic. It does not establish modal response
reconstruction, a concurrent six-component force vector, SCWB governing axial selection
or an alpha denominator. The current source has CQC/SRSS case settings with 5% accidental
eccentricity. The original handoff stated that `Response Spectrum Modal Info` had
metadata but no captured rows; this inventory claim is superseded by the selected-case
source correction above. Modal amplitudes/active damping and accidental-torsion
contributions must be qualified before
modal story-shear aggregation can be qualified. Separate constituent maxima cannot be
summed into an assumed concurrent story response. CSI documents the
[modal amplitudes](https://wikicsiamerica.atlassian.net/wiki/spaces/kb/pages/2006323/Response-spectrum%2Banalysis%2BFAQ)
and [aggregate-before-combination rule](https://web.wiki.csiamerica.com/wiki/spaces/kb/pages/2003704/Base%2Breactions%2Bfor%2Bresponse-spectrum%2Banalysis).
R14/R15 and engineering release remain unchanged at `NOT_READY`.

### Same-source replay acceptance

Final replay: `RUN-357f6e5379d546f99aa3de9fbdd50898`. Input is the unchanged live
acquisition `8b4851511cdcae04734866924bbacb079f9e7903a01d6c7a9b2bd8ebcd32a311`;
this work did not run ETABS analysis or acquire another model. The final result SHA-256 is
`b44579fb7339fb9a9a4799e11e1a98ef832094aa89c8117dd62484b53cd57557`.

| Final recorded scope | Result |
| --- | ---: |
| Columns / spectral combinations | 87 / 8 |
| Qualified member–combination pairs | 696/696 |
| Replayed combination-cut pairs | 3,216/3,216 |
| Six components × Max/Min comparisons | 38,592 |
| Outside source arithmetic tolerance | 0 |
| Largest force / moment discrepancy | 1.111e-12 kN / 1.369e-13 kN·m |

An independent evidence-only Python program using `Decimal(80)` reads native definitions,
case rows and combination rows directly, with no `tbdy_next` imports or production arithmetic.
It independently agrees on all 38,592 comparisons. It also checks **45,024** recorded
center/radius/compression-bound values; none exceed tolerance (maximum discrepancy 3.90e-13).
This is independent arithmetic verification, not a complete structural design oracle.

Repeat `RUN-e07b130d13944616834fce19d6ed9e85` uses the same source and method and gives
**16/16 IDENTICAL** receipt payloads. The report opens with **21** calculator/runner entry
points disabled, zero calls; its mixed-demand artifact equals the sealed snapshot.
The user restarted the server and `/api/pipeline` reports `same-source-spectral-components.v3`.
HTTP JSON and HTML exports equal the locally verified report, including the new replay columns.

Evidence directory: `.receipts/verification/same-source-spectral-final-20261117T180150Z/`.
It contains commands, logs, tested file hashes, clean wheel source, the independent oracle,
`independent-decimal.json`, repeat comparison and `report-projection.json`. Environment:
Windows 11 / CPython 3.12.10 / Node 24.22.1. Tested uncommitted working tree is based on
`85e720d18683a71737c1919d32e393c9d903737b`, package fingerprint
`0c6cab8550af2e036a4368a96ed4c4e40c7921d7ed06952ea3676757ef3b89ea`.
Acceptance prose is updated after testing; tested source/test files remain unchanged.

| Verification actually run on this version | Result |
| --- | --- |
| Focused live/bank/component/native-source suite | 98 tests, OK |
| `python -B tools/test_offline.py` | 1,347 tests, OK; 1 skipped (OS disallows symlinks); 10/10 JavaScript test files passed |
| Clean wheel build and `python -B tools/test_installed_wheel.py <wheel-directory>` | 181 tests, OK |
| Evidence-only `independent_decimal.py` | 38,592 native comparisons and 45,024 recorded derived values, zero outside tolerance |
| Existing CLI `run-pipeline --compare-run` | 16/16 IDENTICAL |

The 957 design pairs, 1,206 evaluated signed-static PMM station rows, and 0 observed
signed-static PMM exceedances are retained. No design scenario or alpha iteration was
applied. R14/R15 still has **0 closed / 87 partial**. The next bounded task is capture and
qualification of native modal amplitudes, active damping and accidental-torsion terms,
then independent verification of modal aggregation before SCWB/alpha policy consumes it.

## Native demand source continuation — 2026-11-17 working tree

The existing basis probe now reads the exact `Load Pattern Definitions` table even
when the discovery-table budget would omit it. Its separate native pattern filter is
set to the full pattern catalog and restored, with failed restoration aborting the capture.
The observed ETABS 23 `Name`/`Type` fields and archived `LoadPat`/`DesignType` fields use
one explicit binding in the existing component algebra; conflicting aliases are rejected.
PMM capture uses the same attached
SapModel and `capture_frame_forces` adapter for a separate supporting case selection.
The selected design-combination denominator remains unchanged. Supporting cases come
from the native combination leaves; response-spectrum definitions identify their modal
cases, and the same-capture modal period table supplies the expected mode inventory.

`Results.Setup.SetOptionModeShape(..., True)` requests all modes. Case/combination
output selections and the previous mode range are independently restored and verified,
including failure paths. No analysis, model save, load assignment or design edit is run.
The existing 100,000-row force-capture bound remains enforced. Complete modal arrays may
exceed the old 32 MiB source limit, so capture, replay, scenario parents and report readers
now share the existing history owner's 64 MiB archive limit. Oversize captures fail;
native force rows are not rounded or silently truncated to fit.

The existing `mixed-demand-components` stage records `native_demand_sources` in the
sealed report evidence. Every member/case and every expected modal step is checked
against the existing PMM configured cut ledger, including analysis-element side identity.
A union of mode IDs is insufficient: a missing cut in one mode remains a source gap.
Primitive static rows feed the existing exact mixed-component algebra at the same native
cut and step. No bank from another acquisition is joined and no new solver is introduced.
Primitive response-spectrum cases retain one native scalar `Max` at each cut. This is
distinct from mixed-combination `Max`/`Min` intervals; no missing minimum or concurrent
force vector is manufactured. The registered source method is `native-demand-source-coverage.v2`.

Acceptance for this increment requires load-pattern capture, complete required primitive
and modal cut coverage, verified restoration, unchanged design-combination scope, sealed
report projection and focused/full offline regressions. These are source acceptance criteria;
they do not authorize modal/directional force concurrence, SCWB axial demand selection,
story shear allocation, alpha iteration or a `READY` engineering release.

### Live source acceptance and exact-version verification

The final user-launched server captured `RUN-14ac327ed55f46f6b45a74c29030a07f` through
the existing `POST /api/live-vs04` operation on 2026-11-17. The locked `kompakt_b.EDB`
model, PID 11788 and API units 6 were unchanged before/after. The 22-pattern display
filter, all output case/combination flags and mode range were restored. The native
mode range was `[1, 1, false]` before/after and `[1, 100, true]` during capture.

| Source acceptance scope | Final same-run evidence |
| --- | ---: |
| Native load-pattern definitions | 22/22 |
| Columns / requested native cases | 87 / 13 |
| Required member–case coverage | 1,131/1,131 |
| Static cases / configured cut rows | 10 / 4,020 |
| Primitive RSX and RSY scalar maxima | 804/804 cut rows |
| Modal cases / modes / configured mode-cut rows | 1 / 100 / 40,200/40,200 |
| All required supporting cut-step rows | 45,024/45,024 |
| Design column–combination pairs (unchanged) | 957 |
| 73 single-element columns, required combination cuts | 2,409/2,409 |
| 14 meshed columns, required combination cuts | 2,013/2,013 |

Input SHA-256: `8b4851511cdcae04734866924bbacb079f9e7903a01d6c7a9b2bd8ebcd32a311`.
Results SHA-256: `1cd749cf6f62e774a7a04928d43edcf80634687185f14ef69b8416d5b3b07933`.
The original archive SHA-256 `85129fae59e4652a66022348f2f130e83f9128b64e814ce769c66b5cb987f71a`
was rechecked unchanged. The first acquisition, `RUN-098bf9d688264b569bb6b98b88478423`,
is retained as partial evidence; it exposed the empty pattern filter and the primitive
spectrum Max-only shape and is not represented as a successful final acceptance.

Offline replay `RUN-9cfdc4ce37b3475fab2e057387b37fa0` matched all **16/16** recorded
stage payloads (`IDENTICAL`, same source and method). The complete report opened with
20 calculator/runner entry points disabled: zero calls, and its native-source, mixed-demand
and R14 projections matched the sealed result. The HTTP JSON export matched too.

Final verification used Windows 11, CPython 3.12.10 and Node 24.22.1, on the uncommitted
working tree based on `85e720d18683a71737c1919d32e393c9d903737b`. The tested package
fingerprint is `0ca9fb62e4604d7a17f721cc3bcca88cfe4ce91747140a7f6d290b532c69531a`.
The final logs, command arrays, clean wheel source, file hashes and live/replay evidence
are in `.receipts/verification/native-demands-final-20261117T163344Z/` (local evidence).

| Verification actually run | Result |
| --- | --- |
| Focused native/column/mixed/alpha/R03/basis suite | 133 tests, OK |
| `python -B tools/test_offline.py` | 1,334 tests, OK; 1 skipped; 10/10 JavaScript files passed |
| Clean wheel build and `python -B tools/test_installed_wheel.py <wheel-directory>` | 168 tests, OK |
| `python -B -m tbdy_next.cli run-pipeline --source <live-input> --case Modal --out <replay-dir> --compare-run <live-run>` | 16/16 IDENTICAL |

The focused suite preceded the final registry-version/report wording edits; those edits
were included in the full suite, clean wheel and live replay. No earlier Linux/CI result
is counted as a new run here. Exact tested file hashes are in `tested-files.json`; this
acceptance text was updated afterwards, without changing the tested source or tests.

This live acquisition applies no selected-design scenario or alpha iteration. Signed
static PMM evaluates 1,206/1,206 station rows with zero observed exceedances, while
R14/R15 remains **0 closed, 87 partial/unbound** and engineering release is `NOT_READY`.
The next acceptance requires one shared modal/directional demand method, SCWB axial-demand
selection and story-shear allocation, verified against an independent complete example.
The required-cut subset above is not an independently established census of every possible cut.

CSI API references: [mode selection](https://docs.csiamerica.com/help-files/etabs-api-2016/html/060c0e63-1f87-d64c-f72a-892899bc88df.htm)
and [mode selection readback](https://docs.csiamerica.com/help-files/etabs-api-2016/html/e21463f2-d1c7-c0f6-c414-a651d5390634.htm).
The installed ETABSv1 COM type library also exposes the three mode-range parameters and
the separate load-pattern display getter/setter. Native force fields follow
[CSI FrameForce](https://docs.csiamerica.com/help-files/etabs-api-2016/html/87689f3e-4175-1627-618b-c4ebae5e89b5.htm).

## What was four islands

| Island | Before | Now |
| --- | --- | --- |
| Live web run | 13-stage sequence inline in `web.py` `do_POST` | `engineering/pipeline.py::run_source_pipeline`; `web.py` only calls it |
| Offline column bank | Separate CLI/Web views, no registry | Registered as `OFFLINE_COLUMN_BANK` stage; data is **still not fed by live capture** |
| Archived 127/C88 | Separate gate flow | Registered as `ARCHIVED_RECEIPT_SCENARIO`; uses the same `column_gates` primitives |
| 94-node DAG | Catalog only | Stage registry binds stages to node IDs; IDs are verified; authority stays `DENIED` |

## Entry points (one runner)

* Web: `POST /api/live-vs04` (unchanged contract) and `GET /api/pipeline` (registry + DAG coverage), routed through `EnginePipelineRunner().run(...)`.
* CLI: `tbdy-next pipeline-plan`, `tbdy-next run-pipeline --source <input.source> --case <case> --out <dir> [--compare-run <RUN-dir>]` (also calls `EnginePipelineRunner().run(...)`).

`run-pipeline --compare-run` verifies both run inventories and compares source, method, plan, and result payloads.
`IDENTICAL` requires both runs to have a finalized v2 snapshot. Earlier runs are reported as
`LEGACY_PARTIAL_COMPARISON`. Exit code 3 indicates a non-identical comparison.

## Finalized results and the axial dependency pilot

The runner derives the evidence used by the standard JSON and print reports, including physical story scope,
B1/B2, source controls, design assignments, and member design evidence. It records these with the calculation
outputs in `engine-results`. The opening receipt identifies the snapshot version. The terminal `live-capture`
receipt links the snapshot, and export verifies the archived input, exact stage inventory, and result hashes.
New standard reports and history consume these results without rerunning the checks. Archived runs retain their
legacy compatibility path. The optional drift what-if calculation is an explicit separate scenario.

Column axial compression validates the required geometry, material, analysis setup, and force artifacts before
calling its existing calculation owner. An expected column Unique ID × selected combination ledger is built from
the physical roster and the request/catalog before evaluating forces. Missing results stay `NOT_PROVEN`, and
unavailable dependencies block the calculation and its dependent design stages. Scope and result counts are
separate. This pilot does not establish an independent physical station inventory or authorize a normative release.

The PMM and local second-order stages now declare their input and output schemas in the same registry.
The PMM ledger keeps each expected member–combination pair, including unsigned envelopes and blocked inputs.
For a verified ETABS minimum-station assignment, the signed check requires at least that many distinct object
stations in every signed combination. The full independent analysis cut inventory remains an explicit closure
gate. R10 passes the selected candidate section directly to R08 for the same Unique ID and run.

For PMM requests, the same ETABS session reads the v1 `Objects and Elements - Frames` and
`Frame Assignments - Output Stations` tables through the existing gateway. PMM joins `ObjName` and `Story`
to the physical column roster, and compares the independently bound `ElmName` set with the analysis element
IDs returned by each force combination. A missing or unmapped element blocks the affected signed or spectral
calculation and stays in the recorded scope. The ETABS table includes generated `Shell` elements, whose object
and element names can overlap with `Frame` names. Only the `Frame` namespace is used for the column roster.
The direct station assignment supplies `MinStations` when `StationOpt` is `Min Stations`. Earlier runs can
use the captured frame summary. Exact native cut coordinates and physical applicability at end offsets remain
separate acceptance requirements.

For the verified `Min Stations = 3` branch with zero I offset and a single analysis element whose oriented
end joints match the object, the runner obtains the required reference cuts from `Column Object Connectivity`
and `Frame Assignments - End Length Offsets` before reading force rows. Both CSI station coordinates must
match at the existing machine tolerance. Extra native cuts are retained. A recorded live source on 2026-11-17
(`RUN-4114cc7f3bec4d54a0ff21e0c1fcd468`) provides 73 eligible columns and 2,409 matching required cuts across
the 11 observed combinations. This archive predates analysis joint coordinate capture.

The same source path retains the `Objects and Elements - Joints` table and reads the required joints as
unrounded global coordinates in metres via `PointElm.GetCoordCartesian`. For a meshed vertical column, the PMM
stage requires an unambiguous directed I-to-J chain and the native coordinates of every joint in that chain.
It requires the three configured cuts and both analysis-element cuts at every internal joint in the supported
zero-I-offset branch, with all internal joints strictly inside the modeled active span. Positions use the existing
machine tolerance. If the source cannot establish the joint coordinates or orientation, the configured subset
remains unverified. A missing element-side force row blocks the affected combination even if the object
station is present. The report identifies each cut by object station, analysis element ID and element station.
The full analysis cut census and TS 500 free length approval remain open.

### PMM v6 acceptance evidence · 2026-11-17

The original PMM v6 work reported 20 passing focused controls in the Windows repository virtual environment.
The separate archive replay derived **2,409 of 2,409** matching required cuts for **73** single-element
columns across **11** combinations. Source SHA-256
`52e7bc54173ff25ce1903834a3f5a0ab441a3b98c9d9b0fa1d2effb0a529c230`.
At that baseline the **14** meshed columns still required live coordinate and two-sided cut verification.

The first live All Columns pass covered 87 columns on a locked ETABS 23 model at kN·m·°C (API 6). It
confirmed the 14 directed mesh chains and blocked all 154 meshed column–combination pairs at the cut
coverage gate. The display table carried rounded joint coordinates, and the affected cut residual reached
6.87 µm. Its input SHA-256 was `b3e4a1064173c51fed0143dade62fc655c1b244de10341127899bde0c292be44`.
The native coordinate adapter addresses that source precision gap at the existing station tolerance.

After the adapter change, the following commands ran in Windows 11 build 26200, Python 3.12.10 from
the YENI virtual environment, and Node.js 24.22.1. They exercised PMM `column-pmm.v6` with the
native joint-coordinate source.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'tests'
.\.venv\Scripts\python.exe -m unittest test_audit_hardening.PmmAnalysisMeshContracts test_audit_hardening.SpectrumPopulationContracts test_r08_local_live.R08LocalUnitTests test_etabs_source_gateway.GatewayTests.test_pmm_reads_mesh_and_station_assignments_through_one_connected_model
.\.venv\Scripts\python.exe -m unittest test_etabs_source_gateway.GatewayTests.test_pmm_reads_unrounded_native_coordinates_only_for_meshed_columns
node --check src/tbdy_next/static/workspace-source.js
```

The first invocation passed **20/20** focused controls. The native coordinate adapter regression
passed **1/1**. The JavaScript syntax check exited zero. These checks ran on the working tree with
native coordinates and the machine-tolerance verticality check.

The archived 73-column coverage count was also recomputed against these sources and again returned
**2,409/2,409**. The standard CLI replay of the recorded single-column request produced 16 stage receipts
and rendered the report. The archive and generated receipts are local evidence and are excluded from Git.

```powershell
$archive = '.receipts/RUN-4114cc7f3bec4d54a0ff21e0c1fcd468/input.source'
$replay = Join-Path ([IO.Path]::GetTempPath()) ('yeni-v6-replay-' + [Guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m tbdy_next.cli run-pipeline --source $archive --case Modal --out $replay
```

### Same-source live mesh acceptance · 2026-11-17

The standard `POST /api/live-vs04` operation used `case=Modal`, `check=column-pmm`, `member=ALL`,
`combination_source=ASSIGNED_DESIGN` and the same 11 combinations and graph hash as the archive.
On the locked ETABS 23 model in API units 6, run `RUN-ed5b6588e770423282450e08018f818c`
captured exactly **100/100** required native analysis joint coordinates without API errors. The recorded
input SHA-256 is `85129fae59e4652a66022348f2f130e83f9128b64e814ce769c66b5cb987f71a`.

The initial result bound 12 meshed columns. For the two remaining columns, four generated joints had a
transverse coordinate difference of one floating-point ULP (4.44 × 10⁻¹⁶ m). The verticality check now
uses the existing machine tolerance for the horizontal coordinates. The force-station match tolerance
stays at 64 ULP capped at 10⁻⁹ m.

```powershell
$live = '.receipts/RUN-ed5b6588e770423282450e08018f818c/input.source'
.\.venv\Scripts\python.exe -m tbdy_next.cli run-pipeline --source $live --case Modal --out .receipts
```

The replay `RUN-5f870820872545a6bac7492becab9032` has the same input SHA-256 and 16 stage receipts.
It uses that one live acquisition for both coordinates and forces.

| Scope | Column–combination pairs | Matched required cuts |
| --- | ---: | ---: |
| 14 meshed columns | 154/154 | 2,013/2,013 |
| Meshed columns · signed static combinations | 42/42 | 549/549 |
| Meshed columns · scalar envelopes | 112/112 | 1,464/1,464 |
| 73 single-element columns | 803/803 | 2,409/2,409 |

Both adjoining cuts at all **72** internal joints matched across the 11 combinations. Scalar envelope
rows establish station coverage. The signed PMM computations cover the three signed static combinations.
Engineering release remains `NOT_READY`. The independent census of every possible cut remains open.

Column longitudinal selection uses the greater of the TBDY area floor, `0.01 Ac`, and any stricter project
policy floor. It accepts equality and selects the least steel area among candidates satisfying the supported
geometry, demand and detailing checks. The report lists the recorded ETABS template and the selected design
candidate separately.

## Column gates & R10 projection on the live path

`engineering/column_live_gates.py::project_column_gates` and `engineering/column_r10_live.py::project_column_r10_live`
are pure deterministic projections over the already replayed live receipts (`geometry_capture`,
`vs05_delta_source` / `vs06_b1_geometry_source`, `column_axial`, `column_pmm`). They own no formulas
(`ts500_column`, `column_gates`, `joint_kernel`, `scwb_kernel`, `transverse_kernel`, `joint_moment_signs`,
`csi_geometry`). New runs persist their outputs in `engine-results`. Existing `RUN-*` directories are immutable.

* CHK-005 (TS500 Eq. 7.7, `0.90 fcd Ac`): proven FAIL when exceeded.
* CHK-004 (TBDY 7.3.1.2, `0.40 fck Ac`): proven FAIL only for combinations the user placed in the `ductile` design
  group; otherwise reported as a reference ratio with `SEISMIC_COMBINATION_ROLE_UNASSIGNED`.
* Reinforcement: `IsDesigned=Yes` is a `TEMPLATE` (`SELECTED_CAGE_MISSING`, `would_fail_if_selected` when
  ρ < 1 %); `IsDesigned=No` below TBDY 7.3.2.1 limits is a proven FAIL.
* Live `AxisAngle`: read from `FRAME_ASSIGNMENTS.AxisAngle`; global moment projections `Mx`/`My` are computed and
  `LOCAL_AXIS_ANGLE_NOT_CAPTURED_LIVE` is cleared only when captured (`90.0°` on Column `127/C88`).
* R10 Live (`column-r10`): joint enclosure & `bw >= 0.75*b` width check + centered `TBDY 7.5` shear limits (`174` column
  ends, `20` narrow-beam ends on `RUN-0a20b4b2...`), SCWB `ΣMrc` references (`BEAM_CAPACITY_NOT_BOUND` until actual/selected
  beam reinforcement is bound), and column confinement Eq. 7.1 & TS500 8.1 shear references (`NOT_PROVEN`).
* Never emits PASS/READY: `canonical_design_pass_allowed` is always `false`.

## Coverage (honest)

30 of 94 nodes are bound to a registered stage (SOURCE_GATE 8/16, DERIVATION 6/10, REGULATORY_CHECK 7/32,
DESIGN_CHECK 9/36). Bindings record implementation coverage. Engineering release remains `NOT_READY`.

## Not done

* Live R10 optional beam/offset/release COM capture (`capture_r10_sources`) is wired as best-effort during `pmm_member`
  capture, but selected/actual beam reinforcement still requires an explicit engineering binding before SCWB can resolve.
* Offline column bank (legacy HDF5 / scenario bank) remains separate from live ETABS captures.
* The axial pilot validates and enforces typed input dependencies. The remaining stages retain their existing
  execution order. Catalog-wide topological scheduling and the general CheckInstance ledger are still open.
* `live_etabs.py` still leaves the model on kN·m·°C after capture (Handoff §5).
* Root-level sprint-named modules (`vs05_*`, `r04_*` …) are not yet moved into subpackages.
