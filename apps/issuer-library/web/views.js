/* Presentation views. No analytical execution. */
const DISPLAY_MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
// 31 December 2024 for a valid YYYY-MM-DD calendar date; anything else is returned unchanged. Never the OS locale.
function displayDate(iso) {
  const m=typeof iso==='string'&&/^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if(!m) return iso;
  const [year,month,day]=[Number(m[1]),Number(m[2]),Number(m[3])],check=new Date(Date.UTC(2000,month-1,day));
  check.setUTCFullYear(year);
  if(year<1||month<1||month>12||check.getUTCFullYear()!==year||check.getUTCMonth()!==month-1||check.getUTCDate()!==day) return iso;
  return `${day} ${DISPLAY_MONTHS[month-1]} ${year}`;
}
function installDestinations() {
  const title = h => h.replace(/^Chart data: /,'').replace(/^T[\w.]+(?:\s*[–/]\s*(?:T[\w.]+|\d+))*\s*[—–]\s*/,'').replace(/^./,s=>s.toUpperCase());
  for (const [id,out] of Object.entries(data)) {
    if(modules[id]) continue;
    const sections=[];
    const audit=[];
    for(const s of out.sections.filter(s=>s.blocks.length)) {
      if(/^(Request|Calculations|Next module)/.test(s.heading)) {audit.push('='+s.heading);continue;}
      sections.push(['s'+s.line,title(s.heading),['='+s.heading]]);
    }
        const first=out.summary?out.sections.find(s=>s.heading==='Reader summary'):out.firstHeading&&out.sections.find(s=>s.heading.startsWith(out.firstHeading));
    const rank=s=>s[0]==='s'+first?.line?-1:s[1]==='Sources'?1:0;
    sections.sort((a,b)=>rank(a)-rank(b));
    sections.push(['audit','Technical audit',audit]);
    modules[id]={name:moduleNames[out.module],subtitle:out.scope,first:first?'s'+first.line:sections[0][0],sections};
  }
  const destinations={
    'W-Library':['Issuer library',[['cases','Issuer cases',[]]]],
    'W-Overview':['Overview',[['overview','Overview',[]]]],
    'W-Calendar':['Event calendar',[['unavailable','Calendar availability',[]]]],
    'W-Reports':['Reports',[['list','Reports',[]]]],
    'W-Evidence':['Evidence library',[['sources','Retained outputs',[]]]],
    'W-Forecast':['Forecast',[['forecast','Forecast',[]]]],
    'CP-OS':['Run activity',[['activity','Run record',[]],['delivery','Delivery scope',[]]]],
    'W-NewRun':['New run',[['run','New run',[]]]],
    'W-Settings':['Settings',[['workspace','Workspace',[]]]],
    'W-Help':['Help',[['help','Using the library',[]]]]
  };
  for(const [id,[name,sections]] of Object.entries(destinations)) {
    modules[id]={name,sections,first:sections[0][0]};
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
// One issuer is one issuerKey, whatever names its runs were recorded under; an unrecorded issuer (null) equals nothing.
const sameIssuer=(a,b)=>a!=null&&a===b;
const issuerReports=context=>window.DESIGN_WORKSPACE.reports.filter(r=>!context||sameIssuer(r.issuerKey,contexts[context]?.issuerKey));
const reportsBuiltFrom=context=>window.DESIGN_WORKSPACE.reports.filter(r=>r.builtFrom.some(b=>b.run===context));
const reportsUsing=output=>window.DESIGN_WORKSPACE.reports.filter(r=>r.builtFrom.some(b=>b.source===output));
// A run's published models: those recorded for its folder and those built from a file it holds.
const publishedModels=()=>window.DESIGN_WORKSPACE.models;
const byModelId=(a,b)=>b.id.localeCompare(a.id);
// One order for the Model select, the section pager and the default: the default model first, then the rest by folder name, latest first.
// A model of another issuer (or of none recorded) is never a run's own, whatever run it names; no run context holds none.
const runModels=context=>{const run=contexts[context];if(!run)return [];const held=publishedModels().filter(m=>sameIssuer(m.issuerKey,run.issuerKey)&&(m.runId===run.folder||m.sources.some(s=>s.run===context))).sort(byModelId),first=modelOrder(held)[0];return first?[first,...held.filter(m=>m!==first)]:held;};
// A model links only to a run whose Forecast page lists it (runModels); with no such run it is shown unlinked.
const modelRun=model=>Object.keys(contexts).find(key=>runModels(key).includes(model))||null;
// A model opens under the run it was published for (its runId), never under a run that only supplied files; with no such run listing it, modelRun's choice stands.
const modelOwnRun=model=>Object.keys(contexts).find(key=>contexts[key].folder===model.runId&&runModels(key).includes(model))||modelRun(model);
// Not superseded by another listed model; one that records a predecessor comes first, then the later folder name.
const modelOrder=models=>[...models].sort((a,b)=>(models.some(m=>m.previous===a.id)-models.some(m=>m.previous===b.id))||((b.previous!=null)-(a.previous!=null))||byModelId(a,b));
function modelRelationship(model,models) {
  const successor=models.find(m=>m.previous===model.id);
  return model.previous?`supersedes ${model.previous}`:successor?`superseded by ${successor.id}`:'relationship not recorded';
}
const tracedRun=report=>report.builtFrom.find(b=>b.run)?.run||null;
const reportName=report=>report.build?`Build ${report.build} · ${report.label.trim()}`:report.label.trim();
const byBuild=(a,b)=>(b.build||0)-(a.build||0)||a.label.trim().localeCompare(b.label.trim());
// A run being prepared lives only in this page, so whatever reloads it asks first (boot.js keeps its own copy).
const mayDiscardDraft=()=>document.body.dataset.draft!=='1'||window.confirm('Reload now? The run you are preparing will be cleared.');
// A frame has no error event for a page that never arrives, so a missing load within the timeout is the failure.
const frameTimeout=()=>Number.isFinite(window.DESIGN_FRAME_TIMEOUT_MS)?window.DESIGN_FRAME_TIMEOUT_MS:6000;
function watchFrame(frame,status,loadingText,failedText,link,missingText) {
  let timer=null;
  const loaded=()=>{clearTimeout(timer);status.hidden=true;};
  const wait=()=>{clearTimeout(timer);status.hidden=false;status.textContent=loadingText;timer=setTimeout(fail,frameTimeout());};
  function fail() {
    const retry=document.createElement('button');
    retry.type='button';retry.className='text-button frame-retry';retry.textContent='Retry';
    retry.addEventListener('click',()=>{frame.setAttribute('src',frame.getAttribute('src'));wait();});
    status.textContent=failedText+' ';
    if(link)status.append(link(),' ');
    status.append(retry);
  }
  // A frame fires load for a 404 page too, so a deliverable that has gone is found by asking for it first.
  function missing() {
    if(!frame.isConnected)return;
    clearTimeout(timer);frame.removeEventListener('load',loaded);
    const reload=document.createElement('button');
    reload.type='button';reload.className='text-button';reload.textContent='Reload';
    reload.addEventListener('click',()=>{if(mayDiscardDraft())location.reload();});
    status.hidden=false;status.textContent=missingText+' ';status.append(reload);
  }
  frame.addEventListener('load',loaded);
  wait();
  if(missingText)fetch(frame.getAttribute('src'),{method:'HEAD',cache:'no-store'}).then(response=>{if(!response.ok)missing();},missing);
  return loaded;
}
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
  const label=[v.unit,data[id].period].filter(Boolean).join(' · ');
  return `<div class="section-heading"><h2>${esc(v.title)}</h2>${label?`<span>${esc(label)}</span>`:''}</div>${v.quote?`<p class="chart-reading">${rich(v.quote.text.replace(/\n/g,' '))}</p>${sourceFooter(`${id}:${v.quote.line}`)}`:''}`;
}
const evidenceHref=(id,line)=>routeHref(data[id].module,current?.output===id?current.section:modules[id].first,`${id}:${line}`,data[id].run);
function comparisonChart(module,v,selection=0) {
  const table=fixtureTable(module,v.table),selected=table.rows[v.rows?.[selection]??0];
  const selectable=['paired','peers'].includes(v.kind)&&!['CP-4C','CP-2A'].includes(data[module].module);
  const rows=selectable?[selected]:(v.rows||table.rows.map((_,i)=>i)).map(i=>table.rows[i]);
  const points=v.kind==='peers'?v.columns.map(c=>({label:table.headers[c],value:selected.cells[c],row:selected,series:0})):rows.flatMap(row=>(v.columns||[v.column]).map((c,i)=>({label:plain(row.cells[0]),series:i,value:row.cells[c],row,column:c})));
  const max=Math.max(1,...points.map(p=>Math.abs(chartNumber(p.value)??0)));
  const hasNegative=points.some(p=>(chartNumber(p.value)??0)<0);
  return `${chartIntro(module,v)}${selectable&&!v.fixed?`<label class="metric-control">Measure <select id="chart-metric">${v.rows.map((idx,i)=>`<option value="${i}" ${i===selection?'selected':''}>${esc(plain(table.rows[idx].cells[0]))}</option>`).join('')}</select></label>`:''}<div class="horizontal-chart ${hasNegative?'diverging':''}">${points.map((p,i)=>{
    const n=chartNumber(p.value),width=n===null?0:Math.abs(n)/max*100;
    return `<button class="chart-row" data-evidence="${esc(`${module}:${p.row.line}`)}"><span class="chart-label">${i&&points[i-1].label===p.label?`<span class="sr-only">${esc(p.label)}</span>`:esc(p.label)}${v.columns&&v.kind!=='peers'?`<small>${esc(table.headers[p.column])}</small>`:''}</span><span class="track ${n===null?'missing':''}">${hasNegative?`<span class="zero-rule"></span><i class="series-${p.series} ${n<0?'negative':''}" style="left:${n<0?50-width/2:50}%;width:${width/2}%"></i>`:`<i class="series-${p.series}" style="width:${width}%"></i>`}</span><strong>${/[\p{L}\p{N}]/u.test(String(p.value??''))?esc(p.value):'Not available'}</strong></button>`;
  }).join('')}</div><p class="matrix-note">Missing values have no bar.</p>`;
}
// A label of two or more words breaks at the space nearest its middle (ties: the earlier one).
function axisLines(label) {
  const spaces=[...label.matchAll(/ /g)].map(m=>m.index);
  if(!spaces.length)return [label];
  const at=spaces.reduce((best,i)=>Math.abs(i-label.length/2)<Math.abs(best-label.length/2)?i:best);
  return [label.slice(0,at),label.slice(at+1)];
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
  return `${chartIntro(module,v)}<div class="vector-chart"><svg viewBox="-5 -12 680 270" role="group" aria-label="${esc(v.title)}. Select a movement to inspect its source."><line x1="0" y1="210" x2="660" y2="210" class="axis"/>${points.map((p,i)=>`<a class="plot-point" href="${evidenceHref(module,p.row.line)}" data-evidence="${esc(`${module}:${p.row.line}`)}" aria-label="${esc(p.label||plain(p.row.cells[0]))}, ${esc(p.display??p.row.cells[v.amount])} ${esc(v.unit)}. View source"><title>${esc(p.label||plain(p.row.cells[0]))}: ${esc(p.display??p.row.cells[v.amount])}</title><rect class="${p.total?'total':p.amount<0?'outflow':'movement'}" x="${i*step+10}" y="${y(Math.max(p.start,p.end))}" width="${step-20}" height="${Math.max(1,Math.abs(y(p.end)-y(p.start)))}"/><text x="${i*step+step/2}" y="${y(Math.max(p.start,p.end))-8}" text-anchor="middle">${esc(p.display??p.row.cells[v.amount])}</text><text class="axis-label" x="${i*step+step/2}" y="232" text-anchor="middle">${axisLines(p.label||plain(p.row.cells[0])).map((line,at)=>`<tspan x="${i*step+step/2}" dy="${at?'1.2em':0}">${esc(line)}</tspan>`).join('')}</text>${i<points.length-1?`<line class="connector" x1="${i*step+step-10}" y1="${y(p.end)}" x2="${(i+1)*step+10}" y2="${y(p.end)}"/>`:''}</a>`).join('')}</svg></div><div class="bridge-key">${points.map((p,i)=>`<span>${sourceLink(`${module}:${p.row.line}`,p.label||plain(p.row.cells[0]))}${classTag(evidence.get(`${module}:${p.row.line}`),'row-classification')}</span>`).join('')}</div>`;
}
function pathChart(module,v) {
  const table=fixtureTable(module,v.table),series=['Reference','Downside','Upside'];
  const values=table.rows.map(r=>chartNumber(r.cells[v.column]));
  if(values.some(n=>n===null))throw new Error('Missing conditional path value');
  const max=Math.max(...values)*1.13, y=n=>200-n/max*175;
  return `${chartIntro(module,v)}<div class="chart-legend path-legend">${series.map((s,i)=>`<span><i class="path-key-${i}"></i>${s}</span>`).join('')}<span>Dashed paths · conditional scenarios</span></div><div class="vector-chart"><svg viewBox="0 0 670 250" role="group" aria-label="Closing cash across FY2025 to FY2027. Select a point to inspect its exact source.">${[0,2000,4000,6000].map(n=>`<line class="gridline" x1="65" x2="600" y1="${y(n)}" y2="${y(n)}"/><text class="axis-label" x="55" y="${y(n)+4}" text-anchor="end">${n.toLocaleString('en-US')}</text>`).join('')}${series.map((name,i)=>{
    const rows=table.rows.filter(r=>r.cells[0].startsWith(name+' / '));
    return `<polyline class="path-${i}" fill="none" stroke-dasharray="${['5 4','2 4','9 4'][i]}" points="${rows.map((r,j)=>`${90+j*235},${y(chartNumber(r.cells[v.column]))}`).join(' ')}"/>${rows.map((r,j)=>`<a class="plot-point" href="${evidenceHref(module,r.line)}" data-evidence="${esc(`${module}:${r.line}`)}" aria-label="${esc(r.cells[0])}, closing cash ${esc(r.cells[v.column])} ${esc(v.unit)}. View source"><title>${esc(r.cells[0])}: ${esc(r.cells[v.column])} ${esc(v.unit)}</title><circle class="point-hit" cx="${90+j*235}" cy="${y(chartNumber(r.cells[v.column]))}" r="12"/><circle class="point-${i}" cx="${90+j*235}" cy="${y(chartNumber(r.cells[v.column]))}" r="4"/></a>`).join('')}`;
  }).join('')}${['2025','2026','2027'].map((year,i)=>`<text class="axis-label" x="${90+i*235}" y="230" text-anchor="middle">FY${year}</text>`).join('')}</svg></div><div class="path-readout">${series.map(name=>{const r=table.rows.find(r=>r.cells[0]===name+' / 2027');return `<div><span>${name} · FY2027</span><strong>${esc(r.cells[v.column])}</strong>${sourceFooter(`${module}:${r.line}`)}</div>`;}).join('')}</div>`;
}
function hedgeChart(module,v) {
  const table=fixtureTable(module,v.table),start=Date.UTC(2023,2,31),end=Date.UTC(2027,8,30),position=date=>(Date.parse(date)-start)/(end-start)*100;
  return `${chartIntro(module,v)}<div class="hedge-axis"><span style="left:0">Mar 2023</span><span style="left:${position('2024-09-30')}%">Sep 2024 base</span><span style="left:100%">Sep 2027</span></div><div class="hedge-chart">${table.rows.map(row=>{
    const dates=row.cells[2].match(/\d{4}-\d{2}-\d{2}/g),dated=dates?.length===2,forward=dated&&dates[0]>'2024-09-30';
    return `<button class="hedge-row" data-evidence="${esc(`${module}:${row.line}`)}"><span>${esc(row.cells[0])}<small>${esc(row.cells[1])} ${row.cells[0]==='FX forwards'?'':'USDm'}</small></span><span class="hedge-lane"><i class="base-rule" style="left:${position('2024-09-30')}%"></i>${dated?`<i class="hedge-span ${forward?'future':''}" style="left:${position(dates[0])}%;width:${position(dates[1])-position(dates[0])}%"></i>`:'<span class="duration-only">Duration only · ≤12 months</span>'}</span><span class="hedge-dates">${dated?esc(dates.join(' → ')):esc(row.cells[2])}<small>${forward?'Forward starting at base date':dated?'Active at base date':'No exact expiry supplied'}</small></span></button>`;
  }).join('')}</div>`;
}
function qualitativeVisual(module,v) {
  const table=fixtureTable(module,v.table);
  if(v.kind==='debate')return `${chartIntro(module,v)}<div class="debates">${table.rows.map(r=>`<section class="debate"><header><h3>${rich(r.cells[0])}</h3><span class="grade unknown">${rich(r.cells[3])}</span></header><div class="arguments"><div><h4>Bull position</h4><p>${rich(r.cells[1])}</p></div><div><h4>Bear position</h4><p>${rich(r.cells[2])}</p></div></div><p class="resolution">${rich(r.cells[4])}</p>${sourceFooter(`${module}:${r.line}`)}</section>`).join('')}</div>`;
  if(v.kind==='agencies')return `${chartIntro(module,v)}<div class="agency-pair">${table.rows.map(r=>`<section><h3>${esc(r.cells[0])}</h3><p class="rating">${rich(r.cells[1])}</p><h4>Proposed issue</h4><p>${rich(r.cells[2])}</p><p class="matrix-note">${rich(r.cells[3])}</p>${sourceFooter(`${module}:${r.line}`)}</section>`).join('')}</div>`;
  return `${chartIntro(module,v)}<div class="qual-matrix">${table.rows.map(row=>`<section><h3>${rich(row.cells[v.columns[0]])}</h3><div>${v.columns.slice(1).map(c=>`<div><h4>${esc(table.headers[c])}</h4><p>${rich(row.cells[c])}</p></div>`).join('')}${sourceFooter(`${module}:${row.line}`)}</div></section>`).join('')}</div>`;
}
const CHART_RENDERERS={paired:comparisonChart,peers:comparisonChart,bars:comparisonChart,bridge:bridgeChart,waterfall:bridgeChart,paths:pathChart,hedges:hedgeChart};
const visualMarkup=(module,v)=>(CHART_RENDERERS[v.kind]||qualitativeVisual)(module,v);
const readerChart=(id,chart)=>comparisonChart(id,{kind:'bars',...chart});
function readerCharts(id,section) {
  const lines=new Set(sectionData(id,section).flatMap(s=>s.blocks).map(b=>b.line));
  return (data[id].charts||[]).filter(c=>lines.has(c.table)).map(c=>readerChart(id,c)).join('');
}
function galleryVisual(module,section) {
  const out=data[module],v=out.visual;
  if(!v||!sectionData(module,section).some(s=>s.blocks.some(b=>b.line===v.table)))return '';
  return `<div id="module-visual">${visualMarkup(module,v)}</div>${visualCoversTable(module,fixtureTable(module,v.table))?'':'<div class="section-heading compact"><h2>Complete findings & exact data</h2><span>Retained output</span></div>'}`;
}
function visualCoversTable(module,block) {
  const {visual:v,summary}=data[module];
  if(block.type==='table'&&summary&&block.rows[0]?.line===summary.line)return true; // The band holds this row.
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
function routeHref(module,section,key=null,context=current?.context,file=lastFile.get(`${context}:${module}`)) {
  const params=new URLSearchParams();
  if(context)params.set('c',context);
  if(file&&`${contexts[context].folder}/${file}`!==defaultOutput(module,context))params.set('o',file);
  if(key)params.set('e',key);
  // A report id is a folder name: encoded, it can hold quotes, angle brackets, ? or # and still route back.
  return `#${encodeURIComponent(module)}/${encodeURIComponent(section)}${params.size?'?'+params:''}`;
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
  const others=Object.entries(contexts).filter(([key,run])=>key!==current.context&&sameIssuer(run.issuerKey,ctx.issuerKey)&&run.modules[module]?.outputs.length);
  const given=(entry?.inputs||[]).map(id=>store.inputs[id]);
  return `<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>${label}</h2><p>${entry?`This run keeps ${plural(given.length,'input file')} for ${esc(moduleNames[module])} and no saved output.`:`No ${esc(moduleNames[module])} output file was found in this run. That alone does not show the module was not run or not applicable.`}</p>${given.map(f=>`<p><a href="${esc(f.href)}" download>${esc(f.source)}</a></p>`).join('')}</div>${others.length?`<div class="available-case"><h3>Other ${esc(ctx.issuer)} runs with this module</h3>${others.map(([key,run])=>`<p><a class="text-action" href="${routeHref(module,firstSection(module,key),null,key)}">${esc(run.run)}${icon('arrow-right')}</a></p>`).join('')}</div>`:''}`;
}
function outputChooser(module) {
  const ctx=contexts[current.context],files=moduleEntry(module,current.context).outputs;
  return `<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>Choose a saved output</h2><p>${files.length} versions of this analysis. Choose one to read.</p></div><div class="output-choices">${files.map(id=>`<a class="text-action" href="${routeHref(module,modules[id].first,null,current.context,data[id].source)}">${esc(data[id].label)}${icon('arrow-right')}</a>`).join('')}</div>`;
}
// The calendar reads two curated tables; a run has one only if it holds that pinned output.
const calendarRun=module=>data[pins[module]]?.run;
function calendarSections(context) {
  return context===calendarRun('CP-1A')?[['tdg','Issuer events',[]]]:context===calendarRun('CP-2E')?[['hedges','Hedge schedule',[]]]:[['unavailable','Calendar availability',[]]];
}
function forecastSections(context) {
  const models=runModels(context);
  return models.length?models.map(m=>[m.id,m.id,[]]):[['none','Forecast availability',[]]];
}
// The run's issuer reports, then any other report built from this run's files (parseRoute sends such a report to this run).
function runReports(context) {
  const own=issuerReports(context);
  return [...own,...(context?reportsBuiltFrom(context).filter(r=>!own.includes(r)):[])];
}
function reportSections(context) {
  const reports=runReports(context);
  return reports.length?[['list','Reports',[]],...reports.map(r=>[r.id,reportName(r),[]])]:[['none','Report availability',[]]];
}
function navigationSections(module,context,output=defaultOutput(module,context)) {
  if(module==='W-Calendar')return calendarSections(context);
  if(module==='W-Evidence')return [['sources','Retained outputs',[]]];
  if(module==='W-Reports')return reportSections(context);
  if(module==='W-Forecast')return forecastSections(context);
  if(Object.hasOwn(modules,module))return modules[module].sections;
  if(output)return modules[output].sections;
  return [['status',moduleEntry(module,context)?.outputs.length?'Choose a saved output':availability(module,context),[]]];
}
function moduleLink(id,label){return `<a class="text-action" href="${routeHref(id,lastSection.get(current?.context+':'+id)||firstSection(id,current?.context))}">${esc(label||moduleNames[id])}${icon('arrow-right')}</a>`;}
// Rows repeat the same two actions, so each is an icon; its accessible name and tooltip still say what it does.
const iconAction=(action,target,href,name,download=false)=>`<a class="icon-action" href="${esc(href)}" ${download?'download':''} aria-label="${esc(`${action}: ${target}`)}" title="${action}">${icon(name)}</a>`;
// A module with no name keeps its code alone.
const nameThenCode=code=>moduleNames[code]&&moduleNames[code]!==code?`${moduleNames[code]} · ${code}`:code;
function sourceInventory(context) {
  const identity=f=>`<details><summary>File identity</summary><p>${esc(f.file)}</p><p class="hash">SHA-256 ${f.sha256}</p></details>`;
  const rows=Object.entries(contexts[context].modules).flatMap(([module,entry])=>[
    ...entry.outputs.map(id=>{const out=data[id];return `<section><div><h3>${esc(nameThenCode(module))}</h3><p>${esc(out.label)}</p>${out.scope==='Retained module output'?'':`<span class="badge badge-gray">${esc(out.scope)}</span>`}</div><div>${iconAction('Open output',`${module} ${moduleNames[module]}, ${out.label}`,routeHref(module,modules[id].first,null,context,out.source),'arrow-right')}${iconAction('Download original handoff',`${module} ${moduleNames[module]}, ${out.label}`,out.href,'download',true)}</div>${identity(out)}</section>`;}),
    ...entry.inputs.map(id=>{const f=store.inputs[id];return `<section><div><h3>${esc(nameThenCode(module))}</h3><p>${esc(f.source)}</p><span class="badge badge-gray">Input</span></div><div>${iconAction('Download original file',`${module} ${moduleNames[module]}, ${f.source}`,f.href,'download',true)}</div>${identity(f)}</section>`;})
  ]);
  if(!rows.length)return `<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>No retained files for this run</h2><p>No module outputs or inputs were found in this run’s folder.</p></div><a class="text-action switch-case" href="#W-Library/cases">Choose another case</a>`;
  return `<div class="source-inventory">${rows.join('')}</div>`;
}
const badge=(kind,text)=>`<span class="badge badge-${kind}">${esc(text)}</span>`;
// The acceptance state a report declares, as the badge and muted qualification text every report listing shows.
const QUALIFICATIONS=['unrun','partial','qualified','blocked'];
function reportAcceptance(report) {
  const candidate=report.mode==='candidate';
  const state=report.mode==='accepted'?'Accepted':candidate?'Candidate · not accepted':'Acceptance not recorded';
  const qualification=report.qualification==='unrun'?'Analytical qualification: not run':QUALIFICATIONS.includes(report.qualification)?`Analytical qualification: ${report.qualification}`:'Analytical qualification not recorded';
  return {state,qualification,html:`<span class="acceptance">${badge('gray',state)} <span class="muted">${esc(qualification)}</span></span>`};
}
function forecastEmpty(context) {
  const ctx=contexts[context],others=publishedModels().filter(m=>sameIssuer(m.issuerKey,ctx.issuerKey)).sort(byModelId);
  const row=m=>{const run=modelOwnRun(m);return `<li class="report-row">${run?`<a class="text-action" href="${routeHref('W-Forecast',m.id,null,run)}">${esc(m.id)}${icon('arrow-right')}</a>`:`<span>${esc(m.id)}</span>`} ${reportAcceptance(m).html}</li>`;};
  return `<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>No forecast model was published from this run’s files</h2></div>${others.length?`<section class="forecast-other"><h2>Other ${esc(ctx.issuerHeading)} models</h2><ol class="report-list">${others.map(row).join('')}</ol></section>`:''}`;
}
// A percent or multiple cell's title: the value in its display unit at four decimals, half away from zero, "≈ " when rounding changed it.
function ratioTitle(exact,kind) {
  const found=/^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(exact);
  if(!found||Math.abs(Number(found[4]||0))>400)return exact;
  const frac=found[3]||'',shift=Number(found[4]||0)+(kind==='percent'?2:0);
  const digits=BigInt(found[2]+frac),scale=frac.length-shift;
  let units,exactly=true;
  if(scale<=4)units=digits*10n**BigInt(4-scale);
  else{const divisor=10n**BigInt(scale-4);units=digits/divisor;const rest=digits%divisor;exactly=rest===0n;if(rest*2n>=divisor)units+=1n;}
  const negative=found[1]==='-'&&units!==0n,text=units.toString().padStart(5,'0');
  return `${exactly?'':'≈ '}${negative?'-':''}${text.slice(0,-4)}.${text.slice(-4)}${kind==='percent'?'%':'x'}`;
}
// One cell's title: the exact amount (ratios in their display unit), else the reason it has no value.
const cellTitle=(cell,kind)=>cell.exact!=null?(kind==='percent'||kind==='multiple'?ratioTitle(cell.exact,kind):cell.exact):cell.reason;
// "Not available" lines: one per row and reason, naming the periods; a repeated column label takes its group's name.
function notAvailableLines(c) {
  const counts=new Map();
  for(const col of c.columns)counts.set(col.label,(counts.get(col.label)||0)+1);
  const period=col=>counts.get(col.label)>1?`${col.label} ${col.group.replace(/\s*\([^()]*\)$/,'')}`:col.label;
  const lines=[];
  for(const row of c.rows){
    const pairs=new Map();
    row.cells.forEach((cell,i)=>{
      if(cell.status!=='na')return;
      const list=pairs.get(cell.reason)||pairs.set(cell.reason,[]).get(cell.reason);
      list.push(period(c.columns[i]));
    });
    for(const [reason,periods] of pairs)lines.push(`Not available: ${row.label} — ${periods.join(', ')}${reason==null?'':`: ${reason}`}`);
  }
  return lines;
}
// The calculation record as a line-item by period grid. The store formatted every cell; this only places it.
function cashflowSection(model) {
  const c=model.cashflow;
  if(!c)return '<section class="forecast-cashflow"><h2>Cash flow model</h2><p>This model has no readable calculation record.</p></section>';
  const groups=[];
  for(const col of c.columns){const last=groups[groups.length-1];if(last&&last.name===col.group)last.span++;else groups.push({name:col.group,span:1});}
  // The first column of each group carries a rule; the Base case and Downside columns sit on a quiet ground.
  const scenario=name=>/^(Base case|Downside)/.test(name),starts=c.columns.map((col,i)=>i===0||c.columns[i-1].group!==col.group);
  const colClass=i=>[starts[i]?'group-start':'',scenario(c.columns[i].group)?'scenario':''].filter(Boolean).join(' '),attr=cls=>cls?` class="${cls}"`:'';
  const head=`<tr><th scope="col" rowspan="2">Line item</th>${groups.map(g=>{const at=c.columns.findIndex(col=>col.group===g.name);return `<th scope="colgroup" colspan="${g.span}"${attr(colClass(at))}>${esc(g.name)}</th>`;}).join('')}</tr><tr>${c.columns.map((col,i)=>`<th scope="col"${attr(colClass(i))}${col.start==null||col.end==null?'':` title="${esc(`${displayDate(col.start)} to ${displayDate(col.end)}`)}"`}>${col.ytd&&col.label.endsWith(' (YTD)')?`${esc(col.label.slice(0,-6))} <span class="col-sub">(YTD)</span>`:esc(col.label)}</th>`).join('')}</tr>`;
  const td=(cell,kind,i)=>{
    const title=cellTitle(cell,kind),label=cell.status==='na'?`n.a.${cell.reason==null?'':`: ${cell.reason}`}`:cell.status==='nm'?'n.m.: not modelled in the calculation record':null;
    return `<td${attr(colClass(i))}${title==null?'':` title="${esc(title)}"`}${label==null?'':` aria-label="${esc(label)}"`}>${esc(cell.display)}</td>`;
  };
  let band=null,body='';
  for(const row of c.rows){
    if(row.band!==band){band=row.band;body+=`<tr class="band-row"><th scope="colgroup" colspan="${c.columns.length+1}">${esc(band)}</th></tr>`;}
    body+=`<tr${row.total?' class="total-row"':''}><th scope="row">${esc(row.label)}</th>${row.cells.map((cell,i)=>td(cell,row.kind,i)).join('')}</tr>`;
  }
  const na=notAvailableLines(c),first=c.columns[0],last=c.columns[c.columns.length-1];
  const caption=[c.units==null?'Units not recorded':c.units,...first?[`${first.label} to ${last.label}`]:[],'history as retained in the handoffs; forecasts are conditional illustrations from the calculation record'].join(' · ');
  return `<section class="forecast-cashflow"><h2 id="cashflow-heading">Cash flow model</h2><p class="forecast-caption">${esc(caption)}</p><div class="table-scroll" role="region" aria-labelledby="cashflow-heading" tabindex="0"><table class="cashflow"><thead>${head}</thead><tbody>${body}</tbody></table></div>${c.notes.length?`<ul class="cashflow-notes">${c.notes.map(line=>`<li>${esc(line)}</li>`).join('')}</ul>`:''}${na.length?`<details class="cashflow-na"><summary>Why cells show n.a. (${na.length} lines)</summary><ul>${na.map(line=>`<li>${esc(line)}</li>`).join('')}</ul></details>`:''}</section>`;
}
// The roles a delivery's sources are declared under; an unknown role shows its own token.
const SOURCE_ROLES={annual:'Annual handoff',quarter:'Quarterly handoff',forecast:'Forecast handoff',forecast_exact:'Forecast calculations',current_synthesis:'Current synthesis'};
const sourceFile=s=>(s.output||s.path||'').split('/').at(-1);
// A fact, not a judgement: sources whose file names carry different attempt numbers.
function attemptNote(sources) {
  const named=[...new Set(sources.map(sourceFile).filter(f=>/-attempt-\d+/.test(f)))];
  const attempt=f=>/-attempt-(\d+)/.exec(f)[1];
  if(new Set(named.map(attempt)).size<2)return '';
  return `<p class="forecast-attempts">${esc(`These files come from different attempts: ${named.map(f=>`${f} (attempt ${attempt(f)})`).join(', ')}`)}</p>`;
}
function forecastView(context,id) {
  const models=runModels(context);
  if(!models.length)return forecastEmpty(context);
  const model=models.find(m=>m.id===id)||models[0];
  const acceptance=reportAcceptance(model);
  const select=`<label for="model-select">Model</label><select id="model-select">${models.map(m=>`<option value="${esc(m.id)}" ${m.id===model.id?'selected':''}>${esc(`${m.id} · ${modelRelationship(m,models)}`)}</option>`).join('')}</select>`;
  const why=`<section class="forecast-why"><h2>Why this model was built</h2>${model.scope==null?'':`<p class="forecast-scope">${esc(model.scope)}</p>`}${model.inputContract==null?'':`<p class="forecast-input">${esc(`Input contract: ${model.inputContract}`)}</p>`}${model.revisionNote==null?'':`<p class="forecast-revision">${esc(`Revision note: ${model.revisionNote}`)}</p>`}</section>`;
  const forecast=model.sources.find(s=>s.role==='forecast'),register=model.register;
  const full=forecast?.output?`<a class="text-action" href="${routeHref(data[forecast.output].module,modules[forecast.output].first,null,forecast.run,data[forecast.output].source)}">Open the full forward credit model output${icon('arrow-right')}</a>`:'';
  const assumptions=`<section class="forecast-assumptions"><h2>Assumptions and their rationale</h2>${register?`<h3>${esc(register.heading)}</h3>${register.intro==null?'':`<p class="register-intro">${esc(register.intro)}</p>`}${register.headers.length?`<div class="table-scroll"><table><thead><tr>${register.headers.map(c=>`<th scope="col">${esc(c)}</th>`).join('')}</tr></thead><tbody>${register.rows.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:''}${full}`:'<p>This model’s forecast handoff has no assumption register.</p>'}</section>`;
  const source=s=>s.output?`<a href="${routeHref(data[s.output].module,modules[s.output].first,null,s.run,data[s.output].source)}">${esc(s.output.split('/').at(-1))}</a>`:`<span title="${esc(s.path)}">${esc(sourceFile(s))}</span>`;
  // The run is the folder the delivery declares the file under, so every source names one the same way.
  const run=s=>{const id=/^runs\/([^/]+)\//.exec(s.path||'')?.[1];return id?`<span class="code">${esc(id)}</span>`:'<span class="muted">Not recorded</span>';};
  const status=s=>s.sha256===null?badge('attention','Invalid path or hash'):s.changed?badge('attention','Changed since publication'):badge('gray','Matches publication');
  const built=`<section class="forecast-built"><h2>Built from</h2><div class="table-scroll"><table><thead><tr><th scope="col">Role</th><th scope="col">Run</th><th scope="col">Source</th><th scope="col">SHA-256 prefix</th><th scope="col">Status</th></tr></thead><tbody>${model.sources.map(s=>`<tr><th scope="row">${esc(Object.hasOwn(SOURCE_ROLES,s.role)?SOURCE_ROLES[s.role]:s.role)}</th><td>${run(s)}</td><td>${source(s)}</td><td>${s.sha256===null?'':esc(s.sha256.slice(0,12))}</td><td>${status(s)}</td></tr>`).join('')}</tbody></table></div>${attemptNote(model.sources)}</section>`;
  return `<div class="forecast"><div class="report-tools forecast-tools">${select}${acceptance.html}<a href="${esc(model.download)}" download>Download original HTML</a></div>${cashflowSection(model)}${assumptions}${model.cashflow?`<section class="forecast-limits"><h2>Model limitations</h2><ul>${model.cashflow.limits.map(l=>`<li>${esc(l)}</li>`).join('')}</ul></section>`:''}${why}${built}<details class="model-original"><summary>Published model (original HTML)</summary><div class="frame-host"><p class="frame-status" role="status" hidden></p><iframe id="model-preview" data-download="${esc(model.download)}" data-src="${esc(model.href)}" title="${esc(model.id)} · published model" sandbox="allow-scripts allow-downloads" referrerpolicy="no-referrer"></iframe></div></details></div>`;
}
// The Library screen. The served catalogue (window.DESIGN_CATALOGUE) is screened and sorted by LibraryLogic (screening.js); this places it. Nothing here calculates, converts or rescales a value.
const METRIC_NAMES={revenue:'Revenue',ebitda:'EBITDA',leverage:'Leverage',coverage:'Interest coverage',cash:'Closing cash',cashflow:'Cash flow measure'};
const LIBRARY_COLUMNS=[['name','Issuer / run'],[null,'Sector'],['date','Evidence date'],['leverage','Leverage'],['coverage','Coverage'],['completion','Completeness'],[null,'Deliverable']];
const catalogueRuns=()=>window.DESIGN_CATALOGUE?.real||[];
// A date that is not a real calendar day is shown as served, never as another day.
function libraryDate(value) {
  if(!value)return '—';
  const day=new Date(`${value}T12:00:00Z`);
  return Number.isNaN(day.getTime())||day.toISOString().slice(0,10)!==value?String(value):day.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
}
// Only a same-origin path is linked; a record cannot send the reader elsewhere.
const libraryPath=href=>/^\/[^/\\]/.test(href??'');
// A value as served: grouping and its own decimals only; no value is missing-as-zero.
function libraryMetric(metric) {
  if(LibraryLogic.numberOf(metric)===null)return '—';
  if(metric.unit==='x')return `${metric.value}×`;
  const decimals=(String(metric.value).split('.')[1]||'').length;
  if(decimals>20)return String(metric.value); // beyond what the formatter takes: shown exactly as served
  return Number(metric.value).toLocaleString('en-GB',{minimumFractionDigits:decimals,maximumFractionDigits:decimals});
}
// A catalogue row joins the store by folder: a match opens that run's Overview; no match keeps the row without the link.
const libraryRunKey=run=>Object.keys(contexts).find(key=>contexts[key].folder===run.id)??null;
const primaryArtifact=run=>run.artifacts.find(a=>a.available&&a.state!=='superseded');
// A pinned report or published model the store holds opens inside the app; any other file opens in its own tab.
function libraryArtifactLink(artifact,key,text,cls,aria='') {
  const pinned=`${artifact.href}&embedded=1`,report=window.DESIGN_WORKSPACE.reports.find(r=>r.href===pinned);
  const model=window.DESIGN_WORKSPACE.models.find(m=>m.href===pinned),owner=model&&modelOwnRun(model);
  const inApp=report?routeHref('W-Reports',report.id,null,key&&sameIssuer(report.issuerKey,contexts[key].issuerKey)?key:tracedRun(report)):owner?routeHref('W-Forecast',model.id,null,owner):null;
  const href=inApp??(libraryPath(artifact.href)?artifact.href:null);
  if(!href)return `<span>${esc(text)}</span>`;
  return `<a class="${cls}" href="${esc(href)}" ${inApp?'':'target="_blank" rel="noopener"'} ${aria?`aria-label="${esc(aria)}"`:''}>${esc(text)}${inApp?'':' ↗'}</a>`;
}
const libraryOpenText=artifact=>artifact.kind==='model'?'Open model':artifact.relationship==='related'?'Related report':'Open report';
function libraryRows() {
  const runs=catalogueRuns(),base=LibraryLogic.filterRuns(runs,{...libraryFilters,search:''});
  // Search also reads the issuer name and terms the store recorded for the joined run, appended after the served fields.
  const shadows=base.map(run=>{const held=contexts[libraryRunKey(run)];return {...run,workflow:[run.workflow,held?.issuer,...(held?.issuerTerms||[])].filter(Boolean).join(' ')};});
  const found=new Set(LibraryLogic.filterRuns(shadows,{search:libraryFilters.search}).map(r=>r.id)),matching=base.filter(r=>found.has(r.id));
  const rows=libraryState.sortKey?LibraryLogic.sortRuns(matching,libraryState.sortKey,libraryState.direction):matching;
  if(!rows.some(r=>r.id===libraryState.selected))libraryState.selected=rows[0]?.id??'';
  return {runs,rows};
}
const libraryCount=({runs,rows})=>`${rows.length} of ${plural(runs.length,'run')} · ${plural(new Set(rows.map(r=>r.issuer)).size,'issuer')}`;
const libraryCell=(primary,secondary,cls='')=>`<td><span class="cell-primary${cls}">${esc(primary)}</span><span class="cell-secondary">${esc(secondary)}</span></td>`;
const libraryMetricCell=(run,key)=>libraryCell(libraryMetric(run.metrics[key]),run.metrics[key]?.basis||'Not available',run.metrics[key]?'':' missing');
function libraryCompletion(run) {
  if(run.completion===null)return libraryCell('Not assessed','Checklist required');
  const done=run.checkpoints?`${run.checkpoints.done}/${run.checkpoints.total} requirements`:'';
  return `<td><span class="cell-primary">${esc(run.completion)}%</span><span class="progress-track" aria-hidden="true"><i style="width:${esc(Number(run.completion))}%"></i></span><span class="cell-secondary">${esc(done)}</span></td>`;
}
function libraryRow(run,selected) {
  const key=libraryRunKey(run),artifact=primaryArtifact(run);
  const identity=`<td><button class="library-run-name" type="button" data-library-select="${esc(run.id)}" aria-expanded="${selected}" aria-controls="run-detail" aria-label="${esc(`View ${run.name}: ${run.title}`)}">${esc(run.name)}<span class="ticker">${esc(run.issuer)}</span></button><span class="cell-secondary">${esc(run.title)}</span>${key?`<a class="run-link" href="${routeHref('W-Overview','overview',null,key)}" aria-label="${esc(`Open run: ${run.name}, ${run.id}`)}">Open run</a>`:''}</td>`;
  const deliverable=artifact?`<td>${libraryArtifactLink(artifact,key,libraryOpenText(artifact),'report-link',`${libraryOpenText(artifact)}: ${run.name}, ${artifact.label}`)}<span class="cell-secondary">Candidate HTML</span></td>`:libraryCell('Handoffs only','No report');
  return `<tr${selected?' class="selected"':''}>${identity}<td>${esc(run.sector)}</td>${libraryCell(libraryDate(run.date),run.period)}${libraryMetricCell(run,'leverage')}${libraryMetricCell(run,'coverage')}${libraryCompletion(run)}${deliverable}</tr>`;
}
function libraryResults({runs,rows}) {
  if(!runs.length)return window.DESIGN_APP?.problem?`<div class="library-empty"><h2>The library could not read this workspace</h2><p>Nothing can be listed until it can be read. Check the workspace folder in Settings, or quit and reopen the library.</p><a class="text-action" href="#W-Settings/workspace">Open Settings${icon('arrow-right')}</a></div>`:`<div class="library-empty"><h2>No runs in this workspace yet</h2><p>Start a new run, or choose another workspace folder in Settings.</p><a class="text-action" href="#W-Settings/workspace">Open Settings${icon('arrow-right')}</a></div>`;
  if(!rows.length)return '<div class="library-empty"><h2>No runs match these filters</h2><p>Try a wider range or include unavailable values. Workflow completeness is not assessed for retained runs.</p><button id="library-empty-reset" class="primary-action" type="button">Reset filters</button></div>';
  const sort=key=>libraryState.sortKey===key?libraryState.direction==='asc'?'ascending':'descending':'none';
  const head=LIBRARY_COLUMNS.map(([key,label])=>key?`<th scope="col" aria-sort="${sort(key)}"><button type="button" data-library-sort="${key}">${label} <span aria-hidden="true">↕</span></button></th>`:`<th scope="col">${label}</th>`).join('');
  return `<div class="table-scroll" role="region" aria-label="Issuer runs table; scroll horizontally for all columns" tabindex="0"><table class="library-table"><caption class="sr-only">Issuer runs, credit metrics, completeness and report availability</caption><thead><tr>${head}</tr></thead><tbody>${rows.map(r=>libraryRow(r,r.id===libraryState.selected)).join('')}</tbody></table></div><p class="hint">Dates refer to evidence, not execution. Ratios keep their original definitions.</p>`;
}
function libraryNav() {
  const runs=catalogueRuns(),f=libraryFilters,reports=runs.filter(LibraryLogic.hasReport).length,issuers=[...new Set(runs.map(r=>r.issuer))];
  const choice=(attrs,active,label,count,mark='')=>`<button type="button" class="nav-choice${active?' active':''}" ${attrs} aria-pressed="${active}">${mark}<span>${esc(label)}</span><span class="count">${count}</span></button>`;
  return `${choice('data-library-nav="all"',!f.issuer&&!f.availability,'All runs',runs.length)}${choice('data-library-nav="reports"',f.availability==='report',`Reports available`,reports)}<p class="eyebrow">Issuers · ${issuers.length}</p>${issuers.map(id=>{
    const mine=runs.filter(r=>r.issuer===id),names=new Set(mine.map(r=>r.name));
    return choice(`data-library-issuer="${esc(id)}" aria-label="${esc(`Filter ${names.size===1?mine[0].name:id}`)}"`,f.issuer===id,names.size===1?mine[0].name:id,mine.length,`<span class="monogram">${esc(id.slice(0,3))}</span>`);
  }).join('')}`;
}
function librarySources(run) {
  const sources=window.DESIGN_CATALOGUE?.sources||{};
  const ids=[...new Set([run.identity_source,run.sector_source,...Object.values(run.metrics).map(m=>m?.source),...run.ratings.map(r=>r.source)].filter(Boolean))];
  const block=id=>{
    const s=Object.hasOwn(sources,id)?sources[id]:null;
    if(!s)return `<div id="source-${esc(id)}" tabindex="-1"><p>${esc(id)} · source record not served</p></div>`;
    const quote=String(s.quote);
    return `<div id="source-${esc(id)}" tabindex="-1"><p>${esc(`${s.path} · line ${s.line}`)}</p><blockquote>${esc(quote.length>1500?`${quote.slice(0,1500)}… [full capture in linked file]`:quote)}</blockquote>${libraryPath(s.href)?`<a href="${esc(s.href)}" target="_blank" rel="noopener">Open retained source ↗</a>`:''}</div>`;
  };
  return `<details class="source-details" id="metric-sources"><summary>Sources &amp; definitions · ${ids.length} references</summary>${ids.map(block).join('')}</details>`;
}
function libraryMetricItem(run,name,key) {
  const metric=run.metrics[key];
  return `<div class="metric-item"><span class="metric-label">${name}</span><span class="metric-value">${esc(libraryMetric(metric))}${metric&&metric.unit!=='x'&&LibraryLogic.numberOf(metric)!==null?`<small>${esc(metric.unit)}</small>`:''}</span><p>${esc(metric?`${metric.period} · ${metric.basis}`:'Not established for this case.')}</p>${metric?.source?`<button class="tertiary-action" type="button" data-library-source="${esc(metric.source)}">View source ↗</button>`:''}</div>`;
}
function libraryDetail({rows}) {
  const run=rows.find(r=>r.id===libraryState.selected);
  if(!run)return '';
  const key=libraryRunKey(run),artifact=primaryArtifact(run);
  const open=[key?`<a class="secondary-action" href="${routeHref('W-Overview','overview',null,key)}">Open run</a>`:'',artifact?libraryArtifactLink(artifact,key,libraryOpenText(artifact),'primary-action'):libraryPath(run.handoff_href)?`<a class="primary-action" href="${esc(run.handoff_href)}" target="_blank" rel="noopener">Open primary handoff ↗</a>`:''].join('');
  const done=run.completion===null?['Workflow completeness · Not assessed','A verified checklist for this workflow has not been supplied. Available files and checked ratios do not establish end-to-end completion.']:[`Workflow completeness · ${run.completion}%`,run.checkpoints?`${run.checkpoints.done} of ${run.checkpoints.total} required checkpoints completed. This is workflow progress, not a credit score.`:'This is workflow progress, not a credit score.'];
  const artifacts=run.artifacts.length?run.artifacts.map(a=>`<li>${a.available?libraryArtifactLink(a,key,a.label,''):`<span>${esc(a.label)} · Unavailable</span>`}<small>${esc(a.issue||(a.state==='superseded'?'Retained failed attempt':`${a.relationship==='related'?'Related annual report · ':''}Candidate · file hashes checked at build`))}</small></li>`).join(''):'<li>No final deliverable has been indexed for this case.</li>';
  return `<div class="detail-head"><div><p class="eyebrow">Selected run</p><h2>${esc(run.name)}</h2><p class="cell-secondary">${esc(`${run.id} / ${run.title}`)}</p></div><div class="detail-actions">${open}</div></div><div class="detail-layout"><div><p>${esc(run.summary)}</p><h3>Scope &amp; open questions</h3><ul class="gap-list">${run.gaps.map(g=>`<li>${esc(g)}</li>`).join('')}</ul>${run.ratings.length?`<h3>Dated ratings</h3>${run.ratings.map(r=>`<p>${esc(`${r.label} · ${libraryDate(r.date)}`)}</p>`).join('')}`:''}<div class="completion-box"><strong>${esc(done[0])}</strong>${esc(done[1])}</div></div><div><div class="metric-grid">${Object.entries(METRIC_NAMES).map(([k,n])=>libraryMetricItem(run,n,k)).join('')}</div><h3>Deliverables &amp; revision history</h3><ul class="artifact-list">${artifacts}</ul>${librarySources(run)}</div></div>`;
}
const libraryAdvanced=()=>['basis','period','leverageMin','leverageMax','coverageMin','coverageMax'].filter(k=>libraryFilters[k]).length;
function libraryPanel() {
  const runs=catalogueRuns(),f=libraryFilters;
  const values=pick=>[...new Set(runs.map(pick).filter(Boolean))].sort();
  const select=(key,label,any,items,extra='')=>`<label>${label}<select id="library-${key}" data-library-filter="${key}">${[['',any],...items].map(([v,t])=>`<option value="${esc(v)}" ${f[key]===v?'selected':''}>${esc(t)}</option>`).join('')}</select></label>${extra}`;
  const plain=v=>[v,v],number=(key,label,hint)=>`<label>${label}<input id="library-${key}" data-library-filter="${key}" type="number" step="any" placeholder="${hint}" value="${esc(f[key])}"></label>`;
  const advanced=libraryAdvanced();
  return `<header class="block-head"><h2>Screening criteria</h2><span class="hint">Combined filters</span></header><div class="search-row"><label class="library-search"><span class="sr-only">Search issuer, run or sector</span>${icon('search')}<input id="library-query" data-library-filter="search" type="search" value="${esc(f.search)}" placeholder="Search issuer, run or sector…" autocomplete="off" aria-controls="library-results"></label><button id="library-clear" class="tertiary-action" type="button">Reset filters</button></div><div class="library-filters">${select('sector','Sector','All sectors',values(r=>r.sector).map(plain))}${select('workflow','Workflow','All workflows',values(r=>r.workflow).map(plain))}${select('completion','Completeness','Any completeness',[['75','75% or above'],['50','50% or above'],['100','100% complete'],['unassessed','Not assessed']])}${select('availability','Deliverables','All runs',[['report','Report available'],['handoff','No report available']])}</div><details id="metric-filters" ${advanced?'open':''}><summary>Credit metrics &amp; period <span id="metric-filter-count">${advanced?`· ${advanced} active`:''}</span></summary><div class="library-filters">${select('basis','Leverage basis','All bases · definitions differ',values(r=>r.metrics.leverage?.basis).map(plain))}${select('period','Financial period','All period types',values(r=>r.period_kind).map(plain))}${number('leverageMin','Leverage, minimum (x)','No minimum')}${number('leverageMax','Leverage, maximum (x)','No maximum')}${number('coverageMin','Coverage, minimum (x)','No minimum')}${number('coverageMax','Coverage, maximum (x)','No maximum')}</div><p class="hint">Numeric filters exclude unavailable values. Select a leverage basis to keep definitions consistent; coverage definitions remain visible on each row.</p></details>`;
}
// A panel rebuild shows an unreadable number box empty, so its stored 'invalid' bound is dropped to keep the filter and the control in agreement.
const clearInvalidBounds=()=>['leverageMin','leverageMax','coverageMin','coverageMax'].forEach(k=>{if(libraryFilters[k]==='invalid')libraryFilters[k]='';});
function libraryView() {
  clearInvalidBounds();
  const view=libraryRows();
  return `<div class="library-screen"><nav id="library-nav" class="library-nav" aria-label="Issuers">${libraryNav()}</nav><div class="library-main"><form id="library-filters" class="library-panel" role="search" aria-label="Screen issuer runs">${libraryPanel()}</form><section class="library-results-panel" aria-label="Run results"><p id="library-count" role="status" aria-live="polite">${libraryCount(view)}</p><div id="library-results">${libraryResults(view)}</div></section><section id="run-detail" class="run-detail" aria-label="Selected run details" tabindex="-1" ${view.rows.some(r=>r.id===libraryState.selected)?'':'hidden'}>${libraryDetail(view)}</section></div></div>`;
}
// Re-places the results from the current filters; the panel itself is only rebuilt on a reset so typing keeps its focus.
function updateLibrary(panel=false) {
  if(panel)clearInvalidBounds();
  const view=libraryRows();
  if(panel)$('library-filters').innerHTML=libraryPanel();
  $('library-nav').innerHTML=libraryNav();
  $('library-count').textContent=libraryCount(view);
  $('library-results').innerHTML=libraryResults(view);
  $('run-detail').innerHTML=libraryDetail(view);
  $('run-detail').hidden=!view.rows.some(r=>r.id===libraryState.selected);
  const advanced=libraryAdvanced();
  $('metric-filter-count').textContent=advanced?`· ${advanced} active`:'';
}
function reportList(context) {
  const ctx=contexts[context],all=window.DESIGN_WORKSPACE.reports,built=reportsBuiltFrom(context),others=ctx?issuerReports(context).filter(r=>!built.includes(r)):[];
  const rest=all.filter(r=>!built.includes(r)&&!others.includes(r));
  const none='No report was built from this run’s files';
  const row=r=>`<li class="report-row">${ctx&&!sameIssuer(r.issuerKey,ctx.issuerKey)&&!r.label.trim().startsWith(r.issuer)?`<span class="report-issuer">${esc(r.issuer)} · </span>`:''}<a class="text-action" href="${routeHref('W-Reports',r.id,null,ctx&&sameIssuer(r.issuerKey,ctx.issuerKey)?context:tracedRun(r))}">${esc(reportName(r))}${icon('arrow-right')}</a><span class="code">${esc(r.id)}</span>${r.status?`<span class="badge badge-gray">${esc(r.status)}</span>`:''} ${reportAcceptance(r).html}</li>`;
  const list=(cls,title,reports)=>reports.length?`<section class="${cls}"><h2>${esc(title)}</h2><ol class="report-list">${[...reports].sort(byBuild).map(row).join('')}</ol></section>`:'';
  if(!ctx)return `<p class="intro">${plural(all.length,'deliverable')} in this workspace.</p>${list('report-other','All deliverables',all)}${all.length?'':`<div class="missing-state"><h2>No deliverables yet</h2><p>A run writes its report here when it finishes.</p></div>`}`;
  const heading=!built.length&&!others.length?`<div class="missing-state"><div class="empty-symbol">${icon('file-text')}</div><h2>${none}</h2></div><a class="text-action" href="#W-Library/cases">Choose another case</a>`:`<p class="intro">${built.length?`${plural(built.length,'report')} built from ${esc(ctx.run)}’s files.`:`${none}.`}</p>`;
  return `${heading}${list('report-built','Built from this run',built)}${list('report-other',`Other ${ctx.issuer} reports`,others)}${list('report-rest','Other issuers’ reports',rest)}`;
}
function reportView(report,context) {
  const ctx=contexts[context],rows=report.builtFrom.map(b=>{
    if(!b.run)return `<tr><th scope="row">${esc(b.module)}</th><td>No matching run file</td><td>${esc(b.source)}</td><td>${b.sha256.slice(0,12)}</td></tr>`;
    const href=b.output?routeHref(b.module,modules[b.source].first,null,b.run,data[b.source].source):routeHref('W-Evidence','sources',null,b.run);
    return `<tr><th scope="row">${esc(b.module)}</th><td>${esc(contexts[b.run].run)}</td><td><a href="${href}">${esc(b.source.split('/').at(-1))}</a></td><td>${b.sha256.slice(0,12)}</td></tr>`;
  }).join('');
  const handoffs=new Set(report.builtFrom.map(b=>b.module)).size,unmatched=new Set(report.builtFrom.filter(b=>!b.run).map(b=>b.module)).size;
  const files=report.files.length?`<details class="built-from"><summary>Files in this deliverable · ${report.files.length}</summary><ul>${report.files.map(f=>`<li><a href="${esc(f.href)}" download>${esc(f.name)}</a></li>`).join('')}</ul></details>`:'';
  const status=[report.status,ctx?'':'No matching run'].filter(Boolean).join(' · ');
  return `<div class="report-tools"><label for="report-select">Report</label><select id="report-select">${[...runReports(context)].sort(byBuild).map(r=>`<option value="${esc(r.id)}" ${r.id===report.id?'selected':''}>${esc(reportName(r))}</option>`).join('')}</select>${status?`<span>${esc(status)}</span><i class="tool-sep" aria-hidden="true"></i>`:''}${reportAcceptance(report).html}<a href="${esc(report.download)}" download>Download original HTML</a><a href="${routeHref('W-Reports','list')}">All reports</a><a href="#W-Library/cases">Return to library</a></div><details class="built-from"><summary>Built from ${handoffs} handoffs · ${unmatched?`${unmatched} with no matching run file`:'byte-identical by SHA-256'}</summary><div class="table-scroll"><table><thead><tr><th scope="col">Module</th><th scope="col">Run</th><th scope="col">File</th><th scope="col">SHA-256 prefix</th></tr></thead><tbody>${rows}</tbody></table></div></details>${files}<div class="frame-host"><p class="frame-status" role="status">Loading report…</p><iframe id="report-preview" title="${esc(reportName(report))} · ${esc(report.issuer)} report" sandbox="allow-scripts allow-downloads" referrerpolicy="no-referrer" src="${esc(report.href)}"></iframe></div>`;
}
function settingsView() {
  const app=window.DESIGN_APP||{},issues=app.issues||[];
  return `<div class="settings"><section><h2>Workspace folder</h2><label class="run-field">Folder holding runs and deliverables<input id="workspace-path" value="${esc(app.workspace)}" ${app.policy_locked?'disabled':''} autocomplete="off"></label><p class="hint">${app.policy_locked?'This location is managed by your IT configuration.':'Use a local folder for offline access. Network shares and cloud placeholders need a connection.'}</p><div class="step-actions"><button id="save-workspace" class="primary-action" type="button" ${app.policy_locked?'disabled':''}>Save and reload</button><button id="refresh-library" class="secondary-action" type="button">Refresh library</button><button id="quit-library" class="tertiary-action" type="button">Quit library</button></div><p id="settings-status" role="status" aria-live="polite"></p></section><section><h2>Workspace issues · ${issues.length}</h2>${issues.length?`<ul class="issue-list">${issues.map(issue=>{const at=String(issue).indexOf(': ');return `<li>${at<0?`<span>${esc(issue)}</span>`:`<span class="code">${esc(String(issue).slice(0,at))}</span><span>${esc(String(issue).slice(at+2))}</span>`}</li>`;}).join('')}</ul>`:'<p>None found.</p>'}</section></div>`;
}
const HELP=`<div class="help-copy"><h2>Find and read a run</h2><p>The library screens every retained run and deliverable by sector, workflow, leverage and coverage. Search, Sector, Workflow, Completeness and Deliverables filters narrow the table, and Credit metrics &amp; period sets the leverage basis, financial period and leverage and coverage minimum and maximum. Search also matches the issuer names recorded in the store. Reset filters clears them, and a column heading sorts the table with missing values last. A missing value never matches a numeric filter. Only a few retained runs carry metrics and none has a recorded completeness yet, so most rows show — for Leverage and Coverage and Not assessed. Choose a run in the library. The Overview, Modules, Calendar, Forecast, Reports and Evidence tabs keep that run selected. Forecast shows the model published from the run’s files, the assumptions behind it and the handoffs it was built from. Browse by credit question or press / to search a name, section or module code, including absorbed aliases.</p><p>Select a finding’s View source action or a chart mark to open the evidence inspector. Escape returns to your reading position and source trigger.</p><h2>Move between the app and deliverables</h2><p>Reports lists every report in the workspace. A report opens inside the app, with this navigation beside it; its Built from list opens the module outputs it used, and a module output names the deliverables that used it.</p><h2>Start a new run</h2><p>Choose New run. Enter the issuer, workflow and dates, or load a saved context file. Choose the issuer folder, model and maximum USD spend. Validating is offline: the review shows the modules in order, the files no module can read and the report sections this run will not produce. Only Start run can call a model, after you approve the review, and only when the provider key is set in the environment that launched the app. If a module is rejected the run stops, keeps its work and makes no automatic paid retry.</p><p>A finished report has automated checks only: review the handoffs against the sources before relying on it.</p><h2>Runs stay separate</h2><p>Each run lists its own saved outputs. A module without one says so and offers other runs of the same issuer; another issuer is reached through the library. Reports list the runs they were built from, traced by SHA-256. Evidence is dated research, not current underwriting. Missing observations are not zero.</p><h2>Run notices</h2><p>The notice strip names the latest run and its state in words: running with the modules accepted so far, complete with a link to its reports, or stopped, failed or interrupted with the reason and the spend. View activity opens the run’s record. Resume appears on stopped, failed or interrupted notices, except a run stopped by a provider ruling. Dismiss hides the notice in that state on this computer; it never changes the run or its files, and the notice returns when the run reaches another state.</p><h2>Resuming a stopped run</h2><p>A run started from New run that stopped, failed or was interrupted can be resumed from its notice, from Run activity or from Recent runs. The resumed run is a new run: it keeps the accepted modules without a new model call and has its own spending cap, and what the stopped run spent is not counted against it. A run stopped by a provider ruling cannot be resumed.</p><h2>n.a. and n.m. in the cash flow model</h2><p>n.a. means not available: the calculation record has no value for that cell, and the reason is on the cell and under Why cells show n.a. It is never zero. n.m. means not modelled: the record does not model that line.</p><h2>Colour has a job</h2><div class="signal-key"><span><i class="series-0"></i>Blue · data and action</span><span><i class="series-1"></i>Navy · comparison</span><span><i class="signal-conditional"></i>Amber · conditional / attention</span><span>Grey · absent / unassessed</span></div><p>Dashed paths are conditional scenarios. Outflows use direction and signed values, not an adverse credit grade.</p><h2>Work offline, close or reopen</h2><p>The application, fonts and scripts are bundled; workspace files must also be available locally. Reports are sandboxed with external network requests blocked. Closing a tab leaves the library running; Quit library in Settings stops it.</p></div>`;
// Modules most likely to state the run's overall credit view come first.
const CALL_ORDER=['CP-6','CP-2','CP-3','CP-2D','CP-1','CP-0'];
function firstFinding(id) {
  const sections=data[id].sections,start=sections.findIndex(s=>s.heading==='Findings');
  if(start<0)return null;
  for(const [at,section] of sections.slice(start).entries()) {
    if(at&&section.level<=sections[start].level)break;
    const block=section.blocks.find(b=>b.type==='text');
    if(block)return {text:block.text,line:block.line};
  }
  return null;
}
function moduleSummary(id) {
  const {summary,call}=data[id];
  if(summary)return {kind:'summary',text:summary.bottomLine,line:summary.line,confidence:summary.confidence,limitation:summary.limitation};
  if(call)return {kind:'call',text:call.text,line:call.line};
  const finding=firstFinding(id);
  return finding&&{kind:'finding',...finding};
}
function leadModule(context,available) {
  const order=[...new Set([...CALL_ORDER,...groups.flatMap(g=>g[1].map(item=>item[0]))])].filter(id=>available.includes(id));
  for(const module of order) {
    const id=defaultOutput(module,context),summary=id&&moduleSummary(id);
    // A first finding is one paragraph of a module's work, so it never stands as the run's bottom line.
    if(summary&&summary.kind!=='finding')return {module,id,summary};
  }
  return null;
}
function summaryLead(lead) {
  if(lead) {
    const {module,id,summary}=lead;
    return `<section class="summary-lead"><p class="summary-owner">${esc(moduleNames[module])}</p><p class="call-quote">${rich(summary.text.replace(/\n/g,' '))}</p>${summary.kind==='summary'?readerFacts(summary):''}${sourceFooter(`${id}:${summary.line}`)}</section>`;
  }
  return '<section class="summary-lead empty"><p>No bottom line is stored for this run. Read the findings below.</p></section>';
}
function summaryCharts(available,context) {
  const charts=available.map(module=>defaultOutput(module,context)).filter(Boolean).flatMap(id=>{
    const visual=data[id].visual;
    if(CHART_RENDERERS[visual?.kind])return [visualMarkup(id,{...visual,fixed:true})];
    return (data[id].charts||[]).map(chart=>readerChart(id,chart));
  }).slice(0,4);
  return charts.length?`<div class="summary-charts">${charts.map(chart=>`<div class="summary-chart">${chart}</div>`).join('')}</div>`:'';
}
function summaryCard(module,context) {
  const id=defaultOutput(module,context),summary=id&&moduleSummary(id);
  const body=!id?`<p class="summary-note">${plural(moduleEntry(module,context).outputs.length,'saved output')}. Choose one to read its findings.</p>`:summary?`<div class="summary-text">${rich(summary.text.replace(/\n/g,' '))}</div>${summary.kind==='summary'?`<span class="badge badge-gray">Confidence: ${esc(summary.confidence)}</span>`:''}${sourceLink(`${id}:${summary.line}`)}`:'<p class="summary-note">No written findings in this output.</p>';
  return `<article class="summary-card" data-module="${esc(module)}" ${id?`data-output="${esc(id)}"`:''}><h3>${moduleLink(module)}</h3>${body}</article>`;
}
function summaryView(context) {
  const available=contextModules(context),built=reportsBuiltFrom(context),lead=leadModule(context,available),led=lead?.module;
  const questions=groups.map(([title,items])=>[title,items.filter(([id])=>available.includes(id)&&id!==led)]).filter(([,items])=>items.length);
  return `${summaryLead(lead)}${summaryCharts(available,context)}<div class="question-map">${questions.map(([title,items])=>`<section><h2>${esc(title)}</h2><div>${items.map(([id])=>summaryCard(id,context)).join('')}</div></section>`).join('')}</div>${built.length?`<section class="summary-deliverables"><h2>Deliverables from this run</h2>${built.map(r=>`<div class="deliverable"><a class="text-action" href="${routeHref('W-Reports',r.id,null,context)}">${esc(reportName(r))}${icon('arrow-right')}</a>${reportAcceptance(r).html}</div>`).join('')}</section>`:''}`;
}
// The retained-record wording for a run with no live record: the heading, and the note and link that follow the flow.
function retainedRecordHtml(ctx,withRecord=false) {
  return {head:`<div class="missing-state"><h2>Retained record · ${esc(ctx.run)}</h2>${withRecord?'':'<p>No live progress is recorded for this run in this workspace.</p>'}</div>`,tail:`<p class="caution">Live progress and spend are recorded only for runs started from New run in this workspace.</p>${moduleLink('W-NewRun','Open New run')}`};
}
function workspaceView(module,section) {
  const context=current?.context,ctx=contexts[context],available=ctx?contextModules(context):[];
  if(module==='W-Library')return libraryView();
  if(module==='W-NewRun')return '';
  if(module==='W-Settings')return settingsView();
  if(module==='W-Overview')return summaryView(context);
  if(module==='W-Calendar') {
    const events=context===calendarRun('CP-1A'),hedges=context===calendarRun('CP-2E');
    if(!events&&!hedges)return `<div class="missing-state"><h2>No calendar retained for this run</h2><p>No dates are inferred from other cases.</p></div>${moduleLink('W-Evidence','Review available evidence')}<a class="text-action switch-case" href="#W-Library/cases">Choose another case</a>`;
    return `${events?eventTimeline():hedgeChart(pins['CP-2E'],data[pins['CP-2E']].visual)}${moduleLink(events?'CP-1A':'CP-2E','Open owning module')}`;
  }
  if(module==='W-Evidence')return `<p class="intro">Source PDFs aren’t included; page references point to the originals.</p>${sourceInventory(context)}`;
  if(module==='W-Reports') {
    const report=window.DESIGN_WORKSPACE.reports.find(r=>r.id===section);
    return report?reportView(report,context):reportList(context);
  }
  if(module==='W-Forecast')return forecastView(context,section);
  if(module==='CP-OS') {
    const flow=`<ol class="activity-flow"><li><h3>Analytical outputs</h3><p>${plural(outputCount(context),'saved output')}</p>${outputCount(context)?moduleLink('W-Evidence','Inspect retained outputs'):''}</li><li><h3>Delivery</h3><p>${reportsBuiltFrom(context).length?`${plural(reportsBuiltFrom(context).length,'report')} built from this run’s files.`:'No report was built from this run’s files.'}</p>${reportsBuiltFrom(context).length?moduleLink('W-Reports','View reports'):''}</li></ol>`;
    if(/^web-[a-f0-9]{32}$/.test(context||''))return `<section id="run-activity" data-run="${esc(context)}"><h2>Run record · ${esc(ctx.run)}</h2><p class="hint">Loading run activity…</p></section>${flow}`;
    const retained=retainedRecordHtml(ctx);
    return `${retained.head}${flow}${retained.tail}`;
  }
  if(module==='W-Help')return HELP;
  return '';
}
function updateWorkspaceChrome(module) {
  const ctx=contexts[current.context],isHome=!ctx||appDestinations.has(module);
  const moduleId=ctx&&(lastSection.get(current.context+':module')||ctx.first),period=current.output?data[current.output].period:ctx?.period;
  const title=isHome?(module==='W-Library'?'Issuer library':moduleNames[module]):ctx.title;
  document.querySelector('.issuer').innerHTML=`<div class="issuer-title"><h1 title="${esc(title)}">${esc(title)}</h1>${isHome?'':`<div class="issuer-meta"><span class="code">${esc(ctx.run)}</span><a href="#W-Library/cases">Change case</a></div>`}</div>${module==='W-Library'?`<div class="page-actions"><a class="secondary-action" href="#W-Reports/list">${icon('files')}All reports</a><a class="primary-action" id="library-new-run" href="#W-NewRun/run">${icon('plus')}New run</a></div>`:''}${isHome?'':`<div class="scope">${icon('calendar-days')}<strong>${esc(period)}</strong></div>`}`;
  document.querySelector('.workspace-tabs').hidden=isHome;
  if(!isHome)document.querySelector('.workspace-tabs').innerHTML=[['W-Overview','Overview','layout-grid'],[moduleId,'Modules','layers'],['W-Calendar','Calendar','calendar-days'],['W-Forecast','Forecast','chart-no-axes-combined'],['W-Reports','Reports','files'],['W-Evidence','Evidence','folder-open']].map(([id,label,img])=>{
    const sections=navigationSections(id,current.context,resolveOutput(id,current.context,lastFile.get(`${current.context}:${id}`))),remembered=lastSection.get(current.context+':'+id),section=sections.some(s=>s[0]===remembered)?remembered:sections[0][0];
    return `<a href="${routeHref(id,section)}" ${(label==='Modules'?isAnalytical(module):id===module)?'aria-current="page"':''}>${icon(img)}${label}</a>`;
  }).join('');
  const report=isReportRoute(module,current.section);
  $('workbench').classList.toggle('report-workspace',report);
  $('workbench').classList.toggle('library-workspace',isHome);
  // The navigator is resident only where its modules are the subject; elsewhere it opens from the Modules button.
  $('workbench').classList.toggle('tools-workspace',!isHome&&!report&&module!=='W-Overview'&&!isAnalytical(module));
  $('content').classList.toggle('report-content',report);
  // The rail shows where you are, and its run-level links keep the selected run.
  const rail=label=>document.querySelector(`.rail [data-place="${label}"]`);
  const place={'W-Library':'Issuer library','W-NewRun':'New run','W-Settings':'Settings','W-Help':'Help','W-Reports':'Reports','CP-OS':'Run activity'}[module]||'Research workspace';
  document.querySelectorAll('.rail a[data-place]').forEach(link=>{
    const here=link.dataset.place===place;
    link.classList.toggle('rail-active',here);
    if(here)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
  });
  rail('Research workspace').hidden=rail('Run activity').hidden=!Object.keys(contexts).length;
  rail('Reports').hidden=!window.DESIGN_WORKSPACE.reports.length&&!Object.keys(contexts).length;
  if(ctx) {
    rail('Research workspace').href=routeHref('W-Overview','overview');
    rail('Run activity').href=(typeof shownRunHref==='function'&&shownRunHref())||routeHref('CP-OS','activity');
    rail('Reports').href=routeHref('W-Reports','list');
  }
  const app=window.DESIGN_APP||{};
  $('app-problem').hidden=!app.problem;
  $('app-problem').textContent=app.problem?`The workspace could not be read: ${app.problem}`:'';
}
