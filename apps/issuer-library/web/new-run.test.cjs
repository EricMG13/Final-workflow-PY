/* New run inside the one app: synthetic responses only; no network or provider. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM,VirtualConsole}=require(process.env.ISSUER_LIBRARY_JSDOM||'jsdom');
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const context=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../../cases/context/research-minimal.json'),'utf8'));
const settle=()=>new Promise(resolve=>setTimeout(resolve,10));
const ID='web-'+'a'.repeat(32);
const ROW_RUNNING={id:ID,state:'running',message:'Working',run_available:true,issuer:'Northbridge Group',pathway:'covenant_refinancing',as_of:'2025-03-31',modules:['CP-0','CP-1'],module_details:[{id:'CP-0',title:'Source readiness'},{id:'CP-1',title:'Financial analysis'}],progress:{module:'CP-1',step:'started',spent_usd:'0.10'}};
const ROW_DONE={id:'web-'+'b'.repeat(32),state:'complete',message:'Done',run_available:true,issuer:'Southport Holdings',pathway:'credit_snapshot',as_of:'2025-06-30',spent_usd:'3.10'};
const IDENTITY=`Northbridge Group · Covenant Refinancing · as of 2025-03-31 · ${ID}`;
function reviewReply(ready){return{ok:true,id:ID,review_id:'b'.repeat(64),issuer:'Northbridge Group',pathway:'covenant_refinancing',as_of:'2025-03-31',modules:['CP-0','CP-1'],module_details:[{id:'CP-0',title:'Source readiness',purpose:'Check issuer files'},{id:'CP-1',title:'Financial analysis',purpose:'Read financial statements'}],config:'sol-medium',provider:'openai',model:'gpt-6.1-sol',effort:'medium',cap_usd:'10.00',hold_usd:'1.86',max_turns:7,prices_as_of:'2026-11-01',provider_ready:ready,provider_key:'OPENAI_API_KEY',sources:[{path:'filings/annual.txt',sha256:'c'.repeat(64)}],ignored:['chart.png'],report_sections:['liquidity-runway'],omitted:['lme-chart'],scope:'User-launched run; analytical accuracy has not been independently reviewed.'};}
async function page(t,{ready=true,startFails=false,list=[],status={state:'running',message:'Working',progress:{module:'CP-0',step:'accepted',spent_usd:'0.42'},run_available:true}}={}){
  const errors=[],calls=[];let starts=0;const virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',error=>errors.push(error));
  const dom=new JSDOM(html,{url:'http://127.0.0.1:54321/#W-NewRun/run',runScripts:'outside-only',virtualConsole});
  const win=dom.window;win.scrollTo=()=>{};win.HTMLElement.prototype.scrollIntoView=function(){};const timers=new Map(),started=[],cleared=[];let nextTimer=1;win.setInterval=fn=>{timers.set(nextTimer,fn);started.push(nextTimer);return nextTimer++;};win.clearInterval=id=>{cleared.push(id);timers.delete(id);};
  const replies={'/api/runs/list':()=>list,'/api/runs/review':()=>reviewReply(ready),'/api/runs/start':()=>{starts++;if(startFails)throw new Error('lost');return{state:'running',id:ID};}};
  win.fetch=async(url,options)=>{calls.push({url,options});const body=url.startsWith('/api/runs/status')?()=>status():replies[url];return{ok:true,json:async()=>body()};};
  const current=status;status=()=>win.__status||current;
  win.eval('window.DESIGN_DATA={runs:{},outputs:{},inputs:{},pins:{}};window.DESIGN_WORKSPACE={reports:[],visuals:[]};window.DESIGN_APP={workspace:"/research",policy_locked:false,issues:[],problem:""};');
  for(const name of ['views.js','actions.js','screen.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,name),'utf8'),dom.getInternalVMContext());
  await settle();
  t.after(()=>{win.close();assert.deepEqual(errors.map(error=>error.message),[]);});
  const doc=win.document,editor=doc.getElementById('context-editor');
  return{win,doc,calls,started,cleared,tick:async()=>{for(const fn of [...timers.values()])fn();await settle();},starts:()=>starts,click:async id=>{doc.getElementById(id).click();await settle();},
    context:()=>win.dispatchEvent(new win.MessageEvent('message',{source:editor.contentWindow,data:{type:'cpos:context',context,problems:[]}})),
    folder:(...names)=>{const input=doc.getElementById('run-sources');const files=names.map(name=>{const file=new win.File(['x'],name.split('/').at(-1));Object.defineProperty(file,'webkitRelativePath',{value:name});return file;});Object.defineProperty(input,'files',{configurable:true,value:files});input.dispatchEvent(new win.Event('change'));},
    confirm:()=>{const box=doc.getElementById('run-confirm');box.checked=true;box.dispatchEvent(new win.Event('change'));}};
}
test('the steps follow the launcher, and untrusted messages are ignored',async t=>{
  const p=await page(t);
  assert.deepEqual([...p.doc.querySelectorAll('.run-stages li')].map(li=>li.textContent),['Context','Issuer folder & budget','Review & start','Progress']);
  assert.equal(p.doc.getElementById('run-sources').hasAttribute('webkitdirectory'),true);
  assert.match(p.doc.getElementById('recent-jobs').textContent,/No recent runs to show/);
  p.win.dispatchEvent(new p.win.MessageEvent('message',{source:p.win,data:{type:'cpos:context',context,problems:[]}}));
  assert.equal(p.doc.getElementById('source-step').hidden,true);
  p.context();assert.equal(p.doc.getElementById('source-step').hidden,false);assert.equal(p.doc.activeElement,p.doc.querySelector('#source-step h2'));
});
test('review sends the folder as relative paths with the launcher options, and starts nothing',async t=>{
  const p=await page(t);p.context();
  p.folder('Northbridge/annual.txt','Northbridge/filings/notes.md','Northbridge/.DS_Store','Northbridge/.git/config');
  assert.match(p.doc.getElementById('upload-list').textContent,/2 files/);
  p.doc.getElementById('run-model').value='opus-medium';p.doc.getElementById('run-budget').value='25';
  p.doc.getElementById('run-modules').value='CP-4';p.doc.getElementById('run-turns').value='7';
  await p.click('review-run');
  const body=p.calls.find(call=>call.url==='/api/runs/review').options.body;
  // Written by hand: the chosen folder's own name is dropped, dot paths are not uploaded.
  assert.deepEqual(JSON.parse(body.get('source_paths')),['annual.txt','filings/notes.md']);
  assert.equal(body.getAll('sources').length,2);
  assert.deepEqual([body.get('config'),body.get('cap_usd'),body.get('modules'),body.get('max_turns')],['opus-medium','25','CP-4','7']);
  assert.deepEqual(JSON.parse(body.get('context')),context);
  assert.equal(p.starts(),0);assert.equal(p.doc.getElementById('review-step').hidden,false);assert.equal(p.doc.activeElement,p.doc.querySelector('#review-step h2'));
});
test('the review shows everything the launcher decided',async t=>{
  const p=await page(t);p.context();p.folder('N/annual.txt');await p.click('review-run');
  const text=p.doc.getElementById('run-review').textContent;
  for(const expected of ['Northbridge Group','Covenant Refinancing','2025-03-31','openai gpt-6.1-sol · medium','USD 10.00','USD 1.86','Source readiness','chart.png','liquidity-runway','lme-chart','not been independently reviewed','not an estimate of total cost','filings/annual.txt'])assert.ok(text.includes(expected),expected);
  assert.equal(p.doc.querySelector('.review-modules').children.length,2);
});
test('only an explicitly confirmed Start launches, once',async t=>{
  const p=await page(t);p.context();p.folder('N/annual.txt');await p.click('review-run');
  assert.equal(p.doc.getElementById('start-run').disabled,true);
  await p.click('start-run');assert.equal(p.starts(),0);
  p.confirm();await p.click('start-run');await p.click('start-run');
  assert.equal(p.starts(),1);assert.equal(p.doc.getElementById('progress-step').hidden,false);
  assert.equal(p.doc.getElementById('run-identity').textContent,IDENTITY);
  assert.deepEqual(JSON.parse(p.calls.find(call=>call.url==='/api/runs/start').options.body),{id:ID,review_id:'b'.repeat(64),confirm:true});
  assert.match(p.doc.getElementById('run-progress').textContent,/running: Working · Source readiness accepted \(1 of 2\)/);
  const bar=p.doc.getElementById('module-stages'),items=[...bar.querySelectorAll('li')];
  assert.equal(bar.hidden,false);assert.deepEqual(items.map(li=>li.querySelector('strong').textContent),['Source readiness','Financial analysis']);
  assert.equal(items[0].getAttribute('aria-current'),'step');assert.equal(items[1].hasAttribute('aria-current'),false);
  assert.equal(items[0].dataset.status,'complete');assert.equal(items[0].querySelector('span:not(.step-marker)').textContent,'Accepted');
  assert.equal(items[1].dataset.status,'incomplete');assert.equal(items[1].querySelector('span:not(.step-marker)'),null);
  const reviewed=p.doc.querySelector('#run-review ol li');
  assert.equal(reviewed.textContent,'Source readiness','the review names modules without codes');
  assert.equal(reviewed.title,'CP-0: Check issuer files');
  assert.match(p.doc.getElementById('run-spend').textContent,/USD 0.42/);
  assert.equal(p.doc.getElementById('open-run').hidden,true);
});
test('a module that has started is shown as running',async t=>{
  const p=await page(t,{status:{state:'running',message:'Working',progress:{module:'CP-1',step:'started',spent_usd:'0.42'},run_available:true}});
  p.context();p.folder('N/annual.txt');await p.click('review-run');p.confirm();await p.click('start-run');
  assert.match(p.doc.getElementById('run-progress').textContent,/running: Working · running Financial analysis \(2 of 2\)/);
  const items=[...p.doc.querySelectorAll('#module-stages li')];
  assert.equal(items[1].hasAttribute('aria-current'),true);assert.equal(items[0].hasAttribute('aria-current'),false);
  const note=li=>li.querySelector('span:not(.step-marker)')?.textContent;
  assert.equal(items[0].dataset.status,'complete');assert.equal(note(items[0]),'Accepted');assert.ok(items[0].querySelector('.step-marker img'),'a tick, not a number');
  assert.equal(items[1].dataset.status,'current');assert.equal(note(items[1]),'Running');assert.equal(items[1].hasAttribute('data-stopped'),false);
  assert.equal(items[0].title,'CP-0');assert.equal(items[1].querySelector('.step-marker').textContent,'2');
});
test('a stopped run does not claim its rejected module is still running',async t=>{
  const p=await page(t,{status:{state:'stopped',message:'CP-1 rejected.',progress:{module:'CP-1',step:'started',spent_usd:'0.42'},run_available:true,id:ID}});
  p.context();p.folder('N/annual.txt');await p.click('review-run');p.confirm();await p.click('start-run');
  assert.equal(p.doc.getElementById('run-progress').textContent.trim(),'stopped: CP-1 rejected. · stopped during Financial analysis (2 of 2)');
  const items=[...p.doc.querySelectorAll('#module-stages li')];
  assert.equal(items[1].getAttribute('aria-current'),'step');
  assert.equal(items[1].dataset.status,'current');assert.equal(items[1].hasAttribute('data-stopped'),true);
  assert.equal(items[1].querySelector('span:not(.step-marker)').textContent,'Stopped here');
  const open=p.doc.getElementById('open-run');assert.equal(open.hidden,false);assert.equal(open.textContent,'Open run');
});
test('recent runs are a table, active first, and a row reopens its run',async t=>{
  const p=await page(t,{list:[ROW_DONE,ROW_RUNNING],status:{state:'running',message:'Working',progress:{module:'CP-1',step:'started',spent_usd:'0.10'},run_available:true}});
  await p.win.eval("window.dispatchEvent(new Event('hashchange'))");
  const table=p.doc.querySelector('#recent-jobs .table-scroll table');
  assert.ok(table,'table');
  assert.deepEqual([...table.querySelectorAll('thead th')].map(th=>th.textContent),['Issuer','Workflow','Module','State','Spend (USD)']);
  const rows=[...table.querySelectorAll('tbody tr')];
  assert.equal(rows.length,2);
  const button=rows[0].querySelector('th[scope="row"] button.text-button');
  assert.equal(button.textContent,'Northbridge Group');assert.equal(button.title,ID);
  const first=[...rows[0].querySelectorAll('td')];
  assert.equal(first[0].textContent,'Covenant Refinancing');assert.ok(first[0].querySelector('.badge.badge-blue'));
  assert.equal(first[1].textContent,'running Financial analysis (2 of 2)');
  assert.equal(first[2].textContent,'running');assert.ok(first[2].querySelector('.badge').classList.contains('badge-blue'));
  assert.equal(first[3].textContent,'0.10');
  const second=[...rows[1].querySelectorAll('td')];
  assert.equal(rows[1].querySelector('th').textContent,'Southport Holdings');
  assert.equal(second[1].textContent,'—');assert.equal(second[2].textContent,'complete');
  assert.ok(second[2].querySelector('.badge').classList.contains('badge-navy'));assert.equal(second[3].textContent,'3.10');
  assert.equal(p.doc.querySelector('.recent-runs').open,true);
  button.click();await settle();
  assert.equal(p.doc.getElementById('progress-step').hidden,false);
  assert.equal(p.doc.getElementById('run-identity').textContent,IDENTITY);
  const bar=p.doc.getElementById('module-stages');
  assert.equal(bar.hidden,false);assert.equal(bar.querySelectorAll('li').length,2);
  assert.equal(bar.querySelectorAll('li')[1].getAttribute('aria-current'),'step');
  assert.equal(p.doc.getElementById('run-progress').textContent,'running: Working · running Financial analysis (2 of 2)');
});
test('a list refresh keeps the focused row',async t=>{
  const list=[{...ROW_RUNNING}];
  const p=await page(t,{list});
  const relist=p.tick;
  await p.win.eval("window.dispatchEvent(new Event('hashchange'))");await settle();
  const table=p.doc.querySelector('#recent-jobs table');
  p.doc.querySelector('#recent-jobs tbody th button').focus();
  assert.equal(p.doc.activeElement.title,ID);
  await relist();
  assert.equal(p.doc.querySelector('#recent-jobs table'),table,'identical list keeps the same table node');
  assert.equal(p.doc.activeElement.title,ID);
  list[0]={...ROW_RUNNING,state:'complete'};
  await relist();
  const changed=p.doc.querySelector('#recent-jobs table');
  assert.notEqual(changed,table,'a changed list rebuilds the table');
  assert.equal(p.doc.activeElement,changed.querySelector('tbody th button'));
  assert.equal(p.doc.activeElement.title,ID);
});
test('a run without a saved review still lists and opens by id',async t=>{
  const p=await page(t,{list:[{id:ID,state:'stopped',message:'Halted',run_available:true,progress:{module:'CP-1',step:'started',spent_usd:'0.10'}}]});
  await p.win.eval("window.dispatchEvent(new Event('hashchange'))");
  const row=p.doc.querySelector('#recent-jobs tbody tr'),tds=[...row.querySelectorAll('td')];
  assert.equal(row.querySelector('th').textContent,ID);
  assert.equal(tds[0].textContent,'—');assert.equal(tds[1].textContent,'stopped during CP-1');
  assert.equal(p.doc.querySelector('.recent-runs').open,false);
  row.querySelector('button').click();await settle();
  assert.equal(p.doc.getElementById('run-identity').textContent,ID);
  assert.equal(p.doc.getElementById('module-stages').hidden,true);
  assert.equal(p.doc.getElementById('run-progress').textContent,'stopped: Halted · stopped during CP-1');
});
test('a missing provider key keeps Start unavailable and names the variable',async t=>{
  const p=await page(t,{ready:false});p.context();p.folder('N/annual.txt');await p.click('review-run');
  p.confirm();assert.equal(p.doc.getElementById('start-run').disabled,true);
  assert.match(p.doc.getElementById('run-review').textContent,/OPENAI_API_KEY is not set/);
  await p.click('revise-run');assert.equal(p.doc.getElementById('source-step').hidden,false);assert.equal(p.doc.getElementById('run-confirm').checked,false);
});
test('a lost Start response reconnects by id instead of launching again',async t=>{
  const p=await page(t,{startFails:true});p.context();p.folder('N/annual.txt');await p.click('review-run');p.confirm();await p.click('start-run');
  assert.equal(p.starts(),1);assert.equal(p.doc.getElementById('progress-step').hidden,false);
  assert.ok(p.calls.some(call=>call.url===`/api/runs/status?id=${ID}`));
});
test('a finished run offers its deliverables; a stopped one offers the run',async t=>{
  for(const [state,label,route] of [['complete','Open deliverables',`W-Reports/list?c=${ID}`],['stopped','Open run',`W-Overview/overview?c=${ID}`]]){
    const p=await page(t,{status:{state,message:'Done',spent_usd:'3.10',run_available:true,id:ID}});p.context();p.folder('N/annual.txt');await p.click('review-run');p.confirm();await p.click('start-run');
    const open=p.doc.getElementById('open-run');
    assert.equal(open.hidden,false,state);assert.equal(open.textContent,label);assert.equal(open.dataset.route,route);
    assert.match(p.doc.getElementById('run-spend').textContent,/USD 3.10/);assert.equal(p.doc.getElementById('another-run').hidden,false);
    const items=[...p.doc.querySelectorAll('#module-stages li')];
    assert.equal(p.doc.getElementById('run-progress').textContent.trim(),`${state}: Done`);
    if(state==='complete')assert.equal(items.at(-1).hasAttribute('aria-current'),true);
    else assert.equal(items.some(li=>li.hasAttribute('aria-current')),false);
    for(const li of items){
      assert.equal(li.dataset.status,state==='complete'?'complete':'incomplete',state);
      if(state==='stopped')assert.equal(li.querySelector('span:not(.step-marker)'),null);
    }
  }
  const failed=await page(t,{status:{state:'failed',message:'Refused',run_available:false,id:ID}});failed.context();failed.folder('N/annual.txt');await failed.click('review-run');failed.confirm();await failed.click('start-run');
  assert.equal(failed.doc.getElementById('open-run').hidden,true);
});
test('context height messages are source checked and bounded',async t=>{
  const p=await page(t),frame=p.doc.getElementById('context-editor');
  const send=(source,height)=>p.win.dispatchEvent(new p.win.MessageEvent('message',{source,data:{type:'cpos:height',height}}));
  send(p.win,1800);assert.equal(frame.style.height,'');send(frame.contentWindow,1800);assert.equal(frame.style.height,'1800px');send(frame.contentWindow,Infinity);send(frame.contentWindow,50001);assert.equal(frame.style.height,'1800px');
});
test('an issuer folder is required before review',async t=>{
  const p=await page(t);p.context();await p.click('review-run');
  assert.match(p.doc.getElementById('new-run-message').textContent,/Choose the issuer folder/);
  assert.equal(p.calls.filter(call=>call.url==='/api/runs/review').length,0);
});
test('a malformed row degrades to a dash and does not hide the others',async t=>{
  const p=await page(t,{list:[{...ROW_RUNNING,module_details:'bad',modules:'CP-0 CP-1'},ROW_DONE]});
  await p.win.eval("window.dispatchEvent(new Event('hashchange'))");
  assert.ok(p.doc.querySelector('#recent-jobs table'));
  const rows=[...p.doc.querySelectorAll('#recent-jobs tbody tr')];
  assert.equal(rows.length,2);
  assert.equal(rows[0].querySelectorAll('td')[1].textContent,'running CP-1','raw id, no ordinal, from the malformed row');
  assert.equal(rows[1].querySelectorAll('td')[3].textContent,'3.10');
  assert.doesNotMatch(p.doc.getElementById('recent-jobs').textContent,/Could not load/);
  p.win.__status={...ROW_RUNNING};
  rows[0].querySelector('button').click();await settle();
  assert.equal(p.doc.getElementById('module-stages').hidden,true);
  assert.equal(p.doc.getElementById('run-progress').textContent,'running: Working · running CP-1');
});
test('a failed render is retried on the next refresh',async t=>{
  const list=[ROW_RUNNING];
  const p=await page(t,{list});
  list[0]={...ROW_RUNNING,message:'Still working'};
  const real=p.doc.createElement.bind(p.doc);let thrown=false;
  p.doc.createElement=tag=>{if(tag==='table'&&!thrown){thrown=true;throw new Error('render fault');}return real(tag);};
  await p.tick();
  assert.ok(thrown);
  assert.match(p.doc.getElementById('recent-jobs').textContent,/^Could not load/);
  await p.tick();
  assert.ok(p.doc.querySelector('#recent-jobs table'));
});
test('polling stops while New run is hidden and resumes on return',async t=>{
  const p=await page(t,{list:[ROW_RUNNING]});
  await p.win.eval("window.dispatchEvent(new Event('hashchange'))");
  assert.equal(p.started.length,1);
  p.doc.getElementById('new-run').hidden=true;
  await p.tick();
  assert.deepEqual(p.cleared,[p.started[0]]);assert.equal(p.started.length,1);
  p.win.location.hash='#W-Reports/list';await settle();
  p.win.location.hash='#W-NewRun/run';await settle();
  assert.equal(p.doc.getElementById('new-run').hidden,false);
  assert.equal(p.started.length,2);
});
test('a failed list fetch is retried and its error does not stick',async t=>{
  const p=await page(t,{list:[ROW_RUNNING]});
  const real=p.win.fetch;let fail=true;
  p.win.fetch=async(url,options)=>{if(url==='/api/runs/list'&&fail){fail=false;throw new Error('offline');}return real(url,options);};
  await p.tick();
  assert.match(p.doc.getElementById('recent-jobs').textContent,/^Could not load/);
  await p.tick();
  assert.ok(p.doc.querySelector('#recent-jobs table'));
});
test('a null module detail does not break the row',async t=>{
  const p=await page(t,{list:[{...ROW_RUNNING,module_details:[null,{id:'CP-1',title:'Financial analysis'}]}]});
  const cells=p.doc.querySelectorAll('#recent-jobs tbody tr td');
  assert.equal(cells[1].textContent,'running Financial analysis (2 of 2)');
});
