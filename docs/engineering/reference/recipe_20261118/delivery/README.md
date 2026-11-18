# YENI recipe integration package

Read `RECIPE.md` or its PDF/DOCX rendering, then use `CHECK_MAPPING.json`, `GOLDEN_CASES.json`, `SOURCE_MANIFEST.json` and `VERIFICATION_RESULTS.json`. Schemas are in `schemas/`; current detailed run records are in `evidence/`. `REVISION_NOTES.md` explains preservation, additions and unresolved evidence differences.

## Safe local integration

The inspected published commit is `b255c3030c09c88a17bbec766fc2bb22682ad027`. The user-reported local `a2e26b664d9b2b217e828de2c1df0c3df26068b1` plus unfinished changes is NOT_INSPECTED. Do not replace local files with the inspected snapshot. Record actual HEAD, dirty/untracked relevant files and hashes, and review owner semantics and signatures before binding.

`tools/inspect_local_binding.py` is a read-only evidence collector. Its output is private local evidence, not automatic semantic approval. Run it with explicit paths:

```bash
python tools/inspect_local_binding.py --repo /path/to/current/YENI --mapping CHECK_MAPPING.json --output /private/path/LOCAL_BINDING.json
```

## Reproduce this delivery's independent checks

Use Python 3.12 or a compatible interpreter. `jsonschema` is required only for schema validation; the two arithmetic tools use the standard library. The validation run recorded here used Python 3.12.14. Install dependencies in your existing approved development environment if needed.

```bash
python tools/validate_delivery.py --root . --self-test --output evidence/LOCAL_DOCUMENT_VALIDATION.json
python tools/verify_golden_arithmetic.py --bank GOLDEN_CASES.json --output evidence/LOCAL_GOLDEN_ARITHMETIC.json
python tools/verify_priority_chain.py --fixture PRIORITY_CHAIN.json --output evidence/LOCAL_PRIORITY_CHAIN.json
```

To additionally verify the inspected source symbols, supply `--repo /path/to/the/pinned/source` to the first command. Changed target bytes must be reviewed; the pinned-byte check is intentionally not a compatibility certificate for newer local work.

The narrow existing-owner comparator accepts the original fetch manifest from the separate private evidence package:

```bash
python tools/compare_existing_owners.py --repo /path/to/the/pinned/source --bank GOLDEN_CASES.json --manifest /private/path/FETCH_MANIFEST.json --output evidence/LOCAL_OWNER_COMPARISONS.json
```

It compares only the 1080 kN and 1620 kN axial limits and the 24 mm minimum-eccentricity primitive. It replaces zero of the existing 44 production comparisons. A newer local owner requires an explicitly reviewed hash/signature/semantic binding; do not bypass the hash guard by substituting unreviewed manifest hashes.

## Counts and authority

73 original controls, 73 primary examples, 12 adapter fixtures, 333 recipe assertions, a separate historical PDF bank with a 333-record compared subset, and 44 historical production comparisons are separate populations. The additional priority chain is one fixture with 1,294 assertions. Three current owner primitive comparisons are a separate subset. Document/schema success and arithmetic agreement close no engineering check.

All JSON formula strings are explanatory. Do not execute them. Production integration calls the verified existing calculation owner through the current pipeline. No ETABS session, model mutation, reanalysis or native setter transaction is performed by these tools.
