"""Historical-source and publication checks. Run from the workspace root; no providers."""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D, localcontext, ROUND_HALF_UP
from copy import deepcopy
from tempfile import TemporaryDirectory
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET

from deploy_vii.registry import canonical, plan
from deploy_vii.report_view import pathways
from deploy_workflow.handoff_delivery import verify_delivery
from deploy_workflow.owners.cpos import run_handoffs

case = Path('runs/cpos-lqd-portfolio-001').resolve()
root = Path.cwd()
load = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
job = load(case / 'workflow.json')
protected = {str(p): sha(p) for p in Path('src').rglob('*.py')}
prior_reports = {str(p): sha(p) for p in (case / 'execution/deliveries').glob('*/report.html')}
for group in ('sources', 'instructions', 'retained_handoffs'):
    for spec in job[group].values(): assert sha(case / spec['path']) == spec['sha256']
expect = load(root / 'runs/lqd-portfolio-001/expectations.json')
raw_source = root / 'runs/lqd-portfolio-001/sources/LQD-20250531-NPORT.xml'
n = {'n': 'http://www.sec.gov/edgar/nport'}
xml = ET.fromstring(raw_source.read_bytes())
assert xml.findtext('.//n:repPdDate', namespaces=n) == expect['portfolio_date']
assert xml.findtext('.//n:repPdEnd', namespaces=n) == expect['not_portfolio_date']
assert xml.findtext('.//n:seriesId', namespaces=n) == 'S000004361'
nav = F(xml.findtext('.//n:netAssets', namespaces=n))
assert nav == F(expect['fund_nav_usd'])
assert F(xml.findtext('.//n:totAssets', namespaces=n)) - F(xml.findtext('.//n:totLiabs', namespaces=n)) == nav
nodes = [(i, x) for i, x in enumerate(xml.findall('.//n:invstOrSec', n), 1) if x.findtext('n:lei', namespaces=n) == expect['issuer_lei']]
assert [i for i, x in nodes] == expect['holding_ordinals'] and len(nodes) == 5
value = lambda x, field: F(x.findtext('n:' + field, namespaces=n))
par = sum(value(x, 'balance') for _, x in nodes)
mark = sum(value(x, 'valUSD') for _, x in nodes)
yr2029 = sum(value(x, 'valUSD') for _, x in nodes if x.findtext('n:debtSec/n:maturityDt', namespaces=n).startswith('2029'))
def loan_value(node):
    conditional = node.find('n:securityLending/n:loanByFundCondition', n)
    if conditional is not None:
        assert conditional.attrib['isLoanByFund'] == 'Y'
        return F(conditional.attrib['loanVal'])
    assert node.findtext('n:securityLending/n:isLoanByFund', namespaces=n) == 'N'
    return F(0)
onloan = sum(loan_value(x) for _, x in nodes)
unknown_loan = deepcopy(nodes[0][1])
unknown_loan.remove(unknown_loan.find('n:securityLending', n))
try: loan_value(unknown_loan)
except AssertionError: pass
else: raise AssertionError('Missing lending status became zero')
selected = next(x for _, x in nodes if x.find('n:identifiers/n:isin', n).attrib['value'] == 'US04010LBG77')
selected_par, selected_value = value(selected, 'balance'), value(selected, 'valUSD')
want = {'issuer_par_usd': par, 'issuer_market_value_usd': mark, 'maturity_2029_value_usd': yr2029,
        'on_loan_value_usd': onloan, 'reported_pct_nav_sum': sum(value(x, 'pctVal') for _, x in nodes),
        'price_10_loss_usd': mark / 10, 'recovery40_proceeds_usd': par * F(2, 5),
        'recovery40_loss_usd': mark - par * F(2, 5), 'recovery60_proceeds_usd': par * F(3, 5),
        'recovery60_loss_usd': mark - par * F(3, 5), 'selected_recovery40_proceeds_usd': selected_par * F(2, 5),
        'selected_recovery40_loss_usd': selected_value - selected_par * F(2, 5)}
