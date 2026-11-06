# TBDY Next Engine

Small, project-owned Turkish structural-engineering application. The older `TBDY`, `Column-Engine`, and R1-C codebases are **references only**; none are runtime dependencies. Each iteration implements **one bounded vertical slice** and records which stage was actually verified.

## VS01 — Modal effective-mass ratio (numerical subcondition)

1. Inspect an ETABS 23.2.0 *readonly preflight* JSON. **Table listed** does not mean **table schema verified**.
2. Import a **complete** `Modal Participating Mass Ratios` capture in `tbdy.next.modal.capture.v1` format.
3. Review source columns and validate all rows, the selected modal case, contiguous modes, and cumulative fractions.
4. Evaluate the 95% mass-ratio subcondition of TBDY 2018 §4.8.1.2; this is **not** a complete seismic engineering verdict.
5. Write local, auditable stage receipts with source SHA-256; do not issue global engineering release.

## Installation and tests

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Web interface

```bash
python -m tbdy_next.cli serve --host 127.0.0.1 --port 8765 --out .receipts
```

Open `http://127.0.0.1:8765`. In Codespaces, forward port 8765 using a **private** port-forward setting. The navigation reserves 16 future workspaces, but **only Modal Analiz (VS01) is active**; the others are visibly marked as planned. The working modal screen exposes source discovery, schema review, numerical assessment, receipts, Model Tree, and Result Tree. No live ETABS connection or model modification is performed.

## Command-line usage

```bash
python -m tbdy_next.cli inspect-preflight --input path/to/etabs_readonly_preflight.json --out .receipts
python -m tbdy_next.cli check-modal --input tests/fixtures/modal_meets.json --case Modal --out .receipts
```

The repository includes **synthetic fixtures only**. Real project files, EDB models, and ETABS snapshots are excluded from git and must remain local/private. VS01 does not establish engineering release. Real modal tables and all used fields require targeted source review before a complete engineering check can be claimed.

Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Selective reference reuse: [`docs/REUSE_REGISTER.md`](docs/REUSE_REGISTER.md).
