'use strict';
// The app's screens over the workspace store. Curated visuals apply only to pinned outputs.
const store=window.DESIGN_DATA,data=store.outputs,contexts=store.runs,pins=store.pins;
// Curated section maps apply only to the exact output they were written for.
const modules = {
  [pins['CP-1']]: {name:'Financial foundation', subtitle:'Reported financials, cash generation and funding', first:'performance', sections:[
    ['performance','Performance',['T4.10']], ['interpretation','Financial interpretation',['Financial read-through']],
    ['statements','Income & equity statements',['T4.4']], ['cash','Cash generation',['T4.5']],
    ['balance','Balance sheet',['T4.6']], ['segments','Segments',['T4.16']],
    ['ebitda','EBITDA definitions & bridges',['Additional issuer bridges','T4.17']],
    ['debt','Debt & maturities',['T4.18']], ['definitions','Definitions & periods',['T4.11','T4.8']],
    ['scope','Scope & reporting basis',['Request','Sources','T4.1']], ['gaps','Gaps & limitations',['Gaps']],
    ['audit','Technical audit',['T4.9','T4.15','Calculations','Next module']]]},
  [pins['CP-1A']]: {name:'Business & governance', subtitle:'Operating model, transactions and issuer behaviour', first:'events', sections:[
    ['business','Business & operating model',['Company, business']], ['ownership','Ownership & control',['Ownership and control']],
    ['transactions','Transactions & capital allocation',['Transaction and capital']], ['events','Events & timeline',['Timeline and governance']],
    ['governance','Governance & financial policy',['Governance topics']], ['conflicts','Conflicting evidence & implications',['Conflicts and credit']],
    ['gaps','Gaps & limitations',['Gaps','Consumer readiness']], ['basis','Evidence & financial backdrop',['Sources','Source register','CP-1 fact']],
    ['audit','Technical audit',['Request','Calculations','Next module']]]},
  [pins['CP-2']]: {name:'Fundamental credit', subtitle:'Integrated assessment, downside mechanisms and monitoring', first:'assessment', sections:[
    ['assessment','Integrated assessment',['Integrated fundamental']], ['business','Business & competitive position',['Fundamental view','Competitive and external']],
    ['risks','Strengths, weaknesses & risks',['Ranked strengths']], ['profile','Financial profile',['Financial profile']],
    ['outlook','Outlook & downside chain',['Outlook and issuer']], ['factors','Six-factor matrix & monitoring',['Six-factor']],
    ['gaps','Gaps & limitations',['Gaps']], ['basis','Evidence & definitions',['Sources','Evidence rows','Calculations']],
    ['audit','Technical audit',['Request','Next module']]]},
  [pins['CP-8']]: {name:'Deliverable comparison', subtitle:'What changed between deliverables, and why?', first:'comparison', sections:[
    ['comparison','Deliverable comparison',['Findings','All five report sections','Material analytical changes','Unresolved regressions']],
    ['gaps','Gaps & limitations',['Gaps']],['sources','Sources',['Sources']],['audit','Technical audit',['Request','Calculations','Next module']]]}
};
const groups = [
  ['Business and evidence',[['CP-0','Source readiness'],['CP-1A','Business & governance'],['CP-DR','Research questions']]],
  ['Financial performance',[['CP-1','Financial foundation'],['CP-1B','Earnings changes'],['CP-L10','Financial change screen'],['CP-1D','Earnings quality'],['CP-1C','Peer benchmark']]],
  ['Liquidity and refinancing',[['CP-2D','Liquidity'],['CP-3C','Refinancing & LME']]],
  ['Outlook and downside',[['CP-2','Fundamental credit'],['CP-2A','Downside'],['CP-2G','Forward credit model'],['CP-2E','Rates, FX & hedging'],['CP-2H','Ratings & triggers']]],
  ['Capital structure and legal',[['CP-4','Legal & covenants'],['CP-4A','Covenant capacity'],['CP-4B','Structural priority'],['CP-4D','Intercreditor control'],['CP-4C','Recovery & fulcrum']]],
  ['Relative value',[['CP-3','Security selection'],['CP-3D','Market-implied risk']]],
  ['Decision and review',[['CP-6','Committee decision'],['CP-5','Evidence validation'],['CP-8','Deliverable comparison']]]
];
// A module the reading groups do not name still gets a place, under its code.
const unnamed=[...new Set(Object.values(data).map(output=>output.module))].filter(id=>id!=='CP-MODEL'&&!groups.some(group=>group[1].some(item=>item[0]===id))).sort();
if(unnamed.length)groups.push(['Other modules',unnamed.map(id=>[id,id])]);
const moduleNames = Object.fromEntries(groups.flatMap(g=>g[1]));
delete modules.undefined; // A pin this workspace does not hold.
const isAnalytical = id => !id.startsWith('W-')&&!['CP-OS','CP-MODEL'].includes(id);
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const plain = value => String(value).replace(/\*\*|`/g,'');
const rich = value => esc(value).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>');
const icon = name => `<img src="icons/${name}.svg" alt="">`;
const matchesHeading = (heading,prefix) => prefix.startsWith('=') ? heading===prefix.slice(1) : heading.startsWith(prefix) && (!/^T\d+\.\d+$/.test(prefix) || !/\d/.test(heading.charAt(prefix.length)));
const evidence = new Map();
const lastSection = new Map(), lastFile = new Map();
const readingPositions = new Map(), expandedGroups = new Map();
const LIBRARY_DEFAULTS = {query:'',sector:'all',workflow:'all',year:'all',content:'all',module:'all'};
const libraryFilters = {...LIBRARY_DEFAULTS};
const expandedIssuers = new Set(); // Issuers whose run list is open; kept for the page session.
let current = null, returnTrigger = null, returnScroll = 0, returnContentScroll = 0;
installDestinations();
const appDestinations=new Set(['W-Library','W-NewRun','W-Settings','W-Help']); // These need no selected run.
const aliases = {'CP-2F':'CP-2E','CP-2C':'CP-1A','CP-1E':'CP-1D','CP-5A':'CP-5','CP-6A':'CP-6'};
for(const visual of window.DESIGN_WORKSPACE.visuals)for(const alias of String(visual.aliases||'').split(/[;,\s]+/).filter(Boolean))aliases[alias]??=visual.module;
// Reader pages show names; the audit, inspector and evidence pages keep exact codes. Text only, so
// downloads, links and the retained files are untouched, and each name carries its code as a title.
const MODULE_CODE=/\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])/,REFERENCE=/\bT\d+[A-Z]?\.\d+\b|\b[FKCS]\d{1,4}\b/;
const READER_TOKEN=new RegExp(`${MODULE_CODE.source}|${REFERENCE.source}`,'g');
// A module's own name wins; a code standing in for its own label takes its parent's name when it has one.
const moduleLabel=code=>{
  const own=moduleNames[code];
  return (own!==code&&own)||moduleNames[aliases[code]]||own||(code==='CP-MEMO'?'Credit memo':null);
};
const namedText=text=>text.replace(new RegExp(MODULE_CODE,'g'),code=>moduleLabel(code)||code);
const showsCodes=({module,section})=>section==='audit'||['W-Evidence','CP-OS','W-Help','W-Settings','W-NewRun'].includes(module);
function readerMark(token) {
  if(!MODULE_CODE.test(token))return Object.assign(document.createElement('small'),{className:'ref',textContent:token});
  const label=moduleLabel(token);
  return label?Object.assign(document.createElement('abbr'),{className:'module-ref',textContent:label,title:token}):token;
}
function nameCodes(root) {
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),nodes=[];
  while(walker.nextNode())nodes.push(walker.currentNode);
  for(const node of nodes) {
    const parent=node.parentElement;
    if(parent.closest('.ref,.module-ref,.built-from,.hash'))continue;
    const parts=[...node.data.matchAll(READER_TOKEN)];
    if(!parts.length)continue;
    // A chart or a select cannot hold markup, so these only take the name.
    if(parent.closest('svg,option')){node.data=namedText(node.data);continue;}
    const fragment=document.createDocumentFragment();
    let at=0;
    for(const part of parts) {
      fragment.append(node.data.slice(at,part.index),readerMark(part[0]));
      at=part.index+part[0].length;
    }
    fragment.append(node.data.slice(at));
    node.replaceWith(fragment);
  }
}

for (const [id, output] of Object.entries(data)) {
  const located={module:output.module,output:id,run:output.run};
  for (const section of output.sections) for (const block of section.blocks) {
    if (block.type === 'table') for (const row of block.rows) {
      const priorText=section.blocks.slice(0,section.blocks.indexOf(block)).filter(b=>b.type==='text').at(-1)?.text;
      const basis=priorText||output.basis?.text;
      evidence.set(`${id}:${row.line}`, {...located,line:row.line,title:plain(row.cells[0]), fields:block.headers.map((label,i)=>[label,row.cells[i]]),section:section.heading,basis});
    }
    else evidence.set(`${id}:${block.line}`, {...located,line:block.line,title:section.heading,fields:[['Retained finding',block.text]],section:section.heading});
  }
  // Unknown nonempty sections remain visible rather than being silently omitted.
  const known = modules[id].sections.flatMap(s=>s[2]);
  const unknown = output.sections.filter(s=>s.blocks.length && !known.some(p=>matchesHeading(s.heading,p)));
  if (unknown.length) modules[id].sections.push(['additional','Additional findings',unknown.map(s=>'='+s.heading)]);
}
for(const definition of Object.values(modules)) {
  const seen=new Set();
  for(const section of definition.sections) {
    if(seen.has(section[1]))section[1]=section[1]==='Gaps'?'Module-wide gaps':`${section[1]} · ${section[0]}`;
    seen.add(section[1]);
  }
}

function sectionData(outputId, id) {
  const definition = modules[outputId].sections.find(s=>s[0]===id);
  return data[outputId].sections.filter(s=>definition[2].some(p=>matchesHeading(s.heading,p)));
}
function findRow(module, prefix, label) {
  for (const s of data[module].sections.filter(s=>matchesHeading(s.heading,prefix))) for (const b of s.blocks.filter(b=>b.type==='table')) {
    const row=b.rows.find(r=>plain(r.cells[0])===label);
    if(row) return {table:b,row,key:`${module}:${row.line}`};
  }
  throw new Error(`Missing pinned fixture: ${module} / ${label}`);
}
function sourceLink(key, label='View source') {
  return `<button class="source-link" data-evidence="${esc(key)}">${icon('file-text')}${esc(label)}</button>`;
}
const PROVENANCE='Documentary Fact|Management Language|Analyst Interpretation|Insufficient Information';
// A class counts only where the handoff declares it; mid-sentence mentions and verdicts never do.
function declaredClasses(value) {
  const cell=value.trim(),found=[];
  const opening=cell.match(new RegExp(`^(${PROVENANCE})[.:]\\s`));
  if(opening)found.push(opening[1]);
  const graded=cell.replace(/\*\*/g,'').match(new RegExp(`^.{1,30} — (${PROVENANCE})$`));
  if(graded)found.push(graded[1]);
  for(const bold of cell.matchAll(/\*\*(.+?)\*\*/g)) {
    if(bold[0]===cell)continue;
    const label=bold[1].trim(),after=cell[bold.index+bold[0].length];
    const match=label.match(new RegExp(`^(${PROVENANCE})[.:]$`))||(after===':'?label.match(new RegExp(`^(${PROVENANCE})$`)):null)||label.match(new RegExp(`^(${PROVENANCE});`))||label.match(new RegExp(`— (${PROVENANCE})`));
    if(match)found.push(match[1]);
  }
  return found;
}
function classification(item) {
  const classes=item.fields.flatMap(([label,value])=>{
    const declared=/classification|category|provenance|evidence (class|type)/i.test(label)?plain(value).trim().match(new RegExp(`^(${PROVENANCE})`)):null;
    return [...(declared?[declared[1]]:[]),...declaredClasses(value)];
  });
  return [...new Set(classes)].join(' · ') || 'Not classified';
}
// Lists show a class only when the handoff declared one; the inspector still says Not classified.
const classTag=(item,cls)=>{const c=classification(item);return c==='Not classified'?'':`<span class="${cls}">${esc(c)}</span>`;};
function sourceFooter(key) {
  const item=evidence.get(key);
  return `<div class="source-footer">${sourceLink(key)}${classTag(item,'badge badge-gray')}</div>`;
}
function tableMarkup(module, block) {
  const financial=block.financial||block.headers.some(h=>/^(FY\d{4}|Sep 30|Own FY)/.test(h))||block.rows.some(r=>r.cells.slice(1).filter(c=>chartNumber(c)!==null).length>=2);
  if(!financial) return `<div class="records">${block.rows.map(row=>{
    const key=`${module}:${row.line}`;
    return `<section class="record"><h3>${rich(row.cells[0])}</h3>${block.headers.slice(1).map((h,i)=>`<div class="record-field"><h4>${esc(h)}</h4><div>${rich(row.cells[i+1])}</div></div>`).join('')}${sourceFooter(key)}</section>`;
  }).join('')}</div>`;
  return `<div class="table-scroll" tabindex="0" role="region" aria-label="Exact source values"><table><thead><tr>${block.headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${block.rows.map(row=>`<tr><th scope="row">${sourceLink(`${module}:${row.line}`,plain(row.cells[0]))}${classTag(evidence.get(`${module}:${row.line}`),'row-classification')}</th>${row.cells.slice(1).map(c=>`<td>${rich(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function sectionsMarkup(module, sections, omitPresentedTable=false) {
  return sections.map(section=>{
    const blocks=section.blocks.filter(block=>!omitPresentedTable||!visualCoversTable(module,block));
    if(!blocks.length)return '';
    return `<section class="source-section"><h2>${esc(section.heading.replace(/^T[\d.\w–]+(?: and T[\d.]+)? — /,''))}</h2>${blocks.map(block=>block.type==='table'?tableMarkup(module,block):narrativeMarkup(module,block)).join('')}</section>`;
  }).join('');
}
function narrativeMarkup(module,block) {
  const text=block.text.replace(/\n/g,' ');
  return `<section class="finding"><div class="prose">${rich(text)}</div>${sourceFooter(`${module}:${block.line}`)}</section>`;
}
function trendChart(module, metric) {
  const {table,row,key}=findRow(module,'T4.10',metric),unit=data[module].basis.unit;
  const points=[3,2,1].map(i=>({label:table.headers[i],exact:row.cells[i],n:Number(row.cells[i].replace(/,/g,''))}));
  const max=Math.max(...points.map(p=>p.n));
  return `<div class="chart-head"><h3>${esc(metric)}</h3><span>${esc(unit)} · ${esc(row.cells[4])}</span></div><div class="bars" role="group" aria-label="${esc(metric)} by financial year">${points.map(p=>`<button class="bar-column" data-evidence="${key}" aria-label="${esc(p.label)} ${esc(metric)} ${esc(p.exact)} ${esc(unit)}. View source"><span class="bar-value">${p.exact}</span><span class="bar" style="height:${Math.max(2,p.n/max*142)}px"></span><span class="bar-period">${p.label}</span></button>`).join('')}</div>${sourceFooter(key)}`;
}
function performanceView() {
  const id=pins['CP-1'],{table}=findRow(id,'T4.10','Net sales');
  const retainedNotes=sectionData(id,'performance').flatMap(s=>s.blocks.filter(b=>b.type==='text')).map(b=>narrativeMarkup(id,b)).join('');
  return `<div class="section-heading"><h2>Performance</h2><span>${esc(table.headers[3])}–${esc(table.headers[1])}</span></div>${trendChart(id,'Net sales')}<div class="section-heading compact"><h3>Exact financial measures</h3></div>${tableMarkup(id,table)}${retainedNotes}`;
}
function eventTimeline() {
  const id=pins['CP-1A'],section=sectionData(id,'events')[0], block=section.blocks.find(b=>b.type==='table');
  const calendar=block.rows.filter(r=>!r.cells[0].includes('FY')&&!r.cells[0].includes(' / ')&&!r.cells[0].includes(' and '));
  const order={'1993':0,'May 8, 2023':1,'July 12, 2024':2,'September 19, 2024':3,'October 2024':4};
  calendar.sort((a,b)=>order[a.cells[0]]-order[b.cells[0]]);
  const periods=block.rows.filter(r=>!calendar.includes(r));
  const rowMarkup=row=>`<li><div class="event-date"><strong>${esc(row.cells[0])}</strong><span>${/^\d{4}$/.test(row.cells[0])?'Year only':/^\w+ \d{4}$/.test(row.cells[0])?'Month only':row.cells[0].includes('FY')||row.cells[0].includes(' / ')||row.cells[0].includes(' and ')?'Fiscal / combined dates':'Exact day'}</span></div><div class="event-body"><p>${rich(row.cells[1])}</p><div class="event-detail">${rich(row.cells[2])}</div>${sourceFooter(`${id}:${row.line}`)}</div></li>`;
  return `<div class="section-heading"><h2>Issuer event timeline</h2><span>Historical record</span></div><p class="intro">Calendar events retain their actual date precision. Fiscal periods and grouped dates stay in a separate register.</p><ol class="timeline">${calendar.map(rowMarkup).join('')}</ol><h2>Fiscal periods & grouped events</h2><ol class="timeline periods">${periods.map(rowMarkup).join('')}</ol>`;
}
function businessVisual() {
  const row=findRow(pins['CP-1A'],'Company, business','End markets / concentration');
  // Read the mix from the retained cell; a change in the handoff surfaces as a failed view.
  const [,mix,reading]=plain(row.row.cells[1]).match(/(FY2024 sales were[^.]+\.) (.+)$/);
  const parts=[...mix.matchAll(/(\d+)% ([^,.]+?)(?=,|\.)/g)].map(m=>[m[2].replace(/^and /,''),Number(m[1])]),max=Math.max(...parts.map(p=>p[1]));
  return `<div class="section-heading"><h2>Revenue exposure</h2><span>FY2024 · approximate</span></div><div class="mix-bars">${parts.map(([label,n])=>`<div><span>${esc(label)}</span><button data-evidence="${row.key}" aria-label="${esc(label)} approximately ${n} percent, view source"><i style="width:${n/max*100}%"></i></button><strong>≈${n}%</strong></div>`).join('')}</div><p class="chart-reading">${esc(reading)}</p>${sourceFooter(row.key)}`;
}
function factorMatrix() {
  const id=pins['CP-2'],table=sectionData(id,'factors')[0].blocks.find(b=>b.type==='table');
  return `<div class="section-heading"><h2>Six-factor view</h2><span>Qualitative · no composite score</span></div><div class="factor-matrix">${table.rows.map(row=>{
    const grade=plain(row.cells[1]).split(' — ')[0], cls=grade==='Weak'?'adverse':grade==='Not Assessable'?'unknown':'neutral';
    return `<div class="factor"><div><h3>${esc(row.cells[0])}</h3>${sourceLink(`${id}:${row.line}`,'Evidence & rationale')}</div><span class="grade ${cls}">${esc(grade)}</span><p>${rich(row.cells[2])}</p></div>`;
  }).join('')}</div><p class="matrix-note">“Not Assessable” is an evidence limitation, not an adverse grade.</p>`;
}
function downside() {
  const id=pins['CP-2'],block=sectionData(id,'factors')[0].blocks.find(b=>b.text?.startsWith('**Primary downside path:**'));
  return `<div class="downside"><p>${rich(block.text)}</p></div>${sourceFooter(`${id}:${block.line}`)}`;
}
function assessment() {
  const id=pins['CP-2'];
  return `${factorMatrix()}${downside()}${sectionsMarkup(id,sectionData(id,'assessment'))}`;
}
const readerFacts=({confidence,limitation})=>`<dl class="summary-facts"><div><dt>Confidence</dt><dd>${esc(confidence)}</dd></div><div><dt>Main limitation</dt><dd>${rich(limitation)}</dd></div></dl>`;
function callBand(id,section) {
  const {summary,call}=data[id];
  if(section!==modules[id].first||!(summary||call))return '';
  const {text,line}=summary?{text:summary.bottomLine,line:summary.line}:call;
  return `<div class="analysis-call"><p class="call-quote">${rich(text.replace(/\n/g,' '))}</p>${summary?readerFacts(summary):''}</div>${sourceFooter(`${id}:${line}`)}`;
}
function renderContent(id,section) {
  if(!isAnalytical(id))return workspaceView(id,section);
  const band=callBand(id,section);
  if(id===pins['CP-1']&&section==='performance')return band+performanceView();
  if(id===pins['CP-1A']&&section==='events')return band+eventTimeline();
  if(id===pins['CP-2']&&section==='assessment')return band+assessment();
  if(id===pins['CP-8']&&section==='comparison')return band+comparisonView();
  let visual=band+(id===pins['CP-1A']&&section==='business'?businessVisual():id===pins['CP-1']&&section==='cash'?trendChart(id,'Net cash provided by operating activities'):id===pins['CP-2']&&section==='outlook'?downside():'');
  visual+=galleryVisual(id,section)+readerCharts(id,section);
  if(section==='audit')visual+=`<div class="audit-intro"><h2>Original output & technical audit</h2><p>The retained output is available alongside its designed presentation. Analytical acceptance has not been verified by this library.</p><a href="${esc(data[id].href)}" download>Download original handoff</a><p class="hash">SHA-256 ${data[id].sha256}</p></div>`;
  return visual+sectionsMarkup(id,sectionData(id,section),true);
}
function renderSearch(query) {
  if(!query){$('search-results').replaceChildren();return;}
  const context=current.context,has=(...parts)=>parts.join(' ').toLowerCase().includes(query);
  // Default outputs first, so the first hit opens what the module itself opens.
  const isDefault=id=>defaultOutput(data[id].module,context)===id;
  const outputs=Object.keys(data).filter(id=>data[id].run===context).sort((a,b)=>isDefault(b)-isDefault(a));
  const code=id=>data[id].label===data[id].module?moduleNames[data[id].module]:`${moduleNames[data[id].module]} · ${data[id].label}`;
  const sectionOf=(id,heading)=>modules[id].sections.find(s=>s[2].some(p=>matchesHeading(heading,p)))?.[0];
  const href=(id,section,key=null)=>routeHref(data[id].module,section,key,context,data[id].source);
  const hit=(kind,owner,label,target)=>`<a class="search-hit" href="${esc(target)}" aria-label="${esc(`${kind}: ${owner} ${label}`)}"><span class="code">${esc(owner)}</span><span>${esc(label)}</span></a>`;
  const group=(title,total,hits)=>total?`<div class="search-group"><p>${title}${hits.length<total?` · ${hits.length} of ${total}`:''}</p>${hits.join('')}</div>`:'';
  // A row's title can be a bare row number; name the cell that matched unless it is a whole paragraph.
  const itemLabel=item=>{
    const title=plain(item.title),cell=item.fields.map(field=>plain(field[1]??'')).find(value=>has(value));
    return has(title)||!cell||cell.length>80?title:`${title} · ${cell}`;
  };
  const figures=outputs.flatMap(id=>{
    const tables=data[id].sections.filter(s=>s.blocks.some(b=>b.type==='table')),visual=data[id].visual;
    const plotted=visual&&tables.find(s=>s.blocks.some(b=>b.line===visual.table));
    return [...(plotted?[[id,visual.title,plotted.heading]]:[]),...tables.map(s=>[id,plain(s.heading),s.heading])];
  }).filter(([id,label])=>has(label,data[id].module));
  const files=[
    ...outputs.filter(id=>has(data[id].source,data[id].label)).map(id=>hit('Source',code(id),data[id].source,href(id,modules[id].first))),
    ...Object.values(store.inputs).filter(input=>input.run===context&&has(input.source)).map(input=>hit('Source',moduleNames[input.module]||input.module,input.source,routeHref('W-Evidence','sources',null,context))),
  ];
  const items=[...evidence.entries()].filter(([,item])=>item.run===context&&has(item.title,...item.fields.map(field=>field[1]))).sort((a,b)=>outputs.indexOf(a[1].output)-outputs.indexOf(b[1].output));
  $('search-results').innerHTML=group('Figures',figures.length,figures.slice(0,6).map(([id,label,heading])=>hit('Figure',code(id),label,href(id,sectionOf(id,heading)))))
    +group('Sources',files.length+items.length,[...files.slice(0,4),...items.slice(0,4).map(([key,item])=>hit('Reference',code(item.output),itemLabel(item),href(item.output,sectionOf(item.output,item.section),key)))]);
}
function renderNavigator(module) {
  const query=$('module-search').value.trim().toLowerCase(),context=current.context;
  let count=0;
  const sectionsOf=id=>navigationSections(id,context).filter(s=>s[0]!=='status');
  const catalogue=groups.concat([['Workspace tools',[['CP-MODEL','Published model'],['CP-OS','Run activity']]]]).map(([title,items])=>{
    const matches=items.filter(([id,name])=>`${id} ${Object.keys(aliases).filter(k=>aliases[k]===id).join(' ')} ${name} ${sectionsOf(id).map(s=>s[1]).join(' ')} ${isAnalytical(id)?availability(id,context):''}`.toLowerCase().includes(query));
    count+=matches.length;
    if(!matches.length)return '';
    const open=query||matches.some(([id])=>id===module)||(expandedGroups.get(title)??false);
    return `<details class="nav-group" data-group="${esc(title)}" ${open?'open':''}><summary>${esc(title)}</summary>${matches.map(([id,name])=>{
      const section=query&&sectionsOf(id).find(s=>s[1].toLowerCase().includes(query));
      return `<a href="${routeHref(id,section?.[0]||lastSection.get(context+':'+id)||firstSection(id,context))}" title="${esc(id)}" class="module-item ${id===module?'selected':''}" ${id===module?'aria-current="page"':''}><span class="module-label">${esc(name)}</span><span class="module-code"><span>${isAnalytical(id)?availability(id,context):'Run record'}</span></span>${section?`<small>${esc(section[1])}</small>`:''}</a>`;
    }).join('')}</details>`;
  }).join('')+(!count?'<p class="empty">No match. Try another name or topic.</p>':'');
  const analytical=!module.startsWith('W-'),outline=current.output||(Object.hasOwn(modules,module)&&module);
  $('module-list').innerHTML=`<details class="module-catalogue" data-group="catalogue" ${query||!analytical||expandedGroups.get('catalogue')?'open':''}><summary>Browse analysis & tools</summary>${catalogue}</details>${analytical&&!query&&outline?`<div class="outline-heading">${esc(moduleNames[module])} · Section outline</div>${outlineMarkup(outline)}`:''}`;
  nameCodes($('module-list'));
  document.querySelector('.nav-filter').innerHTML=`${query?'Matches':'Analysis & tools'} <span>${count}</span>`;
  renderSearch(query);
}
function parseRoute() {
  const [path,query='']=location.hash.slice(1).split('?');
  const [requestedModule,requestedSection]=path.split('/');
  const resolved=!Object.hasOwn(moduleNames,requestedModule)&&Object.hasOwn(aliases,requestedModule)?aliases[requestedModule]:requestedModule;
  let module=Object.hasOwn(moduleNames,resolved)?resolved:'W-Library';
  const params=new URLSearchParams(query);
  let fallback=data[pins[module]]?.run;
  if(!fallback&&module==='W-Calendar')fallback=calendarRun(requestedSection==='hedges'?'CP-2E':'CP-1A');
  const requestedContext=params.get('c');
  let context=Object.hasOwn(contexts,requestedContext)?requestedContext:fallback||current?.context||Object.keys(contexts)[0]||null;
  // A deliverable opens under a run of its own issuer, or under none if no run file matches.
  const report=module==='W-Reports'&&window.DESIGN_WORKSPACE.reports.find(r=>r.id===requestedSection);
  if(report&&contexts[context]?.issuer!==report.issuer)context=tracedRun(report);
  if(!context&&!appDestinations.has(module)&&module!=='W-Reports')module='W-Library';
  const output=resolveOutput(module,context,params.get('o'));
  const sections=navigationSections(module,context,output),first=output?modules[output].first:modules[module]?.first;
  const selected=sections.find(s=>s[0]===requestedSection)||sections.find(s=>s[0]===first)||sections[0];
  const e=params.get('e'),key=e&&(e.includes(':')?e:`${output}:${e}`),item=evidence.get(key);
  const permitted=item&&item.run===context&&(item.output===output||module==='W-Calendar'||module==='W-Overview');
  const file=output&&output!==defaultOutput(module,context)?data[output].source:null;
  return {module,output,file,section:selected[0],context,evidence:permitted?key:null};
}
function go(module,section,key=null,file) {location.hash=file===undefined?routeHref(module,section,key):routeHref(module,section,key,current?.context,file);}
function showInspector(key) {
  const item=evidence.get(key), output=data[item.output];
  $('inspector').hidden=false; $('workbench').classList.add('has-evidence');
  $('inspector').innerHTML=`<div class="inspector-bar"><button id="back-analysis">${icon('arrow-left')}Back to analysis</button><span>Esc</span></div><div class="inspector-body"><h2>Evidence inspector</h2><div class="evidence-context">${esc(item.module)}${output.label===item.module?'':` · ${esc(output.label)}`} · Line ${item.line}</div><h3>${esc(item.title)}</h3><span class="badge badge-gray classification">${esc(classification(item))}</span><div class="evidence-fields">${item.fields.map(([label,value])=>`<div><h4>${esc(label)}</h4><div>${rich(value)}</div></div>`).join('')}</div>${item.basis?`<div class="evidence-basis"><h3>Basis & context</h3><p>${rich(item.basis)}</p></div>`:''}<div class="source-location"><h3>Source location</h3><p>${esc(item.section)}</p><a href="${esc(output.href)}" download>${icon('file-text')}Download retained handoff</a><p class="small">${esc(output.file)}<br>${esc(output.case)} · saved output</p></div><div class="inspector-note"><strong>Reading boundary</strong><p>These are exact retained fields from this historical case. Source and PDF locators remain attributed to the original handoff. The library does not authenticate the underlying PDFs.</p></div></div>`;
  document.querySelectorAll('[data-evidence]').forEach(el=>el.classList.toggle('source-selected',el.dataset.evidence===key));
  if(returnTrigger) {
    if(window.innerWidth<=1050) $('inspector').scrollIntoView({block:'start'});
    $('back-analysis').focus({preventScroll:true});
  }
}
function moduleBody({module,context,output}) {
  try {
    if(output||!isAnalytical(module))return renderContent(output||module,current.section);
    return moduleEntry(module,context)?.outputs.length?outputChooser(module):unavailableView(module);
  } catch(error) {
    // Documented fail-open: logged, and the reader keeps the new header and the original file.
    console.error(error);
    return `<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>Couldn’t present this output</h2><p>The screen could not render this view. The saved file is unchanged.</p>${output?`<a class="text-action" href="${esc(data[output].href)}" download>Download the original handoff</a>`:''}</div>`;
  }
}
function showNavigator(open) {
  $('navigator').classList.toggle('mobile-open',open);
  $('module-toggle').setAttribute('aria-expanded',String(open));
}
function focusSearch() {
  if(current.module!=='W-Library'&&(appDestinations.has(current.module)||!contexts[current.context])){location.hash='W-Library/cases';renderRoute();}
  if(current.module==='W-Library'){$('library-query').focus();return;}
  showNavigator(true);
  $('module-search').focus();
}
function renderRoute() {
  const next=parseRoute(), previous=current,changed=!current||next.module!==current.module||next.output!==current.output||next.section!==current.section||next.context!==current.context;
  const focused=document.activeElement,focusId=focused?.id,focusHref=focused?.getAttribute('href');
  if(changed&&previous)readingPositions.set(`${previous.context}:${previous.output||previous.module}:${previous.section}`,$('content').scrollTop);
  current=next; lastSection.set(next.context+':'+next.module,next.section);
  if(next.file)lastFile.set(`${next.context}:${next.module}`,next.file);else lastFile.delete(`${next.context}:${next.module}`);
  if(isAnalytical(next.module))lastSection.set(next.context+':module',next.module);
  if(changed) {
    const sections=navigationSections(next.module,next.context,next.output),index=sections.findIndex(s=>s[0]===next.section);
    $('module-head').innerHTML=moduleHead(next);
    // A page with one section already says its name in the heading above.
    const only=sections.length===1&&!isAnalytical(next.module);
    const title=`<h3 id="section-title" tabindex="-1" ${only?'class="sr-only"':''}>${esc(sections[index][1])}</h3>`;
    $('section-nav').innerHTML=only||(isAnalytical(next.module)&&!next.output)?title:`${title}<span>${index+1} / ${sections.length}</span><button id="previous-section" ${index===0?'disabled':''} aria-label="Previous section">${icon('arrow-left')}</button><button id="next-section" ${index===sections.length-1?'disabled':''} aria-label="Next section">${icon('arrow-right')}</button>`;
    if(!showsCodes(next))nameCodes($('section-nav'));
    updateWorkspaceChrome(next.module);
    $('content').innerHTML=moduleBody(next);
    if(!showsCodes(next))nameCodes($('content'));
    $('content').scrollTop=readingPositions.get(`${next.context}:${next.output||next.module}:${next.section}`)||0;
    showNavigator(false);
    renderNavigator(next.module);
    document.title=`${moduleNames[next.module]} · Issuer Library`;
    const creating=next.module==='W-NewRun';
    $('content').hidden=creating;
    $('new-run').hidden=!creating;
    if(previous) {
      const report=isReportRoute(next.module,next.section),library=appDestinations.has(next.module)||!contexts[next.context];
      const restored=!report&&!library&&focusId&&$(focusId);
      const link=window.innerWidth>720&&focused?.classList.contains('section-item')&&focusHref&&[...$('module-list').querySelectorAll('.section-item')].find(el=>el.getAttribute('href')===focusHref);
      const destination=report?$('report-select'):library?$('analysis'):$('section-title');
      if(!creating)(restored&&!restored.disabled?restored:link||destination).focus({preventScroll:true});
      if(previous.module!==next.module||previous.context!==next.context)$('navigator').scrollTop=0;
    }
    if(creating)newRun.show();
  }
  if(next.evidence) showInspector(next.evidence);
  else {
    $('inspector').hidden=true; $('workbench').classList.remove('has-evidence');
    document.querySelectorAll('.source-selected').forEach(el=>el.classList.remove('source-selected'));
    if(previous?.evidence&&!changed) {
      $('content').scrollTop=returnContentScroll;
      if(window.innerWidth<=1050) window.scrollTo(0,returnScroll);
      if(returnTrigger?.isConnected)returnTrigger.focus({preventScroll:true});else $('analysis').focus({preventScroll:true});
    }
  }
  const named=contexts[next.context]?`${contexts[next.context].title}, ${contexts[next.context].run}, `:'';
  $('announcement').textContent=`${named}${moduleNames[next.module]}, ${namedText(navigationSections(next.module,next.context,next.output).find(s=>s[0]===next.section)[1])}${next.evidence?', evidence open':''}`;
}
document.addEventListener('change',event=>{
  if(event.target.matches('[data-library-filter]'))updateLibraryResults();
  if(event.target.id==='report-select')go('W-Reports',event.target.value);
  if(event.target.id==='output-select')go(current.module,current.section,null,event.target.value);
  if(event.target.id==='chart-metric') {
    $('module-visual').innerHTML=comparisonChart(current.output,data[current.output].visual,Number(event.target.value));
    nameCodes($('module-visual'));
    $('chart-metric').focus({preventScroll:true});
  }
});
document.addEventListener('click',event=>{
  if(event.target.closest('#rail-search')){focusSearch();return;}
  const searchHit=event.target.closest('.search-hit');
  if(searchHit){returnTrigger=$('module-search');showNavigator(false);if(searchHit.hash===location.hash)$('analysis').focus();}
  const summary=event.target.closest('summary');
  if(summary?.parentElement.dataset.group)expandedGroups.set(summary.parentElement.dataset.group,!summary.parentElement.open);
  const toggle=event.target.closest('.run-toggle');
  if(toggle){
    const open=toggle.getAttribute('aria-expanded')!=='true',issuer=toggle.closest('tbody').querySelector('h2').textContent;
    if(open)expandedIssuers.add(issuer);else expandedIssuers.delete(issuer);
    toggle.setAttribute('aria-expanded',String(open));toggle.getAttribute('aria-controls').split(' ').forEach(id=>{$(id).hidden=!open;});return;
  }
  const unset=event.target.closest('[data-library-unset]');
  if(unset){const control=$('library-filters').querySelector(`[data-library-filter="${unset.dataset.libraryUnset}"]`);control.value='all';updateLibraryResults();control.focus();return;}
  if(event.target.closest('#library-clear')){
    Object.assign(libraryFilters,LIBRARY_DEFAULTS);
    $('library-filters').querySelectorAll('[data-library-filter]').forEach(control=>{control.value=libraryFilters[control.dataset.libraryFilter];});
    updateLibraryResults();$('library-query').focus();return;
  }
  if(event.target.closest('.skip')){event.preventDefault();if(current.evidence){returnTrigger=$('analysis');go(current.module,current.section);}else $('analysis').focus();return;}
  const source=event.target.closest('[data-evidence]');
  if(source){event.preventDefault();returnTrigger=source;returnScroll=window.scrollY;returnContentScroll=$('content').scrollTop;go(current.module,current.section,source.dataset.evidence);return;}
  if(event.target.closest('#back-analysis'))go(current.module,current.section);
  const moduleLink=event.target.closest('.module-item');
  if(moduleLink){$('module-search').value='';expandedGroups.set('catalogue',false);if(moduleLink.hash===location.hash)renderNavigator(current.module);}
  const step=event.target.closest('#next-section')?1:event.target.closest('#previous-section')?-1:0;
  if(step){const sections=navigationSections(current.module,current.context),index=sections.findIndex(s=>s[0]===current.section);if(sections[index+step])go(current.module,sections[index+step][0]);}
});
document.addEventListener('input',event=>{if(event.target.id==='library-query')updateLibraryResults();});
document.addEventListener('submit',event=>{if(event.target.id==='library-filters')event.preventDefault();});
$('module-search').addEventListener('input',()=>renderNavigator(current.module));
$('module-toggle').addEventListener('click',()=>showNavigator(!$('navigator').classList.contains('mobile-open')));
document.addEventListener('keydown',event=>{
  const target=event.target,unmodified=!event.metaKey&&!event.ctrlKey&&!event.altKey;
  if(event.key==='/'&&unmodified&&!/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)){event.preventDefault();focusSearch();return;}
  const step={ArrowRight:1,ArrowDown:1,ArrowLeft:-1,ArrowUp:-1}[event.key];
  if(step&&unmodified) {
    const mark=target.closest?.('[data-evidence]'),chart=mark?.closest('.bars,.mix-bars,.horizontal-chart,.hedge-chart,.vector-chart');
    if(!chart)return;
    const marks=[...chart.querySelectorAll('[data-evidence]')],next=marks[marks.indexOf(mark)+step];
    if(next){next.focus();event.preventDefault();}
    return;
  }
  if(event.key!=='Escape')return;
  // One layer at a time: the search text, then the inspector, then the narrow-screen navigator.
  if(target.matches?.('#module-search,#library-query')&&target.value){event.preventDefault();target.value='';target.dispatchEvent(new Event('input',{bubbles:true}));return;}
  if(current.evidence){event.preventDefault();go(current.module,current.section);return;}
  if($('navigator').classList.contains('mobile-open')){showNavigator(false);$('module-toggle').focus();}
});
window.addEventListener('hashchange',renderRoute);
const newRun=installNewRun();
installSettings();
renderRoute();
