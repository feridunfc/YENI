# VS06-B — Physical source / displacement concurrency evidence (bounded)

**Repository**: `feridunfc/YENI`  
**Working branch**: `work/vs06-story-drift-coverage-20261108`  
**Merge**: HOLD for ALL VS06 sub-stages; PR #5 is the single Draft integration PR.

## 1. CHECK → SOURCE → TYPED VARS → DAG → RESULT

- CHECK: the **existing** `STORY_DRIFT` node. No duplicate regulatory check is registered.
- SOURCE: the same original VS05 `vs05_delta_source` sealed by the reusable read-only ETABS source gateway. Table subset is `Story Definitions`, `Column Object Connectivity`, `Point Object Connectivity` and `Joint Displacements`. The prior `Story Drifts` and `Story Max Over Avg Drifts` source remains bound through VS05 replay and the VS06-A ledger.
- TYPED BINDING: exact observed `UniqueName`, `UniquePtI/J`, `Story`, numeric `X/Y/Z` in metres and `Length` in metres. Duplicate object identity, unknown story and malformed geometry fail closed. Unobserved or unresolved connectivity is *not* a non-applicability certificate.
- DAG: `ANALYSIS_BASIS_GATE` / `SEISMIC_DESIGN_BASIS` not independently authorized. `STORY_DRIFT.execution_authority = DENIED`, normative compliance remains `NOT_PROVEN`.
- RESULT: `vs06_physical_source_review` is a new, SHA-fingerprinted, **read-only derived projection** in the same existing complete JSON/HTML export. The verified historical `vs05-story-drift` receipt and the VS06-A ledger are not altered.

## 2. Evidence taxonomy

Each story includes `assigned_columns_observed`, `endpoint_linked_columns_observed`, and one of:
- `COLUMN_CONNECTIVITY_OBSERVED`
- `COLUMN_ASSIGNMENT_WITH_UNRESOLVED_ENDPOINTS`
- `NO_COLUMN_CONNECTIVITY_OBSERVED`

**None of those means full physical building coverage.** Actual slabs/areas/walls, Null frames, meshed nodes, diaphragm assignments and physical role (including the +14.5 m roof boundary) remain to be reconciled. The four missing spectrum drift rows are not zero, and no story with zero observed columns is removed from the denominator.

The result distinguishes:
- **Ritz `Modal` / `Mode`** node displacement source: signed mode shape, not design earthquake interstory drift.
- **RSX/RSY `LinRespSpec` / `Max`** node source: independent response-spectrum maximum, not a same-instant upper/lower displacement pair. Never subtract those records to fabricate signed design drift.
- Unreconciled analysis/physical generation identity: `NOT_PROVEN`.

No independent design earthquake spectrum displacement pairs are produced. `signed_concurrent_spectrum_design_pairs_proven=0`, `analysis_generation_independently_proven=false`, `formal_compliance=NOT_PROVEN`, and `engineering_release=NOT_READY`.

## 3. Verification

```powershell
cd C:\Users\efeya\PycharmProjects\YENI_VS06
git fetch origin
git pull --ff-only origin work/vs06-story-drift-coverage-20261108
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\verify_vs06_archived_report.py --root "C:\Users\efeya\PycharmProjects\YENI_VS04\.receipts" --run-id RUN-e4a5376365c649b6b7469b0a778617ff --expected-slots 16 --expected-missing 4
```

The tool is **read-only**, uses the original archive and does not start ETABS or change existing receipts. GitHub CI is offline on Linux; it cannot independently establish physical completeness or the actual ETABS analysis generation.

## 4. Explicit open items for VS06-C / final merge

1. Full physical model/area/wall/mesh story census, including uppermost `+14.5` story and foundation/base boundary.
2. Source-approved distinct design earthquake roles, DD-2/DD-3 spectra, R, I, κ, λ, actual load case scaling and analysis generation.
3. Physically and mathematically valid reduced interstory drift demand; pure formula kernels alone are insufficient.
4. Authorized DAG CheckInstances with 100% expected/missing accounting; independent normative oracles; one-button UI/JSON/HTML final acceptance.
5. Supervisor review of Windows real-source replay before declaring this source review accepted.

**VS06-B delivers evidence classification, not TBDY compliance. There is no intermediate merge.**
