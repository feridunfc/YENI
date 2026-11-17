# Current local checkpoint — 2026-11-17

**Local work reconciled. Engineering release: `NOT_READY`; formal compliance:
`NOT_PROVEN`.** The same-source spectral component replay is verified within its
recorded arithmetic scope. Modal aggregation and complete design acceptance remain open.

## Identity and preservation

| Item | Checkpoint |
| --- | --- |
| Repository / active local branch | `feridunfc/YENI` / `work/spectral-modal-source` |
| Integration base (logical main) | `baseline/local_import` |
| Published starting checkpoint | `b255c3030c09c88a17bbec766fc2bb22682ad027` |
| Preserved implementation commit | `60938da94b770631c6a5c34a545c8863162ac8a4` |
| Base of the previously tested dirty tree | `85e720d18683a71737c1919d32e393c9d903737b` |
| Imported context reference | `8df69d2991338b3668f53a35c43f772a9bc4fa5e`, documentation only; not the parent of this local baseline |
| Package fingerprint at the tested Windows tree | `0c6cab8550af2e036a4368a96ed4c4e40c7921d7ed06952ea3676757ef3b89ea` |
| Configuration fingerprint | `244536913d755dc77f372bd72f7a3f1f8ceb6d2f77837e3d73a98ab6d2c946a1` |
| Registered mixed-demand method | `same-source-spectral-components.v3` |
| Raw tested-file manifest | `docs/context/TESTED_FILES_20261117.json` — 401 entries |

The implementation commit preserves 18 locally changed source/test/document paths.
Only `docs/engineering/PIPELINE_UNIFICATION_20261115.md` differs from the earlier test
manifest; its acceptance prose was updated after tests. Source, test, tool and config
bytes still match. Git normalizes text line endings: exact raw fingerprints are from
the recorded Windows checkout, not a promise of equal raw bytes on every OS.

The published context checkpoint follows the implementation commit. Resolve the actual HEAD with
`git rev-parse HEAD`; resolve context history with
`git log -1 --format=%H -- AGENTS.md docs/CURRENT_STATE.md`.
The exported ZIP manifest records its full published SHA after remote verification.
Do not try to embed a commit's own SHA in a file inside that same commit.

Unrelated pre-existing `.idea/`, `build.zip` and the root handoff-recipe copy were
left untracked. They are not new application work. No reset/clean or main merge.
Private evidence remains under `.receipts`; it is not in Git or the context ZIP.
GitHub publication is a checkpoint, not a synchronization service. The imported
guide's suggested 3–5 sprint cadence is not an automatic push schedule.

## Current local branch policy

The user designated `baseline/local_import` as the new integration base on
2026-11-17. The active `work/spectral-modal-source` branch was created directly from
its published checkpoint `b255c3030c09c88a17bbec766fc2bb22682ad027`.
New scoped work branches start from the current local baseline; reviewed, verified
milestones return to it. Development and commits remain local until GitHub publication
is explicitly requested. The old `main` and audit branches remain historical references.

This branch setup changes guidance and context only; modal-source implementation has
not started on this branch yet. The existing ZIP and
`docs/context/CONTEXT_VALIDATION_20261117.json` remain evidence of the published baseline
checkpoint, not validation of later context edits. See `EV-LOCAL-BRANCH-POLICY` for
this local workflow change. The next engineering task below remains the same.

## Last completed work and evidence

| Verified scope | Result | Ledger ID |
| --- | --- | --- |
| PMM v6 configured required subset | 87 columns / 957 design pairs; 4,422/4,422 cuts = 2,409 single-element + 2,013 meshed; 14 meshed columns included | EV-PMM6, EV-LOCAL-NATIVE |
| Same-acquisition supporting sources | 22 load patterns; 1,131/1,131 member-case pairs; 45,024/45,024 supporting cut-step rows; 100 modes / 40,200 modal rows | EV-LOCAL-NATIVE |
| Primitive case-to-combination replay | 696/696 spectral pairs; 3,216/3,216 cuts; 38,592 scalar Max/Min comparisons; zero outside tolerance | EV-LOCAL-SPECTRAL |
| Independent Decimal(80) calculation | 38,592 native comparisons plus 45,024 recorded derived values; zero outside tolerance | EV-LOCAL-ORACLE |
| Repeat and report projection | 16/16 IDENTICAL receipts; 21 disabled calculation entry points; zero report calculator calls; HTTP JSON/HTML equal sealed projection | EV-LOCAL-REPORT |
| Latest recorded Windows regression | 1,347 Python tests, OK (1 OS symlink skip); 10/10 JS files; 181 clean-wheel tests, OK | EV-LOCAL-TESTS |

The **45,024 supporting source rows** and **45,024 derived oracle values** count
different objects. The equality of their counts is coincidental. The 98 focused
tests are a subset of the regression scope, not additional engineering CHECKs.

Historical D3B: 1,307 Python / 141 wheel on Linux and its three-job CI belong to
`85e720d...`; do not attribute that CI to this local baseline. The memory/branch
operation rechecked hashes and evidence, not the engineering regression or live ETABS.
The current CI push filter does not include `baseline/**`; this checkpoint does
not change that workflow or claim a new GitHub CI run.

