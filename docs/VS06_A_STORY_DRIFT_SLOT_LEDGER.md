# VS06-A — STORY_DRIFT evidence-slot accounting (offline / source-numeric)

**Baseline:** `feridunfc/YENI` main `6f157a7eb26184e43c975a8e1f7a770e60d4fe04` (VS05 PR #4 merged).
**Branch:** `work/vs06-story-drift-coverage-20261108`.
**State:** Bounded implementation candidate; engineering acceptance and merge require separate gates.

## Fixed workflow

1. CHECK: existing `STORY_DRIFT` (do not register a second check).
2. SOURCE: *existing* sealed VS05 generic `Joint Displacements`, `Story Definitions`, `Story Drifts`, `Story Max Over Avg Drifts`, points and columns.
3. GATEWAY: keep `tools/etabs_source_gateway_windows.py`; no new COM reader, no ETABS analysis mutation.
4. TYPED BINDING: reuse `story_drift_binding.py` and `story_delta.story_heights`. The verified snapshot and VS05 receipt remain bit-for-bit unchanged.
5. DAG: `STORY_DRIFT` stays a DENIED research candidate, with `ANALYSIS_BASIS_GATE` and `SEISMIC_DESIGN_BASIS` unresolved.
6. OUTPUT: produce a deterministic source-slot accounting projection in **the existing** JSON/HTML report (no extra check or fabricated normative PASS).

## Exact source-slot invariants

- Expected set = observed story labels × RSX/RSY × X/Y (four slots per observed story).
- Every expected slot must be either **OBSERVED_SOURCE_NUMERIC** or **SOURCE_MISSING**.
- No observed/absent overlap, duplicate, invented case/direction, or unaccounted slot.
- Every observed source value is still an ETABS-derived *candidate* (`Story Drifts × h`), not an independently proven design-earthquake displacement.
- Physical applicability of **every** slot = `NOT_PROVEN` until separate approved member/story topology and source authority. Even absence of a physical column from a partial frame census is insufficient to mark a story `NOT_APPLICABLE`.
- Normative status = `NOT_PROVEN`; execution authority = `DENIED`; release = `NOT_READY`.
- Archived VS05 `vs05-story-drift` receipts cannot be rewritten, because complete reports verify their original exact payload. `vs06_story_slot_ledger` is a new **read-only projection after receipt verification**, not a new approved calculation receipt.
- The projection contains SHA-256 computed over its canonical unsigned payload. This is a local integrity fingerprint, **not** third-party source/analysis-generation certification.

## Acceptance tests

Run full regressions:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Dedicated test source: `tests/test_vs06_story_slot_ledger.py`. The synthetic 12/16 fixture retains all four missing `+14.50` RSX/RSY × X/Y slots; no test claims it is the real ETABS model. Negative tests cover checksum tamper, duplicate observed slots, unaccounted missing rows, invented story and unauthorized PASS.

## Remaining gates before VS06-A complete

- Verify against **actual archived** `RUN-e4a5376365c649b6b7469b0a778617ff` under Windows. The private `.receipts` directory is intentionally not committed.
- Independently reconcile the physical `+14.5` story and all relevant columns/area/wall/topology. Do not classify missing slots as `PHYSICAL_NOT_APPLICABLE` without independently verifiable evidence.
- Exercise single-button live ETABS capture and check the JSON/HTML in the actual local environment, retaining selected-case restore.
- Confirm baseline historical receipts remain exportable; classify failures before any merge.
- This milestone alone is **not** the full CheckInstance FCR, authorized regulatory drift, or overall release.

**MERGE:** HOLD until all agreed evidence gates are reviewed. A green GitHub CI is necessary but not sufficient for live engineering acceptance.
