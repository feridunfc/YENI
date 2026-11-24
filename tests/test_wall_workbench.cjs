'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const asset = name => fs.readFileSync(path.join(__dirname, '../src/tbdy_next/static', name), 'utf8');
const requests = [];
const assignments = {beamSelection: {cage: 'beam draft'}, columnSelection: {cage: 'column draft'}};
const controls = new Map();
const document = {getElementById(id) {
  if (!controls.has(id)) controls.set(id, {value: id === 'deskModalCase' ? 'Modal' : 'RUN-base', classList: {toggle() {}}});
  return controls.get(id);
}};
const window = {TBDYWorkspace: {getState: () => ({assignments}), setLiveBusy() {}}, engineConsole: {log() {}}};
const source = asset('workspace-source.js');
vm.runInNewContext(source.replace('  workspace.setLoader(', '  window.runLive = runLive; return;\n  workspace.setLoader('), {
  window, document, URLSearchParams, location: {search: ''},
  async fetch(url, options) {
    assert.equal(options.method, 'POST');
    requests.push(new URL(url, 'http://localhost'));
    throw new Error('Request recorded');
  },
});

async function checkRequests() {
  const strength = {source: 'ASSIGNED_DESIGN', groups: {upper: ['Crack_SeisX_Soil']}};
  await window.runLive();
  await window.runLive(strength);
  await window.runLive(strength, 'ALL');
  await window.runLive(strength, '225');
  assert.equal(requests.length, 4);
  assert.equal(requests[0].pathname, '/api/live-vs04');
  assert.deepEqual([...requests[0].searchParams], [['case', 'Modal']]);
  assert.equal(requests[1].searchParams.get('check'), 'column-axial');
  for (const key of ['member', 'column_selection', 'beam_selection']) assert.ok(!requests[1].searchParams.has(key));
  for (const [i, member] of [[2, 'ALL'], [3, '225']]) {
    const q = requests[i].searchParams;
    assert.equal(q.get('check'), 'column-pmm');
    assert.equal(q.get('member'), member);
    assert.deepEqual(JSON.parse(q.get('assignments')), strength.groups);
    assert.deepEqual(JSON.parse(q.get('column_selection')), assignments.columnSelection);
    assert.deepEqual(JSON.parse(q.get('beam_selection')), assignments.beamSelection);
  }
}

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.attributes = {}; this.events = {}; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(event, callback) { this.events[event] = callback; }
}

function checkDetailRows() {
  const ui = {};
  const module = asset('workspace.js');
  const boundary = '  const minimumLongitudinalReference';
  vm.runInNewContext(module.replace(boundary, '  window.draw = drawTable; return;\n' + boundary), {
    window: ui, document: {createElement: tag => new Element(tag)},
  });
  const group = ['P2', '+0.00', '472'];
  const other = ['P2', '+4.50', '428'];
  const values = [['Net-area axial', 'Crack_SeisX_Soil', '472 Bottom', '2095.63 kN', '19600.00 kN', '10.69']];
  const host = new Element('div');
  host.id = 'deskResultTable';
  ui.draw(host, {headers: ['Pier', 'Storey', 'Wall IDs'], rows: [group, other],
    detailHeaders: ['Check', 'Combination', 'Face', 'Demand', 'Resistance', 'Utilization (%)'],
    rowDetails: new Map([[JSON.stringify(other), []], [JSON.stringify(group), values]])});
  const [line1, detail1, line2, detail2] = host.children[0].children[1].children;
  const toggle1 = line1.children.at(-1).children[0];
  const toggle2 = line2.children.at(-1).children[0];
  assert.equal(detail1.hidden, false);
  assert.equal(detail2.hidden, true);
  assert.equal(toggle2.attributes['aria-controls'], detail2.id);
  assert.equal(toggle1.attributes['aria-expanded'], 'true');
  const nested = detail1.children[0].children[0];
  assert.deepEqual(nested.children[1].children[0].children.map(x => x.textContent), values[0]);
  toggle2.events.click();
  assert.equal(detail2.hidden, false);
  assert.equal(toggle2.attributes['aria-expanded'], 'true');
  toggle1.events.click();
  assert.equal(detail1.hidden, true);
}

checkRequests().then(() => { checkDetailRows(); console.log('Workbench capture scope and governing wall rows: PASS'); })
  .catch(error => { console.error(error); process.exitCode = 1; });
