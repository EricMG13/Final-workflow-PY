from pathlib import Path
from datetime import date
from decimal import Decimal,localcontext
import hashlib,html,json,re
from deploy_vii.contracts import Citation,Fact,ModuleView,ReportTable,Run,Source,Span,TableColumn,TableRow,View
from deploy_workflow.handoff_delivery import table,plain
from deploy_vii.model.frame import Cell as NumberCell,SourceRef
from deploy_vii.model._cells import calc,CONTEXT
from deploy_vii.model.metrics import _ratio
from deploy_vii.bindings import Binding,BindingMap
from deploy_vii.report_view import FactCoord,ReportView,_ChartPoint,_figure_of_points,build,pathways
from deploy_vii.render import render
root=Path.cwd();case=root/'runs/tdg-model-001';manifest=json.loads((case/'inputs.json').read_text())
raws={};lines={};sources=[];facts=[];tables=[];bindings=[];copies={};citations={};source_tables={}
for key,spec in manifest['inputs'].items():
 raw=(root/spec['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==spec['sha256'],key
 copies[key+('.json' if key=='forecast_exact' else '.md')]=raw
 if key=='forecast_exact':continue
 raws[key]=raw;ls=raw.decode().splitlines();lines[key]=ls
 assert tuple(x[3:] for x in ls if x.startswith('## '))==('Request','Sources','Findings','Calculations','Gaps','Next module'),key
 sources.append(Source(source_id=key,name=key+'.md',status='ready',sha256=spec['sha256'],media_type='text/markdown',spans=tuple(Span(locator=f'line {i}',text=t) for i,t in enumerate(ls,1) if t.strip()),extractor='literal-markdown-lines',extraction_status='complete',limitation='Actual retained analytical handoff; scope and underlying source qualifications remain.'))
 # Preserve every original pipe table as literal text, with no number/unit reinterpretation.
 ti=0;i=0;heading='Retained handoff table'
 while i<len(ls):
  if ls[i].startswith(('### ','**')):heading=plain(ls[i].lstrip('#').strip())
  if ls[i].startswith('|') and i+1<len(ls) and re.fullmatch(r'\|[ :|\-]+\|',ls[i+1]):
   headers,rows=table([(j+1,ls[j]) for j in range(i,len(ls))]);tid=f'raw-{key}-{ti}';layouts=[]
   for ri,(no,quote,values) in enumerate(rows):
    ids=[]
    for ci,text in enumerate(values[1:]):
     fid=f'{tid}.r{ri}.c{ci}';ids.append(fid)
     facts.append(Fact(fact_id=fid,label=plain(values[0]),table_id=tid,row_id=f'r{ri}',field=f'c{ci}',text=plain(text) or 'Empty source cell',basis='Literal source-handoff table; no financial reinterpretation.',value_class='source',citations=(Citation(source_id=key,source_sha256=spec['sha256'],locator=f'line {no}',quote=quote),)))
    layouts.append(TableRow(row_id=f'r{ri}',label=plain(values[0]),fact_ids=tuple(ids)))
   tables.append(ReportTable(table_id=tid,title=f'{key}: {heading}',columns=tuple(TableColumn(field=f'c{j}',label=plain(h)) for j,h in enumerate(headers[1:])),rows=tuple(layouts),row_header=plain(headers[0])))
   bindings.append(Binding(fact_coord=FactCoord(module_id='CP-MODEL',table_id=tid),block_id='evidence',cell_slot=tid,unit_class='text'))
   source_tables[(key,i)]=(headers,rows)
   ti+=1;i=rows[-1][0]
  else:i+=1

def selected(key,anchor):
 matches=[i for i,t in enumerate(lines[key]) if t==anchor];assert len(matches)==1,anchor
 i=matches[0];return table([(j+1,lines[key][j]) for j in range(i+1,len(lines[key]))])
def read(key,anchor,label,column):
 headers,rows=selected(key,anchor);matched=[r for r in rows if r[2][0]==label];assert len(matched)==1,label
 no,quote,values=matched[0]
 if column not in headers:return NumberCell(None,'NOT_SOURCED',note='Period is absent from this retained source bridge')
 lexeme=values[headers.index(column)];ref=SourceRef(key,f'line {no}',lexeme)
 citations[(key,f'line {no}')]=Citation(source_id=key,source_sha256=manifest['inputs'][key]['sha256'],locator=f'line {no}',quote=quote)
 if lexeme=='—':return NumberCell(None,'NOT_STATED',sources=(ref,),note='Source dash retained, not zero')
 assert re.fullmatch(r'(?:-?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?|\((?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?\))',lexeme),lexeme
 amount=Decimal(lexeme.replace(',','').replace('(','-').replace(')',''));assert amount.is_finite()
 return NumberCell(amount,basis='REPORTED',sources=(ref,))
inc='### T4.4 — Income statement and comprehensive-income/equity supplements';cf='### T4.5 — Cash-flow statement';bs='### T4.6 — Balance sheet';dash='### T4.10 — Source-supported dashboard';bridge='**Net income to EBITDA and EBITDA As Defined, reported (PDF 53):**'
# Exact selected source row meanings; no issuer bridge is re-based onto operating EBITDA.
input_rows={
'revenue':(inc,'NET SALES'),'cogs':(inc,'COST OF SALES'),'gross_profit':(inc,'GROSS PROFIT'),'selling_admin':(inc,'SELLING AND ADMINISTRATIVE EXPENSES'),'income_statement_amortization':(inc,'AMORTIZATION OF INTANGIBLE ASSETS'),'ebit_reported':(inc,'INCOME FROM OPERATIONS'),
'depreciation':(cf,'Depreciation'),'cf_amortization':(cf,'Amortization of intangible assets and product certification costs'),'cfo':(cf,'Net cash provided by operating activities'),'capex_signed':(cf,'Capital expenditures'),'cash':(cf,'Cash and cash equivalents, end of period'),'interest_cash':(cf,'Cash paid during period for interest, net'),'tax_cash':(cf,'Cash paid during period for income taxes, net of refunds'),
'issuer_ordinary_ebitda':(bridge,'EBITDA'),'issuer_as_defined':(dash,'EBITDA As Defined, total company')}
periods=['FY2022','FY2023','FY2024'];cells={p:{} for p in periods};formulas={}
for p in periods:
 c=cells[p]
 for key,(anchor,label) in input_rows.items():c[key]=read('annual',anchor,label,p)
 with localcontext(CONTEXT):
  c['opex_magnitude']=calc(((c['selling_admin'],1),(c['income_statement_amortization'],1)))
  c['ebit']=calc(((c['gross_profit'],1),(c['opex_magnitude'],-1)))
  c['cash_flow_DA']=calc(((c['depreciation'],1),(c['cf_amortization'],1)))
  c['operating_ebitda']=calc(((c['ebit'],1),(c['cash_flow_DA'],1)))
  c['cfo_less_capex']=calc(((c['cfo'],1),(c['capex_signed'],1)))
  debt_parts=[read('annual',bs,label,'Sep 30, '+p[-4:]) for label in ('Long-term debt','Current portion of long-term debt','Short-term borrowings—trade receivable securitization facility')]
  c['carrying_debt']=calc((part,1) for part in debt_parts)
  c['net_carrying_debt']=calc(((c['carrying_debt'],1),(c['cash'],-1)))
  adjustments=[read('annual',bridge,label,p) for label in ('Acquisition transaction and integration-related expenses','Non-cash stock and deferred compensation expense','Refinancing costs','Other, net')]
  c['issuer_bridge_check']=calc(((c['issuer_ordinary_ebitda'],1),*((v,1) for v in adjustments)))
  c['operating_vs_issuer_basis']=calc(((c['operating_ebitda'],1),(c['issuer_ordinary_ebitda'],-1)))
  for key,num,den in [('gross_carrying_multiple','carrying_debt','issuer_as_defined'),('net_carrying_multiple','net_carrying_debt','issuer_as_defined'),('issuer_earnings_cash_interest','issuer_as_defined','interest_cash')]:c[key]=_ratio(((c[num],1),),((c[den],1),));formulas[key]=f'{num} / {den}'
 assert c['ebit'].value==c['ebit_reported'].value
 if c['issuer_bridge_check'].value is not None:assert c['issuer_bridge_check'].value==c['issuer_as_defined'].value
formulas.update({'opex_magnitude':'selling_admin + income_statement_amortization','ebit':'gross_profit - opex_magnitude','cash_flow_DA':'depreciation + cf_amortization','operating_ebitda':'ebit + cash_flow_DA','cfo_less_capex':'cfo + capex_signed','carrying_debt':'BS long-term debt + current portion + separate securitization','net_carrying_debt':'carrying_debt - cash','issuer_bridge_check':'issuer ordinary EBITDA + acquisition/integration + stock/deferred compensation + refinancing + other net','operating_vs_issuer_basis':'operating_ebitda - issuer_ordinary_ebitda'})
labels={'opex_magnitude':'OPEX below gross profit — S&A plus IS intangible amortization','operating_ebitda':'Operating EBIT plus cash-flow D&A — distinct basis','issuer_ordinary_ebitda':'Issuer ordinary EBITDA — retained reported bridge','issuer_as_defined':'Issuer EBITDA As Defined — management measure','issuer_bridge_check':'Independent sum of issuer ordinary base and its own adjustments','operating_vs_issuer_basis':'Operating-based less issuer ordinary EBITDA — definition difference','cfo_less_capex':'Reported CFO less gross cash capex — cash proxy only','carrying_debt':'BS carrying borrowing categories plus separate securitization','net_carrying_debt':'Mechanical carrying debt less reported cash — access unverified','cash_flow_DA':'Cash-flow depreciation plus intangible/product-certification amortization','gross_carrying_multiple':'Carrying borrowing / issuer EBITDA As Defined','net_carrying_multiple':'Mechanical net carrying borrowing / issuer EBITDA As Defined','issuer_earnings_cash_interest':'Issuer EBITDA As Defined / reported cash interest'}
# A numeric publication register; source text and separate raw tables stay unchanged.
for tid,keys,block,unit_class in [('history',tuple(k for k in cells[periods[0]] if not k.endswith(('multiple','cash_interest'))),'financials-credit-metrics','amount'),('ratios',('gross_carrying_multiple','net_carrying_multiple','issuer_earnings_cash_interest'),'company-profile','multiple')]:
 layouts=[]
 for key in keys:
  ids=[]
  for p in periods:
   cell=cells[p][key];fid=f'{tid}.{key}.{p}';ids.append(fid);known=cell.value is not None
   quotes=tuple(dict.fromkeys(citations[(s.source_id,s.source_locator)] for s in cell.sources))
   facts.append(Fact(fact_id=fid,label=labels.get(key,key.replace('_',' ').title()),table_id=tid,row_id=key,field=p,amount=cell.value,status='known' if known else 'missing',unit='MILLIONS' if unit_class=='amount' else 'MULTIPLE',scale=Decimal(1000000) if unit_class=='amount' else Decimal(1),currency='USD' if unit_class=='amount' else None,period=p,basis='Historical retained-handoff publication. '+('Existing Decimal helper: '+formulas[key] if key in formulas else 'Reported source value; see exact handoff citation.'),value_class='calculated' if key in formulas else 'source',formula=formulas.get(key),calculation_id=f'model.{key}.{p}' if key in formulas else None,citations=quotes,limitation=cell.note if known else (cell.note or cell.reason or 'Missing source input'),decimals=0 if unit_class=='amount' else 2))
  layouts.append(TableRow(row_id=key,label=labels.get(key,key.replace('_',' ').title()),fact_ids=tuple(ids)))
 tables.append(ReportTable(table_id=tid,title='Annual source and computation register' if tid=='history' else 'Defined historical ratios — not covenant/agency measures',columns=tuple(TableColumn(field=p,label=p) for p in periods),rows=tuple(layouts),row_header='Measure'))
 bindings.append(Binding(fact_coord=FactCoord(module_id='CP-MODEL',table_id=tid),block_id=block,cell_slot=tid,unit_class=unit_class,label=tid))
scope=('Manual Model publication from actual checked Markdown handoffs. Historical annual FY2022–FY2024, exact quarterly handoff dates/units and conditional FY2025–FY2027 assumptions remain separate. Source tables are copied literally; all raw financial, segment, add-back, facility, quarterly, scenario and gap tables are on the Model page. Operating-based EBITDA is distinct from the issuer ordinary/As Defined bridge; cash proxy is not discretionary FCF, book debt is not all claims and cash is not certified accessible liquidity. No new underwriting, Excel output, provider run or promoted journal head. Charts show selected historical data only; the complete conditional source tables and unchanged exact forecast JSON remain attached. Native CP-OS automation is unqualified.')
calculation={'schema_version':'retained-handoff-model/1','mode':manifest['execution'],'inputs':manifest['inputs'],'excel_output':False,'scope':scope,'annual_periods':periods,'formulas':formulas,'values':{p:{k:{'amount':str(c.value) if c.value is not None else None,'reason':c.reason,'note':c.note,'sources':[{'source_id':r.source_id,'locator':r.source_locator,'cell_text':r.cell_text} for r in c.sources]} for k,c in row.items()} for p,row in cells.items()},'forecast_exact_file':'forecast_exact.json','forecast_exact_sha256':manifest['inputs']['forecast_exact']['sha256']}
calcraw=(json.dumps(calculation,indent=2)+'\n').encode();sha=hashlib.sha256(calcraw).hexdigest()
mod=ModuleView(module_id='CP-MODEL',title='TDG historical Model and conditional source tables',aliases=(),status='candidate',artifact_sha256=sha,facts=tuple(facts),tables=tuple(tables),limitations=(scope,))
run=Run(run_id='tdg-model-001',issuer_id='TDG',issuer_name='TransDigm Group Incorporated',as_of=date(2024,9,30),case_kind='public',requested_modules=('CP-MODEL',))
view=View(run=run,mode='candidate',modules=(mod,),sources=tuple(sources),analytical_qualification='partial',native_host_qualification='unrun')
pathway=next(p for p in pathways() if p.id=='credit_snapshot').model_copy(update={'title':'TDG Model — historical and conditional inputs','question':'What do the retained financial handoffs and explicitly defined calculations show?','requested_modules':('CP-MODEL',),'blocks':('financials-credit-metrics','company-profile')})
report=build(view,pathway,(BindingMap(module_id='CP-MODEL',entries=tuple(bindings)),))
refs={(item.coord.module_id,item.coord.fact_id):item.ref_ids for item in report.index.facts}
figures=[]
for figid,title,series in [('M1','Operating and issuer earnings bases',(('Operating EBIT plus D&A','operating_ebitda'),('Issuer ordinary EBITDA','issuer_ordinary_ebitda'),('Issuer As Defined','issuer_as_defined'))),('M2','Reported operating cash and capex proxy',(('Reported CFO','cfo'),('CFO less gross cash capex','cfo_less_capex'))),('M3','OPEX below gross profit',(('S&A plus IS amortization','opex_magnitude'),))]:
 figures.append(_figure_of_points('financials-credit-metrics',mod,refs,fig_id=figid,title=title,kind='line',unit_class='amount',unit='USDm',series=tuple(s[0] for s in series),points=tuple(_ChartPoint(name,p,f'history.{key}.{p}') for name,key in series for p in periods),placement='above',summary='Historical annual scope; issuer/operating definitions and missing observations stay distinct.'))
blocks=tuple(b.model_copy(update={'owner':'CP-MODEL','title':'Annual financial Model' if b.block_id=='financials-credit-metrics' else 'Defined historical ratios','full_analysis_route':'CP-MODEL','width':'full','figures':tuple(figures) if b.block_id=='financials-credit-metrics' else (), 'state':'populated'}) for b in report.blocks)
report=ReportView.model_validate_json(report.model_copy(update={'blocks':blocks}).model_dump_json())
rendered=render(view,report);anchor='<div id="call-root"></div>';assert rendered.count(anchor)==1
rendered=rendered.replace(anchor,'<section id="delivery-scope-banner" class="banner" role="note">'+html.escape(scope)+'</section>'+anchor)
nav='["model", "Model", "#CP-1"]';assert rendered.count(nav)==1;rendered=rendered.replace(nav,'["model", "Model", "#CP-MODEL"]')
files={**copies,'calculation.json':calcraw,'view.json':view.model_dump_json(indent=2).encode(),'report-view.json':report.model_dump_json(indent=2).encode(),'model.html':rendered.encode()}
record={'kind':'manual_retained_handoff_model_publication','scope':scope,'analytical_rerun':False,'excel_output':False,'native_accepted_head':False,'sources':manifest['inputs'],'files':{n:hashlib.sha256(raw).hexdigest() for n,raw in files.items()},'raw_source_tables':len(source_tables),'facts':len(facts),'figures':3,'input_contract':'Current six-heading handoffs; selected historical monetary calculations only, all raw tables literal.'}
dest=root/'deliverables/tdg-model-1';dest.mkdir(exist_ok=False)
for name,raw in files.items():(dest/name).write_bytes(raw)
(dest/'delivery.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'destination':str(dest),'facts':len(facts),'raw_tables':len(source_tables),'charts':len(figures),'calculation_sha256':sha,'model_sha256':record['files']['model.html']},indent=2))
