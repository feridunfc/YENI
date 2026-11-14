# R08 — Global P–Δ engine vertical slice (2026-11-14)

## Architecture and ownership

Not an exploratory script. Product path:

ETABS locked SapModel -> live_etabs.read_quick_suite_from_running_etabs
-> story_second_order_capture.capture_story_second_order
-> story_second_order.bind_story_second_order
-> EXISTING engineering.story_pdelta.review_story_pdelta (one theta owner)
-> /api/live-vs04 RunId + ReceiptRun(r08-second-order)
-> build_complete_report exact receipt replay -> check_registry/UI/print report.

Reuses the existing product ETABS generic gateway and story_drift_binding source SHA validation.
Current code branch: work/r08-native-story-pdelta-20261114, based on
docs/recipe73-source-dag-20261113 (the advanced product branch, NOT VS06-only main).
The base branch already contains the permanent R07/R09 reconciliation service,
the engineering.story_pdelta owner and the 94-node DAG. This PR reuses
those owners rather than duplicating algorithms. The permanent R08 output is
the already-declared GLOBAL_SECOND_ORDER node; the historical public
check-registry remains 16 controls until an independently approved catalog revision.

## Source and engineering contract

- Output roles are RSX X, RSY Y and WGHT cumulative weight. These are model-specific and UNAPPROVED.
- The candidate cumulative weight comes from WGHT Story Forces Bottom P,
  crosschecked to WGHT Base Reactions FZ. Do not confuse wi and SUM(wi..wn).
- WGHT factors: LC_DL=1, LC_SDL=1, LC_WDL=1, LC_DDL=1, LC_LL=0.30;
  optionally LC_S=0.30 if that term actually exists in the source.
- ETABS kN-m-C (units code 6) and a locked, already-analyzed model are mandatory.
- Preserve exact case, combination, story, unit, model and gateway SHA evidence.
- A Mass Source may use element self-mass rather than LC_DL. WGHT is not
  automatically proven equivalent to the mass source.
- Source-numerical theta candidate for a given story and direction:
  theta_II_i = AvgDrift_i * CumWeight_i / (StoryShear_i * Height_i)
  theta_limit = 0.12 * D / (Ch * R)
- ETABS Story Max Over Avg Drifts Avg Drift is a source CANDIDATE; not proof of
  the normative column-plus-wall average required by TBDY §4.9.2.
- RSX/RSY Max components are not signed concurrent physical force states.
- Global P–Delta and local column P–delta are separate. No magnification
  is applied to the already completed R07 PMM results by this stage.
- Formal compliance NOT_PROVEN, engineering release NOT_READY,
  analysis generation NOT_PROVEN, global_p_delta_design_applied false.

## Available comparison (NOT a software oracle)

User-observed ETEX candidates: R=7, D=2.5, Ch=0.5,
theta limit approximately 0.0857143; displayed θmax X≈0.007, Y≈0.010,
beta II 1.0. These numbers are NOT hardcoded in engine.
ETABS Base Reactions tonf: WGHT FZ 4368.9334, RSX FX 356.2572, RSY FY 348.3959.

## How to use the permanent product path

On Windows with analyzed, locked kompakt_b.EDB and the existing WGHT
combination, use the product UI's existing ETABS’tan Oku ve Hesapla button.
NO R08 script. R08 CheckResult is produced within the SAME RunID, held in
its immutable receipt and included in the export/print report.

A different model filename fails closed rather than inheriting R/D/Ch.

## Open supervisory gates

Windows COM combo selection ABI and selected table rows require real
on-machine verification. Full physical story population, mass/weight role,
TBDY formula applicability, design-spectrum scaling beta_tE, earthquake
analysis generation, average column/wall drift, model second-order order,
local TS500 P–delta and independent PMM oracle remain NOT_PROVEN.
Any GitHub merge is SOFTWARE integration only, NOT engineering release.
