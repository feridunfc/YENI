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
from the checkout with the project interpreter. At runtime commit `ee2ecca` it
returned exit 3 with 15 numerical matches, 25 insufficient-source labels and
four interpretation differences. In 21 of the 25 rows the independent
calculation and the report value already agree.

| Open group | Count | Next calculation or input |
| --- | ---: | --- |
| GOLDEN-01 scalar comparisons | 16 | Use the printed inputs to call or complete each production calculation. Start with the two axial limits on PDF page 192 and the drift ratio on page 27. |
| GOLDEN-02 second-order comparisons | 5 | Four rows need the Eq. 7.29 length and support basis. The fifth compares the sway branch. The reported displacement, sum of axial force over length and storey shear are available on PDF page 185 of the revised report. |
| GOLDEN-01 full column checks | 2 | For biaxial capacity, bind bar coordinates, axes and concurrent N/M2/M3 to an independent capacity at that axial load and direction. For capacity shear, bind both end moments, clear length, the D branch and the design shear lower bound. |
| GOLDEN-03 and GOLDEN-04 | 2 | Each has an open second-order record. Select a page-bound case per original report, calculate it independently and connect the same inputs to the production owner. |

The four separately classified interpretation rows ask how the final moment
magnification factor was chosen. On GOLDEN-02 page 186 the reported factors
round to the member and storey factor products. The method still needs the
applicable length, selection rule and transfer to the final moment.

For the first three GOLDEN-01 rows, direct production calls reproduced
1,920 kN (TBDY axial limit), 2,880 kN (TS 500 axial limit), and 0.39743835
(drift ratio). These are the next three calls to bind to the registered
comparisons. See `EV-HANDOFF-RESOURCES-20261119` for the checked scope.
[Column section owner](../../src/tbdy_next/column_engine/ts500_column.py)
and [drift ratio owner](../../src/tbdy_next/normative_basis.py)
