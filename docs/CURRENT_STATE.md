# Current local checkpoint — 2026-11-18

**The English recipe package has been reconciled with the newer local code and
integrated as a reference asset. The verified software/documentation milestone
is on the local `baseline/local_import`; GitHub is unchanged.** Native numeric
adapters are implemented and verified offline, with live ETABS acceptance pending.
Engineering release remains `NOT_READY`; formal compliance remains `NOT_PROVEN`.
No new engineering CHECK is closed. Live work follows this intake, as the user ordered.

## Identity and preservation

| Item | Checkpoint |
| --- | --- |
| Repository / active integration branch | `feridunfc/YENI` / `baseline/local_import` |
| Integration base (logical main) | `baseline/local_import` |
| Published integration checkpoint | `b255c3030c09c88a17bbec766fc2bb22682ad027` |
| Preserved runtime / local recipe-review base | `250ff1974316070393f3fff9847d941a80dcd47e` |
| Tested dirty-tree base / prior verified modal binding | `a2e26b664d9b2b217e828de2c1df0c3df26068b1` |
| Runtime package SHA at the tested Windows tree | `fd204205682c2d88c404ca4a7420631fc56638ec6fff2e36ce6f29c2f5e1f5e4` |
| Configuration SHA | `244536913d755dc77f372bd72f7a3f1f8ceb6d2f77837e3d73a98ab6d2c946a1` |
| Registered mixed-demand method | `same-source-spectral-components.v5` |
| Raw tested-file manifest | `docs/context/TESTED_FILES_MODAL_NUMERIC_20261118.json` — 410 entries |
| Manifest SHA | `16e69bfae0fc5e1e7fb877cc71b3c710ab1a789f86ae52c19b2ec2504e85c422` |

All 410 tracked file hashes matched before the context, ledger, gap and acceptance
updates. Runtime/test/tool/config bytes were not changed after verification.
The raw manifest identifies this Windows checkout; Git normalizes text line endings.
Resolve the completed local commit with `git rev-parse HEAD`, and context history
with `git log -1 --format=%H -- docs/CURRENT_STATE.md`. A commit does not embed its
own final SHA. Older manifests, private logs and source receipts remain unchanged.

The reviewed software and recipe milestone is fast-forward integrated locally
from `work/spectral-modal-source`; that branch remains as a preserved checkpoint.
Live acceptance stays open and is not implied by a software integration. No GitHub
push, old-main merge, reset or clean was performed. Keep `.idea/`, `build.zip` and the
untracked root handoff-recipe copy out of commits. They are pre-existing user work.
Private `.receipts`, raw captures, EDB, SQLite and source PDFs are not published.
The exported context ZIP and its earlier validation still describe the published
`b255c303…` checkpoint, not this later code. New work branches start from the current
local `baseline/local_import`; integrate reviewed milestones explicitly.

## Completed bounded increment

The existing `frame_force_capture.py` adapter now reads `Results.ModalPeriod` and
`Results.ModalParticipationFactors` during the same selected all-mode transaction
as supporting frame forces. It also reads the requested spectrum cases' default
eccentricity and diaphragm overrides through `LoadCases.ResponseSpectrum`.
`column_axial.py` supplies the existing plan; there is no second attachment route.

The existing `engineering/demand_sources.py` owner validates return shapes/codes,
finite numeric values, independent mode inventories, case identity, display-table
units, cross-API periods, frequency/eigenvalue relationships and mass/stiffness.
Native numbers are retained without display rounding. The declared 32-ULP check
is a numerical consistency budget, not a guarantee of ETABS solution accuracy.
Printed-digit agreement is not a precision bound when trailing zeros are omitted.

Default eccentricity is dimensionless; overrides are absolute lengths in metres.
The API's override identifiers are retained without guessing a story encoding.
Nonempty overrides remain partial until their story identity is bound. Neither
zero nor nonzero definitions establish applied accidental-torsion forces.
Getter failure cannot become a zero-override result. Selection/mode restoration
failures still invalidate the capture through the existing gateway contract.

One `EnginePipelineRunner`, the existing `mixed-demand-components` stage, and the
sealed-result report remain the owners. No force synthesis, modal combination,
new solver, model mutation, analysis run or normative approval was added.

