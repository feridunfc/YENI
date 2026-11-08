# YENI — Legacy Branch Lineage / Archive Readiness Audit (2026-11-07)

## Verified main / exact ancestry
- main HEAD: `895e6b5b55a2e133b34e199577940ec7cee20837`
- PR #1: head `ba8bd46f2edc7606816400ebc4ed37327c634f24`,
  merge commit `76be74cbf5079994d6dc41cad86e7512409c0612`.
- PR #2: head `ab0434430f10bc36f0e738b594293f54e8308a7c`,
  merge commit `a53f29f65f62b7e15911283aa4e4b6c750d8d0f7`.
- PR #3: head `2632a3f74ca12e721f706bccd6e4d743ab09534a`,
  merge commit `895e6b5b55a2e133b34e199577940ec7cee20837`.

The historical VS01, VS03 and VS04 heads have already been merged
through GitHub PRs. Comparing commit graph alone to main erroneously
shows VS01/VS03 as diverged because GitHub created separate merge
commits and descendants; it does not demonstrate missing product code.

## Content/tree comparison to main

| Branch head | Ahead/behind main | Same blob hashes | Evolved files | Files absent in main |
|---|---:|---:|---:|---:|
| work/modal-mass-v1 (`0a944181`) | 1/21 | 8/15 | 7 | 0 |
| work/vs01-modal-ui-20261107 (`ba8bd46f`) | 9/21 | 20/32 | 12 | 0 |
| work/vs03-material-torsion-20261107 (`ab043443`) | 4/20 | 26/35 | 9 | 0 |
| work/vs04-analysis-source-schema-20261107 (`2632a3f`) | 0/1 | — | — | 0 |
| work/vs05-normative-base-shear-drift-20261107 (`b40be7c`) | 3/0 | — | — | Active, unmerged |

For modal-mass-v1 all 15 historical paths exist in main, including
the original source.py, modal.py, tests and fixtures. Changed paths
are README, tooling/config and later-evolved receipt/CLI files.
A complete semantic equivalence audit of all changed historical
lines was **not** performed; do not call them byte-identical.

For VS01 and VS03, merged PR head SHAs exactly equal retained branch
HEADs, which is definitive lineage for the original branches. Their
file differences arise from later VS02–VS04 changes on main; no source
file from these branch tips is absent in main.

## Supervisor disposition
- **DO NOT RE-MERGE** these three historical branches into main.
- **DO NOT DELETE** them without an explicit cleanup authorization and
  backup/retention policy; they remain useful evidence.
- Do not cherry-pick historical commits solely because `ahead_by>0`.
- Keep VS05 work branch separate; its 3 candidate-kernel/DAG commits
  are not in main, by design.
- Engineering release NOT_READY; normative output NOT_PROVEN.

Sources: GitHub REST PR #1–3, compare main...branch HEAD and full
recursive Git trees retrieved on 2026-11-07.
