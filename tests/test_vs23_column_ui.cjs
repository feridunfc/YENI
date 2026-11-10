/* Beam proposals: real adapter payloads, signed values, ambiguity and UI scope. */
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
from beam_reference_fixture import BeamBank
from tbdy_next.column_engine.store import save_column_bank,read_column_bank
with TemporaryDirectory() as directory:
    root=Path(directory);receipts=root/'receipts';result={}
    for key in ('all','ambiguous','blocked'):
        fixture=BeamBank()
        if key=='ambiguous':
            duplicate=deepcopy(fixture.beam_rows[0]);duplicate['totTopRebar']='.1';fixture.beam_rows.append(duplicate)
        if key=='blocked':fixture.calls.pop(('PointObj.GetCoordCartesian','point','PX+'))
        source=root/(key+'.zip');source.write_bytes(fixture.build());run=save_column_bank(source,receipts)['run_id']
        result[key]=read_column_bank(receipts,run,view='beam-cages')
        if key=='all':result['member']=read_column_bank(receipts,run,view='beam-cages',member_id='C_SYNTHETIC_1')
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
ids.get('columnView').value='beam-cages';ids.get('columnProposal').value='16Φ24';ids.get('columnBeamProposal').value='20';
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
  const initial=take();assert.match(initial.url,/view=beam-cages/);initial.done(clone('all'));await flush();
  assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  assert.equal(rows().length,8);assert.match(rows()[0].textContent,/4Φ20 3Φ20/);
  assert.match(ids.get('columnContext').textContent,/8\/8 filtrelenmiş uç kaynağı/);
  assert.match(ids.get('columnContext').textContent,/Gerekli As, uygulanmış donatı değildir/);
  assert.match(ids.get('columnUnits').textContent,/N=0 saf eğilme/);
  assert.match(ids.get('columnForces').textContent,/−M3/);
  assert.doesNotMatch(ids.get('columnForces').textContent,/candidate_id|source_row_id|UYGUN|PASS/);
  assert.equal(ids.get('columnCase').disabled,true);assert.equal(ids.get('columnBeamProposalControl').hidden,false);
  assert.equal(ids.get('columnProposalControl').hidden,true);
  ids.get('columnView').trigger('change');await flush();const stale=take();
  ids.get('columnMember').value='C_SYNTHETIC_1';ids.get('columnCase').value='RS_SUM';
  ids.get('columnMember').trigger('change');await flush();const member=take();
  assert.match(member.url,/member=C_SYNTHETIC_1/);assert.doesNotMatch(member.url,/case=/);
  member.done(clone('member'));await flush();stale.done(clone('all'));await flush();
  assert.equal(rows().length,4);assert.match(ids.get('columnOverviewDetails').textContent,/Tam hassasiyet/);
  let drawings=descendants(ids.get('columnOverviewDetails')).filter(e=>e.tag==='svg');
  assert.equal(drawings.length,4);
  let circles=descendants(drawings[0]).filter(e=>e.tag==='circle');assert.equal(circles.length,7);
  const profile=samples.member.beam_end_references.profiles[0];
  assert.equal(Number(circles[0].attributes.cy),-(profile.local2_height_mm/2-profile.cover_top_centroid_mm));
  assert.equal(Number(circles[0].attributes.r),10);
  assert.ok(descendants(ids.get('columnOverviewDetails')).filter(e=>e.tag==='details').every(e=>!('open' in e.attributes)));
  ids.get('columnBeamProposal').value='16';ids.get('columnBeamProposal').trigger('change');await flush();
  take().done(clone('member'));await flush();assert.match(rows()[0].textContent,/6Φ16 4Φ16/);
  drawings=descendants(ids.get('columnOverviewDetails')).filter(e=>e.tag==='svg');
  assert.equal(descendants(drawings[0]).filter(e=>e.tag==='circle').length,10);
  ids.get('columnBeamProposal').value='20';ids.get('columnRun').value=samples.ambiguous.run_id;
  ids.get('columnRun').trigger('change');await flush();take().done(clone('ambiguous'));await flush();
  assert.equal(rows().length,8);assert.match(ids.get('columnContext').textContent,/21\/24 donatı\/kapasite senaryosu/);
  assert.match(rows()[0].textContent,/Uç tasarım istasyonu belirsiz/);
  assert.equal(rows()[0].children[7].textContent,'—');assert.equal(rows()[0].children[8].textContent,'—');
  ids.get('columnRun').value=samples.all.run_id;ids.get('columnRun').trigger('change');await flush();take().done(clone('all'));await flush();
  // A one-sided numerical result remains unresolved in the compact table.
  ids.get('columnView').trigger('change');await flush();const partial=clone('all');
  const unresolved=partial.demand_page.rows[0].candidates[1];unresolved.status='BEAM_PROPOSAL_NUMERIC_UNRESOLVED';
  unresolved.capacity.status='BEAM_CAPACITY_UNRESOLVED';unresolved.capacity.negative_m3_knm=null;
  take().done(partial);await flush();assert.match(rows()[0].textContent,/Sayısal çözüm belirsiz/);
  assert.equal(rows()[0].children[7].textContent,'—');assert.equal(rows()[0].children[8].textContent,'—');
  for(const bad of ['source','filter','required_as','selection','source_n','ratio','row_gate','wrong_sign',
      'hidden_candidate_gate','control','blocked_capacity','diameters','missing']) {
    ids.get('columnView').trigger('change');await flush();const r=clone('all'),b=r.beam_end_references,row=r.demand_page.rows[0],c=row.candidates[1];
    if(bad==='source')b.source_joints_result_sha256='OTHER';
    if(bad==='filter')b.member_id_filter='OTHER';
    if(bad==='required_as')row.source.targets.total_required_area_is_provided=true;
    if(bad==='selection')b.selected_design='Φ20';
    if(bad==='source_n')c.capacity.source_beam_axial_force_applied=true;
    if(bad==='ratio')b.scwb_ratio=1.5;
    if(bad==='row_gate')row.final_design_eligible=true;
    if(bad==='wrong_sign')c.capacity.negative_m3_knm=1;
    if(bad==='hidden_candidate_gate')row.candidates[0].physical_cage_proven=true;
    if(bad==='control')row.source.targets.control_references.AsTopCombo.status='MISSING';
    if(bad==='blocked_capacity'){c.status='BEAM_PROPOSAL_BLOCKED';}
    if(bad==='diameters')b.policy.diameters_mm=[16,20,32];
    if(bad==='missing')delete r.beam_end_references;
    take().done(r);await flush();assert.match(ids.get('columnStatus').textContent,/uyuşmuyor/);
    assert.equal(ids.get('columnForces').children.length,0);assert.equal(ids.get('columnExports').children.length,0);
    assert.equal(ids.get('columnOverviewDetails').children.length,0);
  }
  ids.get('columnRun').value=samples.blocked.run_id;ids.get('columnRun').trigger('change');await flush();
  take().done(clone('blocked'));await flush();assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
  assert.match(ids.get('columnContext').textContent,/2 bilinen kolon korunur; kiriş\/uç sayısı bilinmiyor/);
  assert.equal(ids.get('columnForces').children.length,0);
  console.log('VS23 UI: signed N=0 beam proposals, centroid drawing, ambiguity, diameter/filter/stale/authority guards PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
