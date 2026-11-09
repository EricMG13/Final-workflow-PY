# Deferred Issuer Library / CP-OS Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (the global rules make it the coding method). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the five items the previous plan parked as owner calls: a Run activity page over the event log, a native Windows notice when no tab is open, resume-from-the-app after a stop, the grid's derived rows published by model delivery with their sources, and a short verification record.

**Architecture:** Six phases, one PR each, in dependency and risk order. Each phase is independent of the others' code; they share only what already exists at `7cce363a` (`events.jsonl`, `status.json["reason"]`, the run watcher, `HandoffPlan.retained_handoffs`, `ModelDelivery`).
1. Go serves a run's parsed events; the browser lists them on the existing Run activity route.
2. Go records when a tab last polled; at a run's finish with no recent poll, Windows shows a toast through PowerShell (no dependency); other platforms do nothing.
3. Resume = a new reviewed job whose `HandoffPlan.retained_handoffs` are the stopped run's accepted handoffs. CP-OS replays them without a call (its existing mechanism); the app's review → confirm → start flow is unchanged.
4. Model delivery publishes fiscal-year growth, margins and senior secured leverage into `calculation.json["values"]` behind a new, excluded-when-absent manifest field; the store prefers those keys and keeps its derivation for old deliveries.
5. Model delivery publishes LTM Adj EBITDA (and quarter-end senior secured leverage where the quarter register is classifiable) under `calculation.json["quarters"]`; the store reads them.
6. `VERIFICATION.md` becomes the archive by rename; a new short `VERIFICATION.md` holds the recent entries and points at it.

**Tech Stack:** Python 3.13 (standard library only in `apps/issuer-library/engine/store.py`; pydantic 2.14.1 in `src/`), Go 1.24 (`apps/issuer-library/go.mod`), plain browser JavaScript with jsdom tests, PowerShell 5.1 (Windows only, invoked through `os/exec`).

**Spec:** the controller's brief of 2026-11-08 and the "Owner calls" section of `docs/superpowers/plans/2026-11-07-run-events-delivery-coverage-workspace.md`, with the rulings in `.superpowers/sdd/2026-11-07-run-events-delivery-coverage-workspace/progress.md`. All code facts below were read at `7cce363a`. No separate spec file (one-record rule, `AGENTS.md`).

## Decisions

Each: Ruling — why — cost if wrong.

