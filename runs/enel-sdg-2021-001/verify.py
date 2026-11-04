from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D
import copy, hashlib, json, re, tempfile
from deploy_vii.registry import canonical, plan
from deploy_workflow.owners.cpos import run_handoffs
from deploy_workflow.handoff_delivery import verify_delivery

root = Path.cwd()
case = root / 'runs/enel-sdg-2021-001'
load = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
job = load(case / 'workflow.json')
expected = load(case / 'expectations.json')
calc = load(case / 'CP-2E-calculations.json')
out = calc['outputs']
protected = {str(p.relative_to(root)): sha(p) for p in (root / 'src').rglob('*.py')}
for name in ('tdg-001', 'tdg-003', 'cpos-tdg-macro-esg-001', 'cpos-tdg-forecast-001', 'cpos-tdg-model-001'):
    protected.update({str(p.relative_to(root)): sha(p) for p in (root / 'runs' / name).rglob('*') if p.is_file()})
for group in ('sources', 'instructions'):
    for name, spec in job[group].items():
        assert sha((case / spec['path']).resolve()) == spec['sha256'], name
assert calc['upstream_CP-0_sha256'] == sha(case / 'CP-0-attempt-1.md')
for name, digest in calc['source_pdf_hashes'].items():
    assert digest == job['sources'][name]['sha256']

# Literal source-input oracle precedes the model answer; no production financial helper.
i = expected['source_inputs']
p, step, price = F(i['principal_eur_m']), F(i['step_bp']) / 10000, F(i['issue_price_pct']) / 100
assert (p, step, price) == (F(1000), F(1, 400), F(99123, 100000))
want = {'step_decimal': step, 'initial_coupon_decimal': F(0), 'stepped_coupon_decimal': step,
        'initial_annual_coupon_eur_m': F(0), 'stepped_annual_coupon_eur_m': p * step,
        'increment_eur_m': p * step, 'gross_issue_proceeds_eur_m': p * price,
        'par_less_gross_proceeds_eur_m': p * (1 - price), 'displayed_kpi_gap_pp': F('0.5')}
for key, value in want.items():
    assert F(out[key]) == value, key
ratio = F(46580, 85535) * 100
gap = F(55) - ratio
assert ratio == F(expected['independent_expectations']['kpi_ratio_pct_fraction'])
assert gap == F(expected['independent_expectations']['kpi_gap_pp_fraction'])
assert abs(F(out['recomputed_kpi_pct']) - ratio) < F(1, 10**30)
assert abs(F(out['recomputed_gap_pp']) - gap) < F(1, 10**30)
assert D(out['recomputed_kpi_pct']).quantize(D('.0001')) == D('54.4572')
assert D(out['recomputed_gap_pp']).quantize(D('.0001')) == D('.5428')
assert i['observation'] < i['knowledge_cutoff'] < i['reference_date'] < i['maturity']

# Pin primary-page strings rather than just repeating the analytical answer.
pages = {}
for name in ('S1-efi-2019', 'S2-supplement-2019', 'S3-kpi-june-2021', 'S4-issuer-target'):
    pages[name] = {x['page']: ' '.join(x['text'].split()) for x in map(json.loads, (case / 'sources' / (name + '.jsonl')).read_text().splitlines())}
source_checks = [('S1-efi-2019', 51, 'Euro 1,000 million at a fixed rate of 0.00%'),
                 ('S1-efi-2019', 51, '99.123%'), ('S1-efi-2019', 51, '0.189%'),
                 ('S1-efi-2019', 51, 'by 25 bps'),
                 ('S2-supplement-2019', 70, 'no more than once'),
                 ('S2-supplement-2019', 72, 'notification by the Guarantor'),
                 ('S2-supplement-2019', 73, 'no later than 45 days'),
                 ('S2-supplement-2019', 91, 'no event later than 30 days'),
                 ('S3-kpi-june-2021', 4, '46.580'), ('S3-kpi-june-2021', 4, '85.535'),
                 ('S3-kpi-june-2021', 4, '54,5%'), ('S3-kpi-june-2021', 5, i['isin']),
                 ('S3-kpi-june-2021', 3, 'Rome, August 3, 2021'),
                 ('S3-kpi-june-2021', 1, 'limited assurance conclusion'),
                 ('S4-issuer-target', 1, 'equal to or greater than 55%')]
for name, page, text in source_checks:
    assert text in pages[name][page], (name, page, text)
responses = {m: (case / (m + '-attempt-1.md')).read_bytes() for m in ('CP-0', 'CP-2E')}
producer = responses['CP-2E'].decode()
consumer = (case / 'CP-3C-consumer.md').read_text()
assert sha(case / 'CP-2E-attempt-1.md') in consumer
for phrase in ('EUR2.5m per full year', 'June 17, 2024', 'June 30,', 'December 31, 2021', 'Unknown', 'double count', 'missing inputs, not zero'):
    assert phrase in consumer, phrase
assert tuple(re.findall(r'^## (.*)$', consumer, re.M)) == ('Request', 'Sources', 'Findings', 'Calculations', 'Gaps', 'Next module')
assert canonical('CP-2F') == 'CP-2E' and plan(('CP-2F',)) == ('CP-0', 'CP-2E')
checked = []
def check(task, body):
    assert body == responses[task.module_id]
    assert task.instructions == (case / 'instructions.md').read_bytes()
    assert task.run.requested_modules == ('CP-2F',)
    assert dict(task.handoffs) == ({} if task.module_id == 'CP-0' else {'CP-0': responses['CP-0']})
    checked.append(task.module_id)
    return ()
