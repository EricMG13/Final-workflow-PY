# Verification record

Keep one running record here. A pass applies only to the stated scope. Preserve
earlier run artifacts; record a new attempt when instructions or outputs change.

The [current remaining-module record](runs/cpos-sol-remaining-20261105/verification.json)
contains the settled CP-6 timeout cost, the corrected TDG annual publication, the
live CP-8 comparison and checks of the five broader report bundles. The older
entries below retain their historical case scope.

## 2026-11-05 — The M365 custom instruction applies to every module

Owner ruling: the ported Copilot custom instruction is a global persona. `cpos_launch` now
emits it (`READER_PERSONA`) in every module's launcher instructions. The `CANON_SHARED.md`
reader rules and the `### Credit view` opening stay CP-2 only, and CP-2's emitted text is
byte-identical to before. Checks: `tests/test_cpos_launch.py` 79 passed, 1 skipped (paid);
the updated test failed first (`('CP-0', 'senior credit research analyst')`). Ruff and format
are clean; mypy reports nothing in `cpos_launch.py` (28 errors in other files). Not verified:
no paid run, so the persona's effect on non-CP-2 modules' live output is unmeasured.

Second ruling the same day: every module opens `## Findings` with its own `### … view`
paragraph. Evidence: M365 screenshots for VMO2 (CP-0 to CP-2A) and Wood Mackenzie (CP-0 to
CP-2A) open each analytical module with a plain-English view before any table; only CP-1C and
CP-2 call it "Credit view", CP-2A "Downside view". About half the screenshots were read (CP-3
onward unread). `OPENING` now maps all 20 `METHODS` modules (a test fails on a missing one) and
the checker enforces each; `READER_STANDARD` stays CP-2 only (`READER_STANDARD_MODULES`). CP-2's
instructions are byte-identical in all five pathways. CP-2's relative_value route `### Credit
view` is also its opening heading, as before. Checks: `test_cpos_launch.py`, `test_cpos_app.py`,
`test_cpos_handoffs.py` 137 passed, 1 skipped (paid); new tests failed first. Not verified: no
model has produced the new openings; earlier runs' retained handoffs no longer match the new
instructions, so a fresh run must regenerate them.

## 2026-11-05 — CP-2 writes for the credit reader

Web-app CP-2 handoffs read as audit records next to Deploy V's Microsoft 365 handoffs. Compared:
`deliverables/tdg-fy2024-snapshot-7/CP-2.md` (TDG) against M365 Deploy V screenshots in
`~/Documents/VMEDO2 Screenshots` (VMO2, 2026-09-20) and `~/Documents/Module Output` (Wood
Mackenzie, 2026-08-27). These are different issuers and dates, so the comparison is not
controlled. M365 carried as many limitations, but kept them in front matter and gap tables; its
prose opened with the view. M365 also had the user's Copilot custom instruction (a senior
credit-analyst persona), which no web-app prompt carried.

`cpos_launch` now gives CP-2 that custom instruction, the reader-facing rules of Deploy V
`CANON_SHARED.md` (sha256 `1ab484c5072a92944e1ed8b1591f96dfff2a021baf2cc230b8033eaa913a232d`)
and the `### Credit view` opening. The checker rejects a CP-2 handoff whose `## Findings` does
not open with that section in a paragraph (not a table, list, fence or comment). Other modules are
unchanged, and so is CP-2's owner route (`deploy_vii.cp2_synthesis`, Python-composed Markdown),
which produced `deliverables/tdg-fy2024-snapshot-7/CP-2.md`; only the launcher route changed.

Checks: `tests/test_cpos_launch.py` passes (73, live test deselected). The new tests failed
first. Ruff and format are clean on both changed files, and mypy reports nothing in
`cpos_launch.py`. `test_cpos_app.py` and `test_cpos_handoffs.py` pass. `test_owner_cpos.py`
errors in 42 tests at fixture setup (`publication refused: publication_refused`). That file does
not import `cpos_launch`, and an unmodified `ab46df7` checkout fails the same way, so the change
did not cause it; the cause has not been traced.

**Live test, `runs/cpos-launch-cp2-reader-001`, passed for this dated TDG case only.** At the
user's instruction "test first" ([ruling](docs/rulings/2026-11-05-cp2-reader-test.md)), CP-2 ran on
gpt-6.1-sol at medium effort over the accepted CP-0, CP-1 and CP-1A of `cpos-launch-live-002`. Those
three were pinned as retained and replayed without calls; live-002 was not written. CP-2 was
accepted on its first submission: 3 calls, USD 0.13628070, under a USD 8 cap. `run.py` in the folder
produced it. Its 4.4 MB copy of the TDG annual-report PDF (`inputs/dc6a8ea6…`) is left out of the
repository: `cpos-launch-live-002/inputs` keeps the identical file under the same SHA-256 name.

Against the earlier sol-medium TDG CP-2 (`cpos-sol-medium-20261105`, older instructions and
different upstream handoffs, so not a controlled comparison), with crude counts per 1,000 words
of Findings prose:

| Measure | Before | After |
| --- | ---: | ---: |
| `## Request` words | 116 | 43 |
| Findings opens with | bold assessment block, then a 827-word section | `### Credit view`, 117 words |
| Negations (not, no, never, cannot …) | 20.8 | 11.4 |
| Module codes in prose | 11.6 | 2.1 |
| Unitless thousands (e.g. "2,045") | 6.7 | 0.0 |
| Gap rows | 10 | 8 |

All 20 figures in the new opening and findings appear in the retained CP-1 handoff. These were
recomputed by hand: 2,045 − 165 = 1,880; 1,880 − 2,038 − 2,347 = −2,505; 25,068 / 4,173 = 6.01x;
25,068 / 3,813 = 6.57x; 7,267 − 4,348 = 2,919. The publication-cutoff, legal-capacity, earnings and
liquidity limitations remain in `## Gaps`. The drop from 10 to 8 gap rows cannot be attributed,
because the upstream handoffs differ.

The prose rules are instructions only: no check measures tone, word count or units. The web app
should show `### Credit view` first, since it shows sections in document order unless the
catalogue names a first heading; this was read from the code, not seen in a browser. Windows was
not checked.

## 2026-11-05 — repeated source copies removed

At the user's instruction, 20 repeated source copies of 1 MB or more (54.4 MB) were removed from
`execution/inputs` in `cpos-tdg-assurance-001`, `cpos-tdg-quality-001`, `cpos-tdg-comparison-001`,
`cpos-tdg-host-001`, `cpos-tdg-fresh-001` and `cpos-arcc-rv-001`. Each file's SHA-256 matches its name
and a copy kept under `data/public-corpus` or another retained run. Retained records cite them by
hash, not by path. Restore one with `git checkout c7a945d -- <path>`.

Checks at `c7a945d` without these files: 335 tests across 14 run-related test files pass, with the
one live test deselected. The Go tests, including `TestCurrentRetainedWorkspace`, pass. The design
fixture builds and its 59 tests pass. No README, VERIFICATION or METHODOLOGY-REVIEW link breaks.

Of the 17 verification scripts, 9 pass and 8 fail with the same final error on an unmodified
`c7a945d`, so the removal did not cause them:

- `cpos-sol-medium-20261105/verify.py`, `cpos-sol-remaining-20261105/pathways/verify.py` and
  `recovery/verify.py` stop with `delivery_changed: model.html`, and `comparison/verify.py` stops
  with an `AssertionError`. All four passed at `cadb55c`, before PR 2 merged. On `c7a945d`,
  `comparison/verify.py` also writes 7 new files into the retained run, so run it only in a
  disposable checkout until this is fixed. The cause has not been traced.
- `cpos-lqd-portfolio-001/verify.py`, `enel-final-terms-research-001/verify.py` and
  `enel-sdg-2021-001/verify.py` stop with `identity_mismatch`, and `fresh-tdg/verify.py` stops with an
  `AssertionError`. All four also failed at `cadb55c`.

These scripts ran from a temporary path, so the location may be a factor in the failures.

Not verified: the full suite on this change; re-executing the six affected runs from their retained
folders; Windows. Blobs stay in history, so GitHub storage does not shrink.

## 2026-11-05 — user-launched CP-OS runs

`python -m deploy_workflow.owners.cpos_launch` starts a run from a context file, an issuer
folder and a model config. Without `--live` it prepares only. The loop now sends the selected
config's model and effort, and records them; both were hardcoded to sol-medium.

**Offline scope, fake provider, wiring only:** every pathway preset reaches a verified report
from synthetic handoffs; the four configs reach the real provider body builder. Prepared offline
over the real TDG folder: 3.7 MB of 10-K HTML becomes 490 KB of visible text in 181 pages of at
most 3,000 characters, matching cp-os's page size.

**Live attempt 1, `runs/cpos-launch-live-001`, stopped; no handoff was produced.** Three sol-medium
calls, USD 0.28956660. CP-0 read four filings almost whole in parallel, and the next request's
bound (1,124,866) passed the 1,050,000 the budget hold allows, so it was refused before sending.
Repaired with a read limit at 700,000 bytes and instructions to search first;
`test_whole_filing_reads_stop_before_the_request_outgrows_the_budget_bound` reproduced the failure.
The attempt is retained unchanged. Its 12,000-character pages were then cut to cp-os's 3,000.

**Live retry, `runs/cpos-launch-live-002`, passed for this dated TDG case only.** CP-0, CP-1 and
CP-1A were each accepted first time on gpt-6.1-sol at medium effort: 29 calls, USD 0.93149640,
largest request 49,231 input tokens. Both attempts together cost USD 1.22106300. CP-1 and CP-1A
carry their upstream handoffs' hashes, which match the files. The report's four requested sections
are populated and rendered in a browser with no console errors; it reads "Assessment pending"
because CP-6 was not requested.

**Checked by hand against the raw 10-K HTML and its inline XBRL tags, not the run's conversion:**
137 of the 141 annual values in CP-1's financial table equal the tagged fact for that year. The other
four are untagged EBITDA and opening cash, and they appear on the cited page. All 135 table figures
are on the pages their rows cite, all 65 bridge results recompute, and CP-1A's financing, acquisition
and distribution dates match K pages 53-54 and 63. Of 94 quoted spans, 92 are in the filings; CP-0
flags one as re-punctuated, and the other is CP-1's "— (reported dash)" table key, not a quotation.

**Two gaps the filing answers, neither changing a reported figure:**

- CP-1 and CP-1A leave the October distribution unreconciled, but K page:63 gives
  4,216 dividends + 132 equivalents = 4,348. CP-1A read that page.
- CP-1 leaves the 67 between RCF commitments (910) and availability (843) unexplained, but K page:59
  says it is letters of credit. CP-1 did not read that page.

**Limits of this case:** `K page:N` means a page of the run's retained text, not the filing's printed
page. CP-1's method names `extract_statements`, which this loop does not offer, as in the earlier
cp-os loop runs; its handoff says rows were read directly. The test's context leaves the cutoff blank
and says legal documents are "executed" though none were supplied. CP-0 flagged both, so all three
handoffs carry a retrospective label and legal conclusions stay restricted.

**Reviews, inline without agents:** the confidence review confirmed and repaired raw HTML reaching
the model, a cap check sized for the smallest module, silently dropped `_` folders and hardcoded
provider, model and effort in call records. 1,500 generated hostile handoffs produced issues, not
crashes; a hostile issuer name did not reach the report as markup. Rewrite tournament: incumbent
holds except one merged module refusal.

**Not verified:** opus-medium, sol-high and deepseek-max against a real provider; other issuers and
the full pathway presets live; whole-filing completeness of the handoffs, since the review covered
what they state, not everything they could have found; the HTML Model, charts and CP-8, which this
command omits.

## 2026-11-05 — cp-os live loop reused

The [campaign record](runs/cpos-sol-medium-20261105/verification.json) now records
sequential sol-medium module proofs followed by a fresh CP-0 → CP-1 → CP-1A → CP-2
annual issuer-to-deliverable run. It includes the actual responses, independent
source/arithmetic checks, a checker-format repair with retained-response recovery,
populated report/HTML Model/charts/calculation JSON, and zero-provider resume.
This closes that bounded live integration gap. Broader module limitations and
fresh full-pathway coverage in the historical matrix below remain separate.

## Active goal — all modules and aliases

**Current output ruling:** Excel is ingestion-only. No Excel/workbook export is
required or permitted. Model publication means the existing HTML Model, charts
and calculation JSON. Historical references to pending workbook outputs below
are superseded and do not add completion work.

The imported catalog contains **25 modules and 16 aliases**. The user has replaced
CP-MEMO with the actual deliverables; it is a delivery obligation, not another
analytical module or a separate mandatory memo. Coverage requires
actual execution, instruction/source checks and downstream consumption for the
applicable scope. A catalog name, synthetic test, partial result or unsupported
gap is not full coverage. A bounded real case can prove the functions it actually
exercises through retained output, source/instruction checks and actual onward
use. Complete current TDG underwriting, exhaustive source coverage and native
provider qualification are separate claims, not prerequisites for that functional
proof. A gap-only refusal still does not prove the positive function.
Alias-specific breadth must be exercised explicitly.
An exact alias can reuse a checked canonical answer if its routing and identical
obligations are verified; additional alias scope requires additional work.
Direct execution of the existing `registry.canonical` resolver passed for all
25 canonical IDs and all 16 aliases. This proves routing only; the analytical
statuses below remain separate.
CP-OS orchestration, pathways and populated deliverables remain part of the
end-to-end completion condition after analytical links are proven.

Earlier loops used independent subagents. Each run states its execution mode;
current work follows the active project instructions and advances analytical
execution one module at a time.

**Current user clarification:** prove function with an alternative issuer or an
older file when access is unavailable. Clearly labelled historical cases can
exercise a module; every module need not wait for a complete TDG source pack.
This does not make outdated evidence current, synthetic data real, or an isolated
module case an accepted end-to-end pathway. Native provider/runtime and complete
issuer-underwriting claims remain separate from the stated functional evidence.

| Module | Current loop status | Alias coverage still required |
|---|---|---|
| CP-0 | Annual/HTML readiness and actual CP-1 consumption checked. Historical Erste pack adds full supplied-sheet preparation, source conflicts, P1-P8, checked Markdown package and actual CP-1/report use. Broader source profiles/current/full runtime scope remain open | CP-PARSE: sheet/range plus targeted PDF, representation and package duties now exercised; scan/slide/legal/multi-batch scope unqualified |
| CP-1 | Annual loop passed; December-quarter primary statements checked and consumed by CP-1B; other interim/note scope remains | None |
| CP-1A | Bounded annual loop passed; fresh CP-2 consumed business/transaction/governance facts and limitations | CP-2C: absorbed duties checked and consumed; explicit unscorable dimensions retained |
| CP-1B | Reported fiscal-quarter update checked and consumed by CP-2D; CP-OS now publishes five selected earnings sections from its actual handoff. Full preset/benchmark/native scope remains open | None |
| CP-DR | One bounded historical-guidance question answered from official issuer/SEC text; actual qualified CP-2G adoption; raw-byte retrieval and wider research scope remain open | None |
| CP-1C | Actual FY2024 operating/cash/statistical loop checked and consumed/rendered. FY2025 two-class equity and known-components EV-proxy calculation plus two Provisional individual-peer applications now checked, consumed by CP-2 and rendered. Complete economic EV, transaction comps and normalized/current/full scope remain open | None |
| CP-1D | Signed issuer adjustments, recurrence and annual comparison checked; actual CP-2 consumption. CP-OS now publishes all thirteen quality/debt registers into three added earnings sections, preserving the earlier five. Quality earnings remain unresolved | CP-1E: an actual alias request routes once to CP-1D; all six debt registers delivered with independent known-subtotal/leverage checks. Complete obligation quantum/agency basis still open |
| CP-2 | Annual/incremental synthesis consumed by CP-2A and report delivery. Fresh host answer now requested/retained through CP-OS, checked across nine/six/eight analytical lanes and consumed by a new populated report; same-host context and broader/native limits explicit | None |
| CP-2A | Bounded static loop plus historical event/calendar increment checked and actually consumed by CP-2D | CP-2B: seven broader registers, six source-backed projection rows and actual consumer exercised; exhaustive/current/native scope unproven |
| CP-2E | Historical exposure/hedge registers and conditional illustration checked and consumed by CP-2. CP-OS now delivers all17 macro/ESG registers,84 rows and230 exact table values after a delimiter-only repair; complete net rate/FX/cost sensitivities remain open | CP-2F: explicit alias request dispatches once to CP-2E and delivers all eight ESG registers. Separate Enel historical host case adds a checked positive coupon mechanism, actual targeted CP-3C reading and report; complete terms/payments/materiality/market and full-method qualification remain open |
| CP-2G | Three conditional annual paths checked and consumed by CP-2/report. CP-OS now publishes all nine registers with180 independently checked cells/nulls,15 breakpoint tests and224 exact table values. Complete source-backed cash forecast, native fiscal wrapper and Model-driver publication remain open | None |
| CP-2H | Real April 2024 Ford Otosan S&P/Fitch case checked across ten registers and consumed by CP-3C. CP-OS now publishes all ten registers from four pinned handoffs without inventing a new stress module. Exact agency headroom, native runtime and TDG ratings remain unproven | None |
| CP-3 | Actual ARCC two-note normalized historical RV/precision/duration comparison checked, consumed by CP-6 and rendered; runtime can preserve no supported ranking. All ten Relative Value sections now publish through CP-OS with the source-bound conditional yield figure. Full current/executable and complete underwriting scope remains open; Frontier recovery-phase handoff consumed | CP-3A: actual priced pair structure, compensation, recovery-sensitivity/preference trade-offs and monitoring checked/consumed; no robust executable preference asserted. Prior Frontier class-recovery function also exercised. CP-3B: actual historical LQD five-note exposure, concentration, conditional loss and monitoring checked, consumed by CP-6 intake and rendered; full gated selection/sizing pending |
| CP-4 | Actual TDG executed-notes core interpretation checked/repaired and consumed by CP-3C; current/native/full-package acceptance unproven | CP-4A: actual historical ARCC published-precision coverage cushion and conditional commitment difference checked, consumed by CP-6; other basket families unproven. CP-4B: actual historical LMI nineteen-entity partial map checked/repaired and consumed. CP-4D: actual LMI six-view ICA/control loop checked and consumed; complete current package remains unproven |
| CP-4C | Actual Frontier historical numerical pledged-pool waterfall, deficiency recovery, pool-specific marginal-class change and plan EV/equity bridge checked and consumed by CP-3 recovery phase; full/native/all-entity underwriting unproven | None |
| CP-5 | Ford fourteen-claim review consumed by CP-6. Active CP-OS now also retains a fresh TDG twenty-claim host review, targeted lineage repair and checked delivery of all seventeen assurance registers; independent/native/full underwriting acceptance unproven | CP-5A: actual alias request dispatches to CP-5 after selected analysts; eight audit lanes, two inherited Material restrictions and scoped clearance delivered. The actual CP-5 final LQD recheck now also reaches the eight-section CP-OS Portfolio Decision publication. Full/current/independent scope unproven |
| CP-6 | Actual bounded Ford debate consumed CP-5 restrictions; three claims challenged/rebutted, nine dimensions considered, action withheld without market evidence | CP-6A: actual11-step/9-dimension LQD debate,3 matched pitches/attacks/rebuttals, CP-5 reasoning repair/recheck and populated report checked; all eight Portfolio Decision sections now delivered through CP-OS with the cited terminal posture. Exact binding-constraint/implementation and full native scope remain unproven |
| CP-8 | User-defined comparison now runs through CP-OS over23 pinned prior/current files, with actual retained host answer and checked seven-dimension/49-fact report. Five narrative blocks/core156 facts unchanged; Model delivery added. Earlier snapshot2→6 regression/repair loop also retained. Legacy native decision-ledger code is not selected by this route | None; investment-decision post-mortem/calibration is superseded |
| CP-L10 | Actual historical ARCC combined five-screen answer checked, repaired, consumed by CP-5 and rendered into a populated report; native narrow runtime and full-owner work remain separate | CP-L20, CP-L23, CP-L30, CP-L40: all six distinct topics, decisions, upgrades and monitoring exercised per screen; actual resolver maps each to CP-L10 |
| CP-MEMO replacement | Actual deliverables from module handoffs: snapshot, HTML Model/charts/JSON, CP-8 comparison and eight selected earnings sections checked. The eight-section Portfolio Decision preset is also published through CP-OS from actual handoffs; remaining outputs/full-pathway delivery pending | Replaced by actual deliverables per current user ruling |
| CP-MODEL | Historical HTML Model, calculation JSON and three charts from actual handoffs checked and consumed. CP-OS now publishes that method with the report; 81 independently checked numeric cells,51 raw tables,46 blanks and18 chart observations verified. Selected annual USD-million adapter only; broader/native scope open; Excel ingestion-only | None |
| CP-OS | Active local handoff snapshot: planner, current Markdown, bounded repair, resume and checked publication. Fresh host CP-2, Model delivery, CP-8 comparison and CP-5 repair proved within stated scopes. Retained planning now follows pinned consumed inputs, so the Ford ratings case publishes without rebuilding an unused stress analysis; all default fresh plans remain unchanged. All ten Relative Value sections also publish from retained actual historical answers. All eight Portfolio Decision sections now delivered through CP-OS from retained actual LQD analysis, debate and final QA; broader fresh/native/provider and full-pathway delivery remain open | None |
| CP-2D | Annual/quarter cash reviews plus actual historical CRC thirteen-week cash/funding bridge and monthly-to-maturity diagnostic checked, consumed by CP-3C and rendered. Full twelve-month accessible liquidity, formal MTE, actual covenant compliance and native integration remain open | None |
| CP-3D | Actual ARCC historical evaluated-price map, conditional dated July2029 yields/call legs/Treasury residuals, model-loss and price sensitivities independently checked and consumed by CP-3 intake; the full Relative Value publication now retains the cited evaluated-price table and both conditional yield cases. Exact/executable/current and full option/default/native scope remain open | None |
| CP-3C | Actual Ford ratings/funding intake now also delivered through CP-OS with six checked conditional cases. TDG legal consumption and conditional contractual offer calculation checked. Actual CRC forward cash/funding intake now checked across six findings and five route dispositions and rendered; complete takeout/funding/LME feasibility remains open | None |

Later source needs include comparable quarters, peers, governing debt documents,
market quotes, rating evidence, explicit stress/forecast assumptions and prior-run
deliverables. The local corpus already contains additional TDG HTML
filings; they require source-readiness checks before use. Missing inputs will be
addressed at the relevant module, not silently replaced by invented examples.

## CP-OS / CP-3D / CP-3A — all ten Relative Value sections

The [frozen workflow](runs/cpos-arcc-rv-001/workflow.json) now publishes the
[complete existing Relative Value design](runs/cpos-arcc-rv-001/execution/deliveries/70f990d9ed622edfffbd91f9b82ebf54fc3a358a100bc8ed40a3054cd09a7142/report.html)
from actual retained historical ARCC CP-3D, CP-3 and CP-6 answers. This is
publication replay, with zero new provider calls. A format-only CP-3 amendment
copies four original conditional yield results into an explicit table; removing
that block restores every original byte. CP-6 consumed the original version;
no fresh consumer reading or native acceptance is claimed.

The real publication first refused the complete instrument table because the
design slots were unbound. Two existing component declarations and a narrow
adapter now feed the existing renderer:579 facts,528 literal table values,
813 exact handoff citations and four source-bound chart points. Plain finite
percentage tokens, exact unit conversion, missing versus zero, consistent
maturities and both explicit price-basis rows are checked. No pricing is rerun.
Browser review then caught positional TRACE headers overwriting Market Level
and Quote Quality. Exact label guards fix that display error; rebuilt HTML was
checked and the local server stopped. Earlier immutable reports remain retained.

The [single case record](runs/cpos-arcc-rv-001/verification.json) contains the
ranked confidence review, inline rewrite comparison, independent roots, tests
and scope limits. The final clean staged checkout passed163 focused tests;
changed adapter/test Ruff, two-file mypy and JS syntax checks also pass. The
legacy full-suite collection limitation is retained in the case record.
Full current pricing, external peers, executable preference,
complete underwriting and a fresh end-to-end pathway remain open.

## CP-OS / CP-3B / CP-6A / CP-5A — all eight Portfolio Decision sections

The actual [portfolio handoff](runs/lqd-portfolio-001/CP-3.md),
[repaired debate](runs/lqd-debate-001/CP-6-attempt-2.md) and
[final assurance](runs/lqd-debate-001/CP-5-recheck.md) now pass through
[CP-OS](runs/cpos-lqd-portfolio-001/workflow.json) into the complete existing
[eight-section Portfolio Decision design](runs/cpos-lqd-portfolio-001/execution/deliveries/827427820e0e5f1d647ef2323182d9a59eb88edb97a4773b838b01e2ed14e5c4/report.html).
The three requested aliases dispatch canonically once in CP-3 → CP-6 → CP-5
order. Earlier pre-repair QA remains source context; current CP-5 is the actual
post-repair recheck. This is a new publication-evaluation context over retained
answers, not reconstructed original native acceptance or a fresh model run.

The first actual report exposed a display defect: its header said Assessment
pending despite CP-6's explicit Requires More Work. The native header reader
expects settled native bias/confidence facts. A small delivery-adapter correction
now copies the single cited terminal posture for this preset, with no inferred
decision or confidence. The failing regression passes; malformed, duplicate,
uncited and foreign records refuse/are excluded. Other-preset behavior remains.
The original publication is preserved. No analytical value/method was changed.

All498 facts/466 raw table values/659 exact line citations check equal.
Five front-page rows/35 fields match the original NPORT. Twelve independent
money and seven ratio checks preserve May31 2025 NAV, USD versus USDm, exact
issuer identity,2029/on-loan subsets and conditional assumptions. The case verifier
distinguishes explicit not-on-loan N from Y-with-value; unknown status refuses.
All eight sections are populated, and the original full registers remain.

Checked resume invokes no executor. Changed source/stale parent/forged report
and receipt refuse;19 source-context pins and219 case pins match. Browser review
confirms the header, unknown constraint, five holdings, full debate and exact
posture source line142/hash. The local server is stopped. No Excel, provider,
new controller or duplicated analytical run.

`131 passed in15.85s` across the focused delivery/CP-OS/Model/comparison checks;
Ruff and mypy pass. Inline rewrite comparison retained the incumbent helper:
all three alternatives passed16 cases, with no verified practical improvement.
The ranked confidence review, final code and evidence are in the
[single case record](runs/cpos-lqd-portfolio-001/verification.json).
Repeat with `PYTHONPATH=src .venv/bin/python runs/cpos-lqd-portfolio-001/verify.py`.

Requires More Work remains the investment posture. Exact constraints, executable
selection/sizing and complete current underwriting are not established. This
closes a full-preset CP-OS publication link; the broader goal remains active.

## CP-DR — bounded Final Terms search, unresolved result consumed

The [locked brief](runs/enel-final-terms-research-001/RESEARCH_enel-final-terms-research-001.json)
asked one historical Enel instrument-document question before new search.
One initial search and two focused gap stages, followed by inspection of an
existing commercial lead, obtained no primary Final Terms body. Exact web-tool
captures are retained; they are not original HTML/PDF bytes. Language variants
are one source family; current status and other-tranche data are excluded.

The [actual CP-DR answer](runs/enel-final-terms-research-001/ENEL-EFI_CP-DR_20261104.md)
retains the exact question and UNRESOLVED result,0/1 coverage and stop reason.
The [actual CP-2E reading](runs/enel-final-terms-research-001/CP-2E-consumer.md)
rejects this dossier as proof of missing terms. The conditional2.5 EURm annual
illustration,991.23 proceeds and8.77 issue discount remain unchanged; no calendar,
actual payment, document-nonexistence or new issuer conclusion is invented.

CP-OS publishes the retained actual answers into a
[populated report](runs/enel-final-terms-research-001/execution/deliveries/fc7a53f00504420860e75c1952220f326781532d4f8b492759bb66f8f5a4bcad/report.html).
This is publication replay, not CP-OS orchestration of the original web search.
All72 facts/121 line citations and the complete file set check equal; no-executor
resume succeeds. Corrupt-source/stale-upstream controls refuse.212 production
and prior analytical files stay unchanged during checks. No runtime edit,
provider, subagent or Excel output. Confidence review and test-only tournament
skip are in the [single record](runs/enel-final-terms-research-001/verification.json).

Repeat with `PYTHONPATH=src .venv/bin/python
runs/enel-final-terms-research-001/verify.py`. This exercises an honest unresolved
research/adoption path; **positive original-byte discovery remains unproved**.
The broader module/pathway goal stays active.

## CP-2F — historical Enel coupon mechanism, actual handoff and report

[Frozen instructions](runs/enel-sdg-2021-001/instructions.md) → actual
[CP-0 admission](runs/enel-sdg-2021-001/CP-0-attempt-1.md) → actual
[CP-2F/CP-2E pricing answer](runs/enel-sdg-2021-001/CP-2E-attempt-1.md) →
[targeted CP-3C consumer](runs/enel-sdg-2021-001/CP-3C-consumer.md) and
[populated HTML report](runs/enel-sdg-2021-001/execution/deliveries/f6db8cb44acbb3bb57a5257c380e720fba884286e0a20f4c8bdea578bd2906e4/report.html).
The existing CP-OS dispatches CP-0 then canonical CP-2E for the CP-2F request;
there is no competing controller or repeated analytical run for delivery.

Four retained primary PDFs support the separate August3 2021 historical case.
Independent rational arithmetic checks the known zero initial coupon, conditional
EUR2.5m full-year increment on original EUR1,000m principal, EUR991.23m gross
proceeds and EUR8.77m issue discount. The consumer includes the increment once.
June's54.5% observation is not December's target result; assurance, publication,
notice, timing and current principal remain separately gated. No inferred actual
payment, default, issuer materiality, greenium or refinancing feasibility.

All eight ESG views remain, with eight raw tables/42 rows/74 exact table values
and104 exported facts/187 exact handoff-line citations. Browser review confirms
the conditional2.5 row, source line113/hash, known zero, alias and full module.
Full publication reconstruction, no-executor resume and source-change refusal
pass.459 selected production/prior-case files stay unchanged during verification;
the local server is stopped. Only HTML/JSON/Markdown output, no Excel.

Two hand-typed verifier display checks were corrected to54.4572%/0.5428pp
before the financial response was checked; the source-input Fraction oracle was
already correct. The pending exact request was completed and checked on resume,
without repeat dispatch. This is fresh same-host analysis with preflight context,
not independent/provider/native or full-method qualification. The CP-3C consumer
is an actual targeted reading outside this two-module CP-OS plan. Complete final
documents, payment schedule, full ESG schemas/confidence and underwriting remain open.

The [single case record](runs/enel-sdg-2021-001/verification.json) contains the
ranked confidence review and scope limits. Its retained test-only verifier runs
with `PYTHONPATH=src .venv/bin/python runs/enel-sdg-2021-001/verify.py`.
The66 focused CP-OS/Markdown/Model-delivery regressions passed. Rewrite-tournament
skipped: docs, case data and test-only code; no production function change.
The broader goal remains active.

## CP-2E/CP-2F — macro and ESG handoff through CP-OS

