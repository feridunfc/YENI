/* Explicit joint scenarios: production payloads, selection, scope and stale guards. */
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
from scwb_scenario_fixture import ScenarioBank
from tbdy_next.column_engine.store import save_column_bank,read_column_bank
with TemporaryDirectory() as directory:
    root=Path(directory);receipts=root/'receipts';result={}
    for key in ('all','ambiguous','blocked'):
        fixture=ScenarioBank()
        if key=='ambiguous':fixture.beam_rows.append(deepcopy(fixture.beam_rows[0]))
        if key=='blocked':fixture.calls.pop(('PointObj.GetCoordCartesian','point','PX+'))
        source=root/(key+'.zip');source.write_bytes(fixture.build());run=save_column_bank(source,receipts)['run_id']
        result[key]=read_column_bank(receipts,run,view='scwb-scenarios')
        if key=='all':
            result['member']=read_column_bank(receipts,run,view='scwb-scenarios',member_id='C_SYNTHETIC_1')
            result['alternate']=read_column_bank(receipts,run,view='scwb-scenarios',member_id='C_SYNTHETIC_1',column_label='16Φ28',beam_diameter=24)
            result['spectral']=read_column_bank(receipts,run,view='scwb-scenarios',member_id='C_SYNTHETIC_1',column_label='16Φ28',beam_diameter=24,output_case='RS_SUM')
    print(json.dumps(result,ensure_ascii=True))
