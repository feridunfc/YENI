# YENI project guidance

## Read this file first

Start every YENI assignment, including a review, revision, audit or delegated
task, with this instruction in the task brief.

> Önce `feridunfc/YENI` reposunun `baseline/local_import` dalındaki kök `AGENTS.md` dosyasını oku. Çalıştığın dalda belirtilen başlangıç sırasını izle, ardından aşağıdaki görevi yap.

This file is the entry point on `baseline/local_import`. Keep lasting project
decisions and the next reproducible step in the GitHub handoff whenever a
milestone is shared. A later worker must be able to recover them from a checkout.

The product is `feridunfc/YENI`; the runtime is `src/tbdy_next`. Communicate with
the user in Turkish. Keep product UI, calculations and new technical documentation
in English. Other repositories, PDFs and `YENI_P0` are references; `YENI_P0` is
strictly read-only. Do not rebuild the project or create a second solver/pipeline.

## Start and resume

At a new session, handoff or context compaction:

1. Read this file and `docs/CURRENT_STATE.md`.
2. Verify the actual repository, branch, HEAD and working changes with
   `git status --short --branch`, `git rev-parse HEAD` and `git diff --stat`.
   HEAD alone does not identify a dirty working tree. Preserve untracked work.
3. Read only the active GAP entries in `docs/ENGINEERING_GAPS.yaml` and their
   evidence IDs in `docs/VERIFICATION_LEDGER.json`. Follow the linked files as needed.
4. Reconcile claims with code and evidence. A remote HEAD, old ZIP or chat summary
   is not automatically newer than local work. Record conflicts; never roll back
   newer work to make a context document appear correct.
5. State the current task, verified boundary and next concrete step, then continue
   within the user's existing authorization. Do not repeatedly ask for authorization
   already provided in the conversation.

For a new local chat or a GitHub worker, read the
[worker handoff](docs/context/WORKER_HANDOFF_20261119.md) and the
[project charter and source guide](docs/context/PROJECT_CHARTER.md).
Use that guide to identify the existing source, its revision and its calculation
owner before searching for inputs. Local machine and account details are in
the ignored `.receipts/handoff/LOCAL_RESOURCES_20261119.md`.
Missing private evidence must be reported as unavailable, not inferred from a hash.

`CURRENT_STATE` is a concise checkpoint, not the full chat. These files are durable
guidance and an evidence index, not a memory service or an engineering approval.
No automatic pre-compaction hook is assumed. Update the checkpoint at meaningful
milestones and before handoff; do not wait until the context is nearly full.

## Preserve evidence and local work

- Local code and local evidence are primary. GitHub is the sharing/backup
  checkpoint. No background or scheduled sync is configured.
- `baseline/local_import` is the active integration base (the project's logical
  main), per the user's 2026-11-17 instruction. Start scoped `work/<scope>` branches
  from the current local baseline. Per the user's 2026-11-19 standing instruction,
  keep baseline current: integrate each completed, reviewed and verified milestone
  locally and synchronize this branch to GitHub when access is available. Verify
  the remote ref after a normal push; report any pending publication explicitly.
  Keep unfinished work on its work branch. A handoff must not leave a completed
  milestone only on an old work branch or describe a pending push as successful.
  The old `main` and audit branches are historical references unless the user changes
  this policy. Do not publish unrelated branches or change the default branch.
- Select files explicitly for commits. Preserve unrelated files. No `git add .`,
  reset/clean, force-push or unsolicited main merge. Use the requested branch.
- Keep stable GAP IDs. Append new verification IDs; retain historical records and
  use explicit supersession. Record exact commands, environment, source/method
  identity, result, limits, private log locations and hashes. Dirty-tree tests need
  a tested-file manifest as well as base HEAD. Never relabel old tests as new runs.
- Do not publish raw EDB/captures, private SQLite/PDF/model reports, `.receipts`,
  `.env`, credentials, `.venv`, IDE settings or build copies. Public summaries may
  contain hashes and aggregate counts. Code backup does not back up private evidence.
- Current user instructions take precedence over imported handoff suggestions.

## One calculation owner and one acquisition route

