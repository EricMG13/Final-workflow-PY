'use strict';
// What the app does to the server: the New run steps and Settings. Only Start can reach a provider.
async function appRequest(url,body,multipart=false){
  const headers=body===undefined?{}:{'X-Issuer-Library':'1',...multipart?{}:{'Content-Type':'application/json'}};
  const response=await fetch(url,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:multipart?body:JSON.stringify(body),cache:'no-store'});
  if(!response.ok)throw new Error(await response.text());
  return response.json();
}
const WORKFLOW_ACTIVE=['running','starting'];
const workflowTitle=value=>String(value).replace(/_/g,' ').replace(/\b[a-z]/g,letter=>letter.toUpperCase());
const STATE_BADGE={running:'blue',starting:'blue',complete:'navy',stopped:'attention',failed:'attention',interrupted:'attention'};
const textNode=(tag,value)=>{const node=document.createElement(tag);node.textContent=value;return node;};
// The chosen folder's name is dropped: paths are relative to it, as the launcher's --sources are.
const folderPath=file=>(file.webkitRelativePath||file.name).split('/').slice(file.webkitRelativePath?1:0).join('/');
// The launcher skips dot paths without listing them, so they are not worth uploading.
const uploadable=files=>[...files].filter(file=>!folderPath(file).split('/').some(part=>part.startsWith('.')));

