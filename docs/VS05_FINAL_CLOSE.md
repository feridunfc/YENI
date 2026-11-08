# VS05 — bounded source-numerical closure (2026-11-08)

Repository: `feridunfc/YENI`
Branch: `work/vs05-normative-base-shear-drift-20261107`
Accepted starting branch HEAD before final local commit: `b4f6a9ea8ddd0224ab9109ca418f55768850e202`.

## Acceptance scope

This PR **closes the VS05 source-collection / candidate-model / DAG-foundation / STORY_DRIFT *source numerical* vertical slice only**. It does **not** release normative full-building TBDY 2018 compliance.

* Existing 94-node dependency DAG remains a candidate catalog; `STORY_DRIFT.execution_authority=DENIED` is unchanged.
* ETABS 23.2 running session captured `Joint Displacements`, `Story Definitions`, connectivity and `Story Drifts`. A general reusable source gateway is included.
* Real ETABS model: `kompakt_b.EDB`; one-run export `RUN-e4a5376365c649b6b7469b0a778617ff`.
* Spectrum-source drift candidate calculation: **12/16** story/case/direction rows. Missing **four** are all on `+14.5`; no assumed zero or regulatory PASS. Maximum independent-table residual **0.00265 mm** (display precision reconciliation).
* Mode shape: 1044 physical column-mode signed differences, strictly modal-only; **650** non-concurrent RSX/RSY point Max records not differenced.
* The single-click UI, local history, receipt and full JSON/HTML export use the *same* `STORY_DRIFT` record. Main UI layout remains unchanged.
* Windows full regression before closure patch: **341/341 PASS**; final closure runs the full regression again and verifies the same archived run plus HTML output.

## Normative non-acceptance preserved

`STORY_DRIFT.formal_compliance=NOT_PROVEN`, `STORY_DRIFT.dag_execution_authority=DENIED` and overall `ENGINEERING_RELEASE=NOT_READY`. Directional R/I, lambda DD-3/DD-2, qualifying spectral scaling, structural applicability, full physical story/member census, method selection and engineering approval are **next-slice responsibilities**, not silently waived by this source-numeric merge.

The four `+14.5` records are deliberately retained as `MISSING` pending physical-story applicability decisions: a missing source row cannot be inferred to mean a physically absent storey or zero drift.

## Source / check order

`Check chosen → required ETABS data → live table/schema → typed field binding → numerical method → normative gate → UI/report → tests`. Do not reopen generic source discovery or a second DAG design per check.

## Merge policy

Merge the **one** VS05 PR after accepted Windows full regression, archived live run source/receipt/HTML check, clean staged whitelist and green hosted CI. Do not wait for all 94 unrelated checks to become compliant. `main` is not modified until that PR is merged through GitHub.