Physical, Analysis, Design and Result identities remain separate. Web and CLI use
`engineering/pipeline.py::EnginePipelineRunner`. Read the existing owner and tests
before editing; extend them rather than introducing ad hoc scripts or entry points.

| Responsibility | Existing owner under `src/tbdy_next/` |
| --- | --- |
| ETABS attachment and acquisition | `etabs_source_gateway_windows.py`, `live_etabs.py`, `frame_force_capture.py`, `basis_probe.py` |
| Supporting native demand coverage | `engineering/demand_sources.py` |
| Mixed components / shared spectral arithmetic | `engineering/mixed_demands.py`, `column_engine/spectral_envelope.py::replay_component_envelope` |
| PMM / local second order | `column_engine/section_capacity.py`, `column_engine/ts500_column.py` |
| Global P-delta / alpha | `engineering/story_pdelta.py`, `column_engine/story_alpha.py`, `engineering/alpha_iteration.py` |
| Scenario and dependencies | `engineering/design_scenario.py`, `engineering/design_dependencies.py` |
| Immutable source/results and report | `history.py`, `receipts.py`, `engineering/pipeline_snapshot.py`, `reporting.py` |

Finalized v2 reports project sealed results; replay is an explicit separate action.
Keep legacy compatibility separate. Preserve source, model, case/step, physical-cut,
cage and method revisions; changed upstream inputs invalidate dependent results.

Use terminal/API operations without taking over the mouse. Do not invent a new COM
attachment route when the terminal cannot see ETABS; the user-launched server may
have access in another session. Rediscover the PID; never turn a recorded PID into
a permanent default. The user authorized setting kN/m/C (API code 6) on connection;
code 12 is tonf/m/C. Temporary output/pattern/mode selections must be restored and
verified. A restoration failure blocks capture. Respect existing live-read authority;
do not infer authority to run analysis, change design/model data or save the model.

## Engineering boundaries

- Implemented, executed, numerical agreement, normative acceptance and release are
  distinct. CI PASS and low utilization do not imply READY. Cite the applicable
  specification clause, applicability, inputs, units, acceptance criteria and
  independent evidence when closing a check. Do not invent a clause or approval.
- Freeze expected scope independently of successful rows. Missing/BLOCKED cases
  remain in the denominator. NOT_APPLICABLE needs evidence. Do not hide a proven FAIL.
- Use ETABS unique element IDs. Preserve ObjSta/Elm/ElmSta/case/step and element
  side. Story names are identities, not elevations. Apply unit/sign conversion once.
- TEMPLATE, PROPOSED, ALGORITHM_SELECTED_CANDIDATE, engineer-approved and AS_BUILT
  are distinct. Selected column reinforcement must satisfy As >= 0.01 Ac even if
  demand needs less. Crossties, anchorage, cover and spacing need their own checks.
- Spectral Max/Min and interval corners are not simultaneous N-M-V vectors. Do not
  join different models or incompatible case/step/cut extrema. Do not double-apply
  response-spectrum scaling, directional factors or alpha amplification.
- ObjSta/ElmSta, I-J length, physical face and TS500 clear/effective length differ.
  Model lock does not prove analysis generation. Keep global P-delta and local
  second-order ownership separate. Never mutate source vectors or accumulate factors.
- Test counts, CHECK counts, DAG nodes, members and golden fixtures are separate.
  Preserve verified narrow scopes without claiming complete structural acceptance.

## Verification and checkpoint updates

Use the existing local interpreter and confirm its import path. In PowerShell the
usual interpreter is `.\.venv\Scripts\python.exe`; a bare `python` may be a Store stub.
Run relevant positive/negative/boundary checks for code changes. Full offline command:
`python -B tools/test_offline.py`; installed-wheel command:
`python -B tools/test_installed_wheel.py <wheel-directory>` after a clean wheel build.
For context-only updates, validate references, hashes and provenance without claiming
new engineering tests. Use NOT_RUN where appropriate. Independent arithmetic must not
call the production arithmetic it is meant to verify.

At each meaningful checkpoint update: active task, completed scope, changed paths,
decision and reason, exact verification IDs, unresolved gates and next action.
Keep this file stable and short; put changing facts in CURRENT_STATE and the ledger.
