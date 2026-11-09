# Quality gate for changed code

`tools/quality_gate.py` holds new and changed Python code to a readability,
maintainability, complexity and typing standard without requiring a rewrite of the
existing code. It runs on pull requests (`.github/workflows/quality-gate.yml`), by hand
("Run workflow": off a PR it checks the last commit, `HEAD~1`; the PR manager starts it, and the
browser walk, on `main` every hour) and locally:

```bash
uv run python tools/quality_gate.py            # compares with origin/main
uv run python tools/quality_gate.py --base main --json
```

## Scope: changed code, not changed files

The gate diffs the working tree against `--base`. In scope are every changed line and
the whole body of every function (decorators included) that a changed line falls in.
A new file is in scope whole. Findings outside that scope are dropped, so a one-line
edit in a 60-branch legacy function reports the function's complexity, while an edit
elsewhere in the same file does not. Standard library only (`ast`, `subprocess`,
`git diff -U0`); the checkers are the dev dependencies the repo already pins.

## Checks and thresholds

| Check | Threshold | Source of the threshold |
|---|---|---|
| `ruff check` with `tools/ruff-gate.toml` | the repo's rule set plus E501 (100 columns), C901, PLR0911, PLR0912, PLR0913, PLR0915 | repo `pyproject.toml`; pylint design limits at ruff's defaults (returns 6, branches 12, arguments 5, statements 50) |
| McCabe complexity (C901) | 15 | pydantic-ai (`mccabe max-complexity = 15`); ruff's default 10 is exceeded by 180 existing functions, Home Assistant uses 25 |
| `ruff format` | no change in scope | repo formatter settings |
| `mypy` | strict, errors in scope; `tests/` excluded | repo `[tool.mypy] strict = true`; tests are typed by convention only |

Comparable projects read for the thresholds: pydantic-ai (C90 at 15, mypy and pyright
strict), Home Assistant (PL and C selected, complexity 25, PLR09xx ignored), OpenBB
(PLR selected, max-args 8, max-branches 26, max-returns 9), LangChain core (`ALL`
minus C90 and PLR09), Code Climate defaults (complexity 5, 25-line methods, 4 arguments),
SonarQube S3776 cognitive complexity 15.

## Baseline this gate does not try to clear

Measured at `a313b50` on `src`, `apps` and `workflow.py`: 180 functions above
complexity 10 (62 above 15, 15 above 25); 160 with more than 5 arguments, 94 with
more than 12 branches, 56 with more than 50 statements, 33 with more than 6 returns;
356 lines over 100 columns; 46 files `ruff format` would change (27 of them in `src`);
mypy strict reports 33 errors in `src` and 110 with `apps/issuer-library/engine`.
That is why the gate is scoped to changed code. Reducing the baseline is separate work.

## Reading a report

```
src/x.py:120: ruff C901 `f` is too complex (17 > 15)
src/x.py:131: mypy return-value Incompatible return value type ...  [return-value]
src/x.py:140: format FMT ruff format would change
quality gate: 3 finding(s) in 2 changed file(s), 212 line(s) in scope
```

Exit 1 while findings remain, 2 when the gate itself could not run (unknown base ref,
tool missing). A `# noqa` or `# type: ignore[...]` with a reason is the escape hatch, and
the reviewer sees it in the diff.

## Fast tests while working, the full suite weekly

While working, run fast targeted tests only: the test files or `-k` selections that cover the
changed code, each run finishing within a few minutes (wrap it in `timeout 300`). Never run the
whole suite, the `test_owner_*` suites or anything whose fixture promotes CP-0/CP-1 during work.

The full suite, slow tests included, runs every Sunday at 01:00 UTC in GitHub Actions
(`.github/workflows/nightly-tests.yml`, also startable by hand with "Run workflow"):

- sixteen pytest shards (`tools/nightly_tests.py run`). Each collects the whole suite and keeps
  every sixteenth test (`tools/nightly_shard.py`), so a file of slow end-to-end tests spreads over
  every shard; file-size balancing left one shard with hours of `test_earnings_workflow.py` tests
  and cut it short (2026-11-08). The `live`
  and `browser` markers are excluded and provider keys removed; each shard stops after 300 minutes,
  deletes a passing test's `tmp_path` (each workflow store holds about 120 MB of issuer sources;
  module and session fixtures' directories stay to the shard's end, since some are shared across
  modules, e.g. `tests/cpdr_runs.py` `closed_run`), frees unused runner toolchains first and
  prints its log's last 400 lines (with the 30 slowest tests), the failure summary or a crash's trace, to the job log;
