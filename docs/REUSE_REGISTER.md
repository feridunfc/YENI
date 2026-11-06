# Selective technical reuse register

**All files in this repository are independently named and owned by TBDY Next Engine.**
The old repositories are references, not Python dependencies and not bundled source-code imports.

| New module | Reference (read-only) | Actual reuse | Deliberately not inherited |
| --- | --- | --- | --- |
| `source.py` | TBDY `tbdy_engine/catalogs/table_registry.yaml`, `tbdy_engine/etabs/table_catalog.py` @ `1440df1b9300f75b1e604204438f5cada9ebd247` | Known modal table and ETABS column vocabulary, reimplemented as one bounded validator | Generic global table registry and COM lifecycle |
| `modal.py` | TBDY `tbdy_engine/regulatory/seismic_response.py` @ same SHA | 0.95 ratio and >= rule, independent pure implementation | Legacy `CheckResult`/F0 compiler/registry and blanket PASS authority |
| `receipts.py` | Architecture principles of TBDY F0 | Per-run traceability; new local receipt schema | Legacy provenance DAG, rollout policy machinery |
| `cli.py` | None | Brand-new bounded orchestration | Legacy API and 16-tab UI |

No source file from the private reference repositories is copied into the public repository. Reuse percentages are not guessed: future migrations will record the actual before/after code diff when code is imported.