| Evidence executed on this increment | Result | Ledger ID |
| --- | --- | --- |
| Installed ETABS 23 DLL signatures and synthetic source/binding contracts | Signatures match; 25 new tests included in suite totals; live getter execution NOT_RUN | EV-LOCAL-MODAL-NUMERIC-ADAPTER |
| Full Windows offline suite | 1,393 Python tests OK, one OS symlink skip; 10/10 JS files pass | EV-LOCAL-MODAL-NUMERIC-TESTS |
| Clean tracked-file wheel installed in isolation | 227 tests OK | EV-LOCAL-MODAL-NUMERIC-TESTS |
| Same recorded source and repeated CLI run | 16/16 IDENTICAL receipts; existing design artifacts unchanged | EV-LOCAL-MODAL-NUMERIC-REPLAY |
| Sealed JSON/HTML projection through existing HTTP owner | 24 calculation entry points disabled; zero calculation/live calls; projections equal | EV-LOCAL-MODAL-NUMERIC-REPLAY |

Environment: Windows 11, CPython 3.12.10, Node 24.22.1. A first concurrent full run
had two HTTP timeouts and one consequent temporary-directory cleanup error. An
initial separate HTTP report request also timed out. Unchanged code and unchanged
deadlines passed when the full suite and report verification ran sequentially.
Failed attempts remain recorded. Load contention is consistent with this result;
it was not independently proven to be the only cause. No GitHub CI was run.

Private proof: `.receipts/verification/modal-numeric-final-20261118T153106Z/`.
Source acquisition: `RUN-14ac327ed55f46f6b45a74c29030a07f`.
Source SHA: `8b4851511cdcae04734866924bbacb079f9e7903a01d6c7a9b2bd8ebcd32a311`.
Current replay: `RUN-567d448b129c4adebbeb983f433d4577`.
Results SHA: `c172474dc5e3cdab8357a865d38e8ea03c1fd88ebdcfd471b21e06836cffa9f5`.
Repeat: `RUN-746b866854eb482ab63664c5ee05849c`.

The old acquisition contains no newly supported numeric/eccentricity getter payload.
Its v5 replay correctly reports native numeric inputs `NOT_CAPTURED`, **0/100**
unique modal modes, and eccentricity getters `NOT_CAPTURED`, **0/2** spectrum cases.
Previously bound displayed spectrum parameters remain **200/200** case-mode rows.
Do not label those 200 rows as a new successful native-double capture.

## Preserved earlier engineering evidence

- PMM v6 configured required subset: 87 columns / 957 design pairs; 4,422/4,422
  cuts = 2,409 for 73 single-element columns + 2,013 for 14 meshed columns.
- Same acquisition: 22 patterns; 1,131 member-case pairs; 45,024 supporting cut-step
  rows; 100 modes / 40,200 modal force rows.
- Scalar spectral replay: 696 pairs / 3,216 cuts / 38,592 Max/Min comparisons,
  zero outside tolerance. The earlier independent Decimal(80) audit also checked
  45,024 derived values; these are different objects from the supporting source rows.
- Prior selected-case audit: 1,600 exact numeric fields and 200 period matches.
  Its initial unselected table read failed, but the same source already held the
  selected-case rows. That correction is retained in EV-LOCAL-MODAL-PARAMETERS.
- These historical arithmetic/binding audits were not rerun under new labels.
  The current mixed-component artifact and existing design outputs match the prior
  sealed run. Current signed-static PMM retains 1,206 evaluated rows, zero observed
  exceedances. This is not approval of 87 column designs.

## Next task and acceptance

Active task remains `SPECTRAL-MODAL-PRECISION-AND-TORSION-QUALIFICATION`, GAP-018,
then GAP-013 / GAP-016. Next bounded step is live validation of the new getters:

1. Rediscover the ETABS PID and load the current server code. Use the existing
   gateway and current read-only authority; kN/m/C (API 6) on connection is authorized.
2. Capture native numeric results and eccentricity definitions in one new locked-model
   acquisition with verified selection/mode restoration. Never merge these fields
   into an older receipt or a separate model bank.
3. Reconcile every independently expected modal mode and spectrum case. Retain
   missing/error rows and native numbers; inspect real API identities and units.
4. Verify fresh source/report hashes, repeat identity and sealed report projection.
   This accepts only the supported getter/binding scope. Full spectrum amplitude and
   active-damping precision still require separate evidence.
5. Then bind applied torsion contributions and independently verify modal/directional
   aggregation, summing physical story contributions within each mode before modal
   combination. Only after this qualify SCWB governing N, story allocation and alpha
   feedback against a complete independent example.

