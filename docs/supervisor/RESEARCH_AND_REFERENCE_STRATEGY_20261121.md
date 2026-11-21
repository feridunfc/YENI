# Research and Reference Strategy — 2026-11-21

Date: 2026-11-21 UTC. Inspected YENI implementation: `c71a4dda4ab9453f428a38b3ed79931f8e6eeea3` on `baseline/local_import`.

This final research appendix records the completed source and method audit: read-only code findings, primary-source checks and eight proposed experiment cards. It does not report new ETABS acquisition, model analysis, production changes, numerical acceptance or regression runs. Existing C29 results cited below come from YENI's versioned evidence and were not independently recaptured for this appendix.

The canonical sprint plan is [ROADMAP_20261121.md](ROADMAP_20261121.md). Experiment identifiers in this appendix name methods and evidence tasks; they do not define a second sprint schedule.

## 1. Main finding and decision

The remaining engineering work consists of different problem classes. More report parsing will resolve some missing numbers and identify hidden conventions. It cannot recover information destroyed by response-spectrum aggregation, establish a coupled wall-frame critical-load model, or approve a standard interpretation. These require different experiments with different owners and acceptance records.

The highest-value immediate work is the existing same-generation column-wall free-body calculation. It can close the missing compression-source portion of GAP-009 before the coupled stability method is accepted. In parallel, the independent PMM oracle, the discriminating TS500 Eq. (7.29) comparison, and the actual alpha-feedback example can proceed using current owners. None requires restarting C29 deformation recovery or importing an older engine.

The full coupled stability calculation should have two explicit candidate routes: a derived system-stability method with a demonstrated relation to the intended design calculation, or a qualified direct second-order design route. A numerical buckling multiplier alone is not a validated replacement for TS500 story critical-load sums. An unresolved scalar mapping should trigger a recorded method decision and a bounded alternative experiment, not repeated attempts to populate an unsupported `Nk` field.

## 2. What was actually inspected

### 2.1 Reference heads

Repository heads were read through GitHub APIs during this audit. The branches below are named relevant snapshots; this is not an exhaustive review of every historical branch. In particular, only the first 100 TBDY branch records were listed.

| Repository | Inspected branch | Commit | Appropriate use |
| --- | --- | --- | --- |
| `feridunfc/TBDY` | `main` | `1440df1b9300f75b1e604204438f5cada9ebd247` | Formula provenance, directional applicability contracts and negative regression ideas |
| `feridunfc/Column-Engine` | `main` | `df754b202415a58508f60b27d96f731a7b840041` | Historical project identity; worker snapshot below contains the relevant D7 records |
| `feridunfc/Column-Engine` | `worker/d7-b7-codespaces-evidence-20261105` | `4f0afbeb67fd3e7c7d140cd9eb4eda2f191631ca` | Native acquisition recipes, explicit source limitations and rule-card structure |
| `feridunfc/Column` | `main` | `9269a00f5f5471ab68413c039912cafb2cf4db39` | Independent section-oracle concepts and radial admissibility checks |
| `feridunfc/Column` | `worker/v132-c3-c8-column-candidate-20261023` | `083be4f61f312ff8ffbe89f03290e5518adeb796` | Incomplete candidate contracts and pending verification inventory |

### 2.2 Useful assets and transfer risks

