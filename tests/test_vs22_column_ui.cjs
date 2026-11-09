/* SCWB UI: complete neighbours, conditional column sums, no invented beam ratio. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
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
    result={'all':read_column_bank(receipts,run,view='scwb'),
        'member':read_column_bank(receipts,run,view='scwb',member_id='C_SYNTHETIC_1'),
        'spectral':read_column_bank(receipts,run,view='scwb',member_id='C_SYNTHETIC_1',output_case='RS_SUM')}
    fixture=KinematicsBank();fixture.calls.pop(('PointObj.GetCoordCartesian','point','PX+'))
    source=root/'blocked.zip';source.write_bytes(fixture.build());blocked=save_column_bank(source,receipts)['run_id']
    result['blocked']=read_column_bank(receipts,blocked,view='scwb')
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
const ids=new Map([...html.matchAll(/id="(column[^"]+)"/g)].map(m=>[m[1],new Element()]));
ids.get('columnView').value='scwb';ids.get('columnProposal').value='16Φ24';
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
  const initial=take();assert.match(initial.url,/view=scwb/);initial.done(clone('all'));await flush();
  assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  assert.match(ids.get('columnContext').textContent,/deprem yönüyle uyumlu Nd minimumu değildir/);
  assert.match(ids.get('columnForces').textContent,/En küçük ΣMrc kaynak/);
  assert.match(ids.get('columnForces').textContent,/Kiriş uç donatısı bekleniyor/);
  assert.doesNotMatch(ids.get('columnForces').textContent,/state_id|source_row_id|UYGUN|PASS/);
  assert.equal(ids.get('columnForces').children[0].children[1].children.length,36);
  assert.equal(ids.get('columnCase').disabled,false);
  const old=(()=>{ids.get('columnView').trigger('change');return take();})();
  ids.get('columnMember').value='C_SYNTHETIC_1';ids.get('columnMember').trigger('change');await flush();
  const member=take();assert.match(member.url,/member=C_SYNTHETIC_1/);member.done(clone('member'));await flush();
  old.done(clone('all'));await flush();
  assert.equal(ids.get('columnForces').children[0].children[1].children.length,24);
  assert.match(ids.get('columnOverviewDetails').textContent,/C_SYNTHETIC_2/);
  assert.match(ids.get('columnOverviewDetails').textContent,/BX\+/);
  assert.match(ids.get('columnOverviewDetails').textContent,/Tam hassasiyet/);
  assert.ok(descendants(ids.get('columnOverviewDetails')).filter(e=>e.tag==='details').every(e=>!e.attributes.open));
  ids.get('columnCase').value='RS_SUM';ids.get('columnCase').trigger('change');await flush();take().done(clone('spectral'));await flush();
  assert.match(ids.get('columnForces').textContent,/Statik kaynak vakası yok/);
  assert.doesNotMatch(ids.get('columnForces').textContent,/Kiriş uç donatısı bekleniyor|UYGUN|PASS/);
  ids.get('columnCase').value='';ids.get('columnMember').value='';
  ids.get('columnView').trigger('change');await flush();const topology=clone('all');
  Object.assign(topology.demand_page.rows[0],{status:'TOPOLOGY_UNRESOLVED',sampled_minimum_column_sum_knm:null,sampled_minimum_case_ids:[],topology_reasons:['OTHER_INCIDENT_FRAME_NOT_CLASSIFIED']});
  take().done(topology);await flush();assert.match(ids.get('columnForces').textContent,/Bağlantı geometrisi belirsiz/);
  for(const bad of ['source','filter','neighbours','required_as','nd_minimum','exception','selection','row_gate','ratio','beam_total','partial_min','missing']) {
    ids.get('columnView').trigger('change');await flush();const r=clone('all'),s=r.column_scwb,row=r.demand_page.rows[0];
    if(bad==='source')s.source_kinematics_result_sha256='OTHER';
    if(bad==='filter')s.output_case_filter='OTHER';
    if(bad==='neighbours')s.neighbouring_participants_retained=false;
    if(bad==='required_as')s.required_beam_steel_used_as_capacity=true;
    if(bad==='nd_minimum')s.earthquake_compatible_minimum_proven=true;
    if(bad==='exception')s.normative_exception_applied=true;
    if(bad==='selection')s.selected_design='16Φ24';
    if(bad==='row_gate')row.final_design_eligible=true;
    if(bad==='ratio')row.scwb_ratio=1.5;
    if(bad==='beam_total')row.sum_mrb_knm=0;
    if(bad==='partial_min'){row.sampled_minimum_column_sum_knm=100;row.calculated_column_sum_count=0;}
    if(bad==='missing')delete r.column_scwb;
    take().done(r);await flush();assert.match(ids.get('columnStatus').textContent,/uyuşmuyor/);
    assert.equal(ids.get('columnForces').children.length,0);assert.equal(ids.get('columnExports').children.length,0);
    assert.equal(ids.get('columnOverviewDetails').children.length,0);
  }
  ids.get('columnRun').value=samples.blocked.run_id;ids.get('columnRun').trigger('change');await flush();
  take().done(clone('blocked'));await flush();
  assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  assert.match(ids.get('columnContext').textContent,/2 bilinen kolon \/ 4 beklenen uç \/ 24 beklenen kapasite kaydı/);
  assert.match(ids.get('columnContext').textContent,/Birleşim sayısı bilinmiyor/);
  assert.equal(ids.get('columnForces').children[0].children[1].children.length,4);
  console.log('VS22 UI: complete neighbours, static-only minima, missing beam capacity, blocked population, filters and stale/source/authority guards PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
