# Final Workflow

A local workflow joining the Deploy V-derived analytical methods, including
applicable later corrections and additions, to Deploy Workflow's existing deliverables:

**Issuer source files → CP-OS runs analytical modules → Markdown handoffs →
separate delivery process → Deploy Workflow reports, HTML Model, charts and calculation JSON.**

Excel files are supported as analytical inputs only. Deliverables do not include Excel workbooks.

The [remaining-module campaign record](runs/cpos-sol-remaining-20261105/verification.json)
records sequential sol-medium responses, source/instruction reviews, targeted
repairs and actual downstream consumption. Positive functional cases use TDG,
ARCC, LQD, Ford Otosan, Enel, Moog/Wencor, CRC, LMI and Frontier with each
issuer and evidence date kept separate. These are bounded historical proofs,
not current underwriting or universal native-contract acceptance.

The corrected [TDG annual report and Model](runs/cpos-sol-remaining-20261105/recovery/execution/deliveries/96c0def4111ccdccdba03f67829817a9d180bd1b6d23ca5bd36dd88fdb0d1dee/report.html)
use the retained source intake and seven sequential sol-medium modules. The
annual report places the November 2027 notes in fiscal 2028; the reported fiscal
2027 repayment bucket remains 92. The publication has 12 populated panels, charts
and calculation JSON. The [live CP-8 comparison](runs/cpos-sol-remaining-20261105/comparison/execution/deliveries/0656748d344c9ae4a504157fd5681143daddfd978462f95e20a35a5278302f29/report.html)
compares both complete bundles across seven dimensions. Both runs resume from
verified artifacts without another provider call.

Five broader report designs reuse checked handoffs through the existing delivery
process. The December committee response includes a source-checked host erratum
that preserves its original scope and judgment:

| Pathway | Populated panels | Evidence boundary |
|---|---:|---|
| [Earnings update](runs/cpos-sol-remaining-20261105/recovery/pathways/earnings_update/published/report.html) | 14 | TDG December 2024 quarter, separate annual Model and dated guidance |
| [Relative value](runs/cpos-sol-remaining-20261105/pathways/relative_value/published/report.html) | 10 | ARCC December 2024 same-issuer bond comparison; conditional price basis |
| [Portfolio decision](runs/cpos-sol-remaining-20261105/pathways/portfolio_decision/published/report.html) | 8 | LQD May 2025 holdings; Requires More Work, with missing mandate inputs |
| [Covenant/refinancing](runs/cpos-sol-remaining-20261105/recovery/pathways/covenant_refinancing/published/report.html) | 11 | TDG executed 2033 indenture; conditional capacity and liquidity |
| [Distressed/restructuring](runs/cpos-sol-remaining-20261105/recovery/pathways/distressed_restructuring/published/report.html) | 15 | TDG conditional downside; actual distress and quantified recovery not established |

Offline reproduction of the annual and comparison proofs uses `recovery/verify.py`
and `comparison/verify.py` in the campaign directory. The campaign record links
the five verified broader bundles and records the source checks and settled costs.
The literal adapter copies explicit committee action biases as well as portfolio
postures, and keeps Model identity unchanged when sharing its facts with report
charts. It does not generate replacement analysis or infer missing decisions.

The [historical Erste source-intake report](deliverables/erste-source-intake-1/report.html)
now exercises that boundary on real issuer spreadsheets: checked preparation,
actual CP-1 consumption and HTML publication, with conflicting source values
preserved and restricted. This does not certify arbitrary workbook layouts or
complete bank underwriting.

