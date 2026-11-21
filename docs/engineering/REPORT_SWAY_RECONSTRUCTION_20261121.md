# Report sway and column reconstruction — 2026-11-21

## Result and scope

The reference work now follows actual report inputs through independent
arithmetic and the existing production comparison owner. Three GOLDEN-01/02
sway records have production numerical bindings. The unchanged 44-record
gate contains **36 numerical matches, four engineering interpretation
differences and four insufficient-source records**. It still returns
`REQUIRED_REPORT_GOLDEN_COVERAGE_INCOMPLETE`; engineering acceptance is false.
See `EV-REPORT-SWAY-RECONSTRUCTION-20261121` in
[the verification ledger](../VERIFICATION_LEDGER.json).

The private companion bundle contains 26 genuine Drive files: 20 DOCX and
six PDFs with 1,256 pages in total. All originals have source hashes and
ordered text/table extraction. This inventory does not mean that every
calculation, page or graphical annotation was independently checked.
The private bundle retains original bytes, source identities, exact XML
table/row/cell or PDF page locators, extraction scripts and numerical CSV/JSON
results. Raw reports, Drive IDs/URLs and complete row datasets are not
published in this repository.

## Source-linked workflow

The acquisition inventory distinguishes documents and editions by content
hash. DOCX extraction retains actual OOXML nodes, including merged cells,
instead of treating an expanded visual cell grid as the source. PDF records
retain physical page identities. Independent scripts recover printed inputs,
preserve signed case/end tuples and propagate display precision before
comparing quantities. Missing input identity remains explicit.

Only supported comparisons are then bound to existing production owners.
The independent arithmetic does not import the production operation it
checks. Similar member labels do not join different report generations;
in particular, no revision receipt establishes a col5-to-sway1 factor
transfer. The private scripts are verification evidence, not a second
production solver or an alternate pipeline.

| Evidence population | Executed result | Remaining boundary |
| --- | --- | --- |
| Nine DOCX sway reports | 54/54 Q and beta-s rows compatible with printed precision; 864/864 frame-column k rows reproduced | Full model population and engineering applicability are separate |
| Story critical-load sums | 53/54 sums reconstructed | One sway1 story/axis sum disagrees with the printed member population |
| col.docx, col1.docx, col5.docx | All 124 frame-column critical tuples bind to one same-case end; eight wall designs inspected | Six wall M22 summaries contain an unidentified transformation |
| Column and strongcol report arithmetic | 572 comparisons using printed inputs reproduced; 120 joints and ten story/direction summaries extracted | Printed capacities and low-axial classifications are source inputs |
| Minimum-eccentricity convention | 264 magnitudes compatible with the recovered convention | Two signs cannot be inferred from a raw moment printed as zero; normative applicability is separate |
| Joint-panel coefficient hypothesis | 240 rows compatible with the inferred material coefficient | The material coefficient is not explicitly bound in those reports |
| Six PDFs | 172 theta rows and 12 selected column-shear cases reproduced at printed precision | These are targeted calculations, not complete PDF or local TS 500 validation |

The arithmetic category does not convert reported failures into passes.
The reviewed column/joint sources retain 66 joint-panel demand exceedances
against printed limits and six maximum-axial demands above the corresponding
printed design bound. Their case-level evidence remains in the private bundle.

## Findings that constrain the next calculation

In `sway1.docx`, the disputed story critical-load total is 6,206.772 in the
report's force unit, while the printed member-axis population sums to
8,444.716. The sum includes both frame and wall labels. The other 53 story
sums are rounding-compatible. Wall k values also exhibit a distinct rule:
eight wall rows differ from the frame formula, so the frame-column rule
must not be applied to every wall without a qualified method.

For the six col5 wall exceptions, a fresh read of the original XML confirms
the extracted cells. N and M11 each identify a unique end of the stated
case, but the summary M22 is not a raw moment magnitude in any printed
same-story case/end. Sign, axis and end swaps do not repair the binding.
A separate wall-moment transformation is therefore present; its derivation
has not been recovered. No concurrent raw vector or PMM capacity is invented
to hide that gap.

The strong-column story coefficient is a shear-weighted ratio. Replaying
printed joint classifications reproduces its story sums and inverse-alpha
factors. That does not independently establish the reported section
capacities or the low-axial applicability exception. Likewise, the 240 panel
rows support a material-coefficient hypothesis, not an independently bound
material record. These categories remain separate in the private summary.

## Production scalar binding and unresolved factor interpretation

`column_engine/ts500_column.py::sway_phi_reference` evaluates the report scalar

`phi = 1.5 × drift_m × sum(Nd/L)_kN_per_m / story_shear_kN`.

It requires finite nonnegative drift and axial-load/length sum and strictly
positive shear. The adapter converts the printed displacement from mm to m
once. GOLDEN-01 page 186 and GOLDEN-02 page 185 are checked against the
existing hash-bound excerpts, including both printed directions. The
independent oracle uses its own arithmetic.

The two GOLDEN-01 results are 0.010214306765140325 and
0.00907018126759362. The GOLDEN-02 ground result is 0.09391286837852397.
The ground comparison therefore reproduces the numerical crossing of 0.05
from the original to the revised report. `G01_SWAY_PHI_GROUND`,
`G01_SWAY_PHI_UPPER` and `G02_SWAY_BRANCH_CHANGED` now classify as numerical
matches. Complete story populations, uncracked stiffness, required load
combinations and engineering sway classification remain unqualified;
`automatic_sway_assignment_authorized` remains false. This scalar does not
replace the separate TBDY theta owner or the paired end-moment criterion.

The independently reconstructed GOLDEN-02 magnification table contains 36
actual printed rows. All 36 adopted factors agree with **beta × beta-s**
within printed precision, while **zero** agree with MAX(beta, beta-s).
However, the product condition evaluated with the displayed lk values
triggers in **zero** rows. This is evidence of a source-specific
length/selection interpretation problem, not authorization to force the
product branch. The four existing interpretation records remain open.
Qualified physical/effective length, the adopted selection rule and transfer
to the final design moment still need a source-bound resolution.

## Verification and unchanged C29 boundary

The fresh full offline run on baseline
`35fd32326f9014e77a31080ee69591eea8775378` plus the recorded patch passed
**1,690 Python tests, zero skips and 11 JavaScript test files** using
`python -B tools/test_offline.py`. The ledger records the interpreter,
commands, log identity and tested-file manifest. The golden CLI retains its
44 IDs and incomplete-coverage exit status; test success is not release
approval. Historical worker test counts are not relabeled as this run.

This work did not run live ETABS, modify an EDB or recalculate the native
C29 comparison. `EV-C29-NATIVE-CONDITIONAL-TS500-20261121` remains the current
C29 evidence: 18 completed native gravity cases, 12 conditional revised
factors, 24 revised PMM sides at 18 physical case-cuts, and recovered
4-to-8 full-span comparisons. Its original conditional result and numerical
tables remain unchanged.

The full signed column-wall free body and wall-frame critical-load method
remain open, including `STORY_WALL_CRITICAL_LOAD_METHOD_UNSUPPORTED`.
Source reconstruction does not grant the varying-axial TS 500 idealization,
stiffness/creep choices or engineering acceptance. Continue through the
existing owners, retain unsuccessful cases in each expected population,
and keep the reference-report findings separate from live C29 outcomes.
