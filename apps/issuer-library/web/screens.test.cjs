/* Frame states, search scope, tab vocabulary and report rows. Synthetic fixture only; no network or provider. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM,VirtualConsole}=require(process.env.ISSUER_LIBRARY_JSDOM||'jsdom');
const root=path.resolve(__dirname,'../../../artifacts/issuer-library/design-fixture');
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const settle=(ms=10)=>new Promise(resolve=>setTimeout(resolve,ms));
function fixture(hash,timeout){
  const dom=new JSDOM(html,{url:`file://${__dirname}/index.html#${hash}`,runScripts:'outside-only'});
  const w=dom.window;w.scrollTo=()=>{};w.fetch=()=>new Promise(()=>{});
  w.HTMLElement.prototype.scrollIntoView=function(){};
  if(timeout!==undefined)w.DESIGN_FRAME_TIMEOUT_MS=timeout;
  for(const name of ['data.js','workspace-data.js'])vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),dom.getInternalVMContext());
  for(const name of ['views.js','actions.js','screen.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,name),'utf8'),dom.getInternalVMContext());
  return dom;
}
const go=async(w,hash)=>{w.location.hash=hash;w.dispatchEvent(new w.Event('hashchange'));await settle();};
const text=el=>el.textContent.replace(/\s+/g,' ').trim();

test('tab and rail vocabulary follows the approved destinations',t=>{
  const w=fixture('W-Overview/overview?c=tdg-002').window,d=w.document;t.after(()=>w.close());
  assert.deepEqual([...d.querySelectorAll('.workspace-tabs a')].map(a=>a.textContent),['Overview','Modules','Calendar','Reports','Evidence']);
  assert.ok(d.querySelector('.rail a[aria-label="Reports"]'));
  assert.equal(d.querySelector('.rail a[aria-label="Deliverables"]'),null);
  assert.ok(d.querySelector('.rail a[aria-label="Run activity"] img').getAttribute('src').endsWith('icons/activity.svg'));
  w.location.hash='W-Reports/list?c=tdg-002';w.dispatchEvent(new w.Event('hashchange'));
  assert.equal(d.title,'Reports · Issuer Library');
  assert.equal(d.getElementById('section-title').textContent,'Reports');
  assert.equal(d.querySelector('h1').textContent,w.eval('contexts["tdg-002"].title'));
});

test('search is cleared when leaving the analytical modules and can be cleared in place',async t=>{
  const w=fixture('CP-1/performance?c=tdg-002').window,d=w.document;t.after(()=>w.close());
  const search=d.getElementById('module-search'),clear=()=>d.getElementById('module-search-clear');
  search.value='liquidity';search.dispatchEvent(new w.Event('input',{bubbles:true}));
  assert.ok(d.getElementById('search-results').children.length>0);
  assert.equal(clear().hidden,false);
  await go(w,'W-Calendar/events?c=tdg-002');
  assert.equal(search.value,'');assert.equal(d.getElementById('search-results').children.length,0);
  assert.ok(d.getElementById('workbench').classList.contains('tools-workspace'));
  await go(w,'CP-2/assessment?c=tdg-002');
  assert.ok(!d.getElementById('workbench').classList.contains('tools-workspace'));
  search.value='liquidity';search.dispatchEvent(new w.Event('input',{bubbles:true}));
  clear().click();
  assert.equal(search.value,'');assert.equal(d.getElementById('search-results').children.length,0);
  assert.equal(d.activeElement,search);assert.equal(clear().hidden,true);
});

test('the navigator is resident on Overview and Modules only',async t=>{
  const w=fixture('W-Overview/overview?c=tdg-002').window,d=w.document;t.after(()=>w.close());
  const tools=()=>d.getElementById('workbench').classList.contains('tools-workspace');
  assert.equal(tools(),false);
  await go(w,'CP-1/performance?c=tdg-002');assert.equal(tools(),false);
  for(const hash of ['W-Reports/list','W-Evidence/sources','CP-OS/activity']){await go(w,`${hash}?c=tdg-002`);assert.equal(tools(),true,hash);}
});

test('the report frame shows loading, failure with retry, and loaded',async t=>{
  const dom=fixture('W-Calendar/events?c=tdg-002',20),w=dom.window,d=w.document;t.after(()=>w.close());
  const report=w.eval('window.DESIGN_WORKSPACE.reports[0]');
  await go(w,`W-Reports/${report.id}`);
  const status=()=>d.querySelector('.frame-status');
  assert.match(text(status()),/^Loading report/);
  await settle(60);
  assert.match(text(status()),/did not load/);
  assert.equal(status().querySelector('a').getAttribute('href'),report.download);
  const frame=d.getElementById('report-preview'),src=frame.getAttribute('src');
  status().querySelector('.frame-retry').click();
  assert.equal(text(status()),'Loading report…');assert.equal(frame.getAttribute('src'),src);
  frame.dispatchEvent(new w.Event('load'));
  assert.equal(status().hidden,true);
  await settle(60);assert.equal(status().hidden,true);
});

test('the run context frame shows loading, failure with retry, and ready',async t=>{
  const errors=[],virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',e=>errors.push(e));
  const dom=new JSDOM(html,{url:'http://127.0.0.1:54321/#W-NewRun/run',runScripts:'outside-only',virtualConsole}),w=dom.window,d=w.document;
  w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};w.setInterval=()=>1;w.clearInterval=()=>{};
  w.fetch=async()=>({ok:true,json:async()=>[]});
  w.eval('window.DESIGN_FRAME_TIMEOUT_MS=20;window.DESIGN_DATA={runs:{},outputs:{},inputs:{},pins:{}};window.DESIGN_WORKSPACE={reports:[],visuals:[]};window.DESIGN_APP={workspace:"/research",policy_locked:false,issues:[],problem:""};');
  for(const name of ['views.js','actions.js','screen.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,name),'utf8'),dom.getInternalVMContext());
  t.after(()=>{w.close();assert.deepEqual(errors.map(e=>e.message),[]);});
  const status=()=>d.querySelector('#context-step .frame-status');
  assert.match(text(status()),/^Loading run context form/);
  await settle(60);
  assert.match(text(status()),/did not load/);
  status().querySelector('.frame-retry').click();
  assert.match(text(status()),/^Loading run context form/);
  const editor=d.getElementById('context-editor');
  w.dispatchEvent(new w.MessageEvent('message',{source:editor.contentWindow,data:{type:'cpos:height',height:500}}));
  assert.equal(status().hidden,true);
});

test('report rows carry the id, sort by build and prefix other issuers',async t=>{
  const w=fixture('W-Reports/list?c=tdg-002').window,d=w.document;t.after(()=>w.close());
  const reports=w.eval('window.DESIGN_WORKSPACE.reports'),ids=new Set(reports.map(r=>r.id));
  const rows=[...d.querySelectorAll('.report-built .report-list li')];
  assert.ok(rows.length>0);
  const builds=rows.map(li=>Number(/Build (\d+)/.exec(li.textContent)?.[1]??0));
  builds.forEach((b,i)=>{if(i)assert.ok(b<=builds[i-1],`build order ${builds}`);});
  for(const li of d.querySelectorAll('.report-list li')){
    assert.ok(ids.has(li.querySelector('.code')?.textContent),li.textContent);
    assert.ok(!/  /.test(li.textContent),JSON.stringify(li.textContent));
  }
  assertRestRows(w,d,'tdg-002',false);
  // The engine's default label for an uncurated report already starts with its issuer; the fixture's curated labels do not.
  w.eval('window.DESIGN_WORKSPACE.reports[0].label=window.DESIGN_WORKSPACE.reports[0].issuer+" · as of 2025-05-31"');
  await go(w,'W-Reports/list?c=ford-otosan-2024');
  assert.ok(d.querySelector('.report-rest .report-list li .code')&&[...d.querySelectorAll('.report-rest .report-list li a')].some(a=>text(a).includes('TransDigm Group · as of 2025-05-31')),'issuer-led label case missing');
  assertRestRows(w,d,'ford-otosan-2024',true);
});

function assertRestRows(w,d,context,required){
  const reports=w.eval('window.DESIGN_WORKSPACE.reports'),run=w.eval(`contexts["${context}"].issuer`);
  const rest=[...d.querySelectorAll('.report-rest .report-list li')];
  if(required)assert.ok(rest.length>0,`no rows under .report-rest for ${context}`);
  for(const li of rest){
    const report=reports.find(r=>r.id===li.querySelector('.code').textContent),label=text(li.querySelector('a')),shown=text(li).replace(text(li.querySelector('.code')),'');
    const led=report.label.trim().startsWith(report.issuer);
    if(report.issuer!==run&&!led)assert.ok(text(li).startsWith(report.issuer),li.textContent);
    if(led)assert.ok(text(li).includes(report.label.trim()),li.textContent);
    assert.equal(shown.split(report.issuer).length-1,1,`issuer repeated: ${text(li)}`);
    if(led)assert.ok(!li.querySelector('.report-issuer'),`prefix added to a label that has the issuer: ${text(li)}`);
    else assert.ok(li.querySelector('.report-issuer'),`label without issuer left unprefixed: ${label}`);
  }
}

test('the report selector lists builds in the list-page order',async t=>{
  const w=fixture('W-Reports/list?c=tdg-002').window,d=w.document;t.after(()=>w.close());
  const report=w.eval('window.DESIGN_WORKSPACE.reports.filter(r=>r.issuer===contexts["tdg-002"].issuer)[0]');
  await go(w,`W-Reports/${report.id}?c=tdg-002`);
  const options=[...d.querySelectorAll('#report-select option')].map(o=>o.textContent);
  assert.ok(options.length>1);
  const builds=options.map(o=>Number(/^Build (\d+)/.exec(o)?.[1]??0));
  builds.forEach((b,i)=>{if(i)assert.ok(b<=builds[i-1],`select order ${builds}`);});
});

test('Help names Reports, not Deliverables',async t=>{
  const w=fixture('W-Help/help?c=tdg-002').window,d=w.document;t.after(()=>w.close());
  const help=text(d.getElementById('content'));
  assert.match(help,/Reports lists/);assert.doesNotMatch(help,/Deliverables lists/);
});
test('Settings lists workspace issues as path and message and quits as a tertiary action',async t=>{
  const dom=new JSDOM(html,{url:'http://127.0.0.1:54321/#W-Settings/workspace',runScripts:'outside-only'});
  const w=dom.window;t.after(()=>w.close());w.scrollTo=()=>{};w.fetch=()=>new Promise(()=>{});w.HTMLElement.prototype.scrollIntoView=function(){};
  w.eval("window.DESIGN_DATA={runs:{},outputs:{},inputs:{},pins:{}};window.DESIGN_WORKSPACE={reports:[],visuals:[]};window.DESIGN_APP={workspace:'/research',policy_locked:false,issues:['deliverables/x: Delivery manifest requires report.html: and view.json','plain note'],problem:''};");
  for(const name of ['views.js','actions.js','screen.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,name),'utf8'),dom.getInternalVMContext());
  await settle();
  const d=w.document,quit=d.getElementById('quit-library');
  assert.ok(quit.classList.contains('tertiary-action'));
  assert.equal(quit.parentElement.lastElementChild,quit);assert.ok(quit.parentElement.classList.contains('step-actions'));
  const items=[...d.querySelectorAll('.issue-list li')];
  assert.equal(items.length,2);
  assert.equal(items[0].querySelector('.code').textContent,'deliverables/x');
  assert.equal(items[0].children[1].textContent,'Delivery manifest requires report.html: and view.json');
  assert.equal(items[1].querySelector('.code'),null);
});
