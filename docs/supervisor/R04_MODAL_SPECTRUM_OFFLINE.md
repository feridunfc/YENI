# R04 — Offline modal / spectrum / base shear source re-evaluation

**Branch:** \`recovery/r00-r01-vs27-source-20261112\`  
**Mode:** Codespaces/Linux; archived JSON only. No COM, ETABS, model alteration, new analysis, or invented source.

## Why R04 is not a new formula motor

R04 reuses the product-owned implementations:

- \`source.parse_modal_capture\` + \`modal.evaluate_modal_mass\` (TBDY 4.8.1.2 numerical subcondition).
- \`analysis_sources.review_analysis_sources\` + \`analysis_numerics.evaluate_analysis_numerics\` for VS04-D raw source table replay.
- \`spectrum_reconstruction.review_spectrum_reconstruction\` for TSC-2018 26 sample knots and 200 RSX/RSY modal ordinates.
- \`base_shear_screening.review_base_shear_screening\` for the **one conditional lower-bound term** in TBDY Eq. 4.19.

The R04 executable reconstructs receipt-shaped wrappers FROM the full original source fields, re-evaluates the kernels, and compares results against the same archived report. It never trusts a cached PASS as a substitute for a real source.

## Historical input (not part of Git)

Pinned run: \`RUN-d176de308a3c4742a39ecb7f0128a9b1\`, SHA-256 listed in \`config/r04_pinned_report.json\`. Upload only the original full \`all_checks.json\` file to Codespaces \`.private_sources/\`. This file contains model details and must **not** be committed to public Git.

\`\`\`bash
python -m pip install -e .

python tools/r04_review_modal_spectrum.py \
  --report .private_sources/TBDY_NEXT_RUN-d176de308a3c4742a39ecb7f0128a9b1_all_checks.json \
  --output .receipts/R04_modal_spectrum_review.json
\`\`\`

Optional \`--r03 /tmp/r03_unapproved_combobook.json\` prints a **non-authoritative comparison only**. Since R03 is based on the *9 November* column source bank, it MUST NOT be joined to the *8 November* modal/spectrum report merely because case names or model filenames match.

Expected successful *source arithmetic* status:
\`HISTORICAL_SOURCE_NUMERIC_REPLAY_RECONCILED\`.

At this status, the report may describe 100 modal mass-ratio rows; 26 spectrum knots; 200 modal spectral rows; two independent base-reaction component envelopes; and the **conditional minimum Eq. 4.19 term**. It cannot issue full \`V_tE\`, \`beta_tE_X/Y\`, case-scale authorization, or a concurrent six-component force vector. Returned \`engineering_release=NOT_READY\`, \`design_demand_authority=DENIED\`, \`formal_compliance=NOT_PROVEN\` are intentional.

## Required blockers

- Full analysis-generation lineage between sources, including separate R01 native archive.
- DD2/DD3 design-basis/ground-motion approval and governing \`Tp\` in X/Y.
- Seismic mass and basement exclusion boundaries.
- Applied response-spectrum scale, pre-beta modal base shear, gamma_E from complete A1/B2/B3, and applied beta.
- Diaphragm / accidental eccentricity methodology, no max-as-concurrent-vector.
- A complete building check denominator and independent normative oracle.

R04 operates on the original full raw snapshot and compares it against historical recorded numerics. If it finds missing, tampered, contradictory or unsupported data, it writes **BLOCKED_SOURCE_REPLAY** with a nonzero exit code. A file SHA mismatch is rejected before evaluation. No archived source or database is mutated.

**Supervisor:** R04 SOURCE REPLAY CODE WRITTEN; NOT TESTED PER USER REQUEST. CI may run automatically on push; this does not constitute engineering acceptance. End-of-day Windows live acceptance is separate and deferred. Merge HOLD.
