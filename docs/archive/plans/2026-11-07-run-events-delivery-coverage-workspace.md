# Run Events, Delivery Coverage and Workspace Payload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (the global rules make it the coding method). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the open items from the UX/UI and System Review sessions by fixing their three structural causes, not each symptom. The causes: CP-OS emits no run state; delivery drops handoff content without saying so; the app rebuilds one unbounded workspace blob on every page load.

**Architecture:** Three phases, one PR each, in order.
1. The CP-OS core appends a run event log, and the bridge, Go server and browser read state from it.
2. The layout delivery path carries real gap rows, records where every handoff section went (and fails the build when one is dropped), and puts each module's execution and the decision-critical limits on the report's front page.
3. The store sends each distinct handoff once, keyed by hash, and reads each model manifest once. The Go server caches the store result until a workspace file changes.

**Tech Stack:** Python 3.13 (standard library in `store.py`; pydantic 2.14.1 in `src/`), Go, plain browser JavaScript, jsdom tests.

**Spec:** the Decisions section below. It comes from the 2026-11-07 architecture review of the UX/UI session (PR EricMG13/final-workflow#24, merged as `0c596eac`) and the System Review session, both checked against `main` at `0c596eac`. No separate spec file, per the one-record rule in `AGENTS.md`.

## Decisions

| Finding (verified at `0c596eac`) | Decision |
|---|---|
| CP-OS core writes no progress; the bridge writes `progress.json` with only `{module, step, spent_usd}` (`bridge.py:227-239`) | Core appends `events.jsonl` for live runs; Go derives progress from it (Tasks 1-2) |
| Every stop is `stopped` or `failed`, chosen by exception type (`bridge.py:258-270`) | One `stop_reason(error)` with six fixed values, written to `status.json` (Tasks 1-2) |
| Status is polled only while New run is open (`actions.js:26-34`); no title change or notification | App-wide watcher, title mark, a finish notification, fixed stop sentences (Task 3) |
| App accepts `max_turns` 1-200 (`jobs.go:289`), but the executor refuses anything over 64 (`model/handoff.py:357`), after `start-authorization.md` is written | Go limit becomes 64 (Task 2) |
| `starting` is read in Go and JS but never written | Delete it (Task 2) |
| Layout path gives each module one generic limitation (`markdown_delivery.py:274-279`) | Gap rows and paragraphs become limitations (Task 4) |
| No record of which section went where; `verify_delivery` only rebuilds bytes | `coverage.json`, checked when the delivery is built (Task 5) |
| Every module shows "Candidate", with no sign it ran live; CP-5/CP-6 restrictions never reach the front page | Execution sentence per module; cited front-page limits (Task 6) |
| A named run with no issuer ID hides its own model (`store.py:2249-2250` returns before the deliverables' ID) | Fall back to the deliverables' ID (Task 7) |
| Same handoff bytes in N runs are sent N times: 28 hardlinks give 560 MB (`adv-security-handoff-hardlinks.py` exit 1 on main) | `handoffs: {sha256: sections}`, parsed once per hash (Task 8) |
| Each model's `delivery.json`/`view.json` is read up to four times; an over-budget grid is computed, then dropped | One manifest pass; budget checked before cells are computed (Task 9) |
| `store.py` runs on every `GET /api/workspace` (`jobs.go:54-69`) | One-entry cache keyed by a workspace fingerprint (Task 10) |

**Changed from the review's first proposal (each decided on the facts above):**
- **The narrow delivery path stays, frozen.** Launcher runs always use the layout path (`cpos_launch._layout`). Retained manifests, `runs/*/verify.py` and three test files still depend on `prepare`/`mapped_module`. A live run without a layout is refused instead (Task 4).
- **No per-output lazy endpoint.** At boot the browser reads every output's `sections` for navigation, the evidence index and search (`views.js:14-27`, `screen.js:99-113`, `:251-279`). Sending each hash once fixes the measured 560 MB case without rewriting those screens. Add a lazy endpoint only when distinct handoff volume, not duplication, grows too large.
- **The cash flow grid stays in `store.py` for now.** Only the three hash-pinned `deliverables/tdg-model-1..3` reach it. Model delivery computes no growth, margin, LTM or senior leverage. A test (`test_issuer_library_store.py:349`) keeps `store.py` on the standard library. This phase only fixes its cost (Task 9); moving the derived rows is an owner call (see Owner calls).

## Global Constraints

- `runs/` and `deliverables/` never change. `validate.py quick`'s `retained` gate checks this. Only new live runs write `events.jsonl`; retained replays and verify scripts write nothing.
- No paid provider call. Tests use the fakes: `class Adapter` (`tests/test_handoff_loop.py:57-70`), the `provider` fixture (`tests/test_cpos_launch.py:167-209`), and `fakeEngine` (`apps/issuer-library/jobs_test.go:26-52`). Gates remove provider keys from their environment.
- Missing is never zero. A front-page limit the handoff doesn't state shows as "not stated in the handoff". Delivery never writes analysis.
- Existing delivery manifests must hash the same: every new request field uses `Field(default=None or (), exclude_if=...)`. `exclude_if` was verified on pydantic 2.14.1 here: a `None` field is left out of `model_dump_json` and parses back as `None`.
- `store.py` imports only the standard library.
- No new dependency. Excel stays input-only.
- Users are on Windows (Edge/Chrome). A result seen only on macOS says so.
- One PR per phase, each at most 800 changed lines excluding fixtures. Branch each phase from `main` after the previous phase merges: `claude/run-events`, `claude/delivery-coverage`, `claude/workspace-payload`. Pushing and each PR need the owner's go-ahead.
- Every brief and reviewer prompt includes:
  - no stub or fake value standing in for real behaviour;
  - no catch-all hiding a failure unless the fail-open is documented and logged;
  - expected values written by hand, never produced by the code under test;
  - every report ends with a `Not verified:` line.
- One short `VERIFICATION.md` entry per phase. No other review files.

## Validation Schedule

| When | Command | Passes when |
|---|---|---|
| Every task | The focused tests the task names (`timeout 300`) | New test seen failing for the stated cause, then exit 0 |
| Every commit | `python3 apps/issuer-library/validate.py quick` | Exit 0 |
| End of each phase | `validate.py full`, `validate.py browser`, `uv run python tools/quality_gate.py` | All exit 0 |
| End of each phase | Owner's Windows check: `Smoke-test.ps1`, then open the app in Edge | Phase 1: start a run, switch to the Library, see the title mark and the finish notification |
| Whole-branch review | `confidence-review`, `rewrite-tournament` (post-edit) on the phase diff | Confirmed defects fixed |

**Agents** (global §1): `mx-feature` implements every task. `mx-precise` reviews each task. `mx-adversary` also reviews Tasks 1, 2 and 10 (spend figures, ordering, concurrency). `mx-architect` does each phase's whole-branch review.

## Review Focus

1. **A worker killed mid-write** leaves a partial last line in `events.jsonl`: the app shows the last complete event, never an error page (Task 2 `TestRunProgressIgnoresATruncatedLastLine`).
2. **A retained run replayed or verified** writes no `events.jsonl` and no other file under `runs/` (Task 1 `test_a_run_without_an_events_folder_writes_no_events`; `retained` gate).
3. **A delivery manifest written before this plan** gives the same bytes and hash after the new optional fields (Task 6 `test_existing_layout_manifests_serialise_unchanged`).
4. **Two tabs open when a run finishes** give one visible notification, not two (Task 3: the notification `tag` is the run id).
5. **A Gaps section written as prose, with HTML comments or `###` subheadings** gives one limitation per paragraph; comments and headings are not limitations (Task 4 `test_prose_gaps_comments_and_subheadings`).

---

## Phase 1: run events (`claude/run-events`)

### Task 1: Event log in the CP-OS core

**Files:**
- Create: `src/deploy_workflow/run_events.py`
- Modify: `src/deploy_workflow/model/handoff.py`: `HandoffExecutor.__init__` (:341-375), `_turn` after `budget.reserve` (:497), `ModuleTools.write_handoff` rejection (:330-335)
- Modify: `src/deploy_workflow/owners/cpos.py`: `run_handoffs` (:255; module start :378, accept :390, delivery :392, completion :459), `run_live_handoffs` (:494-560)
- Test: `tests/test_run_events.py` (new), `tests/test_handoff_loop.py`, `tests/test_cpos_handoffs.py`

**Interfaces:**
- Produces, in `run_events.py`:
  - `EVENTS = "events.jsonl"`
  - `append_event(directory: Path, event: str, **fields: str | int) -> None`: appends one ASCII JSON line `{"at": "<UTC, seconds, Z>", "event": event, **fields}`, then flush and `os.fsync`. Amounts are `str(Decimal)`.
  - `read_events(path: Path, limit: int = 4 * 1024 * 1024) -> list[dict[str, Any]]`: reads at most `limit` bytes and drops only an unparsable last line.
  - `stop_reason(error: BaseException) -> str`, one of `budget | checker | provider | interrupted | ruling | other`:
    - `BudgetExhausted`, `RunStopped`, or a `cpos_live_stopped` message containing `overrun=True` → `budget`
    - a message starting `cpos_module_failed`, `cpos_live_not_accepted` or `cpos_retained_rejected` → `checker`
    - any other `cpos_live_stopped` → `provider`
    - `cpos_interrupted`, `cpos_live_already_started` → `interrupted`
    - `LivePauseInForce` → `ruling`
- Events and the fields each carries:

  | `event` | Fields | Written at |
  |---|---|---|
  | `module_started` | `module` | cpos.py:378 |
  | `turn` | `module`, `turn` (1-based), `max_turns`, `spent_usd`, `held_usd` (this call's reservation), `cap_usd` | handoff.py, after `reserve` succeeds |
  | `draft_rejected` | `module`, `writes_left` | handoff.py:330-335 |
  | `module_accepted` | `module` | cpos.py:390 |
  | `delivery_started` | — | cpos.py:392 |
  | `delivered` | — | after cpos.py:459 |
  | `stopped` | `reason` | `run_live_handoffs`' `except`, for `Exception` only, before the re-raise |

- New keyword `events: Path | None = None` on `HandoffExecutor` and `run_handoffs`. With `None`, nothing is written. `run_live_handoffs` passes its `directory`, so only live runs log.

- [ ] **Step 1: Write the failing tests.** In `test_handoff_loop.py`, using the existing `Adapter` and `turn()` helpers:

```python
def test_events_record_each_turn_and_rejection(tmp_path):
    # queue: a write_handoff the checker rejects, then one it accepts
    events = read_events(tmp_path / "run" / EVENTS)
    assert [e["event"] for e in events] == ["turn", "draft_rejected", "turn"]
    assert [e["turn"] for e in events if e["event"] == "turn"] == [1, 2]
    assert {e["max_turns"] for e in events if e["event"] == "turn"} == {MAX_TURNS}
    assert all(e["cap_usd"] == str(CAP) and Decimal(e["held_usd"]) > 0 for e in events if e["event"] == "turn")

def test_a_refused_reservation_writes_no_turn_event(tmp_path): ...   # cap below the first hold: no "turn" line
```

In `test_cpos_handoffs.py`, with the `provider` fixture: `test_live_run_events_cover_modules_and_delivery`. The non-`turn` events must equal, per module in plan order, `module_started` then `module_accepted`, followed by `delivery_started` and `delivered`. Also `test_a_run_without_an_events_folder_writes_no_events`: the existing replay test gives no `events.jsonl` anywhere under its directory.

In `test_run_events.py`: `stop_reason` parametrised over one instance of each class or message above, plus `ValueError("x")` → `other`; and `read_events` on a file whose last line is cut mid-JSON returns the complete lines.

- [ ] **Step 2:** Run `uv run pytest tests/test_run_events.py tests/test_handoff_loop.py tests/test_cpos_handoffs.py -q`. Expected: FAIL (import error, then missing events).
- [ ] **Step 3:** Implement the interfaces above.
- [ ] **Step 4:** Rerun Step 2. Expected: PASS. Then `validate.py quick`.
- [ ] **Step 5:** Commit: `CP-OS: live runs append an event log of modules, turns, rejections, delivery and the stop reason`.

### Task 2: Bridge and server read the event log

**Files:**
- Modify: `apps/issuer-library/engine/bridge.py:227-270`. Delete `started` and the `progress.json` writes; keep writing `<module>.md` on acceptance. Add `"reason": stop_reason(error)` to the stopped/failed `status.json`.
- Modify: `apps/issuer-library/jobs.go`:
  - `jobView` (:139-144) reads progress from events, falling back to `progress.json` for retained runs;
  - `max_turns` limit (:289) becomes 64;
  - delete `starting` (:178).
- Modify: `apps/issuer-library/web/actions.js:9,11` (delete `starting`)
- Test: `tests/test_cpos_app.py`, `apps/issuer-library/jobs_test.go`, `apps/issuer-library/server_test.go`

**Interfaces:**
- Consumes: `EVENTS`, `stop_reason` (Task 1).
- Produces: `runProgress(workspace, id string) (map[string]any, bool)` in jobs.go. It reads `runs/<id>/events.jsonl` through `io.LimitReader` (4 MiB) and drops an unparsable last line. It folds the events into `status["progress"]`:

  | Key | Meaning |
  |---|---|
  | `module` | last `module_started` |
  | `step` | `started` / `running` / `repairing` / `accepted` / `delivering` / `delivered` / `stopped`, from the last event (`turn`→`running`, `draft_rejected`→`repairing`) |
  | `turn`, `max_turns` | last `turn` |
  | `spent_usd`, `held_usd`, `cap_usd` | last `turn` |
  | `accepted` | count of `module_accepted` |

  The JSON key `progress` and its `module`/`step`/`spent_usd` keep their names, so `TestRunListAndStatusCarryReviewAndProgress` (`server_test.go:375`) still passes through the fallback.

- [ ] **Step 1: Write the failing tests.**
  - Go:
    - `TestRunProgressFoldsEvents`: write the event lines by hand; assert the folded map, e.g. `step=="repairing"`, `turn==2`, `accepted==1`.
    - `TestRunProgressIgnoresATruncatedLastLine`.
    - `TestRunProgressFallsBackToProgressJSON`.
    - `TestReviewRefusesMoreTurnsThanTheLoopAllows`: `max_turns` 65 → 400; 64 → accepted.
  - Python:
    - `test_a_budget_stop_reports_reason_budget`: the `provider` fixture with a cap below the first hold gives `status.json["reason"] == "budget"`.
    - `test_a_rejected_module_reports_reason_checker`: extend `test_a_rejected_module_stops_with_retained_work_and_no_report` (:186).
- [ ] **Step 2:** Run `go test -race ./... -run 'RunProgress|MoreTurns'` (in `apps/issuer-library`) and `uv run pytest tests/test_cpos_app.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement. `test_start_runs_the_launcher_to_a_report_the_library_can_serve` (:147) pins `progress.json` per call: change it to assert the same module order from `events.jsonl`, and name that change in the report. Update `TestReviewRunListManyStaleActiveJobsExceedTheCap` (:755), which writes `starting`, to use `running`.
- [ ] **Step 4:** Rerun Step 2, then `validate.py quick`. Expected: PASS.
- [ ] **Step 5:** Commit: `Issuer Library: run progress and stop reason come from the CP-OS event log; turn limit matches the loop`.

### Task 3: Run state visible on every screen

**Files:**
- Modify: `apps/issuer-library/web/boot.js` (add the watcher), `web/actions.js` (`describeModule` :36-43, `showStatus` :81-112, Start handler :188-199), `web/screen.js:403` (title), `web/screen.css`
- Create: `apps/issuer-library/web/run-watch.test.cjs`; add it to `NODE_TESTS` in `apps/issuer-library/validate.py:25-34`

**Interfaces:**
- Consumes: `/api/runs/list` items with `state`, `reason`, `modules`, `progress` (Task 2).
- Produces:
  - `watchRuns()` in boot.js:
    - Fetches `/api/runs/list` at boot, then every 5 s while any item is `running`, and stops when none is.
    - Sets the global `runMark`: `"● 2/4 · "` while running (accepted/total modules), `"✓ "` after complete, `"! "` after a stop or failure, `""` with no job.
    - Marks the Run activity rail item with the same symbol (`aria-label` "Run running, 2 of 4 modules", etc.).
    - On a job's transition from `running` to finished, if `Notification.permission === "granted"`, creates `new Notification("Issuer Library", {body, tag: id})`. `body` is `"<issuer> run complete"` or the stop sentence. Clicking opens the run.
  - `screen.js:403` becomes `` `${runMark}${moduleNames[next.module]} · Issuer Library` ``. The watcher re-applies the title when `runMark` changes.
  - The Start handler calls `Notification.requestPermission()` when `'Notification' in window` and permission is `default`. A refusal changes nothing else.
  - `STOP_COPY` in actions.js, shown before the redacted message:

    | `reason` | Sentence |
    |---|---|
    | `budget` | `Stopped: the next model call would pass the spending cap. Retained work is kept; a new run needs a higher cap.` |
    | `checker` | `Stopped: a module's handoff did not pass its check within the allowed turns.` |
    | `provider` | `Stopped: the model provider returned an error or an unknown charge.` |
    | `interrupted` | `Stopped: the run was interrupted before a response was retained.` |
    | `ruling` | `Failed: a provider ruling or pause is in force.` |
    | `other` | *(the message only)* |

  - `describeModule` shows `running <title>, turn 2 of 24`, `repairing <title> after a rejected draft` and `delivering the report`. The spend line reads `Recorded spend: USD <spent> of a USD <cap> cap; the next call holds USD <held>`.

- [ ] **Step 1: Write the failing tests** in `run-watch.test.cjs` (jsdom, fake timers and fetch as in `new-run.test.cjs:12-17`):
  - `'a run that finishes while the Library is open notifies once with the run id as tag'`
  - `'the title carries the run mark on every route and clears with no job'`
  - `'no notification is created without permission'`
  - `'polling stops when no run is active'`
  - `'a stopped run leads with the sentence for its reason'`: one assertion per row above.
  - `'a repairing module shows its turn and the rejected draft'`
- [ ] **Step 2:** Run `node --test --test-timeout=60000 web/run-watch.test.cjs` (needs `ISSUER_LIBRARY_JSDOM`). Expected: FAIL.
- [ ] **Step 3:** Implement. Keep `actions.js`' 2 s poll on New run unchanged.
- [ ] **Step 4:** Rerun Step 2, then `validate.py quick` and `validate.py browser`. Expected: PASS.
- [ ] **Step 5:** Commit: `Issuer Library: run state, stop reason and a finish notification on every screen`.

**Phase 1 end:** run the end-of-phase gates and the Windows check. Add one `VERIFICATION.md` entry, then request the owner's go-ahead for the PR.

---

## Phase 2: delivery coverage (`claude/delivery-coverage`)

### Task 4: Live runs need a layout; gaps become limitations

**Files:**
- Modify: `src/deploy_workflow/owners/cpos.py:300-305` (refuse a live run with no layout)
- Modify: `src/deploy_workflow/markdown_delivery.py`: `literal_module` limitations (:274-279) and a new `gap_limitations`
- Test: `tests/test_markdown_delivery_sections.py`, `tests/test_cpos_handoffs.py`

**Interfaces:**
- Produces: `gap_limitations(raw: str) -> tuple[str, ...]`:
  - Takes the `## Gaps` section after `hide_comments`, using the existing `section` (from `handoff_delivery`).
  - Gives one `plain("; ".join(cells))` per data row of each pipe table, and one `plain(paragraph)` per blank-line-separated paragraph.
  - `###` lines separate groups and are not limitations.
  - With no Gaps section, it returns `()`.
- `literal_module` limitations become `(<the existing fixed sentence>, *gap_limitations(raw))`.
- The refusal text: `ValueError("cpos_layout: a live-provider run needs a delivery layout")`, raised before any dispatch.

- [ ] **Step 1: Write the failing tests** with handoffs built by the file's `handoff()` helper (:20-29). Expected strings are written by hand:
  - `test_each_gap_row_and_paragraph_becomes_a_module_limitation`: a two-row Gaps table plus one paragraph gives `limitations[1:] == ("G1; Revolver availability; Not supplied", "G2; Lease detail; Not supplied", "Market inputs were not supplied.")`.
  - `test_prose_gaps_comments_and_subheadings`: an HTML comment and a `### Assurance limits` line produce no limitation.
  - `test_a_handoff_without_gaps_keeps_only_the_fixed_limitation`.
  - `test_a_live_run_without_a_layout_is_refused_before_any_call` (`provider.calls == []`).
- [ ] **Step 2:** Run `uv run pytest tests/test_markdown_delivery_sections.py tests/test_cpos_handoffs.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement. Tests that pin layout-delivery bytes or limitation counts change deliberately; list each one and its new assertion in the report.
- [ ] **Step 4:** Rerun Step 2, plus `tests/test_markdown_delivery.py tests/test_cpos_launch.py tests/test_portfolio_handoff_delivery.py`. Expected: PASS.
- [ ] **Step 5:** Commit: `Delivery: each handoff gap is a module limitation; a live run needs a layout`.

### Task 5: Coverage record, checked at build

**Files:**
- Modify: `src/deploy_workflow/markdown_delivery.py`: `markdown_files` (:657, :738, :829-848, :1052-1060)
- Test: `tests/test_markdown_delivery_sections.py`, `tests/test_markdown_delivery.py`

**Interfaces:**
- Produces: `coverage.json`, listed in `delivery.json` `files`:
  - Shape: `{"schema": "delivery-coverage/1", "modules": {module_id: [{"id", "heading", "kind": "table"|"prose", "line", "block"}]}}`.
  - Built from `metadata`, the heading line (`section_of`, `_ProseGroup.line`) and each table's binding `block_id`. Unrouted tables are recorded as `"evidence"`.
- Produces: `check_coverage(raw_by_module: dict[str, str], record: dict[str, Any]) -> None`, called in `markdown_files` before it returns:
  - Every `##`/`###` heading line (outside fences and comments) with non-heading content before the next heading must be the `line` of at least one entry.
  - Otherwise it raises `ValueError("delivery_coverage: <module> line <n> <heading> is not presented")`.

- [ ] **Step 1: Write the failing tests:**
  - `test_every_heading_with_content_is_in_the_coverage_record`: a code-built handoff with `##`, `###`, a table and prose; the record's lines equal a hand-written list.
  - `test_routed_sections_name_their_block_and_the_rest_name_evidence`.
  - `test_a_dropped_section_fails_the_build`: monkeypatch `_prose_groups` to drop one group → `delivery_coverage` error.
  - `test_recovery_handoffs_are_fully_covered`: build from the layout delivery manifest in `runs/cpos-sol-remaining-20261105/recovery/execution/` into `tmp_path`; it does not raise. The retained folder is not written.
- [ ] **Step 2:** Run `uv run pytest tests/test_markdown_delivery_sections.py tests/test_markdown_delivery.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun Step 2 and the Task 4 extras. Expected: PASS. `test_cpos_comparison.py` must still pass: CP-8 refuses unlisted files (`cpos.py:609-612`), so `coverage.json` must be listed.
- [ ] **Step 5:** Commit: `Delivery: a coverage record names where every handoff section went, and a dropped section fails the build`.

### Task 6: Execution and front-page limits

**Files:**
- Modify: `src/deploy_workflow/handoff_delivery.py`:
  - `DeliveryRequest` (:148-152): `module_execution: dict[str, str] | None = Field(default=None, exclude_if=lambda v: v is None)`;
  - `MarkdownLayout` (:137-145): `front: tuple[MarkdownRoute, ...] = Field(default=(), exclude_if=lambda v: not v)`.
- Modify: `src/deploy_workflow/owners/cpos.py`: extract `_module_execution(ordered, retained, request) -> dict[str, str]` from :450-453; use it for the completion record and for `DeliveryRequest(module_execution=...)` at :392.
- Modify: `src/deploy_workflow/markdown_delivery.py`: execution sentence per module; front-limits section next to the scope banner (:1029-1049).
- Modify: `src/deploy_workflow/owners/cpos_launch.py`: `_layout` (:394-436) adds `FRONT_ROUTES`.
- Test: `tests/test_markdown_delivery_sections.py`, `tests/test_cpos_launch.py`

**Interfaces:**
- `EXECUTION_WORDS` (in `markdown_delivery.py`) becomes each module's first limitation when `module_execution` is set:

  | `module_execution` | Sentence |
  |---|---|
  | `live-provider` | `Produced by a live model run and accepted by the CP-OS check; not native contract acceptance.` |
  | `retained-response-replay` | `Replayed from a retained response; no new model call was made.` |
  | `host-session` | `Produced in a host session and accepted by the CP-OS check.` |
  | `synthetic` | `Synthetic test content, not issuer analysis.` |

  Module `status` keeps its current value: passing the check is not native acceptance.
- Front limits: `<section id="delivery-limits" role="note">` before `call-root`, with one `<li>` per `front` route.
  - Text: `<route.label>: <plain paragraph> (<module> line <n>)`.
  - No match: `<route.label>: not stated in the handoff`.
  - All text is HTML-escaped. Each listed line also appears in `coverage.json` with block `"front"`.
- `FRONT_ROUTES` (prose routes; heading, prefix → label). Added only for modules in the run:

  | Module | Heading | Prefix | Label |
  |---|---|---|---|
  | CP-6 | `Request` | `**Module status:` | `Committee status` |
  | CP-5 | `Assurance conclusion` | `**Evidence traceability` | `Assurance` |
  | CP-2 | `Findings` | `**Assessment —` | `Assessment and confidence` |

  Before coding, confirm each prefix is required by that module's instructions (`runs/cpos-sol-remaining-20261105/recovery/CP-<n>.instructions.md`). A prefix the instructions don't require is dropped and named in the report.

- [ ] **Step 1: Write the failing tests:**
  - `test_existing_layout_manifests_serialise_unchanged`: for each retained layout delivery manifest under `runs/*/` (`delivery-*.json` with a `layout`), `DeliveryRequest.model_validate_json(raw).model_dump_json(indent=2).encode() == raw`.
    - First run this check at `0c596eac`, before any change. Older manifests may not round-trip even then. Hard-code the paths that pass as the test's list, so the test pins only manifests the current code reproduces.
  - `test_live_execution_reaches_each_module_limitation`.
  - `test_front_routes_put_the_cited_line_above_the_call`: a code-built CP-6 handoff whose Request line 9 reads `**Module status: Ready with Limitations. Committee status: Restricted.**` gives `report.html` containing `id="delivery-limits"`, `Committee status: Module status: Ready with Limitations. Committee status: Restricted.` and `(CP-6 line 9)`.
  - `test_a_front_route_with_no_match_says_not_stated`.
  - `test_launcher_layout_adds_front_routes_only_for_requested_modules` (in `test_cpos_launch.py`).
- [ ] **Step 2:** Run `uv run pytest tests/test_markdown_delivery_sections.py tests/test_cpos_launch.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun Step 2 and all delivery tests from Tasks 4-5. Expected: PASS.
- [ ] **Step 5:** Commit: `Delivery: each module says how it was produced; committee, assurance and confidence lines lead the report`.

**Phase 2 end:** run the end-of-phase gates and add one `VERIFICATION.md` entry. Note that retained deliveries built before this phase no longer rebuild byte-for-byte; their `verification.json` names the commit that built them.

---

## Phase 3: workspace payload (`claude/workspace-payload`)

### Task 7: Named run's own model; load-tolerant frame test

**Files:**
- Modify: `apps/issuer-library/engine/store.py:2249-2250` (`recorded_identity`)
- Modify: `apps/issuer-library/web/screens.test.cjs` (the report-frame test with the 20 ms wait)
- Test: `tests/test_issuer_library_store.py`

- [ ] **Step 1:** Write `test_a_named_run_without_an_id_takes_its_own_deliverables_id`. The case: a catalogue-named run with no `workflow.json` and its own `runs/alpha-001/deliveries/own`. Expected: its `issuerKey` is `id:<the delivery's issuer_id>`, and its model is listed for that run.
- [ ] **Step 2:** Run it, and the probe `python -I /Users/ericguei/Documents/final-workflow/.claude/worktrees/user-initiated-runs-context-d59039/.superpowers/sdd/2026-11-07-issuer-identity-and-report-acceptance/probes/branch3-own-model-name-only-run.py` with its documented arguments. Expected: both fail (probe exit 1).
- [ ] **Step 3:** When the name is set and the manifest has no ID, take the deliverables' single ID by the rule already at :2259. Replace the frame test's fixed 20 ms wait with a wait for the frame's `load` event, with a 5 s ceiling.
- [ ] **Step 4:** The test passes, the probe exits 0, and `screens.test.cjs` passes 10 runs in a row under `yes > /dev/null &` load on all cores (stop the load afterwards).
- [ ] **Step 5:** Commit: `Issuer Library: a named run without an ID shows its own model; the report-frame test waits for load`.

### Task 8: Each handoff sent once

**Files:**
- Modify: `apps/issuer-library/engine/store.py`: `collect_runs` (:543-660; `structured` at :591), `workspace_store` (:2390-2452)
- Modify: `apps/issuer-library/web/boot.js:11-15`
- Modify: test setups that copy boot's globals by hand: `web/library-workspace.test.cjs:69-78`, `web/screens.test.cjs`, `web/new-run.test.cjs`, `designs/build.py`
- Test: `tests/test_issuer_library_store.py`, `web/library-workspace.test.cjs`

**Interfaces:**
- Produces: `workspace_store(...)["handoffs"]: dict[sha256, sections]`. Output records keep every field except `sections`.
  - `structured` runs once per distinct digest through a `parsed: dict[str, tuple[sections, problem]]` shared across runs.
  - `parseError` and issues stay per output.
- Produces: `hydrate(data) -> data` in boot.js. It sets `out.sections = data.handoffs[out.sha256]` for every output and is called before the globals are assigned. Tests call it instead of copying the setup.

- [ ] **Step 1: Write the failing tests:**
  - `test_identical_handoff_bytes_in_many_runs_are_sent_once`: three runs with byte-identical `CP-1.md` give `len(store["handoffs"]) == 1`; the JSON is under 1.5× a one-run store.
  - JS: `'hydrate gives every output the sections of its own hash'`.
- [ ] **Step 2:** Run them, and the probe `adv-security-handoff-hardlinks.py` (same probes folder; `python -I <probe> <export-root> <go-binary> <python>`). Expected: FAIL; probe exit 1.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Tests pass. The probe exits 0 (body under 50 MB), and `adv-security-label-hardlinks.py` still exits 0. Then `validate.py quick` and `validate.py browser`.
- [ ] **Step 5:** Commit: `Issuer Library: each distinct handoff is parsed and sent once`.

### Task 9: One manifest pass; grid budget before compute

**Files:**
- Modify: `apps/issuer-library/engine/store.py`:
  - a new `model_manifests`, used by `delivery_identities` (:2212), `shown_models` (:1998), `run_shows` (:2104) and `read_model` (:2036);
  - `model_sources` called once per model;
  - `cashflow_of` (:1839), `read_cashflow` (:1909), `catalogue_models` (:2148-2161).
- Test: `tests/test_issuer_library_store.py`

**Interfaces:**
- Produces: `model_manifests(root: Path, folders: Iterable[str]) -> dict[str, tuple[dict[str, Any], dict[str, Any]] | str]`, giving each folder's (delivery, view) pair or a problem. It uses the existing bounded, unlinked `delivery_json` and `listed_view`.
- `read_cashflow(files, handoff, budget: int)`: when `len(layout) * len(columns) > budget`, it returns `("limit", ...)` without computing a cell. `catalogue_models` passes the remaining budget in the order the existing budget tests set.

- [ ] **Step 1: Write the failing tests:**
  - `test_each_model_manifest_is_read_once_per_load`: monkeypatch `delivery_json` with a counter; each model folder is read exactly once.
  - `test_a_grid_over_the_budget_is_not_computed`: monkeypatch `spec_cell` with a counter; it stays at 0.
- [ ] **Step 2:** Run `uv run pytest tests/test_issuer_library_store.py -q -k "once_per_load or not_computed"`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** All `test_issuer_library_store.py` tests and the budget tests (:2542-2707) pass, and `forecast-answer-key.json` is unchanged. The probes `branch3-issuer-groups-invariants.py` and `branch3-budget-order-sources-clause.py` exit 0.
- [ ] **Step 5:** Commit: `Issuer Library: model manifests read once per load; an over-budget grid is never computed`.

### Task 10: Workspace cache

**Files:**
- Modify: `apps/issuer-library/server.go`: `Application` (:24-42), `serveWorkspace` (:167-183), `POST /api/refresh` (:188-190)
- Modify: `apps/issuer-library/jobs.go:54-69` (replace the `ponytail:` comment)
- Test: `apps/issuer-library/server_test.go`, `apps/issuer-library/jobs_test.go`

**Interfaces:**
- Produces: `workspaceFingerprint(workspace string, catalogue Catalogue, engineDir string) (string, error)`. It is a SHA-256 over:
  - the catalogue JSON with `BuiltAt` zeroed;
  - sorted lines `relpath\tsize\tmtimeUnixNano` for every regular file under `workspace/runs` and `workspace/deliverables` (`filepath.WalkDir`, links not followed);
  - the same line for `engine/store.py`, `engine/catalog.json` and the visualisation catalogue CSV that `store.visual_catalogue` reads (`store.py:2166-2167`).
- Produces: `Application.storeCache struct{ mu sync.Mutex; key string; body []byte }`, one entry.
  - `serveWorkspace` computes the key under `storeCache.mu`. On a hit it returns `body`; otherwise it runs `engine.library` and stores the result only on success. Holding the mutex makes concurrent requests share one store run.
  - Errors are never cached.
  - `POST /api/refresh` and a workspace switch clear the cache.
  - Comment: `// ponytail: one entry keyed on size and mtime; an edit that keeps both is missed until Refresh. Hash the files if that happens.`

- [ ] **Step 1: Write the failing tests** (`fakeEngine` store script appends one line to a counter file per run):
  - `TestWorkspaceStoreRunsOnceUntilAFileChanges`: two GETs → 1 run; change a run file's size → 2.
  - `TestCatalogueRebuildAloneDoesNotRerunTheStore`: a `refresh()` that changes only `BuiltAt` → still 1. `/api/refresh` itself clears the cache, so call `app.refresh()` directly.
  - `TestConcurrentWorkspaceReadsShareOneStore`: 8 parallel GETs → 1 run.
  - `TestRefreshClearsTheWorkspaceCache`.
  - `TestAFailedStoreIsNotCached`.
- [ ] **Step 2:** Run `go test -race ./... -run 'WorkspaceStore|CatalogueRebuild|ConcurrentWorkspace|RefreshClears|FailedStore'`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun Step 2, then the existing locking tests: `TestStalledClientDoesNotHoldTheCatalogueLock` (:668), `TestWorkspaceSwitchDuringARefreshKeepsTheNewWorkspace` (:759), `TestConcurrentRefreshAndReaders` (:204). Expected: PASS.
- [ ] **Step 5:** Commit: `Issuer Library: the workspace store reruns only when a workspace file changes`.

**Phase 3 end:** run the end-of-phase gates and the Windows check (open a run with many models; reload twice; the second load is immediate). Add one `VERIFICATION.md` entry.

---

## Owner calls (not in this plan)

1. **Move the grid's derived rows** (growth, margins, LTM, senior secured leverage) into model delivery's `calculation.json`, with sources. This would make the viewer lay out values only. It needs new deliverables beside the hash-pinned `tdg-model-1..3`, and in-app runs that publish a model. Recommendation: do it when in-app runs first publish models.
2. **Resume from the app** after a stop. It needs a fresh paid-run approval flow; Task 2's stop reason is its input.
3. **Run activity page** listing a run's events (it still says "No live progress or cost recorded", `views.js:535`).
4. **Native Windows toast** when no browser tab is open. Add only if analysts close the tab during runs.
5. **`VERIFICATION.md` length** (5,650 lines) against the one-concise-record rule.