function installNewRun(){
  let context=null,review=null,busy=false,running=false,polling=false,listing=false,watch=null,activeListed=false,lastRows='';
  function message(value){$('new-run-message').textContent=value;}
  function stage(name){
    for(const id of ['context','source','review','progress'])$(id+'-step').hidden=id!==name;
    document.querySelectorAll('[data-stage]').forEach(item=>{if(item.dataset.stage===name)item.setAttribute('aria-current','step');else item.removeAttribute('aria-current');});
    message('');$(name+'-step').querySelector('h2').focus();
  }
  function controls(){
    $('review-run').disabled=busy||running;
    $('start-run').disabled=busy||running||!review?.provider_ready||!$('run-confirm').checked;
    $('revise-run').disabled=busy||running;
    $('run-sources').disabled=busy||running;
    const wanted=(running||activeListed)&&!$('new-run').hidden;
    if(wanted&&!watch)watch=setInterval(poll,2000);
    if(!wanted&&watch){clearInterval(watch);watch=null;}
  }
  function titleOf(id){return (Array.isArray(review?.module_details)?review.module_details:[]).find(item=>item?.id===id)?.title||id;}
  function describeModule(status,modules,nameOf){
    const p=status.progress||{},moduleId=p.module;
    if(!moduleId)return '';
    const index=modules.indexOf(moduleId),where=index>=0?` (${index+1} of ${modules.length})`:'';
    if(p.step==='started')return `${WORKFLOW_ACTIVE.includes(status.state)?'running':'stopped during'} ${nameOf(moduleId)}${where}`;
    if(p.step==='accepted')return `${nameOf(moduleId)} accepted${where}`;
    return '';
  }
  async function recent(){
    if(listing)return;listing=true;
    try{
      const jobs=await appRequest('/api/runs/list');
      const key=JSON.stringify(jobs);if(key===lastRows){controls();return;}
      if(!jobs.length){$('recent-jobs').textContent='No recent runs to show.';lastRows=key;activeListed=false;controls();return;}
      const active=job=>WORKFLOW_ACTIVE.includes(job.state);
      const ordered=[...jobs.filter(active),...jobs.filter(job=>!active(job))];
      const table=document.createElement('table'),head=document.createElement('tr'),body=document.createElement('tbody');
      head.append(...['Issuer','Workflow','Module','State','Spend (USD)'].map(label=>textNode('th',label)));
      const thead=document.createElement('thead');thead.append(head);
      for(const job of ordered){
        const modules=Array.isArray(job.modules)?job.modules:[],details=Array.isArray(job.module_details)?job.module_details:[];
        const row=document.createElement('tr'),owner=document.createElement('th'),button=textNode('button',job.issuer||job.id);
        owner.scope='row';button.type='button';button.className='text-button';button.title=job.id;
        button.addEventListener('click',()=>{review={...job,modules,module_details:details};running=active(job);stage('progress');showStatus(job);controls();if(running)poll();});
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
      const current=modules.indexOf(status.progress?.module),step=status.progress?.step,active=WORKFLOW_ACTIVE.includes(status.state),runComplete=status.state==='complete';
      bar.replaceChildren(...modules.map((id,i)=>{
        const isComplete=runComplete||i<current||(i===current&&step==='accepted'),isCurrent=i===current&&step==='started',isStopped=isCurrent&&!active&&status.state!=='complete';
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
      const mark=runComplete?bar.lastElementChild:bar.children[current];
      if(mark)mark.setAttribute('aria-current','step');
    }
    const head=`${status.state}: ${status.message||''}`,desc=describeModule(status,modules,titleOf);
    $('run-progress').textContent=desc?`${head} · ${desc}`:head;
    $('run-identity').textContent=review?.issuer?`${review.issuer} · ${workflowTitle(review.pathway)} · as of ${review.as_of} · ${review.id}`:review?.id||'';
    const spent=status.spent_usd??status.progress?.spent_usd;
    $('run-spend').textContent=spent==null?'Spend appears after CP-OS records a completed model response.':`Recorded spend: USD ${spent}`;
    const finished=!WORKFLOW_ACTIVE.includes(status.state);
    $('another-run').hidden=!finished;
    $('open-run').hidden=!finished||status.run_available===false;
    $('open-run').textContent=status.state==='complete'?'Open deliverables':'Open run';
    $('open-run').dataset.route=`${status.state==='complete'?'W-Reports/list':'W-Overview/overview'}?c=${encodeURIComponent(status.id||review?.id)}`;
  }
  function reviewSummary(result){
    const details=(title,nodes)=>{const box=document.createElement('details');box.append(textNode('summary',title),...nodes);return box;};
    const list=(tag,items)=>{const node=textNode(tag,'');node.append(...items);return node;};
    const summary=document.createElement('dl');summary.className='review-summary';
    for(const [label,value] of [['Workflow',workflowTitle(result.pathway)],['As of',result.as_of],['Model',`${result.provider} ${result.model} · ${result.effort}`],['Maximum spend',`USD ${result.cap_usd}`],['Held per call',`USD ${result.hold_usd}`],['Max turns per module',String(result.max_turns)]])summary.append(textNode('dt',label),textNode('dd',value));
    const readiness=textNode('p',result.provider_ready?'Model provider configured. Review the scope and budget before starting.':`Cannot start · ${result.provider_key} is not set in the launching environment. Set it, restart the app and review again.`);
    readiness.className=result.provider_ready?'matrix-note':'caution';
    const modules=list('ol',result.modules.map(id=>{const detail=result.module_details.find(item=>item.id===id),item=textNode('li',detail?.title||id);item.title=detail?`${id}: ${detail.purpose}`:id;return item;}));
    modules.className='review-modules';
    const ignored=result.ignored.length?result.ignored:['None'];
    $('run-review').replaceChildren(textNode('h3',result.issuer),summary,readiness,textNode('h4','Modules to run, in order'),modules,
      details(`Source files · ${result.sources.length} chosen, ${result.ignored.length} ignored`,[list('ul',result.sources.map(source=>textNode('li',`${source.path} · SHA-256 ${source.sha256}`))),textNode('h4','Ignored: no module can read these'),list('ul',ignored.map(name=>textNode('li',name)))]),
      details(`Report · ${result.report_sections.length} sections, ${result.omitted.length} not produced`,[textNode('h4','Sections this run fills'),list('ul',result.report_sections.map(name=>textNode('li',name))),textNode('h4','Sections it does not produce'),list('ul',(result.omitted.length?result.omitted:['None']).map(name=>textNode('li',name)))]),
      details('Scope and limitations',[textNode('p',result.scope),textNode('p',`The spend ceiling applies to this run folder. Each call holds up to the amount shown while in flight; this is not an estimate of total cost. Prices dated ${result.prices_as_of}.`)]));
  }
  async function poll(){
    if(polling)return;
    polling=true;
    try{
      if($('new-run').hidden){controls();return;}
      await recent();
      if(!review||!running)return;
      const status=await appRequest('/api/runs/status?id='+encodeURIComponent(review.id));
      showStatus(status);
      if(!WORKFLOW_ACTIVE.includes(status.state))running=false;
    }catch(error){$('run-progress').textContent='Could not refresh run status. The app will check again automatically. Details: '+error.message;}
    finally{polling=false;controls();}
  }
  window.addEventListener('message',event=>{
    if(event.source!==$('context-editor').contentWindow)return;
    if(event.data?.type==='cpos:height'){
      const height=event.data.height;
      if(Number.isFinite(height)&&height>0&&height<=50000)$('context-editor').style.height=height+'px';
      return;
    }
    if(event.data?.type==='cpos:ready'){$('context-readiness').textContent=event.data.ready?'Required fields complete. Continue when ready.':'Complete the required fields above to continue.';return;}
    if(event.data?.type!=='cpos:context'||running||busy||$('new-run').hidden)return;
    if(event.data.problems?.length){message('Complete the context form before continuing:\n'+event.data.problems.join('\n'));return;}
    context=event.data.context;review=null;
    $('context-summary').textContent=`${context.identity.issuer_name} · ${workflowTitle(context.run.pathway)} · as of ${context.run.as_of}`;
    stage('source');controls();
  });
  $('use-context').addEventListener('click',()=>{$('context-editor').contentWindow.postMessage({type:'cpos:get-context'},'*');});
  $('edit-context').addEventListener('click',()=>{if(!running)stage('context');});
  $('revise-run').addEventListener('click',()=>{review=null;$('run-confirm').checked=false;stage('source');controls();});
  $('run-confirm').addEventListener('change',controls);
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
  $('start-run').addEventListener('click',async()=>{
    if(busy||running||!review?.provider_ready||!$('run-confirm').checked)return;
    busy=true;controls();
    try{
      await appRequest('/api/runs/start',{id:review.id,review_id:review.review_id,confirm:true});
      running=true;stage('progress');$('open-run').hidden=true;$('another-run').hidden=true;await poll();
    }catch(error){
      message(error.message);
      // A lost response must not prompt a second paid launch. Reconnect by id.
      try{const status=await appRequest('/api/runs/status?id='+encodeURIComponent(review.id));if(status.state!=='reviewed'){running=true;stage('progress');await poll();}}catch{}
    }finally{busy=false;controls();}
  });
  $('another-run').addEventListener('click',()=>{if(running)return;review=null;context=null;$('run-sources').value='';$('upload-list').replaceChildren();$('run-confirm').checked=false;stage('context');controls();});
  // The store is read at load, so a finished run needs a reload to appear.
  $('open-run').addEventListener('click',()=>{location.hash=$('open-run').dataset.route;location.reload();});
  window.addEventListener('beforeunload',event=>{if(running){event.preventDefault();event.returnValue='';}});
  controls();
  return{show(){
    if(!$('context-editor').hasAttribute('src'))$('context-editor').src='context-form.html';
    recent();
    document.querySelector('#new-run .run-step:not([hidden]) h2').focus({preventScroll:true});
  }};
}

function installSettings(){
  const status=value=>{$('settings-status').textContent=value;};
  const changing=async(url,body)=>{
    try{await appRequest(url,body);location.reload();}
    catch(error){status('Could not update the library. Details: '+error.message);}
  };
  document.addEventListener('click',async event=>{
    if(event.target.closest('#refresh-library'))await changing('/api/refresh',{});
    if(event.target.closest('#save-workspace'))await changing('/api/settings',{workspace:$('workspace-path').value.trim()});
    if(event.target.closest('#quit-library')){
      try{await appRequest('/api/quit',{});status('Library stopped. You can close this tab; open the launcher to start it again.');}
      catch(error){status(error.message);}
    }
  });
}
