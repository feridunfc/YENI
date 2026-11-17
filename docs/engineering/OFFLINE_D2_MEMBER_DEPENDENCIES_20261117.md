# Offline D2 — member/joint dependencies and revision evidence

Date: 2026-11-17. Base: `4b47511380fbf28d70a2a2a72cc90ccd87c85faa`.
Branch: `audit/pipeline-pmm-v6-20261117`. No live ETABS/COM, new analysis, main merge, or engineering approval.

## Scope

D1 stopped the entire linked design cohort when one mandatory PMM member/combination pair was unresolved.
D2 retains the same pipeline and existing numerical owners, but scopes candidate execution to individual
columns and checks shared physical joints before calling SCWB, joint design, and capacity-shear owners.
It is active for explicit source-bound offline design scenarios. Legacy runs remain immutable; scenario-free
paths have not been migrated to this contract. It is not a second solver or a catalog-wide scheduler.

## Execution contract

1. The existing PMM expected-instance ledger still supplies the complete member/combination denominator.
   Global invalid source/scope or duplicated pair identities block every dependent member. An ordinary
   missing mandatory pair blocks only its own column candidate and local R08 calculation. All expected
   columns/pairs remain in the result; `NOT_PROVEN` is not a physical failure or an exception.
2. Column/beam connectivity is checked against the independently captured frame-assignment census.
   The existing frame-catalog owner supplies adjacency. Missing connectivity is not interpreted as a beamless
   exception. A physically incident column outside a selected subset remains an unavailable joint dependency.
3. Each shared joint requires all incident same-run selected column sections and the selected signed beam-end
   capacities. Missing/released/unresolved inputs block that joint's design consumers. The beam's own independent
   candidate calculation can continue. A missing neighbor does not block a valid column's independent R08.
4. R10 publishes candidate tokens with the scenario input hash and selection/section revision. R08 checks the
   Unique ID, original Section object, source hash, and revision before invoking its owner. A foreign or changed
   candidate cannot silently replace the one used by R10.
5. Story alpha uses the full physical story population, not just successful candidates. An incomplete member or
   joint blocks the applicable story summary. An unresolved or requested-but-unconsumed alpha feedback remains an
   explicit R14 dependency; a reference Ve is never relabeled as a revised design demand.

The initial implementation conservatively blocks both joint directions for a missing incident dependency and
both column capacity-shear axes when an endpoint dependency is unbound. Direction/sign-specific relaxation
requires an explicit subsequent acceptance case. Every run recomputes eligible calculations: no cache reuse.

## Revision contract

`engineering/design_dependencies.py` stores no engineering formulas. It exposes the member/joint plan and
records artifact fingerprints using existing outputs:

`demand -> candidate -> R08; selected beam ends + adjacent candidates -> SCWB -> story alpha -> Ve review -> R14 input`.

`build_revision_evidence` seals payload hashes and exact upstream revision hashes. R14 validates that ledger and
carries its member revision/open dependencies. `compare_revision_evidence(previous, current)` reports changed,
added, and removed artifacts. Tampered upstream pointers, cycles, wrong sources, or candidate revisions changed
after R10 are rejected. This graph is provenance/invalidation evidence, **not** a new execution scheduler or proof
that the alpha iteration has been implemented. `alpha_demand_iteration_implemented=false` is explicit.

The plan and revision evidence are persisted in the existing finalized v2 `engine-results` / `report_evidence`.
Standard report rendering uses those stored outputs. No report-side dependency or engineering recalculation.

## Regression evidence

Environment: Linux, CPython 3.13.5, Node.js 22.16.0. Exact local logs and private model evidence are in the delivery
archive, not in the public source repository.

| Check | Result |
| --- | --- |
| Full existing offline regression | 1,225 Python tests, OK; 10 JavaScript test files, all passed |
| New D2 tests | 22 passed; included in 1,225, not additional engineering checks |
| Isolated installed-wheel suite | 59 tests, OK; includes PMM v6, D1, D2 and existing report integration |
| Real source-bound positive replay | 957 expected pairs; 87 candidates/R08; 180 beam scenarios; 119 bound joint inputs |
| Revision evidence | 811 artifact revisions; engineering release NOT_READY |
| Stored report | 13 calculator/projection entry points disabled; zero calls; R10/R14 match sealed result |

Reproduction:

```bash
python -m pip install -e .
python tools/test_offline.py
python -m unittest discover -s tests -p test_design_member_dependencies.py -v
python -m pip wheel --no-deps --wheel-dir /tmp/yeni-d2-wheel .
python tools/test_installed_wheel.py /tmp/yeni-d2-wheel
python tools/replay_design_scenario.py --bundle /tmp/build.zip \
  --scenario config/scenarios/offline_tight_ties_v1.json --case Modal --out .receipts
```

The private source's SHA-256 remains `85129fae59e4652a66022348f2f130e83f9128b64e814ce769c66b5cb987f71a`.
The positive scenario input SHA-256 is `4a09900abe873a35adab736fe44f2ebb12a951a33e1af2bf62b22529de3d709f`.
These identify the preserved D1 source/policy basis; they do not authorize the model or analysis generation.

## Negative real-source-copy experiment

Only one side of a shared analysis joint was removed from a copy of column 210 / Grav_Ult / analysis element
210-2. The neighboring element's same-position row remained. This is a synthetic negative experiment, not a
claim that the original model has that omission.

- Expected pairs remain **957**, with exactly **one** blocked pair.
- Column 210 candidate and local R08 do not run; **86** other candidates and R08 calculations continue.
- The two affected physical endpoint joints are blocked; their incident columns are 210 and 127.
- Column 127 keeps its independent candidate/R08, but its capacity-shear owner is not called with the missing
  neighbor. **85** independent column Ve-reference owners run. All **180** independent beam scenarios continue.
- The story's full population remains in its dependency accounting. R14 retains all 87 expected members.
- Original source bytes are unchanged, and the report matches the stored R14 result.

The positive source still gives 87 partial/unbound R14 results and zero numerical closures. Source and dependency
qualification are not normative PMM/SCWB/shear acceptance. Known FAIL semantics are retained by the existing R14
owner and are not masked by these additional open gates.

## Explicit remaining work

General catalog-wide topological execution and CheckInstance accounting; complete physical cut census;
source/model/analysis approval; k/sway/creep/free-length inputs; selected cage engineering approval;
spectral demand and SCWB/Ve method; actual alpha demand revision and bounded design convergence;
physical face/anchorage and wider golden-bank integration remain open. The existing 44-record golden command
still reports 15 numerical matches, 25 insufficient-source records, and 4 interpretation differences. This is
not completion of the canonical 467-record SQLite bank.
