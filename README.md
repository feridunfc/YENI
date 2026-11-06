# TBDY Next Engine — fresh owned implementation

A new, small, independently maintained structural engineering product. The old **TBDY**, **Column-Engine** and **R1-C** repositories are reference material, **not runtime dependencies**. New names and boundaries are based on what this product actually executes.

## First vertical slice

1. Read a real ETABS 23.2.0 *readonly preflight* JSON; identify the modal table key. **Discovery is not schema verification.**
2. Import a complete `Modal Participating Mass Ratios` table in `tbdy.next.modal.capture.v1` JSON format.
3. Validate columns, row count, selected case, mode order, and cumulative mass fractions.
4. Evaluate **only** the TBDY 2018 4.8.1.2 numerical mass-ratio subcondition (>=95%).
5. Save immutable stage receipts under a local output directory; no engineering release is claimed.

## Run

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m tbdy_next.cli inspect-preflight --input path/to/etabs_readonly_preflight.json --out .receipts
python -m tbdy_next.cli check-modal --input tests/fixtures/modal_meets.json --case Modal --out .receipts
```

Fixtures are synthetic. Never publish an EDB or real project capture to this public repository. Genuine captured tables stay in local private output directories.

## Architecture and provenance

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/REUSE_REGISTER.md`](docs/REUSE_REGISTER.md). No legacy module imports, no mandatory 94-node scaffolding, and no `PASS` for incomplete engineering authority.