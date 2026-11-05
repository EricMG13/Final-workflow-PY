const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { JSDOM } = require(process.env.ISSUER_LIBRARY_JSDOM || 'jsdom');
const root=path.resolve(__dirname,'../../../artifacts/issuer-library/design-fixture');
const web=path.resolve(__dirname,'../web');
function fixture(hash='CP-1/performance') {
  const dom=new JSDOM(fs.readFileSync(path.join(web,'index.html'),'utf8'),{url:`file://${web}/index.html#${hash}`,runScripts:'outside-only'});
  dom.window.scrollTo=()=>{};dom.window.fetch=()=>new Promise(()=>{});
  dom.window.HTMLElement.prototype.scrollIntoView=function(){this.dataset.scrolledIntoView='true';};
  for(const name of ['data.js','workspace-data.js']) vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),dom.getInternalVMContext());
  for(const name of ['views.js','actions.js','screen.js']) vm.runInContext(fs.readFileSync(path.join(web,name),'utf8'),dom.getInternalVMContext());
  return dom;
}
const norm=s=>s.replace(/\*\*|`/g,'').replace(/\s+/g,' ').trim();
// A reader page's text with each shown name turned back into the retained code.
const retainedText=el=>{const copy=el.cloneNode(true);copy.querySelectorAll('abbr.module-ref').forEach(a=>a.replaceWith(a.title));return norm(copy.textContent);};
const PIN={'CP-1':'tdg-002/CP-1-attempt-2.md','CP-1A':'tdg-002/CP-1A-attempt-3.md','CP-2':'tdg-002/CP-2-attempt-2.md','CP-1C':'tdg-peers-2024-001/CP-1C-attempt-2.md','CP-6':'ford-otosan-2024-001/CP-6-attempt-1.md','CP-8':'tdg-run-comparison-001/CP-8.md'};
test('Every retained body block is reachable in exactly one named section',()=>{
  const dom=fixture(),w=dom.window;
  const result=w.eval(`Object.entries(data).map(([id,out])=>({id,sections:out.sections.filter(s=>s.blocks.length).map(s=>({heading:s.heading,count:modules[id].sections.filter(d=>d[2].some(p=>matchesHeading(s.heading,p))).length})),views:modules[id].sections.map(s=>({id:s[0],html:renderContent(id,s[0]),blocks:sectionData(id,s[0]).flatMap(s=>s.blocks)}))}))`);
  let covered=0;
  for(const m of result){
    for(const section of m.sections)assert.equal(section.count,1,`${m.id}: ${section.heading}`);
    for(const view of m.views){
      const text=norm(JSDOM.fragment(view.html).textContent);
      for(const block of view.blocks){
        const values=block.type==='text'?[block.text]:block.rows.flatMap(r=>r.cells);
        for(const value of values) assert.ok(text.includes(norm(value)),`${m.id}/${view.id} line ${block.line}: ${value.slice(0,70)}`);
        covered++;
      }
    }
  }
  assert.ok(covered>100);dom.window.close();
});
test('Financial chart uses retained periods and values; exact rows preserve dashes and negative signs',()=>{
  const dom=fixture(),w=dom.window;
  assert.deepEqual([...w.document.querySelectorAll('.bar-period')].map(e=>e.textContent),['FY2022','FY2023','FY2024']);
  assert.deepEqual([...w.document.querySelectorAll('.bar-value')].map(e=>e.textContent),['5,429','6,585','7,940']);
  const statements=norm(JSDOM.fragment(w.eval(`renderContent('${PIN['CP-1']}','statements')`)).textContent);
  assert.ok(statements.includes('2,923'));assert.ok(statements.includes('(1)'));assert.ok(statements.includes('—'));
  assert.ok(!statements.includes('2,992'));dom.window.close();
});
test('Inspector retains unknown classification, units and exact row; Escape restores the source trigger',()=>{
  const dom=fixture(),w=dom.window;
  const trigger=w.document.querySelector(`[data-evidence="${PIN['CP-1']}:246"]`);
  w.document.getElementById('content').scrollTop=343;
  trigger.click();w.eval('renderRoute()');
  assert.equal(w.document.activeElement.id,'back-analysis');
  assert.equal(w.document.getElementById('inspector').dataset.scrolledIntoView,'true');
  const text=w.document.getElementById('inspector').textContent;
  for(const value of ['Not classified','USD millions','7,940','6,585','5,429','Reported, PDF 106']) assert.ok(text.includes(value));
  w.document.getElementById('content').scrollTop=777;
  w.document.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));w.eval('renderRoute()');
  assert.equal(w.document.getElementById('inspector').hidden,true);assert.equal(w.document.activeElement,trigger);assert.equal(w.document.getElementById('content').scrollTop,343);
  dom.window.close();
});
test('Timeline keeps all nine events and never assigns calendar days to fiscal or combined dates',()=>{
  const dom=fixture('CP-1A/events'),d=dom.window.document;
  assert.equal(d.querySelectorAll('.timeline li').length,9);
  assert.equal(d.querySelectorAll('.timeline:not(.periods) li').length,5);
  assert.equal(d.querySelectorAll('.periods li').length,4);
  const october=[...d.querySelectorAll('.timeline li')].find(e=>e.querySelector('strong').textContent==='October 2024');
  assert.ok(october.textContent.includes('Month only'));dom.window.close();
});
test('Six-factor assessment preserves producer grades without fabricated numeric scores',()=>{
  const dom=fixture('CP-2/assessment'),d=dom.window.document;
  assert.deepEqual([...d.querySelectorAll('.grade')].map(e=>e.textContent),['Average','Not Assessable','Not Assessable','Not Assessable','Average','Weak']);
  assert.equal(d.querySelectorAll('.grade.adverse').length,1);
  assert.ok(d.getElementById('content').textContent.includes('confidence Medium'));dom.window.close();
});
test('Section navigation, topic search, invalid links and skip link keep issuer/module context',()=>{
  const dom=fixture('CP-1A/ownership'),w=dom.window,d=w.document;
  d.querySelector('.skip').click();assert.ok(w.location.hash.startsWith('#CP-1A/ownership'));assert.equal(d.activeElement.id,'analysis');
  d.getElementById('module-search').value='cash generation';d.getElementById('module-search').dispatchEvent(new w.Event('input'));
  assert.equal(d.querySelector('a.module-item').getAttribute('href'),'#CP-1/cash?c=tdg-002');
  w.location.hash='CP-2/no-such-section?e=99999';w.eval('renderRoute()');
  assert.ok(d.getElementById('module-head').textContent.includes('Fundamental credit'));assert.equal(d.getElementById('section-title').textContent,'Integrated assessment');assert.equal(d.getElementById('inspector').hidden,true);
  dom.window.close();
});
test('Retained text is escaped before formatting; no remote runtime dependency',()=>{
  const dom=fixture(),w=dom.window;
  assert.equal(w.eval(`rich('<img src=x onerror=alert(1)>')`),'&lt;img src=x onerror=alert(1)&gt;');
  for(const el of w.document.querySelectorAll('script[src],link[rel=stylesheet],img[src]')){
    const rel=el.getAttribute('src')||el.getAttribute('href');assert.ok(!/^https?:/.test(rel));assert.ok([web,root].some(folder=>fs.existsSync(path.join(folder,rel.split('?')[0]))),rel);
  }
  dom.window.close();
});
test('Every module primary view renders, with historical case changes and no fictitious missing values',()=>{
  const dom=fixture(),w=dom.window,d=w.document;
  const ids=w.eval('groups.flatMap(g=>g[1].map(m=>m[0]))');
  assert.equal(ids.length,25);
  for(const id of ids){
    w.location.hash=id;w.eval('renderRoute()');
    assert.ok(d.getElementById('content').textContent.length>200||d.querySelector('#content .missing-state'),id);
    assert.ok(!d.getElementById('content').innerHTML.includes('NaN'),id);
    assert.ok(!d.getElementById('module-head').textContent.includes('undefined'),id);
  }
  for(const [id,issuer] of [['CP-2H','Ford Otosan'],['CP-4C','Frontier'],['CP-2G','TransDigm Group']]){
    w.location.hash=id;w.eval('renderRoute()');assert.equal(d.querySelector('.issuer h1').textContent,issuer);
  }
  for(const id of ['CP-L10','CP-3D']){
    w.location.hash=id;w.eval('renderRoute()');assert.ok(d.querySelector('.missing-state'));assert.equal(d.querySelectorAll('#content svg,.chart-row').length,0);
  }
  dom.window.close();
});
test('Numeric parsing and peer comparison preserve absence, negatives, precision and units',()=>{
  const dom=fixture('CP-1C'),w=dom.window,d=w.document;
  assert.deepEqual(Array.from(w.eval(`['—','','not available','1,234.50','(12.5)','0','86.5398%','Infinity','around 2x'].map(chartNumber)`)),[null,null,null,1234.5,-12.5,0,86.5398,null,null]);
  d.getElementById('chart-metric').value='1';d.getElementById('chart-metric').dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(d.activeElement.id,'chart-metric');const rows=[...d.querySelectorAll('.chart-row')];assert.equal(rows.length,4);assert.ok(rows[3].textContent.includes('Not available'));assert.ok(rows[3].querySelector('.missing'));assert.ok(rows[0].textContent.includes('44.47'));
  w.location.hash='CP-3C';w.eval('renderRoute()');assert.equal(d.querySelectorAll('.negative').length,2);assert.ok(d.querySelector('.section-heading').textContent.includes('TRY billions'));
  dom.window.close();
});
test('Conditional path, cash bridge and recovery graphics use retained values without changing scope',()=>{
  const dom=fixture('CP-2G'),w=dom.window,d=w.document;
  assert.deepEqual([...d.querySelectorAll('.path-readout strong')].map(e=>e.textContent),['6,036.61','2,652.78','6,594.60']);
  assert.equal(d.querySelectorAll('polyline').length,3);
  w.location.hash='CP-2D';w.eval('renderRoute()');assert.equal(d.querySelectorAll('.vector-chart rect').length,6);assert.ok(d.querySelector('.vector-chart').textContent.includes('(2,441)'));assert.ok(!d.querySelector('.vector-chart').textContent.includes('4,972'));
  w.location.hash='CP-4C';w.eval('renderRoute()');assert.deepEqual([...d.querySelectorAll('.chart-row strong')].map(e=>e.textContent),['86.5398%','100.0000%','9.5291%','74.9657%','9.5291%','13.8421%']);
  dom.window.close();
});
test('Calendar source inspection keeps owning module and returns to the calendar route',()=>{
  const dom=fixture('W-Calendar/hedges'),w=dom.window,d=w.document;
  const base=parseFloat(d.querySelectorAll('.hedge-axis span')[1].style.left);assert.ok(base>33&&base<34);assert.equal(d.querySelectorAll('.hedge-span.future').length,4);assert.equal(d.querySelectorAll('.hedge-span:not(.future)').length,4);
  d.querySelector('.hedge-row').click();w.eval('renderRoute()');assert.ok(d.getElementById('inspector').textContent.includes('CP-2E'));assert.ok(w.location.hash.startsWith('#W-Calendar/hedges?c=tdg-003&e=tdg-003%2FCP-2E-attempt-2.md'));
  d.getElementById('back-analysis').click();w.eval('renderRoute()');assert.equal(w.location.hash,'#W-Calendar/hedges?c=tdg-003');
  dom.window.close();
});
test('Evidence rows act through labelled icons instead of repeating link words',()=>{
  const dom=fixture('W-Evidence/sources?c=tdg-002'),d=dom.window.document;
  const actions=[...d.querySelectorAll('.source-inventory>section>div:nth-child(2) a')];
  assert.ok(actions.length>4);
  for(const a of actions){
    assert.equal(a.textContent.trim(),'',a.outerHTML);assert.ok(a.querySelector('img'));
    assert.match(a.getAttribute('aria-label'),/^(Open output|Download original handoff|Download original file): CP-/);
    assert.equal(a.title,a.getAttribute('aria-label').split(':')[0]);
  }
  const names=actions.map(a=>a.getAttribute('aria-label'));
  assert.equal(new Set(names).size,names.length,'each icon names its own file');
  dom.window.close();
});
test('The white card starts at the top with no strip of text above it',()=>{
  const dom=fixture('W-Library/cases'),d=dom.window.document;
  assert.equal(d.querySelector('.topbar'),null);assert.equal(d.getElementById('workspace-name'),null);
  assert.ok(!d.body.textContent.includes('no model call until you start a run'));
  dom.window.close();
});
test('Evidence cases are isolated; report build selection changes both preview and original',()=>{
  const dom=fixture('W-Evidence/sources?c=ford-otosan-2024'),w=dom.window,d=w.document;
  assert.equal(d.querySelectorAll('.source-inventory>section').length,8);assert.ok(!d.getElementById('content').textContent.includes('TDG-002'));
  w.location.hash='W-Evidence/sources?c=tdg-002';w.eval('renderRoute()');assert.ok(!d.getElementById('content').textContent.includes('Ford Otosan'));assert.ok(!d.getElementById('content').textContent.includes('Frontier'));
  w.location.hash='W-Reports/tdg-fy2024-snapshot-6';w.eval('renderRoute()');assert.equal(d.getElementById('report-preview').getAttribute('src'),'reports/tdg-fy2024-snapshot-6/preview.html');assert.equal(d.querySelector('.report-tools a[download]').getAttribute('href'),'reports/tdg-fy2024-snapshot-6/original.html');assert.equal(d.getElementById('report-preview').getAttribute('sandbox'),'allow-scripts allow-downloads');
  w.location.hash='W-Library/cases';w.eval('renderRoute()');assert.equal(d.querySelectorAll('.case-list tbody.run-list').length,3);
  dom.window.close();
});
test('Malformed and inherited-object route keys cannot break navigation or cross issuer evidence',()=>{
  const dom=fixture(),w=dom.window,d=w.document;
  for(const hash of ['toString/x','__proto__/x','constructor/x']){w.location.hash=hash;assert.doesNotThrow(()=>w.eval('renderRoute()'));assert.equal(w.eval('current.module'),'W-Library',hash);}
  w.location.hash='CP-2H/s31?e=CP-1:246';w.eval('renderRoute()');assert.equal(d.getElementById('inspector').hidden,true);
  dom.window.close();
});
test('An analytical verdict is not promoted to a provenance classification',()=>{
  const dom=fixture('CP-6'),w=dom.window,d=w.document;
  const last=d.querySelectorAll('.debate')[2];assert.ok(last.textContent.includes('Insufficient Information'));assert.equal(last.querySelector('.source-footer .badge'),null,'an unclassified row shows no tag');
  assert.equal(w.eval(`classification({fields:[['Evidence classification','Insufficient Information']]})`),'Insufficient Information');
  w.location.hash='CP-1D';w.eval('renderRoute()');assert.equal(d.querySelectorAll('.vector-chart rect').length,6);assert.ok(d.querySelector('.vector-chart').textContent.includes('4,173'));
  dom.window.close();
});
test('Workspace tabs preserve issuer/run; unavailable destinations never substitute another case',()=>{
  const dom=fixture('CP-2H'),w=dom.window,d=w.document;
  for(const name of ['Calendar','Deliverables','Evidence','Summary','Analysis']) {
    const link=[...d.querySelectorAll('.workspace-tabs a')].find(a=>a.textContent===name);
    w.location.hash=link.getAttribute('href');w.eval('renderRoute()');
    assert.equal(d.querySelector('.issuer h1').textContent,'Ford Otosan',name);
    assert.equal(w.eval('current.context'),'ford-otosan-2024',name);
    assert.ok(!d.querySelector('#content iframe'),name);
    if(name==='Calendar')assert.ok(d.getElementById('content').textContent.includes('No dates are inferred from other cases.'));
    if(name==='Deliverables')assert.ok(d.getElementById('content').textContent.includes('No report was built from this run’s files'));
  }
  w.location.hash='CP-1/performance?c=ford-otosan-2024';w.eval('renderRoute()');
  assert.ok(d.querySelector('.missing-state'));assert.equal(d.querySelectorAll('.bar-column').length,0);
  assert.ok(d.querySelector('.missing-state').textContent.includes('Inputs only'));assert.ok(d.getElementById('content').textContent.includes('CP-1-selected-input.md'));assert.equal(d.querySelector('.available-case a'),null);
  w.location.hash='CP-1/performance?c=ford-otosan-2024&e=CP-1:246';w.eval('renderRoute()');assert.equal(d.getElementById('inspector').hidden,true);
  dom.window.close();
});
test('TDG runs and delivery collection are distinct and survive a fresh deep link',()=>{
  const dom=fixture('CP-2G'),w=dom.window,d=w.document;
  const calendar=[...d.querySelectorAll('.workspace-tabs a')].find(a=>a.textContent==='Calendar');w.location.hash=calendar.hash;w.eval('renderRoute()');
  assert.equal(d.querySelectorAll('.hedge-row').length,9);assert.equal(d.querySelectorAll('.timeline li').length,0);
  w.location.hash='W-Reports/unavailable?c=tdg-003';w.eval('renderRoute()');assert.equal(d.querySelector('#content iframe'),null);
  assert.ok(d.getElementById('content').textContent.includes('Build 3'));assert.ok(!d.getElementById('content').innerHTML.includes('tdg-deliveries'));
  w.location.hash='W-Evidence/sources?c=tdg-003';w.eval('renderRoute()');
  assert.equal(d.querySelectorAll('.source-inventory>section').length,16);assert.ok(!d.getElementById('content').textContent.includes('TDG-002'));
  const cold=fixture('W-Reports/unavailable?c=ford-otosan-2024');assert.equal(cold.window.document.querySelector('.issuer h1').textContent,'Ford Otosan');assert.equal(cold.window.document.querySelector('#content iframe'),null);
  cold.window.close();dom.window.close();
});
test('Narrative claims expose exact retained evidence without source hard wrapping',()=>{
  const dom=fixture('CP-4/s75'),w=dom.window,d=w.document;
  assert.equal(d.querySelectorAll('.finding').length,3);assert.equal(d.querySelectorAll('.finding br').length,0);
  const button=d.querySelector('.finding .source-link');button.focus();button.click();w.eval('renderRoute()');
  assert.ok(d.getElementById('inspector').textContent.includes('2.0'));assert.equal(d.querySelector('.finding .badge'),null);assert.equal(d.querySelector('#inspector .badge.badge-gray.classification').textContent,'Not classified');
  d.getElementById('back-analysis').click();w.eval('renderRoute()');assert.equal(d.activeElement,button);
  dom.window.close();
});
test('Grouped outline has unique labels, absorbed aliases, persistent disclosures and focus',()=>{
  const dom=fixture('CP-2E'),w=dom.window,d=w.document;
  assert.ok(d.querySelectorAll('.outline-group').length>=4);assert.equal(d.querySelectorAll('.section-item').length,21);
  const disclosure=d.querySelector('.outline-group');disclosure.querySelector('summary').click();const key=disclosure.dataset.group;
  const next=d.getElementById('next-section');next.focus();next.click();w.eval('renderRoute()');
  assert.equal(d.activeElement.id,'next-section');assert.equal([...d.querySelectorAll('.outline-group')].find(e=>e.dataset.group===key).open,false);
  d.getElementById('module-search').value='CP-2F';d.getElementById('module-search').dispatchEvent(new w.Event('input'));assert.equal(d.querySelectorAll('.module-item').length,1);assert.ok(d.querySelector('.module-item').href.includes('CP-2E'));
  w.location.hash='CP-4/s75';w.eval('renderRoute()');d.getElementById('module-search').value='';w.eval('renderNavigator(current.module)');
  const labels=[...d.querySelectorAll('.section-item')].map(e=>e.textContent);assert.equal(new Set(labels).size,labels.length);
  w.location.hash='CP-2F';w.eval('renderRoute()');assert.equal(w.eval('current.module'),'CP-2E');
  dom.window.close();
});
test('Every conditional point and bridge movement has keyboard evidence with exact source fields',()=>{
  const dom=fixture('CP-2G'),w=dom.window,d=w.document;
  assert.equal(d.querySelectorAll('.plot-point').length,9);
  const point=d.querySelectorAll('.plot-point')[1];assert.ok(point.getAttribute('aria-label').includes('2026'));point.focus();point.dispatchEvent(new w.MouseEvent('click',{bubbles:true,cancelable:true}));w.eval('renderRoute()');
  assert.ok(d.getElementById('inspector').textContent.includes('2026'));assert.equal(d.activeElement.id,'back-analysis');
  d.getElementById('back-analysis').click();w.eval('renderRoute()');assert.equal(d.activeElement,point);
  w.location.hash='CP-2D';w.eval('renderRoute()');assert.equal(d.querySelectorAll('.plot-point').length,6);
  dom.window.close();
});
test('Remembered section reading positions are isolated by run and destination',()=>{
  const dom=fixture('CP-4/s75'),w=dom.window,d=w.document;
  d.getElementById('content').scrollTop=270;w.location.hash='CP-4/s100?c=tdg-004';w.eval('renderRoute()');assert.equal(d.getElementById('content').scrollTop,0);
  w.location.hash='CP-4/s75?c=tdg-004';w.eval('renderRoute()');assert.equal(d.getElementById('content').scrollTop,270);
  w.location.hash='CP-4/s75?c=ford-otosan-2024';w.eval('renderRoute()');assert.equal(d.getElementById('content').scrollTop,0);
  dom.window.close();
});
test('Legacy evidence routes reject inherited object names and retain a valid context',()=>{
  for(const section of ['constructor','__proto__','toString']) {
    const dom=fixture('W-Evidence/'+section);assert.equal(dom.window.document.querySelector('.issuer h1').textContent,'TransDigm Group');dom.window.close();
  }
});
test('Navigation focus targets remain visible when the mobile outline or report chrome disappears',()=>{
  const dom=fixture('CP-2G'),w=dom.window,d=w.document;
  Object.defineProperty(w,'innerWidth',{value:640,configurable:true});
  const section=[...d.querySelectorAll('.section-item')].find(a=>a.textContent==='Assumption register');section.focus();w.location.hash=section.hash;w.eval('renderRoute()');
  assert.equal(d.activeElement.id,'section-title');assert.equal(d.getElementById('navigator').classList.contains('mobile-open'),false);
  w.location.hash='W-Reports/tdg-fy2024-snapshot?c=tdg-002';w.eval('renderRoute()');assert.equal(d.activeElement.id,'report-select');
  w.location.hash='W-Library/cases';w.eval('renderRoute()');assert.equal(d.activeElement.id,'analysis');dom.window.close();
});
test('Library filters combine case-insensitive search, sector, content and module without blending runs',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  assert.equal(d.getElementById('library-count').textContent,'3 issuers · 8 runs · 7 reports');
  const search=d.getElementById('library-query');search.focus();search.value='  FORD   2024 ';search.dispatchEvent(new w.Event('input',{bubbles:true}));
  assert.equal(d.querySelectorAll('.run-list a').length,1);assert.equal(d.querySelector('.case-list h2').textContent,'Ford Otosan');assert.equal(d.activeElement,search);
  const sector=d.querySelector('[data-library-filter="sector"]');sector.value='Telecommunications';sector.dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.ok(d.querySelector('.library-empty'));assert.equal(d.querySelectorAll('.run-list a').length,0);
  d.getElementById('library-clear').click();assert.equal(d.querySelectorAll('.run-list a').length,8);assert.equal(d.activeElement,search);
  const content=d.querySelector('[data-library-filter="content"]');content.value='reports';content.dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(d.getElementById('library-count').textContent,'1 issuer · 4 runs · 7 reports');assert.ok(![...d.querySelectorAll('.run-list a')].some(a=>a.href.includes('c=tdg-deliveries')));
  const module=d.querySelector('[data-library-filter="module"]');module.value='CP-2G';module.dispatchEvent(new w.Event('change',{bubbles:true}));assert.equal(d.querySelectorAll('.run-list a').length,1);assert.ok(d.querySelector('.run-list a').href.includes('c=tdg-003'));
  content.value='modules';content.dispatchEvent(new w.Event('change',{bubbles:true}));assert.deepEqual([...d.querySelectorAll('.run-list a')].map(a=>new URLSearchParams(a.hash.split('?')[1]).get('c')).sort(),['ford-otosan-2024','tdg-003']);
  dom.window.close();
});
test('Library filters by recorded workflow and as-of year, and keeps runs without them findable as not recorded',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  w.eval(`Object.assign(contexts['tdg-003'],{pathway:'earnings_update',asOf:'2024-12-28'});Object.assign(contexts['ford-otosan-2024'],{pathway:'credit_snapshot',asOf:'2021-04-11'});location.hash='W-Settings/workspace';renderRoute();location.hash='W-Library/cases';renderRoute()`);
  const pick=(name,value)=>{const c=d.querySelector(`[data-library-filter="${name}"]`);c.value=value;c.dispatchEvent(new w.Event('change',{bubbles:true}));};
  const shown=()=>[...d.querySelectorAll('.run-list a')].map(a=>new URLSearchParams(a.hash.split('?')[1]).get('c')).sort();
  assert.deepEqual([...d.querySelectorAll('[data-library-filter="workflow"] option')].map(o=>o.textContent),['Any workflow','Credit Snapshot','Earnings Update','Not recorded']);
  assert.deepEqual([...d.querySelectorAll('[data-library-filter="year"] option')].map(o=>o.textContent),['Any year','2024','2021','Not recorded']);
  pick('workflow','earnings_update');assert.deepEqual(shown(),['tdg-003']);
  assert.equal(norm(d.querySelector('.run-list a').closest('tr').children[2].textContent),'Earnings Update');
  assert.equal(d.getElementById('library-clear').disabled,false);
  pick('workflow','none');assert.equal(shown().length,6);assert.ok(!shown().includes('tdg-003')&&!shown().includes('ford-otosan-2024'));
  pick('workflow','all');pick('year','2021');assert.deepEqual(shown(),['ford-otosan-2024']);
  pick('year','none');assert.equal(shown().length,6);
  d.getElementById('library-clear').click();assert.equal(shown().length,8);
  assert.equal(d.querySelector('[data-library-filter="year"]').value,'all');
  const search=d.getElementById('library-query');search.value='earnings update';search.dispatchEvent(new w.Event('input',{bubbles:true}));assert.deepEqual(shown(),['tdg-003']);
  dom.window.close();
});
test('The module filter groups modules under the credit question each one answers',()=>{
  const dom=fixture('W-Library/cases'),d=dom.window.document;
  const select=d.querySelector('[data-library-filter="module"]');
  assert.ok(select.querySelectorAll('optgroup').length>2);
  assert.equal(select.querySelector('option[value="CP-2G"]').parentElement.label,'Outlook and downside');
  assert.equal(select.querySelector('option[value="CP-1"]').parentElement.label,'Financial performance');
  dom.window.close();
});
test('Grey text: app pages carry no subtitle, run headers no freshness line, the outline no design notes',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  assert.equal(d.querySelector('.issuer-meta'),null);
  assert.equal(d.querySelector('.nav-help'),null);assert.equal(d.querySelector('.nav-key'),null);
  w.location.hash='CP-1?c=tdg-002';w.eval('renderRoute()');
  assert.equal(norm(d.querySelector('.issuer .scope').textContent),'FY2024 historical evidence · later events separately dated');
  assert.equal(norm(d.querySelector('#context-step .intro').textContent),'Load a saved context or enter the issuer.');
  dom.window.close();
});
test('Library shows one row per issuer; an issuer with several runs opens a drop-down of its runs',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  const table=d.querySelector('table.case-list');
  assert.deepEqual([...table.querySelectorAll('thead th')].map(th=>norm(th.textContent)),['Issuer','Run','Workflow','Period','Reports','Open']);
  const groups=()=>[...d.querySelectorAll('table.case-list tbody.run-list')];assert.equal(groups().length,3);
  const group=name=>groups().find(g=>g.querySelector('h2').textContent===name);
  const cells=row=>[...row.children].slice(1,5).map(c=>norm(c.textContent));
  assert.deepEqual(cells(group('Ford Otosan').querySelector('tr')),['FORD-OTOSAN-2024','Not recorded','11 April 2024','No report'],'one run: the issuer row is the run');
  const tdg=group('TransDigm Group'),head=tdg.querySelector('tr'),toggle=head.querySelector('button.run-toggle');
  assert.equal(head.querySelector('th[scope="rowgroup"] .badge').textContent,'Aerospace & defense');
  assert.deepEqual(cells(head),['6 runs','Not recorded','Varies','7 reports']);
  assert.equal(toggle.getAttribute('aria-expanded'),'false');
  const runRows=[...tdg.querySelectorAll('tr.run-row')];assert.equal(runRows.length,6);assert.ok(runRows.every(r=>r.hidden));
  assert.deepEqual(toggle.getAttribute('aria-controls').split(' ').sort(),runRows.map(r=>r.id).sort());
  toggle.focus();toggle.click();
  assert.equal(toggle.getAttribute('aria-expanded'),'true');assert.ok(runRows.every(r=>!r.hidden));assert.equal(d.activeElement,toggle);
  assert.deepEqual(cells(d.querySelector('.run-list a[href*="c=tdg-002"]').closest('tr')),['TDG-002','Not recorded','FY2024 historical evidence','7 reports']);
  assert.equal(d.querySelectorAll('.run-list a').length,8,'one link per run');
  w.eval(`location.hash='W-Settings/workspace';renderRoute();location.hash='W-Library/cases';renderRoute()`);
  assert.equal(group('TransDigm Group').querySelector('button.run-toggle').getAttribute('aria-expanded'),'true','the drop-down stays open on return');
  w.eval(`contexts['frontier-2020'].sector='Unclassified';location.hash='W-Settings/workspace';renderRoute();location.hash='W-Library/cases';renderRoute()`);
  assert.equal(group('Frontier').querySelector('.badge').textContent,'Sector not recorded');
  assert.ok([...d.querySelectorAll('[data-library-filter="sector"] option')].some(o=>o.value==='Unclassified'&&o.textContent==='Not recorded'));
  dom.window.close();
});
test('A run with no saved outputs says so in an attention badge',()=>{
  const store=structuredClone(NORTHBRIDGE);
  store.runs['web-2']={...store.runs['web-1'],folder:'web-2',run:'WEB-2',modules:{}};
  const dom=appFixture('W-Library/cases',store,NORTHBRIDGE_REPORTS),d=dom.window.document;
  const reports=key=>d.querySelector(`.run-list a[href*="c=${key}"]`).closest('tr').children[4];
  assert.equal(norm(reports('web-2').textContent),'No saved outputs');assert.ok(reports('web-2').querySelector('.badge-attention'));
  dom.window.close();
});
test('Active Library filters show as removable chips, and Clear all appears only when something is filtered',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  const sector=d.querySelector('[data-library-filter="sector"]'),clear=d.getElementById('library-clear');
  assert.equal(clear.hidden,true);assert.equal(d.querySelectorAll('#library-chips .chip').length,0);
  sector.value='Automotive';sector.dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(clear.hidden,false);assert.ok(sector.classList.contains('active'));
  const chip=d.querySelector('#library-chips .chip');assert.equal(norm(chip.textContent),'Sector: Automotive');
  const remove=chip.querySelector('button');assert.equal(remove.getAttribute('aria-label'),'Remove Sector filter');
  remove.click();
  assert.equal(sector.value,'all');assert.equal(d.querySelectorAll('.run-list a').length,8);assert.equal(d.querySelectorAll('#library-chips .chip').length,0);
  assert.equal(d.activeElement,sector);assert.equal(clear.hidden,true);assert.ok(!sector.classList.contains('active'));
  dom.window.close();
});
test('New run and Settings use the shared secondary button for their other actions',()=>{
  const dom=fixture('W-NewRun/run'),w=dom.window,d=w.document;
  const ids=['edit-context','revise-run','another-run'];
  w.eval(`location.hash='W-Settings/workspace';renderRoute()`);ids.push('refresh-library','quit-library');
  for(const id of ids){const b=d.getElementById(id);assert.ok(b.classList.contains('secondary-action'),id);assert.ok(!b.classList.contains('text-button'),id);}
  dom.window.close();
});
test('Review W1: a run folder with a space still opens its issuer drop-down',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  w.eval(`contexts['tdg 005']={...contexts['tdg-002'],folder:'tdg 005',run:'TDG 005'};location.hash='W-Settings/workspace';renderRoute();location.hash='W-Library/cases';renderRoute()`);
  const tdg=[...d.querySelectorAll('tbody.run-list')].find(g=>g.querySelector('h2').textContent==='TransDigm Group'),toggle=tdg.querySelector('button.run-toggle');
  const rows=[...tdg.querySelectorAll('tr.run-row')];assert.equal(rows.length,7);
  assert.ok(rows.every(r=>!/\s/.test(r.id)),'row ids carry no whitespace');
  assert.doesNotThrow(()=>toggle.click());
  assert.equal(toggle.getAttribute('aria-expanded'),'true');assert.ok(rows.every(r=>!r.hidden),'every run row opens, including the spaced one');
  dom.window.close();
});
test('Review W2: a recorded as-of that is not a full date still gives its year',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  w.eval(`contexts['tdg-003'].asOf='2024-12';location.hash='W-Settings/workspace';renderRoute();location.hash='W-Library/cases';renderRoute()`);
  const year=d.querySelector('select[data-library-filter="year"]');
  assert.ok([...year.options].some(o=>o.value==='2024'),'2024 is offered');
  year.value='2024';w.eval('updateLibraryResults()');
  assert.deepEqual([...d.querySelectorAll('.run-list a.run-link')].map(a=>a.textContent),['TDG-003']);
  dom.window.close();
});
test('Review W3: iconAction escapes the link it is given',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  d.body.insertAdjacentHTML('beforeend',w.eval(`iconAction('Open','x','a"b<c',  'arrow-right')`));
  const a=d.body.lastElementChild;assert.equal(a.getAttribute('href'),'a"b<c');assert.equal(a.getAttribute('aria-label'),'Open: x');assert.equal(a.hasAttribute('download'),false);
  d.body.insertAdjacentHTML('beforeend',w.eval(`iconAction('Save','y','f.md','download',true)`));
  assert.equal(d.body.lastElementChild.hasAttribute('download'),true);
  dom.window.close();
});
test('Content labels use the shared grey badge, not a separate tag style',()=>{
  for(const route of ['W-Overview/overview?c=tdg-002','W-Evidence/sources?c=tdg-002','W-Reports/list','CP-4/s75','CP-6']){
    const dom=fixture(route),d=dom.window.document;
    assert.equal(d.querySelectorAll('.tag').length,0,route);
    dom.window.close();
  }
  const dom=fixture('W-Evidence/sources?c=ford-otosan-2024'),d=dom.window.document;
  assert.equal(d.querySelectorAll('.tag').length,0);
  assert.ok([...d.querySelectorAll('.source-inventory .badge.badge-gray')].some(b=>b.textContent==='Input'),'input files carry a grey Input badge');
  dom.window.close();
});
test('Grey text: Evidence rows name only the attempt; the intro states the PDF limitation plainly',()=>{
  const dom=fixture('W-Evidence/sources?c=tdg-002'),d=dom.window.document,content=d.getElementById('content');
  assert.equal(norm(content.querySelector('.intro').textContent),'Source PDFs aren’t included; page references point to the originals.');
  assert.equal(norm(content.querySelector('.source-inventory>section p').textContent),'Attempt 1 of 2');
  assert.ok(![...content.querySelectorAll('.source-inventory .badge')].some(t=>t.textContent==='Saved output'));
  dom.window.close();
});
test('Grey text: run pages drop state narration, hash notes, design specs and empty classifications',()=>{
  const dom=fixture('W-Reports/list?c=tdg-002'),w=dom.window,d=w.document;
  const at=route=>{w.location.hash=route;w.eval('renderRoute()');return d.getElementById('content');};
  let c=at('W-Reports/list?c=tdg-002');
  assert.equal(norm(c.querySelector('.intro').textContent),'7 reports built from TDG-002’s files.');
  assert.equal(c.querySelector('.report-row small'),null);
  c=at('W-Reports/tdg-fy2024-snapshot-3?c=tdg-002');assert.ok(!c.textContent.includes('remains selected'));
  c=at('CP-OS/activity?c=tdg-002');
  assert.ok(c.textContent.includes('No live progress or cost recorded for this run.'));assert.ok(c.textContent.includes('9 saved outputs'));
  assert.ok(!/source identity|SHA-256|historical selection/.test(c.textContent));
  c=at('W-Calendar/unavailable?c=tdg-003');assert.equal(c.querySelector('.context-note'),null);assert.equal(c.querySelector('.matrix-note'),null);
  c=at('CP-1?c=tdg-002');assert.ok(!c.textContent.includes('Source order preserved'));
  c=at('W-Overview/overview?c=tdg-002');
  assert.ok(!c.textContent.includes('Not classified'));
  assert.deepEqual([...c.querySelectorAll('.matrix-note')].map(n=>norm(n.textContent)),['Missing values have no bar.']);
  assert.equal(c.querySelector('.chart-legend'),null);
  const seen=[...c.querySelectorAll('.horizontal-chart .chart-label')].map(l=>norm([...l.childNodes].filter(n=>!n.classList?.contains('sr-only')&&n.tagName!=='SMALL').map(n=>n.textContent).join('')));
  assert.deepEqual(seen.slice(0,4),['Base','','','Demand and margin pressure']);
  c=at('CP-MODEL/publication?c=tdg-002');assert.equal(c.querySelector('.visual-plan'),null);assert.ok(!c.textContent.includes('delivery metadata'));
  c=at('CP-2H?c=tdg-002');assert.equal(c.querySelector('.visual-plan'),null);
  c=at('CP-2?c=tdg-003');assert.equal(norm(c.querySelector('.missing-state p').textContent),'3 versions of this analysis. Choose one to read.');
  c=at('W-Help/help');assert.ok(!c.textContent.includes('Visualisation coverage'));
  dom.window.close();
});
test('The run header names the issuer, its run and period on one line, and the tabs mark the current one',()=>{
  const dom=fixture('W-Overview/overview?c=tdg-002'),d=dom.window.document;
  const header=d.querySelector('.issuer');
  assert.equal(header.querySelector('h1').textContent,'TransDigm Group');
  assert.equal(header.querySelector('.issuer-meta .code').textContent,'TDG-002');
  assert.equal(header.querySelector('.issuer-meta a').getAttribute('href'),'#W-Library/cases');
  assert.ok(header.querySelector('.scope img[src$="calendar-days.svg"]'),'the period carries a calendar icon');
  assert.deepEqual([...d.querySelectorAll('.workspace-tabs a[aria-current="page"]')].map(a=>a.textContent),['Summary']);
  dom.window.close();
});
test('The library says what it is once and puts New run beside its title',()=>{
  const dom=fixture('W-Library/cases'),d=dom.window.document;
  assert.equal(d.querySelector('.issuer-meta'),null,'the title stands alone');
  assert.equal(d.querySelector('#content .intro'),null,'no second introduction');
  assert.ok(d.getElementById('library-new-run').closest('.issuer'),'the primary action sits beside the title');
  const deliverables=d.querySelector('.issuer .secondary-action');assert.equal(deliverables.getAttribute('href'),'#W-Reports/list');assert.equal(norm(deliverables.textContent),'All deliverables');
  assert.equal(d.querySelector('.library-result-meta'),null);
  assert.equal(d.getElementById('library-new-run').getAttribute('href'),'#W-NewRun/run');
  assert.ok(!/separate runs/.test(d.getElementById('library-results').textContent));
  assert.equal(d.querySelector('#content .matrix-note'),null,'no footnote under the list');
  dom.window.close();
});
test('The module filter names each module once',()=>{
  const dom=fixture('W-Library/cases'),d=dom.window.document;
  const options=[...d.querySelectorAll('[data-library-filter="module"] option')].slice(1);
  assert.ok(options.length>5);
  for(const option of options)assert.equal(option.textContent,dom.window.eval(`moduleLabel(${JSON.stringify(option.value)})`),option.value);
  dom.window.close();
});
test('A source footer leaves the line number to the inspector',()=>{
  const dom=fixture('CP-2/assessment'),d=dom.window.document;
  const footers=[...d.querySelectorAll('#content .source-footer')];
  assert.ok(footers.length);
  for(const footer of footers)assert.doesNotMatch(footer.textContent,/Line \d/);
  footers[0].querySelector('.source-link').click();dom.window.eval('renderRoute()');
  assert.match(d.querySelector('.evidence-context').textContent,/Line \d+/);
  dom.window.close();
});
test('Library return restores filters and clear resets retained default values without changing context',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  const search=d.getElementById('library-query');search.value='Ford';search.dispatchEvent(new w.Event('input',{bubbles:true}));
  w.location.hash=d.querySelector('.run-list a').hash;w.eval('renderRoute()');assert.equal(d.querySelector('.issuer h1').textContent,'Ford Otosan');
  w.location.hash='W-Library/cases';w.eval('renderRoute()');assert.equal(d.getElementById('library-query').value,'Ford');assert.equal(d.querySelectorAll('.run-list a').length,1);
  d.getElementById('library-clear').click();assert.equal(d.getElementById('library-query').value,'');assert.equal(d.querySelectorAll('.run-list a').length,8);assert.equal(w.eval('current.context'),'ford-otosan-2024');
  d.getElementById('analysis').focus();d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'/',bubbles:true}));assert.equal(d.activeElement.id,'library-query');
  const submit=new w.Event('submit',{bubbles:true,cancelable:true});d.getElementById('library-filters').dispatchEvent(submit);assert.equal(submit.defaultPrevented,true);
  dom.window.close();
});
test('Literal search text is escaped and short IDs include their separate delivery collection',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  const search=d.getElementById('library-query');search.value='TDG';search.dispatchEvent(new w.Event('input',{bubbles:true}));assert.equal(d.querySelectorAll('.run-list a').length,6);
  search.value='\"><img src=x onerror=alert(1)>';search.dispatchEvent(new w.Event('input',{bubbles:true}));
  w.location.hash='CP-1';w.eval('renderRoute()');w.location.hash='W-Library/cases';w.eval('renderRoute()');
  assert.equal(d.getElementById('library-query').value,'\"><img src=x onerror=alert(1)>');assert.equal(d.querySelector('[onerror]'),null);assert.ok(d.querySelector('.library-empty'));
  dom.window.close();
});
test('Workspace round trips do not persist automatically opened catalogue states',async()=>{
  const dom=fixture('CP-2H'),w=dom.window,d=w.document;
  const settle=()=>new Promise(resolve=>w.setTimeout(resolve,0));
  await settle();assert.equal(d.querySelector('.module-catalogue').open,false);
  w.location.hash='W-Reports/unavailable?c=ford-otosan-2024';w.eval('renderRoute()');await settle();
  w.location.hash='CP-2H/s31?c=ford-otosan-2024';w.eval('renderRoute()');await settle();assert.equal(d.querySelector('.module-catalogue').open,false);
  d.querySelector('.module-catalogue>summary').click();await settle();
  w.location.hash='W-Evidence/sources?c=ford-otosan-2024';w.eval('renderRoute()');await settle();
  w.location.hash='CP-2H/s31?c=ford-otosan-2024';w.eval('renderRoute()');await settle();assert.equal(d.querySelector('.module-catalogue').open,true);
  dom.window.close();
});

// Answer keys from the fix brief. Expected values are written here by hand and
// are never computed by the gallery under test.
const KEY_A={
  'tdg-002':{folder:'tdg-002',outputs:{'CP-1':['CP-1-attempt-1.md','CP-1-attempt-2.md'],'CP-1A':['CP-1A-attempt-1.md','CP-1A-attempt-2.md','CP-1A-attempt-3.md'],'CP-2':['CP-2-attempt-1.md','CP-2-attempt-2.md'],'CP-2A':['CP-2A-attempt-1.md'],'CP-2D':['CP-2D-attempt-1.md']},inputs:[]},
  'tdg-003':{folder:'tdg-003',outputs:{'CP-0':['CP-0.md'],'CP-1':['CP-1-attempt-1.md','CP-1-attempt-2.md'],'CP-1B':['CP-1B-attempt-1.md'],'CP-1D':['CP-1D-attempt-1.md'],'CP-2':['CP-2-integrated.md','CP-2-macro-update.md','CP-2-quality-update.md'],'CP-2A':['CP-2A-calendar-attempt-1.md'],'CP-2D':['CP-2D-attempt-1.md','CP-2D-calendar-consumer.md'],'CP-2E':['CP-2E-attempt-1.md','CP-2E-attempt-2.md'],'CP-2G':['CP-2G-attempt-1.md','CP-2G-attempt-2.md'],'CP-2H':['CP-2H-evidence-check.md']},inputs:[]},
  'tdg-004':{folder:'tdg-004',outputs:{'CP-0':['CP-0.md'],'CP-3C':['CP-3C-legal-consumer.md'],'CP-4':['CP-4-attempt-1.md','CP-4-attempt-2.md']},inputs:[]},
  'tdg-guidance':{folder:'tdg-guidance-001',outputs:{'CP-DR':['CP-DR-attempt-1.md']},inputs:[]},
  'tdg-peers-2024':{folder:'tdg-peers-2024-001',outputs:{'CP-0':['CP-0.md'],'CP-1C':['CP-1C-attempt-1.md','CP-1C-attempt-2.md'],'CP-2':['CP-2-peer-consumer.md']},inputs:['CP-1-peer-inputs-attempt-2.md','CP-1-peer-inputs.md','CP-2-delivery-input-attempt-2.md','CP-2-delivery-input-final.md','CP-2-delivery-input.md']},
  'ford-otosan-2024':{folder:'ford-otosan-2024-001',outputs:{'CP-0':['CP-0.md'],'CP-2G':['CP-2G-published-forecast.md'],'CP-2H':['CP-2H-attempt-1.md','CP-2H-attempt-2.md'],'CP-3C':['CP-3C-consumer.md'],'CP-5':['CP-5-attempt-1.md'],'CP-6':['CP-6-attempt-1.md']},inputs:['CP-1-selected-input.md']},
  'frontier-2020':{folder:'frontier-2020-001',outputs:{'CP-0':['CP-0.md'],'CP-3':['CP-3-recovery-consumer.md'],'CP-4C':['CP-4C-attempt-1.md']},inputs:[]},
  'tdg-run-comparison':{folder:'tdg-run-comparison-001',outputs:{'CP-2':['CP-2-consumer.md'],'CP-8':['CP-8-recheck.md','CP-8.md']},inputs:['CP-2-delivery.md']}
};
const KEY_B={'CP-0':['tdg-003','tdg-004','tdg-peers-2024','ford-otosan-2024','frontier-2020'],'CP-1':['tdg-002','tdg-003'],'CP-1A':['tdg-002'],'CP-1B':['tdg-003'],'CP-1C':['tdg-peers-2024'],'CP-1D':['tdg-003'],'CP-2':['tdg-002','tdg-003','tdg-peers-2024','tdg-run-comparison'],'CP-2A':['tdg-002','tdg-003'],'CP-2D':['tdg-002','tdg-003'],'CP-2E':['tdg-003'],'CP-2G':['tdg-003','ford-otosan-2024'],'CP-2H':['tdg-003','ford-otosan-2024'],'CP-3':['frontier-2020'],'CP-3C':['tdg-004','ford-otosan-2024'],'CP-4':['tdg-004'],'CP-4C':['frontier-2020'],'CP-5':['ford-otosan-2024'],'CP-6':['ford-otosan-2024'],'CP-8':['tdg-run-comparison'],'CP-DR':['tdg-guidance']};
const KEY_C=[
  ['tdg-fy2024-snapshot','Initial snapshot · failed date presentation','tdg-002/CP-2-attempt-2.md','249d0cbdf1ba','38eac27cebeb','Superseded'],
  ['tdg-fy2024-snapshot-2','Annual snapshot · reviewed','tdg-002/CP-2-attempt-2.md','249d0cbdf1ba','324952b09a08',null],
  ['tdg-fy2024-snapshot-3','Integrated · macro/ESG and conditional forecast','tdg-003/CP-2-integrated.md','828e78d47cbb','00186b0f4bdd',null],
  ['tdg-fy2024-snapshot-4','Peer comparison · first delivery, gap rows dropped','tdg-peers-2024-001/CP-2-delivery-input.md','b88d1dfce706','084e27e00b1d',null],
  ['tdg-fy2024-snapshot-5','Peer comparison · gap boundary repaired','tdg-peers-2024-001/CP-2-delivery-input-attempt-2.md','54247baa99d3','5ba26c11e2ee',null],
  ['tdg-fy2024-snapshot-6','Peer comparison · exact fiscal dates added','tdg-peers-2024-001/CP-2-delivery-input-final.md','ba312d7faa8a','6bc718146295',null],
  ['tdg-fy2024-snapshot-7','CP-8 repairs applied','tdg-run-comparison-001/CP-2-delivery.md','22edd045e3d6','c7c4156e7c2a','Latest']
];
const REPORTS_BY_RUN={'tdg-002':[1,2,3,4,5,6,7],'tdg-003':[3],'tdg-004':[],'tdg-guidance':[],'tdg-peers-2024':[4,5,6],'ford-otosan-2024':[],'frontier-2020':[],'tdg-run-comparison':[7]};
const KEY_D=[['CP-2',12,'Not classified'],['CP-2',35,'Analyst Interpretation'],['CP-2',132,'Analyst Interpretation'],['CP-2',39,'Documentary Fact'],['CP-2',45,'Insufficient Information · Documentary Fact'],['CP-2',84,'Analyst Interpretation'],['CP-2',85,'Analyst Interpretation'],['CP-1A',44,'Documentary Fact'],['CP-1A',46,'Analyst Interpretation'],['CP-1A',70,'Documentary Fact'],['CP-6',88,'Not classified'],['CP-6',143,'Not classified'],['CP-1',246,'Not classified']];
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const repo=path.resolve(__dirname,'../../..');
const contentOf=(dom,route)=>{dom.window.location.hash=route;dom.window.eval('renderRoute()');return dom.window.document.getElementById('content');};

test('Key A: every run lists exactly its saved outputs and inputs, with byte-identical downloads',()=>{
  const dom=fixture(),runs=JSON.parse(dom.window.eval('JSON.stringify(contexts)'));
  assert.deepEqual(Object.keys(runs).sort(),Object.keys(KEY_A).sort());
  for(const [key,expected] of Object.entries(KEY_A)){
    const run=runs[key],strip=id=>id.slice(expected.folder.length+1);
    assert.equal(run.folder,expected.folder);
    const outputs=Object.fromEntries(Object.entries(run.modules).filter(([,m])=>m.outputs.length).map(([id,m])=>[id,m.outputs.map(strip).sort()]));
    assert.deepEqual(outputs,Object.fromEntries(Object.entries(expected.outputs).map(([id,files])=>[id,[...files].sort()])),key);
    assert.deepEqual(Object.values(run.modules).flatMap(m=>m.inputs).map(strip).sort(),[...expected.inputs].sort(),key);
    for(const file of [...Object.values(expected.outputs).flat(),...expected.inputs]){
      assert.equal(hash(path.join(root,'sources',`${expected.folder}--${file}`)),hash(path.join(repo,'runs',expected.folder,file)),file);
    }
  }
  dom.window.close();
});
test('Key B: the Contains-module filter returns every run with an output and offers no module without one',()=>{
  const dom=fixture('W-Library/cases'),w=dom.window,d=w.document;
  const select=d.querySelector('[data-library-filter="module"]');
  assert.deepEqual([...select.options].map(o=>o.value).filter(v=>v!=='all').sort(),Object.keys(KEY_B).sort());
  for(const [module,runs] of Object.entries(KEY_B)){
    select.value=module;select.dispatchEvent(new w.Event('change',{bubbles:true}));
    assert.deepEqual([...d.querySelectorAll('.run-list a')].map(a=>new URLSearchParams(a.hash.split('?')[1]).get('c')).sort(),[...runs].sort(),module);
  }
  dom.window.close();
});
test('Availability uses only the recorded labels and an available output is never reported missing',()=>{
  const dom=fixture('CP-1?c=tdg-003'),w=dom.window,d=w.document;
  assert.ok(!d.querySelector('.missing-state'));assert.ok(d.getElementById('module-head').textContent.includes('Attempt 2 of 2'));
  assert.deepEqual([...d.querySelectorAll('#output-select option')].map(o=>o.value),['CP-1-attempt-1.md','CP-1-attempt-2.md']);
  assert.equal(d.querySelector('#output-select').value,'CP-1-attempt-2.md');assert.equal(d.querySelectorAll('.bar-column').length,0);
  const content=contentOf(dom,'CP-1?c=ford-otosan-2024');
  assert.ok(content.textContent.includes('Inputs only'));assert.ok(content.textContent.includes('CP-1-selected-input.md'));assert.ok(!content.textContent.includes('Output available'));
  contentOf(dom,'CP-1?c=tdg-002');d.querySelector('.module-catalogue').open=true;
  const labels=[...d.querySelectorAll('.module-code>span')].map(e=>e.textContent);
  assert.ok(labels.includes('Output available'));assert.ok(labels.includes('No output found'));
  for(const label of labels)assert.ok(['Output available','Inputs only','No output found','Run record'].includes(label),label);
  for(const route of ['CP-L10?c=tdg-002','CP-2H?c=tdg-002','W-Reports/list?c=ford-otosan-2024']){const text=contentOf(dom,route).textContent;assert.ok(!/No output in this run|is available in this gallery/.test(text),route);}
  dom.window.close();
});
test('A module with no output shows no other case, no outline and no pager, and offers only the same issuer',()=>{
  const dom=fixture('CP-2H?c=tdg-002'),d=dom.window.document,content=d.getElementById('content');
  assert.ok(content.querySelector('.missing-state').textContent.includes('No output found'));
  assert.equal(content.querySelector('.visual-plan'),null);
  assert.ok(!/dated rating posture|agency divergence|Ford/i.test(`${content.textContent} ${d.getElementById('module-list').textContent} ${d.getElementById('section-nav').textContent}`));
  assert.equal(d.getElementById('next-section'),null);assert.equal(d.querySelector('.section-outline'),null);
  assert.deepEqual([...content.querySelectorAll('.available-case a')].map(a=>new URLSearchParams(a.hash.split('?')[1]).get('c')),['tdg-003']);
  const ford=contentOf(dom,'CP-1A?c=ford-otosan-2024');assert.equal(ford.querySelector('.available-case a'),null);assert.ok(!ford.innerHTML.includes('c=tdg-'));
  dom.window.close();
});
test('Several unnumbered outputs show a chooser and pick none; a selected output keeps its route',()=>{
  const dom=fixture('CP-2?c=tdg-003'),w=dom.window,d=w.document,content=d.getElementById('content');
  assert.deepEqual([...content.querySelectorAll('.output-choices a')].map(a=>a.textContent.trim()),['Integrated','Macro-update','Quality-update']);
  assert.equal(w.eval('current.output'),null);assert.equal(d.querySelector('.finding'),null);assert.equal(d.getElementById('next-section'),null);
  w.location.hash=content.querySelector('.output-choices a').hash;w.eval('renderRoute()');
  assert.equal(w.eval('current.output'),'tdg-003/CP-2-integrated.md');assert.equal(new URLSearchParams(w.location.hash.split('?')[1]).get('o'),'CP-2-integrated.md');
  const next=d.getElementById('next-section');next.click();w.eval('renderRoute()');assert.equal(w.eval('current.output'),'tdg-003/CP-2-integrated.md');
  dom.window.close();
});
test('Curated views apply only to the exact file they were built for',()=>{
  const dom=fixture('CP-2?c=tdg-002'),w=dom.window,d=w.document;
  assert.equal(d.querySelectorAll('.factor').length,6);assert.equal(d.getElementById('output-select').value,'CP-2-attempt-2.md');
  const select=d.getElementById('output-select');select.focus();select.value='CP-2-attempt-1.md';select.dispatchEvent(new w.Event('change',{bubbles:true}));w.eval('renderRoute()');
  assert.equal(d.querySelectorAll('.factor').length,0);assert.equal(w.eval('current.output'),'tdg-002/CP-2-attempt-1.md');assert.equal(d.activeElement.id,'output-select');
  assert.equal(new URLSearchParams(w.location.hash.split('?')[1]).get('o'),'CP-2-attempt-1.md');
  w.location.hash='CP-1?c=tdg-003';w.eval('renderRoute()');assert.equal(d.querySelectorAll('.bar-column').length,0);
  dom.window.close();
});
test('A render failure names the new module and shows an explicit gap, never stale content',()=>{
  const dom=fixture('CP-1'),w=dom.window,d=w.document;
  let logged=0;w.console.error=()=>{logged++;};
  w.eval(`renderContent=()=>{throw new Error('forced')}`);
  w.location.hash='CP-2G';w.eval('renderRoute()');
  assert.ok(d.getElementById('content').textContent.includes('Couldn’t present this output'));assert.equal(d.querySelectorAll('.bar-column').length,0);
  assert.ok(d.getElementById('module-head').textContent.includes('Forward credit model'));assert.ok(w.document.title.includes('Forward credit model'));
  assert.ok(d.querySelector('#content a[download]').getAttribute('href').includes('CP-2G'));assert.equal(logged,1);
  dom.window.close();
});
test('Key C: reports trace to their source files by hash and carry the recorded labels',()=>{
  const dom=fixture('W-Reports/list?c=tdg-002'),w=dom.window,d=w.document;
  const reports=JSON.parse(w.eval('JSON.stringify(window.DESIGN_WORKSPACE.reports)'));
  assert.equal(reports.length,7);
  KEY_C.forEach(([id,label,cp2,cp2Hash,reportHash,status],i)=>{
    const report=reports[i];
    assert.equal(report.id,id);assert.equal(report.label,label);assert.equal(report.status,status);assert.ok(report.sha256.startsWith(reportHash),id);
    assert.equal(hash(path.join(repo,'deliverables',id,'report.html')),report.sha256);assert.equal(hash(path.join(root,'reports',id,'original.html')),report.sha256);
    const source=module=>report.builtFrom.find(b=>b.module===module);
    assert.equal(source('CP-1').source,'tdg-002/CP-1-attempt-2.md');assert.ok(source('CP-1').sha256.startsWith('301af0eeed2d'));
    assert.equal(source('CP-1A').source,'tdg-002/CP-1A-attempt-3.md');assert.ok(source('CP-1A').sha256.startsWith('6f63963177c2'));
    assert.equal(source('CP-2').source,cp2);assert.ok(source('CP-2').sha256.startsWith(cp2Hash),id);
  });
  for(const [run,builds] of Object.entries(REPORTS_BY_RUN))assert.deepEqual(reports.flatMap((r,i)=>r.builtFrom.some(b=>b.run===run)?[i+1]:[]),builds,run);
  for(const [run,builds] of Object.entries(REPORTS_BY_RUN)){
    const content=contentOf(dom,`W-Reports/list?c=${run}`),built=[...content.querySelectorAll('.report-built .report-row a')].map(a=>a.textContent);
    assert.deepEqual(built.map(t=>Number(t.match(/Build (\d)/)[1])).sort(),builds,run);
    if(!builds.length)assert.ok(content.textContent.includes('No report was built from this run’s files'),run);
  }
  for(const route of ['W-Reports/list?c=tdg-002','W-Reports/tdg-fy2024-snapshot-3?c=tdg-002','W-Library/cases','W-Overview?c=tdg-002','CP-OS?c=tdg-003','W-Help/help'])assert.ok(!/source-run linkage|No report linked|Revision order unverified|Saved build|tdg-deliveries/.test(contentOf(dom,route).innerHTML),route);
  dom.window.close();
});
test('Opening a report keeps the run pinned and Built from reaches each source run',()=>{
  const dom=fixture('W-Reports/list?c=tdg-002'),w=dom.window,d=w.document;
  assert.equal(d.querySelector('.issuer .code').textContent,'TDG-002');
  const row=[...d.querySelectorAll('.report-row a')].find(a=>a.textContent.includes('Build 3'));
  w.location.hash=row.hash;w.eval('renderRoute()');
  assert.equal(w.eval('current.context'),'tdg-002');assert.equal(d.querySelector('.issuer .code').textContent,'TDG-002');
  assert.equal(d.getElementById('report-preview').getAttribute('src'),'reports/tdg-fy2024-snapshot-3/preview.html');
  const links=[...d.querySelectorAll('.built-from a')].map(a=>a.getAttribute('href'));
  assert.ok(links.some(h=>h.includes('c=tdg-003')&&h.includes('o=CP-2-integrated.md')));assert.ok(links.some(h=>h.includes('c=tdg-002')));
  assert.ok(!/accepted|verified/i.test(d.querySelector('.built-from').textContent));
  const six=contentOf(dom,'W-Reports/tdg-fy2024-snapshot-6?c=tdg-002');assert.ok([...six.querySelectorAll('.built-from a')].some(a=>a.getAttribute('href').includes('c=tdg-peers-2024')));
  const other=contentOf(dom,'W-Reports/list?c=tdg-004');assert.ok(other.querySelectorAll('.report-other .report-row').length===7);assert.equal(w.eval('current.context'),'tdg-004');
  dom.window.close();
});
test('CP-8 is the deliverable comparison: all retained rows, both reports and the recheck, none of the old purpose',()=>{
  const dom=fixture('CP-8'),w=dom.window,d=w.document,content=d.getElementById('content');
  assert.equal(w.eval('current.context'),'tdg-run-comparison');assert.equal(w.eval('current.output'),PIN['CP-8']);
  assert.ok(d.getElementById('module-head').textContent.includes('Deliverable comparison'));assert.equal(d.getElementById('output-select').value,'CP-8.md');
  const text=retainedText(content),handoff=fs.readFileSync(path.join(repo,'runs',PIN['CP-8']),'utf8').split('\n');
  const rows=heading=>{const start=handoff.findIndex(l=>l===`### ${heading}`);return handoff.slice(start).filter((l,i,all)=>l.startsWith('|')&&all.slice(0,i).every(x=>!x.startsWith('## '))).slice(2).filter(l=>!/^\|[\s:|-]+\|$/.test(l));};
  const sections=rows('All five report sections').slice(0,5),material=rows('Material analytical changes').slice(0,9),regressions=rows('Unresolved regressions to repair').slice(0,3);
  assert.ok(sections[0].startsWith('| Key findings'));assert.ok(sections[4].startsWith('| Transaction summary'));assert.ok(material[0].startsWith('| Annual financial base'));assert.ok(material[8].startsWith('| Output scope'));assert.ok(regressions[2].startsWith('| RC-3'));
  for(const line of [...sections,...material,...regressions])for(const cell of line.split('|').slice(1,-1))assert.ok(text.includes(norm(cell)),cell.slice(0,60));
  assert.deepEqual([...content.querySelectorAll('.change-row .grade')].map(e=>e.textContent),['Revised','Unchanged','Revised','Unchanged','Unchanged']);
  const reports=[...content.querySelectorAll('a')].map(a=>a.getAttribute('href')||'');
  for(const id of ['tdg-fy2024-snapshot-2','tdg-fy2024-snapshot-6','tdg-fy2024-snapshot-7'])assert.ok(reports.some(h=>h.startsWith(`#W-Reports/${id}?`)&&h.includes('c=tdg-run-comparison')),id);
  assert.ok(text.includes('RC-1/2/3 are closed for this delivery revision.'));assert.ok(text.includes('“Current” means the selected latest local report, not current2026 issuer information.'));
  assert.equal(content.querySelectorAll('.regression-row .grade').length,3);for(const grade of content.querySelectorAll('.regression-row .grade'))assert.equal(grade.textContent,'Closed');
  const gaps=contentOf(dom,`CP-8/gaps`);assert.ok(gaps.textContent.includes('Native integration and assurance'));
  const old=/decision review|attribution|calibration|hit-rate|post-mortem/i;
  assert.ok(!old.test(text));assert.ok(!old.test(d.getElementById('module-head').textContent));assert.ok(!old.test(d.getElementById('module-list').textContent));
  const cp8=JSON.parse(w.eval(`JSON.stringify(window.DESIGN_WORKSPACE.visuals.filter(v=>v.module==='CP-8'))`));assert.equal(cp8.length,3);assert.ok(!old.test(JSON.stringify(cp8)));assert.equal(w.eval('window.DESIGN_WORKSPACE.visuals.length'),91);
  const recheck=contentOf(dom,'CP-8?c=tdg-run-comparison&o=CP-8-recheck.md');assert.ok(recheck.textContent.includes('RC-3 Critical labels'));assert.equal(recheck.querySelectorAll('.change-row').length,0);
  dom.window.close();
});
test('Every band, reading, caution and note quotes its own handoff or an allow-listed legend without digits',()=>{
  const ALLOW=['Select a plotted row to inspect its exact source fields.','Missing values have no bar.','Solid: active at the historical base.','Outlined: starts after the base.','“Not Assessable” is an evidence limitation, not an adverse grade.'];
  for(const legend of ALLOW)assert.ok(!/\d/.test(legend),legend);
  const dom=fixture(),w=dom.window;
  const outputs=JSON.parse(w.eval(`JSON.stringify(Object.keys(data).filter(id=>id.includes('/')).map(id=>({id,file:data[id].file,hasCall:!!data[id].call,first:modules[id].first,views:modules[id].sections.map(s=>({section:s[0],html:renderContent(id,s[0])}))})))`));
  let bands=0,checked=0;
  for(const out of outputs){
    const handoff=norm(fs.readFileSync(path.join(root,'sources',out.file),'utf8'));
    for(const view of out.views){
      const fragment=JSDOM.fragment(view.html);
      for(const el of fragment.querySelectorAll('.analysis-call,.chart-reading,.caution,.matrix-note,.downside')){
        for(const sentence of norm(el.textContent).split(/(?<=[.!?])\s+/).filter(Boolean)){
          checked++;assert.ok(handoff.includes(sentence)||ALLOW.includes(sentence),`${out.id}/${view.section}: ${sentence}`);
        }
      }
      for(const band of fragment.querySelectorAll('.analysis-call')){
        bands++;assert.equal(view.section,out.first);
        const source=band.nextElementSibling?.querySelector('[data-evidence]');assert.ok(source,`${out.id} band has a source action`);
        assert.ok(w.eval(`evidence.has(${JSON.stringify(source.dataset.evidence)})`),source.dataset.evidence);
      }
    }
    if(out.hasCall)assert.equal(JSDOM.fragment(out.views.find(v=>v.section===out.first).html).querySelectorAll('.analysis-call').length,1,out.id);
    else assert.ok(!out.views.some(v=>v.html.includes('analysis-call')),out.id);
  }
  assert.ok(bands>=18,`${bands} bands`);assert.ok(checked>=bands);
  dom.window.close();
});
test('Key D: provenance comes only from labels the handoff declares',()=>{
  const dom=fixture(),w=dom.window;
  for(const [module,line,expected] of KEY_D)assert.equal(w.eval(`classification(evidence.get(${JSON.stringify(`${PIN[module]}:${line}`)}))`),expected,`${module}:${line}`);
  assert.equal(w.eval(`classification({fields:[['Note','Mentions Management Language and Documentary Fact in passing.']]})`),'Not classified');
  assert.equal(w.eval(`classification({fields:[['Category','Documentary Fact']]})`),'Documentary Fact');
  dom.window.close();
});
test('Navigation links keep module identity, each curated module opens on its first page and tabs keep the selected output',()=>{
  const dom=fixture('CP-1?c=tdg-002'),w=dom.window,d=w.document;
  assert.equal([...d.querySelectorAll('a.module-item')].find(a=>a.getAttribute('href').startsWith('#CP-1A/')).getAttribute('href'),'#CP-1A/events?c=tdg-002');
  contentOf(dom,'CP-OS?c=tdg-002');assert.deepEqual([...d.querySelectorAll('.section-item')].map(a=>a.getAttribute('href')),['#CP-OS/activity?c=tdg-002','#CP-OS/delivery?c=tdg-002']);
  const section=w.eval(`modules['tdg-003/CP-1-attempt-1.md'].sections.map(s=>s[0]).find(id=>!modules['tdg-003/CP-1-attempt-2.md'].sections.some(s=>s[0]===id))`);assert.ok(section);
  contentOf(dom,`CP-1/${section}?c=tdg-003&o=CP-1-attempt-1.md`);contentOf(dom,'W-Evidence/sources?c=tdg-003');
  const href=[...d.querySelectorAll('.workspace-tabs a')].find(a=>a.textContent==='Analysis').getAttribute('href');
  assert.ok(href.startsWith(`#CP-1/${section}?`),href);assert.ok(href.includes('o=CP-1-attempt-1.md'),href);
  dom.window.close();
});
test('Run periods and bounded-case limits stay accurate outside the pinned output',()=>{
  const dom=fixture('CP-0?c=ford-otosan-2024'),d=dom.window.document;
  assert.ok(!d.querySelector('.scope').textContent.includes('agency publications'));assert.ok(d.querySelector('.scope').textContent.includes('11 April 2024'));
  assert.ok(contentOf(dom,'W-Evidence/sources?c=frontier-2020').textContent.includes('Bounded recovery consumer · not full security selection'));
  assert.ok(contentOf(dom,'W-Evidence/sources?c=ford-otosan-2024').textContent.includes('Bounded funding-plan consumer · not full refinancing / LME'));
  dom.window.close();
});

