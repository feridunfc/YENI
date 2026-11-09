/* VS20 presentation contract, stale response and explicit proposal regressions. */
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
    result={'all':read_column_bank(receipts,run,view='overview'),
        'member':read_column_bank(receipts,run,view='overview',member_id='C_SYNTHETIC_1'),
        'spectral':read_column_bank(receipts,run,view='overview',member_id='C_SYNTHETIC_1',output_case='RS_SUM')}
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
ids.get('columnView').value='overview';ids.get('columnProposal').value='16Φ24';
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
  const initial=take();assert.match(initial.url,/view=overview/);initial.done(clone('all'));await flush();
  assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  const cells=ids.get('columnForces').textContent;
  for(const value of ['N kaynak (kN)','M2 kaynak (kN·m)','M3 kaynak (kN·m)','16Φ24','0,2410','Ve bekleniyor','Girdiler bekleniyor']) assert.ok(cells.includes(value),value);
  assert.ok(!cells.includes('state_id'));assert.ok(!cells.includes('source_row_id'));assert.ok(!cells.includes('0.24096737015975592'));
  assert.ok(ids.get('columnUnits').textContent.includes('Doğrulanmış Nd/M2d/M3d'));
  const body=ids.get('columnForces').children[0].children[1];assert.equal(body.children.length,2);
  const stale=(()=>{ids.get('columnView').trigger('change');return take();})();
  ids.get('columnProposal').value='16Φ28';ids.get('columnProposal').trigger('change');await flush();
  take().done(clone('all'));await flush();stale.done(clone('all'));await flush();
  assert.match(ids.get('columnForces').textContent,/16Φ28/);
  assert.doesNotMatch(ids.get('columnForces').textContent,/16Φ24/);
  const inspect=descendants(ids.get('columnForces')).find(e=>e.tag==='button');
  assert.equal(inspect.attributes['aria-label'],'C_SYNTHETIC_1 kolonunu incele');inspect.trigger('click');await flush();
  const member=take();assert.match(member.url,/member=C_SYNTHETIC_1/);member.done(clone('member'));await flush();
  assert.match(ids.get('columnOverviewDetails').textContent,/PMM kapsamı ve kritik kayıtlar/);
  assert.match(ids.get('columnOverviewDetails').textContent,/Görüntülenen PMM kaydıyla aynı durumdaki kesme/);
  assert.ok(descendants(ids.get('columnOverviewDetails')).filter(e=>e.tag==='details').every(e=>!e.attributes.open));
  ids.get('columnCase').value='RS_SUM';ids.get('columnCase').trigger('change');await flush();
  const spectral=take();assert.match(spectral.url,/case=RS_SUM/);spectral.done(clone('spectral'));await flush();
  assert.match(ids.get('columnForces').textContent,/Statik hesap kaydı yok/);
  assert.doesNotMatch(ids.get('columnForces').textContent,/0,1978/);
  ids.get('columnMember').value='';ids.get('columnCase').value='';
  for(const bad of ['source','filter','selection','design_values']) {
    ids.get('columnView').trigger('change');await flush();const r=clone('all');
    if(bad==='source') r.column_overview.source_pmm_result_sha256='OTHER';
    if(bad==='filter') r.column_overview.output_case_filter='OTHER';
    if(bad==='selection') r.column_overview.automatic_design_selection=true;
    if(bad==='design_values') r.demand_page.rows[0].scenarios[1].design_values.M2d_knm=100;
    take().done(r);await flush();
    assert.match(ids.get('columnStatus').textContent,/uyuşmuyor/);
    assert.equal(ids.get('columnForces').children.length,0);
    assert.equal(ids.get('columnExports').children.length,0);
    assert.equal(ids.get('columnOverviewDetails').children.length,0);
  }
  console.log('VS20 UI: one vector per member, explicit proposal, precision, details, filters and stale/authority guards PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
