'use strict';
// The screens read the workspace store, so they load once it has arrived. A store that cannot be
// read still opens the app with the problem stated: Settings and Help stay reachable.
(async()=>{
  const read=async url=>{
    const response=await fetch(url,{cache:'no-store'});
    if(!response.ok)throw new Error(await response.text());
    return response.json();
  };
  let catalogue={},store={runs:{},outputs:{},inputs:{},pins:{},handoffs:{},reports:[],models:[],visuals:[],issues:[]},problem='';
  try{catalogue=await read('/api/catalogue');store=hydrate(await read('/api/workspace'));}
  catch(error){problem=error.message;}
  window.DESIGN_DATA={runs:store.runs,outputs:store.outputs,inputs:store.inputs,pins:store.pins};
  window.DESIGN_WORKSPACE={reports:store.reports,models:store.models,visuals:store.visuals};
  window.DESIGN_CATALOGUE={real:catalogue.real||[],sources:catalogue.sources||{}};
  window.DESIGN_APP={workspace:catalogue.workspace||'',policy_locked:!!catalogue.policy_locked,issues:problem?catalogue.issues||[]:store.issues,problem};
  // Discovery runs every 30 seconds. Offer the change rather than moving the screen under the reader.
  const shape=value=>JSON.stringify(value.real?.map(run=>[run.id,run.files?.length,run.artifacts?.filter(item=>item.available).map(item=>item.folder)]));
  const loaded=shape(catalogue);
  // A run being prepared is lost on reload, whichever screen is showing, so the reader is asked first.
  const reload=()=>{if(document.body.dataset.draft==='1'&&!window.confirm('Reload now? The run you are preparing will be cleared.'))return;location.reload();};
  document.getElementById('reload-workspace').addEventListener('click',reload);
  document.getElementById('reload-service').addEventListener('click',reload);
  let failures=0;
  setInterval(async()=>{
    // One missed check changes nothing on screen; two in a row say the service is not answering.
    try{
      const latest=shape(await read('/api/catalogue'));
      failures=0;document.getElementById('service-down').hidden=true;
      if(latest!==loaded)document.getElementById('workspace-updated').hidden=false;
    }catch(error){
      console.warn('Workspace check failed',error);
      if(++failures>=2&&!document.body.dataset.quit)document.getElementById('service-down').hidden=false;
    }
  },30000);
  for(const name of ['views.js','actions.js','screen.js'])await new Promise((resolve,reject)=>{
    const script=document.createElement('script');
    script.src=name;script.onload=resolve;script.onerror=reject;
    document.head.append(script);
  });
  watchRuns();
})();
