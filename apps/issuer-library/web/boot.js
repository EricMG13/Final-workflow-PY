'use strict';
// The screens read the workspace store, so they load once it has arrived. A store that cannot be
// read still opens the app with the problem stated: Settings and Help stay reachable.
(async()=>{
  const read=async url=>{
    const response=await fetch(url,{cache:'no-store'});
    if(!response.ok)throw new Error(await response.text());
    return response.json();
  };
  let catalogue={},store={runs:{},outputs:{},inputs:{},pins:{},reports:[],visuals:[],issues:[]},problem='';
  try{catalogue=await read('/api/catalogue');store=await read('/api/workspace');}
  catch(error){problem=error.message;}
  window.DESIGN_DATA={runs:store.runs,outputs:store.outputs,inputs:store.inputs,pins:store.pins};
  window.DESIGN_WORKSPACE={reports:store.reports,visuals:store.visuals};
  window.DESIGN_APP={workspace:catalogue.workspace||'',policy_locked:!!catalogue.policy_locked,issues:problem?catalogue.issues||[]:store.issues,problem};
  // Discovery runs every 30 seconds. Offer the change rather than moving the screen under the reader.
  const shape=value=>JSON.stringify(value.real?.map(run=>[run.id,run.files?.length,run.artifacts?.filter(item=>item.available).map(item=>item.folder)]));
  const loaded=shape(catalogue);
  document.getElementById('reload-workspace').addEventListener('click',()=>location.reload());
  setInterval(async()=>{
    // A missed check changes nothing on screen; the next one tries again.
    try{if(shape(await read('/api/catalogue'))!==loaded)document.getElementById('workspace-updated').hidden=false;}
    catch(error){console.warn('Workspace check failed',error);}
  },30000);
  for(const name of ['views.js','actions.js','screen.js'])await new Promise((resolve,reject)=>{
    const script=document.createElement('script');
    script.src=name;script.onload=resolve;script.onerror=reject;
    document.head.append(script);
  });
})();
