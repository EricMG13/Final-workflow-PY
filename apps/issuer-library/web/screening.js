/* Pure screening operations for the Library screen; no analysis or metric calculations. Ported from the approved example (examples/issuer-library/logic.js), extended by Plan 4. */
const LibraryLogic = (() => {
  const numberOf = metric => {
    if (metric == null || metric.value == null || String(metric.value).trim() === '') return null;
    const value = Number(metric.value);
    return Number.isFinite(value) ? value : null;
  };
  const hasReport = run => run.artifacts.some(a => a.available && a.state !== 'superseded');
  const inRange = (value, minimum, maximum) => {
    for (const [bound, lower] of [[minimum, true], [maximum, false]]) {
      if (bound == null || String(bound).trim() === '') continue;
      const threshold = Number(bound);
      if (value == null || !Number.isFinite(threshold) || (lower ? value < threshold : value > threshold)) return false;
    }
    return true;
  };
  const figure = metric => { const n = numberOf(metric); return n !== null && n >= 0 ? n : null; };
  const active = (min, max) => [min, max].some(bound => bound != null && String(bound).trim() !== '');
  const SCALE = 'AAA/Aaa AA+/Aa1 AA/Aa2 AA-/Aa3 A+/A1 A/A2 A-/A3 BBB+/Baa1 BBB/Baa2 BBB-/Baa3 BB+/Ba1 BB/Ba2 BB-/Ba3 B+/B1 B/B2 B-/B3 CCC+/Caa1 CCC/Caa2 CCC-/Caa3 CC/Ca C/C D'.split(' ');
  const RANK = new Map(SCALE.flatMap((row, index) => row.split('/').map(symbol => [symbol, index + 1])));
  function ratingPlace(label) {
    let text = String(label ?? '');
    const limited = text.endsWith('/LD');
    if (limited) text = text.slice(0, -3);
    if (text.startsWith('(P)')) text = text.slice(3);
    if (text.endsWith('(EXP)')) text = text.slice(0, -5);
    if (text === 'SD' || text === 'RD') text = 'D';
    if (!RANK.has(text)) return null;
    return limited ? {rank: SCALE.length, placesAs: 'D'} : {rank: RANK.get(text), placesAs: text};
  }
  function lowestRating(run, scope = 'issuer') {
    let lowest = null, lowestRank = 0;
    for (const rating of run.ratings || []) {
      if (scope !== 'any' && rating.scope !== 'issuer') continue;
      const place = ratingPlace(rating.label);
      if (place && place.rank > lowestRank) { lowest = rating; lowestRank = place.rank; }
    }
    return lowest;
  }
  const lowestRank = (run, filters) => { const rating = lowestRating(run, filters.ratingScope); return rating ? ratingPlace(rating.label).rank : null; };
  const metricGroup = (name, prefix) => ({
    on: f => active(f[prefix + 'Min'], f[prefix + 'Max']),
    recorded: run => figure(run.metrics?.[name]) !== null,
    pass: (run, f) => inRange(figure(run.metrics?.[name]), f[prefix + 'Min'], f[prefix + 'Max'])
  });
  // Facility rules: one facility satisfies every active facility group; one of its quotes satisfies every active quote group.
  const overlaps = (low, high, minimum, maximum) => low !== null && high !== null && inRange(high, minimum, '') && inRange(low, '', maximum);
  const sides = (low, high) => [low ?? high, high ?? low];
  const talkRange = facility => sides(figure(facility.terms?.talk_spread_bps_low), figure(facility.terms?.talk_spread_bps_high));
  const priceRange = quote => {
    const price = figure(quote.terms?.price), bid = figure(quote.terms?.bid), ask = figure(quote.terms?.ask);
    return price !== null ? [price, price] : bid !== null && ask !== null ? [bid, ask] : [null, null];
  };
  const FACILITY = {
    talk: {on: f => active(f.talkMin, f.talkMax), recorded: x => talkRange(x)[0] !== null, pass: (x, f) => overlaps(...talkRange(x), f.talkMin, f.talkMax)},
    margin: {on: f => active(f.marginMin, f.marginMax), recorded: x => figure(x.terms?.margin_bps) !== null, pass: (x, f) => inRange(figure(x.terms?.margin_bps), f.marginMin, f.marginMax)},
    coupon: {on: f => active(f.couponMin, f.couponMax), recorded: x => figure(x.terms?.coupon_pct) !== null, pass: (x, f) => inRange(figure(x.terms?.coupon_pct), f.couponMin, f.couponMax)}
  };
  const QUOTE = {
    price: {on: f => active(f.priceMin, f.priceMax), recorded: x => priceRange(x)[0] !== null, pass: (x, f) => overlaps(...priceRange(x), f.priceMin, f.priceMax)},
    yield: {on: f => active(f.yieldMin, f.yieldMax), recorded: x => figure(x.terms?.yield_pct) !== null, pass: (x, f) => inRange(figure(x.terms?.yield_pct), f.yieldMin, f.yieldMax)}
  };
  function facilityMatches(run, filters, names) {
    const facilityNames = names.filter(name => FACILITY[name]), quoteNames = names.filter(name => QUOTE[name]);
    return (run.facilities || []).some(facility => facilityNames.every(name => FACILITY[name].pass(facility, filters))
      && (!quoteNames.length || (facility.quotes || []).some(quote => quoteNames.every(name => QUOTE[name].pass(quote, filters)))));
  }
  const facilityGroup = name => {
    const rule = FACILITY[name] || QUOTE[name];
    const items = run => FACILITY[name] ? run.facilities || [] : (run.facilities || []).flatMap(facility => facility.quotes || []);
    return {on: rule.on, recorded: run => items(run).some(rule.recorded), pass: (run, f) => facilityMatches(run, f, [name])};
  };
  const GROUPS = {
    classification: {on: f => !!f.classification, recorded: run => !!run.classification,
      pass: (run, f) => f.classification === 'not_stated' ? !run.classification : run.classification === f.classification},
    currency: {on: f => !!f.currency, recorded: run => !!run.currency, pass: (run, f) => run.currency === f.currency},
    rating: {on: f => !!(f.ratingBelow || f.ratingAbove), recorded: (run, f) => lowestRank(run, f) !== null,
      pass: (run, f) => {
        const rank = lowestRank(run, f);
        return [[f.ratingBelow, (a, b) => a >= b], [f.ratingAbove, (a, b) => a <= b]].every(([row, ok]) =>
          !row || (rank !== null && SCALE.includes(row) && ok(rank, SCALE.indexOf(row) + 1)));
      }},
    leverage: metricGroup('leverage', 'leverage'), net_leverage: metricGroup('net_leverage', 'netLeverage'),
    coverage: metricGroup('coverage', 'coverage'), cash: metricGroup('cash', 'cash'), undrawn: metricGroup('undrawn', 'undrawn'),
    talk: facilityGroup('talk'), margin: facilityGroup('margin'), coupon: facilityGroup('coupon'),
    price: facilityGroup('price'), yield: facilityGroup('yield'),
    limitation: {on: f => !!f.limitation, recorded: run => (run.gaps || []).length > 0, pass: (run, f) => (run.gaps || []).includes(f.limitation)}
  };
  // Issuers differing only in ASCII case are one issuer; shown text stays as recorded.
  const issuerKey = issuer => String(issuer || '').toLowerCase();
  const activeGroups = filters => Object.keys(GROUPS).filter(name => GROUPS[name].on(filters));
  function commonPass(run, filters) {
    const search = (filters.search || '').trim().toLocaleLowerCase();
    const haystack = [run.name, run.issuer, run.id, run.title, run.sector, run.workflow].join(' ').toLocaleLowerCase();
    if (search && !haystack.includes(search)) return false;
    for (const [key, field] of [['sector','sector'],['workflow','workflow'],['issuer','issuer'],['period','period_kind']]) {
      if (filters[key] && (key === 'issuer' ? issuerKey(run.issuer) !== issuerKey(filters.issuer) : run[field] !== filters[key])) return false;
    }
    if (filters.availability === 'report' && !hasReport(run)) return false;
    if (filters.availability === 'handoff' && hasReport(run)) return false;
    if (filters.basis && run.metrics?.leverage?.basis !== filters.basis) return false;
    if (filters.completion === 'unassessed' && run.completion !== null) return false;
    return !(filters.completion && filters.completion !== 'unassessed' && !inRange(run.completion, filters.completion, ''));
  }
  // Latest-run rule: rows kept with notScreened set, or dropped when another run of the issuer is the screened one.
  function latestStatus(runs, filters) {
    const status = new Map(runs.map(run => [run, {notScreened: false}]));
    if (filters.runs === 'any') return status;
    const groupOf = run => run.issuer === 'Unclassified' ? 'row:' + run.id : 'issuer:' + issuerKey(run.issuer);
    const dateOf = run => run.date || '';
    const latestDate = new Map();
    for (const run of runs.filter(hasReport)) {
      const best = latestDate.get(groupOf(run));
      if (best === undefined || dateOf(run) > best) latestDate.set(groupOf(run), dateOf(run));
    }
    for (const run of runs) {
      const latest = latestDate.get(groupOf(run));
      if (hasReport(run) && dateOf(run) === latest) continue;
      if (latest !== undefined && (hasReport(run) || dateOf(run) <= latest)) status.delete(run);
      else status.get(run).notScreened = true;
    }
    return status;
  }
  const creditActive = (filters, names) => names.length > 0 || !!filters.basis;
  // Rows kept by the Latest rule and common filters that satisfy every active group except those in `skip`.
  function evaluate(runs, filters, skip = []) {
    const status = latestStatus(runs, filters), names = activeGroups(filters), credit = creditActive(filters, names);
    return runs.filter(run => status.has(run) && !(credit && status.get(run).notScreened) && commonPass(run, filters))
      .filter(run => {
        const kept = names.filter(name => !skip.includes(name)), joint = kept.filter(name => FACILITY[name] || QUOTE[name]);
        return kept.filter(name => !joint.includes(name)).every(name => GROUPS[name].pass(run, filters))
          && (!joint.length || facilityMatches(run, filters, joint));
      })
      .map(run => ({run, notScreened: status.get(run).notScreened}));
  }
  const screened = (runs, filters) => evaluate(runs, filters);
  const filterRuns = (runs, filters) => evaluate(runs, filters).map(entry => entry.run);
  function hiddenBy(runs, filters, group) {
    if (!GROUPS[group] || !GROUPS[group].on(filters)) return [];
    return evaluate(runs, filters, [group]).map(entry => entry.run)
      .filter(run => !GROUPS[group].recorded(run, filters) && !GROUPS[group].pass(run, filters));
  }
  function coverage(runs, filters) {
    return Object.fromEntries(activeGroups(filters).map(name => [name, {
      recorded: runs.filter(run => GROUPS[name].recorded(run, filters)).length,
      hidden: hiddenBy(runs, filters, name).length
    }]));
  }
  function sortRuns(runs, key, direction, filters = {}) {
    const metrics = ['leverage', 'net_leverage', 'coverage', 'cash', 'undrawn'];
    const value = run => metrics.includes(key) ? figure(run.metrics?.[key]) : key === 'rating' ? lowestRank(run, filters) : run[key];
    return [...runs].sort((left, right) => {
      const a = value(left), b = value(right);
      if (a == null && b == null) return left.id.localeCompare(right.id);
      if (a == null) return 1;
      if (b == null) return -1;
      const difference = typeof a === 'number' ? a - b : String(a).localeCompare(String(b));
      return (direction === 'desc' ? -difference : difference) || left.id.localeCompare(right.id);
    });
  }
  return {issuerKey, numberOf, hasReport, filterRuns, sortRuns, screened, coverage, hiddenBy, ratingPlace, lowestRating, scale: SCALE};
})();
