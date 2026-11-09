# Reuse audit — 4 November 2026

The next attempt should be an integration and repair pass over existing code. The runner, provider adapters, financial kernel, recording exporter, replay mechanisms, PDF extraction, report renderer and most TDG answer keys already exist. The proposed daily-slice plan should be shortened and reordered around producing and checking one TDG report.

This audit does **not** establish that a complete, accurate TDG report can already be produced. It identifies the components to retain, the remaining defects, and the work that can be removed from the proposed build.

## Coverage and limits

- Inventoried **26 distinct Git stores**, **38 located checkouts**, **2,951 local/remote-tracking branch refs**, and **536 registered worktree paths**. These counts include independent coordinator clones and unborn prototype stores; they are not counts of independent completed implementations.
- **518 worktree directories exist; 18 are missing.** Checked existing worktrees for tracked and untracked source changes: **27 contain source changes**. This includes work that would be missed by looking only at branch tips.
- Searched source-path history across all available refs and targeted commit history for financial composition, periods, recording, budgets, delivery and report work. Inspected candidate implementations and their contracts, not every line of every historical revision.
- Covered the original Credit Operating System, CAOS/LangMVP/Final, CAOS v2/workbench/Databricks/Firebase, Deploy V/VI/VII, Deploy Workflow and its coordinator clones/worktrees, the independent Deploy Workflow Codex implementation, prototypes and three ZIP archives.
- Deleted worktree-only files, unreachable Git objects, cloud-only sessions and remote changes absent from local refs are outside this inventory. No claim is made that those contain nothing useful.

Machine-readable evidence: [repository inventory](REUSE-INVENTORY.json), [historical candidates](REUSE-CANDIDATES.json), [worktree source changes](REUSE-WORKTREE-CHANGES.json). These are inspection snapshots, not permanent branch locks.

## Keep one implementation base

Use `codex/product-epc-a01-final` at **`2c809379`** as the integration base named by the existing plan. Its local checkout is `/Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow`.

This tip contains the CP-1 chain work at `130880a4`, the generic owner binding fix at `8e998240`, the typed producer changes and the later share-family correction. Important Phase A R1 files at `79b86720` already have identical bytes here: `statement_compose.py`, `unit_maps.py`, `owner_workflow.py`, `deploy_vii/model_interface.py` and `deploy_vii/financial_adapter.py`. Repeating that port would duplicate completed work. Replacing this tip with the whole Phase A branch would also lose later work: the source diff toward Phase A R1 removes 1,379 lines and adds 231.

Of 26 source files in the uncommitted Phase A worktree, 24 match committed R1. The two differences are an earlier share-family implementation and prompt wording about reopening an invalid step. They are specific review candidates, not another implementation to merge wholesale.

Preserve the checkpoint-side TRACE display fixes too: `08ea8885` and `35068338`, reflected in checkpoint `9f925b2b`, change `src/deploy_vii/assets/app.js`. The source delta on that side is one file, 30 additions and three deletions. It does not require another general port.

The current reuse manifest already records **88 Python modules / 115 imported files**, originally imported largely from DEPLOY VII `64415539`, followed by 183 patch records. Financial calculation, report construction and other inherited services should continue from these patched versions. Copying the older originals again would discard fixes. See [the import manifest](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/docs/reuse/manifest.json>).

## Concrete reuse map

Paths in the first seven rows are relative to the selected base above.

