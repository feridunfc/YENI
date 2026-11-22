# External audit review evidence

This bundle supports the [22 November cross-review](../EXTERNAL_AUDIT_REVIEW_20261122.md)
of two user-supplied audit documents, initially checked at
`9e486f7a7294e3dc892b836cbb7b7447c9392c28` and then reconciled with the completed
S00/S02 delivery at `1a8fa44364adcc1b4160310344f2100de5fbcf4c`.

| File | Scope |
| --- | --- |
| [REVIEW_EVIDENCE.json](REVIEW_EVIDENCE.json) | Attachment hashes, six independently checked printed sums, published-basis differences, all 49 claimed current Python paths, current registry/DAG counts, all 44 golden IDs/classifications, primary CSI URLs and source hashes |
| [VALIDATION.json](VALIDATION.json) | Document/link/identity checks, unchanged historical ledger records and GAP statuses, changed-path boundary and artifact hashes |
| [LATEST_IMPLEMENTATION_VERIFICATION.json](LATEST_IMPLEMENTATION_VERIFICATION.json) | Latest code/source hashes, 55 focused test identities and results, plus the distinct historical Windows record; includes the overlapping eight-test run without double counting |
| [WORKER_CHECKPOINT.json](WORKER_CHECKPOINT.json) | Evidence-linked completed S00/S02 scopes, one-face S06 progress and the next bounded C104 delivery |

Arithmetic uses Decimal on the supplied strings and does not call production
calculators. The fresh focused runtime call invokes `stage_registry`,
`dag_coverage`, `build_golden_gate` and `golden_gate_summary`; it is not a full test
suite. Review commands normalize environment paths for public documentation;
hashes identify the original private review script/output. The supplied audits
and raw private source captures are not republished here.

The original attachment's 154,770 rows and 77,385 matching Max/Min pairs are
distinct from the later 726 explicitly read Step 1 boundary rows. The later
native ledger and source-preparation implementation provide independent
component loads and signed resultants. This review retains completed S00 and
six-cut S02, while distinguishing code/ledger verification from an unavailable
private native replay. It does not grant full GAP closure or engineering release.

To inspect current golden classification separately, the existing command is:

```text
python -B -m tbdy_next.cli inspect-golden-regression --require-complete
```

Use the checkout's interpreter/import path. The preserved incomplete gate is
expected to return exit 3 with 36/4/4 across 44 records; that command is provided
as a worker entry point, not misreported as this review's executed command.
See the evidence JSON for the focused functions actually invoked. Use the
corrected delivery sequence in the report for S00/S02 work and keep native
calculation evidence distinct from documentation validation.
