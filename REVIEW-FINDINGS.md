# Independent review of the development-stall findings

## Revised direction and subsequent methodology comparison

The target experience is the Deploy V workflow used in M365: read issuer files,
perform the analytical method with tools, and write Markdown handoffs for inter-module
communication. CP-OS is the active orchestrator in this version, responsible for
module execution, handoffs, progress, bounded retries/resume and final delivery.
A separate agent or process, invoked by CP-OS, reads those handoffs and constructs
the deliverables defined in the Deploy Workflow project, reusing its existing
designs and generation code. The Markdown files are intermediate artifacts, not
the final user deliverables. The earlier recommendation below addresses defects
in the later runtime; it is no longer the recommended implementation direction.

The subsequent [cross-project methodology review](METHODOLOGY-REVIEW.md) qualifies
the Deploy V reference: preserve applicable later corrections and additions;
do not revert wholesale to the M365 revision. Later implementations also narrow
some methods, so selecting the newest repository alone would not preserve the
full analytical responsibilities. That comparison governs method selection here.

The stronger design-level finding is that an execution problem became a second
implementation of the analytical workflow. Later schemas, owners, settlement
states and renderer scopes introduced additional failure points between source
reading and a delivered result. Integration defects and deferred real executions
are supported contributors. They do not prove that the models cannot do the work,
nor that removing validation would make their answers correct.

I repeated this mistake in this session by importing the later runtime into the
new project and extending its gates before reproducing the Deploy V experience.
That implementation is unfinished and is paused for this direction correction.

References inspected directly:

- `/Users/ericguei/Documents/Deploy V/README.md` describes a folder-grounded
  package, indexed module selection, producer-before-consumer execution and
  rerunning only affected dependencies.
- The inspected M365 `skills/cp-os-credit-os/SKILL.md`, rule 7, says CP-OS never
  chooses or runs a module. That describes the M365 version only. The user's
  explicit direction for this version replaces that restriction: CP-OS becomes
  the active orchestrator; no additional competing controller is required.
- CP-1's entry and `references/REF_CP-1_STEPS.md` already define source reading,
  normalization, statement extraction, calculations, source references and gaps.
  Its scripts already include credit metrics and handoff checks.
- CP-MODEL already has a workbook exporter and input validation. CP-MEMO already
  defines report export, source mapping and document inspection. Reuse must be
  demonstrated at these interfaces, rather than inferred from file existence.
- Sampled VMEDO2 and Wood Mackenzie screenshots show populated analysis and
  explicit limitations. The VMEDO2 source-readiness screenshot permits financial
  work while restricting legal conclusions dependent on unreadable agreements.
  The October 23 tool-summary screenshot lists file operations, PDF extraction,
  selective OCR and Python execution. These are observable behavior references;
  screenshots alone do not verify the underlying figures or host internals.

Recommended implementation boundary:

1. Reuse the Deploy V-derived analytical instructions, calculation tools and
   Markdown handoffs with the later amendments identified in METHODOLOGY-REVIEW.md.
   Reuse Deploy Workflow's deliverable designs and generation code.
2. Adapt CP-OS into the active orchestrator: supply files, dispatch selected modules
   in dependency order, retain outputs, pass current Markdown handoffs, bound
   retries/cost, resume affected work and invoke delivery. CP-OS owns completion
   through the final checked deliverables.
3. Adapt M365-specific folder/connector access to local file access. Do not carry
   its chat navigation interface into an unattended controller, and do not build
   another analytical schema merely to dispatch a skill.
4. Add a separate delivery process that reads the actual Markdown handoffs and
   adapts their content to Deploy Workflow's existing generators. Prove the path
   from real issuer files through the required modules and their handoffs to a
   populated final deliverable. Handoff production alone is not acceptance.
   Keep the module's analytical depth; narrow the number of modules, not their
   substance. Missing analysis goes back to its producing module for a targeted
   repair; the delivery process must not invent it or rerun the entire analysis.