R14/R15 remain **0 closed / 87 partial**. The current plain replay executes no alpha
iteration; the older explicit scenario's BLOCKED_INPUTS / zero iterations is a
separate observation. R03 profile/load-role/analysis-generation proof, R08 global
P-delta and local second-order ownership, the independent complete cut census,
constructible cages/crossties and normative PMM acceptance remain open. Selected
reinforcement must satisfy `As >= 0.01 Ac`; a template is not an approved cage.
General topological scheduling and complete CheckInstance accounting remain
GAP-005 / GAP-017. Golden production coverage remains 44 records: 15 match,
25 insufficient, four interpretation differences; acceptance is ineligible.

## Completed recipe intake — 2026-11-18

Entry point: [English recipe and local acceptance](engineering/reference/recipe_20261118/README.md).
`YENI_RECIPE_FULL_20261118.zip` SHA:
`6f46177e64a5d0ee8e9b6fc7d7b5ba74e252e2cb547fb3655ad97d6aaf490b1f`.
All 250 payload hashes match. Thirty public text assets are retained unchanged
under `docs/engineering/reference/recipe_20261118/delivery/`; binary renditions,
private PDFs/SQLite and archived code remain private. There is no new production
solver, pipeline stage, runtime import, test modification or dependency.

The worker's `b255c303…` snapshot matched 142 actual Git objects. All 88 referenced
symbol ASTs/signatures are unchanged locally. This is mechanical compatibility,
not a full semantic audit: 44 recipe labels remain partially mapped and 29 unmapped.
That mapping count is separate from the existing 44 production comparisons.

| Fresh intake evidence | Result |
| --- | --- |
| JSON structure/source binding | Five schemas VALID; six negative probes detected |
| Preserved example arithmetic | 333/333 assertions, 73 primary + 12 adapter fixtures |
| Separate synthetic modal-to-alpha chain | 1,294/1,294 assertions |
| Actual local primitive owners | 3/3 values match: 1080 kN, 1620 kN, 24 mm |
| Existing production comparison owner | 44 records remain 15 match / 25 insufficient / four interpretation differences |

The older 13/27/4 stored result differs only in `G02_ALPHA_ground` and
`G02_ALPHA_top`, whose printed Vis/Vik arithmetic is now supplied by the existing
owner. Complete story scope and two-end SCWB binding remain open. Historical
files are not rewritten. The full software tests and pipeline replay above were
not rerun for this reference-only intake. No new live ETABS operation occurred.

Evidence IDs: `EV-RECIPE18-INTAKE`, `EV-RECIPE18-ARITHMETIC`,
`EV-RECIPE18-LOCAL-OWNERS`. Private proof:
`.receipts/verification/recipe-intake-20261118/`; complete extraction:
`.receipts/recipe18/`. The initial long-path extraction was incomplete and retained;
the complete shorter path is the authoritative local extraction.

Adopt the source/cut/combination contracts, shared cage revisions, independent
verification levels and counterexamples as roadmap requirements. The proportional
modal example uses declared capacities; it is not a physical cage or production
building iteration. E-only versus total-M/V alpha amplification remains an
unresolved interpretation. No normative or engineering gate is promoted.

## Operation and handoff

At the earlier runtime-verification observation no ETABS process was visible and
port 8876 refused the connection. Its temporary HTTP test server was closed.
This intake did not recheck or attach to ETABS. Rediscover the PID and server;
do not infer a current live connection from a historical checkpoint.

```powershell
.\.venv\Scripts\python.exe -c "import sys,tbdy_next; print(sys.executable); print(tbdy_next.__file__)"
Get-Process ETABS | Select-Object Id,ProcessName
# Substitute the verified PID.
.\.venv\Scripts\python.exe -m tbdy_next.cli serve --host 127.0.0.1 --port 8876 --out .receipts --etabs-pid <verified-pid>
```

Recorded report: `/report/print?run_id=RUN-567d448b129c4adebbeb983f433d4577`.
Offline HTML: `.receipts/verification/modal-numeric-final-20261118T153106Z/engineering-report.html`.
Continue through `frame_force_capture.py`, `engineering/demand_sources.py`, existing
pipeline/column owners and `tests/test_native_demand_sources.py`. Read the linked
ledger entries and newest PIPELINE_UNIFICATION section before changing code.
