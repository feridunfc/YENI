# PDF Golden Bank V2 — two additional ideCAD reference models

**Date:** 2026-11-13  
**Repository:** `feridunfc/YENI`, reference branch `recovery/r00-r01-vs27-source-20261112`  
**Numerical oracle status:** `REFERENCE_ARITHMETIC_REPLAYED`  
**Engineering authority:** `NOT_PROVEN`; `ENGINEERING_RELEASE=NOT_READY`  
**No engineering source code was modified.** The 73-check recipe mapping remains in `RECIPE73_YENI_INTEGRATION_20261113.md`.

## Data set V2

The V1 independent PDF reference database has been extended with two more **different models**, each isolated by source SHA and document/model identity:

| Source | Pages | Model | SHA-256 |
|---|---:|---|---|
| `2.pdf` | 197 | 2 stories, 5 m/story, columns 30x30 cm, C30/B420C | `dfd8ea48fbb56a3d4f3525b1e7aae7f8de9f05fec341b1c742951db2738e6a31` |
| `3.pdf` | 258 | 3 stories, 3 m/story, columns 40x40 cm, C30/B420C | `0e5d2841d44f0690509cfe681681a238291bed645e24011424ac37b3c9c5f196` |
| Earlier compressed ideCAD PDF | 261 | 3 stories, 5 m/story | `0c6955496aaaa92e2b508ca4eb040927ac8eab2bef92a857f2ff602b8a78fba2` |

Combined: **716 complete searchable PDF pages**, SQLite FTS5 search, source-page and row provenance, 245 new raw numerical observations and 467 numerical comparison cases. New cases **333/333** are arithmetically reproduced within documented printed precision; V1 carries 134 cases, of which 79 are actually printed independent targets and 55 are derived-only references. Thus 412 printed-target comparisons, of which 412 match by the chosen tolerances; **this is not a YENI native end-to-end runtime pass**.

## High-value reference patterns

### SCWB negative/positive pair
- `2.pdf`, physical page 189 (printed 187), ground story: `V_is=34.8720 kN, V_ik=55.6859 kN, alpha_i=0.6262 < 0.70`. Page 3 explicitly flags two errors. Expected downstream action is redesign/classification/reanalysis; never promote this building to PASS because other checks pass.
- `3.pdf`, physical page 248 (printed 246): ground story `144.4710 / 144.4710 = 1.0000`; other story alpha ratios also 1.0. This is **a positive alpha example**, not evidence of full joint-level SCWB design validation.

### TS 500 7.6.2 / moment magnification
- `2.pdf`, physical page 186 (printed 184): the column case with `Nd=471.11 kN, Nk=1727.29 kN, Cm=1` gives `beta=1.549351615`. Story sums `sum_Nd=1975.94 kN, sum_Nk=15894.39 kN` give `beta_s=1.192764971`. The **conditional report-selected product** is `beta*beta_s=1.848012334`, matching printed `1.85`.
- `3.pdf` contains a contrasting no-sway amplification case with selected `beta=1.00`. The specific decision on TS 500 7.29 applicability remains an independent normative gate.

### Further cases
- Modal mass participation / six modes and two distinct cases per file.
- Base-shear modal scale `2.pdf:1.36` versus `3.pdf:1.00`.
- A1, B2, lambda effective drift, global theta, column compressive limit, shear friction, joint shear geometry and slab min thickness. Numeric source rows are retained with printed page references.

## Reproducibility and repository integration

The standalone offline archive distributed in ChatGPT is `TBDY_Offline_PDF_Golden_Bank_V2.zip`. It contains SQLite, all 3 source PDFs, comparison CSV, report, manifest, the previous V1 seed SQLite, and two isolated utility scripts. `scripts/verify_v2_offline.py` verifies all 333 newly added cases, source PDF SHA-256s, database hash and negative/positive alpha assertions **without running ETABS**.

**Status of checks actually executed:** original standalone `TBDY-Next-Engine` numerical core functions (modal, drift, theta, SCWB numeric) plus independent calculations of TS500 beta and other PDF outputs. The native `YENI` repository's full runtime was not installed/executed in this delivery; its algorithms were compared at the source-code contract level only.

### Next vertical slice acceptance
Apply these source-isolated fixtures to `YENI` R07–R14 with exact CheckID and model_id; retain printed-source versus derived-only tags. The negative alpha case must fail/trigger redesign, the positive alpha case must produce its limited affirmative observation, and a real `YENI` PMM/second-order/SCWB end-to-end golden run must be separately executed with source and report receipts. Never transfer force values between ideCAD examples and the ETABS `kompakt_b.EDB` archive.
