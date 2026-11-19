# Column candidate selection and same-run reference acceptance

The latest verified live source now has 87 algorithm-selected column cages bound
to the existing R10, local R08, PMM and R14 pipeline. All columns use 32Φ16
longitudinal bars and Φ10/90 mm ties, with three crossties (five effective legs)
per local direction. These are recorded design candidates, not approved or
as-built reinforcement. Engineering release remains `NOT_READY`; R14 remains
0 closed / 87 partial, with zero proven normative failures.

## Source, method and selection decision

- Implementation base: `5e1e10c1b9ffd0be777202873f4b428ded19b152`.
- Work branch: `work/column-cage-selection`; logical integration base:
  `baseline/local_import`. This checkpoint is local, not a GitHub publication.
- Parent capture: `RUN-77039b97519e45029e209f0031d72d36`.
- Parent byte SHA: `9e5535ad2fe5749aa897a16023a3f7288062388df65f23013d243bbdb77bf640`.
- Final scenario: `RUN-4c6e8d795ca94411a1cd6d7f7f54c9de`.
- Final source SHA: `3de017a56036769e7436bac7f16363b552224740d75014678c73119fd1cd2171`.
- Final results SHA: `84740c17a28a7b9542ae21e0eee9dabeb51a7e6f8d2b2d7ced20b285f1365b83`.
- Runtime package SHA: `6cf4e08485fdb7b021a91988faca578c6b5cf9045231fa0f7740969cae731e52`.
- Configuration SHA: `244536913d755dc77f372bd72f7a3f1f8ceb6d2f77837e3d73a98ab6d2c946a1`.
- [449-file tested manifest](../context/TESTED_FILES_COLUMN_CANDIDATES_20261119.json),
  SHA `731de054fa8350f60aa9b15ee2b49034f2a734fe61e8ce7281b1ce2022544bd7`.
  It predates the final documentation/metadata updates; executable files were
  checked unchanged afterward. Git text normalization and raw file hashes differ.

The plain parent run had no column selection policy. Its PMM reinforcement was
the recorded ETABS template, which does not bind a selected design cage. The user
explicitly requested longitudinal reinforcement and tie/crosstie selection.

The first explicit scenario used the existing tight-tie profile: 90 mm pitches
and 1%–4% longitudinal bounds. `RUN-0505da6ae4394ceabd4c5a22f8e8ff4c` selected
32Φ16 and Φ8/90 for all 87 columns, but the downstream zero-concrete Ve reference
exceeded unity in 40 columns per direction (maximum 1.238826). That trial is
preserved and is not the final transverse choice. The revised policy starts at
Φ10, permits Φ10/Φ12, and retains both 90 mm pitches and the original bar/ratio
search limits. This is an explicit scenario-policy revision, not an executed
spectral alpha iteration or an unrecorded change to ETABS.

Both scenarios preserve the exact original source bytes in `parent.source`.
No ETABS analysis, model edit or save occurred. The existing server's read-only
session probe observed a locked model at units 6 and PID 11788; that PID is not
a permanent default.

## Acceptance results and limits

| Population or quantity | Final recorded result |
| --- | --- |
| Expected / selected / same-run bound columns | 87 / 87 / 87 |
| Longitudinal candidate | 32Φ16 |
| Required / selected As | 6,400 / 6,433.981755 mm² |
| As / Ac | 1.005309649% |
| Ties, confinement and midspan | Φ10 / 90 mm in both zones |
| Crossties / effective legs per direction | 3 / 5 |
| Selected transverse criteria | 87/87 recorded true; no alerts |
| Both high- and low-axial confinement references | Both satisfied in both directions, 87/87 |
| Magnified selected PMM rows | 1,206/1,206 resolved |
| Maximum magnified reference PMM utilization | 0.422829003 |
| Spectral bounding corners | 25,728 evaluated |
| Maximum spectral bound utilization | 0.646794092 |
| Maximum Ve, TS 500 reference utilization | 0.578317179 |
| Maximum Ve, zero-concrete reference utilization | 0.793069850 |
| Spectral alpha iteration | 0; `BLOCKED_INPUTS` |
| R14 | 0 closed / 87 partial |

