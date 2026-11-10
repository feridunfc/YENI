/* Async identity/filter regressions; synthetic DOM, not a visual acceptance. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const staticDir = path.join(__dirname, '..', 'src', 'tbdy_next', 'static');
class Element {
  constructor() { this.children=[]; this.events={}; this.value=''; this.text=''; this.disabled=false; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.text=''; this.children=nodes; }
  set textContent(text) { this.text=String(text); this.children=[]; }
  get textContent() { return this.text + this.children.map(c=>c.textContent).join(' '); }
  addEventListener(event, callback) { this.events[event]=callback; }
  trigger(event) { return this.events[event]?.(); }
  setAttribute(name,value) { (this.attributes ||= {})[name]=String(value); }
}
const ids = new Map();
const html = fs.readFileSync(path.join(staticDir,'index.html'),'utf8');
for (const m of html.matchAll(/id="(column[^"]+)"/g)) ids.set(m[1],new Element());
const pending=[]; const window={};
vm.runInNewContext(fs.readFileSync(path.join(staticDir,'column.js'),'utf8'), {
  window, URLSearchParams,
  document:{getElementById:id=>ids.get(id),createElement:()=>new Element(),createElementNS:()=>new Element()},
  fetch(url) { return new Promise(resolve=>pending.push({url, done:(body,ok=true)=>resolve({ok,json:async()=>body})})); }
});
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
const take=()=>{assert.ok(pending.length);return pending.shift();};
const run=n=>'RUN-'+String(n).repeat(32);
const payload=n=>({run_id:run(n),formal_compliance:'NOT_PROVEN',design_demand_authority:'DENIED',
  observed_column_count:1,selected_column_count:1,force_row_count:1,recorded_output_count:1,
  source_archive_sha256:'SOURCE_'+n,members:[{frame_name:'C'+n,context:{frame:{story_label:'SYNTHETIC'}},reason_codes:[]}],
  force_page:{total:1,offset:0,limit:200,rows:[{Obj:'C'+n,LoadCase:'G',P:-n}]},
  case_coverage:[{name:'G',row_count:1}],engineering_gaps:[],
  static_replay:{matched_rows:1,scalar_comparisons:6,maximum_absolute_difference:0,combinations:[]}});
const select=async n=>{ids.get('columnRun').value=run(n);ids.get('columnRun').trigger('change');await flush();return take();};
(async()=>{
  window.openColumnBank();assert.equal(take().url,'/api/column-history');
  // A refreshed list invalidates any earlier request, then offers explicit selection.
  ids.get('columnRefresh').trigger('click');
  take().done({runs:[1,2].map(n=>({run_id:run(n),force_row_count:1}))});await flush();
  const old=await select(1); const current=await select(2);
  assert.equal(ids.get('columnExports').children.length,0);
  current.done(payload(2));await flush();
  assert.match(ids.get('columnForces').textContent,/C2/);
  old.done(payload(1));await flush();
  assert.doesNotMatch(ids.get('columnForces').textContent,/C1/);
  assert.match(ids.get('columnStatus').textContent,new RegExp(run(2)));
  assert.ok(ids.get('columnExports').children.every(a=>a.href.includes(run(2))));
  ids.get('columnMember').value='C2';ids.get('columnMember').trigger('change');await flush();
  const filtered=take();assert.match(filtered.url,/member=C2/);
  assert.equal(ids.get('columnForces').children.length,0);
  filtered.done(payload(1));await flush();
  assert.match(ids.get('columnStatus').textContent,/eşleşmiyor/);
  assert.equal(ids.get('columnExports').children.length,0);
  const failure=await select(2);failure.done({error:'VERIFIED_COLUMN_BANK_NOT_FOUND'},false);await flush();
  assert.match(ids.get('columnStatus').textContent,/VERIFIED_COLUMN_BANK_NOT_FOUND/);
  assert.equal(ids.get('columnForces').children.length,0);
  const demandPayload=()=>({...payload(2),demand_chain:{source_run_id:run(2),source_archive_sha256:'SOURCE_2',
    design_demand_authority:'DENIED',combination_count:1,static_candidate_count:1,combinations:[],
    design_summary:{row_count:1,unique_static_links:1,ambiguous_design_station_rows:0,references_without_exact_station:0}}});
  const initial=await select(2);initial.done(demandPayload());await flush();
  ids.get('columnView').value='static';ids.get('columnView').trigger('change');await flush();
  const staticRequest=take();assert.match(staticRequest.url,/view=static/);
  const candidate={native_key:{Obj:'C2',ObjSta:3.3,Elm:'E2',ElmSta:1.3,LoadCase:'SUM',StepType:'Single Value',StepNum:0},
    domain_values:{N_compression_kN:180,V2_kN:10.8,V3_kN:-18.4,T_kNcm:260,M2_kNcm:4800,M3_kNcm:-5720}};
  staticRequest.done({...demandPayload(),demand_page:{view:'static',total:1,offset:0,limit:200,rows:[candidate]}});await flush();
  assert.match(ids.get('columnForces').textContent,/4800/);
  assert.match(ids.get('columnUnits').textContent,/kN·cm/);
  // Switching view invalidates an older request even when the run has not changed.
  ids.get('columnView').trigger('change');await flush();const staleStatic=take();
  ids.get('columnView').value='native';ids.get('columnView').trigger('change');await flush();
  take().done(demandPayload());await flush();
  staleStatic.done({...demandPayload(),demand_page:{view:'static',total:1,offset:0,limit:200,rows:[candidate]}});await flush();
  assert.doesNotMatch(ids.get('columnForces').textContent,/4800/);
  assert.match(ids.get('columnUnits').textContent,/kN·m,/);
  ids.get('columnView').value='design';ids.get('columnView').trigger('change');await flush();
  const designRequest=take();assert.match(designRequest.url,/view=design/);
  designRequest.done({...demandPayload(),demand_page:{view:'design',total:1,offset:0,limit:200,rows:[{
    native_design_row:{UniqueName:'C2',Station:'2',PMMRatio:null,PMMCombo:'SUM',VMajCombo:'SUM',VMinCombo:'RS'},
    references:['PMM','MAJOR_SHEAR','MINOR_SHEAR'].map(role=>({role,status:'AMBIGUOUS_DESIGN_STATION'}))}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/Çift tasarım istasyonu/);
  assert.match(ids.get('columnForces').textContent,/—/);
  ids.get('columnView').value='native';ids.get('columnView').trigger('change');await flush();
  const wrong=demandPayload();wrong.demand_chain.source_archive_sha256='OTHER';take().done(wrong);await flush();
  assert.match(ids.get('columnStatus').textContent,/başka bir kaynağa/);
  assert.equal(ids.get('columnForces').children.length,0);
  const precheckPayload=()=>{
    const p=demandPayload();p.demand_chain.result_sha256='DEMAND2';
    p.column_prechecks={source_run_id:run(2),source_archive_sha256:'SOURCE_2',source_demand_result_sha256:'DEMAND2',
      design_demand_authority:'DENIED',critical_selection:{critical_state_count:1},reinforcement_bounds:{calculated_member_count:1}};
    return p;
  };
  ids.get('columnCase').value='SUM';ids.get('columnView').value='critical';ids.get('columnView').trigger('change');await flush();
  const critical=take();assert.match(critical.url,/view=critical/);assert.match(critical.url,/case=SUM/);
  critical.done({...precheckPayload(),critical_scope:{candidate_count:4,pmm_population_reduced:false},
    demand_page:{view:'critical',total:1,offset:0,limit:200,rows:[{...candidate,criteria:['N_COMPRESSION_MAX','V2_ABS_MAX']}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/En büyük basınç/);
  assert.match(ids.get('columnForces').textContent,/4800/);
  assert.match(ids.get('columnContext').textContent,/tam aday nüfusu saklanır/);
  ids.get('columnView').value='reinforcement';ids.get('columnView').trigger('change');await flush();
  const bounds=take();assert.doesNotMatch(bounds.url,/case=/);assert.equal(ids.get('columnCase').disabled,true);
  bounds.done({...precheckPayload(),demand_page:{view:'reinforcement',total:1,offset:0,limit:200,rows:[{
    member_id:'C2',story:'S',section_name:'RECT',gross_area_cm2:'6400',minimum_as_cm2:'64',maximum_as_cm2:'256',
    provided_as_cm2:null,status:'REQUIRED_AREA_BOUNDS_CALCULATED',asmin_source_counts:{NUMERICAL_MATCH:4}}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/6400/);assert.match(ids.get('columnForces').textContent,/256/);
  assert.match(ids.get('columnUnits').textContent,/7.3.2.1/);assert.match(ids.get('columnForces').textContent,/—/);
  ids.get('columnView').value='critical';ids.get('columnView').trigger('change');await flush();
  assert.equal(ids.get('columnCase').disabled,false);
  const invalid=precheckPayload();invalid.column_prechecks.source_demand_result_sha256='OTHER';take().done(invalid);await flush();
  assert.match(ids.get('columnStatus').textContent,/kuvvet zinciriyle eşleşmiyor/);
  assert.equal(ids.get('columnForces').children.length,0);
  const stabilityPayload=()=>{
    const p=precheckPayload();p.column_prechecks.result_sha256='PRECHECK2';
    p.column_stability={axis_convention:'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3',source_run_id:run(2),source_archive_sha256:'SOURCE_2',source_demand_result_sha256:'DEMAND2',
      source_prechecks_result_sha256:'PRECHECK2',design_demand_authority:'DENIED',actual_second_order_applied:false,
      calculated_section_count:1,distinct_section_count:1,native_property_match_count:5};
    return p;
  };
  ids.get('columnView').value='stiffness';ids.get('columnView').trigger('change');await flush();
  const stiffness=take();assert.doesNotMatch(stiffness.url,/case=/);assert.equal(ids.get('columnCase').disabled,true);
  stiffness.done({...stabilityPayload(),demand_page:{view:'stiffness',total:1,offset:0,limit:200,rows:[{
    member_id:'C2',section_name:'RECT',section:{i22_mm4:34133333333.33333,i33_mm4:34133333333.33333,
      r22_exact_mm:230.94010767585,r33_exact_mm:230.94010767585},elastic:{observed_E_MPa:34000},
    lengths:{object_i_j_m:4.5,output_face_span_m:3.8},property_comparison_status:'NUMERICAL_MATCH'}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/34000/);assert.match(ids.get('columnForces').textContent,/3413333/);
  assert.match(ids.get('columnForces').textContent,/230.940/);assert.match(ids.get('columnUnits').textContent,/etkili rijitlik değildir/);
  ids.get('columnView').value='eccentricity';ids.get('columnView').trigger('change');await flush();
  const eccentricity=take();assert.match(eccentricity.url,/case=SUM/);assert.equal(ids.get('columnCase').disabled,false);
  eccentricity.done({...stabilityPayload(),demand_page:{view:'eccentricity',total:1,offset:0,limit:200,rows:[{
    ...candidate,axes:[{n_compression_kn:'1000',source_abs_moment_kNcm:'2000',reference_minimum_moment_kNcm:'3900',status:'BELOW_REFERENCE'},
      {n_compression_kn:'1000',source_abs_moment_kNcm:'4000',reference_minimum_moment_kNcm:'3900',status:'AT_OR_ABOVE_REFERENCE'}]}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/3900/);assert.match(ids.get('columnForces').textContent,/Referans altında/);
  assert.match(ids.get('columnUnits').textContent,/iç istasyonlara/);
  ids.get('columnView').value='stiffness';ids.get('columnView').trigger('change');await flush();
  const wrongStiffness=stabilityPayload();wrongStiffness.column_stability.source_prechecks_result_sha256='OTHER';take().done(wrongStiffness);await flush();
  assert.match(ids.get('columnStatus').textContent,/Rijitlik hesabı seçili kolon kaynağıyla eşleşmiyor/);
  assert.equal(ids.get('columnForces').children.length,0);
  const cagePayload=()=>{
    const p=stabilityPayload();p.column_stability.result_sha256='STABILITY2';
    p.column_cages={axis_convention:'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3',source_run_id:run(2),source_archive_sha256:'SOURCE_2',source_demand_result_sha256:'DEMAND2',
      source_prechecks_result_sha256:'PRECHECK2',result_sha256:'CAGES2',design_demand_authority:'DENIED',selected_design:null};
    return p;
  };
  ids.get('columnMember').value='C2';ids.get('columnView').value='cages';ids.get('columnView').trigger('change');await flush();
  const cageRequest=take();assert.doesNotMatch(cageRequest.url,/case=/);assert.equal(ids.get('columnCase').disabled,true);
  cageRequest.done({...cagePayload(),demand_page:{view:'cages',total:1,offset:0,limit:200,rows:[{
    member_id:'C2',label:'16Φ24',t2_mm:600,t3_mm:700,as_cm2:72.38229474,rho_percent:1.723388,
    center_offset_mm:64,minimum_clear_spacing_mm:94,geometry_status:'PROPOSED_GEOMETRY_CALCULATED',
    area_ratio_status:'WITHIN_1_TO_4_PERCENT_REFERENCE',bars:[{x2_mm:286,x3_mm:236,diameter_mm:24}]}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/72.3823/);assert.match(ids.get('columnContext').textContent,/merkez örtüsü 64 mm/);
  const drawing=ids.get('columnContext').children.find(c=>c.children.some(s=>s.attributes?.role==='img'));
  assert.ok(drawing);assert.equal(drawing.children[0].children[1].attributes.cy,'-236');
  assert.equal(drawing.children[0].children[0].attributes.width,'700');
  assert.equal(drawing.children[0].children[0].attributes.height,'600');
  const pmmPayload=()=>({...cagePayload(),column_pmm:{schema:'tbdy.next.column-pmm-scenarios.v3',
    numerical_policy:{basis:'STRAIN_COMPATIBLE_POINT_AT_FIXED_N_AND_MOMENT_DIRECTION',solver_revision:'VS25_DIRECTION_ROOT'},
    axis_convention:'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3',source_run_id:run(2),source_archive_sha256:'SOURCE_2',
    source_demand_result_sha256:'DEMAND2',source_cages_result_sha256:'CAGES2',source_stability_result_sha256:'STABILITY2',
    design_demand_authority:'DENIED',pmm_population_reduced:false,actual_second_order_applied:false,
    minimum_eccentricity_applied:false,selected_design:null,formal_compliance:'NOT_PROVEN',static_state_count:4,assessment_count:12}});
  ids.get('columnView').value='pmm';ids.get('columnView').trigger('change');await flush();
  const pmmRequest=take();assert.match(pmmRequest.url,/case=SUM/);assert.equal(ids.get('columnCase').disabled,false);
  pmmRequest.done({...pmmPayload(),demand_page:{view:'pmm',total:1,offset:0,limit:200,rows:[{
    ...candidate,native_values:{M2:48,M3:-57.2},candidate_label:'16Φ24',utilization:.2,radial_capacity_kNm:373.363,
    status:'WITHIN_SCENARIO_SURFACE',reason:null}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/Koşullu yüzey içinde/);assert.match(ids.get('columnForces').textContent,/-57.2/);
  assert.match(ids.get('columnUnits').textContent,/ikinci mertebe uygulanmadı/);
  ids.get('columnView').trigger('change');await flush();const badPmm=pmmPayload();badPmm.column_pmm.source_cages_result_sha256='OTHER';
  take().done(badPmm);await flush();assert.match(ids.get('columnStatus').textContent,/PMM hesabının kaynak bağı/);
  assert.equal(ids.get('columnForces').children.length,0);
  const transversePayload=()=>{
    const p=cagePayload();
    p.column_cages.candidates=[{candidate_id:'CAGE2',label:'16Φ24',t2_mm:800,t3_mm:800,
      as_cm2:72.38229474,center_offset_mm:64,bars:[{x2_mm:336,x3_mm:336,diameter_mm:24}]}];
    p.column_transverse={axis_convention:'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3',source_run_id:run(2),source_archive_sha256:'SOURCE_2',source_demand_result_sha256:'DEMAND2',
      source_cages_result_sha256:'CAGES2',result_sha256:'TRANSVERSE2',design_demand_authority:'DENIED',
      formal_compliance:'NOT_PROVEN',selected_design:null,proposal_policy:{physical_arrangement_proven:false}};
    return p;
  };
  ids.get('columnView').value='transverse';ids.get('columnView').trigger('change');await flush();
  const transverseRequest=take();assert.doesNotMatch(transverseRequest.url,/case=/);assert.equal(ids.get('columnCase').disabled,true);
  transverseRequest.done({...transversePayload(),demand_page:{view:'transverse',total:1,offset:0,limit:200,rows:[{
    member_id:'C2',candidate_id:'CAGE2',candidate_label:'16Φ24',shear_axis:'V2',status:'PROPOSED_TRANSVERSE_REFERENCES_CALCULATED',
    confinement_spacing_max_mm:144,layout:{legs:[{endpoints_mm:[[-354,168],[354,168]],diameter_mm:12,kind:'CROSSTIE'}]},
    direction:{bk_axis:3,bk_mm:708,ash_mm2:565.486677646,maximum_lateral_leg_spacing_mm:186,
      confinement:{high_axial_required_ash_mm2:371.7,low_axial_required_ash_mm2:247.8}}}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/371.7/);assert.match(ids.get('columnForces').textContent,/247.8/);
  assert.match(ids.get('columnUnits').textContent,/Ack dıştan dışa/);
  const tieDrawing=ids.get('columnContext').children.find(c=>c.children.some(s=>s.attributes?.role==='img'));
  assert.ok(tieDrawing);assert.equal(tieDrawing.children[0].children[1].attributes.y1,'-168');
  assert.match(tieDrawing.textContent,/düşey yerleşim doğrulanmadı/);
  const shearPayload=()=>({...transversePayload(),column_shear:{axis_convention:'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3',source_run_id:run(2),source_archive_sha256:'SOURCE_2',
    source_demand_result_sha256:'DEMAND2',source_cages_result_sha256:'CAGES2',source_transverse_result_sha256:'TRANSVERSE2',
    design_demand_authority:'DENIED',formal_compliance:'NOT_PROVEN',selected_design:null,ve_status:'NOT_PROVEN',
    source_population_reduced:false,actual_second_order_applied:false,vc_zero_gate:{required:null},static_state_count:8,assessment_count:48}});
  ids.get('columnView').value='shear';ids.get('columnView').trigger('change');await flush();
  const shearRequest=take();assert.match(shearRequest.url,/case=SUM/);assert.equal(ids.get('columnCase').disabled,false);
  shearRequest.done({...shearPayload(),demand_page:{view:'shear',total:1,offset:0,limit:200,rows:[{
    ...candidate,candidate_label:'16Φ24',shear_axis:'V3',status:'SHEAR_REFERENCES_CALCULATED',reason:null,
    calculation:{source_signed_v_kn:-500,branches:{ts500:{vc_kn:100,vw_kn:1000,vr_kn:1100,source_utilization:.454545},
      zero_concrete:{vc_kn:0,vw_kn:1000,vr_kn:1000,source_utilization:.5}}}}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/-500/);assert.match(ids.get('columnForces').textContent,/0.454545/);
  assert.match(ids.get('columnUnits').textContent,/tasarım Ve doğrulanmadı/);
  assert.match(ids.get('columnContext').textContent,/48 kıyas/);
  ids.get('columnView').trigger('change');await flush();const oldShear=take();
  ids.get('columnView').value='native';ids.get('columnView').trigger('change');await flush();
  take().done(transversePayload());await flush();oldShear.done(shearPayload());await flush();
  assert.doesNotMatch(ids.get('columnForces').textContent,/0.454545/);
  ids.get('columnView').value='shear';ids.get('columnView').trigger('change');await flush();
  const unboundShear=shearPayload();unboundShear.column_shear.source_transverse_result_sha256='OTHER';
  take().done(unboundShear);await flush();assert.match(ids.get('columnStatus').textContent,/Kesme hesabının kaynak bağı/);
  assert.equal(ids.get('columnForces').children.length,0);
  ids.get('columnView').trigger('change');await flush();const promoted=shearPayload();promoted.column_shear.vc_zero_gate.required=true;
  take().done(promoted);await flush();assert.match(ids.get('columnStatus').textContent,/Kesme hesabının kaynak bağı/);
  assert.equal(ids.get('columnExports').children.length,0);
  const jointsPayload=()=>{
    const p=transversePayload();p.result_sha256='BANK2';
    p.column_joints={source_run_id:run(2),source_archive_sha256:'SOURCE_2',source_bank_result_sha256:'BANK2',
      source_demand_result_sha256:'DEMAND2',source_cages_result_sha256:'CAGES2',source_transverse_result_sha256:'TRANSVERSE2',
      axis_convention:'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3',scenario:'CENTERLINE_AS_SECTION_CENTER_SCENARIO',
      design_demand_authority:'DENIED',formal_compliance:'NOT_PROVEN',engineering_release:'NOT_READY',
      selected_design:null,ve_status:'NOT_PROVEN',scwb_status:'NOT_PROVEN',physical_geometry_proven:false,
      physical_joint_population_proven:false,joint_node_count:3,column_end_count:4,geometric_limit_count:4,
      graph:{status:'NATIVE_ENDPOINT_GRAPH_BOUND',reason:null}};
    return p;
  };
  const endRow={member_id:'C2',end:'I',point_id:'P1',geometry_column_id:'C2',
    enclosure_scenario:'UNENCLOSED',status:'JOINT_GEOMETRIC_REFERENCES_CALCULATED',
    axes:[{axis:'V2',calculation:{geometric_limit_kn:3786.291061184}},{axis:'V3',calculation:null}],
    faces:{'2+':{face:'2+',frame_id:'B2',native_end:'I',beam_width_mm:600,column_transverse_width_mm:800}},
    missing_faces:['2-'],narrow_faces:[],reason:null};
  ids.get('columnView').value='joints';ids.get('columnView').trigger('change');await flush();
  const jointsRequest=take();assert.doesNotMatch(jointsRequest.url,/case=/);assert.equal(ids.get('columnCase').disabled,true);
  jointsRequest.done({...jointsPayload(),demand_page:{view:'joints',total:1,offset:0,limit:200,rows:[endRow]}});await flush();
  assert.match(ids.get('columnForces').textContent,/3786.29/);
  assert.match(ids.get('columnForces').textContent,/Kuşatılmamış · eşmerkez senaryo/);
  assert.match(ids.get('columnUnits').textContent,/Ve ve SCWB doğrulanmadı/);
  assert.match(ids.get('columnContext').textContent,/B2/);
  ids.get('columnView').trigger('change');await flush();const oldJoint=take();
  ids.get('columnView').value='joint-ties';ids.get('columnView').trigger('change');await flush();
  const jt=take();assert.doesNotMatch(jt.url,/case=/);
  jt.done({...jointsPayload(),demand_page:{view:'joint-ties',total:1,offset:0,limit:200,rows:[{
    member_id:'C2',end:'I',point_id:'P1',lower_column_id:'C1',axis:'V2',lower_axis:'V3',candidate_label:'16Φ24',
    branches:{high:{required_ash_at_joint_spacing_mm2:251.612308,proposed_ash_mm2:565.486678,joint_spacing_mm:100},
      low:{required_ash_at_joint_spacing_mm2:167.741538}},tie_reason:null}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/251.612/);assert.match(ids.get('columnForces').textContent,/V3/);
  oldJoint.done({...jointsPayload(),demand_page:{view:'joints',total:1,offset:0,limit:200,rows:[endRow]}});await flush();
  assert.doesNotMatch(ids.get('columnForces').textContent,/3786.29/);
  assert.match(ids.get('columnUnits').textContent,/tam donatı ihtiyacı doğrulanmadı/);
  for (const change of [p=>p.column_joints.source_transverse_result_sha256='OTHER',p=>p.column_joints.physical_geometry_proven=true]) {
    ids.get('columnView').trigger('change');await flush();const invalid=jointsPayload();change(invalid);take().done(invalid);await flush();
    assert.match(ids.get('columnStatus').textContent,/Birleşim hesabının kaynak bağı/);
    assert.equal(ids.get('columnForces').children.length,0);assert.equal(ids.get('columnExports').children.length,0);
  }
  ids.get('columnView').value='cages';ids.get('columnView').trigger('change');await flush();
  const legacy=cagePayload();delete legacy.column_cages.axis_convention;take().done(legacy);await flush();
  assert.match(ids.get('columnStatus').textContent,/Kesit eksen sözleşmesi eski veya belirsiz/);
  assert.equal(ids.get('columnExports').children.length,0);
  const kinematicsPayload=()=>{
    const p=jointsPayload();p.column_joints.result_sha256='JOINTS2';
    p.column_kinematics={source_run_id:run(2),source_archive_sha256:'SOURCE_2',source_bank_result_sha256:'BANK2',
      source_demand_result_sha256:'DEMAND2',source_joints_result_sha256:'JOINTS2',
      axis_convention:'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3',coordinate_contract:'ETABS_POINT_OBJECT_UX_UY_UZ_RX_RY_RZ_GLOBAL',
      analysis_order:'NOT_PROVEN',analysis_generation_qualified:false,actual_second_order_applied:false,
      cm:null,beta:null,magnified_design_moments:null,design_demand_authority:'DENIED',formal_compliance:'NOT_PROVEN',
      engineering_release:'NOT_READY',linked_member_case_count:1,expected_member_case_count:1,
      analysis_basis:{combinations:[{combination:'SUM',case_names:['G']}],cases:[{case_name:'G',stiffness_type:'Nonlinear Case',
        nonlinear_case_raw:'None',status:'RECORDED_NONLINEAR_CASE_UNRESOLVED',reason:null}]}};
    return p;
  };
  const linkedRow={member_id:'C2',output_case:'SUM',point_i:'I2',point_j:'J2',status:'SAME_CASE_SOURCE_LINKED',
    force_reason:null,kinematics_reason:null,force_pair:{i:{native_key:{Elm:'E2A',ObjSta:0},
      native_values:{P:-180,V2:10.8,V3:-18.4,T:2.6,M2:48,M3:-57.2}},j:{native_key:{Elm:'E2B',ObjSta:3.3},
      native_values:{P:-720,V2:43.2,V3:-73.6,T:10.4,M2:192,M3:-228.8}}},
    calculation:{object_i_j_length_m:4,delta_local_m:[0,.008,-.006],chord_alpha2_rad:.0015,chord_alpha3_rad:.002,
      joint_i_relative_r2_rad:0,joint_i_relative_r3_rad:0,joint_j_relative_r2_rad:0,joint_j_relative_r3_rad:0}};
  ids.get('columnCase').value='SUM';ids.get('columnView').value='end-forces';ids.get('columnView').trigger('change');await flush();
  const ends=take();assert.match(ends.url,/case=SUM/);assert.equal(ids.get('columnCase').disabled,false);
  ends.done({...kinematicsPayload(),demand_page:{view:'end-forces',total:1,offset:0,limit:200,rows:[linkedRow]}});await flush();
  assert.match(ids.get('columnForces').textContent,/-228.8/);assert.match(ids.get('columnForces').textContent,/E2B, 3.3/);
  assert.match(ids.get('columnUnits').textContent,/P çekme pozitif/);
  ids.get('columnView').trigger('change');await flush();const staleEnds=take();
  ids.get('columnView').value='kinematics';ids.get('columnView').trigger('change');await flush();
  take().done({...kinematicsPayload(),demand_page:{view:'kinematics',total:1,offset:0,limit:200,rows:[linkedRow]}});await flush();
  assert.match(ids.get('columnForces').textContent,/0, 8, -6/);
  assert.match(ids.get('columnForces').textContent,/0.0015, 0.002/);
  assert.match(ids.get('columnContext').textContent,/Nonlinear Case/);
  staleEnds.done({...kinematicsPayload(),demand_page:{view:'end-forces',total:1,offset:0,limit:200,rows:[linkedRow]}});await flush();
  assert.doesNotMatch(ids.get('columnForces').textContent,/-228.8/);
  for (const change of [p=>p.column_kinematics.source_joints_result_sha256='OTHER',p=>p.column_kinematics.actual_second_order_applied=true,
                       p=>p.column_kinematics.beta=1.2,p=>p.column_kinematics.coordinate_contract='POINT_LOCAL']) {
    ids.get('columnView').trigger('change');await flush();const invalid=kinematicsPayload();change(invalid);take().done(invalid);await flush();
    assert.match(ids.get('columnStatus').textContent,/Kolon uç hareketlerinin kaynak bağı/);
    assert.equal(ids.get('columnForces').children.length,0);assert.equal(ids.get('columnExports').children.length,0);
  }
  const sensitivityPayload=()=>{
    const p=kinematicsPayload();p.column_kinematics.result_sha256='KINEMATICS2';
    p.column_sensitivity={source_run_id:run(2),source_archive_sha256:'SOURCE_2',source_bank_result_sha256:'BANK2',
      source_demand_result_sha256:'DEMAND2',source_stability_result_sha256:'STABILITY2',source_kinematics_result_sha256:'KINEMATICS2',
      axis_convention:'CSI_T3_ALONG_LOCAL2_T2_ALONG_LOCAL3',policy:{id:'TS500_EQ721_RM_0_0P5_1_REFERENCE_FAMILY',
        radius_basis:'TS500_RECTANGLE_0_30_BENDING_DIMENSION',actual_ei_interval_proven:false,source_axial_force_is_design_nd:false},
      source_population_reduced:false,actual_second_order_applied:false,actual_effective_length_lk_mm:null,actual_beta:null,actual_cm:null,
      actual_creep_ratio:null,actual_sway_classification:null,magnified_design_moments:null,approximate_method_applicability_proven:false,
      analysis_order:'NOT_PROVEN',design_demand_authority:'DENIED',formal_compliance:'NOT_PROVEN',engineering_release:'NOT_READY',
      static_state_count:4,zero_length_reference_count:24,axial_profiles:[{member_id:'C2',output_case:'SUM',recorded_static_station_count:4,
        n_i_kn:'180',n_j_kn:'720',end_n_j_minus_i_kn:'540',recorded_range_kn:'540',recorded_values_status:'RECORDED_AXIAL_VALUES_DIFFER'}]};
    return p;
  };
  const referenceAxis={member_id:'C2',axis:'M2',ec_mpa_observed:30000,gross_inertia_mm4:3.2e9,radius_reference_mm:120,
    radius_exact_mm:115.4700538,length_22i_mm:2640,length_40i_mm:4800,length_100i_mm:12000,
    status:'STIFFNESS_PARAMETER_FAMILY_CALCULATED',reason:null,scenarios:[{creep_ratio_scenario:0,effective_ei_nmm2_scenario:3.84e13,
      length_references:[{nk_kn_scenario:54379},{nk_kn_scenario:16449},{nk_kn_scenario:2631}]}]};
  ids.get('columnView').value='stiffness-scenarios';ids.get('columnView').trigger('change');await flush();
  const stiffnessScenarios=take();assert.doesNotMatch(stiffnessScenarios.url,/case=/);assert.equal(ids.get('columnCase').disabled,true);
  stiffnessScenarios.done({...sensitivityPayload(),demand_page:{view:'stiffness-scenarios',total:1,offset:0,limit:200,rows:[referenceAxis]}});await flush();
  assert.match(ids.get('columnForces').textContent,/3.8400e\+13/);assert.match(ids.get('columnForces').textContent,/2.64, 4.8, 12/);
  assert.match(ids.get('columnContext').textContent,/gerçek sünme oranı/);assert.match(ids.get('columnContext').textContent,/54379/);
  ids.get('columnView').trigger('change');await flush();const oldReference=take();
  ids.get('columnView').value='length-sensitivity';ids.get('columnView').trigger('change');await flush();
  const lengths=take();assert.match(lengths.url,/case=SUM/);assert.equal(ids.get('columnCase').disabled,false);
  lengths.done({...sensitivityPayload(),demand_page:{view:'length-sensitivity',total:1,offset:0,limit:200,rows:[{
    member_id:'C2',axis:'M2',native_key:candidate.native_key,n_source_compression_kn:'1000',status:'SOURCE_LENGTH_REFERENCES_CALCULATED',
    reason:null,scenarios:[{creep_ratio_scenario:0,zero_denominator_length_mm:17074.335419,zero_length_exceeds_100i_reference:true,
      at_reference_lengths:[{lk_over_i_reference:100,effective_length_lk_mm_scenario:12000,nk_kn_scenario:2631,
        source_denominator:.5059,status:'POSITIVE_SOURCE_DENOMINATOR'}]}]}]}});await flush();
  assert.match(ids.get('columnForces').textContent,/17.0743/);assert.match(ids.get('columnUnits').textContent,/İzin verilen boy/);
  assert.match(ids.get('columnContext').textContent,/Kayıtlı N değerleri farklı/);assert.match(ids.get('columnContext').textContent,/540/);
  oldReference.done({...sensitivityPayload(),demand_page:{view:'stiffness-scenarios',total:1,offset:0,limit:200,rows:[referenceAxis]}});await flush();
  assert.doesNotMatch(ids.get('columnForces').textContent,/3.8400e\+13/);
  for (const change of [p=>p.column_sensitivity.source_stability_result_sha256='OTHER',p=>p.column_sensitivity.policy.actual_ei_interval_proven=true,
    p=>p.column_sensitivity.actual_beta=1.2,p=>p.column_sensitivity.actual_effective_length_lk_mm=4000,
    p=>p.column_sensitivity.approximate_method_applicability_proven=true]) {
    ids.get('columnView').trigger('change');await flush();const invalid=sensitivityPayload();change(invalid);take().done(invalid);await flush();
    assert.match(ids.get('columnStatus').textContent,/Etkin boy duyarlılığının kaynak bağı/);
    assert.equal(ids.get('columnForces').children.length,0);assert.equal(ids.get('columnExports').children.length,0);
  }
  console.log('VS11–VS19 column UI identity, filters, native axes, kinematics and stiffness/length parameter scope PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