CP-OS now drives the adapted cp-os live execution loop through the existing
dependency planner and Markdown delivery adapter. The fresh sol-medium
[TDG annual report and Model](runs/cpos-sol-medium-20261105/deliveries/ff9a58944ddfb17f1876151a30020200a622d0d7238d3a79eb1ddba1d7e050fa/report.html)
uses new CP-0, CP-1, CP-1A and CP-2 responses from pinned issuer files, following
separate module proofs. Five populated narrative sections, the HTML Model,
three charts and calculation JSON pass existing delivery and independent
numerical checks. Resume makes no provider calls. A campaign checker falsely
rejected CP-2's recipient punctuation; its reviewed retained response was
recovered after fixing that checker, without repeating analysis.
The [single campaign record](runs/cpos-sol-medium-20261105/verification.json)
retains that intervention, actual calls, cost and scope. Reproduce offline with
`PYTHONPATH=src .venv/bin/python runs/cpos-sol-medium-20261105/verify.py`.
This proves the selected historical annual pathway; complete current underwriting
and fresh execution across broader pathways remain open. The
[whole-system review](METHODOLOGY-REVIEW.md) remains the historical baseline.

CP-OS now also delivers the complete eight-section
[Portfolio Decision report](runs/cpos-lqd-portfolio-001/execution/deliveries/827427820e0e5f1d647ef2323182d9a59eb88edb97a4773b838b01e2ed14e5c4/report.html)
from the actual historical LQD portfolio, repaired debate and final assurance
handoffs. Its header copies the cited **Requires More Work** posture; the exact
constraint and proposed size remain unknown. This is checked retained replay,
with full source content, not current investment approval or a fresh model run.
Reproduce with `PYTHONPATH=src .venv/bin/python runs/cpos-lqd-portfolio-001/verify.py`.

CP-OS also publishes the complete ten-section
[historical ARCC Relative Value report](runs/cpos-arcc-rv-001/execution/deliveries/70f990d9ed622edfffbd91f9b82ebf54fc3a358a100bc8ed40a3054cd09a7142/report.html)
from retained CP-3D, CP-3A and CP-6 handoffs. The existing instrument table and
yield chart preserve both conditional clean/dirty cases and their exact source
references. This proves publication replay, not executable prices or a fresh
analytical run. The [case record](runs/cpos-arcc-rv-001/verification.json) states
the original-answer format amendment and remaining limits.

The [historical Ford funding report](runs/cpos-ford-funding-2024-001/execution/deliveries/526e1b1a46636703a009b9652e982f87df45f147643b2bd082285353a8e5bf58/report.html)
now connects CP-2H's actual handoff to CP-3C and CP-OS delivery. Six conditional
funding cases retain their source units, dates, signs and access assumptions.
This is checked retained-answer replay, not a fresh model run or complete
refinancing/LME assessment. Excel remains ingestion-only.

CP-OS is intended to be the active orchestrator for this version. Its responsibilities
are to launch modules in dependency order, pass their current handoffs, track progress,
handle bounded retries and resume, and invoke delivery. Its role extends through checking that
the requested deliverables exist and contain the handoff content. The M365
navigation-only behavior is not a restriction on this implementation.

[The methodology comparison](METHODOLOGY-REVIEW.md) distinguishes later improvements
from narrower implementations. The M365 experience is the interaction reference;
its older method revision is not copied wholesale. Simplifying execution must
preserve the analytical substance of the requested workflow.

The Markdown files carry analysis between modules and into the delivery process.
They are intermediate artifacts. The delivery process reads them, adapts their
content to the existing generators and constructs the requested final outputs,
preserving figures, source references and limitations. It does not repeat the
analytical workflow or manufacture missing findings.

CP-MEMO is replaced by these actual deliverables. Completion is checked against
the requested populated outputs and their source handoffs, without a separate
CP-MEMO analytical run.

CP-OS also has an explicit paid handoff entry point, `run_live_handoffs` in
`src/deploy_workflow/owners/cpos.py`. It reuses cp-os revision `b57a344`'s source
tools and bounded write/edit loop through final-workflow's existing provider
adapter, durable budget and retained call log. The existing planner, handoff
checks and delivery process remain in charge. No second orchestration layer or
analytical rerun for publication is introduced.

