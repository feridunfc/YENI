/* Actual VS26 production projections: compact summary, drilldown and provenance. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {execFileSync}=require('node:child_process');const root=path.join(__dirname,'..');
const samples=JSON.parse(execFileSync('python',['-c',`
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from column_spectral_fixture import SpectralBank
from tbdy_next.column_engine.store import save_column_bank,read_column_bank
with TemporaryDirectory() as folder:
    root=Path(folder);source=root/'source.zip';receipts=root/'receipts';f=SpectralBank()
    for member,rows in f.forces.items():
        starts=[deepcopy(r) for r in rows if r[1]==0]
        for i in range(1,5):
            for original in starts:
                row=deepcopy(original);row[1]=row[3]=i/10;rows.append(row)
    source.write_bytes(f.build());run=save_column_bank(source,receipts)['run_id'];r={}
    r['all']=read_column_bank(receipts,run,view='spectral-design')
    r['cage']=read_column_bank(receipts,run,view='spectral-design',column_label='16Φ28')
    r['empty']=read_column_bank(receipts,run,view='spectral-design',output_case='SUM')
    r['member']=read_column_bank(receipts,run,view='spectral-design',member_id='C_SYNTHETIC_1',output_case='RS_SUM')
    r['candidates']=read_column_bank(receipts,run,view='spectral-candidates')
    r['next']=read_column_bank(receipts,run,view='spectral-candidates',offset=200)
    r['drill']=read_column_bank(receipts,run,view='spectral-candidates',member_id='C_SYNTHETIC_1',output_case='CAPTURED_HIGH')
    f=SpectralBank();f.forces[f.members[0]].remove(f.source_row('RS_SUM','Min'));source.write_bytes(f.build())
    run=save_column_bank(source,receipts)['run_id'];r['blocked']=read_column_bank(receipts,run,view='spectral-design')
    print(json.dumps(r,ensure_ascii=True))
`],{cwd:root,encoding:'utf8',maxBuffer:16*1024*1024,env:{...process.env,
  PYTHONPATH:[path.join(root,'src'),__dirname].join(path.delimiter),PYTHONUTF8:'1'}}));
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.events={};this.value='';this.text='';this.disabled=false;this.attributes={};}
  append(...nodes){this.children.push(...nodes);} replaceChildren(...nodes){this.text='';this.children=nodes;}
  set textContent(value){this.text=String(value);this.children=[];} get textContent(){return this.text+this.children.map(c=>c.textContent).join(' ');}
  addEventListener(event,callback){this.events[event]=callback;} trigger(event){return this.events[event]?.();}
  setAttribute(name,value){this.attributes[name]=String(value);}
}
const html=fs.readFileSync(path.join(root,'src/tbdy_next/static/index.html'),'utf8');
assert.match(html,/value="spectral-design">Depremli tasarım talebi/);
const ids=new Map([...html.matchAll(/id="(column[^"]+)"/g)].map(m=>[m[1],new Element()]));
ids.get('columnView').value='spectral-design';ids.get('columnProposal').value='16Φ24';
const pending=[],window={};
vm.runInNewContext(fs.readFileSync(path.join(root,'src/tbdy_next/static/column.js'),'utf8'),{window,URLSearchParams,
 document:{getElementById:id=>ids.get(id),createElement:tag=>new Element(tag)},
 fetch(url){return new Promise(resolve=>pending.push({url,done:(body,ok=true)=>resolve({ok,json:async()=>body})}));}
});
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
const take=()=>{assert.ok(pending.length);return pending.shift();};const clone=k=>structuredClone(samples[k]);
const rows=()=>ids.get('columnForces').children[0].children[1].children;
const descendants=e=>[e,...e.children.flatMap(descendants)];
(async()=>{
 window.openColumnBank();take().done({runs:['all','blocked'].map(k=>({run_id:samples[k].run_id,force_row_count:100}))});await flush();
 ids.get('columnRun').value=samples.all.run_id;ids.get('columnRun').trigger('change');await flush();
 const first=take();assert.match(first.url,/view=spectral-design/);assert.match(first.url,/column_cage=/);first.done(clone('all'));await flush();
 assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);assert.equal(rows().length,2);
 assert.equal(ids.get('columnProposalControl').hidden,false);assert.equal(ids.get('columnExports').children.length,3);
 assert.match(ids.get('columnForces').textContent,/CAPTURED_HIGH/);assert.match(ids.get('columnForces').textContent,/Koşullu PMM/);
 assert.doesNotMatch(ids.get('columnForces').textContent,/source_row_id|candidate_id|PASS|UYGUN/);
 assert.match(ids.get('columnContext').textContent,/Ara N/);assert.match(ids.get('columnUnits').textContent,/eşzamanlı/);
 assert.match(ids.get('columnContext').textContent,/Golden rapor kabul kapısı açık/);
 assert.ok(descendants(ids.get('columnOverviewDetails')).filter(e=>e.tag==='details').every(e=>!('open' in e.attributes)));
 const forensic=ids.get('columnExports').children[2];assert.match(forensic.href,/export-spectral-design\?run_id=/);
 assert.doesNotMatch(forensic.href,/view=|member=|case=|offset=/);
 const drill=descendants(ids.get('columnForces')).find(e=>e.tag==='button');drill.trigger('click');await flush();
 const request=take();assert.match(request.url,/view=spectral-candidates/);assert.match(request.url,/member=C_SYNTHETIC_1/);assert.match(request.url,/case=CAPTURED_HIGH/);
 request.done(clone('drill'));await flush();assert.equal(rows().length,64);assert.match(ids.get('columnOverviewDetails').textContent,/source_envelope_content_sha256/);
 ids.get('columnMember').value='';ids.get('columnCase').value='';ids.get('columnView').trigger('change');await flush();take().done(clone('candidates'));await flush();
 assert.equal(rows().length,200);assert.equal(ids.get('columnNext').disabled,false);
 ids.get('columnNext').trigger('click');await flush();const next=take();assert.match(next.url,/offset=200/);next.done(clone('next'));await flush();
 assert.equal(rows().length,56);assert.equal(ids.get('columnNext').disabled,true);assert.match(ids.get('columnPage').textContent,/201–256 \/ 256/);
 assert.match(ids.get('columnExports').children[0].href,/offset=200/);
 ids.get('columnView').value='spectral-design';ids.get('columnView').trigger('change');await flush();const stale=take();
 ids.get('columnProposal').value='16Φ28';ids.get('columnProposal').trigger('change');await flush();take().done(clone('cage'));await flush();stale.done(clone('all'));await flush();
 assert.equal(rows().length,2);assert.match(ids.get('columnForces').textContent,/16Φ28/);
 ids.get('columnProposal').value='16Φ24';ids.get('columnCase').value='SUM';ids.get('columnCase').trigger('change');await flush();take().done(clone('empty'));await flush();
 assert.equal(rows().length,2);assert.match(ids.get('columnForces').textContent,/Çözülen radyal oran yok/);
 ids.get('columnRun').value=samples.blocked.run_id;ids.get('columnRun').trigger('change');await flush();take().done(clone('blocked'));await flush();
 assert.match(ids.get('columnForces').textContent,/kapsamı.*eksik/);assert.doesNotMatch(ids.get('columnStatus').textContent,/gösterilemedi/);
 ids.get('columnRun').value=samples.all.run_id;ids.get('columnRun').trigger('change');await flush();take().done(clone('all'));await flush();
 for(const bad of ['missing','source','parent','policy','rule','physical','continuous','second_order','factor','solver','scope','page','cage','nonfinite','sign','station','ratio','hide_failure','golden_missing','golden_promotion','golden_manifest','golden_normative']){
   ids.get('columnView').trigger('change');await flush();const r=clone('all'),s=r.column_spectral_design,p=r.spectral_pmm,row=r.demand_page.rows[0],state=row.governing_resolved;
   if(bad==='missing')delete r.spectral_pmm;
   if(bad==='source')s.source_archive_sha256='OTHER';
   if(bad==='parent')p.source_population_result_sha256='0'.repeat(64);
   if(bad==='policy')s.permutation_policy='OLD';
   if(bad==='rule')s.applicable_design_rule='TBDY_APPROVED';
   if(bad==='physical')s.physical_concurrency_proven=true;
   if(bad==='continuous')p.continuous_axial_envelope_complete=true;
   if(bad==='second_order')s.second_order_applied=true;
   if(bad==='factor')s.additional_directional_factor_applied=true;
   if(bad==='solver')p.numerical_policy.solver_revision='OTHER';
   if(bad==='scope')r.demand_page.member_id='OTHER';
   if(bad==='page')r.demand_page.offset=1;
   if(bad==='cage')r.demand_page.column_label='16Φ28';
   if(bad==='nonfinite')state.forces.N_kN=NaN;
   if(bad==='sign')state.sign_id='CONCURRENT_VECTOR';
   if(bad==='station')state.station_key.Obj='OTHER';
   if(bad==='ratio')state.conditional_pmm_ratio=null;
   if(bad==='hide_failure')row.unresolved_or_axial_outside_count=1;
   if(bad==='golden_missing')delete r.golden_regression_gate;
   if(bad==='golden_promotion')r.golden_regression_gate.acceptance_eligible=true;
   if(bad==='golden_manifest')r.golden_regression_gate.source_manifest_sha256='0'.repeat(64);
   if(bad==='golden_normative')r.golden_regression_gate.normative_qualification='PROVEN';
   take().done(r);await flush();assert.match(ids.get('columnStatus').textContent,/uyuşmuyor/,bad);
   assert.equal(ids.get('columnForces').children.length,0);assert.equal(ids.get('columnExports').children.length,0);
 }
 ids.get('columnView').value='spectral-candidates';
 for(const bad of ['candidate_parent','candidate_forces','candidate_cut','candidate_rule','evidence_input','evidence_missing']){
   ids.get('columnView').trigger('change');await flush();const r=clone('candidates'),row=r.demand_page.rows[0],c=row.design_candidate;
   if(bad==='candidate_parent')c.source_replay_result_sha256='0'.repeat(64);
   if(bad==='candidate_forces')c.forces.N_kN+=1;
   if(bad==='candidate_cut')c.station_key.Elm='OTHER';
   if(bad==='candidate_rule')c.applicable_design_rule='TBDY_APPROVED';
   if(bad==='evidence_input')row.numerical_evidence.N_N+=1;
   if(bad==='evidence_missing')row.numerical_evidence=null;
   take().done(r);await flush();assert.match(ids.get('columnStatus').textContent,/uyuşmuyor/,bad);
   assert.equal(ids.get('columnForces').children.length,0);
 }
 console.log('VS26 design UI: compact governing view, full lineage drilldown, cage/case filters, paging, separate forensic export, stale and authority guards PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