5. Check material figures, dates, units, source references and file usability in
   the delivered artifacts. A status label, schema-valid response or gap-only
   report is not that proof. Preserve missingness and restrict only conclusions
   whose required evidence is missing; infrastructure failure is not a source gap.

The local Deploy V package may postdate the saved screenshots; exact revision
equivalence has not been established. No Deploy V module or provider was executed
in this review. The earlier imported build has not produced a real-issuer report.

---

Reviewed 2026-11-04, in this session, without subagents.

**Verdict: retain the integration-first diagnosis, but revise the report before using it as a definitive root-cause account.** It identifies a real full-pathway rendering blocker and substantial integration failures. Several universal claims are contradicted by the retained records; its quantitative activity measures and attribution of responsibility overstate what the evidence establishes.

Review target: `claude/codex-development-stall-0305d5`, starting HEAD `9f925b2b`, including the then-untracked report at [work/claude-resume/ROOT-CAUSE.md](</Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673/work/claude-resume/ROOT-CAUSE.md>). During this review another session committed the documentation/review bundle as `e039dec9`; that commit changes no product source or tests. Product source was inspected, not changed. The named branch is attached at `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673`.

## 1. High: provider pauses are incorrectly equated with a prohibition on all admissible proof

Report lines 9–15 and 23 say the only admissible proof was prohibited and offline runs cannot reach a deliverable. The specification explicitly permits qualified offline host-agent execution with actual invocation and submission lineage, and distinguishes implementation-ready, offline-qualified and live-qualified evidence. See [SPEC.md:57](</Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673/docs/SPEC.md:57>).

There is also a bounded counterexample: [CP1-CHART-ACCEPTANCE.md:36](</Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673/docs/CP1-CHART-ACCEPTANCE.md:36>) records actual source calls, submissions, CP-1 settlement, Model publication, populated financial/chart output and browser comparisons. Its closure explicitly applies only to a synthetic case, with other owners and real issuers still open. It is not full live qualification, but it is neither an empty report nor merely a renderer test.

**Correction:** provider pauses prevented live-provider qualification during those periods. They did not prevent all useful integration proof, and the project demonstrably produced bounded offline deliverables. The failure is extending and preserving that proof through the complete required pathway.

## 2. High: the CP-1 frontier and model-capability conclusion are overstated

Report lines 47–53 say CP-1 never passed live and its five steps were valid once. That conflates contract-valid, settled, restricted, numerically checked and fully qualified output.

The retained review of run `80aeb7a0e7`, in addition to the earlier `6522e7ec93` run, explicitly records all five CP-1 steps valid, a restricted CP-1 head, and an independent bounded source comparison: 103 rows, 280 cells, 21 printed nils and five periods. See [tdg-80aeb-component-and-limits.md:5](</Users/ericguei/.codex/worktrees/pretesting-completion/Deploy Workflow/work/pretesting-completion/reviews/tdg-80aeb-component-and-limits.md:5>).

Those results still have substantial limitations: confidence 0 / Insufficient Information, nine open material findings, downstream readiness gaps, and blocked historical-quarter workbook readiness. This is not a fully correct or complete CP-1 deliverable. The same review carefully preserves these distinctions.

I inspected the retained live `run.json` and 27 call records for `80aeb7a0e7`. The stop really is the generic CP-1A submission being parsed as `FinancialBinding`, whose accepted module/step literals exclude CP-1A/business_context. Its recorded spend is $3.64421660. See [post-run-reconciliation.json](</Users/ericguei/.codex/worktrees/pretesting-completion/Deploy Workflow/work/pretesting-completion/releases/tdg-130880a4-20261103T191128Z/post-run-reconciliation.json>).

**Correction:** CP-1 has bounded, verified live component successes; full accurate real-issuer pathway qualification remains unproven. Harness failures obstruct model evaluation. They do not establish that model capability is irrelevant or was never measured.

## 3. High: the historical account omits later live progress

Report lines 25, 48–51 and 100–102 imply live work stopped in September and the only recorded COMPLETE run was on September 23.

