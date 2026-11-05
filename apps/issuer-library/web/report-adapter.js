/* Presentation only: use the retained report's renderer, citations and evidence controls. */
(() => {
  document.body.classList.add('library-report');
  document.title='Issuer report';
  document.querySelectorAll('.brand-mark').forEach(mark=>mark.replaceChildren());
  document.querySelectorAll('.logo-block').forEach(block=>block.remove());
  const content=document.getElementById('inspector-content');
  if(!content)return;
  let trigger=null;
  const dismiss=document.createElement('button');dismiss.type='button';dismiss.className='inspector-dismiss';dismiss.textContent='Close evidence';
  function close(){document.body.classList.remove('evidence-open');if(trigger?.isConnected)trigger.focus();}
  dismiss.addEventListener('click',close);
  document.querySelector('#inspector .insp-head').prepend(dismiss);
  document.addEventListener('click',event=>{if(!event.target.closest('#inspector'))trigger=event.target.closest('button,a')||trigger;},true);
  function classify(){
    document.querySelectorAll('.page-head>.eyebrow').forEach(label=>label.remove());
    document.querySelectorAll('.fig').forEach(item=>item.classList.toggle('narrative',!item.closest('.fig-cell')&&item.textContent.trim().split(/\s+/).length>=6));
  }
  function update(){
    const selected=!content.textContent.startsWith('Select a figure or source');
    const wasOpen=document.body.classList.contains('evidence-open');
    document.body.classList.toggle('evidence-open',selected);
    if(selected&&!wasOpen)content.focus({preventScroll:true});
  }
  new MutationObserver(classify).observe(document.getElementById('view-root'),{childList:true,subtree:true});
  new MutationObserver(update).observe(content,{childList:true,subtree:true});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&document.body.classList.contains('evidence-open'))close();});
  classify();update();
})();
/* Presentation adaptation of copied reports; original downloads are untouched. */
(() => {
  const navigator=document.querySelector('.navigator'),destinations=document.getElementById('rail-dests');
  if(navigator&&destinations) {
    navigator.prepend(destinations);
    destinations.querySelectorAll('.rail-btn').forEach(button=>{
      const label=document.createElement('span');
      label.textContent=button.getAttribute('aria-label')||button.getAttribute('title')||'';
      button.append(label);
    });
  }
  const scope=document.getElementById('delivery-scope-banner'),call=document.getElementById('call-root');
  if(scope) {
    const details=document.createElement('details'),summary=document.createElement('summary');
    details.className='delivery-disclosure';
    summary.textContent='Delivery scope · assessment pending';
    scope.before(details);details.append(summary,scope);
    // These retained snapshots contain an Assessment pending placeholder. Keep it
    // inspectable with the delivery boundary instead of duplicating the workspace.
    if(call)details.append(call);
    document.getElementById('outline')?.addEventListener('click',event=>{
      if(event.target.closest('button')?.textContent==='The call')details.open=true;
    },true);
  }
  const payload=JSON.parse(document.getElementById('report-data').textContent);
  const title=()=>{
    const heading=document.querySelector('.page-head h1');
    if(heading?.textContent===payload.run.issuer_name)heading.textContent=payload.report.pathway.title;
  };
  new MutationObserver(title).observe(document.getElementById('view-root'),{childList:true,subtree:true});
  title();
})();
