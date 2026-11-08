# VS06-C1 — TBDY 2018 §4.9 effective drift candidate readiness, no normative release

Repository: `feridunfc/YENI`  
Branch: `work/vs06-story-drift-coverage-20261108`  
Merge policy: one VS06 final merge only, PR #5 remains DRAFT / MERGE HOLD.

## Normative source

Official AFAD TBDY 2018 §4.9.1.1–4.9.1.4 (printed pp. 55–56):
- Eq (4.32): `Delta_i = u_upper - u_lower` from the *same physically qualified column/wall member* under eligible reduced design earthquake action. Eq (4.19) minimum and §4.7.3.2 Tp cap must not be imposed on the §4.9.1.1 displacement calculation.
- Eq (4.33): `delta_i = (R/I) * Delta_i`.
- Eq (4.34a): `lambda * delta_i,max / h_i <= 0.008*kappa` for attached brittle infills.
- Eq (4.34b): `lambda * delta_i,max / h_i <= 0.016*kappa` only with qualified flexible detailing and experimental connection/displacement-capacity evidence.
- `lambda = Sae_DD3(Tp)/Sae_DD2(Tp)`, same direction and qualified governing Tp; `kappa = 1` for RC and `0.5` for steel, subject to explicit applicability.
- Special one-storey reversible-steel-frame exception and system applicability are not inferred.

Primary legal text: https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf

## Fixed six-step source-driven workflow

1. CHECK: Existing `STORY_DRIFT` node only. No duplicate regulatory check or new COM reader.
2. ETABS sources: Already captured `Story Definitions`, `Column Object Connectivity`, `Point Object Connectivity`, `Joint Displacements`, `Story Drifts`, `Story Max Over Avg Drifts`. Captured RSX/RSY point *Max* rows are not concurrent.
3. General reader: Existing `tools/etabs_source_gateway_windows.py`; old sealed VS05 receipt re-evaluated before this read-only candidate projection.
4. Typed bindings: VS06-A source-slot ledger + VS06-B partial physical-source review; no untrusted manual R, I, DD-2/DD-3 or wall status is promoted.
5. DAG: `RegulatoryCompiler` revalidates the 94-node/140-edge research catalog and exact `STORY_DRIFT` dependencies. It compiles `STORY_DRIFT:X:<story>` and `STORY_DRIFT:Y:<story>` **candidate** `STORY_DIRECTION` instances and reconciles them through `assess_candidate_plan`. Every result remains `NOT_PROVEN`. All nodes remain `DENIED`.
6. Tests/outputs: Synthetic golden and adversarial tests, one unchanged UI source/action, derived `vs06_effective_drift_readiness` in same JSON/HTML export.

## Important denominator distinction

VS05/VS06-A: for 4 ETABS story definitions, there are `4 stories x 2 response-spectrum cases x 2 displayed directions = 16` **source slots**. On `kompakt_b.EDB`, 12 source slots have observed values and 4 are missing at the otherwise declared `+14.5` level.

VS06-C1: the primary direction candidate set is only `4 stories x 2 principal directions = 8` **story-direction check instances** (`RSX-X` and `RSY-Y`). Thus the expected real archive result is `8 expected, 6 source-numeric candidates, 2 source-missing`; all 8 normative outcomes `NOT_PROVEN`. Cross-direction `RSX-Y` and `RSY-X` remain source evidence, not extra formal checks or automatically combined design cases.

**The user states +14.5 story is an empty retained model level.** This is owner context, not independent typed ETABS physical/area/wall/mesh census. This level is not automatically `NOT_APPLICABLE` and is not silently deleted from the candidate denominator.

## Exact authority gaps

- Independently verified full physical Story/Frame/Area/Wall/Null/Mesh census.
- Certified model and analysis generation; same captured seismic direction/case lineage.
- Qualified real reduced member-end displacement (or independently justified modal-spectrum combination giving actual interstorey drift); no difference of independent point Max rows.
- Qualified R, I, governing Tp and verified DD-2/DD-3 spectra at that Tp.
- Verified response-spectrum scaling and Eq (4.32) excluded floor / period cap.
- Documented material κ and infill connection details, tested flexible-wall capacity when that branch is chosen.
- External engineering oracle and supervisor formal review.

## Acceptance

On current worker branch:
```powershell
python -m unittest discover -s tests -q
python tools/verify_vs06_c1_archived.py --root "C:\Users\efeya\PycharmProjects\YENI_VS04\.receipts" --run-id RUN-e4a5376365c649b6b7469b0a778617ff --expected-checks 8 --expected-source-numeric 6
```

These are not live ETABS analysis commands. A green Windows or Linux test suite never authorizes normative `PASS`.

**VS06-C1 = SOURCE_BOUND_DAG_FCR_READINESS candidate; VS06-C formal effective-drift compliance OPEN. Engineering release NOT_READY.**
