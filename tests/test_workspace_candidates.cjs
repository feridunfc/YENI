/* Execute the real workspace projection without starting network or DOM actions. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../src/tbdy_next/static/workspace-source.js'), 'utf8');
const boundary = '  workspace.setLoader(';
assert.ok(source.includes(boundary));
const window = {TBDYWorkspace: {}, engineConsole: {log() {}}};
vm.runInNewContext(source.replace(boundary, '  window.projectTables = runTables; return;\n' + boundary), {
  window, document: {getElementById() { return {}; }}, location: {search: ''}, URLSearchParams,
});
const recorded = {column_candidate_schedule: {
  expected_column_count: 2, bound_column_count: 1, selection_role: 'ALGORITHM_SELECTED_CANDIDATE',
  formal_compliance: 'NOT_PROVEN', rows: [
    {member_id: '210', story: '+0.00', section: 'C80', label: '32Φ16', bar_count: 32, diameter_mm: 16,
      area_mm2: 6433.981754551896, rho_percent: 1.005309649, minimum_area_mm2: 6400,
      tie_diameter_mm: 8, confinement_spacing_mm: 90, midspan_spacing_mm: 90,
      legs_v2: 5, legs_v3: 5, crossties_parallel_v2: 3, crossties_parallel_v3: 3,
      all_tbdy_checks_met: false, transverse_alerts: ['SPACING_UNRESOLVED'],
      pmm_max_utilization: .1, magnified_pmm_utilization: .42, spectral_bound_utilization: .64,
      magnified_pmm_resolved_rows: 3, magnified_pmm_expected_rows: 3, binding_status: 'SAME_RUN_CANDIDATE_BOUND'},
    {member_id: '211', label: null, all_tbdy_checks_met: null, transverse_alerts: [], binding_status: 'CANDIDATE_BLOCKED'},
  ],
}};
const before = JSON.stringify(recorded);
const result = window.projectTables(recorded);
assert.equal(JSON.stringify(recorded), before, 'Viewing must not mutate recorded results');
for (const key of ['4.2', '4.4', '4.5', '4.6']) {
  assert.equal(result[key].rows.length, 2, 'Blocked member must remain visible');
  assert.equal(result[key].rows[1][0], '211');
  assert.ok(result[key].status.includes('1/2'));
}
function value(key, index, header) { return result[key].rows[index][result[key].headers.indexOf(header)]; }
assert.equal(value('4.2', 0, 'As / Ac (%)'), '1.005');
assert.equal(value('4.2', 0, 'Selected As (mm²)'), '6433.98');
assert.equal(value('4.6', 0, 'Crossties V2'), 3);
assert.equal(value('4.6', 0, 'Crossties V3'), 3);
assert.equal(value('4.6', 0, 'Recorded transverse criteria met'), 'No');
assert.equal(value('4.6', 1, 'Recorded transverse criteria met'), 'Unavailable');
assert.equal(value('4.4', 1, 'Magnified reference PMM utilization'), '—');
assert.ok(result['4.4'].note.includes('not simultaneous force vectors'));
assert.equal(window.projectTables({})['4.6'], undefined, 'No invented selection on a plain capture');
// Original P2 roof connection and the separate column end 211/J in the same building.
const floor = {story: '+9.00', z_m: 9, combination: 'Crack_SeisX',
  selected_beam_ends: [{beam: '378', face: 'I'}], mr_wall_lower_knm: 7942.696524442696,
  required_mr_knm: 315.86518368575616, upper_utilization: 0.03976800356323812, status: 'STRONG_WALL_BOUND_SATISFIED'};
const beamColumn = {target_member_id: '211', target_end: 'J', joint_id: '1045', direction: 'Y',
  column_ids: ['128', '211'], beam_ids: ['768'], low_axial_exception: {status: 'EXEMPT_LOW_AXIAL'},
  status: 'SCWB_EQ_7_3_EXEMPT_LOW_AXIAL'};
const wallOnly = {building_design: {wall_sections: {piers: [{pier: 'P2', strong_wall_connections: [floor]}]}}};
assert.equal(window.projectTables(wallOnly)['4.8'], undefined);
assert.equal(window.projectTables({r10_live: {scwb_joints: [beamColumn]}})['7.9'], undefined);
const jointViews = window.projectTables({...wallOnly, r10_live: {scwb_joints: [beamColumn]}});
assert.deepEqual(Array.from(jointViews['7.9'].rows[0]),
  ['P2', '+9.00', '9', 'Crack_SeisX', '378/I', '7942.7', '315.87', '3.98', 'STRONG_WALL_BOUND_SATISFIED']);
assert.equal(jointViews['4.8'].rows[0].at(-1), 'SCWB_EQ_7_3_EXEMPT_LOW_AXIAL');
assert.equal(jointViews['4.8'].rows[0].at(-2), '—');
assert.equal(window.projectTables({})['7.8'], undefined, 'Historical captures must not acquire conditional designs');
assert.equal(window.projectTables({building_design: {wall_sections: {piers: []}}})['7.9'], undefined);
console.log('Workspace selected-candidate coverage, precision and unresolved-state contracts: PASS');