1. **Ruling: the Run activity page fetches `GET /api/runs/events?id=` and renders in the browser; the store does not read `events.jsonl`.** — Go already parses the log (`jobs.go:154-233`); the store runs on every cache miss and must stay cheap; only app runs (`web-<32 hex>`) have a log, and their context key is the job id (`runTarget`, `actions.js:48`). — Cost: a second fetch per visit (local, small).
2. **Ruling: the server knows a tab is open when `GET /api/runs/list` was served within the last 15 s (`tabGrace`).** — The app-wide watcher polls that endpoint every 5 s while a run is running (`actions.js:65-83`); three missed polls mean no tab. — Cost: a tab frozen for 15 s at the finish gets both a browser and a native notice.
3. **Ruling: the native notice is PowerShell + WinRT `ToastNotificationManager` under PowerShell's own AppUserModelID, with the text passed in environment variables and a fixed script; no new dependency, so no decision record.** — Toasts need a registered AUMID; PowerShell's is registered on every Windows 10/11; environment variables avoid quoting user text into a script. The toast has no click action: PowerShell's AUMID cannot open the library. — Cost: on a machine where PowerShell toasts are disabled by policy nothing appears, which is logged.
4. **Ruling: resume is a new job (`intake/<new id>/`, `job.json["resume_of"]`) whose plan pins the stopped run's accepted handoffs as `retained_handoffs`; the stopped run's folder is never reused.** — `_handoff` (`cpos.py:199-253`) refuses a module whose request was retained without a response (`cpos_interrupted`) and the executor refuses a module folder that exists (`handoff.py:452-456`: "resume via CP-OS retained responses; never resend"); `start-authorization.md` is created with `open("x")` (`bridge.py:208`); `start.claim` is one-shot (`jobs.go:548`). `retained_handoffs` is the resume mechanism CP-OS already has (`cpos.py:74-78`, `:346-385`): checked without a call, marked `retained-response-replay` in the report. — Cost: the new run's ledger starts at zero; the stopped run's spend stays in its own status, so the two are read together.
5. **Ruling: a resume keeps the stopped job's context, sources, config and modules; only `cap_usd` and `max_turns` may change.** — Changing sources or context changes the source hashes and `cpos_retained_sources` would refuse every retained handoff; the user who wants that starts a new run. — Cost: none (the New run flow exists for everything else).
6. **Ruling: derived rows go into `calculation.json["values"][<FY>]` as new keys with the existing entry shape, only when `ModelDelivery.derived` is set (`exclude_if` None).** — The store already reads `values[FY][key]` through `("key", name)` (`store.py:1064`, `:1480-1490`) and validates entries with `checked_entries` (`:1079`); the hash-pinned deliverables and `runs/cpos-tdg-model-001` carry no `derived`, so their bytes cannot change. — Cost: a schema bump would be needed if the shape later changes.
7. **Ruling: the store's preference is one new cell operation `("prefer", key, fallback_spec)`: the record's key when present, else the old derivation.** — Smallest change; old deliveries keep working; no second grid. — Cost: a record with a wrong value is shown as-is (the viewer lays out values, which is the goal).
8. **Ruling: senior secured debt in model delivery follows the store's `secured_debt` rules (`store.py:1212-1260`) exactly, including refusing an unclassifiable row.** — Two readers with different rules would show different numbers for the same handoff. — Cost: a register row the rule cannot classify leaves the multiple unavailable with the row named (as today).
9. **Ruling: Phase 5 (LTM) is its own PR; LTM Adj EBITDA at a quarter end = the fiscal year ending within 7 days before the year-to-date window's start + that window − the same window one year earlier; quarter-end senior secured leverage only when the quarter register is fully classifiable.** — The TDG quarter register (`runs/tdg-003/CP-1-attempt-2.md:277-298`) lists government advances and finance leases, which rule 8 cannot classify, so for retained TDG data the quarter leverage stays unavailable with the row named; the synthetic test covers the positive case. — Cost: a second small PR.
10. **Ruling: in-app runs still do not publish a model.** — The brief asks for the rows and sources in `calculation.json` and a store that prefers them; wiring `ModelDelivery` into `cpos_launch.prepare` is a separate feature (`NOT_ANALYTICAL`, `cpos_launch.py:73`). — Cost: the new keys are exercised by tests and future model deliveries until then.
11. **Ruling: the verification record is split by `git mv` (old file becomes the archive) plus a new short file; cutoff = entries dated 2026-11-07 or later stay.** — Moving 5,100 lines into a new file is a 10,000-line diff; a rename is 0 lines in `numstat`, so the PR is about 500 changed lines. The rule chosen: **`VERIFICATION.md` holds the entries of the last two days of work and the header; everything older moves verbatim, in its original order, to `docs/VERIFICATION-ARCHIVE.md`, append-only; a test holds `VERIFICATION.md` under 1,000 lines.** — Cost: a reader of an older entry follows one link.
12. **Ruling: phase order 1 → 2 → 3 → 4 → 5 → 6 (the brief's 1 → 3 → 2 → 4 → 5 with Phase 4 split).** — Nothing in the code reorders it: Phases 1-3 touch disjoint Go/JS/Python surfaces; Phase 4 precedes 5 (shared manifest field); Phase 6 is independent and goes last so its cutoff is applied once. — Cost: none.

## Global Constraints

- `runs/` and `deliverables/` never change (`validate.py quick` `retained` gate). The hash-pinned `deliverables/tdg-model-1..3` and `runs/cpos-tdg-model-001/execution/delivery-07ede06e….json` keep their bytes: every new manifest field is `Field(default=None, exclude_if=lambda v: v is None)`; a full byte round-trip of those manifests already fails at `7cce363a` for other reasons, so the pin test compares key sets (Task 8).
- No paid provider call anywhere. Fakes: the `provider` fixture (`tests/test_cpos_launch.py:167-209`), `fakeEngine` (`apps/issuer-library/jobs_test.go:26-52`), jsdom `fetch` mocks (`web/run-watch.test.cjs:11-29`). Gates strip provider keys (`validate.py` `clean_env`).
- Paid execution stays a separate explicit owner action: a resume reaches a provider only through the existing `POST /api/runs/start` with `confirm: true` after a fresh review.
- Missing is never zero; delivery never writes analysis. A derived value whose operand is missing carries the operand's reason; a register that cannot be classified gives no total.
- `store.py` imports only the standard library (`tests/test_issuer_library_store.py:349`).
- No new dependency (Go, Python, JS). PowerShell is part of Windows.
- Users are on Windows (Edge/Chrome); a result seen only on macOS says so.
- One PR per phase, each ≤ 800 changed lines excluding fixtures (`git diff --numstat "origin/main...HEAD" -- . ':!*.lock'`). Branch each phase from `main` after the previous merges: `claude/run-activity`, `claude/native-toast`, `claude/resume-run`, `claude/model-derived-rows`, `claude/model-ltm`, `claude/verification-archive`. Pushes and PRs need the owner's go-ahead.
- Every brief and reviewer prompt includes: no stub or fake value standing in for real behaviour; no catch-all hiding a failure unless the fail-open is documented and logged; expected values written by hand, never produced by the code under test; every report ends with a `Not verified:` line.
- One short `VERIFICATION.md` entry per phase, macOS-only where that is the case. No other review files.
- Copy rule: UI sentences are given verbatim below; reader pages show module names, not codes (`screen.js:72-74` `showsCodes` lists `CP-OS`, so the activity page may show codes).

## Validation Schedule

| When | Command | Passes when |
|---|---|---|
| Every task | The focused tests the task names (`timeout 300`) | New test seen failing for the stated cause, then exit 0 |
| Every commit | `python3 apps/issuer-library/validate.py quick` (needs `FW_PYTHON`, `ISSUER_LIBRARY_JSDOM`) | Exit 0 |
| Go tasks | in `apps/issuer-library`: `gofmt -l . \| wc -l` is 0; `go vet ./...`; `GOOS=windows GOARCH=amd64 go vet ./...`; `go test -race ./...` | All exit 0 |
| Python tasks | `uv run python tools/quality_gate.py` | Exit 0 |
| End of each phase | `validate.py full`, `uv run python tools/quality_gate.py` | Exit 0 |
| End of Phases 1-3 | Owner's Windows check (Edge): the step named in the phase | As stated |
| Whole-branch review | `confidence-review`, `rewrite-tournament` (post-edit) on the phase diff | Confirmed defects fixed |

**Agents** (global §1): `mx-feature` implements every task; `mx-precise` reviews each task; `mx-adversary` also reviews Tasks 3-6 (paid start path, process execution) and 8-9 (money figures); `mx-architect` does each phase's whole-branch review.

## Review Focus

1. **A resume whose stopped run changed on disk** (an accepted `<module>.md` edited after the stop) must change the review id and be refused at Start, never replayed (Task 4 `test_a_changed_retained_handoff_is_refused_at_start`).
2. **A run that finishes while the only tab is on a non-run page** gets exactly one notice: the browser's, because the watcher polls app-wide; the native one must not fire (Task 2 `TestAFinishedRunNotifiesNativelyOnlyWhenNoTabWatches`, case A).
3. **An events log cut mid-line or over 4 MiB** shows the complete events and says the record is incomplete, never an error page (Task 1 `TestRunEventsEndpointDropsATruncatedLastLine`, JS `'an incomplete log says so'`).
4. **A derived row whose prior year is outside the selected periods** (FY2022 growth) shows a reason, never zero or a value from an unselected year (Task 8 `test_derived_rows_follow_the_record_rules`).
5. **A debt register with a row the rule cannot classify** gives no senior secured total and names the row, in both the delivery and the store (Task 8 and Task 10 unclassified cases).

---

## Phase 1: Run activity page (`claude/run-activity`)

### Task 1: Events endpoint

**Files:**
- Modify: `apps/issuer-library/jobs.go`: `runEvent` (:154-162), `parseEvents` (:193-210), `serveRunAPI` GET branch (:291-317)
- Test: `apps/issuer-library/jobs_test.go`

**Interfaces:**
- `runEvent` gains `At string json:"at,omitempty"`, `Reason string json:"reason,omitempty"`, `WritesLeft *int json:"writes_left,omitempty"`; existing fields gain `omitempty` (`Module`, `Turn`, `MaxTurns`, `SpentUSD`, `HeldUSD`, `CapUSD`). `Event` stays required. `foldEvents` is unchanged by this.
- Produces: `readRunEvents(workspace, id string) (events []runEvent, complete bool, err error)`: opens `runs/<id>/events.jsonl` through `io.LimitReader(file, eventsLimit)`; `complete` is false when the read hit `eventsLimit` or `parseEvents` dropped a last line (it returns a third value `dropped bool`, true when it broke on the last line) or returned `!ok`; on `!ok` it returns the events parsed before the bad line (parseEvents keeps them). A missing file is `(nil, true, fs.ErrNotExist)`.
- `GET /api/runs/events?id=<jobID>` → `200 {"events": [...], "complete": bool}`; `[]` (not null) when the file is missing but `intake/<id>/status.json` exists; `404` when neither exists (same rule as `/api/runs/status`).
- `runProgress` uses `readRunEvents` so the two paths cannot disagree.

- [ ] **Step 1: Write the failing tests** in `jobs_test.go`, writing the log lines by hand:
  - `TestRunEventsEndpointListsEveryEventWithItsFields`: lines `module_started` (CP-0), `turn` (turn 1, max 24, spent "0.00", held "5.73", cap "10"), `draft_rejected` (writes_left 2), `module_accepted`, `delivery_started`, `delivered`; assert the decoded body's `events` has 6 items in order, `events[2].writes_left == 2`, `events[1].held_usd == "5.73"`, `complete == true`, and `events[0].at` equals the written timestamp `"2026-11-08T09:00:00Z"`.
  - `TestRunEventsEndpointDropsATruncatedLastLine`: a last line `{"event":"tur` → 5 events listed, `complete == false`.
  - `TestRunEventsEndpointWithoutALogIsAnEmptyList`: status.json present, no log → `{"events":[],"complete":true}`; neither → 404.
  - `TestRunEventsStopsAtTheReadLimit`: a log longer than `eventsLimit` (make `eventsLimit` a `var` for the test, as `reviewTimeout` is) → `complete == false`.
- [ ] **Step 2:** `go test -race ./... -run 'RunEvents'`. Expected: FAIL (404 route).
- [ ] **Step 3:** Implement the interfaces above.
- [ ] **Step 4:** Rerun Step 2 and `-run 'RunProgress'` (the existing folds still pass); gofmt, go vet (both GOOS), `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `Issuer Library: a run's event log is served as JSON`.

### Task 2: Run activity view

**Files:**
- Modify: `apps/issuer-library/web/views.js:535` (the `CP-OS` branch of `workspaceView`)
- Modify: `apps/issuer-library/web/actions.js` (new `loadRunActivity`, next to `describeModule` :17-30 and `spendText` :31-36)
- Modify: `apps/issuer-library/web/screen.js:389` (after `$('content').innerHTML=moduleBody(next);`)
- Modify: `apps/issuer-library/web/screen.css` (`.activity-log` table)
- Create: `apps/issuer-library/web/run-activity.test.cjs`; add to `NODE_TESTS` in `apps/issuer-library/validate.py:24-35`
- Test: `web/screens.test.cjs` (the `CP-OS/activity?c=tdg-002` route at :56 and :461 must still render the retained-record text)

**Interfaces:**
- Consumes: `/api/runs/status?id=` (`jobView`: `state`, `reason`, `message`, `spent_usd`, `modules`, `module_details`, `progress`) and `/api/runs/events?id=` (Task 1).
- `workspaceView('CP-OS')`: when `/^web-[a-f0-9]{32}$/.test(context)` (the context key, not `ctx.run`), returns `<section id="run-activity" data-run="<context>" aria-live="polite"><h2>Run activity · <ctx.run></h2><p class="hint">Loading run activity…</p></section>` followed by the existing `<ol class="activity-flow">…</ol>` (keep its two items; drop the "No live progress" missing-state and the "Live progress and spend are recorded only…" caution for these runs). Other contexts keep today's markup unchanged.
- `loadRunActivity(section: HTMLElement): Promise<void>` in actions.js: fetches status then events; replaces the `<p class="hint">` with:
  - `<p class="activity-summary">` = `stopText(status)` then ` · ` + `describeModule(status, modules, titleOf)` when non-empty, then a second `<p>` = `spendText(status)`;
  - `<table class="activity-log"><caption>Events (UTC)</caption><thead><tr><th>Time</th><th>Event</th></tr></thead><tbody>…` one row per event, time = `at.slice(11,19)`, text from the table below;
  - when `complete === false`, a trailing `<p class="caution">The record is incomplete: the log was cut or stopped mid-write.</p>`;
  - when `events.length === 0`, `<p class="hint">No events were recorded for this run.</p>` instead of the table;
  - on a fetch failure, `<p class="caution">Could not load the run record. Details: <message></p>` (no retry).

  | `event` | Row text (`title(m)` = module title from `module_details`, else the code) |
  |---|---|
  | `module_started` | `Started <title>` |
  | `turn` | `Turn <turn> of <max_turns> · spend USD <spent_usd> of USD <cap_usd>; this call holds USD <held_usd>` |
  | `draft_rejected` | `Draft of <title> rejected · <writes_left> write(s) left` (singular at 1) |
  | `module_accepted` | `Accepted <title>` |
  | `delivery_started` | `Delivery started` |
  | `delivered` | `Report delivered` |
  | `stopped` | `STOP_COPY[reason]` or, for `other`/unknown, `Stopped (<reason>)` |
  | anything else | `<event>` verbatim (escaped) |

- `screen.js:389`: after the innerHTML assignment, `const activity=$('run-activity');if(activity)loadRunActivity(activity);`. All text goes through `textContent` or `esc`.

- [ ] **Step 1: Write the failing tests** in `run-activity.test.cjs`, harness copied from `run-watch.test.cjs:11-29` with `DESIGN_DATA.runs` holding one context keyed `ID` (`{run:ID,title:'Northbridge Group',period:'as of 31 March 2025',issuerKey:'id:nbg',issuer:'Northbridge Group',modules:{},first:null}`; add any field the screens demand at boot and name it in the report) and `fetch` answering `/api/runs/status` and `/api/runs/events`:
  - `'the run activity page lists each event in order with its text'`: the six hand-written events → `[...doc.querySelectorAll('.activity-log tbody tr')].map(text)` equals the six sentences above with titles from `module_details`, and the summary paragraph equals `'running: Working · running Title CP-1, turn 1 of 24'`.
  - `'a stopped run leads with its stop sentence'`: status `stopped`/`budget` plus a `stopped` event → first paragraph starts with `STOP_COPY.budget`, last row equals `STOP_COPY.budget`.
  - `'an incomplete log says so'`: `complete:false` → the caution text above is present.
  - `'a run without a log shows the no-events line'`.
  - `'a retained run keeps the retained-record text'`: context key `tdg-002` → the page contains `No live progress or cost recorded` and no `#run-activity`; `fetch` is not called.
- [ ] **Step 2:** `node --test --test-timeout=60000 web/run-activity.test.cjs` (needs `ISSUER_LIBRARY_JSDOM`). Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun Step 2, then `web/screens.test.cjs`, `web/run-watch.test.cjs`, `web/escape-sinks.test.cjs` (it audits innerHTML sinks; a new sink must pass its rule), `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `Issuer Library: the Run activity page lists a run's events, spend and stop reason`.

**Phase 1 end:** end-of-phase gates; Windows check: start no run; open an earlier app run's Run activity in Edge and see its events. One `VERIFICATION.md` entry.

---

## Phase 2: Native Windows notice (`claude/native-toast`)

### Task 3: Tab presence and the native notice

**Files:**
- Create: `apps/issuer-library/notify.go` (no build tag)
- Modify: `apps/issuer-library/server.go:24-42` (`Application` gains `watched atomic.Int64`)
- Modify: `apps/issuer-library/jobs.go`: `serveRunAPI` list branch (:296-299), `finishJob` (:613-619)
- Modify: `apps/issuer-library/platform_windows.go`, `apps/issuer-library/platform_other.go`
- Test: `apps/issuer-library/jobs_test.go`, new `apps/issuer-library/notify_test.go`

**Interfaces:**
- `notify.go`:
  - `const tabGrace = 15 * time.Second`
  - `func (app *Application) tabWatching() bool`: `clock().Sub(time.Unix(0, app.watched.Load())) <= tabGrace` (`clock` is the swappable `time.Now` at `launch.go:25`). `serveRunAPI` stores `clock().UnixNano()` into `app.watched` on every `GET /api/runs/list`.
  - `func finishNotice(folder string) (title, body string, ok bool)`: reads `status.json` (`state`) and `review.json` (`issuer`); `ok` false when status is unreadable or `state == "running"`. `title = "Issuer Library"`. `body`: with an issuer, `"<issuer> run <state>"`; without, `"Run <state>"`; `state` is the status word (`complete`, `stopped`, `failed`, `interrupted`). Nothing from `message` (it may carry redacted provider text).
  - `var notifyNatively = platformNotify` (swappable in tests).
  - `const toastScript = …`: a fixed PowerShell program that loads `Windows.UI.Notifications.ToastNotificationManager` and `Windows.Data.Xml.Dom.XmlDocument` (WinRT, `ContentType = WindowsRuntime`), builds `ToastGeneric` XML with two `<text>` nodes whose contents are `CreateTextNode($env:ISSUER_LIBRARY_TOAST_TITLE)` and `CreateTextNode($env:ISSUER_LIBRARY_TOAST_BODY)` (text nodes, never string concatenation into XML), and shows it through `CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe')`. The script contains no Go formatting and no other `$env:` reference.
- `finishJob`: after `app.refresh()`: `if !app.tabWatching() { if title, body, ok := finishNotice(folder); ok { if err := notifyNatively(title, body); err != nil { log.Printf("Run %s: native notice failed: %v", id, err) } } }`.
- `platform_windows.go`: `func platformNotify(title, body string) error`: `exec.CommandContext(ctx, "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", toastScript)` with a 20 s context, `cmd.Env = append(os.Environ(), "ISSUER_LIBRARY_TOAST_TITLE="+title, "ISSUER_LIBRARY_TOAST_BODY="+body)`, `configureWorkerCommand(cmd)` (no console window), `return cmd.Run()`.
- `platform_other.go`: `func platformNotify(title, body string) error { log.Printf("No tab is open; native run notices are Windows-only (%s)", body); return nil }`.

- [ ] **Step 1: Write the failing tests:**
  - `jobs_test.go` `TestAFinishedRunNotifiesNativelyOnlyWhenNoTabWatches`: fakeEngine start flow as in `TestExplicitStartIsOneShotUnderConcurrentRequests` (:147-196); swap `notifyNatively` to append `(title, body)` to a mutex-guarded slice and `clock` to a settable time. Case A: `GET /api/runs/list` just before the worker ends → after the job settles, no call. Case B: set the clock 16 s after the last list GET before the worker ends → exactly one call, `title == "Issuer Library"`, `body == "Run stopped"` (fakeEngine's review carries no issuer and its worker writes `stopped`).
  - `notify_test.go` `TestFinishNoticeTextUsesIssuerAndState`: status `complete` + review `issuer: "Northbridge Group"` → `"Northbridge Group run complete"`; status `running` → `ok == false`; no review → `"Run interrupted"`.
  - `notify_test.go` `TestToastScriptIsFixedAndReadsOnlyTheTwoVariables`: `strings.Count(toastScript, "$env:") == 2`, contains `$env:ISSUER_LIBRARY_TOAST_TITLE` and `$env:ISSUER_LIBRARY_TOAST_BODY`, contains `CreateTextNode`, contains neither `%s` nor `+ $env` (no concatenation into XML).
  - `notify_test.go` `TestTabWatchingWindow`: watched at T, clock T+15 s → true; T+15 s+1 ns → false; never watched (zero) → false.
- [ ] **Step 2:** `go test -race ./... -run 'Notif|FinishNotice|ToastScript|TabWatching'`. Expected: FAIL (undefined symbols).
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun Step 2; gofmt; `go vet ./...`; `GOOS=windows GOARCH=amd64 go vet ./...` and `GOOS=windows GOARCH=amd64 go test -c -o /dev/null ./...`; `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `Issuer Library: a run that finishes with no tab open shows a Windows notice`.

**Phase 2 end:** end-of-phase gates. Windows check (owner, paid run needed for a real finish — or the synthetic event-log route from the Phase 1 ledger cannot end a job, so use a real low-cap run): start a run, close every tab, see the toast at the finish; then repeat with a tab open and see only the browser notification. Record both in the entry; on macOS record `Not verified: the toast itself`.

---

## Phase 3: Resume from the app (`claude/resume-run`)

### Task 4: Launcher and bridge accept retained handoffs

**Files:**
- Modify: `src/deploy_workflow/owners/cpos_launch.py`: `prepare` (:553-623)
- Modify: `apps/issuer-library/engine/bridge.py`: `launch` (:95-109), `review` (:124-172)
- Test: `tests/test_cpos_launch.py`, `tests/test_cpos_app.py`

**Interfaces:**
- `prepare(..., retained: Mapping[str, bytes] | None = None) -> Prepared`. With `retained`, for the longest prefix of `ordered` whose every module is in `retained`, it writes `directory/retained/<module>.md` (`_put`) and adds `RetainedHandoff(path=f"retained/{m}.md", sha256=_sha(raw), source_hashes={name: spec.sha256 for name, spec in request.sources.items()}, upstream={prior: _sha(retained[prior]) for prior in ordered before m})` to `HandoffPlan.retained_handoffs`. Modules after the first non-retained one are not retained (CP-OS requires the upstream chain, `cpos.py:367-369`). `Prepared` gains `retained_modules: tuple[str, ...]`.
- `bridge.retained_of(workspace: Path, job: dict) -> dict[str, bytes]`: `{}` unless `job.get("resume_of")` matches `^web-[a-f0-9]{32}$`; else every `runs/<resume_of>/CP-*.md` (the acceptance copies `start` writes at `bridge.py:231`) keyed by stem. A missing run folder raises `ValueError("the stopped run's retained work is no longer in the workspace")`.
- `bridge.launch(job, directory, out)` passes `retained=retained_of(workspace, job)` (workspace from `read_job`).
- `bridge.review` result gains `"resume_of": job.get("resume_of")` and `"retained_modules": list(prepared.retained_modules)`; `material` gains `"retained": {m: spec.sha256 for m, spec in request.retained_handoffs.items()}` so the review id changes with the retained bytes.
- `bridge.start` is unchanged: it re-runs `review` and compares ids, then `launch` again (deterministic).

- [ ] **Step 1: Write the failing tests:**
  - `test_cpos_launch.py` `test_prepare_pins_a_retained_prefix_and_stops_at_the_first_gap`: `retained={"CP-0": b0, "CP-1A": b2}` for an ordered plan `("CP-0","CP-1","CP-1A")` → `retained_handoffs` keys `== ["CP-0"]`, `upstream == {}`, `source_hashes` equals the plan's source hashes, and `out/retained/CP-0.md` holds `b0`.
  - `test_cpos_app.py` `test_a_resume_replays_accepted_handoffs_and_calls_only_the_rest`: run job A with the `provider` fixture so CP-0 is accepted and the next module rejected (as `test_a_rejected_module_stops_with_retained_work_and_no_report`, :193); then job B = same context/sources, `resume_of: A`, cap "50"; `bridge.review(B)["retained_modules"] == ["CP-0"]`; `bridge.start(B)` with answers that pass → `[m for m, _, _ in provider.calls]` after the resume excludes `"CP-0"`, status `complete`, and the completion record's `module_execution["CP-0"] == "retained-response-replay"`.
  - `test_a_changed_retained_handoff_is_refused_at_start`: after `review(B)`, append a byte to `runs/A/CP-0.md` → `start(B)` raises `review is stale`, no provider call.
  - `test_a_resume_with_nothing_accepted_retains_nothing`: `retained_modules == []`, review ok.
  - `test_a_resume_whose_run_folder_is_gone_is_refused`: the `ValueError` text above.
- [ ] **Step 2:** `uv run pytest tests/test_cpos_launch.py tests/test_cpos_app.py -q -k 'retained or resume'`. Expected: FAIL (`TypeError: prepare() got an unexpected keyword`).
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun Step 2 and the two files whole; `tools/quality_gate.py`; `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `CP-OS launcher: a reviewed run may pin a stopped run's accepted handoffs for replay`.

### Task 5: Resume endpoint

**Files:**
- Modify: `apps/issuer-library/jobs.go`: `NewJob` (:107-115), `jobView` (:131-137, add `resume_of` and `retained_modules` to the copied keys), `serveRunAPI` POST branch (:325-336), `reviewRun` (:341-508; extract the tail from `saveJSON(job.json)` at :461 to the end into `app.reviewJob(w, folder string, job NewJob)`), new `resumeRun`
- Test: `apps/issuer-library/jobs_test.go`

**Interfaces:**
- `NewJob.ResumeOf string json:"resume_of,omitempty"`.
- `POST /api/runs/resume` body `{"id": "<stopped job>", "cap_usd": "12.00", "max_turns": 32}` (`DisallowUnknownFields`, 8 KiB): `400` when `id` fails `jobID`, `cap_usd` is empty, or `max_turns` is outside 1-64; `409 "Only a stopped, failed or interrupted run can be resumed"` unless the old `status.json` state is one of those; `409 "The stopped run's inputs are no longer in the workspace"` when `intake/<id>/job.json`, `context.json` or `sources/` is missing; `503` while quitting. On success it creates `intake/<new id>/`, copies `context.json` and the `sources/` tree with `os.CopyFS` under the workspace root, writes `job.json` = old job with the new `ID`, the given `Cap`/`MaxTurns`, `ResumeOf: id`, then runs `app.reviewJob` exactly as a review does (the `reviews` counter, the write deadline, the review.json/status.json writes, the folder removal on refusal). The response is the review result (`ok`, `review_id`, `retained_modules`, …).
- `/api/runs/resume` never starts a worker; `start` stays the only path to `engine.command("start")`.

- [ ] **Step 1: Write the failing tests** (fakeEngine; extend its `review` branch to echo `job.get('resume_of')` and `job['max_turns']`):
  - `TestResumeReviewsACopyOfTheStoppedRunAsANewJob`: review + start job A, wait for `stopped`; `POST /api/runs/resume {"id":A,"cap_usd":"12.00","max_turns":9}` → 200, body `id != A`, `resume_of == A`; the new `job.json` has `resume_of == A`, `cap_usd == "12.00"`, `max_turns == 9`, the same `sources` entries; `intake/<new>/sources/annual.txt` bytes equal A's; new status `reviewed`; A's folder unchanged (its `job.json` bytes equal before and after); no `synthetic-starts.txt` in the new folder.
  - `TestResumeRefusesARunningOrReviewedJob`: state `reviewed` → 409 with the sentence above; state `running` → 409.
  - `TestResumeRefusesWhenTheStoppedRunsInputsAreGone`: remove A's `sources/` → 409 with the second sentence.
  - `TestResumedJobStartsOnlyThroughConfirmedStart`: after the resume, `POST /api/runs/start` with `confirm:false` → 400; with the new id, its `review_id` and `confirm:true` → 202; the new folder's `synthetic-starts.txt` is `one\n`.
- [ ] **Step 2:** `go test -race ./... -run 'Resume'`. Expected: FAIL (404).
- [ ] **Step 3:** Implement. `reviewRun`'s own tests (`TestUploadReviewDoesNotStart…`, `TestSlowReviewResponse…`, `TestClientDisconnectMidReview`, the review-in-flight switch tests :1276-1500) must pass unchanged after the extraction.
- [ ] **Step 4:** Rerun Step 2 and `go test -race ./...`; gofmt; go vet both GOOS; `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `Issuer Library: a stopped run can be resumed as a new reviewed job that replays its accepted handoffs`.

### Task 6: Resume in the New run screen

**Files:**
- Modify: `apps/issuer-library/web/index.html:30` (progress step gains the resume control)
- Modify: `apps/issuer-library/web/actions.js`: `showStatus` (:143-174), `reviewSummary` (:175-187), a `#resume-run` click handler next to `#another-run` (:257)
- Test: `apps/issuer-library/web/new-run.test.cjs`

**Interfaces:**
- Markup inside `#progress-step .step-actions`, before `#another-run`: `<label id="resume-field" class="run-field" hidden>Maximum spend for the resumed run (USD)<input id="resume-budget" type="number" min="0.01" step="0.01"></label><button id="resume-run" class="secondary-action" type="button" hidden>Resume with retained work</button>`.
- `showStatus`: `#resume-field` and `#resume-run` are shown only when `!WORKFLOW_ACTIVE.includes(status.state) && status.state !== 'complete' && status.state !== 'reviewed'`; `#resume-budget` defaults to `review.cap_usd` when set, else `$('run-budget').value`.
- Click `#resume-run`: `appRequest('/api/runs/resume', {id: review.id, cap_usd: $('resume-budget').value, max_turns: Number(review.max_turns) || Number($('run-turns').value)})`; on `ok`: `review = result; $('run-confirm').checked = false; reviewSummary(result); stage('review'); controls();`; on `!ok`: `message(result.problems.join('\n'))`; on a thrown error: `message('Could not prepare the resumed run. Details: ' + error.message)`.
- `reviewSummary`, when `result.resume_of`: after the readiness paragraph, a `<p class="matrix-note">`: with `retained_modules.length`, `Resumes run <resume_of>. Retained without a new model call: <titles joined by ', '>.`; otherwise `Resumes run <resume_of>. No module of it was accepted; every module runs again.`
- Start stays the existing `#start-run` handler (confirm checkbox, `/api/runs/start`).

- [ ] **Step 1: Write the failing tests** in `new-run.test.cjs` (its `page()` harness; add `'/api/runs/resume'` to `replies` returning `reviewReply(true)` extended with `{id: ID2, resume_of: ID, retained_modules: ['CP-0']}` and record the posted body):
  - `'a stopped run offers a resume that goes through review and confirmation'`: open the stopped row from Recent runs (`status` stopped/budget, `cap_usd` "10.00" in the row) → `#resume-run` visible, `#resume-budget.value === '10.00'`; set it to `12.50`, click → the POST body equals `{id: ID, cap_usd: '12.50', max_turns: 32}`; the review stage shows the note `Resumes run <ID>. Retained without a new model call: Source readiness.`; `#start-run` disabled until `confirm()`; clicking Start posts `/api/runs/start` with `{id: ID2, review_id: …, confirm: true}` and `starts() === 1`.
  - `'a complete or running run offers no resume'`: `#resume-run.hidden === true` in both states.
  - `'a refused resume shows its problems and stays on progress'`: reply `{ok:false, problems:['The stopped run\'s inputs are no longer in the workspace']}` → message text equals it; `#progress-step` still shown.
- [ ] **Step 2:** `node --test --test-timeout=60000 web/new-run.test.cjs`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun Step 2, `web/run-watch.test.cjs`, `web/screens.test.cjs`, `web/escape-sinks.test.cjs`; `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `Issuer Library: Resume with retained work reviews a stopped run again before an explicit Start`.

**Phase 3 end:** end-of-phase gates. Windows check (owner): a run stopped on budget → Resume → review shows the retained modules → confirm → Start; the report's module limitation reads "Replayed from a retained response; no new model call was made." for the retained module. One `VERIFICATION.md` entry naming the spend of both runs.

---

## Phase 4: Derived rows in `calculation.json` (`claude/model-derived-rows`)

### Task 7: Manifest field and store preference

**Files:**
- Modify: `src/deploy_workflow/handoff_delivery.py:78-85` (`ModelDelivery`)
- Modify: `apps/issuer-library/engine/store.py`: `REASON_PHRASES` (:920-923), `CELL_OPS` (:1540-1549), the five `RowSpec`s (`revenue-growth` :1588, `gp-margin` :1608, `adj-margin` :1675, `adj-growth` :1676, `senior` :1741-1749)
- Test: `tests/test_issuer_library_store.py`, `tests/test_model_handoff_delivery.py`

**Interfaces:**
- `class DerivedRows(Contract): debt_register: str | None = None` (the anchor line of the annual debt register, matched like `ModelDelivery.anchors`).
- `ModelDelivery.derived: DerivedRows | None = Field(default=None, exclude_if=lambda v: v is None)`.
- Store: `op_prefer(c: CellContext, key: str, fallback: Spec) -> Cell`: `record = c.column["record"]`; when `record` is not None and `key in record` → `held_cell(record[key], c.kind)`; else `spec_cell(fallback, c)`. Registered as `"prefer"`. The five fiscal specs become `("prefer", "revenue_growth", ("growth", "revenue"))`, `("prefer", "gross_margin", ("margin", "gp"))`, `("prefer", "adj_ebitda_margin", ("margin", "adj"))`, `("prefer", "adj_ebitda_growth", ("growth", "adj"))`, `("prefer", "senior_secured_multiple", ("senior",))`. Quarter and forecast specs are unchanged.
- `REASON_PHRASES` gains `"PRIOR_PERIOD_MISSING": PRIOR_MISSING`, `"REGISTER_DATE_DIFFERS": "secured-debt carrying values are recorded at another date"`, `"UNCLASSIFIED_ROW": "the debt register has a row that cannot be classified"`.

- [ ] **Step 1: Write the failing tests:**
  - `test_model_handoff_delivery.py` `test_a_manifest_without_derived_rows_keeps_its_key_set`: for `runs/cpos-tdg-model-001/execution/delivery-07ede06e6c4828bde0fb39cd68f14e6f3c154a0837dc28734ac7074bf2b080f5.json` and `runs/cpos-tdg-model-001/workflow.json`, `set(json.loads(DeliveryRequest/HandoffPlan.model_validate_json(raw).model_dump_json())["model"]) == set(json.loads(raw)["model"])`, and `"derived"` is in neither. (Byte round-trip of these two fails at `7cce363a`; checked by the planner.)
  - `test_issuer_library_store.py` `test_the_grid_prefers_recorded_derived_rows_and_falls_back_without_them`: build a model fixture as the budget tests do (:2542-2707), with `calculation.json["values"]["FY2024"]` holding `revenue_growth: {"amount": "0.25", "reason": null}` and `senior_secured_multiple: {"amount": null, "reason": "UNCLASSIFIED_ROW"}` → the `Revenue YoY growth` FY2024 cell displays `25.0%` (confirm the store's percent format at `display_amount`, hand-written) and the `Senior secured leverage` cell is `n.a.` with reason `the debt register has a row that cannot be classified`; the same fixture without those keys gives the cells the current derivation gives (`forecast-answer-key.json` unchanged, `tests/test_issuer_library_store.py:1028`).
- [ ] **Step 2:** `uv run pytest tests/test_model_handoff_delivery.py tests/test_issuer_library_store.py -q -k 'key_set or prefers'`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun Step 2, then both files whole and the probes `branch3-issuer-groups-invariants.py`, `branch3-budget-order-sources-clause.py` (paths in the previous ledger, Task 9) exit 0; `tools/quality_gate.py`; `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `Model delivery: an optional derived-rows request; the grid prefers recorded derived rows`.

### Task 8: Delivery publishes the fiscal-year derived rows

**Files:**
- Modify: `src/deploy_vii/model/frame.py:17-24` (`Reason` gains `"PRIOR_PERIOD_MISSING"`, `"REGISTER_DATE_DIFFERS"`, `"UNCLASSIFIED_ROW"`)
- Modify: `src/deploy_workflow/model_handoff_delivery.py`: `FORMULAS`/`LABELS` (:95-122), `_annual_cells` (:244-290) or a new `_derived_cells(reader, cells)`, `build_model` tables loop (:462-535), `values` (:537-567)
- Test: `tests/test_model_handoff_delivery.py`

**Interfaces:**
- With `layout.derived` set, `_derived_cells(reader: _AnnualReader, cells: dict[str, dict[str, Cell]], derived: DerivedRows) -> None` adds to each period's row, under `localcontext(CONTEXT)`:

  | Key | Formula (`FORMULAS`) | Rule |
  |---|---|---|
  | `revenue_growth` | `revenue / prior-year revenue - 1` | prior = the selected period whose `end_date` is 365 or 366 days before this one; none → `Cell(None, "PRIOR_PERIOD_MISSING")`; else `_ratio(((revenue,1),),((prior revenue,1),))` then `calc(((ratio,1),(Cell(Decimal(1), basis="CALCULATED"),-1)))` |
  | `gross_margin` | `gross_profit / revenue` | `_ratio` |
  | `adj_ebitda_margin` | `issuer_as_defined / revenue` | `_ratio` |
  | `adj_ebitda_growth` | `issuer_as_defined / prior-year issuer_as_defined - 1` | as `revenue_growth` |
  | `senior_secured_debt` | `carrying values of the securitization, the term loans aggregate and the secured notes at the register date` | only with `derived.debt_register`: the table under that anchor (`reader.selected`-style lookup on the anchor line); its second header cell's date (`Mon D, YYYY`) is the register date; rows classified exactly as `store.secured_debt` (`store.py:1212-1260`, labels in `CASHFLOW_LABELS`): a `carrying <n>` match in the second cell, case-insensitive; total rows skipped; an unclassified row with a carrying value → `Cell(None, "UNCLASSIFIED_ROW", note=<label>)`; a required row without a carrying value → `COMPONENT_MISSING`. One `SourceRef("annual", "line <n>", "<the matched 'carrying <n>' text>")` per summed row. When the register date is not this period's `end_date` → `Cell(None, "REGISTER_DATE_DIFFERS", note="recorded at <ISO date>")` |
  | `senior_secured_multiple` | `senior_secured_debt / issuer_as_defined` | `_ratio` |

  Without `derived.debt_register` the two senior keys are absent.
- `values[period][key]` entries keep the existing shape (:537-567). Units: growth and margins `unit "FRACTION"`, `quantity_family "dimensionless"`, `currency None`, `scale "1"`; `senior_secured_debt` as `MILLIONS`; `senior_secured_multiple` as `MULTIPLE`. `start_date` as for the operands (`None` for the balance-type `senior_secured_debt`).
- A third table `("derived", <the present derived keys>, "company-profile")` joins the `(tid, keys, block)` loop so `model.html` and `view.json` carry the rows (facts `unit` `"FRACTION"`/`"MULTIPLE"`/`"MILLIONS"`, `decimals` from `_ratio_decimals` for ratios and fractions). `LABELS`: `revenue_growth` "Revenue YoY growth", `gross_margin` "Gross profit margin", `adj_ebitda_margin` "Adj EBITDA margin (As Defined / revenue)", `adj_ebitda_growth` "Adj EBITDA YoY growth (As Defined)", `senior_secured_debt` "Senior secured carrying debt at the register date", `senior_secured_multiple` "Senior secured leverage (secured carrying debt / Adj EBITDA As Defined)".

- [ ] **Step 1: Write the failing tests** (values by hand from `runs/tdg-002/CP-1-attempt-2.md`: FY2024 revenue 7,940, FY2023 6,585, FY2022 5,429; gross profit FY2024 4,672; As Defined 4,173 / 3,395 / 2,646; register at `### T4.18 — Debt/facility register`, header date `Sep 30, 2024`, carrying 486 (securitization, line 367), 8,642 (term loans aggregate, line 368), 2,077 (6.75% secured notes, line 375), 2,727 (6.375% secured notes, line 377); tranche, revolver and subordinated rows carry no secured carrying value or are unsecured). Compare as `test_81` does (:60-76): `Decimal(amount) == Fraction` rounded at prec 38, `ROUND_HALF_EVEN`:
  - `test_derived_rows_are_absent_without_the_request`: `annual_only()` → none of the six keys in `values["FY2024"]`, no `derived` table in `view.json`.
  - `test_derived_rows_follow_the_record_rules`: layout `derived=DerivedRows(debt_register="### T4.18 — Debt/facility register")`:
    - `values["FY2024"]["revenue_growth"]` = `Fraction(271, 1317)` (7940/6585 − 1); `["FY2023"]` = `Fraction(1156, 5429)`; `["FY2022"]` amount `None`, reason `PRIOR_PERIOD_MISSING`;
    - `gross_margin` FY2024 = `Fraction(1168, 1985)`;
    - `adj_ebitda_margin` FY2024 = `Fraction(4173, 7940)`; `adj_ebitda_growth` FY2024 = `Fraction(778, 3395)`;
    - `senior_secured_debt` FY2024 amount `"13932"`, `unit "MILLIONS"`, sources' `locator` `== ["line 367", "line 368", "line 375", "line 377"]` and `cell_text == ["carrying 486", "carrying 8,642", "carrying 2,077", "carrying 2,727"]`;
    - `senior_secured_multiple` FY2024 = `Fraction(4644, 1391)` (13932/4173), `unit "MULTIPLE"`; FY2023 amount `None`, reason `REGISTER_DATE_DIFFERS`, note contains `2024-09-30`;
    - growth/margins: `unit == "FRACTION"`, `quantity_family == "dimensionless"`, `currency is None`, `scale == "1"`.
  - `test_an_unclassified_register_row_gives_no_secured_total`: `annual_only(before=b"| Revolving credit facility | Commitment 910;", after=b"| Revolving credit facility | carrying 910;")` with the same `derived` → FY2024 `senior_secured_debt` amount `None`, reason `UNCLASSIFIED_ROW`, note `"Revolving credit facility"`; `senior_secured_multiple` carries the same reason.
  - `test_the_model_page_lists_the_derived_table`: `view.json` has a table `derived` with six rows in the key order above; `model.html` contains `Senior secured leverage (secured carrying debt / Adj EBITDA As Defined)`.
  - The existing `test_81_values_against_independent_source_fraction_checks`, `test_ambient_decimal_precision_cannot_change_model` and `test_cp_os_publishes_complete_model_bundle_resumes_and_refuses_tampering` pass unchanged.
- [ ] **Step 2:** `uv run pytest tests/test_model_handoff_delivery.py -q`. Expected: FAIL (`DerivedRows` unknown / keys absent).
- [ ] **Step 3:** Implement. If `Reason` is used in a pattern-complete match elsewhere (`grep -rn "ZERO_OR_NEGATIVE_DENOMINATOR" src`), update those sites and name them in the report.
- [ ] **Step 4:** Rerun Step 2; `uv run pytest tests/test_handoff_delivery.py tests/test_cpos_handoffs.py tests/test_cpos_comparison.py -q`; `tools/quality_gate.py`; `validate.py quick` (the `retained` gate proves `runs/` and `deliverables/` untouched). Expected: PASS.
- [ ] **Step 5:** Commit: `Model delivery: fiscal-year growth, margins and senior secured leverage are published with their sources`.

**Phase 4 end:** end-of-phase gates. Live check (deterministic, retained data, macOS): build the CASE model with `derived` into `tmp_path`, copy it as a model folder into a scratch workspace, open the Forecast grid in the real app and see the FY2024 senior secured cell `3.34x` (format per the store) with no "Not calculable". One `VERIFICATION.md` entry labelled deterministic retained-data.

---

## Phase 5: LTM Adj EBITDA and quarter-end leverage (`claude/model-ltm`)

### Task 9: Delivery publishes quarter derived values

**Files:**
- Modify: `src/deploy_workflow/handoff_delivery.py` (`DerivedRows` gains `quarter_bridge: str | None = None`, `quarter_debt_register: str | None = None`)
- Modify: `src/deploy_workflow/model_handoff_delivery.py`: new `_QuarterReader` (the `quarter` input, `table()` from `handoff_delivery.py:286`), `calculation["quarters"]` beside `values` (:568-585)
- Modify: `src/deploy_vii/model/frame.py` (`Reason` gains `"WINDOW_MISSING"`)
- Test: `tests/test_model_handoff_delivery.py`

**Interfaces:**
- Only when `layout.derived` is set and `"quarter" in inputs` and `derived.quarter_bridge` is set: `calculation["quarters"] = {<window>: {ltm_adj_ebitda: entry, senior_secured_debt?: entry, senior_secured_multiple?: entry}}` where `<window>` is the quarter column header `YYYY-MM-DD–YYYY-MM-DD` (en dash or hyphen as printed) of the table under `derived.quarter_bridge`, one entry per window whose start is a fiscal-year start (the day after a selected period's `end_date`) — other columns (prior-year comparatives) are operands only. Entry shape as `values` entries, with `period` = the window text, `start_date`/`end_date` from it.
  - `ltm_adj_ebitda` (`MILLIONS`): row `CASHFLOW_LABELS["adjusted_ebitda"]` = `Total Company EBITDA As Defined` in that table. Value = FY As Defined of the selected period ending within 7 days before the window start + this window − the column whose start and end are 365/366 days earlier (± 7 days). Missing FY or missing prior column → `Cell(None, "WINDOW_MISSING", note=<which>)`. Sources: the annual cell (`"annual"`, its line, text) and the two quarter cells (`"quarter"`, line, text). Formula text: `fiscal-year Adj EBITDA As Defined + year-to-date window - prior-year window`.
  - `senior_secured_debt` / `senior_secured_multiple`: only with `derived.quarter_debt_register`; the table under that anchor must have a `Net` column (header cell starting `Net`) and a `Label` column; the register date is parsed from the anchor line (`Debt — December 28, 2024` → `2024-12-28`) and must equal the window end, else `REGISTER_DATE_DIFFERS`. Classification as Task 8 but on the label with the `Net` cell as the amount: secured = label contains `securitization`, or starts with `Term loans`, or contains `secured notes` and not `subordinated`; unsecured = contains `subordinated` or `unsecured`; blank-label and `Less:`/`Long-term debt` rows are subtotals and skipped; anything else with a number → `UNCLASSIFIED_ROW` naming it. `senior_secured_multiple = senior_secured_debt / ltm_adj_ebitda`.

- [ ] **Step 1: Write the failing tests** (by hand from `runs/tdg-003/CP-1-attempt-2.md`: bridge table at `### Issuer segment EBITDA As Defined bridge`, columns `2024-10-01–2024-12-28` and `2023-10-01–2023-12-30`, row `Total Company EBITDA As Defined` 1,061 / 912 at line 351; annual FY2024 As Defined 4,173 at `runs/tdg-002/CP-1-attempt-2.md:350`; quarter register `### Debt — December 28, 2024` with `Government refundable advances` 16 and `Finance lease obligations` 260 at lines 293-294):
  - `test_ltm_adj_ebitda_is_fy_plus_ytd_less_prior_ytd`: CASE inputs with `derived=DerivedRows(quarter_bridge="### Issuer segment EBITDA As Defined bridge")` → `quarters["2024-10-01–2024-12-28"]["ltm_adj_ebitda"]["amount"] == "4322"` (4,173 + 1,061 − 912); sources `[("annual","line 350","4,173"),("quarter","line 351","1,061"),("quarter","line 351","912")]`; no entry for `2023-10-01–2023-12-30`.
  - `test_the_tdg_quarter_register_cannot_be_classified`: add `quarter_debt_register="### Debt — December 28, 2024"` → `senior_secured_debt` amount `None`, reason `UNCLASSIFIED_ROW`, note `Government refundable advances`; `senior_secured_multiple` the same reason.
  - `test_a_classifiable_quarter_register_gives_quarter_end_leverage`: the same with the two rows removed from a copy of the quarter handoff (`sha256` re-pinned as `annual_only` does) → `senior_secured_debt == "20192"` (649 + 8,645 + 2,079 + 2,728 + 1,438 + 986 + 2,181 + 1,486), `senior_secured_multiple == Fraction(20192, 4322)` rounded at prec 38.
  - `test_quarters_are_absent_without_a_quarter_bridge_request`: `"quarters" not in calculation` for `annual_only()` and for the CASE build without `derived`.
- [ ] **Step 2:** `uv run pytest tests/test_model_handoff_delivery.py -q -k 'ltm or quarter'`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun the whole file and Task 8's Step 4 commands. Expected: PASS.
- [ ] **Step 5:** Commit: `Model delivery: LTM Adj EBITDA and quarter-end senior secured leverage from the quarter handoff, with sources`.

### Task 10: Store reads the quarter values

**Files:**
- Modify: `apps/issuer-library/engine/store.py`: `fiscal_inputs` (:1321-1333; also validate `record.get("quarters")` entries with `checked_entries`), `CellContext`/`CashflowInputs` (carry `quarters: dict[str, dict]`), `CELL_OPS`, `op_needs_ltm` (:1522), `TAIL_ROWS` (a new `ltm-adj` row after `adj-growth` :1676; `senior` quarter spec :1747)
- Test: `tests/test_issuer_library_store.py`

**Interfaces:**
- `op_quarter(c, key)`: the record entry under `quarters[<window of this column>]` (`f"{start}–{end}"`, matching either dash) → `held_cell`, else `absent_cell()` for non-quarter columns, else the fallback given.
- New row `RowSpec("ltm-adj", ADJUSTED, "LTM Adj EBITDA (As Defined)", "money", ("quarter", "ltm_adj_ebitda"), ("key", "issuer_as_defined"), None)`.
- `senior` quarter spec becomes `("prefer-quarter", "senior_secured_multiple", ("ltm",))`; `op_needs_ltm` returns `unavailable_cell("needs quarter-end total carrying debt, which the model does not derive")` when the column's window has an `ltm_adj_ebitda` amount, else `LTM_NEEDED`. `total-leverage`/`net-leverage` quarter specs stay `("ltm",)`.
- `REASON_PHRASES` gains `"WINDOW_MISSING": "the year-to-date or prior-year window is not in the handoffs"`.

- [ ] **Step 1: Write the failing tests:** fixture with `calculation.json["quarters"]["2024-10-01–2024-12-28"] = {"ltm_adj_ebitda": {"amount": "4322", "reason": null}, "senior_secured_multiple": {"amount": "4.6719", "reason": null}}` → the `LTM Adj EBITDA (As Defined)` cell in that quarter column displays `4,322` and the FY2024 cell `4,173`; `Senior secured leverage` in that column displays `4.7x` (confirm the store's multiple format by hand); `Total leverage` in that column is `n.a.` with the new reason; without `quarters` the old `LTM_NEEDED` text is shown and the new row is `—` in quarter columns. `forecast-answer-key.json` gains the new row only if it enumerates rows (read it first; if it must change, hand-write the new row's cells and name the change in the report).
- [ ] **Step 2:** `uv run pytest tests/test_issuer_library_store.py -q -k 'ltm'`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Whole file, probes as Task 7; `tools/quality_gate.py`; `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `Issuer Library: the grid shows recorded LTM Adj EBITDA and quarter-end senior secured leverage`.

**Phase 5 end:** end-of-phase gates; one `VERIFICATION.md` entry (deterministic retained-data scope).

---

## Phase 6: Verification record (`claude/verification-archive`)

### Task 11: Split the record

**Files:**
- Rename: `VERIFICATION.md` → `docs/VERIFICATION-ARCHIVE.md` (`git mv`)
- Create: `VERIFICATION.md`
- Create: `tests/test_verification_record.py`
- Modify: `AGENTS.md` (the "Keep one concise verification record" bullet gains: `Entries older than two days move verbatim to docs/VERIFICATION-ARCHIVE.md; VERIFICATION.md stays under 1,000 lines.`)

**Interfaces (the rule):** `VERIFICATION.md` = the original header (lines 1-9 at `7cce363a`, with one added paragraph `Older entries are in [docs/VERIFICATION-ARCHIVE.md](docs/VERIFICATION-ARCHIVE.md), verbatim and in their original order; new entries go here.`) + every `## ` section whose heading date is 2026-11-07 or later (at `7cce363a`: lines 11-246, the six sections from "Phase 3 and branch end" through "Nightly full-suite run; gate fix for duplicate module names") + the entries later phases added. `docs/VERIFICATION-ARCHIVE.md` = a three-line header (`# Verification archive`, `Moved verbatim from VERIFICATION.md on <date>; entries before 2026-11-07. Append-only; new entries go to VERIFICATION.md.`) + the rest of the old file in its original order, unchanged.

- [ ] **Step 1: Write the failing test** `tests/test_verification_record.py`:
  - `test_the_record_is_short_and_points_at_the_archive`: `VERIFICATION.md` has at most 1,000 lines and contains `docs/VERIFICATION-ARCHIVE.md`; the archive exists and starts with `# Verification archive`.
  - `test_no_entry_is_in_both_files`: the set of `## ` heading lines is disjoint between the two files.
- [ ] **Step 2:** `uv run pytest tests/test_verification_record.py -q`. Expected: FAIL (5,897 lines; no archive).
- [ ] **Step 3:** `git mv VERIFICATION.md docs/VERIFICATION-ARCHIVE.md`; write the new `VERIFICATION.md`; cut the kept sections from the archive and add its header. Then prove the move is verbatim: `diff <(git show HEAD:VERIFICATION.md | tail -n +10) <(cat <(tail -n +11 VERIFICATION.md | sed '/^## .*(branch `claude\/verification-archive`)/,$d') <(tail -n +4 docs/VERIFICATION-ARCHIVE.md))` exits 0 (adjust the `tail` offsets to the header lengths actually written and record the exact command and its exit code in the report).
- [ ] **Step 4:** Rerun Step 2; `git diff --numstat HEAD -- . ':!*.lock' | awk '{s+=$1+$2} END{print s}'` is under 800 (expected about 500: the rename counts 0, the cut counts once, the new file once); `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `Verification: entries before 2026-11-07 move verbatim to docs/VERIFICATION-ARCHIVE.md; the record stays short`.

**Phase 6 end:** add this phase's entry to the new `VERIFICATION.md` (it must still be under 1,000 lines).

---

## Self-review notes

- Spec coverage: five items → Phases 1, 2, 3, 4+5, 6. "Sources" for derived rows: every derived entry carries `sources` and `formula` (Tasks 8-9). "Viewer only lays out values": Tasks 7 and 10 (`prefer`, `quarter`); the old derivation remains only as the fallback for deliveries without the keys.
- Type consistency: `DerivedRows` fields `debt_register` (Task 7-8), `quarter_bridge`, `quarter_debt_register` (Task 9); store ops `prefer` (Task 7), `quarter`, `prefer-quarter` (Task 10); Go `readRunEvents` (Task 1), `tabWatching`/`finishNotice`/`notifyNatively`/`toastScript` (Task 3), `reviewJob`/`resumeRun` (Task 5); bridge `retained_of` (Task 4) and review keys `resume_of`/`retained_modules` (Tasks 4-6).
- Not in this plan (owner items, unchanged): in-app runs publishing a model (Decision 10); a click action on the Windows toast (Decision 3); quarter total/net leverage (needs quarter-end total carrying debt; Task 10 states the reason).
