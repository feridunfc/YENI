/* Exact DOM test of the permanent right-side operation/error console. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const base = path.join(__dirname, '..', 'src', 'tbdy_next', 'static');
const html = fs.readFileSync(path.join(base, 'index.html'), 'utf8');
const js = fs.readFileSync(path.join(base, 'engine-console.js'), 'utf8');

class Element {
  constructor() {
    this.children = [];
    this.dataset = {};
    this.className = '';
    this.events = {};
    this.value = '';
    this.text = '';
  }
  set textContent(v) { this.text = String(v); }
  get textContent() {
    return this.text + this.children.map(x => x.textContent).join('');
  }
  append(...elements) { this.children.push(...elements); }
  prepend(element) { this.children.unshift(element); }
  replaceChildren(...elements) { this.children = elements; this.text = ''; }
  removeChild(element) {
    const idx = this.children.indexOf(element);
    assert.ok(idx >= 0);
    this.children.splice(idx, 1);
  }
  get lastElementChild() { return this.children[this.children.length-1]; }
  addEventListener(event, callback) { this.events[event] = callback; }
}

const start = html.indexOf('<aside class="rail"');
const release = html.indexOf('Mühendislik kabulü<strong>NOT_READY', start);
const consoleAt = html.indexOf('<section class="engine-console"', start);
assert.ok(start >= 0 && release > start && consoleAt > release);
assert.equal((html.match(/id="engineConsoleMessages"/g) || []).length, 1);
assert.equal((html.match(/id="engineConsoleClear"/g) || []).length, 1);
assert.ok(html.includes('<script src="/engine-console.js"></script>'));
assert.ok(html.includes('role="log"'));

const entries = new Element();
entries.dataset.empty = 'true';
const clear = new Element();
const events = {};
const win = {addEventListener(type, callback) { events[type] = callback; }};
const ctx = {
  document: {getElementById(id) {
    if(id === 'engineConsoleMessages') return entries;
    if(id === 'engineConsoleClear') return clear;
    return null;
  }, createElement() { return new Element(); }},
  window: win,
  Date, Error,
  Object, Set, String,
};
vm.runInNewContext(js, ctx, {filename: 'engine-console.js'});
assert.equal(typeof win.engineConsole.log, 'function');
win.engineConsole.log('error', 'ETABS / VS04G',
  'VS04G_PRESENT_UNITS_UNSUPPORTED:expected=6;observed=12');
assert.equal(entries.children.length, 1);
assert.ok(entries.children[0].textContent.includes('expected=6;observed=12'));
assert.ok(entries.children[0].className.includes('console-error'));
assert.equal(entries.dataset.empty, 'false');

win.engineConsole.log('error', 'XSS', '<img src=x onerror=alert(1)>');
assert.ok(entries.children[0].textContent.includes('<img'));
assert.equal(entries.children[0].innerHTML, undefined,
  'Console must use textContent, never HTML interpolation');

for(let i=0;i<45;i++) win.engineConsole.log('info', 'ETABS', 'record '+i);
assert.equal(entries.children.length, 40, 'bounded log retains last 40 only');
assert.ok(entries.children[0].textContent.includes('record 44'));
assert.ok(!entries.children.some(x => x.textContent.includes('record 0')));

events.unhandledrejection({reason: new Error('ASYNC_FAILURE')});
assert.ok(entries.children[0].textContent.includes('ASYNC_FAILURE'));
events.error({message: 'RENDER_FAILURE'});
assert.ok(entries.children[0].textContent.includes('RENDER_FAILURE'));

clear.events.click();
assert.equal(entries.dataset.empty, 'true');
assert.equal(entries.children.length, 1);
assert.ok(entries.children[0].textContent.includes('Henüz işlem kaydı yok'));
console.log('Engine right console: order, safety, bounded events, clear and errors PASS');
