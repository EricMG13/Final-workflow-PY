# Review of the revised reuse plan, e56ee97c

**Verdict: keep `2c809379` and the existing S1A snapshot as the first target; correct the execution and acceptance contracts before a paid run.** The reuse direction is sound. The claim that the remaining work is only 100–150 source lines is an unverified estimate, not evidence that the plan is executable or that its output will satisfy the user.

Reviewed the exact diff from `e039dec9` to `e56ee97c`, the revised plan and `work/claude-resume/REUSE.md`, relevant source at the selected base, and retained artifacts. No product source changes, paid calls, credentials, subagents, commits or pushes were involved.

## Findings requiring plan corrections

### 1. High: the documented live command is rejected before execution

The revised plan at lines 334–335 defines `W=artifacts/tdg-slice/...` and passes it as `--runs-root`. `check_settings` explicitly rejects a relative runs root for live runs, to prevent separate worktrees from maintaining disconnected account ledgers.

A direct call to the existing precheck reproduced:

> `DriverError: --live needs an explicit absolute --runs-root`

Use one explicit absolute shared accounting root. The output can be partitioned by week/day underneath it. Do not relax the root check to make the example command pass.

Evidence: [plan command](</Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673/docs/superpowers/plans/2026-11-04-tdg-daily-slice.md:334>), [existing precheck](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/src/deploy_workflow/model_testing/run.py:183>).

### 2. High: the weekly-cap formula still permits separate provider allowances

Task 2 still specifies `week_cap - account_spend(runs, provider, settlements)`. That function filters by provider. A $60 allowance therefore becomes separate OpenAI and Anthropic allowances when Task 5's weekly Opus run is used. Its proposed tests only use `sol-medium`, so they do not detect this.

A weekly root also hides older spend from `cap_for`, which uses the same loaded runs to calculate account capacity. Keep account-wide history and compute a separate shared weekly view. Reuse existing durable debit reconciliation and locking. Add a mixed-provider case and a previous-week account-spend case; the existing crash-reservation requirement remains relevant.

Evidence: [Task 2 formula](</Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673/docs/superpowers/plans/2026-11-04-tdg-daily-slice.md:191>), [provider-filtered accounting](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/src/deploy_workflow/model_testing/budget.py:185>).

### 3. High: the S1A scope is not propagated through the replay precheck

Task 1 adds `delivery_scope` only to the final `run_pathway` call. The existing `check_reruns` separately calls `check_arguments` without a delivery scope. Once the daily loop supplies `--replay-from`, that precheck constructs the full-preset pack while the earlier run used S1A. `check_same_pack` correctly rejects this difference.

Pass the chosen scope through both precheck and execution, and test the actual driver rerun path. Also forward the new pathway/config selection consistently to each `plan_runs` caller; it is used by both `run_stage` and `check_reruns`.

The existing `test_replay_pack_identity_rejects_an_omitted_scope` passed during this review. It confirms the rejection is deliberate, not an assumption about replay.

Evidence: [replay precheck](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/src/deploy_workflow/model_testing/run.py:535>), [scope-omission regression](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/tests/test_public_s1a_scope.py:244>).

### 4. High: exporting recordings does not implement the stated next-day replay

The daily offline command omits `--delivery-scope` and does not select or preserve yesterday's run identity. The adapter indexes replies by invocation digest and call index. The digest includes run ID, prompt hash, upstream hashes, module, step and attempt. The driver generates run IDs from the chosen runs root.

A direct digest check confirmed that changing only `slice-sol-medium-credit_snapshot-1` to `...-2` changes the lookup key. A fresh scratch root can instead select the first run's ID, which is also not a reliable way to select yesterday. Existing recordings can remain reusable, but the command needs an explicit retained-run identity and the same scope/input/prompt contract. Do not strip identity checks or rewrite recordings to make lookup succeed.

Keep recorded-response replay distinct from `--replay-from --repaired`, which reuses compatible upstream submissions and runs the repaired module **and its downstream consumers** live.

Evidence: [daily command](</Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673/docs/superpowers/plans/2026-11-04-tdg-daily-slice.md:356>), [digest inputs](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/src/deploy_workflow/model/record.py:427>), [adapter lookup](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/src/deploy_workflow/model/adapter.py:282>).

### 5. High: S1A needs its own acceptance result now