const press=(w,target,key,extra={})=>{const e=new w.KeyboardEvent('keydown',{key,bubbles:true,cancelable:true,...extra});target.dispatchEvent(e);return e;};
const type=(w,box,text)=>{box.value=text;box.dispatchEvent(new w.Event('input',{bubbles:true}));};
const searchGroups=d=>[...d.querySelectorAll('#search-results .search-group')].map(g=>({title:g.querySelector('p').textContent,hits:[...g.querySelectorAll('a.search-hit')]}));
test('The / key opens search unless typing or modified, as in Deploy VII',()=>{
  const dom=fixture('CP-1/performance?c=tdg-002'),w=dom.window,d=w.document,main=d.getElementById('analysis'),box=d.getElementById('module-search');
  assert.equal(box.placeholder,'Find a module, figure or source');assert.equal(box.getAttribute('aria-keyshortcuts'),'/');
  assert.equal(d.querySelector('.search kbd').textContent,'/');assert.equal(d.querySelector('.search kbd').getAttribute('aria-hidden'),'true');
  main.focus();
  for(const modifier of ['metaKey','ctrlKey','altKey']){assert.equal(press(w,main,'/',{[modifier]:true}).defaultPrevented,false,modifier);assert.equal(d.activeElement.id,'analysis',modifier);}
  assert.equal(press(w,main,'/').defaultPrevented,true);assert.equal(d.activeElement.id,'module-search');
  assert.ok(d.getElementById('navigator').classList.contains('mobile-open'));assert.equal(d.getElementById('module-toggle').getAttribute('aria-expanded'),'true');
  assert.equal(press(w,box,'/').defaultPrevented,false);
  main.focus();const rail=d.querySelector('.rail button[aria-label="Search (/)"]');assert.ok(rail);rail.click();assert.equal(d.activeElement.id,'module-search');
  contentOf(dom,'W-Library/cases');rail.click();assert.equal(d.activeElement.id,'library-query');
  dom.window.close();
});
test('Escape steps back one layer at a time, as in Deploy VII',()=>{
  const dom=fixture('CP-1/performance?c=tdg-002'),w=dom.window,d=w.document,box=d.getElementById('module-search'),nav=d.getElementById('navigator');
  press(w,d.getElementById('analysis'),'/');type(w,box,'net sales');assert.ok(d.querySelector('#search-results a.search-hit'));
  press(w,box,'Escape');assert.equal(box.value,'');assert.equal(d.getElementById('search-results').children.length,0);assert.equal(d.activeElement.id,'module-search');assert.ok(nav.classList.contains('mobile-open'));
  press(w,box,'Escape');assert.ok(!nav.classList.contains('mobile-open'));assert.equal(d.activeElement.id,'module-toggle');assert.equal(d.getElementById('module-toggle').getAttribute('aria-expanded'),'false');
  contentOf(dom,'W-Library/cases');const query=d.getElementById('library-query');query.focus();type(w,query,'zzz');assert.match(d.getElementById('content').textContent,/No matching issuers or runs/);
  press(w,query,'Escape');assert.equal(query.value,'');assert.doesNotMatch(d.getElementById('content').textContent,/No matching issuers or runs/);
  dom.window.close();
});
test('Arrow keys walk chart marks without wrapping, as in Deploy VII',()=>{
  const dom=fixture('CP-1/performance?c=tdg-002'),w=dom.window,d=w.document,bars=[...d.querySelectorAll('.bars .bar-column')];
  assert.equal(bars.length,3);bars[0].focus();
  assert.equal(press(w,bars[0],'ArrowRight').defaultPrevented,true);assert.equal(d.activeElement,bars[1]);
  press(w,bars[1],'ArrowDown');assert.equal(d.activeElement,bars[2]);
  assert.equal(press(w,bars[2],'ArrowRight').defaultPrevented,false);assert.equal(d.activeElement,bars[2]);
  press(w,bars[2],'ArrowLeft');assert.equal(d.activeElement,bars[1]);press(w,bars[1],'ArrowUp');assert.equal(d.activeElement,bars[0]);
  assert.equal(press(w,bars[0],'ArrowRight',{altKey:true}).defaultPrevented,false);assert.equal(d.activeElement,bars[0]);
  const prose=d.querySelector('#content .source-link');prose.focus();assert.equal(press(w,prose,'ArrowDown').defaultPrevented,false);
  const seen=new Set(),containers='.bars,.mix-bars,.horizontal-chart,.hedge-chart,.vector-chart';
  for(const id of w.eval('Object.values(pins)'))for(const section of w.eval(`modules[${JSON.stringify(id)}].sections.map(s=>s[0])`)){
    const module=id.split('/')[1].match(/CP-[A-Z0-9]+/)[0],context=w.eval(`data[${JSON.stringify(id)}].run`),content=contentOf(dom,`${module}/${section}?c=${context}`);
    for(const mark of content.querySelectorAll('.bar-column,.chart-row,.hedge-row,.plot-point,.mix-bars button')){assert.ok(mark.closest(containers),`${id}/${section}: ${mark.className}`);}
    for(const chart of content.querySelectorAll(containers)){
      seen.add(chart.className.baseVal??chart.className.split(' ')[0]);
      const marks=[...chart.querySelectorAll('[data-evidence]')];if(marks.length<2)continue;
      marks[0].focus();press(w,marks[0],'ArrowRight');assert.equal(d.activeElement,marks[1],`${id}/${section}`);
    }
  }
  assert.deepEqual([...seen].sort(),['bars','hedge-chart','horizontal-chart','mix-bars','vector-chart']);
  dom.window.close();
});
test('Search finds figures and sources of this run and opens them',()=>{
  const dom=fixture('CP-2?c=tdg-002'),w=dom.window,d=w.document,box=d.getElementById('module-search');
  // jsdom follows an anchor click on a later tick; the click handler still runs synchronously.
  const follow=a=>{a.click();w.location.hash=a.getAttribute('href');w.eval('renderRoute()');};
  assert.equal(d.getElementById('search-results').getAttribute('aria-live'),'polite');
  type(w,box,'source-supported dashboard');let groups=searchGroups(d);
  assert.equal(groups[0].title,'Figures');
  assert.equal(groups[0].hits[0].getAttribute('href'),'#CP-1/performance?c=tdg-002');
  assert.equal(groups[0].hits[0].getAttribute('aria-label'),'Figure: Financial foundation · Attempt 2 of 2 T4.10 — Source-supported dashboard');
  assert.ok(groups[0].hits[1].getAttribute('href').includes('o=CP-1-attempt-1.md'));
  assert.ok(contentOf(dom,groups[0].hits[0].getAttribute('href').slice(1)).textContent.includes('7,940'));
  type(w,box,'Quarterly comparison');
  assert.equal(searchGroups(d).length,0,'visual of another run');
  type(w,box,'Pretax continuing income');
  const row=searchGroups(d).find(g=>g.title.startsWith('Sources')).hits.find(a=>a.getAttribute('href').includes('CP-1-attempt-2.md%3A249'));assert.ok(row,'T4.10 row');
  assert.ok(row.getAttribute('href').startsWith('#CP-1/performance?c=tdg-002&e='),row.getAttribute('href'));
  follow(row);
  const inspector=d.getElementById('inspector');assert.equal(inspector.hidden,false);
  for(const exact of ['Pretax continuing income','2,215','1,716','1,127','Reported, PDF 106'])assert.ok(inspector.textContent.includes(exact),exact);
  assert.equal(d.activeElement.id,'back-analysis');
  press(w,d.activeElement,'Escape');w.eval('renderRoute()');assert.equal(inspector.hidden,true);assert.equal(d.activeElement.id,'module-search');assert.equal(box.value,'Pretax continuing income');
  type(w,box,'CP-1-attempt-1.md');const file=searchGroups(d)[0].hits[0];assert.ok(file.getAttribute('href').startsWith('#CP-1/'));assert.ok(file.getAttribute('href').endsWith('?c=tdg-002&o=CP-1-attempt-1.md'));
  follow(file);assert.equal(d.getElementById('output-select').value,'CP-1-attempt-1.md');
  type(w,box,'CP-1-instructions.md');assert.equal(searchGroups(d).length,0,'instructions are not shown');
  type(w,box,'PDF 106');const sources=searchGroups(d).find(g=>g.title.startsWith('Sources'));
  assert.match(sources.title,/^Sources · 4 of \d+$/);assert.equal(sources.hits.length,4);assert.ok(Number(sources.title.split(' of ')[1])>4);
  type(w,box,'Otosan');assert.equal(searchGroups(d).length,0,'another issuer');
  type(w,box,'&');for(const group of searchGroups(d))for(const hit of group.hits)assert.ok(!hit.textContent.includes('&amp;'),hit.textContent);
  type(w,box,'no output found');assert.ok([...d.querySelectorAll('.module-item')].some(a=>a.title==='CP-2H'),'status word');
  contentOf(dom,'CP-1?c=ford-otosan-2024');type(w,box,'Source-supported dashboard');assert.equal(searchGroups(d).length,0,'another run');
  type(w,box,'CP-1-selected-input.md');assert.equal(searchGroups(d)[0].hits[0].getAttribute('href'),'#W-Evidence/sources?c=ford-otosan-2024');
  contentOf(dom,'CP-1?c=tdg-003');type(w,box,'net sales');assert.ok(searchGroups(d).find(g=>g.title.startsWith('Sources')).hits.some(hit=>hit.getAttribute('aria-label')==='Reference: Financial foundation · Attempt 2 of 2 3 · NET SALES'),'a numbered row names the cell that matched');
  contentOf(dom,'CP-1B?c=tdg-003');type(w,box,'Quarterly comparison');const plotted=searchGroups(d)[0].hits[0];assert.ok(plotted.getAttribute('aria-label').startsWith('Figure: Earnings changes')&&plotted.textContent.includes('Quarterly comparison'));assert.ok(contentOf(dom,plotted.getAttribute('href').slice(1)).querySelector('#module-visual'));
  for(const context of w.eval('Object.keys(contexts)')){contentOf(dom,`W-Evidence/sources?c=${context}`);for(const text of ['t','a','.md'])for(const hit of (type(w,box,text),d.querySelectorAll('a.search-hit')))assert.ok(!hit.getAttribute('href').includes('undefined'),`${context} ${hit.getAttribute('href')}`);}
  dom.window.close();
});
test('Chart labels and basis text come from the retained handoff',()=>{
  const dom=fixture('CP-1/performance?c=tdg-002'),w=dom.window,d=w.document;
  assert.equal(d.querySelector('.chart-head span').textContent,'USD millions · Reported, PDF 106');
  const bar=d.querySelector('.bar-column');assert.ok(bar.getAttribute('aria-label').includes('USD millions'));
  bar.click();w.eval('renderRoute()');const basis=d.querySelector('#inspector .evidence-basis').textContent;
  assert.ok(basis.includes('Monetary unit USD millions; statement parentheses retained as negative'),basis);
  assert.ok(!basis.includes('period-end balances'),basis);
  assert.equal(contentOf(dom,'CP-1A/business?c=tdg-002').querySelector('.section-heading span').textContent,'FY2024 · approximate');
  dom.window.close();
});
test('Run inputs can be committed and the CP-8 rule is current',()=>{
  const {spawnSync}=require('node:child_process'),repo=path.resolve(__dirname,'../../..');
  for(const folder of ['tdg-002','tdg-003','tdg-004','tdg-guidance-001','tdg-peers-2024-001','tdg-run-comparison-001','ford-otosan-2024-001','frontier-2020-001'])
    assert.equal(spawnSync('git',['check-ignore','-q',`runs/${folder}/x.md`],{cwd:repo}).status,1,folder);
  assert.equal(spawnSync('git',['check-ignore','-q','runs/tdg-002/x.lock'],{cwd:repo}).status,0);
  assert.ok(fs.readFileSync(path.join(repo,'AGENTS.md'),'utf8').includes('CP-8 compares deliverables from prior runs with the latest current run'));
  const method=fs.readFileSync(path.join(repo,'src/deploy_vii/methods/cp8.md'));
  assert.equal(method.toString().split('\n')[0],'# CP-8 — prior/current deliverable comparison');
  assert.ok(fs.existsSync(path.join(repo,'docs/reuse/legacy-cp8-decision-ledger.md')));
  assert.ok(fs.readFileSync(path.join(repo,'docs/visualisations/MAP.md'),'utf8').includes(`| src/deploy_vii/methods/cp8.md | ${crypto.createHash('sha256').update(method).digest('hex')} |`));
});

