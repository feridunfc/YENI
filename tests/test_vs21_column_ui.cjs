/* VS21 independent comparison UI: scope, failure visibility, filters and stale guards. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const root=path.join(__dirname,'..');
const samples=JSON.parse(execFileSync('python',['-c',`
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from column_kinematics_fixture import KinematicsBank
from tbdy_next.column_engine.store import save_column_bank,read_column_bank
with TemporaryDirectory() as directory:
    root=Path(directory);source=root/'bank.zip';source.write_bytes(KinematicsBank().build())
    receipts=root/'receipts';run=save_column_bank(source,receipts)['run_id']
    result={'all':read_column_bank(receipts,run,view='pmm-quality'),
        'member':read_column_bank(receipts,run,view='pmm-quality',member_id='C_SYNTHETIC_1'),
        'spectral':read_column_bank(receipts,run,view='pmm-quality',member_id='C_SYNTHETIC_1',output_case='RS_SUM')}
    print(json.dumps(result,ensure_ascii=True))
`],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024,env:{...process.env,
  PYTHONPATH:[path.join(root,'src'),__dirname].join(path.delimiter),PYTHONUTF8:'1'}}));
class Element {
  constructor(tag='div') {this.tag=tag;this.children=[];this.events={};this.value='';this.text='';this.disabled=false;this.attributes={};}
  append(...nodes) {this.children.push(...nodes);}
  replaceChildren(...nodes) {this.text='';this.children=nodes;}
  set textContent(text) {this.text=String(text);this.children=[];}
  get textContent() {return this.text+this.children.map(c=>c.textContent).join(' ');}
  addEventListener(event,callback) {this.events[event]=callback;}
  trigger(event) {return this.events[event]?.();}
  setAttribute(name,value) {this.attributes[name]=String(value);}
}
const html=fs.readFileSync(path.join(root,'src/tbdy_next/static/index.html'),'utf8');
assert.match(html,/value="overview" selected/);
const ids=new Map([...html.matchAll(/id="(column[^"]+)"/g)].map(m=>[m[1],new Element()]));
ids.get('columnView').value='pmm-quality';ids.get('columnProposal').value='16Φ24';
const pending=[],window={};
vm.runInNewContext(fs.readFileSync(path.join(root,'src/tbdy_next/static/column.js'),'utf8'),{
  window,URLSearchParams,document:{getElementById:id=>ids.get(id),createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)},
  fetch(url) {return new Promise(resolve=>pending.push({url,done:(body,ok=true)=>resolve({ok,json:async()=>body})}));}
});
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
const take=()=>{assert.ok(pending.length);return pending.shift();};
const descendants=e=>[e,...e.children.flatMap(descendants)];
const clone=key=>structuredClone(samples[key]);
(async()=>{
  window.openColumnBank();take().done({runs:[{run_id:samples.all.run_id,force_row_count:64}]});await flush();
  ids.get('columnRun').value=samples.all.run_id;ids.get('columnRun').trigger('change');await flush();
  const initial=take();assert.match(initial.url,/view=pmm-quality/);initial.done(clone('all'));await flush();
  assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  assert.match(ids.get('columnContext').textContent,/kritik alt küme/);
  assert.match(ids.get('columnContext').textContent,/aynı malzeme modelini/);
  assert.match(ids.get('columnContext').textContent,/gerinim uyumlu denge noktasından/);
  assert.match(ids.get('columnOverviewDetails').textContent,/denge noktaları ve yaklaşım farkları/);
  assert.match(ids.get('columnOverviewDetails').textContent,/Basınç normali θ/);
  assert.match(ids.get('columnForces').textContent,/Bağımsız kapasite/);
  assert.match(ids.get('columnForces').textContent,/Tolerans içinde/);
  assert.doesNotMatch(ids.get('columnForces').textContent,/state_id|source_row_id/);
  assert.equal(ids.get('columnForces').children[0].children[1].children.length,6);
  const old=(()=>{ids.get('columnView').trigger('change');return take();})();
  ids.get('columnMember').value='C_SYNTHETIC_1';ids.get('columnMember').trigger('change');await flush();
  const member=take();assert.match(member.url,/member=C_SYNTHETIC_1/);member.done(clone('member'));await flush();
  old.done(clone('all'));await flush();
  assert.equal(ids.get('columnForces').children[0].children[1].children.length,3);
  assert.match(ids.get('columnOverviewDetails').textContent,/Seçili kolonun tam hassasiyet/);
  assert.ok(descendants(ids.get('columnOverviewDetails')).filter(e=>e.tag==='details').every(e=>!e.attributes.open));
  ids.get('columnCase').value='RS_SUM';ids.get('columnCase').trigger('change');await flush();take().done(clone('spectral'));await flush();
  assert.match(ids.get('columnContext').textContent,/karşılaştırılabilir kritik radyal kayıt yok/);
  assert.doesNotMatch(ids.get('columnForces').textContent,/Tolerans içinde/);
  assert.match(ids.get('columnOverviewDetails').textContent,/Statik hesap kaydı yok/);
  ids.get('columnCase').value='';ids.get('columnMember').value='';
  ids.get('columnView').trigger('change');await flush();const failed=clone('all');
  failed.demand_page.rows[0].status='REFERENCE_UNRESOLVED';failed.demand_page.rows[0].reference_capacity_knm=null;
  failed.demand_page.rows[1].status='NUMERICAL_COMPARISON_MISMATCH';
  failed.demand_page.rows[1].absolute_difference_knm=10;failed.demand_page.rows[1].comparison_budget_knm=1;
  take().done(failed);await flush();
  assert.match(ids.get('columnForces').textContent,/Referans çözülemedi/);assert.match(ids.get('columnForces').textContent,/Tolerans dışında/);
  for(const bad of ['source','filter','full_scope','material','budget','selection','row_gate','false_match','missing',
    'old_solver','old_primary_schema','old_primary_basis','old_primary_revision','native_P_missing','native_M2_string','native_M3_null',
    'point_missing','point_N','point_M','point_c','point_theta','root_residual','root_budget','root_interpolation']) {
    ids.get('columnView').trigger('change');await flush();const r=clone('all');const q=r.column_pmm_quality;
    if(bad==='source')q.source_pmm_result_sha256='OTHER';
    if(bad==='filter')q.output_case_filter='OTHER';
    if(bad==='full_scope')q.full_primary_population_independently_checked=true;
    if(bad==='material')q.independent_material_model_validation=true;
    if(bad==='budget')q.numerical_policy.primary_level_spread_added_to_budget=true;
    if(bad==='selection')q.selected_design='16Φ24';
    if(bad==='row_gate')r.demand_page.rows[0].final_design_eligible=true;
    if(bad==='false_match')r.demand_page.rows[0].absolute_difference_knm=100;
    if(bad==='missing')delete r.column_pmm_quality;
    if(bad==='old_solver')q.primary_solver_revision='OLD_POLYGON_MINIMUM';
    if(bad==='old_primary_schema')r.column_pmm.schema='tbdy.next.column-pmm-scenarios.v2';
    if(bad==='old_primary_basis')r.column_pmm.numerical_policy.basis='COARSE_POLYGON_MINIMUM';
    if(bad==='old_primary_revision')r.column_pmm.numerical_policy.solver_revision='OLD_POLYGON_MINIMUM';
    if(bad==='native_P_missing')delete r.demand_page.rows[0].native_values.P;
    if(bad==='native_M2_string')r.demand_page.rows[0].native_values.M2=String(r.demand_page.rows[0].native_values.M2);
    if(bad==='native_M3_null')r.demand_page.rows[0].native_values.M3=null;
    const point=r.demand_page.rows[0].primary_direction_root;
    if(bad==='point_missing')delete r.demand_page.rows[0].primary_direction_root;
    if(bad==='point_N')point.point.n_n+=100;
    if(bad==='point_M')point.point.m2_nmm*=1.1;
    if(bad==='point_c')point.point.c_mm=0;
    if(bad==='point_theta')point.point.theta_deg=120;
    if(bad==='root_residual')point.direction_residual_nmm=1001;
    if(bad==='root_budget')point.direction_tolerance_nmm=1001;
    if(bad==='root_interpolation')point.interpolated_strain_plane_used=true;
    take().done(r);await flush();assert.match(ids.get('columnStatus').textContent,/uyuşmuyor/);
    assert.equal(ids.get('columnForces').children.length,0);assert.equal(ids.get('columnExports').children.length,0);
    assert.equal(ids.get('columnOverviewDetails').children.length,0);
  }
  console.log('VS21–VS25 UI: root equilibrium evidence, explicit critical subset, numerical mismatch/failure, filters and stale/source/authority guards PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
