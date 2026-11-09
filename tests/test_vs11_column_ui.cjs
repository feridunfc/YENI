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
}
const ids = new Map();
const html = fs.readFileSync(path.join(staticDir,'index.html'),'utf8');
for (const m of html.matchAll(/id="(column[^"]+)"/g)) ids.set(m[1],new Element());
const pending=[]; const window={};
vm.runInNewContext(fs.readFileSync(path.join(staticDir,'column.js'),'utf8'), {
  window, URLSearchParams,
  document:{getElementById:id=>ids.get(id),createElement:()=>new Element()},
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
    p.column_stability={source_run_id:run(2),source_archive_sha256:'SOURCE_2',source_demand_result_sha256:'DEMAND2',
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
  console.log('VS11–VS14 column UI identity, filtering, stiffness units and eccentricity scope PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