// ---- One app: navigation across destinations and deliverables, over any workspace. ----
const NORTHBRIDGE={runs:{'web-1':{folder:'web-1',issuer:'Northbridge',title:'Northbridge',run:'WEB-1',sector:'Industrials',period:'As of 2025-03-31',first:'CP-0',modules:{
  'CP-0':{outputs:['web-1/deliveries/abc/CP-0.md'],inputs:[],default:'web-1/deliveries/abc/CP-0.md'},
  'CP-4A':{outputs:['web-1/CP-4A.md'],inputs:[],default:'web-1/CP-4A.md'}}}},
outputs:{
  'web-1/deliveries/abc/CP-0.md':{id:'web-1/deliveries/abc/CP-0.md',run:'web-1',module:'CP-0',source:'deliveries/abc/CP-0.md',file:'web-1--deliveries--abc--CP-0.md',href:'/files/runs/web-1/deliveries/abc/CP-0.md?sha256=aa',label:'CP-0',sha256:'aa'.repeat(32),case:'Northbridge · WEB-1',period:'As of 2025-03-31',scope:'Retained module output',firstHeading:null,sections:[{heading:'Findings',level:2,line:3,blocks:[{type:'table',line:5,headers:['Item','Value'],rows:[{line:7,cells:['Revenue','0']}]}]}]},
  'web-1/CP-4A.md':{id:'web-1/CP-4A.md',run:'web-1',module:'CP-4A',source:'CP-4A.md',file:'web-1--CP-4A.md',href:'/files/runs/web-1/CP-4A.md?sha256=cc',label:'CP-4A',sha256:'cc'.repeat(32),case:'Northbridge · WEB-1',period:'As of 2025-03-31',scope:'Retained module output',firstHeading:null,parseError:'Body before first heading',sections:[{heading:'Unstructured handoff',level:1,line:1,blocks:[{type:'text',line:1,end:1,text:'Body <b>raw</b>'}]}]}},
inputs:{},pins:{}};
const NORTHBRIDGE_REPORTS={reports:[
  {id:'abc',build:null,label:'Northbridge · as of 2025-03-31',status:null,issuer:'Northbridge',sha256:'r',scope:'s',modelPublished:false,href:'/files/runs/web-1/deliveries/abc/report.html?sha256=r&embedded=1',download:'/files/runs/web-1/deliveries/abc/report.html?sha256=r&download=1',files:[{name:'report.html',href:'/files/runs/web-1/deliveries/abc/report.html?sha256=r&download=1'}],builtFrom:[{module:'CP-0',sha256:'aa'.repeat(32),run:'web-1',source:'web-1/deliveries/abc/CP-0.md',output:true},{module:'CP-9',sha256:'bb'.repeat(32),run:null,source:'CP-9.md',output:false}]},
  {id:'orphan',build:null,label:'Gamma · as of 2024-01-31',status:null,issuer:'Gamma',sha256:'o',scope:'s',modelPublished:false,href:'/files/deliverables/orphan/report.html?sha256=o&embedded=1',download:'/files/deliverables/orphan/report.html?sha256=o&download=1',files:[],builtFrom:[{module:'CP-1',sha256:'dd'.repeat(32),run:null,source:'CP-1.md',output:false}]}],visuals:[]};
