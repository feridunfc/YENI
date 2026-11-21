# Audit evidence and worker entry

This bundle supports the [21 November 2026 system audit](../SYSTEM_AUDIT_20261121.md) at implementation `c71a4dda4ab9453f428a38b3ed79931f8e6eeea3`. It is an audit of actual owners, source meaning, reference methods and product scope. It contains **two diagnostic scripts reproducing three findings**; it is not a new C29 run or a full regression suite.

## Contents and provenance

| File | Purpose |
| --- | --- |
| [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) | 26 retained report hashes, four historical constitution text hashes, source limits and primary provenance |
| [REFERENCE_REPOSITORIES.json](REFERENCE_REPOSITORIES.json) | Five pinned branch heads and 15 actually inspected files; full versus partial reading scope |
| [PRIMARY_SOURCES.json](PRIMARY_SOURCES.json) | Official manufacturer, OpenSees and AFAD URLs; edition/retrieval limits are explained in the research appendix |
| [ARCHITECTURE_INVENTORY.json](ARCHITECTURE_INVENTORY.json) | Registry/candidate catalog counts and actual ownership inventory |
| [GAP_EXIT_RECIPES.json](GAP_EXIT_RECIPES.json) | All 18 stable GAPs, inputs, actual owners, independent oracles and closure criteria |
| [WORKER_PLAN.json](WORKER_PLAN.json) | Canonical S00–S15 dependency and acceptance cards; proposed work, not executed work |
| [ENGINEERING_PROBES.json](ENGINEERING_PROBES.json) | Existing-fixture datum/denominator and conditional-balance observations, with production/test hashes |
| [RECEIPT_INDEX_PROBE.json](RECEIPT_INDEX_PROBE.json) | Actual writer and two readers at the 100-receipt boundary |
| [VALIDATION.json](VALIDATION.json) | Documentation, identity and consistency verification; no new full-suite claim |

Public probe JSON normalizes the local package path to a repository-relative path. The original private observation retains the execution-environment path. All numerical observations and source hashes are preserved. Source/manifest hashes establish identity, not engineering acceptance.

## Portable audit diagnostics

Run from a YENI checkout with its Python environment. These commands do not connect to ETABS or mutate production sources. Receipt objects are temporary. Output belongs in the local receipt area.

```powershell
.\.venv\Scripts\python.exe -X utf8 -B docs\supervisor\audit_20261121\reproduce_engineering_findings.py --repo . --output .receipts\audit-20261121\engineering-before.json
.\.venv\Scripts\python.exe -X utf8 -B docs\supervisor\audit_20261121\reproduce_receipt_index.py --repo . --output .receipts\audit-20261121\receipts-before.json
```

```bash
python -B docs/supervisor/audit_20261121/reproduce_engineering_findings.py --repo . --output .receipts/audit-20261121/engineering-before.json
python -B docs/supervisor/audit_20261121/reproduce_receipt_index.py --repo . --output .receipts/audit-20261121/receipts-before.json
```

**Interpret exit status correctly:** the engineering script returns zero when the probes execute; inspect its `defect_reproduced` values. The receipt script returns zero when the documented baseline defect is reproduced and one when behavior differs. A corrected receipt implementation should differ from the recorded baseline; this is not a conventional green-pass regression test. S00 must add proper production regression tests for corrected behavior.

At this baseline the observations are: negative datum rejected and four expected instances lost; complete-data -100 kN imbalance still leaves conditional story inputs available; 100 receipts written and 99 loaded. The imbalance script executes the producer. The downstream fallback in `compare_level` is a separate code-inspection finding, not a whole-pipeline execution. None establishes that the private C29 source experienced the injected defect.

## First implementation tests and native replay

Use `tests/test_engine_r08_story.py`, `tests/test_r08_story_second_order.py`, `tests/test_gravity_story_basis.py` and integration examples in `tests/test_variable_axial_vertical_slice.py` for S00. Keep missing-wall evidence distinct from proven complete-data imbalance. Check the complete receipt-reader census and numeric ordering beyond index 99.

The existing replay CLI is `python -m tbdy_next.cli run-pipeline --source <archived-input.source> --case <exact-modal-case> --out <receipt-root>`, with optional `--design-scenario <source-bound-scenario.json>` and `--compare-run <RUN-directory>`. These are placeholders to replace from actual local receipts, not a runnable command with invented private paths. `--compare-run` expects identical stage payloads; use it only for intended equivalence, and report deliberate corrected differences separately. Source identity and the unchanged original EDB hash remain distinct checks.

Use the [roadmap](../ROADMAP_20261121.md) for S00/S02 parallel work. Only actual completed experiments receive new implementation evidence IDs. A diagnostic script, planned experiment or historical test result must not be recorded as fresh engineering acceptance.