| Needed behavior | Existing implementation | Remaining work |
| --- | --- | --- |
| Run one issuer/pathway/configuration with a cap | `src/deploy_workflow/run_pathway.py:1084`, `run_pathway`; `model_testing/run.py` | A small selection/CLI adapter if desired. Do not create a new runner. The public API already accepts case, pathway, model, cap, output location and replay parameters. |
| Charge accounting and crash protection | `model/budget.py`; `model_testing/records.py`; `model_testing/budget.py:185`, `account_spend` | Add the weekly aggregation to the existing durable accounting and locking. Retain reservations, unknown charges and settlement matching. |
| Export and replay actual replies | `model/record.py:692`, `export_recording`; `model/adapter.py:282`, `RecordedAdapter` | CLI glue, selection of the retained run, and preservation of replay identity. No new recording format or replay engine. |
| Retain upstream submissions after a downstream repair | `replay.py:311`, `plan_replay`; `check_replay`; `run_pathway(replay_from=..., repaired=...)` | Use the existing identity and dependency checks. This is distinct from replaying recorded model responses. |
| Financial calculation and typed report data | `src/deploy_vii/financial_adapter.py`, `model_interface.py`, `model/`; `statement_compose.py`, `financial_workflow.py` | Repair known typed-unit defects, propagate derived OPEX source evidence, and bind exact fiscal periods. Keep the existing arithmetic/kernel. |
| Public report output | `owner_rendering.py:408`, `PUBLIC_DELIVERY_SCOPES`; `run_scopes.py`; inherited `deploy_vii/report_view.py` and rendering assets | Extend the existing bounded public scope to the full preset and check required sections/data. No replacement renderer. |
| TDG PDF extraction and comparison inputs | `cases/cp1-chain/{expected.json,tdg-financial-reference.json}`; `tests/fixtures/pdf_pages/TDG`; `pdf_headers.py`; `work/cp1-chain-runtime/audit.py` | Reuse the fixtures, key data and financial-row/period checks. The existing audit is bounded to its retained source/scope and must be adapted for full-report acceptance. |
| Independent TDG expected values | `codex/pretesting-completion`, local HEAD `d0909abe` plus uncommitted case files | Select the key files and applicable comparator helpers. Do not merge the entire large test branch. |
| Report completeness, links and chart/data parity examples | Independent `deploy workflow Codex`, HEAD `2e3966d`; `workflow_codex/delivery.py`, `credit_snapshot.py`, existing tests and saved outputs | Adapt checks and presentation examples across the contract boundary. Importing its separate execution model would create another integration project. |

### Select the existing TDG keys

The source checkout is `/Users/ericguei/.codex/worktrees/pretesting-completion/Deploy Workflow`. Follow-up verification confirmed that all eight JSON keys listed below exist at `d0909abe` and match the working-tree bytes. Import from that commit. Other uncommitted work in the checkout should be reviewed separately.

- `cases/extraction-port/tdg-four-filing-statements-expected.json`
- `cases/model-publication-keys/tdg-operating-expense-inputs-expected.json` — 13 period occurrences and 52 source primitives.
- `cases/model-publication-keys/tdg-income-frame-expected.json`
- `cases/model-publication-keys/tdg-period-eligibility-expected.json`
- `cases/model-publication-keys/tdg-direct-da-supplement-expected.json`
- `cases/model-publication-keys/tdg-issuer-reconciliations-expected.json`
- `cases/charts/tdg-credit-source-key.json`
- `cases/deliverable-contracts/tdg-credit-snapshot.json`

There are also existing `cases/prove/epc_a01.py`, `owner_submission_boundary.py`, `source_review_support.py` and `opex_legacy_compatibility.py` checks. Their scope matters: a legacy compatibility check is not the missing assertion that the current Model consumes the correct TDG OPEX amount. The deliverable contract still identifies its comparison command as missing. The keys are reusable; the complete acceptance connection is not already finished.

## Earlier attempts: what to salvage

| Attempt/family | Useful material | Disposition |
| --- | --- | --- |
| DEPLOY VII and Deploy VI | Financial arithmetic, statement/period handling, report assets, ledger failure scenarios | Much of the applicable kernel is already imported. Retain current patched versions; selectively recover regression cases. Earlier EBIT/OPEX handling does not supply the missing source-backed OPEX composition path. |
| `deliverable-design` Workflow worktree | Uncommitted `evaluation/` framework, campaign budget tests, reporting/scoring utilities, public preparation and report previews | Preserve the 44 source changes. Borrow relevant crash/concurrency tests and report examples. Its 12-cell, $100 evaluation campaign and large native runner are not a drop-in daily TDG/$60 controller. |
| Independent Deploy Workflow Codex | Actual saved seven-file synthetic credit-snapshot bundles, financial/report checks and several owner implementations | Reuse acceptance examples and isolated checks. Its fixed source IDs and separate execution/data contracts require adaptation; it has no demonstrated arbitrary-issuer live PDF path. |
| CAOS Databricks/v2/workbench/Firebase | Canonical deliverable assembly, citation checks, HTML rendering, run failures and database budget/lease tests | Use applicable cases and assertions. The PostgreSQL artifact/run model is incompatible with the current filesystem runtime; wholesale adoption adds migration work. |
| Original COS, CAOS/LangMVP/Final | Financial cases, source handling, period logic and historical runtime evidence | Inspect specific cases when they match a remaining failure. Older inferred-period or floating-point calculations must not replace current exact/source-bound contracts. |
| Documents/Credit Operating System prototype | Uncommitted module/tool code | Preserve it, but its legacy CP-1 means capital structure, not the current financial foundation. Matching module names do not establish compatibility. |
| Deploy V, ZIP archives, COAS-V3 and demo/front-end repositories | Methodology validators, export/report examples, UI assets | Useful references and possible regression inputs; no inspected component supplies the missing full TDG proof path. |

