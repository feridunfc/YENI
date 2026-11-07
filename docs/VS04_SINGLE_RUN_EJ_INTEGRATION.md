# VS04 Product Integration Gate — E–J one live run (2026-11-07)

## Objective

The primary `ETABS’tan Oku ve Hesapla` button must perform exactly one
user-triggered HTTP POST and one request-thread-owned ETABS COM acquisition.
The live capture includes the already accepted VS03 eight bounded checks,
VS04-D three analysis-source tables, and now VS04-E / G basis and
diaphragm/spectrum source probes in the **same** locked SapModel session.

After the source snapshot is archived, pure deterministic evaluators
run VS04-E,F,G,H,I,J. All stages share one `RUN-...` and `input_sha256`.
`vs04-pipeline` receipt is required for captures with
`analysis_sources.pipeline_stage_required=true`. On JSON/HTML export and
quick-history selection, the archived input is reevaluated and the sealed
receipt is compared; absent or modified receipts reject the report.

The product presents two distinct inventories: the unchanged eight existing
bounded numerical/geometry/A1 checks, and six **source-only** E–J stages.
They are not equivalent to full TBDY design checks. The five expected
normative engineering target checks (modal case lineage, base shear X/Y,
effective drift X/Y) remain NOT_PROVEN pending complete physical input,
analysis generation, DD2/DD3, A1/B2/B3, spectrum scaling and basement
qualification.

## Failsafe source handling

- ETABS model must already be analyzed and locked; no RunAnalysis / Save.
- Any temporary case selection is verified and restored in each collector,
  including exceptional exits. The sole COM owner, lock and OAPI session
  are shared from the request thread.
- Before acquiring source E/G, the existing VS04 table selection is restored.
  Source E is strictly read only. G temporarily selects RSX and RSY for
  200 selected spectral-modal rows and restores its initial selection.
- Source table capture failure (or unsupported ABI) must be represented as
  NOT_PROVEN. A display-selection restoration error rejects the capture.
- `analysis_generation_proven` remains false, even when all tables come
  from the same SapModel pointer at one instant. Model-analysis freshness
  requires independent proof.

## UI and reports

- One main calculation button; all six E–J stages appear in the VS04
  details and left Result Tree with SOURCE_OBSERVED_UNAPPROVED or NOT_PROVEN.
- A1 classification for X/Y is an alert if any `A1_OBSERVED` source
  row exceeds 1.2; applicability and accidental eccentricity remain
  unapproved, so do not label an A1 finding a compliant design.
- HTML and JSON reports include `vs04_pipeline` source check inventory
  and any conditional Eq 4.19 minimum term with an explicit warning.
- No F–J result is inserted as a ninth code check in `check_registry`.
- Legacy pre-integration runs without `pipeline_stage_required` remain
  readable according to their original record contract.

## Test matrix

Synthetic HTTP capture tests prove one callback / one run ID, one
vs04-pipeline sealed receipt, and matching JSON + HTML + history.
Tampering or deleting that receipt denies both exports and history.
Incomplete same-session input or changed source parameters cannot
produce a normative PASS.

**Windows live E2E remains mandatory.** Validate use with the existing
`kompakt_b.EDB` locked model, original case selection restore, one
set of E/G captured fields, F–J source statuses, and same-run JSON/HTML.
Test numbers and source counts do not prove actual TBDY compliance.

`FORMAL_COMPLIANCE=NOT_PROVEN`
`ENGINEERING_RELEASE=NOT_READY`
`MERGE=HOLD`.
