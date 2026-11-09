/* Adapt the existing context form; its build, fill and validation rules stay authoritative. */
(() => {
  const form = $('f');
  const optional = new Map();
  function disclosure(label) {
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = label; details.append(summary);
    return details;
  }
  const identity = $('sec2'), grid = identity.querySelector('.grid');
  const extra = disclosure('Additional issuer details');
  [...grid.children].slice(2).forEach(item => extra.append(item));
  // The issue classification is required, so it stays visible beside the issuer name and ID.
  const classification = $('classf');
  [...identity.children].filter(item => item !== classification && (item.tagName === 'FIELDSET' || (item.className === 'grid' && item !== grid))).forEach(item => extra.append(item));
  identity.append(extra);
  form.prepend(identity);
  for (let number = 4; number <= 10; number++) {
    const section = $('sec' + number), details = disclosure(STEP_SHORT[number]);
    section.before(details); details.append(section); optional.set(number, details);
  }
  const notice = disclosure('Workflow capabilities and limitations');
  document.querySelector('.notice').before(notice);
  notice.append(document.querySelector('.notice'), $('panel'));
  wide.removeEventListener('change',syncPanel);
  syncPanel=function(){ $('panel').open=true; };
  wide.addEventListener('change',syncPanel);syncPanel();
  document.querySelector('.layout').after(notice);
  const saved = $('sec1').querySelector('.load');
  form.before(saved);
  saved.querySelector('.help').textContent = 'Load context.json to populate this form. You can review and edit every value before continuing.';
  document.querySelector('.legend').textContent = 'Required fields are marked. Defaults are preselected; optional details remain available below.';

  let lastHeight = 0;
  function resize() {
    const height = Math.ceil(document.body.getBoundingClientRect().height);
    if (height !== lastHeight) { lastHeight = height; parent.postMessage({type:'cpos:height',height}, '*'); }
  }
  renderSteps = function(sequence, context) {
    document.querySelectorAll('section.sec').forEach(section => {
      const number = Number(section.dataset.n);
      section.hidden = number === 11 || !sequence.includes(number);
      const wrapper = optional.get(number);
      if (wrapper) wrapper.hidden = section.hidden;
      section.querySelector('.n').textContent = '';
      section.querySelector('.stepline').textContent = '';
    });
    parent.postMessage({type:'cpos:ready',ready:errs.length === 0}, '*');
  };
  renderNav = function() {};
  gotoStep = function(number) {
    if(number === 11)number = 2;
    cur = number;
    update();
    const section = $('sec' + number);
    if (optional.has(number)) optional.get(number).open = true;
    section.querySelector('h2').focus();
    section.scrollIntoView({block:'start'});
  };
  window.addEventListener('message', event => {
    if (event.source !== parent || event.data?.type !== 'cpos:get-context') return;
    const context = update();
    if (errs.length) {
      errs.forEach(error => { tried[error.sec] = true; });
      cur = Number(errs[0].sec); update();
      go(errs[0].el.id);
    }
    parent.postMessage({type:'cpos:context',context,problems:errs.map(error=>error.msg)}, '*');
  });
  // Show module names for the CP- codes the form prints. Text nodes only: attributes, input values and
  // option text (which is the option's value) keep codes, so the emitted context is unchanged.
  let names = null;
  // Each host's title is the codes of all its text nodes, set only where the host had no title of its own.
  const titled = new Map();
  const shown = new WeakMap(), skipped = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'OPTION']);
  const codePattern = /\bCP-[A-Z0-9]+\b/g;
  const observer = new MutationObserver(() => applyNames());
  const watchBody = () => observer.observe(document.body, {childList:true, characterData:true, subtree:true});
  function applyNames() {
    if (!names) return;
    observer.disconnect();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), codes = new Map();
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const host = node.parentElement;
      if (!host || skipped.has(host.tagName) || host.closest('option')) continue;
      const known = shown.get(node);
      const original = known && known.text === node.nodeValue ? known.original : node.nodeValue;
      const found = [];
      const text = original.replace(codePattern, code => {
        if (!Object.hasOwn(names, code)) return code;
        found.push(code); return names[code];
      });
      if (!found.length) continue;
      node.nodeValue = text;
      shown.set(node, {original, text});
      codes.set(host, (codes.get(host) || []).concat(found));
    }
    for (const [host, title] of titled) {
      if (codes.has(host)) continue;
      if (host.title === title) host.removeAttribute('title');
      titled.delete(host);
    }
    for (const [host, list] of codes) {
      const title = list.join(', ');
      if (titled.has(host) ? host.title !== titled.get(host) : host.hasAttribute('title')) continue;
      host.title = title;
      titled.set(host, title);
    }
    watchBody();
  }
  window.addEventListener('message', event => {
    const data = event.data;
    if (event.source !== parent || data?.type !== 'cpos:names' || !data.names || typeof data.names !== 'object') return;
    const entries = Object.entries(data.names);
    if (!entries.every(([, value]) => typeof value === 'string')) return;
    names = Object.fromEntries(entries);
    applyNames();
  });

  new ResizeObserver(resize).observe(document.body);
  document.addEventListener('toggle', resize, true);
  update(); resize();
})();
