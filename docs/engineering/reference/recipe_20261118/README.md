# English recipe integrated with the local YENI baseline

The 2026-11-18 delivery is accepted as a **reference and verification asset**.
The existing production engine, calculation owners, stage registry and ETABS
gateway retain their ownership. This import changes no runtime source, test,
configuration or application dependency and closes no engineering control.
Engineering release remains `NOT_READY`; R14/R15 remain 0 closed / 87 partial.

Start with [the English recipe](delivery/RECIPE.md), then consult
[the 73-control mapping](delivery/CHECK_MAPPING.json),
[the worked examples](delivery/GOLDEN_CASES.json), and
[the additional modal-to-alpha example](delivery/PRIORITY_CHAIN.json).
The 2026-11-13 recipe and migration plan remain historical references; this
package supplies the current English working reference, subject to the limits here.

## Versions and preserved bytes

The worker inspected published commit `b255c3030c09c88a17bbec766fc2bb22682ad027`.
This local intake inspected `250ff1974316070393f3fff9847d941a80dcd47e`, tree
`be2d9852d4d7a831347dd774964fc33c2e37be51`, on Windows / CPython 3.12.10.
The published commit is an ancestor of the local code. Newer local work is preserved.

All 250 payload files in `YENI_RECIPE_FULL_20261118.zip` matched their manifest.
Archive SHA-256: `6f46177e64a5d0ee8e9b6fc7d7b5ba74e252e2cb547fb3655ad97d6aaf490b1f`.
[IMPORT_MANIFEST.json](IMPORT_MANIFEST.json) lists the 30 imported text files,
their exact hashes and the two omitted generated PDF/DOCX renderings. Original
private reports, SQLite banks, source access records and source-code snapshots
remain outside Git. `delivery/SHA256SUMS.txt` describes the original complete
public delivery; use the import manifest to verify this retained subset.

The `delivery/` files remain unchanged historical evidence. Their statements
that the local tree was `NOT_INSPECTED` describe the worker's inspection, not
this later local intake. [LOCAL_BINDING.json](LOCAL_BINDING.json) and
[LOCAL_VERIFICATION.json](LOCAL_VERIFICATION.json) record the local reconciliation.
Do not rewrite original evidence to make it appear newly executed.

All 142 referenced published files matched actual local Git objects. Against
the current working files, 30 matched exactly, 101 differed only in CRLF/LF, and
11 had content changes. All 88 referenced function/class ASTs and signatures
matched. The changed acquisition, demand-source and pipeline files retain the
later numeric/torsion adapters. Symbol compatibility does not certify dependency
semantics, normative applicability or complete control implementation.
The mapping still has **44 partial bindings and 29 unmapped controls**; that
44 is unrelated to the 44 production golden comparison records.

## Fresh verification

| Scope executed during this intake | Result | What it establishes |
| --- | --- | --- |
| Five JSON schemas, identities and source-symbol locations | VALID; six negative contract probes detected | Delivery structure and provenance |
| 73 primary examples plus 12 adapter fixtures | 333/333 assertions match | Frozen example arithmetic and data contracts |
| One separate modal-to-alpha fixture | 1,294/1,294 assertions match | Synthetic arithmetic chain only |
| Current `section_axial_limits_kn` and `minimum_eccentricity_mm` | 3/3 primitive values match: 1080 kN, 1620 kN, 24 mm | Explicit local input/output mappings for these quantities |
| Existing `verification/golden_gate.py::build_golden_gate` | 44 records: 15 match, 25 insufficient, four interpretation differences | The existing production comparison population remains unchanged |

Commands, environment, source and verifier hashes, and private receipt locations
are recorded in `LOCAL_VERIFICATION.json` and ledger entries
`EV-RECIPE18-INTAKE`, `EV-RECIPE18-ARITHMETIC` and `EV-RECIPE18-LOCAL-OWNERS`.
The earlier stored 13/27/4 result and the current 15/25/4 result differ only in
`G02_ALPHA_ground` and `G02_ALPHA_top`: the existing owner now supplies the printed
Vis/Vik arithmetic. This does not establish a complete physical story roster,
two-end SCWB qualification, or permission to apply alpha amplification.