const EMPTY={runs:{},outputs:{},inputs:{},pins:{}};
function appFixture(hash,store,workspace,app={workspace:'/research',policy_locked:false,issues:[],problem:''}) {
  const dom=new JSDOM(fs.readFileSync(path.join(web,'index.html'),'utf8'),{url:`http://127.0.0.1:54321/#${hash}`,runScripts:'outside-only'});
  dom.window.scrollTo=()=>{};dom.window.HTMLElement.prototype.scrollIntoView=function(){};
  dom.window.fetch=()=>new Promise(()=>{});
  dom.window.eval(`window.DESIGN_DATA=${JSON.stringify(store)};window.DESIGN_WORKSPACE=${JSON.stringify(workspace)};window.DESIGN_APP=${JSON.stringify(app)};`);
  for(const name of ['views.js','actions.js','screen.js'])vm.runInContext(fs.readFileSync(path.join(web,name),'utf8'),dom.getInternalVMContext());
  return dom;
}
const goTo=(dom,hash)=>{dom.window.location.hash=hash;dom.window.eval('renderRoute()');return dom.window.document;};
test('The rail reaches every destination, marks where you are and keeps the selected run',()=>{
  const dom=fixture('CP-2H?c=ford-otosan-2024'),d=dom.window.document;
  const rail=label=>d.querySelector(`.rail a[aria-label="${label}"]`);
  for(const label of ['Issuer library','Research workspace','Deliverables','Run activity','New run','Settings','Help'])assert.ok(rail(label),label);
  assert.equal(rail('Deliverables').getAttribute('href'),'#W-Reports/list?c=ford-otosan-2024');
  assert.equal(rail('Run activity').getAttribute('href'),'#CP-OS/activity?c=ford-otosan-2024');
  assert.equal(rail('Research workspace').getAttribute('aria-current'),'page');
  for(const [route,label] of [['W-Library/cases','Issuer library'],['W-NewRun/run','New run'],['W-Settings/workspace','Settings'],['W-Help/help','Help'],['W-Reports/list','Deliverables'],['CP-OS/activity','Run activity']]){
    goTo(dom,route);
    assert.deepEqual([...d.querySelectorAll('.rail a[aria-current]')].map(a=>a.getAttribute('aria-label')),[label],route);
  }
  dom.window.close();
});
test('No destination still calls itself a gallery or a prototype',()=>{
  const dom=fixture('W-Library/cases'),d=dom.window.document;
  for(const route of ['W-Library/cases','W-Overview/overview?c=tdg-002','W-Reports/list?c=tdg-002','W-Evidence/sources?c=tdg-002','CP-OS/activity?c=tdg-002','CP-MODEL/publication?c=tdg-002','W-NewRun/run','W-Settings/workspace','W-Help/help','CP-1/audit?c=tdg-002']){
    goTo(dom,route);
    assert.ok(!/screen.design|prototype|gallery|working app/i.test(d.body.textContent+d.title),route);
  }
  dom.window.close();
});
test('New run lives inside the app and keeps what you entered across navigation',()=>{
  const dom=appFixture('W-Library/cases',NORTHBRIDGE,NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.equal(d.getElementById('new-run').hidden,true);assert.equal(d.getElementById('context-editor').hasAttribute('src'),false);
  assert.equal(d.getElementById('library-new-run').getAttribute('href'),'#W-NewRun/run');
  goTo(dom,'W-NewRun/run');
  assert.equal(d.getElementById('new-run').hidden,false);assert.equal(d.getElementById('content').hidden,true);
  assert.equal(d.getElementById('context-editor').getAttribute('src'),'context-form.html');
  assert.equal(d.querySelector('.issuer h1').textContent,'New run');
  d.getElementById('run-budget').value='37.50';
  goTo(dom,'W-Reports/list?c=web-1');
  assert.equal(d.getElementById('new-run').hidden,true);assert.equal(d.getElementById('content').hidden,false);
  goTo(dom,'W-NewRun/run');
  assert.equal(d.getElementById('run-budget').value,'37.50');assert.equal(d.activeElement,d.querySelector('#context-step h2'));
  dom.window.close();
});
test('Deliverables and module outputs link to each other, in both directions',()=>{
  const dom=appFixture('W-Reports/list',NORTHBRIDGE,NORTHBRIDGE_REPORTS),d=dom.window.document;
  // Written by hand from NORTHBRIDGE: one built from web-1, one from another issuer with no run.
  assert.deepEqual([...d.querySelectorAll('.report-built .report-row a')].map(a=>a.textContent),['Northbridge · as of 2025-03-31']);
  assert.deepEqual([...d.querySelectorAll('.report-rest .report-row a')].map(a=>a.textContent),['Gamma · as of 2024-01-31']);
  goTo(dom,'W-Reports/abc');
  const frame=d.getElementById('report-preview');
  assert.equal(frame.getAttribute('src'),'/files/runs/web-1/deliveries/abc/report.html?sha256=r&embedded=1');
  assert.equal(frame.getAttribute('sandbox'),'allow-scripts allow-downloads');
  assert.equal(d.querySelector('.report-tools a[download]').getAttribute('href'),'/files/runs/web-1/deliveries/abc/report.html?sha256=r&download=1');
  assert.ok(!d.querySelector('.rail').hidden);
  const rows=[...d.querySelectorAll('.built-from tbody tr')].map(row=>row.textContent);
  assert.match(rows[1],/CP-9No matching run file/);assert.match(d.querySelector('.built-from summary').textContent,/2 handoffs · 1 with no matching run file/);
  const toModule=d.querySelector('.built-from tbody a').getAttribute('href');
  assert.match(toModule,/^#CP-0\//);
  goTo(dom,toModule.slice(1));
  assert.equal(dom.window.eval('current.output'),'web-1/deliveries/abc/CP-0.md');
  const back=[...d.querySelectorAll('#module-head a')].find(a=>a.textContent.startsWith('Used in'));
  assert.equal(back.textContent,'Used in Northbridge · as of 2025-03-31');
  goTo(dom,back.getAttribute('href').slice(1));
  assert.ok(d.getElementById('report-preview'));
  dom.window.close();
});
test('A deliverable with no matching run still opens, under no run',()=>{
  const dom=appFixture('W-Reports/orphan?c=web-1',NORTHBRIDGE,NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.equal(dom.window.eval('current.context'),null);
  assert.equal(d.getElementById('report-preview').getAttribute('src'),'/files/deliverables/orphan/report.html?sha256=o&embedded=1');
  assert.equal(d.querySelector('.workspace-tabs').hidden,true);
  assert.match(d.querySelector('.report-tools').textContent,/No matching run/);
  assert.ok(!d.querySelector('.built-from tbody a'));
  d.getElementById('rail-search').click();
  assert.equal(dom.window.eval('current.module'),'W-Library','search from a run-less deliverable goes to the library');assert.equal(d.activeElement.id,'library-query');
  dom.window.close();
});
test('An uncurated workspace works: unnamed modules, unstructured handoffs, no calendar',()=>{
  const dom=appFixture('CP-4A?c=web-1',NORTHBRIDGE,NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.equal(dom.window.eval('current.module'),'CP-4A');
  assert.doesNotMatch(d.body.textContent,/Historical evidence|not current issuer/,'a new run is not historical by default');
  assert.equal(norm(d.querySelector('.issuer .scope').textContent),'As of 2025-03-31');
  assert.match(d.getElementById('module-head').textContent,/Shown unstructured: Body before first heading/);
  assert.ok(d.getElementById('content').textContent.includes('Body <b>raw</b>'),'raw text is shown, escaped');
  assert.equal(d.querySelector('#content b'),null);
  goTo(dom,'CP-0?c=web-1');
  assert.ok(d.getElementById('content').textContent.includes('Revenue'));
  assert.equal(d.querySelector('#content .record-field div').textContent,'0','zero stays a zero');
  goTo(dom,'W-Calendar?c=web-1');
  assert.match(d.getElementById('content').textContent,/No calendar retained for this run/);
  goTo(dom,'CP-1?c=web-1');
  assert.match(d.getElementById('content').textContent,/No output found/);
  dom.window.close();
});
test('A module with several unranked outputs does not break the published model page',()=>{
  const store=JSON.parse(JSON.stringify(NORTHBRIDGE)),first=store.outputs['web-1/deliveries/abc/CP-0.md'];
  store.outputs['web-1/CP-1.md']={...first,id:'web-1/CP-1.md',module:'CP-1',source:'CP-1.md',label:'CP-1',period:'As of 2025-03-31'};
  store.outputs['web-1/CP-1-v2.md']={...first,id:'web-1/CP-1-v2.md',module:'CP-1',source:'CP-1-v2.md',label:'V2',period:'As of 2025-03-31'};
  store.runs['web-1'].modules['CP-1']={outputs:['web-1/CP-1.md','web-1/CP-1-v2.md'],inputs:[],default:null};
  const dom=appFixture('W-Library/cases',store,NORTHBRIDGE_REPORTS),d=dom.window.document;
  goTo(dom,'CP-MODEL/publication?c=web-1');
  assert.equal(dom.window.eval('current.module'),'CP-MODEL');
  assert.match(d.getElementById('content').textContent,/No published model available/);
  dom.window.close();
});
test('Names from a workspace stay text on every destination',()=>{
  const bad='"><img src=x onerror=alert(1)>',store=JSON.parse(JSON.stringify(NORTHBRIDGE)),workspace=JSON.parse(JSON.stringify(NORTHBRIDGE_REPORTS));
  for(const key of ['issuer','title','run','sector','period'])store.runs['web-1'][key]=bad+key;
  for(const output of Object.values(store.outputs))for(const key of ['label','source','case','period','scope','parseError'])if(key in output)output[key]=bad+key;
  for(const report of workspace.reports){for(const key of ['label','status','scope'])report[key]=bad+key;report.files=[{name:bad,href:'/files/x'}];for(const row of report.builtFrom||[])row.source=bad;}
  const dom=appFixture('W-Library/cases',store,workspace,{workspace:bad,policy_locked:false,issues:[bad],problem:bad}),d=dom.window.document;
  for(const route of ['W-Library/cases','W-Overview?c=web-1','CP-0?c=web-1','CP-4A?c=web-1','W-Evidence?c=web-1','W-Calendar?c=web-1','CP-OS?c=web-1','W-Reports/list?c=web-1','W-Reports/abc?c=web-1','W-Reports/orphan','W-Settings/workspace','W-Help/help','W-NewRun/run']){
    goTo(dom,route);
    assert.equal(d.querySelector('img[src="x"]'),null,route);
  }
  dom.window.close();
});
test('An empty workspace opens on the library with only what can work',()=>{
  const dom=appFixture('CP-1/performance',EMPTY,{reports:[],visuals:[]}),d=dom.window.document;
  assert.equal(dom.window.eval('current.module'),'W-Library');
  assert.match(d.getElementById('content').textContent,/No runs in this workspace yet/);
  assert.equal(d.getElementById('library-new-run').getAttribute('href'),'#W-NewRun/run');
  for(const label of ['Research workspace','Run activity','Deliverables'])assert.equal(d.querySelector(`.rail a[aria-label="${label}"]`).hidden,true,label);
  for(const label of ['Issuer library','New run','Settings','Help'])assert.equal(d.querySelector(`.rail a[aria-label="${label}"]`).hidden,false,label);
  for(const route of ['W-Overview/overview','W-Calendar','W-Evidence/sources','CP-OS/activity','CP-1'])assert.equal(dom.window.eval(`location.hash='${route}';renderRoute();current.module`),'W-Library',route);
  assert.match(goTo(dom,'W-Reports/list').getElementById('content').textContent,/No deliverables yet/);
  for(const route of ['W-NewRun/run','W-Settings/workspace','W-Help/help','W-Help/visuals','W-Library/cases'])assert.doesNotThrow(()=>goTo(dom,route),route);
  dom.window.close();
});
test('Settings shows the workspace and its issues and respects the policy lock',async()=>{
  const app={workspace:'/research "main"',policy_locked:true,issues:['runs/x: <b>changed</b>'],problem:''};
  const dom=appFixture('W-Settings/workspace',NORTHBRIDGE,NORTHBRIDGE_REPORTS,app),d=dom.window.document;
  assert.equal(d.getElementById('workspace-path').value,'/research "main"');
  assert.equal(d.getElementById('workspace-path').disabled,true);assert.equal(d.getElementById('save-workspace').disabled,true);
  assert.match(d.querySelector('.settings').textContent,/managed by your IT configuration/);
  assert.equal(d.querySelector('.settings ul b'),null);assert.match(d.querySelector('.settings ul').textContent,/<b>changed<\/b>/);
  const calls=[];dom.window.fetch=async(url,options)=>{calls.push([url,options.headers['X-Issuer-Library']]);return{ok:true,json:async()=>({stopped:true})};};
  d.getElementById('quit-library').click();await new Promise(resolve=>setTimeout(resolve,5));
  assert.deepEqual(calls,[['/api/quit','1']]);assert.match(d.getElementById('settings-status').textContent,/Library stopped/);
  dom.window.close();
});
test('A workspace that cannot be read says so and the app still opens',()=>{
  const dom=appFixture('W-Library/cases',EMPTY,{reports:[],visuals:[]},{workspace:'',policy_locked:false,issues:[],problem:'CP-OS runtime is unavailable'}),d=dom.window.document;
  assert.equal(d.getElementById('app-problem').hidden,false);assert.match(d.getElementById('app-problem').textContent,/CP-OS runtime is unavailable/);
  dom.window.close();
});
test('Search from an app destination goes to the library search',()=>{
  const dom=appFixture('W-Settings/workspace',NORTHBRIDGE,NORTHBRIDGE_REPORTS),d=dom.window.document;
  d.getElementById('rail-search').click();
  assert.equal(dom.window.eval('current.module'),'W-Library');assert.equal(d.activeElement.id,'library-query');
  dom.window.close();
});
test('The shell loads only files the server embeds',()=>{
  const html=fs.readFileSync(path.join(web,'index.html'),'utf8');
  for(const [,rel] of html.matchAll(/(?:src|href)="([^"#]+)"/g))assert.ok(fs.existsSync(path.join(web,rel)),rel);
  const boot=fs.readFileSync(path.join(web,'boot.js'),'utf8');
  for(const name of ['views.js','actions.js','screen.js'])assert.ok(boot.includes(`'${name}'`)&&fs.existsSync(path.join(web,name)),name);
});
test('Module codes read as names on reader surfaces, references are muted, and evidence stays exact',()=>{
  const dom=fixture(),w=dom.window,d=w.document,nameCodes=w.eval('nameCodes');
  const named=text=>{const el=d.createElement('div');el.textContent=text;nameCodes(el);return el;};
  assert.equal(named("CP-2G's assumed 20% earnings reduction").textContent,"Forward credit model's assumed 20% earnings reduction");
  assert.equal(named('CP-2G').querySelector('abbr.module-ref').title,'CP-2G');
  assert.equal(named('CP-2F and CP-PARSE').textContent,'Rates, FX & hedging and Source readiness');
  assert.equal(named('CP-XYZ note').textContent,'CP-XYZ note');
  assert.equal(named('see CP-2-integrated.md').textContent,'see CP-2-integrated.md');
  const references=named('T4.3 normalization and C67');
  assert.equal(references.textContent,'T4.3 normalization and C67');
  assert.deepEqual([...references.querySelectorAll('small.ref')].map(e=>e.textContent),['T4.3','C67']);
  nameCodes(references);
  assert.equal(references.querySelector('.ref .ref'),null,'a second pass changes nothing');
  const chart=d.createElement('div');chart.innerHTML='<svg><text>CP-2G</text></svg>';nameCodes(chart);
  assert.equal(chart.querySelector('text').textContent,'Forward credit model');
  assert.equal(chart.querySelector('abbr'),null,'an abbr would not draw inside a chart');
  dom.window.close();
});
test('Only module codes change on any reader section, and every retained character is restorable',()=>{
  const dom=fixture(),w=dom.window,d=w.document,nameCodes=w.eval('nameCodes');
  const pages=w.eval(`Object.entries(data).filter(([id])=>data[id].source).flatMap(([id])=>modules[id].sections.map(s=>[id,s[0]])).filter(([,s])=>s!=='audit')`);
  assert.ok(pages.length>50);
  for(const [id,section] of pages){
    const el=d.createElement('div');
    el.innerHTML=w.eval(`renderContent(${JSON.stringify(id)},${JSON.stringify(section)})`);
    const before=el.textContent;
    nameCodes(el);
    const left=el.textContent.match(/\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])/g);
    assert.equal(left,null,`${id}/${section} still shows ${left}`);
    el.querySelectorAll('abbr.module-ref').forEach(a=>a.replaceWith(a.title));
    assert.equal(el.textContent,before,`${id}/${section}`);
  }
  dom.window.close();
});
test('The route names codes on reader pages and leaves the audit and inspector exact',()=>{
  const dom=fixture('CP-2/assessment?c=tdg-002'),w=dom.window,d=w.document;
  assert.doesNotMatch(d.getElementById('content').textContent,/\bCP-\d/);
  goTo(dom,'CP-2/audit?c=tdg-002');
  assert.match(d.getElementById('content').textContent,/\bCP-\d/,'the technical audit keeps codes');
  const key=w.eval(`[...evidence.entries()].find(([k,v])=>v.run==='tdg-002'&&v.fields.some(f=>/CP-\\d/.test(f[1])))[0]`);
  w.eval(`showInspector(${JSON.stringify(key)})`);
  assert.match(d.getElementById('inspector').textContent,/\bCP-\d/,'the inspector keeps codes');
  dom.window.close();
});
test('The app is organised by credit question and its chrome shows names, not codes',()=>{
  const dom=fixture('CP-2G?c=tdg-003'),d=dom.window.document,w=dom.window;
  assert.deepEqual([...d.querySelectorAll('.workspace-tabs a')].map(a=>a.textContent),['Summary','Analysis','Calendar','Deliverables','Evidence']);
  const head=d.querySelector('.module-title h2');
  assert.equal(norm(head.textContent),'Forward credit model');assert.equal(head.title,'CP-2G');
  assert.doesNotMatch(d.title,/CP-/);
  assert.deepEqual([...d.querySelectorAll('.nav-group summary')].map(s=>s.textContent).slice(0,7),['Business and evidence','Financial performance','Liquidity and refinancing','Outlook and downside','Capital structure and legal','Relative value','Decision and review']);
  assert.doesNotMatch(d.getElementById('module-list').textContent,/\bCP-\d/);
  assert.equal(d.querySelector('.module-item[aria-current]').title,'CP-2G');
  d.getElementById('module-search').value='cp-2g';w.eval(`renderNavigator(current.module)`);
  assert.ok([...d.querySelectorAll('.module-item')].some(a=>a.textContent.includes('Forward credit model')),'search still finds a code');
  assert.doesNotMatch(d.getElementById('search-results').textContent,/\bCP-\d/);
  assert.ok(d.querySelector('.module-title h2'));
  goTo(dom,'CP-2G/overview?c=tdg-003');
  assert.equal(w.eval('current.module'),'CP-2G','the code still works as a link');
  dom.window.close();
});
test('Summary leads with the stored call and never promotes a finding',()=>{
  const dom=fixture('W-Overview/overview?c=tdg-002'),w=dom.window,d=w.document;
  const band=norm(d.querySelector('.summary-lead').textContent);
  assert.ok(band.includes('Overall, TransDigm presents an established but not fully assessable business profile'));
  assert.ok(band.includes('Fundamental credit'));
  const source=d.querySelector('.summary-lead [data-evidence$=":132"]');
  assert.ok(source,'the band links its source line');
  assert.ok(norm(d.querySelector('[data-module="CP-1A"]').textContent).includes('Control rights, economic interest, shareholder concentration and private-equity sponsor status are therefore unestablished'));
  assert.equal(d.querySelector('.summary-lead').closest('.summary-text'),null,'the bottom line is never clamped');
  source.click();w.eval('renderRoute()');
  assert.equal(d.getElementById('inspector').hidden,false,'its source opens from the Summary');
  assert.equal(w.eval('current.module'),'W-Overview');
  dom.window.close();
});
test('A one-section page does not repeat its heading or show a pager',()=>{
  const dom=fixture('W-Overview/overview?c=tdg-002'),d=dom.window.document;
  assert.ok(d.getElementById('section-title').classList.contains('sr-only'));
  assert.equal(d.getElementById('next-section'),null);
  dom.window.close();
});
test('A run with no stored call says so and shows its findings without a bottom line',()=>{
  const dom=appFixture('W-Overview?c=web-1',NORTHBRIDGE,NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.equal(norm(d.querySelector('.summary-lead').textContent),'No bottom line is stored for this run. Read the findings below.');
  assert.equal(d.querySelector('.call-quote'),null);
  assert.ok(d.querySelector('[data-module]'),'each module with an output still has a card');
  dom.window.close();
});
test('A legal sub-module sits with the legal work under its own name',()=>{
  const dom=appFixture('W-Overview?c=web-1',NORTHBRIDGE,NORTHBRIDGE_REPORTS),d=dom.window.document;
  const link=d.querySelector('.module-item[title="CP-4A"]');
  assert.equal(norm(link.querySelector('.module-label').textContent),'Covenant capacity');
  assert.equal(link.closest('.nav-group').dataset.group,'Capital structure and legal');
  assert.ok(![...d.querySelectorAll('.nav-group summary')].some(s=>s.textContent==='Other modules'));
  assert.equal(dom.window.eval(`moduleLabel('CP-4A')`),'Covenant capacity');
  assert.equal(dom.window.eval(`moduleLabel('CP-2F')`),'Rates, FX & hedging','an absorbed code still takes its parent name');
  dom.window.close();
});
test('A module the groups do not know stays under its code, in its own group',()=>{
  const store=structuredClone(NORTHBRIDGE),output=store.outputs['web-1/CP-4A.md'];
  store.runs['web-1'].modules['CP-99']={outputs:['web-1/CP-99.md'],inputs:[],default:'web-1/CP-99.md'};
  store.outputs['web-1/CP-99.md']={...output,id:'web-1/CP-99.md',module:'CP-99',source:'CP-99.md',file:'web-1--CP-99.md',label:'CP-99'};
  const dom=appFixture('W-Overview?c=web-1',store,NORTHBRIDGE_REPORTS),d=dom.window.document;
  const link=d.querySelector('.module-item[title="CP-99"]');
  assert.equal(link.closest('.nav-group').dataset.group,'Other modules');
  assert.equal(norm(link.querySelector('.module-label').textContent),'CP-99');
  dom.window.close();
});
test('A card quotes only the Findings section, never a later section',()=>{
  const store=structuredClone(NORTHBRIDGE),output=store.outputs['web-1/deliveries/abc/CP-0.md'];
  output.sections.splice(1,Infinity,{heading:'Gaps',level:2,line:9,blocks:[{type:'text',line:9,end:9,text:'A stated gap.'}]});
  const dom=appFixture('W-Overview?c=web-1',store,NORTHBRIDGE_REPORTS),d=dom.window.document;
  const card=d.querySelector('.summary-card[data-module="CP-0"]');
  assert.ok(!card.textContent.includes('A stated gap.'));
  assert.ok(card.textContent.includes('No written findings'));
  dom.window.close();
});
test('A card quotes a finding written under a Findings subsection',()=>{
  const store=structuredClone(NORTHBRIDGE),output=store.outputs['web-1/deliveries/abc/CP-0.md'];
  output.sections.splice(1,Infinity,{heading:'Liquidity',level:3,line:8,blocks:[{type:'text',line:9,end:9,text:'A located finding.'}]});
  const dom=appFixture('W-Overview?c=web-1',store,NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.ok(d.querySelector('.summary-card[data-module="CP-0"]').textContent.includes('A located finding.'));
  dom.window.close();
});
// Real store output over the synthetic fixture, so these tests read what the app is really given.
function readerOutput(before='',after='') {
  const script=`
import json,sys
from pathlib import Path
sys.path.insert(0,'engine')
from store import parse_source,reader_fields
text=Path('designs/reader-fixture/CP-1.md').read_text(encoding='utf-8')
if sys.argv[1]:text=text.replace(sys.argv[1],sys.argv[2])
sections=parse_source(text)
print(json.dumps({'sections':sections,**reader_fields(sections)}))`;
  return JSON.parse(execFileSync(process.env.FW_PYTHON||'python3',['-B','-c',script,before,after],{cwd:path.join(__dirname,'..'),encoding:'utf8'}));
}
function readerStore(fields=readerOutput()) {
  const store=structuredClone(NORTHBRIDGE),id='web-1/CP-1.md';
  store.runs['web-1'].modules['CP-1']={outputs:[id],inputs:[],default:id};
  const {parseError,...base}=store.outputs['web-1/CP-4A.md'];
  store.outputs[id]={...base,id,module:'CP-1',source:'CP-1.md',file:'web-1--CP-1.md',label:'CP-1',...fields};
  return store;
}
test('Summary leads with the reader section: bottom line, confidence and limitation',()=>{
  const dom=appFixture('W-Overview?c=web-1',readerStore(),NORTHBRIDGE_REPORTS),lead=dom.window.document.querySelector('.summary-lead');
  assert.equal(norm(lead.querySelector('.call-quote').textContent),'Total debt / EBITDA fell from 4.20x to 3.60x while liquidity held above 275.');
  assert.match(norm(lead.textContent),/Confidence\s*Medium/);
  assert.match(norm(lead.textContent),/Main limitation\s*The maturity schedule has no FY2027 figure\./);
  assert.equal(lead.querySelector('.source-link').dataset.evidence,'web-1/CP-1.md:17');
  dom.window.close();
});
test('Summary draws chart tables with their exact values and shows a gap as not available',()=>{
  const dom=appFixture('W-Overview?c=web-1',readerStore(),NORTHBRIDGE_REPORTS),d=dom.window.document;
  const charts=[...d.querySelectorAll('.summary-chart')];
  assert.deepEqual(charts.map(c=>norm(c.querySelector('h2').textContent)),['Leverage','Interest cover','Liquidity','Debt maturities']);
  const rows=c=>[...c.querySelectorAll('.chart-row')].map(r=>[norm(r.querySelector('.chart-label').textContent),norm(r.querySelector('strong').textContent)]);
  assert.deepEqual(rows(charts[0]),[['FY2023Total debt / EBITDA','4.20'],['FY2023Net debt / EBITDA','3.85'],['FY2024Total debt / EBITDA','3.60'],['FY2024Net debt / EBITDA','3.25']]);
  assert.deepEqual(rows(charts[3]),[['FY2026Debt maturing','500'],['FY2027Debt maturing','Not available'],['FY2028Debt maturing','1,250']]);
  dom.window.close();
});
test('A handoff with a reader section opens on it, and hostile text stays text',()=>{
  const dom=appFixture('CP-1?c=web-1',readerStore(),NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.equal(norm(d.querySelector('.analysis-call .call-quote').textContent),'Total debt / EBITDA fell from 4.20x to 3.60x while liquidity held above 275.');
  assert.match(norm(d.querySelector('.analysis-call').textContent),/Main limitation\s*The maturity schedule/);
  const content=d.getElementById('content');
  assert.equal(content.querySelector('img[src="x"]'),null);
  assert.ok(content.textContent.includes('<img src=x onerror=alert(document.domain)>'));
  assert.ok(content.textContent.includes('More debt capacity before a covenant test.'));
  assert.equal(content.querySelectorAll('.record h3').length,2,'the band holds the bottom line row; only findings stay as records');
  dom.window.close();
});
test('A chart section is named for its measure and draws its table above the exact rows',()=>{
  const output=readerOutput(),line=output.sections.find(s=>s.heading==='Chart data: leverage').line;
  const dom=appFixture(`CP-1/s${line}?c=web-1`,readerStore(output),NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.equal(norm(d.getElementById('section-title').textContent),'Leverage');
  assert.equal(d.querySelectorAll('#content .chart-row').length,4);
  assert.ok(d.getElementById('content').textContent.includes('Synthetic.'),'the exact table stays below the chart');
  dom.window.close();
});
test('A malformed reader section is named, and the handoff still renders with no bottom line',()=>{
  const fields=readerOutput('| Bottom line |','| Conclusion |');
  assert.match(fields.issue,/Reader summary/);
  assert.equal(fields.summary,null);
  const dom=appFixture('W-Overview?c=web-1',readerStore(fields),NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.match(d.querySelector('.summary-lead').textContent,/No bottom line is stored/);
  assert.ok(d.querySelector('.summary-card[data-module="CP-1"]'));
  dom.window.location.hash='CP-1?c=web-1';dom.window.eval('renderRoute()');
  assert.ok(d.getElementById('content').textContent.includes('Total debt / EBITDA fell'),'its rows stay readable');
  dom.window.close();
});
test('A stopped run holding only one module shows one card',()=>{
  const store=readerStore();
  delete store.runs['web-1'].modules['CP-4A'];delete store.runs['web-1'].modules['CP-0'];
  delete store.outputs['web-1/CP-4A.md'];delete store.outputs['web-1/deliveries/abc/CP-0.md'];
  const dom=appFixture('W-Overview?c=web-1',store,NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.deepEqual([...d.querySelectorAll('.summary-card')].map(c=>c.dataset.module),['CP-1']);
  dom.window.close();
});
test('A reader section opens first, even when the catalogue names another heading',()=>{
  const store=readerStore();
  store.outputs['web-1/CP-1.md'].firstHeading='Chart data: liquidity';
  const dom=appFixture('CP-1?c=web-1',store,NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.equal(norm(d.getElementById('section-title').textContent),'Reader summary');
  assert.ok(d.querySelector('.analysis-call .summary-facts'));
  dom.window.close();
});
test('A catalogue first heading with no body of its own still opens a real section',()=>{
  const store=readerStore(readerOutput('| Bottom line |','| Conclusion |'));
  store.outputs['web-1/CP-1.md'].firstHeading='Findings';
  const dom=appFixture('CP-1?c=web-1',store,NORTHBRIDGE_REPORTS),d=dom.window.document;
  assert.ok(d.getElementById('content').textContent.includes('Total debt / EBITDA fell'));
  dom.window.close();
});
test('Every card on a Summary quotes its own handoff',()=>{
  const dom=fixture(),w=dom.window;
  let checked=0;
  for(const run of w.eval('Object.keys(contexts)')){
    const content=contentOf(dom,`W-Overview/overview?c=${run}`);
    assert.ok(content.querySelector('.summary-lead'),run);
    for(const card of content.querySelectorAll('[data-output]')){
      const text=card.querySelector('.summary-text');
      if(!text)continue;
      const raw=norm(fs.readFileSync(path.join(repo,'runs',card.dataset.output),'utf8').replace(/\n/g,' '));
      assert.ok(raw.includes(retainedText(text)),`${card.dataset.output}: ${text.textContent.slice(0,60)}`);
      checked++;
    }
  }
  assert.ok(checked>=10,`checked ${checked}`);
  dom.window.close();
});
test('A run in the library opens on its Summary',()=>{
  const dom=fixture('W-Library/cases'),d=dom.window.document;
  const link=[...d.querySelectorAll('.run-list a')].find(a=>a.getAttribute('href').includes('c=tdg-002'));
  assert.ok(link.getAttribute('href').startsWith('#W-Overview/overview?'));
  dom.window.close();
});