- the Go server's `go vet` and `go test -race`;
- a report job (`tools/nightly_tests.py report`) that collects every FAILED and ERROR node id,
  compares them with `tests/nightly-known-failures.txt` and fails only on a failure that is not on
  that list or a shard that did not finish. The summary lists new failures and known failures that
  now pass; `failures.txt` is kept as an artifact for 30 days.

To triage a failure, start the workflow by hand with `tests` set to the failing node ids
(space-separated) and, to compare with an earlier commit, `ref` set to that commit. Only a `rerun`
job runs, and it prints short tracebacks to the job log.

To accept a pre-existing failure, add its node id to the known list with a reason. Remove a line
once its test passes again. GitHub runs scheduled workflows from the default branch only. The
first full run (2026-11-07) took about 17 runner-hours with three shards cut short, so the
schedule is weekly (user ruling, 2026-11-07, when the repository was private and used the
account's Actions minutes; it is public since 2026-11-08). The names `nightly-tests` and `nightly-known-failures.txt` stay.

### CI runs of the issuer library gates

- `quality-gate.yml`, job `issuer-library-quick`, on every pull request: `validate.py quick`
  (retained-data check, fixture build, the Node tests under jsdom, the issuer library's Python
  tests) with Node 24 and `uv sync --group dev` set up first (no Go: that job builds no server).
- `issuer-library-browser.yml`, job `issuer-library-browser`, on the weekly schedule (with the
  nightly suite), by hand, and on pull requests touching `apps/issuer-library/**`, `src/**` or the
  workflow itself (about 10 minutes of Actions per matching PR): `validate.py browser` builds the
  Go server and runs `designs/browser_check.py` in chromium and firefox. On failure it uploads
  `$RUNNER_TEMP/browser` (including `faults.json`) as an artifact for 14 days.
- Decision record: jsdom 26.1.0 and Playwright 1.64.0 are the test-only tools `validate.py`
  already requires. CI installs those pinned versions outside the project lock (`npm install
  --no-save`, a separate `uv venv`); they are not runtime dependencies. No job sets a provider key.

## Live testing and repair

Commands run from `apps/issuer-library`; `runs/` and `data/` paths are relative to the repository root
(use `../../runs/...`). `FW_PYTHON` is the project's Python, `ISSUER_LIBRARY_JSDOM`
a jsdom install, `FW_PLAYWRIGHT_PYTHON` a Python with Playwright (test-only tools).

**Offline commands (no provider is called)**
- `python validate.py quick`: retained-data check, fixture build, Node tests, Python tests.
- `python validate.py browser`: builds the Go server, then runs the browser walk in chromium and
  firefox. Needs `FW_PYTHON` and `FW_PLAYWRIGHT_PYTHON`; `FW_BROWSER_OUT` picks the output folder.
- To see every PASS/FAIL line, run `$FW_PLAYWRIGHT_PYTHON designs/browser_check.py chromium firefox`
  directly (needs `FW_PYTHON` and `ISSUER_LIBRARY_BINARY`, a built server).

**faults.json** (in the output folder, redacted)
- Top level: `scope` (what the run covered), `mode` (live walk only: `rehearsal` or `live`),
  `passed` (checks that passed) and `failed` (faults recorded). The units differ: one check can
  record several faults, and a fault need not come from a check.
- Each fault: `walk`, `kind`, `detail`, `url`, `artifacts`.
- Kinds: `check` (a failed check), `console`, `pageerror`, `http` (5xx, or an unexpected 4xx),
  `requestfailed`, `server-log` (a crash in the Go server's log), `flow` (a flow-check finding),
  `exception` (the walk stopped; later checks did not run). The live walk adds `worker` (a process
  left after stop) and `interrupted` (SIGINT, SIGTERM, SIGHUP or SIGQUIT; spend may be above zero; only exception faults
  recorded after the signal are relabelled, an earlier failure keeps its kind).
- Artifacts: `<walk>-failure.png` and `.html`, `server-<port>.log`, `state-<port>/library.log`.
- `server-log` covers the Go server's log only. `jobs.go` discards the engine's stdout and stderr,
  so an engine traceback never reaches a scanned log.

**flow_check.py on a retained run**
- `python designs/flow_check.py runs/<run> [--sources data/public-corpus/v1/TDG]`; it exits 1 on any fault.
- Checks: each upstream handoff a module received equals the accepted one, and arrived in order;
  each source copy hashes to its recorded digest; every accepted handoff equals an accepted draft;
  `calculate` results are gated on their operands; every number in a handoff appears in what the
  module read or received (only the sources its requests name); every accepted handoff has a
  delivered copy, byte-identical; an empty run is a fault.
- Numbers are compared as normalised strings: thousands commas, trailing zeros, a unit suffix
  (x, bn, mm, m, k), dates and page lists are stripped, and long calculation results match their
  roundings.
- A flagged number is a finding to classify, not an automatic defect. Example:
  `runs/cpos-launch-live-002` CP-1 "SOFR + 250 bps" against the source's "2.50%" is a conversion
  the source does not quote. Calibration (2026-11-07): live-002 gives 1 finding (that one);
  `runs/cpos-sol-medium-20261105` gives 1 (CP-2's delivered handoff equals a draft whose review
  still lists 3 issues; its README records that a faulty campaign checker rejected CP-2 and the
  response was recovered by hand).

**Paid walk: `designs/live_check.py`**
- Always rehearse first: `--rehearse --cap 12` is free, uses the fake engine, and labels in its
  scope that the flow and evidence checks were skipped.
- The paid run is an explicit command. CI and `validate.py` never run it. Needs `FW_PYTHON` and
  `ISSUER_LIBRARY_BINARY`; flags `--cap USD`, `--config` (default sol-medium), `--modules`
  (default "CP-1 CP-1A"), `--minutes`, `--out`.
- The provider key comes from the launching environment only (`OPENAI_API_KEY` for sol-medium).
  It is removed from the walk's own environment and passed only to the server. Unset unrelated
  tokens first: other environment secrets still reach the server and worker.
- `--cap` must cover the per-call hold (USD 5.73 for sol-medium); use 12. Recorded cost for
  CP-0..CP-1A was about USD 0.93 in `runs/cpos-launch-live-002`.
- Checks: the review screen against the arguments before Start; the run completes; the app's
  spend equals `status.json`; "Built from" matches the accepted handoffs; flow checks with
  `--sources data/public-corpus/v1/TDG`; `live_evidence` (calls, models, spend within the cap);
  filed values in the report; and the answer key `assert_live_evidence` in
  `tests/test_cpos_launch.py` (rule below). Intake `status.json` is read as the last by name, by
  both the shown-spend check and the teardown.
- The server and worker are stopped on every exit, including SIGHUP and SIGQUIT, and on SIGKILL
  or a crash of `live_check` through a watchdog in its own session (it cannot see a hung
  `live_check`). SIGHUP stops the walk even under `nohup` (the handler replaces the inherited
  ignore; it fails safe: worker and server are stopped). After a SIGKILL no `faults.json` is written: read `status.json` and
  `live/calls.jsonl` by hand. Spend is reported from `status.json` and the ledger; a call of
  unknown cost is counted and recorded as a fault, never as zero. Output in `--out`:
  `faults.json` and `summary.json`.
- The answer key runs only when the config is `sol-medium` and the requested modules are exactly
  "CP-1 CP-1A" (decided from the arguments); the review screen must then list exactly CP-0, CP-1
  and CP-1A. Any other request is labelled "answer key not applicable" in the scope. A review
  screen that lists other modules is an exception fault before Start (no spend).
- Owner notes: do not run it backgrounded with `&` (a job started that way may ignore Ctrl-C; SIGINT stops the walk otherwise); `FW_PYTHON` needs
  pytest for the answer key; do not set `PYTHONOPTIMIZE`; other environment secrets reach the
  server and worker.

**Repair loop**
1. Read `faults.json` and its artifacts.
2. Write a test that fails for the reported cause, at the surface where it was seen. The walk's own
   FAIL line counts when it already fails.
3. Fix.
4. Rerun the gate or walk.
5. A fault that predates the change goes to the owner, not into the task.