The older repository records later live activity:

- [October 3 quality baseline](</Users/ericguei/Documents/caos-databricks/docs/rebuild/quality/2026-10-03-baseline.md:3>) covers nine accepted artifacts from October 2–3, including CP-1 with 19/19 registers, four anchored citations and one of two answer keys met.
- [decisions.md:1362](</Users/ericguei/Documents/caos-databricks/docs/rebuild/decisions.md:1362>), F685, records an October 17 live portfolio run `e2af059f` as COMPLETE. It also records a separate relative-value run accepting seven modules including CP-1, then blocking at CP-2G.
- [decisions.md:1370](</Users/ericguei/Documents/caos-databricks/docs/rebuild/decisions.md:1370>), F703, records a later relative-value attempt accepting nine modules before a CP-CF failure.

These records do not demonstrate complete semantic correctness: the COMPLETE portfolio run met only four of six keys; the longer runs stopped. The original $0.48 credit shortage is documented, but it was not a permanent end to live testing.

**Correction:** distinguish terminal execution status, accepted modules, answer-key coverage and accurate populated deliverables. The claim that September 23 was the only recorded COMPLETE run is contradicted by the repository's own history. I did not recover and independently replay the October 17 underlying run database; this finding concerns the report's claim about what was recorded.

## 4. Confirmed: full presets cannot pass the reviewed renderer's scope check

[owner_rendering.py:579](</Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673/src/deploy_workflow/owner_rendering.py:579>) requires an exact match on pathway, ordered requested modules and case kind. The reviewed branch exposes 18 scopes, all synthetic, with at most five explicitly requested modules.

I constructed each of the six actual `PATHWAY_MODULES` presets as a `Run` and called the existing scope selector. All six returned `owner_render_scope` for both valid case kinds tested: `synthetic` and `public`. This is a deterministic blocker irrespective of model quality. The full driver's finalization really calls that renderer: [run_pathway.py:637](</Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673/src/deploy_workflow/run_pathway.py:637>).

**Necessary qualification:** this result concerns the named branch and full presets, not every bounded rendering API or every unmerged branch.

**The proposed remedy is incomplete.** A new scope with honest gap banners is a useful diagnostic deliverable. It does not satisfy the user's requirement for accurate, fully populated required content. The specification expressly says missing implementations must not be disguised as input gaps. An acceptance check must distinguish expected source gaps, implementation failures and mandatory populated fields.

The TDG deliverable key still explicitly has `comparison_argv: MISSING` at [tdg-credit-snapshot.json:2327](</Users/ericguei/.codex/worktrees/pretesting-completion/Deploy Workflow/cases/deliverable-contracts/tdg-credit-snapshot.json:2327>). This is direct evidence that the intended whole-pathway comparison is unfinished.

## 5. Medium: replay exists; durable and reusable coverage is the missing part

No recording-like JSONL files were tracked at checkpoint HEAD. However, the main checkout's `artifacts/model-testing` contains 21 `calls.jsonl` logs and 524 archived raw responses. The framework already has recording export and a recorded adapter.

The [framework ledger:177](</Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/codex-findings-review-64c673/work/model-testing/framework-build-ledger.md:177>) says the pilot's four stops were reproduced offline at zero provider cost. Subsequent entries describe replaying the CP-0 recordings after fixes. A focused export-to-recorded-adapter test passed again in this review.

The ledger also explains an important limitation: changing the prompt changed invocation digests, so plain replay missed at call zero. Re-keyed old replies were correctly labelled plumbing checks, not new model evidence. The invocation identity includes run ID, step, attempt, upstream hashes and prompt hash; committing a recording file alone does not make arbitrary future executions replayable.

**Correction:** retain portable, redacted, version-bound replay bundles and comparisons. Preserve original live evidence separately from repaired/re-keyed harness exercises. An incomplete run can still provide valuable regression evidence for its successful prefix and its failure.

