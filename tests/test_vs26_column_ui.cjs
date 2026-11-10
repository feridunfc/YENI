/* Production scalar-envelope payloads: bounded navigation and authority guards. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const root=path.join(__dirname,'..');
const samples=JSON.parse(execFileSync('python',['-c',`
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from column_spectral_fixture import SpectralBank
from tbdy_next.column_engine.store import save_column_bank,read_column_bank
with TemporaryDirectory() as directory:
    root=Path(directory);receipts=root/'receipts';result={}
    for key in ('all','blocked','mismatch'):
        fixture=SpectralBank()
        if key=='all':
            for member,rows in fixture.forces.items():
                starts=[deepcopy(r) for r in rows if r[1]==0]
                for i in range(1,61):
                    for original in starts:
                        row=deepcopy(original);row[1]=row[3]=i/100;rows.append(row)
        if key=='blocked':fixture.forces[fixture.members[0]].remove(fixture.source_row('RS_SUM','Min'))
        if key=='mismatch':fixture.source_row('RS_SUM')[11]+=.001
        source=root/(key+'.zip');source.write_bytes(fixture.build());run=save_column_bank(source,receipts)['run_id']
        result[key]=read_column_bank(receipts,run,view='spectral-envelopes')
        if key=='all':
            result['next']=read_column_bank(receipts,run,view='spectral-envelopes',offset=200)
            result['member']=read_column_bank(receipts,run,view='spectral-envelopes',member_id='C_SYNTHETIC_1',output_case='RS_SUM')
            result['empty']=read_column_bank(receipts,run,view='spectral-envelopes',member_id='C_SYNTHETIC_1',output_case='SUM')
    print(json.dumps(result,ensure_ascii=True))
`],{cwd:root,encoding:'utf8',maxBuffer:24*1024*1024,env:{...process.env,
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
ids.get('columnView').value='spectral-envelopes';
const pending=[],window={};
vm.runInNewContext(fs.readFileSync(path.join(root,'src/tbdy_next/static/column.js'),'utf8'),{
  window,URLSearchParams,document:{getElementById:id=>ids.get(id),createElement:tag=>new Element(tag)},
  fetch(url) {return new Promise(resolve=>pending.push({url,done:(body,ok=true)=>resolve({ok,json:async()=>body})}));}
});
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
const take=()=>{assert.ok(pending.length);return pending.shift();};
const descendants=e=>[e,...e.children.flatMap(descendants)];
const clone=key=>structuredClone(samples[key]);
const rows=()=>ids.get('columnForces').children[0].children[1].children;
(async()=>{
  window.openColumnBank();take().done({runs:['all','blocked','mismatch'].map(key=>({run_id:samples[key].run_id,force_row_count:64}))});await flush();
  ids.get('columnRun').value=samples.all.run_id;ids.get('columnRun').trigger('change');await flush();
  const initial=take();assert.match(initial.url,/view=spectral-envelopes/);initial.done(clone('all'));await flush();
  assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  assert.equal(rows().length,200);assert.match(ids.get('columnForces').textContent,/Kaynakla eşleşti/);
  assert.doesNotMatch(ids.get('columnForces').textContent,/source_row_id|UYGUN|PASS|final_design/);
  assert.match(ids.get('columnUnits').textContent,/N alt=−P üst/);assert.match(ids.get('columnUnits').textContent,/eşzamanlı/);
  assert.match(ids.get('columnOverviewDetails').textContent,/V2, V3 ve T/);
  assert.ok(descendants(ids.get('columnOverviewDetails')).filter(e=>e.tag==='details').every(e=>!('open' in e.attributes)));
  assert.equal(ids.get('columnNext').disabled,false);assert.equal(ids.get('columnExports').children.length,2);
  for(const a of ids.get('columnExports').children) {assert.match(a.textContent,/Bu sayfanın/);assert.match(a.href,/view=spectral-envelopes/);}
  ids.get('columnNext').trigger('click');await flush();const next=take();assert.match(next.url,/offset=200/);
  next.done(clone('next'));await flush();assert.equal(rows().length,56);assert.equal(ids.get('columnNext').disabled,true);
  assert.match(ids.get('columnPage').textContent,/201–256 \/ 256/);
  for(const a of ids.get('columnExports').children) assert.match(a.href,/offset=200/);
  ids.get('columnPrevious').trigger('click');await flush();take().done(clone('all'));await flush();assert.equal(rows().length,200);
  ids.get('columnView').trigger('change');await flush();const stale=take();
  ids.get('columnMember').value='C_SYNTHETIC_1';ids.get('columnCase').value='RS_SUM';ids.get('columnCase').trigger('change');await flush();
  const member=take();assert.match(member.url,/member=C_SYNTHETIC_1/);assert.match(member.url,/case=RS_SUM/);
  member.done(clone('member'));await flush();stale.done(clone('all'));await flush();assert.equal(rows().length,64);
  assert.match(ids.get('columnForces').textContent,/76,00 \/ 99,00/);
  for(const a of ids.get('columnExports').children) {assert.match(a.href,/member=C_SYNTHETIC_1/);assert.match(a.href,/case=RS_SUM/);}
  ids.get('columnCase').value='SUM';ids.get('columnCase').trigger('change');await flush();take().done(clone('empty'));await flush();
  assert.equal(rows().length,0);assert.match(ids.get('columnPage').textContent,/gösterilecek kayıt yok/);
  ids.get('columnRun').value=samples.blocked.run_id;ids.get('columnRun').trigger('change');await flush();take().done(clone('blocked'));await flush();
  assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  assert.match(ids.get('columnForces').textContent,/Kaynak bağı eksik/);assert.match(ids.get('columnContext').textContent,/PARTIAL/);
  ids.get('columnRun').value=samples.mismatch.run_id;ids.get('columnRun').trigger('change');await flush();take().done(clone('mismatch'));await flush();
  assert.match(ids.get('columnForces').textContent,/Kaynakla uyuşmuyor/);
  ids.get('columnRun').value=samples.all.run_id;ids.get('columnRun').trigger('change');await flush();take().done(clone('all'));await flush();
  for(const bad of ['missing','source','bank','policy','tolerance','code','physical','double_factor','unit','scope',
      'page','nd','nonfinite','reversed_n','source_key','source_factor','target_step','comparison_component','row_approval']) {
    ids.get('columnView').trigger('change');await flush();const r=clone('all'),s=r.column_spectral_envelopes,row=r.demand_page.rows[0];
    if(bad==='missing')delete r.column_spectral_envelopes;
    if(bad==='source')s.source_archive_sha256='OTHER';
    if(bad==='bank')s.source_bank_result_sha256='OTHER';
    if(bad==='policy')s.policy='OLD';
    if(bad==='tolerance')s.relative_tolerance='1e-3';
    if(bad==='code')s.code_rule_qualified=true;
    if(bad==='physical')s.physical_concurrency_proven=true;
    if(bad==='double_factor')s.additional_directional_factor_applied=true;
    if(bad==='unit')s.units.moment='kNcm';
    if(bad==='scope')s.member_id_filter='OTHER';
    if(bad==='page')r.demand_page.offset=200;
    if(bad==='nd')row.concurrent_force_vector={N:1,M2:2,M3:3};
    if(bad==='nonfinite')row.bounds.M2.upper=NaN;
    if(bad==='reversed_n')row.bounds.N.lower=-row.native_bounds.P.lower;
    if(bad==='source_key')row.source_terms[0].native_key.Elm='OTHER';
    if(bad==='source_factor')row.source_terms[0].factor=999;
    if(bad==='target_step')row.native_steps[0].native_key.StepNum=1;
    if(bad==='comparison_component')row.comparisons[0].component='M1';
    if(bad==='row_approval')row.final_design_eligible=true;
    take().done(r);await flush();assert.match(ids.get('columnStatus').textContent,/uyuşmuyor/,'guard '+bad);
    assert.equal(ids.get('columnForces').children.length,0);assert.equal(ids.get('columnExports').children.length,0);
    assert.equal(ids.get('columnOverviewDetails').children.length,0);
  }
  console.log('VS26 UI: scalar bounds, P/N reversal, exact lineage, pagination/export scope, source/policy/authority and stale guards PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