The existing scorer iterates every module in the full `credit_snapshot` preset. An absent module cannot pass, and `PathwayScore.passed` requires every module to pass. Merely forwarding the S1A scope will leave deliberately unrequested owners scored as absent/failing. Preserve full-preset scoring, but define a distinct S1A acceptance result based on its selected modules and required financial output.

The five S1A front sections are `key-findings`, `company-operating-model`, `strengths-weaknesses`, `company-profile` and `transaction-summary`. They do not include the full preset's financial-table/chart-strip sections. The route includes CP-MODEL and can expose underlying financial data, but section existence or a page of gap messages does not prove that the user received a useful populated financial deliverable.

Move the **S1A** output comparison before the first acceptance attempt. Keep the broader twelve-section comparator for the later expansion if desired. Check the actual Model/report values, units, dates and provenance against existing keys, and state which specific gaps are allowed. Repair the already-reproduced typed-unit errors before paying to encounter them again.

Evidence: [full-preset score loop](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/src/deploy_workflow/model_testing/pathway.py:122>), [overall pass predicate](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/src/deploy_workflow/model_testing/pathway.py:191>), [S1A sections](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/src/deploy_workflow/owner_rendering.py:385>).

### 6. Medium: the cited export/replay test is currently failing

Ran `tests/model/test_o5_done_when.py::test_a_live_shaped_run_archives_raw_and_replays_to_the_same_records` unchanged on `2c809379`. It failed before replay with `BudgetExhausted: reserving 5.310000 passes the cap 1`.

A controlled, in-memory fixture change to a $10 cap allowed both the fake-live run and the replay to reach `valid`. The test then failed its record-equality assertion. The only non-timing differences were `reserved_usd`: live reserved `5.310000` for both calls; offline replay reserved `0.04152500` and `0.04513500`.

Root cause: the loop deliberately uses the context-ceiling reservation for an adapter with a live ruling and estimated-token reservation for an offline adapter. The fixture's $1 cap and identical-reservation expectation no longer match that behavior. This does **not** demonstrate a broken response replay engine. It does mean this test cannot currently be cited as passing proof on the selected base. Update its fixture/expectations while preserving separate assertions for each accounting policy. No fixture/source file was changed in this review.

Evidence: [cited test](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/tests/model/test_o5_done_when.py:354>), [reservation policy](</Users/ericguei/.codex/worktrees/product-epc-a01-final/Deploy Workflow/src/deploy_workflow/model/loop.py:573>).

## Correct the evidence and estimate

- **6522 is not the only retained TDG run with five valid CP-1 steps.** The later retained `issuer-pdf-sol-medium-tdg-fy2024-20261103-80aeb7a0e7` snapshot also records `source_context`, `financials`, `narrative`, `readiness` and `quality` as valid. Its CP-1 head is restricted and the run stops at the CP-1A `FinancialBinding` error; it has no delivered report. Use both attempts when selecting reusable evidence, without promoting either to end-to-end success.
- The inventory says every historical hybrid cell needed a financials repair. Its retained Sonnet summary instead records first-submit acceptance for financials and a repair at narrative. Accepted historical steps remain useful evidence; details should come from the retained summaries.
- All eight named TDG JSON keys do exist at `d0909abe` and match the working-tree bytes. The plan's `git show` import is valid for these files. This corrects the overly broad warning about uncommitted keys in my preceding audit; unrelated uncommitted work still exists in that checkout.
- OPEX and exact-period binding remain real implementation work. The sum is small; preserving both source components through existing financial contracts and validating exact fiscal dates is the acceptance requirement. Count completion by that behavior, not by a predicted line count.
- Do not automatically drop the typed layer after two failed fix rounds. The proposed fallback is untested and explicitly restores the share-count-as-money defect. Keep it as a measured alternative only if it passes the same quantity, period, provenance and output checks.

## Execution recommendation

Keep the existing S1A scope and chain tip. Fold the corrections above into the current tasks; no new framework, repository or broad audit is required. First establish one bounded S1A report with its required financial data compared against the existing keys. Then expand the scope when the smaller deliverable is proven. Calendar labels such as “day 2” or “week 2” should not substitute for those acceptance conditions.

Verification in this review: one existing scope-identity regression passed; the cited export/replay regression failed unchanged, then reached valid replay under a controlled fixture-budget probe and failed only the outdated reservation-equality assertion. The live-root and recording-identity counterexamples were reproduced without network/provider calls. No full test-suite or end-to-end live pass is claimed.