Live manifests select `execution: live-provider`, a positive `provider_cap_usd`
and `max_attempts: 1`; each module may repair up to three submitted drafts within
the bounded live loop. The caller supplies the evidence/instruction checker and
a live ruling, and launches with `OPENAI_API_KEY`. Unknown charges stop execution.
Import, build, retained replay and ordinary delivery make no provider calls.
The [sequential sol-medium campaign](runs/cpos-sol-medium-20261105/verification.json)
retains actual requests, responses, source checks, repairs and consumption proof.

## Start a run from a context file and issuer folder

Select the issuer files, the context file and the model. Without `--live` this only
prepares the run: it reads every file, writes the pinned manifest and module
instructions, prints the plan and makes no provider call.

```bash
PYTHONPATH=src .venv/bin/python -m deploy_workflow.owners.cpos_launch \
  --context path/to/context.json \
  --sources path/to/issuer-folder \
  --config sol-medium \
  --cap 25
```

Add `--live --ruling docs/rulings/<file>.md` to start the paid run; the ruling must
name the selected config, and the provider key must be in the launching environment.
CP-OS then runs the modules in order and publishes `deliveries/<id>/report.html`.

- **Context file:** a `context/1` file, such as one from
  [the context form](docs/templates/context-form.html). It sets the issuer, as-of date,
  case kind and pathway, and every module can read it as the source `context`.
- **Issuer folder:** read recursively. PDF, TXT, Markdown, XLSX, CSV, JSON and JSONL files
  are pinned as they are; HTML filings are pinned as their visible text in cp-os's
  3,000-character pages, headed by the filed document's name and hash. Other files and `_`-prefixed folders are listed as
  ignored, dotfiles are skipped, and an unreadable file stops the launch.
- **Model:** `--config` is `sol-medium`, `sol-high`, `opus-medium` or `deepseek-max`.
- **Cap:** a USD ceiling per run folder. Each call holds up to its worst-case price
  against the cap until it settles (USD 5.73 for `gpt-6.1-sol`), and a cap too small
  for one call of the largest module is refused before anything is sent.
- **Modules:** the pathway's preset by default. `--modules` narrows it, keeping
  dependencies, and must fill at least one report section.
- **Run folder:** `--out`, or `runs/<run id>`. A changed request, including a new file
  in the issuer folder or a new cap, needs a new folder. Relaunching the same request
  rechecks finished modules without resending them.

**Current limits:**

- The automated checks cover handoff structure, issuer/date/source/upstream anchors
  and report selectors. They hold no independent expected values, so a passing run has
  not had analytical review, and each report says so in its scope.
- It publishes the report only. The HTML Model, charts and calculation JSON need
  issuer-specific row selectors, which remain hand-written manifest work, as does CP-8.
- A module interrupted mid-call, or stopped by the cap, is never resent because its
  charge may be unknown. Finishing that request means a new run folder, which repeats
  and pays for the earlier modules.

- Reads stop once a module's context reaches about 700,000 bytes. The module is told to
  use what it has and record the rest as a gap, so a run over very large filings may not
  read all of them.

One paid test covers this path with historical TDG FY2024 files: CP-0, CP-1 and CP-1A
on `sol-medium`, retained in `runs/cpos-launch-live-002`. An ordinary test run skips it.
A rerun rechecks the retained answers and sends nothing. It passed at USD 0.93, and
[VERIFICATION.md](VERIFICATION.md) records the review of its answers against the filing.
The first attempt, [`runs/cpos-launch-live-001`](runs/cpos-launch-live-001), stopped
during CP-0 after USD 0.29; its reads of whole filings led to the read limit above.

```bash
CPOS_LIVE_RULING=docs/rulings/<file>.md PYTHONPATH=src:. .venv/bin/python -m pytest tests/test_cpos_launch.py -m live -q
```

## Development loop

Develop one bounded module result and its next handoff at a time:

1. **Fix the input.** Name the issuer files, requested scope, selected method
   revision and instructions. Retain the exact instruction file and source hashes.
2. **Run the model and retain its answer.** Keep the actual Markdown output and
   evidence used. State whether execution was a host session, provider call,
   retained-response replay or synthetic test. These prove different things.
