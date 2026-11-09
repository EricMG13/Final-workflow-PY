# Refactoring sweep contract: 2026-11-08 update

Prepared 2026-11-08. Kind `refactoring`, scope `changed-update`. Steps after prepare
(`discover`, `launch`) each need their own invocation.

## Authority

- `AGENTS.md` at HEAD (project rules; wins on conflict), `~/.claude/CLAUDE.md` §1–§5
  (global rules; the Deploy VII amendment does not apply here), `docs/QUALITY-GATE.md`,
  `METHODOLOGY-REVIEW.md` for method selection, `docs/rulings/*.md`,
  `docs/superpowers/plans/2026-11-08-deferred-features.md` (the plan the range implements).
- Retained gates: listed under *Gates*. Project review rules: confidence-review after code
  changes; rewrite-tournament (post-edit) on nontrivial changed functions.
- Excluded: the superseded CP-8 investment post-mortem gate, a separate CP-MEMO module,
  Excel export as a deliverable.

## Base and comparison

| Identity | Value |
|---|---|
| Starting commit | `0619a9be27f0b8d8543a7d5eb75ac555fc3d54c1` (= `origin/main` locally, PR #43) |
| Starting tree | `e965191da966318f994fbf5bc4ae58432252b828` |
| Branch | `claude/sweep-prepare-c802ee` (worktree `.claude/worktrees/adversarial-reviewer-ux-ui-d73bdd`) |
| Comparison base | `e1a24112` (PR #30, last merge of 2026-11-07), tree `c31df3e73ee836c5e8d632e55c34f74f0a69e8c4` |
| Range | `e1a24112..0619a9be`: PRs #31–#43, 56 files, +12941/−6012, 37 code files |
| Why | Owner choice, 2026-11-08: the 2026-11-08 update (run events, activity page, native toast, resume, model derived rows and LTM, register hardening, store CRLF, record split) |
| Dirty input at start | none (clean tree); untracked: none |

Local `main` is at `8c6e4591`, 43 PRs behind; it is not the base. Remote state was not
fetched; `origin/main` is the local ref only.

## Scope and ownership

In scope: code files changed in the range and their callers/imports.

- Python: `apps/issuer-library/engine/{bridge,store}.py`, `apps/issuer-library/designs/{browser_check,build}.py`,
  `apps/issuer-library/validate.py`, `src/deploy_vii/model/frame.py`,
  `src/deploy_workflow/{handoff_delivery,markdown_delivery,model_handoff_delivery,run_events}.py`,
  `src/deploy_workflow/model/handoff.py`, `src/deploy_workflow/owners/{cpos,cpos_launch}.py`.
- Go: `apps/issuer-library/{jobs,notify,platform_other,platform_windows,server}.go`.
- JS/CSS/HTML: `apps/issuer-library/web/{actions,boot,hydrate,screen,views}.js`, `index.html`, `screen.css`.
- Tests in the range may change only to add causal tests; existing assertions are not weakened.

Out of scope: `runs/`, `data/`, `cases/`, `deliverables/`, `handoffs/`, `examples/`,
docs except this sweep's files and the verification record entry, predecessor repositories,
the plan files, everything outside the range unless a confirmed in-range defect's sibling.

Owned by this sweep: `docs/sweeps/refactoring/{CONTRACT.md,goal.txt}`,
`artifacts/sweeps/refactoring/**` (git-ignored), and the patches launch makes.

Other writers (worktrees seen 2026-11-08): main checkout and
`~/.codex/worktrees/issuer-design-integration` (`codex/issuer-design-integration`, at `8c6e4591`),
`.claude/worktrees/sub-agents-merge-pr-539f73` (`claude/session-idea-review-bfd736`),
`.claude/worktrees/hungry-sanderson-a3f26c`, `.claude/worktrees/system-design-remaining-calls-e06c23`
(detached). Before launch, check `origin/main` and open PRs for overlap with the in-scope files.

## Decisions and permissions

- Owner decisions: comparison base above. Rulings in `docs/rulings/` stand.
- Behavior changes: only to repair a confirmed defect, with a causal failing test first.
- Dependencies and pins: no new dependency, no pin change (`pyproject.toml`, `uv.lock`,
  `go.mod`, jsdom 26.1.0, Playwright 1.64.0 unchanged).
- External actions: no push, PR, merge or publication without a separate owner request.
  Commits only when launch is authorized, explicit paths, no `git add -A`.
- Spend: **not authorized**. No provider call, no `designs/live_check.py` without `--rehearse`.
- Unanswered: none blocking discover.

## Protected behavior

| Invariant | Check |
|---|---|
| Values, periods, units, sources, limitations preserved handoff → deliverable; missing ≠ zero | `tests/test_model_handoff_delivery.py`, `tests/test_markdown_delivery_sections.py`, `tests/test_cpos_handoffs.py` |
| Retained-run flow (handoff order, digests, delivered copies byte-identical) | `designs/flow_check.py ../../runs/cpos-launch-live-002 --sources ../../data/public-corpus/v1/TDG` → 1 finding; `../../runs/cpos-sol-medium-20261105` → 1 finding (calibration 2026-11-07) |
| Answer keys untouched | `apps/issuer-library/designs/forecast-answer-key.json`, `assert_live_evidence` in `tests/test_cpos_launch.py`, frozen oracles in tests: byte-identical to the starting tree `0619a9be` (not `e1a24112`: the range added the LTM row to the forecast key) |
| Run events, resume, spend accounting, notice | `tests/test_run_events.py`, `tests/test_cpos_launch.py`, `tests/test_cpos_app.py`, Go `jobs_test.go`, `server_test.go`, `notify_test.go` |
| Store parsing (CRLF, register cells) | `tests/test_issuer_library_store.py` |
| Web screens | Node tests via `validate.py quick` |
| Retained `runs/` and predecessor repos unmutated | `git status --short -- runs data cases deliverables` empty |
| No credential files, no provider keys | gitleaks not wired here; `git diff --name-only` review |
| `VERIFICATION.md` < 1000 lines | `tests/test_verification_record.py` |

## Gates and baseline

All from the repository root unless noted; Python 3.13.15, uv 0.12.5, Go 1.26.4, Node 24.16.0, macOS.
No `timeout` binary: bound runs with the Bash tool timeout (300 s for pytest).

| Gate | Command | Accept |
|---|---|---|
| Quality gate (changed code) | `uv run python tools/quality_gate.py` (base `origin/main`) | exit 0 |
| Range debt measurement (discover only) | `uv run python tools/quality_gate.py --base e1a24112 --json` | measurement, not a gate |
| Targeted pytest | `uv run pytest <affected test files>` | exit 0 |
| Issuer library | `FW_PYTHON=.venv/bin/python ISSUER_LIBRARY_JSDOM=<jsdom 26.1.0 dir> python3 apps/issuer-library/validate.py quick` per task; `full` at branch end | exit 0 |
| Go | in `apps/issuer-library`: `go vet ./...` and `go test -race ./...` | exit 0 |
| Browser walk (branch end, if Playwright available) | `python3 apps/issuer-library/validate.py browser` with `FW_PYTHON`, `FW_PLAYWRIGHT_PYTHON` | exit 0, else recorded as not run |
| Flow check (branch end) | see *Protected behavior* | finding counts unchanged |
| Diff size | `git diff --numstat origin/main...HEAD -- . ':!*.lock'` sum ≤ 800 | exit 0 |
| Full suite | weekly CI only (`nightly-tests.yml`); not run locally | known list `tests/nightly-known-failures.txt` |

Baseline: not yet run on the starting tree; discover runs it and registers red gates as rows.
GitNexus: the 2026-11-08 record says the repository is not indexed; check `gitnexus status` at
each step.

## Targets

Discover measures; launch reduces only rows with a measured before value. Candidate metrics,
restricted to functions changed in the range:

1. Quality-gate findings against `e1a24112` (C901 > 15, PLR09xx, E501, format, mypy strict). Target 0.
2. Complexity of the largest changed functions (`model_handoff_delivery.py`, `store.py`,
   `markdown_delivery.py`, `cpos_launch.py`, `jobs.go`, `actions.js`). Target: each at or below
   the gate threshold, no new function above it.
3. Duplicated logic across `handoff_delivery.py` / `markdown_delivery.py` /
   `model_handoff_delivery.py` and `bridge.py` / `store.py`, measured as repeated blocks with line
   counts. Target: one source of truth where callers agree on behavior.
4. Unused reachable code introduced in the range (no callers). Target: removed after reading all callers.
5. Open items the range's own record names (escaped `\|` register cells, CRLF, resume path,
   `GetSystemDirectoryW`), classified as defect, decision or platform-only.

Taste-only rewrites, features and items outside the range are not targets.

## Runtime

Controller (this session) plans, coordinates, writes contract/register/record; it writes no code.
Workers per global §1: `mx-scaffold` / `mx-feature` (Sonnet) implement; `mx-precise` reviews each
task; `mx-adversary` when a diff touches sensitive code (spend/cost accounting in
`cpos_launch.py`/`run_events.py`, job ordering and resume in `jobs.go`/`bridge.py`, store writes);
`mx-feature` re-reviews small fixes; `mx-architect` reviews the branch; `confidence-review` and
`rewrite-tournament` run once on the branch diff. Implementers have no MCP tools; library docs go
in briefs. No goal/session runner is assumed.

## Stop conditions

- Per item: at most two Sonnet fix rounds; a third only via `mx-autonomous` plan + fresh
  `mx-feature`; then the item goes to the owner as `decision`.
- Total: at most 12 launched items and 6 hours of launch wall time; diff ≤ 800 changed lines.
  On exhaustion, remaining rows become `deferred` with reason.
- A finding that predates the range goes to the owner, not into the sweep.
- A new writer's change to an in-scope file on `origin/main` stops overlapping work until refreshed.

## State and evidence

| File | Path |
|---|---|
| Contract | `docs/sweeps/refactoring/CONTRACT.md` |
| Goal | `docs/sweeps/refactoring/goal.txt` |
| Knowledge, progress, register | `artifacts/sweeps/refactoring/{knowledge,progress,register}.md` (git-ignored) |
| Probes, raw logs | `artifacts/sweeps/refactoring/{probes,logs}/` |
| Verification entry | `VERIFICATION.md` (one entry at completion) |

Freshness: before each step compare HEAD, tree, dirty diff, `origin/main`, this contract's hash and
the rule files above with `progress.md`; refresh affected planning before any mutation.

## Completion

Every register row has a status (`fixed`, `fixed-at-base`, `duplicate`, `deferred`, `decision`,
`not-a-defect`, `platform-only`); every `fixed` row has a causal test or a same-metric
before/after; all gates above exit 0 on the final tree (browser walk recorded if not run);
protected answer keys byte-identical to the starting tree `0619a9be`; flow-check counts unchanged; one VERIFICATION.md
entry with commands, exits and a `Not verified:` line. Windows-only behavior (toast,
`platform_windows.go`, Edge) stays `platform-only` unless checked on Windows.
