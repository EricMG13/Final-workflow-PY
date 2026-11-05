/* Presentation views. No analytical execution. */
function installDestinations() {
  const title = h => h.replace(/^T[\w.]+(?:\s*[–/]\s*(?:T[\w.]+|\d+))*\s*[—–]\s*/,'').replace(/^./,s=>s.toUpperCase());
  for (const [id,out] of Object.entries(data)) {
    if(modules[id]) continue;
    const sections=[];
    const audit=[];
    for(const s of out.sections.filter(s=>s.blocks.length)) {
      if(/^(Request|Calculations|Next module)/.test(s.heading)) {audit.push('='+s.heading);continue;}
      sections.push(['s'+s.line,title(s.heading),['='+s.heading]]);
    }
    const first=out.firstHeading&&out.sections.find(s=>s.heading.startsWith(out.firstHeading));
    const rank=s=>s[0]==='s'+first?.line?-1:s[1]==='Sources'?1:0;
    sections.sort((a,b)=>rank(a)-rank(b));
    sections.push(['audit','Technical audit',audit]);
    modules[id]={name:moduleNames[out.module],subtitle:out.scope,first:first?'s'+first.line:sections[0][0],sections};
  }
  const destinations={
    'W-Library':['Issuer library','Find a run or start a new one',[['cases','Issuer cases',[]]]],
    'W-Overview':['Summary','The bottom line, charts and findings for this run',[['overview','Summary',[]]]],
    'W-Calendar':['Event calendar','Dates, precision and analytical ownership stay together',[['unavailable','Calendar availability',[]]]],
    'W-Reports':['Deliverables','Reports and their files, traced to the handoffs they were built from',[['list','Deliverables',[]]]],
    'W-Evidence':['Evidence library','Retained handoffs and their source identities',[['sources','Retained outputs',[]]]],
    'CP-MODEL':['Published model','Financial publication and definition controls',[['publication','Publication state',[]],['inputs','Model inputs',[]]]],
    'CP-OS':['Run activity','Retained artifacts and delivery scope',[['activity','Run record',[]],['delivery','Delivery scope',[]]]],
    'W-NewRun':['New run','Context, issuer folder and budget, review, then an explicit start',[['run','New run',[]]]],
    'W-Settings':['Settings','Workspace folder and library controls',[['workspace','Workspace',[]]]],
    'W-Help':['Help','Using the library',[['help','Using the library',[]],['visuals','Visualisation coverage',[]]]]
  };
  for(const [id,[name,subtitle,sections]] of Object.entries(destinations)) {
    modules[id]={name,subtitle,sections,first:sections[0][0]};
    moduleNames[id]=name;
    data[id]={sections:[]};
  }
}