for name, expected in want.items(): assert F(expect[name]) == expected, name
ratios = {'issuer_pct_nav': mark / nav * 100, 'selected_pct_nav': selected_value / nav * 100,
          'maturity_2029_pct_issuer': yr2029 / mark * 100, 'price_10_loss_nav_bp': mark / 10 / nav * 10000,
          'recovery_40_loss_nav_bp': want['recovery40_loss_usd'] / nav * 10000,
          'recovery_60_loss_nav_bp': want['recovery60_loss_usd'] / nav * 10000,
          'selected_recovery40_nav_bp': want['selected_recovery40_loss_usd'] / nav * 10000}
with localcontext() as context:
    context.prec = 60
    for name, v in ratios.items():
        assert (D(v.numerator) / D(v.denominator)).quantize(D('.000000001'), rounding=ROUND_HALF_UP) == D(expect[name]), name
assert expect['new_position_size'] is None and expect['risk_budget_limit'] is None
assert selected_value < mark and onloan < mark and yr2029 < mark
for _, node in nodes:
    assert node.findtext('n:units', namespaces=n) == 'PA' and node.findtext('n:curCd', namespaces=n) == 'USD'
assert [canonical(a) for a in job['run']['requested_modules']] == ['CP-3', 'CP-6', 'CP-5']
order = plan(tuple(job['run']['requested_modules']), retained={m: tuple(s['upstream']) for m, s in job['retained_handoffs'].items()})
assert order == ('CP-3', 'CP-6', 'CP-5')
answers = {m: (case / s['path']).read_bytes() for m, s in job['retained_handoffs'].items()}
checked = []
def no_execute(task): raise AssertionError('No repeat analytical run: ' + task.module_id)
def check(task, raw):
    assert raw == answers[task.module_id]
    assert dict(task.handoffs) == {m: answers[m] for m in order[:order.index(task.module_id)]}
    checked.append(task.module_id)
    return ()
report = run_handoffs(case / 'workflow.json', case / 'execution', execute=no_execute, check=check)
assert tuple(checked) == order
for old, digest in prior_reports.items(): assert sha(Path(old)) == digest
manifests = list((case / 'execution').glob('delivery-*.json'))
matched = []
for manifest in manifests:
    try: verify_delivery(manifest, report.parent)
    except ValueError: continue
    matched.append(manifest)
assert len(matched) == 1
view = load(report.parent / 'view.json'); rv = load(report.parent / 'report-view.json')
assert tuple(b['block_id'] for b in rv['blocks']) == next(p.blocks for p in pathways() if p.id == 'portfolio_decision')
assert len(rv['blocks']) == 8 and all(b['state'] == 'populated' for b in rv['blocks'])
assert rv['call'][0]['value_text'] == 'Requires More Work' and rv['call'][0]['meter'] is None
passport = next(p for p in rv['passports'] if p['ref_id'] == rv['call'][0]['ref_id'])
header_fields = {x['name']: x['value'] for x in passport['fields']}
assert header_fields['Source'] == 'CP-6' and header_fields['SHA-256'] == hashlib.sha256(answers['CP-6']).hexdigest()
assert 'Final Sizing Posture: Requires More Work' in header_fields['Quote']
assert 'Insufficient Information' in rv['blocks'][3]['lines'][0]['runs'][0]['text']
facts = citations = raw_cells = 0
for module in view['modules']:
    m = module['module_id']; lines = answers[m].decode().splitlines()
    assert (report.parent / (m + '.md')).read_bytes() == answers[m]
    for fact in module['facts']:
        facts += 1
        assert fact['citations']
        for cite in fact['citations']:
            assert cite['source_id'] == m and cite['source_sha256'] == hashlib.sha256(answers[m]).hexdigest()
            assert cite['quote'] == lines[int(cite['locator'].split()[-1]) - 1]
            citations += 1
        if fact['table_id'].startswith('raw-'):
            fields = [s.strip().replace('**', '').replace('`', '') for s in fact['citations'][0]['quote'].strip('|').split('|')]
            assert fact['label'] == fields[0]
            cell = fields[int(fact['field'][1:]) + 1]
            assert fact['text'] == cell
            raw_cells += 1