TBDY 2018 §7.3.2.1 supplies the existing longitudinal lower-bound criterion;
§7.3.4.1–7.3.4.2 are the existing tie/confinement references. The audit requires
As ≥ 0.01 Ac without a rounding allowance, complete unique-ID coverage, bar/leg
counts, clearance and tied-bar spacing, both confinement references and both
shear references. It does not independently approve the normative branch,
physical confinement lengths, hooks, splices or anchorage. The independent
Decimal audit below verifies area arithmetic, not a complete PMM oracle.

Magnified PMM retains the recorded reference effective-length/creep/sway inputs.
Spectral corners bound independent component extremes; they are not simultaneous
force vectors. Numerical reference acceptance does not close R14 or the GAPs.
The remaining 17 gate codes concern spectral SCWB/alpha demand policy and
feedback, approved model/load roles and analysis generation, complete physical
cut/face/anchorage evidence, and local second-order input approval.

## Existing pipeline and presentation changes

Selection executes through `EnginePipelineRunner`, `design_scenario.py`,
`column_r10_live.py` and `rebar_selection.py`. The same selected cage binds the
local R08/PMM owner and dependency ledger; R14 consumes those recorded results.
No new solver, attachment route, calculation module or parallel pipeline was added.
Calculation algorithms and the scenario registry are unchanged in this increment.

`reporting.py` now projects a candidate schedule from sealed results. It preserves
expected blocked members and distinguishes candidates from the original ETABS
template. A mismatched unique ID cannot display another member's cage or count
as a bound candidate. HTML/JSON and `workspace-source.js` show count, diameter,
As, percentage, minimum area, ties, crossties and selected-cage reference results
for all unique IDs. Workspace tabs 4.2, 4.4, 4.5 and 4.6 use the same saved run.
Formatting changes no stored precision; viewing does not select or recalculate.

## Fresh verification and reproducibility

Private evidence directory:
`.receipts/verification/column-cage-selection-20261118T193312Z/`.
The explicit commands and exits are retained in `request-provenance.json`,
`tie10-run-command.json`, `selection-run.log`, `tie10-run.log`, and their `.exit`
files. Scenario requests preserve their exact parent SHA and policy. Main command:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m tbdy_next.cli run-pipeline --source .receipts/RUN-77039b97519e45029e209f0031d72d36/input.source --case Modal --out .receipts --design-scenario .receipts/verification/column-cage-selection-20261118T193312Z/selection-request-tie10.json
```

Final run verification uses the private `verify_cage_run.py` with the final run ID
and `--require-reference-limits`. `verify_workspace.cjs` executes the actual
workspace projection over that saved schedule. Results:

- 16 receipt hashes/finalization links verified; exact parent bytes preserved.
- 435 independent Decimal(80) area comparisons; zero outside 1e-8 absolute
  arithmetic tolerance, maximum difference 5.524e-13. No production arithmetic
  is called by this oracle. This tolerance does not establish PMM solver accuracy.
- 27 calculation entry points disabled during local report construction;
  zero calls. Actual user server 8876 JSON/HTML/workspace script match the current
  projection. All four workspace tables retain the same 87 unique IDs.
- 30 focused Python tests passed: candidate schedule 6, report export 10,
  reinforcement selection 6, web 8. Commands use `unittest discover -s tests -p`
  with the corresponding `test_column_candidate_schedule.py`,
  `test_report_export.py`, `test_rebar_selection.py` and `test_web.py` patterns.
- 11/11 JavaScript test files passed. Seven first attempts could not start the
  Windows Store Python stub; retries with `.venv/Scripts` first in PATH passed.
  The new view-test harness initially stopped after a loader registration and
  failed; its boundary was corrected and the test passed. Initial logs are retained.
- Environment: Windows 11 build 26200, CPython 3.12.10, Node 24.22.1.
- Full Python suite, installed wheel and CI: **NOT_RUN for this presentation
  increment**. The prior 1,407/241-test modal milestone remains historical evidence.
- No visual browser inspection is claimed; verification covers actual report
  responses and workspace data projection without using the mouse.

Ledger IDs: `EV-COLUMN-CAGE-TIE10`, `EV-COLUMN-CAGE-REPORT-TESTS`.
The next bounded engineering task resumes GAP-018 spectrum amplitude/active
damping/applied torsion qualification, then GAP-013/GAP-016 spectral alpha and
normative closure. Selection alone is not construction approval.
