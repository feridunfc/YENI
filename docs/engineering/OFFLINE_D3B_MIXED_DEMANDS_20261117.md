# D3B — Mixed static component algebra and recorded spectral intervals

Date: 2026-11-17. Base commit: `929b51e93a2cfd91d20c43ad0e571490f6c6cd2a`.
Branch: `audit/pipeline-pmm-v6-20261117`. Main merge remains HOLD.
No live ETABS/COM, new analysis, source mutation, new solver or second pipeline.

## Implemented scope

The existing alpha owner can now isolate the earthquake case contribution of a
mixed **signed Linear Add** combination. `engineering/mixed_demands.py` expands
nested Linear Add definitions to exact rational **case** coefficients. The
native static-case load/pattern definitions establish the observed earthquake
versus other action classification; labels and user design-group names cannot
supply that evidence. ETABS `LoadSF` and legacy `SF` are supported; contradictory
fields, unknown roles, earthquake self weight, cycles and nonlinear operators
are rejected. A static case mixing action roles is outside this branch.

The earthquake functional is represented by a deterministic rational combination
of the captured signed outputs. For example, if C = 1.2 G + E and the same
source contains G and C, E = C - 1.2 G. A rank-deficient source cannot be repaired
with a guessed factor, least squares, spectral extrema or a different archive.
Every force component uses the same object, analysis element side, object station,
element station and step. Missing or ambiguous supporting rows remain explicit.
The original row hash and derived earthquake-component hash are distinct.

**Do not collapse separate cases just because their load patterns resemble one
another.** Their stiffness/initial-condition definitions may differ. This change
operates at native case identity, not inferred pattern-equivalent force identity.

Alpha uses the extracted earthquake shear at the existing common bottom cuts.
The existing D3 reference policy then applies the absolute 1/alpha factor to the
eligible combination's ORIGINAL M/V vectors; N and T do not change and factors
do not compound. Selection, R08 and capacity owners remain unchanged. This is a
reference implementation, not approval of a project's action roles, analysis
order, geometry or a complete structural design.

## Spectral path: actual advancement and explicit limits

A single `mixed-demand-components` stage in the existing registry records the
native six-component Max/Min intervals under `report_evidence`, before snapshot
finalization. It consumes the axial and PMM scope artifacts. The interval
arithmetic belongs to the existing `column_engine/spectral_envelope.py` owner;
no parallel spectral solver was introduced.

For a supported direct Linear Add route, recorded endpoints give midpoint and
half-width, preserving local axes and the compression convention N = -P.
Captured combination coefficients are retained once; no extra 100/30, D or
spectrum scale is applied. These **observed** midpoint/half-width values are NOT
independent recovery of constituent cases. A separate bank replay, with its own
verified archive identity and primitive cases, provides independent constituent
arithmetic evidence. The two physical source namespaces are not joined.

The frozen member/combination population, configured required cuts and additional
source cuts remain visible. Missing Max/Min, wrong units, unbound mesh, blocked
upstream records, duplicate scope or ambiguous cuts cannot become complete
interval evidence. One-ULP differences use the existing unique station matcher;
this does not merge the two analysis-element sides of a joint.

JSON and printable reports project the recorded artifact only. New evidence does
not authorize signed alpha, does not narrow the existing PMM reference box and
does not raise `canonical_design_pass_allowed` or engineering release status.

## Verification in this delivery

- 32 new public tests cover exact coefficient identities, deficient rank, native
  LoadSF/role handling, mixed shear separation, original-demand scaling,
  missing/opposite element sides, frozen spectral scope, unit/error propagation,
  recorded interval arithmetic and report escaping/no-calculation behavior.
- The 50 D3 tests remain successful. The full local offline run has 1,307 Python
  tests, ten JavaScript test files, and no reported skips or failures.
- Installed-wheel validation has 141 tests; this repeats tests in a separate
  environment and is not an additional engineering CHECK count.
- Real same-source PMM replay retains 87 columns / 957 pairs. The new spectral
  artifact contains 696 pairs and 3,216 interval cuts. Alpha remains
  `BLOCKED_INPUTS`, zero iterations, and R15 remains 87 partial/unbound.
- The separate verified SQLite/native ZIP bank replays 24 direct spectral
  combinations, 9,648 case-cut pairs, 19,296 native Max/Min rows, and 115,776 scalar
  comparisons. No comparison exceeds the existing 1e-9 absolute + 1e-12 relative
  tolerance. An independent Decimal(80) implementation reproduces the sums;
  maximum absolute discrepancies are 1.058e-12 kN and 4.505e-13 kNm.

Local environment: Linux, CPython 3.13.5. See the delivery evidence for exact
commands, run/result hashes, report fault injection and CI status. Private raw
captures, SQLite files and reports are intentionally not in this public commit.

## What is NOT closed

This delivery does **not** close the complete mixed/spectral design method or
independent full-building iteration acceptance. It closes a bounded mixed
signed component operation and the source/record/report path of spectral scalar
intervals. Positive mixed tests are explicit synthetic source examples, not
real-model structural acceptance.

The latest capture has eight response-spectrum mixed combinations, but lacks
primitive force records and a Load Pattern Definitions table needed for the
new signed separation branch. The separate bank has primitive case forces but
only mode 1 frame-force records in its Modal case. Aggregate spectral member
maxima are not signed, mutually concurrent story forces. Neither a midpoint nor
sum of independent maxima is promoted to a normative alpha denominator.

A complete spectral demand policy must still reconcile directional/modal
combination, SCWB governing axial-force conditions and story shear aggregation,
with an independent full numerical example. A successful scalar envelope replay
is not that acceptance. Existing analysis-generation, k/sway/creep/free-length,
physical joint/anchorage and general DAG scheduler gates remain open.

## Sources and reproduction

- TBDY 2018, 7.3.6.1–7.3.6.3, printed page 118: reference alpha scope and factor.
  Official text: `https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf`.
- CSI Response-spectrum analysis FAQ: modal combinations do not retain force
  correspondence; design envelopes and simultaneous response are different.
  `https://wikicsiamerica.atlassian.net/wiki/spaces/kb/pages/2006323`.

```bash
python -m pip install -e .
PYTHONPATH=tests python -m unittest test_mixed_design_demands test_alpha_design_iteration -v
python tools/test_offline.py
python tools/replay_design_scenario.py --bundle /tmp/build.zip \
  --scenario config/scenarios/offline_tight_ties_v1.json --case Modal --out .receipts
```

No manual PASS flags, no model-name special case, and no new live capture are
required to reproduce these software/source checks. Formal release stays NOT_READY.
