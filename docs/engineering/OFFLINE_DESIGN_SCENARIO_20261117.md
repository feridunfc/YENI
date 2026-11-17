# Offline D1 — Source-bound candidate scenario and dependency guard

Base: `b6a95a09b5df459a5ab25ec504994fb7c5b579b0` on
`audit/pipeline-pmm-v6-20261117`. No live ETABS, COM, new analysis or main merge.

## Delivered behavior

`tbdy-next run-pipeline --design-scenario request.json` uses the existing
`EnginePipelineRunner`, selection owners, PMM, R08, R10, R14 and snapshot v2.
There is no second pipeline or solver. It changes only the beam/column policy
objects, never captured forces, geometry, cases, request scope or units.

The scenario request pins the original `input.source` byte SHA-256. The new
RUN contains the derived `input.source` plus the byte-identical original as
`parent.source`. Native source content has a separate semantic digest. Both
normalized selection policies, the scenario ID and parent/source hashes form
a deterministic scenario identity. A scenario is an **algorithm-selected
candidate**, not an engineer-approved or as-built reinforcement declaration.

Replaying a derived RUN requires its parent file. Nested scenario changes
are rejected: return to the original capture to make another policy choice.
A report or compare operation verifies the parent and the scenario binding;
a missing/corrupt parent cannot silently fall back to a legacy report path.
Existing historical RUN directories remain immutable. Old runs without a
scenario retain their original compatibility behavior.

The existing `--beam-selection` / `--column-selection` CLI overrides now
create the same explicit scenario record (`cli-selection`). They cannot be
combined with `--design-scenario`. A null policy means no selection, not a
silent default. Scenario policy keys and booleans are validated before work.

## Dependency pilot — deliberately conservative

Before scenario selection, the existing PMM member–combination ledger must
match the current source and known expected population. Signed pairs require
resolved PMM rows. Scalar envelopes remain nonconcurrent reference inputs;
they are never relabelled as signed PMM. All requested pairs require the
independently bound mesh and the supported configured-cut subset, without
missing/ambiguous cuts or unmatched analysis elements.

A missing required pair stops the run's **linked candidate cohort** (beam
selection/R10/local R08); upstream source, axial and PMM results remain
visible. The blocked pair and the full expected denominator stay recorded.
This intentionally conservative gate is NOT per-joint topological scheduling:
a single missing pair can stop the whole linked design cohort. It does not
claim that unaffected columns are physically inadequate.

After R10 selects candidates once, a second ledger records the candidate
selection and numerical section hashes. Each section must be the same
in-memory candidate object reported by R10 for that Unique ID in this run.
Missing/mismatched candidates stop downstream local design. R08 still uses
its existing same-run `SelectedColumnCage` handoff, not a second selection.
The ledgers and scenario lineage are sealed with report evidence and the
R14 result. JSON reports expose the same R14 block; HTML retains the stored
R14 result and input/result hashes, without a new calculation path.

No rule, capacity equation, station tolerance, solver or normative acceptance
threshold is changed by this work. `NOT_READY` and independent full-cut,
analysis-generation, k/sway/Rm/clear-length and spectral method gates remain.
The strict cohort gate is implemented for explicit offline scenarios. The
legacy non-scenario live path is not promoted to this new acceptance level.

## Codespaces

Keep the public repo separate from private evidence. Do not unzip a full
working-directory bundle over the checkout.

```bash
python -m pip install -e .
python tools/test_offline.py
python -m pip wheel --no-deps --wheel-dir /tmp/yeni-wheel .
python tools/test_installed_wheel.py /tmp/yeni-wheel

# Upload the existing private build.zip to Codespaces, outside tracked files.
python tools/replay_design_scenario.py \
  --bundle /path/to/build.zip \
  --scenario config/scenarios/offline_tight_ties_v1.json \
  --case Modal --out .receipts
```

The ZIP helper reads only the selected source entry, verifies its expected
hash, and calls the existing CLI. It does not extract .git, code, EDB or old
RUN directories. With an already available source:

```bash
tbdy-next run-pipeline \
  --source /path/to/original/input.source --case Modal --out .receipts \
  --design-scenario config/scenarios/offline_tight_ties_v1.json
```

The example has explicit 10 mm / 90 mm / four-leg beam stirrups, 90 mm column
spacing and a 1–4% column selection range. It is a **reference request**, not
an approved detailing solution or proof that these choices satisfy the model.
It is pinned to capture SHA
`85129fae59e4652a66022348f2f130e83f9128b64e814ce769c66b5cb987f71a`.

Run comparison (do not repeat policy flags on the already derived source):

```bash
tbdy-next run-pipeline --source .receipts/RUN-<scenario>/input.source \
  --case Modal --out .receipts --compare-run .receipts/RUN-<scenario>
```

The sidecar `parent.source` must remain next to the derived input. Same-code,
same-environment comparisons can be exact; cross-platform identity is not
assumed. Runtime paths and timestamps do not enter the scenario digest.

## Validation and remaining work

Automated source/policy/identity/dependency/snapshot/CLI tests are in
`tests/test_offline_design_scenario.py`. The installed-wheel test now also
runs this module and the 21 PMM v6 / native-coordinate focused controls.
The existing CI push filter includes `audit/**`.

Real-source evidence is maintained privately, not committed to the public
repository. The single-row negative experiment removes one internal-node
side from a copy of the accepted capture; the original is untouched. It
checks that the same expected 957 pairs remain, the affected pair is listed,
and linked candidate owners are not called. This is a mutation experiment,
not a finding that the original ETABS capture is missing the row.

Next: generalize this cohort guard into the existing StageRegistry's typed
per-member/per-joint dependencies, carry invalidation through actual demand
and cage revisions, and close normative applicability separately. In
particular selected SCWB neighbor handling and full demand feedback must not
be inferred complete from successful scenario execution. No new CHECK count
or whole-product compliance percentage is claimed by this delivery.