3. **Check the answer.** Compare it with the instructions and issuer evidence.
   Check exact amounts, units, periods, source references, missingness and any
   calculations. Use expectations independent of production calculations.
4. **Repair only an observed failure.** Identify whether it is in the instructions,
   model answer, source access, calculation or handoff. Preserve the failed answer,
   make the smallest justified change and repeat the affected check.
5. **Consume the handoff.** The next module must open it and use its content,
   carrying limitations forward. A generated file alone does not pass this step.

Use the same six Markdown headings: Request, Sources, Findings, Calculations,
Gaps, Next module. Preserve module-specific analysis within them; the headings
are a common envelope, not a replacement for the methodology. A failed targeted
check triggers a targeted repair, not another repository or full rebuild.

For an exact alias, reuse the canonical analytical answer and verify that the
alias selects the same method and that the answer meets its obligations. If an
alias carries additional analytical scope, execute and check that scope. A name
in the registry proves neither case; repeating identical analysis is unnecessary.

Functional proof may use another issuer or an older file when access is missing.
Label the issuer/date and retain real evidence; do not mix the case into TDG or
claim current underwriting. The [historical Ford Otosan ratings case](runs/ford-otosan-2024-001/CP-2H-attempt-2.md)
uses real S&P/Fitch reports and an [actual refinancing consumer](runs/ford-otosan-2024-001/CP-3C-consumer.md).
It demonstrates bounded analysis and communication while broader runtime and
issuer-specific gaps remain explicit.
Its [evidence review](runs/ford-otosan-2024-001/CP-5-attempt-1.md) is actually
consumed by the [restricted historical committee debate](runs/ford-otosan-2024-001/CP-6-attempt-1.md).
The [TDG event-calendar increment](runs/tdg-003/CP-2A-calendar-attempt-1.md)
separately exercises CP-2B's additional duties, with an
[actual liquidity consumer](runs/tdg-003/CP-2D-calendar-consumer.md).
An [executed-notes interpretation](runs/tdg-004/CP-4-attempt-2.md) now feeds an
[actual legal-to-funding consumer](runs/tdg-004/CP-3C-legal-consumer.md). It
preserves document boundaries, legal definitions and conditional cash amounts.
The separate [LMI structural map](runs/lmi-2014-001/CP-4B-attempt-2.md) feeds an
[intercreditor-control assessment](runs/lmi-2014-001/CP-4D-attempt-1.md).
The [ARCC quantitative coverage case](runs/arcc-2024-001/CP-4A-attempt-1.md)
uses real published financial and executed legal inputs, and its
[actual capacity challenge](runs/arcc-2024-001/CP-6-capacity-consumer.md) preserves
the difference between a positive ratio cushion and usable financing.
The [Frontier numerical restructuring case](runs/frontier-2020-001/CP-4C-attempt-1.md)
reuses the existing waterfall helper on real dated scenario inputs and feeds an
[actual recovery comparison](runs/frontier-2020-001/CP-3-recovery-consumer.md).
Modeled recoveries, final outcomes and price-based preference remain distinct.

Keep instructions in `prompts/`, actual run artifacts in `runs/<run>/`, and one
concise running record in [VERIFICATION.md](VERIFICATION.md). That record states
the scope tested, result, remaining limitation and next small win. A changed
instruction gets a new retained revision; earlier run inputs/outputs remain intact.

Extend CP-OS to further pathways after the relevant module links work. Reuse the
proven instructions, handoffs and existing execution code. Final
completion still requires populated deliverables constructed from those handoffs
and checked against them.

The first [CP-OS-driven report](runs/cpos-tdg-snapshot-001/execution/deliveries/db57f31adc5539190599e8e5068770f7ed65edc42f1bec9e51ee9d8b11e02005/report.html)
replays actual checked annual TDG answers. Reproduce or resume it with:

```sh
PYTHONPATH=src .venv/bin/python -m deploy_workflow.owners.cpos \
  --manifest runs/cpos-tdg-snapshot-001/workflow.json \
  --state runs/cpos-tdg-snapshot-001/execution \
  --replay-responses runs/cpos-tdg-snapshot-001/responses.json
```

