# R06 — Source-bound N–M2–M3 semantics (Codespaces offline)

R06 uses existing VS26 typed builders, not a new PMM or spectrum engine.
Inputs: immutable 9 Nov native full-model-evidence.zip and matching
YENI_RUN-5cf449b850fc41eeadcdd7528249f932_columns.zip.
Both pinned SHA-256 values are stored in config/r01_archived_sources.json.

Strict historical source numerical targets:
- 87 observed columns; 34,170 native force rows; 402 exact native cuts.
- 2,412 signed static physical source vectors; one exact (Obj, ObjSta, Elm,
  ElmSta, LoadCase, StepType, StepNum) key for every six-component tuple.
- 24 supported direct spectral combinations; 9,648 Max/Min pairs;
  19,296 native step rows; 115,776 scalar comparisons.
- 77,184 conditional P/M2/M3 eight-corner candidates; all signs explicitly
  tied to native P (tension-positive); N = -P (compression-positive).
- Six spectral component envelopes are NOT concurrent signed six-component
  force states. V2, V3 and torsion are not appended to corner candidates.

All these counts are HISTORICAL EXPECTATIONS awaiting R06 offline execution.
They do not by themselves establish live capture readiness, full building
coverage, applied second-order analysis, design demand or code acceptance.

Codespaces usage (private source files are .gitignored):

    python -m pip install -e .
    python tools/r06_review_native_demand.py \
      --bank .private_sources/YENI_RUN-5cf449b850fc41eeadcdd7528249f932_columns.zip \
      --native .private_sources/full-model-evidence.zip \
      --r01 .receipts/R01_archived_source_receipt.json \
      --r02 .receipts/R02_physical_analysis_ledger.json \
      --r03 .receipts/R03_unapproved_combobook.json \
      --output .receipts/R06_native_demand_semantics.json

The --r01/--r02/--r03 receipts are optional. If absent, cross-slice
receipt coverage remains incomplete. A supplied foreign run, changed
combination factor, forged design role or source mismatch is rejected.
No file is overwritten; input source ZIP remains byte-identical.
Exit 0 means source-numeric semantics reconstructed, NOT an engineering PASS.

R06 cannot assert project-load-role authorization; nominal horizontal and
vertical earthquake combinations; modal scaling and gamma/beta; analysis
generation; actual joint faces; second order; complete intermediate-axial
demand sweep; or selected/iterated reinforcement.

Supervisor: code committed but manual tests and golden acceptance deferred
by user's request until end-of-day. No live ETABS/COM. Merge HOLD.
formal_compliance=NOT_PROVEN, design_demand_authority=DENIED,
engineering_release=NOT_READY.
