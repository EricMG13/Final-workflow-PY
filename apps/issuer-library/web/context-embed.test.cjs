/* Existing context form + embedded presentation, no browser/network/providers. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {JSDOM,VirtualConsole}=require(process.env.ISSUER_LIBRARY_JSDOM||'jsdom');
const html=fs.readFileSync(path.join(__dirname,'context-form.html'),'utf8');
function form(t){
 const errors=[],messages=[],console=new VirtualConsole();console.on('jsdomError',error=>errors.push(error));
 const dom=new JSDOM(html,{runScripts:'dangerously',virtualConsole:console,beforeParse(win){win.scrollTo=()=>{};win.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});win.ResizeObserver=class{observe(){}};win.HTMLElement.prototype.scrollIntoView=function(){};win.postMessage=value=>messages.push(value);}});
 const win=dom.window,doc=win.document;
 t.after(()=>{assert.deepEqual(errors,[]);win.close();});
 return{win,doc,messages,set(id,value){const field=doc.getElementById(id);field.value=value;field.dispatchEvent(new win.Event('input',{bubbles:true}));},submit(){win.dispatchEvent(new win.MessageEvent('message',{source:win,data:{type:'cpos:get-context'}}));return messages.filter(item=>item.type==='cpos:context').at(-1);}};
}
test('one required context path retains all original optional fields',t=>{
 const p=form(t);for(const id of ['sec1','sec2','sec3'])assert.equal(p.doc.getElementById(id).hidden,false);
 assert.equal(p.win.getComputedStyle(p.doc.querySelector('.stepnav')).display,'none');
 assert.equal(p.doc.querySelector('#sec2 details').open,false);assert.ok(p.doc.getElementById('s2-guarantors'));
 assert.equal(p.submit().problems.length,2);assert.equal(p.doc.activeElement.id,'s2-issuer_name');
 p.set('s2-issuer_name','Synthetic Émetteur');p.set('s3-reporting_currency','EUR');
 const result=p.submit();assert.equal(result.problems.length,0);assert.equal(result.context.identity.issuer_name,'Synthetic Émetteur');assert.equal(result.context.run.reporting_currency,'EUR');
});
test('context destinations use visible disclosure names instead of removed numbering',t=>{
 const p=form(t),labels=[...p.doc.querySelectorAll('summary')].map(node=>node.textContent);
 for(const label of ['Deal terms','Quotes','Valuation'])assert.ok(labels.includes(label));
 assert.doesNotMatch(p.doc.body.textContent,/section [457]/i);
 assert.match(p.doc.getElementById('sec1').textContent,/Shows “Deal terms”/);
 assert.match(p.doc.getElementById('sec1').textContent,/Shows “Quotes”/);
 assert.match(p.doc.getElementById('sec2').textContent,/market cap and net debt in “Valuation”/);
});
test('earnings requirements and optional-section errors keep native validation',t=>{
 const p=form(t);p.set('s2-issuer_name','Synthetic earnings');
 const choice=p.doc.getElementById('run_type-earnings');choice.checked=true;choice.dispatchEvent(new p.win.Event('change',{bubbles:true}));
 assert.ok(p.submit().problems.some(value=>value.includes('Current period')));
 p.set('s3-current_period','q3-2026');p.set('s3-prior_period','q2-2026');assert.equal(p.submit().problems.length,0);
});
test('loading a valid saved context keeps focus on visible context for review',async t=>{
 const p=form(t),input=p.doc.getElementById('load');
 const raw=fs.readFileSync(path.resolve(__dirname,'../../../cases/context/research-minimal.json'),'utf8');
 Object.defineProperty(input,'files',{configurable:true,value:[new p.win.File([raw],'context.json',{type:'application/json'})]});input.dispatchEvent(new p.win.Event('change'));
 for(let attempt=0;attempt<30&&!p.doc.getElementById('loadmsg').textContent.startsWith('Loaded');attempt++)await new Promise(resolve=>setTimeout(resolve,5));
 assert.match(p.doc.getElementById('loadmsg').textContent,/Loaded context.json/);
 assert.equal(p.doc.activeElement.closest('section').id,'sec2');
 const result=p.submit();assert.equal(result.problems.length,0);assert.equal(result.context.identity.issuer_name,'Northbridge Group');assert.equal(result.context.run.as_of,'2026-10-31');
});