| Source at the pinned commit | Verified finding | Reuse decision |
| --- | --- | --- |
| TBDY, `tbdy_engine/design/columns/sway_stability.py` | Separates scalar phi from qualified directional proof; checks prescribed load/stiffness/source bases. Failure of the sufficient non-sway condition is not automatically proof of the opposite classification. | Adapt explicit applicability and negative-test ideas to the existing YENI owner. Confirm member-length convention: a common story-height expression is not generally identical to a sum of individual `N/L` terms. |
| TBDY, `tbdy_engine/design/columns/local_axis_sway_binding.py` | Binds actual local axes to global directional evidence. M3 bending concerns local-2 displacement; M2 concerns local-3. An oblique member can depend on both global directions. | Reuse the mapping questions and oblique-member verification cases. Do not assume global X equals local M2. |
| TBDY, `tbdy_engine/design/columns/slenderness_basis.py` | Distinguishes factual model length from normative unsupported/effective-length choices. | Use as a contract checklist. Retain YENI's existing clear-length/effective-length owners and source identities. |
| TBDY, `tbdy_engine/design/columns/moment_magnification.py` | The inspected old code places `1.3` in the wrong part of both Eq. (7.24) and Eq. (7.27) denominators: `1 - Nd/(1.3*Nk)`. | **Do not import this arithmetic.** YENI already uses `1 - 1.3*Nd/Nk` in `_magnification_denominator`. This is a historical transfer risk, not a newly discovered YENI defect. |
| Column-Engine, `tools/audit_d7b12_phi_readiness.py` | Its narrower 87-column signed-P evidence does not prove simultaneous N/M2/M3. The tool deliberately retains `native_design_n_m2_m3=NOT_PROVEN` and story phi as unavailable. | Reuse source-scope discipline. Do not describe this archive as the missing completed solver. |
| Column-Engine, `docs/D7_B14_WINDOWS_ETABS_CAPTURE_RECIPE_TR.md` | Documents typed native capture, complete censuses and restoration. | Use only ideas still needed by the current gateway. Re-discover live PID and installed API; do not revive historical machine defaults. |
| Column-Engine, `docs/D7_B14_EXISTING_SOURCE_RECOVERY_TR.md` | Records source searches that failed to prove whole-population or same-generation inputs. Geometry matching and assigned pier names are insufficient. | Preserve the exhausted-search result. Repeating the same archive search has low value unless a specific new source is identified. |
| Column-Engine, `tbdy_column_workflow/recipe_v11/RULE_CARDS.json` and `rules.py` | There are 27 cards, but implementation acceptance is not proved; the registry distinguishes a small number of leaf implementations from reference-only cards. The phi card's binary wording is stronger than the more careful TBDY proof contract. | Reuse the card schema with an actual consumer and qualified applicability. Card count is not implemented-check count. Resolve contradictory semantics explicitly. |
| Column, `SPRINT_B7_INDEPENDENT_ORACLE_EVIDENCE.md` and `tests/independent/oracle.py` | An independent strip-integral/fixed-N root/geometry implementation offers a useful numerical oracle. It shares material and strain assumptions with the compared implementation. | Reuse the verification design, not the source as normative authority. Independence of implementation is valuable even when assumptions remain common and separately unverified. |
| Column, `tbdy_column_core/engineering/radial_admissibility.py` | Checks finite nondegenerate boundaries, interior-origin assumptions and ray/boundary geometry. | Add the corresponding boundary questions to the current PMM review. A ray entry point is not automatically the governing resistance. |
| Column worker, `docs/c_series/C8_SUPERVISOR_BATCH_REVIEW.md` and `C01_C32_SUPERVISOR_MATRIX.md` | The inspected handoff explicitly says prepared, untested and not supervisor-reviewed. Numeric second-order/design-search acceptance is absent, and the matrix remains unverified. | Treat as incomplete candidate work. Do not rely on memory that the branch was accepted or import its kernel as finished production. |

