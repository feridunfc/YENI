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
  console.log('VS11 column UI identity/filter/export regressions PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
