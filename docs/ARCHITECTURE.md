# Project-owned architecture — Vertical Slice 01

The code in `src/tbdy_next/` is owned by this project. Nothing imports from, executes, or copies runtime modules from TBDY, Column-Engine or R1-C.

1. `source.py` — discovers ETABS table *names* and validates modal table *rows*. It never equates discovery with verified rows.
2. `modal.py` — pure, unitless TBDY 2018 4.8.1.2 **mass-ratio numerical subcondition**, not a complete engineering assessment.
3. `receipts.py` — append-only per-run JSON receipts with raw-input SHA-256 and receipt SHA-256.
4. `cli.py` — routes one bounded vertical slice at a time. No COM or implicit ETABS actions.

`inspect-preflight`: file -> discovery -> receipt.

`check-modal`: complete modal table -> schema acceptance -> numerical check -> two receipts.

## Status vocabulary

`DISCOVERED` means a table key exists in ETABS metadata, not that rows were read.
`SCHEMA_VALID` means the table rows are structurally complete for this slice.
`MEETS_NUMERICAL_CRITERION` means arithmetic meets the selected 95% subcondition; **it is not engineering PASS**.
All stages keep `engineering_release=NOT_READY` until independently reviewed rule/model/analysis context can be evaluated.

## Future slices

VS02: analysis-basis + modal source interpretation, then first full modal engineering check.
VS03: base shear source/combo and engineering rule.
VS04: column axial TBDY/TS500; VS05: local/global second-order and PMM; VS06: SCWB.

Future changes are versioned and additive; no blanket 94-node gate is required to implement a single rule.