The report's assertion that there was "no cheaper way" to find harness defects is unsupported. Schema composition, real-source heading detection, context delivery and generic owner bindings can all be exercised offline. Existing replay work demonstrates this in practice.

## 6. Medium: the activity statistics are not reliable measures of effort or causation

I reproduced the large line-addition totals across all refs with merges excluded: `cases/` 1,415,063; `tests/` 199,810; `src/` 143,923. Source additions are about 5.94% of all additions. This supports the observation that much added text is outside product source. It does not measure time spent, value delivered or wasted effort. Repeated additions and generated/fixture content distort that inference.

The table's **"Commits touching" is mislabelled**. For example, its 1,647 for cases and 1,833 for tests match file-change rows, not distinct commits. Counting unique non-merge commit IDs per directory gives 332 for cases, 1,086 for tests and 741 for source in the inspected repository. Multiple changed files in one commit must not be counted as multiple commits.

Across the eight named repository locations I counted 10,814 commit occurrences but **9,622 distinct commit hashes**. `caos-v2` and `caos-workbench` share 1,192 commits. The report's approximately 10,800 total double-counts that shared history. Counts can move as other sessions write; these were read during this review.

The "six of seven live stops" table is not an exhaustive census: the framework ledger also records the earlier initial pilot's UnknownCharge and CallLimit failures, and rows group multiple configurations. Its broad pattern of harness failures is supported; its exact denominator needs a defined run inventory.

I did not independently recount the claimed 1,900 agents or inspect every transcript to attribute every rule to the user.

## 7. Medium: the proposed causes and remedies need stronger boundaries

Frequent transitions, disconnected branches, deferred testing and expensive review loops are credible contributors. They do not prove that each restart erased all useful evidence, that changing agent family caused the stalls, or that most responsibility belongs to the user. Existing acceptance records explicitly preserve earlier bounded evidence. Requalification of changed code is also legitimate; the failure is not making reusable proof survive that change.

Likewise, $3–$4 partial-run costs do not establish a roughly $5 full-pathway cost. The later daily-slice ruling sets $10/run and $60/week, which is an authorization ceiling, not demonstrated full-pathway affordability. This review did not exercise that authority.

The strongest supported diagnosis is:

> Product development and verification repeatedly progressed without a maintained, runnable acceptance path that takes representative source material through the exact supported orchestration, settlement, downstream consumers and rendering, then compares the required populated output with independent expectations. Local component successes and large quantities of keys did not close that integration gap. Provider pauses, restarts and coordination overhead amplified it, but cannot explain it alone.

## What to retain from the recommendations

1. Keep one repository and one representative issuer/pathway until its proof is repeatable. Reuse the existing bounded successes and retained live prefixes.
2. Make the full preset render and give it a runnable comparison with explicit required content and permitted source gaps. A diagnostic report is a milestone, not completion.
3. Reproduce known failures offline and establish a complete harness walk, clearly distinguishing scripted input from original live replies. Freeze prompt/source/code identities for replay.
4. Use bounded live runs to measure model behavior once known deterministic blockers are removed. Record the outcome and preserve the evidence whether the run succeeds or fails.
5. Measure progress by independently checked required output, unresolved blockers and repeatability. Treat agent counts, commits and passing-test totals as supporting operational data.

## Verification and limits

Three existing focused tests passed in 3.28 seconds:

- `tests/model/test_record.py::test_export_recording_replays_through_recorded_adapter`
- `tests/test_owner_rendering.py::test_fast_scope_table_rows_and_gated_rows`
- `tests/test_owner_rendering.py::test_fast_outside_scope_is_refused`

The separate read-only scope probe checked six full presets against synthetic and public cases: all twelve were refused with `owner_render_scope`. These checks establish the specific adapter/scope behavior, not full-pathway correctness.

No product code was changed, no provider call was made, no credentials were read, no subagents were used, and no commit or merge was performed. No full heavy suite, browser re-verification, complete workflow execution or comprehensive five-month transcript audit was performed. Historical successes above are explicitly scoped to retained records; they are not promoted to present-day qualification.