capital = rv['blocks'][6]
assert len(capital['rows']) == 5
for row, (ordinal, node) in zip(capital['rows'], nodes, strict=True):
    assert row['label'] == f"{ordinal} / " + node.findtext('n:cusip', namespaces=n)
    loan = node.find('n:securityLending/n:loanByFundCondition', n)
    expected = [node.find('n:identifiers/n:isin', n).attrib['value'], node.findtext('n:debtSec/n:maturityDt', namespaces=n),
                node.findtext('n:debtSec/n:annualizedRt', namespaces=n), node.findtext('n:balance', namespaces=n),
                node.findtext('n:valUSD', namespaces=n), node.findtext('n:pctVal', namespaces=n),
                loan.attrib['loanVal'] if loan is not None else '0; source reports not on loan']
    if loan is None: assert loan_value(node) == 0
    assert [c['text'] for c in row['cells']] == expected
assert all(sha(Path(p)) == digest for p, digest in protected.items())
assert {p.suffix for p in report.parent.iterdir()} == {'.md', '.json', '.html'}
assert not any(p.suffix.lower() in {'.xls', '.xlsx', '.xlsm', '.xlsb'} for p in (case / 'execution').rglob('*'))
assert len(list((case / 'execution/requests').glob('*/*/*.response.md'))) == 3
assert run_handoffs(case / 'workflow.json', case / 'execution', execute=no_execute, check=check) == report
refusals = []
for kind in ('source', 'stale-upstream'):
    with TemporaryDirectory(prefix='lqd-portfolio-refusal-') as tmp:
        wrong = deepcopy(job)
        for group in ('sources', 'instructions', 'retained_handoffs'):
            for s in wrong[group].values(): s['path'] = str((case / s['path']).resolve())
        if kind == 'source': wrong['sources'][next(iter(wrong['sources']))]['sha256'] = '0' * 64
        else: wrong['retained_handoffs']['CP-6']['upstream']['CP-3'] = '0' * 64
        p = Path(tmp) / 'workflow.json'; p.write_text(json.dumps(wrong))
        try: run_handoffs(p, Path(tmp) / 'state', execute=no_execute, check=check)
        except ValueError as error:
            assert ('cpos_input_changed' if kind == 'source' else 'cpos_retained_stale') in str(error)
            refusals.append({'kind': kind, 'refusal': str(error)})
        else: raise AssertionError('Wrong context accepted')
with TemporaryDirectory(prefix='lqd-publication-refusal-') as tmp:
    target = Path(tmp) / 'delivery'
    shutil.copytree(report.parent, target)
    (target / 'report.html').write_bytes((target / 'report.html').read_bytes() + b'\nforged report')
    receipt = load(target / 'delivery.json')
    receipt['files']['report.html'] = sha(target / 'report.html')
    (target / 'delivery.json').write_text(json.dumps(receipt))
    try: verify_delivery(matched[0], target)
    except ValueError as error:
        refusals.append({'kind': 'forged-report-and-receipt', 'refusal': str(error)})
    else: raise AssertionError('Forged publication completed')
pins = load(Path('cases/PINS.json'))
assert all(sha(Path(path)) == digest for path, digest in pins.items())
result = {'report': str(report.relative_to(root)), 'sha256': sha(report), 'all_preset_sections': 8,
          'facts': facts, 'exact_handoff_citations': citations, 'raw_table_values': raw_cells,
          'source_holding_rows_and_fields': [5, 7], 'money_oracle_checks': len(want), 'ratio_oracle_checks': len(ratios),
          'old_report_bytes_preserved': prior_reports, 'code_files_unchanged_during_verification': len(protected),
          'source_context_pins': len(job['sources']), 'case_pins_verified': len(pins), 'negative_controls': refusals,
          'call': rv['call'], 'header_source': header_fields, 'no_executor_resume': True, 'excel_output': False}
v = load(case / 'verification.json'); v['checks'] = result
(case / 'verification.json').write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('old_report_bytes_preserved', 'header_source')}, indent=2))
