# Public normal-pipeline examples

These files are **CONTRACT_FIXTURE / GENERATED_OFFLINE_NOT_ETABS**. All source
tables and signed forces are explicit synthetic inputs. No ETABS analysis,
original-building acceptance or design approval is claimed. `LIVE_ETABS` is the
existing adapter schema name; `example_context` records the actual synthetic
origin. Calculation outputs and capacities are produced by the existing runner.

The exporter normally names its input `input.source`. These public copies use
`synthetic_input.json` with identical bytes, as recorded in each source manifest.

From an editable checkout:

```sh
python -B -m tbdy_next.cli run-pipeline --source examples/vertical_slice_20261121/one_story/synthetic_input.json --design-scenario examples/vertical_slice_20261121/one_story/design-scenario.json --case Modal --out .receipts/public-one
python -B -m tbdy_next.cli run-pipeline --source examples/vertical_slice_20261121/two_story/synthetic_input.json --design-scenario examples/vertical_slice_20261121/two_story/design-scenario.json --case Modal --out .receipts/public-two
```

Expected conditional numerical results:

| Example | Columns / beams | Signed rows | Numerical completion |
| --- | --- | --- | --- |
| One story | 1 / 2 | 15 | 1 / 1; roof joint and Phi10/90 column ties |
| Two stories | 2 / 4 | 30 | 2 / 2; actual interior SCWB and Phi12/70 column ties |

Both retain engineering release `NOT_READY`. The two-story interior joint has
16 unique combination/axis/rotation comparisons. Its initial Phi10/90 trial is
partial; use `tools/write_vertical_slice_example.py --stories 2
--tie-diameter-mm 10 --tie-spacing-mm 90 --out <new-directory>` to reproduce it.
The six tests in `tests/test_vertical_slice_pipeline.py` additionally cover a
changed K/Rm basis, one genuine native-demand cage retry, missing native cuts,
web/CLI equality and report projection without calculation.

See [the implementation report](../../docs/engineering/VERTICAL_SLICE_20261121.md)
for method boundaries, the original-building handoff and all verification levels.
