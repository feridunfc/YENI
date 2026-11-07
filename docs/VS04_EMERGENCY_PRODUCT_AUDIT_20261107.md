# VS04 — ACIL SUPERVISOR URUN DENETIMI (2026-11-07)

## Durum
PRODUCT NOT_READY; MERGE HOLD. Source arithmetic findings do not authorize
building code compliance.

## Branch
main = a53f29f65f62b7e15911283aa4e4b6c750d8d0f7
work/vs04-analysis-source-schema-20261107 = 2a249786d940bf0ddcdddb1f0599a0e1054ea85e
VS04 13 commits ahead of main, zero behind. Do NOT merge just because FF is possible.

Three historical branches diverge from main:
work/modal-mass-v1, work/vs01-modal-ui-20261107,
work/vs03-material-torsion-20261107.
Never delete before reviewing unique commits.

## Measured proof and limits
- Existing eight bounded VS03 screening checks are accepted.
- VS04-D sources 5/5 arithmetic.
- VS04-E/F/G/H source shape, modal selection, mass, geometry and diaphragm inventory.
- VS04-I 26 analytic source knot values and 200 modal accelerations reconstructed.
- VS04-J candidate Eq 4.19 minimum term = 1355.185792361929752 kN.
- Normative VtE, gammaE, beta_tE and effective drift have NOT been authorized.
- Five semi-rigid diaphragm definitions, 3 directly assigned in observed
  shell and joint sources. Diaphragm mass report still zero.
- Missing analysis generation, basement boundary, A1/B2/B3, Tp X/Y,
  DD2/DD3, actual spectrum scaling and physical drift semantics.

## Canonical pipeline
A Existing ETABS -> B source snapshot -> C schema/units/identity ->
D typed engineering facts -> E applicability and prerequisites ->
F independent TBDY kernel -> G CheckResult ->
H same-run source receipts + JSON/HTML and I Result Tree + tables.

If prerequisites are absent: NOT_PROVEN with exact reasons. If a rule
is demonstrably not applicable: NOT_APPLICABLE with exact applicability
decision. Never silently promote source-only success to formal PASS.

## Web UI
One primary live calculation button: ETABS'tan Oku ve Hesapla.
It calls /api/live-vs04 and can display the eight accepted screening
checks plus VS04 schema, source arithmetic and normative missing-evidence
ledger in one run_id. It does NOT yet run VS04-F through VS04-J on the
live web path. Their outputs are standalone offline evidence tools.
The new UI has NOT been proven by Windows browser/ETABS live acceptance.

## Ordered merge criteria
1. Single Windows UI button -> one locked model session -> one run_id;
   fail closed and restore ETABS display case selection.
2. All supported source and numerical stages must flow into the same
   CheckResult, receipt, JSON/HTML and Result Tree; no missing stages.
3. At minimum one fully sourced base-shear check and one full directional
   effective-drift check need independent normative oracle, rule card,
   all input authority and negative boundaries.
4. Retest history, source hash tampering, unit/case/direction mismatch.
5. GitHub CI and Windows live E2E acceptance, Supervisor disposition.
6. Only then PR review and approved merge to main.
7. Audit historical branch uniqueness before delete/archive.

Present state: MERGE HOLD; ENGINEERING_RELEASE NOT_READY.
