# TBDY Next Engine

Small, project-owned Turkish structural-engineering application. The older `TBDY`, `Column-Engine`, and R1-C codebases are **references only**; none are runtime dependencies. Each iteration implements **one bounded vertical slice** and records which stage was actually verified.

## VS01 — Modal effective-mass ratio (numerical subcondition)

1. From the Windows UI, attach to an already-running ETABS 23.2.0 instance.
2. Read the **complete** `Modal Participating Mass Ratios` table via the project-owned adapter. Offline JSON imports are optional.
3. Validate real source fields, all rows, selected modal case, contiguous modes, and cumulative fractions.
4. Evaluate the 95% mass-ratio subcondition of TBDY 2018 §4.8.1.2; this is **not** a complete seismic engineering verdict.
5. Show live X/Y results and old CLI results in the UI; write local receipts with source SHA-256. Never issue global engineering release.

## Installation and tests

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Windows / PyCharm — direct ETABS web connection

ETABS 23.2.0 must already be running with an analyzed, locked model. This
application never saves the model or starts analysis. Run from the repository
root with the project interpreter:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install comtypes
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m tbdy_next.cli serve --host 127.0.0.1 --port 8765 --out .receipts
```

Open `http://127.0.0.1:8765`, choose **Modal analiz**, then press **ETABS'a
bağlan ve hesapla**. No JSON file selection is required. The local server
reads only `Modal Participating Mass Ratios` from the active ETABS instance,
restores any temporary output-case selection, validates the rows, performs the
same VS01 numerical check as the CLI, and saves the input + stage receipts
under `.receipts/RUN-*`. Existing CLI results appear in the UI automatically.

The web server only listens on localhost; actual COM access is lazy and occurs
only after clicking the live button. Windows COM live acceptance is separate
from mock-based CI verification. In Codespaces/Linux the live button does not
connect to ETABS. Only **Modal analiz (VS01)** is implemented; the other 15
navigation tabs remain planned. The 95% result is a numerical subcondition,
not a global seismic-design release.

## Command-line usage

```bash
python -m tbdy_next.cli inspect-preflight --input path/to/etabs_readonly_preflight.json --out .receipts
python -m tbdy_next.cli check-modal --input tests/fixtures/modal_meets.json --case Modal --out .receipts
```

The repository includes **synthetic fixtures only**. Real project files, EDB models, and ETABS snapshots are excluded from git and must remain local/private. VS01 does not establish engineering release. Real modal tables and all used fields require targeted source review before a complete engineering check can be claimed.

Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Selective reference reuse: [`docs/REUSE_REGISTER.md`](docs/REUSE_REGISTER.md).
