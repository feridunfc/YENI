# Single pipeline owner — 2026-11-15

Status: working tree only. `COMMIT=HOLD · PUSH=HOLD · MERGE=HOLD`.

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
