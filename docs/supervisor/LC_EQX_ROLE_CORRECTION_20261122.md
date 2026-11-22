# LC_EQX design role and corrected worker priority

**Date:** 22 November 2026. **Inspected implementation:**
`388849d4073b60db4dd396bad9b748db538842bf`.
**Evidence:** `EV-LC-EQX-DESIGN-ROLE-CORRECTION-20261122`.

## 1. Project instruction and correction

The user clarified that LC_EQX is the equivalent-static earthquake reference
used for beta amplification, not a direct design-action case in this project.
In this context the amplification is the modal equivalent-base-shear factor
**beta_tE**, distinct from the TS 500 column beta/beta_s and the global
second-order beta_II. Record the actual directional case mapping from the
project's source; do not infer every role from a case name alone.

The earlier supervisor explanation incorrectly made the local LC_EQX C104
moment discrepancy a prerequisite to the main reinforcement/design path.
That priority is withdrawn. The current code trace does not pass this local
transition moment to either beta_tE or PMM. This correction supersedes the
unconditional W22-first assignment in the
[earlier review](C104_TRANSITION_REVIEW_20261122.md) and
[earlier experiment plan](c104_review_20261122/W22_TRANSFER_PLAN.json).
Those dated files and all achieved numerical results remain historical evidence.

The next delivery is the **actual case-role, scale and design-consumer trace**.
Further W22/W23 model changes are conditional on a demonstrated effect on a
quantity the project actually uses. This reprioritization does not establish
that the shared model or the true design demands are mesh-independent.

## 2. Different factors have different inputs

TBDY 2018 4.8.4.1, Eq. (4.31), scales modal results against the equivalent base
shear. In the existing implementation:

`beta_tE = max(1, gamma_E * VtE / Vtx_pre_beta)`.

The inputs are directional base shears and qualified system/boundary choices.
The local C104/W21/W22 M3 resultant is not an input. The relevant basement
boundary must follow the applicable project scope, including 4.8.4.2.
See the [published regulation, 4.8.4](https://www.imo.org.tr/Eklenti/89,depremyonetmeligipdf.pdf?0=).

| Calculation | Existing owner | Role and limitation |
| --- | --- | --- |
| Modal base-shear beta_tE | [normative_basis.py](../../src/tbdy_next/normative_basis.py), `eq_4_31_base_scale` | Uses equivalent/modal base shear, irregularity and basement qualification; no local M3 input |
| Required versus applied beta | [normative_checks.py](../../src/tbdy_next/normative_checks.py), `directional_base_shear_check` | Checks explicitly supplied pre-beta modal shear and applied scale; formula availability does not prove the private model's scale |
| Actual spectral combination components | [mixed_demands.py](../../src/tbdy_next/engineering/mixed_demands.py), `spectral_component_evidence` | Traces assigned combination definitions and source identities |
| Existing spectral replay/candidates | [spectral_envelope.py](../../src/tbdy_next/column_engine/spectral_envelope.py), [spectral_design.py](../../src/tbdy_next/column_engine/spectral_design.py) | Preserve source scale, with `spectrum_scale_reapplied=False`; recorded scale still requires project qualification |
| TS 500 local/story magnification | [ts500_column.py](../../src/tbdy_next/column_engine/ts500_column.py), `moment_magnification_factors` | Separate beta/beta_story owner; do not substitute beta_tE |
| C104 transition diagnostic | [coupled_wall_transition.py](../../src/tbdy_next/engineering/coupled_wall_transition.py), `project_transition` | Six-action first-order balance/mesh comparison; R08 attaches it as `boundary["coupled_wall_transition"]`, without direct beta_tE or PMM consumption |

The code also contains supplementary signed-static research paths. For example,
[story_static_reference.py](../../src/tbdy_next/engineering/story_static_reference.py)
explicitly reports `assigned_to_design=False`. Historical paired-static TS 500
research does not turn LC_EQX into an adopted design action. Conversely, the user
instruction is not proof that no historical diagnostic ever reads this case.

## 3. Corrected next calculation

1. **Recover actual roles.** Read the same-generation assigned combination graph,
   equivalent-static X/Y references and response-spectrum case definitions.
   Record which cases supply base-shear references and which supply design
   effects. Follow nested combinations. If an assigned design combination actually
   includes LC_EQX despite the declared role, expose that source/policy conflict;
   do not silently remove its force or relabel it as approved.
2. **Close the scale trace.** For each direction, record VtE, the modal base shear
   before beta, gamma_E and its evidence, required beta_tE, actually applied scale,
   units, model generation and applicable basement boundary. Identify whether
   scaling is already embedded in native spectrum results or is applied by a
   qualified consumer; prevent a second application. A case-scale number may
   include other unit/normalization factors and is not automatically beta alone.
3. **Compare consumed outputs.** Using retained compatible models first, compare
   the relevant base-shear/scale quantities and actual gravity, spectral and other
   assigned design demands at the physical cuts. Preserve directional-combination
   and spectral bound semantics; Max/Min components are not a newly simultaneous
   signed vector. Report unavailable rows as unavailable.
4. **Decide W22's priority from measured relevance.** If used quantities are stable
   while the auxiliary LC_EQX local M3 differs, retain that local diagnostic and
   continue the qualified design slice. If a used global quantity or actual design
   demand fails its declared budget, investigate the associated W22/W23 mechanism
   and then the smallest useful mesh experiment. No new mesh solve is required
   merely to reduce the auxiliary LC_EQX M3 difference.

The archived six-case diagnostic includes cases beyond LC_EQX. Their role must
also be read from the actual assigned combinations; the user correction does not
erase a relevant LC_H, gravity or other demand discrepancy. A diagnostic failure
is preserved even when it is not the governing product dependency.

**Required first receipt:** a source-bound table of case roles, required/applied
beta_tE and scale ownership, actual design-combination lineage, comparison of the
consumed quantities, and an explicit relevance decision for W22/W23. The prior
H/V experiment remains available if that decision requires it.

## 4. Preserved scope and verification

Preserve the twelve C104 free-body balances, 288 independently reintegrated
components, recorded mesh failures, six C29 story balances, complete C29 24-face
capacity scope and its conditional R14 result. No GAP status is promoted.
Coupled second-order applicability, construction continuity and actual design
demand adequacy retain their own exits.

This is a documentation and source-consumer review. It makes no production
change, performs no native analysis and claims no new engineering test run or
private scale verification. The [scope and next-action record](lc_eqx_role_20261122/SCOPE_AND_NEXT_ACTION.json)
pins the inspected source files and the [validation](lc_eqx_role_20261122/VALIDATION.json)
checks historical evidence preservation and documentation integrity.