The prior 1,393 Python tests, 10 JavaScript files, 227 installed-wheel tests,
16/16 repeat receipts and sealed-report projection belong to the preceding
runtime increment. They were **not rerun or relabelled** for this reference-only
change. No new recorded-source pipeline run, live ETABS operation or engineering
acceptance is claimed here.

The isolated schema dependency was installed under private `.receipts`; the
application still has no new dependency. The imported `delivery/tools/` scripts
are frozen audit references, never production imports or pipeline stages.
Formula strings remain display-only. Reproduction of the two arithmetic records:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B docs/engineering/reference/recipe_20261118/delivery/tools/verify_golden_arithmetic.py --bank docs/engineering/reference/recipe_20261118/delivery/GOLDEN_CASES.json
.\.venv\Scripts\python.exe -X utf8 -B docs/engineering/reference/recipe_20261118/delivery/tools/verify_priority_chain.py --fixture docs/engineering/reference/recipe_20261118/delivery/PRIORITY_CHAIN.json
```

## Decisions carried into the existing roadmap

| Adopted reference requirement | Existing owner / unresolved gate |
| --- | --- |
| Freeze member, combination, element-side, cut and step populations before reading successes | `frame_force_capture.py`, `engineering/column_axial.py`; GAP-004/015 |
| Separate native precision, applied torsion, modal aggregation and directional rules | `engineering/demand_sources.py`, `engineering/mixed_demands.py`, `column_engine/spectral_envelope.py`; GAP-018 |
| Qualify governing axial demand and physical story allocation before SCWB/alpha feedback | `column_engine/scwb_kernel.py`, `column_engine/story_alpha.py`, `engineering/alpha_iteration.py`; GAP-013 |
| Bind every reinforcement-dependent consumer to the same selected/actual cage revision | `engineering/design_dependencies.py`, existing column/joint owners; GAP-013/014 |
| Retain a complete independent example with source, intermediate values and sealed outputs | Existing `verification/golden_gate.py` and `report_oracles.py`; GAP-016 |
| Keep explicit dependencies, missing-input blockers and complete CheckInstance accounting | `engineering/pipeline.py::EnginePipelineRunner`; GAP-005/017 |

The synthetic modal example has proportional signed modal fields and declared
capacity curves. It has no finite-element solution, actual bar cage or production
design iteration. Its positive subset-ratio result is not generalized to arbitrary
modal fields. Its counterexamples are useful rejection criteria: summing member
peaks does not establish story shear, and corner checks need proof of demand
containment and resistance-set/transform conditions over the whole domain.
The recipe's E-only amplification and the current total-M/V policy remain distinct
unapproved interpretations; this import does not select or equate them.

Closing a control still requires its applicable clause and method decision,
independently expected scope, same-source identities, explicit units/axes,
intermediate values and tolerances, positive/negative/boundary/missing-input
evidence, production-owner comparison, and a sealed pipeline/report result.
A schema, AST match, assertion total or low utilization cannot replace those gates.

## Next bounded acceptance

The user ordered live ETABS work **after** this integration. The next work branch
starts from the updated local `baseline/local_import` and continues GAP-018:

1. Rediscover the active ETABS PID and use the existing user-launched server and gateway.
2. Capture native numeric modal inputs and eccentricity definitions in one new
   locked-model acquisition; verify temporary selection/mode restoration.
3. Reconcile the independent expected mode and spectrum-case inventories, retaining
   every missing/error row. Do not merge new payloads into an old receipt or bank.
4. Verify source/results identity, repeatability and sealed report projection.
   This accepts the supported getter/binding scope only.
5. Then qualify applied torsion, spectral amplitudes/active damping, modal/directional
   aggregation, governing N and story allocation before a complete production
   SCWB/alpha iteration example. The imported synthetic chain is a reference for
   that work, not its completed acceptance record.

The local baseline advance is a software/documentation integration checkpoint.
It does not approve a structural design. No main merge, force push or GitHub
publication is part of this intake.