Pinned source links: [TBDY](https://github.com/feridunfc/TBDY/tree/1440df1b9300f75b1e604204438f5cada9ebd247), [Column-Engine D7](https://github.com/feridunfc/Column-Engine/tree/4f0afbeb67fd3e7c7d140cd9eb4eda2f191631ca), [Column main](https://github.com/feridunfc/Column/tree/9269a00f5f5471ab68413c039912cafb2cf4db39), [Column candidate](https://github.com/feridunfc/Column/tree/083be4f61f312ff8ffbe89f03290e5518adeb796).

### 2.3 Actual report-source inventory and reconstruction scope

The [report reconstruction record](../engineering/REPORT_SWAY_RECONSTRUCTION_20261121.md), evidence `EV-REPORT-SWAY-RECONSTRUCTION-20261121`, supplies the following executed scope. These are existing project results, not new calculations performed for this appendix. The 26-file inventory has content hashes and ordered extraction; it does not mean that every calculation, page or graphical annotation was independently verified.

| Source population | Recorded reconstruction | Scope still open |
| --- | --- | --- |
| 26 actual report files: 20 DOCX and six PDFs; 1,256 PDF pages | Originals identified by content hash, with ordered text/table extraction | Complete engineering verification of every file/page is not claimed |
| Nine DOCX sway reports | 54/54 Q and beta-s rows and 864/864 frame-column k rows reproduced at printed precision | Full model population and engineering applicability |
| 54 story critical-load sums | 53/54 sums reconstructed | One printed sum disagrees with the displayed member population |
| Three column reports | 124/124 critical tuples bound to a same-case end; eight wall designs inspected | Six wall M22 summaries have an unidentified transformation |
| Column and strong-column report arithmetic | 572 printed-input comparisons reproduced; 120 joints and ten story/direction summaries extracted | Reported capacities and low-axial classifications remain source inputs |
| Minimum eccentricity and panel coefficient | 264 eccentricity magnitudes compatible with the inferred convention; 240 panel rows compatible with a material-coefficient hypothesis | Two signs are indeterminate at printed zero; the material coefficient lacks an explicit source binding |
| Six PDFs | 172 theta rows and 12 selected column-shear cases reproduced at printed precision | Targeted arithmetic is not complete report or normative validation |
| Fixed 44-record production golden gate | 36 numerical matches, four interpretation differences and four insufficient-source records | Engineering acceptance remains false |

The source-linked review also retains 66 panel demand exceedances and six maximum-axial demands above the corresponding printed bounds. Reconstructing those calculations does not turn their failures into passes. Raw reports and full row datasets remain private; the linked reconstruction note is the public evidence summary.

## 3. Primary-source register and its limits

All web retrievals below were made on 2026-11-21. CSI API pages describe the documented 2016 API. The installed ETABS type library and output settings must still be checked before using a signature or enumeration value in a current capture.

| ID | Primary source | Verified point and practical implication |
| --- | --- | --- |
| CSI-01 | [AreaJointForceShell API](https://docs.csiamerica.com/help-files/etabs-api-2016/html/e6826614-bf6b-d3cd-a0e5-5d70e06cbc07.htm) | Returns object/element/point, case, step type/number and six force components. Components use point-element local axes. Preserve these identities and transform the correct axes before combining wall forces. |
| CSI-02 | [SectionCutAnalysis API](https://docs.csiamerica.com/help-files/etabs-api-2016/html/be5b0573-7188-5a02-da50-9a3ab73bf28c.htm) | Supplies cut resultants with case/step identities; useful as a separate extraction-path check against integrated boundary forces. |
| CSI-03 | [Section cuts](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Section_Cuts.htm), [cut data](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Section_Cut_Data_Form.htm), [SAP output conventions](https://docs.csiamerica.com/help-files/sap/Output/Section_Cut_Output_Conventions.htm) | Mesh/group membership, selected side, reference origin and axes determine the free body represented by a resultant. Define the actual physical cut and included nodes before comparison. |
| CSI-04 | [Initial P-Delta analysis](https://docs.csiamerica.com/help-files/etabs/Menus/Analyze/Set_Analysis_Options/Initial_P-Delta_Analysis.htm) | Initial P-Delta uses a preload state for subsequent linear analyses. Nonlinear-case geometric settings are separate. A calculation's label alone does not identify its stiffness state or prevent double counting. |
| CSI-05 | [Buckling form](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Buckling_Form.htm) | Buckling factors belong to a defined spatial load pattern and stiffness state. Changing the reference-load magnitude rescales the factor. The result is not a universal column critical load. |
| CSI-06 | [Analysis Reference Manual](https://docs.csiamerica.com/manuals/etabs/Analysis%20Reference.pdf), July 2016, revision 15 | Generalized eigenbuckling is a system problem. Joint-force conventions and edge-constraint interpolation explain why a frame adjoining shell edges must be treated as a coupled assembly. Relevant locations: PDF p. 370/printed 349; PDF p. 69/printed 48; PDF p. 204/printed 183. |
| CSI-07 | [RSA torsional-irregularity FAQ](https://web.wiki.csiamerica.com/wiki/spaces/etabs/pages/1474589/Torsional%2BIrregularities%2Bcheck%2Bfor%2BResponse%2BSpectrum%2BAnalysis%2BRSA) | Spectrum maxima do not retain correspondence or timing between different response quantities. More digits or report examples cannot recover a unique simultaneous N/M/V state. The FAQ's separate ASCE-specific design discussion is not adopted here as a TBDY rule. |
| CSI-08 | [Response spectrum settings](https://docs.csiamerica.com/help-files/etabs/Menus/Define/Load_Cases/Response_Spectrum.htm) | Modal and directional combination choices, damping, scaling and diaphragm eccentricity are distinct model inputs. Reconstruct them separately before comparing a reported resultant. |
| CSI-09 | [Deflected configuration](https://web.wiki.csiamerica.com/wiki/spaces/kb/pages/2005292/Deflected%2Bconfiguration) | Spectrum-combined deflections lose the signs needed to describe a physical simultaneous deformed shape. |
| CSI-10 | [Nonlinear-static output option](https://docs.csiamerica.com/help-files/etabs-api-2016/html/a967c5f3-3f6f-4cef-45f3-d9c331494e55.htm), [multistep-static output option](https://docs.csiamerica.com/help-files/etabs-api-2016/html/577536f1-68a6-1d01-d552-84a4a37e5256.htm) | The public pages do not establish the meaning of every integer option. Read the installed API/getter and verify the returned step roster; never guess which integer means all steps. |
| OS-01 | [OpenSees moment-curvature example](https://opensees.berkeley.edu/OpenSees/manuals/ExamplesManual/HTML/3886.htm) | Demonstrates a fiber section under controlled axial force and curvature. It is an independent numerical experiment pattern, not a TS500-approved material model or a ready PMM acceptance oracle. |
| TBDY-01 | [AFAD official entry](https://afad.gov.tr/turkiye-bina-deprem-yonetmeligi), [official PDF](https://www.afad.gov.tr/kurumlar/afad.gov.tr/2309/files/TBDY_2018.pdf) | Primary official provenance. Direct page/PDF opening encountered timeout/502, but indexed official clause text and the user-provided official-format PDF were available. |
| TS-01 | User-provided TS500 PDF, opaque private source identity below | Text read successfully and printed p. 27 visually verified. This identifies the supplied edition's wording and formulas; it does not certify the current consolidated edition. |

The TS500 PDF is 83 pages, 898,520 bytes, SHA-256 `d925114d01a1de2baee63738bc0da0112b547b58526c3394843c36ee66722d44`. It is the February 2000 text with appended T1/2001 and T2/2002 amendments. The audit did not verify a current consolidated TSE edition or project adoption. Keep that qualification as a specific source-profile task. It need not stop numerical method development against this explicitly named supplied edition.

The visually verified source page is PDF p. 34 / printed p. 27. The public audit records the standard hash, edition, page and finding; original document bytes, rendered pages and private source access details are not included.

## 4. Standard interpretation findings that change the work plan

### 4.1 TS500 approximate-method applicability is a real boundary

The supplied TS500 §7.6.1 describes a general second-order approach considering material nonlinearity, cracking, creep and shrinkage. It allows the approximate method subject to its stated slenderness limit, `lk/i <= 100`. Section 7.6.2 describes that approximation for columns whose section and axial force do not vary along their height. Accordingly, a self-weight `Nmax` substitution or a wall-coupled member is an explicit idealization requiring validation and an acceptance decision; being able to calculate a beta is not sufficient.

The §7.6.2.1 paired-analysis route compares first- and second-order column end moments under the same horizontal and vertical loads and linear-material assumptions, with its 5% criterion. The alternative phi route refers to the whole resisting system, uncracked sections and its stated load combinations. The existing gravity-only C29 demonstration therefore cannot by itself establish a complete automatic directional sway classification. It remains a verified numerical result within its declared scope.

These two routes should become explicit method choices. The worker should freeze the correct load/stiffness/population basis for one route and compute it through the existing owner, instead of mixing cracked design EI, a gravity-only drift and a differently generated story shear into one phi value.

### 4.2 The denominator is confirmed; the old code is not a safe oracle

The supplied PDF, PDF p. 34 / printed p. 27, visually confirms the denominator forms `1 - 1.3 Nd/Nk` and `1 - 1.3 sum(Nd)/sum(Nk)`. Current YENI's `column_engine/ts500_column.py::_magnification_denominator` already implements this placement correctly. The inspected old TBDY file does not. This is a strong reason to keep historical assets subordinate to a source-linked formula card and current owner tests.

### 4.3 Eq. (7.29) has a source conflict, not merely missing code

On the same visually inspected page, the prose refers to slenderness using free length, while the displayed expression uses `lk`. The supplied text says to use the larger individual/story factor ordinarily and their product under the exception. YENI's report reconstruction shows 36 recovered factor rows matching a product while none of those displayed-lk conditions selects it. Reproducing all 36 products establishes the report's numerical behavior; it does not prove its normative branch or missing hidden inputs.

The next reverse-engineering experiment must distinguish the alternatives. Calculate both length readings, rounding intervals and possible reported-hidden-input effects on cases near the branch boundary. The method record must explicitly name the adopted interpretation, remaining source conflict and approval status. A worker can implement and report both numerical interpretations before that decision; it must not silently change all cases to product because a report did so.

### 4.4 Alpha feedback is a calculation with separate system boundaries

The user-provided TBDY text confirms the §7.3.6 distinction between `0.70 <= alpha_i < 1` and `alpha_i < 0.70`, and describes where the `1/alpha_i` demand increase applies. The former can support a real downstream feedback demonstration; the latter entails the specified structural-system consequences and cannot be repaired simply by iterating a prepared success dictionary. Section 7.3.7 then links capacity shear to signed end-capacity/demand conditions and brittle limits. A complete example must use the actual incident-beam and selected-column capacities and re-run affected consumers.

## 5. Method decision matrix

Legend: **RE** = reverse engineering of an existing report; **Native** = exact native source acquisition; **R&D** = analytical/numerical method experiment; **Decision** = explicit engineer/source-profile acceptance. These labels are work types, not approval statuses.

| Open question | RE can establish | Native evidence required | R&D required | Decision / consumer |
| --- | --- | --- | --- | --- |
| Column-wall story compression, GAP-009 | Sign and reporting convention, expected result scale | Same model/generation/case/step and actual wall/frame cuts; independently obtained upper loads | Integration and equilibrium verification | Existing `gravity_story_basis.py`; source scope can close separately from critical-load method |
| Coupled wall-frame critical behavior, GAP-009 | Historical assumptions and reported factors | Geometry/edge constraints/EI/load distribution, including geometry changes | Coupled subsystem, mesh, geometric stiffness and direct second-order comparison | Choose supported system method or direct-design route; no invented wall `Nk` |
| Sway classification / Eq. (7.29), GAP-009/016 | Printed arithmetic, hidden-length candidates, threshold behavior | Qualified load roster, whole-system population, axes, stiffness and exact state | Discriminating comparisons and uncertainty around report rounding | Versioned interpretation and applicability; existing TS500 owner |
| PMM, GAP-010 | Report inputs and outputs at matched N, direction, cage and units | Actual bar coordinates, materials and demand identity | Independent integration/root/radial-capacity and convergence experiments | Numerical qualification plus material/detailing acceptance; existing section owner |
| SCWB and alpha feedback, GAP-013/014 | Reported joint selection, ratio and amplification conventions | Complete beam/column topology and compatible signed demand/capacity state | Actual nontrivial feedback through selection, shear and joint consumers | Applicable-alpha and amplification policy; existing alpha/SCWB owners |
| RSA component mismatch, GAP-018 | Scalar aggregation conventions and printed precision intervals | Full-precision modal amplitudes, modes, damping/correlation, scaling and eccentricity contributions | Reconstruct exact scalar quantities and locate residual mechanism | Existing shared spectral owner; precision mismatch can close without inventing concurrence |
| RSA simultaneous design vector, GAP-018 | Only what the report explicitly assumes | Signed static/stepwise evidence where appropriate, or enough modal data for the chosen design policy | Bound/design-envelope method with demonstrated coverage | Explicit design combination policy; a unique time-concurrent vector cannot be recovered from Max/Min |
| Actual alpha below one | Known report candidate with all incident elements | Full compatible source/cage/demand state | Executable example showing changed downstream result | No replacement of stage outputs by canned dictionaries |
| General wall/pier design, GAP-015 | Missing factor conventions and six unidentified wall M22 transforms | Actual pier/wall assignments, local axes, cuts, loads, mesh and reinforcement | Qualified wall capacity, shear and detailing methods | Separate wall scope; finishing the C29 frame slice does not finish this owner |

## 6. Executable experiment cards

The following eight cards are proposed tasks, not completed calculations. The combined E09-E / E16-A entry is one card. Use existing calculation/acquisition owners. An analysis sandbox model is an evidence source for a method experiment; it is not a second production pipeline. Each completed card must return numerical outputs, unresolved cases in the denominator, method/source identities and a sealed consumer result where that consumer exists.

### E09-A — Finish the signed column-wall free body first

**Input:** Existing finest METHOD source, first-order `C29G_U_F`, the two already identified physical cut planes. Freeze expected populations independently: +0.00 has 32 columns plus 21 wall objects; +4.50 has 32 plus four. Counts describe physical contributions; generated shell-joint rows will be more numerous.

**Procedure:** Reuse the current gateway. Read installed output-setting meanings and restore every temporary selection. Capture actual signed step rows; retain shell element, point, case, step and axes. Define which side acts on the upper body, transform forces to global coordinates once and deduplicate by physical contribution. Obtain external upper-body loads and self-weight independently from the model's loads, multipliers and geometry/material quantities, not by relabeling the force sum as a load. Include all relevant cut boundaries and imposed forces. Where available, compare with native `SectionCutAnalysis` as an independent extraction route.

**Output:** Two case-cut rows first, then all three first-order gravity cases at both planes: expected/evaluated counts, signed force sum, compression sum, independently calculated external force, residual and each contributor's lineage. Once vertical balance works, extend the coupled-subsystem record to six resultants about one stated origin; use `M_O = M_P + r_OP x F` during origin transfer.

**Gate:** Existing `gravity_story_basis.py` uses 0.01 kN absolute / 1e-6 relative tolerance for vertical balance. Apply its actual `isclose` semantics and preserve the separate signed-sum versus compression-sum distinction. Missing wall rows or a mismatched state are failures of source completeness, not zero contributions. A native cut and an integrated cut from one solver cross-check acquisition but are not independent validation of the physical model.

**Exit:** Close the supported free-body/compression subtask while retaining `STORY_WALL_CRITICAL_LOAD_METHOD_UNSUPPORTED` until E09-B/C is decided. Do not rerun all 18 completed METHOD cases just to prove a newly captured case roster if existing solved generations are valid.

### E09-B — Qualify the coupled physical subsystem and direct second-order behavior

**Input:** The actual C104/W21/W22 coupled assembly, including the real geometry change at elevation -1.50 m, frame-shell edge constraints, tributary loads, boundaries, material/EI basis and source generation. This is a different method question from the completed standalone C29 deformation convergence.

**Procedure:** Establish a first-order signed equilibrium model at each relevant physical cross section, then compare first- and second-order responses under identical load and stiffness bases. Refine the actual coupled mesh and preserve common physical cuts, not only generated element stations. Track six section resultants, load transfer, local/member/global deformations and candidate governing sections. Use the same source for an independent reduced analytical model only where its kinematic assumptions are justified.

**Output:** A convergence table separating discretization error from changes of EI, creep or boundary idealization. Identify whether internal frame force changes represent exchange with walls rather than a defect in force extraction. Report both geometries and the region around the change.

**Gate:** Prespecify numerical tolerances before examining the next run; retain existing C29 tolerances only for the quantities and scope they were designed for. A direct linear-material geometric second-order result is useful numerical evidence. It does not by itself satisfy every requirement of the TS500 general nonlinear-material approach. Record which additional material/creep effects are modeled, bounded or still awaiting an adopted method.

**Exit:** A supported direct-demand candidate can feed the existing design-demand and PMM owners under an explicitly versioned method. Keep scalar magnification unavailable where its assumptions are unproved; do not prevent the valid direct-demand candidate from being calculated and reviewed.

### E09-C — Use buckling as a system experiment, then decide the mapping

**Input:** A frozen compatible gravity-load pattern, actual geometric-stiffness contribution, boundary conditions and the E09-B stiffness model.

**Procedure:** First verify the chosen numerical setup against an analytical Euler/member-frame case. Then extract several lowest modes of the coupled assembly; examine mode localization, mesh and stiffness sensitivity. Repeat for materially different spatial load patterns. Record the exact reference load magnitude so eigenvalue rescaling cannot be mistaken for changed physical resistance.

**Output:** Critical multipliers, mode identities/shapes, load-pattern sensitivity and comparison with the direct second-order response trend. Derive, rather than assume, any proposed link to the story factor required by the design owner. A global multiplier multiplied by a story axial sum is not automatically that story's `sum(Nk)`.

**Gate:** The mapping must preserve the intended degrees of freedom, participating members, load pattern and axis meaning and must reproduce independently understood limiting cases. Solver agreement alone is insufficient. If no defensible scalar mapping is obtained, document the failed assumption and choose the qualified direct route from E09-B for the coupled scope.

**Exit:** A concrete method decision with a demonstrated applicability domain, instead of an arbitrary critical-load number chosen to populate a table.

### E09-D — Bound what the self-weight Nmax idealization actually proves

**Input:** Actual variable axial distribution and the frozen `Nmax` scenario, identical EI/boundaries and physical cuts.

**Procedure:** For a narrowly defined beam-column stability model with nonnegative compression and fixed stiffness/supports, test whether pointwise replacement by `Nmax` orders the geometric-energy term as intended. Separately compare actual signed section moments, deformations and PMM over the already available refined cases. Do not infer the latter bounds from the former energy statement.

**Output:** A statement of the exact mathematical domain, proof or counterexample, and numerical difference by governing quantity. Retain local N for minimum eccentricity and section PMM where the existing method does so.

**Gate:** A bound on a Rayleigh stability quotient does not establish componentwise bounds on every signed response or PMM utilization in a coupled building. Preserve `ADOPTED` versus `INDEPENDENTLY_VERIFIED` status for the idealization. If useful only as a sensitivity/reference, keep it as that class while the direct source-based branch progresses.

### E09-E / E16-A — Resolve the discriminating sway/report questions

**Input:** Existing source-linked report rows, all printed geometry/material/factor inputs, their precision intervals and the supplied TS500 page.

**Procedure:** Select cases that can actually distinguish free-length and effective-length readings, product and max selection, or hidden rounding. Calculate both readings through the current TS500 owner. For phi, choose the whole-system prescribed-load route or the paired first/second-order route and explicitly separate its stiffness assumptions from the design-EI scenario. Bind directional evidence to real local axes, including an oblique member.

**Output:** A compact truth table of branch predicates, factors and final design moments; exact source locations; rows that distinguish hypotheses; and a decision record with adopted interpretation and alternative result. If every existing case lies on the same side of both predicates, state that it cannot decide the interpretation and obtain the specific missing input/case.

**Gate:** Matching a rounded final number is insufficient where different intermediate rules can produce it. Do not enlarge a tolerance to turn a convention difference into a numerical match. A report oracle stays a report oracle until its applicability is independently accepted.

### E10-A — Independent PMM at the actual fixed N and demand direction

**Input:** One actual complete report example and the C29 selected cages, with bar coordinates, cover, materials, axes, strain/material assumptions and matched design-force identities. Do not substitute a different cage with the same total steel area.

**Procedure:** Establish analytical limits such as pure axial and suitable symmetric bending cases. Implement an independent numerical oracle using separate strip/fiber integration and independent root/geometry logic; the Column B7 work is a useful blueprint. Sweep fixed N and moment direction, locate all relevant roots, refine the angular and spatial integration grids, and verify radial-domain assumptions. A second solver such as OpenSees can add a check only after the constitutive law and control problem are matched.

**Output:** Production versus independent resistance at identical N and direction; equilibrium residuals; spatial/angular/root error estimates; resultant utilization; and counterexamples near axial and ray-admissibility boundaries. Show implementation independence and separately list shared assumptions.

**Gate:** Choose absolute/relative tolerance budgets in capacity units before comparison. A loose historical regression tolerance is not the oracle's numerical error estimate. Do not accept a convex-hull or radial construction outside the domain in which it has been demonstrated to represent the intended capacity boundary.

**Exit:** Qualification of the tested section-method domain, then consumption by the current `section_capacity.py` and report owner. This can progress in parallel with E09-A; it does not require a solved full wall-frame stability theory.

### E13-A — A real alpha feedback run that changes a downstream decision

**Input:** Prefer an existing report/building case with `0.70 <= alpha_i < 1`, complete incident beams, both compliant and deficient joints as applicable, candidate cages and source-compatible demands. Choose a case that actually changes a controlling moment/shear, utilization or reinforcement decision.

**Procedure:** Compute the original SCWB/alpha from current owners. Apply the appropriate immutable demand transformation exactly once. Re-run affected selection, PMM, capacity shear, transverse-reinforcement and joint consumers. Recompute dependent capacities/alpha where the algorithm requires it; record every iteration and stopping condition. If a stiffness or geometry change invalidates the native demand generation, return to the declared reanalysis policy instead of keeping stale forces.

**Output:** Before/after source vectors, transformation identity, alpha, selected cage, governing PMM/shear/joint values and dependency invalidations. Include an alpha=1 control and the alpha<0.70 structural-system boundary separately.

**Gate:** The positive case must call real stage owners, not inject already-successful results. Replaying the same run must not accumulate a second alpha factor. If no existing report is complete enough, document the precise missing fields and qualify an independently analyzed physical benchmark as a separate example; never relabel it as the original building.

### E18-A — Finish scalar RSA reconstruction, then make the design-policy choice

**Input:** Existing bound modal sources, installed analysis settings, full-precision amplitudes and the known residual subset. Current project records identify 4,686 of 4,824 scalar comparisons explained and 138 needing further resolution; treat that census as repository evidence until independently rerun.

**Procedure:** Partition the residual by source generation, quantity, direction, mode roster, rounding, scaling and diaphragm-eccentricity contribution. Reconstruct one representative mismatch end to end using the shared spectral owner, then apply the explained correction to the frozen full population. Preserve signed modal vectors and the exact correlation/scaling basis. An extra report containing only extrema does not repair missing modal precision or timing.

**Output:** Full fixed-denominator residual table, mechanism for each class, exact arithmetic and updated scalar-consumer result. Separately present candidate design policies: an approved envelope/bound with a proved coverage domain, or compatible signed static/stepwise cases within their declared purpose. Neither is to be represented as a recovered simultaneous spectrum history.

**Gate:** Interval corners are not automatically a proof of every PMM maximum over a continuous N/M domain; demonstrate the relevant monotonicity/convexity/coverage or search the remaining domain. Do not use independently maximized RSA terms to claim force equilibrium or actual alpha partition. Policy adoption and numerical scalar reconstruction have separate acceptance records.

## 7. Dependencies and method decisions

[ROADMAP_20261121.md](ROADMAP_20261121.md) owns sprint numbering, scheduling and integration order. The table below records technical dependencies for those sprints.

| Work package | Dependency and concrete exit |
| --- | --- |
| Shared source acquisition | Freeze valid model/generation identities, obtain exact first-order wall cuts and missing modal/eccentricity data through the current gateway, and restore selections. Confirm existing authority before model-analysis mutations. |
| E09-A free body | Complete two cuts in one real gravity case, then the other four case-cuts. Publish the actual equilibrium table and the supported GAP sub-scope independently of critical-load-method acceptance. |
| Parallel reference tasks | E10-A PMM, E09-E / E16-A sway interpretation, E18-A scalar residuals and E13-A example selection can proceed once their own source identities are complete. They share identities rather than mutable engineering outputs. |
| Coupled method experiment | E09-B and E09-C need the coupled physical geometry, load and boundary basis. E09-D bounds the existing idealization's applicability. A missing method calls for an experiment, not another search of an already exhausted archive. |
| Method decision | Compare the calculated candidates and their applicability; adopt a justified scalar method or a qualified direct branch. Do the calculable work before requesting a decision on the resulting concrete evidence. |
| Production integration | Extend existing owners, execute real consumers, seal the normal-runner result and update evidence IDs and GAP sub-scopes. Run the relevant code and integration gates for implementation changes. Documentation-only research is not a new engineering run. |

A research sprint exits with a supported calculation consumed by the existing pipeline, or a sharply delimited rejected hypothesis with numerical counterevidence and the next viable method candidate. Keep the complete standalone-column slice usable while the coupled method advances; retain every required physical member in building force accounting.

## 8. Work that should not be repeated or overstated

- Do not restart the completed native 2/4/8 C29 full-span recovery merely because GAP-009 remains partial. The missing coupled/global acceptance is a different scope.
- Do not call the old TBDY/Column engines authoritative because their directory or constitution looks more complete. Their inspected arithmetic and handoff records include known defects and explicit unfinished acceptance.
- Do not count 26 report files as 26 independently verified examples, 27 rule cards as 27 live checks, or test counts as engineering release evidence.
- Do not infer same-generation data from an unchanged EDB hash or a locked model alone.
- Do not put missing walls at zero axial force to obtain a complete-looking story sum. Conditional frame-only results and the complete free body must remain distinguishable.
- Do not reinterpret a spectrum Max/Min table as simultaneous signed forces, even after exact scalar reproduction.
- Do not close a source-conflict or engineering-acceptance gate by making the code reproduce an undocumented legacy convention.

## 9. Public audit limits and reproducibility

This audit inspected 15 named files across the pinned reference snapshots, not every source file or historical branch. Several long files were inspected in relevant sections rather than read in full. The tables identify the files and the findings that their inspected content supports. No historical reference code was copied or merged into YENI.

The source register retains primary URLs, exact repository commits and the supplied standard's hash/page identity. Report reconstructions are tied to the existing public engineering note and verification ledger. Private source documents and complete row datasets are outside this public appendix.

The TS500 source-edition qualification remains explicit. Final design use must bind the project's adopted edition and interpretation. The eight experiment cards have status **PROPOSED / NOT_RUN** in this audit. Completion of the research appendix does not imply completion of those experiments, closure of the engineering GAPs or release approval.
