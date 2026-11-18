# Live modal input binding — 2026-11-18

The existing pipeline now binds all **100 independently expected modal modes**
from one new ETABS acquisition. This completes the bounded native numeric getter
and identity-binding acceptance, including the repeat/report evidence below.
It does not close a structural engineering CHECK. R14/R15 remain **0 closed / 87
partial**; engineering release is `NOT_READY` and compliance is `NOT_PROVEN`.

## Source and implementation identity

- Published integration base: `baseline/local_import`,
  `a9d053f3422d981e3c576fe5e4c0d4b72549d150`, including the English recipe.
- Local work branch: `work/spectral-live-acceptance`, retained after fast-forward
  integration into the local baseline. The tested tree extends the published base;
  the final local commit is resolved from Git history. This increment is not pushed.
- Registered existing stage: `mixed-demand-components`, method
  `same-source-spectral-components.v6`. No additional stage or connection route.
- Live run: `RUN-77039b97519e45029e209f0031d72d36`.
- Source SHA: `9e5535ad2fe5749aa897a16023a3f7288062388df65f23013d243bbdb77bf640`.
- Results SHA: `c88b0245b764cef48534c966c4fb5d680d4b2cac20f4d14ea975193e5dafaac8`.
- Runtime package SHA:
  `92f34f2baf472c4e30cfbeee8721a7225416ed7cbf4bdf37326cf50fd47599bc`.
- Configuration SHA:
  `244536913d755dc77f372bd72f7a3f1f8ceb6d2f77837e3d73a98ab6d2c946a1`.

Private proof is under
`.receipts/verification/live-modal-numeric-20261118T184903Z/`.
Raw sources, model files, reports and wheel/build copies are not published.

## Observed failure and bounded correction

The first live acquisition rejected `ModalParticipationFactors` because the
native return omitted mode identity. A diagnostic-only change preserved the
next rejected return: all 100 rows contained `StepType = null`, `StepNum = 0`.
The same transaction's `ModalPeriod` return contained the explicit case/mode
identities. Its 100 same-case periods matched the participation periods exactly
and uniquely. Both earlier error receipts remain immutable and rejected.

CSI's [participation signature](https://docs.csiamerica.com/help-files/etabs-api-2016/html/eeed62fb-02ee-ccc7-294e-801669425bf0.htm)
and [period signature](https://docs.csiamerica.com/help-files/etabs-api-2016/html/07dd92be-7f20-d55e-676a-22af467bfa9c.htm)
describe the arrays but do not establish this observed omission behavior for
ETABS 23. The installed DLL signature and the retained live return are separate
evidence. The null/zero identity rule is a local, explicitly bounded adapter rule.

The existing `frame_force_capture.native_modal_rows` owner now accepts that
specific participation shape only when the companion period getter is valid,
contains the entire independently expected case/mode inventory, and provides
one exact same-case period match. Derived `mode_identity` records its mode and
`UNIQUE_EXACT_SAME_CASE_PERIOD` basis. The original StepType/StepNum and numeric
fields remain unchanged. The report shows the identity basis separately.

Repeated periods, unknown cases, missing companions, duplicate resolved modes,
other missing-step shapes and even one-ULP period mismatches cannot use this
fallback. Row position and nearest-period matching are never used. Explicit
native case/step identities retain their existing contract. Missing participation
modes remain in the denominator. An archived `CAPTURE_ERROR` cannot qualify input.

The numeric relationships retain the existing **32-ULP consistency budget**;
this is not a statement of solver accuracy. Display precision is still separate.
Nonfinite native returns retain bounded typed diagnostics without making the
whole source non-JSON. Selection/mode restoration failures still block capture.

## Acceptance evidence

| Criterion | Observed result |
| --- | --- |
| Same attached session, locked model, API units 6 | Verified before and after the new read |
| Both getters captured in existing all-mode transaction | 100 period rows; 100 participation rows |
| Independently expected mode identities | 100/100 bound; raw null/zero preserved |
| Independent arithmetic, no production calculation imports | Decimal(80), 500 comparisons, 0 outside tolerance; maximum difference 4 ULP |
| Native eccentricity definitions | 2/2 cases bound, default ratio 0.05, zero overrides |
| Temporary output and mode selections | Restored and verified |
| Stored receipt integrity | 16 receipts verified |
| Same-source explicit CLI repeat | 16/16 `IDENTICAL`, no missing or mismatched stages |
| Sealed report projection | 25 calculation entry points disabled; zero calculation/live calls; JSON/HTML equal |
| Existing user server on port 8876 | JSON and HTML match the sealed projection |

The Decimal audit independently reads the same native values and frozen period
inventory. It checks cross-API periods, reciprocal periods, circular frequencies,
squared circular frequencies and stiffness/mass ratios. These are 500 numeric
relationships, not 500 engineering CHECKs or independent physical analyses.

## Software verification

Environment: Windows 11 build 26200, CPython 3.12.10, Node 24.22.1.
[The tested-file manifest](../context/TESTED_FILES_MODAL_LIVE_20261118.json) records
445 raw file hashes, SHA `4dc69b85204ae68e076c4005b625c1cc4a9fffc3909a3bb6b2eb7314d6cfb196`.
It identifies the dirty tree over the published base; the
manifest's documentation/line-ending metadata hashes predate final checkpoint edits. Runtime, tests,
configuration and tool bytes are unchanged after verification.
The public manifest is LF-normalized; its 445 path/hash pairs equal the original
private pre-test CRLF manifest. Both manifest hashes are recorded in the ledger.

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_native_demand_sources.py -v` | 87 tests OK; 14 added over the published base |
| `.\.venv\Scripts\python.exe -X utf8 -B tools/test_offline.py` | 1,407 Python tests OK, one OS symlink skip; 10/10 JavaScript test files pass |
| `.\.venv\Scripts\python.exe -X utf8 -B tools/test_installed_wheel.py <private-wheel-directory>` | 241 tests OK from an isolated installed wheel |
| `.\.venv\Scripts\python.exe -X utf8 -B -m tbdy_next.cli run-pipeline --source .receipts/RUN-77039b97519e45029e209f0031d72d36/input.source --case Modal --out <private-repeat-directory> --compare-run .receipts/RUN-77039b97519e45029e209f0031d72d36` | All 16 receipts identical |

The wheel was built offline with `pip wheel --no-build-isolation --no-index
--disable-pip-version-check --no-deps`, from 317 tracked runtime/test/tool/config
and packaging files whose bytes matched the tested manifest. No stale build copy
was used. GitHub CI was **NOT_RUN** for this local increment.

## Remaining boundary and next acceptance

The run preserves 87 columns / 957 design pairs and 1,206 evaluated signed-static
PMM rows. It does not approve reinforcement cages, local second-order effects or
the complete spectral design method. The existing 44 golden production comparisons
remain 15 numerical matches, 25 insufficient-source records and four interpretation
differences; engineering acceptance remains ineligible.

Default eccentricity and zero overrides are definitions, not proof of applied
torsion forces. Spectrum amplitudes and active damping retain display precision.
Modal force reconstruction, simultaneity, governing SCWB axial demand, story-shear
allocation and spectral alpha iteration remain unqualified. No alpha iteration,
new ETABS analysis, model edit or model save was performed.

Next, extend the same source and calculation owners to establish amplitude/damping
precision and applied accidental-torsion contributions. Then independently verify
modal/directional aggregation before SCWB/story allocation/alpha consumption.
GAP-018 remains `PARTIAL`; source acceptance does not grant normative approval.
