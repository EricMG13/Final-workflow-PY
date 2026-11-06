/* Execute retained report renderers in a simulated DOM, without browser/network. */
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {JSDOM,VirtualConsole}=require(process.env.ISSUER_LIBRARY_JSDOM || 'jsdom');
const deliveries=path.resolve(__dirname,'../../../deliverables');
// Resolves after the report's own hashchange handler has rendered the destination.
const open=(dom,dest)=>new Promise(resolve=>{dom.window.addEventListener('hashchange',resolve,{once:true});dom.window.document.querySelector(`#rail-dests [data-dest="${dest}"]`).click();});
for (const folder of fs.readdirSync(deliveries).sort()) {
 const file=path.join(deliveries,folder,'report.html');if(!fs.existsSync(file))continue;
 test(`retained ${folder}: native sections and evidence inspector remain functional`,async t=>{
  const errors=[];const virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',error=>errors.push(error));
  const dom=new JSDOM(fs.readFileSync(file,'utf8'),{url:'http://127.0.0.1:54321/files/deliverables/'+folder+'/report.html?embedded=1',runScripts:'dangerously',virtualConsole,beforeParse(win){win.matchMedia=()=>({matches:false});win.HTMLElement.prototype.scrollIntoView=function(){};}});
  t.after(()=>{assert.deepEqual(errors,[]);dom.window.close();});
  const doc=dom.window.document;assert.ok(doc.getElementById('nav-issuer').textContent.includes(JSON.parse(fs.readFileSync(path.join(deliveries,folder,'view.json'),'utf8')).run.issuer_name));assert.equal(doc.querySelectorAll('#rail-dests a').length,6);
  await open(dom,'model');
  const figure=doc.querySelector('.fact-value');
  // Only these reports carry a financial model; the others have no figures to inspect.
  assert.equal(Boolean(figure),/^(tdg-fy2024-snapshot|erste-source-intake)/.test(folder));
  if(figure){figure.click();assert.match(doc.getElementById('inspector-content').textContent,/SHA-256/);}
  await open(dom,'evidence');assert.match(doc.getElementById('view-root').textContent,/Source|Evidence/);
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
 await open(dom,'model');assert.equal(doc.body.classList.contains('evidence-open'),false);
 assert.equal(doc.querySelector('.page-head>.eyebrow'),null);assert.doesNotMatch(doc.getElementById('view-root').textContent,/DEPLOY VII|State Street Investment Management/);
 const figure=doc.querySelector('.fact-value');figure.click();await new Promise(resolve=>setImmediate(resolve));assert.equal(doc.body.classList.contains('evidence-open'),true);
 doc.querySelector('button[aria-label="Close inspector"]').click();await new Promise(resolve=>setImmediate(resolve));assert.equal(doc.body.classList.contains('evidence-open'),false);
});

test('the report preview shows module names, keeps figures and leaves the inspector and original exact',async t=>{
 const errors=[],virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',error=>errors.push(error));
 const file=path.join(deliveries,'tdg-fy2024-snapshot-7/report.html'),raw=fs.readFileSync(file,'utf8');
 const before=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
 const dom=new JSDOM(raw,{url:'http://127.0.0.1:54321/report',runScripts:'dangerously',virtualConsole,beforeParse(win){win.matchMedia=()=>({matches:false});win.HTMLElement.prototype.scrollIntoView=function(){};}});
 t.after(()=>{assert.deepEqual(errors,[]);dom.window.close();});
 const win=dom.window,doc=win.document;
 assert.match(doc.getElementById('view-root').textContent,/\bCP-\d/,'the retained report does name modules');
 win.eval(fs.readFileSync(path.join(__dirname,'report-adapter.js'),'utf8'));
 const root=doc.getElementById('view-root');
 assert.doesNotMatch(root.textContent,/\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])/);
 assert.doesNotMatch(doc.querySelector('.navigator').textContent,/\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])/);
 assert.ok(root.textContent.includes('Business & governance'));
 assert.ok(root.textContent.includes('3.14x'));assert.ok(root.textContent.includes('Analyst Interpretation'));
 await open(dom,'model');
 assert.doesNotMatch(root.textContent,/\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])/,'a later destination is named too');
 const figure=doc.querySelector('.fact-value');figure.click();await new Promise(resolve=>setImmediate(resolve));
 assert.match(doc.getElementById('inspector-content').textContent,/CP-1 \/ evidence-trace/,'the inspector keeps codes');
 assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),before);
});

test('the preview names every module the app names, including absorbed codes',()=>{
 const adapter=fs.readFileSync(path.join(__dirname,'report-adapter.js'),'utf8'),screen=fs.readFileSync(path.join(__dirname,'screen.js'),'utf8');
 const names=JSON.parse(adapter.match(/const MODULE_NAMES=(\{[^}]*\});/)[1]);
 const groupsText=screen.slice(screen.indexOf('const groups = ')+15,screen.indexOf('// A module the reading groups')).trim().replace(/;$/,'');
 const app=Object.fromEntries(new Function(`return ${groupsText}`)().flatMap(group=>group[1]));
 for(const [code,name] of Object.entries(app))assert.equal(names[code],name,code);
 const rows=fs.readFileSync(path.resolve(__dirname,'../../../docs/visualisations/catalogue.csv'),'utf8').split('\n').slice(1).filter(Boolean);
 for(const row of rows){
  const [,module,quoted,bare]=row.match(/^[^,]*,([^,]*),(?:"([^"]*)"|([^,]*))/);
  for(const alias of (quoted??bare).split(/[;,\s]+/).filter(Boolean))assert.equal(names[alias],app[alias]??app[module],alias);
 }
});

