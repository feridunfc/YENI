# R07–R09 / R08: permanent engine integration (2026-11-14)

## Engineering contract

Research-only PowerShell/Python capture helpers are NOT the source of truth for calculated results. The durable owner is now:

- tbdy_next.engineering.live_column.review_live_column: verifies signed live ETABS source and native combination receipts, reuses column_engine.section_capacity.solver, reconciles all observed stations, and binds physical offsets/axes/endpoints.
- tbdy_next.engineering.story_pdelta.review_story_pdelta: direction-matched numeric-only TBDY 4.9.2 story screening; individual G+nQ story weights, spectral shears, and corresponding reduced average drifts.
- tbdy-next reconcile-live-column / tbdy-next precheck-story-pdelta: one stable CLI, private inputs and sealed outputs.

Do not create duplicate numerical kernels under tools/. Never use a file hash to claim matching analysis generation; even when numerical forces and physical geometry match, same-cut/joint-face authority still needs evidence.

## Verified exploratory reference (private; never commit)

Model C:\tmp\kompakt_b.EDB; object 127, C88 +4.50, 800×800 mm C35/45. Native LC_DL 0.0 m signed six-component row was captured. The static Grav_Ult Linear Add combination was captured for object/element 127 at 0.0, 1.9, 3.8 m. The already-observed PMM numeric scenario, with PROPOSED 16Φ24 cage, reports numeric utilization 0.021684879367740273 / 0.016703979355374668 / 0.05407789743409475, in that station order. These values are not approved design utilizations.

Live geometry: node I=1044, J=412, I–J=4.50 m; observed Auto offsets 0.00/0.70 m, reduced source output span=3.80 m. The reduced output span is NOT a TS500 approved effective length. R08 retains k, ln, sway, EI, creep, analysis order and double-counting gates.

## Windows/offline workflow

1. Capture private ETABS receipts using the existing read-only gateway/research capture adapters. Inspect model lock, kN–m–C, model sha before/after, reversible output case/combination selection, field metadata, stations and steps.
2. Run permanently installed production CLI from the repo root (no scripts to recopy):

       tbdy-next reconcile-live-column --live-receipt .private_sources/r07_r09_live.json --lc-dl-run .private_sources/r07_r09_results/R21-R07R09-1adcced5ebffa7f447c794bc/run_result.json --combo-capture .private_sources/r07_127_gravult_capture.json --combo-pmm .private_sources/r07_127_gravult_numeric_result.json --geometry .private_sources/r08_127_live_offsets_axes_points.json --out .private_sources/r08_engine_reconciled_new.json

   Run with python -m tbdy_next.cli instead of tbdy-next if necessary. Never overwrite existing receipts.

3. Story second-order source must be a separately typed JSON with schema tbdy.next.r08.story-source.v1. Rows top-to-bottom must contain individual wi, NOT cumulative ETEX Wi, story height hi, Vi and reduced average Delta(i,ort) in X and Y. Use RSX for both X shear and drift, RSY for both Y shear and drift. Mark G_PLUS_NQ mass participation explicitly. Then:

       tbdy-next precheck-story-pdelta --input .private_sources/r08_story_source_v1.json --out .private_sources/r08_story_numeric_new.json

4. Verify source numerical equality, store receipts in .private_sources, and only then add the next engineering check to the same engine. Make PRs from a pinned base and merge the implemented source/numeric code, not unapproved compliance.

## Important semantic differences

- MsSrc1 seismic mass G+nQ and a WGHT load combination are related but NOT automatically identical; check element self-mass, load-pattern self-weight factors, additional masses and snow before approving.
- The ETABS WGHT base reaction is a cumulative building force; it is NOT individual story wi. The ETEX Wi field may already be cumulative: verify report semantics and do not sum twice.
- ETABS RSX / RSY response-spectrum Max values are statistical component envelopes; do not combine six components as a concurrent signed PMM force state.
- R=behavior factor and D=overstrength factor; text labels in third-party interfaces can be reversed. The numeric reference threshold is theta(II,lim) = 0.12 D/(Ch R) under the stated applicability.
- Global system P–Delta, local member P–delta, and theta(II) story screening are different checks. Screening does not prove P–Delta was already applied or approve local magnification.
- ENGINEERING_RELEASE=NOT_READY, engineering_verdict=NOT_PROVEN, selected_cage_approved=False; never auto-upgrade based on a low numeric PMM ratio.

## Promotion criteria: research -> engine -> merge

Every resolved obstacle requires (1) pinned source identity, (2) service under src/tbdy_next, (3) CLI/report boundary, (4) regression for valid and fail-closed paths, (5) GitHub CI, and (6) separate Supervisor disposition for engineering compliance. Source/numeric code may be merged while design acceptance remains denied. Existing PRs #6/#7 and base-branch dependencies must be reconciled before main-line merge.