def no_execute(task):
    raise AssertionError('Unexpected repeat dispatch: ' + task.module_id)
report = run_handoffs(case / 'workflow.json', case / 'execution', execute=no_execute, check=check)
assert checked == ['CP-0', 'CP-2E']
manifest, = (case / 'execution').glob('delivery-*.json')
assert verify_delivery(manifest, report.parent) == report
view = load(report.parent / 'view.json')
rv = load(report.parent / 'report-view.json')
assert rv['call_withheld'] == 'not_requested'
assert all(b['state'] == 'populated' for b in rv['blocks'])
facts = citations = table_values = 0
raw_tables = []
for module in view['modules']:
    m = module['module_id']; lines = responses[m].decode().splitlines()
    assert (report.parent / (m + '.md')).read_bytes() == responses[m]
    for fact in module['facts']:
        facts += 1
        assert fact['citations']
        for cite in fact['citations']:
            assert cite['source_id'] == m and cite['source_sha256'] == hashlib.sha256(responses[m]).hexdigest()
            assert cite['quote'] == lines[int(cite['locator'].split()[-1]) - 1]
            citations += 1
        if m == 'CP-2E' and fact['table_id'].startswith('raw-'):
            cells = [x.strip() for x in fact['citations'][0]['quote'].strip('|').split('|')]
            assert fact['label'] == cells[0] and fact['text'] == cells[int(fact['field'][1:]) + 1]
            table_values += 1
    if m == 'CP-2E':
        raw_tables = [t for t in module['tables'] if t['table_id'].startswith('raw-')]
assert len(raw_tables) == 8  # T2G.5 has two tables; T2G.7 is prose.
assert {re.search(r'T2G\.\d', t['title'])[0] for t in raw_tables} == {'T2G.' + str(n) for n in (1, 2, 3, 4, 5, 6, 8)}
main = rv['blocks'][1]
assert main['rows'][0]['label'] == 'Instrument' and len(main['rows']) == 10
assert len(main['tabs']) == 4
coupon_tab = next(t for t in main['tabs'] if t['rows'][0]['label'] == 'Initial coupon')
assert [r['cells'][1]['text'] for r in coupon_tab['rows']] == ['0', '2.5', '2.5', '991.23', '8.77']
assert {p.suffix for p in report.parent.iterdir()} == {'.md', '.json', '.html'}
assert load(report.parent / 'delivery.json')['excel_output'] is False
assert not any(p.suffix.lower() in {'.xls', '.xlsx', '.xlsm', '.xlsb', '.xltx', '.xltm'} for p in (case / 'execution').rglob('*'))
assert len(list((case / 'execution/requests').glob('*/*/*.response.md'))) == 2
assert not (case / 'execution/requests/CP-2F').exists()

# Synthetic controls concern arithmetic and condition logic, never issuer outcomes.
controls = {'equality_is_numeric_pass_only': F(55) >= F(55),
            'interim_below_target_not_final_failure': i['observation'] != i['reference_date'],
            'full_condition_with_unknown_notice_not_established': all(x is True for x in (True, True, None)) is False,
            'known_zero_distinct_from_missing': F(out['initial_annual_coupon_eur_m']) == 0 and None != 0,
            'wrong_cash_would_fail_oracle': F(25) != want['increment_eur_m']}
assert all(controls.values())
with tempfile.TemporaryDirectory(prefix='enel-source-refusal-') as tmp:
    bad = copy.deepcopy(job)
    for group in ('sources', 'instructions'):
        for spec in bad[group].values(): spec['path'] = str((case / spec['path']).resolve())
    bad['sources']['S1-efi-2019']['sha256'] = '0' * 64
    pth = Path(tmp) / 'workflow.json'; pth.write_text(json.dumps(bad))
    try:
        run_handoffs(pth, Path(tmp) / 'state', execute=no_execute, check=check)
    except ValueError as exc:
        refusal = str(exc); assert 'cpos_input_changed' in refusal
    else: raise AssertionError('Changed source accepted')
for path, digest in protected.items(): assert sha(root / path) == digest, path
result = {'report': str(report.relative_to(root)), 'report_sha256': sha(report),
          'source_phrase_checks': len(source_checks), 'raw_tables': len(raw_tables),
          'raw_table_rows': sum(len(t['rows']) for t in raw_tables), 'exact_table_values': table_values,
          'facts': facts, 'exact_citations': citations, 'no_executor_resume': True,
          'source_refusal': refusal, 'synthetic_controls': controls,
          'protected_files_unchanged_during_verification': len(protected),
          'independent_money_expectations': {k: str(v) for k, v in want.items()},
          'ratio_fraction': str(ratio), 'gap_pp_fraction': str(gap),
          'consumer': {'path': str((case / 'CP-3C-consumer.md').relative_to(root)), 'sha256': sha(case / 'CP-3C-consumer.md')},
          'file_extensions': ['.html', '.json', '.md'], 'excel_output': False}
Path('/tmp/final-workflow-enel-check-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
