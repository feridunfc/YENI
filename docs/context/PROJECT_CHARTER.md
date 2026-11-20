# Project charter and source guide

Start each assignment at the repository-root [AGENTS.md](../../AGENTS.md).
This is the shareable edition of the architectural rules in the 14 November
master handoff. The recipe manifest preserves the historical document as
`MASTER-HANDOFF`, SHA-256
`71aebf28114f34709f70e2ddbd02b78159ab55deed950e7c6264a4706d12960f`.
Its branch list and publication hold describe that dated snapshot. The
[worker handoff](WORKER_HANDOFF_20261119.md) carries the current branch workflow.
[Original source manifest](../engineering/reference/recipe_20261118/delivery/SOURCE_MANIFEST.json)

## Calculation and review

- YENI owns one engineering runtime. Web and CLI enter through the same
  `EnginePipelineRunner`. ETABS data enters through the existing gateway.
  Use terminal or API access and keep `YENI_P0` read-only.
- Track physical geometry, the analysis model and generation, design choices
  and sealed results separately. Carry units, local axes, member, station,
  load combination and step with each demand. Use concurrent forces from the
  same cut for an interaction calculation.
- Work through one complete calculation at a time. Read its existing owner
  and tests, follow the inputs to the governing result, and compare that result
  with an independent example. Record the returned scope and the outstanding
  fields in the relevant GAP. Reports read the sealed result.
- Use [the architecture](../ARCHITECTURE.md) and the
  [engineering recipe and control mapping](../engineering/reference/recipe_20261118/README.md)
  to locate an owner. Use the [GAP register](../ENGINEERING_GAPS.yaml) and
  [verification ledger](../VERIFICATION_LEDGER.json) for current implementation
  and acceptance status.

## Where to look before requesting a source

| Source | What a worker can use |
| --- | --- |
| Bundled report comparisons | The [report manifest](../../src/tbdy_next/verification/data/SOURCE_MANIFEST.json) pins GOLDEN-01 through GOLDEN-04 and the historical arithmetic packages. The [comparison code](../../src/tbdy_next/verification/golden_gate.py) identifies each production call. |
| Independent PDF bank | The ledger identifies `SRC-PDF-V2` by SHA-256. Its three documents contain 716 pages, 467 reference cases and 245 structured observations. Search the read-only bank by document identity, page, member and quantity. |
| Original and compressed report editions | The original local 2.pdf, 3.pdf and 4.pdf matched GOLDEN-02, GOLDEN-03 and GOLDEN-04 respectively. The separate compressed fourth PDF has a different hash. The PDF-only SQLite tables include story-alpha and column/beam moment rows for both original reports 03 and 04. Use the requested report's own rows. |
| Selected ETABS model | The GAP-018 coverage matrix and `EV-COLUMN-JOINT-SLICE-20261119` identify the 87-column scenario. Its source, parent and model generation belong to the building calculation. The local resource index gives the private replay locations. |
| Historical handoff verifier | The attached `verify_handoff.py` is the same file as the one in the private handoff. It checked documentation and source integrity for `EV-HANDOFF-20261119` against `46dcb3c`. Its result records engineering tests and live ETABS as `NOT_RUN`. |

The private index resolves machine paths and connected accounts. GitHub workers
can start with the bundled report fixtures and the source IDs above.

## Resume the 44 report comparisons (GAP-016)

Run `python -B -m tbdy_next.cli inspect-golden-regression --require-complete`
from the checkout with the project interpreter. The current gate returns
exit 3 with 20 numerical matches, 20 insufficient-source labels and
four interpretation differences. Sixteen of the 20 open rows already contain
agreeing independent and reference values at their recorded tolerances; five
of these references are derived Boolean expectations, not printed numeric
results. The existing `INSUFFICIENT_SOURCE` classification therefore includes
missing production adapters and unresolved method or source qualification,
as well as missing inputs.

The existing `G01_THETA_GROUND` and `G01_THETA_UPPER` records now call
`engineering.story_pdelta.theta_ii_reference`, the same scalar operation used
by the production story-P-delta wrapper. GOLDEN-01 PDF page 28 supplies the
cumulative weights, average drifts, shears and heights for both directions.
The resulting dimensionless values are 0.007516853605560383 and
0.005997760967498111. The original IDs, source identity, expected values and
tolerances are unchanged. `EV-AUDIT-FIXES-20261120` records these additions.
The comparison verifies theta arithmetic and its units; source qualification,
the theta limit, beta and system acceptance remain separate. The production
wrapper retains its complete source and limit checks.
[Story-P-delta owner](../../src/tbdy_next/engineering/story_pdelta.py)

| Open group | Count | Next calculation or input |
| --- | ---: | --- |
| GOLDEN-01 scalar comparisons | 11 | Four spectrum coefficients/periods, two confinement quantities, two joint-shear equilibria, two sway indicators and one local-beta result. Their scalar source inputs are bundled. Complete the existing-owner adapters or the explicit stability-method decision described below. |
| GOLDEN-02 second-order comparisons | 5 | Four printed-symbol Eq. 7.29 Boolean probes have source inputs; distinguish that arithmetic from physical clear length, support and final-factor approval. The fifth compares the sway branch. Revised displacement, sum of axial force over length and storey shear are available on PDF page 185; bind both compared cases to the production sway calculation. |
| GOLDEN-01 full column checks | 2 | For biaxial capacity, bind bar coordinates, axes and concurrent N/M2/M3 to an independent capacity at that axial load and direction. For capacity shear, bind both end moments, clear length, the D branch and the design shear lower bound. |
| GOLDEN-03 and GOLDEN-04 | 2 | Each has an open second-order record. Select a page-bound case per original report, calculate it independently and connect the same inputs to the production owner. |

The next two G01 comparisons are the one- and two-beam joint equilibria on
page 194. Reuse the arithmetic owned by
`engineering.column_r10_live._attach_r13_joint_shear_and_transverse`, exposing
a shared scalar operation within that owner if needed. Retain the source
steel areas, strength, column-shear deduction and rounding allowance; this
does not qualify the complete physical joint. The six spectrum/confinement
quantities need adapters to arithmetic already present in `basis_linkage`,
`spectrum_reconstruction`, `engineering.rebar_selection` and
`column_engine.transverse_kernel`, not another request for the same source
numbers. The two sway indicators require a production operation within the
existing stability owner, `column_engine.ts500_column`. Its local-beta
adapter also needs the explicit Cm/end-moment interpretation and a
factor-greater-than-one reference; a result of 1.0 alone cannot diagnose a
wrong denominator.

The four separately classified interpretation rows ask how the final moment
magnification factor was chosen. On GOLDEN-02 page 186 the reported factors
round to the member and storey factor products. The method still needs the
applicable length, selection rule and transfer to the final moment.

The registered GOLDEN-01 cases on page 192 call the production section owner
and compare 1,920 kN (TBDY) and 2,880 kN (TS 500). The page 27 case calls the
production drift-ratio owner and compares 0.39743835 with the rounded 0.3975.
The public case IDs, source pages and test results are in
`EV-GOLDEN01-OWNER-BINDINGS-20261119`.
[Column section owner](../../src/tbdy_next/column_engine/ts500_column.py)
and [drift ratio owner](../../src/tbdy_next/normative_basis.py)
