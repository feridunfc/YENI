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
exit 3 with 33 numerical matches, seven insufficient-source or method records,
and four interpretation differences across the same 44 comparisons. The
November 21 production adapters add 13 matches using the existing calculation
owners. See [the implementation verification](../engineering/vertical_slice_20261121/VERIFICATION_RESULTS.json).

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
| GOLDEN-01 sway phi | 2 | Bind `G01_SWAY_PHI_GROUND` and `G01_SWAY_PHI_UPPER` to a supported calculation with the report's full story populations and explicit method. The printed scalar inputs are available. |
| GOLDEN-02 sway change | 1 | `G02_SWAY_BRANCH_CHANGED` needs both story populations and the same method binding. Page 185 gives the revised displacement, sum of axial force over length and storey shear. |
| Biaxial PMM and capacity shear | 2 | `PMM_REPORT_GATE` needs bar coordinates, axes, concurrent N/M2/M3 and independent fixed-N, fixed-direction capacity. `CAPACITY_SHEAR_REPORT_GATE` needs both end moments, physical clear length, D and the design shear lower bound. |
| GOLDEN-03 and GOLDEN-04 | 2 | `GOLDEN03_REPORT_GATE` and `GOLDEN04_REPORT_GATE` need one independently calculated, page-bound second-order case per report and the same inputs in the production owner. |

The historical sway phi uses `1.5 × drift × sum(N/L) / story shear`. The
existing `column_engine.ts500_column` sway classifier uses paired first- and
second-order displacements. A future comparison needs explicit method and
population alignment. The separately implemented TBDY theta checks continue
to use the production story-P-delta owner.

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
