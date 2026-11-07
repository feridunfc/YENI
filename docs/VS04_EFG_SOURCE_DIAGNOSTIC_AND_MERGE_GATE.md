# VS04 — E/F/G Display-Selection Evidence Closure and Merge Gate

**Scope:** Source-report and product acceptance only. No new normative TBDY
PASS, no changes to accepted VS03 eight checks, and no ETABS model mutation.

## Ground truth: 2026-11-07 Windows live source

Real run `RUN-f86e77b043d841b38bc9aec8b689bc8d` produced:

- E: 14 of 15 candidate sources structurally read; the sole failed table
  was `Response Spectrum Modal Info`, return code 1 without cases selected
- F: 3 of 4 typed-source checks, fourth `SPECTRUM_MODAL_OUTPUT` failed
  because the original unselected read did not return rows
- G: 4 of 5 source reads; 3 diaphragm tables and a 200-row
  `Response Spectrum Modal Info` when RSX and RSY were temporarily
  selected. Original unselected failure remains recorded
- H: 4/4 diaphragm + modal source associations
- I: 26/26 analytic spectrum knots and 200/200 independently
  reconstructed modal input accelerations, based on source printed
  precision and circular frequencies
- J: Eq. 4.19 *conditional* minimum term
  `1355.185792361929752 kN`, not actual `VtE` or `beta_tE`

The same live source snapshot stores the raw data for all six stages,
a single `run_id`, and input/receipt SHA-256 verification on JSON/HTML
export and history. Nevertheless a shared source snapshot does NOT
independently establish the freshness or identity of the ETABS analysis
generation.

## Model of the repair: preserve failed history, reconcile dependency

The E/F/G data was not fully captured in the original selection.
It must not be rewritten as 15/15, 4/4 or 5/5.

For newly captured `pipeline_contract_version=v2`, a pure, deterministic
diagnostic recognizes *only* this exact bounded pattern:

1. E: precisely one failed source of 15, exactly
   `Response Spectrum Modal Info`, and captured
   `ret_code=1` under original no-case selection
2. F: precisely 3/4 and the only missing component
   `SPECTRUM_MODAL_OUTPUT`
3. G: precisely 4/5 and the original-selection read failed,
   but the temporarily selected RSX/RSY read captured exactly 200 rows;
   selected case display was restored
4. The live payload records E/G from the same locked SapModel request
5. H: full 4/4 association, I: 26/26 analytic knots and 200/200
   independent modal acceleration reconstruction

Only then E/F/G get `SOURCE_PARTIAL_DISPLAY_DEPENDENCY_EXPLAINED` as
their **product-level source diagnostic**, retaining their original
`source_status`, original observed/expected coverage,
`reason_codes` and missing regulatory evidence.

If any additional source fails, selected-mode rows are missing, another
case is selected, 200-mode proof is inconsistent, or the original
ret-code evidence is not present, diagnostic status remains
`NOT_PROVEN`; no source errors are hidden or accepted by fallback.

H and I stay `SOURCE_OBSERVED_UNAPPROVED`; J stays
`CONDITIONAL_ONLY_NOT_CODE_APPROVED`. All six retain
`formal_compliance=NOT_PROVEN`. The five expected normative checks remain
NOT_PROVEN and are not added to the eight accepted bounded controls.

## Product outputs

The source v2 `CheckResult` exposes:

- `check_id`, source stage, explicit source status and interpreted
  source-only status
- `coverage.expected`, `observed_in_original_stage`,
  `unobserved_in_original_stage`,
  `independent_selected_case_reconciliation_count`
- `execution_status`, `applicability`, `reason_codes`,
  `missing_evidence`, source identity and `formal_compliance`

The *same object* is rendered by the left Result Tree, VS04 details,
JSON report, HTML report and receipt-verified history. The JSON report
`scope`/title now explicitly describe six source-only stages; it no
longer describes the product as schema-only or a complete TBDY design.

### Backwards compatibility: immutable v1 receipts

The v1 evaluator must remain unchanged for source snapshots lacking
`analysis_sources.pipeline_contract_version="v2"`. The v1 receipt's
original payload is recomputed exactly as it was at capture time.
Historical receipts must remain readable even if interpreted as
source-partial before this change. Only *new* Windows captures set v2.

### Engineering and merge acceptance

- CI of current exact commit on Python 3.11 and 3.12
- Tests of 14/15 → 3/4 → 4/5 provenance with the 200-row selected-case
  dependency, negative mutated sources, and v1 replay preservation
- Same source result in the single-run JSON/HTML/history/left tree
- New Windows single-button replay recommended as live presentation
  acceptance; previous E–J Windows capture already confirmed the data
  boundaries (not a new model-analysis generation proof)
- Supervisor must approve **source/integration merge**, not a full
  regulatory engineering release

**Engineering design remains:** full `VtE`, `gamma_E`, `beta_tE`,
DD-2/DD-3 `lambda`, directional `Tp`, physical drift `Delta_i`,
diaphragm accidental eccentricity effect, and independent model/analysis
generation = NOT_PROVEN.

**Next after merge:** develop TBDY normative algorithm on a fresh
versioned branch derived from accepted `main`, with per-rule applicability,
independent hand or standard oracle, typed physical inputs, fail-closed
`CheckResult` and fully reported design quantities. The new normative
branch must not modify accepted VS04 source receipts.