`run_handoffs` passes frozen instructions, source bytes, current earlier Markdown
and targeted feedback to the executor. The checker must return actual issues;
headings alone cannot approve analysis. Responses are retained before checks,
repairs are bounded and changed inputs invalidate affected requests. An interrupted
dispatch with no retained response requires that response before resume. Report
writes are staged and verified; changed renderer bytes create a new publication.
The replay command checks retained-byte parity, not fresh analytical accuracy.
This first snapshot publishes five narrative sections; its own Model/chart scope
remains unrun. The later publication below adds those outputs. No Excel output.

The [CP-OS report with Model delivery](runs/cpos-tdg-model-001/execution/deliveries/de1be08fb3a040d4e4f916cce017b1541b8eaaa8235b6fb50b7c4afb916a2bfc/report.html)
links to the populated HTML Model, three charts and calculation JSON. Reproduce
or resume the retained-handoff publication with:

```sh
PYTHONPATH=src .venv/bin/python -m deploy_workflow.owners.cpos \
  --manifest runs/cpos-tdg-model-001/workflow.json \
  --state runs/cpos-tdg-model-001/execution
```

All four analytical answers are already pinned in the manifest, so no duplicate
response map is needed. Explicit row selectors and source-checked fiscal dates
adapt the selected annual USD-million layout to the existing calculation/rendering
code. Other currencies/layouts remain outside this adapter's verified scope.
Additional quarter and conditional-forecast tables are preserved literally;
their presence does not constitute complete current underwriting. The
[verification record](runs/cpos-tdg-model-001/verification.json) covers 81 numeric
cells, 51 raw tables, 46 preserved blanks, chart/table agreement and publication
resume/refusal checks. Excel remains ingestion-only.

CP-8 now uses CP-OS's existing exchange to compare completed prior/current
deliveries and publish a [checked comparison report](runs/cpos-tdg-comparison-001/execution/deliveries/04082614b4fa418445e0d483a3b12e81855decb2ec0b8fd5cfb263c9b47fe20f/report.html).
It checks values, periods, assumptions, conclusions, sources, limitations and
output scope. The actual retained host answer compares23 pinned input files;
this pair adds Model delivery while preserving all five narrative sections.
Investment-decision history is not an input gate. The imported native
decision-ledger owner is not used by this route.

The [historical TDG earnings report](runs/cpos-tdg-earnings-001/execution/deliveries/25d29570b506ce5c1536ad3a0b564387598b0f1deed58e702d55e3787238b10f/report.html)
connects the actual retained CP-0 → CP-1 → CP-1B handoffs to five selected sections
of the existing earnings design. It preserves all handoffs and source-line links,
89/91-day fiscal windows, signed cash flows and explicit missing guidance. This
proves replay publication of that bounded case, not a fresh model run, native
acceptance or the full earnings pathway. Excel remains input-only. Resume with:

```sh
PYTHONPATH=src .venv/bin/python -m deploy_workflow.owners.cpos \
  --manifest runs/cpos-tdg-earnings-001/workflow.json \
  --state runs/cpos-tdg-earnings-001/execution
```

The [case verification](runs/cpos-tdg-earnings-001/verification.json) records the
actual scope, independent comparisons, browser/source checks and remaining limits.

The [quality/debt extension](runs/cpos-tdg-quality-001/execution/deliveries/c93479b08736770845f403c97825fc55c86c2e1ea58a39ca876056c7a13e849b/report.html)
adds three earnings sections from the retained CP-1D/CP-1E answer. All thirteen
registers match the handoff; annual and quarterly bases stay separate, quality
earnings remain unresolved, and 24,961 remains a known-item debt subtotal.
The [workflow](runs/cpos-tdg-quality-001/workflow.json) actually requests CP-1E and
dispatches once to CP-1D. Existing code performs the publication; this is replay
verification with no new model/provider call or Excel output.

