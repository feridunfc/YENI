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

## Column crosstie detailing, recorded 2026-11-15

Carry the user's crosstie requirement into CHK-123/F07. Provide internal crossties to restrain longitudinal bars and close excessive gaps between restraining legs. Verify the tie and crosstie leg positions, maximum unsupported spacing, restrained bars and anchorage in both section axes for the selected cage. The PMM sketch shows the perimeter tie and longitudinal bars. ETABS template diameter, pitch and counts document the starting cage inputs. The confinement verdict requires the actual layout.

## Acceptance criteria for each engineering check

1. **Scope.** Record the check ID, governing standard edition and clause, applicability, formula branch and required inputs. Derive the expected population independently of the rows that arrive. Identify each required member or story, axis, combination, physical station and step as applicable. Cite the evidence for each exclusion.
2. **Source.** Verify every required field, unit, native ID and local-axis mapping against one model and analysis generation. Bind the combination definitions, cage and calculation version to the same run. Missing, duplicate and conflicting rows receive explicit dispositions that identify the affected keys.
3. **Engine.** Use the normal live route and typed capture, with one existing engine owner per formula. Use its sealed stage receipt for replay and its verified result for the API, UI and exports. Keep alternate calculations within the independent validation fixtures.
4. **Numerics.** Agree on an independent calculation or benchmark and the comparison tolerance for each quantity before comparing. Check exact IDs, signs, formula branches and verdicts separately from numerical tolerances. Exercise ordinary, boundary and missing-source cases, including a case that fails for a known reason.
5. **Product.** Verify a controlled live ETABS run, replay its exact receipt and open the corresponding result in the running product. The same RunID, evidence, value, unit, threshold and status must reach the served API, visible table and supported exports. Required fields must display their value or a reason. Close the check when its required population has zero unresolved rows and the independent comparison is accepted. Track numeric completion, engineering verdict and release separately. Reopen acceptance after model, analysis, combination, cage or calculation changes.

**PMM (R03, R06, R07, R09).** Bind each signed N, M2 and M3 vector to one combination, physical cut and step. Account for all required combinations and physical cuts, including seismic families. Response-spectrum component envelopes require an approved demand method for PMM. Verify the accepted cage's geometry, bar areas, materials and minimum reinforcement. Apply the existing minimum eccentricity rule to the demand and use the existing PMM kernel for capacity. Verify positive and negative moments, unequal local axes, axial-only demand and the capacity boundary with the independent oracle. Report the controlling combination, station, demand, capacity and utilization. Distinguish a numerical template scenario from approved design evidence in the result.

**Slenderness and moment magnification (R08).** Bind physical support faces, clear length, end restraints and sway classification to each local axis. Use the same cage and design demand to establish effective stiffness, creep basis, Euler load, paired signed end moments and applicable story sums. Verify effective length, effective slenderness and each magnification branch with the TS 500 kernel. Resolve the applicable Eq. (7.29) interpretation before granting that branch design authority. Record where global and local second-order effects are applied. Carry the resulting signed moments into the same PMM demand vector. Joint-to-joint geometric L/r remains a separate observed ratio.

## Promotion criteria: research -> engine -> merge

Every resolved obstacle requires (1) pinned source identity, (2) service under src/tbdy_next, (3) CLI/report boundary, (4) regression for valid and fail-closed paths, (5) GitHub CI, and (6) separate Supervisor disposition for engineering compliance. Source/numeric code may be merged while design acceptance remains denied. Existing PRs #6/#7 and base-branch dependencies must be reconciled before main-line merge.
