"""Readable VS21 numerical comparison; no capacity calculation in rendering."""
from html import escape
import json
from .column_overview_report import number, _table

STATUS={"NUMERICAL_COMPARISON_MATCH":"Within tolerance","NUMERICAL_COMPARISON_MISMATCH":"Outside tolerance",
    "REFERENCE_UNRESOLVED":"Reference unresolved","REFERENCE_NOT_STABLE":"Reference unstable"}
PRIMARY={"WITHIN_SCENARIO_SURFACE":"Within conditional surface","EXCEEDS_SCENARIO_SURFACE":"Conditional surface exceeded",
    "AXIAL_ONLY_SCENARIO":"Axial only","OUTSIDE_SCENARIO_AXIAL_RANGE":"Axial limit exceeded",
    "NUMERIC_UNRESOLVED":"Numerical solution unresolved","BLOCKED_INPUTS":"Input missing"}


def quality_html(result):
    content=('<section class="column-quality"><h2>Independent numerical PMM comparison · VS21 / VS25</h2><p><strong>'+
        str(result['comparison_count'])+' governing records / '+str(result['filtered_primary_assessment_count'])+
        ' filtered primary PMM evaluations · NOT_PROVEN / NOT_READY</strong></p>'
        '<p>The comparison covers the highest resolved radial PMM records for each column and proposal, including all ties. '
        'Independent verification of governing-record selection and the full PMM population is pending. '
        'The coverage table lists axial-only, unresolved and missing-input states separately.</p>'
        '<p>The primary calculation solves strain-compatible equilibrium at fixed N in the source moment direction. '
        'The axial residual is ≤1 N and the directional residual is ≤0.001 kN·m. Angular samples determine the root bracket and support the sampling stability check.</p>'
        '<p>Both methods use the same material model. Material model acceptance, seismic design demand, '
        'second-order behavior and code compliance require separate evidence. A continuous error bound and uniqueness of all roots remain unverified.</p>')
    content+='<p>'+escape(' · '.join(STATUS[k]+': '+str(v) for k,v in result['status_counts'].items()) or
        'The selected filter has no comparable governing radial records.')+'</p>'
    content+=_table(('Column','Story','Proposal','Governing static combination','Primary capacity (kN·m)','Independent capacity (kN·m)',
        '|Fark| (kN·m)','Tolerans (kN·m)','Numerical comparison'),[(r['member_id'],r['story'],r['candidate_label'],r['native_key']['LoadCase'],
            number(r['primary_capacity_knm']),number(r['reference_capacity_knm']),number(r['absolute_difference_knm'],4),
            number(r['comparison_budget_knm'],4),STATUS[r['status']]) for r in result['rows']])
    content+='<details><summary>Governing equilibrium points and approximation differences</summary><p>θ is the angle of the compression normal from local 2 toward local 3, reduced to the first quadrant by biaxial symmetry.</p>'
    content+=_table(('Column','Proposal','Compression normal θ (°)','c (mm)','|ΔN| (N)','Directional residual (kN·m)',
        'Difference from coarse minimum (kN·m)'),[(r['member_id'],r['candidate_label'],
            number(r['primary_direction_root']['point']['theta_deg'],5),number(r['primary_direction_root']['point']['c_mm'],5),
            number(r['primary_direction_root']['axial_residual_n'],5),number(r['primary_direction_root']['direction_residual_nmm']/1e6,6),
            number(r['primary_root_minus_coarse_minimum_knm'],6)) for r in result['rows']])+'</details>'
    content+='<details><summary>Comparison coverage and excluded states</summary>'
    content+=_table(('Column','Proposal','Primary records','Radial','Nonradial','Governing ties','Primary calculation states'),
        [(g['member_id'],g['candidate_label'],g['primary_state_count'],g['primary_radial_state_count'],g['primary_nonradial_state_count'],
            g['target_count'],' · '.join(PRIMARY[k]+': '+str(v) for k,v in g['primary_status_counts'].items()) or 'Static record unavailable')
            for g in result['members']])+'</details>'
    content+=('<details><summary>Independent calculation and tolerances</summary><p>Concrete uses strip integration split at section edges. '
        'Concrete displaced by a bar uses two-point Gauss integration over the disk. Axial equilibrium and moment direction use independent bisection. '
        'The three levels use 8, 16 and 32 disk panels and 12, 24 and 48 angular intervals per quadrant. Axial residual ≤0.05 N. '
        'Directional residual ≤100 N·mm + 10⁻⁸ |M|. Consecutive capacity difference ≤100 N·mm + 10⁻⁵ max(M). '
        'The primary-to-reference tolerance is 1000 N·mm + 0.002 max(M) + (1 + 0.05) N × section radius. '
        'The tolerance excludes the spread across the three primary levels. The c/θ planes at the primary root and bracket endpoints '
        'are independently integrated with differences ≤0.05 N and ≤100 N·mm. This checks the supplied planes. '
        'The comparison uses the supplied primary results and unrounded values for decisions.</p></details>')
    content+='<details><summary>Full precision, source identifiers and all three solution levels</summary><pre>'+escape(
        json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))+'</pre></details></section>'
    return content
