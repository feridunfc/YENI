/* Controller regression with a minimal DOM double; this is not visual browser QA.
   Run: node tests/test_vs07_ui_state.cjs. All engineering payloads are synthetic. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const staticDir = path.join(__dirname, '..', 'src', 'tbdy_next', 'static');
const html = fs.readFileSync(path.join(staticDir, 'index.html'), 'utf8');
const script = fs.readFileSync(path.join(staticDir, 'quick.js'), 'utf8');

class Element {
  constructor(tag = 'div') {
    this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {};
    this.events = {}; this.style = {}; this.value = ''; this.className = '';
    this.text = ''; this.disabled = false;
    this.classList = {toggle: (name, force) => {
      const classes = new Set(this.className.split(' ').filter(Boolean));
      (force ?? !classes.has(name)) ? classes.add(name) : classes.delete(name);
      this.className = [...classes].join(' ');
    }};
  }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map(c => c.textContent).join(' '); }
  get options() { return this.children; }
  append(...nodes) { this.children.push(...nodes); }
  prepend(...nodes) { this.children.unshift(...nodes); }
  replaceChildren(...nodes) { this.text = ''; this.children = nodes; }
  setAttribute(key, value) { this.attributes[key] = value; }
  insertAdjacentElement(_where, node) { this.append(node); }
  addEventListener(name, handler) { this.events[name] = handler; }
  trigger(name) { return this.events[name]?.(); }
  scrollIntoView() { this.scrolled = true; }
  querySelectorAll(selector) {
    const match = selector.match(/^\[data-([\w-]+)(?:="([^"]+)")?\]$/);
    const all = this.children.flatMap(c => [c, ...c.querySelectorAll('*')]);
    if (!match) return selector === '*' ? all : [];
    const key = match[1].replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    return all.filter(c => c.dataset[key] !== undefined &&
      (match[2] === undefined || c.dataset[key] === match[2]));
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
const run = n => 'RUN-' + String(n).repeat(32);
const entry = n => ({run_id: run(n), model_name: 'SYNTHETIC_' + n,
  captured_at_utc: '2026-11-08T00:00:00Z', source_mode: 'SYNTHETIC', case: 'Modal',
  modal: {status: 'MEETS_NUMERICAL_CRITERION'}, geometry: {checks: []}});
const report = n => ({run_id: run(n), checks: [], check_inventory: {count: 5}});
const b2 = {status: 'SOURCE_PARTIAL', numeric_condition: 'PARTIAL_SYNTHETIC',
  source_coverage: {resolved: 3, expected: 4},
  comparison_coverage: {resolved: 1, expected: 4, unresolved: 3},
  source_rows: [], items: [], assumptions_notes: ['SYNTHETIC'], reason_codes: [],
  source_payload_sha256: 'SYNTHETIC_SOURCE', result_sha256: 'B2_RUN_2_ONLY'};
const b1 = {formal_compliance: 'NOT_PROVEN', source_candidate_wall_beams: 1,
  source_wall_load_rows: 1, b1_numerical: {formal_compliance: 'NOT_PROVEN',
    eta_ci_min: '0.8', numeric_condition: 'SYNTHETIC_B1', paired_results: []},
  story_direction_areas: [], assumptions_notes: [], beam_assumptions: [],
  result_sha256: 'B1_OLD_RUN_MUST_NOT_RETURN'};
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };

function boot(history = [entry(1), entry(2), entry(3)]) {
  const ids = new Map(), created = [], pending = [], calls = [];
  for (const match of html.matchAll(/<([a-z]+)\b[^>]*\bid="([^"]+)"[^>]*>/g)) {
    const el = new Element(match[1]); el.id = match[2];
    el.value = match[0].match(/\bvalue="([^"]*)"/)?.[1] || '';
    ids.set(el.id, el);
  }
  const context = {
    document: {getElementById: id => ids.get(id), createElement: tag => {
      const el = new Element(tag); created.push(el); return el;
    }},
    window: {showModalFullTable() {}, open() {}, location: {assign() {}}},
    URLSearchParams, setTimeout, active: 7,
    tabs: Array.from({length: 16}, (_, i) => 'Tab ' + i),
    selectTab(index) { context.active = index; context.window.renderQuickChecksForTab(index); },
    setTree(id, values) { ids.get(id).replaceChildren(...values.map(v => {
      const el = new Element('li'); el.textContent = v; return el;
    })); },
    fetch(url) {
      calls.push(url);
      const value = url === '/api/check-registry' ? {implemented_check_count: 2, checks: [
        {check_id: 'WEAK_STORY_B1', title: 'B1', tab_id: 9, panel_id: 'vs06-b1-panel'},
        {check_id: 'SOFT_STORY_B2', title: 'B2', tab_id: 9, panel_id: 'b2Panel'}
      ]} : url === '/api/quick-history' ? {runs: history} : undefined;
      if (value) return Promise.resolve({ok: true, json: async () => value});
      return new Promise(resolve => pending.push({url, resolve: body =>
        resolve({ok: true, json: async () => body})}));
    }
  };
  vm.runInNewContext(script, context, {filename: 'quick.js'});
  const take = prefix => {
    const index = pending.findIndex(p => p.url.startsWith(prefix));
    assert.ok(index >= 0, 'Missing request: ' + prefix);
    return pending.splice(index, 1)[0];
  };
  const chooser = () => created.find(e => e.attributes['aria-label'] === 'Raporlanacak kayıt');
  const select = async n => { chooser().value = run(n); chooser().trigger('change'); await flush(); };
  return {ids, context, calls, take, chooser, select};
}

(async () => {
  const ui = boot(); await flush();
  const delayedReport = ui.take('/api/export-checks?run_id=' + run(1));
  ui.ids.get('b1UseRun').trigger('click'); await flush();
  const delayedB1 = ui.take('/api/export-checks?run_id=' + run(1));
  ui.ids.get('c2Calculate').trigger('click'); await flush();
  const delayedC2 = ui.take('/api/vs06-drift-scenario?run_id=' + run(1));
  await ui.select(2);
  const exclusion = {story: '+13.00', applicability: 'NOT_APPLICABLE'};
  const scopedDrift = {status: 'SOURCE_COVERAGE_COMPLETE',
    evaluated_story_case_direction_count: 12, expected_story_case_direction_count: 12,
    items: [], excluded_stories: [exclusion]};
  ui.take('/api/export-checks?run_id=' + run(2)).resolve({...report(2),
    story_drift: scopedDrift, soft_story_b2: {...b2, excluded_stories: [exclusion]}});
  await flush();
  assert.match(ui.ids.get('b2Result').textContent, /B2_RUN_2_ONLY/);
  assert.match(ui.ids.get('b2Result').textContent, /NOT_APPLICABLE.*\+13.00/);
  assert.match(ui.ids.get('storyDriftReport').textContent, /12\/12/);
  assert.match(ui.ids.get('storyDriftReport').textContent, /NOT_APPLICABLE.*\+13.00/);
  delayedReport.resolve({...report(1), soft_story_b2: {...b2, result_sha256: 'STALE_B2'}});
  delayedB1.resolve({...report(1), vs06_b1_result: b1});
  delayedC2.resolve({formal_compliance: 'NOT_PROVEN', engineering_release: 'NOT_READY',
    rows: [], scenario_sha256: 'STALE_C2'});
  await flush();
  assert.match(ui.ids.get('b2Result').textContent, /B2_RUN_2_ONLY/);
  assert.match(ui.ids.get('storyDriftReport').textContent, /12\/12/);
  assert.doesNotMatch(ui.ids.get('b1Result').textContent, /B1_OLD_RUN/);
  assert.equal(ui.ids.get('c2Report').textContent, '');
  assert.equal(ui.ids.get('b1Json').disabled, true);
  assert.equal(ui.ids.get('c2Calculate').disabled, false);
  ui.context.window.selectSavedEngineeringRun(entry(1), false);
  assert.equal(ui.chooser().value, run(2), 'Background modal history cannot replace selection');
  await ui.select(3);
  assert.doesNotMatch(ui.ids.get('b2Result').textContent, /B2_RUN_2_ONLY/);
  ui.take('/api/export-checks?run_id=' + run(3)).resolve(report(3)); await flush();
  assert.match(ui.ids.get('b2Result').textContent, /eski kayıtta/);
  ui.context.selectTab(1);
  assert.match(ui.ids.get('vs06-b1-panel').className, /hidden/);
  ui.context.selectTab(9);
  assert.doesNotMatch(ui.ids.get('vs06-b1-panel').className, /hidden/);
  assert.doesNotMatch(ui.ids.get('b2Panel').className, /hidden/);
  assert.equal(ui.calls.some(url => url.includes('/api/live-')), false);

  const old = boot([]); await flush();
  old.context.window.selectSavedEngineeringRun({...entry(3), result: entry(3).modal}, false);
  await flush();
  assert.equal(old.chooser().value, run(3), 'Modal-only archive remains selectable');
  old.take('/api/export-checks?run_id=' + run(3)).resolve(report(3)); await flush();
  console.log('UI controller: stale B1/B2/C2, shared history, historical selection and panel routing PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