The broad search did **not** locate an implemented, verified replacement that already solves all three remaining financial problems: typed quantity enforcement, source-backed multi-row OPEX propagation, and exact reported-period binding. This is a targeted search result, not proof of absence from every unreachable revision.

## Recovered deliverables that already exist

The independent Codex implementation saved both positive and missing-history synthetic credit-snapshot bundles on 28 October. Each contains `report.html`, `Model.html`, `full-analysis.html`, `evidence.html`, `limitations.html`, `calculations.json` and `index.html`.

- [Open the existing positive report](</Users/ericguei/Documents/Codex/2026-10-28/cla/outputs/credit-snapshot-positive/report.html>)
- [Open its bundle index](</Users/ericguei/Documents/Codex/2026-10-28/cla/outputs/credit-snapshot-positive/index.html>)
- [Open the missing-history report](</Users/ericguei/Documents/Codex/2026-10-28/cla/outputs/credit-snapshot-missing-history/report.html>)

This audit recomputed all 14 file sizes and SHA-256 hashes against their saved verification receipts; all match. Both compressed tool-receipt files also match their recorded SHA-256 hashes. The saved receipts describe 13 actual synthetic workflow stages. Their thousands of tool receipts are runtime tool calls, not thousands of paid model calls.

These are concrete reusable report artifacts. They establish synthetic delivery in that implementation; they do not establish live TDG financial accuracy. This audit did not rerun those entire pipelines or inspect the reports visually in a browser.

## Corrections to the committed daily-slice plan

Reviewed plan: `e039dec9`, `docs/superpowers/plans/2026-11-04-tdg-daily-slice.md` on `claude/codex-development-stall-0305d5`.

| Original task | Reuse-based change |
| --- | --- |
| 0: branch, ruling, context | Keep the chosen integration base and one integrator. Preserve existing evidence and the checkpoint-side display fixes. No repository restart. |
| 1: slice CLI | Thin adapter over the existing runner. The API can already run one case; CLI work must not become a prerequisite for discovering whether report production works. |
| 2: weekly budget | Extend existing accounting. Correct the proposed provider-local weekly calculation and preserve account-wide history. |
| 3: recordings | Wrap the existing exporter. Specify replay identity explicitly before promising next-day replay. |
| 4: full scope | Extend the existing renderer. A missing required section is a failure to resolve, not something to drop with a commit-message note. |
| 5: daily live loop | Put the first acceptance attempt after the already-known deterministic blockers are repaired and the report comparator is connected. Run subsequent attempts when a repair or new hypothesis warrants one. |
| 6–7: typed-unit defects | Keep as targeted repairs, using the existing probes. Bring them before the first paid attempt. |
| 8: keys/OPEX | Import selected existing keys; wire the actual Model-input comparison and source provenance. Reuse the financial kernel. |
| 9: exact periods | Retain current period/context validation and repair the source-date binding. Printed PDF year labels alone do not establish fiscal start dates. |
| 10: PDF/report comparison | Reuse the existing PDF case, fixtures and key material. Bring the report comparator into the first acceptance attempt. Preserve the user's pinned-corpus-first preference; a separate PDF-only full run need not be scheduled by an arbitrary “week 2” rule. |

Three concrete plan hazards need correction:

