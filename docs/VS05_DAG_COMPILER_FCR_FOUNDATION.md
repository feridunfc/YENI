# VS05 — RegulatoryCompiler / Engineering DAG / FCR Foundation

**Stage:** V05-ARCH-D1, candidate-only compilation and immutable accounting.

## Authority and original source

The architecture contract comes from the user-supplied
`TBDY_Mimari_DAG_TamRapor(1).txt` and
`TBDY_DAG_94_Dugum(1).mmd` (R1-C/R1-B research dated 2026-11-06).
An exact source graph is preserved in
`config/dag/tbdy_r1c_94_candidate.json`.

The imported graph has:
- **94 distinct nodes**
- **140 distinct directed edges**
- 16 SOURCE_GATE, 10 DERIVATION, 32 REGULATORY_CHECK, 36 DESIGN_CHECK
- **68 candidate check nodes**, not 68 executed design checks

This is a **research candidate**. All 94 nodes retain
`execution_authority=DENIED` and `compliance_status=NOT_PROVEN`.
The code does NOT copy or present 94 full TBDY/TS500 formula kernels.
The R1-C 10-stage runtime was only a source-level prototype and is
not silently installed as a second production engine.

## Programmatic acceptance contract

`src/tbdy_next/compiled_dag.py` implements:

1. `validate_candidate_catalog`: exact 94/140 cardinality; distinct
   IDs, known node types and types census; no unknown producers, duplicate
   or self dependency; acyclic deterministic topological waves; SHA-256
   of the entire catalog.
2. `RegulatoryCompiler.compile_candidate`: explicit model profile
   declaration, combo-book declaration and **explicit** CheckInstance
   inventory. No missing physical stories, columns, joints or foundations
   are guessed from the 94 static nodes. Instance IDs/grains are checked,
   sorted and frozen in a canonical SHA-256 plan.
3. `assess_candidate_plan`: FCR reconciliation of every expected
   CheckInstance ID. Missing outcomes become NOT_PROVEN, duplicate/unexpected
   outcomes are rejected, and an injected caller-supplied PASS is
   **never promoted** because node execution authority is DENIED.
   The FCR itself is canonical-hash sealed.
4. `tools/audit_vs05_candidate_dag.py`: strictly offline, accepts
   the exact catalog and an explicit *synthetic* plan input, writes a new
   reduced candidate DAG/plan/FCR receipt (exclusive write; no overwrite).

### Intentional missing approvals

An approved production `ApprovedModelProfile` and `ComboBook` are
**not available**. Self-declared `status=APPROVED` or an approval string
is untrusted. This version intentionally offers **no API** that grants
execution authority or changes source evidence into design PASS.

The first provided `tests/fixtures/vs05_candidate_plan_input.json`
contains only four illustrative instances:
`BASE_SHEAR:X`, `BASE_SHEAR:Y`,
`STORY_DRIFT:X:+4.50`, `STORY_DRIFT:Y:+4.50`.
Those are a **synthetic demonstration denominator**, not a complete
building-wide engineering census or the authoritative list for any real
ETABS model.

### Minimal invariant

```text
Original 94/140 candidate graph (DENIED)
      ↓ graph validation and topological wave freeze
Explicit candidate CheckInstances + Profile/Combo declarations (untrusted)
      ↓ RegulatoryCompiler.compile_candidate
Canonical candidate plan SHA + frozen expected instance denominator
      ↓ assess_candidate_plan
FCR: expected = observed + missing; NO missing or PASS elision
      ↓
Source-only receipt for diagnostic review
```

## Offline rehearsal

```powershell
python tools/audit_vs05_candidate_dag.py `
  --catalog config/dag/tbdy_r1c_94_candidate.json `
  --plan-input tests/fixtures/vs05_candidate_plan_input.json `
  --out .receipts/VS05/CANDIDATE_DAG_FCR.json
```

Expected: 94 nodes, 140 edges, zero executable nodes,
4 expected candidates, 4 reconciled NOT_PROVEN; 0 PASS.
Use a new filename for subsequent runs.

## Release and next engineering slice

This foundation **does not** replace the accepted VS04 single-button
live ETABS source pipeline. Future work must:
- Verify and approve the project's ModelProfile and exact nested ComboBook
- Bind physical/analysis model identities and independent analysis generation
- Compile the *actual* per-story/per-member/per-joint CheckInstance
  denominator (not just candidate DAG nodes)
- Register verified SourceGate / Derivation / FormalCheck producers
- Execute a bounded topological plan while preserving missing and
  REANALYSIS_REQUIRED results
- Have FCR reconcile the complete expected list into the same sealed
  `RunResult` that the left UI, JSON, HTML and Word report **only read**
- Prove actual live Windows/ETABS and independent normative oracles before
  permitting individual PASS/FAIL on a model

**Engineering release NOT_READY. VS05 branch MERGE=HOLD.**
