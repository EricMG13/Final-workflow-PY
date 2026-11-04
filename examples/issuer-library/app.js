(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('catalog-data').textContent);
  const $ = id => document.getElementById(id);
  const {numberOf, hasReport, filterRuns, sortRuns} = LibraryLogic;
  const fields = ['search','sector','workflow','completion','availability','basis','period','leverageMin','leverageMax','coverageMin','coverageMax'];
  const metricNames = {revenue:'Revenue',ebitda:'EBITDA',leverage:'Leverage',coverage:'Interest coverage',cash:'Closing cash',cashflow:'Cash flow measure'};
  let dataset = 'real', issuer = '', selected = data.real[0].id, sortKey = '', direction = 'asc';
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text != null) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const link = (text, href, className) => {
    const element = node('a', text, className);
    element.href = href; element.target = '_blank'; element.rel = 'noopener';
    return element;
  };
  const button = (text, action, className) => {
    const element = node('button', text, className); element.type = 'button';
    element.addEventListener('click', action); return element;
  };
  const dated = value => new Date(value + 'T12:00:00Z').toLocaleDateString('en-GB', {day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
  const formatted = metric => {
    const value = numberOf(metric);
    if (value === null) return '—';
    if (metric.unit === 'x') return metric.value + '×';
    const decimals = (metric.value.split('.')[1] || '').length;
    return value.toLocaleString('en-GB', {minimumFractionDigits:decimals,maximumFractionDigits:decimals});
  };
  const filters = () => Object.fromEntries([...fields.map(id => [id,$(id).validity?.badInput ? 'invalid' : $(id).value]), ['issuer',issuer]]);
  const primaryArtifact = run => run.artifacts.find(a => a.available && a.state !== 'superseded');
  function populateSelect(id, values, placeholder) {
    $(id).replaceChildren(new Option(placeholder, ''), ...[...new Set(values.filter(Boolean))].sort().map(value => new Option(value,value)));
  }
  function initialiseDataset() {
    const rows = data[dataset];
    populateSelect('sector', rows.map(r => r.sector), 'All sectors');
    populateSelect('workflow', rows.map(r => r.workflow), 'All workflows');
    populateSelect('period', rows.map(r => r.period_kind), 'All period types');
    populateSelect('basis', rows.map(r => r.metrics.leverage?.basis), 'All bases · definitions differ');
    $('real-data').setAttribute('aria-pressed', String(dataset === 'real'));
    $('demo-data').setAttribute('aria-pressed', String(dataset === 'illustrative'));
    $('dataset-note').classList.toggle('demo', dataset === 'illustrative');
    $('dataset-note').replaceChildren(
      node('strong', dataset === 'real' ? 'Existing evidence. ' : 'Fictional examples. '),
      document.createTextNode(dataset === 'real'
        ? `${rows.length} curated run folders. Historical metrics, original reports and unassessed workflow completeness.`
        : 'Issuer names, credit metrics and completion scores are illustrative. No actual reports or investment conclusions.'));
    $('all-count').textContent = rows.length;
    $('report-count').textContent = rows.filter(hasReport).length;
    const issuers = [...new Set(rows.map(r => r.issuer))];
    $('issuer-count').textContent = issuers.length;
    $('issuer-nav').replaceChildren(...issuers.map(id => {
      const matching = rows.filter(r => r.issuer === id);
      const choice = button('', () => {issuer = issuer === id ? '' : id; render();}, 'issuer-choice');
      choice.dataset.issuer = id;
      choice.setAttribute('aria-label', 'Filter ' + matching[0].name);
      choice.append(node('span',id.slice(0,3),'issuer-monogram'),node('span',matching[0].name),node('span',matching.length));
      return choice;
    }));
  }
  function reset() {
    fields.forEach(id => {$(id).value = '';}); issuer = ''; sortKey = ''; direction = 'asc';
    selected = data[dataset][0]?.id; render();
  }
  function switchDataset(next) {
    dataset = next; initialiseDataset(); reset();
  }
  function metricCell(run, key) {
    const cell = node('td');
    const metric = run.metrics[key];
    cell.append(node('span',formatted(metric),metric ? 'cell-primary' : 'cell-primary missing'),
      node('span',metric?.basis || 'Not available','cell-secondary'));
    return cell;
  }
  function completionCell(run) {
    const cell = node('td');
    if (run.completion === null) {
      cell.append(node('span','Not assessed','date-primary'),node('span','Checklist required','cell-secondary'));
    } else {
      const score = node('span',null,'score');
      score.append(node('span',run.completion + '%','cell-primary'));
      const track = node('div',null,'progress-track');
      const fill = node('div',null,'progress-fill'); fill.style.width = run.completion + '%';
      track.append(fill); track.setAttribute('aria-hidden','true');
      cell.append(score,track,node('span',`${run.checkpoints.done}/${run.checkpoints.total} requirements`,'cell-secondary'));
    }
    return cell;
  }
  function selectRun(id) {
    selected = id; render();
    $('run-detail').focus({preventScroll:true});
    $('run-detail').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  }
  function runRow(run) {
    const row = node('tr'); row.classList.toggle('selected',selected === run.id);
    const identity = node('td');
    const name = button(run.name,() => selectRun(run.id),'issuer-title');
    name.setAttribute('aria-label',`View ${run.name}: ${run.title}`);
    name.setAttribute('aria-expanded', String(selected === run.id)); name.setAttribute('aria-controls','run-detail');
    name.append(node('span',run.issuer,'ticker'));
    identity.append(name,node('span',run.title,'run-title'));
    const date = node('td'); date.append(node('span',dated(run.date),'cell-primary date-primary'),node('span',run.period,'cell-secondary'));
    const deliverable = node('td');
    const artifact = primaryArtifact(run);
    if (artifact) {
      const text = artifact.relationship === 'related' ? 'Related report ↗' : 'Open report ↗';
      const anchor = link(text,artifact.href,'report-link'); anchor.setAttribute('aria-label',`${text}: ${run.name}, ${artifact.label}`);
      deliverable.append(anchor,node('span','Candidate HTML','cell-secondary'));
    } else deliverable.append(node('span',dataset === 'real' ? 'Handoffs only' : 'Illustrative','date-primary'),node('span','No report','cell-secondary'));
    row.append(identity,node('td',run.sector),date,metricCell(run,'leverage'),metricCell(run,'coverage'),completionCell(run),deliverable);
    return row;
  }
  function showSource(sourceId) {
    $('metric-sources').open = true;
    const target = $('source-' + sourceId);
    target.focus({preventScroll:true}); target.scrollIntoView({block:'center'});
  }
  function renderMetric(run, key) {
    const item = node('div',null,'metric-item'), metric = run.metrics[key];
    const value = node('span',formatted(metric),'metric-value');
    if (metric && metric.unit !== 'x') value.append(node('small',metric.unit));
    item.append(node('span',metricNames[key],'metric-label'),value,
      node('p',metric ? `${metric.period} · ${metric.basis}` : 'Not established for this case.','metric-basis'));
    if (metric?.source) item.append(button('View source ↗',() => showSource(metric.source),'source-link'));
    return item;
  }
  function evidenceDetails(run) {
    const details = node('details',null,'source-details'); details.id = 'metric-sources';
    const ids = [...new Set([run.identity_source,run.sector_source,...Object.values(run.metrics).map(m => m?.source),...run.ratings.map(r => r.source)].filter(Boolean))];
    details.append(node('summary',`Sources & definitions · ${ids.length} references`));
    if (!ids.length) details.append(node('p','Fictional dataset: no issuer sources or evidence pins.'));
    for (const id of ids) {
      const source = data.sources[id], block = node('div'); block.id = 'source-' + id; block.tabIndex = -1;
      block.append(node('p',`${source.path} · line ${source.line}`),node('blockquote',source.quote.length > 1500 ? source.quote.slice(0,1500) + '… [full capture in linked file]' : source.quote),
        link('Open retained source ↗',source.href,'source-link'));
      details.append(block);
    }
    return details;
  }
  function renderDetails(run) {
    const root = $('run-detail'); root.hidden = !run; root.replaceChildren();
    if (!run) return;
    const head = node('div',null,'detail-head'), title = node('div');
    title.append(node('p','SELECTED RUN','eyebrow'),node('h2',run.name),node('p',`${run.id} / ${run.title}`,'detail-id'));
    head.append(title);
    const artifact = primaryArtifact(run);
    if (artifact) head.append(link(artifact.relationship === 'related' ? 'Open related report ↗' : 'Open report ↗',artifact.href,'primary-button'));
    else if (run.handoff_href) head.append(link('Open primary handoff ↗',run.handoff_href,'primary-button'));
    const layout = node('div',null,'detail-layout'), left = node('div',null,'detail-left'), right = node('div');
    left.append(node('p',run.summary,'detail-description'),node('h3','Scope & open questions','detail-section-title'));
    const gaps = node('ul',null,'gap-list'); run.gaps.forEach(gap => gaps.append(node('li',gap))); left.append(gaps);
    if (run.ratings.length) {
      left.append(node('h3','Dated ratings','detail-section-title'));
      run.ratings.forEach(rating => left.append(node('p',`${rating.label} · ${dated(rating.date)}`,'rating-line')));
    }
    const completion = node('div',null,'completion-box');
    completion.append(node('strong',run.completion === null ? 'Workflow completeness · Not assessed' : `Illustrative completeness · ${run.completion}%`),
      document.createTextNode(run.completion === null
        ? 'A verified checklist for this workflow has not been supplied. Available files and checked ratios do not establish end-to-end completion.'
        : `${run.checkpoints.done} of ${run.checkpoints.total} required checkpoints completed. The example denominator spans sources, analysis, verification, downstream use and delivery. This is workflow progress, not a credit score.`));
    left.append(completion);
    const grid = node('div',null,'metric-grid'); Object.keys(metricNames).forEach(key => grid.append(renderMetric(run,key))); right.append(grid);
    right.append(node('h3','Deliverables & revision history','detail-section-title'));
    const artifacts = node('ul',null,'artifact-list');
    if (!run.artifacts.length) artifacts.append(node('li',dataset === 'real' ? 'No final deliverable has been indexed for this case.' : 'Fictional example · no actual deliverable.'));
    run.artifacts.forEach(item => {
      const entry = node('li');
      if (item.available) entry.append(link(item.label + ' ↗',item.href)); else entry.append(node('span',item.label + ' · Unavailable'));
      entry.append(node('small',item.issue || (item.state === 'superseded' ? 'Retained failed attempt' : `${item.relationship === 'related' ? 'Related annual report · ' : ''}Candidate · file hashes checked at build`)));
      artifacts.append(entry);
    });
    right.append(artifacts,evidenceDetails(run)); layout.append(left,right); root.append(head,layout);
  }
  function render() {
    const f = filters(), matching = filterRuns(data[dataset],f);
    const rows = sortKey ? sortRuns(matching,sortKey,direction) : matching;
    if (!rows.some(r => r.id === selected)) selected = rows[0]?.id;
    $('run-rows').replaceChildren(...rows.map(runRow));
    $('results-count').textContent = `${rows.length} of ${data[dataset].length} runs · ${new Set(rows.map(r => r.issuer)).size} issuers`;
    $('empty-state').hidden = rows.length > 0;
    document.querySelectorAll('[data-sort]').forEach(th => th.setAttribute('aria-sort',th.dataset.sort === sortKey ? direction === 'asc' ? 'ascending' : 'descending' : 'none'));
    document.querySelectorAll('[data-issuer]').forEach(el => {const active = el.dataset.issuer === issuer; el.classList.toggle('active',active); el.setAttribute('aria-pressed',String(active));});
    $('all-runs').classList.toggle('active',!issuer && !f.availability);
    $('all-runs').setAttribute('aria-pressed',String(!issuer && !f.availability));
    $('reports-only').classList.toggle('active',f.availability === 'report');
    $('reports-only').setAttribute('aria-pressed',String(f.availability === 'report'));
    const advanced = ['basis','period','leverageMin','leverageMax','coverageMin','coverageMax'].filter(key => f[key]).length;
    $('metric-filter-count').textContent = advanced ? `· ${advanced} active` : '';
    renderDetails(rows.find(r => r.id === selected));
  }
  fields.forEach(id => $(id).addEventListener($(id).tagName === 'SELECT' ? 'change' : 'input',render));
  document.querySelectorAll('[data-sort]').forEach(th => th.querySelector('button').addEventListener('click',()=>{
    direction = sortKey === th.dataset.sort && direction === 'asc' ? 'desc' : 'asc'; sortKey = th.dataset.sort; render();
  }));
  $('real-data').addEventListener('click',() => switchDataset('real'));
  $('demo-data').addEventListener('click',() => switchDataset('illustrative'));
  $('clear').addEventListener('click',reset); $('empty-reset').addEventListener('click',reset);
  $('all-runs').addEventListener('click',reset);
  $('reports-only').addEventListener('click',()=>{issuer=''; $('availability').value='report'; render();});
  document.addEventListener('keydown',event => {
    if (event.key === '/' && !event.metaKey && !event.ctrlKey && !event.altKey && !['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)) {
      event.preventDefault(); $('search').focus();
    }
  });
  $('build-date').textContent = data.built_at;
  initialiseDataset(); render();
})();