The [assured earnings report](runs/cpos-tdg-assurance-001/execution/deliveries/d7e9aed9c0da5d2bc7b91f839456c0a0e449a6f200e82d36d5ba335f5351da66/report.html)
adds an actual host-model CP-5/CP-5A review under Evidence/CP-5. It traces twenty
selected assertions and preserves two inherited Material limitations. A targeted
repair changes computed debt's lineage to Calculated; financial values and all
eight analytical sections remain unchanged. This is restricted historical use,
with no provider or independent-context qualification. The
[verification record](runs/cpos-tdg-assurance-001/verification.json) distinguishes
the two host answers, four reused upstreams, controls and publication checks.
Explicit replay, with no new model analysis:

```sh
PYTHONPATH=src .venv/bin/python -m deploy_workflow.owners.cpos \
  --manifest runs/cpos-tdg-assurance-001/workflow-replay.json \
  --state /tmp/final-workflow-cp5-assurance-replay-001
```

The [historical Ford Otosan ratings report](runs/cpos-ford-ratings-2024-001/execution/deliveries/8840802b892e729314078d335ecd5a0965d67e9ad32f5b34468daae73a321f56/report.html)
publishes all ten CP-2H registers from four checked handoffs. CP-OS follows the
inputs pinned by each reused answer; a published agency forecast does not cause
an unused stress model to be rebuilt. Fresh work retains its normal catalog
requirements. Source/upstream hashes and analytical review are still mandatory.
The report preserves April 2024 preliminary/expected ratings, approximate/proxy
limits and unavailable true headroom; it does not classify the company as
distressed or give a current rating. [Verification](runs/cpos-ford-ratings-2024-001/verification.json).

```sh
PYTHONPATH=src .venv/bin/python -m deploy_workflow.owners.cpos \
  --manifest runs/cpos-ford-ratings-2024-001/workflow.json \
  --state runs/cpos-ford-ratings-2024-001/execution
```

The local host API is `cpos.run_comparison`, with the same executor/checker
contract as `run_handoffs`. Explicit retained-answer replay is also available:

```sh
PYTHONPATH=src .venv/bin/python -m deploy_workflow.owners.cpos --compare \
  --manifest runs/cpos-tdg-comparison-001/workflow-replay.json \
  --state runs/cpos-tdg-comparison-001/replay \
  --replay-responses runs/cpos-tdg-comparison-001/responses.json
```

Replay is labelled separately from the original host exchange. Complete
bundle/file/issuer bindings, bounded repairs and verified publication are
required; source or output changes are not silently accepted. Broader pathway
qualification remains open.

The [fresh host CP-2 report](runs/cpos-tdg-host-001/execution/deliveries/17e1d418be894f6aeff979f100e87460fc3f9d80ed4f22cb7114e4b1c5c8627d/report.html)
demonstrates the actual host exchange: CP-OS retains the request, the current host
answers it, the answer is checked, and separate delivery consumes it. CP-0, CP-1
and CP-1A are reused without new executor calls. `retained_handoffs` in the
[workflow](runs/cpos-tdg-host-001/workflow.json) pins each answer, source hashes
and the exact upstream handoffs it was checked against. Changed context refuses
reuse; a rejected retained answer requires a corrected/reviewed input. Completion
records each module's origin separately, including when identical publication
bytes arise from different execution histories. This proves one fresh CP-2 host
response with preceding context, not independent/provider/native qualification.

First bounded result: [TDG CP-0 handoff](runs/tdg-001/CP-0.md) and
[CP-1 intake sample](runs/tdg-001/CP-1-intake.md). These establish a same-session
source-readiness and handoff check, not full CP-1 or runtime acceptance.

