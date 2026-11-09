# Live Testing and Repair Framework Plan

**Goal:** Detect faults in the Issuer Library's front and back end on every change, prove that data flows correctly (sources → module handoffs → delivered handoffs → rendered report) through a real provider run, and record every fault so it can be repaired test-first.

**Architecture:**
- The Playwright walk (`apps/issuer-library/designs/browser_check.py`) records every fault class in `faults.json`, with artifacts, and isolates each walk so one failure cannot hide the rest.
- A stdlib-only checker (`designs/flow_check.py`) traces hashes and numbers through a run folder, independently of production code. The offline fake-provider walk runs it, and it also runs on retained runs.
- A paid walk (`designs/live_check.py`) drives the real engine through the app under an explicit spend cap.
- CI runs the offline gates.

**Spec:** The owner's request of 2026-11-07, to "create a robust live testing and repair framework to detect faults and bugs" across the updated front end and back end, and to "include provider runs to test if data flowing correctly". The owner skipped design questions, so the design choices are the controller's. Task-by-task execution, rulings and review results are in the SDD ledger, not here.

## Baseline (main at e562c366)

- `validate.py quick` failed on `fixture`, then `node`. `designs/build.py` still called `built_from(folder, …)` after b1970e81 changed its parameter to a verified `files` map.
- Browser walk: `cpos_live_not_accepted: CP-0 not accepted within bounds`. Commit 2758841f added a required opening view (`OPENING`, `src/deploy_workflow/owners/cpos_launch.py`). The fake engine never writes it.
- That one exception aborted the rest of chromium's walks, so about 20 checks never ran. `validate.py report()` printed only the last 40 lines.
- Neither gate ran in CI.

## Constraints

- No provider call from `validate.py`, pytest or CI. Paid execution happens only through `live_check.py`, run explicitly with `--cap`.
- Keys come only from the launching environment. Every captured log and artifact is redacted.
- `flow_check.py` and `faults.py` use the stdlib only and import nothing from `src/` or `engine/`.
- `runs/`, `deliverables/` and `data/` are never modified.
- No stub stands in for real behaviour. A catch-all is allowed only when it is documented and recorded as a fault. Every expected HTTP 4xx and every ignored request failure is listed with a reason.
- Changed Python passes `tools/quality_gate.py`. Each PR stays at or under 800 changed lines.
- Two browser walks never run at once, because they use fixed ports 53901–53910.

## Review focus

1. Real handoffs that round, scale, negate in parentheses or add `%` must not flood `flow_check`. Normalisation is pinned by tests and calibrated on retained live runs.
2. Digits inside digests, dates, identifiers and page lists are not data.
3. A provider key never reaches `faults.json`, logs or artifacts.
4. A walk that fails midway still writes `faults.json` and its artifacts. The next walk runs, and the gate exits non-zero.
5. `live_check` without a key, without `--cap`, or with a non-positive or non-finite cap exits 2 before any server, browser or folder exists.

## Tasks

1. **Fault capture.** New `designs/faults.py`, holding `redact`, `crashes`, `http_fault`, `request_fault` and `Faults.write`.
   - `browser_check.py` imports with no side effects and runs through `main()`.
   - Each walk (`<engine>-library`, `<engine>-run`, `stopped`) runs in `attempt()`, which records an `exception` fault with screenshot and HTML, then continues.
   - Server stdout, stderr and `state-<port>/library.log` are redacted and scanned for crashes.
   - Responses and failed requests become `http` and `requestfailed` faults.
   - `validate.report()` prints every `FAIL` line.
   - Proof: on the baseline, `faults.json` recorded the CP-0 fault in both browsers.
2. **Baseline regressions.**
   - `build.py` passes the delivery's verified file map.
   - The fake engine writes `### <OPENING[module]>` where `_opens_with` requires it, importing `OPENING` rather than copying it.
   - Proof: `quick` all PASS; the browser walk 111 passed, 0 failed.
3. **Data-flow checker.**
   - `flow_check.run_faults(run, sources)` checks four things:
     - every received upstream hash and text equals the accepted handoff;
     - every source hash matches the file;
     - every number in a handoff appears in what that module read or received;
     - every delivered copy is byte-equal to the accepted handoff.
   - `report_faults(text, handoffs)` flags report numbers that appear in no handoff.
   - It is wired into the fake-run walk, and its CLI runs on retained runs.
4. **Paid live walk.**
   - `live_check.py --cap USD [--config] [--modules] [--minutes] [--out] [--rehearse]` drives New run on TDG as of 2024-09-30 with the real engine. It then runs the flow checks and `live_evidence`, whose answer key is `assert_live_evidence` in `tests/test_cpos_launch.py`.
   - `--rehearse` runs the same walk on the fake engine for free and skips the flow and evidence checks. Its scope string says so.
5. **CI and docs.**
   - The PR job `issuer-library-quick` runs `validate.py quick`.
   - The browser job installs Playwright 1.64.0 and uploads artifacts on failure.
   - `docs/QUALITY-GATE.md` documents live testing and the repair loop:
     1. Read `faults.json`.
     2. Write a test that fails at the surface where the fault was seen.
     3. Fix.
     4. Rerun.
     5. Hand pre-existing faults to the owner.

After the tasks: whole-branch review, then a paid run only on the owner's explicit go-ahead (config, modules, cap).