const moduleEntry=(module,context)=>contexts[context]?.modules[module];
const defaultOutput=(module,context)=>moduleEntry(module,context)?.default??null;
function resolveOutput(module,context,file) {
  const entry=moduleEntry(module,context);
  return entry?.outputs.find(id=>data[id].source===file)||entry?.default||null;
}
function availability(module,context) {
  const entry=moduleEntry(module,context);
  return !entry?'No output found':entry.outputs.length?'Output available':'Inputs only';
}
const contextModules=context=>Object.keys(contexts[context].modules).filter(id=>contexts[context].modules[id].outputs.length);
const outputCount=context=>contextModules(context).reduce((sum,id)=>sum+contexts[context].modules[id].outputs.length,0);
const issuerReports=context=>window.DESIGN_WORKSPACE.reports.filter(r=>!context||r.issuer===contexts[context].issuer);
const reportsBuiltFrom=context=>window.DESIGN_WORKSPACE.reports.filter(r=>r.builtFrom.some(b=>b.run===context));
const reportsUsing=output=>window.DESIGN_WORKSPACE.reports.filter(r=>r.builtFrom.some(b=>b.source===output));
const tracedRun=report=>report.builtFrom.find(b=>b.run)?.run||null;
const reportName=report=>report.build?`Build ${report.build} · ${report.label}`:report.label;
const isReportRoute=(module,section)=>module==='W-Reports'&&window.DESIGN_WORKSPACE.reports.some(r=>r.id===section);
function firstSection(module,context) {
  const output=defaultOutput(module,context);
  return output?modules[output].first:navigationSections(module,context)[0][0];
}
const plural=(n,word)=>`${n} ${word}${n===1?'':'s'}`;
function moduleHead({module,context,output}) {
  const files=moduleEntry(module,context)?.outputs||[],out=output&&data[output];
  const meta=!out?'':files.length>1?`<label class="output-meta output-select">Saved output <select id="output-select">${files.map(id=>`<option value="${esc(data[id].source)}" ${id===output?'selected':''}>${esc(data[id].label)}</option>`).join('')}</select></label>`:`<span class="output-meta">Saved output${out.label===module?'':` · ${esc(out.label)}`}</span>`;
  const used=output?reportsUsing(output):[];
  const usedIn=used.length===1?`<a class="output-meta" href="${routeHref('W-Reports',used[0].id)}">Used in ${esc(reportName(used[0]))}</a>`:used.length?`<a class="output-meta" href="${routeHref('W-Reports','list')}">Used in ${used.length} deliverables</a>`:'';
  const flag=out?.parseError?`<span class="output-meta">Shown unstructured: ${esc(out.parseError)}</span>`:'';
  return `<div class="module-title"><h2 ${module.startsWith('W-')?'':`title="${esc(module)}"`}>${esc(moduleNames[module])}</h2>${meta}${usedIn}${flag}</div>`;
}
function fixtureTable(module,line) {
  const table=data[module].sections.flatMap(s=>s.blocks).find(b=>b.type==='table'&&b.line===line);
  if(!table)throw new Error(`Missing visual table ${module}:${line}`);
  return table;
}
function chartNumber(value) {
  const clean=plain(value).trim().replace(/,/g,'');
  if(!/^(?:[-+]?\d+(?:\.\d+)?|\(\d+(?:\.\d+)?\))(?:%|x)?$/.test(clean))return null;
  const number=Number(clean.replace(/[()%x]/g,''))*(clean.startsWith('(')?-1:1);
  return Number.isFinite(number)?number:null;
}
function chartIntro(id,v) {
  return `<div class="section-heading"><h2>${esc(v.title)}</h2>${v.unit?`<span>${esc(v.unit)}</span>`:''}</div>${v.quote?`<p class="chart-reading">${rich(v.quote.text.replace(/\n/g,' '))}</p>${sourceFooter(`${id}:${v.quote.line}`)}`:''}`;
}
const evidenceHref=(id,line)=>routeHref(data[id].module,current?.output===id?current.section:modules[id].first,`${id}:${line}`,data[id].run);
function comparisonChart(module,v,selection=0) {
  const table=fixtureTable(module,v.table),selected=table.rows[v.rows?.[selection]??0];
  const selectable=['paired','peers'].includes(v.kind)&&!['CP-4C','CP-2A'].includes(data[module].module);
  const rows=selectable?[selected]:(v.rows||table.rows.map((_,i)=>i)).map(i=>table.rows[i]);
  const points=v.kind==='peers'?v.columns.map(c=>({label:table.headers[c],value:selected.cells[c],row:selected,series:0})):rows.flatMap(row=>(v.columns||[v.column]).map((c,i)=>({label:plain(row.cells[0]),series:i,value:row.cells[c],row,column:c})));
  const max=Math.max(1,...points.map(p=>Math.abs(chartNumber(p.value)??0)));
  const hasNegative=points.some(p=>(chartNumber(p.value)??0)<0);
  const legend=v.columns&&v.kind!=='peers'?`<div class="chart-legend">${v.columns.map((c,i)=>`<span><i class="series-${i}"></i>${esc(table.headers[c])}</span>`).join('')}</div>`:'';
  return `${chartIntro(module,v)}${selectable&&!v.fixed?`<label class="metric-control">Measure <select id="chart-metric">${v.rows.map((idx,i)=>`<option value="${i}" ${i===selection?'selected':''}>${esc(plain(table.rows[idx].cells[0]))}</option>`).join('')}</select></label>`:''}${legend}<div class="horizontal-chart ${hasNegative?'diverging':''}">${points.map(p=>{
    const n=chartNumber(p.value),width=n===null?0:Math.abs(n)/max*100;
    return `<button class="chart-row" data-evidence="${module}:${p.row.line}"><span class="chart-label">${esc(p.label)}${v.columns&&v.kind!=='peers'?`<small>${esc(table.headers[p.column])}</small>`:''}</span><span class="track ${n===null?'missing':''}">${hasNegative?`<span class="zero-rule"></span><i class="series-${p.series} ${n<0?'negative':''}" style="left:${n<0?50-width/2:50}%;width:${width/2}%"></i>`:`<i class="series-${p.series}" style="width:${width}%"></i>`}</span><strong>${n===null?'Not available':esc(p.value)}</strong></button>`;
  }).join('')}</div><p class="matrix-note">Select a plotted row to inspect its exact source fields. Missing values have no bar.</p>`;
}
function bridgeChart(module,v) {
  const table=fixtureTable(module,v.table),rows=(v.rows||table.rows.map((_,i)=>i)).map(i=>table.rows[i]);
  let running=0;
  const points=rows.map((row,i)=>{
    const amount=chartNumber(row.cells[v.amount]);
    if(amount===null)throw new Error('Non-numeric bridge input');
    const isTotal=i===0||(v.kind==='waterfall'&&i===rows.length-1);
    const start=isTotal?0:running;
    running=isTotal?amount:running+amount;
    if(v.total!==undefined&&Math.abs(running-chartNumber(row.cells[v.total]))>.001)throw new Error('Retained bridge does not reconcile');
    return {row,start,end:running,total:isTotal,amount};
  });
  if(v.total!==undefined) {
    const row=rows.at(-1),closing=chartNumber(row.cells[v.total]);
    points.push({row,start:0,end:closing,total:true,amount:closing,display:row.cells[v.total],label:'Issuer As Defined EBITDA'});
  }
  const max=Math.max(...points.map(p=>Math.max(p.start,p.end)))*1.16;
  const width=660,height=210,step=width/points.length,y=n=>height-n/max*height;
  return `${chartIntro(module,v)}<div class="vector-chart"><svg viewBox="-5 -12 680 270" role="group" aria-label="${esc(v.title)}. Select a movement to inspect its source."><line x1="0" y1="210" x2="660" y2="210" class="axis"/>${points.map((p,i)=>`<a class="plot-point" href="${evidenceHref(module,p.row.line)}" data-evidence="${module}:${p.row.line}" aria-label="${esc(p.label||plain(p.row.cells[0]))}, ${esc(p.display??p.row.cells[v.amount])} ${esc(v.unit)}. View source"><title>${esc(p.label||plain(p.row.cells[0]))}: ${esc(p.display??p.row.cells[v.amount])}</title><rect class="${p.total?'total':p.amount<0?'outflow':'movement'}" x="${i*step+10}" y="${y(Math.max(p.start,p.end))}" width="${step-20}" height="${Math.max(1,Math.abs(y(p.end)-y(p.start)))}"/><text x="${i*step+step/2}" y="${y(Math.max(p.start,p.end))-8}" text-anchor="middle">${esc(p.display??p.row.cells[v.amount])}</text><text class="axis-label" x="${i*step+step/2}" y="232" text-anchor="middle">${i+1}</text>${i<points.length-1?`<line class="connector" x1="${i*step+step-10}" y1="${y(p.end)}" x2="${(i+1)*step+10}" y2="${y(p.end)}"/>`:''}</a>`).join('')}</svg></div><div class="bridge-key">${points.map((p,i)=>`<span><b>${i+1}</b>${sourceLink(`${module}:${p.row.line}`,p.label||plain(p.row.cells[0]))}<span class="row-classification">${esc(classification(evidence.get(`${module}:${p.row.line}`)))}</span></span>`).join('')}</div>`;
}
function pathChart(module,v) {
  const table=fixtureTable(module,v.table),series=['Reference','Downside','Upside'];
  const values=table.rows.map(r=>chartNumber(r.cells[v.column]));
  if(values.some(n=>n===null))throw new Error('Missing conditional path value');
  const max=Math.max(...values)*1.13, y=n=>200-n/max*175;
  return `${chartIntro(module,v)}<div class="chart-legend path-legend">${series.map((s,i)=>`<span><i class="path-key-${i}"></i>${s}</span>`).join('')}<span>Dashed paths · conditional scenarios</span></div><div class="vector-chart"><svg viewBox="0 0 670 250" role="group" aria-label="Closing cash across FY2025 to FY2027. Select a point to inspect its exact source.">${[0,2000,4000,6000].map(n=>`<line class="gridline" x1="65" x2="600" y1="${y(n)}" y2="${y(n)}"/><text class="axis-label" x="55" y="${y(n)+4}" text-anchor="end">${n.toLocaleString('en-US')}</text>`).join('')}${series.map((name,i)=>{
    const rows=table.rows.filter(r=>r.cells[0].startsWith(name+' / '));
    return `<polyline class="path-${i}" fill="none" stroke-dasharray="${['5 4','2 4','9 4'][i]}" points="${rows.map((r,j)=>`${90+j*235},${y(chartNumber(r.cells[v.column]))}`).join(' ')}"/>${rows.map((r,j)=>`<a class="plot-point" href="${evidenceHref(module,r.line)}" data-evidence="${module}:${r.line}" aria-label="${esc(r.cells[0])}, closing cash ${esc(r.cells[v.column])} ${esc(v.unit)}. View source"><title>${esc(r.cells[0])}: ${esc(r.cells[v.column])} ${esc(v.unit)}</title><circle class="point-hit" cx="${90+j*235}" cy="${y(chartNumber(r.cells[v.column]))}" r="12"/><circle class="point-${i}" cx="${90+j*235}" cy="${y(chartNumber(r.cells[v.column]))}" r="4"/></a>`).join('')}`;
  }).join('')}${['2025','2026','2027'].map((year,i)=>`<text class="axis-label" x="${90+i*235}" y="230" text-anchor="middle">FY${year}</text>`).join('')}</svg></div><div class="path-readout">${series.map(name=>{const r=table.rows.find(r=>r.cells[0]===name+' / 2027');return `<div><span>${name} · FY2027</span><strong>${esc(r.cells[v.column])}</strong>${sourceFooter(`${module}:${r.line}`)}</div>`;}).join('')}</div>`;
}
function hedgeChart(module,v) {
  const table=fixtureTable(module,v.table),start=Date.UTC(2023,2,31),end=Date.UTC(2027,8,30),position=date=>(Date.parse(date)-start)/(end-start)*100;
  return `${chartIntro(module,v)}<div class="hedge-axis"><span style="left:0">Mar 2023</span><span style="left:${position('2024-09-30')}%">Sep 2024 base</span><span style="left:100%">Sep 2027</span></div><div class="hedge-chart">${table.rows.map(row=>{
    const dates=row.cells[2].match(/\d{4}-\d{2}-\d{2}/g),dated=dates?.length===2,forward=dated&&dates[0]>'2024-09-30';
    return `<button class="hedge-row" data-evidence="${module}:${row.line}"><span>${esc(row.cells[0])}<small>${esc(row.cells[1])} ${row.cells[0]==='FX forwards'?'':'USDm'}</small></span><span class="hedge-lane"><i class="base-rule" style="left:${position('2024-09-30')}%"></i>${dated?`<i class="hedge-span ${forward?'future':''}" style="left:${position(dates[0])}%;width:${position(dates[1])-position(dates[0])}%"></i>`:'<span class="duration-only">Duration only · ≤12 months</span>'}</span><span class="hedge-dates">${dated?esc(dates.join(' → ')):esc(row.cells[2])}<small>${forward?'Forward starting at base date':dated?'Active at base date':'No exact expiry supplied'}</small></span></button>`;
  }).join('')}</div><p class="matrix-note">Solid: active at the historical base. Outlined: starts after the base.</p>`;
}
function qualitativeVisual(module,v) {
  const table=fixtureTable(module,v.table);
  if(v.kind==='debate')return `${chartIntro(module,v)}<div class="debates">${table.rows.map(r=>`<section class="debate"><header><h3>${rich(r.cells[0])}</h3><span class="grade unknown">${rich(r.cells[3])}</span></header><div class="arguments"><div><h4>Bull position</h4><p>${rich(r.cells[1])}</p></div><div><h4>Bear position</h4><p>${rich(r.cells[2])}</p></div></div><p class="resolution">${rich(r.cells[4])}</p>${sourceFooter(`${module}:${r.line}`)}</section>`).join('')}</div>`;
  if(v.kind==='agencies')return `${chartIntro(module,v)}<div class="agency-pair">${table.rows.map(r=>`<section><h3>${esc(r.cells[0])}</h3><p class="rating">${rich(r.cells[1])}</p><h4>Proposed issue</h4><p>${rich(r.cells[2])}</p><p class="matrix-note">${rich(r.cells[3])}</p>${sourceFooter(`${module}:${r.line}`)}</section>`).join('')}</div>`;
  return `${chartIntro(module,v)}<div class="qual-matrix">${table.rows.map(row=>`<section><h3>${rich(row.cells[v.columns[0]])}</h3><div>${v.columns.slice(1).map(c=>`<div><h4>${esc(table.headers[c])}</h4><p>${rich(row.cells[c])}</p></div>`).join('')}${sourceFooter(`${module}:${row.line}`)}</div></section>`).join('')}</div>`;
}
const CHART_RENDERERS={paired:comparisonChart,peers:comparisonChart,bars:comparisonChart,bridge:bridgeChart,waterfall:bridgeChart,paths:pathChart,hedges:hedgeChart};
const visualMarkup=(module,v)=>(CHART_RENDERERS[v.kind]||qualitativeVisual)(module,v);
function galleryVisual(module,section) {
  const out=data[module],v=out.visual;
  if(!v||!sectionData(module,section).some(s=>s.blocks.some(b=>b.line===v.table)))return '';
  return `<div id="module-visual">${visualMarkup(module,v)}</div>${visualCoversTable(module,fixtureTable(module,v.table))?'':'<div class="section-heading compact"><h2>Complete findings & exact data</h2><span>Retained output</span></div>'}`;
}
function visualCoversTable(module,block) {
  const v=data[module].visual;
  return block.type==='table'&&v?.table===block.line&&(['agencies','debate'].includes(v.kind)||(v.kind==='matrix'&&new Set(v.columns).size===block.headers.length));
}
function comparisonView() {
  const id=pins['CP-8'],run=data[id].run,compare=data[id].compare,recheck=data[compare.recheck];
  const parts=heading=>sectionData(id,'comparison').find(s=>s.heading.startsWith(heading)).blocks;
  const tableOf=heading=>parts(heading).find(b=>b.type==='table'),notes=heading=>parts(heading).filter(b=>b.type==='text').map(b=>narrativeMarkup(id,b)).join('');
  const reportLink=reportId=>`<a class="text-action" href="${routeHref('W-Reports',reportId,null,run)}">${esc(reportName(window.DESIGN_WORKSPACE.reports.find(r=>r.id===reportId)))}${icon('arrow-right')}</a>`;
  const field=(table,row,i)=>`<div class="record-field"><h4>${esc(table.headers[i])}</h4><div>${rich(row.cells[i])}</div></div>`;
  const quoted=(blocks,pattern)=>blocks.filter(b=>b.type==='text').map(b=>b.text.replace(/\n/g,' ').match(pattern)?.[0]).find(Boolean);
  const heading=(title,count)=>`<div class="section-heading compact"><h2>${esc(title)}</h2><span>${count}</span></div>`;
  const changes=tableOf('All five report sections'),material=tableOf('Material analytical changes'),regressions=tableOf('Unresolved regressions');
  const recheckFindings=recheck.sections.find(s=>s.heading==='Findings').blocks,recheckRows=recheckFindings.find(b=>b.type==='table').rows;
  const recheckHref=routeHref('CP-8',modules[recheck.id].first,null,run,recheck.source);
  return `<div class="comparison-pair"><div><span>Prior</span>${reportLink(compare.prior)}</div><div><span>Current</span>${reportLink(compare.current)}</div><p>${esc(quoted(data[id].sections.find(s=>s.heading==='Request').blocks,/“Current” means[^.]+\./))}</p></div>${notes('Findings')}
  ${heading('All five report sections','Prior → current')}${changes.rows.map(row=>{
    const word=plain(row.cells[1]).match(/^(Unchanged|Revised)/)[1];
    return `<section class="debate change-row"><header><h3>${rich(row.cells[0])}</h3><span class="grade ${word==='Unchanged'?'unknown':'neutral'}">${word}</span></header>${[1,2,3].map(i=>field(changes,row,i)).join('')}${sourceFooter(`${id}:${row.line}`)}</section>`;
  }).join('')}
  ${heading('Material analytical changes','Prior and current deliverable')}${material.rows.map(row=>`<section class="debate"><header><h3>${rich(row.cells[0])}</h3></header><div class="arguments">${[1,2].map(i=>`<div><h4>${esc(material.headers[i])}</h4><p>${rich(row.cells[i])}</p></div>`).join('')}</div>${field(material,row,3)}${field(material,row,4)}${sourceFooter(`${id}:${row.line}`)}</section>`).join('')}
  ${heading('Unresolved regressions to repair','Requested from CP-2')}<div class="recheck"><p>${esc(quoted(recheckFindings,/RC-1\/2\/3 are closed[^.]+\./))}</p><a class="text-action" href="${recheckHref}">Read the recheck${icon('arrow-right')}</a>${reportLink(compare.repaired)}</div>${regressions.rows.map(row=>{
    const after=recheckRows.find(r=>plain(r.cells[0]).startsWith(plain(row.cells[0]).split(' ')[0]));
    return `<section class="debate regression-row"><header><h3>${rich(row.cells[0])}</h3><span class="grade neutral">${esc(plain(after.cells[2]))}</span></header>${field(regressions,row,1)}${field(regressions,row,2)}<div class="record-field"><h4>Recheck · ${esc(recheckFindings.find(b=>b.type==='table').headers[1])}</h4><div>${rich(after.cells[1])}</div></div>${sourceFooter(`${id}:${row.line}`)}</section>`;
  }).join('')}${notes('Unresolved regressions')}`;
}
function visualPlan(module) {
  const rows=window.DESIGN_WORKSPACE.visuals.filter(v=>v.module===module);
  return `<details class="visual-plan"><summary>Visualisation plan · ${rows.length} specified views</summary>${rows.map(v=>`<section><h3>${esc(v.title)}</h3><span class="tag">${esc(v.form)}</span><p>${esc(v.guard)}</p><small>Required inputs: ${esc(v.inputs)}</small></section>`).join('')}</details>`;
}
function routeHref(module,section,key=null,context=current?.context,file=lastFile.get(`${context}:${module}`)) {
  const params=new URLSearchParams();
  if(context)params.set('c',context);
  if(file&&`${contexts[context].folder}/${file}`!==defaultOutput(module,context))params.set('o',file);
  if(key)params.set('e',key);
  return `#${module}/${section}${params.size?'?'+params:''}`;
}
function sectionGroups(id) {
  const result=new Map(),module=data[id].module;
  for(const section of modules[id].sections) {
    const [sectionId,label,prefixes]=section,heading=prefixes.join(' ');
    let group='Findings & analysis';
    if(sectionId==='audit'||/^(Sources|Scope &|Evidence &|Definitions & periods|Source register)/.test(label))group='Evidence & audit';
    else if(/gap|limit|monitor|follow-up|readiness/i.test(label))group='Limits & monitoring';
    else if(module==='CP-2E')group=heading.includes('T2G.')?'ESG & credit effects':heading.includes('T2F.')?'Rates, FX & hedges':'Credit conclusion';
    else if(module==='CP-1D')group=heading.includes('T1E.')?'Debt & obligations':'Earnings quality';
    else if(module==='CP-5')group=heading.includes('T5B.')?'Evidence lineage':'Validation & remediation';
    if(!result.has(group))result.set(group,[]);
    result.get(group).push(section);
  }
  return [...result];
}
function outlineMarkup(id) {
  const module=data[id].module||id;
  return `<div class="section-outline" aria-label="${esc(moduleNames[module])} sections">${sectionGroups(id).map(([group,sections])=>{
    const key=`${id}:${group}`,open=expandedGroups.get(key)??true;
    return `<details class="outline-group" data-group="${esc(key)}" ${open?'open':''}><summary>${esc(group)}</summary>${sections.map(([sectionId,label])=>`<a class="section-item" href="${routeHref(module,sectionId)}" ${current.section===sectionId?'aria-current="location"':''}>${esc(label)}</a>`).join('')}</details>`;
  }).join('')}</div>`;
}
function unavailableView(module) {
  const ctx=contexts[current.context],entry=moduleEntry(module,current.context),label=availability(module,current.context);
  const others=Object.entries(contexts).filter(([key,run])=>key!==current.context&&run.issuer===ctx.issuer&&run.modules[module]?.outputs.length);
  const given=(entry?.inputs||[]).map(id=>store.inputs[id]);
  return `<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>${label}</h2><p>${esc(ctx.title)} · ${esc(ctx.run)} remains selected. ${entry?`This run keeps ${plural(given.length,'input file')} for ${esc(moduleNames[module])} and no saved output.`:`No ${esc(moduleNames[module])} output file was found in this run. That alone does not show the module was not run or not applicable.`}</p>${given.map(f=>`<p><a href="${esc(f.href)}" download>${esc(f.source)}</a></p>`).join('')}</div>${others.length?`<div class="available-case"><h3>Other ${esc(ctx.issuer)} runs with this module</h3>${others.map(([key,run])=>`<p><a class="text-action" href="${routeHref(module,firstSection(module,key),null,key)}">${esc(run.run)}${icon('arrow-right')}</a></p>`).join('')}</div>`:''}${visualPlan(module)}`;
}
function outputChooser(module) {
  const ctx=contexts[current.context],files=moduleEntry(module,current.context).outputs;
  return `<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>Choose a saved output</h2><p>${esc(ctx.run)} keeps ${files.length} ${esc(moduleNames[module])} outputs. None is marked as the primary one.</p></div><div class="output-choices">${files.map(id=>`<a class="text-action" href="${routeHref(module,modules[id].first,null,current.context,data[id].source)}">${esc(data[id].label)}${icon('arrow-right')}</a>`).join('')}</div>`;
}
// The calendar reads two curated tables; a run has one only if it holds that pinned output.
const calendarRun=module=>data[pins[module]]?.run;
function calendarSections(context) {
  return context===calendarRun('CP-1A')?[['tdg','Issuer events',[]]]:context===calendarRun('CP-2E')?[['hedges','Hedge schedule',[]]]:[['unavailable','Calendar availability',[]]];
}
function reportSections(context) {
  const reports=issuerReports(context);
  return reports.length?[['list','Deliverables',[]],...reports.map(r=>[r.id,reportName(r),[]])]:[['none','Report availability',[]]];
}
function navigationSections(module,context,output=defaultOutput(module,context)) {
  if(module==='W-Calendar')return calendarSections(context);
  if(module==='W-Evidence')return [['sources','Retained outputs',[]]];
  if(module==='W-Reports')return reportSections(context);
  if(Object.hasOwn(modules,module))return modules[module].sections;
  if(output)return modules[output].sections;
  return [['status',moduleEntry(module,context)?.outputs.length?'Choose a saved output':availability(module,context),[]]];
}
function moduleLink(id,label){return `<a class="text-action" href="${routeHref(id,lastSection.get(current?.context+':'+id)||firstSection(id,current?.context))}">${esc(label||moduleNames[id])}${icon('arrow-right')}</a>`;}
function sourceInventory(context) {
  const identity=f=>`<details><summary>File identity</summary><p>${esc(f.file)}</p><p class="hash">SHA-256 ${f.sha256}</p></details>`;
  const rows=Object.entries(contexts[context].modules).flatMap(([module,entry])=>[
    ...entry.outputs.map(id=>{const out=data[id];return `<section><div><h3>${module} · ${esc(moduleNames[module])}</h3><p>${esc(out.label)} · ${esc(out.case)} · ${esc(out.period)}</p><span class="tag">Saved output</span>${out.scope==='Retained module output'?'':` <span class="tag">${esc(out.scope)}</span>`}</div><div><a class="text-action" href="${routeHref(module,modules[id].first,null,context,out.source)}">Open output${icon('arrow-right')}</a><a href="${esc(out.href)}" download>Original handoff</a></div>${identity(out)}</section>`;}),
    ...entry.inputs.map(id=>{const f=store.inputs[id];return `<section><div><h3>${module} · ${esc(moduleNames[module])}</h3><p>${esc(f.source)}</p><span class="tag">Input</span></div><div><a href="${esc(f.href)}" download>Original file</a></div>${identity(f)}</section>`;})
  ]);
  return `<div class="source-inventory">${rows.join('')}</div>`;
}
function libraryRecords() {
  return Object.entries(contexts).map(([key,run])=>({key,issuer:run.issuer,sector:run.sector,run:run.run,period:run.period,first:run.first,modules:contextModules(key),outputs:outputCount(key),reports:reportsBuiltFrom(key).map(r=>r.id)}));
}
function filterLibrary(records,filters) {
  const terms=filters.query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return records.filter(record=>{
    if(filters.sector!=='all'&&record.sector!==filters.sector)return false;
    if(filters.content==='reports'&&!record.reports.length)return false;
    if(filters.content==='modules'&&!record.outputs)return false;
    if(filters.module!=='all'&&!record.modules.includes(filters.module))return false;
    const searchable=`${record.issuer} ${record.key} ${record.run} ${record.period} ${record.sector} ${record.modules.join(' ')}`.toLowerCase();
    return terms.every(term=>searchable.includes(term));
  });
}
function libraryCount(records) {
  const issuers=new Set(records.map(r=>r.issuer)).size,reports=new Set(records.flatMap(r=>r.reports)).size;
  return `${plural(issuers,'issuer')} · ${plural(records.length,'run')} · ${plural(reports,'report')}`;
}
function libraryResults(records) {
  if(!Object.keys(contexts).length)return `<div class="library-empty"><h2>No runs in this workspace yet</h2><p>Start a new run, or choose another workspace folder in Settings.</p><a class="text-action" href="#W-Settings/workspace">Open Settings${icon('arrow-right')}</a></div>`;
  if(!records.length)return '<div class="library-empty"><h2>No matching issuers or runs</h2><p>Try a shorter issuer name, another sector or a different content selection. Clear filters to see all retained cases.</p></div>';
  return `<div class="case-list">${[...new Set(records.map(r=>r.issuer))].map(issuer=>{
    const matches=records.filter(r=>r.issuer===issuer);
    return `<section><div><h2>${esc(issuer)}</h2><p>${esc(matches[0].sector)} · separate runs</p></div><div class="run-list">${matches.map(record=>`<a href="${routeHref('W-Overview','overview',null,record.key)}"><strong>${esc(record.run)}</strong><span>${esc(record.period)}</span><small>${plural(record.modules.length,'module')} · ${plural(record.outputs,'saved output')} · ${plural(record.reports.length,'report')}</small>${icon('arrow-right')}</a>`).join('')}</div></section>`;
  }).join('')}</div>`;
}
function libraryView() {
  const records=libraryRecords(),matches=filterLibrary(records,libraryFilters);
  const options=(items,value)=>items.map(([key,label])=>`<option value="${esc(key)}" ${value===key?'selected':''}>${esc(label)}</option>`).join('');
  const retainedModules=groups.flatMap(g=>g[1]).filter(([id])=>records.some(r=>r.modules.includes(id)));
  const active=libraryFilters.query!==''||['sector','content','module'].some(key=>libraryFilters[key]!=='all');
  return `<div class="library-discovery"><div class="library-actions"><p class="intro">Find an issuer or retained run, then read its findings, visuals and evidence together.</p><a class="primary-action" id="library-new-run" href="#W-NewRun/run">${icon('plus')}New run</a></div><form id="library-filters" class="library-filters" role="search" aria-label="Filter issuer library"><label class="library-search">Search issuers or runs<span>${icon('search')}<input id="library-query" data-library-filter="query" type="search" value="${esc(libraryFilters.query)}" placeholder="Issuer name, run ID or year" autocomplete="off" aria-controls="library-results"></span></label><label>Sector<select data-library-filter="sector" aria-controls="library-results">${options([['all','All sectors'],...[...new Set(records.map(r=>r.sector))].map(s=>[s,s])],libraryFilters.sector)}</select></label><label>Available content<select data-library-filter="content" aria-controls="library-results">${options([['all','All content'],['modules','Module outputs'],['reports','Saved reports']],libraryFilters.content)}</select></label><label>Contains module<select data-library-filter="module" aria-controls="library-results">${options([['all','Any module'],...retainedModules.map(([id,name])=>[id,`${id} · ${name}`])],libraryFilters.module)}</select></label><button id="library-clear" type="button" ${active?'':'disabled'}>Clear filters</button></form><div class="library-result-meta"><p id="library-count" role="status" aria-live="polite">${libraryCount(matches)}</p><a class="text-action" href="#W-Reports/list">All deliverables${icon('arrow-right')}</a></div></div><div id="library-results">${libraryResults(matches)}</div><p class="matrix-note">Missing observations are not zero. Comparable credit metrics and completeness scores are not available across these retained examples.</p>`;
}
function updateLibraryResults() {
  $('library-filters').querySelectorAll('[data-library-filter]').forEach(control=>{libraryFilters[control.dataset.libraryFilter]=control.value;});
  const records=filterLibrary(libraryRecords(),libraryFilters);
  $('library-results').innerHTML=libraryResults(records);
  $('library-count').textContent=libraryCount(records);
  $('library-clear').disabled=!libraryFilters.query&&['sector','content','module'].every(key=>libraryFilters[key]==='all');
}
function reportList(context) {
  const ctx=contexts[context],all=window.DESIGN_WORKSPACE.reports,built=reportsBuiltFrom(context),others=ctx?issuerReports(context).filter(r=>!built.includes(r)):[];
  const rest=all.filter(r=>!built.includes(r)&&!others.includes(r));
  const none='No report was built from this run’s files (checked by SHA-256)';
  const runsOf=r=>[...new Set(r.builtFrom.filter(b=>b.run).map(b=>contexts[b.run].run))];
  const row=r=>`<li class="report-row"><a class="text-action" href="${routeHref('W-Reports',r.id,null,ctx&&r.issuer===ctx.issuer?context:tracedRun(r))}">${esc(reportName(r))}${icon('arrow-right')}</a>${r.status?`<span class="tag">${esc(r.status)}</span>`:''}<small>${runsOf(r).length?`Uses ${runsOf(r).map(esc).join(', ')}`:'No matching run file'}</small></li>`;
  const list=(cls,title,reports)=>reports.length?`<section class="${cls}"><h2>${esc(title)}</h2><ol class="report-list">${[...reports].reverse().map(row).join('')}</ol></section>`:'';
  if(!ctx)return `<p class="intro">${plural(all.length,'deliverable')} in this workspace.</p>${list('report-other','All deliverables',all)}${all.length?'':`<div class="missing-state"><h2>No deliverables yet</h2><p>A run writes its report here when it finishes.</p></div>`}`;
  const heading=!built.length&&!others.length?`<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>${none}</h2><p>${esc(ctx.title)} · ${esc(ctx.run)} remains selected.</p></div><a class="text-action" href="#W-Library/cases">Choose another case</a>`:`<p class="intro">${built.length?`${plural(built.length,'report')} built from ${esc(ctx.run)}’s files (checked by SHA-256).`:`${none}.`}</p>`;
  return `${heading}${list('report-built','Built from this run',built)}${list('report-other',`Other ${ctx.issuer} reports`,others)}${list('report-rest','Other issuers’ deliverables',rest)}`;
}
function reportView(report,context) {
  const ctx=contexts[context],rows=report.builtFrom.map(b=>{
    if(!b.run)return `<tr><th scope="row">${esc(b.module)}</th><td>No matching run file</td><td>${esc(b.source)}</td><td>${b.sha256.slice(0,12)}</td></tr>`;
    const href=b.output?routeHref(b.module,modules[b.source].first,null,b.run,data[b.source].source):routeHref('W-Evidence','sources',null,b.run);
    return `<tr><th scope="row">${esc(b.module)}</th><td>${esc(contexts[b.run].run)}</td><td><a href="${href}">${esc(b.source.split('/').at(-1))}</a></td><td>${b.sha256.slice(0,12)}</td></tr>`;
  }).join('');
  const handoffs=new Set(report.builtFrom.map(b=>b.module)).size,unmatched=new Set(report.builtFrom.filter(b=>!b.run).map(b=>b.module)).size;
  const files=report.files.length?`<details class="built-from"><summary>Files in this deliverable · ${report.files.length}</summary><ul>${report.files.map(f=>`<li><a href="${esc(f.href)}" download>${esc(f.name)}</a></li>`).join('')}</ul></details>`:'';
  return `<div class="report-tools"><label for="report-select">Report</label><select id="report-select">${issuerReports(context).map(r=>`<option value="${esc(r.id)}" ${r.id===report.id?'selected':''}>${esc(reportName(r))}</option>`).join('')}</select><span>${report.status?`${esc(report.status)} · `:''}${ctx?`${esc(ctx.run)} remains selected`:'No matching run'}</span><a href="${esc(report.download)}" download>Download original HTML</a><a href="${routeHref('W-Reports','list')}">All deliverables</a><a href="#W-Library/cases">Return to library</a></div><details class="built-from"><summary>Built from ${handoffs} handoffs · ${unmatched?`${unmatched} with no matching run file`:'byte-identical by SHA-256'}</summary><div class="table-scroll"><table><thead><tr><th scope="col">Module</th><th scope="col">Run</th><th scope="col">File</th><th scope="col">SHA-256 prefix</th></tr></thead><tbody>${rows}</tbody></table></div></details>${files}<iframe id="report-preview" title="${esc(reportName(report))} · ${esc(report.issuer)} report" sandbox="allow-scripts allow-downloads" referrerpolicy="no-referrer" src="${esc(report.href)}"></iframe>`;
}
function settingsView() {
  const app=window.DESIGN_APP||{},issues=app.issues||[];
  return `<div class="settings"><section><h2>Workspace folder</h2><label class="run-field">Folder holding runs and deliverables<input id="workspace-path" value="${esc(app.workspace)}" ${app.policy_locked?'disabled':''} autocomplete="off"></label><p class="hint">${app.policy_locked?'This location is managed by your IT configuration.':'Use a local folder for offline access. Network shares and cloud placeholders need a connection.'}</p><div class="step-actions"><button id="save-workspace" class="primary-action" type="button" ${app.policy_locked?'disabled':''}>Save and reload</button><button id="refresh-library" class="text-button" type="button">Refresh library</button><button id="quit-library" class="text-button" type="button">Quit library</button></div><p id="settings-status" role="status" aria-live="polite"></p></section><section><h2>Workspace issues · ${issues.length}</h2>${issues.length?`<ul>${issues.map(issue=>`<li>${esc(issue)}</li>`).join('')}</ul>`:'<p>None found.</p>'}</section></div>`;
}
const HELP=`<div class="help-copy"><h2>Find and read a run</h2><p>Choose a run in the library. The Summary, Analysis, Calendar, Deliverables and Evidence tabs keep that run selected. Browse by credit question or press / to search a name, section or module code, including absorbed aliases.</p><p>Select a finding’s View source action or a chart mark to open the evidence inspector. Escape returns to your reading position and source trigger.</p><h2>Move between the app and deliverables</h2><p>Deliverables lists every report in the workspace. A report opens inside the app, with this navigation beside it; its Built from list opens the module outputs it used, and a module output names the deliverables that used it.</p><h2>Start a new run</h2><p>Choose New run. Enter the issuer, workflow and dates, or load a saved context file. Choose the issuer folder, model and maximum USD spend. Validating is offline: the review shows the modules in order, the files no module can read and the report sections this run will not produce. Only Start run can call a model, after you approve the review, and only when the provider key is set in the environment that launched the app. If a module is rejected the run stops, keeps its work and makes no automatic paid retry.</p><p>A finished report has automated checks only: review the handoffs against the sources before relying on it.</p><h2>Runs stay separate</h2><p>Each run lists its own saved outputs. A module without one says so and offers other runs of the same issuer; another issuer is reached through the library. Reports list the runs they were built from, traced by SHA-256. Evidence is dated research, not current underwriting. Missing observations are not zero.</p><h2>Colour has a job</h2><div class="signal-key"><span><i class="series-0"></i>Blue · data and action</span><span><i class="series-1"></i>Navy · comparison</span><span><i class="signal-conditional"></i>Amber · conditional / attention</span><span>Grey · absent / unassessed</span></div><p>Dashed paths are conditional scenarios. Outflows use direction and signed values, not an adverse credit grade.</p><h2>Work offline, close or reopen</h2><p>The application, fonts and scripts are bundled; workspace files must also be available locally. Reports are sandboxed with external network requests blocked. Closing a tab leaves the library running; Quit library in Settings stops it.</p></div>`;
// Modules most likely to state the run's overall credit view come first.
const CALL_ORDER=['CP-6','CP-2','CP-3','CP-2D','CP-1','CP-0'];
function firstFinding(id) {
  const sections=data[id].sections,start=sections.findIndex(s=>s.heading==='Findings');
  if(start<0)return null;
  for(const section of sections.slice(start)) {
    if(section.heading==='Calculations')break;
    const block=section.blocks.find(b=>b.type==='text');
    if(block)return {text:block.text,line:block.line};
  }
  return null;
}
function moduleSummary(id) {
  const {call}=data[id];
  if(call)return {kind:'call',text:call.text,line:call.line};
  const finding=firstFinding(id);
  return finding&&{kind:'finding',...finding};
}
function summaryLead(context,available) {
  const order=[...new Set([...CALL_ORDER,...groups.flatMap(g=>g[1].map(item=>item[0]))])].filter(id=>available.includes(id));
  for(const module of order) {
    const id=defaultOutput(module,context),summary=id&&moduleSummary(id);
    // A first finding is one paragraph of a module's work, so it never stands as the run's bottom line.
    if(summary&&summary.kind!=='finding')return `<section class="summary-lead"><p class="summary-owner">${esc(moduleNames[module])}</p><p class="call-quote">${rich(summary.text.replace(/\n/g,' '))}</p>${sourceFooter(`${id}:${summary.line}`)}</section>`;
  }
  return '<section class="summary-lead empty"><p>No bottom line is stored for this run. Read the findings below.</p></section>';
}
function summaryCharts(available,context) {
  const charts=available.map(module=>defaultOutput(module,context)).filter(id=>id&&CHART_RENDERERS[data[id].visual?.kind]).slice(0,4);
  return charts.length?`<div class="summary-charts">${charts.map(id=>`<div class="summary-chart">${visualMarkup(id,{...data[id].visual,fixed:true})}</div>`).join('')}</div>`:'';
}
function summaryCard(module,context) {
  const id=defaultOutput(module,context),summary=id&&moduleSummary(id);
  const body=!id?`<p class="summary-note">${plural(moduleEntry(module,context).outputs.length,'saved output')}. Choose one to read its findings.</p>`:summary?`<div class="summary-text">${rich(summary.text.replace(/\n/g,' '))}</div>${sourceLink(`${id}:${summary.line}`)}`:'<p class="summary-note">No written findings in this output.</p>';
  return `<article class="summary-card" data-module="${esc(module)}" ${id?`data-output="${esc(id)}"`:''}><h3>${moduleLink(module)}</h3>${body}</article>`;
}
function summaryView(context) {
  const available=contextModules(context),built=reportsBuiltFrom(context);
  const questions=groups.map(([title,items])=>[title,items.filter(([id])=>available.includes(id))]).filter(([,items])=>items.length);
  return `${summaryLead(context,available)}${summaryCharts(available,context)}<div class="question-map">${questions.map(([title,items])=>`<section><h2>${esc(title)}</h2><div>${items.map(([id])=>summaryCard(id,context)).join('')}</div></section>`).join('')}</div>${built.length?`<section class="summary-deliverables"><h2>Deliverables from this run</h2>${built.map(r=>`<a class="text-action" href="${routeHref('W-Reports',r.id,null,context)}">${esc(reportName(r))}${icon('arrow-right')}</a>`).join('')}</section>`:''}`;
}
function workspaceView(module,section) {
  const context=current?.context,ctx=contexts[context],available=ctx?contextModules(context):[];
  if(module==='W-Library')return libraryView();
  if(module==='W-NewRun')return '';
  if(module==='W-Settings')return settingsView();
  if(module==='W-Overview')return summaryView(context);
  if(module==='W-Calendar') {
    const events=context===calendarRun('CP-1A'),hedges=context===calendarRun('CP-2E');
    if(!events&&!hedges)return `<div class="missing-state"><h2>No calendar retained for this run</h2><p>${esc(ctx.title)} · ${esc(ctx.run)} remains selected. No dates are inferred from other cases.</p></div>${moduleLink('W-Evidence','Review available evidence')}<a class="text-action switch-case" href="#W-Library/cases">Choose another case</a>`;
    return `<p class="context-note">${esc(ctx.run)} · historical dates and source precision</p>${events?eventTimeline():hedgeChart(pins['CP-2E'],data[pins['CP-2E']].visual)}${moduleLink(events?'CP-1A':'CP-2E','Open owning module')}`;
  }
  if(module==='W-Evidence')return `<p class="intro">Original handoffs for ${esc(ctx.run)}. Source PDF locators inside them do not imply the underlying PDFs are bundled.</p>${sourceInventory(context)}`;
  if(module==='W-Reports') {
    const report=window.DESIGN_WORKSPACE.reports.find(r=>r.id===section);
    return report?reportView(report,context):reportList(context);
  }
  if(module==='CP-MODEL')return `<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>No published model available for this selection</h2><p>${reportsBuiltFrom(context).some(r=>!r.modelPublished)?'The delivery metadata of the reports built from this run records CP-MODEL as unpublished.':'No model publication is linked to this retained run.'}</p></div><div class="requirements">${available.filter(id=>['CP-1','CP-1D','CP-2G'].includes(id)).map(id=>`<div><h3>${esc(moduleNames[id])}</h3>${moduleLink(id)}<p>${esc(data[defaultOutput(id,context)]?.period)}</p></div>`).join('')}</div>${visualPlan('CP-MODEL')}`;
  if(module==='CP-OS')return `<div class="missing-state"><h2>Retained record · ${esc(ctx.run)}</h2><p>This historical selection does not supply live progress or execution costs.</p></div><ol class="activity-flow"><li><h3>Analytical outputs</h3><p>${plural(outputCount(context),'saved output')}, each with its own original source identity.</p>${moduleLink('W-Evidence','Inspect retained outputs')}</li><li><h3>Delivery</h3><p>${reportsBuiltFrom(context).length?`${plural(reportsBuiltFrom(context).length,'report')} built from this run’s files (checked by SHA-256).`:'No report was built from this run’s files (checked by SHA-256).'}</p>${moduleLink('W-Reports','View reports')}</li></ol><p class="caution">Runs started here report their progress and spend on New run.</p>${moduleLink('W-NewRun','Open New run')}`;
  if(module==='W-Help')return section==='visuals'?`<p class="intro">${window.DESIGN_WORKSPACE.visuals.length} specified visualisations. Populated views require retained evidence; the remaining requirements are recorded below.</p>${groups.flatMap(g=>g[1]).map(([id])=>`<h2>${esc(id)} · ${esc(moduleNames[id])}</h2>${visualPlan(id)}`).join('')}`:`${HELP}<a class="text-action" href="${routeHref('W-Help','visuals')}">Visualisation coverage</a>`;
  return '';
}
function updateWorkspaceChrome(module) {
  const ctx=contexts[current.context],isHome=!ctx||appDestinations.has(module);
  const moduleId=ctx&&(lastSection.get(current.context+':module')||ctx.first),period=current.output?data[current.output].period:ctx?.period;
  const title=isHome?(module==='W-Library'?'Issuer library':moduleNames[module]):ctx.title;
  document.querySelector('.issuer').innerHTML=`<div><h1>${esc(title)}</h1><div class="issuer-meta">${isHome?esc(modules[module].subtitle):`<span class="code">${esc(ctx.run)}</span><a href="#W-Library/cases">Change case</a>`}</div></div>${isHome?'':`<div class="scope"><strong>${esc(period)}</strong><span>Retained evidence · not updated since this run</span></div>`}`;
  document.querySelector('.workspace-tabs').hidden=isHome;
  if(!isHome)document.querySelector('.workspace-tabs').innerHTML=[['W-Overview','Summary','layout-grid'],[moduleId,'Analysis','layers'],['W-Calendar','Calendar','calendar-days'],['W-Reports','Deliverables','files'],['W-Evidence','Evidence','folder-open']].map(([id,label,img])=>{
    const sections=navigationSections(id,current.context,resolveOutput(id,current.context,lastFile.get(`${current.context}:${id}`))),remembered=lastSection.get(current.context+':'+id),section=sections.some(s=>s[0]===remembered)?remembered:sections[0][0];
    return `<a href="${routeHref(id,section)}" ${(label==='Analysis'?isAnalytical(module):id===module)?'aria-current="page"':''}>${icon(img)}${label}</a>`;
  }).join('');
  const report=isReportRoute(module,current.section);
  $('workbench').classList.toggle('report-workspace',report);
  $('workbench').classList.toggle('library-workspace',isHome);
  $('content').classList.toggle('report-content',report);
  // The rail shows where you are, and its run-level links keep the selected run.
  const rail=label=>document.querySelector(`.rail a[aria-label="${label}"]`);
  const place={'W-Library':'Issuer library','W-NewRun':'New run','W-Settings':'Settings','W-Help':'Help','W-Reports':'Deliverables','CP-OS':'Run activity'}[module]||'Research workspace';
  document.querySelectorAll('.rail a[title]').forEach(link=>{
    const here=link.getAttribute('aria-label')===place;
    link.classList.toggle('rail-active',here);
    if(here)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
  });
  rail('Research workspace').hidden=rail('Run activity').hidden=!Object.keys(contexts).length;
  rail('Deliverables').hidden=!window.DESIGN_WORKSPACE.reports.length&&!Object.keys(contexts).length;
  if(ctx) {
    rail('Research workspace').href=routeHref('W-Overview','overview');
    rail('Run activity').href=routeHref('CP-OS','activity');
    rail('Deliverables').href=routeHref('W-Reports','list');
  }
  const app=window.DESIGN_APP||{};
  $('workspace-name').textContent=app.workspace?`Workspace · ${app.workspace}`:'';
  $('workspace-name').title=app.workspace||'';
  $('app-problem').hidden=!app.problem;
  $('app-problem').textContent=app.problem?`The workspace could not be read: ${app.problem}`:'';
}
