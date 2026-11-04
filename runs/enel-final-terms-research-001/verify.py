"""Case-only verification; run from the project root. No search or provider call."""
from pathlib import Path
import hashlib
import json
from deploy_workflow.handoff_delivery import section, table, verify_delivery
from deploy_workflow.owners.cpos import run_handoffs

case = Path('runs/enel-final-terms-research-001')
load = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
job = load(case / 'workflow.json')
brief = load(case / 'RESEARCH_enel-final-terms-research-001.json')
record = load(case / 'verification.json')
canonical = json.dumps(brief, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
assert record['approved_plan_hash'] == 'sha256:' + hashlib.sha256(canonical).hexdigest()
assert len(brief['questions']) == 1 and brief['questions'][0]['question_id'] == 'RQ-final-terms'
assert brief['mode'] == 'standalone' and brief['source_mode'] == 'web_only'
assert len(list((case / 'sources').iterdir())) == 4
assert 'Empty search results' in (case / 'sources/search-initial.json').read_text()
assert 'Final Terms' in (case / 'sources/lead-retrieval.json').read_text()
assert not list((case / 'sources').glob('*.pdf'))
prior_paths = [case / job['sources'][k]['path'] for k in ('prior-pricing', 'prior-calculations')]
protected = {str(p): sha(p) for p in prior_paths}
protected.update({str(p): sha(p) for p in Path('src').rglob('*.py')})
for group in ('sources', 'instructions', 'retained_handoffs'):
    for spec in job[group].values():
        assert sha(case / spec['path']) == spec['sha256']
responses = {m: (case / s['path']).read_bytes() for m, s in job['retained_handoffs'].items()}
research = responses['CP-DR'].decode().splitlines()
qcols, qrows = table(section(research, 'TDR.1 — locked question and workstream'))
assert qcols == list(brief['questions'][0])
assert len(qrows) == 1 and qrows[0][2] == list(brief['questions'][0].values())
ecols, erows = table(section(research, 'TDR.2 — evidence and gap ledger'))
assert len(ecols) == 10 and len(erows) == 3
assert {row[2][7] for row in erows} == {'gap'}
fcols, frows = table(section(research, 'TDR.3 — finding and permitted consequence'))
assert len(fcols) == 7 and len(frows) == 1
assert frows[0][2][4] == 'UNRESOLVED'
assert '0 ANSWERED / 1 locked question = 0%' in responses['CP-DR'].decode()
acols, arows = table(section(responses['CP-2E'].decode().splitlines(), 'Research adoption'))
assert len(acols) == 5 and len(arows) == 1
assert arows[0][2][:3] == ['RQ-final-terms', hashlib.sha256(responses['CP-DR']).hexdigest(), 'REJECTED']
assert 'EUR2.5m' in responses['CP-2E'].decode()
assert 'Still missing' in responses['CP-2E'].decode()
checked = []
def check(task, body):
    assert body == responses[task.module_id]
    assert dict(task.handoffs) == ({} if task.module_id == 'CP-DR' else {'CP-DR': responses['CP-DR']})
    checked.append(task.module_id)
    return ()
def no_execute(task):
    raise AssertionError('No duplicate analysis permitted: ' + task.module_id)
report = run_handoffs(case / 'workflow.json', case / 'execution', execute=no_execute, check=check)
assert checked == ['CP-DR', 'CP-2E']
manifest, = (case / 'execution').glob('delivery-*.json')
assert verify_delivery(manifest, report.parent) == report
view = load(report.parent / 'view.json')
rv = load(report.parent / 'report-view.json')
facts = citations = 0
for module in view['modules']:
    m = module['module_id']; lines = responses[m].decode().splitlines()
    assert (report.parent / (m + '.md')).read_bytes() == responses[m]
    for fact in module['facts']:
        facts += 1
        assert fact['citations']
        for cite in fact['citations']:
            assert cite['source_sha256'] == hashlib.sha256(responses[m]).hexdigest()
            assert cite['quote'] == lines[int(cite['locator'].split()[-1]) - 1]
            citations += 1
        if fact['table_id'].startswith('raw-'):
            fields = [s.strip() for s in fact['citations'][0]['quote'].strip('|').split('|')]
            assert fact['label'] == fields[0] and fact['text'] == fields[int(fact['field'][1:]) + 1]
assert all(b['state'] == 'populated' for b in rv['blocks'])
assert rv['call_withheld'] == 'not_requested'
assert len(rv['blocks'][1]['rows']) == 7
assert {p.suffix for p in report.parent.iterdir()} == {'.html', '.json', '.md'}
assert load(report.parent / 'delivery.json')['excel_output'] is False
assert not any(p.suffix.lower() in {'.xls', '.xlsx', '.xlsm', '.xlsb'} for p in (case / 'execution').rglob('*'))
assert len(list((case / 'execution/requests').glob('*/*/*.response.md'))) == 2
for path, digest in protected.items():
    assert sha(Path(path)) == digest
print(json.dumps({'report': str(report), 'sha256': sha(report), 'facts': facts, 'exact_citations': citations,
                  'locked_questions': 1, 'answered_questions': 0, 'coverage_pct': 0,
                  'research_outcome': 'UNRESOLVED', 'adoption': 'REJECTED',
                  'no_duplicate_execution': True, 'previous_files_unchanged_during_check': len(protected),
                  'excel_output': False}, indent=2))
