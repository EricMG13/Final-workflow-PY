'use strict';
// What the app does to the server: the New run steps and Settings. Only Start can reach a provider.
async function appRequest(url,body,multipart=false){
  const headers=body===undefined?{}:{'X-Issuer-Library':'1',...multipart?{}:{'Content-Type':'application/json'}};
  const response=await fetch(url,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:multipart?body:JSON.stringify(body),cache:'no-store'});
  if(!response.ok){const error=new Error(await response.text());error.status=response.status;throw error;}
  return response.json();
}
const WORKFLOW_ACTIVE=['running'];
const workflowTitle=value=>String(value).replace(/_/g,' ').replace(/\b[a-z]/g,letter=>letter.toUpperCase());
const STATE_BADGE={running:'blue',complete:'navy',stopped:'attention',failed:'attention',interrupted:'attention'};
const textNode=(tag,value)=>{const node=document.createElement(tag);node.textContent=value;return node;};
// Why a run stopped, in words a reader can act on. The redacted message follows the sentence.
const STOP_COPY={budget:'Stopped: the next model call would pass the spending cap. Resuming keeps the accepted modules; the resumed run has its own cap.',checker:'Stopped: a module\'s handoff did not pass its check within the allowed turns.',provider:'Stopped: the model provider returned an error or an unknown charge.',interrupted:'Stopped: the run was interrupted before a response was retained.',ruling:'Failed: a provider ruling or pause is in force.'};
function stopSentence(status){return WORKFLOW_ACTIVE.includes(status.state)||status.state==='complete'?'':STOP_COPY[status.reason]||'';}
// A raw state or engine prefix is never shown: the five states have plain words.
const STATE_WORD={running:'Running',complete:'Complete',stopped:'Stopped',failed:'Failed',interrupted:'Interrupted'};
const stateWord=state=>STATE_WORD[state]||'Not running';
// WEB-04CD5A5D: the short form of an app run id, as the grey badges elsewhere show it; the full id stays in a title.
function shortRunId(id){const match=/^web-([a-f0-9]{8})[a-f0-9]{24}$/.exec(String(id));return match?`WEB-${match[1].toUpperCase()}`:String(id);}
// The day a run started, from the time of its first recorded event; '' when none was recorded (never guessed).
function startedOn(job){const day=typeof job?.started_at==='string'?job.started_at.slice(0,10):'',shown=displayDate(day);return shown!==day?shown:'';}
// A resumed run is a new execution with its own cap; the cap only has to be a positive decimal, as the engine requires.
const DECIMAL=/^\d+(\.\d+)?$/;
const positiveAmount=value=>DECIMAL.test(value)&&/[1-9]/.test(value);
// A bare module code in an engine message becomes "<module name> (<code>)" where the run names it.
function nameModuleCodes(text,details){
  const list=Array.isArray(details)?details:[];
  return String(text).replace(/(?<!\()\bCP-[A-Z0-9]+\b(?!\))/g,code=>{const title=list.find(item=>item?.id===code)?.title;return title&&title!==code?`${title} (${code})`:code;});
}
// hasDesc: the caller also prints describeModule, which says more than the engine's message for a running job.
function stopText(status,hasDesc=false){
  const sentence=stopSentence(status),message=status.message?nameModuleCodes(status.message,status.module_details):'';
  if(sentence)return message?`${sentence} ${message}`:sentence;
  const word=stateWord(status.state);
  return message&&!(hasDesc&&WORKFLOW_ACTIVE.includes(status.state))?`${word}: ${message}`:word;
}
// Whether a finished run can be reviewed again with its accepted work retained (New run's Resume): the states jobs.go resumes.
// A ruling or pause is not a stop that more budget or a retry can change, so it is never resumable.
const resumable=status=>['stopped','failed','interrupted'].includes(status.state)&&status.reason!=='ruling';
// The module step, with a stop between modules (after module_accepted, before the next module_started) read as the accepted step:
// progress.module is then the module that was accepted, not one the run stopped in.
const moduleStep=p=>p?.step==='stopped'&&p.stopped_during==='accepted'?'accepted':p?.step;
function describeModule(status,modules,nameOf){
  const p=status.progress||{},moduleId=p.module,active=WORKFLOW_ACTIVE.includes(status.state),step=moduleStep(p);
  // A stop after every module was accepted happened in delivery, not in the last module.
  if(p.step==='delivering')return active?'delivering the report':'stopped while delivering the report';
  if(p.step==='stopped'&&(p.stopped_during==='delivering'||(modules.length>0&&p.accepted>=modules.length)))return 'stopped while delivering the report';
  if(p.step==='delivered')return 'report delivered';
  if(!moduleId)return '';
  const index=modules.indexOf(moduleId),where=index>=0?` (${index+1} of ${modules.length})`:'',turn=p.turn&&p.max_turns?`, turn ${p.turn} of ${p.max_turns}`:'';
  if(step==='running')return `${active?'running':'stopped during'} ${nameOf(moduleId)}${turn||where}`;
  if(step==='repairing')return `${active?'repairing':'stopped while repairing'} ${nameOf(moduleId)} after a rejected draft${turn}`;
  if(step==='started')return `${active?'running':'stopped during'} ${nameOf(moduleId)}${where}`;
  if(step==='accepted')return `${active||p.step!=='stopped'?`${nameOf(moduleId)} accepted`:`stopped after ${nameOf(moduleId)}`}${where}`;
  if(p.step==='stopped')return `stopped during ${nameOf(moduleId)}${where}`;
  return '';
}
// The module description as its own sentence: capitalised, ended with a full stop, and the counts kept whole across a line break.
function descSentence(desc){
  if(!desc)return '';
  const kept=desc.replace(/ \((\d+) of (\d+)\)/g,'\u00a0($1\u00a0of\u00a0$2)').replace(/turn (\d+) of (\d+)/g,'turn\u00a0$1\u00a0of\u00a0$2');
  return `${kept[0].toUpperCase()}${kept.slice(1)}.`;
}
// The status sentence and the module description, each on its own line.
function summaryLines(head,desc){
  const lines=[textNode('span',head)];
  if(desc)lines.push(textNode('span',descSentence(desc)));
  for(const line of lines)line.className='summary-line';
  return lines;
}
function spendText(status){
  const p=status.progress||{},spent=status.spent_usd??p.spent_usd;
  if(spent==null)return 'Spend appears after CP-OS records a completed model response.';
  if(spent==='unknown')return 'Recorded spend could not be read; it may be above zero.';
  if(WORKFLOW_ACTIVE.includes(status.state))return p.cap_usd!=null&&p.held_usd!=null?`Recorded spend: USD ${spent} of a USD ${p.cap_usd} cap; the next call holds USD ${p.held_usd}`:`Recorded spend: USD ${spent}`;
  return p.cap_usd!=null?`Recorded spend: USD ${spent} of a USD ${p.cap_usd} cap`:`Recorded spend: USD ${spent}`;
}
// One line of a run's event log, in words.
function eventText(event,titleOf){
  const title=titleOf(event.module);
  switch(event.event){
    case 'module_started':return `Started ${title}`;
    case 'turn':return `Turn ${event.turn} of ${event.max_turns} · spend USD ${event.spent_usd} of USD ${event.cap_usd}; this call holds USD ${event.held_usd}`;
    case 'draft_rejected':return `Draft of ${title} rejected · ${event.writes_left} ${event.writes_left===1?'write':'writes'} left`;
    case 'module_accepted':return `Accepted ${title}`;
    case 'delivery_started':return 'Delivery started';
    case 'delivered':return 'Report delivered';
    case 'stopped':return STOP_COPY[event.reason]||`Stopped (${event.reason})`;
    default:return String(event.event);
  }
}
// "8 November 2026 · 09:00:00" from an event's ISO time (the table says UTC), the date only when it differs from the row above;
// a missing or malformed time is a dash, never a guess.
function eventTime(at,previousDay=''){
  const match=/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})/.exec(String(at||''));
  if(!match)return '—';
  return match[1]===previousDay?match[2]:`${displayDate(match[1])} · ${match[2]}`;
}
const eventDay=at=>/^(\d{4}-\d{2}-\d{2})T\d{2}:\d{2}:\d{2}/.exec(String(at||''))?.[1]||'';
// The events table in its bordered card, shared by the live view and the retained one.
function activityLog(events,titleOf){
  const table=document.createElement('table');table.className='activity-log';
  table.append(textNode('caption','Events (UTC)'));
  const headRow=document.createElement('tr');headRow.append(textNode('th','Time'),textNode('th','Event'));
  const thead=table.appendChild(document.createElement('thead'));thead.append(headRow);
  const body=table.appendChild(document.createElement('tbody'));
  let day='';
  for(const event of events){const row=document.createElement('tr');row.append(textNode('td',eventTime(event.at,day)),textNode('td',eventText(event,titleOf)));body.append(row);day=eventDay(event.at)||day;}
  const card=document.createElement('div');card.className='table-scroll';card.tabIndex=0;card.setAttribute('role','region');card.setAttribute('aria-label','Run events');card.append(table);
  return card;
}
// A run with no live status (404) is a retained record, the page's wording for runs not started from New run. If its
// event log still exists, the log and the last spend it recorded are shown; the "none recorded" sentence only when there is none.
function showRetainedRecord(section,id,events){
  const parts=retainedRecordHtml(contexts[id],events.length>0);
  section.insertAdjacentHTML('afterend',parts.head);
  const head=section.nextElementSibling;
  section.remove();
  if(events.length){
    const spent=[...events].reverse().find(event=>event.spent_usd);
    const extra=[];
    if(spent)extra.push(textNode('p',`Last recorded spend: USD ${spent.spent_usd}`));
    extra.push(activityLog(events,code=>code||''));
    head.after(...extra);
  }
  document.getElementById('content').insertAdjacentHTML('beforeend',parts.tail);
}
// Fills the Run activity section of an app run from its status and its event log. No retry: a
// failed fetch is said on the page. A reply that lands after the reader left the page changes nothing.
async function loadRunActivity(section){
  const id=section.dataset.run,hint=section.querySelector('.hint');
  try{
    const status=await appRequest(`/api/runs/status?id=${encodeURIComponent(id)}`),record=await appRequest(`/api/runs/events?id=${encodeURIComponent(id)}`);
    if(!section.isConnected)return;
    const modules=Array.isArray(status.modules)?status.modules:[],details=Array.isArray(status.module_details)?status.module_details:[];
    const titleOf=code=>details.find(item=>item?.id===code)?.title||code||'';
    const desc=describeModule(status,modules,titleOf),head=stopText(status,!!desc),events=Array.isArray(record.events)?record.events:[];
    const parts=[textNode('p',''),textNode('p',spendText(status))];
    parts[0].append(...summaryLines(head,desc));parts[0].className='activity-summary';parts[0].setAttribute('aria-live','polite');
    if(resumable(status)){
      const resume=textNode('a','Resume this run');resume.className='text-action';resume.href=`#W-NewRun/run?resume=${encodeURIComponent(id)}`;
      resume.addEventListener('click',event=>{if(!mayDiscardDraft())event.preventDefault();});
      parts.push(resume);
    }
    if(events.length)parts.push(activityLog(events,titleOf));
    else{const none=textNode('p','No events were recorded for this run.');none.className='hint';parts.push(none);}
    if(record.complete===false){const note=textNode('p','The record is incomplete: the log was cut or stopped mid-write.');note.className='caution';parts.push(note);}
    hint.replaceWith(...parts);
  }catch(error){
    if(!section.isConnected)return;
    if(error.status===404){
      let events=[];
      try{const record=await appRequest(`/api/runs/events?id=${encodeURIComponent(id)}`);events=Array.isArray(record.events)?record.events:[];}
      catch(inner){console.warn('Run activity: no event log for a run without a live status',inner);}
      if(section.isConnected)showRetainedRecord(section,id,events);
      return;
    }
    const note=document.createElement('div'),detail=document.createElement('details');
    note.className='caution';detail.append(textNode('summary','Technical detail'),textNode('p',error.message));
    note.append(textNode('p','Could not load this run\'s live record. Reload the library to try again.'),detail);
    hint.replaceWith(note);
  }
}
// The app-wide run watcher: one list request at load, then every 5 s while a run is active. It sets
// runMark (the title prefix), the rail mark and the run-state strip, and notifies when a run this page
// saw running finishes.
let runMark='',titleBase='';
const runWatch={timer:null,busy:false,states:new Map(),last:null,jobs:[],shown:null,memory:{}};
function applyTitle(){if(titleBase)document.title=`${runMark}${titleBase} · Issuer Library`;}
function runTarget(job){return `${job.state==='complete'?'W-Reports/list':'W-Overview/overview'}?c=${encodeURIComponent(job.id)}`;}
function reloadApp(){location.reload();}
function describeMark(job){
  const modules=Array.isArray(job.modules)?job.modules:[],accepted=job.progress?.accepted,word=stateWord(job.state).toLowerCase();
  if(WORKFLOW_ACTIVE.includes(job.state)){
    const count=modules.length&&Number.isInteger(accepted)?`${accepted}/${modules.length}`:'';
    return{mark:count?`● ${count} · `:'● ',symbol:'●',label:`Run activity — run ${word}`,kind:'running'};
  }
  const done=job.state==='complete';
  return{mark:done?'✓ ':'! ',symbol:done?'✓':'!',label:`Run activity — run ${word}`,kind:done?'complete':'stopped'};
}
// Dismissals are kept per viewer, as the state each job id was dismissed in. Without storage the notice
// stays dismissed for this page only, and the next load shows it again.
const DISMISS_KEY='issuer-library.run-strip-dismissed';
function readDismissed(){
  let stored={};
  try{const value=JSON.parse(localStorage.getItem(DISMISS_KEY)||'{}');if(value&&typeof value==='object'&&!Array.isArray(value))stored=value;}
  catch(error){console.warn('Run notice dismissals could not be read; a dismissed notice shows again after a reload',error);}
  return{...stored,...runWatch.memory};
}
function dismissRun(job){
  runWatch.memory[job.id]=job.state;
  try{localStorage.setItem(DISMISS_KEY,JSON.stringify(readDismissed()));}
  catch(error){console.warn('Run notice dismissal could not be saved; the notice shows again after a reload',error);}
}
// The active job if any; otherwise the most recently started job that is not running. The rail mark and title follow
// that job; the strip shows it unless it was dismissed in its present state (Dismiss hides only the strip, and never falls back
// to an older job). The list is newest first, and a job that left it keeps the last one seen.
function chooseShown(jobs){
  const dismissed=readDismissed(),open=job=>dismissed[job.id]!==job.state,running=jobs.filter(job=>WORKFLOW_ACTIVE.includes(job.state));
  if(running.length){const live=running.find(open);return{mark:live||running[0],strip:live||null};}
  const candidate=jobs.find(job=>STATE_WORD[job.state])||runWatch.last;
  if(!candidate||!STATE_WORD[candidate.state])return{mark:null,strip:null};
  return{mark:candidate,strip:open(candidate)?candidate:null};
}
const jobRoute=(place,job)=>`#${place}?c=${encodeURIComponent(job.id)}`;
function stripView(job){
  const word=stateWord(job.state),title=`Run ${word.toLowerCase()} · ${job.issuer||job.id}`;
  const activity={label:'View activity',href:jobRoute('CP-OS/activity',job),reload:true};
  if(WORKFLOW_ACTIVE.includes(job.state)){
    const modules=Array.isArray(job.modules)?job.modules:[],accepted=job.progress?.accepted;
    const details=Array.isArray(job.module_details)?job.module_details:[];
    const desc=describeModule(job,modules,id=>details.find(item=>item?.id===id)?.title||id);
    const count=modules.length&&Number.isInteger(accepted)?`${accepted} of ${modules.length} modules accepted`:desc;
    return{tone:'brand',icon:'activity',title,lines:count?[count]:[],actions:[activity]};
  }
  if(job.state==='complete')return{tone:'grey',icon:'circle-check',title,lines:[],actions:[{label:'View reports',href:jobRoute('W-Reports/list',job),reload:true}]};
  const actions=[activity];
  if(resumable(job))actions.push({label:'Resume',href:`#W-NewRun/run?resume=${encodeURIComponent(job.id)}`,reload:false});
  return{tone:'amber',icon:'triangle-alert',title,lines:[stopText(job),spendText(job)],actions};
}
function stripLine(line,i){const node=textNode('p',line);node.className=i===0?'strip-text':'strip-text strip-spend';node.setAttribute('aria-live','off');return node;}
function showRunStrip(job){
  const strip=document.getElementById('run-strip');
  if(!strip)return;
  if(!job){strip.hidden=true;strip.removeAttribute('data-key');strip.replaceChildren();return;}
  const view=stripView(job),key=`${job.id}|${job.state}`;
  // Only a change of state is announced: a poll that moves the count rewrites the quiet line in place.
  const line=strip.querySelector('.strip-text');
  if(strip.dataset.key===key&&!strip.hidden){
    if(line&&view.lines.length){line.textContent=view.lines[0];return;}
    if(line){line.remove();return;}
    if(!view.lines.length)return;
    // Supporting lines first appearing in an unchanged state are added after the title, without a rebuild or a new announcement.
    strip.querySelector('.strip-title').after(...view.lines.map(stripLine));return;
  }
  strip.dataset.key=key;strip.dataset.tone=view.tone;strip.hidden=false;
  const icon=document.createElement('span');icon.className='strip-icon';icon.dataset.icon=view.icon;icon.setAttribute('aria-hidden','true');
  const body=document.createElement('div');body.className='strip-body';
  const title=textNode('strong',view.title);title.className='strip-title';body.append(title);
  body.append(...view.lines.map(stripLine));
  const actions=document.createElement('div');actions.className='strip-actions';
  for(const action of view.actions){const link=textNode('a',action.label);link.href=action.href;link.dataset.stripLink=action.reload?'reload':'go';actions.append(link);}
  body.append(actions);
  const close=document.createElement('button'),mark=document.createElement('img');
  close.type='button';close.className='strip-close';close.title='Dismiss';close.setAttribute('aria-label','Dismiss run notice');
  mark.src='icons/x.svg';mark.alt='';close.append(mark);
  strip.replaceChildren(icon,body,close);
}
function showRunMark(job){
  const view=job?describeMark(job):{mark:'',symbol:'',label:'',kind:''},rail=document.getElementById('run-mark');
  runMark=view.mark;
  if(rail){rail.hidden=!job;rail.textContent=view.symbol;rail.dataset.state=view.kind;}
  const link=document.querySelector('.rail [data-place="Run activity"]');
  if(link){
    if(job){link.setAttribute('aria-label',view.label);link.setAttribute('href',jobRoute('CP-OS/activity',job));}
    else{link.removeAttribute('aria-label');link.setAttribute('href',current?.context?routeHref('CP-OS','activity'):'#CP-OS/activity');}
  }
  applyTitle();
}
// The Run activity rail link goes to the job the mark shows; null leaves the selected run's link.
function shownRunHref(){return runWatch.shown?jobRoute('CP-OS/activity',runWatch.shown):null;}
// The job whose own page is open: its Run activity page, or New run's progress panel showing it. Its stop sentence is already
// on that page, so the strip stays away there (not a dismissal; it returns on other screens).
let panelRunId=null;
function viewShowsRun(job){
  if(current?.module==='CP-OS'&&current.section==='activity'&&current.context===job.id)return true;
  return current?.module==='W-NewRun'&&panelRunId===job.id;
}
function presentRun(){
  const chosen=chooseShown(runWatch.jobs),mark=chosen.mark,strip=chosen.strip&&!viewShowsRun(chosen.strip)?chosen.strip:null;
  runWatch.shown=mark;runWatch.strip=strip;
  if(mark&&!WORKFLOW_ACTIVE.includes(mark.state))runWatch.last=mark;
  showRunMark(mark);showRunStrip(strip);
}
document.addEventListener('click',event=>{
  const close=event.target.closest?.('#run-strip .strip-close'),link=event.target.closest?.('#run-strip a[data-strip-link]');
  if(close&&runWatch.strip){dismissRun(runWatch.strip);presentRun();return;}
  if(!link)return;
  event.preventDefault();
  if(!mayDiscardDraft())return;
  location.hash=link.getAttribute('href');
  if(link.dataset.stripLink==='reload')reloadApp();
});
const canNotify=()=>typeof Notification!=='undefined'&&Notification.permission==='granted';
// A tab that cannot build the browser notice says so, so the server still shows the native one.
const runListUrl=()=>canNotify()?'/api/runs/list':'/api/runs/list?notify=0';
// The raw engine message is never shown here: it can hold bare module codes. A stop reads "<issuer>: <stop sentence>".
function noticeBody(job){
  if(job.state==='complete')return `${job.issuer||'The'} run complete`;
  const sentence=stopSentence(job);
  if(sentence)return job.issuer?`${job.issuer}: ${sentence}`:sentence;
  const word=stateWord(job.state).toLowerCase();
  return job.issuer?`${job.issuer} run ${word}`:`Run ${word}`;
}
function notifyFinished(job){
  if(!canNotify())return;
  const note=new Notification('Issuer Library',{body:noticeBody(job),tag:job.id});
  note.onclick=()=>{window.focus();if(mayDiscardDraft()){location.hash=runTarget(job);reloadApp();}};
}
async function watchRuns(){
  if(runWatch.busy)return;
  runWatch.busy=true;
  try{
    const jobs=await appRequest(runListUrl()),active=jobs.filter(job=>WORKFLOW_ACTIVE.includes(job.state));
    for(const job of jobs){
      if(runWatch.states.get(job.id)==='running'&&job.state!=='running')notifyFinished(job);
      runWatch.states.set(job.id,job.state);
    }
    runWatch.jobs=jobs;
    presentRun();
    if(active.length&&!runWatch.timer)runWatch.timer=setInterval(watchRuns,5000);
    if(!active.length&&runWatch.timer){clearInterval(runWatch.timer);runWatch.timer=null;}
  }catch(error){console.warn('Run watch failed; the next check will retry while a run is active',error);}
  finally{runWatch.busy=false;}
}
// The chosen folder's name is dropped: paths are relative to it, as the launcher's --sources are.
const folderPath=file=>(file.webkitRelativePath||file.name).split('/').slice(file.webkitRelativePath?1:0).join('/');
// The launcher skips dot paths without listing them, so they are not worth uploading.
const uploadable=files=>[...files].filter(file=>!folderPath(file).split('/').some(part=>part.startsWith('.')));

