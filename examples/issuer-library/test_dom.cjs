/* DOM simulation only: no browser, network, layout or screenshot assertions. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require(process.env.ISSUER_LIBRARY_JSDOM || 'jsdom');
const html = fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
function page(t) {
  const errors = [];
  const console = new VirtualConsole(); console.on('jsdomError', error => errors.push(error));
  const dom = new JSDOM(html, {url:'https://example.invalid/examples/issuer-library/index.html',runScripts:'dangerously',virtualConsole:console,beforeParse(window) {
    window.matchMedia = () => ({matches:true});
    window.HTMLElement.prototype.scrollIntoView = function() {};
  }});
  const {window} = dom, document = window.document;
  t.after(() => {assert.deepEqual(errors,[]); window.close();});
  const set = (id,value) => {const input=document.getElementById(id); input.value=value; input.dispatchEvent(new window.Event(input.tagName === 'SELECT' ? 'change' : 'input',{bubbles:true}));};
  return {window,document,set,click:id => document.getElementById(id).click(),rows:()=>[...document.querySelectorAll('#run-rows tr')]};
}
test('initial real dataset has seven runs and correct selected source values',t=>{
  const p=page(t);
  assert.equal(p.rows().length,7);
  const detail=p.document.getElementById('run-detail').textContent;
  assert.match(detail,/5.96×/); assert.match(detail,/3.60×/); assert.match(detail,/1,880/);
  assert.match(detail,/Workflow completeness · Not assessed/);
  assert.equal(p.document.querySelectorAll('#run-rows .progress-fill').length,0);
});
test('combining sector, basis and leverage selects only the annual TDG run',t=>{
  const p=page(t); p.set('sector','Aerospace & defense'); p.set('basis','Total carrying debt / EBITDA As Defined'); p.set('leverageMin','5');
  assert.equal(p.rows().length,1); assert.match(p.rows()[0].textContent,/Annual credit review/);
  assert.match(p.document.getElementById('metric-filter-count').textContent,/2 active/);
});
test('unassessed real completeness is not treated as a high score; empty state resets',t=>{
  const p=page(t); p.set('completion','75');
  assert.equal(p.rows().length,0); assert.equal(p.document.getElementById('empty-state').hidden,false);
  assert.equal(p.document.getElementById('run-detail').hidden,true);
  p.click('empty-reset'); assert.equal(p.rows().length,7);
});
test('fictional dataset stays separated and completion filters work',t=>{
  const p=page(t); p.click('demo-data');
  assert.equal(p.rows().length,6); assert.match(p.document.getElementById('dataset-note').textContent,/Fictional examples/);
  p.set('completion','75'); assert.equal(p.rows().length,3);
  assert.equal(p.document.querySelectorAll('#run-rows a').length,0);
  p.click('real-data'); assert.equal(p.rows().length,7); assert.equal(p.document.getElementById('completion').value,'');
});
test('report-only view includes direct and explicitly related annual reports',t=>{
  const p=page(t); p.click('reports-only'); assert.equal(p.rows().length,2);
  assert.match(p.rows()[1].textContent,/Related report/);
  for (const anchor of p.document.querySelectorAll('#run-rows a')) {
    const destination=path.resolve(__dirname,decodeURIComponent(anchor.getAttribute('href')));
    assert.ok(fs.existsSync(destination)); assert.equal(anchor.target,'_blank'); assert.equal(anchor.rel,'noopener');
  }
});
test('source details preserve an exact quoted row and provide a working local target',t=>{
  const p=page(t); p.document.querySelector('.metric-item .source-link').click();
  assert.equal(p.document.getElementById('metric-sources').open,true);
  assert.match(p.document.activeElement.textContent,/Net sales \| 7,940/);
  const anchor=p.document.activeElement.querySelector('a');
  assert.ok(fs.existsSync(path.resolve(__dirname,decodeURIComponent(anchor.getAttribute('href')))));
});
test('keyboard shortcut, selected detail focus and sort state work in the DOM',t=>{
  const p=page(t); p.document.dispatchEvent(new p.window.KeyboardEvent('keydown',{key:'/',bubbles:true}));
  assert.equal(p.document.activeElement.id,'search');
  p.document.querySelector('[data-sort="leverage"] button').click();
  assert.equal(p.document.querySelector('[data-sort="leverage"]').getAttribute('aria-sort'),'ascending');
  assert.match(p.rows()[0].textContent,/Ford Otosan/);
  p.rows()[0].querySelector('button').click(); assert.equal(p.document.activeElement.id,'run-detail');
  assert.match(p.document.getElementById('run-detail').textContent,/TRY m/);
});
test('template has no unresolved tokens, duplicate IDs or unlabeled filters',t=>{
  const p=page(t); assert.doesNotMatch(html,/\/\*(DATA|APP|LOGIC|STYLE|FONTS)\*\//);
  const ids=[...p.document.querySelectorAll('[id]')].map(x=>x.id);
  assert.equal(ids.length,new Set(ids).size);
  for(const control of p.document.querySelectorAll('input,select')) assert.ok(control.labels.length,control.id);
  assert.equal(p.document.querySelectorAll('script[src],link[rel="stylesheet"],img[src^="http"]').length,0);
});
test('all seven run detail views retain existing local evidence and delivery links',t=>{
  const p=page(t);
  const labels=[...p.document.querySelectorAll('#run-rows .issuer-title')].map(el=>el.getAttribute('aria-label'));
  let links=0;
  for(const label of labels) {
    [...p.document.querySelectorAll('#run-rows .issuer-title')].find(el=>el.getAttribute('aria-label')===label).click();
    for(const anchor of p.document.querySelectorAll('#run-detail a')) {
      const relative=decodeURIComponent(anchor.getAttribute('href'));
      const absolute=path.resolve(__dirname,relative);
      assert.ok(absolute.startsWith(path.resolve(__dirname,'../..') + path.sep));
      assert.ok(fs.existsSync(absolute),relative); links++;
    }
  }
  assert.ok(links >= 30);
});
