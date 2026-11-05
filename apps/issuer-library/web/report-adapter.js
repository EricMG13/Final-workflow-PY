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
/* Reader text shows module names. The inspector keeps exact codes and the original download is untouched. */
(() => {
  const MODULE_NAMES={"CP-0":"Source readiness","CP-1A":"Business & governance","CP-DR":"Research questions","CP-1":"Financial foundation","CP-1B":"Earnings changes","CP-L10":"Financial change screen","CP-1D":"Earnings quality","CP-1C":"Peer benchmark","CP-2D":"Liquidity","CP-3C":"Refinancing & LME","CP-2":"Fundamental credit","CP-2A":"Downside","CP-2G":"Forward credit model","CP-2E":"Rates, FX & hedging","CP-2H":"Ratings & triggers","CP-4":"Legal & covenants","CP-4A":"Covenant capacity","CP-4B":"Structural priority","CP-4D":"Intercreditor control","CP-4C":"Recovery & fulcrum","CP-3":"Security selection","CP-3D":"Market-implied risk","CP-6":"Committee decision","CP-5":"Evidence validation","CP-8":"Deliverable comparison","CP-MODEL":"Published model","CP-OS":"Run activity","CP-MEMO":"Credit memo","CP-PARSE":"Source readiness","CP-2C":"Business & governance","CP-1E":"Earnings quality","CP-2B":"Downside","CP-2F":"Rates, FX & hedging","CP-3A":"Security selection","CP-3B":"Security selection","CP-5A":"Evidence validation","CP-6A":"Committee decision","CP-L20":"Financial change screen","CP-L23":"Financial change screen","CP-L30":"Financial change screen","CP-L40":"Financial change screen"};
  const CODE=/\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])/g;
  function nameCodes(root) {
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),nodes=[];
    while(walker.nextNode())nodes.push(walker.currentNode);
    for(const node of nodes) {
      const codes=node.data.match(CODE);
      if(!codes)continue;
      node.data=node.data.replace(CODE,code=>MODULE_NAMES[code]||code);
      node.parentElement.title=[...new Set([node.parentElement.title,...codes].filter(Boolean))].join(', ');
    }
  }
  // Only child changes are observed, so rewriting text here cannot trigger another pass.
  for(const root of document.querySelectorAll('.navigator,#view-root,#call-root')) {
    new MutationObserver(()=>nameCodes(root)).observe(root,{childList:true,subtree:true});
    nameCodes(root);
  }
})();