function installNewRun(){
  let context=null,review=null,busy=false,running=false,polling=false,listing=false,watch=null,activeListed=false,lastRows='';
  function message(value){$('new-run-message').textContent=value;}
  function stage(name){
    for(const id of ['context','source','review','progress'])$(id+'-step').hidden=id!==name;
    panelRunId=name==='progress'?review?.id||null:null;presentRun();
    document.querySelectorAll('[data-stage]').forEach(item=>{if(item.dataset.stage===name)item.setAttribute('aria-current','step');else item.removeAttribute('aria-current');});
    message('');$(name+'-step').querySelector('h2').focus();
  }
  function controls(){
    $('review-run').disabled=busy||running;
    $('start-run').disabled=busy||running||!review?.provider_ready||!$('run-confirm').checked;
    $('revise-run').disabled=busy||running;
    $('resume-run').disabled=busy||running||!resumeBudgetOk();
    $('run-sources').disabled=busy||running;
    const wanted=(running||activeListed)&&!$('new-run').hidden;
    if(wanted&&!watch)watch=setInterval(poll,2000);
    if(!wanted&&watch){clearInterval(watch);watch=null;}
  }
  // The server requires a non-empty cap and the engine a positive one; the resumed run's spend starts at zero, so the old spend is not compared.
  const resumeBudgetOk=()=>positiveAmount($('resume-budget').value.trim());
  function titleOf(id){return (Array.isArray(review?.module_details)?review.module_details:[]).find(item=>item?.id===id)?.title||id;}
  // Shows one recorded run's progress panel: a Recent-runs click, or the run strip's Resume link.
  function openJob(job){
    const modules=Array.isArray(job.modules)?job.modules:[],details=Array.isArray(job.module_details)?job.module_details:[];
    review={...job,modules,module_details:details};running=WORKFLOW_ACTIVE.includes(job.state);stage('progress');showStatus(job);controls();if(running)poll();
  }
  // #W-NewRun/run?resume=<id> opens that run's panel once; the query is then dropped so a revisit does not reopen it.
  async function openRequested(){
    const id=new URLSearchParams(location.hash.split('?')[1]||'').get('resume');
    if(!id||$('new-run').hidden||busy)return;
    history.replaceState(null,'','#W-NewRun/run');
    if(running){message('Another run is in progress. Resume this run after it finishes.');return;}
    try{const job=(await appRequest(runListUrl())).find(item=>item.id===id);if(job)openJob(job);else message('That run is no longer in the recent list.');}
    catch(error){message('Could not open that run. Details: '+error.message);}
  }
  async function recent(){
    if(listing)return;listing=true;
    try{
      // Only the app-wide watcher builds the browser notice, so this page's poll never speaks for the tab.
      const jobs=await appRequest('/api/runs/list?notify=0');
      const key=JSON.stringify(jobs);if(key===lastRows){controls();return;}
      if(!jobs.length){const link=textNode('a','Issuer library');link.href='#W-Library/cases';$('recent-jobs').replaceChildren('No runs started from this app are recorded in this workspace yet. Earlier runs are in the ',link,'.');lastRows=key;activeListed=false;controls();return;}
      const active=job=>WORKFLOW_ACTIVE.includes(job.state);
      // Newest started first whatever the state; a run with no recorded start follows the dated ones in the server's order.
      const startedMs=job=>{const ms=typeof job.started_at==='string'?Date.parse(job.started_at):NaN;return Number.isNaN(ms)?null:ms;};
      const ordered=jobs.map((job,index)=>[job,index]).sort(([a,i],[b,j])=>{const x=startedMs(a),y=startedMs(b);if(x!==null&&y!==null&&x!==y)return y-x;if((x===null)!==(y===null))return x===null?1:-1;return i-j;}).map(([job])=>job);
      const table=document.createElement('table'),head=document.createElement('tr'),body=document.createElement('tbody');
      head.append(...['Issuer','Workflow','Module','State','Spend (USD)'].map(label=>textNode('th',label)));
      const thead=document.createElement('thead');thead.append(head);
      for(const job of ordered){
        const modules=Array.isArray(job.modules)?job.modules:[],details=Array.isArray(job.module_details)?job.module_details:[];
        const row=document.createElement('tr'),owner=document.createElement('th'),button=textNode('button',[job.issuer,shortRunId(job.id),startedOn(job)].filter(Boolean).join(' · '));
        owner.scope='row';button.type='button';button.className='text-button';button.title=job.id;
        button.addEventListener('click',()=>openJob(job));
        owner.append(button);
        const workflow=textNode('td','');
        if(job.pathway){const badge=textNode('span',workflowTitle(job.pathway));badge.className='badge badge-blue';badge.prepend(document.createElement('i'));workflow.append(badge);}else workflow.textContent='—';
        const state=textNode('td',''),badge=textNode('span',job.state);badge.className=`badge badge-${STATE_BADGE[job.state]||'gray'}`;state.append(badge);
        row.append(owner,workflow,textNode('td',describeModule(job,modules,id=>details.find(d=>d?.id===id)?.title||id)||'—'),state,textNode('td',String(job.spent_usd??job.progress?.spent_usd??'—')));
        body.append(row);
      }
      table.append(thead,body);
      const scroll=document.createElement('div');scroll.className='table-scroll';scroll.tabIndex=0;scroll.append(table);
      const focused=document.activeElement?.closest?.('#recent-jobs')?document.activeElement.title:null,old=document.querySelector('#recent-jobs .table-scroll');
      const left=old?old.scrollLeft:0,top=old?old.scrollTop:0;
      $('recent-jobs').replaceChildren(scroll);
      if(focused)[...document.querySelectorAll('#recent-jobs button')].find(button=>button.title===focused)?.focus();
      scroll.scrollLeft=left;scroll.scrollTop=top;
      const hadActive=activeListed;activeListed=jobs.some(active);
      if(activeListed&&!hadActive)document.querySelector('.recent-runs').open=true;
      lastRows=key;
      controls();
    }catch(error){lastRows='';$('recent-jobs').textContent='Could not load recent runs. Reopen New run to try again. Details: '+error.message;}
    finally{listing=false;}
  }
  function showStatus(status){
    const modules=Array.isArray(review?.modules)?review.modules:[];
    const bar=$('module-stages');
    bar.hidden=!modules.length;
    if(modules.length){
      const current=modules.indexOf(status.progress?.module),rawStep=status.progress?.step,step=moduleStep(status.progress),active=WORKFLOW_ACTIVE.includes(status.state),runComplete=status.state==='complete';
      // Report delivery follows the last accepted module: ahead, current while delivering, done, or stopped.
      const delivering=step==='delivering'&&active,delivered=runComplete||step==='delivered',deliveryStopped=(rawStep==='stopped'&&(status.progress.stopped_during==='delivering'||status.progress.accepted>=modules.length))||(!active&&!runComplete&&(step==='delivering'||status.progress?.accepted>=modules.length));
      const modulesDone=runComplete||deliveryStopped||step==='delivering'||step==='delivered';
      bar.replaceChildren(...modules.map((id,i)=>{
        const isComplete=modulesDone||i<current||(i===current&&step==='accepted'),isCurrent=i===current&&(['started','running','repairing'].includes(step)||(step==='stopped'&&!deliveryStopped)),isStopped=isCurrent&&!active&&status.state!=='complete';
        const li=document.createElement('li');li.dataset.status=isComplete?'complete':isCurrent?'current':'incomplete';li.title=id;
        if(isStopped)li.setAttribute('data-stopped','');
        const marker=document.createElement('span');marker.className='step-marker';marker.setAttribute('aria-hidden','true');
        if(isComplete){const tick=document.createElement('img');tick.src='icons/check.svg';tick.alt='';marker.append(tick);}else marker.textContent=String(i+1);
        const text=document.createElement('div');text.append(textNode('strong',titleOf(id)));
        const note=isComplete?'Accepted':isStopped?'Stopped here':isCurrent?'Running':'';
        if(note)text.append(textNode('span',note));
        li.append(marker,text);
        return li;
      }));
      const delivery=document.createElement('li');
      delivery.dataset.status=delivered?'complete':delivering?'current':'incomplete';
      if(deliveryStopped&&!delivered)delivery.setAttribute('data-stopped','');
      const deliveryMarker=document.createElement('span');deliveryMarker.className='step-marker';deliveryMarker.setAttribute('aria-hidden','true');
      if(delivered){const tick=document.createElement('img');tick.src='icons/check.svg';tick.alt='';deliveryMarker.append(tick);}else deliveryMarker.textContent=String(modules.length+1);
      const deliveryText=document.createElement('div');deliveryText.append(textNode('strong','Report delivery'));
      const deliveryNote=delivered?'Delivered':deliveryStopped?'Stopped':delivering?'Delivering':'';
      if(deliveryNote)deliveryText.append(textNode('span',deliveryNote));
      delivery.append(deliveryMarker,deliveryText);bar.append(delivery);
      const mark=delivered||delivering||deliveryStopped?delivery:bar.children[current];
      if(mark)mark.setAttribute('aria-current','step');
    }
    const desc=describeModule(status,modules,titleOf),head=stopText(status,!!desc);
    $('run-progress').replaceChildren(...summaryLines(head,desc));
    // The short id in the grey run badge as elsewhere; the full id stays in its title.
    const idBadge=review?.id?textNode('span',shortRunId(review.id)):null;
    if(idBadge){idBadge.className='code';idBadge.title=review.id;}
    $('run-identity').replaceChildren(...[review?.issuer?`${review.issuer} · ${workflowTitle(review.pathway)} · as of ${displayDate(review.as_of)} · `:'',idBadge].filter(Boolean));
    $('run-spend').textContent=spendText(status);
    const finished=!WORKFLOW_ACTIVE.includes(status.state);
    $('another-run').hidden=!finished;
    // A run that ended without a report can be reviewed again with its accepted work retained.
    const canResume=resumable(status);
    $('resume-field').hidden=!canResume;$('resume-run').hidden=!canResume;
    const field=$('resume-budget');
    const hint=$('resume-hint');
    hint.hidden=!canResume;
    if(!canResume)field.removeAttribute('aria-describedby');
    else{
      field.setAttribute('aria-describedby','resume-hint');
      // The final spend status.json records; a progress figure is the spend before a call and is not the stopped run's total.
      const spent=status.spent_usd;
      hint.textContent=`This cap applies to the resumed run's own model calls; ${DECIMAL.test(String(spent))?`the USD ${spent} recorded for the stopped run`:'spend recorded for the stopped run'} is not counted against it.`;
    }
    // Set once per run, so a poll never overwrites what the reader typed. The previous cap is the run's recorded one, never the
    // draft's budget; with none recorded the field stays empty and Review waits for the analyst's amount.
    if(canResume&&field.dataset.run!==review?.id){field.dataset.run=review?.id;field.value=status.progress?.cap_usd??review?.cap_usd??'';}
    // One primary action per view: Resume when the run can be resumed, otherwise Open.
    $('resume-run').className=canResume?'primary-action':'secondary-action';
    $('open-run').className=canResume?'secondary-action':'primary-action';
    $('open-run').hidden=!finished||status.run_available===false;
    $('open-run').textContent=status.state==='complete'?'Open deliverables':'Open run';
    $('open-run').dataset.route=runTarget({state:status.state,id:status.id||review?.id});
  }
  function reviewSummary(result){
    const details=(title,nodes)=>{const box=document.createElement('details');box.append(textNode('summary',title),...nodes);return box;};
    const list=(tag,items)=>{const node=textNode(tag,'');node.append(...items);return node;};
    const summary=document.createElement('dl');summary.className='review-summary';
    for(const [label,value] of [['Workflow',workflowTitle(result.pathway)],['As of',displayDate(result.as_of)],['Model',`${result.provider} ${result.model} · ${result.effort}`],['Maximum spend',`USD ${result.cap_usd}`],['Held per call',`USD ${result.hold_usd}`],['Max turns per module',String(result.max_turns)]])summary.append(textNode('dt',label),textNode('dd',value));
    const readiness=textNode('p',result.provider_ready?'Model provider configured. Review the scope and budget before starting.':`Cannot start · ${result.provider_key} is not set in the launching environment. Set it, restart the app and review again.`);
    readiness.className=result.provider_ready?'matrix-note':'caution';
    let resumed=null;
    if(result.resume_of){
      const kept=Array.isArray(result.retained_modules)?result.retained_modules:[];
      const named=kept.map(id=>result.module_details.find(item=>item.id===id)?.title||id);
      const why=typeof result.retained_note==='string'?result.retained_note:'';
      const head=kept.length?`Resumes run ${shortRunId(result.resume_of)}. Retained without a new model call: ${named.join(', ')}.`:why?`Resumes run ${shortRunId(result.resume_of)}.`:`Resumes run ${shortRunId(result.resume_of)}. No module of it was accepted; every module runs again.`;
      resumed=textNode('p',[head,why,kept.length||!why?'':'Every module runs again.'].filter(Boolean).join(' '));
      resumed.className='matrix-note';
    }
    const modules=list('ol',result.modules.map(id=>{const detail=result.module_details.find(item=>item.id===id),item=textNode('li',detail?.title||id);item.title=detail?`${id}: ${detail.purpose}`:id;return item;}));
    modules.className='review-modules';
    const ignored=result.ignored.length?result.ignored:['None'];
    $('run-review').replaceChildren(textNode('h3',result.issuer),summary,readiness,...(resumed?[resumed]:[]),textNode('h4','Modules to run, in order'),modules,
      details(`Source files · ${result.sources.length} chosen, ${result.ignored.length} ignored`,[list('ul',result.sources.map(source=>textNode('li',`${source.path} · SHA-256 ${source.sha256}`))),textNode('h4','Ignored: no module can read these'),list('ul',ignored.map(name=>textNode('li',name)))]),
      details(`Report · ${result.report_sections.length} sections, ${result.omitted.length} not produced`,[textNode('h4','Sections this run fills'),list('ul',result.report_sections.map(name=>textNode('li',name))),textNode('h4','Sections it does not produce'),list('ul',(result.omitted.length?result.omitted:['None']).map(name=>textNode('li',name)))]),
      details('Scope and limitations',[textNode('p',result.scope),textNode('p',`The spend ceiling applies to this run folder. Each call holds up to the amount shown while in flight; this is not an estimate of total cost. Prices dated ${displayDate(result.prices_as_of)}.`)]));
  }
  async function poll(){
    if(polling)return;
    polling=true;
    try{
      if($('new-run').hidden){controls();return;}
      await recent();
      if(!review||!running)return;
      const asked=review.id,status=await appRequest('/api/runs/status?id='+encodeURIComponent(asked));
      // The reader may have opened another run while this reply was in flight; it describes the old one.
      if(review?.id!==asked)return;
      showStatus(status);
      if(!WORKFLOW_ACTIVE.includes(status.state))running=false;
    }catch(error){$('run-progress').textContent='Could not refresh run status. The app will check again automatically. Details: '+error.message;}
    finally{polling=false;controls();}
  }
  let contextLoaded=null;
  window.addEventListener('message',event=>{
    if(event.source!==$('context-editor').contentWindow)return;
    if(['cpos:ready','cpos:height'].includes(event.data?.type)&&contextLoaded)contextLoaded();
    if(event.data?.type==='cpos:height'){
      const height=event.data.height;
      if(Number.isFinite(height)&&height>0&&height<=50000)$('context-editor').style.height=height+'px';
      return;
    }
    if(event.data?.type==='cpos:ready'){$('context-editor').contentWindow.postMessage({type:'cpos:names',names:moduleNames},'*');$('context-readiness').textContent=event.data.ready?'Required fields complete. Continue when ready.':'Complete the required fields above to continue.';return;}
    if(event.data?.type!=='cpos:context'||running||busy||$('new-run').hidden)return;
    if(event.data.problems?.length){message('Complete the context form before continuing:\n'+event.data.problems.join('\n'));return;}
    context=event.data.context;review=null;document.body.dataset.draft='1';
    $('context-summary').textContent=`${context.identity.issuer_name} · ${workflowTitle(context.run.pathway)} · as of ${displayDate(context.run.as_of)}`;
    stage('source');controls();
  });
  $('use-context').addEventListener('click',()=>{$('context-editor').contentWindow.postMessage({type:'cpos:get-context'},'*');});
  $('edit-context').addEventListener('click',()=>{if(!running)stage('context');});
  $('revise-run').addEventListener('click',()=>{review=null;$('run-confirm').checked=false;stage('source');controls();});
  $('run-confirm').addEventListener('change',controls);
  $('resume-budget').addEventListener('input',controls);
  $('run-sources').addEventListener('change',()=>{
    const files=uploadable($('run-sources').files),bytes=files.reduce((sum,file)=>sum+file.size,0);
    const list=textNode('ul','');list.append(...files.slice(0,8).map(file=>textNode('li',folderPath(file))));
    if(files.length>8)list.append(textNode('li',`and ${files.length-8} more`));
    $('upload-list').replaceChildren(textNode('p',`${files.length} file${files.length===1?'':'s'} · ${(bytes/1048576).toFixed(1)} MiB`),list);
    review=null;
  });
  $('review-run').addEventListener('click',async()=>{
    if(busy||running||!context)return;
    const files=uploadable($('run-sources').files);
    if(!files.length){message('Choose the issuer folder, then choose Validate and review run.');return;}
    busy=true;controls();message('Checking the context, files and budget. No model call has been made…');
    try{
      const body=new FormData();
      body.set('context',JSON.stringify(context,null,2));body.set('config',$('run-model').value);body.set('cap_usd',$('run-budget').value);
      body.set('modules',$('run-modules').value);body.set('max_turns',$('run-turns').value);
      body.set('source_paths',JSON.stringify(files.map(folderPath)));
      files.forEach(file=>body.append('sources',file,file.name));
      const result=await appRequest('/api/runs/review',body,true);
      if(!result.ok){message(result.problems.join('\n'));return;}
      review=result;$('run-confirm').checked=false;
      reviewSummary(result);stage('review');
    }catch(error){message('Could not prepare the run review. Check the inputs and choose Validate and review run again. Details: '+error.message);}
    finally{busy=false;controls();}
  });
  $('resume-run').addEventListener('click',async()=>{
    if(busy||running||!review?.id)return;
    busy=true;controls();message('Checking the stopped run\'s inputs and retained work. No model call has been made…');
    try{
      const result=await appRequest('/api/runs/resume',{id:review.id,cap_usd:$('resume-budget').value,max_turns:Number(review.max_turns)||Number(review.progress?.max_turns)||Number($('run-turns').value)});
      if(!result.ok){message(result.problems.join('\n'));return;}
      review=result;$('run-confirm').checked=false;
      reviewSummary(result);stage('review');
    }catch(error){message('Could not prepare the resumed run. Details: '+error.message);}
    finally{busy=false;controls();}
  });
  $('start-run').addEventListener('click',async()=>{
    if(busy||running||!review?.provider_ready||!$('run-confirm').checked)return;
    busy=true;controls();
    try{
      await appRequest('/api/runs/start',{id:review.id,review_id:review.review_id,confirm:true});
      running=true;delete document.body.dataset.draft;stage('progress');$('open-run').hidden=true;$('another-run').hidden=true;
      if('Notification' in window&&Notification.permission==='default')Notification.requestPermission().catch(error=>console.warn('Notification permission request failed',error));
      watchRuns();await poll();
    }catch(error){
      message(error.message);
      // A lost response must not prompt a second paid launch. Reconnect by id.
      try{const status=await appRequest('/api/runs/status?id='+encodeURIComponent(review.id));if(status.state!=='reviewed'){running=true;delete document.body.dataset.draft;stage('progress');await poll();}}catch{}
    }finally{busy=false;controls();}
  });
  $('another-run').addEventListener('click',()=>{if(running)return;review=null;context=null;delete document.body.dataset.draft;$('run-sources').value='';$('upload-list').replaceChildren();$('run-confirm').checked=false;stage('context');controls();});
  // The store is read at load, so a finished run needs a reload to appear.
  $('open-run').addEventListener('click',()=>{location.hash=$('open-run').dataset.route;location.reload();});
  window.addEventListener('beforeunload',event=>{if(running){event.preventDefault();event.returnValue='';}});
  window.addEventListener('hashchange',openRequested);
  controls();
  return{show(){
    if(!$('context-editor').hasAttribute('src')){
      contextLoaded=watchFrame($('context-editor'),document.querySelector('#context-step .frame-status'),'Loading run context form…','The run context form did not load.');
      $('context-editor').src='context-form.html';
    }
    recent();openRequested();
    document.querySelector('#new-run .run-step:not([hidden]) h2').focus({preventScroll:true});
  }};
}

