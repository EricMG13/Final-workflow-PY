/* Pure screening operations for the Library screen; no analysis or metric calculations. Ported unchanged from the approved example (examples/issuer-library/logic.js). */
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
  function filterRuns(runs, filters) {
    const search = (filters.search || '').trim().toLocaleLowerCase();
    return runs.filter(run => {
      const haystack = [run.name, run.issuer, run.id, run.title, run.sector, run.workflow].join(' ').toLocaleLowerCase();
      if (search && !haystack.includes(search)) return false;
      for (const [key, field] of [['sector','sector'],['workflow','workflow'],['issuer','issuer'],['period','period_kind']]) {
        if (filters[key] && run[field] !== filters[key]) return false;
      }
      if (filters.availability === 'report' && !hasReport(run)) return false;
      if (filters.availability === 'handoff' && hasReport(run)) return false;
      if (filters.basis && run.metrics.leverage?.basis !== filters.basis) return false;
      if (filters.completion === 'unassessed' && run.completion !== null) return false;
      if (filters.completion && filters.completion !== 'unassessed' && !inRange(run.completion, filters.completion, '')) return false;
      return inRange(numberOf(run.metrics.leverage), filters.leverageMin, filters.leverageMax)
        && inRange(numberOf(run.metrics.coverage), filters.coverageMin, filters.coverageMax);
    });
  }
  function sortRuns(runs, key, direction) {
    const value = run => key === 'leverage' || key === 'coverage' ? numberOf(run.metrics[key]) : run[key];
    return [...runs].sort((left, right) => {
      const a = value(left), b = value(right);
      if (a == null && b == null) return left.id.localeCompare(right.id);
      if (a == null) return 1;
      if (b == null) return -1;
      const difference = typeof a === 'number' ? a - b : String(a).localeCompare(String(b));
      return (direction === 'desc' ? -difference : difference) || left.id.localeCompare(right.id);
    });
  }
  return {numberOf, hasReport, filterRuns, sortRuns};
})();