1. **The proposed $60 limit is per provider.** Task 2 says to subtract `account_spend(runs, provider, settlements)`. Sol and Opus could therefore each consume a separate $60 allowance. Calculate a shared weekly total across providers, including unsettled reservations. Keep the lifetime/account history separate from the week's view; making the runs root the current week must not hide previous account spend. Use the existing lock/ledger mechanism.
2. **Recording replay is identity-sensitive.** The existing request digest includes run identity and request context. A newly generated run ID or changed prompt can fail lookup even when the JSONL is present. A baseline replay needs retained request identity and matching inputs. Upstream submission replay after a repair is a separate existing operation with its own identity checks. Specify and test both, including intentional behavior changes after a fix.
3. **“Rendered” cannot become “correct.”** Task 4 permits dropping unrecognized section IDs; Task 10 delays comparison; the daily ledger measures frontier and an accuracy ratio. Required output coverage and provenance must also be checked, or an incomplete report can look successful. Gap banners are appropriate only for explicitly allowed source gaps, not for bypassing required financial output.

## What remains genuinely unfinished

The current defects are observable without a paid model call. Running the existing Review A probes against `2c809379` reproduced these examples:

- A diluted EPS value of `2.40` is accepted as monetary/MILLIONS while the correct per-share classification is refused; the gate accepts the wrong classification.
- A hand-written untyped EPS line passes `_column_failure` with `None`, has no statement issue, and becomes a USD monetary cell with a 1,000,000 scale factor.
- A thousands-denominated table can borrow a millions cue from another page.
- Mixed/negated share-scale cues and a euro-denominated source against a USD book are accepted incorrectly.

Those findings establish necessary repair scope. They do not establish that every TDG row is wrong or that the entire producer should be replaced.

The OPEX problem also extends beyond adding two numbers: the derived input must retain its source components and propagate through the Model/report contracts. Existing arithmetic and independent keys help; a new arithmetic engine does not. The source-period key likewise needs to drive exact date validation instead of inferred calendar periods.

Finally, the full public delivery scope and full rendered-output comparator still need to be connected. Existing bounded public rendering is useful evidence of machinery, not proof of the full preset.

## Shortest defensible next sequence

1. **Consolidate the selected existing code and evidence.** Use `2c809379`, preserve the checkpoint display delta, select the existing TDG keys and retain the actual live CP-1 artifacts. Do not import another execution framework.
2. **Repair known deterministic failures and connect acceptance.** Reuse the probes and keys for typed quantities, OPEX and exact periods. Extend the existing public scope and comparator so the next complete output can be judged immediately. Preserve required sections and provenance checks.
3. **Exercise the retained evidence, then make one bounded live attempt under the applicable ruling.** Replay what the existing recordings/submissions genuinely support; do not manufacture downstream replies to claim success. Use the existing budget machinery with the corrected aggregate cap. Retain actual responses for the next regression.
4. **Stop at the first concrete defect, repair it, and resume from the furthest valid compatible point.** The milestone is a populated TDG report whose required values, units, dates, source identities and links match the independent keys, with specifically permitted gaps explained. A daily cadence or more green unit tests is not itself that milestone.

This removes the need for a new runner, budget engine, replay engine, financial kernel, renderer, PDF extractor, oracle campaign or second evaluation framework. It does not justify promising a completion date before the integrated report attempt exposes the next remaining defect.

## Verification performed in this audit

- **13 selected existing tests passed in 2.50 seconds** on `2c809379`: cap arithmetic, crash-held reservations, durable debit reconciliation, recording export/replay, public scope selection, frozen TDG composition of 103 rows/280 cells, and printed PDF period mapping.
- Used the existing review-worktree virtual environment with `PYTHONPATH=src` in the selected base; confirmed the imported composer came from that base. Disabled bytecode and pytest cache writes. Its tracked working tree remained clean.
- Ran the two existing typed/gate probes; the defects above reproduced. Their exit status is not a passing correctness test—the printed counterexamples are the result.
- Verified the 14 recovered report files and both compressed tool-receipt hashes against saved receipts.
- No product source was changed, no paid/provider calls were made, no credentials were read, and no branch was committed, pushed or merged. No subagents were used. The committed daily plan and active heartbeat were left unchanged.