let settingsBusy=false;
function installSettings(){
  const status=value=>{$('settings-status').textContent=value;};
  // One request at a time: the buttons stay disabled until it fails (success reloads the page).
  const lock=(on,note)=>{
    settingsBusy=on;
    for(const id of ['save-workspace','refresh-library','quit-library'])if($(id))$(id).disabled=on||(id==='save-workspace'&&window.DESIGN_APP.policy_locked);
    if(note)status(note);
  };
  const changing=async(url,body,note)=>{
    if(settingsBusy)return;
    // Success reloads the page, which clears a run being prepared: ask before sending anything.
    if(!mayDiscardDraft())return;
    lock(true,note);
    try{await appRequest(url,body);location.reload();}
    catch(error){lock(false);status('Could not update the library. Details: '+error.message);}
  };
  document.addEventListener('click',async event=>{
    if(event.target.closest('#refresh-library'))await changing('/api/refresh',{},'Refreshing the library…');
    if(event.target.closest('#save-workspace'))await changing('/api/settings',{workspace:$('workspace-path').value.trim()},'Saving the workspace…');
    if(event.target.closest('#quit-library')&&!settingsBusy){
      lock(true,'Stopping the library…');
      try{await appRequest('/api/quit',{});document.body.dataset.quit='1';status('Library stopped. You can close this tab; open the launcher to start it again.');}
      catch(error){lock(false);status(error.message);}
    }
  });
}
