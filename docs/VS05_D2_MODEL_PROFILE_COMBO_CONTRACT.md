# VS05-ARCH-D2 — Candidate ModelProfile and ComboBook Contracts

## Scope and evidence boundary

This sprint introduces typed, source-bounded *candidate* ModelProfile
and ComboBook contracts that feed the existing D1 RegulatoryCompiler/FCR.
No human-oracle or production approval authority has been issued.
The 94-node research DAG remains DENIED and NOT_PROVEN.

The source scope follows the owner-supplied architectural contract:
Physical/Analysis identities, versioned profile and combination graph,
exact source/units, fail-closed CheckInstance denominator, independent
algorithm rules and readonly reporting.

## Candidate ModelProfile

- Project/model/version ID; source_snapshot_sha256 must be exactly 64
  lowercase hex characters; unit declaration kN_m_C
- Exactly one base story and at least one upper-story candidate with
  height_m, elevation_m and stable story ID
- Explicit physical_elements with unique element ID, story ID,
  element type and I/J endpoint identifiers
- Missing vertical members per upper story are explicitly listed.
  An empty story cannot disappear from the candidate denominator.
- analysis_generation_id must be null. A caller cannot authorize
  an analysis generation with a string or boolean in a profile JSON.
- Geometry is structurally checked; it is not independently certified
  as a complete ETABS model census.

## Candidate ComboBook

- Exact named cases with source GUIDs, nested combo graph with
  typed CASE or COMBO references, explicit Decimal coefficient strings,
  unique IDs and closed/referential graph
- The supported candidate operator names are SUM, SRSS,
  ENVELOPE_MAX and ENVELOPE_MIN.
- Unknown source, duplicate/orphan and cyclic terms are rejected.
- Consumer roles require exact source reference and explicit
  requires_concurrent_vector intent.
- When a consumer requires a concurrent design vector, any nested SRSS
  or ENVELOPE operator causes fail-closed rejection.
- A SUM operator alone is NOT proof of same case, step, element, station
  or signed N/M2/M3 concurrence. Separate model/analysis source proof
  remains required.

## D1 candidate compilation and FCR

compile_limited_source_candidates validates both source snapshots
match and creates a bounded list:
  BASE_SHEAR:X and BASE_SHEAR:Y
  STORY_DRIFT:X:<upper-story>, STORY_DRIFT:Y:<upper-story> for each upper story.

This is NOT a complete building-wide regulatory CheckInstance inventory.
The D1 compiler freezes exact candidate instance IDs and typed source
declaration hashes. Execution remains DENIED, FCR retains missing
instances as NOT_PROVEN and prevents an untrusted PASS promotion.

Synthetic test example has 1 base story, 2 upper stories and
6 candidate instances. Falsified generation, wrong units, wrong SHA,
unknown source names, nested envelope, duplicate members, missing
vertical elements and source mismatch are tested negatively.

## Remaining engineering gates

Independent source-approved ModelProfile, actual full Frame/Area/Joint
denominators, exact ComboBook consumer roles, generation proof,
physical node displacements, qualified Tp, DD2/DD3, concurrent
demand, all normative conditions and a live one-run FCR/RunResult
integration remain OPEN.

VS05 merge HOLD.
ENGINEERING_RELEASE NOT_READY.
FORMAL_COMPLIANCE NOT_PROVEN.

Related branch audit: docs/LEGACY_BRANCH_AUDIT_20261107.md.
