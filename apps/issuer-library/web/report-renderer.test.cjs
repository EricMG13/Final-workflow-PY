/* Execute retained report renderers in a simulated DOM, without browser/network. */
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require(process.env.ISSUER_LIBRARY_JSDOM || 'jsdom');
const deliveries=path.resolve(__dirname,'../../../deliverables');
for (const folder of fs.readdirSync(deliveries).sort()) {
 const file=path.join(deliveries,folder,'report.html');if(!fs.existsSync(file))continue;
 test(`retained ${folder}: native sections and evidence inspector remain functional`,async t=>{
  const errors=[];const virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',error=>errors.push(error));
  const dom=new JSDOM(fs.readFileSync(file,'utf8'),{url:'http://127.0.0.1:54321/files/deliverables/'+folder+'/report.html?embedded=1',runScripts:'dangerously',virtualConsole,beforeParse(win){win.matchMedia=()=>({matches:false});win.HTMLElement.prototype.scrollIntoView=function(){};}});
  t.after(()=>{assert.deepEqual(errors,[]);dom.window.close();});
  const doc=dom.window.document;assert.ok(doc.getElementById('nav-issuer').textContent.includes(JSON.parse(fs.readFileSync(path.join(deliveries,folder,'view.json'),'utf8')).run.issuer_name));assert.equal(doc.querySelectorAll('#rail-dests a').length,6);
  doc.querySelector('#rail-dests [data-dest="model"]').click();await new Promise(resolve=>setTimeout(resolve,10));
  const figure=doc.querySelector('.fact-value');
  // Only these reports carry a financial model; the others have no figures to inspect.
  assert.equal(Boolean(figure),/^(tdg-fy2024-snapshot|erste-source-intake)/.test(folder));
  if(figure){figure.click();assert.match(doc.getElementById('inspector-content').textContent,/SHA-256/);}
  doc.querySelector('#rail-dests [data-dest="evidence"]').click();await new Promise(resolve=>setTimeout(resolve,10));assert.match(doc.getElementById('view-root').textContent,/Source|Evidence/);
 });
}

test('embedded presentation opens evidence on demand and restores the trigger',async t=>{
 const errors=[],virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',error=>errors.push(error));
 const raw=fs.readFileSync(path.join(deliveries,'tdg-fy2024-snapshot-2/report.html'),'utf8');
 const dom=new JSDOM(raw,{url:'http://127.0.0.1:54321/report',runScripts:'dangerously',virtualConsole,beforeParse(win){win.matchMedia=()=>({matches:false});win.HTMLElement.prototype.scrollIntoView=function(){};}});
 t.after(()=>{assert.deepEqual(errors,[]);dom.window.close();});
 const win=dom.window,doc=win.document;win.eval(fs.readFileSync(path.join(__dirname,'report-adapter.js'),'utf8'));
 assert.equal(doc.title,'Issuer report');assert.equal(doc.querySelector('.brand-mark').textContent,'');assert.equal(doc.querySelector('.logo-block'),null);
 assert.equal(doc.body.classList.contains('evidence-open'),false);assert.ok(doc.querySelector('.fig.narrative'));
 const cite=[...doc.querySelectorAll('button')].find(button=>button.getAttribute('aria-label')==='Key findings: C65 (cited C65)');
 cite.click();await new Promise(resolve=>setImmediate(resolve));assert.equal(doc.body.classList.contains('evidence-open'),true);assert.equal(doc.activeElement.id,'inspector-content');
 doc.querySelector('.inspector-dismiss').click();assert.equal(doc.body.classList.contains('evidence-open'),false);assert.equal(doc.activeElement,cite);
 cite.click();await new Promise(resolve=>setImmediate(resolve));doc.dispatchEvent(new win.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));assert.equal(doc.body.classList.contains('evidence-open'),false);assert.equal(doc.activeElement,cite);
 doc.querySelector('#rail-dests [data-dest="model"]').click();await new Promise(resolve=>setTimeout(resolve,10));assert.equal(doc.body.classList.contains('evidence-open'),false);
 assert.equal(doc.querySelector('.page-head>.eyebrow'),null);assert.doesNotMatch(doc.getElementById('view-root').textContent,/DEPLOY VII|State Street Investment Management/);
 const figure=doc.querySelector('.fact-value');figure.click();await new Promise(resolve=>setImmediate(resolve));assert.equal(doc.body.classList.contains('evidence-open'),true);
 doc.querySelector('button[aria-label="Close inspector"]').click();await new Promise(resolve=>setImmediate(resolve));assert.equal(doc.body.classList.contains('evidence-open'),false);
});