`],{cwd:root,encoding:'utf8',maxBuffer:10*1024*1024,env:{...process.env,
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
ids.get('columnView').value='scwb-scenarios';ids.get('columnProposal').value='16Φ24';ids.get('columnBeamProposal').value='20';
const pending=[],window={};
vm.runInNewContext(fs.readFileSync(path.join(root,'src/tbdy_next/static/column.js'),'utf8'),{
  window,URLSearchParams,document:{getElementById:id=>ids.get(id),createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)},
  fetch(url) {return new Promise(resolve=>pending.push({url,done:(body,ok=true)=>resolve({ok,json:async()=>body})}));}
});
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
const take=()=>{assert.ok(pending.length);return pending.shift();};
const descendants=e=>[e,...e.children.flatMap(descendants)];
const clone=key=>structuredClone(samples[key]);
const rows=()=>ids.get('columnForces').children[0].children[1].children;
(async()=>{
  window.openColumnBank();take().done({runs:['all','ambiguous','blocked'].map(key=>({run_id:samples[key].run_id,force_row_count:64}))});await flush();
  ids.get('columnRun').value=samples.all.run_id;ids.get('columnRun').trigger('change');await flush();
  const initial=take();assert.match(initial.url,/view=scwb-scenarios/);assert.match(initial.url,/column_cage=16%CE%A624/);assert.match(initial.url,/beam_diameter=20/);
  initial.done(clone('all'));await flush();assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  assert.equal(rows().length,6);assert.match(ids.get('columnForces').textContent,/Koşullu oran ≥1/);
  assert.match(ids.get('columnForces').textContent,/Senaryo referansını karşılıyor/);
  assert.doesNotMatch(ids.get('columnForces').textContent,/result_id|source_row_id|UYGUN|PASS/);
  assert.match(ids.get('columnUnits').textContent,/kolon kaynak N/);assert.match(ids.get('columnUnits').textContent,/kiriş N=0/);
  assert.equal(ids.get('columnCase').disabled,false);assert.equal(ids.get('columnProposalControl').hidden,false);assert.equal(ids.get('columnBeamProposalControl').hidden,false);
  ids.get('columnView').trigger('change');await flush();const old=take();
  ids.get('columnMember').value='C_SYNTHETIC_1';ids.get('columnMember').trigger('change');await flush();take().done(clone('member'));await flush();
  old.done(clone('all'));await flush();assert.equal(rows().length,4);
  assert.match(ids.get('columnOverviewDetails').textContent,/C_SYNTHETIC_2/);
  assert.match(ids.get('columnOverviewDetails').textContent,/BX\+\/I/);assert.match(ids.get('columnOverviewDetails').textContent,/BX-\/J/);
  assert.match(ids.get('columnOverviewDetails').textContent,/Tam hassasiyet/);
  assert.ok(descendants(ids.get('columnOverviewDetails')).filter(e=>e.tag==='details').every(e=>!('open' in e.attributes)));
  ids.get('columnProposal').value='16Φ28';ids.get('columnProposal').trigger('change');await flush();const pendingProposal=take();
  ids.get('columnBeamProposal').value='24';ids.get('columnBeamProposal').trigger('change');await flush();const alternate=take();
  assert.match(alternate.url,/column_cage=16%CE%A628/);assert.match(alternate.url,/beam_diameter=24/);
  alternate.done(clone('alternate'));await flush();pendingProposal.done(clone('member'));await flush();
  assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);assert.match(ids.get('columnContext').textContent,/kolon 16Φ28 \/ kiriş Φ24/);
  ids.get('columnCase').value='RS_SUM';ids.get('columnCase').trigger('change');await flush();const spectral=take();
  assert.match(spectral.url,/case=RS_SUM/);spectral.done(clone('spectral'));await flush();
  assert.match(ids.get('columnForces').textContent,/Statik kolon N kaydı yok/);assert.doesNotMatch(ids.get('columnForces').textContent,/Senaryo referansını karşılıyor/);
  ids.get('columnProposal').value='16Φ24';ids.get('columnBeamProposal').value='20';ids.get('columnRun').value=samples.ambiguous.run_id;
  ids.get('columnRun').trigger('change');await flush();take().done(clone('ambiguous'));await flush();
  const incomplete=rows().find(r=>r.textContent.includes('Katılımcı kapasitesi eksik'));assert.ok(incomplete);
  assert.equal(incomplete.children[7].textContent,'—');assert.equal(incomplete.children[5].textContent,'—');
  ids.get('columnRun').value=samples.all.run_id;ids.get('columnRun').trigger('change');await flush();take().done(clone('all'));await flush();
  // An explicit deficient conditional reference stays visible, with no approval label.
  ids.get('columnView').trigger('change');await flush();const below=clone('all');
  const deficient=below.demand_page.rows.find(r=>r.minimum_normalized_scenario_ratio!==null);
  deficient.minimum_normalized_scenario_ratio=.8;deficient.scenario_reference_satisfied=false;deficient.status='SCENARIO_REFERENCE_NOT_SATISFIED';
  take().done(below);await flush();assert.match(ids.get('columnForces').textContent,/Senaryo referansının altında/);
  for(const bad of ['source','beam_source','factor','transfer','nd','actual_cage','selection','case_basis','scwb_ratio',
      'filter','choice','partial_min','row_approval','negative_ratio','missing']) {
    ids.get('columnView').trigger('change');await flush();const r=clone('all'),s=r.scwb_scenarios,row=r.demand_page.rows.find(x=>x.minimum_normalized_scenario_ratio!==null);
    if(bad==='source')s.source_scwb_result_sha256='OTHER';
    if(bad==='beam_source')s.source_beam_result_sha256='OTHER';
    if(bad==='factor')s.factor=1;
    if(bad==='transfer')s.physical_joint_moment_transfer_proven=true;
    if(bad==='nd')s.earthquake_compatible_minimum_proven=true;
    if(bad==='actual_cage')s.actual_or_selected_cages_bound=true;
    if(bad==='selection')s.selected_design='16Φ24/Φ20';
    if(bad==='case_basis')s.case_basis='SAME_DESIGN_STATE';
    if(bad==='scwb_ratio')row.scwb_ratio=2;
    if(bad==='filter')s.output_case_filter='OTHER';
    if(bad==='choice')s.display_column_label='16Φ28';
    if(bad==='partial_min')row.calculated_case_rotation_count=1;
    if(bad==='row_approval')row.final_design_eligible=true;
    if(bad==='negative_ratio')row.minimum_normalized_scenario_ratio=-1;
    if(bad==='missing')delete r.scwb_scenarios;
    take().done(r);await flush();assert.match(ids.get('columnStatus').textContent,/uyuşmuyor/);
    assert.equal(ids.get('columnForces').children.length,0);assert.equal(ids.get('columnExports').children.length,0);
    assert.equal(ids.get('columnOverviewDetails').children.length,0);
  }
  ids.get('columnRun').value=samples.blocked.run_id;ids.get('columnRun').trigger('change');await flush();take().done(clone('blocked'));await flush();
  assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  assert.match(ids.get('columnContext').textContent,/2 bilinen kolon \/ 4 beklenen kolon ucu korunur/);
  assert.match(ids.get('columnContext').textContent,/birleşim ve senaryo paydası bilinmiyor/);
  assert.equal(ids.get('columnForces').children.length,0);
  console.log('VS24 UI: explicit paired scenarios, native moment branches, complete minima, filters and stale/source/authority guards PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