[Original instructions](runs/tdg-003/CP-2E-instructions.md) → actual
[macro/ESG answer](runs/tdg-003/CP-2E-attempt-2.md) and
[actual CP-2 consumer](runs/tdg-003/CP-2-macro-update.md) →
[CP-OS alias workflow](runs/cpos-tdg-macro-esg-001/workflow.json) →
[complete analytical module page](runs/cpos-tdg-macro-esg-001/execution/deliveries/eb4d3551d6644d2baee1579c295300acc57fdc67a563731ff14aa4fb2f246c49/report.html#CP-2E).
The CP-2F request dispatches CP-2E once. All nine macro and eight distinct ESG
registers remain:17 tables,84 rows and230 table values checked against exact
source columns;970 total exported facts retain1133 source-line citations.

Actual delivery found T2G.1 had four columns and only three separator cells.
The [new copy](runs/cpos-tdg-macro-esg-001/CP-2E-table-repair.md) changes that
single delimiter; every other byte is equal. Original reply, failed manifest
and requests remain. No financial analysis or runtime/parser change was needed.
The already retained USDm-versus-bps repair also remains intact.

Independent source/Fraction checks retain floating principal9189, gross
arithmetic91.89 versus issuer-reported approximately30, conditional1188/1850
interest/proxy, active swaps2700 and remediation41/prior44. Source images151/139
were viewed; future collars, cap notional, source approximate estimates and
issuer counterevidence remain separate. The unchanged pure helper again returns
missing sensitivities where floor/hedge/FX data are missing. No invented zeros,
ratchet, greenium, payment inference or current/outcome claim.

Browser review confirms all17 register headings, CP-2F alias label and exact
remediation source line/hash. Checked resume, stale/source mutation refusals
and full publication/file-set checks pass;531 earlier input/code/run files stay
unchanged. The local server is stopped. This is retained replay; full effective
rate/FX/cost and TDG sustainability-linked term/pricing evidence remain open.
Units/dates stay literal; native numeric inspector facets remain unpopulated.
No Excel output, provider, subagent or production function change. Confidence
review and the configuration/test-only tournament skip are in the single
[case record](runs/cpos-tdg-macro-esg-001/verification.json). Broader goal remains active.

## CP-2G — conditional forecast handoff through CP-OS

[Original instructions](runs/tdg-003/CP-2G-instructions.md) → actual
[forecast answer](runs/tdg-003/CP-2G-attempt-2.md) → retained actual
[CP-2 consumer](runs/tdg-003/CP-2-integrated.md) →
[CP-OS workflow](runs/cpos-tdg-forecast-001/workflow.json) and
[populated report](runs/cpos-tdg-forecast-001/execution/deliveries/c9116c348257b3bb4b281d43aa8bef1d4c186de3e82a7b9a7171ef9f59b9c2ee/report.html).
All nine T2H analytical registers, qualified research adoption and driver gaps
are preserved. Independent source/assumption Fractions verify180 cells/nulls,
15 break tests and171 displayed operating/roll-forward/ratio cells including
labels.224 CP-2G table values match their exact original columns; the full
publication retains1040 facts/1209 exact handoff-line citations.

The first publication correctly refused CP-2A's generic issuer-free heading.
A new heading names TDG; every subsequent byte matches the original. The old
reply and failed manifest/requests remain. CP-2G originally consumed the old
title version; its financial equivalence is checked explicitly. No analysis,
methodology or production function was changed. Supplemental prior module
handoffs are frozen context, not newly launched native owners. The existing
four-module dependency plan suffices.

Browser review confirms2.28x downside versus3.14x reference coverage, the
first FY2025 analyst watch, missing accessible liquidity and the repaired10.37%
source citation. Source corruption, stale upstream, wrong cash, null-to-zero
and wrong-date probes refuse; checked resume executes no model.520 earlier
source/code/run files remain byte-identical. The local server is stopped.

This is historical retained replay, not fresh financial-model/provider/native
proof, a complete issuer cash/refinancing plan, or an as-of-guidance-date
backtest. October–September planning windows and separately dated later-quarter
context remain explicit. No workbook output/gate. Confidence doubts and the
configuration/test-only tournament skip are in the single
[case record](runs/cpos-tdg-forecast-001/verification.json). Broader goal remains active.

## CP-3C — historical funding handoff through CP-OS

[Original instructions](runs/ford-otosan-2024-001/instructions.md) → actual
[CP-3C answer](runs/ford-otosan-2024-001/CP-3C-consumer.md), consuming CP-2H →
[CP-OS retained replay](runs/cpos-ford-funding-2024-001/workflow.json) →
[populated funding report](runs/cpos-ford-funding-2024-001/execution/deliveries/526e1b1a46636703a009b9652e982f87df45f147643b2bd082285353a8e5bf58/report.html).
The six scenario rows match independently checked source components and rational
arithmetic;179 exported facts retain325 exact handoff citations. The January2024
plan start, April review date, TRY-billion scale, rounded inputs, conditional
access and separate cash-use assumptions stay explicit. Negative balances do
not establish actual financing failure. Original CP-5/CP-6 consumption is pinned.

Actual delivery initially rejected the physically wrapped “Ford Otosan” name.
Normalising comparison whitespace fixes it without altering source bytes; a
further adversarial check preserves the boundary between title and Request.
Six whitespace cases failed before the repair; foreign/source-only/blank and
cross-section identities still refuse.115 focused tests, Ruff and selected
mypy pass. Browser inspection confirms the table, negative-balance source and
unassessed capacity/feasibility tab. The local server is stopped.

The existing planner reuses the five actual handoffs without manufacturing an
unused CP-2D model. No analytical methodology change, fresh/provider execution,
subagent or Excel output. Complete maturity, legal, access/outcome and LME
analysis remain open; this does not close the full module/pathway goal.
Confidence doubts, exact hashes, checks and materiality-based tournament skip
are in the single [case record](runs/cpos-ford-funding-2024-001/verification.json).

## CP-8 — actual comparison through CP-OS

[Frozen instructions](runs/cpos-tdg-comparison-001/instructions.md) → actual CP-OS
[request](runs/cpos-tdg-comparison-001/execution/requests/CP-8/ed0f4d41d1f0e0ada1fdfe0e526d105d8416d56f27f160ea2506bdd76fac0e4a/1.request.json)
→ [retained host answer](runs/cpos-tdg-comparison-001/execution/requests/CP-8/ed0f4d41d1f0e0ada1fdfe0e526d105d8416d56f27f160ea2506bdd76fac0e4a/1.response.md)
→ source/instruction check → separate delivery →
[populated comparison report](runs/cpos-tdg-comparison-001/execution/deliveries/04082614b4fa418445e0d483a3b12e81855decb2ec0b8fd5cfb263c9b47fe20f/report.html).
Actual current host with preceding context and access to frozen check data;
not blind/independent-context or provider/native proof. Only CP-8 was requested;
no upstream analytical rerun, decision history, provider, subagent or Excel output.

**Finding:** the selected prior/current TDG publications have the same historical
financial date, byte-identical CP-1/CP-1A/CP-2 handoffs,156 unchanged core facts
and five exactly equal narrative blocks. The current publication adds the checked
historical Model,81 numeric cells,51 raw tables and three charts/18 observations.
The actual answer compares all seven requested dimensions and explains that
new visibility is not financial growth, a stronger credit assessment or closure
of the Critical cash/contract evidence gaps. Seven annual values remain missing;
quarter and conditional-forecast dates/assumptions remain separate.

**Integration:** CP-OS verifies complete prior/current receipt/file hashes,
issuer/date and embedded View/ReportView consistency, then uses its existing
retain/check/repair/resume exchange. The separate adapter publishes actual CP-8
content with exact citations. The active route uses the user's definition;
imported native decision-ledger code is not invoked or converted by this case.

**Observed repairs:** adversarial copies initially allowed a foreign Model or
an advertised Model with missing HTML. Explicit Model/main identity/content/hash
and required-file checks now refuse both. The inherited prose composition could
not become a dense table by changing its kind alone; the existing tabular-slot
helper now preserves all columns/rows. Dimension faults receive bounded targeted
feedback. Browser review also corrected source/gap table headings locally.

**Checks:**83 focused tests passed; selected two-file mypy and Ruff passed.
All49 exported facts match actual handoff text/line/hash; seven comparison rows
and four correctly named analytical tables are populated. Actual browser checks
confirm the comparison, source inspector and continuing gaps. CLI replay returned
the same final publication with zero new model execution. One actual response
and both publication revisions remain retained. The local server was stopped.
Confidence review, inline post-edit tournament, exact revisions and limits are
in the same [case verification](runs/cpos-tdg-comparison-001/verification.json).
The orchestration incumbent holds; a single-response-digest simplification won
in delivery. All14 original native navigation definitions remain AST-identical.

Broader pathway integration and independent/provider qualification remain open.
The bounded CP-8 function is now orchestrated and delivered; this is not overall
goal completion or general acceptance of every imported runtime route.

## CP-0 / CP-PARSE — real spreadsheets to checked intake and report

[Retained instructions](runs/erste-parse-2024-001/instructions-2.md) →
[actual CP-0 answer](runs/erste-parse-2024-001/ERSTE_CP-0_20261104.md) →
[checked preparation ZIP](runs/erste-parse-2024-001/ERSTE_CP-PARSE_20261104_BATCH-001-of-001.zip)
→ [actual CP-1 consumer](runs/erste-parse-2024-001/CP-1-consumer.md) →
[populated report](deliverables/erste-source-intake-1/report.html).
Historical Erste Group FY2024/comparative2023, separate from TDG. Actual current
host model with preceding context, no provider/subagent or workbook output.

Three issuer-hosted spreadsheets were ingested with the existing read-only
extractor. All654 stored cell strings and source formats matched independent
raw-OOXML checks, including72 empty cells, two merge metadata spans and preserved
named ranges. Their original values contain a material conflict: W1 D4 stores
`7.5279999999999996` under EUR million while the matching PDF shows7,528; W2
assets and W3 operating cash flow have similar discrepancies. The independently
inspected original PDF images confirm the different representations. No parser
bug or general correction multiplier was established; no source was rewritten.
The PDF was explicitly added under a retained instruction amendment.

CP-0 retains P1-P8: full four-source inventory/triage, original hashes, exact
sheet/page locators, source restrictions, coverage, one active representation per
source and a checked eight-member Markdown-only ZIP. Three supplied sheets were
fully read; four of170 PDF pages were inspected, with166 explicitly outside the
targeted scope. Formula/cache/macro/external-link parts were absent; none was run.
Prepared text preserves the PDF's font-glyph limitation and native Excel display
geometry remains unverified. Successful extraction does not approve source amounts.

CP-1 actually opened the handoff and all four packaged representations, checked
their hashes and used six individually matching worksheet observations plus
three separately sourced PDF observations. All18 prior/current values match
independent source literals, with EUR/share distinct from EUR million and annual
durations distinct from instants. Source zeros remain zero; blank group headings
do not become values. G1-G5 and the ban on blanket rescaling reach the report.
All142 delivered facts have exact handoff-line/hash citations. Browser checks
confirm both observation tabs, five restrictions and the exact C39 source quote.

The same [case verification](runs/erste-parse-2024-001/verification.json) records
method revisions, original/package/output hashes, confidence checks and limits.
Existing extraction, mapping, bindings, report-view and rendering code were reused
unchanged; no production functions were edited, so post-edit rewrite tournament
was skipped. The local browser/server were closed. This proves the named
preparation/intake/delivery functions, not scan/slide/legal/multi-batch support,
complete current bank underwriting, a fresh provider/native pass or CP-OS
execution of this issuer case. Overall pathway work remains active.

## CP-OS — report and Model published from checked handoffs

[Frozen workflow](runs/cpos-tdg-model-001/workflow.json) → four explicitly retained
analytical answers → separate delivery →
[populated report](runs/cpos-tdg-model-001/execution/deliveries/de1be08fb3a040d4e4f916cce017b1541b8eaaa8235b6fb50b7c4afb916a2bfc/report.html),
[HTML Model and charts](runs/cpos-tdg-model-001/execution/deliveries/de1be08fb3a040d4e4f916cce017b1541b8eaaa8235b6fb50b7c4afb916a2bfc/model.html)
and calculation JSON. CP-OS stages, verifies and completes the bundle; no second
analytical execution, provider or Excel output. This case is deterministic
publication of actual checked handoffs, not a fresh model or full-pathway pass.

**Reuse and checked content:** promoted the retained original Model builder;
existing Decimal, metric, chart, report-view and rendering components remain
unchanged. Explicit selectors bind the selected annual USD-million layout and
source-reported fiscal dates. All81 numeric cells match independent pre-existing
source/Fraction expectations exactly at the shared rounding precision:74 known,
7 missing. The publication preserves51 raw tables/1,924 value cells, including46
original blanks, and three charts/18 observations with exact table twins.
Operating EBITDA3,843, issuer ordinary3,813 and As Defined4,173 remain distinct
in FY2024. Additional quarter windows and conditional forecasts remain literal,
separately scoped inputs; no current/full forecast claim is added.

**Observed defects repaired:** a wrong balance instant could bind prior-year
debt to a later fiscal label; explicit per-share source rows could be selected as
money; and an all-missing numeric register could be labelled populated. Concrete
fault cases reproduced these failures. Source-instant/type/unit checks and an
empty-Model refusal now prevent them. Missing operands stay gaps, actual zero
remains zero, and source reconciliation differences refuse publication.

**Verification:**66 focused tests passed; Ruff and selected-file mypy with silent
import following passed. An unrestricted mypy invocation also inspected an
unchanged dependency and reported11 existing annotation errors in inline_xbrl.py;
no project-wide type-check pass is claimed. Inline confidence review and post-edit
rewrite tournament are in the same [case verification](runs/cpos-tdg-model-001/verification.json).
Both material incumbents hold; tested alternatives provided no material benefit.
All14 original navigation definitions remain AST-identical. CLI resume returned
the same verified publication with zero analytical execution. Actual browser
navigation opened the Model, its fiscal-year/ratio views and exact handoff
citation, then the calculation JSON; the local verification server was stopped.

**Remaining scope:** other layouts/currencies, broader pathways, fresh/provider
qualification and complete current underwriting remain open. This adapter adds
delivery of proven content; it does not establish analytical scope absent from
the handoffs. Continue the same module-by-module loop for the remaining gaps.

## CP-OS — fresh host response with checked upstream reuse

[Frozen workflow](runs/cpos-tdg-host-001/workflow.json) → actual retained CP-OS
request → [fresh CP-2 answer](runs/cpos-tdg-host-001/execution/requests/CP-2/4ca1b576eeae591784a10f1ac2401566f430619aed7391b22de5f06f1f56f265/1.response.md)
→ source/instruction check → separate delivery →
[populated report](runs/cpos-tdg-host-001/execution/deliveries/17e1d418be894f6aeff979f100e87460fc3f9d80ed4f22cb7114e4b1c5c8627d/report.html).
Actual current host with preceding context and access to the frozen oracle;
not a blind, independent or provider/native run. CP-0, CP-1 and CP-1A are explicit
retained inputs. No previously proven financial extraction was repeated.

**Observed integration changes:** CP-OS originally rejected explicit retained
upstreams. Added pinned reuse with source hashes and exact prior-handoff bindings;
source/context changes now refuse stale replay, and rejected retained work stops
for correction rather than calling an executor. An adversarial origin-change case
also exposed completion records keyed only by publication bytes: identical reports
could collide despite different execution histories. Completion records now use
their complete content hash and keep per-module execution origins. Existing
publications and earlier records remain intact.

**Model-output comparison:**24 financial table coordinates match the independent
literal upstream expectations;12 source rows, the two Critical CP-1A restrictions,
nine profile dimensions, six matrix factors and eight monitoring lanes checked.
Medium confidence and Ready with limitations remain. Annual cash, source-defined
cash-after-capex, carrying debt/principal, availability/LCs and declared/paid/payable
distributions retain their distinct bases and dates. Conditional downside/horizons
are not realized outcomes. No new calculations, thresholds, ratings or security
action; no analytical-method repair was warranted by this first checked answer.

**Onward use:** CP-OS resumed the actual pending response with zero repeated
executors. Separate delivery consumed it into five populated narrative sections;
156 fact/physical-line citations and exact copied handoffs checked. The full
analytical answer is retained in the delivered CP-2.md; this summary adapter does
not render every analytical table. Browser confirms the new assessment, preserved
restrictions and exact `f50a11f5…` source hash. No provider, credential files,
subagents, Excel output, forged native head or second analysis for delivery.

**Required reviews/checks:** confidence review and inline post-edit tournament are
in the same [case verification](runs/cpos-tdg-host-001/verification.json).
Both material incumbents hold: shortcuts that skip stored-byte/context checks
fail adversarial cases; local renaming passes without a substantive improvement.
**40 focused tests passed**; Ruff and selected-file mypy passed. No full-suite or
full-pathway qualification claimed. General Model/chart integration and further
pathways remain active work.

## CP-OS — active handoff execution and verified snapshot delivery

[Frozen workflow](runs/cpos-tdg-snapshot-001/workflow.json) and
[pinned prior answers](runs/cpos-tdg-snapshot-001/responses.json) → CP-OS
CP-0 → CP-1 → CP-1A → CP-2 →
[populated report](runs/cpos-tdg-snapshot-001/execution/deliveries/db57f31adc5539190599e8e5068770f7ed65edc42f1bec9e51ee9d8b11e02005/report.html).
This is deterministic replay of actual previously checked historical TDG answers,
not fresh model execution or independent/native analytical acceptance. Original
fresh-model descriptions inside copied answers describe their original run.

**Change:** CP-OS now drives a local executor/checker exchange using the existing
dependency planner, directory lock and immutable writes. It retains responses
before checking, passes current earlier Markdown, bounds targeted retries and
resumes retained answers without execution. Missing response after a dispatched
call refuses automatic repeat. Changed inputs invalidate affected requests;
changed publication bytes create a new delivery without rerunning analysis.
The separate existing adapter constructs the report. Staging and exact full-file
reconstruction checks precede publication/completion. No second analytical run,
provider call, credential access, competing controller or Excel output was added.

**Actual checks:** four ordered current-handoff maps and exact response copies,
staged source hashes, zero executor calls on resume, five populated requested
sections and159 exact fact/physical-line citations passed. Browser inspection
confirms populated assessment, strengths/weaknesses, company/transaction sections,
candidate/scope limitations and exact CP-2 source quote/hash. The report retains
its full-pathway/Model/chart gaps; a replay byte checker cannot independently
approve fresh analysis. Current support is the public five-section scope only.

**Confidence review and post-edit tournament:** details and source hashes are in
the same [case verification](runs/cpos-tdg-snapshot-001/verification.json).
Adversarial checks cover source/response tampering, forged delivery hashes,
interrupted execution/check/publication, stale consumers, retry ceilings and one
writer. Review added atomic staged publication and renderer-sensitive delivery
identity. Forty differential task variants matched retained bytes/feedback/errors;
the clearer task-copy candidate won. The orchestration incumbent holds: proposed
verification skipping admits a forged pre-completion report; other rewrites add
no verified benefit. All14 prior navigation function/class ASTs remain unchanged.

Focused checks: **34 passed**; Ruff and strict selected-file mypy passed. A broader
runner run was interrupted after **147 passed,2 failed**. Both failures reproduce
with the exact pre-edit CP-OS/delivery files: a money-stop fixture expects
UnknownCharge but gets OverrunStop, and a live-resume fixture never reaches its
injected second-reservation kill. Traced these to stale test inputs:300k tokens
are now priced within the selected1.05m context, and the live worst-case reservation
6.724560 exceeds the fixture's5USD cap. Updated only those fixtures to exceed the
known context and clear the reservation; all three money/resume cases now pass.
Production pricing/budget logic is unchanged. This is not a green full-suite claim.
Fresh host exchange and remaining module/pathway/Model
integration are the next proof obligations; the overall goal remains active.

## CRC — forward cash/funding bridge, actual CP-3C consumption and delivery

[Frozen request/source/method pins](runs/crc-liquidity-2020-001/inputs.json) →
[CP-2D attempt1](runs/crc-liquidity-2020-001/CP-2D-attempt-1.md) →
[targeted repair](runs/crc-liquidity-2020-001/CP-2D-repair-request.md) →
[CP-2D attempt2](runs/crc-liquidity-2020-001/CP-2D-attempt-2.md) →
[actual CP-3C consumption](runs/crc-liquidity-2020-001/CP-3C-consumer.md) →
[populated report](deliverables/crc-2020-liquidity-1/report.html).
Current host model with preceding context and access to the oracle; no provider,
independent/native assurance or accepted head. This is CRC's initial discussion
budget dated9July2020, attached to its filed23July2020 senior DIP agreement,
not approved/achieved funding or a current TDG assessment. Located SEC tool-text
captures are retained; full original-document byte equivalence is not claimed.

**Function exercised:** source-qualified thirteen-week and monthly cash bridges,
uses/mitigants/gaps registers, financing timing, revolving advances/paydowns,
conditional LC-adjusted capacity and a horizon-qualified Tight assessment.
Without projected DIP funding, cash is negative21USDm by week ending17July;
peak funding needed to retain target cash10 is120USDm on18September, compared
with final thirteen-week loan balance82. Monthly January is explicitly a stub
through15January2021 maturity. An unchanged conditional LC-capacity case needs
30USDm more to retain target10. Those are displayed-budget diagnostics; neither
positive cash nor nominal capacity proves actual access or covenant compliance.
Full twelve-month accessible liquidity, formal MTE and complete takeout stay gaps.

**Observed repair:** the first answer described all senior obligations as due at
maturity. Operative principal and specified fee payment clauses support narrower
claims; LC treatment and complete takeout need their own terms. Exactly one
maturity row changed, with no numerical or other analytical changes. The actual
native request check also exposed a wiring issue: editing `methods/cp2d.md` alone
does not affect `liquidity_bridge`, which loads a separate prompt text. The same
small clarification is now in that loaded text; actual offline composition has
it once and otherwise matches the preceding request bytes. This does not qualify
the broader historical ten-step method in the narrower native route.

**Checks:**164 independent Fraction comparisons,153 producer numeric/date
coordinates, seven exact register schemas, source dates/stub and nonzero rounding
residuals checked. CP-3C actually consumed the final handoff, with six findings,
five route dispositions and19 amount/date/definition checks. Separate delivery
reused the existing parser, View/ReportView and renderer:25 tables,123 rows,
515 literal cells/fact-line citations,23 explicit missing cells and six front
findings checked. Browser inspection confirms actual producer/consumer source
quotes/hashes, repaired maturity scope and missing MTE, never zero. Native typed
number inspector facets are not all supplied by this literal adapter.

The required confidence review is in the same
[case verification](runs/crc-liquidity-2020-001/verification.json), including the
exact prompt-only diff and frozen source/delivery hashes. Focused deterministic
tests after the loaded-prompt edit: **325 passed in1.09s** (`tests/test_method_cp2d.py`
and `tests/test_handoff_delivery.py`). No full-suite or live acceptance claim.
Rewrite-tournament skipped: static text/generated artifacts only; no Python
function changed. No Excel output, analytical rerun for delivery or new controller.
Temporary report server stopped. General/native CP-OS completion remains open.

## TDG / Moog — dated valuation construction, actual CP-2 consumption and delivery

[Frozen request/input/source pins](runs/tdg-valuation-2025-001/inputs.json) →
[actual CP-1C answer](runs/tdg-valuation-2025-001/CP-1C-attempt-1.md) →
[checked CP-2 consumption](runs/tdg-valuation-2025-001/CP-2-consumer.md) →
[populated report](deliverables/tdg-fy2025-valuation-1/report.html).
Current host model with preceding context; no provider, subagent, independent
assurance or native accepted head. FY2025 issuers/prices are explicitly historical
and Stale at the2026-11-04 run date; no FY2024 financial values are imported.

**Function exercised:** separate-class prices and actual outstanding shares;
gross/net-carrying/fair borrowing distinctions; finance leases outside borrowings;
restricted cash exclusion; exact scale conversion; reported-line EBITDA definition;
and conditional individual-peer EV-proxy/revenue and earnings applications. Full
EV stays missing because unestablished capital/investment/economic adjustments
are not factual zeros. N=1 has no sector statistics/range; actual current-date
native admission excludes the stale record. The two different methods are not
range endpoints, debt coverage, recovery or current security advice. Transaction
methods and complete/normalized/current valuation remain unproven.

**Evidence/check:**21 independent Fraction-source arithmetic comparisons,
17 named producer result coordinates, three exact valuation table schemas,
25 retained source literals and11 actual consumer value copies passed. The source
check caught one retention gap: the exact note4 receivables passage was absent
although the MD&A amount was retained. Added that original SEC passage separately;
no number, producer answer or original frozen input was changed. Five wrong-basis
alternatives differ from the oracle (class-price/share-count, omitted leases,
restricted cash and adjusted-EBITDA substitution); this is case verification,
not proof of a general input validator. Raw filing downloads failed; located
primary web captures are retained without claiming full-file byte equivalence.

Reused the existing Decimal helpers, Markdown reader, View/ReportView and HTML
renderer, with the previous literal case composer. No production function change
or analytical rerun for delivery. Seven original tables plus twelve narrative
presentations,61 rows and174 fact/physical-line citations checked;28 missing cells
stay missing. Actual browser AX confirms the Provisional header, five CP-2
findings, three valuation tables, exact consumer/producer hashes and source-line
quotes, the missing median and full margin/definition narrative. Periods/units
remain in literal columns/quotes; the manual adapter does not populate every
native financial-number inspector facet. Confidence doubts and dispositions are
in the same [case verification](runs/tdg-valuation-2025-001/verification.json).
Rewrite-tournament skipped: analytical Markdown/generated data and existing
composition only, no production function edits. No Excel output. CP-OS/general
typed publication and the remaining analytical functions are still open.

## Excel ingestion only — active wording aligned

The output ruling already excluded Excel. Removed the remaining active
model-workbook objective in CP-0, workbook-delivery language in the two readiness
projections, and the current CP-MODEL recommendation to use a workbook exporter.
README states the input-only boundary beside the architecture. No new exporter,
analytical execution or completion gate was added; historical artifacts remain intact.

**Confidence review:** (1) hidden output requirement: traced the native publisher
to `model.html`, `calculation.json` and its receipt, and the handoff adapter to
HTML report delivery; no runtime workbook writer found. The stale text came from
the historical workbook objective, not an active Excel export gate. (2) input
regression: read-only ingestion of the retained synthetic portfolio XLSX passed,
with eight sheets, five compliance rows, exact Decimal NAV630928502 and matching
source-cell locators; source bytes unchanged. (3) unintended code changes: AST
comparison against reconstructed prior display strings confirms unchanged control
flow, schemas, signatures and calculations. Ruff's nine ISC004 findings are
identical to that baseline. Rewrite-tournament skipped: docs, comments and display
string edits only, with no new branching.

**Checks:** `PYTHONPATH=src:tests:tests/prompts .venv/bin/pytest
tests/test_handoff_delivery.py -q` → **12 passed**. The broader financial-workflow
run was interrupted after nine passes and one setup error: native Model publication
rejects mixed `MILLIONS` and `currency` metadata in T4.9. Reproduced that same
unit-guard refusal with current and restored prior display wording; it is separate
from the Excel ruling, and native publication integration remains open. The legacy
portfolio test file cannot collect because `scripts.build_templates` is absent;
the read-only input check above does not claim that full suite passed. No provider
execution or workbook output occurred.

## LQD / ARCC — complete scoped portfolio debate, actual assurance and delivery

[Input/method pins](runs/lqd-debate-001/inputs.json) and frozen request →
[CP-6 attempt1](runs/lqd-debate-001/CP-6-attempt-1.md) →
[actual CP-5 audit](runs/lqd-debate-001/CP-5.md) →
[targeted CP-6 attempt2](runs/lqd-debate-001/CP-6-attempt-2.md) →
[actual CP-5 recheck](runs/lqd-debate-001/CP-5-recheck.md) →
[populated portfolio report](deliverables/lqd-arcc-debate-2/report.html).
Current host model with preceding context; three simulated viewpoints inline,
no subagents/providers/independent/native accepted heads. Historical2025-05-31
LQD-held ARCC notes; no December2024 or November2026 data promoted into it.
CP-6A is absorbed into CP-6. Its CIO final-view subsection is not a CP-MEMO owner.

**Function exercised:** all11 substantive CP6A steps, four exact schema column
sets, three ordered pitches/attacks/rebuttals, nine evidence dimensions and nine
CIO final-view elements. Actual holdings/NAV, maturity/loan subsets and conditional
USD/NAVbp losses rechecked against raw NPORT and pre-producer independent
expectations. One explicitly scoped concentration3; eight unavailable dimensions
unscored, no partial average. Requires More Work, Neither wins and exact constraint
Insufficient Information. This is actual measured portfolio debate, not a positive
mandate/constraint/headroom or implementable-size proof. Those inputs remain gaps;
existing ownership proves none of them.

**Confirmed reasoning repair:** RV2 defended identity/value availability against
an attack on protection/mispricing; RV3 defended small NAV footprint against an
unasserted fund-dominance claim rather than the actual limits/budget/operations
objection. True facts did not answer the attacked propositions. CP5-P01/P02
required Insufficient Information, rather than partial rebuttal/mitigation. The
repair changes exactly four defense/matrix rows and one obsolete QA-follow-up
clause; all financial literals/counts, score, source/date, posture and winner are
unchanged. Actual CP5 recheck closes both findings within restricted case scope.

**Method change justified by output:** active cp6.md now requires each rebuttal
to answer the exact attacked proposition, preserving agreed facts without claiming
they prove mispricing/capacity. Also corrected its historical future-owner M10
reservation: CP6A is absorbed analysis; the narrower imported typed composer still
does not supply its registers. Delivery must consume actual handoffs without a
competing owner or repeated underwriting. No Python/schema/composer was edited.

**Confidence review:** ranked doubts were false partial rebuttals, invented breach/
headroom, partial averages/unknown-to-zero conversion, date/denominator/subset errors,
false native/independent claims and dropped reasoning/source quotes. Actual audit
and exact repair comparison resolve the reasoning defects. Raw source/independent
literal checks preserve the quantities and limitations. Docs/static-prompt/generated
case work only; rewrite tournament skipped under that explicit exception.

**Delivery boundary:**22 tables (11 original plus11 narrative presentations),73
rows and164 value/narrative facts/citations. It retains the three full pitches,
posture, constraint, scoring qualification and calculation reasoning; table-only
copying would drop material analysis. Eight unknown scores remain missing/null,
not zero. The existing CallItem shows the actual cited Requires More Work posture,
without a fabricated confidence meter or native committee approval. Existing
Workflow renderer/contracts/View/ReportView/Markdown reader reused; no new
analytical execution, Excel output or general controller.

First report retained but rejected before browser/final publication: its multiline
quotes contained literal slash-n text, and its first check shared that escape.
An independent original physical-line-slice check found this. Report2 uses actual
newlines and a separate physical-slice expectation: all15 narrative and149 table-
value citations exact, all164 values/statuses unchanged. This fixes presentation
provenance; no producer analysis changed. Browser AX confirms the actual posture,
six front-page findings, all11 substantive step headings and RV3's full lines69–79
quote/hash. Complete physical layout/accessibility not qualified. Server stopped.

**Prompt validation limitation:** actual assembled CP6 request contains the revised
method exactly once. Replacing only that text with the saved pre-edit method
reproduces the historical FROZEN hash; other messages are byte-identical. The
inherited prompt-text suite reports21 failed/31 passed because its historical
snapshot/rollback hashes include older CP1/CP3/CP6/source wording. The committee-
specific mismatch is intentional for this method change; no golden hashes were
regenerated to force green. Initial test invocation needed the tests helper path;
correct command used PYTHONPATH=src:tests:tests/prompts. This is not a full-suite
pass. Current analytical/source/repair/physical-citation checks pass. Detailed
[pins, dispositions and checks](runs/lqd-debate-001/verification.json) retained.

The full goal remains active: remaining analytical functions, exact binding-
constraint/implementation evidence, general handoff integration and CP-OS
orchestration/delivery completion have not been asserted by this case.

## ARCC — actual two-note RV comparison and supported abstention

[Instructions/source pins](runs/arcc-selection-2024-001/inputs.json) →
[actual CP-3 / absorbed CP-3A answer](runs/arcc-selection-2024-001/CP-3-attempt-2.md)
→ [actual CP-6 challenge](runs/arcc-selection-2024-001/CP-6-consumer.md) →
[populated report](deliverables/arcc-fy2024-rv-1/report.html).
Current host model with preceding context; no agents/providers or native accepted
heads. Historical Dec31 2024 parent-unsecured USD pair, not current research or
an information-availability backtest. Equivalent actual Lite fundamentals remain
screening-level, not a relabelled full CP-1/CP-2 foundation. All18 selected CP-3/
CP-3A schema IDs checked, shared source/gap tables explicit. No Excel output.

**New positive function:** March2029 has an actually retained executed source;
exact fixed5.875% coupon, Sep/Mar cash flows, Feb1 2029 par call and Treasury+35bp
make-whole input differ from July's5.950%, Jan/Jul, Jun15 call and+30bp. Same
annual financial date controls evaluated values and separate debt roles. Existing
unchanged low-level solver on explicit fractional flows agrees with independent
Decimal roots/PV/derivative. Separate calendar checks confirm accrued interest,
nine/ten remaining coupons and partial terminal coupons; source Treasury columns
checked. Independent data and schedules were frozen before model answer.

Clean-assumption July extra yield2.210154bp becomes only0.160839bp extra simple
Treasury-par residual; analyst±0.5USDm display sensitivity gives a yield-gap
range−0.616287 to5.036816bp. Dirty assumption instead gives18.522010bp extra yield
and16.472695bp residual; its display sensitivity preserves positive yield order.
Possibly different unknown bases also matter. Both actual countercases change
CP-6's next action: resolve precise matched basis/depth first. Neither higher
yield nor shorter duration alone establishes a risk-adjusted preference. Both
remain Requires More Work / RV Unclear; this is a measured comparison, not a
gap-only refusal, current trade or full issuer/all-series qualification.

**Actual repair:** attempt1 treated the nearest-million display interval too
implicitly. Annual source states USDm but supplies no rounding algorithm/error
bound. Attempt2 explicitly labels analyst sensitivity, not a confidence interval
or guaranteed valuation accuracy. Numbers and conclusions unchanged; attempt1
retained. Source, all schema columns, inherited H4A conflict rows, calculation
claims and consumer numbers checked in [case verification](runs/arcc-selection-2024-001/verification.json).

**Confirmed runtime defect and smallest fix:** owner.compute rejected an empty
ordering even with Insufficient Information and a limitation, while the existing
composer already rendered No ordering. Actual model evidence justified abstaining;
the transport forced a permutation. The missing-instrument check now exempts only
that explicit abstention; nonempty permutations, duplicate/unknown/omitted IDs,
confidence caps, evidence validation and limitations remain. Both prompt/context
surfaces and active CP-3 method match. No new composer, schema or financial engine.

**Confidence review (ranked):** accidental acceptance of partial/unknown/duplicate
orders; hidden missing limitation/basis; dropped consumer rows; prompt contradiction;
changed error order/signature; false analytical/native proof. Public blank/whitespace
limitation cases reject, nonempty partial order rejects, existing refusal oracles
pass, CP6 catalogue preserves No ordering/confidence/limitation, and canonical/
CP3A/CP3B store-route regressions settle only a CP3 head. Synthetic routing tests
are labelled as such. Replaced the obsolete missing historical MODULES.csv static
unverified-counter assertion with these actual route regressions. Full native
provider qualification remains open.

**Rewrite tournament — post-edit, inline:** _preference_issues only; signature and
stable issues contract unchanged. Impact: validator→owner.compute/store submit/
probe, composer and CP6 catalogue; no GitNexus available. Speed used direct Counter
iteration, Memory consolidated the facility membership structures, Readability
named the abstention condition. All three matched the incumbent on500 adversarial
shape/confidence/evidence cases. Bracket: Speed over Memory, Speed over Readability,
then **Incumbent holds**: smallest verified diff, existing explicit order/dedup
idiom, no material benefit at measured facility counts (all linear). Static prompt
edits/test-only changes exempt. Full candidate/final code and timings are in case
verification; no extra review files. Final changed function body retains:

```python
def _preference_issues(
    submission: RelativeValueSubmission, upstream: Upstream, evidence: _Evidence
) -> list[str]:
    """The ordering, the basis and gap propagation on the preference (decision 0007, rulings
    4 and 5)."""
    row = submission.preference
    insufficient = row.confidence == "Insufficient Information"
    issues = _basis_issues("preference", row.basis, upstream.catalogue, evidence)
    instruments = [item.facility_id for item in submission.instruments]
    known = set(instruments)
    ranked = Counter(row.ordering)
    for facility_id in dict.fromkeys(row.ordering):
        if facility_id not in known:
            issues.append(f"preference.ordering: {facility_id} is not an instruments row")
        elif ranked[facility_id] > 1:
            issues.append(f"preference.ordering: {facility_id} appears more than once")
    if row.ordering or not insufficient:
        for facility_id in dict.fromkeys(instruments):
            if facility_id not in ranked:
                issues.append(f"preference.ordering: {facility_id} is missing")
    if insufficient and not row.limitation:
        issues.append("preference: an Insufficient Information preference states its limitation")
    strength = evidence.strength()
    if not strength and not insufficient:
        issues.append(
            "preference.confidence: Insufficient Information without observed or indicative "
            "market evidence"
        )
    if not insufficient and not _cites_market(row.basis):
        issues.append("preference: a relative value preference cites a market_evidence quote")
    reasons = _cap_reasons(upstream, evidence)
    if reasons and row.confidence == "High":
        issues.append(f"preference.confidence: capped below High because {'; '.join(reasons)}")
    if _talk_only(row.basis, evidence):
        issues += _level_issues("preference.rationale", row.rationale)
    return issues
```

**Validation:** focused method/context/blank-input/store connection tests:
**231 passed,1 skipped** (pre-existing CP5-spec skip). Linear-readiness CP3 tests:
**3 passed**. Mypy engine: **no issues**. Ruff engine/tests: **clean**;
live/prompts.py has the same four pre-existing ISC004 findings as its saved
baseline, no new diagnostic. Exact scoped diffs inspected; no predecessor/history
mutation. Heavy historical owner-promotion suites and providers were not run.

**Delivery:**21 tables,68 rows,379 literal value cells and exact source-line
citations checked against handoffs; existing Workflow renderer/View/ReportView/
Markdown table reader reused. Browser AX confirms both compensation cases, dates,
limitations, actual consumer quote/hash and all18 producer table headings. Complete
cell accessibility/physical layout not qualified. Server stopped. This is a
case-specific populated report; general CP-OS/handoff integration, remaining
analytical functions, full current/executable selection and portfolio/committee
implementation stay open. The full goal remains active.

## LQD / ARCC — actual portfolio exposure and conditional loss

[Input/instruction pins](runs/lqd-portfolio-001/inputs.json) → actual current-host
[CP-3 portfolio-function answer](runs/lqd-portfolio-001/CP-3.md) → checked
[CP-6 portfolio intake](runs/lqd-portfolio-001/CP-6-portfolio-consumer-attempt-2.md)
→ [populated HTML report](deliverables/lqd-arcc-portfolio-1/report.html).
Current host model with preceding context; no subagents/providers, independent
context, native accepted heads or analytical rerun for delivery. No Excel output.
Full same-date CP-3 selection gate explicitly remains blocked; this proves the
scoped holdings/exposure/sensitivity communication, not full CP-3B or CP-6A.

**Positive work:** real SEC NPORT holdings at2025-05-31, matching NAV
30,823,830,378.19 USD, exact issuer LEI rather than substring. Five ARCC notes:
33,773,000 USD par;33,762,233.40 USD value;0.109532894% NAV. Two2029 maturities:
17,698,117.83 USD,52.419866957% of held issuer value. Assumed40%-par proceeds
13,509,200 USD imply20,253,033.40 USD loss/6.570576451 NAVbp. Alternative60%-par
and−10%-price sensitivities checked too. These are explicit analyst assumptions,
not PD/recovery forecasts or risk-budget usage. No fund mandate/limit, proposed
trade, depth or budget was invented; posture Requires More Work.

**Actual source/instruction checks:** all2,910 source nodes considered for exact
identity, five selected; note IDs, amounts, par units, USD, coupon precision,
maturities, percent-NAV and lending fields checked. repPdDate binds holdings;
repPdEnd is fiscal-year end. Securities-on-loan value is already a subset;
Ares Strategic Income Fund is a different LEI. Selected July2029 loss is already
inside group loss. Existing December2024 pricing/legal context is not promoted
to current2025/2026 selection or applied to newly observed series. Allnine
T3C.1–9 schema columns, seven concentration/four liquidity/four downside
categories and inherited quotation wording checked. Expectations were frozen
before answer using manual literals/Fraction math; source math checked with
Decimal. [Detailed verification](runs/lqd-portfolio-001/verification.json).

**Confidence review:** ranked doubts were date/NAV mismatch, name/lending double
count, par-versus-value loss basis, cross-date legal/selection claims, lost cells
and false sizing/completion. Raw identities/fields, independent calculations,
exact columns and limitations resolve the supported claims. The initial scratch
percentage tolerance was too tight for a five-field sum; preserved originals and
checked each field's precision separately. Consumer attempt1 had an incorrect
manually transcribed producer hash; rejected before delivery, retained, and
attempt2 repairs only that digest. No production code changed. Rewrite tournament
skipped: docs/generated case data only, no changed production function.

**Delivery:** existing Workflow renderer/contracts/View/ReportView and literal
Markdown table reader reused;16 raw tables/80 rows,349 value cells and exact line
citations checked. Twelve original nulls remain missing, not zero. Browser AX
confirms the historical scope, five front-page conclusions, gate/no-sizing
restrictions, source inspector's actual quote/hash, and all13 CP-3 table headings.
Table cells expose Inspect labels in AX; complete missing-cell interaction,
physical layout/accessibility qualification is not claimed. Server stopped.
This is a populated case-specific report, not a general portfolio adapter or
CP-OS orchestration pass. Full selection/preference, committee/implementation,
remaining analytical functions and orchestration/delivery integration stay open.

## TDG Model — actual retained handoffs to HTML, JSON and charts

[Input/instruction pins](runs/tdg-model-001/inputs.json) → deterministic separate
delivery from actual annual/quarter CP-1, CP-2G and current CP-2 handoffs →
[populated Model](deliverables/tdg-model-3/model.html) and
[calculation JSON](deliverables/tdg-model-3/calculation.json) →
[actual CP-2 consumption](runs/tdg-model-001/CP-2-consumer.md).
Current user Excel ruling is recorded in AGENTS/methodology and future delivery
scope text: ingestion only, no workbook generation. No Excel file was generated.
The older workbook-export method is not selected. Reused existing Workflow
renderer/View/ReportView/chart components and Decimal sum/ratio helpers; no new
financial engine or second analytical execution. Source revisions are pinned in
[case verification](runs/tdg-model-001/verification.json).

**Populated scope:**43 complete raw handoff tables (annual, quarter, conditional
paths and current synthesis),81 numeric historical cells, three charts and the
unchanged exact forecast JSON. All1,779 raw source cells/labels/quotes were
independently compared, including46 originally blank cells preserved as missing.
All81 calculation/quantity-family/unit/currency/scale/period checks pass against
pre-output literal expectations plus exact Fraction checks. Known numeric74,
missing7. Eighteen chart marks/table twins pass, with the absent FY2022 ordinary-
EBITDA observation explicitly plotted as a gap. Historical FY2022–2024 math,
unequal actual quarter windows and conditional FY2025–2027 assumptions remain
separate; no LTM, pro forma or available liquidity is invented.

**Definition control actually used:** FY2024 OPEX is1,141 and EBIT3,531 USDm.
Operating EBIT plus cash-flow D&A is3,843, while issuer ordinary EBITDA is3,813
and its own adjusted bridge reaches4,173. FY2023's equivalent difference is43.
These are distinct bases, not an unexplained extra add-back. CP-2 uses the
published distinction, keeps its Medium historical assessment, and retains cash-
access and sustainable-earnings restrictions. Its consumed Model2 calculation,
View and inputs are byte-identical in final Model3; the final host recheck and
browser confirm the presentation-only change.

**Confidence review — ranked doubts:** (1) CONFIRMED initial JSON lacked explicit
per-value dimensional metadata: added without changing amounts; (2) CONFIRMED
46 source blanks became known placeholder text: repaired to missing/null with
exact citations; (3) CONFIRMED browser hid ratio fiscal headings in key-value
layout: existing dense-table layout restores FY2022/23/24, all values unchanged;
(4) wrong EBITDA/OPEX/CF/debt base:81 independent checks and actual consumer
preserve definitions, source bridge and cash roles; (5) dropped/unlike periods,
rows or sources: all43 raw tables and1,779 cells checked against original handoffs;
(6) false promotion, Excel output or overwrite: candidate/manual scope remains,
no journal head fabricated, no Excel generated, Model1/2 retained. General/native
CP-OS integration and independent-context assurance remain open.

Actual browser AX confirms allthree chart series/gaps, correct money units,
ratio years, the OPEX formula/period/basis inspector and Model rail opening all43
source-table headings. Physical screenshot/layout/accessibility qualification is
not claimed. The local server was stopped. Only two static scope strings changed
in production code; `pytest tests/test_handoff_delivery.py -q`: **12 passed**.
Rewrite tournament skipped under its trivial-edit rule: static strings, docs and
generated presentation data, no changed production function. The full objective
remains active, including market/portfolio and CP-OS integration.

## CP-8 correction — actual prior/current deliverables and repair loop

**Current user authority:** CP-8 compares deliverables from prior runs with the
latest current run. The imported investment-decision post-mortem was the wrong
task; external investment decisions/outcomes and three-decision calibration are
not prerequisites. Earlier ledger references to that gate describe superseded
methodology, not remaining CP-8 obligations. AGENTS.md and the selected
`src/deploy_vii/methods/cp8.md` now state the corrected function; catalog title/
purpose match. The former method is preserved at
`docs/reuse/legacy-cp8-decision-ledger.md`, SHA256
`41252b13b5734319fde4a92b291db0cbb55cd5190c727bb7dbf9a8bc964b9c28`.
The unused Berkshire source investigation is explicitly stopped without CP-8 proof.

[Frozen instructions/input pins](runs/tdg-run-comparison-001/instructions.md) →
[actual CP-8 comparison](runs/tdg-run-comparison-001/CP-8.md) →
[actual CP-2 consumer](runs/tdg-run-comparison-001/CP-2-consumer.md) →
[new populated report](deliverables/tdg-fy2024-snapshot-7/report.html) →
[actual CP-8 recheck](runs/tdg-run-comparison-001/CP-8-recheck.md).
Current host model with preceding context, sequential, no agents/providers/native
acceptance. Compared actual hash-verified TDG snapshot2 and snapshot6 bundles,
allfive report sections and delivered module tables. Both have the historical
2024-09-30 financial base; “current” means selected latest local delivery, not
2026 issuer information. The comparison distinguishes added analytical scope
from financial performance between periods.

**Observed findings and actual repair:** CP-2 adopted three supported restorations:
(1) the prior dated FY2028/FY2029 principal concentration disappeared from the
new compact summary/dashboard; (2) the related-party/lender-reporting restriction
remained in CP-1A but fell out of CP-2's gap list; (3) two inherited Critical
restrictions remained in CP-1A but lost explicit labels in CP-2's consequence
cells. These were visibility regressions, not evidence that the subjects were
resolved or entirely absent from all upstream material. Existing source values,
scenarios, peer analysis and Medium fundamental confidence remain intact.

**Verification:** both original bundles' file hashes pass; CP-1/CP-1A facts,
tables/artifact hashes are identical; three of the original five report blocks
are exactly equal. The actual review uses meaning rather than shifted ordinals
or duplicated Strengths/Weaknesses labels. Snapshot7 adds only one weakness and
one two-cell gap, plus two severity prefixes. All **166 literal facts and exact
citations** match copied handoff lines (including labelled prose-table joins),
the maturity wording equals the prior delivered fact, the other four blocks
are exactly equal and CP-MODEL remains blocked. Actual browser AX inspection
confirms maturity figures on the front page and allthree restriction restorations
on Limitations. The local server was stopped. [Case verification data](runs/tdg-run-comparison-001/verification.json)
pins instructions, both inputs, producer, consumer, recheck and final output.

**Confidence review — ranked doubts:** (1) false financial changes from same-period
report development: exact bases and financial/module data checked; no such claim;
(2) invalid ordinal pairing or lost duplicate labels: allfive sections read and
semantic themes paired, with unchanged tables compared completely; (3) omitted
gap mistaken for resolution or severity downgrade: unchanged CP-1A inspected,
only inherited labels restored; (4) repair overreach or lost cells: complete
before/after field differences and166 literal citation checks pass; (5) scope/
assurance drift: candidate/historical/Model limits remain visible and native
legacy routing is explicitly unqualified. An initial scratch substring check
failed on the existing adapter's labelled prose-table joins; the check now
reconstructs those rows and all166 pass. No production defect was hidden by
changing model values. Rewrite tournament skipped: documentation, catalog
metadata and generated delivery data only; no production function changed.

This proves CP-8's actual compare → consumer repair → populated delivery function.
The legacy Python owner/schema implements the superseded post-mortem and still
needs adaptation when CP-OS orchestration is integrated. Full market/portfolio,
remaining module breadth, Model publication and end-to-end CP-OS obligations
remain active; the full objective is not complete.

## ARCC FY2024 — five Lite screens, actual QA consumption and report

[Frozen instructions](runs/arcc-lite-2024-001/instructions.md) → source admission →
[checked combined Lite answer](runs/arcc-lite-2024-001/ARCC_CP-L10_20261104-attempt-3.md)
→ [actual CP-5 recheck and escalation use](runs/arcc-lite-2024-001/CP-5-lite-consumer-attempt-2.md)
→ [populated screening report](deliverables/arcc-fy2024-lite-1/report.html).
Current host model with preceding context, sequential, no agents/providers or
native accepted heads. Historical/outdated ARCC FY2024/FY2023 annual evidence,
selected executed-note and evaluated-market handoffs; no December2024 availability
backtest. Original issuer files and predecessor repositories remain unchanged.

The selected broader CP-OS Lite methods combine **CP-L10/20/23/30/40** in one
owner: 20 exact tables, 30 canonical topics, 30 targeted upgrades and five
screen-specific monitoring rows. Seventeen unchanged method/reference/schema
files were added to the archive; all **65 archive hashes** pass. The legacy
seven-KPI/two-quarter runtime proves a narrower function and is not silently
credited with this five-screen analytical breadth. The detailed payload schemas'
missing shared base prevents claiming complete native payload validation.

**Actual comparison and repair:** 33 primary rows/passages checked, original
balance/cash pages115/255 viewed; all30 pre-output attention tuples/ranks and
closed table/topic/owner fields reproduced. First-answer transport repairs fix
object IDs, boolean flags and confidence literals without changing financial
facts or analytical choices. CP-5's first actual review then finds two Material
method defects: generic OVERALL mechanisms and absent observable monitoring
triggers. Attempt3 repairs exactly those five cells and five rows. All source,
topic, upgrade and other decision data retain parity. The actual second CP-5
answer closes those defects and uses the priorities for cash, capital-policy,
market-basis and document-scope evidence escalation. First responses are retained.
Same-session screening QA is not independent-context, full CP-5/5A or committee
clearance. [Case verification data](runs/arcc-lite-2024-001/verification.json)
pins the final producer/consumer, earlier attempt, instructions and evidence.

**Delivery:** case-specific literal data adaptation, unchanged Deploy renderer;
no second analytical run or new production adapter. Five checked OVERALL rows
populate the front page; all20 original tables appear on CP-L10. A separate raw-
Markdown comparison checks **85 source rows, 630 original cells, five summaries
and 635 exact line citations**, including source and output hashes. Actual browser
AX inspection confirms the historical scope, five conclusions, all20 headings,
aliases and monitoring rows; source inspection opens the exact line68 quote and
producer SHA256. AX buttons name their Inspect action rather than expose all
cell text, so the raw Markdown/View check supplies that fidelity evidence.
The existing renderer shows an unjudged Assessment pending; no investment call
is inferred. The local verification server was stopped.

**Confidence review — scoped data/analytical boundary:** (1) dropped/changed table
cells or row labels: independently enumerated source rows equal the delivered
View, all citations exact; (2) source roles and missingness: BDC investment cash,
PIK recognition/collections, restricted cash, debt captions, rate-scenario limits,
historical evaluated-price basis and subsequent events remain distinct; five
GAP_ONLY topics remain requests, never zeros/adverse/immaterial conclusions;
(3) repair overreach: allfive source/topic/upgrade tables remain byte-identical
and only the reviewed fields change; (4) assurance overstatement: candidate
report and screening/full-upgrade banner remain visible. Native/full-owner,
physical layout and general adapter/orchestration qualification remain open.
No confirmed delivery defect survived these checks. Two scratch preflight count/
call-state assumptions failed before publication checks and were corrected to
the actual source/renderer contracts; no model fact was changed to fit them.
Rewrite tournament skipped: analytical Markdown, exact archive copies and
generated presentation data only; no production function was added or changed.
The broader all-module/pathway/delivery objective remains active.

## ARCC FY2024 — actual market map and conditional pricing consumed

[Frozen instructions](runs/arcc-market-2024-001/instructions.md) → CP-0 admission
and focused CP-1 extraction → [checked CP-3D answer](runs/arcc-market-2024-001/CP-3D-attempt-2.md)
→ [actual CP-3 market-intake consumer](runs/arcc-market-2024-001/CP-3-market-consumer.md).
Current host model with preceding context; sequential, zero agents/provider calls
or native accepted heads. The original ARCC annual/legal files were reused read
only, with an additional original-page291 visual check. Official Treasury CSV
supplies the matched Dec31 2024 par curve. All sources are historical/outdated;
the ARCC report's February2025 publication prevents a Dec31 availability backtest.

Ten actual parent-unsecured evaluated observations now replace invented market
fixtures for this bounded function. They are Level2 estimates in rounded USDm,
not executable clean bid/ask quotes. The July2029 fixed coupon5.950% is distinct
from issuer effective post-swap6.040%. Two explicit clean/dirty interpretations
produce conditional maturity yields5.622366%/6.316949%: **69.46bp of basis
uncertainty**, not a credit opportunity. The supplied30E/360 convention is an
analyst scenario, not exact dealer/legal EOM certification. The source-known
June2029 par-call leg has a partial coupon; two terminal legs do not establish
full YTW/OAS or the earlier contingent make-whole path.

**Actual checks:** ten ordered source principal/carrying/fair/prior-fair blocks,
eight executed-term literals and five exact Treasury tenor/header values;
independent48-digit Decimal Newton/PV checks on **four terminal roots, four yield
shocks and six assumed-recovery loss-break-even cases**. Prices, timing,
default-model limitations and source rounding remain explicit. Three refusal/
missing-price controls are separately labelled. All48 method archive pins pass;
six newly retained files are unchanged CP-3D method/helper dependencies plus
the selected CP-3 intake reference. [Case verification data](runs/arcc-market-2024-001/verification.json)
pins outputs, sources, decisions and calculations.

The existing high-level helper correctly rejects dated/nondefault-convention
inputs. Its unchanged low-level PV/yield primitives were reused on explicit
scenario flows; this does **not** qualify a general production dated-bond adapter.
The first model answer had one narrative14-point phrase inconsistent with its
actual15.294-point difference. Only that wording was repaired; first answer,
tables and calculations remain retained. No production change or analytical-
method rewrite was justified. Implied loss figures are model-dependent break-
even illustrations, not factual/default forecasts or market-quoted probabilities.

The actual CP-3 consumer adopts the price/basis/coupon/call/sensitivity findings
and changes the next action to convention resolution and matching fundamental/
terms completion. Its full scoring/selection gate is **not cleared** by the prior
statutory-coverage snapshot. This proves CP-3D's bounded substantive pricing and
communication function, not full CP-3/RV, preference, portfolio, exact current
pricing, option/default calibration, general delivery or CP-OS completion.

## TDG peers FY2024 — actual comparison, onward synthesis and populated report

[Frozen instructions](runs/tdg-peers-2024-001/instructions.md) → source admission
and focused CP-1 extraction → [checked CP-1C answer](runs/tdg-peers-2024-001/CP-1C-attempt-2.md)
→ [actual CP-2 consumer](runs/tdg-peers-2024-001/CP-2-peer-consumer.md) →
[populated five-section report](deliverables/tdg-fy2024-snapshot-6/report.html).
Current host model with preceding context, sequential, no agents/provider calls
or native accepted heads. Historical/outdated FY2024 sources, differing issuer
year-ends; CW's February 2025 filing prevents a September 2024 point-in-time claim.

Three real peers replace invented fixtures for this bounded function. All sixteen
selection dimensions and eleven alignment points were considered before running
the unchanged archived `peer_statistics.py`. Selection remains **Web-Scraped —
Unverified**; primary statement facts are separately checked. Moog's missing
reported group operating subtotal is excluded, not filled with segment profit.
Finance leases are added only where outside borrowing captions. Reported CFO,
customer funding and receivable-sale differences remain visible. No common
EBITDA/FFO/available-liquidity or normalized credit ranking is manufactured.

**Verification:** 42 literal source/upstream re-anchor checks; ten real metric-
period results compared with independent exact Fraction expectations; 23 displayed
ratios and five monetary rows checked. N=2 permits range only for operating margin;
N=3 permits medians elsewhere. Average/quartiles/stdev remain suppressed. Four
synthetic missing/classification/sample controls are separately labelled.
All 42 selected-method archive hashes pass; five are the newly retained unchanged
CP-1C method/reference/helper dependencies. [Case verification data](runs/tdg-peers-2024-001/verification.json)
pins sources, decisions, outputs, calculations, repairs and delivery.

**Observed repairs:** the first CP-1 extraction's unnecessarily specific Wencor
timing phrase was replaced with directly retained acquisition/organic MD&A facts;
no financial cell changed. The final evidence check found the previously read
HEICO lease passage missing from retained captures; an additional exact primary
capture closes that retention gap. CP-1C's first completed answer has one corrected
formatting artifact and an explicit additional-capture locator; figures unchanged.
First responses and initial captures remain preserved.

**Delivery:** actual consumer rows were copied literally into existing report
fields, without another analytical run or production-code change. One blank
table boundary initially dropped five gap rows; the input was repaired and the
first delivery preserved. Exact peer fiscal dates and the later-filing caveat
were then copied beside the comparison. Final snapshot-6 checks all **163 facts
and 163 exact handoff-line citations**, six finding/effect rows, five peer gaps,
five report blocks and input/output hashes. Actual browser AX inspection confirmed
figures, N, restrictions, gap transport and final explicit dates. The renderer's
embedded JSON requires a browser/ReportView check; stripping scripts from raw
HTML is not a valid visibility test. Local verification server was stopped.

Report SHA-256: `6bc718146295fda0ffc4b850a5a5a7c55ccb84d3b7a642cb16c62f7192873081`.
The actual CP-2 peer answer passed its bounded source/instruction review. No
analytical-method rewrite or production edit was justified. This completes the
stated operating/cash comparison link and report increment, **not all CP-1C**:
positive trading/transaction/implied-value work still needs actual dated value
inputs. Market/RV, portfolio, actual decision/outcome calibration, Lite aliases,
Model publication and active CP-OS/full delivery remain goal obligations.

## Frontier 2020 — positive numerical recovery and actual onward comparison

Under the user's alternative/older-source ruling, the actual **June 29, 2020
third-amended-plan disclosure statement** supplies documentary distress, claims,
modeled liquidation proceeds and plan valuation. This is neither invented issuer
data nor a realized-distribution result. [Frozen instructions](runs/frontier-2020-001/instructions.md)
→ [CP-0 admission](runs/frontier-2020-001/CP-0.md) →
[actual CP-4C answer](runs/frontier-2020-001/CP-4C-attempt-1.md) →
[actual CP-3 recovery-phase consumer](runs/frontier-2020-001/CP-3-recovery-consumer.md).
Current host model with context, sequential, no agents/provider calls/native heads.
Direct documentary grounding does not fabricate accepted CP-1/2G/4 artifacts or
claim full native gates. CP-3's price-based preference remains gated.

Retained exact public tool captures cover 1,456 indexed passages without unresolved
overlap conflicts, including complete selected liquidation/valuation ranges.
Original HTML bytes, full 6,924-line coverage and entity-chart visual review are
not claimed. Source hypothetical sale/liquidation dates (Oct 31/Nov 1, 2020) and
plan valuation date (Jan 1, 2021) remain separate, with the actual April 14 filing
as the distress trigger.

The unchanged existing helper actually allocated **net pledged proceeds**, after
source costs/local claims: low 3,523.2 USDm versus 4,139 first-lien claims leaves
615.8 deficiency; high 5,274.1 pays first lien and leaves 1,135.1 for 1,600 second
lien. The **pool-specific** marginal rank moves from first lien to second lien.
Equal-rank 1L instruments are aggregated, avoiding arbitrary serial preference.
Net pledged value is explicitly not group EV; costs/upflow are not added twice.

Exact independent Fraction arithmetic distributes HoldCo's 1,306.1 / 1,654.1
USDm pro rata over 13,706.4 / 11,949.8 modeled GUC. Only unpaid secured balances
join that rank. Total modeled recovery is **86.5398%–100% for 1L**,
**9.5291%–74.9657% for 2L**, and **9.5291%–13.8421% for HoldCo Senior Notes**.
Selected independently published payouts match within 0.1 USDm from rounded
inputs; differences remain visible. The plan EV less 6,560 net debt and 1,370
tax-affected pension/OPEB independently matches source equity **2,070/3,320/4,570
USDm**. It is a different scenario, not a liquidation recovery or trading price.

All ten broader functional register views are represented. Source priority is
an aggregation of an underlying entity analysis, not our independent legal
validation. Source claim bases, preliminary estimates, omitted liquidation taxes,
operational risk and unaligned plan recovery bases remain explicit. No observed
answer defect required repair. One helper import initially failed for its
transitive `validate_handoff` dependency; the unchanged dependency was copied
with the existing helper, without editing production or predecessor files.

The actual CP-3 consumer uses the class/rank/sensitivity distinctions and rejects
equating protection with an attractive price. It is a bounded recovery-phase
result; full CP-3/CP-3A preference and portfolio work remain. Two separately
labelled negative controls refuse a duplicate claim and unknown senior amount;
they are not issuer outcome evidence.

[Verification data](runs/frontier-2020-001/verification.json) pins sources,
instructions, methods, calculations, outputs and actual consumer input. All
**37** current selected-method archive hashes passed. No new production code
was justified by this case; unchanged reused helper copies are not a redesign.

| Actual retained answer | SHA-256 |
|---|---|
| CP-4C | e0b0a126724a5af0ae97ce133f804962d66fb3851c3a841c69021966b00a4146 |
| CP-3 recovery consumer | 3f15bf73ef25073d2a95304e111a8d974932b938b1a31083ee3646526fd9ea8a |

Remaining work includes peer/market/portfolio and decision-outcome functions,
Lite aliases, Model publication, CP-OS pathways and checked final deliverables.

## ARCC FY2024 — positive actual-input CP-4A calculation and consumption

The user's older/different-issuer ruling supplies a functional quantitative case
without inventing TDG covenant EBITDA. [Frozen instructions](runs/arcc-2024-001/instructions.md)
→ [CP-0 admission](runs/arcc-2024-001/CP-0.md) →
[focused CP-1 inputs](runs/arcc-2024-001/CP-1.md) →
[selected CP-4 interpretation](runs/arcc-2024-001/CP-4.md) →
[actual CP-4A answer](runs/arcc-2024-001/CP-4A-attempt-1.md) →
[actual CP-6 capacity challenge](runs/arcc-2024-001/CP-6-capacity-consumer.md).
Sequential host-model work with prior context; no independent agents, paid calls
or native acceptance. Focused CP-1/4/6 increments do not claim those full gates.

Original issuer-hosted annual PDF bytes are retained, SHA-256
`4483569e723b1a0c479d1ce45bcf64e11f6c82c98754bce1aa317641eb81e170`.
Visual checks on PDF pp65/274 match the per-unit definition and financial roles.
Direct SEC HTML requests returned 403; successful public tool captures preserve
all 1,706 base-indenture indexes and 525 supplement indexes. One shorter boundary
truncation at base L815 is preserved in captures; the complete matching-prefix
line is retained. No unresolved conflict; original legal bytes are not claimed.

The selected incurrence test uses asset coverage, not industrial EBITDA. Actual
published coverage per unit 1,962 divided by 1,000 gives 1.962. Against the
reported 150% minimum incorporated through the governing covenant, the existing
headroom helper returns **0.462 ratio / 46.2 percentage points**. An independently
specified Fraction expectation 462/1,000 matches. The 196% whole-percent source
presentation gives 46 pp; no unrounded precision or different definition is
invented. Three separately labelled synthetic controls test inclusive equality
and adjacent boundaries; they are not issuer events or acceptance proof.

The additional **2,219 USDm** equals the issuer-described conditional commitment
ceiling 6,732 minus existing commitment 4,513. It is not unused, legally usable
or funded borrowing capacity. It is not added to approximately 5.1 USDbn reported
facility availability or to ratio room. Principal versus carrying debt, conditional
defeasance, separate default limbs, and January/February subsequent events remain
distinct. Unknown dollar debt/RP/leakage capacity remains null.

All thirteen broader CP-4A duties were considered in combined views. First output
passed the selected instruction/source comparison; no confirmed answer defect or
production/methodology change justified a repair. The first ad hoc section check
incorrectly expected a literal T4C.2 instead of combined T4C.1–2; the checker was
corrected, not the answer. The actual CP-6 consumer retains the positive cushion
and rejects a present usable-financing inference. This proves applicable bounded
quantitative interpretation/arithmetic and communication, not every basket family,
current underwriting, exact transaction compliance or complete pathway delivery.

[Verification data](runs/arcc-2024-001/verification.json) pins sources, instructions,
selected methods, outputs, checks and consumer input. Thirty exact selected
method sources are archived in the existing reuse manifest, including LMI and
ARCC selections. No predecessor file or historical run was changed.

| Actual retained answer | SHA-256 |
|---|---|
| CP-4A | ca53528bf1f6d9758a7d9194e76af181eb884e237388fe46e839e601606168b6 |
| CP-6 focused consumer | 02091a993792739fdb4c0a5ca235be6f80b0f0a3a6e5b27d0b7674d559f18b14 |

Next: a positive source-backed numerical recovery/fulcrum case. LMI intake alone
does not qualify that function. Other module/alias and CP-OS/delivery work remains.

## LMI 2014 structural map → intercreditor control → recovery intake

TDG's operative ICA body was not located in the bounded searches; another
indenture's reference was not promoted into that agreement. Under the user's
source-choice ruling, the next proof uses the public **2014-06-19 LMI Aerospace
ICA** as a separate outdated case. Seven exact web responses retain all 708
indexed source lines without gaps or conflicting overlap. Original HTML bytes,
visual assurance and current amendments are not claimed.

[Frozen instructions](runs/lmi-2014-001/instructions.md) →
[actual CP-0 admission](runs/lmi-2014-001/CP-0.md) →
[repaired CP-4B map](runs/lmi-2014-001/CP-4B-attempt-2.md) →
[actual CP-4D control assessment](runs/lmi-2014-001/CP-4D-attempt-1.md) →
[actual CP-4C intake](runs/lmi-2014-001/CP-4C-intake.md).
Sequential current-host-model work with context, no agents/providers/native heads.
An inventory check confirmed only the root controller running; old agents are
completed. No new subagent or background integrator was launched.

**CP-4B:** every one of the nineteen named acknowledgment entities appears once,
with explicit unknown assets/earnings/carrying-debt/perimeter fields. A combined
matrix preserves overlapping entity/guarantee/security views; recitals are
identified as descriptions, not independent guarantee/perfection evidence.
The first answer omitted the actual Section 2.4 collateral-difference conditions.
[Attempt 1](runs/lmi-2014-001/CP-4B-attempt-1.md) remains; attempt 2 carries the
conditional subsidiary-equity, local-law and later-new-asset differences without
inventing an affected entity or value. No numerical leakage or actual trapdoor
capacity is asserted from missing underlying covenants/usage.

**CP-4D:** actually consumed that exact map and populated all six functional
control views. It preserves the actual lien-versus-payment-versus-structural
distinction; 180-day later-of start; overlapping 15-day action notice; continuing
senior-action/stay conditions; turnover, conditional release, cash-collateral-bid
versus debt-purchase distinction; discharge/refinancing/reinstatement; and the
conditional DIP cap's dependency on the underlying defined amount. Eleven
source passages and selected register columns/rows passed direct checks.
Three synthetic elapsed-date controls match independent expected dates; they
are explicitly not issuer events, legal deadlines or eligibility results.

**CP-4C consumer:** actual use changes the required asset/claim/pool/control
inputs. A revolver commitment is not a funded claim, face amount is not all-in
claims, and guarantees do not multiply principal or asset value nineteenfold.
No numerical waterfall is produced from missing values. That intake does
**not** prove the positive numerical recovery or fulcrum function.

[Verification data](runs/lmi-2014-001/verification.json) retains source, instruction,
input/method and output hashes, nineteen source-named rows, null-field checks,
the observed output repair and synthetic controls separately. These are bounded
historical structural/control functions with actual onward use, not full current
legal-family or native-schema acceptance. No methodology/production code change
was justified by these responses. The selected analytical duties use current
project transport, not inherited full-run/grade/format authority.

| Actual retained answer | SHA-256 |
|---|---|
| CP-4B attempt 2 | e186678812528929002a854fe19d79f66dbf92c080a2ab096768a40229711665 |
| CP-4D | b18a5ede24ce956c7c3fe23d38b099dd2f841eef8d568f9f0c198d15d78f5776 |
| CP-4C intake | 091bdc13d2e335f1e6385a678094b1e2e6da33ad2252f027ac25181128676d7a |

Next: an actual source-backed quantitative capacity case and a positive numerical
recovery case, rather than counting more missing-input refusals as proof. Other
module/alias, CP-OS and checked final-delivery obligations remain active.

## TDG executed legal source → CP-4 → CP-3C

Previous goal turn was **progress**: retained source-grounded outputs and actual
downstream consumption. This increment follows
[frozen instructions](runs/tdg-004/CP-4-instructions.md) and admits the actual
September 19, 2024 execution-version indenture through
[CP-0](runs/tdg-004/CP-0.md). A direct raw-byte request returned 403; twenty
successful public web-tool captures retain every indexed line 0–2876, with
1,445 matching overlaps and no missing/conflicting index. These are complete
indexed text, not original HTML bytes, visual or cryptographic assurance.

[CP-4 attempt 1](runs/tdg-004/CP-4-attempt-1.md) remains intact.
[Attempt 2](runs/tdg-004/CP-4-attempt-2.md) repairs an insufficiently explicit
special-consent qualifier: enhanced consent concerns the specified non-permitted
all/substantially-all collateral release or materially adverse ICA change, not
every release. It also makes the relevant default/exclusion and offer conditions
explicit. Fourteen source-provision findings and eight broader core registers
were checked. Strict incurrence is not maintenance; reported EBITDA/cash interest
does not become the legal fixed-charge ratio. Current usage/headroom stays null.
CP-4A/4B/4D breadth is not claimed complete from this core interpretation.

[Actual CP-3C consumer](runs/tdg-004/CP-3C-legal-consumer.md) uses the exact
repaired answer across five funding paths. The notes indenture does not govern
the separate A/R facility extension. A conditional all-original-principal tender
uses 1,500 gross principal rather than 1,486 carrying value: 101% gives 1,515
USD million principal component, independently matched by Fractions. Missing
accrued interest remains a Gap in the existing sum helper; full cash need is not
invented. No actual control change, tender, default or financing outcome is claimed.

[Verification data](runs/tdg-004/CP-4-verification.json) retains exact source,
input/method/answer pins, actual source threshold reads, synthetic controls,
all three complete rewrite candidates and review evidence. Current host model
throughout, with context; no agents, paid provider, native accepted heads or new
final deliverable. No broader analytical-method rewrite was justified.

### Confidence review — CP-4 threshold parser

Least confident about, ranked:

1. **Partial numeric recognition — confirmed.** Actual source notation is
   fractional; it was already refused. Five ASCII/spacing format controls of
   that legal threshold incorrectly returned the denominator as 3%. Root cause:
   the percent regex could begin after a fraction slash. Refuse unsupported
   fractional-percent tokens rather than approximate or parse a smaller number.
2. **Over-broad refusal — confirmed in the first guard.** A valid 50% with a
   slash-form date was wrongly rejected. Bind the fraction to its own percentage
   suffix; the dated percentage now survives.
3. **Whitespace/sign variants — confirmed.** Signed denominator controls still
   returned 3. Optional ASCII/Unicode signs and whitespace are now handled by
   the refusal pattern; the actual web/vulgar fraction forms still refuse.
4. **Caller/value/reason changes — verified within scope.** The validator and
   report-test callers preserve their interface; ratios, exact Decimal spellings,
   errors and missingness retain behavior. This pure function adds no I/O or
   shared mutable state. Focused tests, type checking and differential cases pass.
5. **Fraction arithmetic support — by design absent.** The source consent stays
   exact two-thirds, not a rounded Decimal or actual vote result. No current
   capacity is calculated from synthetic threshold controls.
6. **Unrelated cleanup — avoided.** Full ruff reports one existing TRY004 in an
   unchanged citations validator. The scoped check excludes that existing finding;
   no unrelated source edit was made. Raw HTML/current legal completeness remains
   an analytical limit, not something this parser patch resolves.

Checks: `.venv/bin/pytest -q tests/test_cp4_threshold_source_forms.py tests/test_method_cp4.py`
— **37 passed in 0.43s** after final selection/test edits;
`.venv/bin/mypy --follow-imports=silent src/deploy_vii/cp4_legal.py tests/test_cp4_threshold_source_forms.py`
— passed; `.venv/bin/ruff check --ignore TRY004 src/deploy_vii/cp4_legal.py tests/test_cp4_threshold_source_forms.py`
— passed with that explicit baseline exclusion. Before/after diff is only one
compiled pattern and a two-line guard (five production lines), plus the new tests.
No predecessor repository was changed.

### Post-edit rewrite tournament — parse_threshold

Inline, no agents. Impact set: `_threshold_issues`, `_test`, method tests and the
new source-form regressions. Preserve signature, exact values/reasons, refusal
and strictness, with no new side effects. Speed (`findall`), memory (first/count)
and readability (early dispatch) candidates each matched **1,555** exact
input/result cases; actual source threshold parsing and three labelled synthetic
strict-boundary controls also passed. Bracket and complete candidates are retained
in the verification data.

**Winner: Incumbent holds**, `src/deploy_vii/cp4_legal.py:302`.

- The fix remains limited to the reproduced fractional-token failure.
- Bounded lists and consistent `finditer` use avoid parallel state or extra lists.
- No challenger demonstrated a material benefit; final focused tests/type checks
  verify the retained caller contracts. No performance gain is claimed.

Final code:

```python
_FRACTION_PERCENT = re.compile(
    rf"[0-9]\s*[/⁄]\s*[+−-]?\s*{_NUMBER}\s*(?:%|percent|per cent){_AFTER}", re.IGNORECASE
)

def parse_threshold(text: str, unit: str) -> tuple[Decimal | None, str | None]:
    """The one threshold a quoted text states, as written (a ratio N to one is N, a multiple
    N x is N, a percentage is its number: 12.5 for 12.5%), or None with the reason it cannot be
    read. A ratio to anything but one is not read: Python would have to divide a number the
    model never wrote. Only the multiple and percent forms are read."""
    plain = normalise(text)
    values: list[Decimal] = []
    issue: str | None = None
    if unit == "multiple":
        for match in _RATIO.finditer(plain):
            numerator, denominator = _decimal(match[1]), _decimal(match[2] or match[3])
            if denominator == 0:
                issue = "the ratio has a zero denominator"
            elif denominator != 1:
                issue = "a ratio to other than one is not read; set threshold_unit to other"
            else:  # "5.00 to 1.00" keeps its written 5.00
                values.append(numerator)
        # A ratio's own numbers are read once: the "N times" form is searched outside them.
        values += [_decimal(m[1]) for m in _TIMES.finditer(_RATIO.sub(" ", plain))]
    elif unit == "percent":
        if _FRACTION_PERCENT.search(plain):
            return None, "a fractional percentage is not parsed; set threshold_unit to other"
        values = [_decimal(m[1]) for m in _PERCENT.finditer(plain)]
    else:
        return None, f"a {unit} threshold is not parsed"
    if issue is not None:
        return None, issue
    if not values:
        return None, f"no {unit} threshold is written in it"
    if len(values) > 1:
        return None, "it states more than one threshold; quote the one tested"
    return values[0], None
```

| Actual retained answer | SHA-256 |
|---|---|
| CP-4 attempt 2 | 2df299b0a2ddeead6035f8edf8f040a8ec3855d5eec043fc2620170013d3dee0 |
| CP-3C legal consumer | 3ea649342cf8cc91f1205591b7d3c3ae4a7f51687117b34ee4ba98bee0bdcb63 |

Next: genuine structural/intercreditor and capacity cases, using other dated
sources where necessary. Other modules/aliases, CP-OS and checked final outputs
remain obligations; no gap-only refusal counts as positive functional proof.

## TDG historical event/calendar increment — absorbed CP-2B

[Frozen instructions](runs/tdg-003/CP-2A-calendar-instructions.md) →
[actual CP-2A / CP-2B event output](runs/tdg-003/CP-2A-calendar-attempt-1.md) →
[actual CP-2D consumer](runs/tdg-003/CP-2D-calendar-consumer.md).
Annual source base September 30, 2024; historical reference November 7, 2024
through November 7, 2025; executed November 4, 2026. Not current events, realised
outcomes or a point-in-time source-availability backtest. Later quarter amounts
are not substituted into the annual base. Prior static stress is reused, not rerun.

Six selected objects address two hedge transitions, facility expiry, the fiscal
debt schedule and separate operating/finance lease windows. Seven broader
registers and six contiguously ranked source-linked projection rows are present.
Three exact dates stay ordered; three fiscal windows remain windows. READY
means historical presentation admission, not complete underwriting/publication.
The ordinal event-occurrence labels are explicitly separate from adverse-outcome
probability; High/High yields Critical monitoring, not a default-probability claim.

[Verification data](runs/tdg-003/CP-2A-calendar-verification.json) pins instructions,
actual inputs/methods, source PDF, three newly inspected page renders and both
answers. Eleven source terms were checked in a fresh extraction of the original
PDF; pages 130/133/148 were visually checked. Gross/carrying/commitment, notional,
principal, lease cash/interest and liability amounts remain distinct. No net
hedge coverage, full obligations total, remaining cash need or runway is invented.

CP-2D's actual use prioritises the July facility access question independently
of the long-term wall, requests dated exposure mapping at hedge transitions,
and rejects full-year-as-remaining and lease/principal/OCF duplication. Structural,
date, source/projection and actual consumer identity checks passed. Semantic
probability/impact/priority judgments remain host-model assessments with context;
there is no isolated API, native owner or independent reviewer qualification.
No source/method/code change was justified. Analytical Markdown/data and rendered
source evidence only; no new final deliverable is claimed for this increment.

| Actual retained answer | SHA-256 |
|---|---|
| CP-2A calendar / CP-2B scope | 8a8c66676f63f1e95abf8f3fe83573687b584c142aad4ec0e06b316197bcd7c9 |
| CP-2D calendar consumer | e41fd566bbda1ae8e5c6ba02bc0dff3f8186888475a63885ea445dd093b1573f |

Next useful proof: an actual operative-document legal case and onward market/
security functions, using another dated issuer/file if needed. Full module
scope, remaining aliases, CP-OS and checked final deliverables remain open.

## Historical assurance and committee consumption — Ford Otosan

[CP-5 instructions](runs/ford-otosan-2024-001/CP-5-instructions.md) were frozen
before [the actual CP-5/absorbed CP-5A answer](runs/ford-otosan-2024-001/CP-5-attempt-1.md).
Fourteen material statements retain source/locator, lineage, verdict and
limitation. All seventeen broader trace/QA registers were addressed; their
meanings are explicitly distinct from the later typed runtime's table numbers.
The [verification data](runs/ford-otosan-2024-001/CP-5-verification.json) pins
actual input/method revisions. Nine earlier input/source hashes, eleven source
terms, six independent rational funding cases and two residuals passed. Semantic
support judgments remain model-authored assessments, not proved by word matching.

One Material source-assurance finding, CP5-001, is counted once: original PDF/
visual confirmation and residual causes remain unestablished. The unchanged
confidence helper returns **46 / Low / Restricted** from the declared fourteen
claims, trace-metadata completeness and partial source gate. Independent exact
arithmetic matches; the trace checklist is not full underwriting completeness.
Three synthetic score/cap controls and four synthetic unsupported-claim controls
are separate from the real findings and claim population. No source or producer
answer was silently rewritten.

[CP-6 instructions](runs/ford-otosan-2024-001/CP-6-instructions.md) then preceded
[its actual debate](runs/ford-otosan-2024-001/CP-6-attempt-1.md), which consumed
the exact CP-5 answer and preserved CP5-001, the conditional funding cases,
provisional ratings and source residuals. Three Bull claims were attacked and
rebutted; ten thesis and nine Chair dimensions were considered. Two supported
ordinal scores and seven null scores produce no average. The incomplete causal
downside path is not called proved default. Action bias and action confidence
remain **Insufficient Information** without market preference/evidence. The
[CP-6 verification data](runs/ford-otosan-2024-001/CP-6-verification.json) records
input identities and structural checks. Actual semantic instruction comparison
found no justified methodology or code patch.

Current host model throughout, with context; no agents, paid provider, independent
persona votes or native accepted heads. CP-6A's actual portfolio/RV source gate
is unsatisfied; no empty registers count as alias proof. No final Ford deliverable
or complete CP-6/CP-6A pathway is claimed. Docs/data only in this increment;
confidence/rewrite code reviews are not triggered by analytical Markdown/data.

| Actual retained answer | SHA-256 |
|---|---|
| CP-5 | a447168100a8ecd9930abbbe82f1b143e6ef3435ea849e80583f8bb0fb47a751 |
| CP-6 | 1204b4d00afc8bdd6c8ed183f742d6cff4f6e178e4aab0e14ff2685348c4d99c |

Next useful proofs remain an event-calendar increment on retained TDG evidence,
then actual legal/market cases and the corresponding broader consumers. The
historical source-choice ruling avoids waiting for a perfect single-issuer pack.

## Historical alternative case — Ford Otosan, 2024-04-11

Previous goal turn was **progress**: actual module consumption and an updated
populated report. This turn initially tested TDG CP-2H access and preserved the
[incomplete source gate](runs/tdg-003/CP-2H-evidence-check.md). Public bodies
required agency registration; search snippets were not promoted into triggers.
The user then explicitly authorised older/alternative-issuer files for functional
proof. Work continued on two public, agency-authored reports hosted by Ford
Otosan, without another access request or a claim that the TDG gap was closed.

[Frozen case instructions](runs/ford-otosan-2024-001/instructions.md) → actual
[source admission](runs/ford-otosan-2024-001/CP-0.md) →
[selected financial input](runs/ford-otosan-2024-001/CP-1-selected-input.md) →
[published-forecast consumption](runs/ford-otosan-2024-001/CP-2G-published-forecast.md)
→ [CP-2H actual answer](runs/ford-otosan-2024-001/CP-2H-attempt-2.md) →
[actual CP-3C consumer](runs/ford-otosan-2024-001/CP-3C-consumer.md).
Sequential current-host-model work with context and unchanged pure helpers; no
subagents, paid providers, isolated API or accepted legacy execution heads.
The source/forecast admission increments are explicitly narrower than full
CP-0/CP-1/CP-2G acceptance; they do not impersonate another issuer's producers.

**Observed and verified:**

- The source financial table's **51** selected cells match the written response.
  [Financial calculations](runs/ford-otosan-2024-001/financial-calculations.json)
  retain nine independent ratios, nine source-rounded comparisons and three FFO
  identities. Display residuals −1 / +1 TRY million remain explicit rather than
  becoming source corrections or zero plugs; `--` remains null.
- Both agencies' actual posture, provisional issue state, dated criteria,
  definitions, conditions, divergence and monitoring were considered across all
  ten T2R registers. Attempt 1 remains; attempt 2 preserves canonical `BB-`
  instead of typographic `BB−`, with no rating-level change.
- [CP-2H calculations](runs/ford-otosan-2024-001/CP-2H-calculations.json) retain
  sixteen source-term/qualifier checks and exact input/method hashes. Approximate
  Fitch leverage produces only an approximate central distance with unknown
  crossing status. S&P gross ratios are not tested as Fitch net leverage. The
  earnings-geography calculation is a qualified proxy, not true agency headroom.
  Six signed/equality controls, two timing/missingness controls and four duration/
  range controls passed. Those controls are labelled synthetic calculations,
  never source forecasts or live analytical qualification.
- CP-3C actually consumed the retained CP-2H hash and used provisional funding
  conditions and metric differences in its reasoning. Its
  [calculation record](runs/ford-otosan-2024-001/CP-3C-intake-calculations.json)
  verifies the rounded source-plan components, six ratios/balances and missingness
  propagation independently. All **24** displayed consumer cells match the record.
  Removing assumed sources and changing distributions are conditional scenarios,
  not actual funding failures. This is intake/funding work, not full CP-3C/LME proof.

**Method finding:** the broader method handles the real case's preliminary/
expected ratings, qualitative conditions, agency differences and approximate
inputs. The later owner's direct ratio-label mapping, fixed three-year shape and
omitted adjustment/duration scope must not override those meanings. No analytical
method rewrite or production-code change was justified by this response. Exact
method/helper copies are retained in the existing selected-method archive.
No code confidence/rewrite review was needed for Markdown, calculation data and
unchanged evidence copies. Full native runtime qualification is not claimed.

| Actual retained output | SHA-256 |
|---|---|
| Selected CP-1 input | a9779359848e8e6c7fed50d4d01cb0c56e60b76b61643c4b00eedd6e429180af |
| Published forecast | 87fb2d2ac4f8941e8acf51facf2aa2d78fd938d808d6d5e5ea584cd9e3e3b931 |
| CP-2H attempt 2 | 4f390c0b0e36f2ea91f179ffd4d872d696635d1a06a2a3b3719590c496c74b72 |
| CP-3C consumer | 4dacb927b491334e57cd01fd848437156975cb0e1b44599e92eeaee490acaed8 |

Bounded historical ratings-analysis/consumption loop passed. The current TDG
agency report, exact native headroom and all remaining module/alias, delivery and
orchestration obligations are not declared complete. Next useful proof: CP-5/
CP-5A assurance of the actual case, then broader legal/path functions with a real
older source that supplies their inputs. No gap-only artifact counts as that proof.

## tdg-003 — actual interim and earnings loop

### Guidance research → conditional forecast → updated populated report

**Progress, not full module/pathway acceptance.** The one-question
[CP-DR dossier](runs/tdg-guidance-001/CP-DR-attempt-1.md) located original November
7, 2024 issuer guidance and its SEC midpoint bridge. The fixed brief's one question
is answered (100% of that bounded factual scope); CP-2G actually opened and
qualified the evidence. Two raw HTML requests returned HTTP 403; exact web-tool
text/locators survive in the [source record](runs/tdg-guidance-001/source-record.json).
SEC and IR are one originating family. Preflight discovery preceded brief lock;
the record does not claim otherwise. No realised later outcome entered the model.

[CP-2G instructions](runs/tdg-003/CP-2G-instructions.md) were frozen before the
[actual answer](runs/tdg-003/CP-2G-attempt-2.md). Current host model with context,
unchanged pure `forecast`/`test_breaks`; no isolated API, paid provider or full
legacy owner. Nine annual rows across reference/downside/disconfirming upside
passed 215 arithmetic/ratio/balance/break/missingness checks, plus nine closing-
cash checks computed solely from input assumptions using independent Fractions.
All 144 displayed operating/roll-forward/metric cells were checked. Attempt 1
retains the observed rounding error; attempt 2 repairs 10.36% to **10.37%**.

Exact guidance midpoints 8,850 / 4,685 remain distinct from finite-driver outputs
8,849.924 / 4,685.1497656. Cash drivers, repayments and excluded additional uses
are explicit analyst stipulations, not a source-backed issuer financing plan.
The downside crosses the 3x analyst coverage watch in FY2025 (2.28x versus 3.14x
reference), not a covenant. Unknown access/minimum cash stay null; positive
year-end cash does not prove liquidity. Actual September dates trigger the
calendar-only wrapper refusal; no fake calendar or accepted runtime head was used.
Full forecast and per-slot CP-MODEL driver contract remain unready.

[CP-2 actually consumed the increments](runs/tdg-003/CP-2-integrated.md), preserving
cash-use conditions, uncertainty, countercase and exact producer hashes. The
unchanged renderer/design then produced the [updated five-section report](deliverables/tdg-fy2024-snapshot-3/report.html).
All **151** handoff-line/hash citations, six exported-file hashes, and five
populated/collapsed sections pass. Browser inspection observed the conditional
2.28x/3.14x findings and assumptions, the limitations destination and C65's exact
CP-2 line 36/hash. Model publication remains visibly blocked. No CP-MEMO
analytical execution was added. Local verification server stopped.

| Retained artifact | SHA-256 |
|---|---|
| CP-DR actual answer | e74a0b1f4b30af1ecb761b5833081e99db000b01b64ad2274131b53bc552ff44 |
| CP-2G actual answer, attempt 2 | 696d6c06044ef19f7902dcd0c2c90f62796b4577889941b9e16877d726265928 |
| CP-2G calculations | 04907444cc2b07852bbb6b9f229119cd0d5096af85a14e47cdb0a7bae0ba3843 |
| Integrated CP-2 | 828e78d47cbb8d718ab4ec8522034ff197500af8411b8a61fde0601f2c51c802 |
| Updated HTML report | 00186b0f4bdd9a0b31eb2e2ceaa4b372090acb37bf75487adaca67d8d5b33118 |
| Delivery record | 34793cf790944fd0ac370ee4c6213fbdc3428ff722b4d1acd430e0abc8e0ad3f |

### Confidence review — issuer check in handoff_delivery.prepare

Ranked doubts, actual causes and outcomes:

1. **Correct issuer refused after word wrapping — confirmed.** Actual integrated
   CP-2 failed before export; three LF/CRLF/tab/repeated-space cases reproduced
   it. Literal casefolded substring matching treated layout as identity. Compare
   casefolded, whitespace-normalised strings; keep original bytes for hashes,
   citations and exported handoffs. Three regression variants now pass.
2. **Empty normalised name accepted — confirmed in adversarial review.** `Run`
   requires only string length, so whitespace survives validation and normalises
   to empty, which matches any text. A concrete whitespace-only manifest wrongly
   exported before repair. Explicitly refuse an empty normalised name; its
   regression now refuses before creating a destination.
3. **Normalization changing provenance or admitting changed/wrong inputs — fine.**
   The hash check still precedes identity comparison. Exact raw-byte copies and
   citation hashes pass; changed-hash and different-issuer refusals still pass.
   Source amounts, dates and analysis are not normalised or rewritten.
4. **Error/ordering, rendering and publication behavior — fine within this patch.**
   Existing disk-failure, overwrite, escaping and concurrent-writer checks pass.
   Re-preparing the actual new manifest after the final guard matches the stored
   view/report/copies exactly. Browser checked visible assumptions and limitations.
   Full pathways/Model publication remain open, not inferred from this check.

Checks: `.venv/bin/pytest -q tests/test_handoff_delivery.py` — **12 passed**;
`.venv/bin/ruff check src/deploy_workflow/handoff_delivery.py tests/test_handoff_delivery.py`
— passed; `.venv/bin/mypy --follow-imports=silent src/deploy_workflow/handoff_delivery.py`
— passed. Before/after diff inspected; only the identity comparison and its
normalised local changed in production code. No predecessor files were touched.

### Post-edit rewrite tournament — prepare identity check

Inline, no agents. Impact set from `rg`: `deliver`/CLI and focused delivery tests;
signature, return values, ordering and side effects remain fixed. Three complete
`prepare` candidates (speed fast path, regex/memory, named-boolean readability)
and the incumbent were compared on **94** actual/Unicode-whitespace/refusal cases
per candidate. Scratch candidates/backup are outside the project. **Winner:
Incumbent holds**, `src/deploy_workflow/handoff_delivery.py` lines 292–298.

- One normalization per input expresses the permitted layout differences.
- The empty-name and missing-name refusal are explicit in the same guard.
- Alternatives add branches, regex work or a temporary without verified benefit.

Final changed code (surrounding hash-first ordering unchanged):

```python
issuer_name = " ".join(request.run.issuer_name.casefold().split())
# Inside the existing per-handoff loop, after the unchanged source-hash check:
if not issuer_name or issuer_name not in " ".join(raw.decode().casefold().split()):
    raise ValueError(f"Issuer name is not established in {module_id}")
```

The focused tests/typecheck above pass on the final code. Candidate equivalence
and actual manifest re-preparation passed; no performance gain is claimed.
Final provenance audit found the project `skills/` paths absent; the cause was
not established. All seven method files used in these loops were found as exact
SHA-matching copies in `cp-os` and [archived here](docs/reuse/selected-methods/manifest.json).
Final method/input hashes pass against those archives; existing run outputs and
predecessor repositories were not changed.
Remaining work: all still-pending modules/aliases, supported forecast inputs,
CP-OS automation/pathways and the full deliverables. The active goal is incomplete.

### Macro / hedging and absorbed ESG — subsequent loop

[Frozen instructions](runs/tdg-003/CP-2E-instructions.md) →
[actual CP-2E/CP-2F answer, attempt 2](runs/tdg-003/CP-2E-attempt-2.md) →
[actual CP-2 consumption](runs/tdg-003/CP-2-macro-update.md).
Current host model with conversation context and unchanged pure helpers; no
isolated API, paid provider or full imported runtime execution. All 17 descriptive
macro/ESG registers and six common headings checked. Sixteen input/method/visual
hashes, nine exact source excerpts and nine arithmetic/conditional controls pass.
Hedge schedule (PDF 151) and remediation table (PDF 139) were visually checked.
The [calculation record](runs/tdg-003/CP-2E-attempt-1-calculations.json) preserves
source identities and actual missing-input results from the single-facility helper.

**Observed repair:** attempt 1's calculation-summary label called 91.89 a bps
quantity. Attempt 2 correctly says **91.89 USDm for +100 bp**; attempt 1 remains.
The issuer's approximately 30 USDm rate effect is retained as reported, not an
independent hedge reconstruction. Future-starting collars are not current
protection at the September 2024 base. No fake floor, FX earnings share, net
exposure, ratchet or greenium was supplied to force a numeric answer.

Absorbed CP-2F considers actual environmental liabilities 5 + 36 = 41 (prior 44),
estimate/payment uncertainty, safety/physical/transition channels and contrary
issuer cost expectations. This supports targeted monitoring, not a new ESG score
or incremental loss. PDF 139 also closes CP-1E's preferred-share question only
at the two stated dates; other claims remain open. CP-2 actually consumed these
findings/limits and exact hashes. Bounded handoff loop passed; full module quantum,
forecast, current outcomes and end-to-end delivery remain unproven.

CP-2E answer SHA-256:
`488d4a43a22ee8d1282cdf83bec2a57f5d0cefe58b5da40bb8bd9f4d8c1aeeca`.
Calculation record:
`5b7c94551da78d59a3a42b0d1045a80052c4a47b7e9b7af4a25a0f3dafe49e6a`.
No production code changed. Next: CP-2G's explicit dated forecast assumptions
and fiscal-calendar boundary, using these actual handoffs.

### Earnings quality and absorbed adjusted debt — subsequent loop

Previous goal turn: **progress**, with actual quarterly statements/earnings and
CP-2D consumption plus two observed numeric-reader repairs. This subsequent
loop used the same retained inputs and advanced CP-1D/CP-1E → CP-2 in the current
host-model context. No new provider/API, production-code change or legacy owner
execution occurred. There is no independent-context model qualification claim.

Inputs/instructions were frozen before the answer. The
[CP-1D/CP-1E actual answer](runs/tdg-003/CP-1D-attempt-1.md) preserves all thirteen
selected descriptive registers. The [calculation record](runs/tdg-003/CP-1D-attempt-1-calculations.json)
pins four actual upstream handoffs, source/method/code hashes and the visually
checked [annual pension table](runs/tdg-003/source-preparation/pdf134-pension.png).
Source and upstream hashes match. Known totals use unchanged `cp1d._sum` and
`_quotient`; independent integer and Fraction checks verify both signed bridges,
the debt subtotal, all eight quotients and displayed leverage changes.

**Observed findings / selected changes:**

- The later core is an additional-financing-case model starting with already-
  adjusted EBITDA. Feeding the issuer's reported adjustments to it would add
  the same 360 twice (4,173 + 360 = 4,533). Actual `_bridge_amount('-64')` refuses
  the signed quarterly item. This is a scope mismatch, not a reason to invent
  Saving/Cost labels or broaden a quote parser. The issuer review starts at
  ordinary EBITDA and reuses the applicable pure arithmetic only.
- Reported transcription support is separate from sustainable normalisation.
  Named annual/quarterly periods establish recurring stock compensation and
  repeated acquisition/refinancing categories. Heterogeneous adjustments remain
  unresolved rather than receiving a default accepted fraction or haircut.
  Quality-adjusted EBITDA stays null; no denominator is manufactured.
- CP-1E's broader debt inventory was actually exercised, not inferred from
  `canonical('CP-1E') == 'CP-1D'`. Finance leases/securitization/advances already
  counted have a known zero second addition. The stated convention adds 62
  operating leases and 19 gross recognised pension liabilities to 24,880,
  yielding a **known-item subtotal** 24,961. Pension asset 13 / net deficit 6
  remain separate; the 4,216 dividend payable remains a separate material cash
  commitment. Unknown claims and agency/covenant conventions remain gaps.

[Actual CP-2 consumption](runs/tdg-003/CP-2-quality-update.md) opened the CP-1D
artifact, retained its exact hash and used its recurrence, cash-conversion,
obligation and uncertainty findings in issuer-specific reasoning. The strongest
counterevidence—positive reported earnings/OCF and a negative quarterly adjustment
that reduces issuer EBITDA—was preserved. No legal, default or rating conclusion
was substituted for missing evidence. Bounded handoff loop passed; full module/
alias quantum, source coverage, forecasts and pathway delivery remain unproven.

| Retained identity | SHA-256 |
|---|---|
| CP-1D actual answer | 02403f02658abdc5c8ed82fe4a5a8bb12d80f20de8a2dd0ac99a3ac740ccde6b |
| CP-1D instructions | 6c71bc731480124fca01a5f3aceca94ea5102b1fa09411cefee4c79907aa0a98 |
| CP-1D calculations | ad7b384c0d962cfd43195c7f2656c6c1f1056065e16e3f2662ff4b20181532fb |
| CP-2 targeted update | f147a5ad94c83015487f4e254788e8f93d025b643eedf213ba2d6184bf1a443e |

No source-code review/rewrite tournament was needed: changes in this loop are
model Markdown, calculation data and documentation, using unchanged arithmetic.
The separate CP-MODEL publication inspection confirmed that its existing workbook
expects validated typed inputs and makes explicit validation claims; no input
status or receipt was fabricated to force current handoffs through it. A specific
unresolved definition boundary is its `EBIT + D&A` calculation versus TDG's
net-income-to-EBITDA bridge: FY2024 source EBIT 3,531 plus D&A 312 is 3,843,
while issuer EBITDA is 3,813. This is a mapping question, not a full exporter
reproduction; no source amount is changed to make it pass. Publication is still
pending. Next analytical loop: CP-2E/CP-2F currency/macro sensitivity,
using the actual issuer exposure and hedge disclosures before choosing shocks.

Previous goal turn: **progress**, with populated report delivery and CP-2D evidence.
This turn extended the real source → CP-0 → CP-1 → CP-1B → CP-2D chain, sequentially
in the current host-model context. No isolated provider/API or legacy runtime
execution occurred. The user clarified that **CP-MEMO is replaced by the actual
deliverables**; it is not another analytical module or mandatory standalone memo.

- [CP-0](runs/tdg-003/CP-0.md): `aa6752f51236ca51dc452f247c212764947878eb21ffd36e6caa75fbfecb809d`.
  All twelve raw/text/metadata hashes and original compound-unit definition hash
  matched. Readiness is bounded to inspected sections, not whole-pack certification.
- [CP-1 accepted increment](runs/tdg-003/CP-1-attempt-2.md):
  `8be815a5103120678d923721a7c52ab3ebaad28985a98df1f673be092d227582`.
  All five primary statements, both equity windows and selected notes: 220 source
  rows retained, 634 arithmetic/numeric checks including 478 inline readings.
  [Attempt 1](runs/tdg-003/CP-1-attempt-1.md) remains; attempt 2 corrects a one-line
  note locator, updates the accumulated check count and retains source-rounded
  margins for downstream comparison. [Calculation record](runs/tdg-003/CP-1-attempt-1-calculations.json):
  `f6baddb8bdf35d8cb9c10ca062067cad2e86463e1baad7ade7a18ef5ff6f38eb`.
- [CP-1B actual update](runs/tdg-003/CP-1B-attempt-1.md):
  `c8fcdda68f74cd7512d15d6603c8aca7e1823e5a32c7bcdec8a5930a01b29a12`.
  Consumed the exact CP-1 hash. Seventeen numerical comparisons and two source-
  rounded margin-point changes checked independently with Fraction arithmetic.
  [Calculations/diagnostics](runs/tdg-003/CP-1B-attempt-1-calculations.json):
  `bb61c12fb934ec3523307954d88b8a16cdf372beda7296ccb43d615c2b346836`.
- [CP-2D actual consumer](runs/tdg-003/CP-2D-attempt-1.md):
  `36978d54a4c6d10dad21e381c8c7351d6e1a4d95aeb58bcc1226aed223ee0196`.
  Opened the actual CP-1B answer; reconciled 6,261 + 752 − 24 − 4,516 − 14 = 2,459
  with the existing pure sum and independent integers. [Record](runs/tdg-003/CP-2D-attempt-1-calculations.json):
  `ff8ece014820d8e49b25f237d54d63ddfff44af88b4e7ff61887ad448cdd41e9`.
  Quarterly flows were not fed into the annual run-rate engine.

All instruction files were retained before their answers in `runs/tdg-003`.
All four six-heading envelopes and downstream-consumed hashes passed. Source
unit/period meanings, unavailable versus source-zero values and original signs
remain intact. Original source data and predecessor repositories were not edited.

**Findings that change the next action:** the reported quarter windows contain
89/91 inclusive days despite the common thirteen-week label. Original dates
remain intact. Pure legacy diagnostics returned `incompatible_dimensions` for
actual U.S. GAAP metadata and `unsupported_pair` for actual nonzero earnings
changes; the code is IFRS- and flat/missing-comparison-specific. This does not
invalidate the model's supported source-grounded analysis. It identifies the
specific constraints to replace before that slice can automate ordinary earnings.

Cash declined to 2,459 despite improved OCF. The whole-quarter distribution line
4,396 is distinct from the October event; annual/interim narratives differ on
vested equivalents (132 versus 131). Both are retained as an unresolved disclosure
difference. No unsupported residual allocation, runway or current sufficiency
conclusion is supplied. Full note/quarter series, legal/access documents, forecast
assumptions, workbook publication and pathway coverage remain unfinished.

### Confidence review — actual numeric-reader failures

Ranked doubts, traced to source and tested:

1. **Zero versus missing:** real H4 `f-57` is a displayed dash explicitly tagged
   `ixt:fixed-zero`; the old amount reader refused it. The
   [XBRL transformation registry](https://www.xbrl.org/Specification/inlineXBRL-transformationRegistry/REC-2022-02-16/inlineXBRL-transformationRegistry-REC-2022-02-16.html)
   defines this as zero for any text. Add that transform after the nil check;
   preserve the original lexeme. Nil remains None; an untagged dash still refuses.
2. **Decimal lexical coverage:** actual source `f-71` is par value `.01` with scale
   zero; it also refused. Permit a leading decimal point with digits. Actual
   source regression now returns exactly 0.01, with its unit kept separate.
3. **Signs/scale/precision/error paths:** existing bounds, sign handling and
   150-digit numeric context remain. Unknown number-word format still refuses;
   this is selected-format support, not full XBRL conformance. 478 actual selected
   numeric readings match source cells/scale/sign. Header facts can be embedded
   within a label: an initial exact-cell membership assertion was corrected to
   substring containment before discovering the genuine `.01` reader defect.
4. **Caller/typing impact:** repository references show `run_inputs` uses parsing/
   period lines, not this amount conversion. Import/input tests pass. Strict mypy
   of the changed Fact class/method passes; whole-file mypy retains the identical
   eleven pre-existing untyped-parser errors, checked against the hash-exact
   baseline. They are not claimed fixed.
5. **Regression failure attribution:** the focused imported subset produced
   **113 passed, 1 failed**. The failure hard-codes a predecessor corpus path and
   83 historical quote misses; current source/key pairing yields 52. Re-running
   with the exact old amount function reproduces the same failure. This unrelated
   external-corpus snapshot test remains open; its expected count was not changed.

Verified: `.venv/bin/pytest -q tests/test_inline_xbrl_fixed_zero.py` — **8 passed**;
ruff check of changed source/tests and test formatting passed. Broader command:
`.venv/bin/pytest -q tests/test_inline_xbrl_fixed_zero.py tests/test_run_inputs.py tests/test_html_text.py`
— 113 passed / the one pre-existing failure above. Source-preparation hashes stay
at their actual generation version; the new handoff records current reader hash.

### Post-edit rewrite tournament — Fact.amount

**Winner: readability candidate**, `src/deploy_workflow/inline_xbrl.py:40`.
Inline incumbent/speed/memory/readability comparison, with backup and direct
final diff inspection. All three complete candidates matched values/error types/
messages for 974 actual facts and 1,000 adversarial combinations. Impact set:
new numeric-reading test and ad hoc actual-source extraction; `run_inputs` parses
without calling amount. No GitNexus metadata is present.

- One named transform removes repeated format splitting and makes dispatch clear.
- Nil precedence, exact source-zero semantics and error behavior remain intact.
- No extra abstraction, parser rewrite or performance claim is introduced.

Final code:

```python
def amount(self) -> Decimal | None:
    if self.nil:
        return None
    transform = self.format.split(":")[-1]
    if transform == "fixed-zero":
        return Decimal(0)
    if transform not in {"num-dot-decimal", "numdotdecimal", "zerodash", "numdash", ""}:
        raise ValueError(f"unsupported numeric format on {self.fact_id}")
    text = re.sub(r"[\s,]", "", self.lexeme)
    if text in {"-", "—", "–"} and transform in {"zerodash", "numdash"}:
        return Decimal(0)
    if (not re.fullmatch(r"(?:\d+(?:\.\d+)?|\.\d+)", text)
            or len(text) > 100 or abs(self.scale) > 30):
        raise ValueError(f"unsupported numeric lexeme on {self.fact_id}")
    with localcontext() as ctx:
        ctx.prec = 150
        value = Decimal(text).scaleb(self.scale)
    return value.copy_negate() if self.negative else value
```

Verification is the exact focused/broader pytest commands above and isolated
strict typecheck of the changed Fact class. Other changes are docs, retained
model/data artifacts and tests; no further nontrivial production function changed.

## tdg-002 — CP-1 annual foundation

Execution: fresh subagent `cp1_execution`, with no inherited conversation and no
access to historical answers or expected-value files in its assigned inputs.
It read the actual CP-0 handoff, the same issuer PDF and frozen instructions.
Independent source review was prepared before that reviewer saw the answer.
No provider API or imported runtime invocation occurred.

- [Instructions](runs/tdg-002/CP-1-instructions.md):
  `a5aea0c588a2ebd1054f98cee2820506642d206d1c8b416cfa86409143b08b56`.
- [Selected five-stage method snapshot](runs/tdg-002/selected-cp1-stage-instructions.md):
  `422f635fc64b30a0986e7332efdfb1f8d7c5964010adb708815a0f70705f1393`.
  Source/context, financials, narrative and readiness are analytical work;
  quality is an independent check. The local catalog has 18 T4 IDs, omitting T4.7.
- [Attempt 1](runs/tdg-002/CP-1-attempt-1.md):
  `38c22ba91b3d55a2a54461317bf09f092af8d84a72abd946e1d44dcb96c88a09`.
- [Attempt 1 calculations](runs/tdg-002/CP-1-attempt-1-calculations.txt):
  `d8dbe3f1d2b33bec52651a05d7e5469016d0414848127e96c8eac76a940ac626`.

**Attempt 1 result: repair required; not released downstream.** Primary statement
figures were substantially correct, but classification and completeness defects
would affect the next consumer:

| Observed defect | Source/instruction comparison | Targeted repair |
|---|---|---|
| Commitment less availability called funded revolver debt, including in G5 | PDF 45 explicitly identifies the difference as letters of credit; PDF 132 alone does not establish a funded draw | Separate commitments, availability, letters of credit and funded borrowing; retain exact maturity dates |
| Opening total equity labeled TD Group deficit | PDF 108 values include noncontrolling interests | Relabel the summary total; preserve amounts and complete equity transcription |
| Issuer EBITDA bridges missing | PDF 53–54 contain net-income and operating-cash bridges, distinct from segment EBITDA As Defined on 142 | Extract and reconcile both available bridges with their definitions |
| Calculated OPEX not exposed for downstream use; intangible amortization offered conditionally as total D&A | Expense equations were retained but no explicit aggregate; the source labels distinguish intangible amortization from total D&A | Retain calculated OPEX/lineage and a definition-preserving account mapping |
| Partial calculation/claim trace | Headline equations pass, but component-level checks and unambiguous narrative operand references are incomplete | Extend the calculation transcript and references; retain the existing financial narrative |

The final attempt-1 file already included the narrative and authorized-share count;
an early preview-based repair description overstated their absence. The executor
received that correction before closing the repair. Original answer hashes remain
unchanged.

Checks completed before repair: 103 numeric row vectors (280 numeric/dash cells)
from PDF 105/106/107/109 were present in the corresponding output tables, including
duplicate-vector counts; labels/units were separately source-reviewed. The full
31-row equity transcription passed 58 exact column/total arithmetic checks and
independent source review. These checks do not establish note coverage or runtime
acceptance. Source review confirmed the two-year EBITDA bridges and the three-year
segment bridge; an initial reviewer sign error for `Other, net` was corrected by
exact recalculation before use as an expectation.

Existing OPEX helper was exercised separately with source-derived, schema-valid
FinancialBook fixtures: signed results −1,141/−919/−884 for FY24/23/22. Missing
EBIT, duplicate SG&A, failed reconciliation and disjoint citation locations
returned no composition. This checks arithmetic and guards, not a complete
ingestion pipeline. Its four-label selection ignores other expense rows, so the
model must establish source-block completeness independently. No product code was
changed on the strength of this bounded check.

[Repair instructions](runs/tdg-002/CP-1-repair-1-instructions.md), SHA-256
`65723e34d0bc34423020ff5c94aacb289628d27d3748ce42c2042a5bdd7736e9`,
produced separate attempt-2 files. The review result follows.

**Attempt 2: annual source/output check passed.**
[Repaired handoff](runs/tdg-002/CP-1-attempt-2.md), SHA-256
`301af0eeed2d90edd2671ef0c71dc759e66c000b3722a0c4ceacfba6fb1332bb`;
[calculation transcript](runs/tdg-002/CP-1-attempt-2-calculations.txt), SHA-256
`16d3fc2dd7ff4a0a0801eb6c3a9d5a6da87321034351aafd248f0541ffb4e5e9`.
The independent reviewer found no remaining material defect in the targeted
annual scope. Root checks reproduced the 280 source numeric/dash cells, all
cash-flow component totals, income/OPEX equations, comprehensive income,
31-row equity roll-forward and both issuer EBITDA bridges. New material quotes
and exact maturity dates match their source passages. Original files remained
unchanged. Supplementary schedules retain their stated visual-review limitation.

The source-informed methodology correction is narrow: available capacity is not
funded borrowing; distinguish letters of credit explicitly. Keep entity/perimeter
labels and reported EBITDA definitions intact. Retain calculated expense
composition with its inputs. No new financial framework was needed.

**Next consumer executed:** fresh subagent `cp1a_execution` received the checked
attempt-2 Markdown and [CP-1A instructions](runs/tdg-002/CP-1A-instructions.md),
SHA-256 `2c02097f0a9f98cede63c095f1d3df9fc461951f2561d0dd0723cce1d2a8a440`.
The selected CP-1A method hash is
`075ade1573851dba48e763edacdbe76d3d0ff240302c5e58d7cb5671ae2e3929`.
Its answer retained ten groups of actual CP-1 facts with table/row/period/unit
references: cash flows, debt, dividends/payable, segment results and maturities.
These were used in the new business/governance analysis. This closes the bounded
annual CP-1 handoff-consumption check. CP-1A's own acceptance and the remaining
module/alias coverage goal stay open.

### CP-1A / CP-2C attempt 1 — repair required

[Actual response](runs/tdg-002/CP-1A-attempt-1.md), SHA-256
`bed151758ef5664bbd242f22ac830544348d62e6c63eee68dfc54399de256908`;
[governance judgments](runs/tdg-002/CP-1A-attempt-1-governance-inputs.json), SHA-256
`7fc6417bea9417245c0c442f1b369506ab5609cb5adebac974b36d2a6e466bc9`;
[calculation transcript](runs/tdg-002/CP-1A-attempt-1-calculations.txt), SHA-256
`efdf8e9361e72b7093930e3e172d39c99dd6dba8e383b8257ca2f12e3eea9fe0`.

The existing governance calculation reproduced four scored dimensions, composite
5 and rubric-level High from eight submitted judgments. Five dimensions were
Not Scorable. **The reproducible score did not establish source acceptance.**

- Only 4/11 governance citations matched the declared page: five used reconstructed
  ellipses/colon snippets absent from the source and two cited page 115 for text
  on 114. All were syntactically valid JSON/Pydantic inputs. Exact quotation/page
  checks therefore remain separate from schema and score checks.
- The answer omitted the filing's explicit September 19 debt funding of the
  special dividend (PDF 29/131/146). Declaration and financing are FY2024;
  dividend cash payment is October. It must not label the disclosed funding
  source as unknown or move financing into October.
- A business row combined fact categories; some recipients were described in
  generic business/liquidity terms rather than CP-3C refinancing/LME, CP-4 legal/
  covenant and CP-6 committee-debate responsibilities. Available amendment
  history and ownership proxy deferrals require more precise treatment.

[Targeted repair](runs/tdg-002/CP-1A-repair-1-instructions.md), SHA-256
`b4ac51bb4048af47fa0f6b9569982e9d46b73505a1c064d9697238ee4f187b46`,
produced separately retained attempt-2 files. No CP-1A answer is released to CP-2
until the repaired evidence and handoff pass.

**Attempt 2:** [answer](runs/tdg-002/CP-1A-attempt-2.md), SHA-256
`1704ecb4b5e284fa48c56437eede47f419ee5f126889f9a57bc02734edb81102`;
[judgments](runs/tdg-002/CP-1A-attempt-2-governance-inputs.json), SHA-256
`8e9c694dc42abc671b741ed45508ffa91358d131f0f3ca637e4bd6fec7053531`;
[calculation](runs/tdg-002/CP-1A-attempt-2-calculations.txt), SHA-256
`67e6164fa9cebb87c9d6bd60b64827778636c598f0608928ee405f16432a200d`.
Root reproduced all 20/20 JSON quotations, the three direct Markdown quotations,
eight schema-valid judgments and the five-dimension score. September financing /
October payment and recipient uses were repaired. The independent source review
and root found remaining category and timeline errors: a row combines issuer
estimates and management characterizations; a February–March interval includes
the June amendment and April redemption; Extant dates were more precise than
the source. The new Mixed creditor-treatment judgment lacked established
creditor-class effects. Disclosed amendments remain useful evidence without
forcing that dimension to be scorable.

[Second targeted repair](runs/tdg-002/CP-1A-repair-2-instructions.md), SHA-256
`e09684575c8036a308f29e925de9913f82db85eb27f770f9c080a0be05bd9505`,
produced separate attempt-3 files. Source and scorer remain unchanged.
Original attempt-1/2 identities are preserved.

**Attempt 3: bounded historical source/output check passed.**
[Accepted handoff](runs/tdg-002/CP-1A-attempt-3.md), SHA-256
`6f63963177c2ea7d54bd043532e250e28625ea70c0ec229d63d55768c2c174fe`;
[judgments](runs/tdg-002/CP-1A-attempt-3-governance-inputs.json), SHA-256
`87bd84313d2201ba5313eac8d2376339718cccb618254efb2824695741343c52`;
[calculation](runs/tdg-002/CP-1A-attempt-3-calculations.txt), SHA-256
`b41c93cdfc5ed719e82fe0ac899305e0f3ae63c813c862b43d924011551461a2`.
The targeted diff corrects dates and fact categories and removes the unsupported
creditor-treatment scoring direction. Root checked new timing/estimate detail
against PDF 4 and 128–131, reproduced all 20 quote matches and the unchanged
scorer, and confirmed earlier hashes. Four dimensions are scored, five Not
Scorable; composite 5 / rubric High is not a credit rating or default finding.
The last edit corrected only the attempt number in the heading before freezing.
Actual CP-1 financial consumption is preserved. CP-2C's absorbed governance duties
were exercised with their explicit evidence limits; full legal/current-liquidity
assessment is not claimed.

**CP-2 execution started:** fresh `cp2_execution` receives only accepted Markdown
handoffs and [frozen instructions](runs/tdg-002/CP-2-instructions.md), SHA-256
`12e5002a278dd5fdb99f22c17c83742f8768a40d04bee7e1e66f5780ed0ef385`.
The selected current method is supplemented with applicable Deploy V dimensions,
downside and monitoring responsibilities identified in the version comparison.
This preserves scope; it is not a performance-based method rewrite. Historical
and current T2 labels differ, so supplementary tables use descriptive names.
The four actual evidence categories are used despite the inherited Five Categories
heading. Independent review prepares expectations before reading the answer.
No provider/runtime, orchestration or final-delivery success is implied.

**CP-2 attempt 1 reviewed; repair required.**
[Actual synthesis](runs/tdg-002/CP-2-attempt-1.md), SHA-256
`7c3875fc6da8b4e61e454853fd339dc212f056bf2aad2388d1c925d0ba34022b`,
consumed CP-1A's actual business mix, dated transactions, ownership uncertainty,
governance result and critical restrictions. This closes CP-1A/absorbed CP-2C's
bounded handoff-consumption check. Independent review found the carried numbers,
bases, dates and distinction between rubric High and credit confidence intact.
CP-2 itself did not pass: three required sections were missing, its CP-1 gap
references used nonexistent T4.12 labels, and multiple cash-flow explanations
treated interest/tax/working capital as uses after OCF although already embedded
in OCF. The reviewer and root also questioned Average liquidity/margin grades
whose stated evidence does not establish usable buffer or margin stability.
[Targeted repair instructions](runs/tdg-002/CP-2-repair-1-instructions.md), SHA-256
`e83cba358b9b52cdcf264a4a345ce61d2b880afee1d528d99d73d82d2faff056`,
retain the checked financial values and scope, correct those defects and require
a final heading/reference/basis check before closing attempt 2. No provider,
calculation formula or product-code change is involved.

**CP-2 attempt 2: bounded synthesis check passed.**
[Repaired handoff](runs/tdg-002/CP-2-attempt-2.md), SHA-256
`249d0cbdf1ba8159dcae68d4ff3241c73ea092ff66353c0c2eef08691e0afa57`,
passes the targeted independent review. All six sections, separate Critical-gap
rows, actual upstream references and usable downstream content are present.
OCF components are distinguished from subsequent uses; liquidity/margin
assessments now remain Not Assessable where the evidence cannot establish them.
Confidence stays Medium. The earlier answer and upstream hashes are unchanged.

**CP-2A started:** [instructions](runs/tdg-002/CP-2A-instructions.md), SHA-256
`7c9a69e7e52cc43948381698f2f74ae0bd0ef4c9553998c23b4ca241da2c8e40`.
Fresh `cp2a_execution` uses CP-2's actual risk reasoning, CP-1A context and
CP-1's numerical operands, with independently prepared checking expectations.
The selected later method is explicitly a static screen. Its existing pure
calculation functions are reused directly; no fabricated internal Fact records
or second financial extraction is required. The adapter preserves the actual
OCF-less-capex proxy, carrying-debt and issuer-EBITDA definitions. Newly calculated
ratios are not reconciled to absent reported ratios; this differs from the
runtime's nine-fact/report-ratio offering gate and is disclosed in instructions.
Shock sizes/watch levels are hypothetical analyst assumptions. CP-2B's older
event-risk/calendar scope is absent from this implementation and remains open.

The scoped source-availability check found only the five already retained TDG
filings in the inspected corpus/project locations. No underlying debt agreements,
dated market quotes, agency actions, definitive proxy or investor decision/outcome
history was located. These are future input needs, not analytical failures.
The user confirmed that actual decision/outcome history is not available locally.
CP-8 historical calibration therefore remains unproven; fabricated decisions or
gap-only output cannot stand in for it. Other supported module loops continue.

**Interim-source preparation only:** reused existing `convert_html`, `parse` and
`period_lines` functions on the four already retained TDG HTML filings. All raw
hashes match the import inventory. Located text and the existing parser's complete
context/unit/fact metadata are retained in the
[source-preparation manifest](runs/tdg-003/source-preparation/manifest.json).
Output hashes/counts rechecked: March quarter 336 contexts/1,141 inline facts;
June quarter 373/1,256; annual HTML 477/1,928; December quarter 241/974. No values
were inferred or source files changed. This prepares later CP-0/CP-1 work; it is
not analytical acceptance or quarterly-model proof.

Independent raw-HTML checks matched all 5,299 numeric facts' IDs, concepts,
context/unit references, lexemes, scale/sign/nil and format attributes, plus all
1,427 context identities/dates/dimensional flags. Nested inline EPS tags required
a stack in the ad hoc check; a first single-active-fact check missed an outer tag.
The source data and production parser were not changed to make that check pass.
One real limitation was found: the existing parser deliberately stores compound
units as empty tuples. The four USD/share units affect 22/22/78/13 facts, so its
unit metadata alone is insufficient for EPS. Exact original unit XML (all 20
unit definitions, including numerator/denominator) is retained in
[raw-unit-definitions.json](runs/tdg-003/source-preparation/raw-unit-definitions.json),
SHA-256 `43065ea24743ed74c91bf75155e4036b772c6c18b538bd4034ad7cfbf0398dc1`.
Every element matched the raw source verbatim. The preparation manifest flags
this limit; the original parser JSON remains unchanged. Future CP-0/CP-1 work
must use these original definitions rather than inferring from a unit ID.

## tdg-002 — CP-2A checked output

[Actual CP-2A answer](runs/tdg-002/CP-2A-attempt-1.md), fresh host-model subagent,
SHA-256 `6591fd403e775f7e1caefd7ac4de96b95a48df8b364e77a249b2c9eb0f79f199`.
This consumes CP-2's actual downside chain and preserves CP-1's five numerical
operands and CP-1A's limitations. Independent rational-arithmetic review passed
both stressed cases, four breakpoint fractions/order and eight crossing decisions.
No repair was required. The earliest chosen watch is 7x carrying debt / issuer
EBITDA As Defined at 14.8266% decline with interest fixed. It is an analyst watch,
not a covenant/default probability. The combined 20% earnings / 10% interest
stress crosses both chosen watches but not zero cash proxy or 1x interest cover.

[Inputs](runs/tdg-002/CP-2A-attempt-1-inputs.json):
`c4a6c348f3eae99dc4b3e2f3587a0f9aeb5a915aad196d74eda903ea630d9f49`;
[calculation transcript](runs/tdg-002/CP-2A-attempt-1-calculations.txt):
`15366f95e51120a8ab55d8580964aecdf8725763725bec0b9e6b7fcaca8e52d6`.
Direct reuse of existing pure functions, no provider or full runtime execution.
Reported-ratio reconciliation, future liquidity and CP-2B's additional calendar
scope remain absent. CP-2D subsequently opened this answer and used the combined
scenario and watch meanings in its liquidity reasoning; consumption was in the
current host context, not a new isolated API run.

## tdg-002 — Markdown to populated report

**Passed bounded delivery:** [five-section snapshot, attempt 2](deliverables/tdg-fy2024-snapshot-2/report.html)
uses the actual checked CP-1/CP-1A/CP-2 handoffs. The new narrow adapter calls the
existing `report_view.build` and `render.render` with shipped bindings. It copies
literal values and analysis, with citations to the exact model-handoff lines;
it creates no execution receipts, accepted runtime heads or replacement analysis.
Candidate preview, missing CP-MODEL publication, historical financial date and
subsequent-event distinction remain visible. The report is populated; the full
pathway, workbook/charts and CP-OS automation remain unproven.

All 159 mapped facts have exact original-line/hash citations. All six exported
files match [delivery.json](deliverables/tdg-fy2024-snapshot-2/delivery.json).
Report SHA-256: `324952b09a08ac87c66708c1ed4b9dc4d33dce7567279ab942ae1233d80a8aa6`.
Browser inspection verified five sections, expansion, alternate tabs and the
C65 evidence inspector (CP-2 line 35 and exact retained hash). Dates in the
transaction/timeline prose were observed after repair. Initial delivery is kept
in `deliverables/tdg-fy2024-snapshot` as the failed date-presentation attempt.

### Confidence review — handoff_delivery.py

Ranked doubts and outcomes:

1. **Loss of analytical meaning at rendering:** confirmed defect. Existing prose
   layout omits row labels; transaction dates lived only in those labels. Include
   every original column in prose, including Period/status. Concrete July 31,
   May 8 and October examples now pass through to visible report text.
2. **Table boundaries:** confirmed defects. Initial selection merged later tables;
   retaining only the first contiguous table fixed it. A second adversarial case
   showed section extraction removed blank boundaries; preserve blank lines.
   Malformed widths and duplicate required headings refuse before export.
3. **Provenance and missingness:** verified exact handoff hashes/line citations,
   negative `(165)`, proxy `1,880`, and `Not reconstructed`; no numeric conversion.
   The provenance names the model handoff, not a fresh issuer-source validation.
4. **Unsafe text:** script-closing input is retained in the embedded payload but
   escaped by the existing renderer; no literal executable script is emitted.
5. **Export ordering/races:** two writers produce one complete winner and one
   refusal. Existing destinations remain unchanged. Injected disk failure raises
   and leaves no completion record. Partial directories are retained for diagnosis;
   retries require a new destination. Completion requires a valid record and hashes.
6. **Contract/UI assumptions:** existing collapsed sections contain real content;
   treating collapse as emptiness was corrected. Focused tests, strict source
   typecheck and browser inspection pass. Selected heading names are deliberately
   bounded to these handoff contracts; other formats need a reviewed mapping.

Checks: `.venv/bin/pytest -q tests/test_handoff_delivery.py` — **8 passed**;
`.venv/bin/ruff check src/deploy_workflow/handoff_delivery.py tests/test_handoff_delivery.py`
— passed; `.venv/bin/mypy --follow-imports=silent src/deploy_workflow/handoff_delivery.py`
— passed. No unrelated production source or predecessor repository changed.

### Post-edit rewrite tournament

Inline review, capped to the two parsing functions `section` and `table`;
`mapped_module`, `prepare` and `deliver` were outside this pass's two-symbol cap
and covered by the confidence review. No Git/GitNexus metadata is present;
`rg` found callers only in this adapter and its focused test module. Backups and
full speed/memory/readability candidates are in the temporary review scratchpad.
All three candidates matched results/error types/messages on 2,000 section
inputs and 2,000 table inputs. Final diff inspected directly.

**Winner:** readability candidate for `section`; table incumbent holds.
- Exact heading/prefix comparisons express the finite Markdown contract directly.
- Blank lines, source line numbers, ambiguity refusals and return types remain intact.
- The table's simple loop is clearer than extra passes or iterator combinators.

Final selected function:

```python
def section(lines: list[str], title: str) -> list[tuple[int, str]]:
    headings = (f"## {title}", f"### {title}")
    matches = [i for i, line in enumerate(lines) if line in headings]
    if len(matches) != 1:
        raise ValueError(f"Expected one Markdown section: {title}")
    start = matches[0]
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    boundaries = tuple("#" * size + " " for size in range(1, level + 1))
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith(boundaries)),
        len(lines),
    )
    return [(i + 1, lines[i]) for i in range(start + 1, end)]
```

Verification: the focused pytest command and mypy command above pass after the
selected rewrite and the later one-line date mapping repair. Test-only additions
need no further rewrite tournament. No performance gain is claimed.

## tdg-002 — CP-2D historical liquidity review

[Instructions](runs/tdg-002/CP-2D-instructions.md), frozen before the answer:
`c86aacf03eb368a38e6af1be99bbe6993ed46eb8339824ba2213e0b701414c92`.
[Actual answer](runs/tdg-002/CP-2D-attempt-1.md):
`90a88b819e125d16407975929e421ee2151c3348f71c37fe4bb25d4f8334d880`.
Fresh current-host-model analysis, with the surrounding conversation available;
no new subagent, provider call or runtime receipt. CP-2A's combined stress and
watch meanings were actually consumed as liquidity questions, not converted
into a forecast. Five upstream hashes and all six common headings pass.

Existing `compose_bridge` reused directly with traced Markdown operands.
Independent integer/Fraction arithmetic verified historical cash 6,261, residual
0, six numeric debt-financing cash-flow components totaling 4,972, and the later
method's historical ex-debt movement (2,197). That last measure includes
acquisitions/distributions and is explicitly not recurring burn. Missing CFO
propagates a gap; missing funded draw, complete facility terms and minimum cash
leave liquidity/runway/funding results unavailable. The reported 843 borrowing
availability is retained independently, never reconstructed with 67 of letters
of credit as funded debt. Exact fiscal dates and October events remain distinct.

[Inputs](runs/tdg-002/CP-2D-attempt-1-inputs.json):
`eb51c126c4e434901a4db769d2e029ce2039736ca099256e9d82870fa8daafb6`;
[transcript](runs/tdg-002/CP-2D-attempt-1-calculations.txt):
`46487708ee3eb65a963dc849521b193af38771e43673702c7fa6e0ddc3c8f76b`.
Targeted PDF 133 inspection confirmed that the FY2025 93 maturity row is
**long-term debt excluding finance leases**, not all obligations. The answer
retains separate securitization/lease questions and avoids duplicate amortization.

**Result:** bounded historical calculations, instruction comparison and liquidity
reasoning passed; no complete forward CP-2D acceptance, numerical runway or
adequacy classification. No production-method code change was justified. Next:
validate retained quarterly filings through CP-0/CP-1 before earnings-delta or
updated liquidity work; then actual downstream consumption of this handoff.

## tdg-001 — 2026-11-04

**Small win:** CP-0 source readiness → CP-1 handoff intake, using one real TDG
annual PDF. **Result: passed for this bounded, same-session check.**

Execution was the current assistant with local file tools. The prompt files were
written before their respective outputs. The broader conversation remained in
context. No isolated model/API run, imported runtime invocation or paid provider
execution occurred. This is fresh model-authored work, not replayed historical
CP-0/CP-1 output; the source figures were read from the supplied PDF.

| Input / output | Retained artifact |
|---|---|
| CP-0 instructions | [prompts/CP-0.md](prompts/CP-0.md) |
| Source identity, method revisions and scope | [CP-0 handoff](runs/tdg-001/CP-0.md) |
| Fresh text extraction | [source-pages.jsonl](runs/tdg-001/source-pages.jsonl), pypdf 6.21.2, layout mode |
| Consumer instructions | [prompts/CP-1-intake.md](prompts/CP-1-intake.md) |
| Consumer's actual output | [CP-1 intake](runs/tdg-001/CP-1-intake.md) |

### Instructions versus observed output

| Required behavior | Observed evidence / check |
|---|---|
| Establish issuer, perimeter, authority, currency, periods and units from the source. | Located passages retained in CP-0. All 16 quoted excerpts in its evidence and page-map tables match the cited extracted page after whitespace normalization. Three primary statement renders were also inspected. |
| Distinguish extraction coverage from actual review. | 160 page records; 157 contain text. Empty pages 156/159/160 inspected visually. Page 156 contains a missed rotated non-GAAP table; 159/160 appear blank. CP-0 explicitly lists examined text, visual checks and unverified coverage. |
| Permit supported work while preserving material limitations. | Ready with limitations for annual primary statements. G1 restricts use of the missed supplemental table; G2 retains extraction/visual uncertainty; G3 limits version/current-filing claims. No financial dataset or calculation produced by CP-0. |
| Next module can use the handoff. | Consumer resolved source/text paths and the five statement page numbers from CP-0 Markdown, checked the source hash and opened those pages. All three gap IDs carried into the consumer output. |
| Preserve quantities and periods. | Six reported samples checked against PDF rows/rendered columns: sales 7,940 USD million; EPS 25.62 USD/share; average shares 57.8 million shares; cash 6,261 USD million; issued shares 61,904,833 shares; operating cash flow 2,045 USD million. Four duration samples use 2023-10-01 through 2024-09-30; cash and issued shares use the 2024-09-30 instant without a start date. |
| Retain usable communication. | Both outputs contain the six common headings; their relative links resolve. CP-0's 11 link occurrences checked. Prompt/source hashes remained unchanged. |

Checks used direct file/hash/link checks and assertions against source text plus
the retained page renders, without production financial calculations. An initial
ad hoc page-map check misidentified a prose table row as a page-map row; correcting
that check to select the four-column page-map entries resolved it. No module
answer or financial value was changed to make the check pass.

### Retained output identities

- CP-0: `b00dc9ded43bd41413143000b6e78799450f658667a85e4f3afcf54a9646a1f0`
- CP-1 intake: `c4448f016d0ea1015fb4b79985b0c2d3683d1fa55f3701777ec63d678f99fd23`
- Text extraction: `3ef306e99b330ddf535f096a1a507d9a8feadc559101e4b410d061dce67778db`

**Change justified by this run:** carry the actual extraction gap to the next
consumer with its affected scope. No further analytical-method or product-code
change is justified by these checks. README standardizes the small loop.

**Remaining boundary:** this is neither full CP-0 certification nor full CP-1
acceptance. No automation, complete pathway, delivery adapter or final deliverable
has been proven. Same-session consumption does not establish independent-context
model reliability. The raw API response/replay loop remains untested.

**Next small win:** complete CP-1 annual statement extraction and reconciliation
using this handoff; verify the existing OPEX helper against independent source
expectations; then have CP-1A consume the resulting full Markdown. Orchestration
and pathway work follows proven module links.


## 2026-11-04 — Local Issuer Library example

User-approved example: `examples/issuer-library/index.html`, built from a curated
catalogue of seven real run folders (three issuers), sixteen sourced metric
cells and three existing TDG delivery bundles. Twenty-six handoff/source pins
were checked. Separate fictional screening data demonstrates completeness
percentages; every real completion score remains null. Historical annual,
quarterly, guidance, agency and legal scopes remain distinct. All reports and
historical run files are read only. No CP-OS integration or analytical execution
is claimed. The working directory has no Git metadata; no commit was made.

**Confidence review — all new example code, ranked doubts.**

1. **Report issuer identity. CONFIRMED and fixed:** a valid OTHER-issuer bundle
   could be linked to a TDG catalogue row when only hashes were checked. A
   concrete adversarial bundle reproduced it. Admission now checks the verified
   `view.json` issuer; the regression disables the foreign report link.
2. **Evidence transport, missingness and dates. Verified within curated scope:**
   literal metrics were compared with the selected handoff rows; independent
   expectations preserve 5.96x/3.60x, the 1,880 cash proxy, Q1 cash 2,459 and
   S&P cover 8.2x. No TDG quarterly leverage is fabricated. Unit/period/basis
   labels and source excerpts survive. Null, zero, malformed numeric filters,
   unlike leverage bases and missing-last sorting have focused JS checks.
   The source-token guard is not a general semantic or period validator.
3. **Missing/corrupt files and paths. CONFIRMED and fixed:** malformed
   `delivery.json` with `files: []` raised AttributeError instead of disabling
   the link. Shape validation now handles it. Changed report bytes, changed
   source bytes/quotes, and project escapes are tested. Canonicalizing both
   endpoints repaired relative links across macOS `/var` symlinks. Identity is
   parsed from the same bytes whose hash passed, avoiding a second file read.
4. **Completeness and fictional/real separation. Verified:** real scores cannot
   be admitted as percentages; fictional checklist counts reproduce their
   scores and have no report links. Dataset switches reset filters; unassessed
   real scores cannot satisfy a numeric minimum. No score denotes credit quality.
5. **Navigation, injection and focus. Verified in DOM simulation:** all seven
   detail views link to existing local files; combined filters, reset, source
   disclosure, sorting, focus transfer and `/` search work. JSON escapes `<`;
   dynamic text uses textContent. No external runtime resources or fetch calls.
6. **Partial publication and caller impact. Verified/by design:** only the
   generated example page is atomically replaced. A failed source check happens
   before replacement. Runtime files are embedded; the page is a dated snapshot,
   not a file monitor. Source and delivery integrity reflects build time only.
7. **Visual/browser behavior. OPEN:** browser security policy rejected `file:`
   navigation. No alternative browser route was attempted. Layout, responsive
   rendering, real keyboard/screen-reader behavior and browser tab opening are
   not verified; jsdom supplies no layout or visual acceptance evidence.

**Rewrite tournament — no-argument post-edit, inline, no agents.** Two most
material symbols selected: `build.py:admit_catalog` and `logic.js:filterRuns`.
GitNexus has no index for this directory; `rg` traced callers to the builder,
`app.js:render`, and focused tests. Invariants: independent admitted snapshot,
source pins, exact missingness, issuer identity, separate scopes, conjunctive
filters, and unchanged output/exception contracts. Other presentation and
admission helpers were confidence-reviewed, not selected under the two-symbol cap.

Three full challengers per target were compared in temporary scratch files:
speed (cached predicates/tokens), memory (loop/shallow copies), readability
(staged filters/JSON copying). All passed the base focused suites. A further
nested-mutation probe disqualified the Python memory rewrite: it aliases input
metadata. Speed beat memory and staged filtering on simplicity/allocations;
the incumbent beat that challenger for this small catalogue.

**Winner: Incumbent holds.**
- One-pass filtering keeps the conditions together without intermediate arrays.
- Explicit deepcopy retains a fully independent snapshot; token caching adds
  state for a negligible repeated-excerpt workload.
- No caller-contract change or extra helper layer is justified.
Final code remains in `examples/issuer-library/build.py` and `logic.js`; no
challenger was applied. Final focused verification and caller checks passed.

**Verification:** `.venv/bin/python -m unittest discover -s
examples/issuer-library -p test_build.py` — 9 passed; `node --test
examples/issuer-library/test_logic.cjs` — 5 passed;
`ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node
--test examples/issuer-library/test_dom.cjs` — 9 passed. Ruff passed for both
Python files; the HTML rebuild passed and all three recorded delivery bundles
matched their hashes. jsdom 26.1.0 is a temporary test dependency only. This is
23 code/data/DOM tests, not a browser acceptance result.


### Issuer Library — deliverables design alignment (2026-11-04)

Updated the existing example at the user's request. It embeds the deliverables'
actual `src/deploy_vii/assets/tokens.css` and `app.css`, the same brand image and
all seven Red Hat faces; the OFL text is retained. Source revisions: tokens
`b7ab135a4bb33247117b65e915eec9d7ebd48fbfb6cdc61e42dbd13ab2bfbc9b`,
shared CSS `14aa4a822ef30a8827a0152b4b7470883967e558dff409aacea4dcc8c0a5cfd4`.
The library now uses the navy rail, white navigator, compact page/call headings,
square blocks, report status colours and Mono numeric columns. Library overrides
use 39 resolved design-token references with no private hex-colour palette.

**Confidence review, ranked doubts:** (1) shared CSS collisions and responsive
visibility: traced selector specificity for the three-column library, mobile
navigator and print rules; all nine DOM checks pass, but physical layout remains
unverified; (2) fonts, logo and offline embedding: verified seven embedded faces,
byte-identical logo, exact shared styles, retained license and no unresolved
placeholders; (3) DOM structure and navigation: balanced generated markup, one
main landmark, original IDs/labels intact and existing detail/filter/source tests
pass; (4) financial and status drift: catalogue and screening logic hashes match
pre-edit copies; `app.js` is byte-identical, and real scores remain unassessed.
No confirmed functional defect was found in this styling change. Browser visual
review remains open under the previously recorded local-file policy block.

Rewrite tournament skipped under its trivial-edit rule: CSS/template changes
and static font/asset/token wiring only; no new branching, parsing algorithm,
financial calculation or screening behavior. Rebuilt the self-contained HTML.
Validation: 9 Python + 5 screening + 9 DOM checks passed; Ruff passed. Existing
reports, sources and predecessor repositories were not modified.


## 2026-11-04 — Offline Issuer Library (isolated worktree)

Scope: approved read-only Windows local web app, automatic run/delivery discovery,
standard locations, bundled launcher and the existing deliverable design. All work
is in `apps/issuer-library` on `codex/offline-issuer-library`; no analytical module,
predecessor repository, historical run or original deliverable was changed. No
provider execution. Development baseline is snapshot commit `1a21c6c`.

Verification: 17 Go tests pass with `go test -race ./...`; 9 DOM simulations pass
with `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node
--test web/app.test.cjs`. Native and Windows-targeted `go vet ./...`, Python
packaging Ruff checks and `git diff --check` pass. `python3 packaging/build.py`
builds Windows amd64/arm64 GUI executables and a macOS arm64 development binary
with Go 1.26.4, CGO disabled, local toolchain and module downloads disabled.
`python3 packaging/smoke_test.py ../../artifacts/issuer-library/darwin-arm64/issuer-library`
passed compiled startup, all six retained report responses, repeated-launch reuse,
30-second automatic new-run discovery, settings persistence, quit and restart.
The latest build incorporates the additionally tested delivery-completeness gate
and first-run UI; lifecycle implementation is unchanged from the smoke run.

Retained-data scope: 10 run folders + 3 separately identified delivery revisions
= 13 records, six hash-checked report bundles. Seven original reviewed summaries
keep their source pins and numerical definitions (TDG leverage 5.96x, coverage
3.60x; real completeness stays null). Other folders are visible with unknown
screening metadata. New `library.json` manifests are supported; CP-OS is not
changed to generate these automatically. The library neither interprets arbitrary
financial prose nor treats a shared issuer as proof that two runs are related.
The shared report tokens/CSS are byte-identical; fonts and logo are bundled.

Confidence review — ranked doubts, root causes and disposition:
1. Historical links / concurrent file changes: CONFIRMED. An old URL could open
   newly published bytes after refresh. Added hash-pinned URLs and a failing-before,
   passing-after test. Responses send the bytes that were actually verified. A
   mutation during HTTP response construction is covered by a deterministic test.
2. Metadata trust / missing collections: CONFIRMED. An input `handoff_href` could
   survive when no handoff path existed, and omitted artifacts serialized as null.
   Derived links are rebuilt, collections normalized, source/identity/metric pins
   admitted before publication. Wrong-issuer mappings previously hid a valid
   independently discovered report; that report now gets its own revision row.
   Each confirmed issue was reproduced before its patch.
3. Completeness / financial precision: CONFIRMED. A producer checklist could claim
   delivery with no available direct bundle. Its score is now withheld on missing,
   changed or only-related delivery. Synthetic complete/partial/corrupt cases cover
   the boundary; these are transport checks, not analytical acceptance. Display
   and screening now preserve exact decimal strings (including adjacent decimals
   beyond binary floating precision), zero vs missing, periods, units and basis.
4. Filesystem/HTTP boundaries: verified scoped `os.Root` reads, relative path checks,
   symlink escape rejection, regular-file checks, explicit file allowlist, 64 MiB
   read ceiling and request-body limits. Host/Origin/cross-site checks and custom
   POST headers block browser cross-origin mutations. HTML is sandboxed without
   same-origin privileges or network access. These are local-desktop controls, not
   authentication for a remotely hosted multi-user service.
5. Refresh/settings/launch ordering: verified race tests, configuration precedence,
   policy lock, stale-workspace link rejection, atomic config/index replacement,
   repeated launch, automatic scan and clean shutdown/restart. The persisted index
   is rebuilt rather than trusted. Per-user data and canonical workspace files stay
   separate; IT policy is read on launch. Temporary smoke workspaces are synthetic.
6. Offline packaging and design: checked ZIP file lists and executable headers;
   archives contain only the executable, instructions, font licence and a clearly
   fictional schema example (the executable includes the public legacy metadata
   adapter). No source PDFs, reports, keys or runtime installers are included.
7. Still open: execution of the Windows launcher/Known Folder integration and real
   browser visual/keyboard acceptance. Host execution is macOS; Windows binaries
   are cross-compiled and vetted, unsigned pilot builds. Browser security previously
   rejected local-file navigation, and no alternate browser access was attempted.
   Enterprise signing/distribution and Windows acceptance remain rollout work.

Rewrite tournament — no-argument post-edit mode, inline, two-symbol cap:
- Targets: `verifyDelivery` (`discovery.go`) and `Application.serveFile` (`server.go`),
  the admission and serving boundary for real reports. Other nontrivial functions
  (run admission/discovery/checklist, settings/launcher, UI and exact comparisons)
  received the confidence review and focused tests above; generated/copied assets,
  docs and tests are excluded from tournament scope.
- Impact set: `discover -> verifyDelivery`; `ServeHTTP -> serveFile`, reached through
  initial discovery, scheduled/manual refresh, settings changes and HTTP file links.
  GitNexus context/impact returned repository-not-indexed; `rg` enumerated every
  definition/caller and the Go compiler plus full focused suite checked contracts.
- Full incumbent and all three complete challenger source files were retained in
  `/tmp/offline-issuer-library-tournament` before applying any candidate. A (speed)
  computes the response digest once; B (memory) streams a reopened verified file;
  C (readability) consolidates delivery failures in a closure.
- Bracket: A beats B because B fails `TestResponseUsesTheBytesThatWereVerified`:
  mutation between verification and streaming returns different bytes. A beats C
  because C adds closure state without improving I/O or the serving boundary.
  A beats the incumbent only for `serveFile`; **Incumbent holds** for `verifyDelivery`.
- **Winner: Snippet A**, replacing `Application.serveFile` in `server.go`.
  Justification: (1) preserves hash-pinned evidence and HTTP range semantics;
  (2) avoids hashing the same response twice; (3) retains the direct error paths,
  lock lifetime and byte snapshot instead of adding streaming/closure machinery.
- Verification: A and C pass `go test ./...`; B fails the adversarial mutation test.
  Final chosen combination passes `go test -race ./...`. Callers and signatures are
  unchanged and `go vet` passes. Original report and source bytes are never rewritten.
- Final code for the winning replacement:

```go
func (app *Application) serveFile(w http.ResponseWriter, r *http.Request) {
	name := strings.TrimPrefix(r.URL.Path, "/files/")
	app.mu.RLock()
	defer app.mu.RUnlock()
	hash, allowed := app.catalogue.Allowed[name]
	if !allowed || !localPath(name) {
		http.NotFound(w, r)
		return
	}
	root, err := os.OpenRoot(app.config.Workspace)
	if err != nil {
		http.Error(w, "Workspace unavailable", http.StatusGone)
		return
	}
	defer root.Close()
	raw, err := readFile(root, name)
	if err != nil {
		http.Error(w, "File unavailable; refresh the library", http.StatusGone)
		return
	}
	pinned := r.URL.Query().Get("sha256")
	actual := ""
	if hash != "" || pinned != "" {
		actual = digest(raw)
	}
	if hash != "" && actual != hash {
		http.Error(w, "File changed since verification; refresh the library", http.StatusConflict)
		return
	}
	if pinned != "" && actual != pinned {
		http.Error(w, "This link refers to a different evidence version; refresh the library", http.StatusConflict)
		return
	}
	ext := strings.ToLower(path.Ext(name))
	contentType := "text/plain; charset=utf-8"
	if ext == ".html" || ext == ".htm" {
		contentType = "text/html; charset=utf-8"
	}
	if ext == ".pdf" {
		contentType = "application/pdf"
	}
	if ext == ".xlsx" {
		contentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
		w.Header().Set("Content-Disposition", mime.FormatMediaType("attachment", map[string]string{"filename": path.Base(name)}))
	}
	// Reports retain their local scripts but receive an opaque sandboxed origin:
	// a report cannot read the library API, modify settings or access the network.
	w.Header().Set("Content-Security-Policy", "sandbox allow-scripts allow-downloads; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
	w.Header().Set("Content-Type", contentType)
	http.ServeContent(w, r, path.Base(name), time.Time{}, bytes.NewReader(raw))
}

```

Final package SHA-256 (ZIP):
- Windows amd64: `e84db551d9c03f2932a93996ed0a26149056914a73f3a5ad1773d3ba6095b38e`.
- Windows arm64: `1690e576318599ee2bd4ac894b514fc04c7bfd8ad57404b27d2aefe15e060ac1`.


### Issuer Library — consolidated report view (2026-11-04)

User requested one interface for the library and deliverables. Reports now open
inside the application with their existing renderer, sections and inspector.
A persistent toolbar returns to the filtered library, switches explicitly indexed
revisions and downloads the original HTML. Browser routes pin run, delivery and
file hash. Only the library or report shell is shown at a time; there is one
report navigation shell. Standalone report files remain byte-for-byte unchanged.
Windows amd64/arm64 packages and the local preview were rebuilt.

Confidence review — ranked doubts and findings:
1. Frame isolation vs functionality: verified the application's `frame-src 'self'`
   and the report's explicit local `frame-ancestors` opt-in. Sandbox retains scripts
   and downloads without same-origin privileges; null-origin/cross-site API requests
   remain forbidden. Ordinary file views still forbid framing. Original bytes and
   hash checks are unchanged for embedded view and attachment responses. Policy
   semantics checked against MDN's iframe sandbox and frame-ancestors documentation.
2. Lost filters, focus and report state: CONFIRMED skip-link regression, reproduced
   before patch. The library skip link previously closed the report. It now focuses
   the active report; returning after a refresh falls back to visible library focus
   if the original link was replaced. Library shortcuts don't focus hidden controls.
   Filters, scroll context, revision controls and report document identity are covered
   by DOM checks. A stable report is not reloaded when another record changes.
3. Stale/bookmarked/untrusted routes: verified catalogue-only URL resolution,
   exact hash matching, initial-load deep links, rejected arbitrary URLs, unavailable
   revisions and explicit downloads. A stale link cannot silently adopt new bytes.
4. Data/rendering/exports: simulated all six retained report renderers, navigated
   native Model/Evidence sections and opened fact inspectors. Live HTTP checks of
   all six embedded views and all six downloads matched their original file bytes.
   No analysis, deliverable reconstruction or historical-file edits occurred.
5. Packaging/regressions: 18 Go tests pass with `go test -race ./...`; 23 DOM checks
   pass with `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom
   node --test web/app.test.cjs web/report-renderer.test.cjs`. Native/Windows-targeted
   Go vet pass. Rebuilt executable resources match the final frontend. Preview is
   served at `http://127.0.0.1:53708`; the previous preview was already stopped.
   Actual browser framing/layout and Windows execution remain unverified: DOM
   simulation does not enforce browser CSP or render layout.

Post-edit rewrite tournament, inline, two targets:
- `ReportWorkspace.create.sync`, `web/report.js:23`, and `Application.serveFile`,
  `server.go:133`. Other changes are linking/copy, styling and header wiring;
  they received the confidence review above. GitNexus reported no index for this
  repository; `rg` plus the JS/Go suites checked the impact set instead.
- Impact set: report-link creation in library rows/details/history; initial catalogue
  acceptance and later polling; hashchange/back/revision events; ServeHTTP file
  dispatch; range, hash, embedding, download and byte-snapshot tests. Signatures,
  source identities, lock lifetime, original bytes and error contracts are invariants.
- Full candidate files and logs are in `/tmp/consolidated-library-tournament`.
  UI A caches too early and fails the new-revision-discovery test (selector becomes
  empty); UI B iterates directly, eliminating a filtered-array allocation; UI C uses
  filter/map/spread. B beats A on correctness and C on allocations/straight-line flow.
  B beats the incumbent by retaining the same simple loop with no temporary array.
- Server A consolidates duplicate disposition writes (passes); B streams a reopened
  file and fails the adversarial byte-snapshot mutation test; C uses a MIME switch
  (passes). A beats B; C offers no material benefit over A or the direct incumbent
  branches. **Incumbent holds** for serveFile: no verified improvement justifies
  replacing its explicit serving/export paths.
- **Winner: Snippet B** for `web/report.js:23` (sync).
  Justification: (1) preserves catalogue and hash validation; (2) keeps live revision
  updates without resetting the report document; (3) removes a temporary array while
  retaining an explicit, readable loop. Final chosen JS/Go combination passes the
  exact commands above, with caller contracts unchanged. Final winning function:

```javascript
    function sync() {
      const params = new URLSearchParams(window.location.hash.slice(1));
      const opening = params.has('report');
      const wasOpen = !$('report-workspace').hidden;
      if (opening && !wasOpen) {
        previousFocus = document.activeElement;
        scrollPosition = window.scrollY;
        if (!new URLSearchParams(previousHash.slice(1)).has('report')) libraryHash = previousHash || '#main';
      }
      $('library-workspace').hidden = opening;
      $('report-workspace').hidden = !opening;
      document.body.classList.toggle('report-open', opening);
      previousHash = window.location.hash;
      if (!opening) {
        $('report-frame').removeAttribute('src');
        currentSource = '';
        if (wasOpen) {
          window.scrollTo(0,scrollPosition);
          (previousFocus?.isConnected ? previousFocus : $('main')).focus({preventScroll:true});
        }
        return;
      }

      if (!wasOpen) $('report-back').focus();
      const data = catalogue();
      $('report-revision').replaceChildren();
      $('report-revision').disabled = true;
      $('report-title').textContent = 'Deliverable';
      $('report-context').textContent = '';
      if (!data) { unavailable('Loading the workspace…'); return; }
      const run = data.real.find(item => item.id === params.get('run'));
      const artifact = run?.artifacts.find(item => item.folder === params.get('report'));
      if (!run || !artifact?.available) { unavailable('This report is unavailable. Return to the library to refresh or choose another revision.'); return; }

      // The URL always comes from admitted catalogue metadata, never the route.
      const source = new URL(artifact.href,window.location.href);
      const pin = params.get('sha256');
      if (source.origin !== window.location.origin || !source.pathname.startsWith('/files/deliverables/') || !pin || source.searchParams.get('sha256') !== pin) {
        unavailable('This link refers to a different report version. Return to the library and open the current revision.'); return;
      }
      $('report-title').textContent = run.name;
      $('report-context').textContent = `${run.issuer} · ${run.period} · ${artifact.relationship === 'related' ? 'Related report · ' : ''}${artifact.state}`;
      for (const item of run.artifacts) {
        if (!item.available) continue;
        const option = document.createElement('option');
        option.value = href(run,item); option.textContent = `${item.label} · ${item.state}`;
        option.selected = item.folder === artifact.folder;
        $('report-revision').append(option);
      }
      $('report-revision').disabled = $('report-revision').options.length < 2;
      const download = new URL(source);download.searchParams.set('download','1');
      $('report-export').href = download.pathname + download.search;
      $('report-export').download = artifact.folder.split('/').at(-1) + '.html';
      $('report-export').hidden = false;
      source.searchParams.set('embedded','1');
      const nextSource = source.pathname + source.search;
      $('report-frame').title = `${run.name} — ${artifact.label}`;
      $('report-frame').hidden = false;
      $('report-status').hidden = true;
      // Polling must not reset the report's active section or evidence inspector.
      if (currentSource !== nextSource) { currentSource = nextSource; $('report-frame').src = nextSource; }
    }

```

Updated ZIP SHA-256:
- Windows amd64: `5912cc98911a851a959f58d2bb489b4e35b34f4dd4703791597c667018416e6e`.
- Windows arm64: `9e4fb0763f281ac5e912f459bb5caf56dda4dd4321aa79a339b0db348832a077`.


## 2026-11-04 — New run in the offline issuer library

Built in the isolated `codex/offline-issuer-library` worktree. The app embeds the
existing context form, validates uploads through the existing context/input
validators, shows module order and the USD ceiling, and requires a separate explicit
Start. Only Start can create the scoped live authorization and invoke CP-OS's existing
runner. No provider calls were made in this build or its tests.

The scoped Markdown transport retains typed analytical modules literally, supplies
only currently bound upstream handoffs to prompts, and constructs delivery from those
handoffs through existing renderer/bindings and applicable Model exports. A terminal
receipt with refusals or missing module heads is stopped, not complete. New business
folders are `intake/`, `runs/`, `deliverables/` under the selected workspace; Windows
uses its standard Known Folder locations for configuration and user state. The full
Windows ZIP includes the interpreter, pinned wheels and engine; no installation-time
or launch-time download is needed. External CP-DR retrieval is explicitly unavailable
in this upload launcher. Existing analytical methods and prices were not changed.

### Confidence review — New run and delivery boundary

Least confident about (ranked):
1. Paid admission, duplicate clicks and changing inputs — highest blast radius.
   Investigated → Go's serialized admission plus exclusive persistent `start.claim`;
   Python recomputes the job/context/source/code fingerprint; the runner checks actual
   validated original hashes before staging. Concurrent requests admit one worker.
   Verdict → fine under the local per-user process contract; stale/corrupt review,
   missing credentials and changed hashes are refused. No automatic paid restart.
2. Publication corruption and loss of the original run audit.
   Investigated → a copy could change after source verification. A concrete corruption
   hook reproduced publication of changed bytes. Moving instead of copying also loses
   the audit (tournament regression reproduced both failures).
   Verdict → CONFIRMED bug, patched. Verify the copied manifest, exact file set and
   copied hashes before atomic directory rename; preserve the run's original delivery.
3. Empty enterprise workspace on first use.
   Investigated → compiled HTTP review failed with “runs is not an existing directory”.
   Verdict → CONFIRMED bug, patched. Prepare the standard parent folders through Go's
   workspace-root handle. Repeat compiled review succeeds with zero execution folders.
4. Windows encoding, CRLF, binary logs and POSIX-only I/O.
   Investigated → default text encoding could misread UTF-8 JSON paths on Windows;
   workers now explicitly use `-X utf8`. Ruling lines trim CR; file logs/staging use
   binary mode; portable locking, positioned reads and directory flushes replace
   unsupported operations. Reverting the UTF-8 setting fails its focused guard test.
   Verdict → portability fixes verified on macOS, both Windows targets compile/vet.
   Native Windows behavior remains OPEN; bundled `Smoke-test.ps1` covers packaged
   imports, an accented workspace path, competing locks and offline review.
5. Hidden UI errors, opaque-frame communication and report navigation.
   Investigated → browser exercised the actual wizard, parent message bridge, source
   upload, review, low-budget rejection, missing-key Start disablement, report opening,
   C65 evidence inspection, revision switching and return preserving search. Browser
   console contained no warnings/errors. DOM tests reject messages from other windows.
   Verdict → fine for the tested browser/viewport. Saved-context chooser automation
   timed out inside the opaque iframe; that import picker was not accepted as tested.
   Context entered through the wizard and the outer source picker both worked.
6. Exact values, missing versus zero, source lineage and a false completion label.
   Investigated → canonical Markdown payload is parsed and compared to retained module
   heads; a synthetic literal-transport test preserves `0.00`, currency, period and
   source references, detects handoff mutation, and exercises downstream consumption.
   Full-plan coverage/refusal checks gate completion. Output remains candidate/partial.
   Verdict → verified transport scope only. No new live analytical success is claimed.
7. A failed worker offering a nonexistent library run.
   Investigated → status omitted `run_available`, and the frontend treated omission as
   available. The API now returns the actual directory state; the false/true cases pass.
   Verdict → CONFIRMED bug, patched.
8. Credentials, historical files and the package boundary.
   Investigated → providers receive keys only from process environment. Worker output
   is discarded except structured redacted status. Upload names never become paths.
   Report origin/sandbox, pinned-byte and upload admission tests pass. ZIP inspection
   verifies parity with source and excludes intake/runs/deliverables/credential folders.
   Verdict → fine within this local, single-user application contract. Predecessor
   repositories and historical run/delivery directories were not edited.

Fixed: verified-copy publication; first-use standard folders; explicit UTF-8 and
CRLF/binary portability; accurate run availability. Verified fine: once-only Start,
stale-input refusal, offline review, literal transport, source-backed report serving.
By-design: credentials/network required only for live execution; unassessed screening
metadata stays unknown; stopped workflows expose gaps. Still open: native Windows
acceptance, iframe saved-context picker acceptance, and any paid/live analytical run.

### Verification actually performed

- `cd apps/issuer-library && go test -race ./... && go vet ./...`: PASS, 26 Go tests.
  `GOOS=windows GOARCH=amd64 go vet ./...` and `GOOS=windows GOARCH=arm64 go vet ./...`:
  PASS. Both native PE architectures were inspected, including bundled Python.
- `PYTHONPATH=src:tests:tests/prompts /Users/ericguei/Documents/final-workflow/.venv/bin/python -m pytest tests/test_cpos_app.py tests/product/test_context.py tests/product/test_context_prepare.py tests/product/test_context_pack.py tests/model/test_record.py tests/model/test_adapter.py -q`:
  **381 passed in 3.46s**. CP-OS tests use synthetic seams, never a provider.
- `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node --test web/app.test.cjs web/report-renderer.test.cjs web/new-run.test.cjs` from the app:
  **27 passed** (17 library/report interaction, 6 retained renderer, 4 New run).
- Ruff on every changed Python runtime module and `tests/test_cpos_app.py`: PASS.
  `git diff --check`: PASS.
- `python3 packaging/build.py` from the app: PASS; offline executable build, pinned
  runtime/dependency download verification and complete Windows ZIPs rebuilt.
- `ISSUER_LIBRARY_PYTHON=/Users/ericguei/Documents/final-workflow/.venv/bin/python python3 apps/issuer-library/packaging/smoke_test.py artifacts/issuer-library/darwin-arm64/issuer-library`:
  PASS — compiled launch, six retained reports, repeat launch, accented workspace,
  existing CP-OS context/source/budget review, missing-provider Start refusal before
  claim, discovery, settings persistence, shutdown/restart. No execution was created
  by review. Provider keys are removed from the test process environment.
- Actual in-app browser at `http://127.0.0.1:53708`: the interaction cases above passed.
  Synthetic uploads were isolated under `/tmp/issuer-library-browser-check/workspace`;
  no Start was clicked. Restored the real worktree workspace and its 13 records with
  no discovery issues. Review screenshot: `artifacts/issuer-library/new-run-review.png`.
- Broader runner/input/prompt subset earlier: **188 passed, 2 failed, 1 skipped**.
  Both failures reproduced against unchanged source in `/tmp/cpos-pre-change/src`:
  `test_a_money_stop_on_the_call_that_ends_the_walk_stops_the_resume[unknown]` expects
  an UnknownCharge despite current pricing producing OverrunStop;
  `test_a_live_run_resumed_offline_is_refused` uses a $5 ceiling below the current
  $6.724560 reservation floor and stops before its injected kill. Pricing and these
  historical expectations were not changed to hide the failures.
  `tests/test_owner_rendering.py` cannot collect because the imported project lacks
  `docs/OWNER-RENDERING-LEASE.md`; no new lease was invented. New transport/delivery
  tests explicitly cover this app's boundary, not the uncollectable legacy suite.

### Rewrite tournament — no-argument post-edit mode, inline

Read changed symbols and invariants; chose the two most material symbols per pass:
`Application.startRun` (`apps/issuer-library/jobs.go:293`) and Python `start`
(`apps/issuer-library/engine/bridge.py:160`). The other changed functions
(review/upload, frontend create, transport/delivery and platform helpers) were outside
this capped pass. No agents were used. GitNexus context/impact was attempted but the
repository is not indexed; `rg` references plus Go compilation/tests and focused Python
callers supplied the impact set: ServeHTTP/serveRunAPI, browser explicit Start/status,
Engine.command, bridge main, review/read_job, run_pathway, receipt verifier and export.
Signatures, errors, one-shot side effects, ceiling/source approval, audit preservation
and publication/status ordering must be unchanged.

Full incumbents, three full alternatives and outputs are retained in the scratch
`/tmp/cpos-start-tournament`. A-speed drops revalidation/provider admission and fails
both ecosystems' guards; B-memory streams JSON allowing trailing content and moves the
audit delivery, failing corrupt-review and audit-preservation tests. Both are
disqualified for changed side effects/contracts. C-readability names the Go guard's
conditions and extracts Python publication to a helper; both focused suites pass, but
it provides no complexity/cost improvement over the ordered gates in one place.
Bracket: neither A nor B qualifies; C survives the correctness bracket; the Incumbent
beats C on explicit sequencing with no extra helper traversal.

**Winner: Incumbent holds** for both Start boundaries; no replacement applied.
Justification:
- Keeps admission, verification, launch and settlement in their explicit required order.
- Preserves every caller contract and retained audit while rejecting the adversarial cases.
- Splitting a single-use publication block adds indirection without a measured benefit.

Verification: each alternative ran `cd apps/issuer-library && go test ./...`, then
`PYTHONPATH=src:tests /Users/ericguei/Documents/final-workflow/.venv/bin/python -m pytest tests/test_cpos_app.py -q`.
A: Go FAIL / Python 1 failed, 9 passed. B: Go FAIL / Python 2 failed, 8 passed.
C: Go PASS / Python 10 passed. Restored incumbents; final `go test -race ./...` PASS
and final Python focused run above PASS. Reviewed the actual diff and all impact-set
interfaces. Concrete invariant: two concurrent confirmed Start requests produce one
synthetic worker line; a source/budget change is refused before real execution.

<details><summary>Final incumbent code (both reviewed Start boundaries)</summary>

```text
func (app *Application) startRun(w http.ResponseWriter, r *http.Request) {
	var request struct {
		ID       string `json:"id"`
		ReviewID string `json:"review_id"`
		Confirm  bool   `json:"confirm"`
	}
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 8192))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&request); err != nil || !jobID.MatchString(request.ID) || !request.Confirm {
		http.Error(w, "Explicit confirmation of a reviewed run is required", 400)
		return
	}
	app.mu.Lock()
	defer app.mu.Unlock()
	if len(app.activeJobs) > 0 {
		http.Error(w, "A CP-OS run is already active; wait for it to finish", 409)
		return
	}
	folder := filepath.Join(app.config.Workspace, "intake", request.ID)
	raw, err := os.ReadFile(filepath.Join(folder, "review.json"))
	if err != nil {
		http.Error(w, "Review this run before starting", 409)
		return
	}
	var review struct {
		ReviewID      string `json:"review_id"`
		ProviderReady bool   `json:"provider_ready"`
	}
	if json.Unmarshal(raw, &review) != nil || review.ReviewID != request.ReviewID || !review.ProviderReady {
		http.Error(w, "Review is invalid or the provider is not configured", 409)
		return
	}
	claim, err := os.OpenFile(filepath.Join(folder, "start.claim"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		if !os.IsExist(err) {
			http.Error(w, "Could not retain the start authorisation", 500)
			return
		}
		http.Error(w, "This run has already been started; no additional call was made", 409)
		return
	}
	claim.Close()
	command := app.engine.command(context.Background(), "start", folder)
	// Discard command output; structured, redacted status is the only browser contract.
	command.Stdout = io.Discard
	if err = saveJSON(filepath.Join(folder, "status.json"), JobStatus{State: "running", Message: "CP-OS is validating the reviewed inputs and starting the selected workflow.", ID: request.ID}); err != nil {
		http.Error(w, "Could not retain start state", 500)
		return
	}
	if err = command.Start(); err != nil {
		_ = saveJSON(filepath.Join(folder, "status.json"), JobStatus{State: "failed", Message: "CP-OS runtime could not start."})
		http.Error(w, "CP-OS runtime could not start", 503)
		return
	}
	if app.activeJobs == nil {
		app.activeJobs = map[string]bool{}
	}
	app.activeJobs[request.ID] = true
	go func() {
		_ = command.Wait()
		raw, _ := os.ReadFile(filepath.Join(folder, "status.json"))
		var status JobStatus
		_ = json.Unmarshal(raw, &status)
		if status.State == "running" {
			_ = saveJSON(filepath.Join(folder, "status.json"), JobStatus{State: "interrupted", Message: "The worker exited without a final result. Retained evidence remains available; no automatic paid retry was made."})
		}
		app.mu.Lock()
		delete(app.activeJobs, request.ID)
		app.refreshLocked()
		app.mu.Unlock()
	}()
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusAccepted)
	jsonResponse(w, JobStatus{State: "running", ID: request.ID, Message: "Run started."})
}

def start(directory: Path) -> None:
    from deploy_workflow.cpos_handoffs import transport

    approved = json.loads((directory / "review.json").read_text())
    current = review(directory)
    if approved["review_id"] != current["review_id"]:
        raise ValueError("review is stale; review the inputs again before starting")
    if not current["provider_ready"]:
        raise ValueError("the selected provider is not configured in the launching environment")
    job, workspace, model, context, sources = read_job(directory)
    # This receipt is created only after the web API's explicit, one-shot Start.
    ruling = directory / "start-authorization.md"
    with ruling.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(
            f"lifts: live-provider-pause\nby: user\ndate: {date.today()}\nconfigs: {model.config_id}\nreview: {current['review_id']}\n"
        )
    adapter = LiveAdapter(model, ruling, rulings_root=directory)
    with transport():
        result = run_pathway(
            case_id=job["id"],
            run_id=job["id"],
            sources=sources,
            context=directory / "context.json",
            pathway=context.run.pathway,
            model=model,
            adapter=adapter,
            cap_usd=Decimal(job["cap_usd"]),
            run_dir=workspace / "runs" / job["id"],
            approved_inputs=approved["inputs_sha256"],
        )
    if result.outcome != "settled":
        write_json(
            directory / "status.json",
            {
                "state": "stopped",
                "message": Redactor.from_environ(os.environ).text(
                    result.stopped_reason or "Workflow stopped."
                ),
                "spent_usd": str(result.spent_usd),
            },
        )
        return
    from deploy_vii.execution import Execution
    from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt

    receipt = OwnerRunReceipt.model_validate_json((result.run_dir / "owner-run.json").read_bytes())
    publication = result.run_dir / "publication"
    verify_owner_run_receipt(
        Execution(result.run_dir / "execution"),
        receipt,
        publication_directory=publication if publication.exists() else None,
    )
    completed = complete_receipt(receipt)
    delivered = result.run_dir / "delivery"
    manifest = json.loads((delivered / "delivery.json").read_text())
    for name, expected in manifest["files"].items():
        if (
            Path(name).name != name
            or hashlib.sha256((delivered / name).read_bytes()).hexdigest() != expected
        ):
            raise ValueError("delivery verification failed")
    target = workspace / "deliverables" / job["id"]
    target.parent.mkdir(exist_ok=True)
    if target.exists():
        raise ValueError("delivery destination already exists")
    staging = Path(tempfile.mkdtemp(prefix=".cpos-", dir=target.parent))
    try:
        for file in delivered.iterdir():
            if file.is_symlink() or not file.is_file():
                raise ValueError("unexpected delivery file")
            shutil.copyfile(file, staging / file.name)
        if (
            json.loads((staging / "delivery.json").read_text()) != manifest
            or {file.name for file in staging.iterdir()}
            != set(manifest["files"]) | {"delivery.json"}
            or any(
                hashlib.sha256((staging / name).read_bytes()).hexdigest() != expected
                for name, expected in manifest["files"].items()
            )
        ):
            raise ValueError("copied delivery failed verification")
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    write_json(
        directory / "status.json",
        {
            "state": "complete" if completed else "stopped",
            "message": "Requested runtime finished; handoffs and delivery hashes verified."
            if completed
            else "Workflow ended with module refusals or incomplete outputs. The report retains its explicit gaps; this is not completion.",
            "spent_usd": str(result.spent_usd),
            "run_id": job["id"],
        },
    )
```

</details>

Final archive SHA-256 (pilot builds, unsigned; native Windows acceptance pending):
- amd64: `98eba12c4a433840c226bd6da77cda41602e66aad5d875e7331219c58c07a3c9`.
- arm64: `38fc4c48957e1a1d50ab85b60972d3dd6f21d77154a82fe643c504eb2996836c`.


## 2026-11-04 — Deploy VII library refinement after the Astra critique

User chose all critique fixes and pinned the Deploy VII design system. Read the
current critique snapshot `2026-11-04T19-06-16Z__apps-issuer-library-web-index-html.md`;
worked in the existing isolated worktree. Canonical Deploy VII tokens, shared CSS,
fonts, logo, analytical values and historical documents remain unchanged. No model
or provider was called. No extra analytical/orchestration layer was added.

Changes: one required-context page using the existing form/build/fill/validators,
optional disclosures, one continuation action, field-directed errors and stage focus;
accurate unidentified-record grouping/counts; compact task header and laptop table
with pinned issuer/report columns; contextual report evidence and laptop reading
layout; narrative citation typography; scope/budget/readiness first in approval,
with authoritative registry names and disclosed source hashes/pricing. Separate
unlinked deliveries are explicitly labelled; lineage is never inferred. Help/upload
instructions and embedded data-font CSP were corrected. The new embedded report
presentation is applied only after verifying original report hashes, and never to
HTML downloads. Original files, unembedded responses and exports retain exact bytes.

### Confidence review — ranked doubts and investigation

1. Original report integrity and sandbox isolation (largest impact).
   Investigated → reportPresentation is called only for admitted hashed deliveries,
   embedded=1 and download!=1, after source/pin verification. Tests remove the scoped
   inserted block and compare every original byte; also check retained file identity,
   exact exported bytes with combined flags, original storage non-aliasing, fragments,
   mixed-case HTML, source mutation/pins and opaque/network-disabled CSP.
   Verdict → fine for this boundary. No analytical values are recalculated.
2. Required/optional context drift from the existing form.
   Investigated → the adapter only moves existing DOM controls and changes presentation;
   build(), fill(), shape checks, conditional requirements and source validation stay
   authoritative. Actual generated-form tests preserve Unicode/currency, validate
   earnings periods and load an existing saved context through FileReader.
   CONFIRMED bug → native valid-file loading targeted its standalone Review step,
   which this embedded mode hides. The regression first failed with sec11 focus;
   gotoStep now returns to the visible issuer context and the test passes.
3. Keyboard and asynchronous stage restoration.
   Investigated → source-window validation bounds height/readiness messages; stage
   transitions focus headings and returning restores prior library focus. A concrete
   leave-and-return-to-Sources test initially focused the hidden Context heading.
   CONFIRMED bug → reentry now focuses the current visible stage; regression passes.
   Browser verified missing-issuer focus/aria-invalid and Sources heading focus.
4. Context auto-height feedback and nested scrolling.
   Investigated → body margins collapsed outside its measured bounds: browser showed
   body 1632px but document 1656px. CONFIRMED bug → body flow-root contains margins.
   Final constrained-width check: body 1832.52px, document 1833px, matching the rounded
   height sent to the parent. Height messages are bounded, finite and source-checked.
5. Missing issuer identity being turned into a claimed relationship.
   Investigated → old UI grouped the backend Unclassified sentinel under its first
   filename and counted it as an issuer. The independent critique reproduced it.
   CONFIRMED bug → use an explicit unidentified bucket, separate counts and predicate.
   Live result: 13 records, 3 identified issuers, 3 unidentified records; bucket yields
   exactly 3 rows and zero identified issuers. Established issuer metadata is unchanged.
6. Report evidence focus, close/reopen and available reading width.
   Investigated → native renderer/citations remain active. Adapter observes rendered
   evidence, opens on selection, restores the triggering control on close and keeps
   view changes from reopening dismissed evidence. DOM/browser tests cover C65,
   native Close inspector, Escape/close mechanics and report routing/revisions/back.
   Verdict → fine for tested paths. At 1366px the idle reading grid is 56px + 1310px;
   the inspector occupies no idle space. At laptop widths evidence opens contextually.
7. Approval comprehension without weakening spending control.
   Investigated → labels come from existing registry metadata; cap/reservation strings
   retain exact values. Hashes, limitations and price date stay in disclosures.
   Existing one-shot Start, review fingerprint and provider guard are unchanged.
   Browser review with synthetic inputs rendered real metadata and stayed disabled
   without credentials even after the approval checkbox was checked. No Start clicked.
   Verdict → fine for offline review and synthetic Start seam; no live success claimed.
8. Design-system drift, font/network packaging and responsive breakpoints.
   Investigated → canonical tokens and app.css compare byte-for-byte to their bundled
   copies. All assets remain local. Generated form now permits its packaged data fonts
   in both CSP policies; browser computed family is Red Hat Text with no console
   warnings/errors. Scope-appropriate sizes use the existing type roles.
   Verdict → tested at 680px reflow, 1024x768, 1280x720, 1366x768 and 1600x1000.
   First row moved from the critique's ~624px to 420px at 1280x720, with 4 full rows
   visible. At 1600px document width equals viewport width. Browser font-set iteration
   was unavailable in the read-only automation API, so no per-face load claim is made.

Fixed: misleading identity grouping, competing context progression, error/return/load
focus, collapsed-margin iframe overflow, laptop space allocation, approval hierarchy.
Verified fine: literal context transport, existing approval gates, original report
bytes/exports, sandbox isolation, real citations, conditional validation and packaging.
By-design: unknown lineage stays separate; compact Deploy VII status/navigation cues
remain. Still open: native Windows execution, actual browser saved-file picker inside
the opaque frame, full NVDA/200% browser zoom/print acceptance, and paid model execution.
Saved-context FileReader/validation/focus was tested in a DOM simulation, not via a
native file-picker acceptance run. These limits do not imply observed production bugs.

### Verification

- `cd apps/issuer-library && go test -race ./... && go vet ./...`: PASS, 27 tests.
  Both `GOOS=windows GOARCH=amd64 go vet ./...` and arm64 equivalent: PASS.
- `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node --test apps/issuer-library/web/app.test.cjs apps/issuer-library/web/new-run.test.cjs apps/issuer-library/web/context-embed.test.cjs apps/issuer-library/web/report-renderer.test.cjs` from repository root:
  **35 passed** (including unchanged retained renderers and new presentation/form paths).
- `PYTHONPATH=src:tests /Users/ericguei/Documents/final-workflow/.venv/bin/python -m pytest tests/test_cpos_app.py -q`: **10 passed**. Ruff bridge check: PASS.
- `ISSUER_LIBRARY_PYTHON=/Users/ericguei/Documents/final-workflow/.venv/bin/python python3 apps/issuer-library/packaging/smoke_test.py artifacts/issuer-library/darwin-arm64/issuer-library`:
  PASS — compiled launch/reopen, retained reports, accented workspace, offline real
  context/source/budget validation, unavailable-provider Start gate, discovery,
  persistence, shutdown/restart. The final later changes were embedded UI/focus only.
- `python3 packaging/build.py` from app: PASS. Final amd64/arm64 ZIP integrity and
  both launcher/Python PE architectures checked; bridge/source parity checked;
  no issuer runs, uploads or credentials enter packages. `git diff --check`: PASS.
- Browser: empty-context field recovery; required context and Sources focus; upload
  and offline review using a clearly synthetic issuer/source in a temporary workspace;
  unchecked/checked approval still cannot Start without credentials; real report C65
  opens/closes with focus restoration; revision 2→1 and Back; unknown bucket; 1024px
  Browse issuers; wide layout. Real workspace restored with 13 records. No providers.
  Existing user preview remains running at http://127.0.0.1:53708/. Viewport override
  reset. Screenshots: artifacts/issuer-library/library-polished.png and
  artifacts/issuer-library/new-run-polished.png. No historical directory mutated.
- One final detector pass (before margin containment and load-focus correction):
  19 findings: cramped-padding 6, monotonous-spacing 2, undersized-ui-text 1,
  tiny-text 6, side-tab 4. Section padding findings misidentify top-only separators
  within a shared 12px parent gutter as side boundaries. Other retained small labels,
  operational selection edges and spacing are incumbent Deploy VII role choices.
  Primary table labels/periods/bases now use the 12px table role. No unexplained
  new visual findings remain in the inspected path. This is not a WCAG certification.

### Rewrite tournament — post-edit mode, inline, two material symbols

Targets read: `server.go:213` reportPresentation and `context-embed.js:38` renderSteps.
Skipped under this pass's two-symbol cap: NewRun.create/stage/review composition,
issuer grouping, evidence observer, gotoStep and mechanical assets/docs/tests.
GitNexus context and upstream impact were attempted; returned only other indexed
repositories. Used rg and compiler/tests as the caller-contract oracle instead.
Impact: admitted serveFile embedding, exports/ranges/CSP and Go byte/pin tests;
original form update→renderSteps, conditional sequences, wrappers, ready messages,
saved-file load, parent height and new-run validation. Invariants: no original-byte
mutation/aliasing; same insertion bytes and document endings; no export transformation;
all original input/conditional semantics; hidden review section; finite source-checked
messages; no provider side effects. Full candidates/logs retained under
`/tmp/issuer-library-polish-tournament`.

Go A-speed preallocates output and manually copies offsets; B-memory sizes chunks
then appends them; C-readability uses standard bytes.Join for the same single output
allocation. Each passed `go test ./...`. JS A uses a Set of section numbers, B uses
for-of, C extracts a displaySection helper; each passed actual generated-form tests
via `python3 packaging/sync_assets.py` then `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node --test web/context-embed.test.cjs`.
Bracket: B beats A by avoiding manual offsets; C beats B and the incumbent through
fewer staging operations and clearer boundaries. JS variants show no measured benefit;
incumbent holds. Final complete app/form suites above pass after chosen code applied.

**Winner: Go Snippet C**, reportPresentation at server.go:213; **JS Incumbent holds**.
Justification:
- bytes.Join makes the exact immutable insertion pieces explicit with one output buffer.
- Removes hand-managed lengths/copy offsets and the intermediate addition buffer.
- Preserves every caller contract, export and original-storage invariant in real tests.

Final selected code:
```text
func reportPresentation(original []byte) []byte {
	style, _ := resources.ReadFile("web/report-adapter.css")
	script, _ := resources.ReadFile("web/report-adapter.js")
	position := bytes.LastIndex(bytes.ToLower(original), []byte("</body>"))
	if position < 0 {
		position = len(original)
	}
	return bytes.Join([][]byte{original[:position], []byte("<style data-library-presentation>"), style,
		[]byte("</style><script data-library-presentation>"), script, []byte("</script>"), original[position:]}, nil)
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
```

Final Windows archive SHA-256 (unsigned pilot packages; native acceptance pending):
- amd64: `9a1944f506d52370858fdb314229cc021f080062e3b6d58ddfc621dff1c75f28`.
- arm64: `7c79251407cb896f536ead1bf2a5f17e81aa4e1800adc90d93a1f6b371058606`.

## 2026-11-04 — four Deploy VII critique fixes and symbol-only branding

Scope: the four Priority Issues in critique snapshot
`2026-11-04T20-54-29Z__apps-issuer-library-web-index-html.md`.
User requested no product/company name, only the supplied STT.D.svg symbol.
The source SVG was inspected: one path and a white-fill style, no scripts,
external references or instructions. The symbol is copied byte-for-byte into
current renderer assets and the generated offline app assets. No predecessor
repository, retained report or historical run directory was modified.

- Report adapter now follows the native 1350px navigator/search breakpoint.
  Paired 5:7 blocks remain when they fit; prose and narrative figures cap at 80ch.
- Embedded context guidance names Deal terms, Quotes and Valuation, preserving
  all original analytical qualifications and validation. The numbered standalone
  template remains unchanged.
- Metric metadata can explicitly declare cited/calculated/synthetic provenance.
  Missing classification stays missing; the library shows **Not classified**
  beside Source in screening and details. No legacy classifications inferred.
- Library, embedded reports and newly generated standalone HTML use only the
  supplied symbol. Retained original HTML exports preserve their audit bytes.

### Confidence review — this change

Least confident about (ranked):
1. **Responsive CSS and native search could still disagree.** Traced native
   focusSearch/showNavigator and inherited drawer rules against adapter CSS.
   Browser checks at 1280, 1350, 1351, 1366, 1440 and 1500px show a 236px
   navigator, fixed through 1350 and sticky from 1351, Search and / focusing a
   visible field, no document overflow. Prose max computes to 712.8px (80ch).
   Verdict: verified fine; the conflicting 1500px navigation override was fixed.
2. **Classification might be inferred or accepted without source verification.**
   Traced admitRun through finite exact string validation and hash/line/quote
   verification, then publication of sources; the new enum never supplies a
   default. Go cases retain exact zero with each allowed kind, leave omitted
   provenance empty, reject unknown/C1. DOM cases verify all three canonical SVG
   marks and unknown-without-a-mark, without a Start request. Verdict: fine.
3. **Source links on a different row could focus the wrong run or lose values.**
   Traced metricCell -> metricSource -> selectRun/renderDetails -> showSource;
   DOM regression clicks a different row and checks expanded sources and exact
   focused source ID. Existing exact decimal sorting/filter tests pass. Browser
   geometry at 1280 confirms Source and Not classified share one line within
   their cells. Verdict: fine. Initial wrapping was corrected with a compact
   Source label and the DS label role, without shrinking the existing type scale.
4. **Rebranding could disappear on a report route change or alter evidence.**
   Adversarial navigation reproduced a dynamically recreated branded page header;
   the adapter now removes that presentation header on every view-root update.
   DOM test switches module and checks no branded header returns. Go tests restore
   original bytes by removing only the injected presentation and verify downloads,
   pinning, isolation, original storage and the exact inline SVG. A fresh synthetic
   unrun standalone report embeds the supplied SVG, omits the old company/brand,
   and initialises its real renderer without JavaScript errors. Verdict: fixed/fine.
5. **Named guidance could refer to an unavailable conditional section or change
   native validation.** Generated-form tests check named disclosures and all
   original field/conditional/load behavior. Browser Primary reveals Deal terms
   with matching guidance; Research restored afterward. Verdict: fine.
6. **Packaging or Windows-specific behavior may differ from the preview.**
   Windows amd64/arm64 vet and cross-compilation checked; final archive/native
   smoke results recorded below. Actual Windows desktop/browser acceptance remains
   open because this host is macOS. No paid/provider execution occurred.

Fixed: responsive breakpoint, reading measure, stale section labels, missing
classification display, dynamic branding header and source-label wrapping.
Verified fine: exact decimals/zero/missing, evidence focus, original bytes/CSP,
source selection, native form rules and newly rendered symbol-only HTML.
By design: an absent classification is not a cited/calculated/synthetic claim;
retained original exports are unchanged. Open: native Windows acceptance.

### Rewrite tournament — post-edit, inline, two material symbols

Targets read: web/app.js:93 metricSource; discovery.go:79 admitRun's new enum guard.
Skipped: mechanical renderer branding, generated assets/copy and one-line caller
wiring; no broader rewrite of existing discovery or analytical code. GitNexus
context and upstream impact were attempted for both; this worktree is not indexed.
Used rg plus Go compiler/tests as the caller-contract oracle instead.
Impact: metricCell/runRow and renderMetric/renderDetails -> render, selected run,
poll/reload, source focus; discover's manifest and legacy admitRun calls -> /api/library
JSON -> frontend metrics. Invariants: exact values, missing vs zero, no inferred
provenance, pinned evidence before publication, canonical glyphs and contextual
accessible links; no provider execution or contract/signature changes.

Full backups, complete candidates and focused logs are in
`/tmp/issuer-library-fixes-tournament`. JS A hoists glyph markup, B selects shapes
with explicit comparisons, C normalises an allowed kind first. Every challenger
passed `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node
--test apps/issuer-library/web/app.test.cjs` (19/19). Guard A uses an && chain,
B a boolean allow-list expression, C a map; all passed `go test -run
'TestMetric|TestDiscovery|TestChangedAndMalformed' ./...` from the app directory.

Bracket: JS A beats B (readable mapping, no nested ternaries, stable geometry);
A beats C (no duplicated allow-list, no per-call list, fewer intermediate states);
incumbent beats A (keeps this tiny mapping beside its only consumer, avoids an
extra outer binding, no measured speed improvement). Go B beats A (positive
allow-list, clearer error branch, equal constant space); B beats C (no map
allocation, no lookup indirection, visible enum); incumbent beats B (native
switch expresses the closed set, zero extra local state, same error contract).

**Winner: Incumbent holds** at app.js:93–115 and discovery.go:79–84.
Justification:
- Closed sets and canonical shapes stay visible at their single validation/render boundary.
- Alternatives add state or duplicate allowed values without a measured benefit.
- All candidates preserve contract tests; original files were restored byte-for-byte
  and the complete focused suites rechecked after restoration.

Final code (unchanged incumbent):
```javascript
  function metricSource(run, key) {
    const metric=run.metrics[key], row=node('span',null,'metric-source');
    const marks={
      cited:'<path d="M1 .5h4l2 2v6H1z" class="pg-cited"/>',
      calculated:'<rect x=".5" y=".5" width="7" height="8" class="pg-calc"/><path d="M2 3.5h4M2 5.5h4" class="pg-calc-line"/>',
      synthetic:'<path d="M3 .5h2v3l2.5 4.5h-7L3 3.5z" class="pg-synth"/>'
    };
    const known=Object.hasOwn(marks,metric.provenance);
    const classification=node('span',known ? metric.provenance[0].toUpperCase()+metric.provenance.slice(1) : 'Not classified','metric-provenance');
    classification.title=known ? 'Producer-declared provenance' : 'The source metadata does not classify provenance.';
    if (known) {
      const glyph=document.createElementNS('http://www.w3.org/2000/svg','svg');
      glyph.setAttribute('viewBox','0 0 8 9');glyph.setAttribute('width','8');glyph.setAttribute('height','9');glyph.setAttribute('class','pg');glyph.setAttribute('aria-hidden','true');
      glyph.innerHTML=marks[metric.provenance];classification.prepend(glyph);
    }
    const source=button('Source',()=>{if(selected!==run.id)selectRun(run.id);showSource(metric.source);},'source-link');
    source.setAttribute('aria-label',`View source for ${metricNames[key]}: ${run.name}, ${run.title}`);
    row.append(source,classification);
    return row;
  }
```
```go
		switch metric.Provenance {
		case "", "cited", "calculated", "synthetic":
		default:
			return run, fmt.Errorf("metric provenance must be cited, calculated, synthetic or omitted")
		}
```

Validation before packaging:
- Go race suite and vet PASS; Windows amd64/arm64 vet PASS.
- All app/context/retained-renderer DOM tests: **37 passed**.
- `PYTHONPATH=src:tests /Users/ericguei/Documents/final-workflow/.venv/bin/python -m
  pytest tests/test_cpos_app.py tests/test_connected_render.py tests/test_codex_render_fixes.py -q`:
  **36 passed**; Ruff render.py and diff whitespace PASS.
- Real browser at 1280x720, 1366x768, 1440x900, 1500x900: module filter CP-1A,
  module -> Front Page, C65 evidence/locator, Escape and citation focus return,
  revision 2 -> 1 -> 2, Back and library return all PASS. The first bookmarked
  reload correctly falls back to main focus; subsequent Back returns to its
  originating report link (also separately verified at 1280). No invented analysis.
- One final Impeccable detect pass: 19 incumbent warnings (6 cramped-padding,
  2 monotonous-spacing, 1 undersized-ui-text, 6 tiny-text, 4 side-tab), matching
  the prior critique. Canonical selection/status edges, DS micro/label roles and
  context sections sharing a parent gutter were reviewed in the browser and kept.
  Regex-only CSS/JS coverage is incomplete; the detector is not acceptance proof.

Final package/browser verification:
- `python3 packaging/build.py` from apps/issuer-library: PASS (Go tests,
  Windows amd64/arm64 and macOS arm64 builds; pinned Python and eight wheels).
- Final ZIP integrity, launcher/Python PE architectures, bridge/renderer/symbol
  parity and exclusion of workspace runs, uploads and credentials: PASS.
- amd64 ZIP SHA-256: `c548f687dd25d375b8a44d97bbd5e703bb8235aa4659a1423576200e3c650e9d`.
- arm64 ZIP SHA-256: `252ba4c87b6cab1e8f17fd5e97e18e2cf161daa4b1f7696d07fa000ff722672e`.
- `ISSUER_LIBRARY_PYTHON=/Users/ericguei/Documents/final-workflow/.venv/bin/python
  python3 apps/issuer-library/packaging/smoke_test.py
  artifacts/issuer-library/darwin-arm64/issuer-library`: PASS — compiled
  launch/reopen, retained reports, Unicode workspace, offline CP-OS context/source/
  budget review, unavailable-provider Start gate, discovery, persistence and restart.
- Restarted the user preview from the final packaged macOS binary with provider
  keys removed at http://127.0.0.1:53708/. Actual workspace restored: 13 records.
  Final 1366px report has no old visible branding or page overflow; narrative
  figures compute to 80ch (633.6px at their text role). Final 1280px Search shows
  a fixed 236px drawer; both revisions and Back/focus work. Browser error/warn
  log is empty. Temporary viewport override reset; library tab retained.
- Proof images: artifacts/issuer-library/library-symbol-only.png and
  artifacts/issuer-library/report-laptop-fixed.png. Closed only the processed
  critique snapshot. No acceptance claim for native Windows or a paid run.

## 2026-11-04 — independent Astra re-critique after four fixes

A: `/root/symbol_critique_a`, B: `/root/symbol_critique_b`, both Astra, isolated with no prior critique/verification or detector input to A. Source unchanged. A live IAB inspection; B CLI/source/test inspection and failed IAB attempt (capability unavailable); parent supplied fresh-tab live fallback after both assessments finalized. All temporary tabs closed and viewport reset. No overlay/live-server, paid execution or native Windows acceptance.

Three fixes pass: coherent navigator/search at 1280/1350/1351/1366/1440/1500, named context destinations, explicit unknown/declared provenance. Symbol-only branding passes; original downloads stay byte-equal. Reading-width fix is partial: at 1440, Strengths/weaknesses block1100px/body712.8px/grid688.8px with 197.4px explanation columns, while module prose is1074px/max-width:none. Separate P2: eight identical Limitation outline targets. Score31/40, zero P0/P1, two P2. Required CLI scan19 warnings interpreted against DS. All37 DOM tests and Go race/vet pass. Screenshot: artifacts/issuer-library/critique-prose-width.png.

Archived critique: /Users/ericguei/.codex/worktrees/offline-issuer-library/final-workflow-library/.impeccable/critique/2026-11-04T21-55-37Z__apps-issuer-library-web-index-html.md

## 2026-11-04 — navigation review and Deploy VII chart investigation

Read-only review; symbol-only branding accepted and unchanged. Browser traced
issuer filter -> annual run -> Retained files (32 flat technical files for tdg-002)
-> report -> Back. File anchors use target=_blank. Report hides the library and
only exposes Back, revision selector and export; no cross-issuer/run/file switcher.
Own background tab closed; preview untouched. Proposed persistent issuer/run
context plus Overview/Reports/Sources/Files and an in-app document list/viewer.

Inspected actual /Users/ericguei/Documents/DEPLOY VII source (not just design
screenshots): charts.py implements line, grouped, stacked, waterfall, debt_stack
and unavailable frames; report_view.py names S.1 Leverage, S.2 Interest cover,
S.3 Liquidity and S.4 Maturity wall. Renderer embeds SVG, focusable provenance
marks and table twins. Executed two original pure component checks for each of
five chart kinds against that reference source with Python -B and bytecode off:
10 targeted checks PASS using explicitly synthetic fixtures; no issuer/model run
or reference writes. Current workflow already contains and extends this engine.

Missing-chart root cause: all six retained report-view.json files have the same
five narrative blocks and zero chart/figure objects. handoff_delivery.py:38 scopes
those five blocks, inserts blocked CP-MODEL and explicitly excludes numeric/chart
publication; delivery manifests report cp_model_published=false. Browser confirms
zero svg.chart and zero chart-figure elements. Reuse existing chart types and
bind verified handoff series through delivery, retaining exact period/unit/basis/
source and table parity; unavailable series remain explicit gaps. No application
code or historical deliverable was changed by this investigation.

## 2026-11-04 — module chart and qualitative visualisation catalogue

Mapped 24 active canonical modules, all 16 aliases and separate delivery into
91 specifications. Sources: current owner/handoff contracts, registered figure
bindings, selected methodology and all six Deploy VII front-page references;
inspected source revisions are hashed in docs/visualisations/MAP.md. Named figure
register has 14 existing producers, six design gaps and DR.6's unavailable frame.
Nine event lanes retain source identity, date precision, conditional status and
actual/forecast separation. Required content and proposed graphical treatments
are explicitly distinguished; producer presence is not issuer acceptance.

Confidence review of the documentation addressed coverage, quantitative versus
qualitative classification, narrower current alias duties, CP-OS's active role,
CP-8's one-case limits, currency qualification and missing figure producers.
Registry/alias coverage, unique IDs, CSV round-trip, 21 named entries, 91 HTML/
Markdown specifications, local download links and embedded-only HTML assets pass.
Browser at 1280x800 and 1366x768: no page overflow, zero broken anchors; module
overview -> CP-1B and shared calendar links reach the correct headings. Console
warn/error log empty. Proof: artifacts/issuer-library/visualisation-map-preview.png.
Temporary preview server/tab closed and viewport reset; main app preview retained.
Generated documentation only; no shipped functions changed, so post-edit rewrite
tournament does not apply. No analytics/provider run or historical source edits.

## 2026-11-04 — issuer research frontend

Built the approved symbol/palette into a persistent research workspace with run
switching, Overview/Modules/Visuals/Events/Reports/Sources/Files, a local handoff
reader and cross-run report navigation. Reviewed the mapped module contracts and
actual TDG, Ford and ARCC handoffs; the 91 visual specifications remain an explicit
requirements index. Financial views plot one original table row across explicit
period columns; CP-1A event views preserve source order and date precision.
Advanced graphs/nine-lane aggregation are still data/binding requirements, not
claimed implementation. File counts never establish acceptance. Symbol SHA-256
remains 67d73e1e8a6700b1528dabb1ad4c2e91963325bbde625cc4f84be5e294430dfd.

Reference/asset provenance: apps/issuer-library/DESIGN-SOURCES.md. Lucide SVGs and
license notices bundled locally; Red Hat fonts retained. User-pinned world and
standing discretion applied code-first. Impeccable finish review/documentation
performed inline under the project's no-subagent rule. DESIGN.md, PRODUCT.md and
the token sidecar describe the built app; no predecessor/history mutations.

Confidence review, ranked and traced:
1. Wrong primary revision: catalogue primary URL was hash-pinned while file-list
   URLs were not. Reproduced first-attempt selection; resolve the matching local
   path and retain its primary hash. Regression passes.
2. Stale data after a failed source change: old Overview chart could survive the
   new failure. Clear on selection/loading/error; adversarial HTTP 409 test passes.
3. Late file response/filter changes: per-reader abort plus signal/disconnection
   checks prevent replacement; delayed earlier-response regression passes. Filter
   changes clear selection and navigation so previous/next cannot use old results.
4. Malformed tables: silently skipping mismatched cells could conceal a row in
   the formatted reader. Reject that entire table as structured data and retain
   its original text. Regression passes; no eligible chart is produced from it.
5. Numeric/temporal interpretation: zero versus dash, negative parentheses,
   malformed commas, unsafe integers, exact decimal display and explicit period
   order tested. Event dates stay original text; no fabricated timestamp or risk.
6. Trust seams: DOM text insertion, same-origin /files/ URL guard and existing
   server allowlist/hash checks retained. XSS-like text/foreign-URL tests pass.
7. Navigation/focus: source links open Sources; cross-run report selection updates
   return context. Revisions preserve pins. New run explicit Start gating retained.
8. Layout: corrected unidentified-record count grid; reading-width restriction
   now targets prose rather than the complete Strengths/weaknesses container.
9. Offline packaging: served JS/CSS/catalogue/icon bytes equal source; license
   notices and reference documentation verified inside both Windows ZIPs.

Post-edit rewrite tournament, inline; scoped to mount and series. GitNexus context/
impact unavailable for this unindexed worktree; rg establishes mount <- renderDetails
<- render/accept/filter/selectRun and series <- loadVisual, plus DOM/parser tests.
Invariants: cancellation owns the mounted run, original data/source identities,
no missing-to-zero coercion, unchanged public callbacks and source-only rendering.
Speed pre-index/caching contender offers no meaningful benefit at 24 modules/91
specifications and introduces invalidation state. Memory shared-lifecycle contender
breaks independent reader/chart cancellation and is disqualified. Readability wins
for mount: extracted createFileReader with its own abort/selection lifecycle.
Incumbent series holds: its small table-to-row mapping retains exact strings with
no new calculation state. Final code: web/research.js createFileReader/mount and
web/workspace-data.js series. Other small helpers covered by confidence review;
generated catalogue, documentation, CSS and packaging copies are out of tournament.

Verification: 47 distinct frontend checks pass across the complete 46-check run
and focused 29-check final recheck (includes the new stale-chart regression).
Command: ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom
node --test web/app.test.cjs web/workspace-data.test.cjs web/report-renderer.test.cjs
web/new-run.test.cjs web/context-embed.test.cjs (from apps/issuer-library).
Go tests/race/vet pass. Windows amd64/arm64 and macOS builds pass. Final packaged
smoke passes launch/reopen, Unicode paths, offline context/source/budget review,
unavailable-provider Start gate, discovery/persistence/shutdown/restart.

Live browser: 1280x800, 1366x768, 1440x900 and 390x844. Verified file filtering,
reader, next file, real financial chart and seven-event TDG table, report revision
2 -> 1 -> 2, cross-run switch/back, screening and New run context. No page overflow
or console errors/warnings. Final byte-matched packaged preview retained at
http://127.0.0.1:53809/ with provider keys removed and viewport override reset.
Proof: artifacts/issuer-library/research-desktop.png, research-desktop-full.png,
research-mobile.png. Static Impeccable scan: six micro-text role warnings and one
false dark-background shadow warning; main prose/ground/depth inspected visually.
Inline finish disposition: ship within this frontend/data-lens scope. Native
Windows execution and advanced analytical-figure population remain unproven.

Final ZIP SHA-256:
- amd64: 5686ffcefcd49b21a864da500b31c1f2709166a81bd8cc79906146c057cf07f7
- arm64: c6501e2f22d0f38538675473c21b0ce8fda81b71ef563b5bddd9cec7ca3e107b


## 2026-11-04 — new frontend Astra critique

Read-only dual Astra assessment, explicitly requested by the user: independent
design review and detector/source assessment. A inspected 1280×800 and 1366×768;
parent supplied 1440×900 and 1280×800 live fallback because B could not access IAB.
Module-to-file transitions, chart discovery/provenance, CP-1A timeline links,
report return and run switching reviewed. No providers, Start run, UI code or
historical artifacts changed; no native Windows acceptance claimed.

Result: 22/40; three P1 findings (module/output/visual separation, chart row
qualification loss, laptop reading-space allocation) and two P2 findings
(timeline orientation/source navigation, run-switch task reset). Symbol-only
branding and core palette retained. Detector: 81 flags, 18 warnings and 63
advisories; many schema/cascade false positives, not 81 confirmed defects.
Second scan recovered truncated output. No overlay/server; all review-created
tabs closed and viewport overrides reset. Snapshot:
`.impeccable/critique/2026-11-04T23-14-39Z__apps-issuer-library-web-index-html.md`.
Fresh screenshots: `artifacts/issuer-library/critique-2026-11-04-*`.

## 2026-11-04 — module workspace integration

Applied the two recommended choices: selecting a module opens its analysis with
an explicit retained-output selector; this pass integrates existing charts/event
registers rather than building the remaining mapped figures. Four run views now
lead to Overview, Modules, Reports and Sources & files. Charts and events attach
to their own source tables inside the module. Run changes preserve the module and
per-run output selection. Symbol, palette, fonts, historical runs and reports are
unchanged. No provider execution.

### Confidence review — changed frontend only, inline

Ranked doubts, root-cause checks and dispositions:

1. **Loss of analytical identity — repaired and verified.** The old adapter
   dropped non-period columns. Series now retain every qualification column,
   source headers/row, table line and exact row line. Independent retained TDG
   assertions check `Calculated; simple subtraction only` and `Non-GAAP issuer
   metric, PDF 142`, as well as exact values and source order. Units not explicitly
   available beside a table remain a visible limitation; no units are inferred.
2. **Stale responses or cross-run selection — verified fine.** Each module/file
   request owns an AbortController and checks cancellation and connectedness.
   Adversarial delayed responses cannot replace the current output. Selections
   are scoped to run + module; missing output shows an empty state. Primary file
   SHA pins survive matching against unpinned catalogue paths. A designated input
   remains readable but is not promoted into chartable analytical output.
3. **Evidence destinations and focus — repaired and verified.** Source rows have
   individual line locators. Live keyboard Enter on the FY2022 cash-after-capex
   mark focused source row 253; Back to visual restored that SVG mark. Event links
   open their individual rows, not the table header or a new raw-file tab.
4. **Date precision — repaired and verified.** Calendar ordering only recognises
   explicit single calendar dates; ranges, fiscal periods and combined dates stay
   separate. A zero named day was found to fall through as month precision;
   corrected and regression-tested alongside invalid leap days and month bounds.
   Original date strings and classifications remain unchanged.
5. **Empty output / untrusted content — repaired and verified.** Empty files get
   an explicit state; failed loads clear old charts and expose Retry. Text uses
   textContent, including headings/qualifiers; URL guards restrict reads to the
   local indexed namespace. Missing, zero, unsafe numbers and malformed tables
   retain their prior guards. No financial signal is inferred from file counts.
6. **Laptop geometry and lifecycle — repaired and verified.** Live inspection
   found inherited column flex direction and obscured chart anchors. Explicit
   direction and observed toolbar height fix them. Library navigation collapses
   during module reading; module/output context remains visible. ResizeObserver
   is disconnected on mount cancellation. Empty-library cleanup uses suspend.
7. **Test harness assumptions — corrected.** The report helper now waits for the
   actual hashchange instead of an arbitrary 10ms. SVG scrollIntoView uses the
   same Element stub as HTML. The New run harness loads the actual frontend
   dependency order, and closes its window before asserting collected errors.
   These were harness defects, not browser failures.

By design: generic table charts are presentation views, not accepted model
figures. The first retained output is a labelled preview when no designated output
exists; no latest-filename acceptance is inferred. Unknown provenance is explicitly
Not classified. Native Windows browser acceptance remains unperformed.

### Rewrite tournament — no-argument post-edit mode, inline

Scoped to `createModuleWorkspace` and `analyticalDocument` in web/research.js;
other changed helpers were reviewed above and excluded by the two-symbol cap.
GitNexus context was attempted: this worktree is not among its indexed repos.
The rg impact set is local: mount → createModuleWorkspace → openModule →
analyticalDocument; app.renderDetails calls mount; source navigation calls
showSources; empty-state cleanup calls suspend. DOM tests exercise these seams.

Invariants: preserve output identity/pins, per-run selections, abort/disposal,
exact source text and row mapping, original table order, missing/zero distinction,
unaccepted-attempt status and all public signatures/side effects.

- **createModuleWorkspace winner: speed/readability cache, applied.** Incumbent
  repeated alias/file/output filtering on navigation and overview rendering.
  Speed candidate precomputes retained/output maps. Memory candidate defers those
  maps, but navigation counts immediately require every module anyway. Readability
  candidate separates output/controller ownership, adding more state plumbing.
  Bracket: eager cache beats lazy cache; eager cache beats extra controller split;
  cached candidate beats incumbent. Justification: one consistent classification
  per mount, direct lookups, no public contract or request-lifetime change.
- **analyticalDocument: incumbent holds.** Speed candidate pre-indexes every
  table's series/events; memory candidate parses each table lazily; readability
  candidate extracts table rendering with additional callback/result plumbing.
  In this bounded document renderer, DOM creation dominates and the incumbent
  keeps row attachment, visual placement and source focus in one auditable loop.
  No challenger provided a correctness/readability benefit sufficient to justify
  changing those coupled semantics. No blind/agent assessment is claimed.

Applied cache core (the surrounding function and caller signatures are retained):
```js
const retainedByModule = new Map(owners.map(id => {
  const aliases = VisualCatalogue.find(v => v.module === id)?.aliases.split(',').map(s => s.trim()) || [];
  return [id, files.filter(file => [id, ...aliases].includes(file.module))];
}));
const outputsByModule = new Map([...retainedByModule].map(([id, items]) =>
  [id, items.filter(file => /\.md$/i.test(file.base) && ['Module handoffs', 'Retained attempts'].includes(file.kind))]));
const matches = id => retainedByModule.get(id) || [];
const outputs = id => outputsByModule.get(id) || [];
```

### Verification and artifacts

- **56/56 frontend tests passed:**
  `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node --test apps/issuer-library/web/app.test.cjs apps/issuer-library/web/workspace-data.test.cjs apps/issuer-library/web/report-renderer.test.cjs apps/issuer-library/web/new-run.test.cjs apps/issuer-library/web/context-embed.test.cjs`.
- `go -C apps/issuer-library test ./...` passed; changed JS syntax checks passed.
- Windows amd64/arm64 and macOS arm64 packages rebuilt. Both Windows ZIPs passed
  integrity checks; archived PE executables match build outputs. Served JS/CSS/help
  match final source bytes. User SVG matches byte-for-byte.
- Packaged browser checks: 1280×800, 1366×768, 1440×900; no page-wide overflow.
  Verified chart qualifications, keyboard evidence/return, calendar/source views,
  run changes with missing output and restored attempt, report revision 2 → 1 → 2,
  report Back retaining CP-1A attempt 3, and Sources & files. Console errors/warnings
  empty. Report revision selection used the native menu after a semantic locator
  failed; actual revision identity and iframe URL were checked.
- Impeccable detector: 96 flags, 18 warnings / 78 advisories; 64 font-size schema
  advisories, 8 colour, 6 radius, 6 cramped-padding, 6 tiny-text, 4 side-tab,
  1 spacing and 1 dark-glow. Inherited context/help flags, intentional shadow and
  incomplete token-schema coverage are not 96 confirmed defects. Live laptop
  inspection governs actual hierarchy/readability; no overlay was injected.
- Fresh evidence: `artifacts/issuer-library/module-charts-1280.png`,
  `module-events-1366.png`, `module-analysis-1440.png`.
- Preview: http://127.0.0.1:53810/ (final packaged executable, no provider keys).
  Viewport reset; preview tab retained as the user-facing result.


## 2026-11-04 — Curated module presentation after Direction C review

Scope: inline review and refinement of `apps/issuer-library/web/{research.js,
research.css,workspace-data.js,app.js}` and their frontend tests, help and design
records. No subagents, providers, analytical reruns or historical-run mutations.
Existing branch work was preserved. Direction C reference was the supplied
`/Users/ericguei/Downloads/Direction C - Workbench.dc.html`, SHA-256
`bcd9dec94f44c6a3c8356823619031d3d721d70ede9aafefd53a4dc67d34da85`.
Its dense reading hierarchy and adjacent evidence informed the refinement;
reference financial data and conclusions were not copied.

### Result and confidence review

Least-confident points, investigated against code, retained files and browser:

1. **Accidental loss or misclassification of content — verified / repaired.**
   Presentation selects two leading analytical sections, keeps further analysis
   expandable and preserves all technical content in lazy Evidence & audit.
   Range coverage over 61 actual retained outputs found zero unassigned
   non-heading content lines. Unknown sections remain readable. Code-fence
   headings no longer create sections. CP-0 and CP-5 retain substantive lineage
   work in analysis instead of hiding their central purpose in audit.
2. **Hiding qualifications — verified within presentation scope.** Chart-local
   units, source qualifiers, exact value strings and period order remain intact;
   missing table basis is explicitly stated, not inferred from another section.
   Scope/limitations are directly reachable. Source/entity and normalization
   records remain in audit; the entire original output remains downloadable.
   This is section selection, not generated replacement analysis or acceptance.
3. **Source mapping and stale evidence — repaired and verified.** Inspectors
   resolve the exact retained table row using original line numbers. Switching
   measures closes the prior proof; switching output/module discards it. Escape
   and Back to visual restore the original trigger. The live 1280px check found
   reflow could push the clicked chart out of view; scrolling the trigger after
   reflow keeps chart and proof visible together. Unknown-provenance badges were
   accidentally hidden by a broad last-span rule; that rule now excludes badges.
   TDG CP-1 line 246 and CP-1A line 100 were verified against their retained rows.
4. **Navigation and restoration — repaired and verified.** Module navigation
   defaults to available outputs, with search and an All modules option. `/`
   targets the module search while reading. Output changes retain selector focus.
   A session cache restores issuer/module/output after reload, scoped to the
   workspace; cached output URLs are matched only against admitted catalogue
   files. Tests reject cross-workspace restoration and an external cached URL.
   Browser reload retained TDG-002 / CP-1A / attempt 3.
5. **Async, empty and untrusted input paths — verified.** Existing abort guards,
   stale-fetch tests, empty-output/error/retry states and textContent/URL guards
   still pass. Audit renders once and only after opening. Metadata never marks
   retained attempts as accepted; selected inputs do not become chartable output.
6. **Laptop usability — verified.** At 1280×800, 1366×768 and 1440×900 there was
   no page-wide horizontal overflow. Verified chart/proof return, visible unknown
   badges, qualitative disclosures, event navigation to an initially collapsed
   section, exact event proof, report revision 2 → 1 → 2, and report Back retaining
   the same module/output. Console warnings/errors were empty. Viewport reset;
   the final preview tab is retained.

By design: all original analytical words are preserved; selecting and collapsing
sections does not rewrite long conclusions. Event date precision remains explicit.
Chart rendering does not assert analytical approval. Native Windows UI execution
remains untested on this Mac; Windows artifacts were cross-built and checked.

### Rewrite tournament — no-argument post-edit, inline

Two most material symbols: `WorkspaceData.presentation` (workspace-data.js:78–119)
and `analyticalDocument` (research.js:146–226). Other changed navigation/inspector
helpers are covered by confidence review and excluded by the two-symbol cap.
GitNexus context was attempted: this worktree is not indexed. rg impact set:
app.renderDetails → ResearchWorkspace.mount → createModuleWorkspace/openModule →
analyticalDocument → WorkspaceData.presentation; the data and DOM tests cover
these interfaces. Signatures, returned section/visual targets, original source
positions, output identity, text safety and fetch cancellation must be preserved.

**Winner: Incumbent holds — WorkspaceData.presentation.**
- Sorting a bounded section list keeps priority and source-order ties explicit.
- A linear-selection speed candidate requires more branching to preserve the
  separate second-panel preference; it did not improve clarity enough to win.
- A streaming memory candidate loses ancestor/range information; a classifier
  extraction adds parameter plumbing without simplifying the contract.

**Winner: Snippet B — table grouping in analyticalDocument, applied at 149–150
and lookup sites.** Bracket: grouped lookup beats repeated lazy filtering;
grouped lookup beats separate renderer plumbing; grouped lookup beats incumbent.
- Series/events are classified by original table line once, retaining order.
- Table rendering uses direct lookups instead of filtering all items per table.
- Public results, exact rows, disclosure targets and inspection callbacks remain
  unchanged; focused and complete frontend checks passed after application.

Final winning core (surrounding function and signatures retained):
```js
const groupByTable = (items, key) => {
  const groups = new Map();
  for (const item of items) {
    if (!groups.has(item[key])) groups.set(item[key], []);
    groups.get(item[key]).push(item);
  }
  return groups;
};
const seriesByTable = groupByTable(series, 'line');
const eventsByTable = groupByTable(events, 'tableLine');
// In the table-rendering loop:
const eligible = visuals ? (seriesByTable.get(table.line) || []) : [];
const register = visuals ? (eventsByTable.get(table.line) || []) : [];
```

No blind or independent-agent judgment is claimed. Actual source and callers were
re-read, backups retained in /tmp, and final syntax/DOM/data checks verified the
winning implementation. The concrete invariant case retained FY2024/FY2023/FY2022
values 7,940 / 6,585 / 5,429 and source row 246 while plotting oldest to newest.

### Checks and shipped local artifacts

- **66/66 frontend tests passed:**
  `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node --test apps/issuer-library/web/app.test.cjs apps/issuer-library/web/workspace-data.test.cjs apps/issuer-library/web/report-renderer.test.cjs apps/issuer-library/web/new-run.test.cjs apps/issuer-library/web/context-embed.test.cjs`.
- `python3 apps/issuer-library/packaging/build.py` passed, including Go tests.
  Changed JS syntax checks and `git diff --check` passed.
- Windows amd64/arm64 ZIP integrity and archived executable identity checked;
  both executables have PE headers. Packaged preview serves final JS/CSS/help
  bytes. Symbol equals supplied STT.D.svg byte-for-byte.
- Final executable hashes: Windows amd64
  `dcdf825652e25cbbdea58395d9b24e0f8ab222716327a6bb3c31d27bea659332`;
  Windows arm64
  `7cc8655879309cd052cd24d89fb9578faf108dd60de17c27446490ee7a54eb5e`;
  macOS arm64
  `f2958227dc04b3b638b5111c0d5f07554043493fa98b1c8c1714d5bbe056c2b5`.
- Screenshots: `artifacts/issuer-library/curated-analysis-1366.png`,
  `curated-evidence-1280.png`, `curated-events-1440.png`.
- Preview: http://127.0.0.1:53810/ — final packaged executable, provider keys unset.
- The single pre-refinement Impeccable detector run reported 96 flags (18 warning,
  78 advisory); these include inherited/incomplete-token-schema flags, not 96
  verified defects. Manual laptop inspection determined confirmed findings;
  its temporary detector report was removed. No separate review files were added.


## 2026-11-05 — Impeccable clarify: interface copy

Applied the clarify playbook to the existing library, module reader and New run
flow, reusing the session's loaded product/design context. Existing Impeccable
schema drift was not repaired. No subagents or provider execution. Symbol,
colours, analytical text, units, qualifications and internal file taxonomy stayed
unchanged. New visible category labels map to the existing internal values.

Copy now names actions (Filter runs, View source, Open source file, Back to
analysis), distinguishes Primary output from Saved output, explains empty/error
recovery and retains Not classified. Reports & revisions replaces inconsistent
section naming; superseded revisions are no longer generically called failed.
New run distinguishes offline validation from paid execution, explains the initial
minimum budget without presenting it as a total-cost estimate, and gives a recent
history empty state. Help/README and a short DESIGN.md glossary match the labels.

Confidence review — least-confident points, investigated and resolved:
1. **Meaning and acceptance:** older saved attempts can coexist with a designated
   primary output. Corrected the history copy to describe only the selected file,
   then verified both cases in DOM tests and the browser. Analytical acceptance
   remains explicitly unverified; no claim of failed analysis follows merely from
   a superseded revision.
2. **Empty-state actionability:** a zero-result filter left Back to selected run
   active although no run was selected. Disabled it until results return;
   verified disabled/re-enabled states and Reset filters recovery.
3. **File categories and evidence:** display-only labels preserve taxonomy values,
   filtering, source-row line numbers and local URL guards. Existing exact-value,
   unknown-provenance, stale-response and report-navigation tests still pass.
4. **Cost and history claims:** traced the reservation minimum to bridge.py's
   budget-floor check. Start and approval controls are untouched. jobs.go excludes
   reviewed drafts from recent history, so the final empty text says No recent
   runs to show, not that no run has ever been prepared. This last semantic
   correction received a focused seven-test rerun and a required package rebuild;
   it did not trigger another visual-polish round.
5. **Copy fit and accessibility:** checked 1366×768 and 1280×800 laptop views,
   390×844 narrow view and 640×450 reflow (the CSS viewport equivalent of a
   1280×900 view at 200%; native browser zoom itself was not exercised). No
   page-wide overflow. Chart labels, source inspector and empty-state actions
   remained readable; accessible source/measure names match visible wording.
   Browser console warnings/errors empty. Viewport reset and preview tab retained.

Rewrite tournament: skipped as trivial copy/label changes plus short empty-state
presentation updates; no nontrivial function/algorithm rewrite in this pass.
Confidence review was still performed. Backups live in /tmp/issuer-clarify-before.

Verification:
- 66/66 frontend tests passed with
  `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node --test apps/issuer-library/web/app.test.cjs apps/issuer-library/web/workspace-data.test.cjs apps/issuer-library/web/report-renderer.test.cjs apps/issuer-library/web/new-run.test.cjs apps/issuer-library/web/context-embed.test.cjs`.
- After the final recent-history wording correction, `node --test
  apps/issuer-library/web/new-run.test.cjs` with the same JSDOM environment passed
  7/7. No paid calls; fixtures are synthetic DOM responses.
- JS syntax and git diff whitespace checks passed. Packaging Go tests passed.
  Both Windows ZIPs passed integrity and executable identity checks. Five served
  files match final source bytes. Native Windows UI execution remains untested.
- Final executable SHA-256: amd64
  `5247e44494fac39c699dca2f1d974a75587a85ee32cab59e0dd22e98c67ab918`;
  arm64 `f87a8d6b9fa41e2346e9f13c7411448350eafda0caa53d23beb9aaed8f89f530`.
- Screenshot: `artifacts/issuer-library/clarified-module-1366.png`.
- Updated packaged preview: http://127.0.0.1:53810/.

## 2026-11-05 — Information architecture proposal

User confirmed complete findings/data in designed analyst views, with raw handoffs
available in audit. Created one requested architecture document at
`apps/issuer-library/INFORMATION-ARCHITECTURE.md`; the live frontend is unchanged.
Compared the retained Direction C reference with the current module screenshot,
the 91-item catalogue, and TDG-002 CP-1/CP-1A/CP-2 instruction/output structures.
The map check found each of 24 canonical entries plus delivery exactly once,
all 91 visual IDs assigned, and no unknown IDs. `git diff --check` passed.
This is planning, not analytical acceptance or implementation. No code, provider
execution, historical source changes or subagents; code-review skills/tests are
not triggered by this documentation-only step.
# CP-1 / CP-1A / CP-2 screen designs — 5 November 2026

Scope: separate clickable HTML prototype in `artifacts/issuer-library/screen-designs/`,
authored in `apps/issuer-library/designs/`. The working application, launcher,
provider execution and historical run directories were not changed by this task.
Pinned source: TDG-002 CP-1 attempt 2, CP-1A attempt 3, CP-2 attempt 2.

## Confidence review

Least confident about, ranked, investigated inline under the no-subagents rule:

1. **Omitted or duplicated content.** A prefix match for T4.1 also matched T4.10,
   T4.11 and later tables. Confirmed with the all-sections parity check; corrected
   numeric heading boundaries. A fenced equity transcription was initially treated
   as prose; converted it to a full table using the handoff's stated column order.
   All nonblank body lines now retain exact row/paragraph parity: CP-1 315,
   CP-1A 87, CP-2 91. Every retained block has one named home; custom leading views
   preserve their underlying exact fields. Unknown substantive sections have an
   Additional findings fallback. Source copies match their retained originals.
2. **Financial and qualitative semantics.** Verified FY2023 operating income is
   2,923, correcting the generated composition's erroneous illustrative text.
   No chart reads that image. Negative amounts, source dashes, source order,
   share families, calculated versus reported qualifications and historical scope
   remain. CP-2 grades are exactly Average / Not Assessable / Not Assessable /
   Not Assessable / Average / Weak. Only the supplied Weak grade receives adverse
   colour. No scores or probabilities are invented. Timeline retains all nine
   events: five calendar entries and four fiscal/combined entries; October has
   month precision only. Inspector includes retained context and unknown provenance
   remains Not classified. Verified by independent fixed-value assertions and UI.
3. **Navigation and return.** Corrected catalogue labels against the approved IA;
   added persistent quick access to all three screens. Confirmed and fixed a skip
   link that could reset the route. Topic search opens the matching section.
   Narrow inspection initially inherited the source's window scroll and hid the
   Back control above the viewport. Reproduced in browser; corrected inspection
   scroll, focus and return position. Final observed Back button top was 15px;
   closing restored the FY2024 source trigger and prior scroll. Module/section
   navigation, deep links, invalid route fallback and Escape passed.
4. **Browser execution and escaping.** A renderer named `performance` collided
   with the browser global in JSDOM; renamed `performanceView`. HTML is escaped
   before inline formatting; source assets use relative local paths; data has no
   fetch or remote runtime dependency. Seven focused checks pass. Parser rejects
   malformed table rows, unclosed equity data and body-before-heading; Unicode
   retention passes. Builder reads/writes UTF-8 explicitly for Windows portability.
5. **Layout and device limits.** Browser screenshots at 1366×768, 1280×800 and
   390×844 show no page-wide horizontal overflow. Evidence remains beside analysis
   at laptop widths and has a separate reading view on narrow widths. The first
   narrow analysis capture was malformed during viewport transition and was
   replaced with a valid capture; the narrow-scroll bug required a focused final
   confirmation. Native Windows and browser file:// opening remain unverified:
   the built-in browser rejected the file protocol. No workaround was attempted.
   All browser verification used the already-running localhost prototype.

Fixed: section prefix duplication, equity-table presentation, catalogue names,
skip-link route reset, global name collision, narrow evidence focus/scroll.
Verified fine: source/body parity, exact values and dates, producer grades, local
assets, escaped source text, module/section/inspector interactions.
By design: one pinned output per module, other workspace destinations are context
only, source PDF viewer and production app integration are outside these designs.
Open: native Windows/direct-file smoke test; production adapter generalisation.

## Rewrite tournament — post-edit, inline

Targets: `parse_source` (build.py:16–76) and `renderRoute` (screen.js:171–195).
Only these two material symbols were tournamented; view templates and helper
renderers were covered by parity/interaction tests. GitNexus has no index for
this repository (it returned only other repositories); `rg` established the
impact set. `parse_source` is called only by the fixture builder and verification;
`renderRoute` is called at startup, by hashchange and by focused tests.

Invariants: exact source strings/locators, fail closed for malformed fixture rows,
all substantive content addressable, module/section pinning, no new analysis,
preserved source focus and narrow scroll, unknown provenance, no network requests.

**Winner: Incumbent holds for both.**

- Speed challenger: regex-wide parsing / cached rendered pages would save negligible
  work on three fixtures but makes source line boundaries or detached focus targets
  harder to preserve. Disqualified when semantics change; no verified benefit.
- Memory challenger: streaming parser / incremental DOM updates add state and
  duplicate rendering paths to a small fixture. Exact source copies are retained
  intentionally; no material allocation problem was measured.
- Readability challenger: splitting each table and route branch into handlers adds
  interfaces without reducing the state transitions. Current single-pass parser and
  explicit changed-view versus evidence-only route preserve the simplest design.

No rewrite applied. Final code is the reviewed functions at the paths/lines above;
no parallel draft files were retained. Caller contracts were rechecked with the
builder, source parity checks, syntax validation and seven focused tests.

Commands/results:

```text
python3 apps/issuer-library/designs/build.py                         PASS, 3 modules
node --check apps/issuer-library/designs/screen.js                   PASS
ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom \
  node --test apps/issuer-library/designs/design.test.cjs            7/7 PASS
Parser adversarial/Unicode probes                                  4/4 PASS
Independent source row/paragraph parity                            493 body lines
git diff --check                                                   PASS
```

## Impeccable finish review — inline, prototype scope

Disposition: **fix** for production promotion; the requested three screen designs
are delivered for review. The full comp-to-production gate was not completed and
must not be represented as a shipping production frontend. The user explicitly
requested screen designs at this stage. This inline review substitutes for the
skill's agents because the project prohibits subagents.

- Persistence: approved IA contract and prototype extension to DESIGN.md recorded.
  Build-phase state records `finish: fix`; spec/hero production reproduction gates
  remain open. No production release verdict is claimed.
- Fidelity: symbol/type/palette/ground/persistent module navigation/adjacent
  inspector match the pinned hybrid. Data-correct text, compact laptop header,
  complete section selector, three-screen quick links and narrow reflow are
  deliberate adaptations for source truth and accessibility. Type uses local
  Red Hat fonts; material is one lifted white surface with internal rules; ground
  is #EEF0F5. No raster imitation or invented branding ships.
- Ceiling: designed financial, timeline and qualitative presentations are distinct.
  Exact tables and full findings remain reachable. Production output/revision
  selection, all-module adapters and real PDF inspection are future integration.
- Material fixes for promotion: implement approved designs in the working shell,
  prove adapters on further outputs and run Windows/revision/report navigation
  checks; complete the production reproduction/review gates. These are not hidden
  claims of functionality in the screen-design artifact.
- Keep: complete content through named module sections, adjacent evidence at
  laptop sizes, explicit date precision and units, symbol-only branding, and
  colour tied to supplied evidence states.

Captures: `cp1-1366.png`, `cp1a-1366.png`, `cp2-1366.png`, `cp2-1280.png`,
`mobile-analysis.png`, `mobile-inspector.png` in the artifact folder. Composition
reference is generated, not source evidence, and is not bundled into the UI.


## 2026-11-05 — Complete module/workspace screen designs (designs only)

User explicitly chose “Complete the screen designs first.” Extended the separate
Direction C/current-layout hybrid in `apps/issuer-library/designs/`, preserving
symbol-only branding. No production integration, provider execution or historical
run mutation. All 22 analytical module designs are reachable: 19 use retained
outputs (including the bounded CP-3 / CP-3C consumers); CP-L10, CP-3D and CP-8 have
honest missing-evidence states. Library, Overview, Calendar, Reports, Evidence,
CP-MODEL publication state, CP-OS run record and Help are interactive. The 91-view
visualisation specification remains a plan, not a claim of 91 populated figures.

Confidence review, inline as required (no subagents):

1. Content loss or duplicate presentation — independently compared all 2,546
   substantive raw body lines across 19 originals with parsed blocks; every
   block maps to exactly one section and every exact cell/text appears in its
   rendered view. Fixed paragraph whitespace preservation and removed repeated
   tables only when the designed view contains every field. Original handoff
   SHA-256 values match. Verdict: verified.
2. Numeric meaning — tested missing versus zero, signed/parenthesized values,
   percentages, exact precision, FY2027 scenario endpoints, a six-component cash
   bridge, and total recovery including deficiencies. Added the explicit 4,173
   issuer EBITDA endpoint. Peer percentage selections exclude USD rows. Timeline
   base-date label was at the wrong visual position; aligned it to the actual
   September 2024 point (between 33% and 34% of its dated axis). Verdict: fixed.
3. Case boundaries and malformed links — TDG/Ford/Frontier headings, source
   inventories and dates stay separate; cross-module evidence is allowed only
   from Calendar. A reproduced `#toString/x` crash exposed inherited object keys;
   patched registry lookup with Object.hasOwn and tested constructor/__proto__.
   Verdict: fixed, with regression coverage.
4. Provenance — a reproduced CP-6 decision verdict was being classified as
   evidence type. Insufficient Information now requires a provenance/classification
   field; otherwise Not classified remains beside the source link. Verdict: fixed.
5. Navigation and focus — fixed chart-selector focus loss after replacement and
   restored analytical-scroll position as well as focus when closing evidence.
   Tests cover the source→inspector→Escape cycle, timeline owner, section/topic
   search, invalid links, issuer switches and report build routing. Verdict: fixed.
6. Reports, offline dependencies and input safety — all six original report
   downloads are byte-identical; only separately named previews get the symbol
   adapter. All assets/data are local, rich text is escaped, report frames permit
   scripts but not same-origin access/top navigation. No remote runtime dependency
   or provider call is introduced. Native file/Windows execution remains untested.
7. Laptop layout — browser walkthroughs at 1366px and 1280px covered 22 modules and
   two tools with no page/content horizontal overflow. Inspected chart, hedge,
   committee and adjacent-inspector compositions. All six report builds loaded at
   1280×720; switching and Return to library worked. No browser error logs observed.
   Current screenshots have decoded JPEG format and dimensions in the provenance
   manifest; old prototype captures remain on disk but are excluded from the ZIP.

Rewrite tournament, no-argument post-edit mode, inline:

- Targets: `screen.js:164–173` parseRoute and `views.js:52–64` comparisonChart.
  The two-symbol cap excludes the other builder/layout/template helpers from this
  tournament pass; they received the confidence/content review above. GitNexus is
  not indexed for this repository; rg resolved callers: renderRoute→parseRoute;
  galleryVisual and the metric-change handler→comparisonChart. Signatures, route
  fallback, source ownership, exact chart values, missing-data semantics and HTML
  output are the invariants.
- Three executable challengers per target: speed (explicit loops), memory
  (reduced allocations), readability (guard clauses / point helper). Route bracket:
  speed beats slicing/memory; readability beats speed; incumbent beats readability.
  Chart bracket: reduction/memory beats loops; memory beats helper/readability;
  incumbent beats memory. All six alternatives were semantically equivalent on
  237 route cases and 19 chart selections. No runtime pressure justifies extra
  mutable loops, slicing or helpers for these bounded fixtures.
- **Winner: Incumbent holds.** No replacement of either reviewed function.
- **Justification:**
  - Existing expressions keep module/section/evidence checks and point construction together.
  - Every candidate preserved observed output; none improved the dominant rendering cost.
  - Keeping the direct implementations avoids extra helpers and repeated return shapes.
- **Verification:** `node /tmp/issuer-design-tournament.cjs` passed all variant
  comparisons; `node --check apps/issuer-library/designs/screen.js` and the matching
  views.js command passed. Caller contracts rechecked by the focused suite:
  `ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node --test apps/issuer-library/designs/design.test.cjs` — 14/14 pass.

<details><summary>Final code — tournament incumbents</summary>

```js
function parseRoute() {
  const [path,query='']=location.hash.slice(1).split('?');
  const [requestedModule,requestedSection]=path.split('/');
  const module=Object.hasOwn(modules,requestedModule)?requestedModule:'CP-1';
  const section=modules[module].sections.some(s=>s[0]===requestedSection)?requestedSection:modules[module].first;
  const e=new URLSearchParams(query).get('e');
  const key=e&&(e.includes(':')?e:`${module}:${e}`);
  const permitted=key&&(key.startsWith(module+':')||module==='W-Calendar');
  return {module,section,evidence:permitted&&evidence.has(key)?key:null};
}
function comparisonChart(module,v,selection=0) {
  const table=fixtureTable(module,v.table),selected=table.rows[v.rows?.[selection]??0];
  const selectable=['paired','peers'].includes(v.kind)&&module!=='CP-4C'&&module!=='CP-2A';
  const rows=selectable?[selected]:(v.rows||table.rows.map((_,i)=>i)).map(i=>table.rows[i]);
  const points=v.kind==='peers'?v.columns.map(c=>({label:table.headers[c],value:selected.cells[c],row:selected,series:0})):rows.flatMap(row=>(v.columns||[v.column]).map((c,i)=>({label:plain(row.cells[0]),series:i,value:row.cells[c],row,column:c})));
  const max=Math.max(1,...points.map(p=>Math.abs(chartNumber(p.value)??0)));
  const hasNegative=points.some(p=>(chartNumber(p.value)??0)<0);
  const legend=v.columns&&v.kind!=='peers'?`<div class="chart-legend">${v.columns.map((c,i)=>`<span><i class="series-${i}"></i>${esc(table.headers[c])}</span>`).join('')}</div>`:'';
  return `${chartIntro(v)}${selectable?`<label class="metric-control">Measure <select id="chart-metric">${v.rows.map((idx,i)=>`<option value="${i}" ${i===selection?'selected':''}>${esc(plain(table.rows[idx].cells[0]))}</option>`).join('')}</select></label>`:''}${legend}<div class="horizontal-chart ${hasNegative?'diverging':''}">${points.map(p=>{
    const n=chartNumber(p.value),width=n===null?0:Math.abs(n)/max*100;
    return `<button class="chart-row" data-evidence="${module}:${p.row.line}"><span class="chart-label">${esc(p.label)}${v.columns&&v.kind!=='peers'?`<small>${esc(table.headers[p.column])}</small>`:''}</span><span class="track ${n===null?'missing':''}">${hasNegative?`<span class="zero-rule"></span><i class="series-${p.series} ${n<0?'negative':''}" style="left:${n<0?50-width/2:50}%;width:${width/2}%"></i>`:`<i class="series-${p.series}" style="width:${width}%"></i>`}</span><strong>${n===null?'Not available':esc(p.value)}</strong></button>`;
  }).join('')}</div><p class="matrix-note">Select a plotted row to inspect its exact source fields. Missing values have no bar.</p>`;
}
```
</details>

Delivery: `artifacts/issuer-library/module-screen-designs.zip`, 75 files (~5.4 MB),
ZIP CRC check passes. Entry is `screen-designs/index.html`; localhost preview is
`http://127.0.0.1:53812/`. DESIGN.md and bundled README describe the actual scope.
Screens retain all analytical restrictions; this is not an analytical acceptance
review, a Windows launcher test, or a claim of a completed single-issuer pathway.

### 2026-11-05 — adversarial design review (no implementation changes)

Target: `apps/issuer-library/designs/index.html`, slug
`apps-issuer-library-designs-index-html`, preview port 53812. Applied Impeccable
critique/audit/Operate guidance and a11y-audit. Single-context review as required by
this project's prohibition on subagents: visual Assessment A recorded before
detector Assessment B. Design heuristic scores (0–4, higher is better):
status 3; real-world match 2; control 2; consistency 2; prevention 3;
recognition 2; efficiency 2; minimalism 2; recovery 3; help 3 — **24/40**.

Confirmed priorities:

- P1, case continuity: Ford CP-2H → Reports opens TransDigm; Calendar is also
  case-hardcoded. The gallery labels its historical cases, but does not demonstrate
  the approved pinned-issuer/run workspace journey. Preserve selected context and
  show a contextual unavailable state where its report or calendar is absent.
- P1, narrative evidence: CP-4/s75 renders three prose blocks and 17 forced line
  breaks with zero evidence actions. Add claim/section evidence access and remove
  source wrapping from designed prose; retain exact text and audit downloads.
- P1, discovery/focus: CP-2E has 21 flat section options; CP-4 has duplicate Gaps
  labels; CP-2F alias search has no result. Next section and section selection
  leave keyboard focus on BODY. Use a grouped, persistent outline and restore focus.
- P2, laptop reading area: at 1280×720 content starts at y279 and ends at y702;
  the CP-2G chart extends to y776 and its readout starts at y794. Report iframe
  height is 402px with nested report chrome. Consolidate navigation/status chrome.
- P2, visual contract: CP-1B colours reported Current values amber although the
  key reserves amber for conditional/attention. CP-2G plotted points are passive,
  unlike hedge and bar rows. Use semantic colour roles and consistent point-level
  keyboard/pointer evidence access. Hedge axis/date text measures 9px.

Preserve symbol-only branding, Red Hat fonts, restrained depth, explicit missing
data, module-owned visuals and the adjacent inspector. At 1366×768 the hedge
inspector opened by keyboard; Escape restored focus to its originating hedge row.
No page horizontal overflow in this check. These are design findings, not a claim
of analytical errors, complete WCAG conformance, or Windows execution testing.

Deterministic scans, each run once: Impeccable 78 findings (11 warnings and 67
advisories); small text corroborated, font parsing/flush-tab padding and many
token advisories do not establish user-facing defects. a11y scanner 18 findings
(17 serious, 1 moderate), all unsupported as reported after source/DOM triage:
decorative image alt, actual #analysis skip target, implicit status live region,
and CSS files treated as documents. The manually reproduced focus defect remains.
Screenshots: `artifacts/issuer-library/screen-designs/adversarial-forward-1280.jpg`
and `adversarial-prose-1280.jpg`. No implementation or bundle changes. No separate
critique snapshot/trend, respecting the single verification record requirement.

### 2026-11-05 — five design fixes, complete screen designs only

Scope: `apps/issuer-library/designs/`, its generated HTML bundle and design
context documentation. Production app, launchers, analytical execution and
historical runs were not changed. Symbol-only branding retained byte-for-byte.

Implemented: pinned issuer/run in deep links and workspace tabs; explicit
unavailable destinations and case switching; persistent grouped section outline
above the module catalogue with aliases, unique labels and remembered state;
source inspection for every narrative block and plotted mark; compact laptop
chrome and a single report identity shell; comparison colours separated from
labelled conditional signals. All retained content and original downloads remain.
The six report builds stay a separate delivery collection: no inferred run link
or verified revision order. No current issuer analysis or new provider run.

Confidence review — doubts ranked and traced:

1. Case leakage through workspace links or evidence URLs — followed parseRoute,
   routeHref, navigationSections and renderRoute into every destination. Ford
   Reports/Calendar stay Ford and show absence; TDG-002 events and TDG-003 hedges
   stay separate; cross-case evidence is rejected. Deep-link and context tests pass.
2. Malformed legacy evidence routes — adversarial `W-Evidence/constructor`
   reproduced a TypeError because a plain-object legacy lookup inherited Object
   members. Added an own-property guard. `constructor`, `__proto__`, `toString`
   regression passes; explicit context and aliases retain their contracts.
3. Focus after rebuilding navigation — browser proved next-section/outline focus
   and inspector Escape return. Final source review also found hidden targets when
   compact navigation closes or report/library chrome disappears. Route focus now
   targets the visible section title, report selector or main region; targeted DOM
   regression covers all three. This final focus guard received DOM verification;
   the preceding browser visual captures remain visually unchanged.
4. Coverage and source fidelity — complete-content test still verifies every
   retained block is reachable once; narrative newlines become spaces only in
   presentation. All 19 handoff hashes and six original report hashes match.
   Unknown provenance remains Not classified, never inferred from a verdict.
5. Chart values and evidence — retained strings, periods, quantity units, negatives
   and missing/zero distinctions pass the existing independent expected-value
   checks. Nine scenario points and all bridge marks expose source actions. Browser
   Enter on Reference/FY2026 opens its exact row; Escape returns to that point.
6. Report adaptation — all six embedded records declare Assessment pending;
   folding that placeholder with delivery limitations is scoped to these copies.
   The call outline action expands the disclosure. All six builds switched in the
   browser; citation inspection and Return to library worked. Originals untouched.
7. Laptop density and responsive state — inspected 1280×720, 1366×768 and a 640px
   compact view. Final 1280 content starts y217 (previously y279), whole path plot
   ends y624 with axes/years visible, and report iframe height is 518px (was 402px).
   Active section outline is immediately available above the catalogue. No page
   horizontal overflow; report navigator scrollWidth equals clientWidth. Hedge
   labels are 11px. No browser console errors observed. Functional text floor 11px.
8. Offline/package boundary — local assets only, source/generated files agree,
   original symbol agrees, ZIP CRC passes. Native Windows and direct file-browser
   execution were not run in this screen-design review; these are not app releases.

Fixed: legacy-route prototype lookup, hidden focus destinations, outline below
catalogue, report navigation crowding, and all five accepted design findings.
Verified fine: complete data coverage, case boundaries, values and original bytes.
By design: absent case outputs and unlinked report collection remain explicit.
Open: production integration and native Windows execution, deferred by the user.

Rewrite tournament — no-argument post-edit mode, inline (no subagents):

- Two decision functions selected: `parseRoute` and `sectionGroups`. Remaining
  rendering/template helpers, report adaptation and build copying received the
  confidence review; excluded from this tournament by the two-symbol cap.
- GitNexus context returned repository not indexed. rg impact set: renderRoute
  calls parseRoute; renderNavigator → outlineMarkup calls sectionGroups. Both are
  design-only browser globals; focused DOM suite is the caller contract oracle.
- Invariants: exact route shape; explicit case preference; safe aliases/defaults;
  no cross-case evidence; complete section membership exactly once; group insertion
  order, labels and source section identities preserved. No analytical calculation
  or original artifact mutation.
- Three executable challengers each: parser speed (explicit section loops), memory
  (substring path extraction), readability (guarded context branches); grouping
  speed (indexed iteration/single bucket lookup), memory (array buckets), readability
  (named label classifier). All six matched their incumbent on **11,540 route cases
  and 30 module/workspace groupings**.
- Parser bracket: speed beats slicing/memory; readability beats speed; readability
  beats incumbent. Grouping bracket: speed beats array/memory; speed beats helper/
  readability; incumbent beats speed. No performance improvement was claimed.

**Winner:** readability challenger replaces parseRoute; sectionGroups incumbent holds.

Justification:
- Explicit context branches make the legacy-own-property guard and case precedence
  reviewable without changing signatures or return values.
- Ordered Map buckets retain all original section references and group order.
- Extra grouping helpers/loops do not improve these bounded fixtures enough to
  justify replacing the direct implementation.

Final code — tournament winners:

```js
function parseRoute() {
  const [path,query='']=location.hash.slice(1).split('?');
  const [requestedModule,requestedSection]=path.split('/');
  const resolved=Object.hasOwn(aliases,requestedModule)?aliases[requestedModule]:requestedModule;
  const module=Object.hasOwn(modules,resolved)?resolved:'CP-1';
  const params=new URLSearchParams(query),legacyCases={ford:'ford-otosan-2024',frontier:'frontier-2020',tdg:'tdg-002'};
  let fallback=contextKey(data[module]);
  if(!fallback&&module==='W-Reports')fallback='tdg-deliveries';
  if(!fallback&&module==='W-Evidence'&&Object.hasOwn(legacyCases,requestedSection))fallback=legacyCases[requestedSection];
  if(!fallback&&module==='W-Calendar')fallback=requestedSection==='hedges'?'tdg-003':'tdg-002';
  const requestedContext=params.get('c');
  const context=Object.hasOwn(contexts,requestedContext)?requestedContext:fallback||current?.context||'tdg-002';
  const sections=navigationSections(module,context);
  const selected=sections.find(s=>s[0]===requestedSection)||sections.find(s=>s[0]===modules[module].first)||sections[0];
  const e=params.get('e'),key=e&&(e.includes(':')?e:module+':'+e),item=evidence.get(key);
  const permitted=item&&contextKey(data[item.module])===context&&(item.module===module||module==='W-Calendar');
  return {module,section:selected[0],context,evidence:permitted?key:null};
}
function sectionGroups(module) {
  const result=new Map();
  for(const section of modules[module].sections) {
    const [id,label,prefixes]=section,heading=prefixes.join(' ');
    let group='Findings & analysis';
    if(id==='audit'||/^(Sources|Scope &|Evidence &|Definitions & periods|Source register)/.test(label))group='Evidence & audit';
    else if(/gap|limit|monitor|follow-up|readiness/i.test(label))group='Limits & monitoring';
    else if(module==='CP-2E')group=heading.includes('T2G.')?'ESG & credit effects':heading.includes('T2F.')?'Rates, FX & hedges':'Credit conclusion';
    else if(module==='CP-1D')group=heading.includes('T1E.')?'Debt & obligations':'Earnings quality';
    else if(module==='CP-5')group=heading.includes('T5B.')?'Evidence lineage':'Validation & remediation';
    if(!result.has(group))result.set(group,[]);
    result.get(group).push(section);
  }
  return [...result];
}
```

Verification: `node /tmp/issuer-design-five-fixes/tournament.cjs` reported all six
challengers equivalent; the readability winner was applied and callers rechecked.
`ISSUER_LIBRARY_JSDOM=/tmp/issuer-library-dom-check/node_modules/jsdom node --test
apps/issuer-library/designs/design.test.cjs` — **22/22 pass**. Node syntax checks for
screen.js, views.js and report-preview.js passed. Single Impeccable detector pass:
93 flags (7 warnings, 86 advisories); source-only stale small-text declarations were
raised to the 11px floor, font parsing/flush tab padding were false positives, and
remaining token advisories were triaged against the approved dense design language.
No second detector loop or independent-agent claim.

Delivery: `artifacts/issuer-library/module-screen-designs.zip` — 72 files,
5,238,864 bytes, CRC verified. Preview `http://127.0.0.1:53812/` remains available.
Four fresh JPEGs (`refined-outline-1280`, `refined-evidence-1366`,
`refined-reports-1280`, `refined-library-1366`) are identified in the capture manifest;
older screenshots are retained on disk but excluded from this ZIP. Viewport override
reset; preview tab retained as a deliverable. Temporary review candidates removed.

### 2026-11-05 — repeated Impeccable critique, outline persistence and library filters

Scope: screen-design gallery only. All five accepted fixes rechecked against the
Direction C/current-layout hybrid and Deploy VII language, with exact symbol-only
branding. No production integration, provider call or historical artifact edits.
Single-context review required by AGENTS.md; no subagents or independent review
claim. Assessment A was completed before the one detector pass.

Design assessment: authored for issuer research through grouped analytical
sections, dated case boundaries, domain-specific graphics and exact evidence.
The two priority findings were P1 catalogue state overwriting the persistent
outline and P2 unfiltered library discovery burying Ford/Frontier below TDG runs.
Both are repaired. Remaining minor concern: long subsection labels remain dense;
the historical gallery cannot prove production run/revision relationships.

Five-fix verification:
- Issuer context: Ford → unavailable Reports → Modules remains Ford and the
  same dated run. Separate TDG report collection is explicitly labelled.
- Grouped outline: the round trip now preserves the deliberately closed
  catalogue; outline y330.5 at 1280×720, versus the reproduced y922 regression.
  CP-2E groups retain rates/FX, ESG, limits, conclusion and evidence distinctions.
- Evidence: CP-4 narrative line 77 and CP-2G Reference/FY2026 point open exact
  retained content. Ford line 35 also opens and Escape returns to View source.
  Unknown provenance stays Not classified beside the source action.
- Laptop/report navigation: actual DOM sizes verified at 1280×720 and 1366×768.
  All six report builds switch at 1366; build 1 → 6 and C65 inspection rechecked
  at 1280. Preview and original link agree. Return to library restores filtering.
  At 1280, report iframe is 517.86px high; child scrollWidth/clientWidth both
  1200px. No horizontal overflow or console errors in checked paths. CP-2G plot
  fits within its reading panel with axis/years visible.
- Colour signals: quarterly prior/current remain blue/navy comparisons;
  conditional downside remains labelled amber with a distinct dash pattern.
  Missing values and analytical verdicts never become provenance classifications.

Library now combines case-insensitive issuer/run/year text, sector, available
content and contained-module filters. Counts distinguish 3 issuers, 7 runs and
1 report collection. Empty results explain recovery; Clear filters resets all
criteria and focuses search. Filters persist on return within the same page
session. No unsupported credit-metric/completeness filters were invented.

Heuristic review (0–4, all applicable): status 3; real-world match 3; user control
3; consistency 3; error prevention 4; recognition 3; efficiency 3; minimalism 3;
error recovery 3; help 3. **31/40, Good**; a qualitative review score, not a user
study. The analyst can move finding → source → finding; keyboard users retain
focus; first-time users can find Ford without traversing TDG's runs. Five main
workspace destinations and long outlines remain the main cognitive load; named
groups and the optional catalogue contain it without hiding module content.

Confidence review — ranked doubts, investigation and disposition:
1. Programmatic disclosure state contaminating user state — CONFIRMED bug. Native
   browser reproduced Reports → Modules forcing catalogue open. The capture-phase
   toggle listener persisted programmatically opened details. Persist only
   deliberate summary clicks (including native keyboard activation), before the
   native state change. Async regression distinguishes workspace renders from
   explicit user expansion; browser confirms visible outline on return.
2. Filter results blending cases or inventing completeness — fine. Traced
   contexts → libraryRecords → filterLibrary → libraryResults → routeHref. Eight
   records preserve insertion order and explicit case IDs. AND combinations,
   module membership, short TDG ID, empty results and singular/plural counts pass.
   Missing credit metrics are stated, not scored; no cross-run aggregation.
3. Reset restoring old defaults after a return — prevented. A native form.reset
   would restore the saved values used to render the returned form. Clear instead
   assigns each default to the live control, then updates results. Regression
   covers returning with filters, clearing, focus and Enter without navigation.
4. Search escaping and focus — fine. Literal `\"><img...>` stays text, creates no
   onerror node, and yields no results. Only the result container/count is replaced
   while typing, keeping the search/select nodes and focus intact. Browser checked
   combined Ford/2024 filters, no matches, reset and retained return selection.
5. Stale served preview — CONFIRMED. Server source contained the new library while
   a previously opened tab still used old script bytes. Generated entry URLs now
   carry content hashes for five mutable JS/CSS/data assets. All hashes verified;
   paths remain relative. Fresh navigation rendered the corrected controls.
6. Data, originals and branding — fine. All 19 copied handoff SHA-256 values and
   six original report SHA-256 values match their retained source records. Symbol
   is byte-identical to supplied STT.D.svg. Source/generated JS/CSS agree; entry
   differs intentionally only by versioned local asset references.
7. Scope of browser proof — open/by design. Native Windows and direct file URLs
   were not exercised. Measured laptop sizes are reported, not requested override
   sizes; this pass does not claim a new 640px check. No claim of production
   integration or live run history. Production integration remains deferred.

Fixed: disclosure persistence and stale served assets. Verified fine: filters,
focus, context, evidence, report selection and source bytes. By design: session
only filter memory, explicit unavailable metrics and unlinked delivery collection.

Rewrite tournament — no-argument post-edit mode, inline, two-symbol cap:
- Targets: filterLibrary and libraryResults in views.js. GitNexus repository was
  not indexed; rg caller set is workspaceView → libraryView and the input/change/
  clear handlers → updateLibraryResults. Templates/helpers received confidence
  review and are excluded from this two-symbol tournament.
- Invariants: AND criteria, literal case-insensitive terms, exact module matches,
  no input mutation, same row identities/order, escaped output, pinned case links,
  same empty state and issuer/run/report counts.
- Six actual executable challengers: filter speed loops, memory regex terms and
  readability boolean chain; results pre-grouped Map, reduced allocation string
  accumulation and a named issuer renderer. 1,680 filter cases and 512 rendering
  cases passed exact equivalence; identities/order retained.
- Filter bracket: speed beats memory; speed beats boolean-chain readability;
  incumbent beats speed. Results bracket: named renderer beats string accumulation;
  named renderer beats Map; incumbent beats named renderer. Incumbents hold both.

Justification:
- Guard clauses build the searchable string once per record and express criteria
  plainly; the boolean alternative repeats string construction for every term.
- Eight records/three issuers show no performance pressure that justifies extra
  Map/loop state or string mutation. No performance gain is claimed.
- Existing render scope keeps escaping, grouping and pinned links reviewable
  together; the additional helper offered no demonstrated contract improvement.

Verification: focused DOM suite **26/26 pass** after the final code/build changes;
JS syntax checks passed. Local asset hash checks passed. Detector ran once after
visual assessment: **87 flags (5 warnings, 82 advisories)**. Three 11px text
warnings concern approved compact metadata, not body prose; flush tab padding is
intentional; Red Hat parsing is a false positive (computed font verified).
Token advisories describe shades/radii/type sizes beyond the sparse token list,
not 87 distinct user-facing defects. No new material issue from this scan.

Run bookkeeping: target slug apps-issuer-library-designs-index-html; no ignore
file. Review tabs stayed in the background. Read-only browser evaluation prevents
overlay injection, so native screenshots/DOM measurements supply evidence. No
critique live server was started. Existing preview server remains the deliverable.
Review-only tabs closed and temporary viewport override reset. Separate critique
snapshot/trend persistence omitted under AGENTS.md's one-record instruction;
this record holds the review. Two priority issues resolved; questions skipped.

Final code — retained tournament incumbents:

```js
function filterLibrary(records,filters) {
  const terms=filters.query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return records.filter(record=>{
    if(filters.sector!=='all'&&record.sector!==filters.sector)return false;
    if(filters.content!=='all'&&record.content!==filters.content)return false;
    if(filters.module!=='all'&&!record.modules.includes(filters.module))return false;
    const searchable=`${record.issuer} ${record.key} ${record.run} ${record.period} ${record.sector} ${record.modules.join(' ')}`.toLowerCase();
    return terms.every(term=>searchable.includes(term));
  });
}
function libraryResults(records) {
  if(!records.length)return '<div class="library-empty"><h2>No matching issuers or runs</h2><p>Try a shorter issuer name, another sector or a different content selection. Clear filters to see all retained cases.</p></div>';
  return `<div class="case-list">${[...new Set(records.map(r=>r.issuer))].map(issuer=>{
    const matches=records.filter(r=>r.issuer===issuer);
    return `<section><div><h2>${esc(issuer)}</h2><p>${esc(matches[0].sector)} · historical cases</p></div><div class="run-list">${matches.map(record=>`<a href="${routeHref(record.first,modules[record.first].first,null,record.key)}"><strong>${esc(record.run)}</strong><span>${esc(record.period)}</span><small>${record.content==='reports'?`${window.DESIGN_WORKSPACE.reports.length} saved builds · separate delivery collection`:`${record.modules.length} retained module ${record.modules.length===1?'output':'outputs'}`}</small>${icon('arrow-right')}</a>`).join('')}</div></section>`;
  }).join('')}</div>`;
}
```

Delivery: updated module-screen-designs.zip contains 73 files, 5,279,248 bytes; ZIP CRC verified. Five fresh JPEGs in capture-provenance.json have measured dimensions and hashes. Earlier captures remain on disk but are excluded from this ZIP. Temporary review candidates removed after recording results. Preview remains http://127.0.0.1:53812/.

### 2026-11-05 — five UX fixes from the adversarial review (screen designs only)

Scope: `apps/issuer-library/designs/`, regenerated `artifacts/issuer-library/screen-designs/`,
`module-screen-designs.zip` and the CP-8 lines of `docs/visualisations/`. Applied by Claude
Code in this worktree, uncommitted. No provider call. No change to `apps/issuer-library/web/`,
Go code or any existing file under `runs/` or `deliverables/`.

Fixes:
1. Each run shows its own saved outputs, keyed `<run-folder>/<file>`, with an attempt chooser.
   Labels are Output available / Inputs only / No output found. Evidence does not cross runs.
2. Conclusion bands and chart notes quote retained text through locators. A moved quote, a
   quote cut through bold text or a missing pinned output fails the build.
3. Reports list the run they were built from and trace to it by SHA-256; the build fails
   unless each report has exactly one source match.
4. CP-8 now presents the run comparison (`runs/tdg-run-comparison-001/CP-8.md`), not the
   superseded post-mortem. The build fails unless CP-8 cites the compared reports' hashes.
5. Provenance tags appear only where an output declares them: 1,326 of 1,389 pinned items
   read "Not classified".

Checks:
- `node --test apps/issuer-library/designs/design.test.cjs` with `ISSUER_LIBRARY_JSDOM` set:
  41 of 41 pass. The 15 new tests use hand-written keys. The last 3 were watched failing first.
- Build guards fired on a doctored catalog: missing pin, bold cut, unmatched quote.
- Built-in browser: 32 routes at 1366×768 and 18 at 1280×720 had no overflow after one fix
  (2px on CP-6). A last pass over 12 routes showed no console error, failed page or
  "undefined" text. The native attempt selector changes route and content.
  `reports/tdg-fy2024-snapshot-7/preview.html` opens top-level.
- `diff -rq` against main: copied `runs/tdg-run-comparison-001/` and
  `deliverables/tdg-fy2024-snapshot-7/` identical. Bundle: 101 files, CRC clean, identical to
  the folder apart from earlier captures, which it now excludes.

Confidence review, repaired: `#undefined` CP-OS outline links; curated CP-1A catalogue link on
the wrong first page; bounded-scope tag lost from Evidence; Ford and Frontier periods taken from
a pin; tab losing the section of a non-default output.

Rewrite tournament, post-edit and inline with no agents. `collect_runs`: pinned branch extracted
to `pinned_fields`, `data.js` byte-identical. `declaredClasses`: incumbent holds; its forms were
calibrated against retained outputs and a merged regex only moved the complexity.

By design: CP-1A has no conclusion band (no genuine conclusion block). CP-8 cells keep the
handoff's missing spaces verbatim. The CP-8 audit page quotes the handoff's own words
"post-mortem" and "calibration".

Open:
- `.gitignore` ignores `runs/` here, so the copied CP-8 input stays out of a commit on this
  branch; main already tracks it. A fresh checkout needs it before `build.py` will run.
- Inspector basis text for T4.10 ("USD millions…") is still hard-coded.
- `artifacts/issuer-library/visualisation-map.html` still shows the old CP-8.
- `src/deploy_vii/methods/cp8.md` and this branch's `AGENTS.md` predate the CP-8 rule.

Not verified: the report iframe inside the gallery (the built-in browser blocks it; the page
opens top-level); the unzipped bundle in a browser (compared by file only); keyboard and screen
reader use beyond Escape returning focus; other browsers; contrast. Curated quotes were read for
sentence cuts, not re-checked against issuer filings.

### 2026-11-05 — open items closed; Deploy VII keyboard and search in the screen designs

Scope: `apps/issuer-library/designs/`, `.gitignore`, `AGENTS.md`, `src/deploy_vii/methods/cp8.md`,
`docs/reuse/legacy-cp8-decision-ledger.md`, `tests/test_connect_cp8.py`, the CP-8 lines of
`docs/visualisations/MAP.md` and `artifacts/issuer-library/visualisation-map.html`. Uncommitted.
Deploy VII read only (`src/deploy_vii/assets/app.js`, commit be92508). No change to
`apps/issuer-library/web/`, Go code or existing run files. No provider call.

Adopted from Deploy VII: `/` focuses search unless typing or modified; rail "Search (/)";
`kbd` hint; layered Escape (search text, inspector, navigator, with focus returned); arrow keys
along chart marks with no wrap; `aria-live` Figures and Sources groups capped at 6 and 4+4; status
word searchable. Addition: a capped group shows "4 of N". Not adopted: inspector tab arrows (the
gallery has no tabs); tally chips, Help and Print (not keyboard or search). Results stay in the
current run.

Open items closed:
- `.gitignore` now matches main, so `runs/` can be committed (198 files, gitleaks clean).
- T4.10 basis and chart head now read handoff text (T4.3 row, each row's qualification); the build
  fails if the row or unit no longer matches. Also dropped "issuer estimates", which the CP-1A cell
  does not say.
- `AGENTS.md` and `cp8.md` now equal main; `AGENTS.md` also gains main's Excel rule. The old
  method moved to the legacy record, and `tests/test_connect_cp8.py` now reads its guard limits there.
- The map page's CP-8 was regenerated from `MAP.md` by a one-off script; no generator exists.

Checks:
- `design.test.cjs`: 47 of 47. All 6 new tests and the matched-cell check were watched failing first.
- `tests/test_connect_cp8.py` with main's venv: 686 pass, 1 fail, same before and after.
- Map parity script: 23 `MAP.md` lines missing before, all CP-8; 0 after. No broken anchors or
  duplicate ids.
- Built-in browser with real keys at 1366×768: `/`, typing, Tab, Enter into the inspector, Escape
  twice, arrows, Enter and Escape on a mark. At 375×812: `/` and Escape returning focus to the toggle.
  No console errors or page overflow. Search over 3,092 items took 2 ms or less.

Confidence review, repaired: placeholder clipped at 1366 (search icon removed); numbered rows
listed as "3" (now "3 · NET SALES"); focus left on a hidden link when a hit matches the current
route. Verified fine: quotes escaped in labels; no blank titles; `W-Library` has only the page that
holds its search box.

Rewrite tournament, post-edit and inline with no agents: `renderSearch` and the keydown handler,
incumbents hold. Splitting adds lines without removing a branch, and caching has no measured need.

Open:
- `test_methods_file_keeps_the_adaptation_record` reads `docs/methods-drafts/cp8.md`, absent here
  and on main. Predates this change.
- On main, 7 tests in `tests/test_connect_cp8.py` fail; 6 are the guard-limit tests repointed here.
- `METHODOLOGY-REVIEW.md` here still differs from main (213 diff lines).
- `src/deploy_workflow/owners/cp8.py:418` comment still names `methods/cp8.md`.

Not verified: other browsers; screen readers; the map page as rendered (only the parity script
and anchor check ran); full Python suite (only `tests/test_connect_cp8.py` ran).
### 2026-11-05 — one Issuer Library web app; New run through the launcher; Windows hardening

Scope: `apps/issuer-library/`, its tests, and the engine files the Windows path needs. Users are
on Windows only (owner, 2026-11-05). Verified by Claude Code on macOS. No provider was called;
the browser and bridge runs replaced `LiveAdapter.complete` and used a placeholder key.

Changed:
- Gallery and working app are one web app: a rail across library, research workspace,
  deliverables, run activity, New run, search, settings and help. Deliverables open inside it,
  and link both ways to the module outputs they were built from.
- New run follows `owners/cpos_launch.py`: `prepare` for the offline review, `run_live_handoffs`
  for Start. Launcher deliveries are verified and listed. A stopped run shows the handoffs it
  accepted and publishes no report.
- Windows: an open workbook's `~$` lock file no longer refuses a run. Replacing a file waits out
  a scanner or reader holding it (`platform_io.replace`, `saveJSON`). A page load runs only
  `store.py` (0.65 s to 0.03 s per process, measured here). Review refuses a workspace too deep
  for a run before any spend. The packaged build reuses its pinned runtime without downloading.
- CP-8 guard tests read the retained legacy method, with a hand-written key.

Checked, on the branch merged with `origin/main`:
- Node 88/88. `go test -race` and `go vet` pass; Windows `go vet`, test compile and amd64/arm64
  cross-builds pass.
- Python store, app, launcher and CP-8 connection tests: 782 passed, 1 paid skip.
  `tests/test_method_cp8.py`: 622 passed.
- Chromium and Firefox, 82/82, over the 41 retained runs here: every section of every module of
  every run, a fake-provider run through the real bridge to a report, a stopped run, the links
  both ways, search and Reload. That pass found and fixed a Published model crash on a run with
  several unranked outputs.
- Compiled smoke test (macOS binary) against the engine folder extracted from the Windows zip,
  under a path with spaces and accents: PASS. Pages at 1280x600 and 1536x730 with scrollbars
  shown have no horizontal overflow.
- Mutation checks on the front end: 11 of 13 failed a test. The two survivors are a Start handler
  guard behind the disabled button and server check, and tab markup built while hidden.

Confidence review confirmed and fixed: a stopped run hid paid handoffs; a `CP-notes.md` or a bad
`workflow.json` took the whole library down; a symlink out of a run was read; two deliveries of a
module had one label; a hard-coded "Historical evidence" label sat on every new run. Verified
fine: `-X utf8` covers Windows text encoding, workers run with `CREATE_NO_WINDOW`, no import in
`src` or the engine is missing from the pinned wheels, hostile names stay text on every destination.

Rewrite tournament, inline: a readability candidate for `store.collect_runs` was applied. A
hash-once speed candidate lost (the full workspace loads in 0.19 s). `handoff_files`, `parseRoute`,
`installNewRun`, `reviewRun` and `bridge.start` hold.

Not verified: anything on Windows itself (no `.exe`, `Smoke-test.ps1` or Edge run; the sharing
violation fix was simulated); a paid provider call; WebKit, which hangs on a blank page on this
machine; `tests/test_method_*` other than CP-8, about 10,000 slow tests; `docs/visualisations/MAP.md`
rows for files changed since its catalogue date. HTML Model deliveries `tdg-model-1`, `-2` and `-3`
hold no report, so the library lists them in Settings as issues and does not present them.

### CP-1B handoffs → CP-OS → earnings report (2026-11-04)

**Progress: bounded replay publication, no fresh model run.** The actual retained
CP-0 → CP-1 → CP-1B answers from `runs/tdg-003` now populate five sections of the
existing earnings report design. No analytical executor/provider was called.
[Report](runs/cpos-tdg-earnings-001/execution/deliveries/25d29570b506ce5c1536ad3a0b564387598b0f1deed58e702d55e3787238b10f/report.html),
[frozen workflow](runs/cpos-tdg-earnings-001/workflow.json) and
[single verification record](runs/cpos-tdg-earnings-001/verification.json).

Amounts/columns, signed capex, 89/91-day windows, ordinary versus As Defined
EBITDA, unresolved 131/132 disclosure difference and missing guidance are retained.
The new presentation adapter performs no financial arithmetic. Seventeen prior
comparisons and two margin-point changes were independently rechecked with
Fractions. Publication retains 1,118 literal facts, 1,345 line citations and all
three exact handoff files. It contains HTML, JSON and Markdown only: Excel is
input-only, with no workbook export or completion gate. The full earnings preset
and native analytical acceptance remain unproven.

**Confidence review, ranked:** (1) table context: an isolated pre-guard reproduction
turned the Revenue matrix into one Value column; complete-table/table-block guards
now reject this; (2) call semantics: browser exposed “No judgement is recorded”
beside the actual earnings assessment; absence of CP-6 now explicitly means not
requested, while CP-1B's Medium-confidence assessment remains literal; (3) exact
values, missing/zero, units and source identities: boundary and original-line/hash
checks pass; (4) repeated/stale analysis and publication corruption: reuse,
changed-presentation, pin, retry, interruption, lock and tamper checks pass;
(5) native versus presentation proof: native CP1B layout validator still refuses
this broader answer; qualifiers remain partial/candidate/unrun. General Markdown,
other layouts and full pathway coverage remain outside this case.

**Rewrite tournament, post-edit, inline:** targeted `literal_module` and
`markdown_files`; `run_handoffs` and contract/dispatch changes were confidence-
reviewed under the two-symbol cap. Six full scratch candidates were checked for
actual byte parity, signatures and selector refusals. The speed parser changed a
preamble refusal into success and was disqualified. Winners: readability for the
paragraph loop (direct sentinel enumeration, fewer allocations, identical lines),
and memory for publication (one file map, no extra cache/helper, identical bytes).
Exact brackets, final fenced code and caller-impact checks are in the case record.

Validation: the five-file focused pytest command in that record passed **95 tests
in 15.38s**; Ruff and three-file mypy passed. Browser confirmed exact Revenue line
71/hash, assessment, definitions, missing guidance and corrected CP-6 status.
Local server stopped. Older publications remain untouched; layout-only changes
reuse the same three response requests. Twenty-four other CP-OS definitions are
AST-identical to the pre-edit snapshot.

A broader legacy `test_owner_cpos` fixture failed before navigation, during native
CP-MODEL publication: T4.9 mixes `currency USD US$ m` and `MILLIONS USD` in one
column. Its retained publication error traces through `OwnerWorkflow.publish`
to `_scale_of`, outside the handoff adapter. The broad check was interrupted after
95 passes and that setup error (203.36s). No native unit guard or fixture was
weakened; this failure remains recorded separately from the verified replay route.

### CP-1D/CP-1E → CP-OS → quality/debt report (2026-11-04)

**Progress, retained-answer replay.** The actual CP-1E alias request now orders
CP-0 → CP-1 → CP-1B → CP-1D and publishes eight selected earnings sections.
[Workflow](runs/cpos-tdg-quality-001/workflow.json),
[report](runs/cpos-tdg-quality-001/execution/deliveries/c93479b08736770845f403c97825fc55c86c2e1ea58a39ca876056c7a13e849b/report.html)
and [single verification record](runs/cpos-tdg-quality-001/verification.json).
The checked quality/debt answer was already actually consumed by CP-2; this turn
connects it to delivery without another analytical execution or production edit.

Reviewed actual instructions/output, the source annual bridge/lease passages and
the pension-table image. The selected CP-OS skill's analytical seven/six-stage
method matches its retained hash; the exact skill and schema sources are restored
under the existing archive with revision e67bf0c. Current project transport and
output rules govern; no historical approval/export process was introduced.

Independent integer/Fraction checks confirm annual 3,813 + 360 = 4,173; quarter
1,087 + 13 + 25 − 64 = 1,061; known debt 24,880 + 62 + 19 = 24,961; eight ratios;
and leverage deltas +0.0212x/+0.0194x from unrounded quotients. Gross pension
liabilities 3 + 16, separate asset 13 and net deficit 6 are distinct. No second
addition of leases/securitization already in carrying debt, no complete-debt
claim, no quality-earnings haircut and no quarterly/LTM substitution.

An independent parser compared all thirteen delivered analytical tables exactly:
57 rows, 227 cells including row labels, matching headers and one occurrence each.
All five earlier blocks are exactly equal. All 1,598 original-line/hash citations
across 1,308 literal facts passed. CP-1E exposes one CP-1D artifact; repeat CLI
execution returns the same report with four retained response requests and one
completion. Exact publication/file-set checks pass. No Excel output or provider
call. Five production source hashes match the prior 95-test verified revision;
those regressions were not rerun or claimed as fresh analytical proof.

Browser confirmed negative quarterly (64), the recurring-cost challenge,
Medium-confidence/unresolved earnings assessment, 53.63%/49.01% annual conversion,
24,961 known subtotal, zero duplicate additions and unavailable full total.
The pension subtotal opens exact CP-1D line158 and hash02403f… . Server stopped.
Data/selector review found no new defect or justified source-code change; global
code-review/rewrite gates are inapplicable to config/docs/retained-data work.
Full earnings preset, complete debt/quality evidence and other pathway work
remain open. The active goal is not complete.

### CP-5/CP-5A — actual host review → targeted repair → delivery (2026-11-04)

**Progress.** CP-OS actually requested CP-5 after the four checked retained
CP-0/CP-1/CP-1B/CP-1D handoffs. CP-5A dispatches once to CP-5; no extra reviewer
process, memo or provider was used. The actual host saw preceding context and
frozen expectations, so this is not independent-context or native qualification.
[Frozen workflow](runs/cpos-tdg-assurance-001/workflow.json),
[final report](runs/cpos-tdg-assurance-001/execution/deliveries/d7e9aed9c0da5d2bc7b91f839456c0a0e449a6f200e82d36d5ba335f5351da66/report.html),
[single verification record](runs/cpos-tdg-assurance-001/verification.json).

The twenty-assertion review exercises the five-driver trace, original sources,
calculations/definitions, five auditability dimensions, eight QA audit lanes,
issue/clearance work and four explicitly counterfactual false-claim probes.
The controls are not actual producer findings or a measured independent-model
failure-detection rate. The actual evaluated producers retain two disclosed
Material restrictions: source coverage and the unresolved 132/131 equivalents
difference. No Critical producer error or unrestricted/current/legal/market
clearance was invented. Reported cash remains authoritative; the event difference
restricts disaggregation/reconstruction, not the reported closing balance.

**Observed model repair:** first answer ab3001… incorrectly called computed
carrying/net debt Directly Sourced. Reported H4 components still require addition
and subtraction; their calculated result has Calculated lineage. A new targeted
CP-5 request was retained before the repaired answer dbf884…; the earlier answer,
reviews and publications remain. Financial values, support verdicts and source
findings do not change. The unchanged helper now uses five Directly Sourced,
ten Calculated, two Analyst Inference, one Conflicting and two Insufficient
Information claims. E74.0/C100/S0.7/P30 yields raw29.08, independently727/25,
rounded29 / Insufficient Information / Restricted. Trace fields180/180 are
bookkeeping, not full underwriting completeness or financial accuracy. Severity
was not adjusted to improve the band; other analysts' qualitative views remain.

**Actual consumption:** delivery retains the exact repaired CP-5 answer and all
seventeen assurance tables (86 rows), with its prose, source/issue details and
clearance. All eight analytical blocks are unchanged. All2,042 original-line/hash
citations across1,670 literal facts pass. Final report SHA:
7aefaafe77068bc6fb066911332e325d0da66dc78a1ae537dbac9258bb577fc7.
Browser confirms C04 Calculated, the corrected score/Restricted use and exact
line101/hash dbf884… . A copied replay banner was also corrected to distinguish
four reused upstreams from actual host review; the explicit replay manifest
labels all-five-answer replay. Replay retains identical handoff/View/ReportView
bytes and no new model analysis. Local verification server stopped.

No production code or tests changed; five production source hashes match the
previously verified revision. Confidence-review/rewrite code gates do not apply
to these model-output/config/docs/data changes. One analytical instruction
amendment records claim-level derivation before lineage scoring. No Excel output,
credential read, paid call, subagent or predecessor mutation. Other modules,
full pathways and requested deliverables remain active work; the goal is not done.

### CP-2H → CP-OS → historical ratings report (2026-11-04)

**Progress, retained-answer replay.** The actual four Ford Otosan handoffs now
reach the [ratings report](runs/cpos-ford-ratings-2024-001/execution/deliveries/8840802b892e729314078d335ecd5a0965d67e9ad32f5b34468daae73a321f56/report.html).
[Workflow](runs/cpos-ford-ratings-2024-001/workflow.json) and
[single verification/review record](runs/cpos-ford-ratings-2024-001/verification.json).
No new analytical/provider run or CP-2A output was manufactured. The actual prior
CP-3C consumer contains the exact final CP-2H hash.

The exact pre-edit CP-OS refuses this case because the legacy CP-2G requirements
expand into CP-2A and demand another instruction/analytical build. Existing
`registry.dependencies/plan` now accept the pinned consumed-input graph for
reused answers. Fresh/default requirements stay unchanged: 347 canonical, alias,
preset and pair plans match the pre-edit implementation. CP-5 fan-in, canonical
ID/cycle checks and source/upstream verification remain. This is a reuse boundary,
not an independent assertion of historical authenticity or native acceptance.

Presentation now supports an explicit standalone heading/question and declared
legal/brand names in the title or Request. The case's CP-0 explicitly identifies
Ford Otomotiv Sanayi A.S. (Ford Otosan); generic historical headings are retained.
A source-only foreign-name control refuses. An adversarial whitespace alias
initially bypassed identity matching; nonblank alias/heading validation fixes it.
The existing ratings block is reused without labelling Ford a distressed issuer.

All ten rating tables match exactly once: 27 rows / 79 cells including row labels.
All252 original-line/hash citations across150 literal facts pass. Nine independent
Fraction ratios and source-minus-subtotal residuals −1/+1 are preserved; missing
source adjustments stay null. True Fitch headroom/crossing and sustained windows
remain indeterminate; the S&P15pp geography distance is explicitly a proxy.
Browser confirmed dates, preliminary/expected states, standalone heading, those
qualifications and exact CP-2H line64/hash4f390c… . Server stopped. CLI resume
returns the same report with four retained requests and no executor call.

**Confidence review:** traced fresh-versus-retained planning, stale pins, cycles,
mutable input snapshots, CP-5 ordering, issuer declarations/blank aliases,
financial/period preservation, default consumers and publication compatibility.
Confirmed boundary/blank-alias defects were repaired; wider model/current/native
claims remain unproved. The initial pin check failure was traced to only CP-8's
user-required title/purpose replacement versus the ancestor catalog. Updated only
that catalog hash in PINS, preserving its prior copy; no financial oracle changed.
All219 pins now match.

**Post-edit rewrite tournament, inline/no agents:** targeted `dependencies` and
`markdown_files`; thin keyword forwarding/CP-OS call wiring/layout fields were
confidence-reviewed. Six full scratch candidates tested. Registry memory variant
reread changing input and spuriously added CP-2A, so disqualified; speed/readability
added allocation/indirection. **Registry incumbent holds.** Markdown memory wins:
stream slots instead of storing a temporary list, with nonempty-bound invariant,
same signatures and exact bytes in three real publications. Full fenced final
code, three-bullet justifications, brackets and impact sets are in the case record.

Validation: **143 passed in16.50s**, Ruff and four-file mypy passed; src compileall
passed. Exact prior earnings, quality/debt and assurance publications also verify
unchanged. The actual changed definitions are limited to dependencies/plan,
run_handoffs, MarkdownLayout and markdown_files. Older run/source directories and
predecessors were not edited. Overall modules/aliases/pathways goal remains active.