Accepted acquisition: `RUN-14ac327ed55f46f6b45a74c29030a07f`.
Source SHA: `8b4851511cdcae04734866924bbacb079f9e7903a01d6c7a9b2bd8ebcd32a311`.
Latest sealed replay: `RUN-357f6e5379d546f99aa3de9fbdd50898`.
Results SHA: `b44579fb7339fb9a9a4799e11e1a98ef832094aa89c8117dd62484b53cd57557`.
Repeat: `RUN-e07b130d13944616834fce19d6ed9e85`.

Private proof directories:

- `.receipts/verification/native-demands-final-20261117T163344Z/`
- `.receipts/verification/same-source-spectral-final-20261117T180150Z/`
- `.receipts/verification/local-context-import-20261117/` (this preservation operation)

Missing private evidence on another machine means NOT_AVAILABLE / NOT_REPLAYED,
not a reason to manufacture a run. Old archive `85129fae...` and the separate native
bank remain separate source namespaces; the new acquisition supersedes their missing
primitive/mode limits only for its own source. Partial earlier captures remain intact.

## Architecture and next engineering task

**Next task: `SPECTRAL-MODAL-SOURCE-QUALIFICATION`**, focusing on GAP-018, then
GAP-013 and GAP-016. No new independent CHECK or parallel pipeline is needed.

One `EnginePipelineRunner` serves Web and CLI. The existing `mixed-demand-components`
stage uses `mixed_demands.py` and the shared `replay_component_envelope` arithmetic
owner. The existing ETABS gateway and force adapter collect supporting sources;
finalized v2 reporting projects immutable results. A general catalog-wide topological
scheduler and full expected-CHECK census are still open (GAP-005 / GAP-017).

1. Inspect the accepted source and existing reader before requesting another capture.
   `Response Spectrum Modal Info` has field metadata but zero captured rows / capture
   error. Its DatabaseTables display-case selection needs investigation through the
   existing gateway. Do not add a second COM attachment route.
2. Bind native modal amplitudes, active per-mode damping and accidental-torsion
   contributions with exact case/mode/cut/axis identity. Restore all temporary filters.
   Recorded RSX/RSY settings are CQC modal / SRSS directional with 5% accidental
   eccentricity; constant case damping alone does not prove active modal damping.
3. Independently verify modal/directional aggregation, including aggregation within
   each mode before combination for story totals. Do not sum unrelated Max values.
4. Only after qualification, define governing SCWB axial demand and story-shear
   allocation, then validate alpha feedback with a complete independent example.

Acceptance for this slice: a frozen expected case/mode/cut denominator; source and
selection lineage; missing/ambiguous/torsion/damping failure paths; independent expected
values and tolerances; sealed result/report agreement; repeat identity. Scalar replay
agreement alone cannot qualify simultaneity or a story-alpha denominator.

Primary files: `src/tbdy_next/engineering/demand_sources.py`, `mixed_demands.py`,
`alpha_iteration.py` (the latter two in the same directory),
`src/tbdy_next/column_engine/spectral_envelope.py`, `basis_probe.py` and
`etabs_source_gateway_windows.py` (the latter two at the package root).
Start with `tests/test_native_demand_sources.py` and
`tests/test_same_source_spectral_replay.py`, then the existing mixed/alpha suites.

## Remaining engineering gates

- R14/R15: **0 closed / 87 partial**. Latest plain replay applied no new design
  scenario and did not execute alpha iteration. The older explicit scenario has
  `BLOCKED_INPUTS` / 0 iterations; these are different observations.
- Full physical-cut census, clear/effective length and normative PMM acceptance
  remain unproven despite the complete configured required subset.
- R03 approved model profile/load roles/design families and analysis generation
  remain open. EDZ/other-case native stiffness labels are not silently equated.
- R08 global P-delta and column/wall averaging, local k/sway/free length/creep and
  second-order ownership need acceptance. Model lock is insufficient.
- Selected As must meet 0.01 Ac; actual model/template, algorithm-selected candidate
  and approved reinforcement remain distinct. Crossties and other detailing are open.
- Golden production subset: 44 records = 15 match / 25 insufficient / 4 interpretation
  difference, acceptance ineligible. The 467-record bank is a different scope.

The latest replay retains 1,206 evaluated signed-static PMM station rows with zero
observed exceedances; that is numerical evidence, not 87 approved column designs.

## Local operation and handoff

Use the existing `.venv` from the repo root. Current user authorization allows
read-only acquisition through the existing ETABS session and kN/m/C on connection.
No live action is needed for this memory checkpoint. A PID/server observation is
volatile: rediscover it and verify `/api/pipeline` after a required server restart.

```powershell
.\.venv\Scripts\python.exe -c "import sys,tbdy_next; print(sys.executable); print(tbdy_next.__file__)"
Get-Process ETABS | Select-Object Id,ProcessName
# Substitute the verified PID; do not reuse an old number by assumption.
.\.venv\Scripts\python.exe -m tbdy_next.cli serve --host 127.0.0.1 --port 8876 --out .receipts --etabs-pid <verified-pid>
```

Latest recorded report: `/report/print?run_id=RUN-357f6e5379d546f99aa3de9fbdd50898`
on the local server. Do not restart it or take over the mouse for a documentation update.
At the next meaningful milestone update this checkpoint and append ledger evidence.
Read the relevant section of `docs/engineering/PIPELINE_UNIFICATION_20261115.md`
for detailed provenance; older sections describe history, not the current source limit.