The next loop produced a [checked CP-1 annual handoff](runs/tdg-002/CP-1-attempt-2.md),
with source tables, financial interpretation and exact reconciliation transcripts.
A fresh CP-1A model consumed its financial facts. Its
[business and governance handoff](runs/tdg-002/CP-1A-attempt-3.md) passed a bounded
historical source check after targeted repairs. A fresh CP-2 model consumed it
and produced a [checked fundamental-credit synthesis](runs/tdg-002/CP-2-attempt-2.md).
A fresh CP-2A model then consumed that synthesis and produced a
[checked static downside screen](runs/tdg-002/CP-2A-attempt-1.md). Its output then informed a
[historical cash bridge and liquidity review](runs/tdg-002/CP-2D-attempt-1.md),
with unsupported forward liquidity kept explicit.
A later [quarterly CP-1 increment](runs/tdg-003/CP-1-attempt-2.md) supplies the
actual December financial statements. Its [earnings update](runs/tdg-003/CP-1B-attempt-1.md)
was checked and consumed by an [updated historical cash review](runs/tdg-003/CP-2D-attempt-1.md).
The [earnings-quality and adjusted-debt review](runs/tdg-003/CP-1D-attempt-1.md)
then tested the signed adjustments, recurring costs and broader CP-1E obligations;
[CP-2 consumed its findings](runs/tdg-003/CP-2-quality-update.md). Unresolved quality
earnings and unquantified claims remain explicit rather than becoming numbers.
The [macro/hedging and absorbed ESG review](runs/tdg-003/CP-2E-attempt-2.md)
checks dated protection and environmental obligations; [CP-2's actual update](runs/tdg-003/CP-2-macro-update.md)
uses them without converting reported sensitivities or missing exposures into
independently modelled results.
CP-OS now also routes an explicit CP-2F request into the
[complete17-register macro/ESG module page](runs/cpos-tdg-macro-esg-001/execution/deliveries/eb4d3551d6644d2baee1579c295300acc57fdc67a563731ff14aa4fb2f246c49/report.html#CP-2E).
A single malformed table delimiter was corrected in a new retained copy; every
analytical cell is unchanged. This is checked replay, with the existing debt/hedge
overview and full source-linked module/Evidence content, no Excel output.

The separate [historical Enel pricing report](runs/enel-sdg-2021-001/execution/deliveries/f6db8cb44acbb3bb57a5257c380e720fba884286e0a20f4c8bdea578bd2906e4/report.html)
adds a positive sustainability-linked coupon test: CP-OS retains actual host
CP-0/CP-2F answers, and a [targeted CP-3C reading](runs/enel-sdg-2021-001/CP-3C-consumer.md)
uses the conditional cash cost without double counting it. Final terms, actual
payments and broader underwriting remain unproven. The host has preflight
context; no provider, production-code change or workbook output was involved.

The [bounded guidance research](runs/tdg-guidance-001/CP-DR-attempt-1.md) supplies
dated management targets to the [conditional forward-model check](runs/tdg-003/CP-2G-attempt-2.md).
[CP-2's integrated update](runs/tdg-003/CP-2-integrated.md) actually consumes it,
keeping assumed cash drivers and missing liquidity/access distinct from proof.
CP-OS now also publishes the [nine-register conditional forecast report](runs/cpos-tdg-forecast-001/execution/deliveries/c9116c348257b3bb4b281d43aa8bef1d4c186de3e82a7b9a7171ef9f59b9c2ee/report.html)
from those actual handoffs. Its source dates, fiscal planning windows, assumptions,
first coverage watch and cash/access gaps remain explicit. This is retained
replay, with an issuer-heading amendment only; no financial reanalysis or Excel output.
The imported catalog has 25 entries and 16 aliases, with CP-MEMO replaced by
actual delivery. Routing checks alone do not count as analytical coverage.

The [ARCC historical market case](runs/arcc-market-2024-001/CP-3D-attempt-2.md)
adds actual evaluated observations and independently checked conditional bond
pricing/sensitivities, consumed by CP-3 intake. Price basis, coupon/issuer-hedge
rates and call assumptions remain distinct. It is not executable/current market
qualification or completed security selection; no new production code was needed.

The [historical ARCC Lite screening report](deliverables/arcc-fy2024-lite-1/report.html)
adds the actual combined CP-L10/20/23/30/40 answer and CP-5 recheck. It displays
five checked conclusions and all20 source-linked analytical tables. Independent
copy checks cover630 original cells and five front-page summaries. This is a
manual, historical screening deliverable with gaps and targeted upgrades; native
runtime breadth, full security selection and general CP-OS integration remain open.

The [updated populated five-section report](deliverables/tdg-fy2024-snapshot-7/report.html)
consumes the actual CP-1, CP-1A and integrated CP-2 Markdown handoffs through a narrow
adapter to the existing report design. Figures remain literal, citations identify
exact handoff lines, and missing Model publication and broader pathway work remain
visible. This is manual retained-handoff delivery, not automated runtime proof.
Reproduce into a new directory (existing destinations are refused):

```sh
PYTHONPATH=src .venv/bin/python -m deploy_workflow.handoff_delivery \
  --manifest runs/tdg-run-comparison-001/snapshot-inputs.json \
  --output deliverables/tdg-snapshot-new
```

The HTML is self-contained. `delivery.json` pins its inputs and output hashes.
The initial snapshot remains as the failed date-presentation attempt; attempt 2
is the earlier reviewed annual deliverable. Attempt 3 adds checked macro/ESG and
conditional forecast interpretation, with all assumptions and limits visible.
Attempt 6 adds the actual FY2024 peer comparison consumed by CP-2, including
sample sizes, definitions, unverified selection and exact differing fiscal dates.
Attempts 4–5 retain the initial gap-boundary repair and date-presentation increment.
Attempt7 applies the [actual CP-8 prior/current deliverable comparison](runs/tdg-run-comparison-001/CP-8.md),
consumed by CP-2: it restores historical maturity visibility, the retained
related-party/reporting gap and two inherited Critical evidence labels. All166
facts/citations pass; other values, confidence and scope remain intact. CP-8
compares run deliverables; the older investment-decision post-mortem is superseded.

The existing statistics helper and renderer were reused unchanged; a literal
delivery-input adaptation carries the new handoff content. A separate
[FY2025 valuation report](deliverables/tdg-fy2025-valuation-1/report.html) now adds
the actual two-class equity/known-components EV-proxy calculation and two
Provisional individual-peer applications, consumed by CP-2. Complete economic
EV, transaction comps and normalized/current valuation remain open. The
historical Model/charts publication below is separate from automated CP-OS proof.

The [historical CRC liquidity report](deliverables/crc-2020-liquidity-1/report.html)
adds the actual CP-2D forward cash/funding bridge and CP-3C consumption from a
July2020 discussion budget. It preserves financing conditions, source rounding,
the January maturity stub and explicit full-horizon/access/MTE gaps. One maturity
scope repair was checked against operative source terms and added to the actual
loaded prompt. This is checked host-model handoff delivery, with no Excel output;
full funding feasibility and native CP-OS completion remain open.

Python 3.13.15 and dependencies are pinned. Install with `uv sync --locked --offline`
when the packages are cached. Each project has its own `.venv`.

Original runtime imports, TDG keys and source-file hashes are recorded in
`docs/reuse/import.json`. Public TDG filings are retained in `data/public-corpus/v1/TDG`.
The preceding investigation remains in `REUSE-AUDIT.md` and `REUSE-PLAN-REVIEW.md`.

Work is in progress. Current bounded outcomes are in [VERIFICATION.md](VERIFICATION.md).
Runtime command documentation will follow verification of the integrated
implementation. No live success is implied by importing code or historical evidence.

The [populated historical Model](deliverables/tdg-model-3/model.html) now
publishes43 retained source tables, defined annual calculations and three charts,
with [calculation JSON](deliverables/tdg-model-3/calculation.json) and the original
exact conditional-forecast record. Independent checks cover81 numeric cells and
all1,779 raw table cells. CP-2 actually consumed it. This earlier publication was
assembled manually from checked handoffs; the CP-OS publication above now connects
the same method to orchestration. Broader/native qualification remains open. Operating-based,
issuer ordinary and As Defined EBITDA remain separate; missing observations and
original blanks do not become zeros.

