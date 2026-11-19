# Current local checkpoint — 2026-11-19

**87 column reinforcement candidates are selected and bound to the same pipeline run.**
Final candidate: **32Φ16 + Φ10/90 mm ties, three crossties per local direction**.
Selected As 6,433.98 mm² ≥ 6,400 mm² (1.0053%). The final reference checks pass,
but R14 remains **0 closed / 87 partial**, formal compliance `NOT_PROVEN`,
engineering release `NOT_READY`. No user input or server restart is pending.

## Repository and source identity

- Logical integration base: `baseline/local_import`.
- Verified work branch: `work/column-cage-selection`, based on local baseline
  `5e1e10c1b9ffd0be777202873f4b428ded19b152`. Integrate the reviewed milestone locally;
  resolve the final commit with `git rev-parse HEAD` and inspect working changes.
- Published GitHub baseline remains `a9d053f3422d981e3c576fe5e4c0d4b72549d150`.
  The modal-identity and candidate-schedule increments are local; no new push.
- Original live source: `RUN-77039b97519e45029e209f0031d72d36`, SHA
  `9e5535ad2fe5749aa897a16023a3f7288062388df65f23013d243bbdb77bf640`.
- Final selection run: `RUN-4c6e8d795ca94411a1cd6d7f7f54c9de`, derived-source SHA
  `3de017a56036769e7436bac7f16363b552224740d75014678c73119fd1cd2171`.
- Final result SHA: `84740c17a28a7b9542ae21e0eee9dabeb51a7e6f8d2b2d7ced20b285f1365b83`.
- Runtime package SHA: `6cf4e08485fdb7b021a91988faca578c6b5cf9045231fa0f7740969cae731e52`.
- [449-file tested manifest](context/TESTED_FILES_COLUMN_CANDIDATES_20261119.json),
  SHA `731de054fa8350f60aa9b15ee2b49034f2a734fe61e8ce7281b1ce2022544bd7`.
  Final documentation and metadata edits are outside its executable test scope.
  Executable files were rechecked unchanged. Raw Windows hashes differ from Git
  text normalization; preserve the exact LF manifest.

Preserve unrelated `.idea/`, `build.zip` and the root handoff-recipe copy.
Keep `.receipts`, model captures, SQLite/PDFs, credentials and environments private.
`YENI_P0` stays read-only. No reset/clean, old-main merge or force-push.

## Completed selection and product work

[Detailed acceptance and commands](engineering/COLUMN_CAGE_SELECTION_ACCEPTANCE_20261119.md).
The plain live-source run had no selection policy. The requested scenario uses
existing `EnginePipelineRunner`, scenario/dependency owners, R10 selection and
same-cage local R08/PMM, then sealed R14/report outputs. No second solver or
attachment route was added. Calculation algorithms are unchanged.

The initial Φ8/90 trial `RUN-0505da6ae4394ceabd4c5a22f8e8ff4c` is retained. Forty
columns per direction exceeded the zero-concrete Ve reference (maximum 1.2388).
It was not adopted as the final transverse choice. The final explicit policy
allows ties 10/12 mm, keeps 90 mm confinement/midspan pitches and 1%–4%
longitudinal bounds, and preserves the exact original bytes in `parent.source`.
No ETABS analysis, model edit or save occurred.

| Final reference evidence | Result |
| --- | --- |
| Expected / selected / same-run bound columns | 87 / 87 / 87 |
| Transverse, both confinement and both shear references | All recorded criteria satisfied |
| Magnified selected PMM | 1,206/1,206 rows; max utilization 0.422829 |
| Spectral bounding corners | 25,728; max bound utilization 0.646794 |
| Ve TS 500 / zero-concrete reference maxima | 0.578317 / 0.793070 |
| Independent Decimal(80) area comparisons | 435; zero outside 1e-8; max difference 5.524e-13 |
| Source/receipt integrity | 16 receipts; original bytes preserved |
| Spectral alpha iteration | 0; BLOCKED_INPUTS |

`reporting.py` adds a projection of the saved candidate schedule, preserving
blocked members and unique-ID binding. `workspace-source.js` shows selected bars,
As, percentage, minimum As, ties and crossties across all IDs in tabs 4.2, 4.4,
4.5 and 4.6. Original ETABS template gates are explicitly labelled separately.
The data remains full precision; only display precision is reduced.

The user restarted server 8876. Its JSON, HTML and workspace script match the
final projection. All four tables contain the same 87 unique IDs. During local
report verification 27 calculation entry points were disabled; zero were called.
No mouse/browser takeover or visual inspection was performed. The existing
server's session probe observed PID 11788, locked model, units 6; rediscover the
session before future reads rather than making that PID permanent.

Fresh tests: **30 focused Python tests / 11 JavaScript files passed**. Initial
Node Python-path and view-harness failures are retained with successful retries.
Full Python suite, installed wheel and CI are **NOT_RUN for this presentation
increment**. Do not relabel the prior modal milestone's 1,407 Python / 241 wheel
results as newly run. Environment: Windows 11 build 26200, Python 3.12.10,
Node 24.22.1.

Private proof: `.receipts/verification/column-cage-selection-20261118T193312Z/`.
Ledger IDs: `EV-COLUMN-CAGE-TIE10`, `EV-COLUMN-CAGE-REPORT-TESTS`.

## Remaining engineering boundary and next task

The candidates are not engineer-approved or as-built. Hooks, splices, anchorage,
physical confinement lengths and complete physical-cut scope remain open.
Magnified PMM uses recorded reference clear/effective-length, sway and creep
assumptions; low utilization does not approve those inputs. Spectral corners
are independent bounds, not simultaneous force vectors. Both Ve/confinement
reference branches passing does not approve their normative applicability.

The final R14 retains 17 gate codes: R03 approved model/load roles and analysis
generation; physical joint faces/cuts/anchorage; local R08 effective-length,
sway, creep and analysis-order approval; spectral SCWB/story-alpha policy and
alpha feedback. No engineering CHECK or stable GAP is newly CLOSED.

Next bounded task resumes `SPECTRAL-MODAL-PRECISION-AND-TORSION-QUALIFICATION`,
GAP-018, then GAP-013 / GAP-016. Acquire unrounded spectrum amplitude and active
damping/applied-torsion evidence through the existing gateway; preserve expected
case/mode/direction/cut scope. Independently verify modal/directional aggregation
and story allocation before qualifying spectral alpha. General scheduler and
complete CheckInstance accounting remain GAP-005 / GAP-017.

## Earlier verified work and recipe

[Native modal acceptance](engineering/LIVE_MODAL_IDENTITY_ACCEPTANCE_20261118.md):
100/100 native numeric modes, 2/2 eccentricity definitions, 500 independent
numeric relationships, 16/16 identical repeat receipts, 1,407 Python / 10 JS /
241 wheel tests. This earlier scope is preserved. Eccentricity definitions do not
prove applied torsion or active damping. The existing registered method remains
`same-source-spectral-components.v6`.

Historical PMM v6 configured-cut proof remains 2,409 cuts for 73 single-element
columns plus 2,013 for 14 meshed columns, including both sides at 72 internal
joints. Do not convert a configured subset into a complete physical census.

[English recipe entry point](engineering/reference/recipe_20261118/README.md).
Published recipe/v5 source assets remain at a9d053f…; their evidence and the
73-control map are reference coverage, not 73 accepted production checks.
The old exported context ZIP describes b255c303… and is superseded by current
Git documents and ledger. No automatic GitHub sync is configured.
